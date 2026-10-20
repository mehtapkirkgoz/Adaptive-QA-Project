"""Browser verification for the controlled local sample application."""

from time import perf_counter

from playwright.sync_api import Error, Route, expect, sync_playwright

from adaptive_qa.config import ProjectConfig
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.targets import validate_local_sample_target
from adaptive_qa.storage import save_result
from pathlib import Path
from uuid import uuid4


def _verify_sample_page(evidence_path: Path) -> None:
    project = ProjectConfig(
        project_id="local-demo",
        name="Local Sample Application",
        base_url="http://127.0.0.1:8000",
        allowed_hosts=("127.0.0.1",),
    )
    validate_local_sample_target(project.base_url, project)

    def handle_request(route: Route) -> None:
        try:
            validate_local_sample_target(route.request.url, project)
        except ValueError:
            route.abort("blockedbyclient")
            return

        route.continue_()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(timeout=10_000)

        try:
            context = browser.new_context(
                service_workers="block",
                accept_downloads=False,
            )

            try:
                context.set_default_timeout(5_000)
                context.set_default_navigation_timeout(10_000)
                context.route("**/*", handle_request)
                context.route_web_socket(
                    "**/*",
                    lambda connection: connection.close(),
                )

                page = context.new_page()
                response = page.goto(
                    project.base_url,
                    wait_until="domcontentloaded",
                )

                if response is None or response.status != 200:
                    raise RuntimeError(
                        "Sample page did not return HTTP 200."
                    )

                expect(page).to_have_title("Adaptive QA Sample")
                expect(
                    page.get_by_role(
                        "heading",
                        name="Adaptive QA Sample",
                        exact=True,
                    )
                ).to_be_visible()

                login_form = page.locator("#login-form")

                username_field = login_form.get_by_label(
                    "Username",
                    exact=True,
                )
                password_field = login_form.get_by_label(
                    "Password",
                    exact=True,
                )
                submit_button = login_form.get_by_role(
                    "button",
                    name="Sign in",
                    exact=True,
                )

                expect(username_field).to_be_visible()
                expect(password_field).to_be_visible()
                expect(password_field).to_have_attribute(
                    "type",
                    "password",
                )
                expect(submit_button).to_be_visible()
                page.screenshot(
                    path=str(evidence_path),
                    full_page=True,
                    timeout=5_000,
                )

            finally:
                context.close()
        finally:
            browser.close()


def run_login_form_test() -> TestResult:
    """Execute the local login form test and return a structured result."""
    started_at = perf_counter()

    evidence_directory = Path("artifacts/screenshots")
    evidence_directory.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_directory / f"{uuid4().hex}.png"

    try:
        _verify_sample_page(evidence_path)
    except AssertionError:
        status = TestStatus.FAILED
        message = "The sample page or login form did not meet expectations."
    except (Error, RuntimeError):
        status = TestStatus.ERROR
        message = "Browser execution or sample page loading failed."
    else:
        status = TestStatus.PASSED
        message = "The sample page and login form checks passed."

    return TestResult(
        case_id="LOGIN-001",
        status=status,
        duration_seconds=perf_counter() - started_at,
        message=message,
        evidence_paths=(evidence_path.as_posix(),) if evidence_path.is_file() else (),
    )


if __name__ == "__main__":
    result = run_login_form_test()
    print(result)

    result_path = save_result(result)
    print(f"Result saved to: {result_path}")

    if result.status != TestStatus.PASSED:
        raise SystemExit(1)