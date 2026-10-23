"""Project-bound credentials, replay refusal, expiration and revocation."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_qa.agent_registry import AgentRegistry,AgentAuthenticationError,AgentIdentity,message_signature,token_signing_key
from adaptive_qa.project_store import ProjectStore,ProjectActor
from adaptive_qa.organization_store import OrganizationStore,OrganizationNotFound
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_policy import OrganizationRole as Role


class AgentRegistryTests(unittest.TestCase):
    def test_signed_protocol_binds_body_path_sequence_and_response_direction(self):
        grant = self.registry.issue(self.owner,self.org,self.project)
        key = token_signing_key(grant.token.value)
        payload = b'{}'
        signature = message_signature(key,'/agent/poll',1,payload)
        for path,body in (('/agent/result',payload),('/agent/poll',b'{"extra":true}')):
            with self.assertRaises(AgentAuthenticationError):
                self.registry.authenticate_message(grant.agent_id,1,path,body,signature)
        identity,response_key = self.registry.authenticate_message(grant.agent_id,1,'/agent/poll',payload,signature)
        self.assertEqual(identity.project_id,self.project)
        self.assertEqual(key,response_key)
        with self.assertRaises(AgentAuthenticationError):
            self.registry.authenticate_message(grant.agent_id,1,'/agent/poll',payload,signature)
        self.assertNotEqual(signature,message_signature(key,'/agent/poll',1,payload,response=True))

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.projects = ProjectStore(Path(self.temp.name)/'projects.sqlite')
        self.organizations = OrganizationStore(self.projects)
        self.scoped = OrganizationProjects(self.organizations)
        self.owner,self.other = ProjectActor('a'*32),ProjectActor('b'*32)
        self.org = self.organizations.create(self.owner,'Pilot')
        self.project = self.scoped.create(self.owner,self.org,'Controlled')['project_id']
        self.settings = {'base_url':'http://127.0.0.1:8000/','allowed_hosts':['127.0.0.1'],
                         'allow_data_changes':False,'secret_references':{}}
        self.scoped.save_configuration(self.owner,self.org,self.project,self.settings)
        self.now = 1000.
        self.registry = AgentRegistry(self.scoped,clock=lambda:self.now)

    def test_grant_is_masked_and_only_hash_is_persisted(self):
        grant = self.registry.issue(self.owner,self.org,self.project)
        self.assertNotIn(grant.token.value,repr(grant))
        self.assertEqual(str(grant.token),'[REDACTED]')
        self.assertNotIn(grant.token.value.encode(),self.projects.database.read_bytes())
        identity = self.registry.authenticate(grant.agent_id,grant.token.value,1)
        self.assertEqual(identity.organization_id,self.org)
        self.assertEqual(identity.project_id,self.project)

    def test_duplicate_concurrent_sequence_is_accepted_exactly_once(self):
        grant = self.registry.issue(self.owner,self.org,self.project)
        def authenticate(_):
            try:
                self.registry.authenticate(grant.agent_id,grant.token.value,1)
                return True
            except AgentAuthenticationError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(authenticate,range(8))),1)
        self.assertTrue(self.registry.authenticate(grant.agent_id,grant.token.value,2))

    def test_revocation_expiry_invalid_secret_and_old_sequence_fail_closed(self):
        grant = self.registry.issue(self.owner,self.org,self.project,lifetime_seconds=60)
        self.registry.authenticate(grant.agent_id,grant.token.value,4)
        for sequence in (4,3,True,0,'5'):
            with self.assertRaises(AgentAuthenticationError):
                self.registry.authenticate(grant.agent_id,grant.token.value,sequence)
        with self.assertRaises(AgentAuthenticationError):
            self.registry.authenticate(grant.agent_id,'x'*43,5)
        self.registry.revoke(self.owner,self.org,grant.agent_id)
        with self.assertRaises(AgentAuthenticationError):
            self.registry.authenticate(grant.agent_id,grant.token.value,5)
        second = self.registry.issue(self.owner,self.org,self.project,lifetime_seconds=60)
        self.now += 60
        with self.assertRaises(AgentAuthenticationError):
            self.registry.authenticate(second.agent_id,second.token.value,1)

    def test_owner_only_enrollment_and_policy_changes_invalidate_credentials(self):
        self.organizations.set_member(self.owner,self.org,self.other.user_id,Role.ADMIN)
        with self.assertRaises(OrganizationNotFound):
            self.registry.issue(self.other,self.org,self.project)
        grant = self.registry.issue(self.owner,self.org,self.project)
        self.scoped.save_configuration(self.owner,self.org,self.project,dict(self.settings,allow_data_changes=True))
        with self.assertRaises(AgentAuthenticationError):
            self.registry.authenticate(grant.agent_id,grant.token.value,1)
        with self.assertRaises(AgentAuthenticationError):
            self.registry.issue(self.owner,self.org,self.project)
        with self.projects._connection() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM dashboard_agents').fetchone()[0],1)

    def test_recheck_refuses_changed_scope_and_revoked_identity(self):
        grant = self.registry.issue(self.owner,self.org,self.project)
        identity = self.registry.authenticate(grant.agent_id,grant.token.value,1)
        with self.projects._connection() as c,self.assertRaises(AgentAuthenticationError):
            self.registry.recheck(c,AgentIdentity(grant.agent_id,'f'*32,self.project))
        self.registry.revoke(self.owner,self.org,grant.agent_id)
        with self.projects._connection() as c,self.assertRaises(AgentAuthenticationError):
            self.registry.recheck(c,identity)
