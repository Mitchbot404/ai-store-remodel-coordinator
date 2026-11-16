"""Transactional local intake; no operational approval interface exists yet."""
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from .models import AuditEvent, BlockerRecord, SourceReference, TaskRecord, WorkflowState


def now():
    return datetime.now(timezone.utc).isoformat()


def required(**values):
    for key, value in values.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{key} is required.')


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS blockers (id TEXT PRIMARY KEY, task_id TEXT NOT NULL UNIQUE REFERENCES tasks(id), record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audits (id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), record TEXT NOT NULL);
            ''')

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
        required(blocker_type=blocker_type, observed_condition=observed_condition, reporter_id=reporter_id,
                 source_type=source_type, source_note=source_note)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM tasks WHERE id=?', (task_id,)).fetchone():
                raise ValueError('Task does not exist.')
            if db.execute('SELECT 1 FROM blockers WHERE task_id=?', (task_id,)).fetchone():
                raise ValueError('This task already has a blocker. Phase 1 supports one blocker per task.')
            ref = self._source(db, task_id, reporter_id, source_type, source_note)
            blocker = BlockerRecord(str(uuid4()), task_id, blocker_type, observed_condition,
                                    material_fixture_status.strip() or 'UNKNOWN', now(), reporter_id,
                                    [ref], WorkflowState.BLOCKED, 'UNRESOLVED')
            db.execute('INSERT INTO blockers VALUES (?, ?, ?)', (blocker.blocker_id, task_id, json.dumps(asdict(blocker))))
            self._audit(db, task_id, reporter_id, 'BLOCKER_REPORTED', 'READY', 'BLOCKED', [ref])
        return blocker.blocker_id

    def tasks(self):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT record FROM tasks ORDER BY rowid')]

    def case(self, task_id):
        with self.connect() as db:
            row = db.execute('SELECT record FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row is None:
                raise ValueError('Task does not exist.')
            result = {'task': json.loads(row[0])}
            for table in ('blockers', 'sources', 'audits'):
                result[table] = [json.loads(r[0]) for r in db.execute(f'SELECT record FROM {table} WHERE task_id=? ORDER BY rowid', (task_id,))]
            result['workflow_state'] = result['blockers'][0]['workflow_state'] if result['blockers'] else 'READY'
            return result

    def transition(self, *args, **kwargs):
        raise PermissionError('State changes beyond blocker intake require Phase 2 authenticated supervisor review.')
