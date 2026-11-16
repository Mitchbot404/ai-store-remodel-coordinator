# Phase 1 validation

## Phase 2 validation — November 16, 2026

The initial combined run passed 38 tests in 114.04 seconds. This included the adapted Phase 1 intake and Streamlit tests, assigned-role allow/deny checks, missing approval details, state/rationale/source validation, persisted decisions, source/audit preservation, logout revocation, and lifecycle branches through waiting, workaround, reassignment, resolution, completion, and return to READY.

Manual browser verification used the separate ignored `data/manual-phase2.sqlite3` and port 8502. Observed the signed-out login-only screen, signed in as a synthetic supervisor, submitted a source-linked BLOCKED-to-UNDER_REVIEW decision, verified the resulting state and approved owner/next action, expanded the persisted decision, and signed out. The signed-out screen again hid all operational records. The temporary test server was stopped afterward. Manual inspection identified and corrected a stale Phase 1 banner and owner display. No real operational approval was performed.

Additional all-invalid-edge coverage and the final full-suite result are recorded below. Automated UI tests cover associate intake; the manual browser check covers supervisor review. Other roles are verified at the service layer. No claim is made of exhaustive manual UI testing, production security validation, or fresh dependency installation.

Final combined run: **39 passed in 117.19 seconds** using Python 3.14, Streamlit 1.66.1, and pytest 9.2.0 from the existing local environment. Every disallowed directed pair between distinct workflow states is attempted and rejected without mutation. `git diff --check` passed. No Phase 2 commit has been created.

---

Validation date: November 15, 2026.

- Python 3.14, Streamlit 1.66.1, pytest 9.2.0 from the existing local PawPalPlus environment were used for verification; no files in that project were modified.
- `python -m pytest -q remodel-coordinator/tests`: **18 passed in 1.73 seconds**.
- Tests cover required task fields, field persistence across store reopening, source links, explicit unknown material status, atomic duplicate rejection, missing-source rejection, nonexistent task rejection, all eight denied manual state requests, the state graph, and the Streamlit create/report flow.
- Streamlit started successfully on localhost port 8501. UI behavior was executed through Streamlit AppTest; no manual browser visual inspection is claimed.
- Restricted-environment test/server launches stalled. The same tests succeeded outside that environment. An initial test collection error was fixed by adding project-root configuration in pytest.ini.
- Fresh-environment dependency installation and GitHub Actions execution have not been verified. Requirements are bounded compatibility ranges rather than a fully locked dependency set.
- Authentication, supervisor approvals, full lifecycle transitions, timing performance targets, and AI quality are not claimed or tested as implemented features.
