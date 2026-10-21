"""Verify an explicit no-results search binding across real local UI and API."""

from dataclasses import asdict, replace
import json
from pathlib import Path
from threading import Thread
from uuid import uuid4

from adaptive_qa.api_catalog import API_BY_ID
from adaptive_qa.api_models import ApiConfiguration
from adaptive_qa.browser_process import run_isolated_sample_test
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestStatus
from adaptive_qa.sample_api import SampleApiHandler, create_sample_api
from adaptive_qa.sample_data import SampleData
from adaptive_qa.ui_api_bridge import UiApiBinding, validate_ui_api


class CombinedHandler(SampleApiHandler):
    page = (Path(__file__).resolve().parents[1] / 'samples/web/index.html').read_bytes()

    def do_GET(self):
        if self.path == '/':
            self._record()
            self._respond(200, self.page, raw=True, media='text/html; charset=utf-8')
        else:
            super().do_GET()


def main():
    server = create_sample_api(uuid4().hex, handler=CombinedHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        ui_result = run_isolated_sample_test('SEARCH-002')
        assert ui_result.status == TestStatus.PASSED, ui_result
        query = SampleData().search_query
        api = API_BY_ID['API-006']
        api = replace(api, request=replace(api.request, query=(('q', query),)))
        binding = UiApiBinding('local-demo', 'SEARCH-002', ('API-006',))
        configuration = ApiConfiguration(ProjectConfig('local-demo', 'Local UI/API',
            'http://127.0.0.1:8000', ('127.0.0.1',)))
        passed = validate_ui_api(binding, ui_result, (api,), configuration)
        assert passed.result.status == TestStatus.PASSED
        before = len(server.operations)
        blocked_ui = validate_ui_api(binding, replace(ui_result, status=TestStatus.FAILED), (api,), configuration)
        blocked_config = validate_ui_api(binding, ui_result, (api,), None)
        assert blocked_ui.result.status == blocked_config.result.status == TestStatus.BLOCKED
        assert len(server.operations) == before
        failed = validate_ui_api(binding, ui_result, (replace(api, expected_status=503),), configuration)
        assert failed.result.status == TestStatus.FAILED
        assert failed.ui_result.status == TestStatus.PASSED
        path = Path('artifacts/bridge/report.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'checks': 4, 'passed': True, 'results': [
            asdict(item) for item in (passed, blocked_ui, blocked_config, failed)]}, indent=2), encoding='utf-8')
        print('Four explicit UI/API binding checks passed without altering layer outcomes.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
