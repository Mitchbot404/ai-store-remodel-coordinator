"""Synthetic scenario fixtures, explicitly loaded into a NEW demo database only."""
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from .auth import Auth, Role
from .store import Store

SCENARIOS = [
    ('S1', 1.5, 'DELAYED', 'Fixture truck 90 minutes late; other approved tasks may continue.'),
    ('S2', 72, 'DELAYED', 'Fixture shipment delayed three days; temporary layout and later recovery require review.'),
    ('S3', 4, 'DAMAGED', 'Fixture significantly damaged or outdated; no software safety determination.'),
    ('S4', 5, 'MISSING', 'Contradictory shipment observations require supervisor reconciliation.'),
    ('S5', 6, 'NO_LOCAL_WORK', 'No productive local work remains; supervisor may consider reassignment and return plan.'),
]


def build_demo(path, password, at=None):
    from pathlib import Path
    path = Path(path)
    if path.exists():
        raise ValueError('Demo requires a new database path; existing data is never overwritten.')
    path.parent.mkdir(parents=True, exist_ok=True)
    at = at or datetime.now(timezone.utc)
    auth = Auth(path)
    for role in Role:
        auth.provision(role.name, password, role)
    store = Store(path, auth.login('ASSOCIATE', password))
    ids = {}
    for name, hours, status, note in SCENARIOS:
        target = at + timedelta(hours=12) if name == 'S1' else at - timedelta(hours=1)
        key = store.create_task('SYN-' + name, 'Demo area', name + ': ' + note, target.isoformat(), ['Synthetic fixture'], 'ASSOCIATE', source_note=note)
        # Backdated synthetic report fixture, not an operational timestamp editing API.
        with patch('coordinator.store.now', return_value=(at - timedelta(hours=hours)).isoformat()):
            store.report_blocker(key, 'Synthetic fixture exception', note, 'ASSOCIATE', 'Synthetic scenario', note, status)
        store.add_observation(key, 'Synthetic scenario', note, status)
        if name == 'S4':
            store.add_observation(key, 'Synthetic support update', 'A different synthetic observer reports arrival.', 'ARRIVED')
        ids[name] = key
    auth.logout(store.token)
    return ids
