"""Licensed single-device primitives; customer startup is wired separately."""

from dataclasses import replace
from uuid import uuid4

from adaptive_qa.auth_store import AuthenticationError
from adaptive_qa.licensing import LicenseError
from adaptive_qa.local_free import LOCAL_ACTOR
from adaptive_qa.project_store import ProjectActor, ProjectStore, OwnedProject, _name


class LicensedLocalSessions:
    """One explicitly provisioned administrator authenticates the existing workspace."""
    local_licensed = True

    def __init__(self, auth, administrator):
        if not isinstance(administrator, ProjectActor) or administrator == LOCAL_ACTOR:
            raise ValueError('An explicitly provisioned administrator is required.')
        self.auth, self.administrator = auth, administrator
        self.database, self.session_seconds = auth.database, auth.session_seconds

    def _local(self, actor):
        if actor != self.administrator:
            raise AuthenticationError('Authentication failed.')
        return LOCAL_ACTOR

    def login(self, email, password):
        grant = self.auth.login(email, password)
        try:
            actor = self._local(grant.actor)
        except AuthenticationError:
            self.auth.logout(grant.token.value)
            raise
        return replace(grant, actor=actor)

    def actor_for_session(self, token):
        return self._local(self.auth.actor_for_session(token))

    def verify_csrf(self, token, csrf):
        return self._local(self.auth.verify_csrf(token, csrf))

    def logout(self, token):
        self.auth.logout(token)


class LicensedLocalProjects(ProjectStore):
    """Preserve the free workspace identity and enforce verified project capacity."""

    def __init__(self, database, licenses):
        self.licenses = licenses
        super().__init__(database)

    def require_license(self):
        claims = self.licenses.current()
        if claims is None:
            raise LicenseError('A valid local license is required.')
        return claims

    def create(self, actor, name):
        self._actor(actor); _name(name)
        if actor != LOCAL_ACTOR:
            raise ValueError('The licensed workspace requires its internal local identity.')
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            claims = self.require_license()
            count = connection.execute('SELECT count(*) FROM dashboard_projects').fetchone()[0]
            if claims.max_projects is not None and count >= claims.max_projects:
                raise LicenseError('Licensed local project capacity reached.')
            project = OwnedProject(uuid4().hex, actor.user_id, name)
            connection.execute('INSERT INTO dashboard_projects(project_id, owner_id, name) VALUES (?, ?, ?)',
                (project.project_id, project.owner_id, project.name))
            return project

    def admit_execution(self, connection, *, starting=False):
        claims = self.require_license()
        if starting:
            running = 0
            for table in ('dashboard_discovery_jobs', 'dashboard_test_runs', 'dashboard_interactive_jobs', 'dashboard_api_jobs'):
                if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                    running += connection.execute(f"SELECT count(*) FROM {table} WHERE status IN ('running', 'cancel_requested')").fetchone()[0]
            if running >= claims.max_concurrent_runs:
                raise LicenseError('Licensed concurrent execution capacity reached.')

    def execution_allowed(self):
        try:
            self.require_license()
            return True
        except LicenseError:
            return False


def create_licensed_app(database, auth, administrator, licenses, *, port=8767, ui_directory=None):
    """Internal local composition; customer CLI/worker packaging remains separate."""
    from adaptive_qa.web_app import create_app
    return create_app(LicensedLocalSessions(auth, administrator),
        projects=LicensedLocalProjects(database, licenses), port=port, ui_directory=ui_directory)
