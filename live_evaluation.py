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


def record(stream, **fields):
    fields['timestamp'] = datetime.now(timezone.utc).isoformat()
    stream.write(json.dumps(fields, ensure_ascii=False) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def collect(stream, provider, requests):
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
                if meta['failure_stage'] != 'validation_rejection' or not meta['usage']:
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


def main(check_only):
    requests = verified_cases()
    slots, capacity = allowance()
    print(f'Frozen inputs verified. {len(requests)} eligible cases. S9 blocked locally.')
    print(f'Remaining ledger allowance: {slots} attempts and USD {capacity / 1e9:.6f}.')
    if check_only:
        return
    if slots <= 0 or capacity <= 0:
        raise ValueError('Cumulative allowance exhausted.')
    if JOURNAL.exists():
        raise ValueError('An evaluation journal already exists. Inspect it before any further request.')
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('Open a private interactive PowerShell terminal for hidden entry.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT):
        raise ValueError('Run from the verified clean checkout.')
    key = getpass.getpass('Restricted project key (hidden, this evaluation process only): ').strip()
    if not key:
        raise ValueError('No key entered. No requests sent.')
    JOURNAL.parent.mkdir(exist_ok=True)
    with JOURNAL.open('x', encoding='utf-8') as stream:
        record(stream, status='run_started', commit=commit, model=MODEL, reference_version='phase6a-reference-v2',
               approved_on='2026-11-26', dataset_sha256=DATA_HASH, reference_sha256=REFERENCE_HASH,
               prompt_version=PROMPT_VERSION, schema_version=SCHEMA_VERSION, starting_slots=slots,
               starting_capacity_nanodollars=capacity)
        os.environ.update(OPENAI_API_KEY=key, OPENAI_LIVE_ENABLED='yes', PHASE6A_REFERENCE_APPROVED='yes')
        del key
        try:
            outcome = collect(stream, OpenAIProvider(), requests)
            record(stream, status=outcome)
            print(outcome)
        finally:
            for name in ('OPENAI_API_KEY', 'OPENAI_LIVE_ENABLED', 'PHASE6A_REFERENCE_APPROVED'):
                os.environ.pop(name, None)
    print('Local evidence saved. Return to the project chat for analysis.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify the frozen inputs and ledger offline.')
    try:
        main(parser.parse_args().check)
    except (ValueError, OSError, sqlite3.Error) as error:
        sys.exit(str(error))
