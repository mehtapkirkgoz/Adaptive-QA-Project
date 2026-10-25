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
    with zipfile.ZipFile(wheel) as package:
        if any('issue_local_license' in name or 'check_https_api' in name for name in package.namelist()):
            raise ValueError('Publisher issuance and fixture-routing tools must not be in the customer wheel.')
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
from time import perf_counter
started = perf_counter()
def stage(name):
    print('[installed-check] ' + name + ' elapsed=' + str(round(perf_counter()-started, 2)), flush=True)
stage('catalog-start')
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import adaptive_qa
assert Path(adaptive_qa.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.api_catalog import API_CASES
from adaptive_qa.database_catalog import DATABASE_CASES
assert (len(TEST_CASES), len(API_CASES), len(DATABASE_CASES)) == (51, 34, 15)
stage('schema-start')
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
# Exercise the installed wheel away from checkout, with ephemeral signing keys only.
stage('licensing-start')
import base64, time
from dataclasses import asdict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from adaptive_qa.license_store import LicenseStore
from adaptive_qa.licensing import LicenseClaims, LicenseError, license_message
from adaptive_qa.local_free import LOCAL_ACTOR, LocalFreeProjects
from adaptive_qa.local_licensed import LicensedLocalProjects
from adaptive_qa.local_cli import configure_parser
import argparse
parser = argparse.ArgumentParser()
configure_parser(parser.add_subparsers(dest='command'))
assert parser.parse_args(['local','license-status','--trusted-keys','publisher.json']).local_command == 'license-status'
private = Ed25519PrivateKey.generate()
clock = [int(time.time())]
licenses = LicenseStore(Path('license.sqlite'), {'ephemeral':private.public_key().public_bytes_raw()}, clock=lambda:clock[0])
prior = LocalFreeProjects(Path('local-projects.sqlite')).create(LOCAL_ACTOR,'Preserved local project')
payload = asdict(LicenseClaims('a'*32,'b'*32,clock[0]-1,clock[0]-1,clock[0]+100,2,1))
signature = base64.urlsafe_b64encode(private.sign(license_message('ephemeral',payload))).rstrip(b'=').decode()
licenses.install(json.dumps(dict(key_id='ephemeral',payload=payload,signature=signature)).encode())
paid = LicensedLocalProjects(Path('local-projects.sqlite'),licenses)
assert paid.get(LOCAL_ACTOR,prior.project_id) == prior
paid.create(LOCAL_ACTOR,'Second local project')
clock[0] += 100
try:
    paid.create(LOCAL_ACTOR,'Expired')
except LicenseError:
    pass
else:
    raise AssertionError('Installed release granted expired license access')
assert len(paid.list(LOCAL_ACTOR)) == 2
stage('recovery-start')
from adaptive_qa.local_free import create_free_app
from adaptive_qa.local_backup import create_local_backup, restore_local_backup
workspace = Path('edition-workspace').resolve()
create_free_app(workspace/'projects.sqlite')
LocalFreeProjects(workspace/'projects.sqlite').create(LOCAL_ACTOR,'Recovered free project')
create_local_backup(workspace,Path('edition-backup').resolve(),maintenance_confirmed=True)
restore_local_backup(Path('edition-backup').resolve(),Path('edition-recovered').resolve(),maintenance_confirmed=True)
assert len(LocalFreeProjects(Path('edition-recovered/projects.sqlite')).list(LOCAL_ACTOR)) == 1
assert not Path('edition-recovered/auth.sqlite').exists()
stage('status-start')
from adaptive_qa.__main__ import main
sys.argv = ['adaptive-qa', '--status']
main()
stage('complete')
"""
        # This is an installation/migration/recovery verification budget, not
        # a target-test deadline. The combined check exceeded the old 30-second
        # cap on Windows CI; stage logs now locate any future stalls.
        subprocess.run([sys.executable, '-I', '-u', '-c', code, str(site),
                        json.dumps(manifest.get('database_schema_revisions'))], cwd=temporary,
                       env=environment, check=True, timeout=120)
        if os.environ.get('ADAPTIVE_QA_VERIFY_LICENSED_UI') == '1':
            ui = Path(temporary)/'dashboard'
            with zipfile.ZipFile(directory/'dashboard.zip') as assets:
                assets.extractall(ui)
            browser_environment = dict(environment)
            browser_environment['ADAPTIVE_QA_VERIFY_SITE'] = str(site)
            browser_environment['ADAPTIVE_QA_VERIFY_UI'] = str(ui)
            subprocess.run([sys.executable,str(ROOT/'scripts/check_licensed_ui.py')],cwd=temporary,
                env=browser_environment,check=True,timeout=180)
            report = json.loads((Path(temporary)/'artifacts/local-license/ui.json').read_text(encoding='utf-8'))
            if (not report.get('installed_wheel') or not report.get('recovered_results_and_license')
                    or report.get('api_ui_confirmed_result') != 'passed'
                    or report.get('api_requests') != 1 or not report.get('api_result_preserved_after_recovery')
                    or report.get('database_ui_confirmed_result') != 'passed'
                    or not report.get('database_fixture_unchanged')
                    or not report.get('database_result_preserved_after_recovery')
                    or not report.get('database_fixture_not_in_backup')):
                raise ValueError('Installed licensed browser/recovery evidence is incomplete.')
            output = ROOT/'artifacts/local-license'; output.mkdir(parents=True,exist_ok=True)
            (output/'installed-ui.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            subprocess.run([sys.executable,str(ROOT/'scripts/check_https_api.py'),'--licensed'],cwd=temporary,
                env=browser_environment,check=True,timeout=180)
            https_report=json.loads((Path(temporary)/'artifacts/https-api/licensed.json').read_text(encoding='utf-8'))
            if (not https_report.get('installed_wheel') or not https_report.get('licensed')
                    or https_report.get('passed_status_contracts') != 3
                    or not https_report.get('status_only_non_json_passed')
                    or not https_report.get('redirect_failed_without_follow')
                    or not https_report.get('untrusted_tls_failed_before_http')
                    or not https_report.get('cancelled_without_retry')
                    or https_report.get('actual_fixture_http_requests') != 4
                    or https_report.get('explicitly_confirmed_jobs') != 6
                    or https_report.get('secret_headers_sent') is not False
                    or not https_report.get('unsaved_confirmation_cleared')
                    or not https_report.get('older_backend_capability_fail_closed')
                    or https_report.get('ui_external_requests') or https_report.get('page_errors')
                    or https_report.get('test_socket_override') != 'owned_fixture_only'):
                raise ValueError('Installed HTTPS operator evidence is incomplete.')
            https_output=ROOT/'artifacts/https-api';https_output.mkdir(parents=True,exist_ok=True)
            (https_output/'installed-licensed.json').write_text(json.dumps(https_report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_commit': revision, 'files_verified': len(manifest['files']),
                      'installed_catalog': {'ui': 51, 'api': 34, 'database': 15},
                      'activation_enabled': False}, indent=2))


if __name__ == '__main__':
    check_release(sys.argv[1])
