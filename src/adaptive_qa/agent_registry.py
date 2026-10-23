"""Project-bound local-pilot agent credentials; no network or execution here."""

from dataclasses import dataclass, field
import hashlib
import hmac
import math
import re
import secrets
import time
from uuid import uuid4

from adaptive_qa.organization_policy import OrganizationAction as Action
from adaptive_qa.project_store import ProjectActor, _id
from adaptive_qa.secrets import SecretValue


class AgentAuthenticationError(Exception):
    """Invalid, expired, revoked and replayed credentials have one outcome."""


@dataclass(frozen=True)
class AgentGrant:
    agent_id: str
    organization_id: str
    project_id: str
    expires_at: float
    token: SecretValue = field(repr=False)


@dataclass(frozen=True)
class AgentIdentity:
    """Trusted server identity; client-supplied instances never authorize work."""
    agent_id: str
    organization_id: str
    project_id: str


def _digest(token):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        raise AgentAuthenticationError('Agent authentication failed.')
    return hashlib.sha256(token.encode('ascii')).digest()


AGENT_PATHS = frozenset(('/agent/poll','/agent/check','/agent/result','/agent/finish'))


def message_signature(key,path,sequence,payload,*,response=False):
    """Authenticate exact protocol direction/path/sequence/body without sending the token."""
    if (not isinstance(key,bytes) or len(key)!=32 or path not in AGENT_PATHS
            or type(sequence) is not int or not 1<=sequence<=2147483647
            or not isinstance(payload,bytes) or len(payload)>1024*1024 or type(response) is not bool):
        raise AgentAuthenticationError('Agent authentication failed.')
    prefix = 'adaptive-agent-v1-response' if response else 'adaptive-agent-v1-request'
    return hmac.new(key,(prefix+'\n'+path+'\n'+str(sequence)+'\n').encode()+payload,'sha256').hexdigest()


def token_signing_key(token):
    return _digest(token)


