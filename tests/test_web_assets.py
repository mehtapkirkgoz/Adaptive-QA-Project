"""Built UI files are public; local source and storage remain private."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from starlette.testclient import TestClient
from adaptive_qa.auth_store import AuthStore
from adaptive_qa.web_app import create_app


class WebAssetsTests(unittest.TestCase):
    def test_built_assets_security_and_private_file_denial(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            ui = root / 'ui'
            (ui / 'assets').mkdir(parents=True)
            (ui / 'index.html').write_text('<div>Local UI</div>', encoding='utf-8')
            (ui / 'assets/app.js').write_text('console.log("local");', encoding='utf-8')
            (ui / 'private.txt').write_text('PRIVATE_SENTINEL', encoding='utf-8')
            with TestClient(create_app(AuthStore(root / 'auth.sqlite'), ui_directory=ui), base_url='http://127.0.0.1:8765') as client:
                response = client.get('/')
                self.assertEqual(response.status_code, 200)
                self.assertIn('Local UI', response.text)
                self.assertEqual(response.headers['cache-control'], 'no-store')
                self.assertIn("script-src 'self'", response.headers['content-security-policy'])
                self.assertNotIn('unsafe-inline', response.headers['content-security-policy'])
                self.assertEqual(client.get('/assets/app.js').status_code, 200)
                for path in ('/private.txt', '/auth.sqlite', '/src/main.tsx', '/assets/%2e%2e/private.txt'):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 404)
                    self.assertNotIn('PRIVATE_SENTINEL', response.text)

    def test_invalid_explicit_build_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            auth = AuthStore(root / 'auth.sqlite')
            with TestClient(create_app(auth), base_url='http://127.0.0.1:8765') as client:
                self.assertEqual(client.get('/').status_code, 404)
            with self.assertRaises(ValueError):
                create_app(auth, ui_directory=root)
