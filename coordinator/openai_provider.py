"""Opt-in Responses adapter. No operational capability; no retries or secret logs."""
from datetime import datetime, timezone
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import sqlite3
from time import perf_counter
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4
from jsonschema import Draft202012Validator

from .candidates import CandidateError
from .analysis import build_analysis_request, validate_analysis, PROMPT_VERSION, SCHEMA_VERSION

MODEL = 'gpt-5.4-mini-2026-03-17'
ENDPOINT = 'https://api.openai.com/v1/responses'
MAX_REQUEST_BYTES = 32768
MAX_RESPONSE_BYTES = 65536
MAX_OUTPUT_TOKENS = 1500
TIMEOUT_SECONDS = 20
# USD in billionths: $0.75 / million input, $4.50 / million output.
INPUT_RATE = 750
OUTPUT_RATE = 4500
BUDGET_NANODOLLARS = 2_000_000_000
MAX_REQUESTS = 30


class AttemptFailure(CandidateError):
    """Only controlled evaluation evidence can cross the provider boundary."""
    def __init__(self, evidence):
        super().__init__('OpenAI generation failed or was rejected. No automatic retry; manual review remains available.')
        self.evidence = evidence


def budget_path():
    """One ledger for this Windows user, outside the synced repository."""
    base = os.environ.get('LOCALAPPDATA')
    if not base:
        raise CandidateError('Live evaluation requires the local Windows budget directory.')
    return Path(base) / 'CEN4010-Remodel-Coordinator' / 'evaluation-budget.sqlite3'


class BudgetLedger:
    """Reserve worst-case spend atomically and never release uncertain charges.

    Reservations persist across processes/runs; there is deliberately no reset API.
    The trusted local user must not delete this file or switch Windows accounts
    during the evaluation. Provider project limits remain a second boundary.
    """
    def __init__(self, path):
        self.path = Path(path)

    def reserve(self, request_bytes):
        # Count the entire JSON payload as potential input tokens plus protocol
        # overhead. UTF-8 bytes conservatively bound the byte-based tokenizer.
        amount = (request_bytes + 8192) * INPUT_RATE + MAX_OUTPUT_TOKENS * OUTPUT_RATE
        if not 0 < request_bytes <= MAX_REQUEST_BYTES:
            raise CandidateError('Evaluation request exceeds its size limit.')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute('CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, amount INTEGER NOT NULL, created_at TEXT NOT NULL, outcome TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            spent, count = db.execute('SELECT COALESCE(SUM(amount),0), COUNT(*) FROM reservations').fetchone()
            if count >= MAX_REQUESTS:
                raise CandidateError('The 30-request evaluation limit is exhausted.')
            if spent + amount > BUDGET_NANODOLLARS:
                raise CandidateError('The cumulative $2 evaluation budget is exhausted.')
            identifier = str(uuid4())
            db.execute('INSERT INTO reservations VALUES (?, ?, ?, ?)',
                       (identifier, amount, datetime.now(timezone.utc).isoformat(), 'reserved'))
        return identifier, amount

    def finish(self, identifier, outcome):
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE reservations SET outcome=? WHERE id=?', (outcome, identifier))


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'Redirect rejected', headers, None)


SAFE_ERROR_CODES = frozenset({
    'access_denied', 'billing_hard_limit_reached', 'context_length_exceeded',
    'insufficient_permissions', 'insufficient_quota', 'invalid_api_key', 'missing_scope',
    'invalid_request_error', 'model_access_denied', 'model_not_allowed', 'model_not_found',
    'organization_deactivated', 'permission_denied', 'rate_limit_exceeded',
    'server_error', 'unsupported_country_region_territory', 'unsupported_model',
    'unsupported_parameter', 'unsupported_value',
})


def _error_fields(detail):
    if not isinstance(detail, dict):
        return {}
    allowed_types = {'invalid_request_error', 'authentication_error', 'permission_error',
                     'insufficient_quota', 'rate_limit_error', 'server_error', 'api_error'}
    fields = {}
    for name, allowed in [('code', SAFE_ERROR_CODES), ('type', allowed_types)]:
        value = detail.get(name)
        if isinstance(value, str) and value:
            fields['provider_error_' + name] = value if value in allowed else 'unrecognized_' + name
    return fields


