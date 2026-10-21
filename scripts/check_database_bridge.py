"""Real local UI prerequisite, authorized API record creation, and SQLite readback."""

from contextlib import closing
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Thread
from uuid import uuid4

from check_ui_api_bridge import CombinedHandler
from adaptive_qa.api_models import ApiCase, ApiConfiguration, ApiRequest, HttpMethod, JsonCheck, JsonOperator
from adaptive_qa.api_process import run_isolated_api_case
from adaptive_qa.browser_process import run_isolated_sample_test
from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_bridge import DatabaseBinding, validate_ui_api_database
from adaptive_qa.database_models import DatabaseCase, DatabaseCheck, DatabaseConfiguration, DatabaseOperator, QueryTemplate
from adaptive_qa.models import TestCase, TestStatus, TestType
from adaptive_qa.sample_api import create_sample_api
from adaptive_qa.sample_database import prepare_sample_database
from adaptive_qa.secrets import SecretReference


class RecordHandler(CombinedHandler):
    def do_POST(self):
        self._record()
        if self.path != '/api/fixture-order':
            self._respond(404, {'error': 'not_found'})
            return
        if self.headers.get('Authorization') != 'Bearer ' + self.server.token:
            self._respond(403, {'error': 'forbidden'})
            return
        lengths = self.headers.get_all('Content-Length', [])
        if self.headers.get('Transfer-Encoding') or lengths != ['2'] or self.rfile.read(2) != b'{}':
            self._respond(400, {'error': 'invalid_fixture_request'})
            return
        with closing(sqlite3.connect(self.server.fixture_path)) as connection, connection:
            connection.execute('INSERT INTO orders VALUES (?, ?, ?, ?)',
                               (3, 'bridge-user', 'created', None))
        self._respond(201, {'id': 3, 'status': 'created'})


def main():
    variables = ('QA_BRIDGE_DATABASE_PATH', 'QA_BRIDGE_CREATE_TOKEN')
    previous = {key: os.environ.get(key) for key in variables}
    with TemporaryDirectory(prefix='adaptive-qa-db-bridge-') as temporary:
        path = prepare_sample_database(Path(temporary) / 'bridge.db')
        token = uuid4().hex
        os.environ.update(dict(zip(variables, (str(path), token))))
        server = create_sample_api(token, handler=RecordHandler)
        server.fixture_path = path
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            project = ProjectConfig('local-database', 'Local database bridge',
                'http://127.0.0.1:8000', ('127.0.0.1',), allow_data_changes=True)
            api_config = ApiConfiguration(project, SecretReference(variables[1]))
            definition = TestCase('API-DB-CREATE', 'Create fixture order', TestType.API, (),
                ('Create a fixed fake order in the disposable fixture.',), 'Order creation returns 201.', changes_data=True)
            api_case = ApiCase(definition, ApiRequest('/api/fixture-order', HttpMethod.POST,
                body_json='{}', use_authentication=True), 201,
                (JsonCheck(('status',), JsonOperator.EQUALS, 'created'),))
            db_definition = TestCase('DB-BRIDGE', 'Created order persists', TestType.DATABASE, (),
                ('Read the API-created record.',), 'Created status and fake owner are persisted.')
            db_case = DatabaseCase(db_definition,
                QueryTemplate(project.project_id, 'created_order',
                    'SELECT customer, status FROM orders WHERE id=:id', ('id',)), (('id', 3),),
                (DatabaseCheck(DatabaseOperator.ROW_COUNT, 1),
                 DatabaseCheck(DatabaseOperator.CELL_EQUALS, 'bridge-user'),
                 DatabaseCheck(DatabaseOperator.CELL_EQUALS, 'created', column=1)))
            db_config = DatabaseConfiguration(project, SecretReference(variables[0]))
            binding = DatabaseBinding(project.project_id, 'SEARCH-002', definition.case_id, db_definition.case_id)
            # Seed data does not contain this order; prove absence before creation.
            with closing(sqlite3.connect(path)) as connection:
                assert connection.execute('SELECT count(*) FROM orders WHERE id=3').fetchone()[0] == 0
            ui = run_isolated_sample_test('SEARCH-002')
            assert ui.status == TestStatus.PASSED, ui
            # Existing mutation policy must prevent record creation when disabled.
            denied = run_isolated_api_case(api_case, replace(api_config,
                project=replace(project, allow_data_changes=False)))
            assert denied.status == TestStatus.BLOCKED
            before = len(server.operations)
            blocked = validate_ui_api_database(binding, ui, denied, db_case, db_config,
                fixture_root=temporary, database_runner=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
            assert blocked.status == TestStatus.BLOCKED and len(server.operations) == before
            api = run_isolated_api_case(api_case, api_config) if ui.status == TestStatus.PASSED else denied
            assert api.status == TestStatus.PASSED, api
            passed = validate_ui_api_database(binding, ui, api, db_case, db_config, fixture_root=temporary)
            assert passed.status == TestStatus.PASSED, passed
            wrong = replace(db_case, checks=(DatabaseCheck(DatabaseOperator.CELL_EQUALS, 'wrong'),))
            failed = validate_ui_api_database(binding, ui, api, wrong, db_config, fixture_root=temporary)
            assert failed.status == TestStatus.FAILED and ui.status == api.status == TestStatus.PASSED
            report = json.dumps({'checks': 4, 'ui': asdict(ui), 'api': asdict(api),
                'database': [asdict(item) for item in (blocked, passed, failed)],
                'mutation_policy': asdict(denied)}, indent=2)
            assert token not in report and str(path) not in report and 'bridge-user' not in report
            destination = Path('artifacts/database/bridge.json')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(report, encoding='utf-8')
            print('Four UI/API/database controls passed; created record verified independently.')
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == '__main__':
    main()
