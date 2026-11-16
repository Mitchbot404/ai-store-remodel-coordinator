# Phase 1 implementation record

Baseline: CEN4010_Assignment2.pdf, section 7.2 (fields), 7.3 (transitions), 7.4 (authority), and section 8 (incremental implementation). Course handouts describe the complete final submission; they do not override the user's instruction to stop after Phase 1.

| Requirement | Phase 1 evidence |
| --- | --- |
| FR-01 task registration | Required-field validation and persistence tests |
| FR-02 blocker intake | Linked blocker, mandatory source, explicit UNKNOWN, duplicate rejection |
| FR-03 source traceability | Source records linked to blocker and audit, visible in UI |
| FR-06 controlled states | Exact enum and transition graph; only READY/BLOCKED reachable in this phase |
| FR-07 / NFR-09 authority | All non-intake transitions denied; review deferred |
| NFR-06 integrity | Atomic intake and audit transactions; failure tests |

## Implementation choices and deviations

No logical architecture redesign. Streamlit and SQLite implement the intake/view and state-store responsibilities in one local process. The report does not prescribe a storage engine. UUIDs and UTC timestamps are generated locally. Task-source and audit-task associations are storage metadata outside the report's listed fields. ReviewDecision has all specified fields but no persistence/action path until Phase 2. Review state initially UNRESOLVED, with no AI candidate implied.

The phase deliberately does not satisfy the full security or full transition requirements yet: authentication, assigned roles, and operational review belong to implementation step 2. Every review transition is unavailable rather than simulated with a role dropdown. One blocker per task is a conservative implementation restriction for the report's bounded one-blocker workflow. Later lifecycle support must revisit it explicitly.

## Phase 2 recommendation (not implemented)

Add authenticated prototype accounts and the report's role matrix, a supervisor review workbench, persisted ReviewDecision records, approved owner/next action, all eleven guarded transitions, workaround evidence/end conditions, and resolution/completion evidence. Test the complete allow/deny role matrix and atomic review/audit updates before adding AI. Exception/timing logic follows that work; bounded AI is step 4 in the report.

## AI development assistance

Codex read the supplied report, generated Phase 1 code/documentation/tests, and ran verification. No model is part of the running application. Student review is still needed before committing/submitting. Validation results are recorded separately in validation.md.
