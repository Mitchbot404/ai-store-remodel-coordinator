# Phase 3 exceptions and representative scenarios

Baseline: Assignment 2 FR-03/05, sections 7.3 and 7.6, and S1–S5. No AI, new architecture, safety automation, staffing automation, or resolution automation.

## Use

The authenticated case view displays missing/unknown context, conflicting observations, and timing flags with source IDs and affected fields. Sources remain visible in the existing evidence panel. Add a source note and optionally select a structured material observation. Blank means unclassified free text; UNKNOWN is an explicit observation, never an inferred fact.

An ARRIVED observation conflicts with MISSING or DELAYED observations attached to the same bounded blocker. Both remain stored. Supervisors reconcile by selecting all conflicting sources, supplying a corrected material status, and recording a conflict reconciliation rationale. The review and audit are saved by the existing transaction. A new contradictory source reopens the flag. Historical conflict evidence remains visible as CONFLICT_REVIEWED after reconciliation.

Missing critical context or an unresolved conflict prevents consequential transitions. UNKNOWN material status additionally prevents resolution/completion. The UI directs reviewers to the existing UNDER_REVIEW path; the flag itself does not mutate state. This preserves both the state graph and the user's prohibition on automatic exception transitions. A reviewer can route BLOCKED/WAITING/REASSIGNED cases to UNDER_REVIEW through the existing permitted path. A workaround follows its existing WAITING_FOR_MATERIAL path first. No new transition edge is added.

## Timing semantics

Checks run when viewing a case or submitting review, not as a background scheduler. Blocker age is a proxy for delay because the baseline has no scheduled shipment-arrival field. Short: 1 to less than 3 hours; extended: 3 to less than 24 hours; multi-day/long-running: at least 24 hours. Approaching target: within 24 hours; overdue: strictly past target. These are prototype thresholds, not employer rules. RESOLVED/COMPLETED/returned-READY cases receive no open-blocker timing alerts. ISO timestamps are supported; date-only targets mean midnight UTC. Sequence markers receive a manual sequence-impact review flag, never a fabricated deadline.

## Synthetic demonstrations

Create an isolated new database:

```powershell
.venv\Scripts\python create_demo.py data/scenarios.sqlite3
$env:REMODEL_DB = 'data/scenarios.sqlite3'
.venv\Scripts\python -m streamlit run app.py
```

The command prompts for a demo password and creates ASSOCIATE, SUPPORT, SUPERVISOR, TECHNICAL accounts. Use only in a local synthetic demo. Existing paths are refused. S1 models a 90-minute delay with an approaching target; S2 a three-day delay; S3 a damaged fixture; S4 contradictory missing/arrived sources; S5 exhausted local work. Cases begin BLOCKED and unapproved. A human must approve ownership and actions. S2 workaround and recovery and S5 reassignment/return details are demonstrated through the existing review form and exercised in tests. Synthetic backdated reporting is fixture-only and does not add a timestamp-editing API.

## Changes and limits

Source records gain optional material_status metadata; existing dataclass fields and historical notes remain unchanged. Review corrected_values gains conflict_resolution_note. No schema migration or destructive rewrite is needed. Phase 2 tests now provide verified material status for final transitions; this is a necessary stronger gate, not removal of prior permission coverage.

Conflict detection is intentionally deterministic and conservative: it covers structured arrival versus absence for one blocker, not arbitrary natural-language contradictions or multiple separately identified materials. Historical arrival after a delay still requires a reviewer to reconcile the evidence. Free text is not automatically interpreted. Unknown hard intake fields can be detected in legacy records, but a general task/source correction editor is not included; incomplete records remain blocked from consequential decisions. Source authorization is the existing synthetic-only intake boundary, not an external evidence-verification system. Phase 2 authentication/security limitations still apply.

## Phase 4 readiness

The structured records, source references, exception flags, and human review gates provide a bounded baseline for candidate-only summarization after user review. Phase 4 must keep AI read-only against operational state, validate the CandidateReviewPackage schema, preserve UNKNOWN/conflicts, and test unsupported-claim rejection. No model, credentials, prompt, or service has been added here.
