"""Exercise the frozen run plan and worksheets exclusively with offline transports."""
import json
import sqlite3
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


def test_recovery_preflight_preserves_history_and_requires_approval(tmp_path, monkeypatch):
    prior = tmp_path / 'run01.jsonl'
    journal = tmp_path / 'run02.jsonl'
    ledger = tmp_path / 'ledger.sqlite3'
    data = [
        dict(status='run_started', dataset_sha256=live.DATA_HASH, reference_sha256=live.REFERENCE_HASH, model=MODEL),
        dict(status='preflight_rejection', case_id='S9', attempts=0),
        dict(status='scheduled_trial_started', case_id='S1', repetition=1),
        dict(status='provider_failure', case_id='S1', repetition=1, metadata=dict(invocation_mode='live_attempt',
             http_status=403, budget_reservation_id='synthetic-reservation', reserved_cost_usd=0.01598775)),
        dict(status='stopped_after_failed_or_ambiguous_attempt')]
    prior.write_text('\n'.join(map(json.dumps, data)))
    monkeypatch.setattr(live, 'JOURNAL', prior)
    monkeypatch.setattr(live, 'RUN_02_JOURNAL', journal)
    monkeypatch.setattr(live, 'budget_path', lambda: ledger)
    monkeypatch.setattr(live, 'allowance', lambda: (29, 1984012250))
    with pytest.raises(sqlite3.OperationalError):
        live.main(True, '02')
    assert not ledger.exists()
    with sqlite3.connect(ledger) as db:
        db.execute('CREATE TABLE reservations (id TEXT, amount INTEGER, outcome TEXT)')
        db.execute("INSERT INTO reservations VALUES ('synthetic-reservation',15987750,'failed_or_rejected')")
    original = (prior.read_bytes(), ledger.read_bytes())
    live.main(True, '02')
    with pytest.raises(ValueError, match='separate owner approval'):
        live.main(False, '02')
    assert not journal.exists()
    journal.write_text('existing run 02')
    with pytest.raises(ValueError, match='already has a journal'):
        live.main(False, '02', True)
    assert journal.read_text() == 'existing run 02'
    assert original == (prior.read_bytes(), ledger.read_bytes())


def test_first_recovery_request_is_scored_s1_and_failure_stops(tmp_path):
    calls = []
    class Rejected:
        def analyze(self, request):
            calls.append(request['context']['task']['task_id'])
            raise AttemptFailure(dict(failure_stage='validation_rejection', usage={'input_tokens': 10}))
    with (tmp_path / 'run02').open('w+') as stream:
        assert live.collect(stream, Rejected(), live.verified_cases(), recovery=True).startswith('stopped_after')
        stream.seek(0)
        gate, scheduled, result = map(json.loads, stream)
    assert calls == ['SYN-EVAL-S1'] and gate['case_id'] == 'S9' and gate['attempts'] == 0
    assert all((r['case_id'], r['repetition']) == ('S1', 1) for r in (scheduled, result))
