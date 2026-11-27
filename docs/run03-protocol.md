# Run 03 prompt intervention and proposed protocol amendment

**Run 03 is awaiting owner approval.** Its prompt is `review-focus-v2`. Runs 01 and 02 used `review-focus-v1`. The reference set is independently versioned as `phase6a-reference-v2`. No new live observations have been collected for this intervention.

## Diagnosis

Run 02 returned a schema-valid S1 response. `source:S1-SRC-1` was present in the catalog, and both `SOURCE_UPDATES` and `MATERIAL_READINESS` appeared in its eligible focuses. The validator tracks IDs in one set across *all* groups. The second placement violated that rule. The recorded rejection category covers both fabricated and repeated references; replay establishes repetition in this instance. The missing instruction is a confirmed contract mismatch. It cannot establish how the model would have responded to different wording. [Original returned choices](../evaluation/results/live-run-02.json)

| Output rule | What v1 communicated | What v2 tells the model |
| --- | --- | --- |
| Evidence membership, eligibility and uniqueness | Select relevant IDs using each item's eligible focuses. No global uniqueness rule. | Use catalog IDs only. Place an ID at most once across the entire response, including within a group. Choose its single most relevant eligible focus. |
| Groups and fields | Follow the schema. Bounds, nonempty arrays and exact keys were supplied in JSON. Focus uniqueness was implicit. | Return exactly the four named fields with the schema's types and bounds. Use at least one group, exactly the two group fields, one group per focus, and at least one eligible ID per group. |
| Required evidence | Include every required ID, preserve UNKNOWN and both sides of conflicts. | Use the supplied `required_evidence_ids` list and preserve missing/UNKNOWN evidence and all conflict sides. The builder includes every flag and the applicable original sources. |
| Questions and recommendations | Select eligible codes and include required questions. The schema supplied the permitted lists and minimum counts. Uniqueness was implicit. | Select at least one from each permitted list, include every required question and do not repeat a code within either list. |
| Authority and final check | CANDIDATE only, untrusted source text, no generated facts, safety decisions or operational writes. | Keep those boundaries and check the **complete** response for eligibility, uniqueness, coverage and schema compliance before returning it. |

The server still enforces context size, source authorization, case linkage, valid flag references, response completeness, pinned model, size and usage limits. Those checks are responsibilities of the application. The model only receives the whitelisted context, instructions and schema. No case-specific example or reference answer was added. The exact prompts are `INSTRUCTIONS_V1` and `INSTRUCTIONS` in [analysis.py](../coordinator/analysis.py). Their SHA-256 hashes, over the UTF-8 instruction strings, are:

| Prompt | SHA-256 |
| --- | --- |
| review-focus-v1 | `27bedbf368ee9a049dbc065bce6477e5d893977811beb1758f7a33e37ccb2fcf` |
| review-focus-v2 | `8f4c64992e2e9022c00b93cdcc31c91795266fe98433b6a9f6ce66ad7491983e` |

## Offline evidence and interpretation

The archived S1 output still passes its original JSON schema and fails evidence validation under **both** instruction versions. A separately authored offline S1 fixture validates. There is no postprocessing of the live response. The case-specific schema, whitelisted inputs, required items, validator, deterministic renderer and scoring thresholds are identical. The bounded mock stays pinned to v1; the canonical mock retains its existing template. Archived results and personal worksheets are preserved.

The intervention was designed after inspecting S1. Any authorized run 03 will reuse the same frozen cases. A change in results cannot by itself establish generalization, causation or human usefulness. The proposed stopping change also affects which cases may be observed. Compare each run by its own denominator and label any cumulative numbers. Codex assisted with the diagnosis, prompt, offline replay, tests and protocol draft.

## Proposed amendment for owner approval

1. Start with S1 repetition 1, using the same pinned model, settings and nine eligible cases for three scheduled repetitions. Record S9 once as a pre-provider rejection. Maximum **27 additional requests**. No connectivity probe.
2. Record each attempted trial before advancing. If a completed response from the pinned model has confirmed usage, passes the strict case-specific schema, and fails a recognized evidence rule, record the rejection and move to the **next scheduled trial**, including after S1 repetition 1. Examples include a repeated eligible ID, repeated focus, duplicate question, missing required evidence or a recognized placement error. A repeated reference in the shared fabricated/repeated error category is verified against the catalog. A rejected response produces no candidate.
3. Stop on provider or configuration failure, exhausted budget, ledger finalization error, unknown usage, unexpected model, or an unclassified or potentially unsafe response. Malformed, fabricated or unbounded outputs cannot qualify as known ordinary rejections. Never retry a trial, repair an output, release a reservation, or substitute a mock.
4. Preserve the raw-versus-accepted distinction, timestamps, usage and sanitized failure evidence. Record terminal outcome counts by run and cumulatively in the run 03 journal. Reconcile interrupted attempts with the private ledger before reporting. Keep the [existing metrics and thresholds](evaluation-methodology.md), including the timing denominator of all attempted generations.

| Evidence at preparation | Attempts | Validated | Validation rejections | Provider failures | Reserved USD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Run 01, v1 | 1 | 0 | 0 | 1 | 0.01598775 |
| Run 02, v1 | 1 | 0 | 1 | 0 | 0.01598775 |
| Run 03, v2 (pending) | 0 | 0 | 0 | 0 | 0 |
| Cumulative | 2 | 0 | 1 | 1 | 0.03197550 |

The real ledger had **28 slots and $1.96802450 of reservation capacity** at preflight. Each future dispatch still requires its own atomic reservation against the original 30-attempt/$2 limits. The project owner's prior approval for run 02 does not enable run 03.

For offline verification, run `.\.venv\Scripts\python.exe -m live_evaluation --run 03 --check` in the repository. This checks the two journals against the published reports, verifies both reservations and frozen input hashes, and stops before private key entry. After explicit approval of the run **and** amendment, the private-console launcher accepts `--run 03 --approve-run-03`. It exclusively creates `data/phase6a-live-v2-run-03.jsonl`. The worksheet generator can use `--run 03` after collection to produce a separate local packet; no worksheets are generated during preparation.
