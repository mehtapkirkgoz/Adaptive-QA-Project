"""Browser verification for the controlled local sample application."""

from playwright.sync_api import Route, expect, sync_playwright

from adaptive_qa.config import ProjectConfig
from adaptive_qa.targets import validate_local_sample_target


def verify_sample_page() -> None:
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

                print("Sample page verification passed.")
            finally:
                context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    verify_sample_page()