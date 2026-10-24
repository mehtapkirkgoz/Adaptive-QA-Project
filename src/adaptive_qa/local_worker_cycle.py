"""One operator-requested pass over the existing local execution queues."""


def process_local_cycle(projects):
    from adaptive_qa.dashboard_jobs import DashboardDiscoveryQueue
    from adaptive_qa.dashboard_worker import process_discovery_once
    from adaptive_qa.dashboard_runs import DashboardRunQueue
    from adaptive_qa.dashboard_run_worker import process_run_once
    from adaptive_qa.interactive_queue import OwnedInteractiveQueue, process_owned_interactive_once

    outcomes = {}
    for name, queue_type, process in (
        ('discovery', DashboardDiscoveryQueue, process_discovery_once),
        ('run', DashboardRunQueue, process_run_once),
        ('interactive', OwnedInteractiveQueue, process_owned_interactive_once),
    ):
        outcomes[name] = process(queue_type(projects))
    return outcomes
