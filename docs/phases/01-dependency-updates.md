# Phase 1 maintenance: dependency updates

Historical checkpoint, merged in [PR #5](https://github.com/damogallagher/redpanda/pull/5). Behavior, versions, counts and handover statements below describe their recorded commits. Check out the recorded revision to reproduce that checkpoint. For the current system, use the [README](../../README.md), [verification commands](../phase-verification.md) and [handover](../handover.md).

Date: 20 October 2026. Base: merged main `cf664e1`.
Branch: `maintenance/phase-1-dependency-updates`. Damien reviews and merges.

## Changes

| Dependency | Previous | Updated | Location |
|---|---|---|---|
| PostgreSQL | 16.14-bookworm | 16.15-bookworm | [Compose](../../compose.infrastructure.yml) |
| Hatchling | 1.27.0 | 1.32.4 | [Build configuration](../../pyproject.toml) |
| uv | 0.13.1 | 0.13.3 | [Dockerfile](../../Dockerfile), [CI](../../.github/workflows/ci.yml) |

PostgreSQL's new multi-architecture manifest digest is `sha256:0ea6700a3b4f0ae6ce746519073558aed4d88a79d8d07622a9a644946c7319c4`. Its official manifest includes Linux AMD64 and ARM64. Python, application dependencies, inference settings, and application code are unchanged. `uv lock --check` with uv 0.13.3 passed, so the existing runtime/test lockfile required no changes. Hatchling is pinned separately in the build-system requirements.

Added [one integration test](../../tests/test_postgres_upgrade.py) for the actual database upgrade. It starts the previous pinned 16.14 image in a unique disposable Compose project, writes a sentinel row, stops the database, then recreates it using the new image and the same volume. It asserts:

- Server version changes from `160014` to `160015`.
- The original sentinel row is unchanged.
- The migration marker and its original timestamp are unchanged.
- A new insert succeeds after the upgrade.

The test removes only its own project's containers, network, and volumes in `finally`. It does not use `.env`, model credentials, or the demo database. Keeping the old image in this test is intentional: it is the upgrade's source version.

## Run and verify

With Docker running and uv 0.13.3 available, run from the repository root:

```sh
make verify-phase-1
```

To use exactly uv 0.13.3 without replacing an existing global uv installation, the equivalent command used for this local verification was:

```sh
make verify-phase-1 UV='uvx --from uv==0.13.3 uv'
```

Expected: **86 unit tests**, **4 integration tests**, **100% line and branch coverage**, clean formatting/lint/types and Compose validation, successful container build/configuration check, and the final Phase 1 PASS message. Test reports are written to `reports/`; CI publishes them as `phase-1-test-reports`. The first run may download both PostgreSQL images and build dependencies.

Run only the database upgrade check:

```sh
uv run --frozen pytest tests/test_postgres_upgrade.py -v
```

Expected: `test_postgres_16_14_data_survives_16_15_upgrade PASSED`. A wrong version, missing/changed row, replaced migration timestamp, failed new write, startup failure, or cleanup failure makes the test fail.

## Apply to an existing local demo

After checking out the approved changes, keep the same `.env` and Compose project name used for the demo, then:

```sh
docker compose pull postgres
docker compose stop postgres
docker compose up -d --wait postgres
docker compose exec postgres psql -U triage -d triage -Atc 'SHOW server_version_num'
```

Expected: `160015`. These commands keep the existing named volume. Do not run `down --volumes` for this update. This development-database procedure does not replace an organization's production backup and rollout process.

## Observed verification

Tested implementation commit: `68d33a3`. The full Phase 1 command above passed locally on macOS ARM64 using Python 3.13.16 and uv 0.13.3:

- 86 unit tests passed, zero failures/skips.
- All 176 executable application lines and 32 branches covered; zero missing or excluded lines.
- 4 real integration tests passed, including the old-to-new database upgrade.
- Formatting, lint, strict types, both Compose configurations, and the rebuilt packaged CLI passed.

See the [machine-readable evidence](../evidence/phase-1-dependency-updates.json). The original [Phase 1 evidence](../evidence/phase-1-verification.json) is retained unchanged. No live model request was needed because model dependencies and behavior did not change. Phase 2 had not started at this maintenance checkpoint.

Review [PR #5](https://github.com/damogallagher/redpanda/pull/5). The [GitHub Linux CI run](https://github.com/damogallagher/redpanda/actions/runs/39418079879) passed on `e853a1f` in 1 minute 7 seconds; this commit contains the same implementation as `68d33a3` plus documentation. Subsequent documentation-only commits do not change the tested implementation; the PR shows their latest checks.

Documentation checks passed: 83 relative links across 22 Markdown files resolved, the original assignment's SHA-256 matched, and whitespace checks passed. No disposable test containers or volumes remained after verification.

## Upstream references

- [PostgreSQL 16.15 release notes](https://www.postgresql.org/docs/16/release-16-15.html): no dump/restore is needed from 16.x. The release also describes special handling for certain extensions and logical decoding configurations; this foundation uses none of those.
- [Hatchling change history](https://hatch.pypa.io/latest/history/hatchling/) and [1.32.4 package](https://pypi.org/project/hatchling/1.32.4/): the successful container build exercises the updated build backend and package metadata.
- [uv 0.13.3 release](https://github.com/astral-sh/uv/releases/tag/0.13.3).
