"""Run 20 controlled API cases and persist safe outcome-only artifacts."""

from dataclasses import asdict
import json
import os
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from uuid import uuid4

from adaptive_qa.api_catalog import API_CASES
from adaptive_qa.api_models import ApiConfiguration
from adaptive_qa.api_process import run_isolated_api_case
from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestStatus
from adaptive_qa.sample_api import create_sample_api
from adaptive_qa.secrets import SecretReference
from adaptive_qa.storage import save_result


def main():
    token = uuid4().hex + uuid4().hex
    server = create_sample_api(token)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        configuration = ApiConfiguration(ProjectConfig('local-api', 'Local API',
            'http://127.0.0.1:8000', ('127.0.0.1',), allow_data_changes=True),
            SecretReference('QA_SAMPLE_API_TOKEN'))
        with patch.dict(os.environ, {'QA_SAMPLE_API_TOKEN': token}):
            for case in API_CASES:
                result = run_isolated_api_case(case, configuration)
                assert result.status == TestStatus.PASSED, result
                results.append(asdict(result))
                save_result(result, Path('artifacts/api/results'))
        report = {'cases': len(results), 'passed': len(results), 'results': results,
                  'operations': server.operations, 'fixture': 'stateless_local_api'}
        serialized = json.dumps(report, indent=2)
        assert token not in serialized and 'Authorization' not in serialized
        path = Path('artifacts/api/report.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding='utf-8')
        print(f'{len(results)} controlled API cases passed; reports contain outcomes only.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
