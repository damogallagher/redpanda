# 21 October 2026 — Security and code quality

Scope: application, operator scripts, containers, database permissions, dependencies and CI. Branch `hardening/security-quality-audit` follows PR #15 so the count fix is retained; PR #15 merged during work and this follow-up now targets main directly; Damien reviews and merges. No private profiles or application data are changed. No paid inference is needed for this audit.

## User

Make sure ALL code is production ready, is fully secure, follws ALL best practices - no excuses. Check for things like magic numbers and other items a tool like Sonar would check for

## Assistant — progress

I’ll audit the application, scripts, containers and CI for concrete security and maintainability issues, including duplicated limits, magic numbers, error handling, secrets, dependency risks and static-analysis findings. I’ll fix issues with regression tests, preserve 100% coverage, and open a review PR. I’ll report the verified results and any unresolved findings explicitly; a clean scan alone cannot prove complete security.

## Assistant — progress

The first pass found duplicated limits, seven functions above the default complexity threshold, and two concrete issues worth fixing: transcript files are not consistently written with private permissions, and the evaluation helper can misreport a valid oversized-input abstention as a failure.

I’ll also add repeatable security and quality checks to CI so these issues are caught in future changes.

## Assistant — progress

The security scan has flagged Docker subprocess calls for review. They use argument lists without a shell; I’ll restrict the helper to Docker commands and document that trust boundary. I’m also separating the complicated parsing and reasoning functions into smaller steps, with the existing failure tests checking that their behavior stays intact.

## Assistant — progress

The locked Python dependency audit found no known vulnerabilities. The refactored application now passes checks for security patterns, magic-number comparisons and function complexity. I’m adding regression tests for private report files, oversized evaluation input and hostile API host headers before running the full system checks.

## Assistant — progress

The new regression tests pass, and application coverage is still 100% for lines and branches. I found a larger security gap in the database setup: the API and sink share the database administrator account. I’m giving them separate, limited roles and adding tests that prove the database rejects unauthorized writes.

## Assistant — progress

The real database tests now confirm that the reader cannot write, create objects or become an administrator, and that the sink cannot delete results or change migrations. ShellCheck, workflow linting and Dockerfile linting also pass.

The container scans found published vulnerabilities in upstream images, including PostgreSQL’s image and bundled Ollama. I’m checking for vendor updates and will record the remaining findings explicitly; these scans are not a clean security result.

## Assistant — progress

The vendor check found fresh Python and PostgreSQL image rebuilds and Ollama 0.40.8. I’ve updated those pins and kept PostgreSQL on 16.15. The full test suite is running now, including data preservation, replay, count limits, database permissions and end-to-end delivery. Redpanda and Connect still point to the same published manifests.
