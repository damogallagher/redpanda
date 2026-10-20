# Phase 01: Foundation and feasibility

Status: implemented and locally verified; PR #3 merged by Damien on 20 October 2026.
Branch: `phase/01-foundation`. Base: merged Phase 0/documentation work (`8e0fa6e`).

## What was built

| Component | Behavior | Files |
|---|---|---|
| Local infrastructure | Single-node Redpanda, Postgres 16, persistent volumes, readiness checks; no host-published ports | [base Compose](../../compose.infrastructure.yml), [local Compose](../../docker-compose.yml) |
| Initialization | Four topics via `rpk --if-not-exists`; one idempotent SQL migration marker; local model download | [SQL](../../db/001-foundation.sql), Compose files |
| Configuration | Explicit Ollama/OpenAI selection, model/URL/timeouts/token limit, validation, masked key | [config](../../src/triage/config.py), [.env.example](../../.env.example) |
| Model boundary | One request to the selected provider; input/output limits, complete-response validation, sanitized failures; no automatic retries/fallback | [model adapter](../../src/triage/llm.py) |
| Contracts | Strict versioned event/result schemas, timezone-aware timestamps, evidence required for substantive decisions | [schema models](../../src/triage/schema.py), [JSON contracts](../../schemas/edit-event.v1.json), [result contract](../../schemas/analysis-result.v1.json) |
| Diagnostics | Validate configuration, export schemas, or perform a synthetic real-model smoke | [CLI](../../src/triage/cli.py) |
| Quality gate | Locked dependencies, non-root container, formatting/lint/types, 100% line/branch coverage, real infrastructure tests | [Makefile](../../Makefile), [CI](../../.github/workflows/ci.yml), [tests](../../tests/test_infrastructure.py) |

No live Wikipedia ingestion, multi-step reasoning, sink, or serving API is included. The model smoke is a connectivity/feasibility probe only; the later worker will own retries, total item deadlines, output parsing, confidence policy, and evidence grounding. HTTP timeouts here are per operation, not a global item deadline.

## Versions and resources

The [dependency update record](01-dependency-updates.md) documents the latest pins and verification. The initial Phase 1 evidence at the end of this page retains its original versions and results.

- Python 3.13.16, uv 0.13.3, Hatchling 1.32.4; runtime/test dependencies and hashes in `uv.lock`.
- Redpanda v26.2.5; Postgres 16.15-bookworm; Ollama 0.40.6; Python slim image. All container bases use multi-architecture manifest digests for ARM64/AMD64.
- Selected local model: Qwen2.5 7B, Apache 2.0, approximately 4.7 GB weights. Recorded model ID: `845dbda0ea48`; [full manifest digest and size](../evidence/phase-1-local-model-metadata.json). Model tags are mutable; retain the actual digest with evaluation evidence.
- Verified hosted model: `gpt-6.1-sol` through OpenAI Chat Completions.
- Test machine: ARM64 Mac with 32 GiB physical RAM; Docker reported 10 CPUs and approximately 30.8 GiB RAM. Ollama container limit 8 GiB, Redpanda 2 GiB, Postgres 512 MiB.
- Practical starting allocation: 12 GiB Docker RAM and 12 GB disk for local mode, 4 GiB Docker RAM for hosted mode. Smaller-machine minimums have not been benchmarked.

## Run the automated checks

Prerequisites: Docker running, Compose >=2.20, Make, uv (0.13.3 used in CI). Run from the repository root:

```sh
make verify-phase-1
```

The command installs the pinned Python/dependencies if necessary, checks lint/format/types and both Compose files, runs all unit tests with coverage, starts isolated real broker/database tests, and builds/runs the application container. It never calls a real model and requires no API key.

Expected results:

- All unit tests pass; zero missing source lines and zero missing branches. Coverage below 100% fails the command.
- Four infrastructure tests pass: hosted Compose excludes local inference; topic setup runs twice and an exact JSON payload survives broker produce/consume; SQL setup runs twice and leaves one migration row after a database restart; upgrading a disposable 16.14 database to 16.15 preserves existing data and accepts new writes.
- Container configuration check reports `status: valid`; the packaged CLI works as user 10001.
- Final output: `PASS: Phase 1 deterministic checks. Real model smoke is a separate check.`

For individual layers:

```sh
make test-unit
make test-integration
make test-container
```

Reports: `reports/unit.xml`, `reports/integration.xml`, `reports/coverage.json`, `reports/coverage.xml`. CI attaches these to its `phase-1-test-reports` artifact. Reports are generated, not committed. Expected duration after downloads: under a minute on the recorded machine; initial Python/image downloads vary by connection.

## Demonstrate observable behavior

Follow either the [local or hosted README setup](../../README.md), then:

