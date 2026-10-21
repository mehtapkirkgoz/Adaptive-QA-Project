"""Browser verification for the controlled local sample application."""

import argparse
from time import perf_counter

from playwright.sync_api import Error, Page, Route, expect, sync_playwright

from adaptive_qa.config import ProjectConfig
from adaptive_qa.catalog import TEST_CASES
from adaptive_qa.egress import DestinationGuard, EgressProxy, chromium_proxy_options
from adaptive_qa.models import TestResult, TestStatus
from adaptive_qa.targets import validate_local_sample_target
from adaptive_qa.storage import save_result
from adaptive_qa.smoke_checks import SMOKE_CHECKS
from adaptive_qa.ui_bindings import ElementBindingError, REUSABLE_CHECKS, SITE_PATHS
from adaptive_qa.element_models import MatchStatus
from adaptive_qa.extra_ui_checks import EXTRA_CHECKS
from pathlib import Path
from uuid import uuid4

VARIANT_CHECKS = {**REUSABLE_CHECKS, **EXTRA_CHECKS}


def _capture_evidence(page: Page, evidence_path: Path) -> None:
    """Capture optional evidence without changing the test outcome."""
    temporary_path = evidence_path.with_suffix(".tmp")
    try:
        image = page.screenshot(type="png", full_page=True, timeout=5_000)
        temporary_path.write_bytes(image)
        temporary_path.replace(evidence_path)
    except (Error, OSError):
        pass
    finally:
        # Publish only complete files; partial writes remain unlinked.
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


def _verify_sample_page(evidence_path: Path, case_id: str = "LOGIN-001", *, site: str = "root") -> None:
    project = ProjectConfig(
        project_id="local-demo",
        name="Local Sample Application",
        base_url="http://127.0.0.1:8000",
        allowed_hosts=("127.0.0.1",),
    )
    validate_local_sample_target(project.base_url, project)

    def handle_request(route: Route) -> None:
        try:
            if route.request.method not in ("GET", "HEAD"):
                raise ValueError("Data-changing requests are disabled.")
            validate_local_sample_target(route.request.url, project)
        except ValueError:
            route.abort("blockedbyclient")
            return

        route.continue_()

    guard = DestinationGuard(project, local_sample=True)
    with EgressProxy(guard) as proxy, sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            timeout=10_000,
            **chromium_proxy_options(proxy.url),
        )

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
                try:
                    response = page.goto(
                        project.base_url + SITE_PATHS[site],
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

                    if site != 'root':
                        from adaptive_qa.crawler import CrawlResult
                        from adaptive_qa.page_collector import collect_page_snapshot
                        from adaptive_qa.planning import PlanDecision, build_test_plan
                        definition = next(case for case in TEST_CASES if case.case_id == case_id)
                        snapshot = collect_page_snapshot(page)
                        plan = build_test_plan(CrawlResult((snapshot,), 1, ()), (definition,), project)
                        if plan.cases[0].decision != PlanDecision.SELECTED or plan.cases[0].target_url != snapshot.url:
                            raise RuntimeError('Fixture prerequisites do not support the selected case.')
                        VARIANT_CHECKS[case_id](page)
                    else:
                        SMOKE_CHECKS[case_id](page)
                except (AssertionError, Error, RuntimeError):
                    _capture_evidence(page, evidence_path)
                    raise
                else:
                    _capture_evidence(page, evidence_path)

            finally:
                context.close()
        finally:
            browser.close()


def run_sample_test(case_id: str, *, site: str = "root") -> TestResult:
    """Execute a registered sample check in a fresh browser context."""
    definition = next((case for case in TEST_CASES if case.case_id == case_id), None)
    if site not in SITE_PATHS or (site != 'root' and case_id not in VARIANT_CHECKS):
        return TestResult(case_id, TestStatus.BLOCKED, 0.0, 'No controlled fixture executor binding is registered.')
    if case_id not in SMOKE_CHECKS or definition is None:
        return TestResult(case_id, TestStatus.BLOCKED, 0.0, "No sample executor is registered.")
    if definition.changes_data:
        return TestResult(case_id, TestStatus.BLOCKED, 0.0, "Data-changing sample tests are disabled.")
    started_at = perf_counter()

    evidence_directory = Path("artifacts/screenshots")
    evidence_directory.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_directory / f"{uuid4().hex}.png"

    try:
        if site != 'root':
            _verify_sample_page(evidence_path, case_id=case_id, site=site)
        elif case_id == "LOGIN-001":
            _verify_sample_page(evidence_path)
        else:
            _verify_sample_page(evidence_path, case_id=case_id)
    except AssertionError:
        status = TestStatus.FAILED
        message = "The sample page or selected check did not meet expectations."
    except ElementBindingError as error:
        status = TestStatus.BLOCKED if error.result.status in (MatchStatus.MISSING, MatchStatus.AMBIGUOUS) else TestStatus.ERROR
        message = f'Element binding {error.result.status.value}: {error.result.logical_name}.'
    except (Error, RuntimeError):
        status = TestStatus.ERROR
        message = "Browser execution or sample page loading failed."
    else:
        status = TestStatus.PASSED
        message = "The sample page and selected check passed."

    return TestResult(
        case_id=case_id,
        status=status,
        duration_seconds=perf_counter() - started_at,
        message=message,
        evidence_paths=(evidence_path.as_posix(),) if evidence_path.is_file() else (),
    )


def run_login_form_test() -> TestResult:
    """Compatibility entry point for the existing login worker."""
    return run_sample_test("LOGIN-001")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a controlled sample smoke check.")
    parser.add_argument("--case", choices=sorted(SMOKE_CHECKS), default="LOGIN-001")
    args = parser.parse_args()
    result = run_sample_test(args.case)
    print(result)

    result_path = save_result(result)
    print(f"Result saved to: {result_path}")

    if result.status != TestStatus.PASSED:
        raise SystemExit(1)
