# Approved live experiment

The project owner approved the frozen v2 inputs on November 26, 2026. The previous verified implementation was commit `2153c1b`. The run journal records the exact evaluation code commit. The existing protocol, ten cases, two archived mock reports, prompt, pinned model, limits and acceptance thresholds apply. [Approved references](reference-expectations.md) · [Evaluation methodology](evaluation-methodology.md)

## Run locally

### Run 02 recovery preparation

The project owner reported correcting the project model allowlist from the family name to the exact snapshot already requested by the application. The dashboard review found no Responses log entry. Run 01 captured HTTP 403 only. Its cause remains unconfirmed.

To verify run 02 offline from the repository, use:

```powershell
.\.venv\Scripts\python.exe -m live_evaluation --run 02 --check
```

This checks both frozen input hashes and reconciles run 01's stopped S1 request with its existing reservation in the Windows ledger. It creates no recovery journal and does not prompt for credentials. Run 01 retains its original journal, published result and 1 of the 30 cumulative slots.

**Separate owner approval is pending.** After approval, the private-console launcher accepts `--run 02 --approve-run-02` and uses the existing hidden key prompt. The first request is **S1 repetition 1**, scored in the experiment. Its failure, including an evidence-validation rejection, stops the run. If it validates, the runner continues the existing nine-case, three-repetition schedule, up to 27 requests including that first request. S9 is rejected locally. There is no separate connectivity probe. Subsequent trials use the original stop rules. The model, prompt, references, acceptance thresholds, timeout, token limits and cumulative spending rules are unchanged.

Run 02 exclusively creates `data/phase6a-live-v2-run-02.jsonl`. An existing recovery journal blocks a repeat launch. Keep the original run 01 journal, ledger and worksheets. Account dashboard rounding or a missing Responses log does not release run 01's reservation. Run 02 has 29 slots and $1.98401225 of conservative capacity available at preparation time. The ledger rechecks the limits at each reservation.

### Private diagnostics

For future genuine requests, the transport assigns a fresh client request ID and saves it before dispatch. When available, it also records the recognized OpenAI request ID from the response header on successful and error HTTP responses. These IDs stay under `%LOCALAPPDATA%\CEN4010-Remodel-Coordinator\private-request-ids\` in a file named for the local reservation. To troubleshoot, a local reviewer can match the trial's private reservation to that file. Keep it outside Git, shared reports and worksheets. A failure before any response can leave only the client ID.

For HTTP errors the journal can retain the HTTP status and recognized machine-readable error code and type. Unknown strings become category labels. Oversized, malformed or message-only bodies yield no code. The diagnostic parser reads at most 8,193 bytes and never stores the body, provider message, key or complete headers. Previously missing diagnostics cannot be recovered from run 01.

### Historical run 01

The November 26 run has already stopped after HTTP 403. Its journal and cumulative ledger are retained. The command below documents that run. The current task is the offline [personal exercise](manual-review-exercise.md). [Reconciled results](evaluation-results.md)

From a private PowerShell console in the repository, run:

```powershell
.\.venv\Scripts\python.exe -m live_evaluation
```

Enter the restricted key at the hidden console prompt. Only the evaluation process receives it. The launcher sets process-local provider gates and clears the key on exit. No clipboard utility, secret file, persistent environment variable, Streamlit session or chat exchange is needed. Keep the console open through completion. To inspect the preflight without prompting for a key or contacting the provider, append `--check`.

The runner verifies both frozen hashes, preflights every case and checks the local cumulative ledger. It journals S9 once as ineligible and runs the other nine in dataset order for each of three scheduled repetitions. No connectivity probe is needed. Each paid attempt gets the existing atomic conservative reservation. A known validation rejection with reported usage is retained and the schedule advances to the next distinct trial. An ambiguous failure, provider/configuration error or exhausted allowance stops collection. The runner issues no retries and refuses to overwrite or resume an existing journal. After an interruption, retain the journal and ledger for reconciliation.

Results are written incrementally to ignored `data/phase6a-live-v2.jsonl`. The parent checkout stays clean. The collector uses frozen synthetic case dictionaries, with no operational Store or database connection. Original evidence and decisions in the fixture remain read-only. The reference file is hashed separately. The API receives the existing bounded case context, evidence catalog and permitted codes. The controller records model choices separately from the locally rendered facts. Codex assisted with run instrumentation, worksheet preparation and testing.

## Scoring before observing results

Use the published thresholds and show numerators and denominators. Count unique reserved invocations as attempts. Reconcile interrupted trials against the unchanged ledger. S9 and an unreserved budget stop are pre-provider outcomes. Report all provider failures and validation rejections. A completed refusal produces no schema-conformant candidate. Separate structurally valid responses from those also passing evidence and authority checks. Record missing usage or billing as unavailable. Token-based estimates use the adapter rates. Reservations are conservative limits, not invoices.

For latency, count accepted packages delivered in at most ten seconds over *all attempted generations*. Report end-to-end elapsed time separately from adapter latency. For the 200-word target, count whitespace-delimited words in the displayed status values, missing/conflict messages, uncertainty, proposed step, group labels, rendered flag messages, questions and recommendations. Exclude identifiers, source citations and verbatim original source details. Include repeated visible warnings. Keep the unabridged rendering and document any field omissions. Apply the same convention to comparable mock and live views.

For each accepted package, check each rendered evidence ID, source link, exact attributed note, material status, required uncertainty/conflict item, and approved owner/action against the frozen case. Report unassessed judgments separately. Semantic support, misleading grouping and practical usefulness require human assessment. For rejected outputs retain known bounded IDs/codes where the strict schema permits them. Record local rejection categories and available usage for other failures. Arbitrary invalid model text, response bodies and request headers stay out of the evidence.

Assignment 2's FR-03–05, NFR-01/02 and candidate acceptance criteria govern evidence traceability, uncertainty, latency and readability. Its authority rules reserve decisions for supervisors. The Final Project and Grading Criteria call for reproducible representative and exception behavior, supported claims, disclosure of AI assistance, and a clear account of remaining limitations. This run supplies technical evidence. The owner supplies the personal review judgments. The Sporting Goods walkthrough stays supplementary and receives zero extra requests.

## Human comparison

After collecting and checking the journal, run `.\.venv\Scripts\python.exe -m prepare_trials` once. Open `data/phase6a-personal-trials/START.md`, then complete files 01–15 in order. Each contains the original case, source IDs, fixed-time flags and questions. The assigned mock is the archived **bounded deterministic mock** so its evidence choices can be compared with the same live interface. The canonical mock remains a separate technical comparator. Use live repetition **one**, fixed in advance, even if a later output looks better. A missing or rejected assigned output produces a marked manual fallback. Keep personal answers local. [Timing, rating and review instructions](manual-review-exercise.md)
