"""Deterministic, read-only exception checks. No operational decisions."""
from datetime import datetime, timezone, timedelta

STATUSES = ('UNKNOWN', 'ARRIVED', 'MISSING', 'DELAYED', 'OUTDATED', 'DAMAGED', 'NO_LOCAL_WORK')


def unknown(value):
    return value is None or (isinstance(value, str) and value.strip().upper() in {'', 'UNKNOWN', 'UNASSIGNED'})


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (ValueError, TypeError, AttributeError):
        return None


def inspect_case(case, at=None):
    at = at or datetime.now(timezone.utc)
    flags = []
    def flag(code, message, refs=(), blocking=False, fields=()):
        flags.append(dict(code=code, message=message, source_refs=list(refs), blocking=blocking, fields=list(fields)))
    task = case['task']; sources = case['sources']
    for field in ('task_id', 'project_id', 'department_area', 'description', 'target_date_or_sequence', 'reporter_id', 'created_at'):
        if unknown(task.get(field)):
            flag('MISSING_INFORMATION', f'Task {field} is missing or unknown.', fields=[field], blocking=True)
    if not isinstance(task.get('required_items'), list) or any(unknown(i) for i in task.get('required_items', [])):
        flag('MISSING_INFORMATION', 'Required material list is missing or contains unknown items.', fields=['required_items'], blocking=True)
    for source in sources:
        for field in ('source_id', 'source_type', 'captured_at', 'submitted_by', 'supported_fields_or_note', 'authorization_flag'):
            if unknown(source.get(field)):
                flag('MISSING_INFORMATION', f'Source {field} is missing or unknown.', [source.get('source_id')], True, [field])
        if source.get('material_status') == 'UNKNOWN':
            flag('UNKNOWN_SOURCE_STATUS', 'Source explicitly reports UNKNOWN material status.', [source.get('source_id')])
    if not case['blockers']:
        return flags
    blocker = case['blockers'][0]; refs = blocker.get('source_refs', [])
    for field in ('blocker_id', 'blocker_type', 'observed_condition', 'reported_at', 'reporter_id', 'review_state'):
        if unknown(blocker.get(field)):
            flag('MISSING_INFORMATION', f'Blocker {field} is missing or unknown.', refs, True, [field])
    if not refs or not set(refs) <= {s.get('source_id') for s in sources}:
        flag('MISSING_INFORMATION', 'Blocker source evidence is missing.', refs, True, ['source_refs'])
    if unknown(blocker.get('material_fixture_status')):
        flag('UNKNOWN_MATERIAL_STATUS', 'Material status is UNKNOWN; verify before resolution/completion.', refs, fields=['material_fixture_status'])
    observations = [s for s in sources if s.get('source_id') in refs and s.get('authorization_flag') == 'SYNTHETIC' and s.get('material_status')]
    arrived = [s for s in observations if s['material_status'] == 'ARRIVED']
    absent = [s for s in observations if s['material_status'] in {'MISSING', 'DELAYED'}]
    conflict_refs = {s['source_id'] for s in arrived + absent}
    reconciled = any(d.get('decision_type') in {'APPROVED', 'CORRECTED'} and
                     d.get('corrected_values', {}).get('conflict_resolution_note') and
                     not unknown(d.get('corrected_values', {}).get('material_fixture_status')) and
                     conflict_refs <= set(d.get('source_refs', [])) for d in case.get('decisions', []))
    if arrived and absent:
        flag('CONFLICT_REVIEWED' if reconciled else 'CONFLICT',
             'Arrival and missing/delayed sources disagree. ' + ('Supervisor reconciliation is recorded; original evidence retained.' if reconciled else 'Supervisor reconciliation required; no source selected automatically.'),
             sorted(conflict_refs), not reconciled)
    for source in observations:
        status = source['material_status']
        if status in {'OUTDATED', 'DAMAGED', 'NO_LOCAL_WORK'}:
            flag(status, 'Human review required: ' + status + '. This is not safety or reassignment approval.', [source['source_id']])
    if blocker['workflow_state'] not in {'RESOLVED', 'COMPLETED', 'READY'}:
        reported = timestamp(blocker.get('reported_at'))
        if reported is None or reported > at:
            flag('INVALID_TIMING', 'Reported time is invalid or in the future.', refs)
        else:
            age = at - reported
            if age >= timedelta(days=1):
                flag('MULTI_DAY_DELAY', 'Open blocker has lasted at least 24 hours.', refs)
            elif age >= timedelta(hours=3):
                flag('EXTENDED_DELAY', 'Open blocker has lasted at least 3 hours.', refs)
            elif age >= timedelta(hours=1):
                flag('SHORT_DELAY', 'Open blocker has lasted between 1 and 3 hours.', refs)
        target = timestamp(task.get('target_date_or_sequence'))
        if target:
            if at > target:
                flag('OVERDUE_OPEN_BLOCKER', 'Open blocker is past the task target.', refs, fields=['target_date_or_sequence'])
            elif target - at <= timedelta(days=1):
                flag('APPROACHING_TARGET', 'Open blocker is within 24 hours of the task target.', refs, fields=['target_date_or_sequence'])
        else:
            flag('SEQUENCE_REVIEW', 'Sequence/unknown target has no clock deadline; supervisor must assess sequence impact.', refs, fields=['target_date_or_sequence'])
    return flags
