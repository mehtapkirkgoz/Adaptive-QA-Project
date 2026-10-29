"""Explicit authenticated single-server profile; never reuse the free local identity."""
from dataclasses import dataclass
from pathlib import Path
from contextlib import closing
from urllib.parse import urlsplit
import re

from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore


@dataclass(frozen=True)
class HostedOrigin:
    origin: str

    def __post_init__(self):
        if not isinstance(self.origin,str):raise ValueError('An explicit HTTPS origin is required.')
        p=urlsplit(self.origin)
        if (p.scheme!='https' or p.username or p.password or p.path or p.query or p.fragment
                or p.port not in (None,443) or not p.hostname or p.netloc!=p.hostname
                or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?',p.hostname)
                or '.' not in p.hostname or '..' in p.hostname or p.hostname.replace('.','').isdigit()
                or p.hostname.endswith('.localhost') or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in p.hostname.split('.'))):
            raise ValueError('Use an exact lowercase HTTPS hostname without a path or port.')

    @property
    def authority(self):return urlsplit(self.origin).netloc


class HostedSessions(AuthStore):
    hosted=True


class HostedProjects(ProjectStore):
    """Owner-scoped accounts, with bounded server workspace creation."""
    hosted=True
    def create(self,actor,name):
        from adaptive_qa.project_store import OwnedProject,_name
        from uuid import uuid4
        self._actor(actor);_name(name)
        with self._connection() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT count(*) FROM dashboard_projects WHERE owner_id=?',(actor.user_id,)).fetchone()[0]>=1:
                raise ValueError('This server edition supports one active project per account.')
            project=OwnedProject(uuid4().hex,actor.user_id,name)
            c.execute('INSERT INTO dashboard_projects (project_id,owner_id,name) VALUES (?,?,?)',(project.project_id,actor.user_id,name))
            return project


def hosted_workspace(workspace):
    root=Path(workspace).resolve()
    if root==Path(root.anchor):raise ValueError('Use a dedicated private server data directory.')
    if any((root/name).exists() or (root/name).is_symlink() for name in ('license.sqlite','preview-process.json')):
        raise ValueError('Use a separate server workspace, not an existing local edition.')
    if (root/'projects.sqlite').is_file():
        import sqlite3
        with closing(sqlite3.connect((root/'projects.sqlite').as_uri()+'?mode=ro',uri=True)) as c:
            if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_projects'").fetchone():
                if c.execute('SELECT 1 FROM dashboard_projects WHERE owner_id=?',('f'*32,)).fetchone():
                    raise ValueError('Do not reuse an account-free local database on a server.')
    root.mkdir(parents=True,exist_ok=True)
    return root


def create_hosted_app(workspace,public_origin,*,ui_directory):
    from adaptive_qa.web_app import create_app
    origin=HostedOrigin(public_origin)
    root=hosted_workspace(workspace)
    return create_app(HostedSessions(root/'auth.sqlite'),projects=HostedProjects(root/'projects.sqlite'),
                      port=8080,ui_directory=ui_directory,hosted_origin=origin)


def hosted_route(method,path):
    """Only the authenticated URL/login product, never local fixtures or server secrets."""
    if method in ('GET','HEAD') and (path=='/' or path.startswith('/assets/')):return True
    rules={
        '/api/runtime':{'GET'},'/api/auth/me':{'GET'},'/api/auth/login':{'POST'},'/api/auth/logout':{'POST'},
        '/api/projects':{'GET'},'/api/browser-reviews':{'GET'},'/api/site-checks':{'GET','POST'},
    }
    if path in rules:return method in rules[path]
    patterns=(
        (r'/api/site-checks/[a-f0-9]{32}',{'GET'}),
        (r'/api/site-checks/[a-f0-9]{32}/cancel',{'POST'}),
        (r'/api/projects/[a-f0-9]{32}/configuration',{'GET'}),
        (r'/api/projects/[a-f0-9]{32}/interactive/website-login/(?:review|jobs)',{'POST'}),
        (r'/api/projects/[a-f0-9]{32}/interactive/jobs(?:/[a-f0-9]{32})?',{'GET'}),
        (r'/api/projects/[a-f0-9]{32}/interactive/jobs/[a-f0-9]{32}/cancel',{'POST'}),
        (r'/api/projects/[a-f0-9]{32}/runs/[a-f0-9]{32}/evidence/[a-f0-9]{32}',{'GET'}),
    )
    return any(method in methods and re.fullmatch(pattern,path) for pattern,methods in patterns)
