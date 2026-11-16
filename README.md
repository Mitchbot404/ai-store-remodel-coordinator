# Remodel Issue and Material Readiness Coordinator

CEN 4010 Final Project, Phase 2: authenticated human review of synthetic remodel blockers. Based on the Assignment 2 Solution Design Report. No AI, employer integrations, or confidential data.

## Setup

Use Python 3.11 or later, from this directory:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python manage_users.py associate "Associate"
.venv\Scripts\python manage_users.py supervisor "Supervisor/Manager"
.venv\Scripts\python -m streamlit run app.py
```

Account creation prompts for a password; there are no default credentials. Additional roles are `Stocking/Support` and `Technical/System Owner`. Open http://127.0.0.1:8501 and sign in. Data stays in the ignored `data/prototype.sqlite3`. For a separate database, set `REMODEL_DB` and pass the same path to account provisioning with `--database`.

```powershell
.venv\Scripts\python -m pytest -q
```

## Demonstration

As an associate, create a synthetic task with a project, area, description, sequence/date, required items, and any available source note. Report a source-backed blocker: READY becomes BLOCKED. Add an observation. Sign out and sign in as a supervisor. Select the task and source, enter an owner, next action, and rationale, and approve UNDER_REVIEW. Review the saved decision and audit history. From UNDER_REVIEW choose waiting, a documented workaround, reassignment, or evidence-backed resolution. Only RESOLVED can advance to COMPLETED. Rejected/unresolved reviews must leave approval fields blank and retain the current state.

## Architecture

Streamlit provides intake, source/history viewing, and human review. `coordinator/models.py` preserves the five report structures and eight-state graph. `coordinator/store.py` enforces authorization, validation, and transactional persistence. `coordinator/auth.py` verifies passwords and expiring sessions. `manage_users.py` is a trusted local account-provisioning command. Review decisions and transitions append audit history; original source records are retained.

See [Phase 2 controls and limitations](docs/phase2.md), [Phase 1 baseline](docs/phase1.md), and [validation evidence](docs/validation.md). The prototype is localhost-only and synthetic-only. It has no MFA, login throttling, enterprise identity, or per-project access partitioning. Local administrators remain trusted. One blocker per task remains the bounded lifecycle model.

No remote repository has been published. Add the repository URL after publication. Phase 3 has not begun.
