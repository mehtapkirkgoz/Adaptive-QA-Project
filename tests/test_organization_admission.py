"""Real concurrent SQLite reservations cannot oversubscribe organization quotas."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.organization_admission import OrganizationAdmission, OrganizationCapacityExceeded
from adaptive_qa.organization_policy import OrganizationQuota, OrganizationRole as Role
from adaptive_qa.organization_store import OrganizationStore, OrganizationNotFound
from adaptive_qa.project_store import ProjectStore, ProjectActor


class OrganizationAdmissionTests(unittest.TestCase):
    def test_usage_snapshot_is_scoped_and_counts_cancelled_admissions(self):
        first = self.ledger.reserve(self.actor,self.org)
        second = self.ledger.reserve(self.actor,self.org)
        token = self.ledger.claim(self.actor,self.org,first)
        self.assertEqual(self.ledger.usage(self.actor,self.org),
                         {'utc_day':1,'pending_runs':1,'active_runs':1,'daily_admitted_runs':2})
        self.ledger.cancel_pending(self.actor,self.org,second)
        self.ledger.finish(self.actor,self.org,first,token)
        self.assertEqual(self.ledger.usage(self.actor,self.org),
                         {'utc_day':1,'pending_runs':0,'active_runs':0,'daily_admitted_runs':2})
        with self.assertRaises(OrganizationNotFound):
            self.ledger.usage(self.other,self.org)
        self.assertEqual(self.ledger.usage(self.other,self.second)['daily_admitted_runs'],0)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.organizations = OrganizationStore(ProjectStore(Path(self.temp.name) / 'projects.sqlite'))
        self.actor = ProjectActor('a' * 32)
        self.other = ProjectActor('b' * 32)
        self.org = self.organizations.create(self.actor, 'One', quota=OrganizationQuota(2, 2, 1, 3))
        self.second = self.organizations.create(self.other, 'Two')
        self.now = 86400.0
        self.ledger = OrganizationAdmission(self.organizations, clock=lambda: self.now)

    def test_parallel_reservations_enforce_pending_limit(self):
        def reserve(_):
            try:
                return self.ledger.reserve(self.actor, self.org)
            except OrganizationCapacityExceeded:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            admitted = [value for value in pool.map(reserve, range(8)) if value]
        self.assertEqual(len(admitted), 2)
        self.assertEqual(len(set(admitted)), 2)

    def test_parallel_claims_enforce_active_limit_and_reject_stale_tokens(self):
        ids = [self.ledger.reserve(self.actor, self.org) for _ in range(2)]
        def claim(reservation):
            try:
                return reservation, self.ledger.claim(self.actor, self.org, reservation)
            except OrganizationCapacityExceeded:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed = [value for value in pool.map(claim, ids) if value]
        self.assertEqual(len(claimed), 1)
        reservation, token = claimed[0]
        with self.assertRaises(OrganizationNotFound):
            self.ledger.finish(self.actor, self.org, reservation, 'f' * 32)
        self.assertEqual(self.ledger.finish(self.actor, self.org, reservation, token), 'finished')
        with self.assertRaises(OrganizationNotFound):
            self.ledger.finish(self.actor, self.org, reservation, token)
        remaining = next(value for value in ids if value != reservation)
        self.assertTrue(self.ledger.claim(self.actor, self.org, remaining))

    def test_cancellation_frees_pending_but_does_not_refund_daily_usage(self):
        for _ in range(3):
            reservation = self.ledger.reserve(self.actor, self.org)
            self.ledger.cancel_pending(self.actor, self.org, reservation)
        with self.assertRaises(OrganizationCapacityExceeded):
            self.ledger.reserve(self.actor, self.org)
        self.now += 86400
        self.assertTrue(self.ledger.reserve(self.actor, self.org))

    def test_other_organization_and_user_cannot_claim_or_release(self):
        reservation = self.ledger.reserve(self.actor, self.org)
        with self.assertRaises(OrganizationNotFound):
            self.ledger.claim(self.other, self.second, reservation)
        token = self.ledger.claim(self.actor, self.org, reservation)
        with self.assertRaises(OrganizationNotFound):
            self.ledger.finish(self.other, self.second, reservation, token)
        self.assertEqual(self.ledger.finish(self.actor, self.org, reservation, token), 'finished')

    def test_revoked_members_cannot_claim_and_active_release_is_cancelled(self):
        member = ProjectActor('c' * 32)
        self.organizations.set_member(self.actor, self.org, member.user_id, Role.MEMBER)
        pending = self.ledger.reserve(member, self.org)
        active = self.ledger.reserve(member, self.org)
        token = self.ledger.claim(member, self.org, active)
        self.organizations.remove_member(self.actor, self.org, member.user_id)
        with self.assertRaises(OrganizationNotFound):
            self.ledger.claim(member, self.org, pending)
        self.assertEqual(self.ledger.finish(member, self.org, active, token), 'cancelled')
        self.ledger.cancel_pending(member, self.org, pending)

    def test_viewer_and_invalid_clock_cannot_create_reservations(self):
        self.organizations.set_member(self.actor, self.org, self.other.user_id, Role.VIEWER)
        with self.assertRaises(OrganizationNotFound):
            self.ledger.reserve(self.other, self.org)
        for value in (True, -1, float('nan'), float('inf'), '1'):
            self.now = value
            with self.assertRaises(ValueError):
                self.ledger.reserve(self.actor, self.org)


if __name__ == '__main__':
    unittest.main()
