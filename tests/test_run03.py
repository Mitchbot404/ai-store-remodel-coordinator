"""Offline intervention checks. No test obtains live model output."""
from copy import deepcopy
from hashlib import sha256
import json
import sqlite3

import pytest
from jsonschema import Draft202012Validator

import live_evaluation as live
from coordinator.analysis import (BASELINE_PROMPT_VERSION, PROMPT_VERSION, PROMPTS,
                                  MockAnalysisProvider, build_analysis_request, validate_analysis)
from coordinator.candidates import CandidateError
from coordinator.openai_provider import AttemptFailure, MODEL, OpenAIProvider


def archived(number):
    return json.loads((live.ROOT / 'evaluation/results' / f'live-run-{number}.json').read_bytes())


def independent_s1_fixture():
    return dict(review_state='CANDIDATE', groups=[
        dict(focus_code='TIMING_REVIEW', evidence_ids=['flag:0', 'flag:1']),
        dict(focus_code='MATERIAL_READINESS', evidence_ids=['source:S1-SRC-1']),
    ], question_codes=['VERIFY_TIMING'], recommendation_codes=['REQUEST_TIMING_REVIEW'])


def test_prompt_intervention_is_text_only_and_rejection_is_preserved():
    assert sha256(PROMPTS[BASELINE_PROMPT_VERSION].encode()).hexdigest() == (
        '27bedbf368ee9a049dbc065bce6477e5d893977811beb1758f7a33e37ccb2fcf')
    assert sha256(PROMPTS[PROMPT_VERSION].encode()).hexdigest() == (
        '8f4c64992e2e9022c00b93cdcc31c91795266fe98433b6a9f6ce66ad7491983e')
    cases = live.verified_cases()
    for legacy in cases.values():
        old = build_analysis_request(legacy, prompt_version=BASELINE_PROMPT_VERSION)
        new = build_analysis_request(legacy)
        assert old.pop('instructions') != new.pop('instructions') and old == new
    request = build_analysis_request(cases['S1'])
    rejected = archived('02')['attempts'][0]['metadata']['bounded_output']
    before = deepcopy(rejected)
    for version in PROMPTS:
        contract = build_analysis_request(cases['S1'], prompt_version=version)
        Draft202012Validator(contract['schema']).validate(rejected)
        with pytest.raises(CandidateError, match='Fabricated or repeated evidence reference'):
            validate_analysis(rejected, contract)
        assert rejected == before
    good = independent_s1_fixture()
    assert validate_analysis(good, request) == good


@pytest.mark.parametrize('field', ['question_codes', 'recommendation_codes', 'focus_code'])
def test_duplicate_codes_in_schema_valid_fixture(field):
    contract = build_analysis_request(live.verified_cases()['S1'])
    output = independent_s1_fixture()
    if field == 'focus_code':
        output['groups'].append(dict(focus_code='TIMING_REVIEW', evidence_ids=['flag:0']))
    else:
        output[field].append(output[field][0])
    Draft202012Validator(contract['schema']).validate(output)
    with pytest.raises(CandidateError, match='duplicate|repeated'):
        validate_analysis(output, contract)


@pytest.mark.parametrize('version', [BASELINE_PROMPT_VERSION, PROMPT_VERSION])
def test_wire_instructions_match_actual_metadata(version, tmp_path, monkeypatch):
    monkeypatch.setenv('OPENAI_LIVE_ENABLED', 'yes')
    monkeypatch.setenv('PHASE6A_REFERENCE_APPROVED', 'yes')
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-test-placeholder')
    request = live.verified_cases()['S1']
    before = deepcopy(request)
    def stub(payload, key):
        assert json.loads(payload)['instructions'] == PROMPTS[version]
        return dict(model=MODEL, status='completed', usage=dict(input_tokens=100, output_tokens=40),
                    output=[dict(type='message', role='assistant', content=[
                        dict(type='output_text', text=json.dumps(independent_s1_fixture()))])])
    provider = OpenAIProvider(prompt_version=version, test_transport=stub, test_ledger_path=tmp_path/'ledger')
    metadata = provider.analyze(request)['metadata']
    assert (metadata['invocation_mode'], metadata['prompt_version']) == ('offline_stub', version)
    assert MockAnalysisProvider().analyze(request)['metadata']['prompt_version'] == BASELINE_PROMPT_VERSION
    assert request == before


def test_v2_injection_and_required_evidence():
    cases = live.verified_cases()
    for case in ('S4', 'S6', 'S10'):
        request = build_analysis_request(cases[case])
        before = deepcopy(cases[case])
        output = MockAnalysisProvider().analyze(cases[case])['analysis']
        assert validate_analysis(output, request)['review_state'] == 'CANDIDATE'
        assert cases[case] == before
        if case == 'S10':
            assert 'ADMIN-999' in str(request['catalog']) and 'ADMIN-999' not in request['instructions']
            output['groups'][0]['evidence_ids'][0] = 'source:ADMIN-999'
            with pytest.raises(CandidateError): validate_analysis(output, request)
        else:
            assert request['required_evidence_ids'] and request['required_question_codes']
            for required in request['required_evidence_ids']:
                partial = deepcopy(output)
                for group in partial['groups']:
                    group['evidence_ids'] = [i for i in group['evidence_ids'] if i != required]
                partial['groups'] = [g for g in partial['groups'] if g['evidence_ids']]
                with pytest.raises(CandidateError): validate_analysis(partial, request)
            output['question_codes'] = ['CHECK_SOURCE_CONTEXT']
            with pytest.raises(CandidateError): validate_analysis(output, request)


