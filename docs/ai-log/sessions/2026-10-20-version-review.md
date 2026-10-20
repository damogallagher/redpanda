# 20 October 2026 — Dependency version review

Context: Phase 1 PR #3 is merged. This exchange reviews dependency choices; no new implementation phase was requested.

## 01. User

Postgres 16, should it be Postgres 17? Should we be using latest versions of other libraries?

## 02. Assistant

I’ll check the assignment’s Postgres requirement and the pinned dependency versions, then separate upgrades worth making from changes that would add risk to the exercise.

## 03. Assistant

The assignment explicitly names Postgres 16, so that major version is appropriate. I did find a patch update we should make: the project pins 16.14, while PostgreSQL recommends 16.15. The application and test libraries are current; a couple of build tools have newer releases. I’ll document the findings and recommendations in GitHub.

## 04. Assistant

The remaining recommendation is to refresh PostgreSQL’s patch release, Hatchling, and uv, then rerun the Phase 1 checks. I’ve recorded the sources and upgrade checks in a small documentation PR so the version decisions stay alongside the project.

## 05. Assistant — final response

**I’d keep PostgreSQL 16 for this assignment, but update 16.14 → 16.15.** The [assignment explicitly specifies version 16](https://github.com/damogallagher/redpanda/blob/main/docs/assignment/fde-take-home-exercise.md), and it remains supported until November 2028. PostgreSQL recommends using the latest maintenance release within that major version. I missed that patch update during Phase 1. [PostgreSQL policy](https://www.postgresql.org/support/versioning/)

For other dependencies, use **supported stable releases, exact version pins, and verified upgrades**. My checks found:

| Component | Recommendation |
|---|---|
| HTTPX, Pydantic, pytest, pytest-cov, mypy, Ruff | Already match current releases; keep. |
| Python 3.13.16 | Still supported; keep the tested runtime for this exercise. |
| Ollama 0.40.6 | Current stable release; keep. |
| Hatchling | Update 1.27.0 → 1.32.4. |
| uv | Update 0.13.1 → 0.13.3. |

Python 3.13 receives security fixes through October 2029, although newer feature releases exist. [Python support status](https://www.python.org/downloads/)

Any upgrades should pass `make verify-phase-1`, including 100% line and branch coverage, infrastructure checks, and the container build.

I recorded the sources, upgrade checks, and our exchange in [PR #4](https://github.com/damogallagher/redpanda/pull/4). It contains documentation only; the recommended version updates have not yet been applied.
