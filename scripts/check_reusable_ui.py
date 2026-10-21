"""Verify existing UI definitions across controlled names and project mappings."""

from dataclasses import asdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from adaptive_qa.browser_process import run_isolated_sample_test
from adaptive_qa.models import TestStatus
from adaptive_qa.local_browser import VARIANT_CHECKS


def main():
    root = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(('127.0.0.1', 8000), partial(SimpleHTTPRequestHandler, directory=str(root / 'samples/web')))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        for site in ('english', 'turkish', 'mapped'):
            for case_id in VARIANT_CHECKS:
                result = run_isolated_sample_test(case_id, site=site)
                assert result.status == TestStatus.PASSED, (site, result)
                assert result.evidence_paths and all(Path(path).is_file() for path in result.evidence_paths)
                results.append({'site': site, **asdict(result)})
        path = root / 'artifacts/matching/reusable.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'runs': len(results), 'passed': True, 'results': results}, indent=2), encoding='utf-8')
        print(f'{len(results)} isolated reusable UI runs passed.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
