"""The browser represents an empty HTTP(S) root path as '/', without a redirect."""
from urllib.parse import urlsplit


def canonical_root_url(value):
    # Deliberately do not equate different paths, ports, hosts, encodings or queries.
    if not isinstance(value, str) or '?' in value or '#' in value:
        return value
    parsed = urlsplit(value)
    if parsed.scheme in ('http', 'https') and parsed.netloc and not parsed.path:
        return value + '/'
    return value
