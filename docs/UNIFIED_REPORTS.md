# Integrated local review reports

Owner request: show browser reviews and automatic test results in the existing
website workspace instead of separate temporary HTML pages.

The main local workspace now has a Reports link and an inline Browser reviews
section. A report selector, four outcome totals, status filter, per-check evidence
and scope notes all remain on the same page as URL checks and demo login history.
Imported observations are explicitly labelled as browser reviews; automatic engine
results and the accepted 100-case catalog are not rewritten or conflated with them.

Trusted offline imports validate bounded text, exact check fields, unique check
identities, supported statuses and an HTTPS target without credentials/query.
Counts are derived rather than trusted. Imports are idempotent, owner/project
scoped and stored locally in an additive dashboard_browser_reviews table. The
authenticated GET endpoint only reads already imported reports. There is no HTTP
import, target execution, automatic resubmission or central licensing contact.
Reading old databases without the new table returns an empty list without migration.
Reports are rendered as escaped React text, not HTML, and contain no active target links.

Customer review data remains in the local workspace, outside committed sources.
Preserve owner settings, existing result rows and pending work during preview
upgrades. Import the six existing reviews plus the additional blocked access
attempt only after taking a database backup and validating ownership. Keep old
standalone report URLs available for existing bookmarks; the main workspace is
the primary review interface.

Validation: focused ownership/authentication/idempotence/input tests and a real
browser proof exercise report selection, filtering, escaped HTML evidence,
reload non-replay, preserved configuration, mobile overflow and zero external or
mutation requests. The browser proof also runs against the installed release.
Accepted implementation: 50cac149fe7ee2f195d8cf1a543c90c8fe4c0ed0 / Core
40415364472, twelve successful jobs and twelve verified archives with 226 PNGs.
The 935-test regression and full installed release verification passed. Seven
existing local reviews were imported after backup and offline rehearsal, preserving
all twelve prior table digests. The main workspace and authenticated history showed
all seven reports; existing report bookmarks remained available, with no new target
requests. See evidence/unified-reports-ci-50cac14.json and
evidence/unified-reports-preview-50cac14.json. Later root-URL compatibility work is
tracked separately in ROOT_URL_COMPATIBILITY.md.
