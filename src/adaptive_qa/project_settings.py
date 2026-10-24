"""Bounded dashboard settings; validating references never resolves secrets."""

from urllib.parse import urlsplit
from dataclasses import asdict
import json
from adaptive_qa.form_configuration import saved_form_mappings

from adaptive_qa.config import ProjectConfig, extract_hostname
from adaptive_qa.secrets import SecretReference
from adaptive_qa.discovery_target import discovery_support


SECRET_SLOTS = ('login_username', 'login_password', 'api_token', 'database_path', 'search_query')


def reference_name(owner_id, project_id, slot):
    if slot not in SECRET_SLOTS:
        raise ValueError('Unknown secret slot.')
    return f'ADAPTIVE_QA_{owner_id.upper()}_{project_id.upper()}_{slot.upper()}'


def validate_settings(project, data):
    fields = {'base_url', 'allowed_hosts', 'allow_data_changes', 'secret_references'}
    if not isinstance(data, dict) or set(data) not in (fields, fields | {'form_mappings'}):
        raise ValueError('Exact project settings fields are required.')
    url, hosts, references = data['base_url'], data['allowed_hosts'], data['secret_references']
    if not isinstance(url, str) or len(url) > 512:
        raise ValueError('A bounded target URL is required.')
    parsed = urlsplit(url)
    if parsed.query or parsed.fragment:
        raise ValueError('Target URLs must not contain queries or fragments.')
    if (not isinstance(hosts, list) or not 1 <= len(hosts) <= 10
            or any(not isinstance(host, str) or len(host) > 253 for host in hosts)
            or len(set(hosts)) != len(hosts)):
        raise ValueError('One to ten distinct hostnames are required.')
    for host in hosts:
        if extract_hostname('https://' + host) != host:
            raise ValueError('Hostnames must be normalized.')
    config = ProjectConfig(project.project_id, project.name, url, tuple(hosts), data['allow_data_changes'])
    if not isinstance(references, dict) or len(references) > len(SECRET_SLOTS):
        raise ValueError('Bounded secret references are required.')
    for slot, name in references.items():
        if slot not in SECRET_SLOTS or name != reference_name(project.owner_id, project.project_id, slot):
            raise ValueError('Secret references must belong to this owner, project and slot.')
        SecretReference(name)  # Syntax only: never read process environment here.
    mappings = saved_form_mappings(data.get('form_mappings', []), project.project_id)
    return {'form_mappings': json.loads(json.dumps([asdict(item) for item in mappings.mappings])), 'base_url': config.base_url, 'allowed_hosts': list(config.allowed_hosts),
            'allow_data_changes': config.allow_data_changes, 'secret_references': dict(references)}


def public_settings(project, data):
    available = {slot: reference_name(project.owner_id, project.project_id, slot) for slot in SECRET_SLOTS}
    if data is None:
        return {'configured': False, 'available_secret_references': available, 'discovery_support': discovery_support(None)}
    return {'configured': True, 'base_url': data['base_url'],
            'form_mappings': data.get('form_mappings', []),
            'discovery_support': discovery_support(data),
            'allowed_hosts': data['allowed_hosts'], 'allow_data_changes': data['allow_data_changes'],
            'secret_references': {slot: {'environment_variable': name, 'value': '[REDACTED]'}
                                  for slot, name in data['secret_references'].items()},
            'available_secret_references': available}
