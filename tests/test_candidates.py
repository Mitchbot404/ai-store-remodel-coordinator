from copy import deepcopy
from datetime import datetime, timezone
import pytest
from coordinator.auth import Auth
from coordinator.store import Store
from coordinator.scenarios import build_demo
from coordinator.candidates import CandidateService, CandidateError, MockProvider, FailureProvider, build_request, validate

AT = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)


@pytest.fixture(scope='module')
def demo(tmp_path_factory):
    path = tmp_path_factory.mktemp('candidate') / 'demo.sqlite3'
    ids = build_demo(path, 'candidate-test-password', AT)
    auth = Auth(path)
    return ids, Store(path, auth.login('SUPERVISOR', 'candidate-test-password'))


@pytest.mark.parametrize('scenario', ['S1','S2','S3','S4','S5'])
def test_scenario_generation_is_read_only(demo, scenario):
    ids, store = demo; key = ids[scenario]; before = store.case(key)
    service = CandidateService(store)
    package = service.generate(key, MockProvider(), AT)
    assert package['review_state'] == 'CANDIDATE'
    assert store.case(key) == before
    assert service.latest(key)['package'] == package
    if scenario == 'S4':
        assert package['conflicts']
        assert 'ARRIVED' in package['supported_status'] and 'MISSING' in package['supported_status']


@pytest.mark.parametrize('mutation', ['missing','extra','bad_ref','unsupported','unknown','conflict','approval','type','next_step','time'])
def test_adversarial_output_rejected(demo, mutation):
    ids, store = demo
    request = build_request(store.case(ids['S4']), AT.isoformat())
    output = deepcopy(request['template'])
    if mutation == 'missing': del output['uncertainty_note']
    elif mutation == 'extra': output['approved_owner'] = 'Autonomous team'
    elif mutation == 'bad_ref': output['source_refs'] = ['invented-source']
    elif mutation == 'unsupported': output['supported_status'] = 'Truck arrives tomorrow at 9.'
    elif mutation == 'unknown': output['missing_fields'] = ['All information confirmed.']
    elif mutation == 'conflict': output['conflicts'] = []
    elif mutation == 'approval': output['review_state'] = 'APPROVED'
    elif mutation == 'type': output['source_refs'] = 'wrong-type'
    elif mutation == 'next_step': output['candidate_next_step'] = 'Reassign the team and resolve this blocker.'
    else: output['generated_at'] = 'yesterday'
    with pytest.raises(CandidateError): validate(output, request)


def test_mock_deterministic_and_prompt_boundary(demo):
    ids, store = demo
    request = build_request(store.case(ids['S1']), AT.isoformat())
    assert MockProvider().generate(request) == MockProvider().generate(request)
    assert not {'sessions','users','audits','password'} & set(request['context'])
    assert 'UNKNOWN' in request['instructions'] and 'untrusted' in request['instructions']


def test_unknown_and_failure_fallback(demo):
    ids, store = demo
    key = store.create_task('SYN-UNKNOWN', 'Demo', 'UNKNOWN fixture details', 'Step 1', [], 'SUPERVISOR')
    store.report_blocker(key, 'Delay', 'Awaiting details', 'SUPERVISOR', 'Synthetic', 'Status unknown')
    service = CandidateService(store); before = store.case(key)
    package = service.generate(key, MockProvider(), AT)
    assert 'UNKNOWN' in package['supported_status'] and package['missing_fields']
    with pytest.raises(CandidateError): service.generate(key, FailureProvider(), AT)
    assert store.case(key) == before
    assert service.latest(key)['package'] == package
    store.add_observation(key, 'Synthetic', 'New note')
    assert service.latest(key) == {'stale':True}


def test_rejected_provider_does_not_persist_or_write(demo):
    ids, store = demo; key = ids['S1']; before = store.case(key)
    service = CandidateService(store); previous = service.latest(key)
    class BadProvider:
        def generate(self, request):
            output = request['template']; output['review_state'] = 'APPROVED'; return output
    with pytest.raises(CandidateError): service.generate(key, BadProvider(), AT)
    assert store.case(key) == before and service.latest(key) == previous


def test_non_supervisor_denied(demo):
    ids, store = demo
    associate = Store(store.path, store.auth.login('ASSOCIATE','candidate-test-password'))
    with pytest.raises(PermissionError): CandidateService(associate).generate(ids['S1'], MockProvider(), AT)


def test_context_change_rejected(demo):
    ids, store = demo; key = ids['S5']; service = CandidateService(store)
    class SlowProvider:
        def generate(self, request):
            store.add_observation(key, 'Synthetic concurrent update', 'Evidence changed during generation')
            return request['template']
    with pytest.raises(CandidateError): service.generate(key, SlowProvider(), AT)
    assert service.latest(key)['stale']
