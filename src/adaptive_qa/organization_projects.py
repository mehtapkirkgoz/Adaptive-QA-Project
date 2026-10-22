"""Membership-scoped projects, separate from historical personal projects."""

import json
from uuid import uuid4

from adaptive_qa.organization_admission import OrganizationCapacityExceeded
from adaptive_qa.organization_policy import OrganizationAction as Action
from adaptive_qa.organization_store import OrganizationStore
from adaptive_qa.project_store import OwnedProject, ProjectNotFound, _id, _name
from adaptive_qa.project_settings import validate_settings, public_settings


class OrganizationProjects:
    def __init__(self, organizations):
        if not isinstance(organizations, OrganizationStore):
            raise ValueError('A trusted organization store is required.')
        self.organizations = organizations
        with organizations.projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_organization_projects ('
                      'sequence INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT UNIQUE NOT NULL, '
                      'organization_id TEXT NOT NULL, name TEXT NOT NULL, settings_json TEXT)')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_organization_projects_scope '
                      'ON dashboard_organization_projects(organization_id, sequence)')

    def _row(self, c, actor, organization_id, project_id, action=Action.READ):
        _id(project_id)
        self.organizations._membership(c, actor, organization_id, action)
        row = c.execute('SELECT * FROM dashboard_organization_projects '
                        'WHERE project_id=? AND organization_id=?', (project_id, organization_id)).fetchone()
        if row is None:
            raise ProjectNotFound('Project not found.')
        return row

    @staticmethod
    def _public(row):
        return {'project_id': row['project_id'], 'organization_id': row['organization_id'], 'name': row['name']}

    def create(self, actor, organization_id, name):
        _name(name)
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.organizations._membership(c, actor, organization_id, Action.CONFIGURE)
            quota = c.execute('SELECT max_projects FROM dashboard_organizations WHERE organization_id=?',
                              (organization_id,)).fetchone()
            count = c.execute('SELECT count(*) FROM dashboard_organization_projects WHERE organization_id=?',
                              (organization_id,)).fetchone()[0]
            if quota is None or type(quota[0]) is not int or not 1 <= quota[0] <= 1000 or count >= quota[0]:
                raise OrganizationCapacityExceeded('Organization project capacity reached.')
            project_id = uuid4().hex
            c.execute('INSERT INTO dashboard_organization_projects (project_id, organization_id, name) VALUES (?, ?, ?)',
                      (project_id, organization_id, name))
            return self._public(self._row(c, actor, organization_id, project_id))

    def list(self, actor, organization_id):
        with self.organizations.projects._connection() as c:
            self.organizations._membership(c, actor, organization_id, Action.READ)
            rows = c.execute('SELECT * FROM dashboard_organization_projects WHERE organization_id=? '
                             'ORDER BY sequence DESC LIMIT 1000', (organization_id,)).fetchall()
            return [self._public(row) for row in rows]

    def get(self, actor, organization_id, project_id):
        with self.organizations.projects._connection() as c:
            return self._public(self._row(c, actor, organization_id, project_id))

    def rename(self, actor, organization_id, project_id, name):
        _name(name)
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self._row(c, actor, organization_id, project_id, Action.CONFIGURE)
            c.execute('UPDATE dashboard_organization_projects SET name=? WHERE project_id=? AND organization_id=?',
                      (name, project_id, organization_id))
            return self._public(self._row(c, actor, organization_id, project_id))

    def configuration(self, actor, organization_id, project_id):
        with self.organizations.projects._connection() as c:
            row = self._row(c, actor, organization_id, project_id)
            project = OwnedProject(project_id, organization_id, row['name'])
            return public_settings(project, None if row['settings_json'] is None else json.loads(row['settings_json']))

    def save_configuration(self, actor, organization_id, project_id, data):
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = self._row(c, actor, organization_id, project_id, Action.CONFIGURE)
            project = OwnedProject(project_id, organization_id, row['name'])
            settings = validate_settings(project, data)
            c.execute('UPDATE dashboard_organization_projects SET settings_json=? '
                      'WHERE project_id=? AND organization_id=?',
                      (json.dumps(settings, allow_nan=False), project_id, organization_id))
            return public_settings(project, settings)
