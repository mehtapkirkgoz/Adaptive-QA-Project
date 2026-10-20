"""Verify matching with real Chromium and fully intercepted offline pages."""

from dataclasses import asdict
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy, MatchStatus, ProjectElementMappings
from adaptive_qa.element_matching import match_element


def main():
    reports = []
    role = lambda value: LocatorSpec(LocatorStrategy.ROLE, value, 'button')
    mapping = ElementMapping('login.submit', (role('Sign in'), role('Giriş yap')))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(service_workers='block')
            context.route('**/*', lambda route: route.fulfill(status=200, body='<html></html>', content_type='text/html'))
            page = context.new_page()
            page.goto('http://127.0.0.1:8000')
            def check(name, html, expected, selected=mapping):
                page.set_content(html)
                bound = match_element(page, selected)
                try:
                    assert bound.result.status == expected, (name, bound.result)
                    assert (bound.handle is not None) == (expected == MatchStatus.MATCHED)
                    reports.append({'name': name, **asdict(bound.result)})
                finally:
                    bound.close()
            check('english', '<button>Sign in</button>', MatchStatus.MATCHED)
            check('turkish', '<button>Giriş yap</button>', MatchStatus.MATCHED)
            check('ambiguous alternatives', '<button>Sign in</button><button>Giriş yap</button>', MatchStatus.AMBIGUOUS)
            check('duplicate name', '<button>Sign in</button><button>Sign in</button>', MatchStatus.AMBIGUOUS)
            check('missing', '<button>Register</button>', MatchStatus.MISSING)
            check('exact name', '<button>Sign in now</button>', MatchStatus.MISSING)
            check('hidden', '<button hidden>Sign in</button><button>Giriş yap</button>', MatchStatus.MATCHED)
            check('inert', '<div inert><button>Sign in</button></div>', MatchStatus.MISSING)
            overlap = ElementMapping('login.submit', (role('Sign in'), LocatorSpec(LocatorStrategy.TEST_ID, 'submit')))
            check('overlap deduplication', '<button data-testid="submit">Sign in</button>', MatchStatus.MATCHED, overlap)
            scoped = ElementMapping('login.submit', mapping.locators, 'login')
            check('scope', '<form data-testid="login"><button>Sign in</button></form><button>Sign in</button>', MatchStatus.MATCHED, scoped)
            check('missing scope', '<button>Sign in</button>', MatchStatus.ERROR, scoped)
            check('duplicate scope', '<form data-testid="login"></form>' * 2, MatchStatus.ERROR, scoped)
            labeled = ElementMapping('login.username', (LocatorSpec(LocatorStrategy.LABEL, 'Email'),))
            check('label', '<label>Email<input></label>', MatchStatus.MATCHED, labeled)
            override = ElementMapping('login.submit', (LocatorSpec(LocatorStrategy.TEST_ID, 'custom'),))
            configured = ProjectElementMappings('demo', (override,)).resolve(mapping, project_id='demo')
            check('project replacement', '<button>Sign in</button><button data-testid="custom">Enter</button>', MatchStatus.MATCHED, configured)
            check('disabled is visible', '<button disabled>Sign in</button>', MatchStatus.MATCHED)
            check('candidate limit', '<button>Sign in</button>' * 201, MatchStatus.ERROR)
            page.set_content('<button>Sign in</button>')
            bound = match_element(page, mapping)
            page.set_content('<button>Sign in</button>')
            try:
                assert not bound.handle.evaluate('el => el.isConnected')
                reports.append({'name': 'replacement does not retarget', 'status': 'passed'})
            finally:
                bound.close()
            page.close()
            assert match_element(page, mapping).result.status == MatchStatus.ERROR
            reports.append({'name': 'closed page', 'status': 'passed'})
        finally:
            browser.close()
    destination = Path('artifacts/matching/report.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({'checks': len(reports), 'passed': True, 'results': reports}, indent=2), encoding='utf-8')
    print(f'{len(reports)} Chromium matching checks passed.')


if __name__ == '__main__':
    main()
