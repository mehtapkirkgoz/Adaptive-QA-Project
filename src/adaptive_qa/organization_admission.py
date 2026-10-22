"""Atomic local admission ledger; reservations never start test execution."""

import math
import time
from uuid import uuid4

from adaptive_qa.organization_policy import OrganizationAction as Action, OrganizationQuota
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.project_store import _id


class OrganizationCapacityExceeded(ValueError):
    """No admission was recorded because an organization limit was reached."""


class OrganizationAdmission:
    def __init__(self, organizations, *, clock=time.time):
        if not isinstance(organizations, OrganizationStore) or not callable(clock):
            raise ValueError('A trusted organization store and clock are required.')
        self.organizations = organizations
        self.clock = clock
        with organizations.projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_organization_admissions ('
                      'reservation_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, '
                      'user_id TEXT NOT NULL, utc_day INTEGER NOT NULL, '
                      'status TEXT NOT NULL, claim_token TEXT)')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_admission_status '
                      'ON dashboard_organization_admissions(organization_id, status)')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_admission_day '
                      'ON dashboard_organization_admissions(organization_id, utc_day)')

    def _day(self):
        value = self.clock()
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 253402300799:
            raise ValueError('A finite nonnegative UTC timestamp is required.')
        return int(value // 86400)

    def _quota(self, c, organization_id):
        row = c.execute('SELECT max_projects, max_pending_runs, max_active_runs, max_daily_runs '
                        'FROM dashboard_organizations WHERE organization_id=?', (organization_id,)).fetchone()
        if row is None:
            raise OrganizationNotFound('Organization not found.')
        return OrganizationQuota(*tuple(row))

    def usage(self, actor, organization_id):
        """Scoped advisory snapshot; only transactional reserve/claim admit work."""
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN')
            self.organizations._membership(c, actor, organization_id, Action.READ)
            day = self._day()
            pending = c.execute("SELECT count(*) FROM dashboard_organization_admissions WHERE organization_id=? AND status='pending'", (organization_id,)).fetchone()[0]
            active = c.execute("SELECT count(*) FROM dashboard_organization_admissions WHERE organization_id=? AND status='active'", (organization_id,)).fetchone()[0]
            daily = c.execute('SELECT count(*) FROM dashboard_organization_admissions WHERE organization_id=? AND utc_day=?', (organization_id,day)).fetchone()[0]
            return {'utc_day':day,'pending_runs':pending,'active_runs':active,'daily_admitted_runs':daily}

    def reserve(self, actor, organization_id):
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            return self._reserve(c, actor, organization_id)

    def _reserve(self, c, actor, organization_id):
        """Trusted queue composition; caller must hold BEGIN IMMEDIATE."""
        if not c.in_transaction:
            raise ValueError('Admission requires an existing write transaction.')
        day = self._day()
        self.organizations._membership(c, actor, organization_id, Action.EXECUTE)
        quota = self._quota(c, organization_id)
        pending = c.execute('SELECT count(*) FROM dashboard_organization_admissions '
                            "WHERE organization_id=? AND status='pending'", (organization_id,)).fetchone()[0]
        daily = c.execute('SELECT count(*) FROM dashboard_organization_admissions '
                          'WHERE organization_id=? AND utc_day=?', (organization_id, day)).fetchone()[0]
        if not quota.admits('pending_runs', pending) or not quota.admits('daily_runs', daily):
            raise OrganizationCapacityExceeded('Organization admission capacity reached.')
        reservation_id = uuid4().hex
        c.execute('INSERT INTO dashboard_organization_admissions VALUES (?, ?, ?, ?, ?, NULL)',
                  (reservation_id, organization_id, actor.user_id, day, 'pending'))
        return reservation_id

    def claim(self, actor, organization_id, reservation_id):
        _id(reservation_id)
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.organizations._membership(c, actor, organization_id, Action.EXECUTE)
            quota = self._quota(c, organization_id)
            row = c.execute('SELECT status FROM dashboard_organization_admissions '
                            'WHERE reservation_id=? AND organization_id=? AND user_id=?',
                            (reservation_id, organization_id, actor.user_id)).fetchone()
            if row is None or row['status'] != 'pending':
                raise OrganizationNotFound('Reservation not found.')
            active = c.execute('SELECT count(*) FROM dashboard_organization_admissions '
                               "WHERE organization_id=? AND status='active'", (organization_id,)).fetchone()[0]
            if not quota.admits('active_runs', active):
                raise OrganizationCapacityExceeded('Organization execution capacity reached.')
            token = uuid4().hex
            c.execute("UPDATE dashboard_organization_admissions SET status='active', claim_token=? "
                      'WHERE reservation_id=?', (token, reservation_id))
        return token

    def finish(self, actor, organization_id, reservation_id, claim_token):
        """Release only the exact owned claim; no test result is published here."""
        self.organizations.projects._actor(actor)
        for value in (organization_id, reservation_id, claim_token):
            _id(value)
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            try:
                self.organizations._membership(c, actor, organization_id, Action.EXECUTE)
                status = 'finished'
            except OrganizationNotFound:
                status = 'cancelled'
            changed = c.execute('UPDATE dashboard_organization_admissions SET status=?, claim_token=NULL '
                                "WHERE reservation_id=? AND organization_id=? AND user_id=? AND status='active' "
                                'AND claim_token=?', (status, reservation_id, organization_id, actor.user_id,
                                                     claim_token)).rowcount
            if changed != 1:
                raise OrganizationNotFound('Reservation not found.')
        return status

    def cancel_pending(self, actor, organization_id, reservation_id):
        self.organizations.projects._actor(actor)
        _id(organization_id)
        _id(reservation_id)
        with self.organizations.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            changed = c.execute("UPDATE dashboard_organization_admissions SET status='cancelled' "
                                "WHERE reservation_id=? AND organization_id=? AND user_id=? AND status='pending'",
                                (reservation_id, organization_id, actor.user_id)).rowcount
            if changed != 1:
                raise OrganizationNotFound('Reservation not found.')
