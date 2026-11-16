import os
from pathlib import Path
import streamlit as st
from coordinator.store import Store

st.set_page_config(page_title='Remodel Coordinator', layout='centered')
st.title('Remodel Issue and Material Readiness Coordinator')
st.warning('Phase 1 • Local synthetic-data prototype only. No authentication or operational approvals.')
path = Path(os.environ.get('REMODEL_DB', str(Path(__file__).parent / 'data' / 'prototype.sqlite3')))
path.parent.mkdir(parents=True, exist_ok=True)
store = Store(path)

with st.expander('Create remodel task', expanded=True):
    with st.form('task'):
        project = st.text_input('Synthetic project ID')
        area = st.text_input('Department / area')
        description = st.text_area('Task description')
        target = st.text_input('Target date or sequence marker')
        items = st.text_area('Required items (one per line; blank means none)')
        reporter = st.text_input('Synthetic reporter ID')
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
    names = {t['task_id']: f"{t['department_area']} — {t['description']} ({t['task_id'][:8]})" for t in tasks}
    task_id = st.selectbox('View task', list(names), format_func=names.get)
    case = store.case(task_id)
    st.subheader(f"Current state: {case['workflow_state']}")
    st.json(case['task'])
    if not case['blockers']:
        with st.form('blocker'):
            kind = st.text_input('Blocker type')
            condition = st.text_area('Observed condition')
            material = st.text_input('Material / fixture status', value='UNKNOWN')
            actor = st.text_input('Blocker reporter ID')
            source_type = st.text_input('Source type', value='Synthetic observation')
            note = st.text_area('Supporting source note')
            if st.form_submit_button('Report blocker'):
                try:
                    store.report_blocker(task_id, kind, condition, actor, source_type, note, material)
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    else:
        st.write('Owner: UNASSIGNED · Next action: UNASSIGNED · Review: UNRESOLVED')
        st.json(case['blockers'])
    with st.expander('Preserved source information'):
        st.json(case['sources'])
    with st.expander('Audit history'):
        st.json(case['audits'])
