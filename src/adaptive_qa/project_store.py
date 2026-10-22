"""Owner-scoped project persistence; authenticated HTTP sessions remain separate."""

from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
import re
import json
import sqlite3
from uuid import uuid4

from adaptive_qa.project_settings import validate_settings, public_settings
from adaptive_qa.schema_migrations import validate_runtime_schema

def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise ValueError('Identity must be a lowercase UUID hex string.')


def _name(value):
    if (not isinstance(value, str) or not value.strip() or len(value) > 100
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError('Project name must be bounded non-empty text without controls.')


@dataclass(frozen=True)
class ProjectActor:
    """Trusted internal identity; HTTP callers must never supply this directly."""
    user_id: str

    def __post_init__(self):
        _id(self.user_id)


@dataclass(frozen=True)
class OwnedProject:
    project_id: str
    owner_id: str
    name: str

    def __post_init__(self):
        _id(self.project_id)
        _id(self.owner_id)
        _name(self.name)


class ProjectNotFound(LookupError):
    """Missing and other-owner projects have the same external outcome."""


class ProjectStore:
    """Separate project database; no queue mutation or target execution."""
    def __init__(self, database: Path):
        self.database = Path(database).resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_projects ('
                'sequence INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL UNIQUE, '
                'owner_id TEXT NOT NULL, name TEXT NOT NULL)')
            connection.execute('CREATE INDEX IF NOT EXISTS dashboard_projects_owner '
                               'ON dashboard_projects(owner_id, sequence)')
            connection.execute('CREATE TABLE IF NOT EXISTS dashboard_project_settings ('
                               'project_id TEXT PRIMARY KEY, settings_json TEXT NOT NULL)')

    @contextmanager
    def _connection(self):
        with closing(sqlite3.connect(self.database, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            validate_runtime_schema(connection, 'projects.sqlite')
            with connection:
                yield connection

    @staticmethod
    def _actor(actor):
        if not isinstance(actor, ProjectActor):
            raise ValueError('A trusted typed project actor is required.')

    @staticmethod
    def _project(row):
        return OwnedProject(row['project_id'], row['owner_id'], row['name'])

    def create(self, actor, name):
        self._actor(actor)
        _name(name)
        project = OwnedProject(uuid4().hex, actor.user_id, name)
        with self._connection() as connection:
            connection.execute('INSERT INTO dashboard_projects (project_id, owner_id, name) VALUES (?, ?, ?)',
                               (project.project_id, project.owner_id, project.name))
        return project

    def get(self, actor, project_id):
        self._actor(actor)
        _id(project_id)
        with self._connection() as connection:
            row = connection.execute('SELECT project_id, owner_id, name FROM dashboard_projects '
                'WHERE project_id=? AND owner_id=?', (project_id, actor.user_id)).fetchone()
        if row is None:
            raise ProjectNotFound('Project not found.')
        return self._project(row)

    def list(self, actor, *, limit=20, offset=0):
        self._actor(actor)
        if (type(limit) is not int or not 1 <= limit <= 100
                or type(offset) is not int or not 0 <= offset <= 100000):
            raise ValueError('Pagination must use bounded nonnegative integers and a positive limit.')
        with self._connection() as connection:
            rows = connection.execute('SELECT project_id, owner_id, name FROM dashboard_projects '
                'WHERE owner_id=? ORDER BY sequence DESC LIMIT ? OFFSET ?',
                (actor.user_id, limit, offset)).fetchall()
        return tuple(self._project(row) for row in rows)

    def rename(self, actor, project_id, name):
        self._actor(actor)
        _id(project_id)
        _name(name)
        with self._connection() as connection:
            cursor = connection.execute('UPDATE dashboard_projects SET name=? WHERE project_id=? AND owner_id=?',
                                        (name, project_id, actor.user_id))
            if cursor.rowcount != 1:
                raise ProjectNotFound('Project not found.')
        return OwnedProject(project_id, actor.user_id, name)

    def configuration(self, actor, project_id):
        self._actor(actor)
        _id(project_id)
        with self._connection() as connection:
            row = connection.execute('SELECT p.project_id, p.owner_id, p.name, s.settings_json '
                'FROM dashboard_projects p LEFT JOIN dashboard_project_settings s ON p.project_id=s.project_id '
                'WHERE p.project_id=? AND p.owner_id=?', (project_id, actor.user_id)).fetchone()
        if row is None:
            raise ProjectNotFound('Project not found.')
        data = json.loads(row['settings_json']) if row['settings_json'] is not None else None
        return public_settings(self._project(row), data)

    def save_configuration(self, actor, project_id, data):
        project = self.get(actor, project_id)
        validated = validate_settings(project, data)
        with self._connection() as connection:
            connection.execute('INSERT INTO dashboard_project_settings (project_id, settings_json) '
                'SELECT project_id, ? FROM dashboard_projects WHERE project_id=? AND owner_id=? '
                'ON CONFLICT(project_id) DO UPDATE SET settings_json=excluded.settings_json',
                (json.dumps(validated, allow_nan=False), project_id, actor.user_id))
        return public_settings(project, validated)
