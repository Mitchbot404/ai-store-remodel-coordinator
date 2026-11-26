# Sporting Goods shipment delay walkthrough

On November 26, 2026, the project owner exercised the local Streamlit prototype with AI guidance, a synthetic Sporting Goods fixture delay and the deterministic mock. The owner reported **13 checks, 12 passing at the tested scope and one partially passing**. The notes give an aggregate score without assigning the partial grade to a numbered check. The observations below preserve that distinction.

| Check | What the owner observed |
| --- | --- |
| 1. Authentication | The supervisor signed in. |
| 2. Task intake | Creating the remodel task produced READY. |
| 3. Blocker intake | Reporting the fixture delay produced BLOCKED. |
| 4. Evidence | Original source records retained identifiers and timestamps. |
| 5. Generation | The mock produced a CANDIDATE summary. |
| 6. Candidate correction | The supervisor corrected candidate information. Operational state stayed BLOCKED. |
| 7. Routing | A separate approved human decision moved the case to UNDER_REVIEW. |
| 8. Incomplete workaround | The application rejected the incomplete approval. |
| 9. Workaround activation | A supervisor decision reached WORKAROUND_ACTIVE. Its safety note and cited shipment status did not establish that the intended inspection detail had been recorded. |
| 10. Staleness | The earlier candidate became stale after operational changes. |
| 11. Regeneration | A second candidate reflected the updated operational information. |
| 12. History | Candidate versions, human decisions and audit history remained available. Two identical corrections appeared in the history. |
| 13. Failure | Simulated failure produced an error explaining that manual review remained available. Both earlier candidates remained visible. No third successful candidate appeared. |

The walkthrough establishes what a user saw. It supplies no timed manual comparison, independent usefulness rating or live-model result.

## Investigation and corrections

**Workaround evidence.** Read-only inspection of the saved synthetic case confirmed that the third source's note was exactly “Structured material observation” and its status was DELAYED. The workaround decision cited three sources. The workbench submits the note and selected status as separate values. The store rejects an empty note and persists the submitted text verbatim before adding the status. An automated Streamlit form check exercised both behaviors. No input trace establishes whether a longer note was typed, pasted into another field or left unsubmitted. The investigation found no reproducible loss of submitted text.

Assignment 2 FR-10 requires source evidence along with the affected task, owner, workaround type, reviewer-supplied safety note and end condition. The old gate verified that cited sources existed for the task. It never asked which observation supported the proposed workaround. The corrected gate requires a supervisor to designate a specific case observation, persists its ID in the existing decision and includes it in the audit citations. A label-only or status-only observation such as the one in this case cannot serve as that evidence. It can still be cited as shipment context. When details are missing, the supervisor can add a new observation while preserving the original. The gate checks attribution and recognizable empty or label-only values. The supervisor judges the relevance, physical conditions and adequacy of the evidence. Existing decisions retain their original contents.

**Narrative uncertainty.** Both saved candidates had an empty missing-fields list although the source explicitly described an unconfirmed replacement date. FR-05 checks required fields and structured status conflicts. The prototype has no required replacement-date field. Its mock reads flags from the structured checks and does not interpret that sentence as a missing field. This is a real coverage gap against the broader uncertainty goal in Assignment 2 §7.5. The workbench now labels the scope of the list. The original observation, candidate packages and deterministic generator are preserved. In the manual/mock/live comparison, distinguish preserving the source from drawing the reviewer's attention to its uncertainty. Record whether the reviewer had to discover it independently.

**Repeated correction.** The two saved evaluations of candidate 1 matched on all recorded content except the review timestamp, approximately 11.95 seconds apart. Each submission previously inserted another decision and audit event. The records cannot distinguish a double click from an intentional resubmission. Within the existing write transaction, the application now rejects a repeat of the same reviewer's latest evaluation of that candidate. It compares outcome, reviewed status, proposed step, rationale and cited source set. A changed review can be saved, including a return to an earlier assessment after a revision. The two historical events remain intact.

**Generic recommendation.** Both saved packages asked an authorized supervisor to review the evidence and open questions. The regenerated package updated the approved operational context, but an unchanged set of structured missing/conflict conditions selected the same recommendation. Retain this example when comparing how well each approach directs attention to the unconfirmed date or the temporary workaround's end condition. No improvement in usefulness has been measured.

## Independent offline verification

The regression suite uses fresh temporary databases. A Streamlit AppTest exercises observation entry and explicit workaround citation. Store tests reject a missing designation, the generic source and an uncited or unrelated ID without changing the case. Concurrent identical corrections with differently ordered citations produce one new decision and one audit event. Subsequent revisions remain possible.

The failure regression generates a candidate, records a correction and an operational review, then regenerates before forcing the provider error. It compares every row of tasks, blockers, sources, decisions, audits and both complete saved candidate versions before and after the failure. It then submits a separate supervisor decision through the normal manual path. This checks persistence and continued access to operational review independently of the UI message. These checks are automated. The project owner's walkthrough preceded the fixes. [Complete suite results](validation.md)

## Deferred interface work

For Phase 6B, review horizontal overflow, replace raw JSON in operational views, shorten forms to fields relevant to the selected decision, and move technical IDs behind readable source labels. Candidate versions and audit entries need clearer chronology. Stronger visual hierarchy and guidance should make the supervisor's next task obvious and give the workbench the appearance of an operational dashboard.

## Evaluation boundary

This synthetic case supplements the validation notes. It does not change the ten evaluation cases, reference v2, archived mock results, scores or approval status. Codex assisted with the investigation, implementation, regression tests and documentation. Live evaluation still requires the owner's explicit approval of corrected reference v2 and the existing configuration and spending gates.
