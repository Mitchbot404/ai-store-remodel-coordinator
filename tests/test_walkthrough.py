"""Offline regression checks derived from the synthetic Sporting Goods walkthrough."""
import secrets
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from coordinator.auth import Auth, Role
from coordinator.candidates import CandidateError, CandidateService, FailureProvider, MockProvider
from coordinator.store import Store


@pytest.fixture
def shipment(tmp_path):
    path = tmp_path / 'walkthrough.sqlite3'
    auth = Auth(path)
    password = secrets.token_urlsafe(24)
    auth.provision('reviewer', password, Role.SUPERVISOR)
    store = Store(path, auth.login('reviewer', password))
    key = store.create_task('Synthetic', 'Sporting Goods', 'Set display', 'Step 2', [], 'reviewer')
    store.report_blocker(key, 'Shipment', 'Fixture delayed', 'reviewer', 'Shipment observation',
                         'A confirmed replacement delivery date is unavailable.', 'DELAYED')
    return store, key


def test_workaround_requires_designated_observation(shipment):
    store, key = shipment
    label = store.add_observation(key, 'Synthetic supervisor observation', 'Structured material observation', 'DELAYED')
    store.review(key, 'BLOCKED', 'APPROVED', 'UNDER_REVIEW', 'Team', 'Verify', 'Delay reported', [label])
    detail = 'Supervisor observed the proposed temporary display in its marked location.'
    ref = store.add_observation(key, 'Layout inspection', detail)
    before = store.case(key)
    fields = dict(workaround_type='Temporary display', end_condition='Shipment verified',
                  safety_approval_note='Supervisor reviewed the temporary layout.')

    def activate(refs, **extra):
        store.review(key, 'UNDER_REVIEW', 'APPROVED', 'WORKAROUND_ACTIVE', 'Team', 'Use temporary layout',
                     'Supervisor reviewed the cited inspection', refs, {**fields, **extra})

    for refs, extra in [([label, ref], {}), ([label, ref], {'workaround_evidence_ref': label}),
                        ([label], {'workaround_evidence_ref': ref}), ([ref], {'workaround_evidence_ref': 'unrelated'})]:
        with pytest.raises(ValueError, match='observation|observed'):
            activate(refs, **extra)
        assert store.case(key) == before
    activate([label, ref], workaround_evidence_ref=ref)
    after = store.case(key)
    assert after['workflow_state'] == 'WORKAROUND_ACTIVE'
    assert after['decisions'][-1]['corrected_values']['workaround_evidence_ref'] == ref
    assert after['audits'][-1]['source_refs'] == [label, ref]
    assert after['sources'] == before['sources']


def test_workbench_saves_submitted_observation_verbatim(shipment, monkeypatch):
    store, key = shipment
    monkeypatch.setenv('REMODEL_DB', store.path)
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'))
    app.session_state['token'] = store.token
    app.run()
    def widget(widgets, label):
        return next(item for item in widgets if item.label == label)
    note = 'Inspected the marked location.\nThe proposed temporary display is documented here.'
    widget(app.selectbox, 'Structured observation').select('DELAYED')
    widget(app.button, 'Save observation').click().run()
    assert any('source_note is required' in item.value for item in app.error)
    assert len(store.case(key)['sources']) == 1
    widget(app.text_area, 'New source observation').set_value(note)
    widget(app.button, 'Save observation').click().run()
    assert not app.exception
    source = store.case(key)['sources'][-1]
    assert (source['supported_fields_or_note'], source['material_status']) == (note, 'DELAYED')
    ref = source['source_id']
    store.review(key, 'BLOCKED', 'APPROVED', 'UNDER_REVIEW', 'Team', 'Verify', 'Delay recorded', [ref])
    app.run()
    widget(app.selectbox, 'Approved transition').select('WORKAROUND_ACTIVE')
    widget(app.selectbox, 'Observation I verified supports the proposed workaround').select(ref)
    for label, value in [('Approved owner / team', 'Team'), ('Approved next action', 'Use temporary layout'),
                         ('Workaround type', 'Temporary display'), ('Safety approval note', 'Human inspection recorded'),
                         ('End condition', 'Delivery verified')]:
        widget(app.text_input, label).set_value(value)
    widget(app.text_area, 'Rationale / condition verification').set_value('Supervisor verified the cited layout.')
    widget(app.button, 'Record human review').click().run()
    assert not app.exception
    decision = store.case(key)['decisions'][-1]
    assert decision['approved_transition'] == 'WORKAROUND_ACTIVE'
    assert decision['corrected_values']['workaround_evidence_ref'] == ref
    assert decision['source_refs'] == [ref]


def test_duplicate_evaluation_and_legitimate_revisions(shipment):
    store, key = shipment
    store.add_observation(key, 'Shipment update', 'No confirmed replacement date.', 'DELAYED')
    service = CandidateService(store)
    refs = service.generate(key, MockProvider())['source_refs']
    candidate = service.latest(key)['candidate_id']
    def evaluate(reason, evidence):
        store.evaluate_candidate(key, candidate, 'CORRECTED', 'Timing uncertain', 'Request date', reason, evidence)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(evaluate, 'Clarify timing', order) for order in (refs, refs[::-1])]
        errors = [result.exception() for result in results]
    assert errors.count(None) == 1
    assert any(isinstance(error, ValueError) and 'already recorded' in str(error) for error in errors)
    evaluate('Additional clarification needed', refs)
    evaluate('Clarify timing', refs)
    after = store.case(key)
    assert [d['rationale_note'] for d in after['decisions']] == [
        'Clarify timing', 'Additional clarification needed', 'Clarify timing']
    assert len([a for a in after['audits'] if a['action'] == 'CANDIDATE_EVALUATED']) == 3
    assert after['workflow_state'] == 'BLOCKED'


def test_provider_failure_preserves_records_and_all_candidate_versions(shipment):
    store, key = shipment
    service = CandidateService(store)
    first = service.generate(key, MockProvider())
    ref = first['source_refs'][0]
    store.evaluate_candidate(key, service.latest(key)['candidate_id'], 'CORRECTED', 'No confirmed ETA',
                             'Ask for an update', 'Uncertainty in the source note', [ref])
    store.review(key, 'BLOCKED', 'APPROVED', 'UNDER_REVIEW', 'Team', 'Verify timing', 'Human review', [ref])
    second = service.generate(key, MockProvider())
    assert first['missing_fields'] == second['missing_fields'] == []
    assert first['candidate_next_step'] == second['candidate_next_step']

    def records():
        with store.connect() as operational, sqlite3.connect(service.path) as candidates:
            return ([operational.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
                     for table in ('tasks', 'blockers', 'sources', 'decisions', 'audits')],
                    candidates.execute('SELECT rowid, * FROM candidates ORDER BY rowid').fetchall())

    before = records()
    assert len(before[1]) == 2
    with pytest.raises(CandidateError):
        service.generate(key, FailureProvider())
    assert records() == before
    store.review(key, 'UNDER_REVIEW', 'APPROVED', 'WAITING_FOR_MATERIAL', 'Team', 'Await verified update',
                 'Supervisor verified delay', [ref])
    assert store.case(key)['workflow_state'] == 'WAITING_FOR_MATERIAL'