def _http_error_fields(error):
    """Extract only recognized machine codes. Never retain the message, body or headers."""
    try:
        raw = error.read(8193)
        if len(raw) <= 8192:
            body = json.loads(raw)
            if isinstance(body, dict):
                return _error_fields(body.get('error'))
    except (ValueError, RecursionError, OSError, HTTPException):
        pass
    finally:
        error.close()
    return {}


def _save_server_id(log, headers):
    identifier = headers.get('x-request-id') if headers else None
    if isinstance(identifier, str) and re.fullmatch(r'(?:req_[A-Za-z0-9]{1,96}|[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})', identifier):
        log.write(json.dumps({'provider_request_id': identifier}) + '\n')


def _send(payload, key, ledger, reservation):
    client_id = str(uuid4())
    request = Request(ENDPOINT, payload, {
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key,
        'X-Client-Request-Id': client_id,
    }, method='POST')
    directory = ledger.path.parent / 'private-request-ids'
    directory.mkdir(exist_ok=True)
    # One private file per reservation, outside the synced repo. Write the client
    # ID before dispatch so it is available even when no response headers arrive.
    with (directory / (reservation + '.jsonl')).open('x', encoding='utf-8') as log:
        log.write(json.dumps({'client_request_id': client_id}) + '\n')
        log.flush()
        try:
            with build_opener(_NoRedirect()).open(request, timeout=TIMEOUT_SECONDS) as response:
                _save_server_id(log, response.headers)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            _save_server_id(log, error.headers)
            raise
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Oversized response')
    return json.loads(raw)


def _extract(response):
    if not isinstance(response, dict) or response.get('status') != 'completed' or response.get('error') or response.get('incomplete_details'):
        raise ValueError('Incomplete response')
    if response.get('model') != MODEL:
        raise ValueError('Unexpected model')
    messages = response.get('output')
    if not isinstance(messages, list):
        raise ValueError('Missing output')
    texts = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError('Malformed message')
        if message.get('type') == 'reasoning':
            continue
        if message.get('type') != 'message' or message.get('role') != 'assistant':
            raise ValueError('Unexpected output type')
        for part in message.get('content', []):
            if not isinstance(part, dict) or part.get('type') != 'output_text' or not isinstance(part.get('text'), str):
                raise ValueError('Refusal or malformed content')
            texts.append(part['text'])
    if len(texts) != 1 or len(texts[0].encode('utf-8')) > MAX_RESPONSE_BYTES:
        raise ValueError('Missing or oversized structured output')
    usage = response.get('usage', {})
    counts = {name: usage.get(name) for name in ('input_tokens', 'output_tokens')}
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError('Missing token usage')
    return json.loads(texts[0]), counts


