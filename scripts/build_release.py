"""Build an inactive release from committed sources, never from workspace secrets."""

import ast
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, *, timeout=300):
    subprocess.run(command, cwd=cwd, check=True, timeout=timeout)


def publish_bundle(bundle, destination, base):
    """Publish once, allowing a short Windows file-handle release window."""
    for attempt in range(5):
        if (base.resolve() != base or bundle.resolve() != bundle
                or not bundle.is_relative_to(base) or not bundle.is_dir()
                or destination.parent != base or destination.resolve() != destination):
            raise ValueError('Release publication path is unsafe.')
        if destination.exists() or destination.is_symlink():
            raise ValueError('Never overwrite a published release.')
        try:
            bundle.rename(destination)
            return
        except PermissionError as error:
            if (sys.platform != 'win32' or getattr(error, 'winerror', None) not in (5, 32)
                    or attempt == 4):
                raise
            # Only retry publication of the same inactive bytes to an unused
            # destination. Recheck containment and nonexistence before each try.
            print(json.dumps({'release_publication': 'retrying_windows_publication',
                              'attempt': attempt + 1}), flush=True)
            time.sleep(.1 * 2**attempt)


def build_release(commit=None):
    if commit is not None:
        import re
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise ValueError('An explicit full lowercase commit SHA is required.')
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', (commit or 'HEAD') + '^{commit}'], cwd=ROOT, text=True).strip()
    base = ROOT / 'artifacts' / 'releases'
    if base.resolve() != base:
        raise ValueError('Release storage must not redirect outside the repository.')
    base.mkdir(parents=True, exist_ok=True)
    destination = base / revision
    if destination.exists() or destination.is_symlink():
        raise ValueError('This committed release already exists; never overwrite a published bundle.')
    with TemporaryDirectory(prefix='.build-', dir=base) as temporary:
        workspace = Path(temporary).resolve()
        source = workspace / 'source'
        source.mkdir()
        archive = workspace / 'source.zip'
        run(['git', 'archive', '--format=zip', f'--output={archive}', revision], ROOT)
        with zipfile.ZipFile(archive) as snapshot:
            for entry in snapshot.infolist():
                path = source / entry.filename
                if (not path.resolve().is_relative_to(source)
                        or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('Release sources must not contain redirected paths.')
            snapshot.extractall(source)
        bundle = workspace / 'bundle'
        bundle.mkdir()
        wheels = workspace / 'wheels'
        run([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir', str(wheels), '.'], source)
        candidates = list(wheels.glob('adaptive_qa-*.whl'))
        if len(candidates) != 1:
            raise ValueError('Exactly one application wheel must be built.')
        shutil.copyfile(candidates[0], bundle / candidates[0].name)
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        if npm is None:
            raise ValueError('Node/npm are required to compile the dashboard.')
        run([npm, 'ci', '--no-audit', '--no-fund'], source / 'frontend')
        run([npm, 'run', 'build'], source / 'frontend')
        ui = source / 'frontend' / 'dist'
        if not (ui / 'index.html').is_file():
            raise ValueError('The compiled dashboard entry point is missing.')
        with zipfile.ZipFile(bundle / 'dashboard.zip', 'w', compression=zipfile.ZIP_DEFLATED) as output:
            for path in sorted(ui.rglob('*')):
                if path.is_symlink() or not path.resolve().is_relative_to(ui.resolve()):
                    raise ValueError('Dashboard assets must not redirect outside their build directory.')
                if path.is_file():
                    output.write(path, path.relative_to(ui).as_posix())
        for name in ('requirements.lock.txt',):
            shutil.copyfile(source / name, bundle / name)
        shutil.copyfile(source / 'frontend' / 'package-lock.json', bundle / 'frontend-package-lock.json')
        files = [{'name': path.name, 'bytes': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                 for path in sorted(bundle.iterdir())]
        schema_source = ast.parse((source / 'src/adaptive_qa/schema_migrations.py').read_text(encoding='utf-8'))
        schema_revision = next(ast.literal_eval(node.value) for node in schema_source.body
                        if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == 'SCHEMA_REVISION' for target in node.targets))
        if type(schema_revision) is not int or schema_revision < 1:
            raise ValueError('Release schema revision must be a positive integer.')
        manifest = {'schema_version': 1, 'source_commit': revision, 'files': files,
                    'database_schema_revisions': [0, schema_revision],
                    'activation_enabled': False, 'python_version': sys.version.split()[0],
                    'node_version': subprocess.check_output(['node', '--version'], text=True).strip(),
                    'limitations': ['No runtime, fixtures, Chromium, credentials or databases are bundled.',
                                    'No service activation or byte-for-byte reproducibility is claimed.']}
        (bundle / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        publish_bundle(bundle, destination, base)
    print(json.dumps({'source_commit': revision, 'release_directory': str(destination),
                      'activation_enabled': False}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', help='Build an explicit reviewed historical commit instead of HEAD')
    build_release(parser.parse_args().commit)
