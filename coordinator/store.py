"""Authenticated intake and transactional human review workflow."""
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from .models import AuditEvent, BlockerRecord, SourceReference, TaskRecord, WorkflowState, ReviewDecision, ALLOWED_TRANSITIONS
from .auth import Auth, Role
from .exceptions import inspect_case, STATUSES, unknown


def now():
    return datetime.now(timezone.utc).isoformat()


def required(**values):
    for key, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{key} is required.')


class Store:
    def __init__(self, path, token=None):
        self.path = str(path)
        self.auth = Auth(path)
        self.token = token
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS blockers (id TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE REFERENCES tasks(id), record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audits (id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), record TEXT NOT NULL);
            ''')

    def authorize(self, roles=(Role.ASSOCIATE, Role.SUPPORT, Role.SUPERVISOR)):
        actor, role = self.auth.identity(self.token)
        if role not in roles:
            raise PermissionError("Your assigned role cannot perform this action.")
        return actor

    def connect(self):
        db = sqlite3.connect(self.path)
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def _source(self, db, task_id, reporter, source_type, note):
        required(source_type=source_type, source_note=note)
        source = SourceReference(str(uuid4()), source_type, now(), reporter, note, 'SYNTHETIC')
        db.execute('INSERT INTO sources VALUES (?, ?, ?)', (source.source_id, task_id, json.dumps(asdict(source))))
        return source.source_id

    def _audit(self, db, task_id, actor, action, prior, state, refs):
        event = AuditEvent(str(uuid4()), actor, action, prior, state, refs, now())
        db.execute('INSERT INTO audits VALUES (?, ?, ?)', (event.event_id, task_id, json.dumps(asdict(event))))

    def create_task(self, project_id, department_area, description, target_date_or_sequence,
                    required_items, reporter_id, source_type='Synthetic observation', source_note=''):
        actor = self.authorize((Role.ASSOCIATE, Role.SUPERVISOR))
        if reporter_id != actor:
            raise ValueError("Reporter must match the signed-in user.")
        required(project_id=project_id, department_area=department_area, description=description,
                 target_date_or_sequence=target_date_or_sequence, reporter_id=reporter_id)
        if not isinstance(required_items, list) or any(not isinstance(i, str) or not i.strip() for i in required_items):
            raise ValueError('Required items must be a list of nonblank names; an empty list means none.')
        task = TaskRecord(str(uuid4()), project_id, department_area, description,
                          target_date_or_sequence, required_items, reporter_id, now())
        with self.connect() as db:
            db.execute('INSERT INTO tasks VALUES (?, ?)', (task.task_id, json.dumps(asdict(task))))
            refs = [self._source(db, task.task_id, reporter_id, source_type, source_note)] if source_note.strip() else []
            self._audit(db, task.task_id, reporter_id, 'TASK_CREATED', None, 'READY', refs)
        return task.task_id

    def report_blocker(self, task_id, blocker_type, observed_condition, reporter_id,
                       source_type, source_note, material_fixture_status='UNKNOWN'):
        actor = self.authorize((Role.ASSOCIATE, Role.SUPERVISOR))
        if reporter_id != actor:
            raise ValueError("Reporter must match the signed-in user.")
        required(blocker_type=blocker_type, observed_condition=observed_condition, reporter_id=reporter_id,
                 source_type=source_type, source_note=source_note)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM tasks WHERE id=?', (task_id,)).fetchone():
                raise ValueError('Task does not exist.')
            if db.execute('SELECT 1 FROM blockers WHERE task_id=?', (task_id,)).fetchone():
                raise ValueError('This task already has a blocker. This bounded prototype supports one blocker per task.')
            ref = self._source(db, task_id, reporter_id, source_type, source_note)
            blocker = BlockerRecord(str(uuid4()), task_id, blocker_type, observed_condition,
                                    material_fixture_status.strip() or 'UNKNOWN', now(), reporter_id,
                                    [ref], WorkflowState.BLOCKED, 'UNRESOLVED')
            db.execute('INSERT INTO blockers VALUES (?, ?, ?)', (blocker.blocker_id, task_id, json.dumps(asdict(blocker))))
            self._audit(db, task_id, reporter_id, 'BLOCKER_REPORTED', 'READY', 'BLOCKED', [ref])
        return blocker.blocker_id

    def tasks(self):
        self.authorize()
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT record FROM tasks ORDER BY rowid')]

    def case(self, task_id):
        self.authorize()
        with self.connect() as db:
            row = db.execute('SELECT record FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise ValueError('Task does not exist.')
            result = {'task': json.loads(row[0])}
            for table in ('blockers', 'sources', 'audits', 'decisions'):
                result[table] = [json.loads(r[0]) for r in db.execute(f'SELECT record FROM {table} WHERE task_id=? ORDER BY rowid', (task_id,))]
            result['workflow_state'] = result['blockers'][0]['workflow_state'] if result['blockers'] else 'READY'
            return result

    def transition(self, *args, **kwargs):
        raise PermissionError('Use an authenticated supervisor review decision to change state.')

    def add_observation(self, task_id, source_type, note, material_status=None):
        actor = self.authorize()
        if material_status is not None and material_status not in STATUSES:
            raise ValueError("Unsupported structured material status.")
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM tasks WHERE id=?', (task_id,)).fetchone():
                raise ValueError('Task does not exist.')
            ref = self._source(db, task_id, actor, source_type, note)
            if material_status is not None:
                source = json.loads(db.execute('SELECT record FROM sources WHERE id=?', (ref,)).fetchone()[0])
                source['material_status'] = material_status
                db.execute('UPDATE sources SET record=? WHERE id=?', (json.dumps(source), ref))
            row = db.execute('SELECT record FROM blockers WHERE task_id=?', (task_id,)).fetchone()
            state = 'READY'
            if row:
                blocker = json.loads(row[0])
                blocker['source_refs'].append(ref)
                state = blocker['workflow_state']
                db.execute('UPDATE blockers SET record=? WHERE task_id=?', (json.dumps(blocker), task_id))
            self._audit(db, task_id, actor, 'SOURCE_ADDED', state, state, [ref])
        return ref

    def review(self, task_id, expected_state, decision_type, target, owner, next_action,
               rationale, source_refs, corrected_values=None):
        actor = self.authorize((Role.SUPERVISOR,))
        required(rationale=rationale)
        if decision_type not in {'APPROVED', 'CORRECTED', 'REJECTED', 'UNRESOLVED'}:
            raise ValueError('Invalid review decision.')
        corrections = corrected_values or {}
        allowed_fields = {'material_fixture_status', 'workaround_type', 'safety_approval_note',
                          'end_condition', 'destination_context', 'return_condition', 'local_work_exhausted', 'conflict_resolution_note'}
        if set(corrections) - allowed_fields or any(not isinstance(v, str) or not v.strip() for v in corrections.values()):
            raise ValueError('Invalid correction fields or values.')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT record FROM blockers WHERE task_id=?', (task_id,)).fetchone()
            if not row:
                raise ValueError('A blocker is required for review.')
            blocker = json.loads(row[0])
            prior = blocker['workflow_state']
            if prior != expected_state:
                raise ValueError('State changed. Reload before reviewing.')
            if prior == 'COMPLETED':
                raise ValueError('Completed tasks are terminal.')
            new = target or prior
            if new != prior and new not in ALLOWED_TRANSITIONS[prior]:
                raise ValueError('Transition is not allowed by the design.')
            if decision_type in {'REJECTED', 'UNRESOLVED'} and (new != prior or corrections or owner or next_action):
                raise ValueError('Rejected/unresolved reviews cannot approve changes.')
            valid_refs = {r[0] for r in db.execute('SELECT id FROM sources WHERE task_id=?', (task_id,))}
            if not source_refs or not set(source_refs) <= valid_refs:
                raise ValueError('Select supporting sources from this task.')
            if decision_type in {'APPROVED', 'CORRECTED'}:
                required(approved_owner=owner, approved_next_action=next_action)
            if new == 'WORKAROUND_ACTIVE' and new != prior:
                for field in ('workaround_type', 'safety_approval_note', 'end_condition'):
                    required(**{field: corrections.get(field, '')})
            if new == 'REASSIGNED' and new != prior:
                for field in ('destination_context', 'return_condition', 'local_work_exhausted'):
                    required(**{field: corrections.get(field, '')})
            context = {'task': json.loads(db.execute('SELECT record FROM tasks WHERE id=?', (task_id,)).fetchone()[0]), 'blockers': [dict(blocker)]}
            for table in ('sources', 'decisions'):
                context[table] = [json.loads(r[0]) for r in db.execute(f'SELECT record FROM {table} WHERE task_id=? ORDER BY rowid', (task_id,))]
            if decision_type in {'APPROVED', 'CORRECTED'}:
                if 'material_fixture_status' in corrections:
                    context['blockers'][0]['material_fixture_status'] = corrections['material_fixture_status']
                context['decisions'].append({'decision_type': decision_type, 'corrected_values': corrections, 'source_refs': source_refs})
            flags = inspect_case(context)
            consequential = new != prior and new in {'WORKAROUND_ACTIVE', 'REASSIGNED', 'RESOLVED', 'COMPLETED', 'READY'}
            if consequential and any(f['blocking'] for f in flags):
                raise ValueError('Missing context or conflicting evidence requires UNDER_REVIEW and supervisor reconciliation.')
            if new != prior and new in {'RESOLVED', 'COMPLETED'} and unknown(context['blockers'][0]['material_fixture_status']):
                raise ValueError('Verify material status before resolution/completion; keep the case under review.')
            decision = ReviewDecision(actor, decision_type, corrections, owner, next_action,
                                      new if new != prior else '', rationale, now())
            record = asdict(decision)
            record['source_refs'] = list(source_refs)
            db.execute('INSERT INTO decisions VALUES (?, ?, ?)', (str(uuid4()), task_id, json.dumps(record)))
            blocker['workflow_state'] = new
            blocker['review_state'] = 'APPROVED' if decision_type == 'CORRECTED' else decision_type
            if 'material_fixture_status' in corrections:
                blocker['material_fixture_status'] = corrections['material_fixture_status']
            db.execute('UPDATE blockers SET record=? WHERE task_id=?', (json.dumps(blocker), task_id))
            self._audit(db, task_id, actor, 'REVIEW_' + decision_type, prior, new, list(source_refs))
            if new != prior:
                self._audit(db, task_id, actor, 'STATE_TRANSITION_APPROVED', prior, new, list(source_refs))
