"""Real DOM acceptance for URL-independent read-only form matching."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from adaptive_qa.form_checks import check_login_form, check_search_form
from adaptive_qa.element_models import ElementMapping, LocatorSpec, LocatorStrategy, ProjectElementMappings
from adaptive_qa.ui_bindings import ElementBindingError


def main():
    login = '<form><label>Username<input name="user"></label><label>Password<input type="password"></label><button>Sign in</button></form>'
    search = '<form><label>Search products<input type="search"></label><button>Search</button></form>'
    outcomes, requests = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.route('**/*', lambda route: (requests.append(route.request.method), route.abort()))
            def verify(name, html, check, expected='passed', **kwargs):
                page.set_content(html)
                page.evaluate('''() => {window.formWrites=0;
                    document.addEventListener('submit',e=>{window.formWrites++;e.preventDefault()});
                    document.addEventListener('input',()=>window.formWrites++);
                    document.addEventListener('click',()=>window.formWrites++);}''')
                try:
                    check(page, **kwargs)
                except ElementBindingError as error:
                    status = error.result.status.value
                except AssertionError:
                    status = 'failed'
                except ValueError:
                    status = 'rejected'
                else:
                    status = 'passed'
                assert status == expected, (name, status, expected)
                assert page.evaluate('window.formWrites') == 0
                assert page.locator('input').evaluate_all('els=>els.every(el=>!el.value)')
                outcomes.append({'scenario': name, 'status': status})
            verify('English login', login, check_login_form)
            verify('Turkish login', login.replace('Username', 'Kullanıcı adı').replace('Password', 'Şifre').replace('Sign in', 'Giriş yap'), check_login_form)
            verify('Email and alternative login button', login.replace('Username', 'Email address').replace('Sign in', 'Log in'), check_login_form)
            verify('English search', search, check_search_form)
            verify('Turkish search', search.replace('Search products', 'Ürün ara').replace('Search', 'Ara'), check_search_form)
            verify('Ambiguous login forms', login+login, check_login_form, 'ambiguous')
            verify('Alternative buttons do not choose first', login.replace('</form>', '<button>Login</button></form>'), check_login_form, 'ambiguous')
            verify('Missing password', login.replace('Password', 'Unknown'), check_login_form, 'missing')
            verify('Unmasked password', login.replace('type="password"', 'type="text"'), check_login_form, 'failed')
            verify('Different forms cannot combine', login.replace('<button>', '</form><form><button>'), check_login_form, 'missing')
            verify('Other form email is excluded', login+'<form><label>Email<input type="email"></label><button>Register</button></form>', check_login_form)
            verify('Hidden duplicate excluded', login+'<div hidden>'+login+'</div>', check_login_form)
            verify('Ambiguous search forms', search+search, check_search_form, 'ambiguous')
            verify('Disabled login button', login.replace('<button>', '<button disabled>'), check_login_form, 'failed')
            verify('Non-submit search button', search.replace('<button>', '<button type="button">'), check_search_form, 'failed')
            mapped = ProjectElementMappings('owned', tuple(ElementMapping(key, (LocatorSpec(LocatorStrategy.TEST_ID, key),))
                for key in ('login.username', 'login.password', 'login.submit')))
            custom = '<form><input data-testid="login.username"><input data-testid="login.password" type="password"><button data-testid="login.submit">Continue</button></form>'
            verify('Explicit project replacement', custom, check_login_form, project_id='owned', mappings=mapped)
            verify('Foreign mapping rejected', custom, check_login_form, 'rejected', project_id='other', mappings=mapped)
            assert not requests
        finally:
            browser.close()
    output = Path('artifacts/matching')
    output.mkdir(parents=True, exist_ok=True)
    report = {'outcomes': outcomes, 'network_requests': len(requests), 'input_click_submit_events': 0,
              'catalog_cases_added': 0, 'dashboard_activation': False}
    (output/'general-form-checks.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'scenarios': len(outcomes), 'network_requests': 0, 'input_click_submit_events': 0}))


if __name__ == '__main__':
    main()
