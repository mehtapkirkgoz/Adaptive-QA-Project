"""Real KDF/session persistence, CSRF identity, expiry and login admission checks."""

from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from adaptive_qa.auth_store import AuthStore, AuthenticationError
from adaptive_qa.project_store import ProjectNotFound, ProjectStore


PASSWORD = 'Local test password 123!'


class AuthStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'accounts.db'
        self.now = 1000.0
        self.store = AuthStore(self.path, session_seconds=60, clock=lambda: self.now)
        self.alice = self.store.create_user('alice@example.test', PASSWORD)

    def login(self):
        return self.store.login('ALICE@example.test', PASSWORD)

    def test_passwords_use_distinct_salted_hashes_not_plaintext(self):
        self.store.create_user('bob@example.test', PASSWORD)
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute('SELECT salt, password_hash FROM dashboard_users').fetchall()
        self.assertEqual([len(row[0]) for row in rows], [16, 16])
        self.assertNotEqual(rows[0], rows[1])
        self.assertNotIn(PASSWORD.encode(), self.path.read_bytes())

    def test_login_issues_hidden_tokens_and_persists_only_digests(self):
        grant = self.login()
        self.assertEqual(grant.actor, self.alice)
        self.assertNotIn(grant.token.value, repr(grant))
        self.assertNotIn(grant.csrf_token.value, repr(grant))
        self.assertNotIn(grant.token.value.encode(), self.path.read_bytes())
        self.assertNotIn(grant.csrf_token.value.encode(), self.path.read_bytes())
        self.assertEqual(AuthStore(self.path, clock=lambda: self.now).actor_for_session(grant.token.value), self.alice)

    def test_unknown_and_wrong_password_have_same_error(self):
        errors = []
        for email in ('alice@example.test', 'unknown@example.test'):
            with self.assertRaises(AuthenticationError) as failure:
                self.store.login(email, 'Wrong test password!')
            errors.append(str(failure.exception))
        self.assertEqual(errors, ['Authentication failed.'] * 2)

    def test_failed_logins_consume_persistent_slots_before_hashing(self):
        for _ in range(5):
            with self.assertRaises(AuthenticationError):
                self.store.login('alice@example.test', 'Wrong test password!')
        restarted = AuthStore(self.path, clock=lambda: self.now)
        with patch('adaptive_qa.auth_store._derive', side_effect=AssertionError('Unexpected KDF')):
            with self.assertRaises(AuthenticationError):
                restarted.login('alice@example.test', PASSWORD)
        self.now += 60
        self.assertEqual(self.login().actor, self.alice)

    def test_expired_and_logged_out_sessions_cannot_authenticate(self):
        first = self.login()
        self.now = first.expires_at
        with self.assertRaises(AuthenticationError):
            self.store.actor_for_session(first.token.value)
        second = self.login()
        self.store.logout(second.token.value)
        self.store.logout(second.token.value)
        with self.assertRaises(AuthenticationError):
            self.store.actor_for_session(second.token.value)

    def test_csrf_token_is_bound_to_its_own_session(self):
        first, second = self.login(), self.login()
        self.assertNotEqual(first.token.value, second.token.value)
        self.assertEqual(self.store.verify_csrf(first.token.value, first.csrf_token.value), self.alice)
        with self.assertRaises(AuthenticationError):
            self.store.verify_csrf(first.token.value, second.csrf_token.value)

    def test_server_session_actor_enforces_project_owner(self):
        bob = self.store.create_user('bob@example.test', PASSWORD)
        project_store = ProjectStore(self.path)
        project = project_store.create(bob, 'Bob private project')
        actor = self.store.actor_for_session(self.login().token.value)
        with self.assertRaises(ProjectNotFound):
            project_store.get(actor, project.project_id)

    def test_duplicate_account_and_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_user('ALICE@example.test', PASSWORD)
        for email, password in (('invalid', PASSWORD), ('valid@example.test', 'short'),
                                ('valid@example.test', 'x' * 257), ('valid@example.test', '💻' * 3)):
            with self.assertRaises(ValueError):
                self.store.create_user(email, password)
        for token in ('', '../secret', 'a' * 42, True):
            with self.assertRaises(AuthenticationError):
                self.store.actor_for_session(token)

    def test_session_limit_revokes_oldest_grant(self):
        store = AuthStore(self.path, session_seconds=3600, clock=lambda: self.now)
        grants = []
        for _ in range(11):
            self.now += 13
            grants.append(store.login('alice@example.test', PASSWORD))
        with self.assertRaises(AuthenticationError):
            store.actor_for_session(grants[0].token.value)
        self.assertEqual(store.actor_for_session(grants[-1].token.value), self.alice)
