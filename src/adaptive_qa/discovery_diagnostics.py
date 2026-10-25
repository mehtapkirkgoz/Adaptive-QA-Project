"""Fixed, value-free access diagnostics; no target exception text is persisted."""

ACCESS_DIAGNOSTICS=frozenset({
    'dns_resolution_failed','destination_blocked','tls_verification_failed',
    'connection_failed','inspection_timeout','access_denied','target_http_error',
    'redirect_outside_scope','inspection_process_error','inspection_unavailable',
})


class DestinationDNSError(ValueError):
    """The bounded OS resolver could not return a valid destination."""


def failed_discovery_code(payload):
    if not isinstance(payload,dict) or payload.get('pages')!=[]:
        return None
    code=payload.get('diagnostic_code')
    if isinstance(code,str) and code in ACCESS_DIAGNOSTICS:return code
    limitations=payload.get('limitations',[])
    if not isinstance(limitations,list):return 'inspection_unavailable'
    if 'time_limit' in limitations:return 'inspection_timeout'
    if 'discovery_process_error' in limitations:return 'inspection_process_error'
    return 'inspection_unavailable'