```sh
docker compose ps -a
docker compose exec redpanda rpk topic list
docker compose exec postgres psql -U triage -d triage -c 'TABLE schema_migrations;'
make smoke-model
```

Expected: long-running services healthy; initialization services exited 0; the four documented topics; one row with version 1; one model response identifying the stronger causal claim. Initialization can run again without changing those counts:

```sh
docker compose run --rm topics
docker compose exec postgres psql -U triage -d triage -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/001-foundation.sql
```

The topic round-trip fixture deliberately tests broker transport, not the later edit-event ingestion contract. It runs only in isolated test projects and is not used as a real source event.

## Demonstrate failure without a model charge

```sh
docker compose run --rm --no-deps -e LLM_BACKEND=invalid model-check triage check-config
```

Expected: exit code **2**, a short configuration error, no provider request, and no credential printed. Unit tests also verify 429/5xx responses, redirects, network timeouts, excessive input/output, missing/invalid/truncated responses, required hosted credentials, schema failures, and no fallback or hidden retry.

## Real model smoke observations

Both runs use the same synthetic before/after statement about association versus causation, not personal/customer content:

| Backend | Model | Observed request time | Outcome |
|---|---|---|---|
| Local container | Qwen2.5 7B | 7.788 seconds | Concise description of the change in meaning |
| Hosted OpenAI | GPT-6.1 Sol | 2.911 seconds | Concise description of the change in meaning |
| Local candidate, not selected | Qwen3 4B | 25.687 seconds | Correct final observation but unwanted long explanation |

See the complete [local](../evidence/phase-1-local-model.json), [hosted](../evidence/phase-1-hosted-model.json), and [candidate](../evidence/phase-1-local-candidate-qwen3.json) request/response records. Each includes the actual visible prompts, model, response, and elapsed time. These single runs do not establish accuracy or statistically meaningful throughput. Prompt/schema evaluation is later work. Native-host inference was not used for these records.

## Cleanup, troubleshooting, and handover

- `docker compose down` stops the demo while preserving data and weights. Unit tests do not touch containers. Integration tests use a unique `triage-test-*` project and remove only that project's volumes, even after failure.
- Docker unavailable: start Docker Desktop and retry. A failed test is not reported as a skip.
- Download/model initialization failure: inspect `docker compose logs model-init`; check internet/disk availability, then rerun `docker compose run --rm model-init` in local mode.
- Connection refused or unknown model: wait for model initialization and check `LLM_BASE_URL`, `OLLAMA_MODEL`, and `LLM_MODEL`. A model's availability is distinct from the server being healthy.
- OpenAI 401/403/429: check the untracked key, model access, quota, and billing. There is no automatic provider switch or retry in this phase.
- Token-limited/incomplete output: the adapter fails explicitly. Adjust `LLM_MAX_TOKENS` within the documented 16–8192 range and rerun deliberately; higher limits can increase hosted cost.
- Before changing inference mode, bring the old Compose configuration down. This avoids retaining an unused local model container in hosted mode.
- For interrupted work: inspect the progress log and tested commit before resuming. Next phase starts from merged main and adds Connect ingestion/configuration tests, not more model orchestration.

## References checked

- [Redpanda local quickstart](https://docs.redpanda.com/streaming/current/get-started/quick-start/)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Qwen2.5 7B weights and license](https://ollama.com/library/qwen2.5:7b)
- [OpenAI Chat Completions request contract](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [GPT-6.1 Sol supported API endpoints](https://developers.openai.com/api/docs/models/gpt-6.1-sol)

## Initial Phase 1 verification and PR

Locally verified application commit: `e278b5b` using `make verify-phase-1`.

- **86 unit tests passed**, zero failures/skips; 176/176 source lines and 32/32 branches covered; no excluded lines.
- **3 real infrastructure tests passed**, zero failures/skips, in 14.007 seconds including setup/cleanup.
- Formatting, lint, strict type checking, both Compose configurations, and packaged-container configuration check passed.
- Default model bootstrap reran successfully with the same persistent volume; initialization services exited 0. Container user ID was verified as 10001. No Ollama OOM events were recorded.
- Documentation links, original assignment integrity, and staged secret checks passed.

Machine-readable [local verification record](../evidence/phase-1-verification.json). Review [PR #3](https://github.com/damogallagher/redpanda/pull/3). The [first Linux CI run](https://github.com/damogallagher/redpanda/actions/runs/39403308104) passed; the PR checks show the latest run for subsequent updates. Documentation-only evidence updates do not change the tested application source. The independent README write-up remains Damien's responsibility.

Final review also verified that a configured sub-five-second timeout limits connection setup, and that incompatible model settings in the developer shell cannot affect the deterministic container check.
