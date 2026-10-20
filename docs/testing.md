# Test and acceptance policy

Status: Phases 1–6 checks are implemented. Use `make test` for the cumulative deterministic gate; the [operator guide](operations.md) separates live, success, expected-fault and intentionally failing demonstrations.

For a reviewer-friendly command matrix and concrete expected behavior, use the [phase verification guide](phase-verification.md).

## Coverage gate

Require 100% executed lines AND 100% branches for all first-party production Python modules, including API, worker, adapters, configuration, and executable Python utilities. Collect over the entire source directory, including unimported modules. Unit tests run without internet or model credentials. Use injected boundary clients, fake time, and deterministic model responses; test real application behavior around those boundaries.

Use pytest/coverage with branch measurement and a 100% failure threshold, and verify zero missing lines and branches in the machine-readable report. Do not round a near-100 result into a pass, omit difficult modules, or add `pragma: no cover` to satisfy the metric. Tests themselves and third-party code are outside production-code coverage. Shell glue, SQL, Docker Compose, and Connect YAML require their own integration/configuration tests; a Python coverage percentage says nothing about them.

The planning-only PR has no coverage percentage. From the first executable application code, a PR cannot pass with missing coverage. Do not add meaningless code or tests merely to obtain a green badge.

## Independent layers

| Layer | What it establishes |
|---|---|
| Unit | Parsing, schema validation, retry decisions, branching, budgets, idempotency keys, API behavior |
| Connect native tests | SSE parsing, filters, projection, routing, timestamps, preservation of fields |
| Contract | Event/result schemas and compatibility between Connect, worker, sink, API |
| Integration | Real broker/database delivery, acknowledged publishing, upserts, offsets, restart and replay |
| End to end with fixtures | Deterministic complete path through real infrastructure with stubbed external APIs/model |
| Real model evaluation | Extraction/evidence quality, review decisions, abstention, latency, calls and resource cost |
| Clean-start smoke | Documented startup works from a clean clone with empty application volumes |

CI runs deterministic checks on every PR with least-privilege permissions and pinned dependencies/actions. Real-feed/model runs are separately recorded and must not make every unit test flaky. A controlled integration failure must fail the CI job, not be hidden by retry-until-green behavior.

## Command interface

Available now: `make check`, `make test-unit`, `make test-foundation`, `make test-integration`, `make test-connect`, `make test-startup`, `make test-container`, `make verify-phase-1`, `make verify-phase-2`, `make verify-phase-3`, `make test-enrichment`, `make inspect-enrichment`, `make smoke-enrichment`, `make smoke-ingestion`, `make smoke-model`, `make verify-phase-4`, `make test-reasoning`, `make demo-reasoning`, and `make evaluate-development`. `make verify-phase-5`, `make test-serving`, `make test-e2e`, `make demo-results`, and `make seed-results` are also available. Fixture end-to-end includes real Connect/Postgres/API with external HTTP doubles; Phase 6 adds `make test-local`, `make test-frontier`, `make demo-success`, `make demo-failures`, `make demo-test-failure`, and `make accept-live-local`.

- `make check`: formatting, lint, types, and applicable config checks (unit coverage is a separate target).
- `make test-unit`: deterministic unit suite with 100% line/branch coverage enforcement.
- `make test-connect`: native Connect processor tests and configuration lint.
- `make test-foundation`: the four Phase 1 integration checks only.
- `make test-integration`: all 29 deterministic real Redpanda/Postgres/HTTP ingestion and Compose profile checks.
- `make test-startup`: 13 launcher behavior tests plus two actual Compose profile contracts.
- `make test-enrichment`: exact revision evidence, provenance, bounds, retries, failure outcomes, and CLI checks.
- `make inspect-enrichment`: print the attributed fixture result using the packaged CLI, offline.
- `make smoke-enrichment`: opt-in comparison of one known public revision pair; excluded from CI.
- `make smoke-ingestion`: opt-in 30-second public-source observation; excluded from CI.
- `make test-reasoning`: reasoning/worker unit cases plus real-broker delivery tests.
- `make demo-reasoning`: print a validated result and the failed-publication/replay evidence.
- `make evaluate-development`: six predeclared cases with the selected live model and saved transcripts.
- `make test-e2e`: deterministic fixture-to-API verification.
- `make test-local` / `make test-frontier`: nine frozen acceptance cases with explicit provider profiles; at most 28 model calls.
- `make verify-phase-N`: cumulative relevant deterministic checks; live demonstrations are separate.

Use isolated Compose project names/volumes for tests. Cleanup may remove only test-owned resources. Never delete a user's existing volumes as part of a routine test.

## Risk cases that must have observable assertions

- SSE heartbeat, blank/malformed JSON, missing fields, bots, wrong namespace, invalid revision IDs.
- Correct projection retains required fields and timestamp units; irrelevant input makes no model calls.
- Missing/deleted revisions, 429 with Retry-After, timeouts, oversized diff, HTML escaping, and invalid redirects.
- Dirty JSON with code fences or surrounding prose; braces inside strings; multiple ambiguous objects; wrong types/enums; non-finite/out-of-range confidence; invented evidence; prompt-injection text.
- Both model backends: request/response schema, credentials/configuration validation, explicit provider selection, and no silent local-to-hosted failover.
- Retry limits, low-confidence boundary, conflicting assessments, exhausted budget, total deadline, unavailable model; failure must never silently become a routine result.
- Publish failure before offset commit; crash after acknowledged publish but before commit; sink/database outage; duplicate replay; poison message; graceful shutdown.
- API pagination bounds, missing IDs, unavailable database, safe error responses, and deterministic ordering.

For the riskiest parser and routing decisions, deliberately change the relevant behavior and demonstrate that the tests fail, then restore it. Record this mutation check; 100% execution without meaningful assertions is insufficient.

## Evidence per PR

Record tested commit, exact command, tool/model/image versions, fixture IDs, exit status, unit count, missing lines/branches, integration/evaluation result, and known limitations. Publish coverage/test reports as CI artifacts and concise summaries in the phase document. Distinguish actual observations from expected outputs.

Evaluate a small, human-reviewed development set and a separate held-out set. Define the rubric and release threshold before inspecting held-out results. Include routine edits, substantive claim changes, ambiguous edits, missing evidence, and adversarial instructions. Measure false alarms, missed review cases, evidence grounding, abstention, latency, and model-call count. Do not claim general accuracy from a tiny demo set or tune repeatedly on the held-out set.
