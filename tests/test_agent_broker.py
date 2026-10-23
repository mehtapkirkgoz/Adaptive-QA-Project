"""Scoped leases preserve quota, ordered outcomes and replay/cancellation rules."""

import unittest
import test_organization_runs as run_fixtures
from adaptive_qa.agent_registry import AgentRegistry,AgentAuthenticationError
from adaptive_qa.agent_broker import AgentBroker
from png_fixture import png_bytes


class AgentBrokerTests(unittest.TestCase):
    def setUp(self):
        self.f = run_fixtures.OrganizationRunTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.registry = AgentRegistry(self.f.scoped,clock=lambda:self.f.now)
        self.grant = self.registry.issue(self.f.owner,self.f.org,self.f.project)
        self.identity = self.registry.authenticate(self.grant.agent_id,self.grant.token.value,1)
        self.broker = AgentBroker(self.registry,self.f.queue)

    def test_claim_is_project_bound_and_private_worker_token_never_leaves_broker(self):
        self.f.submit()
        lease = self.broker.claim(self.identity)
        self.assertEqual(lease['configuration']['base_url'],'http://127.0.0.1:8000/')
        self.assertNotIn('claim_token',lease)
        self.assertNotIn('user_id',lease)
        self.assertIsNone(self.broker.claim(self.identity))
        self.assertEqual(self.f.queue.admission.usage(self.f.owner,self.f.org)['active_runs'],1)

    def test_real_typed_result_and_png_publish_once_and_terminal_replay_is_rejected(self):
        run = self.f.submit()
        lease = self.broker.claim(self.identity)
        self.assertTrue(self.broker.result(self.identity,lease['lease_id'],'LOGIN-001','passed',.1,png=png_bytes())['accepted'])
        with self.assertRaises(ValueError):
            self.broker.result(self.identity,lease['lease_id'],'LOGIN-001','passed',.1)
        self.assertEqual(self.broker.finish(self.identity,lease['lease_id']),{'status':'completed'})
        with self.assertRaises(AgentAuthenticationError):
            self.broker.finish(self.identity,lease['lease_id'])
        result = self.f.queue.get(self.f.owner,self.f.org,self.f.project,run['run_id'])['results'][0]
        self.assertEqual(self.f.queue.evidence(self.f.owner,self.f.org,self.f.project,run['run_id'],result['evidence_id']),png_bytes())
        self.assertEqual(self.f.queue.admission.usage(self.f.owner,self.f.org)['active_runs'],0)

    def test_expired_lease_cancels_without_retry_and_preserves_partial_result(self):
        run = self.f.submit(cases=('LOGIN-001','SEARCH-001'))
        lease = self.broker.claim(self.identity)
        self.broker.result(self.identity,lease['lease_id'],'LOGIN-001','passed',.1)
        with self.assertRaises(ValueError):
            self.f.queue.recover_interrupted()
        self.f.now+=121
        with self.assertRaises(AgentAuthenticationError):
            self.broker.result(self.identity,lease['lease_id'],'SEARCH-001','passed',.1)
        self.assertEqual(self.broker.sweep(),{'cancelled':1})
        public = self.f.queue.get(self.f.owner,self.f.org,self.f.project,run['run_id'])
        self.assertEqual(public['status'],'cancelled')
        self.assertEqual(len(public['results']),1)
        self.assertIsNone(self.broker.claim(self.identity))

    def test_revocation_and_cross_agent_lease_cannot_publish_results(self):
        self.f.submit()
        lease = self.broker.claim(self.identity)
        other = self.registry.issue(self.f.owner,self.f.org,self.f.project)
        identity = self.registry.authenticate(other.agent_id,other.token.value,1)
        with self.assertRaises(AgentAuthenticationError):
            self.broker.result(identity,lease['lease_id'],'LOGIN-001','passed',.1)
        self.registry.revoke(self.f.owner,self.f.org,self.grant.agent_id)
        with self.assertRaises(AgentAuthenticationError):
            self.broker.result(self.identity,lease['lease_id'],'LOGIN-001','passed',.1)
        self.assertEqual(self.broker.sweep(),{'cancelled':1})

    def test_cancellation_drops_late_result_and_invalid_png_never_commits(self):
        run = self.f.submit()
        lease = self.broker.claim(self.identity)
        with self.assertRaises(ValueError):
            self.broker.result(self.identity,lease['lease_id'],'LOGIN-001','passed',.1,png=b'<svg/>')
        self.f.queue.cancel(self.f.owner,self.f.org,self.f.project,run['run_id'])
        self.assertTrue(self.broker.check(self.identity,lease['lease_id'])['cancel_requested'])
        self.assertFalse(self.broker.result(self.identity,lease['lease_id'],'LOGIN-001','passed',.1,png=png_bytes())['accepted'])
        self.assertEqual(self.broker.finish(self.identity,lease['lease_id']),{'status':'cancelled'})
        self.assertEqual(self.f.queue.get(self.f.owner,self.f.org,self.f.project,run['run_id'])['results'],[])
