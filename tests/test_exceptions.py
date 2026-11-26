from copy import deepcopy
from datetime import datetime, timezone, timedelta
import pytest
from coordinator.exceptions import inspect_case
from coordinator.scenarios import build_demo
from coordinator.auth import Auth
from coordinator.store import Store

AT = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)


@pytest.fixture(scope='module')
def demo(tmp_path_factory):
    path = tmp_path_factory.mktemp('scenarios') / 'demo.sqlite3'
    ids = build_demo(path, 'synthetic-test-password', AT)
    auth = Auth(path)
    return ids, Store(path, auth.login('SUPERVISOR', 'synthetic-test-password'))


def codes(case, at=AT):
    return {f['code'] for f in inspect_case(case, at)}


@pytest.mark.parametrize('scenario,expected', [('S1', 'SHORT_DELAY'), ('S2', 'MULTI_DAY_DELAY'),
    ('S3', 'DAMAGED'), ('S4', 'CONFLICT'), ('S5', 'NO_LOCAL_WORK')])
def test_scenarios_are_read_only(demo, scenario, expected):
    ids, store = demo
    before = store.case(ids[scenario])
    assert expected in codes(before)
    assert store.case(ids[scenario]) == before
    assert before['workflow_state'] == 'BLOCKED'


@pytest.mark.parametrize('section,field', [('task','description'), ('task','required_items'),
    ('task','project_id'), ('blocker','observed_condition'), ('source','supported_fields_or_note')])
def test_missing_context(demo, section, field):
    ids, store = demo; c = deepcopy(store.case(ids['S1']))
    record = c['task'] if section == 'task' else c['blockers' if section == 'blocker' else 'sources'][0]
    record.pop(field)
    assert any(f['code'] == 'MISSING_INFORMATION' and f['blocking'] for f in inspect_case(c, AT))


def test_unknown_and_sequence(demo):
    ids, store = demo; c = deepcopy(store.case(ids['S1']))
    c['blockers'][0]['material_fixture_status'] = 'UNKNOWN'
    c['task']['target_date_or_sequence'] = 'Step 4'
    assert {'UNKNOWN_MATERIAL_STATUS', 'SEQUENCE_REVIEW'} <= codes(c)
    assert c['blockers'][0]['material_fixture_status'] == 'UNKNOWN'
    c['sources'][0]['material_status'] = 'UNKNOWN'
    assert 'UNKNOWN_SOURCE_STATUS' in codes(c)


def test_missing_context_gate(demo):
    ids, store = demo
    key = store.create_task('SYN-MISSING', 'UNKNOWN', 'Incomplete area context', 'Step 1', [], 'SUPERVISOR')
    store.report_blocker(key, 'Delay', 'Missing fixture', 'SUPERVISOR', 'Synthetic note', 'Location not yet confirmed', 'MISSING')
    approve(store, key, 'UNDER_REVIEW')
    before = store.case(key)
    with pytest.raises(ValueError):
        approve(store, key, 'RESOLVED', {'material_fixture_status':'ARRIVED'})
    assert store.case(key) == before


@pytest.mark.parametrize('hours,code', [(1,'SHORT_DELAY'),(2,'SHORT_DELAY'),(3,'EXTENDED_DELAY'),(24,'MULTI_DAY_DELAY'),(72,'MULTI_DAY_DELAY')])
def test_delay_boundaries(demo, hours, code):
    ids, store = demo; c = deepcopy(store.case(ids['S1']))
    c['blockers'][0]['reported_at'] = (AT-timedelta(hours=hours)).isoformat()
    assert code in codes(c)


def test_target_and_closed_case(demo):
    ids, store = demo; c = deepcopy(store.case(ids['S1']))
    assert 'APPROACHING_TARGET' in codes(c)
    c['task']['target_date_or_sequence'] = (AT-timedelta(seconds=1)).isoformat()
    assert 'OVERDUE_OPEN_BLOCKER' in codes(c)
    c['blockers'][0]['workflow_state'] = 'RESOLVED'
    assert 'OVERDUE_OPEN_BLOCKER' not in codes(c)


def approve(store, key, target, corrections=None):
    c = store.case(key)
    store.review(key, c['workflow_state'], 'APPROVED', target, 'Synthetic team', 'Follow approved action',
                 'Synthetic supervisor verified supplied evidence', [s['source_id'] for s in c['sources']], corrections)


def test_conflict_gate_reconciliation_and_new_conflict(demo):
    ids, store = demo; key = ids['S4']; original = store.case(key)['sources']
    approve(store, key, 'UNDER_REVIEW')
    before = store.case(key)
    with pytest.raises(ValueError):
        approve(store, key, 'RESOLVED', {'material_fixture_status':'ARRIVED'})
    assert store.case(key) == before
    approve(store, key, '', {'material_fixture_status':'ARRIVED', 'conflict_resolution_note':'Supervisor checked both observations and verified arrival.'})
    assert 'CONFLICT_REVIEWED' in codes(store.case(key))
    assert store.case(key)['sources'] == original
    store.add_observation(key, 'Synthetic new note', 'Another report says still missing', 'MISSING')
    assert 'CONFLICT' in codes(store.case(key))
    assert store.case(key)['workflow_state'] == 'UNDER_REVIEW'


def test_s2_workaround_recovery_and_s5_reassignment(demo):
    ids, store = demo
    approve(store, ids['S2'], 'UNDER_REVIEW')
    ref = store.add_observation(ids['S2'], 'Synthetic inspection', 'Supervisor checked the temporary layout against the proposed display plan.')
    approve(store, ids['S2'], 'WORKAROUND_ACTIVE', dict(workaround_type='Temporary display', safety_approval_note='Human supplied demo approval', end_condition='Delivery verified', workaround_evidence_ref=ref))
    approve(store, ids['S2'], 'WAITING_FOR_MATERIAL')
    store.add_observation(ids['S2'], 'Synthetic recovery', 'New fixture delivered', 'ARRIVED')
    approve(store, ids['S2'], 'UNDER_REVIEW')
    approve(store, ids['S2'], 'RESOLVED', dict(material_fixture_status='ARRIVED', conflict_resolution_note='Supervisor verifies later delivery supersedes delay report.'))
    assert any(d['corrected_values'].get('end_condition') for d in store.case(ids['S2'])['decisions'])
    approve(store, ids['S5'], 'UNDER_REVIEW')
    approve(store, ids['S5'], 'REASSIGNED', dict(destination_context='Synthetic site B', return_condition='Return after delivery', local_work_exhausted='All demo local tasks blocked'))
    assert store.case(ids['S5'])['workflow_state'] == 'REASSIGNED'
    assert store.case(ids['S5'])['decisions'][-1]['corrected_values']['return_condition']


def test_unknown_prevents_resolution_and_associate_cannot_approve(demo):
    ids, store = demo; key = ids['S3']
    approve(store, key, 'UNDER_REVIEW')
    with pytest.raises(ValueError):
        approve(store, key, 'RESOLVED', {'material_fixture_status':'UNKNOWN'})
    associate = Store(store.path, store.auth.login('ASSOCIATE','synthetic-test-password'))
    with pytest.raises(PermissionError):
        approve(associate, key, 'RESOLVED')
    assert store.case(key)['workflow_state'] == 'UNDER_REVIEW'
