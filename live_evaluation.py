"""Run the owner-approved v2 experiment in a private local Windows console."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from time import perf_counter

from coordinator.analysis import build_analysis_request, render_analysis, PROMPT_VERSION, SCHEMA_VERSION
from coordinator.candidates import build_request, validate, CandidateError
from coordinator.openai_provider import (
    AttemptFailure, OpenAIProvider, budget_path, MAX_REQUESTS, BUDGET_NANODOLLARS, MODEL,
)

ROOT = Path(__file__).resolve().parent
JOURNAL = ROOT / 'data' / 'phase6a-live-v2.jsonl'
RUN_02_JOURNAL = ROOT / 'data' / 'phase6a-live-v2-run-02.jsonl'
DATA_HASH = 'd1618ef687ca3c0f11f0b2d93fe55482520d0ee7ea902b0d384cef32f11e53db'
REFERENCE_HASH = '2f2baf43a64159f7f16b411ec29469fb351dccca33fcb79f20bf81807b688d0d'


def verified_cases():
    data = (ROOT / 'evaluation/cases.json').read_bytes()
    refs = (ROOT / 'evaluation/reference-expectations.json').read_bytes()
    if hashlib.sha256(data).hexdigest() != DATA_HASH or hashlib.sha256(refs).hexdigest() != REFERENCE_HASH:
        raise ValueError('The frozen evaluation inputs differ from the owner-approved hashes.')
    dataset = json.loads(data)
    requests = {}
    for entry in dataset['cases']:
        key = entry['id']
        try:
            request = build_request(entry['case'], dataset['evaluated_at'])
            build_analysis_request(request)
        except CandidateError:
            if key != 'S9':
                raise
        else:
            if key == 'S9':
                raise ValueError('Invalid-source case passed preflight. Stop.')
            requests[key] = request
    return requests


def allowance():
    path = budget_path()
    if os.name != 'nt' or path.parent.parent.resolve() != (Path.home() / 'AppData/Local').resolve():
        raise ValueError('Use the project owner’s normal local Windows account and ledger.')
    if not path.exists():
        return MAX_REQUESTS, BUDGET_NANODOLLARS
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        count, reserved = db.execute('SELECT COUNT(*), COALESCE(SUM(amount),0) FROM reservations').fetchone()
    return MAX_REQUESTS - count, BUDGET_NANODOLLARS - reserved


def verify_run_01(journal, ledger):
    """Reconcile the saved failure before permitting a separately journaled recovery."""
    rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
    if [r.get('status') for r in rows] != ['run_started', 'preflight_rejection',
            'scheduled_trial_started', 'provider_failure', 'stopped_after_failed_or_ambiguous_attempt']:
        raise ValueError('Recovery requires the original stopped run 01 journal.')
    header, preflight, start, result, _ = rows
    meta = result['metadata']
    if (header['dataset_sha256'] != DATA_HASH or header['reference_sha256'] != REFERENCE_HASH
            or header['model'] != MODEL or preflight['case_id'] != 'S9' or preflight['attempts'] != 0
            or any((r['case_id'], r['repetition']) != ('S1', 1) for r in (start, result))
            or meta['invocation_mode'] != 'live_attempt' or meta['http_status'] != 403):
        raise ValueError('Run 01 does not match the reconciled S1 failure.')
    with sqlite3.connect(ledger.as_uri() + '?mode=ro', uri=True) as db:
        row = db.execute('SELECT amount, outcome FROM reservations WHERE id=?',
                         (meta['budget_reservation_id'],)).fetchone()
    if row != (15_987_750, 'failed_or_rejected') or meta['reserved_cost_usd'] != 0.01598775:
        raise ValueError('The original run 01 reservation must remain in the cumulative ledger.')


def record(stream, **fields):
    fields['timestamp'] = datetime.now(timezone.utc).isoformat()
    stream.write(json.dumps(fields, ensure_ascii=False) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def collect(stream, provider, requests, *, recovery=False):
    if recovery and next(iter(requests), None) != 'S1':
        raise ValueError('Recovery must begin with S1 repetition one.')
    record(stream, case_id='S9', status='preflight_rejection', attempts=0, reason='invalid_required_source')
    for repeat in range(1, 4):
        for key, request in requests.items():
            trial = dict(case_id=key, repetition=repeat)
            record(stream, **trial, status='scheduled_trial_started')
            started = perf_counter()
            try:
                generation = provider.analyze(request)
            except AttemptFailure as error:
                meta = error.evidence
                record(stream, **trial, status=meta['failure_stage'], metadata=meta,
                       elapsed_seconds=perf_counter() - started)
                if (recovery and (key, repeat) == ('S1', 1)
                        or meta['failure_stage'] != 'validation_rejection' or not meta['usage']):
                    return 'stopped_after_failed_or_ambiguous_attempt'
            except CandidateError:
                record(stream, **trial, status='pre_provider_stop', reason='configuration_size_or_budget_gate')
                return 'stopped_at_gate'
            else:
                package = request['template']
                validate(package, request)
                display = render_analysis(generation['analysis'], build_analysis_request(request))
                record(stream, **trial, status='validated', **generation, package=package, display=display,
                       elapsed_seconds=perf_counter() - started)
    return 'planned_trials_finished'


def main(check_only, run='01', approved_run_02=False):
    requests = verified_cases()
    slots, capacity = allowance()
    recovery = run == '02'
    journal = RUN_02_JOURNAL if recovery else JOURNAL
    if recovery:
        verify_run_01(JOURNAL, budget_path())
        if journal.exists():
            raise ValueError('Run 02 already has a journal. Reconcile it before any further request.')
        print('Run 01 reconciled. Run 02 starts with S1 repetition 1. No connectivity probe.')
    print(f'Frozen inputs verified. {len(requests)} eligible cases. S9 blocked locally.')
    print(f'Remaining ledger allowance: {slots} attempts and USD {capacity / 1e9:.6f}.')
    if check_only:
        return
    if recovery and not approved_run_02:
        raise ValueError('Run 02 needs separate owner approval before private key entry.')
    if slots <= 0 or capacity <= 0:
        raise ValueError('Cumulative allowance exhausted.')
    if journal.exists():
        raise ValueError('An evaluation journal already exists. Inspect it before any further request.')
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('Open a private interactive PowerShell terminal for hidden entry.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT):
        raise ValueError('Run from the verified clean checkout.')
    key = getpass.getpass('Restricted project key (hidden, this evaluation process only): ').strip()
    if not key:
        raise ValueError('No key entered. No requests sent.')
    journal.parent.mkdir(exist_ok=True)
    with journal.open('x', encoding='utf-8') as stream:
        record(stream, status='run_started', run=run, commit=commit, model=MODEL, reference_version='phase6a-reference-v2',
               approved_on='2026-11-26', dataset_sha256=DATA_HASH, reference_sha256=REFERENCE_HASH,
               prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION, starting_slots=slots,
               starting_capacity_nanodollars=capacity)
        os.environ.update(OPENAI_API_KEY=key, OPENAI_LIVE_ENABLED='yes', PHASE6A_REFERENCE_APPROVED='yes')
        del key
        try:
            outcome = collect(stream, OpenAIProvider(), requests, recovery=recovery)
            record(stream, status=outcome)
            print(outcome)
        finally:
            for name in ('OPENAI_API_KEY', 'OPENAI_LIVE_ENABLED', 'PHASE6A_REFERENCE_APPROVED'):
                os.environ.pop(name, None)
    print('Local evidence saved. Return to the project chat for analysis.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify the frozen inputs and ledger offline.')
    parser.add_argument('--run', choices=['01', '02'], default='01')
    parser.add_argument('--approve-run-02', action='store_true', help='Use only after separate owner authorization for run 02.')
    try:
        args = parser.parse_args()
        main(args.check, args.run, args.approve_run_02)
    except (ValueError, OSError, sqlite3.Error) as error:
        sys.exit(str(error))
