# Phase 4 bounded candidate summarization

The Assignment 2 CandidateReviewPackage structure is implemented in coordinator/candidates.py. No AI-generated action can become an operational approval. Phase 5 has not begun.

## Workflow and authority

Only a signed-in supervisor can generate/view candidates. The service reads the authorized task, blocker, synthetic sources, exception flags and latest approved owner/next action. Provider code receives a detached JSON-compatible snapshot, never a Store object, credentials, session records, other tasks, or write tools. Source text is treated as untrusted data, not instructions.

The provider returns task_id, blocker_id, supported_status, source_refs, missing_fields, conflicts, uncertainty_note, candidate_next_step, generated_at and review_state=CANDIDATE. Validation precedes persistence/display. Candidate storage is a separate SQLite file beside the operational database, with suffix `.candidates.sqlite3`. No operational audit event, owner/action, ReviewDecision, task, or blocker is written. A context hash detects later case changes and suppresses stale output. Stored packages are revalidated before display. Generation failure displays a safe error and preserves access to the manual workflow. A prior valid candidate may remain visible with its original timestamp after a failed attempt.

## Provider interface

Provider.generate(request) accepts instructions, whitelisted context, a candidate template, and allowed review-only next steps, and returns a dictionary. MockProvider is deterministic for identical input and is the default. The UI explicitly labels it as a mock, not a live model. FailureProvider is selectable only as a synthetic failure test.

Optional configuration: CANDIDATE_PROVIDER=http, CANDIDATE_ENDPOINT=https://your-authorized-adapter, CANDIDATE_API_KEY, CANDIDATE_MODEL. JsonHttpProvider POSTs the request plus model to an endpoint that implements this contract, uses a 20-second timeout and limits the response to 64 KiB. It is a generic adapter interface, not a tested vendor-specific integration. Configure only an endpoint authorized to receive synthetic context. No live endpoint or credential was used or validated. Environment files and SQLite artifacts are ignored; no secrets are supplied or committed.

## Validation choice and deviation

An unrestricted prose validator cannot reliably prove factual support. This phase therefore uses constrained extractive output: all factual fields must exactly match the canonical source-linked template, including UNKNOWN, conflicts, IDs and timestamp. The candidate next step is a prescribed request for human review/clarification, never an operational instruction. Extra/missing keys, wrong types, invented sources, altered facts, omitted conflicts, changed review labels and unauthorized next steps are rejected. The timestamp is server-supplied. missing_fields contains human-readable missing/unknown flag descriptions; supported_status is a JSON-formatted string of attributed recorded values and observations.

This is intentionally stricter than free-form candidate summarization. A future live model cannot provide novel wording under this contract. It validates the isolation, schema, review controls and fallback path, but does not demonstrate useful generative-model reasoning or superiority over the non-AI tracker. No unsupported output is silently repaired or presented as approved. The prompt also explicitly prohibits safety determinations, authoritative-source selection, priority changes, reassignment, workarounds, resolution and completion.

## Limits and Phase 5 readiness

The existing one-blocker scope, structured conflict detection and local authentication limitations remain. Local code/filesystem administrators are trusted; Python plugins are not an operating-system security boundary. Database permissions should protect both files. Candidate generation is synchronous, and concurrent operational changes cause rejection after generation. No candidate approval button or mapping from candidate to operational decision is added; existing human review remains independent.

Ready for review as a candidate-only integration foundation. Phase 5 should present candidates beside source evidence and approved decisions, retain explicit reviewer corrections, and test that stale/failed candidates never become approvals. Live provider quality, response latency and usefulness still require evaluation before claiming a production AI capability.
