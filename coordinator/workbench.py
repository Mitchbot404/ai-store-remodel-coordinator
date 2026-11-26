"""Supervisor package: evidence, candidate evaluation and explicit operational approval."""
import json
import streamlit as st
from .candidates import CandidateService, FailureProvider, build_request
from .analysis import build_analysis_request, render_analysis
from .exceptions import inspect_case, STATUSES
from .models import ALLOWED_TRANSITIONS


def render_workbench(store, task_id, case):
    task, blocker = case['task'], case['blockers'][0]
    approved = [d for d in case['decisions'] if d.get('scope') != 'CANDIDATE_EVALUATION' and d['decision_type'] in {'APPROVED', 'CORRECTED'}]
    latest = approved[-1] if approved else {}
    st.subheader('Supervisor case review')
    st.write(task['department_area'] + ' — ' + task['description'])
    a, b, c = st.columns(3)
    a.metric('Recorded workflow state', case['workflow_state'])
    b.metric('Human-approved owner', latest.get('approved_owner', 'UNASSIGNED'))
    c.write('**Human-approved next action**')
    c.write(latest.get('approved_next_action', 'UNASSIGNED'))
    st.caption('Candidate evaluation never changes these approved values. Operational approval is a separate action below.')
    left, right = st.columns(2)
    with left:
        st.subheader('Recorded facts and original evidence')
        st.write('**Blocker:**', blocker['observed_condition'])
        st.write('**Recorded material status:**', blocker['material_fixture_status'])
        st.write('**Target / sequence:**', task['target_date_or_sequence'])
        st.write('**Required items:**', ', '.join(task['required_items']) or 'None recorded')
        st.caption('Reporter: ' + blocker['reporter_id'] + ' | Reported: ' + blocker['reported_at'])
        with st.expander('Full task and blocker details'):
            st.json({'task': task, 'blocker': blocker})
        st.write('**Missing, conflicting and timing information**')
        for flag in inspect_case(case):
            st.warning(flag['code'] + ': ' + flag['message'])
            st.caption('Evidence: ' + ', '.join(str(r) for r in flag['source_refs']))
        for source in case['sources']:
            with st.container(border=True):
                st.caption(source['source_id'] + ' | ' + source['source_type'] + ' | ' + source['captured_at'])
                st.text(source['supported_fields_or_note'])
                st.caption('Submitted by ' + source['submitted_by'] + ' | ' + source.get('material_status', 'Unclassified observation'))
        with st.expander('Add source observation'):
            with st.form('workbench-observation-' + task_id):
                note = st.text_area('New source observation')
                st.caption('Record what you observed here. A material status alone describes the shipment.')
                status = st.selectbox('Structured observation', [''] + list(STATUSES))
                if st.form_submit_button('Save observation'):
                    try:
                        store.add_observation(task_id, 'Synthetic supervisor observation', note, status or None)
                        st.rerun()
                    except (ValueError, PermissionError) as error:
                        st.error(str(error))
    with right:
        st.subheader('CANDIDATE — not operational approval')
        service = CandidateService(store)
        failure = st.checkbox('Simulate provider failure (synthetic test only)')
        failure_key = 'candidate-error-' + task_id
        if st.button('Generate CANDIDATE summary'):
            try:
                service.generate(task_id, FailureProvider() if failure else None)
                st.session_state.pop(failure_key, None)
            except Exception:
                st.session_state[failure_key] = 'Generation failed or was rejected. Manual operational review remains available.'
        if failure_key in st.session_state:
            st.error(st.session_state[failure_key])
        candidate = None
        try:
            candidate = service.latest(task_id)
            if candidate is None:
                st.info('No candidate available. Review the original evidence manually or generate a candidate.')
            elif candidate.get('stale'):
                st.warning('Stale candidate: evidence or operational context changed. Regenerate before evaluating.')
            else:
                package = candidate['package']; identifier = candidate['candidate_id']
                provider = candidate['provider']
                label = 'Deterministic mock — no live-model performance demonstrated' if provider in {'mock', 'MockProvider', 'mock_bounded', 'MockAnalysisProvider'} else 'External provider: ' + provider + ' — quality not validated'
                st.caption(label)
                if 'analysis' in candidate:
                    meta = candidate['generation_metadata']
                    st.caption('Analysis provenance: ' + meta.get('invocation_mode', 'unverified') +
                               ' | Model: ' + meta.get('model', 'none'))
                    st.write('**CANDIDATE review focus — not work priority**')
                    rendered = render_analysis(candidate['analysis'], build_analysis_request(
                        build_request(case, package['generated_at'])))
                    for group in rendered['groups']:
                        with st.expander(group['label']):
                            for item in group['items']:
                                st.text(item['text'])
                                if item.get('material_status'):
                                    st.caption('Recorded source status: ' + item['material_status'])
                                st.caption('Sources: ' + ', '.join(item['source_refs']))
                    for question in rendered['questions']:
                        st.write('• ' + question)
                    for recommendation in rendered['recommendations']:
                        st.write('• ' + recommendation)
                    st.caption('Evidence selection and ordering are candidate judgments. Displayed source text is a recorded claim, not independent verification.')
                st.caption('Candidate ID: ' + identifier + ' | Generated: ' + package['generated_at'])
                if any(d.get('candidate_id') == identifier for d in case['decisions']):
                    st.info('Previously evaluated candidate. Earlier evaluations remain in the history below.')
                st.write('**Candidate recorded-status summary**')
                st.json(json.loads(package['supported_status']))
                st.write('**Proposed next step for review:**', package['candidate_next_step'])
                st.write('**Missing / UNKNOWN (structured fields):**', package['missing_fields'] or 'None flagged')
                st.caption('Original source notes may describe additional uncertainty.')
                st.write('**Conflicts:**', package['conflicts'] or 'None flagged')
                st.info(package['uncertainty_note'])
                st.caption('Source IDs match the original evidence at left: ' + ', '.join(package['source_refs']))
                with st.form('candidate-evaluation-' + task_id + '-' + identifier):
                    st.write('**Evaluate candidate information only**')
                    outcome = st.selectbox('Candidate evaluation outcome', ['UNRESOLVED','APPROVED','CORRECTED','REJECTED'])
                    human_status = st.text_area('Human-reviewed status')
                    human_next = st.text_area('Human-reviewed proposed next step (not an operational approval)')
                    rationale = st.text_area('Evaluation rationale / corrections / usefulness notes')
                    refs = st.multiselect('Evaluation supporting sources', package['source_refs'], format_func=lambda ref: ref + ' — ' + next(s['supported_fields_or_note'] for s in case['sources'] if s['source_id'] == ref))
                    if st.form_submit_button('Record candidate evaluation only'):
                        try:
                            store.evaluate_candidate(task_id, identifier, outcome, human_status, human_next, rationale, refs)
                            st.rerun()
                        except (ValueError, PermissionError) as error:
                            st.error(str(error))
            with st.expander('Candidate version history'):
                st.dataframe(service.history(task_id), hide_index=True)
        except Exception:
            st.warning('Candidate unavailable or invalid. Continue with manual operational review.')
    st.divider()
    st.subheader('Separate operational decision — supervisor authority')
    st.caption('Evaluating a candidate does not submit this form. State transitions and evidence gates remain enforced here.')
    operational_review(store, task_id, case)
    with st.expander('Previous human decisions and candidate evaluations'):
        for decision in reversed(case['decisions']):
            st.write('**' + decision.get('scope', 'OPERATIONAL_REVIEW') + ' — ' + decision['decision_type'] + '**')
            st.json(decision)
    with st.expander('Audit history'):
        st.json(case['audits'])


