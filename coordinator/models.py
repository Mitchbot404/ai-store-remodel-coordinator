from dataclasses import dataclass
from enum import Enum


class WorkflowState(str, Enum):
    READY = 'READY'
    BLOCKED = 'BLOCKED'
    UNDER_REVIEW = 'UNDER_REVIEW'
    WORKAROUND_ACTIVE = 'WORKAROUND_ACTIVE'
    WAITING_FOR_MATERIAL = 'WAITING_FOR_MATERIAL'
    REASSIGNED = 'REASSIGNED'
    RESOLVED = 'RESOLVED'
    COMPLETED = 'COMPLETED'


# Solution Design Report section 7.3. Transitions are applied through authenticated intake or supervisor review.
ALLOWED_TRANSITIONS = {
    'READY': {'BLOCKED'},
    'BLOCKED': {'UNDER_REVIEW'},
    'UNDER_REVIEW': {'WORKAROUND_ACTIVE', 'WAITING_FOR_MATERIAL', 'REASSIGNED', 'RESOLVED'},
    'WORKAROUND_ACTIVE': {'WAITING_FOR_MATERIAL'},
    'WAITING_FOR_MATERIAL': {'UNDER_REVIEW'},
    'REASSIGNED': {'UNDER_REVIEW'},
    'RESOLVED': {'READY', 'COMPLETED'},
    'COMPLETED': set(),
}


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    project_id: str
    department_area: str
    description: str
    target_date_or_sequence: str
    required_items: list[str]
    reporter_id: str
    created_at: str


@dataclass(frozen=True)
class BlockerRecord:
    blocker_id: str
    task_id: str
    blocker_type: str
    observed_condition: str
    material_fixture_status: str
    reported_at: str
    reporter_id: str
    source_refs: list[str]
    workflow_state: WorkflowState
    review_state: str


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    source_type: str
    captured_at: str
    submitted_by: str
    supported_fields_or_note: str
    authorization_flag: str


@dataclass(frozen=True)
class ReviewDecision:
    reviewer_id: str
    decision_type: str
    corrected_values: dict
    approved_owner: str
    approved_next_action: str
    approved_transition: str
    rationale_note: str
    decided_at: str


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    actor_id: str
    action: str
    prior_state: str | None
    new_state: str
    source_refs: list[str]
    timestamp: str
