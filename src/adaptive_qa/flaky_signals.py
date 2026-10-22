"""Conservative advisory signals; outcome changes are not proof of a flaky test."""

import hashlib


def build_flaky_report(runs, actor, project_id):
    groups = {}
    history = runs.list(actor, project_id)
    excluded = 0
    for run in reversed(history):
        if run['status'] != 'completed':
            excluded += 1
            continue
        context = runs.comparison_context(actor, project_id, run['run_id'])
        if not context['contracts'] or not context['execution_context']:
            excluded += 1
            continue
        for result in run['results']:
            if result['status'] not in ('passed', 'failed'):
                continue
            contract = context['contracts'].get(result['case_id'])
            if not contract:
                continue
            key = (result['case_id'], context['configuration'], contract, context['execution_context'])
            groups.setdefault(key, []).append((run['run_id'], result['status']))
    signals = []
    for key, observations in groups.items():
        outcomes = [status for _, status in observations]
        passed, failed = outcomes.count('passed'), outcomes.count('failed')
        transitions = sum(left != right for left, right in zip(outcomes, outcomes[1:]))
        enough = len(outcomes) >= 5
        potential = enough and min(passed, failed) >= 2 and transitions >= 2
        signals.append({'case_id': key[0], 'context_id': hashlib.sha256(':'.join(key).encode()).hexdigest(),
            'observations': len(outcomes), 'passed': passed, 'failed': failed,
            'transitions': transitions, 'potential_flakiness': potential,
            'assessment': ('potential_flakiness' if potential else 'insufficient_history' if not enough else
                           'mixed_outcomes' if passed and failed else 'consistent_observed'),
            'run_ids': [run_id for run_id, _ in observations]})
    return {'scope': 'latest_20_owned_runs', 'minimum_observations': 5,
            'excluded_runs': excluded, 'signals': signals,
            'reason': 'Advisory only. Matching saved policy, definitions, fixture and runtime sources are required. '
                      'External state and timing can still differ; no test outcome or retry policy is changed.'}
