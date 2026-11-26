"""Offline end-to-end checks. No external API is invoked."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import pytest
from streamlit.testing.v1 import AppTest
from coordinator.auth import Auth
from coordinator.store import Store
from coordinator.scenarios import build_demo
from coordinator.candidates import CandidateService, CandidateError
from coordinator.analysis import MockAnalysisProvider
from evaluate_ai import run

AT = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)


@pytest.fixture(scope='module')
def demo(tmp_path_factory):
    path = tmp_path_factory.mktemp('phase6a') / 'demo.sqlite3'
    ids = build_demo(path, 'offline-fixture-password', AT)
    return ids, Store(path, Auth(path).login('SUPERVISOR', 'offline-fixture-password'))


@pytest.mark.parametrize('scenario', ['S1', 'S2', 'S3', 'S4', 'S5'])
def test_sidecar_generation_and_review_preserve_operational_authority(demo, scenario):
    ids, store = demo
    key = ids[scenario]; service = CandidateService(store); before = store.case(key)
    package = service.generate(key, MockAnalysisProvider(), AT)
    latest = service.latest(key)
    assert store.case(key) == before
    assert latest['generation_metadata']['invocation_mode'] == 'deterministic_mock'
    assert latest['analysis']['review_state'] == 'CANDIDATE'
    store.evaluate_candidate(key, latest['candidate_id'], 'CORRECTED', 'Human assessment',
                             'Proposed clarification only', 'Synthetic comparison', package['source_refs'])
    after = store.case(key)
    for field in ('task', 'blockers', 'sources', 'workflow_state'):
        assert after[field] == before[field]
    assert after['decisions'][-1]['candidate_analysis'] == latest['analysis']
    assert after['decisions'][-1]['approved_transition'] == ''
    assert service.latest(key)['analysis'] == latest['analysis']


def test_corrupt_sidecar_and_stale_generation_rejected(demo):
    ids, store = demo; key = ids['S4']; service = CandidateService(store)
    package = service.generate(key, MockAnalysisProvider(), AT)
    candidate = service.latest(key); before = store.case(key)
    with sqlite3.connect(service.path) as db:
        bad = deepcopy(candidate['analysis']); bad['review_state'] = 'APPROVED'
        db.execute('UPDATE candidates SET analysis=? WHERE rowid=?', (json.dumps(bad), candidate['candidate_id']))
    with pytest.raises(CandidateError): service.latest(key)
    with pytest.raises(CandidateError):
        store.evaluate_candidate(key, candidate['candidate_id'], 'APPROVED', 'Status', 'Step', 'Reason', package['source_refs'])
    assert store.case(key) == before
    class Concurrent:
        def analyze(self, request):
            store.add_observation(key, 'Synthetic', 'Changed during analysis', 'UNKNOWN')
            return MockAnalysisProvider().analyze(request)
    with pytest.raises(CandidateError): service.generate(key, Concurrent(), AT)
    assert service.latest(key)['stale']


def test_unauthorized_analysis_and_disabled_live_fallback(demo, monkeypatch):
    ids, store = demo; key = ids['S1']
    for username in ('ASSOCIATE', 'SUPPORT', 'TECHNICAL'):
        other = Store(store.path, store.auth.login(username, 'offline-fixture-password'))
        with pytest.raises(PermissionError): CandidateService(other).generate(key, MockAnalysisProvider(), AT)
    monkeypatch.setenv('CANDIDATE_PROVIDER', 'openai')
    monkeypatch.delenv('OPENAI_LIVE_ENABLED', raising=False)
    before = store.case(key)
    with pytest.raises(CandidateError): CandidateService(store).generate(key, at=AT)
    assert store.case(key) == before
    assert CandidateService(store).latest(key)['package']


@pytest.mark.parametrize('mode', ['manual', 'mock', 'mock_bounded'])
def test_dataset_offline_comparison(mode):
    result = run(mode)
    assert len(result['results']) == 10
    assert result['human_evaluation'] == 'NOT_PERFORMED'
    assert result['reference_status'] == 'AI_DRAFT_PENDING_HUMAN_REVIEW'
    for item in result['results']:
        if item['case_id'] == 'S9':
            assert item['status'] == 'rejected_or_failed' and item['failure_stage'] == 'preflight'
        else:
            assert item['status'] == ('manual_review_pending' if mode == 'manual' else 'validated')
        assert item['human_assessment'] is None


def test_live_evaluation_requires_exact_dataset_review():
    with pytest.raises(ValueError, match='Review'):
        run('live', approval_hash='unreviewed')


def test_supervisor_analysis_ui_and_failure_fallback(demo, monkeypatch):
    ids, store = demo
    monkeypatch.setenv('REMODEL_DB', store.path)
    monkeypatch.setenv('CANDIDATE_PROVIDER', 'mock_bounded')
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'))
    app.session_state['token'] = store.token
    app.run()
    assert not app.exception
    next(b for b in app.button if b.label == 'Generate CANDIDATE summary').click().run()
    assert not app.exception
    assert any('deterministic_mock' in c.value for c in app.caption)
    assert any('CANDIDATE review focus' in m.value for m in app.markdown)
    next(c for c in app.checkbox if c.label.startswith('Simulate provider')).check().run()
    next(b for b in app.button if b.label == 'Generate CANDIDATE summary').click().run()
    assert app.error and not app.exception
    assert any(b.label == 'Record human review' for b in app.button)
