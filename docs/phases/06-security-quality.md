# Security and code-quality follow-up

Historical checkpoint, merged in [PR #16](https://github.com/damogallagher/redpanda/pull/16). Behavior, versions, counts and handover statements below describe their recorded commits. Check out the recorded revision to reproduce that checkpoint. For the current system, use the [README](../../README.md), [verification commands](../phase-verification.md) and [handover](../handover.md).

Requested 21 October 2026. Branch `hardening/security-quality-audit` follows the evidence-count fix in PR #15. PR #15 merged during this audit; the unpublished branch was fast-forwarded to main `298edac` with an identical tree before committing. PR #16 targeted main directly and was merged by Damien. PRs #13 and #14 were separate at that checkpoint and were subsequently merged. The original assignment and independent personal README sections are unchanged.

## What changed and why

| Finding | Change | Verification |
|---|---|---|
| Transcript permissions depended on the process umask; report overwrite followed destination symlinks and could leave partial files | A shared private JSON writer encodes first, creates a mode-0600 temporary file in the destination directory, flushes it and atomically replaces the destination entry. New report directories use mode 0700. Existing files become private; symlink targets are not overwritten. Failed writes retain the old report and remove the temporary file. | `tests/test_security.py`: mode, symlink, encoding, creation, flush and replacement failures; existing CLI/operator tests |
| Evaluation assumed every original `ready` input makes model calls, even if a legacy oversized input is normalized to an abstention | Score call counts against the validated result's enrichment status. Expected capacity abstentions pass with zero calls. Reject an evaluation file over 256 KiB before parsing/inference. | Real reasoning with forbidden HTTP transport; oversized valid-JSON prefixes with trailing whitespace |
| Shared size/call policies were repeated and numerical comparisons obscured intent | `src/triage/limits.py` owns shared byte, character, hunk, call and deadline policies. HTTP status comparisons use `HTTPStatus`; parser depth/cell counts and retry bounds have local named policies. | Existing boundary suite, PR #15 regressions, Ruff `PLR2004` |
| Seven functions exceeded complexity 10, including reasoning at 25 | Split parsing, bounded HTTP reading, operator dispatch and review into focused helpers. One private reasoning object holds per-item state and the shared budget. No additional agent framework or retry layer. | Every function now passes complexity ≤10; existing invalid-output, retry, deadline, contradiction, replay and delivery tests |
| API accepted arbitrary Host headers | Restrict to `localhost` and `127.0.0.1`, reject hostile DNS hostnames before storage, add frame-denial and no-referrer headers. | Host spoofing tests, existing validation/error/header tests, real loopback API checks |
| API and sink received the database administrator password | API uses `triage_reader` with SELECT only; sink uses `triage_writer` with SELECT/INSERT/UPDATE and identity-sequence usage. Neither can create roles/databases/tables, delete results, modify migrations or become administrator. Only the one-shot migration receives the admin password. | Real TCP authentication, denied SQL, role escalation, repeatable migration and credential rotation; full sink upsert/replay/outage path |
| ShellCheck reported ambiguous empty `CDPATH` assignments | Use explicit empty strings in all affected launchers. Preserve supported trusted `UV` command prefixes. | ShellCheck plus launcher tests including paths with spaces |
| Security and maintainability checks were not repeatable CI gates | Add pinned Bandit/pip-audit and checksum-verified ShellCheck/actionlint/Hadolint. CI runs them plus stricter Ruff and existing strict types/formatting/full tests. | Local gates and GitHub CI evidence below |
| Vendor images had published advisories | Refresh Python 3.13.16/trixie and PostgreSQL 16.15/bookworm digests; use Ollama 0.40.8; align the test fixture server with the refreshed Python base. No database major or distribution change. | Fresh image scans, database upgrade test and full Docker acceptance; remaining findings are disclosed separately |

The private writer is atomic within one directory and flushes file contents; it is not a promise of directory-entry durability across sudden power loss. Reports must still be stored in an operator-controlled directory. No routine live model transcript is published automatically.

## Simple test commands

From the review branch, install the locked environment with `uv sync --frozen`. With Docker running:

```sh
make test-security
make test
```

`make test-security` exercises the new security boundaries, operator failure/cleanup behavior and real database permission checks. It returns nonzero if a forbidden action succeeds. The database runs in a unique disposable project; only that project's resources are cleaned up. No live provider, public feed or paid model call is used.

`make test` is the cumulative gate: security lint, style, types, all application unit tests with **100% line and branch coverage**, real infrastructure/recovery/upgrade checks, the built container, native Connect tests and offline evidence inspection. Reports are under `reports/`. Existing `make test-evidence-limits`, `make demo-success`, `make demo-failures` and the deliberately failing `make demo-test-failure` remain available. A handled abstention is a success when that is the declared expectation.

To run the source and advisory checks separately:

```sh
make audit-code
make audit-dependencies
```

`audit-code` is deterministic and needs no Docker/provider. `audit-dependencies` queries current public advisories for the full hashed Python lock, including development tools; a finding or unavailable advisory service fails the command. It does not silently auto-upgrade dependencies. It can change outcome as new vulnerabilities are published.

ShellCheck **0.11.0**, actionlint **1.7.12** and Hadolint **2.15.1** must be on PATH for:

```sh
make audit-tools
```

Use official [ShellCheck releases](https://github.com/koalaman/shellcheck/releases/tag/v0.11.0), [actionlint releases](https://github.com/rhysd/actionlint/releases/tag/v1.7.12) and [Hadolint releases](https://github.com/hadolint/hadolint/releases/tag/v2.15.1), choosing your architecture and verifying release SHA-256 values. CI installs exact Linux binaries with hard-coded checksums before running the same target. It uses only the existing three pinned GitHub actions. `make help` lists all entry points. If necessary append `UV='uvx --from uv==0.13.4 uv'` to Make commands.

## Applying the database permissions

The existing `./scripts/start-local.sh` or `./scripts/start-frontier.sh` launchers run both result-table creation and `db/003-service-roles.sql` before starting sink/API. They work with existing volumes: no reset, table rewrite or data loss is required. The schema version remains 2 because the result/table contract is unchanged. Role reconciliation is rerunnable and serialized with an advisory transaction lock.

Each profile now supports `TRIAGE_READER_PASSWORD` and `TRIAGE_WRITER_PASSWORD`. Existing profiles without these fields use the documented local-only defaults; samples include them. Keep all three database passwords consistent between local/frontier profiles when sharing the same project. Use distinct random passwords on a shared host and retain profiles with private permissions. A launcher rerun reconciles the service passwords, then recreates API/sink with matching settings. Changing `POSTGRES_PASSWORD` alone does **not** rotate an existing PostgreSQL administrator password; that is unchanged official-image behavior.

Passwords are separate environment values, never interpolated into connection URLs or command-line SQL. The migration uses psql's quoted variable substitution, tested with apostrophes and URL punctuation. Operator launchers clear exported overrides so the selected profile is authoritative. No real private profile is edited by this PR.

The API intentionally remains a loopback deployment. Access with `http://localhost:8000` or `http://127.0.0.1:8000`; arbitrary public/custom hostnames are rejected. A reverse-proxy deployment requires an explicit authenticated/TLS design and a reviewed hostname policy.

## Scanner interpretation and production boundary

This is a Sonar-style combination of security, maintainability, complexity and coverage checks, **not an actual SonarQube analysis**. No Sonar server/project token was configured. Ruff checks the application for security patterns, magic-value comparisons, complexity, overly broad exception handling and asynchronous hazards; test assertions and fixture literals are excluded only from security/complexity/magic-value lint categories, never from test execution or application coverage. Existing correctness/style/type gates remain. Normal units such as 0/1, enum versions and self-explanatory field declarations are not indiscriminately turned into constants.

Bandit has two narrowly reviewed hotspots in the local Docker operator module: importing `subprocess` (`B404`) and calling it (`B603`, Ruff `S603`). The helper accepts only Docker as the executable, uses an argument list with `shell=False`, bounds execution time, removes credential/config overrides and never echoes captured configuration on failure. PATH, Compose files and Docker access are trusted operator privileges; no HTTP/source/model input can call this helper. The scoped annotations document these reviewed uses; security checks are not disabled globally. Local operator access is not a sandbox against a malicious machine administrator.

Trivy's Dockerfile `DS-0026` low finding is reviewed: the same image serves a bounded CLI/worker and an API, so a single image-level HTTP health check would be wrong. Compose supplies API readiness and infrastructure health checks; the worker exits on fatal delivery errors. The finding is retained rather than hidden by a meaningless health command.

The [security review](../security-review.md) and machine-readable audit evidence record remaining vendor image vulnerabilities. A zero Python advisory result, 100% exercised branches, strict lint or a passing functional suite cannot establish absence of vulnerabilities. This local project is **not approved for internet/shared-tenant production deployment**: published image findings, authenticated TLS/ACLs for broker and API, external secret management, backup/restore and deployment-specific availability controls require resolution under that deployment's threat model. Do not expose the local default credentials or unauthenticated ports publicly.

## Verification record

Implementation `4d8247b` passed the complete local gate: **453 unit tests, 31 integration checks, 72 native Connect cases**, with **1,172 lines and 286 branches covered at 100%**, zero exclusions. `make test-security` passed **62** checks. `make audit-tools` and the 63-package hashed dependency audit passed. A deliberately unsafe untracked fixture failed the quality gate as expected; it was never added to the application.

[Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39690196848) passed on the same commit. Downloaded artifacts confirm counts/coverage; emitted warnings and check annotations are both zero. [Verification JSON](../evidence/security-quality-verification.json) contains commands, scope, hashes and results. The [image findings](../evidence/security-quality-images.json) are separately disclosed failing vulnerability scans, not rolled into a misleading green result.

PR #16 was merged by Damien during verification. This evidence handover follows current main, disables the optional CI cache and does not change application code. PR #13 and PR #14 were subsequently refreshed against the merged hardening branch and merged by Damien; PR #13 adds one integration case, so the combined expected count is **32 integration checks**. The study pack remains pinned to its historical snapshot.

Final combined-main [Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39690982066) passed on `872974c`: **453 unit / 32 integration / 72 Connect cases**, **100% lines/branches**. Both conflict-resolution PR checks passed. Downloaded artifacts confirm the results; one setup-uv cache-save warning annotation appeared because concurrent runs tried to reserve the same optional cache key. This follow-up disables that optional cache using the pinned action's documented input. Source, tests and dependency pins are unchanged. All disposable local containers were removed; profiles, model weights and retained application data were preserved.

Follow-up [PR #17](https://github.com/damogallagher/redpanda/pull/17) passed [Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39692092595) on `8c1c914`: 453 unit / 32 integration / 72 Connect cases, 100% application lines and branches, **zero emitted warnings and zero check annotations**. Downloaded artifacts verify the optional-cache fix. The closing evidence/transcript update changes documentation only; application, tests and workflow match this tested commit.

## Submission documentation follow-up — 22 October 2026

PR #17 is merged. Main `54e31574266d33723fa4f69ce4feb1ab4e2848cd` passed [Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39840801993): **453 unit / 32 integration / 72 Connect cases**, all **1,172 lines and 286 branches** covered, no failures/skips/exclusions and **zero emitted warnings or check annotations**. The `main_after_pr17` section of the [verification JSON](../evidence/security-quality-verification.json) includes downloaded report hashes. This confirms `make verify-phase-6` on merged main, including the service-role and count-boundary regressions; it is not a new live-model evaluation or image scan.

Branch `docs/submission-readiness` starts from that main commit. It aligns the current demo's expected counts, removes the obsolete pre-merge PR #13 checkout instruction, documents all three shared database passwords, and corrects the handover's outdated role limitation. The Phase 5 record explicitly separates its original permissions from the later hardening. Earlier execution evidence, frozen study artifacts and the original assignment are preserved. README.md is unchanged in full, including Damien's reserved personal sections. The [conversation log](../ai-log/sessions/2026-10-22-submission-readiness.md) includes the readiness assessment and this requested follow-up.

Initial documentation validation at `d155419`: `git diff --check` passed; every relative Markdown file target resolved; `sh -n` accepted all 16 shell blocks in that version of the demo. Comparison with `54e3157` confirmed README.md, the assignment, all six study-pack files, application code, tests, dependencies and workflow were unchanged. No new application tests applied to those documentation-only changes. The normal PR workflow still runs the cumulative gate.

To review, compare the current demo totals with README.md and the linked CI artifacts, then compare the handover's reader/writer permissions with `db/003-service-roles.sql`. To repeat runtime verification with Docker running, use `make verify-phase-6 UV='uvx --from uv==0.13.4 uv'`; expect the totals above and the Phase 6 PASS message. Success and failure/recovery demonstrations remain in the [demo guide](../submission-demo.md), with project-scoped cleanup and troubleshooting. Damien reviews/merges this documentation PR and writes the personal README sections independently; security/deployment limitations remain as recorded above.

Review: [PR #18](https://github.com/damogallagher/redpanda/pull/18). Documentation corrections were committed as `d155419`; the closing update adds the review link and visible handover. PR CI is separate from the completed main run above and was still running at handover.