class AgentRegistry:
    def __init__(self, scoped_projects, *, clock=time.time):
        self.scoped = scoped_projects
        self.projects = scoped_projects.organizations.projects
        self.clock = clock
        with self.projects._connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS dashboard_agents ('
                      'agent_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, project_id TEXT NOT NULL, '
                      'issuer_id TEXT NOT NULL, token_hash BLOB UNIQUE NOT NULL, expires_at REAL NOT NULL, '
                      'revoked INTEGER NOT NULL DEFAULT 0, last_sequence INTEGER NOT NULL DEFAULT 0)')
            c.execute('CREATE INDEX IF NOT EXISTS dashboard_agents_scope ON dashboard_agents(organization_id,project_id)')

    def _now(self):
        value = self.clock()
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=253402300799:
            raise AgentAuthenticationError('Agent authentication failed.')
        return value

    def _current(self,c,row):
        if row is None or row['revoked'] or row['expires_at']<=self._now():
            raise AgentAuthenticationError('Agent authentication failed.')
        try:
            issuer = ProjectActor(row['issuer_id'])
            self.scoped.organizations._membership(c,issuer,row['organization_id'],Action.MANAGE_ORGANIZATION)
            project = self.scoped._row(c,issuer,row['organization_id'],row['project_id'],Action.CONFIGURE)
            import json
            settings = json.loads(project['settings_json'])
            if (settings['base_url'] not in ('http://127.0.0.1:8000','http://127.0.0.1:8000/')
                    or settings['allowed_hosts']!=['127.0.0.1'] or settings['allow_data_changes'] is not False):
                raise ValueError()
        except (LookupError,ValueError,TypeError,KeyError):
            raise AgentAuthenticationError('Agent authentication failed.') from None
        return AgentIdentity(row['agent_id'],row['organization_id'],row['project_id'])

    def issue(self,actor,organization_id,project_id,*,lifetime_seconds=3600):
        """Trusted operator enrollment; token returned once, never stored in plaintext."""
        if type(lifetime_seconds) is not int or not 60<=lifetime_seconds<=86400:
            raise ValueError('Agent lifetime must be 60 seconds to one day.')
        agent_id,token = uuid4().hex,secrets.token_urlsafe(32)
        expires = self._now()+lifetime_seconds
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.scoped.organizations._membership(c,actor,organization_id,Action.MANAGE_ORGANIZATION)
            self.scoped._row(c,actor,organization_id,project_id,Action.CONFIGURE)
            count = c.execute('SELECT count(*) FROM dashboard_agents WHERE organization_id=? AND revoked=0 AND expires_at>?',
                              (organization_id,self._now())).fetchone()[0]
            if count>=10:
                raise ValueError('Local agent enrollment capacity reached.')
            c.execute('INSERT INTO dashboard_agents (agent_id,organization_id,project_id,issuer_id,token_hash,expires_at) VALUES (?, ?, ?, ?, ?, ?)',
                      (agent_id,organization_id,project_id,actor.user_id,_digest(token),expires))
            self._current(c,c.execute('SELECT * FROM dashboard_agents WHERE agent_id=?',(agent_id,)).fetchone())
        return AgentGrant(agent_id,organization_id,project_id,expires,SecretValue(token))

    def authenticate(self,agent_id,token,sequence):
        try:
            _id(agent_id)
        except ValueError:
            raise AgentAuthenticationError('Agent authentication failed.') from None
        digest = _digest(token)
        if type(sequence) is not int or not 1<=sequence<=2147483647:
            raise AgentAuthenticationError('Agent authentication failed.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM dashboard_agents WHERE agent_id=?',(agent_id,)).fetchone()
            if row is None or not hmac.compare_digest(bytes(row['token_hash']),digest) or sequence<=row['last_sequence']:
                raise AgentAuthenticationError('Agent authentication failed.')
            identity = self._current(c,row)
            c.execute('UPDATE dashboard_agents SET last_sequence=? WHERE agent_id=?',(sequence,agent_id))
            return identity

    def recheck(self,c,identity):
        if not isinstance(identity,AgentIdentity):
            raise AgentAuthenticationError('Agent authentication failed.')
        row = c.execute('SELECT * FROM dashboard_agents WHERE agent_id=?',(identity.agent_id,)).fetchone()
        current = self._current(c,row)
        if current!=identity:
            raise AgentAuthenticationError('Agent authentication failed.')
        return current

    def authenticate_message(self,agent_id,sequence,path,payload,signature):
        """Internal transport authentication; return a private response-signing key."""
        try:
            _id(agent_id)
        except ValueError:
            raise AgentAuthenticationError('Agent authentication failed.') from None
        if not isinstance(signature,str) or not re.fullmatch(r'[0-9a-f]{64}',signature):
            raise AgentAuthenticationError('Agent authentication failed.')
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM dashboard_agents WHERE agent_id=?',(agent_id,)).fetchone()
            if row is None:
                raise AgentAuthenticationError('Agent authentication failed.')
            key = bytes(row['token_hash'])
            expected = message_signature(key,path,sequence,payload)
            if not hmac.compare_digest(expected,signature) or sequence<=row['last_sequence']:
                raise AgentAuthenticationError('Agent authentication failed.')
            identity = self._current(c,row)
            c.execute('UPDATE dashboard_agents SET last_sequence=? WHERE agent_id=?',(sequence,agent_id))
            return identity,key

    def revoke(self,actor,organization_id,agent_id):
        _id(agent_id)
        with self.projects._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.scoped.organizations._membership(c,actor,organization_id,Action.MANAGE_ORGANIZATION)
            changed = c.execute('UPDATE dashboard_agents SET revoked=1 WHERE agent_id=? AND organization_id=?',(agent_id,organization_id)).rowcount
            if changed!=1:
                raise AgentAuthenticationError('Agent authentication failed.')
