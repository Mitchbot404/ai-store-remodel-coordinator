"""Paid API access is never used: every provider call has an injected transport."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import sqlite3

import pytest

from coordinator.candidates import CandidateError
from coordinator.analysis import MockAnalysisProvider
from coordinator.openai_provider import (
    OpenAIProvider, BudgetLedger, MODEL, MAX_OUTPUT_TOKENS, MAX_REQUEST_BYTES,
    BUDGET_NANODOLLARS, budget_path,
)


@pytest.fixture
def legacy_request():
    return {'context': {
        'task': {'task_id': 'synthetic-task', 'department_area': 'Demo', 'description': 'Fixture delayed'},
        'blocker': {'blocker_id': 'synthetic-blocker', 'material_fixture_status': 'DELAYED',
                    'observed_condition': 'Fixture delayed'},
        'workflow_state': 'BLOCKED', 'approved_owner': 'UNASSIGNED',
        'approved_next_action': 'UNASSIGNED', 'flags': [],
        'sources': [{'source_id': 'source-1', 'supported_fields_or_note': 'Synthetic delayed fixture',
                     'material_status': 'DELAYED', 'authorization_flag': 'SYNTHETIC'}],
    }}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv('OPENAI_LIVE_ENABLED', 'yes')
    monkeypatch.setenv('PHASE6A_REFERENCE_APPROVED', 'yes')
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-test-placeholder')


def response_for(legacy_request):
    output = MockAnalysisProvider().analyze(legacy_request)['analysis']
    return {'status': 'completed', 'model': MODEL,
            'output': [{'type': 'message', 'role': 'assistant',
                        'content': [{'type': 'output_text', 'text': json.dumps(output)}]}],
            'usage': {'input_tokens': 500, 'output_tokens': 100}}


def test_adapter_wire_contract_and_offline_metadata(legacy_request, enabled, tmp_path):
    calls = []
    before = deepcopy(legacy_request)
    def transport(payload, key):
        calls.append(json.loads(payload))
        assert key == 'offline-test-placeholder'
        assert key.encode() not in payload
        return response_for(legacy_request)
    result = OpenAIProvider(test_transport=transport, test_ledger_path=tmp_path/'ledger.sqlite3').analyze(legacy_request)
    payload = calls[0]
    assert payload['model'] == MODEL and payload['store'] is False
    assert payload['reasoning'] == {'effort': 'none'}
    assert payload['max_output_tokens'] == MAX_OUTPUT_TOKENS
    assert payload['text']['format']['strict'] is True
    assert not {'tools', 'previous_response_id'} & set(payload)
    assert result['metadata']['invocation_mode'] == 'offline_stub'
    assert result['metadata']['usage'] == {'input_tokens': 500, 'output_tokens': 100}
    assert result['analysis']['review_state'] == 'CANDIDATE'
    assert legacy_request == before


@pytest.mark.parametrize('gate', ['OPENAI_LIVE_ENABLED', 'PHASE6A_REFERENCE_APPROVED', 'OPENAI_API_KEY'])
def test_configuration_gates_prevent_transport(legacy_request, enabled, tmp_path, monkeypatch, gate):
    monkeypatch.delenv(gate)
    calls = []
    provider = OpenAIProvider(test_transport=lambda *args: calls.append(args), test_ledger_path=tmp_path/'ledger.sqlite3')
    with pytest.raises(CandidateError):
        provider.analyze(legacy_request)
    assert not calls and not (tmp_path/'ledger.sqlite3').exists()


@pytest.mark.parametrize('mutation', ['refusal', 'incomplete', 'malformed', 'model', 'tool', 'usage', 'fabricated', 'unsupported'])
def test_failed_outputs_rejected_without_retry(legacy_request, enabled, tmp_path, mutation):
    response = response_for(legacy_request)
    if mutation == 'refusal': response['output'][0]['content'] = [{'type': 'refusal', 'refusal': 'Cannot comply'}]
    elif mutation == 'incomplete': response['status'] = 'incomplete'
    elif mutation == 'malformed': response['output'][0]['content'][0]['text'] = '{truncated'
    elif mutation == 'model': response['model'] = 'unapproved-model'
    elif mutation == 'tool': response['output'] = [{'type': 'function_call', 'name': 'resolve_blocker'}]
    elif mutation == 'usage': response['usage']['output_tokens'] = MAX_OUTPUT_TOKENS + 1
    else:
        output = json.loads(response['output'][0]['content'][0]['text'])
        if mutation == 'fabricated': output['groups'][0]['evidence_ids'] = ['fabricated-source']
        else: output['approved_owner'] = 'Invented approval'
        response['output'][0]['content'][0]['text'] = json.dumps(output)
    calls = []
    def transport(*args):
        calls.append(True)
        return response
    ledger = tmp_path/'ledger.sqlite3'
    with pytest.raises(CandidateError):
        OpenAIProvider(test_transport=transport, test_ledger_path=ledger).analyze(legacy_request)
    assert len(calls) == 1
    with sqlite3.connect(ledger) as db:
        assert db.execute('SELECT outcome FROM reservations').fetchone()[0] == 'failed_or_rejected'
        assert db.execute('SELECT amount FROM reservations').fetchone()[0] > 0


def test_timeout_redacts_provider_exception_and_keeps_reservation(legacy_request, enabled, tmp_path):
    def timeout(*args):
        raise TimeoutError('offline-test-placeholder should never be shown')
    with pytest.raises(CandidateError) as error:
        OpenAIProvider(test_transport=timeout, test_ledger_path=tmp_path/'ledger.sqlite3').analyze(legacy_request)
    assert 'offline-test-placeholder' not in str(error.value)
    assert error.value.__suppress_context__


def test_oversized_request_never_reaches_transport(legacy_request, enabled, tmp_path):
    legacy_request['context']['sources'][0]['supported_fields_or_note'] = 'x' * (MAX_REQUEST_BYTES + 1)
    calls = []
    with pytest.raises(CandidateError):
        OpenAIProvider(test_transport=lambda *args: calls.append(True), test_ledger_path=tmp_path/'ledger.sqlite3').analyze(legacy_request)
    assert calls == []


def test_budget_is_cumulative_atomic_and_bounded(tmp_path):
    path = tmp_path/'ledger.sqlite3'
    # Initialize before concurrent reservations, then race several independent instances.
    BudgetLedger(path).reserve(100)
    def reserve(_):
        try:
            BudgetLedger(path).reserve(100)
            return True
        except CandidateError:
            return False
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(reserve, range(40)))
    assert sum(results) == 29
    with sqlite3.connect(path) as db:
        total, count = db.execute('SELECT SUM(amount), COUNT(*) FROM reservations').fetchone()
        assert count == 30 and total <= BUDGET_NANODOLLARS
    with pytest.raises(CandidateError): BudgetLedger(path).reserve(100)


def test_dollar_ceiling_blocks_before_reserving(tmp_path):
    path = tmp_path/'ledger.sqlite3'
    BudgetLedger(path).reserve(100)
    with sqlite3.connect(path) as db:
        db.execute('UPDATE reservations SET amount=?', (BUDGET_NANODOLLARS,))
    with pytest.raises(CandidateError, match='budget'):
        BudgetLedger(path).reserve(100)


def test_default_path_and_stub_pair_cannot_silently_change_budget(monkeypatch, tmp_path):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert budget_path() == tmp_path/'CEN4010-Remodel-Coordinator'/'evaluation-budget.sqlite3'
    monkeypatch.delenv('LOCALAPPDATA')
    with pytest.raises(CandidateError): budget_path()
    with pytest.raises(ValueError): OpenAIProvider(test_ledger_path=tmp_path/'reset.sqlite3')
