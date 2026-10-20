# Dependency version review

Reviewed on 20 October 2026 against merged Phase 1 (`62f2330`).
This historical snapshot records the recommendations made before implementation. The subsequent [dependency update record](phases/01-dependency-updates.md) documents their implementation and verification.

## PostgreSQL

Keep major version 16 for this exercise: the [original assignment](assignment/fde-take-home-exercise.md#stack-all-free-all-local-all-open-source) explicitly lists `postgres:16`. PostgreSQL 16 is supported through 9 November 2028. The upstream [versioning policy](https://www.postgresql.org/support/versioning/) recommends the current minor release within the chosen major.

The Compose pin at review was **16.14-bookworm**. The recommendation was to update to **16.15-bookworm**, with a verified multi-architecture digest, before submission. This corrects a missed maintenance update in the Phase 1 selection. The upstream [security list](https://www.postgresql.org/support/security/) includes fixes in 16.15. PostgreSQL 17 is also supported, but the exercise has no identified requirement for its features. The current upstream stable major is 18; 19 is still a release candidate on the review date.

Changing a PostgreSQL major version requires a data migration. Never just change 16 to 17 and reuse the existing data directory. Review the release notes even for maintenance upgrades.

## Direct dependencies and infrastructure

| Component | Project pin at review | Verified upstream information | Recommendation at review |
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

These steps were recommendations at the time of review. See the subsequent [dependency update record](phases/01-dependency-updates.md) for completed checks; the initial Phase 1 evidence continues to apply to its recorded versions.

## Phase 4 addition

Added `confluent-kafka==2.16.0` for the worker's Kafka boundary, with wheel hashes in `uv.lock`. The [official release on PyPI](https://pypi.org/project/confluent-kafka/2.16.0/) was published 7 October 2026 and includes Python 3.13 macOS ARM64 and Linux wheels. The small adapter uses explicit delivery callbacks and synchronous offset commits described in the [official client API](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html). Real Redpanda tests exercise publication, offset inspection, restart/replay, and shutdown. Existing dependency and image pins remain unchanged.

## Phase 6 security-driven application image update

The Python runtime remains 3.13.16 and all Python dependencies remain locked. The application Dockerfile now uses the official `3.13.16-slim-trixie` multi-architecture manifest and a separate build stage; the running image excludes pip/uv/ensurepip and source/build tooling. This targeted Debian 12 → 13 base change addresses findings from an actual container scan. Postgres remains 16.15 and its data format is unchanged. See the [security review](security-review.md) for the exact digest, scanner evidence, remaining advisories and scope. Native ARM64 and Ubuntu AMD64 acceptance are checked separately; model/provider versions remain explicit.

## Phase 6 CI follow-up — 20 October 2026

Rechecked **all 39 registry packages in `uv.lock`, plus Hatchling and uv**, against official PyPI metadata. All 41 match current stable releases after the update. See the [complete version/source list](evidence/actions-dependency-review.json) and [verification record](phases/06-ci-maintenance.md). This is a dated review; exact pins deliberately do not change automatically on release day.

| Component | Before → current | Source / reason |
|---|---|---|
| actions/checkout | 5 → 7.0.1 | [Official release](https://github.com/actions/checkout/releases/tag/v7.0.1); Node 24, full commit pin |
| astral-sh/setup-uv | 7 → 10.3.0 | [Official release](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.0); Node 24, full commit pin |
| actions/upload-artifact | 4 → 7.0.2 | [Official release](https://github.com/actions/upload-artifact/releases/tag/v7.0.2); Node 24 and updated artifact library remove deprecations |
| uv | 0.13.3 → 0.13.4 | [Official release](https://github.com/astral-sh/uv/releases/tag/0.13.4); bundled CA security update, same pin in CI and Docker build |
| FastAPI | 0.156.0 → 0.156.1 | [Official release](https://github.com/fastapi/fastapi/releases/tag/0.156.1); request-field metadata fix |
| HTTPX2 (dev only) | absent → 2.15.1 | [PyPI release](https://pypi.org/project/httpx2/2.15.1/); Starlette 1.9 TestClient selects this supported transport |

HTTPX 0.28.1 is still the latest stable release of the application's separate `httpx` distribution. HTTPX2 and its new transitive packages are development-only; they are not installed in the runtime image. Pytest treats warnings as errors instead of hiding the deprecated fallback. GitHub's [Node migration notice](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/) calls for action versions that declare Node 24; no runtime override or deprecation suppression is used.
