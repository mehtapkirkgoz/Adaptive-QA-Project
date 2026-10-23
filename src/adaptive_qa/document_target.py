"""Explicit path binding for title-independent checks on controlled documents."""

from adaptive_qa.document_checks import DOCUMENT_CHECKS


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
