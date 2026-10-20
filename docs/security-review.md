# Phase 6 security and dependency review

Reviewed 20 October 2026. Scope: this local exercise, its locked Python environment, application boundaries, scripts, and container configuration. This is not a penetration test or certification.

## Locked Python dependencies

Ran the official [PyPA pip-audit](https://github.com/pypa/pip-audit) 2.9.0 against the full exported lock, including development dependencies, without dependency resolution or automatic upgrades:

```sh
uv export --frozen --no-emit-project --format requirements-txt --output-file reports/requirements.txt
uvx --from pip-audit==2.9.0 pip-audit --no-deps --disable-pip \
  -r reports/requirements.txt -f json -o reports/dependency-audit.json
```

Observed exit 0: **33 packages audited, zero known vulnerabilities, zero skipped packages**. [Machine-readable evidence](evidence/phase-6-dependencies.json). This point-in-time check queries public advisories and is separate from deterministic CI. It does not cover operating-system packages, undeclared tools, or future advisories. Python dependency pins remain unchanged; the application image base was updated as described below.

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
