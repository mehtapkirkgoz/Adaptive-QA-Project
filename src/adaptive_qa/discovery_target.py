"""Non-network profile validation; actual connections retain pinned IP checks."""

from ipaddress import ip_address
from urllib.parse import urlsplit

from adaptive_qa.config import ProjectConfig, extract_hostname
from adaptive_qa.document_target import controlled_start_path
from adaptive_qa.policy import DestinationPolicy, validate_public_ip


def validate_discovery_url(url, project, profile):
    if profile == 'controlled_local':
        from adaptive_qa.targets import validate_local_sample_target
        return validate_local_sample_target(url, project)
    if profile != 'public_https':
        raise ValueError('Unknown discovery profile.')
    DestinationPolicy().validate_url(url)
    if not project.is_url_allowed(url):
        raise ValueError('Discovery destination is outside the configured host scope.')
    host = extract_hostname(url)
    if host == 'localhost' or host.endswith('.localhost'):
        raise ValueError('Loopback names are not public discovery destinations.')
    try:
        address = ip_address(host)
    except ValueError:
        if all(character in '0123456789.' for character in host):
            raise ValueError('Ambiguous numeric destination.') from None
    else:
        validate_public_ip(str(address))


def validate_discovery_project(project, profile):
    if (not isinstance(project, ProjectConfig) or profile not in ('controlled_local', 'public_https')
            or len(project.project_id) > 128 or len(project.name) > 128
            or len(project.base_url) > 2048 or not 1 <= len(project.allowed_hosts) <= 20
            or any(len(host) > 253 for host in project.allowed_hosts)):
        raise ValueError('A bounded typed discovery configuration is required.')
    parsed = urlsplit(project.base_url)
    if parsed.query or parsed.fragment:
        raise ValueError('Discovery start URLs must omit queries and fragments.')
    if profile == 'controlled_local':
        controlled_start_path({'base_url': project.base_url, 'allowed_hosts': project.allowed_hosts})
    validate_discovery_url(project.base_url, project, profile)


def configured_discovery(settings, *, project_id='configured-discovery'):
    if (not isinstance(settings, dict) or not isinstance(settings.get('base_url'), str)
            or not isinstance(settings.get('allowed_hosts'), (list, tuple))):
        raise ValueError('Saved discovery settings are required.')
    try:
        project = ProjectConfig(project_id, 'Configured discovery', settings['base_url'],
                                tuple(settings['allowed_hosts']), settings['allow_data_changes'])
    except (KeyError, TypeError):
        raise ValueError('Invalid discovery settings.') from None
    profile = 'controlled_local' if project.base_url.startswith('http://127.0.0.1:8000') else 'public_https'
    validate_discovery_project(project, profile)
    return profile, project


def discovery_support(settings):
    try:
        profile, _ = configured_discovery(settings)
    except ValueError:
        return {'supported': False, 'profile': None, 'execution_scope': 'none'}
    return {'supported': True, 'profile': profile,
            'execution_scope': 'controlled_ui' if profile == 'controlled_local' else 'document_ui'}
