# Actions and dependency maintenance — 20 October 2026

Context: follow-up to Phase 6, on `phase/06-acceptance`, review PR #11. Visible conversation only; tool findings are recorded separately in the maintenance guide. No credentials are logged.

## User

Also fix this github action: [https://github.com/damogallagher/redpanda/actions/runs/39478225848/job/118819667267](https://github.com/damogallagher/redpanda/actions/runs/39478225848/job/118819667267). I also see this warning on the github action:&#x20;

| [**foundation**](https://github.com/damogallagher/redpanda/actions/runs/39478225848/job/118819667267#step:11:2) | Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02. For more information see: [https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/) |
| --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

&#x20;Make sure ALL actions have NO warnings and are using the latest versions of libraries

## Assistant

> I’ll inspect that run and the current workflows, fix the failure, and update the actions and affected dependencies to current stable versions. I’ll run the checks, verify that the warnings are gone, and add the changes and prompt log to the open PR.

## Assistant

> The reported failure is a floating-point timing assumption in a test; Phase 6 already fixes it with a controlled clock. I also confirmed two separate deprecation warnings: the old artifact action and the API test client. I’m updating all three workflow actions and checking every locked Python dependency against its current release.

## Assistant

> The current releases include a new uv security patch and a FastAPI patch, so I’m including both. All three actions now use Node 24. The affected API/model tests pass without warnings, and I’ve made Python warnings fail the test suite so future deprecations cannot quietly accumulate.

## Assistant

> All 41 checked Python packages and build tools now match their latest stable releases. The full unit suite passes with 100% line and branch coverage and zero warnings. The Docker recovery checks are still running; next I’ll verify the updated workflow on GitHub, including its annotations and artifact upload.
