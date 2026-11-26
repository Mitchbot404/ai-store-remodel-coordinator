from datetime import datetime, timezone
import json
import sqlite3
import pytest
from coordinator.auth import Auth
from coordinator.store import Store
from coordinator.scenarios import build_demo
from coordinator.candidates import CandidateService, CandidateError, MockProvider, FailureProvider


@pytest.fixture(scope='module')
def demo(tmp_path_factory):
    path = tmp_path_factory.mktemp('phase5') / 'demo.sqlite3'
    ids = build_demo(path, 'integration-test-password')
    auth = Auth(path)
    return ids, Store(path, auth.login('SUPERVISOR', 'integration-test-password'))


@pytest.mark.parametrize('scenario', ['S1','S2','S3','S4','S5'])
@pytest.mark.parametrize('outcome', ['APPROVED','CORRECTED','REJECTED','UNRESOLVED'])
def test_scenario_candidate_evaluation(demo, scenario, outcome):
    ids, store = demo; key = ids[scenario]; service = CandidateService(store)
    package = service.generate(key, MockProvider())
    candidate = service.latest(key); before = store.case(key)
    store.evaluate_candidate(key, candidate['candidate_id'], outcome, 'Human records uncertainty and verifies sources',
                             'Request further supervisor review', 'Synthetic review rationale', package['source_refs'])
    after = store.case(key); decision = after['decisions'][-1]
    assert decision['candidate_id'] == candidate['candidate_id']
    assert decision['candidate_snapshot'] == package
    assert decision['reviewer_id'] == 'SUPERVISOR'
    assert decision['decision_type'] == outcome and decision['approved_transition'] == ''
    assert after['task'] == before['task'] and after['blockers'] == before['blockers']
    assert after['sources'] == before['sources']
    assert after['audits'][:-1] == before['audits']
    assert after['audits'][-1]['action'] == 'CANDIDATE_EVALUATED'
    assert after['audits'][-1]['prior_state'] == after['audits'][-1]['new_state']
    assert service.latest(key)['package'] == package
    assert service.history(key)[0]['reviewed']
    assert json.loads(package['supported_status'])['approved_owner'] == 'UNASSIGNED'


def test_stale_invalid_failure_and_history(demo):
    ids, store = demo; key = ids['S4']; service = CandidateService(store)
    package = service.generate(key, MockProvider()); identifier = service.latest(key)['candidate_id']
    store.add_observation(key, 'Synthetic', 'Further observation', 'UNKNOWN')
    before = store.case(key)
    with pytest.raises(CandidateError):
        store.evaluate_candidate(key, identifier, 'APPROVED', 'Status', 'Step', 'Rationale', package['source_refs'])
    assert store.case(key) == before
    assert service.latest(key) == {'stale': True}
    with pytest.raises(CandidateError): service.generate(key, FailureProvider())
    assert store.case(key) == before
    service.generate(key, MockProvider()); newer = service.latest(key)['candidate_id']
    assert newer != identifier and any(h['candidate_id'] == identifier for h in service.history(key))
    with sqlite3.connect(service.path) as db:
        bad = json.loads(db.execute('SELECT package FROM candidates WHERE rowid=?', (newer,)).fetchone()[0])
        bad['review_state'] = 'APPROVED'
        db.execute('UPDATE candidates SET package=? WHERE rowid=?', (json.dumps(bad), newer))
    with pytest.raises(CandidateError):
        store.evaluate_candidate(key, newer, 'APPROVED', 'Status', 'Step', 'Rationale', package['source_refs'])
    assert store.case(key) == before


def test_unauthorized_evaluation(demo):
    ids, store = demo
    for role in ['ASSOCIATE','SUPPORT','TECHNICAL']:
        actor = Store(store.path, store.auth.login(role, 'integration-test-password'))
        with pytest.raises(PermissionError):
            actor.evaluate_candidate(ids['S1'], '1', 'APPROVED', 'Status', 'Action', 'Reason', [])


def test_evaluation_does_not_replace_approved_owner(demo):
    ids, store = demo; key = ids['S2']; case = store.case(key)
    store.review(key, case['workflow_state'], 'APPROVED', 'UNDER_REVIEW', 'Approved team', 'Approved action', 'Human review', [case['sources'][0]['source_id']])
    service = CandidateService(store); package = service.generate(key, MockProvider())
    store.evaluate_candidate(key, service.latest(key)['candidate_id'], 'CORRECTED', 'Different assessment', 'Proposed action only', 'Correction', package['source_refs'])
    regenerated = service.generate(key, MockProvider())
    assert json.loads(regenerated['supported_status'])['approved_owner'] == 'Approved team'
    assert json.loads(regenerated['supported_status'])['approved_next_action'] == 'Approved action'
