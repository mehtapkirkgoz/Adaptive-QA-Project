"""Local credential and opaque server-session core; no HTTP endpoints yet."""

from contextlib import closing, contextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import sqlite3
import time
from threading import BoundedSemaphore
from uuid import uuid4

from adaptive_qa.project_store import ProjectActor
from adaptive_qa.secrets import SecretValue
from adaptive_qa.schema_migrations import validate_runtime_schema


_KDF_SLOTS = BoundedSemaphore(2)


def _email(value):
    if (not isinstance(value, str) or not value.isascii() or len(value) > 254
            or not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', value)):
        raise ValueError('A bounded ASCII email address is required.')
    return value.lower()


def _password(value):
    if not isinstance(value, str):
        raise ValueError('Password must be bounded text.')
    try:
        raw = value.encode('utf-8')
    except UnicodeError:
        raise ValueError('Password must be valid UTF-8 text.') from None
    if len(value) < 12 or len(raw) > 256:
        raise ValueError('Password must contain at least 12 characters and at most 256 UTF-8 bytes.')
    return raw


def _derive(password, salt):
    if not _KDF_SLOTS.acquire(timeout=1):
        raise AuthenticationError('Authentication failed.')
    try:
        return hashlib.scrypt(password, salt=salt, n=2**17, r=8, p=1, dklen=32, maxmem=256 * 1024 * 1024)
    finally:
        _KDF_SLOTS.release()


def _token_hash(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', value):
        raise AuthenticationError('Authentication failed.')
    return hashlib.sha256(value.encode('ascii')).digest()


class AuthenticationError(Exception):
    """Missing, invalid, expired, or throttled authentication has one outcome."""


@dataclass(frozen=True)
class SessionGrant:
    actor: ProjectActor
    token: SecretValue = field(repr=False)
    csrf_token: SecretValue = field(repr=False)
    expires_at: float


class AuthStore:
    def __init__(self, database: Path, *, session_seconds=3600, clock=time.time):
        if type(session_seconds) is not int or not 60 <= session_seconds <= 86400:
            raise ValueError('Session lifetime must be an integer in [60, 86400].')
        if not callable(clock):
            raise ValueError('A trusted server clock is required.')
        self.database = Path(database).resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.session_seconds, self.clock = session_seconds, clock
        with self._connection() as connection:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS dashboard_users (
                    user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
                    salt BLOB NOT NULL, password_hash BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS dashboard_sessions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_hash BLOB NOT NULL UNIQUE, csrf_hash BLOB NOT NULL,
                    user_id TEXT NOT NULL REFERENCES dashboard_users(user_id), expires_at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS dashboard_sessions_user ON dashboard_sessions(user_id, sequence);
                CREATE TABLE IF NOT EXISTS dashboard_login_admission (
                    identity_hash BLOB PRIMARY KEY, attempts INTEGER NOT NULL, window_start REAL NOT NULL);
            ''')

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(self.database, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            validate_runtime_schema(connection, 'auth.sqlite')
            connection.execute('PRAGMA foreign_keys=ON')
            with connection:
                yield connection

    def create_user(self, email, password):
        """Trusted local provisioning; not an open registration endpoint."""
        email, raw = _email(email), _password(password)
        salt = secrets.token_bytes(16)
        key = _derive(raw, salt)
        actor = ProjectActor(uuid4().hex)
        try:
            with self._connection() as connection:
                connection.execute('INSERT INTO dashboard_users VALUES (?, ?, ?, ?)',
                                   (actor.user_id, email, salt, key))
        except sqlite3.IntegrityError:
            raise ValueError('Account provisioning failed.') from None
        return actor

    def _admit(self, email, now):
        identity = hashlib.sha256(email.encode('ascii')).digest()
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('DELETE FROM dashboard_login_admission WHERE window_start<=?', (now - 60,))
            row = connection.execute('SELECT attempts FROM dashboard_login_admission WHERE identity_hash=?',
                                     (identity,)).fetchone()
            if row is not None and row['attempts'] >= 5:
                raise AuthenticationError('Authentication failed.')
            if row is None:
                count = connection.execute('SELECT count(*) FROM dashboard_login_admission').fetchone()[0]
                if count >= 10000:
                    raise AuthenticationError('Authentication failed.')
                connection.execute('INSERT INTO dashboard_login_admission VALUES (?, 1, ?)', (identity, now))
            else:
                connection.execute('UPDATE dashboard_login_admission SET attempts=attempts+1 WHERE identity_hash=?', (identity,))

    def login(self, email, password):
        email, raw = _email(email), _password(password)
        now = self.clock()
        self._admit(email, now)  # Separate committed transaction: failed checks consume admission.
        with self._connection() as connection:
            row = connection.execute('SELECT user_id, salt, password_hash FROM dashboard_users WHERE email=?', (email,)).fetchone()
        # Unknown accounts still perform the same expensive KDF operation.
        key = _derive(raw, row['salt'] if row is not None else bytes(16))
        expected = row['password_hash'] if row is not None else bytes(32)
        matched = hmac.compare_digest(key, expected)
        if row is None or not matched:
            raise AuthenticationError('Authentication failed.')
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expires_at = self.clock() + self.session_seconds
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('DELETE FROM dashboard_sessions WHERE expires_at<=?', (self.clock(),))
            connection.execute('INSERT INTO dashboard_sessions (token_hash, csrf_hash, user_id, expires_at) VALUES (?, ?, ?, ?)',
                               (_token_hash(token), _token_hash(csrf), row['user_id'], expires_at))
            connection.execute('DELETE FROM dashboard_sessions WHERE user_id=? AND sequence NOT IN '
                '(SELECT sequence FROM dashboard_sessions WHERE user_id=? ORDER BY sequence DESC LIMIT 10)',
                (row['user_id'], row['user_id']))
        return SessionGrant(ProjectActor(row['user_id']), SecretValue(token), SecretValue(csrf), expires_at)

    def _session(self, token):
        digest = _token_hash(token)
        with self._connection() as connection:
            row = connection.execute('SELECT user_id, csrf_hash FROM dashboard_sessions '
                'WHERE token_hash=? AND expires_at>?', (digest, self.clock())).fetchone()
        if row is None:
            raise AuthenticationError('Authentication failed.')
        return row

    def actor_for_session(self, token):
        return ProjectActor(self._session(token)['user_id'])

    def verify_csrf(self, token, csrf_token):
        row = self._session(token)
        if not hmac.compare_digest(row['csrf_hash'], _token_hash(csrf_token)):
            raise AuthenticationError('Authentication failed.')
        return ProjectActor(row['user_id'])

    def logout(self, token):
        digest = _token_hash(token)
        with self._connection() as connection:
            connection.execute('DELETE FROM dashboard_sessions WHERE token_hash=?', (digest,))
