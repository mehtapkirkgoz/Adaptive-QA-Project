"""One bounded operator pass; no dispatch, network or automatic work replay."""

import math
import time

from adaptive_qa.agent_broker import AgentBroker
from adaptive_qa.agent_registry import AgentRegistry
from adaptive_qa.dashboard_runs import DashboardRunQueue
from adaptive_qa.organization_discovery import OrganizationDiscoveryQueue
from adaptive_qa.organization_projects import OrganizationProjects
from adaptive_qa.organization_runs import OrganizationRunQueue
from adaptive_qa.organization_store import OrganizationStore
from adaptive_qa.project_store import ProjectStore
from adaptive_qa.worker_lock import worker_lock


def maintenance_once(projects, *, limit=100, clock=time.time):
    if not isinstance(projects, ProjectStore) or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('A trusted project store and batch limit from 1 to 100 are required.')
    now = clock()
    if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
        raise ValueError('A finite maintenance timestamp is required.')
    with worker_lock(projects.database):
        scoped = OrganizationProjects(OrganizationStore(projects))
        shared = OrganizationRunQueue(OrganizationDiscoveryQueue(scoped), clock=lambda: now)
        registry = AgentRegistry(scoped, clock=lambda: now)
        expired = AgentBroker(registry, shared).sweep()
        personal = DashboardRunQueue(projects, clock=lambda: now)
        return {'cancelled_agent_runs': expired['cancelled'],
                'personal_evidence_removed': personal.prune_expired_evidence(limit=limit)['removed'],
                'shared_evidence_removed': shared.prune_expired_evidence(limit=limit)['removed']}
