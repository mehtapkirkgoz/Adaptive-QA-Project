# Public Interface Demo

The owner selected a GitHub-hosted interface demo while real automation remains
local, and explicitly authorized making Adaptive-QA-Project public. No domain,
paid plan, external backend or customer-site execution is required for this demo.

## What Is Published

`npm run build:demo` creates frontend/dist-demo with relative asset paths suitable
for a GitHub Pages project subdirectory. Only this compiled directory is uploaded.
The demo contains synthetic projects, the accepted 100-case definition catalog,
search/layer filters and an explicitly illustrative report. It has no sign-in,
API access, persistent storage, target discovery or test execution. Sample targets
use reserved example.test names and are not contacted. The default `npm run build`
continues to build the authenticated local application.

The demo is labeled on every screen. Illustrative results are not acceptance
evidence or a run against a real site. Catalog counts are separate from applicable
test counts. Browser tests verify project-subpath assets, project selection,
51/34/15 filters, search/empty results, report labels, reload and responsive
widths 390/768/1440 with zero API/external requests or page errors.

## Publication

1. In repository Settings > Pages, select GitHub Actions as the source.
2. Run the `Publish interface demo to GitHub Pages` workflow on main.
3. Review its successful deployment and open the URL returned by GitHub.

The workflow is manual to avoid silently publishing every development push.
It builds only the demo and uploads only frontend/dist-demo. It never deploys
the Python API, databases, screenshots, credentials, workers or full repository.
Making the repository public separately exposes its tracked source/history, as
explicitly requested by the owner. Generated artifacts and local data remain
ignored. A basic token/private-key pattern and sensitive tracked-history path
check found no matches before the visibility change; this is not an exhaustive
secret-scanner or third-party security audit.

GitHub Pages supplies static hosting only. Python, database persistence and
Playwright workers continue locally. A future fully online automation service
needs a separately reviewed backend/worker runtime and hosting decision.

## Local Preview

```powershell
npm --prefix frontend run build:demo
python -m http.server 8790 --bind 127.0.0.1 --directory frontend/dist-demo
```

Open http://127.0.0.1:8790/. The working local application remains separate on
http://127.0.0.1:8765/ when its server is running. Demo/static deployment does not
mark Sprint 9's runtime, rollback, operations or integrated acceptance complete.
