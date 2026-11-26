# Phase 6A evidence: offline only

Recorded November 26, 2026. **Live-model evaluation: NOT RUN. Human evaluation: NOT PERFORMED. API charges incurred by this work: $0.** References remain AI-assisted drafts awaiting owner review.

Dataset `phase6a-v1` SHA256: `68ca7d4a5402d30e9b4bdbc9a499ce447dfb4739ef9c2bcc69416fd74d668963`. Fixed case clock: `2026-11-26T12:00:00+00:00`. The checked-in JSON reports retain execution timestamps and reference hashes.

| Condition | Cases processed | Validated candidates | Required-source rejection | Human scores |
| --- | ---: | ---: | ---: | --- |
| Original canonical mock | 10 | 9 | S9 | Not measured |
| Bounded-analysis mock | 10 | 9 | S9 | Not measured |
| Manual review | Case packet prepared | N/A | S9 requires evidence repair | Not performed |
| GPT-5.4 mini live | 0 | N/A | N/A | Not measured |

Both mocks validated S1–S8 and S10; S9 was rejected before generation because its required source did not exist. This is expected preflight behavior, not a model failure. The bounded mock selects all available catalog entries deterministically and uses eligible review aids; it is not generative reasoning. No accuracy or usefulness advantage over the canonical mock has been demonstrated.

Evidence: [canonical mock](../evaluation/results/mock.json), [bounded mock](../evaluation/results/mock-bounded.json). Each report includes the package, analysis where applicable, provenance, observed offline elapsed time, failure stage and blank human assessment. These times measure local code, not live API latency or human review effort.

## Rejected and corrected development outputs

Offline adversarial tests deliberately supplied unsupported factual prose, invented evidence IDs, false APPROVED labels, unauthorized workaround codes, missing conflict sides/UNKNOWN evidence, invalid grouping, malformed JSON, model mismatches, refusals, incomplete responses and timeouts. These were rejected without effective operational decisions. Prompt-injection text was retained as source data and was not executed. These are constructed tests, not observed live-model hallucinations.

The first new-test collection failed because a fixture used pytest's reserved name `request`; it was renamed, then the focused suite passed. A provider-label review also corrected the workbench so bounded mock output is explicitly identified as deterministic rather than external-provider output. See [validation](validation.md) for final test totals.

## Metrics not yet established

Live factual accuracy, semantic source support, live schema pass rate, live conflict/UNKNOWN preservation, unauthorized recommendation rate, live latency, human correction/rejection rates, practical usefulness and manual-vs-live improvement are **NOT MEASURED**. Offline contract checks do not substitute for these results. No blank human fields have been filled with guesses. Failed provider output is sanitized rather than exposed; raw-output semantic error rates cannot be reconstructed from the current coarse failure record alone. Before claiming such rates, extend the reviewed local error-evidence procedure or explicitly mark them unmeasurable.

The next evidence gate is owner review of [reference expectations](reference-expectations.md), followed by secure local key entry and the bounded approved live experiment. Then complete the [human exercise](manual-review-exercise.md). Phase 6A is still incomplete; Phase 6B has not begun.
