"""Opt-in account-free loopback workspace; no network licensing or telemetry."""

from dataclasses import dataclass
from pathlib import Path
import secrets
from threading import Lock
import time
from uuid import uuid4

from adaptive_qa.auth_store import AuthenticationError
from adaptive_qa.project_store import ProjectActor, ProjectStore, OwnedProject, _name
from adaptive_qa.secrets import SecretValue

LOCAL_ACTOR = ProjectActor('f'*32)


@dataclass(frozen=True)
class LocalGrant:
    actor: ProjectActor
    token: SecretValue
    csrf_token: SecretValue


class LocalFreeSessions:
    """Bounded ephemeral browser sessions, not registered users or persisted credentials."""
    local_free = True
    session_seconds = 8*60*60

    def __init__(self, database, *, clock=time.time):
        self.database = Path(database)
        self.clock, self.lock, self.sessions = clock, Lock(), {}

    def bootstrap(self, token=None):
        with self.lock:
            now = self.clock()
            self.sessions = {key: value for key, value in self.sessions.items() if value[1] > now}
            if token in self.sessions:
                csrf = self.sessions[token][0]
            else:
                if len(self.sessions) >= 16:
                    self.sessions.pop(next(iter(self.sessions)))
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                self.sessions[token] = (csrf, now+self.session_seconds)
            return LocalGrant(LOCAL_ACTOR, SecretValue(token), SecretValue(csrf))

    def actor_for_session(self, token):
        with self.lock:
            entry = self.sessions.get(token)
            if not entry or entry[1] <= self.clock():
                raise AuthenticationError('Local session expired.')
            return LOCAL_ACTOR

    def verify_csrf(self, token, csrf):
        self.actor_for_session(token)
        with self.lock:
            entry = self.sessions.get(token)
            if not entry or entry[1] <= self.clock() or not isinstance(csrf, str) or not secrets.compare_digest(entry[0], csrf):
                raise AuthenticationError('Invalid local session.')
        return LOCAL_ACTOR

    def logout(self, token):
        with self.lock:
            self.sessions.pop(token, None)

    def login(self, *args):
        raise AuthenticationError('This edition does not use accounts.')


class LocalFreeProjects(ProjectStore):
    def create(self, actor, name):
        self._actor(actor); _name(name)
        if actor != LOCAL_ACTOR:
            raise ValueError('The free workspace requires its internal local identity.')
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            if connection.execute('SELECT 1 FROM dashboard_projects WHERE owner_id=?', (actor.user_id,)).fetchone():
                raise ValueError('The free edition supports one active local project.')
            project = OwnedProject(uuid4().hex, actor.user_id, name)
            connection.execute('INSERT INTO dashboard_projects (project_id, owner_id, name) VALUES (?, ?, ?)',
                               (project.project_id, actor.user_id, project.name))
            return project


def create_free_app(database, *, port=8766, ui_directory=None):
    license_path = Path(database).absolute().with_name('license.sqlite')
    if license_path.exists() or license_path.is_symlink():
        raise ValueError('This workspace contains licensing state; open it with the licensed local commands.')
    from adaptive_qa.web_app import create_app
    projects = LocalFreeProjects(database)
    return create_app(LocalFreeSessions(database), projects=projects, port=port, ui_directory=ui_directory)
