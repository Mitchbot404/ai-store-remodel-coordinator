import sqlite3
import pytest
from coordinator.auth import Auth, Role
from coordinator.store import Store
from coordinator.models import ALLOWED_TRANSITIONS
import json


@pytest.fixture
def accounts(tmp_path):
    path = tmp_path / 'roles.sqlite3'
    auth = Auth(path)
    result = {}
    for role in Role:
        auth.provision(role.name, 'synthetic-password-123', role)
        result[role] = Store(path, auth.login(role.name, 'synthetic-password-123'))
    return result


def case(accounts):
    s = accounts[Role.ASSOCIATE]
    key = s.create_task('SYN', 'Area', 'Task', 'Step 1', [], 'ASSOCIATE')
    s.report_blocker(key, 'Delay', 'Missing', 'ASSOCIATE', 'Synthetic', 'Missing fixture')
    return key


def review(s, key, target, **kwargs):
    c = s.case(key)
    args = dict(task_id=key, expected_state=c['workflow_state'], decision_type='APPROVED', target=target,
                owner='Demo team', next_action='Follow recorded action', rationale='Human verifies condition from selected evidence',
                source_refs=[c['sources'][-1]['source_id']])
    if target in {'RESOLVED', 'COMPLETED'}:
        args['corrected_values'] = {'material_fixture_status': 'ARRIVED'}
    args.update(kwargs)
    s.review(**args)


@pytest.mark.parametrize('role', list(Role))
def test_role_permissions(accounts, role):
    key = case(accounts)
    s = accounts[role]
    if role == Role.TECHNICAL:
        with pytest.raises(PermissionError):
            s.case(key)
        with pytest.raises(PermissionError):
            s.add_observation(key, 'Synthetic', 'Update')
    else:
        s.add_observation(key, 'Synthetic', 'Update')
        assert s.case(key)['sources'][-1]['submitted_by'] == role.name
    if role != Role.SUPERVISOR:
        with pytest.raises(PermissionError):
            s.review(key, 'BLOCKED', 'APPROVED', 'UNDER_REVIEW', 'Owner', 'Action', 'Review', [])
    else:
        review(s, key, 'UNDER_REVIEW')
    if role in (Role.SUPPORT, Role.TECHNICAL):
        with pytest.raises(PermissionError):
            s.create_task('SYN', 'Area', 'Task', '1', [], role.name)
        with pytest.raises(PermissionError):
            s.report_blocker(key, 'Delay', 'Missing', role.name, 'Synthetic', 'Note')


@pytest.mark.parametrize('branch', ['WAITING_FOR_MATERIAL', 'WORKAROUND_ACTIVE', 'REASSIGNED'])
def test_lifecycle_and_preserved_history(accounts, branch):
    key = case(accounts)
    s = accounts[Role.SUPERVISOR]
    before = s.case(key)
    review(s, key, 'UNDER_REVIEW')
    details = {}
    if branch == 'WORKAROUND_ACTIVE':
        details = dict(workaround_type='Temporary display', safety_approval_note='Synthetic supervisor approval', end_condition='Fixture arrives')
    if branch == 'REASSIGNED':
        details = dict(destination_context='Synthetic store B', return_condition='Fixture arrives', local_work_exhausted='All local tasks blocked')
    review(s, key, branch, corrected_values=details)
    if branch == 'WORKAROUND_ACTIVE':
        review(s, key, 'WAITING_FOR_MATERIAL', rationale='Temporary work is complete; original blocker remains')
    s.add_observation(key, 'Synthetic shipment update', 'Fixture arrived; team returned')
    review(s, key, 'UNDER_REVIEW')
    review(s, key, 'RESOLVED')
    review(s, key, 'COMPLETED', rationale='Supervisor verifies completed task')
    c = Store(s.path, s.token).case(key)
    assert c['workflow_state'] == 'COMPLETED'
    assert c['audits'][:2] == before['audits']
    assert c['sources'][:1] == before['sources']
    assert c['decisions'][-1]['reviewer_id'] == 'SUPERVISOR'
    assert c['decisions'][-1]['approved_owner'] == 'Demo team'
    assert len([a for a in c['audits'] if a['action'] == 'STATE_TRANSITION_APPROVED']) == len(c['decisions'])


def test_resume_ready(accounts):
    key = case(accounts); s = accounts[Role.SUPERVISOR]
    for state in ['UNDER_REVIEW', 'RESOLVED', 'READY']:
        review(s, key, state)
    assert s.case(key)['workflow_state'] == 'READY'


@pytest.mark.parametrize('change', [dict(target='COMPLETED'), dict(source_refs=[]), dict(owner=''),
    dict(expected_state='READY'), dict(decision_type='INVALID'), dict(source_refs=['wrong-case']),
    dict(decision_type='REJECTED'), dict(corrected_values={'workflow_state': 'COMPLETED'})])
def test_rejected_changes_atomic(accounts, change):
    key = case(accounts); s = accounts[Role.SUPERVISOR]; before = s.case(key)
    with pytest.raises(ValueError):
        review(s, key, 'UNDER_REVIEW', **({k:v for k,v in change.items() if k != 'target'})) if 'target' not in change else review(s, key, change['target'])
    assert s.case(key) == before


@pytest.mark.parametrize('target', ['WORKAROUND_ACTIVE', 'REASSIGNED'])
def test_consequential_details_required(accounts, target):
    key = case(accounts); s = accounts[Role.SUPERVISOR]
    review(s, key, 'UNDER_REVIEW')
    with pytest.raises(ValueError):
        review(s, key, target)


def test_nontransition_reviews(accounts):
    key = case(accounts); s = accounts[Role.SUPERVISOR]
    for decision in ['REJECTED', 'UNRESOLVED']:
        review(s, key, '', decision_type=decision, owner='', next_action='')
    review(s, key, '', decision_type='CORRECTED', corrected_values={'material_fixture_status': 'Delayed'})
    c = s.case(key)
    assert len(c['decisions']) == 3
    assert c['workflow_state'] == 'BLOCKED'
    assert c['blockers'][0]['material_fixture_status'] == 'Delayed'


def test_authentication_and_revocation(accounts):
    s = accounts[Role.ASSOCIATE]
    with pytest.raises(PermissionError):
        s.auth.login('ASSOCIATE', 'wrong')
    with pytest.raises(PermissionError):
        Store(s.path).tasks()
    s.auth.logout(s.token)
    with pytest.raises(PermissionError):
        s.tasks()


def test_all_invalid_edges(accounts):
    key = case(accounts); s = accounts[Role.SUPERVISOR]
    for prior in ALLOWED_TRANSITIONS:
        for target in ALLOWED_TRANSITIONS:
            if prior == target or target in ALLOWED_TRANSITIONS[prior]:
                continue
            with s.connect() as db:
                blocker = json.loads(db.execute('SELECT record FROM blockers WHERE task_id=?', (key,)).fetchone()[0])
                blocker['workflow_state'] = prior
                db.execute('UPDATE blockers SET record=? WHERE task_id=?', (json.dumps(blocker), key))
            before = s.case(key)
            with pytest.raises(ValueError):
                review(s, key, target)
            assert s.case(key) == before
