"""Exercise the frozen run plan and worksheets exclusively with offline transports."""
import json
from copy import deepcopy
from hashlib import sha256

import pytest

import live_evaluation as live
from coordinator.analysis import MockAnalysisProvider
from coordinator.openai_provider import AttemptFailure, MODEL, OpenAIProvider
from prepare_trials import worksheets


def test_frozen_plan_and_separate_trial_conditions(tmp_path):
    requests = live.verified_cases()
    before = deepcopy(requests)
    journal = tmp_path / 'offline.jsonl'
    with journal.open('w', encoding='utf-8') as stream:
        live.record(stream, dataset_sha256=live.DATA_HASH, reference_sha256=live.REFERENCE_HASH)
        assert live.collect(stream, MockAnalysisProvider(), requests) == 'planned_trials_finished'
    rows = [json.loads(s) for s in journal.read_text(encoding='utf-8').splitlines()]
    assert requests == before
    assert [(r['case_id'], r['attempts']) for r in rows if r.get('status') == 'preflight_rejection'] == [('S9', 0)]
    accepted = [r for r in rows if r.get('status') == 'validated']
    assert len(accepted) == len({(r['case_id'], r['repetition']) for r in accepted}) == 27
    output = worksheets(journal, tmp_path / 'trials')
    assert len(list(output.glob('[0-9]*.md'))) == 15
    for path in output.glob('*Manual.md'):
        assert '## CANDIDATE' not in path.read_text(encoding='utf-8')
    for path in output.glob('*Live.md'):
        assert 'Candidate unavailable' in path.read_text(encoding='utf-8')
    for path in output.glob('*Mock.md'):
        assert '## CANDIDATE · deterministic_mock' in path.read_text(encoding='utf-8')
    with pytest.raises(FileExistsError):
        worksheets(journal, output)


def test_validation_rejection_retains_safe_diagnostics(tmp_path, monkeypatch):
    for key, value in [('OPENAI_LIVE_ENABLED', 'yes'), ('PHASE6A_REFERENCE_APPROVED', 'yes'),
                       ('OPENAI_API_KEY', 'offline-stub')]:
        monkeypatch.setenv(key, value)
    request = live.verified_cases()['S4']
    raw = MockAnalysisProvider().analyze(request)['analysis']
    raw['groups'] = raw['groups'][:1]
    response = dict(status='completed', model=MODEL, usage=dict(input_tokens=12, output_tokens=10),
                    output=[dict(type='message', role='assistant', content=[dict(type='output_text', text=json.dumps(raw))])])
    provider = OpenAIProvider(test_transport=lambda *_: response, test_ledger_path=tmp_path / 'ledger')
    with pytest.raises(AttemptFailure) as failure:
        provider.analyze(request)
    meta = failure.value.evidence
    assert meta['failure_stage'] == 'validation_rejection' and meta['schema_valid']
    assert meta['bounded_output'] == raw and meta['usage'] == response['usage']
    assert meta['estimated_usage_cost_usd'] > 0 and 'omitted' in meta['reason']
    response['output'][0]['content'][0]['text'] = json.dumps(dict(secret='unapproved arbitrary content'))
    with pytest.raises(AttemptFailure) as failure:
        provider.analyze(request)
    assert not failure.value.evidence['schema_valid'] and 'unapproved arbitrary content' not in str(failure.value.evidence)


def test_frozen_hashes_and_transport_stop(tmp_path):
    for filename, expected in [('cases.json', live.DATA_HASH), ('reference-expectations.json', live.REFERENCE_HASH)]:
        assert sha256((live.ROOT / 'evaluation' / filename).read_bytes()).hexdigest() == expected
    class Failed:
        def analyze(self, request):
            raise AttemptFailure(dict(failure_stage='provider_failure', usage=None, reason='transport_error'))
    with (tmp_path / 'log').open('w+') as stream:
        assert live.collect(stream, Failed(), live.verified_cases()).startswith('stopped_after')
        stream.seek(0)
        assert [json.loads(line)['status'] for line in stream] == [
            'preflight_rejection', 'scheduled_trial_started', 'provider_failure']