def operational_review(store, task_id, case):
    with st.form('review-' + task_id):
        st.subheader('Supervisor review')
        decision = st.selectbox('Decision', ['APPROVED', 'CORRECTED', 'REJECTED', 'UNRESOLVED'])
        target = st.selectbox('Approved transition', [''] + sorted(ALLOWED_TRANSITIONS[case['workflow_state']]))
        owner = st.text_input('Approved owner / team')
        action = st.text_input('Approved next action')
        rationale = st.text_area('Rationale / condition verification')
        refs = st.multiselect('Supporting sources', [r['source_id'] for r in case['sources']],
                              format_func=lambda ref: next(r['supported_fields_or_note'] for r in case['sources'] if r['source_id'] == ref))
        material_correction = st.text_input('Corrected material status (optional)')
        conflict_note = st.text_area('Conflict reconciliation rationale (select all conflicting sources and correct material status)')
        st.caption('For a workaround, record its type, human safety approval, and end condition. For reassignment, record destination, return condition, and why local work is exhausted.')
        notes = {s['source_id']: s['supported_fields_or_note'] for s in case['sources']
                 if s.get('authorization_flag') == 'SYNTHETIC'}
        workaround_ref = st.selectbox('Observation I verified supports the proposed workaround',
                                      list(notes), index=None,
                                      format_func=lambda ref: notes[ref] + ' — ' + ref,
                                      help='Required when activating a workaround. This source will be cited in your decision. If the inspection details are missing, record an observation first.')
        details = {field: st.text_input(field.replace('_', ' ').capitalize()) for field in
                   ['workaround_type', 'safety_approval_note', 'end_condition', 'destination_context', 'return_condition', 'local_work_exhausted']}
        if st.form_submit_button('Record human review'):
            try:
                corrections = {k: v for k, v in details.items() if v.strip()}
                if target == 'WORKAROUND_ACTIVE' and workaround_ref:
                    corrections['workaround_evidence_ref'] = workaround_ref
                    refs = list(dict.fromkeys([*refs, workaround_ref]))
                if conflict_note.strip():
                    corrections['conflict_resolution_note'] = conflict_note
                if material_correction.strip():
                    corrections['material_fixture_status'] = material_correction
                store.review(task_id, case['workflow_state'], decision, target, owner, action, rationale, refs, corrections)
                st.rerun()
            except (ValueError, PermissionError) as error:
                st.error(str(error))