class OpenAIProvider:
    """The optional stub transport is for offline tests, never labeled live."""
    def __init__(self, *, test_transport=None, test_ledger_path=None):
        if (test_transport is None) != (test_ledger_path is None):
            raise ValueError('Test transport and temporary ledger must be supplied together.')
        self._test_transport = test_transport
        self._test_ledger_path = test_ledger_path

    def analyze(self, legacy_request):
        if os.environ.get('OPENAI_LIVE_ENABLED') != 'yes' or os.environ.get('PHASE6A_REFERENCE_APPROVED') != 'yes':
            raise CandidateError('Live generation is disabled until reference review and explicit enablement.')
        key = os.environ.get('OPENAI_API_KEY', '')
        if not key.strip():
            raise CandidateError('Configure OPENAI_API_KEY locally; never paste it into the application.')
        request = build_analysis_request(legacy_request)
        context = {k: request[k] for k in (
            'context', 'catalog', 'required_evidence_ids', 'allowed_question_codes',
            'allowed_recommendation_codes', 'required_question_codes')}
        settings = {'reasoning': {'effort': 'none'}, 'max_output_tokens': MAX_OUTPUT_TOKENS, 'store': False}
        payload = json.dumps({
            'model': MODEL, 'instructions': request['instructions'],
            'input': [{'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}],
            'text': {'format': {'type': 'json_schema', 'name': 'candidate_review_focus',
                                'strict': True, 'schema': request['schema']}},
            **settings,
        }, ensure_ascii=False).encode('utf-8')
        if len(payload) > MAX_REQUEST_BYTES:
            raise CandidateError('Evaluation request exceeds its size limit.')
        ledger = BudgetLedger(self._test_ledger_path if self._test_transport else budget_path())
        reservation, amount = ledger.reserve(len(payload))
        started = perf_counter()
        evidence = dict(provider='openai', requested_model=MODEL, model=None,
                        invocation_mode='offline_stub' if self._test_transport else 'live_attempt',
                        prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION, settings=settings,
                        budget_reservation_id=reservation, reserved_cost_usd=amount / 1_000_000_000,
                        usage=None, estimated_usage_cost_usd=None, schema_valid=None,
                        completed_response=False, failure_stage='provider_failure', reason='transport_error')
        try:
            response = (self._test_transport(payload, key) if self._test_transport else
                        _send(payload, key, ledger, reservation))
            evidence['reason'] = 'unexpected_or_incomplete_response'
            if isinstance(response, dict):
                evidence.update(_error_fields(response.get('error')))
                evidence['model'] = MODEL if response.get('model') == MODEL else None
                evidence['completed_response'] = response.get('status') == 'completed'
                counts = response.get('usage')
                if isinstance(counts, dict) and all(type(counts.get(k)) is int and counts[k] >= 0
                                                     for k in ('input_tokens', 'output_tokens')):
                    evidence['usage'] = {k: counts[k] for k in ('input_tokens', 'output_tokens')}
                    evidence['estimated_usage_cost_usd'] = (
                        counts['input_tokens'] * INPUT_RATE + counts['output_tokens'] * OUTPUT_RATE) / 1e9
            try:
                output, usage = _extract(response)
            except ValueError as error:
                # Only fixed adapter categories can enter the evaluation journal.
                evidence['reason'] = {
                    'Unexpected model': 'model_mismatch', 'Incomplete response': 'incomplete_or_error',
                    'Refusal or malformed content': 'refusal_or_malformed_content',
                    'Missing token usage': 'missing_usage', 'Unexpected output type': 'unexpected_output_type',
                }.get(str(error), 'invalid_response')
                raise
            if usage['input_tokens'] > len(payload) + 8192 or usage['output_tokens'] > MAX_OUTPUT_TOKENS:
                # Keep full reservation; never retry unexpected billing/output.
                raise ValueError('Unexpected usage')
            evidence.update(failure_stage='validation_rejection', reason='schema_mismatch',
                            schema_valid=Draft202012Validator(request['schema']).is_valid(output))
            if not evidence['schema_valid']:
                raise ValueError('Schema mismatch')
            # The strict schema admits only known codes and evidence IDs.
            evidence['bounded_output'] = output
            try:
                analysis = validate_analysis(output, request)
            except CandidateError as error:
                evidence['reason'] = str(error)  # validator uses local fixed messages only
                raise
            elapsed = perf_counter() - started
            evidence.update(failure_stage='provider_failure', reason='ledger_finalization')
            ledger.finish(reservation, 'validated')
        except Exception as error:
            if isinstance(error, HTTPError):
                evidence.update(reason='http_error', http_status=error.code, **_http_error_fields(error))
            elif isinstance(error, json.JSONDecodeError) and evidence['completed_response']:
                evidence.update(failure_stage='validation_rejection', reason='invalid_json', schema_valid=False)
            evidence['latency_seconds'] = round(perf_counter() - started, 6)
            try:
                ledger.finish(reservation, 'failed_or_rejected')
            except Exception:
                pass  # Existing reservation remains counted even if logging fails.
            raise AttemptFailure(evidence) from None
        return {'analysis': analysis, 'metadata': {
            'provider': 'openai', 'model': MODEL,
            'invocation_mode': 'offline_stub' if self._test_transport else 'live_response',
            'prompt_version': PROMPT_VERSION, 'schema_version': SCHEMA_VERSION,
            'settings': settings, 'latency_seconds': round(elapsed, 6), 'usage': usage,
            'schema_valid': True, 'completed_response': True,
            'reserved_cost_usd': amount / 1_000_000_000,
            'estimated_usage_cost_usd': (usage['input_tokens'] * INPUT_RATE + usage['output_tokens'] * OUTPUT_RATE) / 1_000_000_000,
            'budget_reservation_id': reservation,
        }}
