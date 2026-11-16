"""Run locally to provision individually assigned prototype accounts."""
import argparse
import getpass
from pathlib import Path
from coordinator.auth import Auth, Role

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('role', choices=[r.value for r in Role])
    parser.add_argument('--database', default=str(Path(__file__).parent / 'data' / 'prototype.sqlite3'))
    args = parser.parse_args()
    password = getpass.getpass('Password (12+ characters): ')
    if password != getpass.getpass('Confirm password: '):
        raise SystemExit('Passwords do not match.')
    Path(args.database).parent.mkdir(parents=True, exist_ok=True)
    Auth(args.database).provision(args.username, password, args.role)
    print('Account created.')
