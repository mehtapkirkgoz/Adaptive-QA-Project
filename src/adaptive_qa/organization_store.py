"""Transactional organization membership; existing projects remain owner-scoped."""

from uuid import uuid4

from adaptive_qa.organization_policy import (
    OrganizationAction as Action, OrganizationRole as Role,
    OrganizationMembership, OrganizationQuota, permits,
)
from adaptive_qa.project_store import ProjectStore, _id, _name


class OrganizationNotFound(LookupError):
    """Absent organizations and missing privileges have the same outcome."""


class OrganizationStore:
    """Uses the existing projects database and its supported-schema gate.

    Only trusted server identities may call this internal store. No HTTP
    membership claims or access to historical owner projects are introduced.
    """
    def __init__(self, projects):
        if not isinstance(projects, ProjectStore):
            raise ValueError('A trusted project store is required.')
        self.projects = projects
        with projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_organizations ('
                      'organization_id TEXT PRIMARY KEY, name TEXT NOT NULL, '
                      'max_projects INTEGER NOT NULL, max_pending_runs INTEGER NOT NULL, '
                      'max_active_runs INTEGER NOT NULL, max_daily_runs INTEGER NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_organization_members ('
                      'organization_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL, '
                      'PRIMARY KEY (organization_id, user_id))')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_members_user '
                      'ON dashboard_organization_members(user_id, organization_id)')

    @staticmethod
    def _membership(c, actor, organization_id, action):
        ProjectStore._actor(actor)
        _id(organization_id)
        row = c.execute('SELECT role FROM dashboard_organization_members '
                        'WHERE organization_id=? AND user_id=?',
                        (organization_id, actor.user_id)).fetchone()
        try:
            member = None if row is None else OrganizationMembership(organization_id, actor.user_id, Role(row['role']))
        except ValueError:
            raise OrganizationNotFound('Organization not found.') from None
        if not permits(actor, member, organization_id, action):
            raise OrganizationNotFound('Organization not found.')
        return member

    def create(self, actor, name, *, quota=None):
        ProjectStore._actor(actor)
        _name(name)
        quota = OrganizationQuota() if quota is None else quota
        if not isinstance(quota, OrganizationQuota):
            raise ValueError('A typed organization quota is required.')
        organization_id = uuid4().hex
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            count = c.execute("SELECT count(*) FROM dashboard_organization_members WHERE user_id=? AND role='owner'", (actor.user_id,)).fetchone()[0]
            if count >= 20:
                raise ValueError('Local organization creation capacity reached.')
            c.execute('INSERT INTO dashboard_organizations VALUES (?, ?, ?, ?, ?, ?)',
                      (organization_id, name, quota.max_projects, quota.max_pending_runs,
                       quota.max_active_runs, quota.max_daily_runs))
            c.execute('INSERT INTO dashboard_organization_members VALUES (?, ?, ?)',
                      (organization_id, actor.user_id, Role.OWNER.value))
        return organization_id

    def membership(self, actor, organization_id):
        with self.projects._connection() as c:
            return self._membership(c, actor, organization_id, Action.READ)

    def list(self, actor):
        ProjectStore._actor(actor)
        with self.projects._connection() as c:
            rows = c.execute('SELECT o.organization_id, o.name, m.role FROM dashboard_organizations o '
                            'JOIN dashboard_organization_members m ON m.organization_id=o.organization_id '
                            'WHERE m.user_id=? ORDER BY o.organization_id LIMIT 100', (actor.user_id,)).fetchall()
            return [{'organization_id': row['organization_id'], 'name': row['name'],
                     'role': Role(row['role']).value} for row in rows]

    def quota(self, actor, organization_id):
        with self.projects._connection() as c:
            self._membership(c, actor, organization_id, Action.READ)
            row = c.execute('SELECT * FROM dashboard_organizations WHERE organization_id=?',
                            (organization_id,)).fetchone()
            if row is None:
                raise OrganizationNotFound('Organization not found.')
            return OrganizationQuota(*(row[k] for k in ('max_projects', 'max_pending_runs',
                                                        'max_active_runs', 'max_daily_runs')))

    def members(self, actor, organization_id):
        with self.projects._connection() as c:
            self._membership(c, actor, organization_id, Action.MANAGE_MEMBERS)
            return [{'user_id':row['user_id'],'role':Role(row['role']).value} for row in c.execute(
                'SELECT user_id,role FROM dashboard_organization_members WHERE organization_id=? ORDER BY user_id LIMIT 100', (organization_id,))]

    def set_member(self, actor, organization_id, user_id, role):
        """Owner/admin may assign non-owner roles; admins cannot create peers."""
        _id(user_id)
        if not isinstance(role, Role) or role is Role.OWNER:
            raise ValueError('A non-owner typed role is required; ownership transfer is not enabled.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            caller = self._membership(c, actor, organization_id, Action.MANAGE_MEMBERS)
            target = c.execute('SELECT role FROM dashboard_organization_members '
                               'WHERE organization_id=? AND user_id=?', (organization_id, user_id)).fetchone()
            if target is None and c.execute('SELECT count(*) FROM dashboard_organization_members WHERE organization_id=?', (organization_id,)).fetchone()[0] >= 100:
                raise ValueError('Local organization membership capacity reached.')
            if (target and target['role'] == Role.OWNER.value) or (
                    caller.role is Role.ADMIN and (role is Role.ADMIN or
                        (target and target['role'] == Role.ADMIN.value))):
                raise OrganizationNotFound('Organization not found.')
            c.execute('INSERT INTO dashboard_organization_members VALUES (?, ?, ?) '
                      'ON CONFLICT(organization_id, user_id) DO UPDATE SET role=excluded.role',
                      (organization_id, user_id, role.value))

    def remove_member(self, actor, organization_id, user_id):
        _id(user_id)
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            caller = self._membership(c, actor, organization_id, Action.MANAGE_MEMBERS)
            target = c.execute('SELECT role FROM dashboard_organization_members '
                               'WHERE organization_id=? AND user_id=?', (organization_id, user_id)).fetchone()
            if target is None or target['role'] == Role.OWNER.value or (
                    caller.role is Role.ADMIN and target['role'] == Role.ADMIN.value):
                raise OrganizationNotFound('Organization not found.')
            c.execute('DELETE FROM dashboard_organization_members WHERE organization_id=? AND user_id=?',
                      (organization_id, user_id))
