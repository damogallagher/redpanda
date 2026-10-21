# Phase 6 security and dependency review

Reviewed 20 October 2026. Scope: this local exercise, its locked Python environment, application boundaries, scripts, and container configuration. This is not a penetration test or certification.

## Locked Python dependencies

Ran the official [PyPA pip-audit](https://github.com/pypa/pip-audit) 2.9.0 against the full exported lock, including development dependencies, without dependency resolution or automatic upgrades:

```sh
uv export --frozen --no-emit-project --format requirements-txt --output-file reports/requirements.txt
uvx --from pip-audit==2.9.0 pip-audit --no-deps --disable-pip \
  -r reports/requirements.txt -f json -o reports/dependency-audit.json
```

Observed exit 0: **33 packages audited, zero known vulnerabilities, zero skipped packages**. [Machine-readable evidence](evidence/phase-6-dependencies.json). This point-in-time check queries public advisories and is separate from deterministic CI. It does not cover operating-system packages, undeclared tools, or future advisories. At that original audit commit, Python dependency pins were unchanged; the application image base was updated as described below. The later CI follow-up updates FastAPI/uv and adds a supported test transport, with its separate audit recorded next.


### CI follow-up audit

After the FastAPI/uv/HTTPX2 changes, repeated the advisory audit with the full hashed export:

```sh
uv export --frozen --no-emit-project --format requirements-txt --output-file reports/requirements.txt
uvx --from pip-audit==2.9.0 pip-audit --disable-pip --require-hashes \
  -r reports/requirements.txt -f json -o reports/dependency-audit.json
```

Observed exit 0: **36 installed packages, zero known vulnerabilities, zero skipped packages**, with no audit warnings. `--require-hashes` already implies no dependency resolution. [Audit result](evidence/actions-dependency-audit.json) and [verification](evidence/actions-verification.json). The larger [41-package version inventory](evidence/actions-dependency-review.json) additionally includes platform-specific lock entries and build tools. This follow-up did not repeat the OS/container scan; the remaining Debian findings below are still disclosed.

## Boundary review

- Real content is treated as untrusted text. Fixed Wikipedia endpoint, bounded response size/time, strict provenance checks, schema validation and exact-source quotes limit malformed/injected content. The model cannot execute tools or alter Wikipedia. Semantic mistakes remain possible.
- Kafka acknowledges output before committing input. Native Connect tests and real recovery drills cover invalid records, failed publication, replay and duplicate upsert. SQL uses bound parameters, API limits and sanitized errors. Database role separation/TLS/auth are not part of this local deployment.
- Default ports exposed to the host bind to loopback. App containers run non-root with read-only filesystems, dropped capabilities and no-new-privileges. Docker still requires a trusted local operator.
- `.env` and both profiles remain ignored and outside the explicit Docker build allowlist. Model-only test commands capture config in memory without printing it; failure tests check redaction. Reports save only curated synthetic prompts and outputs with private file permissions. Runtime logs retain bounded metadata, not routine full prompts/responses.
- Cleanup defaults retain all volumes; destructive flags require exact project/logical-volume labels and reject external volumes. Tests verify separate data/weight deletion and another project's sentinel preservation. No global pruning or host-model deletion is implemented.

Final secret/assignment integrity checks are recorded in the Phase 6 evidence. No clean container-scan result is assumed from the Python audit.

## Application container scan and fixes

Downloaded [Trivy 0.76.0](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0) from its official release and verified the archive SHA-256 against that release's checksum file. Scanned the local ARM64 application image and its OS/Python packages, with HIGH/CRITICAL severity filtering. The [condensed before/after evidence](evidence/phase-6-container-audit.json) retains image IDs, database timestamps, every advisory ID, package/version, vendor status, and links. Full local reports are ignored under `reports/`.

```sh
trivy image --scanners vuln --severity HIGH,CRITICAL --format json \
  --output reports/container-audit.json --exit-code 1 IMAGE_NAME
```

Use the image name shown by `docker compose images model-check` after building your selected profile. This scan exits 1 when findings exist; it is **not** counted as a passed security gate. Docker Scout was unavailable without login; no login was requested or bypassed.

The initial image had 67 package/advisory pairs (2 critical, 65 high), including four Python build-tool findings. Removed runtime build tooling using a two-stage Docker build and moved the stateless app image from Python 3.13.16 Debian 12 to the official **Python 3.13.16 Debian 13** image, pinned to manifest `sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` (ARM64 and AMD64 verified). This retains the Python version and dependency lock. Postgres version/data format is unchanged. The [Debian SQLite advisory](https://security-tracker.debian.org/tracker/CVE-2025-7458) and [OpenSSL advisory](https://security-tracker.debian.org/tracker/CVE-2026-84782) support the targeted base change. The old zlib critical label additionally has a [Debian note about unaffected binary packages](https://security-tracker.debian.org/tracker/CVE-2023-45853); it was not silently suppressed.

After hardening: **zero critical and zero Python-package high/critical findings; 44 high package/advisory pairs across eight unique Debian advisories remain**. None has a fixed version listed for the installed stable distribution in the scan. This is a disclosed residual risk, not a vulnerability-free image or an approved production security exception.

| Remaining advisory | Exposure assessment for this app |
|---|---|
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), [78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), [78409](https://security-tracker.debian.org/tracker/CVE-2026-78409), [78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | util-linux mount/namespace paths. The worker/API do not invoke these commands; non-root, dropped capabilities and no-new-privileges limit the described privileged operations. Debian records no-DSA/minor status for trixie. These controls are mitigations, not removal of the packages. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | ACL pathname traversal requiring a privileged caller. The app does not perform privileged ACL updates; Debian expects a later point-release fix. |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | `infocmp` CLI handling; the service does not invoke it on user input. Debian classifies it as minor/no-DSA. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd library package match retained in the evidence. No systemd daemon runs in the application image; full library reachability has not been proven. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | Perl Archive::Tar memory exhaustion. The app does not invoke Perl or process tar input; Debian postpones the stable fix pending upstream regressions. |

Before external deployment: reassess these findings under the actual threat model, update to vendor-fixed image digests when available, scan **every** deployed infrastructure image and architecture, and apply auth/TLS/network/secret/backup controls. No unstable Debian packages or ad-hoc system-library replacement were introduced merely to reduce a scan count. These broader deployment controls remain outside the local assignment.

## 21–22 October 2026: security and code-quality follow-up

This section supersedes the original boundary/role description above. [PR #16](https://github.com/damogallagher/redpanda/pull/16) is merged. The [implementation guide](phases/06-security-quality.md) records the fixes, exact commands, trusted-operator subprocess review, compatibility and deployment instructions. This is a Sonar-style source/complexity/security review; no SonarQube server or penetration test was run.

**Verified code gates:** Ruff 0.17.1 (including security rules, magic comparisons and complexity ≤10), strict mypy 2.4.0, Bandit 1.9.4, ShellCheck 0.11.0, actionlint 1.7.12 and Hadolint 2.15.1 pass. Only two documented Docker subprocess hotspots have scoped security annotations. The deliberate negative quality fixture is rejected for unsafe shell execution and a magic comparison. The full hashed-lock audit with pip-audit 2.10.1 finds **zero advisories in 63 packages, zero skipped packages**. The scanner versions and native release checksums are pinned; no blanket security-rule suppression is used.

The API now has a restricted reader account and the sink a separate insert/update account. Real database tests prove denied writes, deletion, DDL, administrator escalation and migration changes; password rotation works without data reset. Reports/transcripts use private atomic replacement and do not overwrite symlink targets. Host validation rejects hostile DNS names before storage access. The evaluator accepts expected zero-call capacity abstentions and rejects oversized manifests before inference. Historical 20-hunk records remain readable; new reasoning stays within the shared eight-hunk processing budget.

Local and [Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39690196848) on `4d8247b` passed **453 unit / 31 integration / 72 Connect cases**, **1,172/1,172 lines and 286/286 branches (100%)**, zero exclusions and emitted warnings/annotations. `make test-security` passed all **62** focused checks. PR #13 subsequently adds one helper-volume integration test; the current README reflects that combined count. [Verification](evidence/security-quality-verification.json) and [dependency evidence](evidence/security-quality-dependencies.json) retain exact counts, commands and report hashes.

### Image scans: findings remain open

Used official **Trivy 0.76.1**, with release archive SHA-256 verification and a fresh advisory database. Scanned the application and all four deployed upstream runtime images on ARM64. An additional AMD64 Ollama scan returned the same severity counts; other AMD64 images were not separately vulnerability-scanned. The local-only fixture HTTP server uses the refreshed Python base but was not separately scanned as a deployed service. Source-tree secret scanning found no secrets; it does not cover private profiles or historical Git commits. Dockerfile analysis reports one retained low finding, `DS-0026` (service-specific health checks live in Compose).

| Selected runtime image | Critical package/advisory pairs | High pairs | Unique advisories |
|---|---:|---:|---:|
| Application, Python 3.13.16/trixie refreshed base | 0 | 44 | 8 |
| Redpanda 26.2.5 | 0 | 48 | 10 |
| Redpanda Connect 4.114.0 | 0 | 1 | 1 |
| PostgreSQL 16.15/bookworm refreshed manifest | 4 | 96 | 50 |
| Ollama 0.40.8 | 0 | 50 | 46 |

Each vulnerability command returned **exit 1**, meaning findings exist. These scans are **not passed security gates**, and the counts are package/advisory matches rather than a verified count of exploitable paths. [Full condensed findings](evidence/security-quality-images.json) retain every advisory, affected package/version, fixed version when reported, binary target, architecture, image identity and report hash. No advisory IDs were excluded. Routine scanner severity-source notices are retained in local scan logs; the no-warning CI claim above applies to the CI checks, not these separate scans.

The four PostgreSQL critical matches are [SQLite CVE-2025-7458](https://security-tracker.debian.org/tracker/CVE-2025-7458), [libxml2 CVE-2026-6653](https://security-tracker.debian.org/tracker/CVE-2026-6653), [zlib CVE-2023-45853](https://security-tracker.debian.org/tracker/CVE-2023-45853), and Go [CVE-2025-68121](https://avd.aquasec.com/nvd/cve-2025-68121) in the image's `gosu` binary. Debian's zlib advisory includes an unaffected-binary-package qualification; the scanner match is still retained for review. The Go fixed version does not mean the published PostgreSQL image already contains that fix. No claim that all these library paths are reachable—or proven unreachable—from this service is made.

Refreshed the Python and PostgreSQL vendor digests and [Ollama to 0.40.8](https://github.com/ollama/ollama/releases/tag/v0.40.8), preserving Python/PostgreSQL versions and PostgreSQL's distribution. The high/critical counts **did not improve** in the updated manifests. Redpanda and Connect's selected stable tags still resolve to the same published manifests. PostgreSQL data preservation and the complete pipeline pass with the refreshed pin; an isolated Ollama daemon returned version 0.40.8 and an empty model list without downloading weights or making model calls. This is not a new semantic model-accuracy evaluation.

**Production decision: not approved for public/shared-tenant deployment.** These vendor findings need resolution or a documented deployment-specific security assessment; a clean Python audit cannot waive them. Internet-facing deployment additionally requires authentication/TLS/ACLs, external secrets, network isolation, recovery/backups and availability controls. Current loopback bindings, constrained DB roles and bounded model access reduce exposure but do not establish complete security. The repository now enforces stronger repeatable engineering gates; it does not claim that every possible security flaw has been eliminated.

The later combined-main run `39690982066` also passes 453 unit / 32 integration tests at 100% coverage, but has one cache-reservation warning annotation from concurrent setup-uv saves. The evidence retains that warning. This handover disables the optional shared cache (`enable-cache: false`) using the [pinned action input](https://github.com/astral-sh/setup-uv/blob/1c37ad07a6a961277cf70c0d37d6f313000f5884/action.yml); it does not suppress warnings or weaken checks.
