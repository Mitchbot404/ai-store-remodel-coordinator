# Phase 5: Supervisor Review Package and Full Integration

Implemented November 25, 2026 (local time). Phase 6 has not started. The Assignment 2 Solution Design Report remains the design baseline; all scenario records are synthetic.

## Workflow and authority

The supervisor workbench combines task/blocker details, recorded state, approved owner/action, original evidence, missing/conflict/timing flags, the current candidate, human controls, candidate versions, review decisions and audits. Original sources remain visible beside candidate output. Mock output is explicitly labeled deterministic and CANDIDATE; external-provider output is identified separately without claiming validated quality.

Candidate evaluation supports APPROVED, CORRECTED, REJECTED and UNRESOLVED. Approval here means acceptance of candidate information only. Each evaluation requires a rationale and case source references; approval/correction additionally requires human-reviewed status and proposed next step. The operational approval form remains separate and retains all prior state-transition, evidence, workaround, reassignment, resolution and completion gates. Technical/System Owner has no operational review authority.

The existing ReviewDecision JSON record is extended with `scope=CANDIDATE_EVALUATION`, candidate ID, candidate snapshot, provider and supporting sources. Its corrected_values retain the human-reviewed status and proposed step. The record preserves the currently approved operational owner/action, leaves approved_transition empty, and records reviewer, outcome, rationale and timestamp. `CANDIDATE_EVALUATED` audit events have identical prior/new states. Evaluations cannot overwrite operational records or resolve conflicting evidence. Operational readers exclude evaluation-scoped decisions when determining approved owner/action.

## Lifecycle and persistence

Candidate packages stay in the separate candidate SQLite file. Existing row IDs identify versions; new generations also retain a context_snapshot. The context snapshot column is added without deleting or replacing Phase 4 records. Old records have no retrospective snapshot. Candidate packages remain CANDIDATE even after a human evaluates them; evaluation history is separate from their content.

No candidate, current candidate, previously evaluated candidate, stale candidate and generation failure have explicit UI states. Source and operational-context changes invalidate the current version. Evaluation-only events do not invalidate it. Evaluation takes an operational database write lock, reloads the case, checks the stored context hash and reruns the Phase 4 schema/evidence validator before appending the human decision. Stale, invalid, nonexistent or foreign-case candidate IDs cannot be used. Regeneration appends; it does not replace history. Failure leaves manual review available and retains earlier candidate versions.

## Design adjustments

No architecture or state-machine redesign was needed. The supervisor presentation is extracted into `coordinator/workbench.py` for cohesion. Additive metadata on existing ReviewDecision JSON records avoids a duplicate operational decision system. A separate context snapshot is retained with new candidates to support later evaluation against the evidence actually supplied. These additions implement Phase 5 traceability requirements without adding operational powers to the provider.

## Evidence and limitations

See [validation](validation.md) for automated and manual results. Tests cover all four outcomes across S1–S5 and retention of source/candidate/audit history. The manual checks cover S1, S4, correction, rejection, stale/regenerated candidates and provider failure. Other scenario checks are automated, not claimed as manually exercised.

Retained evidence includes the original candidate status/step, original sources and conflict records, new-generation context snapshot, provider identifier, reviewer status/step, outcome, corrections/rationale, source selections, timestamps and unchanged operational approvals. Supervisors can record usefulness notes in the rationale, but there is no validated usefulness score or controlled manual-review comparison yet.

The strict canonical-template validator checks exact structured evidence and permitted review-only steps. It rejects novel free-form prose, including potentially accurate paraphrases. Passing it demonstrates contract compliance, not generative reasoning, semantic factuality or practical usefulness. No live-model performance is claimed. Timing flags are a generation-time snapshot; elapsed time alone does not change the context hash. Current flags are recomputed in the workbench; regenerate to refresh the candidate's timing context.

Prototype limitations remain: local administrator trust, local account/session authentication without enterprise controls, one blocker per task, no project access partitioning, no production concurrency/security evaluation, and no public deployment. Candidate IDs are local SQLite row IDs; manual database rewriting/deletion/compaction is outside the supported workflow. History lists version metadata; reviewed versions also retain full snapshots in decision history. Raw unreviewed historical packages remain stored in the candidate database.

## Requirements for Phase 6, pending review

Meaningful live-model evaluation requires an explicitly configured compatible provider, recorded model/prompt/validator versions and generation settings, a synthetic evaluation set with independent human reference judgments, and predefined measures for factuality, traceability, UNKNOWN/conflict preservation, correction/rejection rates and usefulness. Include adversarial evidence, failures, stale context and representative S1–S5 cases. Compare manual review with candidate-assisted review using a consistent rubric and measured review effort. Preserve raw model responses safely for error analysis if that capability is approved. Any extension beyond canonical-template validation needs separate adversarial validation and must retain the operational write boundary. Mock results cannot establish live-model quality.

## Material AI assistance

OpenAI Codex assisted with implementation, tests, documentation, browser-based prototype verification and Git preparation for this phase. The developer remains responsible for reviewing the changes and reporting this assistance under course requirements. This development assistance is distinct from the application's deterministic mock provider. No final report or presentation was started.
