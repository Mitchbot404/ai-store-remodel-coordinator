# Prototype validation history

## Sporting Goods walkthrough follow-up — November 26, 2026

The owner reported 12 passes at the tested scope and one partial pass across 13 manual checks. The walkthrough was AI-guided and used synthetic records and the deterministic mock. [Observations, root causes, fixes and deferred usability work](sporting-goods-walkthrough.md)

The full local offline suite passed **169 tests in 138.31 seconds**. The four focused walkthrough tests also passed in 6.84 seconds. They exercise observation entry and evidence selection in Streamlit, transactional workaround and duplicate-evaluation gates, and preservation of all operational records and candidate versions across a provider failure followed by manual review. Two existing lifecycle tests now cite an explicit synthetic inspection observation. The source dataset, reference expectations and archived mock outputs remain at revision 2. The original walkthrough was the manual exercise. The post-change form verification used automated Streamlit AppTest.

## Phase 6A offline preparation — November 26, 2026

Complete suite: **154 passed in 134.87 seconds (2:14)**, including all 103 existing tests unchanged and 51 new cases. Focused validation first passed 39 analysis/adapter tests and 12 integration/UI cases. New coverage includes source whitelisting, unsupported content, fabricated IDs, duplicate/misattributed evidence, conflict/UNKNOWN preservation, prompt-injection text, candidate-only output, malformed/refused/incomplete responses, model identity, timeout redaction, size limits, cumulative concurrent budget reservations, disabled-live gates, stale/corrupt stored analysis, unauthorized roles, S1–S5 operational invariance and candidate-to-human snapshots. Tests globally disable the real OpenAI transport; fake responses are identified as offline stubs.

Streamlit AppTest verified the supervisor bounded-analysis display and simulated provider failure with manual review controls still available. These are automated UI checks; no new manual browser verification or actual secret-entry exercise is claimed. The PowerShell key-entry launcher was parsed successfully without executing a secret prompt. No key was read, printed or saved by this work. The local Windows configuration binds Streamlit to localhost; no public app was deployed.

The original canonical mock and bounded mock each processed the ten fixed synthetic evaluation cases: nine validated, S9 rejected at required-source preflight. Reports in `evaluation/results/` retain actual offline run metadata and blank human assessments. References are AI-assisted drafts pending independent owner review. No paid API calls, live-model results, human ratings or human review times are claimed. The initial reserved pytest fixture-name error was corrected before the passing runs. `git diff --check` passed. Phase 6A live evaluation remains pending; Phase 6B/6C and final deliverables have not started.

## Phase 5 validation — November 25, 2026

Complete local suite: **103 passed in 127.89 seconds**; final pre-commit rerun: **103 passed in 126.01 seconds**. This includes all 80 earlier tests and 23 new integration cases: four candidate evaluation outcomes across S1–S5, candidate-to-human traceability, unchanged task/blocker/source records, appended evaluation audit history, stale/invalid candidate rejection, provider failure, version retention, unauthorized role rejection and preservation of previously approved owner/action. Python and dependencies came from the existing local verification environment; GitHub Actions separately tests the repository environment. `git diff --check` and the staged whitespace check passed. Only the eight intended source/test/documentation files were staged; local data, sessions, credentials and caches remained excluded.

Manual browser checks used the isolated ignored synthetic database on localhost port 8505. S1 showed short-delay/target flags and a clearly labeled deterministic CANDIDATE. Rejection was submitted and persisted without an operational transition. A new source observation made the prior candidate stale and removed its evaluation form; regeneration created a new version. Simulated provider failure showed an error while preserving the earlier candidate and separate operational review controls. S4 displayed both MISSING and ARRIVED sources, a conflict flag and a candidate requiring reconciliation. A CORRECTED candidate evaluation was submitted with both conflicting sources retained; the UI marked it previously evaluated and kept the conflict, BLOCKED state and UNASSIGNED approval values. The saved records were checked directly as well as through the browser. No operational approval was submitted. All five scenario blockers remained BLOCKED.

S2, S3, S5 and approval/unresolved evaluation outcomes were covered by automated tests; no manual execution of those flows is claimed. A screenshot of the S4 supervisor view was captured locally. The temporary server was stopped after verification. The interface exposes full task/blocker details in an expander in addition to the main summary.

The mock provider produced canonical templates. Human correction and rejection were deliberate test inputs, not evidence of live-model errors or measured usefulness. Phase 4 adversarial rejection tests continue to pass. No live model, employer data, production deployment, Phase 6 implementation, final report or presentation was introduced. See [Phase 5](phase5.md) for additive design changes, AI development assistance and requirements for meaningful later evaluation. Earlier sections below are historical phase-time observations, including their then-current commit status.

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

## Phase 6A reference revision 2

All 165 offline tests passed in 162.33 seconds, including ten per-case chronology and provenance checks and one report-hash check. Both mock providers accepted nine cases and rejected S9 before generation. The reference reviewer and approval timestamp are blank pending final review. See [revision 2 evidence](evaluation-results.md).
