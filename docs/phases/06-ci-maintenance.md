# Phase 6 follow-up: clean CI and current dependencies

Review branch: `phase/06-acceptance`, [PR #11](https://github.com/damogallagher/redpanda/pull/11). Damien reviews and merges.

## Failure and changes

The [reported main-branch run](https://github.com/damogallagher/redpanda/actions/runs/39478225848) failed on `119.99999999999999 == 120` in the Ollama request-contract test. Elapsed-time arithmetic makes exact equality unreliable with a real clock. Phase 6 commit `8ea8ec4` already supplies a fixed clock for that contract test; production timeouts and separate elapsed-time tests remain intact. Re-running the old commit would still run its old test/workflow; the correction reaches main when this PR is merged.

All three actions are updated to their latest official stable releases as checked on 20 October 2026, pinned by full commit SHA: checkout 7.0.1, setup-uv 10.3.0, upload-artifact 7.0.2. All declare Node 24 directly. This replaces the old artifact action that produced Node 20, `punycode`, and `url.parse()` deprecation messages. Checkout explicitly uses `main` for Git initialization, resolving the initial-branch migration hint. Missing test artifacts now fail the upload step instead of producing a warning.

Updated FastAPI 0.156.0 → 0.156.1 and uv 0.13.3 → 0.13.4 in CI/build/current instructions. uv's patch includes an upstream certificate-store security fix. Added dev-only `httpx2==2.15.1`, the supported transport selected by Starlette's TestClient. Application HTTPX remains at its current stable 0.28.1. Python warnings now become test failures through `filterwarnings = ["error"]`; no ignore filters or Node warning suppression are added.

Reviewed every registry package in the refreshed lockfile, plus Hatchling and uv: **41 packages**, all matching current PyPI releases. The [machine-readable review](../evidence/actions-dependency-review.json) records each package, action SHA, and primary source. Infrastructure/runtime major versions remain the project's explicit supported choices; this is not a major-version migration or a claim that the outstanding Debian advisories are fixed. Historical evidence retains the versions originally tested.

## How to verify

From the repository root, with Docker running:

```sh
make test UV='uvx --from uv==0.13.4 uv'
```

Expected: exit 0; 416 unit tests, 29 integration/configuration checks, 72 native Connect cases; all 1,082 application lines and 276 branches covered, no missing/excluded coverage and no Python warnings. Reports are in `reports/` and the `phase-6-test-reports` CI artifact. No model, API key, or live feed is used. Tests create and remove only disposable infrastructure.

To inspect a completed GitHub run (replace `RUN_ID` with the run linked from PR #11):

```sh
gh run view RUN_ID --repo damogallagher/redpanda
gh run view RUN_ID --repo damogallagher/redpanda --log
gh run download RUN_ID --repo damogallagher/redpanda \
  --name phase-6-test-reports --dir /tmp/redpanda-ci-reports
```

Expect a successful job and artifact upload, zero warning annotations, and no emitted deprecation/build/test warnings in the log. A command argument such as tar's `--warning=no-unknown-keyword` is not an emitted warning. The intentionally failing demonstration remains separate (`make demo-test-failure`); it must exit nonzero.

## Observed results

The 53 affected API/model adapter tests passed with warnings treated as errors. The full local gate passed on implementation `55fdf4e`: 416 unit tests, 29 integration/configuration checks, 72 Connect cases; 100% line and branch coverage with no exclusions and zero emitted warnings. A fully hashed lock export passed pip-audit with 36 installed packages, zero vulnerabilities and zero skips. The 41-package version review also covers platform-specific lock entries and build tools; these counts measure different scopes.

GitHub [run 39485899270](https://github.com/damogallagher/redpanda/actions/runs/39485899270) passed on `55fdf4e` in 5 minutes 22 seconds. All action steps and artifact upload succeeded. The check-run annotations API returned an empty array; the full log contains zero emitted warnings/deprecations. Downloaded JUnit/coverage artifacts independently confirm the same passing counts and 100% lines/branches. Closing commits update documentation/conversation only; the tested workflow and dependency files remain identical. The [verification JSON](../evidence/actions-verification.json) records actual commands, commits and results; original assignment, private profile hashes/permissions and reserved README sections remain unchanged. No paid model calls were made for this maintenance.