def test_amended_protocol_records_rejection_then_advances_without_retry(tmp_path):
    original = live.verified_cases()
    cases = deepcopy(original)
    calls = []
    class Stub:
        def analyze(self, request):
            calls.append(request['context']['task']['task_id'])
            if len(calls) == 1:
                meta = deepcopy(archived('02')['attempts'][0]['metadata'])
                meta.update(invocation_mode='offline_stub', prompt_version=PROMPT_VERSION,
                            failure_stage='validation_rejection')
                raise AttemptFailure(meta)
            return MockAnalysisProvider().analyze(request)
    path = tmp_path / 'offline'
    with path.open('w') as stream:
        live.record(stream, status='run_started', prompt_version=PROMPT_VERSION)
        assert live.collect(stream, Stub(), cases, amended=True) == 'planned_trials_finished'
    assert cases == original
    assert calls == [v['context']['task']['task_id'] for v in cases.values()] * 3
    summary = live.run_counts({'03': path})['cumulative']
    assert summary == dict(attempts=27, validated=26, validation_rejection=1, provider_failure=0)
    rows = [json.loads(s) for s in path.read_bytes().splitlines()]
    assert len({(r['case_id'], r['repetition']) for r in rows if r['status']=='scheduled_trial_started'}) == 27
    assert rows[1]['case_id'] == 'S9' and rows[1]['attempts'] == 0


@pytest.mark.parametrize('update', [
    {'failure_stage': 'provider_failure'}, {'reason': 'unexpected_failure'}, {'usage': None},
    {'reservation_finalization_failed': True}, {'model': None}, {'prompt_version': BASELINE_PROMPT_VERSION},
    {'usage': {'input_tokens': 15}}, {'schema_valid': False}, {'estimated_usage_cost_usd': None},
    {'reason': 'schema_mismatch', 'bounded_output': {'review_state':'APPROVED'}},
    {'bounded_output': {'groups': [{'evidence_ids':['made-up','made-up']}]}}
])
def test_amendment_stops_on_uncertain_or_security_failures(tmp_path, update):
    meta = deepcopy(archived('02')['attempts'][0]['metadata'])
    meta.update(failure_stage='validation_rejection', invocation_mode='offline_stub', prompt_version=PROMPT_VERSION)
    meta.update(update)
    class Failed:
        def analyze(self, request):
            raise AttemptFailure(meta)
    with (tmp_path/'journal').open('w+') as stream:
        assert live.collect(stream, Failed(), live.verified_cases(), amended=True).startswith('stopped_after')
        stream.seek(0)
        assert len(list(stream)) == 3


def test_run03_requires_separate_approval_and_matches_both_reservations(tmp_path, monkeypatch):
    ledger = tmp_path/'ledger'
    with sqlite3.connect(ledger) as db:
        db.execute('CREATE TABLE reservations (id TEXT, amount INTEGER, outcome TEXT)')
        for number, name in [('01','JOURNAL'), ('02','RUN_02_JOURNAL')]:
            report = archived(number)
            attempt, = report['attempts']
            attempt['metadata']['budget_reservation_id'] = number
            rows = [dict(status='run_started', **report['run']), report['preflight'],
                    dict(status='scheduled_trial_started', case_id='S1', repetition=1),
                    attempt, dict(status=report['disposition'])]
            path = tmp_path / number
            path.write_text('\n'.join(map(json.dumps, rows)))
            monkeypatch.setattr(live, name, path)
            db.execute('INSERT INTO reservations VALUES (?,15987750,?)', (number,'failed_or_rejected'))
    path = tmp_path/'03'
    monkeypatch.setattr(live, 'RUN_03_JOURNAL', path)
    monkeypatch.setattr(live, 'budget_path', lambda: ledger)
    monkeypatch.setattr(live, 'allowance', lambda: (28, 1968024500))
    live.main(True, '03')
    with pytest.raises(ValueError, match='explicit owner approval'):
        live.main(False, '03', approved_run_02=True)
    assert not path.exists()
    path.write_text('original')
    with pytest.raises(ValueError, match='already has a journal'): live.main(False, '03', approved_run_03=True)
    assert path.read_text() == 'original'
    with sqlite3.connect(ledger) as db:
        db.execute("UPDATE reservations SET id='unrelated' WHERE id='01'")
    with pytest.raises(ValueError, match='historical reservations'): live.reconcile_before_run_03()
