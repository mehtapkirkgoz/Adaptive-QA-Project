"""Verify release hashes, install its wheel away from source, and check its catalog."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def check_release(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / 'release.json').read_text(encoding='utf-8'))
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if manifest['source_commit'] != revision or manifest['activation_enabled'] is not False:
        raise ValueError('Release must match the checked-out commit and remain inactive.')
    if {entry['name'] for entry in manifest['files']} | {'release.json'} != {p.name for p in directory.iterdir()}:
        raise ValueError('Release file set does not match its manifest.')
    wheel = None
    for entry in manifest['files']:
        path = directory / entry['name']
        if path.parent != directory or path.is_symlink() or not path.is_file():
            raise ValueError('Release files must be regular children of the bundle.')
        if path.stat().st_size != entry['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Release file digest or size does not match.')
        if path.name.endswith('.whl'):
            if wheel is not None:
                raise ValueError('A release must have exactly one application wheel.')
            wheel = path
    if wheel is None:
        raise ValueError('The application wheel is missing.')
    with zipfile.ZipFile(directory / 'dashboard.zip') as assets:
        if 'index.html' not in assets.namelist() or assets.testzip() is not None:
            raise ValueError('The dashboard archive is incomplete or corrupt.')
        if any(name.startswith(('/', '\\')) or '..' in Path(name).parts for name in assets.namelist()):
            raise ValueError('Unsafe dashboard asset path.')
    with TemporaryDirectory(prefix='adaptive-qa-release-check-') as temporary:
        site = Path(temporary) / 'installed'
        environment = dict(os.environ)
        environment.pop('PYTHONPATH', None)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', '--target', str(site), str(wheel)],
                       cwd=temporary, env=environment, check=True, timeout=120)
        code = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import adaptive_qa
assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.api_catalog import API_CASES
from adaptive_qa.database_catalog import DATABASE_CASES
assert (len(TEST_CASES), len(API_CASES), len(DATABASE_CASES)) == (51, 34, 15)
from adaptive_qa.schema_migrations import SCHEMA_REVISION
import json, sqlite3
assert json.loads(sys.argv[2]) == [0, SCHEMA_REVISION]
from adaptive_qa.auth_store import AuthStore
from adaptive_qa.project_store import ProjectStore
for factory, name in ((AuthStore, 'future-auth.sqlite'), (ProjectStore, 'future-projects.sqlite')):
    connection = sqlite3.connect(name)
    connection.execute('PRAGMA user_version=2147483647')
    connection.close()
    try:
        factory(Path(name))
    except ValueError:
        pass
    else:
        raise AssertionError('Installed release did not reject a future schema')
from adaptive_qa.__main__ import main
sys.argv = ['adaptive-qa', '--status']
main()
"""
        subprocess.run([sys.executable, '-I', '-c', code, str(site),
                        json.dumps(manifest.get('database_schema_revisions'))], cwd=temporary,
                       env=environment, check=True, timeout=30)
    print(json.dumps({'source_commit': revision, 'files_verified': len(manifest['files']),
                      'installed_catalog': {'ui': 51, 'api': 34, 'database': 15},
                      'activation_enabled': False}, indent=2))


if __name__ == '__main__':
    check_release(sys.argv[1])
