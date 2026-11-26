# Phase 6A: live integration and evaluation preparation

Status: **OFFLINE IMPLEMENTATION; REFERENCE REVIEW AND LIVE EVALUATION PENDING**. November 26, 2026. Phase 6B/6C, public deployment, final report and presentation have not started.

## Minimal architecture correction

The original provider receives one canonical template and its validator requires exact equality, including the single allowed next step. A live model connected to that interface alone would demonstrate reproduction, not meaningful assistance. The Phase 4 package, mock and exact validator therefore remain intact as the reliable factual baseline.

Phase 6A adds a separately stored, versioned analysis object: ordered evidence groups, clarification codes and review-only recommendations. The model can select relevant observations, change their order and choose their grouping within validated categories. It cannot write new factual values or arbitrary prose. The workbench renders original evidence and fixed labels locally; it calls the ordering **review focus**, never operational priority. Mandatory flags and both conflict sides cannot be omitted. Original sources and human approval controls remain accessible.

This is deliberately constrained generative selection and organization. Whether those choices help a reviewer is an empirical question; neither schema compliance nor a source-ID match proves usefulness or truth. Source notes remain attributed, unverified observations, even when they claim approval or contain instructions. Unsupported output fields, invented IDs, unsuitable groupings and operational recommendation codes fail validation.

## Persistence and authority

Candidate storage gains additive `analysis` and `generation_metadata` columns; old records remain readable. The CandidateReviewPackage keeps its report-defined fields. Stored analysis is revalidated against the authorized case on display and review. Human evaluations snapshot the analysis and provenance alongside the original package; they still cannot change operational state, owner or action. Post-generation case checks, stale rejection, authorization, audit preservation and separate operational review remain enforced.

The OpenAI adapter receives serialized context only, with no Store, database, session or operational tool capability. The provider interface and budget ledger are isolated from operational state. Metadata distinguishes deterministic mock, offline HTTP stub and actual live response, and records model/prompt/schema/settings/latency/token usage. Failed attempts are sanitized and counted against budget without retries. Raw external exceptions are not displayed or persisted. Rejection reasons are currently coarse; full raw-output semantic error analysis is not implemented and must not be claimed.

## Evaluation preparation

The ten fixed synthetic cases, separate draft references, metric definitions and blank manual comparison exercise are in `evaluation/` and the linked documents below. The owner must approve or correct references before any live run. The runner does not send reference answers to providers. Invalid required references are rejected before generation. A real provider/validation failure stops further paid attempts in that run. The total budget persists between runs.

Offline commands:

```powershell
.venv\Scripts\python evaluate_ai.py --mode mock --output data/evaluation/mock.json
.venv\Scripts\python evaluate_ai.py --mode mock_bounded --output data/evaluation/mock-bounded.json
.venv\Scripts\python evaluate_ai.py --mode manual --output data/evaluation/manual.json
.venv\Scripts\python -m pytest -q
```

The manual output is a case packet, not evidence that a person performed the task. `evaluation/results/` contains reviewed synthetic offline evidence only. Future raw evaluation runs should go under ignored `data/` until reviewed for publication.

## Design deviations and limitations

The additive analysis object preserves the report's candidate structure while allowing bounded choices that exact-template validation prevented. No workflow architecture, role or transition redesign was needed. All 103 original tests remain unchanged. The new live adapter and approval/budget gates are necessary for the authorized paid integration.

No live model has been evaluated, and no independent human judgments, usefulness ratings or review times exist yet. The 200-word target is checked for the bounded review-aid labels/questions/recommendations, excluding evidence details; it does not establish whole-screen readability, which needs human review. The canonical package and original evidence remain separately displayed. Timing flags use a fixed generation clock; time passing alone does not invalidate the context hash. Authentication, one-blocker-per-task, trusted local administration and row-ID limitations from Phase 5 remain.

The next step is owner reference review and private local key entry, followed by the approved live experiment and actual human comparison within Phase 6A. Phase 6B readiness cannot be concluded from offline results.

## Material AI development assistance

Codex assisted with code, test cases, synthetic cases, proposed reference expectations, documentation and review. Proposed references are AI-assisted drafts, not independently authored or human-validated ground truth. Review found and corrected a reserved pytest fixture name; further validation results are recorded separately. AI assistance in developing the software is distinct from the application's still-unmeasured live model.

See [provider configuration](provider-configuration.md), [methodology](evaluation-methodology.md), [references for owner review](reference-expectations.md), [manual exercise](manual-review-exercise.md), [results](evaluation-results.md), and [validation](validation.md).
