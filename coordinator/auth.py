"""Local prototype credentials and expiring opaque sessions; no default passwords."""
import hashlib
import hmac
import secrets
import sqlite3
import time
from enum import Enum


class Role(str, Enum):
    ASSOCIATE = 'Associate'
    SUPPORT = 'Stocking/Support'
    SUPERVISOR = 'Supervisor/Manager'
    TECHNICAL = 'Technical/System Owner'


class Auth:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT NOT NULL, salt TEXT NOT NULL, digest TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL);
            ''')

    def provision(self, username, password, role):
        # Local administrative CLI only, never exposed as a user action.
        role = Role(role)
        if not username.strip() or len(password) < 12:
            raise ValueError('Username and a password of at least 12 characters are required.')
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (username, role.value, salt, digest))

    def login(self, username, password):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT salt, digest FROM users WHERE username=?', (username,)).fetchone()
            salt, expected = row if row else ('invalid-user', '0' * 64)
            actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
            if not hmac.compare_digest(actual, expected):
                raise PermissionError('Invalid credentials.')
            token = secrets.token_urlsafe(32)
            db.execute('INSERT INTO sessions VALUES (?, ?, ?)', (self._hash(token), username, time.time() + 3600))
            return token

    @staticmethod
    def _hash(token):
        return hashlib.sha256((token or '').encode()).hexdigest()

    def identity(self, token):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT u.username, u.role FROM sessions s JOIN users u ON u.username=s.username WHERE s.digest=? AND s.expires>?',
                             (self._hash(token), time.time())).fetchone()
        if not row:
            raise PermissionError('Please sign in again.')
        return row[0], Role(row[1])

    def logout(self, token):
        with sqlite3.connect(self.path) as db:
            db.execute('DELETE FROM sessions WHERE digest=?', (self._hash(token),))
