"""Run each database scenario in an isolated child and persist metadata only."""

from dataclasses import asdict
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from adaptive_qa.config import ProjectConfig
from adaptive_qa.database_catalog import DATABASE_CASES
from adaptive_qa.database_models import DatabaseConfiguration
from adaptive_qa.database_process import run_isolated_database_case
from adaptive_qa.models import TestStatus
from adaptive_qa.sample_database import prepare_sample_database
from adaptive_qa.secrets import SecretReference


def main():
    results = []
    variable = 'QA_SAMPLE_DATABASE_PATH'
    previous = os.environ.get(variable)
    try:
        with TemporaryDirectory(prefix='adaptive-qa-db-fixture-') as temporary:
            path = prepare_sample_database(Path(temporary) / 'fixture.db')
            original = path.read_bytes()
            os.environ[variable] = str(path)
            project = ProjectConfig('local-database', 'Local database',
                'http://127.0.0.1:8000', ('127.0.0.1',))
            config = DatabaseConfiguration(project, SecretReference(variable))
            for case in DATABASE_CASES:
                result = run_isolated_database_case(case, config, fixture_root=temporary)
                if result.status != TestStatus.PASSED:
                    raise RuntimeError(f'{result.case_id}: {result.status}: {result.message}')
                results.append(asdict(result))
            if path.read_bytes() != original:
                raise RuntimeError('Database checks changed the prepared fixture.')
            encoded = json.dumps({'case_count': len(results), 'results': results}, indent=2)
            if str(path) in encoded or 'SELECT ' in encoded or 'demo-user' in encoded:
                raise RuntimeError('Private fixture inputs escaped into results.')
    finally:
        if previous is None:
            os.environ.pop(variable, None)
        else:
            os.environ[variable] = previous
    destination = Path('artifacts/database/report.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(encoded, encoding='utf-8')
    print(f'{len(results)} isolated database cases passed; fixture unchanged and removed.')


if __name__ == '__main__':
    main()
