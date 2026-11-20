import os
from pathlib import Path
import streamlit as st
from coordinator.store import Store
from coordinator.auth import Auth, Role
from coordinator.models import ALLOWED_TRANSITIONS
from coordinator.exceptions import inspect_case, STATUSES
from coordinator.candidates import CandidateService, CandidateError, FailureProvider

st.set_page_config(page_title='Remodel Coordinator', layout='centered')
st.title('Remodel Issue and Material Readiness Coordinator')
st.caption('Phase 4 - Synthetic prototype - Candidate summaries require human review')
path = Path(os.environ.get('REMODEL_DB', str(Path(__file__).parent / 'data' / 'prototype.sqlite3')))
path.parent.mkdir(parents=True, exist_ok=True)
auth = Auth(path)
try:
    actor, role = auth.identity(st.session_state.get('token'))
except PermissionError:
    with st.form('login'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        if st.form_submit_button('Sign in'):
            try:
                st.session_state.token = auth.login(username, password)
                st.rerun()
            except PermissionError as error:
                st.error(str(error))
    st.stop()
st.sidebar.write(f'{actor} — {role.value}')
if st.sidebar.button('Sign out'):
    auth.logout(st.session_state.token)
    st.session_state.clear()
    st.rerun()
store = Store(path, st.session_state.token)
if role == Role.TECHNICAL:
    st.info('Technical role: maintain configuration and accounts through local administration. Operational records and approvals are unavailable.')
    st.stop()


if role in (Role.ASSOCIATE, Role.SUPERVISOR):
    with st.expander('Create remodel task', expanded=True):
        with st.form('task'):
            project = st.text_input('Synthetic project ID')
            area = st.text_input('Department / area')
            description = st.text_area('Task description')
            target = st.text_input('Target date or sequence marker')
            items = st.text_area('Required items (one per line; blank means none)')
            reporter = actor
            source = st.text_area('Source note (required when source material exists)')
            has_source = st.checkbox('Source material exists')
            if st.form_submit_button('Create task'):
                try:
                    if has_source and not source.strip():
                        raise ValueError('Record the available source information.')
                    store.create_task(project, area, description, target, [x for x in items.splitlines() if x.strip()], reporter, source_note=source)
                    st.success('Task created.')
                except ValueError as error:
                    st.error(str(error))

tasks = store.tasks()
if not tasks:
    st.info('Create a synthetic task to begin.')
else:
    names = {t["task_id"]: f"{t['department_area']} - {t['description']} ({t['task_id'][:8]})" for t in tasks}
    task_id = st.selectbox('View task', list(names), format_func=names.get)
    case = store.case(task_id)
    st.subheader(f"Current state: {case['workflow_state']}")
    st.json(case['task'])
    st.subheader('Exception and review flags')
    flags = inspect_case(case)
    if not flags:
        st.info('No detected exceptions. This is not confirmation of safety or readiness.')
    for flag in flags:
        st.warning(flag['code'] + ': ' + flag['message'])
        st.caption('Source references: ' + ', '.join(str(r) for r in flag['source_refs']) + ' | Fields: ' + ', '.join(flag['fields']))
    if any(f['blocking'] for f in flags):
        st.error('Review required: use the permitted UNDER_REVIEW path. Consequential changes are blocked until context is complete and conflicts are reconciled.')
    if not case['blockers'] and role in (Role.ASSOCIATE, Role.SUPERVISOR):
        with st.form('blocker'):
            kind = st.text_input('Blocker type')
            condition = st.text_area('Observed condition')
            material = st.text_input('Material / fixture status', value='UNKNOWN')
            st.caption(f'Reporter: {actor}')
            source_type = st.text_input('Source type', value='Synthetic observation')
            note = st.text_area('Supporting source note')
            if st.form_submit_button('Report blocker'):
                try:
                    store.report_blocker(task_id, kind, condition, actor, source_type, note, material)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    else:
        approved = [d for d in case['decisions'] if d['decision_type'] in ('APPROVED', 'CORRECTED')]
        latest = approved[-1] if approved else {}
        st.write('Owner:', latest.get('approved_owner', 'UNASSIGNED'), 'Next action:', latest.get('approved_next_action', 'UNASSIGNED'))
        st.json(case['blockers'])
    with st.expander('Preserved source information'):
        st.json(case['sources'])
    with st.expander('Audit history'):
        st.json(case['audits'])

    with st.form('observation'):
        update_type = st.text_input('Update source type', value='Synthetic material update')
        update_note = st.text_area('New source observation')
        update_status = st.selectbox('Structured material observation (optional)', [''] + list(STATUSES))
        if st.form_submit_button('Add observation'):
            try:
                store.add_observation(task_id, update_type, update_note, update_status or None)
                st.rerun()
            except (ValueError, PermissionError) as error:
                st.error(str(error))
    if role == Role.SUPERVISOR and case['blockers']:
        st.subheader('CANDIDATE summary - not an approval')
        st.caption('Default: deterministic mock, not a live AI model. Human review below remains authoritative.')
        service = CandidateService(store)
        simulate_failure = st.checkbox('Simulate provider failure (synthetic test only)')
        if st.button('Generate CANDIDATE summary'):
            try:
                service.generate(task_id, FailureProvider() if simulate_failure else None)
                st.success('Validated candidate saved separately. Operational records unchanged.')
            except Exception:
                st.error('Candidate generation failed or was rejected. Continue with the structured case and human review.')
        try:
            candidate = service.latest(task_id)
            if candidate and candidate.get('stale'):
                st.info('Previous candidate is stale. Generate again using the current evidence.')
            elif candidate:
                st.caption('Provider: ' + candidate['provider'])
                st.json(candidate['package'])
        except Exception:
            st.warning('Saved candidate is unavailable or invalid. Use the structured case and human review.')
    if role == Role.SUPERVISOR and case['blockers']:
        with st.form('review'):
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
            details = {field: st.text_input(field.replace('_', ' ').capitalize()) for field in
                       ['workaround_type', 'safety_approval_note', 'end_condition', 'destination_context', 'return_condition', 'local_work_exhausted']}
            if st.form_submit_button('Record human review'):
                try:
                    corrections = {k: v for k, v in details.items() if v.strip()}
                    if conflict_note.strip():
                        corrections['conflict_resolution_note'] = conflict_note
                    if material_correction.strip():
                        corrections['material_fixture_status'] = material_correction
                    store.review(task_id, case['workflow_state'], decision, target, owner, action, rationale, refs, corrections)
                    st.rerun()
                except (ValueError, PermissionError) as error:
                    st.error(str(error))
    with st.expander('Human review decisions'):
        st.json(case['decisions'])
