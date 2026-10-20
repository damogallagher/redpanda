# Dependency version review

Reviewed on 20 October 2026 against merged Phase 1 (`62f2330`).
This records recommendations; no runtime versions were changed or retested in this review.

## PostgreSQL

Keep major version 16 for this exercise: the [original assignment](assignment/fde-take-home-exercise.md#stack-all-free-all-local-all-open-source) explicitly lists `postgres:16`. PostgreSQL 16 is supported through 9 November 2028. The upstream [versioning policy](https://www.postgresql.org/support/versioning/) recommends the current minor release within the chosen major.

The Compose pin is **16.14-bookworm**. It should be updated to **16.15-bookworm**, with a verified multi-architecture digest, before submission. This corrects a missed maintenance update in the Phase 1 selection. The upstream [security list](https://www.postgresql.org/support/security/) includes fixes in 16.15. PostgreSQL 17 is also supported, but the exercise has no identified requirement for its features. The current upstream stable major is 18; 19 is still a release candidate on the review date.

Changing a PostgreSQL major version requires a data migration. Never just change 16 to 17 and reuse the existing data directory. Review the release notes even for maintenance upgrades.

## Direct dependencies and infrastructure

| Component | Current project pin | Verified upstream information | Recommendation |
|---|---|---|---|
| Python | 3.13.16 | Latest 3.13 patch; 3.13 receives security fixes until October 2029. Latest feature release is 3.15.0. | Retain the tested, supported runtime for this exercise; a newer feature release needs a separate compatibility check. |
| HTTPX / Pydantic | 0.28.1 / 2.14.1 | Match current PyPI releases. | Keep. |
| pytest / pytest-cov | 9.1.1 / 7.1.0 | Match current PyPI releases. | Keep. |
| mypy / Ruff | 2.4.0 / 0.17.1 | Match current PyPI releases. | Keep. |
| Hatchling | 1.27.0 | Current PyPI release is 1.32.4. | Update and verify wheel/container builds. |
| uv | 0.13.1 in Docker and CI | Current PyPI release is 0.13.3. | Update Docker and CI together, then verify frozen installs and builds. |
| Redpanda | v26.2.5 | Matches the current official quickstart. GitHub's latest-release endpoint returned v26.2.2, so that endpoint alone does not establish the newest broker patch. | Keep the tested quickstart pin; check official release notes before changing it. |
| Ollama | 0.40.6 | Matches the project's latest stable GitHub release. | Keep. |
| Redpanda Connect | Not yet included in Phase 1 | Latest stable GitHub release is 4.114.0. | Recheck, pin, and test when implementing Phase 2. |

Sources checked directly:

- [Python downloads and support status](https://www.python.org/downloads/) and [3.13.16 release](https://www.python.org/downloads/release/python-31316/).
- PyPI project JSON metadata (`https://pypi.org/pypi/<package>/json`) for [HTTPX](https://pypi.org/project/httpx/), [Pydantic](https://pypi.org/project/pydantic/), [pytest](https://pypi.org/project/pytest/), [pytest-cov](https://pypi.org/project/pytest-cov/), [mypy](https://pypi.org/project/mypy/), [Ruff](https://pypi.org/project/ruff/), [Hatchling](https://pypi.org/project/hatchling/), and [uv](https://pypi.org/project/uv/).
- [Redpanda quickstart](https://docs.redpanda.com/streaming/current/get-started/quick-start/), [Redpanda GitHub releases](https://github.com/redpanda-data/redpanda/releases), [Ollama 0.40.6](https://github.com/ollama/ollama/releases/tag/v0.40.6), and [Connect 4.114.0](https://github.com/redpanda-data/connect/releases/tag/v4.114.0).

This is a direct-dependency and infrastructure version review, not a complete vulnerability audit of transitive packages, operating-system packages, or CI actions.

## Update and verification approach

Prefer supported stable versions, apply maintenance/security fixes, and pin exact versions and container digests so reviewers reproduce the tested environment. Avoid floating `latest` tags and prereleases. Choose major upgrades for a concrete need, support lifecycle, or demonstrated compatibility.

For the recommended PostgreSQL, Hatchling, and uv updates:

1. Create a maintenance branch from merged main. Read upstream release notes and verify the PostgreSQL image supports both ARM64 and AMD64.
2. Change the exact pins and any affected lockfile metadata. Preserve existing data volumes and credentials.
3. Run `make verify-phase-1`. All unit tests must pass with 100% line and branch coverage; all three infrastructure tests and the packaged-container check must pass.
4. Check the PostgreSQL version in a disposable test instance. If validating an existing-data upgrade, create a separate disposable 16.14 database with a sentinel row, stop it, start 16.15 using that test volume, and confirm the row and migration marker remain intact. Do not use the user's demo volume for this test.
5. Record the actual commands, tested commit, results, and image digest in the phase evidence. Open a PR for Damien to review and merge.

These upgrade steps are recommendations, not completed test results. The existing Phase 1 evidence applies to its recorded versions.
