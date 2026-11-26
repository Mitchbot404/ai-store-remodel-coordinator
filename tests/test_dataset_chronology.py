"""Check event times and same-case provenance independently of candidate generation."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'evaluation'
DATA = json.loads((ROOT / 'cases.json').read_bytes())


def stamp(value):
    instant = datetime.fromisoformat(value)
    assert instant.utcoffset() is not None
    return instant


@pytest.mark.parametrize('entry', DATA['cases'], ids=lambda entry: entry['id'])
def test_case_chronology_and_source_links(entry):
    case = entry['case']
    task = case['task']
    blocker, = case['blockers']
    cutoff = stamp(DATA['evaluated_at'])
    start = stamp(task['created_at'])
    reported = stamp(blocker['reported_at'])
    assert start <= reported <= cutoff
    assert blocker['task_id'] == task['task_id']
    sources = {s['source_id']: s for s in case['sources']}
    assert len(sources) == len(case['sources'])
    for source in sources.values():
        assert source['authorization_flag'] == 'SYNTHETIC'
        assert source['supported_fields_or_note'].strip()
        assert start <= stamp(source['captured_at']) <= cutoff
    # Blocker links are cumulative through the snapshot. Decision links are as-of approval.
    assert set(blocker['source_refs']) - sources.keys() == (
        {'S9-SRC-NOT-RECORDED'} if entry['id'] == 'S9' else set())
    for decision in case['decisions']:
        decided = stamp(decision['decided_at'])
        assert reported <= decided <= cutoff
        assert decision['source_refs']
        for ref in decision['source_refs']:
            assert stamp(sources[ref]['captured_at']) <= decided
    if entry['id'] == 'S2':
        decision, = case['decisions']
        assert set(decision['source_refs']) == {'S2-INTAKE', 'S2-LAYOUT'}
        assert all(stamp(sources[ref]['captured_at']) > stamp(decision['decided_at'])
                   for ref in ('S2-SRC-1', 'S2-SRC-2'))


def test_checked_in_offline_evidence_matches_review_artifacts():
    refs = ROOT / 'reference-expectations.json'
    reference = json.loads(refs.read_bytes())
    assert reference['dataset_version'] == DATA['dataset_version']
    assert reference['status'] == DATA['reference_status'] == 'AI_DRAFT_PENDING_HUMAN_REVIEW'
    assert reference['reviewer'] is None and reference['reviewed_at'] is None
    for report_path in ('mock.json', 'mock-bounded.json'):
        report = json.loads((ROOT / 'results' / report_path).read_bytes())
        assert report['dataset_sha256'] == hashlib.sha256((ROOT / 'cases.json').read_bytes()).hexdigest()
        assert report['reference_sha256'] == hashlib.sha256(refs.read_bytes()).hexdigest()
