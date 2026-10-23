"""Conservative saved-configuration review before any discovery job exists."""

from adaptive_qa.api_catalog import API_CASES
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.config import ProjectConfig
from adaptive_qa.crawler import CrawlResult
from adaptive_qa.database_catalog import DATABASE_CASES
from adaptive_qa.planning import build_test_plan
from adaptive_qa.document_target import serialize_target_binding


class ConfigurationRequired(ValueError):
    """A project needs saved settings before a plan can be reviewed."""


def review_project_plan(projects, actor, project_id):
    project = projects.get(actor, project_id)
    settings = projects.configuration(actor, project_id)
    if not settings['configured']:
        raise ConfigurationRequired()
    config = ProjectConfig(project.project_id, project.name, settings['base_url'],
                           tuple(settings['allowed_hosts']), settings['allow_data_changes'])
    definitions = TEST_CASES + tuple(case.definition for case in API_CASES) + tuple(case.definition for case in DATABASE_CASES)
    # Never invent discovery evidence or treat configured credentials as an adapter binding.
    plan = build_test_plan(CrawlResult((), 0, ('Discovery has not been run for this project.',)), definitions, config)
    return serialize_plan(plan, definitions, project_id)


def serialize_plan(plan, definitions, project_id, *, discovery_status='not_run',
                   inspected_pages=0, configuration_source='saved_settings'):
    by_id = {case.case_id: case for case in definitions}
    return {'project_id': project_id, 'execution_authorized': plan.execution_authorized,
            'discovery_status': discovery_status, 'scope': plan.scope, 'inspected_pages': inspected_pages,
            'configuration_source': configuration_source,
            'limitations': list(plan.assessment.limitations),
            'counts': {'catalog': len(definitions), **{decision: sum(item.decision == decision for item in plan.cases)
                       for decision in ('selected', 'skipped', 'blocked')}},
            'features': [{'feature': f.feature, 'status': f.status} for f in plan.assessment.features],
            'cases': [{'case_id': item.case_id, 'name': by_id[item.case_id].name,
                       'test_type': by_id[item.case_id].test_type, 'decision': item.decision,
                       'reason': item.reason, 'changes_data': by_id[item.case_id].changes_data,
                       **serialize_target_binding(item.case_id, item.target_url)}
                      for item in plan.cases]}
