import pytest
from coordinator.store import Store
from coordinator.models import WorkflowState, ALLOWED_TRANSITIONS


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'test.sqlite3')


def create(store, **changes):
    args = dict(project_id='SYN-01', department_area='Demo area', description='Install sample shelf',
                target_date_or_sequence='Step 1', required_items=['Sample shelf'], reporter_id='demo-associate',
                source_note='Synthetic plan calls for one shelf.')
    args.update(changes)
    return store.create_task(**args)


def report(store, task_id, **changes):
    args = dict(task_id=task_id, blocker_type='Material delay', observed_condition='Sample shelf missing',
                reporter_id='demo-associate', source_type='Synthetic note', source_note='Sample delivery delayed.')
    args.update(changes)
    return store.report_blocker(**args)


def test_round_trip_and_traceability(store):
    key = create(store)
    assert store.case(key)['workflow_state'] == 'READY'
    report(store, key, material_fixture_status='')
    case = Store(store.path).case(key)
    assert case['workflow_state'] == 'BLOCKED'
    assert case['task']['description'] == 'Install sample shelf'
    assert case['blockers'][0]['material_fixture_status'] == 'UNKNOWN'
    assert case['blockers'][0]['source_refs'][0] == case['sources'][1]['source_id']
    assert [e['new_state'] for e in case['audits']] == ['READY', 'BLOCKED']
    assert case['sources'][0]['supported_fields_or_note'] == 'Synthetic plan calls for one shelf.'


@pytest.mark.parametrize('field', ['project_id', 'department_area', 'description', 'target_date_or_sequence', 'reporter_id'])
def test_missing_task_fields(store, field):
    with pytest.raises(ValueError):
        create(store, **{field: ' '})
    assert store.tasks() == []


def test_missing_source_and_duplicate_are_atomic(store):
    key = create(store)
    with pytest.raises(ValueError):
        report(store, key, source_note='')
    assert store.case(key)['workflow_state'] == 'READY'
    report(store, key)
    before = store.case(key)
    with pytest.raises(ValueError):
        report(store, key)
    assert store.case(key) == before


def test_unknown_task(store):
    with pytest.raises(ValueError):
        report(store, 'nonexistent')


@pytest.mark.parametrize('state', list(WorkflowState))
def test_no_manual_state_bypass(store, state):
    key = create(store)
    with pytest.raises(PermissionError):
        store.transition(key, state, role='supervisor')
    assert store.case(key)['workflow_state'] == 'READY'


def test_exact_state_graph():
    assert len(WorkflowState) == 8
    assert sum(map(len, ALLOWED_TRANSITIONS.values())) == 11
    assert ALLOWED_TRANSITIONS['RESOLVED'] == {'READY', 'COMPLETED'}
    assert ALLOWED_TRANSITIONS['COMPLETED'] == set()
