# Remodel Issue and Material Readiness Coordinator

CEN 4010 Final Project, Phase 1: a local non-AI issue tracker based on the Assignment 2 Solution Design Report, sections 7.1–7.4 and implementation step 1. Synthetic data only. No employer systems, integrations, policies, or confidential records.

## Setup and run

Use Python 3.11 or later. From this folder:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m streamlit run app.py
```

Open http://127.0.0.1:8501. The app binds to localhost. SQLite records persist in `data/prototype.sqlite3`, excluded from Git. Set `REMODEL_DB` to use a different database path.

```powershell
.venv\Scripts\python -m pytest -q
```

## Demonstration

Create project `SYN-01`, area `Demo area`, description `Install sample shelf`, sequence `Step 1`, item `Sample shelf`, reporter `demo-associate`, and source `Synthetic plan calls for one shelf`. Observe READY. Report a material-delay blocker with a synthetic delivery note. Observe BLOCKED, UNRESOLVED review, unassigned ownership, preserved sources, and the READY-to-BLOCKED audit event. Restart the app to confirm persistence.

## Architecture and authority

`app.py` provides intake and viewing. `coordinator/models.py` defines the five requested structures and the exact eight-state / eleven-edge graph in report section 7.3. `coordinator/store.py` validates intake and atomically stores records, evidence, and audit history using SQLite. No AI service or external network call is included.

Task creation initializes READY; a source-backed blocker changes the displayed state to BLOCKED. The state is derived from the linked blocker to avoid two conflicting status values. All other state-changing operations fail closed. ReviewDecision is defined but is not created or applied in Phase 1. Names entered in reporter fields are attribution labels, not authenticated identities.

## Scope and limitations

This is a local, single-user synthetic prototype, not a deployed operational system. Authentication and roles (NFR-04), supervisor decisions, source-update intake, conflict detection, timing alerts, and subsequent transitions remain unimplemented. No approval controls are exposed. Do not deploy before access controls exist. Database access itself is not protected against a local administrator.

One blocker per task is enforced for this slice; reopening and multiple historical blockers require later lifecycle work. Source captured_at records intake time. Material status may explicitly be UNKNOWN. Required items may be empty to mean no material is required. Sources are append-only through the application; there is no edit/delete API.

See `docs/phase1.md` for traceability and deviations. No remote repository has been created or published; add its URL here after publication.
