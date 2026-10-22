"""Value-free context fingerprint for controlled local UI observations."""

import hashlib
from importlib.metadata import version, PackageNotFoundError
import json
from pathlib import Path
import platform
import sys


def capture_execution_context():
    """Missing or changed sources mean unknown context, never a guessed match."""
    package = Path(__file__).resolve().parent
    sources = ('local_browser.py', 'smoke_checks.py', 'extra_ui_checks.py',
        'document_checks.py', 'semantic_checks.py', 'element_matching.py',
        'ui_bindings.py', 'sample_data.py', 'egress.py', 'browser_process.py', 'targets.py',
        'execution_context.py', 'dashboard_run_worker.py')
    try:
        hashes = {}
        for path in [package / name for name in sources] + [package.parent.parent / 'samples/web/index.html']:
            with path.open('rb') as stream:
                content = stream.read(262145)
            if len(content) > 262144:
                return None
            hashes[path.name] = hashlib.sha256(content).hexdigest()
        snapshot = {'sources': hashes, 'python': list(sys.version_info[:3]),
                    'platform': platform.system(), 'playwright': version('playwright'),
                    'profile': 'controlled-local-root-read-only-v1'}
        return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    except (OSError, PackageNotFoundError):
        return None
