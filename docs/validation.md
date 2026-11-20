# Phase 1 validation

## Phase 4 validation — November 19, 2026

Complete Phase 1–4 suite: **80 passed in 196.76 seconds (3:16)**. No failures. Includes S1–S5 candidate generation, exact schema/types, source-reference matching, unsupported facts, removed conflicts, false approval labels, unauthorized next steps, UNKNOWN preservation, deterministic mock behavior, stale-context rejection, persistence, supervisor-only access and provider-failure fallback. Original operational permission/state tests remain in the suite. `git diff --check` passed.

Manual Streamlit checks on isolated port 8504: generated S1 delayed-material, S4 conflicting-source and UNKNOWN-material candidates; observed CANDIDATE labels, source references, preserved UNKNOWN/conflict descriptions, and unchanged BLOCKED states/unassigned ownership. Simulated provider failure through the checkbox: safe error displayed while the structured case, previous validated candidate (with original timestamp), and human review form remained available. No approval was submitted. A serialized before/after comparison of every row in tasks, blockers, sources, decisions and audits matched exactly after all four checks. Three validated candidates were stored separately; the failed attempt added no candidate. Temporary server stopped.

Adversarial test outputs included invented arrival timing, bogus sources, omitted conflict evidence, APPROVED status and an instruction to reassign/resolve. All were rejected; none were operational writes. These were deliberately constructed fake-provider outputs, not discovered live-model hallucinations. No live model credentials or endpoint were used. Provider quality, live endpoint compatibility, latency and free-form summarization usefulness remain unverified. No Phase 5 work or Phase 4 commit was performed.

## Phase 3 validation — November 19, 2026

Initial combined suite: **59 passed in 215.81 seconds**. Includes prior phase tests (with explicit verified material status now supplied before final transitions) and S1–S5, missing/unknown context, source preservation, no automatic transitions, conflict gating/reconciliation/reopening, timing boundaries, overdue/open behavior, workaround recovery history, reassignment context, and supervisor authority. A final run adds a direct missing-critical-context gate test and explicit UNKNOWN source-status assertion.

Manual Streamlit verification used an isolated ignored scenario database on localhost port 8503. Signed in as a synthetic supervisor; inspected S1 short-delay and approaching-target flags; selected S4 and verified the conflict, extended-delay and overdue flags, linked source IDs, and unchanged BLOCKED/UNRESOLVED state. Expanded source information and confirmed both MISSING and ARRIVED records remained. Added an explicit UNKNOWN observation through the UI and verified UNKNOWN_SOURCE_STATUS appeared while the conflict and original workflow state persisted. The review form exposes a conflict rationale and corrected-status field. Reconciliation enforcement and lifecycle completion are automated-test checks, not claims of manually exercising every scenario end-to-end.

No AI integration or real operational data was used. Final-suite result follows below.

Final complete run: **60 passed in 267.87 seconds (4:27)**. No failures. `git diff --check` passed. The temporary manual-demo server was stopped. Phase 3 changes are not committed; no Phase 4 work began.

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
