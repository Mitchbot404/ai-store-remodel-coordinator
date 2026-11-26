# Remodel Issue and Material Readiness Coordinator

CEN 4010 Final Project: a bounded issue tracker for coordinating a remodel task when fixtures or materials are unavailable. Based on the Assignment 2 Solution Design Report. Synthetic data only; no employer integrations or confidential data.

Phases 1–5 are implemented: task/blocker intake and source history; authenticated human review and workflow controls; exception flags and S1–S5 synthetic scenarios; candidate-only summaries; and an integrated supervisor review package. Candidate generation defaults to a deterministic mock provider. It does **not** demonstrate validated live-model performance or useful generative reasoning. Phase 6 has not started.

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

To create all five synthetic scenarios in a **new** local database, run:

```powershell
.venv\Scripts\python create_demo.py data/scenarios.sqlite3
$env:REMODEL_DB = 'data/scenarios.sqlite3'
.venv\Scripts\python -m streamlit run app.py
```

The setup prompts for a local demo password. Sign in with ASSOCIATE, SUPPORT, SUPERVISOR, or TECHNICAL and that password. The command refuses to overwrite an existing database. Never reuse a real account password. Database files and sessions must remain local. Automated tests use disposable credentials only in temporary test databases; they are not application defaults.

As an associate, create a synthetic task with a project, area, description, sequence/date, required items, and any available source note. Report a source-backed blocker: READY becomes BLOCKED. Add an observation. Sign out and sign in as a supervisor. Select the task and source, enter an owner, next action, and rationale, and approve UNDER_REVIEW. Review the saved decision and audit history. From UNDER_REVIEW choose waiting, a documented workaround, reassignment, or evidence-backed resolution. Only RESOLVED can advance to COMPLETED. Rejected/unresolved reviews must leave approval fields blank and retain the current state.

## Architecture

Streamlit provides intake, source/history viewing, and human review. `coordinator/models.py` preserves the five report structures and eight-state graph. `coordinator/store.py` enforces authorization, validation, and transactional persistence. `coordinator/auth.py` verifies passwords and expiring sessions. `manage_users.py` is a trusted local account-provisioning command. Review decisions and transitions append audit history; original source records are retained.

`coordinator/exceptions.py` raises deterministic missing/conflicting/timing flags without changing state. `coordinator/candidates.py` supplies the provider interface, exact source-matching validation, and separate candidate storage. A supervisor can generate a clearly labeled CANDIDATE summary or simulate provider failure. Human approval remains required for consequential transitions; candidates cannot change state, ownership, next action, safety decisions, reassignment, workarounds, resolution, or completion.

The optional generic HTTPS provider adapter is isolated and configured through environment variables, with no keys in source. It requires a compatible endpoint and has not been verified against a live model. The current strict validator accepts only the canonical source-linked template and review-only next step, not novel free-form model prose. See the Phase 4 documentation before configuring an external endpoint.

See [Phase 2 controls and limitations](docs/phase2.md), [Phase 1 baseline](docs/phase1.md), and [validation evidence](docs/validation.md). The prototype is localhost-only and synthetic-only. It has no MFA, login throttling, enterprise identity, or per-project access partitioning. Local administrators remain trusted. One blocker per task remains the bounded lifecycle model.

### Integrated supervisor review

Select a task with a blocker as SUPERVISOR. The workbench places original evidence and exception flags beside the CANDIDATE package, with approved owner/action and current state above. Source IDs connect the candidate to the original observations. Generate a candidate or continue manually; simulated provider failure leaves the manual controls available.

Use **Record candidate evaluation only** to approve, correct, reject, or leave candidate information unresolved. Supply a rationale and supporting sources; approval/correction also requires a human-reviewed status and proposed step. These evaluations append an existing ReviewDecision with a candidate snapshot and a separately labeled audit event. They do not change operational state or approved owner/action. Use the separate **Record human review** form for operational decisions under the original permission and evidence gates.

Evidence or operational-context changes mark older candidates stale and prevent their evaluation. Regeneration preserves previous versions. Candidate history and prior human decisions remain accessible in the same view. See [Phase 5 implementation and evaluation limitations](docs/phase5.md).

Repository: [Mitchbot404/ai-store-remodel-coordinator](https://github.com/Mitchbot404/ai-store-remodel-coordinator). See [Phase 4 candidate controls and provider configuration](docs/phase4.md) and [Phase 3 exception rules and demo instructions](docs/phase3.md).
