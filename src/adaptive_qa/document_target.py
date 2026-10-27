"""Explicit path binding for title-independent checks on controlled documents."""

from adaptive_qa.document_checks import DOCUMENT_CHECKS
from adaptive_qa.form_checks import FORM_CHECKS
from adaptive_qa.document_url import canonical_root_url

LOCAL_ORIGIN = 'http://127.0.0.1:8000'


def validate_document_path(case_id, path, *, site='root'):
    if case_id not in DOCUMENT_CHECKS or site != 'root':
        raise ValueError('Only independent document checks support a document path.')
    if (not isinstance(path, str) or not 1 <= len(path) <= 512 or not path.isascii()
            or not path.startswith('/') or path.startswith('//')
            or any(ch in path for ch in ('\\', '%', '?', '#', ':'))
            or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in path)
            or any(part in ('.', '..') for part in path.split('/'))):
        raise ValueError('A canonical controlled document path is required.')
    return path


def controlled_start_path(settings):
    """Validate the fixed fixture origin without DNS or network access."""
    if (not isinstance(settings, dict) or not isinstance(settings.get('base_url'), str)
            or not isinstance(settings.get('allowed_hosts'), (list, tuple))
            or '127.0.0.1' not in settings['allowed_hosts']
            or not settings['base_url'].startswith(LOCAL_ORIGIN)):
        raise ValueError('An explicitly allowed controlled local document is required.')
    return validate_document_path('DOC-001', settings['base_url'][len(LOCAL_ORIGIN):] or '/')


def serialize_target_binding(case_id, target_url):
    if target_url in (LOCAL_ORIGIN, LOCAL_ORIGIN+'/'):
        return {'target_binding': 'local_root'}
    if case_id in DOCUMENT_CHECKS or case_id in FORM_CHECKS:
        try:
            path = controlled_start_path({'base_url': target_url, 'allowed_hosts': ['127.0.0.1']})
        except ValueError:
            pass
        else:
            return {'target_binding': 'local_document' if case_id in DOCUMENT_CHECKS else 'local_form',
                    'document_path': path}
        if isinstance(target_url, str):
            from urllib.parse import urlsplit
            from adaptive_qa.discovery_target import configured_discovery
            try:
                profile, _ = configured_discovery({'base_url': target_url,
                    'allowed_hosts': [urlsplit(target_url).hostname], 'allow_data_changes': False})
            except ValueError:
                pass
            else:
                if profile == 'public_https':
                    return {'target_binding': 'public_document' if case_id in DOCUMENT_CHECKS else 'public_form',
                            'document_url': canonical_root_url(target_url)}
    return {'target_binding': None}


def validate_runtime_binding(settings, case_id, decision):
    if (not isinstance(decision, dict) or decision.get('decision') != 'selected'
            or decision.get('test_type') != 'ui'):
        raise ValueError('A current selected UI binding is required.')
    from adaptive_qa.discovery_target import configured_discovery
    profile, project = configured_discovery(settings)
    if profile == 'public_https':
        if (case_id in DOCUMENT_CHECKS and decision.get('target_binding') == 'public_document'
                and canonical_root_url(decision.get('document_url')) == project.base_url):
            return
        if (case_id in FORM_CHECKS and decision.get('target_binding') == 'public_form'
                and canonical_root_url(decision.get('document_url')) == project.base_url):
            return
        raise ValueError('Only an independently checked document bound to the saved HTTPS URL is supported.')
    path = controlled_start_path(settings)
    if path == '/' and decision.get('target_binding') == 'local_root':
        return
    if (path != '/' and case_id in DOCUMENT_CHECKS
            and decision.get('target_binding') == 'local_document'
            and decision.get('document_path') == path):
        return
    if (path != '/' and case_id in FORM_CHECKS
            and decision.get('target_binding') == 'local_form'
            and decision.get('document_path') == path):
        return
    raise ValueError('The selected case is not bound to the saved document.')
