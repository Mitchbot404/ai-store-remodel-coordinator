# Phase 2 human review and workflow controls

The authoritative baseline remains Assignment 2 sections 7.2–7.4. No AI or automatic operational decision making is included.

## Workflow

Provision named users locally with `python manage_users.py username "Associate"`. Other exact roles are `Stocking/Support`, `Supervisor/Manager`, and `Technical/System Owner`. Password entry is hidden and requires 12 characters. There are no default application credentials. Use `--database` when running against a custom REMODEL_DB.

Sign in before viewing records. Associates and supervisors create tasks/blockers; attribution comes from their authenticated identity. Associates, support, and supervisors add synthetic observations without silently changing approved status. Supervisors record APPROVED, CORRECTED, REJECTED, or UNRESOLVED decisions. Each decision requires rationale and task-local source references. Approved/corrected decisions require owner and next action. Rejected/unresolved decisions preserve state and previous approved ownership.

All eleven edges from section 7.3 are retained. Initial READY-to-BLOCKED intake requires source evidence. Subsequent transitions require a supervisor review and are checked against the graph inside a transaction. Workarounds require type, human safety approval note, and end condition; reassignments require destination/context, return condition, and local-work-exhausted explanation. Human reviewers verify physical conditions in the rationale and supporting source records; software does not decide safety or material arrival. Completion is terminal.

Decisions, blocker status, and audit events are committed atomically. Reviews and approved transitions create separate audit entries. Existing sources and history are retained. A stale state submission is rejected. Direct transition calls remain prohibited.

## Design choices and limits

- Existing dataclass fields remain unchanged. Decision storage adds task linkage, decision ID, and source references as metadata for traceability. User/session tables and a decisions table are additive; existing Phase 1 records remain readable after login.
- Authentication intentionally replaces Phase 1 anonymous access and caller-supplied identities. Existing tests were updated to authenticate; baseline intake behavior remains covered.
- All lifecycle transitions require supervisor review, including routing transitions. This conservative implementation does not delegate routing authority to support or associates.
- Technical users have no operational content or approvals in the UI. Configuration, account provisioning, and validation remain local administrative commands rather than a new management dashboard.
- One blocker per task remains. READY after resolution retains the same blocker history; a later READY-to-BLOCKED supervisor review reopens that bounded case.
- SQLite is local and unencrypted. Local filesystem administrators can alter code/data and provision roles; application authorization cannot prevent that. Do not expose this prototype to untrusted networks.
- Passwords use salted PBKDF2-SHA256 (600,000 iterations). Opaque sessions are stored as hashes, expire after one hour, and are revoked on logout. No MFA, rate limiting, account recovery, password-change UI, or enterprise identity integration is implemented.
- Operational roles share access to this single synthetic project dataset; there is no per-store access partitioning. Denied attempts are surfaced as errors, not appended to operational audit history.
- No conflict/timing detection or AI has been added. Phase 3 should implement missing/conflicting information flags, timing checks, and representative scenario fixtures before AI work.

## Development record

Codex generated the changes and tests against the supplied design. Review and commit remain the student's responsibility. Manual verification uses a separate ignored synthetic database, not the user's Phase 1 records.
