# Phase 6A technical evaluation results

On November 26, 2026, S1 repetition one returned **HTTP 403**. The evaluator stopped after one of 27 planned requests. It recorded no completed model response, no validation rejection and no accepted candidate. The HTTP status alone does not identify the cause. No connectivity probe or retry appears in the ledger. The other 26 trials were never sent (S1 repetitions two and three, plus all three repetitions of S2–S8 and S10). S9 was rejected separately before provider invocation. [Sanitized attempt record](../evaluation/results/live-run-01.json)

The run used commit `b011d29`, approved reference v2, prompt `review-focus-v1` and schema `bounded-analysis-v1`. It requested OpenAI `gpt-5.4-mini-2026-03-17` with reasoning effort `none`, strict structured output, a 1,500-token output cap and storage disabled. The actual serving model, input/output token counts, usage-based cost and provider-billed amount are unknown. The only failure took **1.649106 seconds** in the adapter and **1.661626 seconds** end to end. There is no successful generation latency sample.

The journal's reservation ID and amount match the sole entry in the local ledger, marked `failed_or_rejected`. The runner started with 30 slots and $2. It retained **$0.01598775** against the failed attempt, leaving **29 slots and $1.98401225** of cumulative reservation capacity. This accounting measures the local spending guard. Confirming actual charges requires provider billing evidence. The original journal, ledger and private identifiers remain local.

| Frozen criterion | Live result |
| --- | --- |
| Reject invalid required sources before transmission | **Pass.** S9 was rejected in 1/1 applicable case, with zero provider attempts for S9. |
| Validated candidate within 10 s on at least 90% of attempts | **Fail for this run.** 0/1 attempted generations delivered a candidate. A fast HTTP error does not satisfy the target. |
| At least 95% raw schema compliance | **Unassessable.** 0 completed model responses. The single failure occurred before output validation. |
| 100% source traceability, preservation of missing/UNKNOWN information and conflicts | **Unassessable for live output.** 0 accepted candidates, 0 live claims or applicable items available for scoring. S4's conflict was never sent. |
| Zero unsupported claims or unauthorized recommendations and at most 200 words | **Unassessable for live output.** 0 model outputs. The model's handling of S10's injection and S3's fixture condition also remains untested. |
| Human authority and operational isolation | **Preserved on the observed failure path.** 0 effective operational actions across 1 attempt. The evaluator reads frozen dictionaries and has no operational Store connection. Dataset and reference hashes matched after the run. No before/after snapshot of an external operational database was taken. |
| Human corrections, rejection, usefulness and review effort | **Pending.** 0 scored personal trials. Five live-assigned worksheets contain manual fallback. Their scores cannot measure live-model usefulness. |

Dataset `phase6a-v2` SHA256: `d1618ef687ca3c0f11f0b2d93fe55482520d0ee7ea902b0d384cef32f11e53db`. Fixed case clock: `2026-11-26T12:00:00+00:00`. The checked-in JSON reports retain execution timestamps and reference hashes.

| Condition | Cases processed | Validated candidates | Required-source rejection | Human scores |
| --- | ---: | ---: | ---: | --- |
| Original canonical mock | 10 | 9 | S9 | Not measured |
| Bounded-analysis mock | 10 | 9 | S9 | Not measured |
| Manual review | Case packet prepared | N/A | S9 requires evidence repair | Not performed |
| GPT-5.4 mini live | 10 preflighted, 1 request | 0 | S9 | Not measured |

Both mocks validated S1–S8 and S10; S9 was rejected before generation because its required source did not exist. This is expected preflight behavior, not a model failure. The bounded mock selects all available catalog entries deterministically and uses eligible review aids; it is not generative reasoning. No accuracy or usefulness advantage over the canonical mock has been demonstrated.

Rechecking each archived mock against the frozen cases reproduced all nine canonical packages in each condition. Both included all 19/19 expected source IDs and retained the approved owner and next action in 9/9 eligible cases, including S2's existing workaround. All 9/9 summaries in each condition met the 200-word limit under the frozen counting convention (canonical range 40–67 words, bounded range 100–184). These are technical checks. The single live failure produced no clarification question or recommendation to compare with the mocks. The supplementary Sporting Goods walkthrough received zero requests.

Evidence: [canonical mock](../evaluation/results/mock.json), [bounded mock](../evaluation/results/mock-bounded.json). Each report includes the package, analysis where applicable, provenance, observed offline elapsed time, failure stage and blank human assessment. These times measure local code, not live API latency or human review effort.

## Rejected and corrected development outputs

Offline adversarial tests deliberately supplied unsupported factual prose, invented evidence IDs, false APPROVED labels, unauthorized workaround codes, missing conflict sides/UNKNOWN evidence, invalid grouping, malformed JSON, model mismatches, refusals, incomplete responses and timeouts. These were rejected without effective operational decisions. Prompt-injection text was retained as source data and was not executed. These are constructed tests, not observed live-model hallucinations.

The first new-test collection failed because a fixture used pytest's reserved name `request`; it was renamed, then the focused suite passed. A provider-label review also corrected the workbench so bounded mock output is explicitly identified as deterministic rather than external-provider output. See [validation](validation.md) for final test totals.

## Metrics not yet established

An additional [AI-guided Sporting Goods walkthrough](sporting-goods-walkthrough.md) identified two points to examine in the manual/mock/live comparison. The source described an unconfirmed replacement date while both canonical mock summaries displayed zero missing fields. Both versions proposed the same review step across a change in operational state. This supplementary observation carries no human usefulness score and leaves the frozen v2 evaluation cases and results intact.

Phase 6A remains open. The owner can complete the 15 worksheets now, recording fallback separately. A live-assisted comparison still requires an accepted live candidate for each assigned case. Any future paid work must account for this preserved failure, the remaining slots and the existing ledger. Codex assisted with technical reconciliation, documentation and exercise preparation. The owner supplies all personal judgments and review times. [Reference approval](reference-expectations.md) · [Personal exercise](manual-review-exercise.md)

## Revision 2 chronology check

The fixed evaluation time is November 26 at 12:00 UTC. Each case represents a snapshot at that time. The blocker's source list includes subsequent observations. Each dated supervisor decision must cite evidence already captured when the supervisor acted.

In S2, S2-INTAKE records the missed shipment on November 23 at 12:00 UTC. S2-LAYOUT records a proposed temporary layout on November 24 at 11:30 UTC. The supervisor approved that layout at 12:00 UTC that day. S2-SRC-1 and S2-SRC-2 retain their original November 26 timestamps and contents. The snapshot reflects the existing supervisor approval and keeps the original blocker open.

The fixture checks cover all ten cases, including task/blocker linkage, timezone-aware event order, source uniqueness within each case, source capture by the evaluation time, and decision-time evidence. S9 retains the deliberately absent source to test preflight rejection. Across the nine accepted cases, both mock reports preserved the authorized source-ID sets, and the structured flags matched the expectations. These checks establish record consistency within the synthetic dataset.
