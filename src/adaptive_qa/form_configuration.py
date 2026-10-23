"""Typed saved form mappings and secret-free runtime snapshots."""
from adaptive_qa.element_models import ProjectElementMappings, ElementMapping, LocatorSpec, LocatorStrategy
from adaptive_qa.form_checks import FORM_DEFAULTS

def decode_form_mappings(data):
    if data is None:
        return None
    if not isinstance(data, dict) or set(data) != {'project_id', 'mappings'} or not isinstance(data['mappings'], list):
        raise ValueError('Invalid form mappings.')
    mappings = []
    for item in data['mappings']:
        if not isinstance(item, dict) or set(item) != {'logical_name', 'locators', 'scope_test_id'}:
            raise ValueError('Invalid element mapping.')
        if not isinstance(item['locators'], list):
            raise ValueError('Invalid locator alternatives.')
        locators = tuple(LocatorSpec(LocatorStrategy(spec['strategy']), spec['value'], spec['role'])
                         for spec in item['locators']
                         if isinstance(spec, dict) and set(spec) == {'strategy', 'value', 'role'})
        if len(locators) != len(item['locators']):
            raise ValueError('Invalid locator fields.')
        mappings.append(ElementMapping(item['logical_name'], locators, item['scope_test_id']))
    return ProjectElementMappings(data['project_id'], tuple(mappings))


def saved_form_mappings(raw, project_id):
    if not isinstance(raw, list) or len(raw) > len(FORM_DEFAULTS):
        raise ValueError('At most five known form mappings are supported.')
    typed = decode_form_mappings({'project_id': project_id, 'mappings': raw})
    if any(item.logical_name not in FORM_DEFAULTS for item in typed.mappings):
        raise ValueError('Unknown form mapping key.')
    return typed


def runtime_configuration(settings):
    snapshot = {key: settings[key] for key in ('base_url', 'allowed_hosts', 'allow_data_changes')}
    if settings.get('form_mappings'):
        snapshot['form_mappings'] = settings['form_mappings']
    return snapshot


def mapping_action_names(settings, project_id):
    names = {}
    for item in saved_form_mappings(settings.get('form_mappings', []), project_id).mappings:
        if item.logical_name in ('login.submit', 'search.submit'):
            aliases = tuple(spec.value for spec in item.locators
                            if spec.strategy == LocatorStrategy.ROLE and spec.role == 'button')
            if aliases:
                names[item.logical_name.split('.')[0]] = aliases
    return names
