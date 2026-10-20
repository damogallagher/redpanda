# Redpanda FDE exercise

Wikipedia edit triage in Python, using Redpanda and a selectable local or hosted model.

**Phase 4 adds multi-step reasoning and durable delivery.** Redpanda Connect ingests Wikipedia edits; a Python worker fetches revision evidence, extracts changes, assesses them, and reviews uncertain output. It publishes validated results or explicit errors before committing the input offset. Persistence and the readable API arrive in Phase 5.

- [Phase 4: reasoning, delivery, and a repeatable walkthrough](docs/phases/04-reasoning.md)
- [Phase 3: inspect revision evidence and test failure behavior](docs/phases/03-enrichment.md)
- [Start or switch local/frontier mode](docs/startup.md)
- [Original assignment, unchanged](docs/assignment/fde-take-home-exercise.md)
- [Phase 2: ingestion, exact test commands, and live evidence](docs/phases/02-ingestion.md)
- [Phase 1: what changed, how to test, and evidence](docs/phases/01-foundation.md)
- [Phase 1 dependency updates and database upgrade check](docs/phases/01-dependency-updates.md)
- [Verify every phase](docs/phase-verification.md) · [Implementation plan](docs/implementation-plan.md)
- [Test policy](docs/testing.md) · [Progress](docs/progress.md) · [Prompt/response log](docs/ai-log/README.md)

## Quick verification — no model or API key needed

Prerequisites: Docker with Compose **2.20 or newer**, Make, and [uv](https://docs.astral.sh/uv/getting-started/installation/) (tested/pinned in CI: 0.13.3). Start Docker first. Python 3.13.16 is installed automatically by uv if needed.

From the repository root:

```sh
make verify-phase-4
```

This runs formatting/lint/type checks, unit tests with **100% line and branch coverage**, configuration checks, real broker/database and HTTP ingestion tests, native Connect tests, an application-container build/configuration check, offline inspection of an attributed Wikipedia diff, and real-broker acknowledgement/replay/shutdown tests. The infrastructure tests create unique disposable projects and remove only their own volumes. Initial dependency/image downloads need internet; subsequent unit tests require no network. Test reports appear in `reports/` and as PR workflow artifacts.

Expected final line:

```text
PASS: Phase 4 reasoning and durable-delivery checks. Live model evaluation is separate.
```

Expected: **333 unit tests (including launcher checks), 21 integration/configuration tests, 40 native Connect tests, 100% Python line and branch coverage**. For narrower checks use `make test-unit`, `make test-connect`, or `make test-integration`. `make verify-phase-1` still checks the foundation only. If your global uv differs, run `make verify-phase-4 UV='uvx --from uv==0.13.3 uv'`.

To demonstrate live ingestion without a model or key, run `make smoke-ingestion` (about 40 seconds with cached images). It samples the public stream for 30 seconds in an isolated project, prints validated topic records and counts, and cleans up. See [Phase 2](docs/phases/02-ingestion.md) for exact expected fixture outputs, interactive `rpk` inspection, metrics, cleanup, and reconnect limitations.

## Inspect revision evidence — no model needed

```sh
make inspect-enrichment
```

Expected: JSON with `source: "fixture"`, `status: "ready"`, provenance, and before/after text for a saved public edit. To verify the same revisions against Wikipedia now:

```sh
make smoke-enrichment
```

This separate live check makes at most two public requests and no model calls. See the [Phase 3 walkthrough](docs/phases/03-enrichment.md) for the exact revision IDs, expected evidence, unavailable/oversized demonstrations, exit codes, and limits. `make test-enrichment` runs the focused offline tests. The Phase 4 worker uses this same enrichment client.

## Follow an edit through reasoning and delivery

```sh
make demo-reasoning
```

No model or key is needed. This starts an isolated Redpanda, prints a two-step `review` result, then proves a failed output publication leaves the input offset unchanged and restarting delivers both pending edits. It cleans up its own resources. The [Phase 4 guide](docs/phases/04-reasoning.md) explains exact expected values, other failure cases, and at-least-once delivery.

For real model quality using six saved inputs, select/start a model below, wait until it is ready, then run:

```sh
make evaluate-development
```

Expect six allowed decisions and saved prompts/responses in `reports/development.json`; a failure exits nonzero. The [development rubric](docs/evaluations/development.md) separates these examples from a general accuracy claim. Hosted evaluation incurs charges; local evaluation uses downloaded weights. No live Wikipedia requests or Kafka offset changes occur.

Inspect the running worker:

```sh
docker compose logs -f worker
docker compose exec redpanda rpk topic consume results --num 1 --format '%k\t%v\n'
docker compose exec redpanda rpk group describe triage-v1
```

`results` contains decisions, source evidence, extracted changes, and step outcomes. Technical errors go to `processing-errors`. After a successful ten-edit batch, `docker compose start worker` processes the next batch. A failed publication stops the worker and leaves the input uncommitted for restart; acknowledged output may duplicate if an offset commit fails. Phase 5 will deduplicate storage by analysis key.

## Run with a local model

The default local model is **Qwen2.5 7B** (about 4.7 GB of weights). Allow approximately 12 GB free disk for the local setup and 12 GiB of Docker memory; the recorded run used a 32 GiB Apple Silicon machine. These are practical starting allocations, not validated minimums. Use hosted inference on smaller machines.

Create the private profiles once on a fresh clone, preserving existing files:

```sh
test -f .env.local || (umask 077; cp .env.local.example .env.local)
test -f .env.frontier || (umask 077; cp .env.frontier.example .env.frontier)
```

Start local mode:

```sh
./scripts/start-local.sh
```

The script validates `.env.local`, stops the previous mode while retaining volumes, copies it over `.env`, and starts the stack in the background. Edit `.env.local` for lasting local settings. See the [startup guide](docs/startup.md) for switching, failure behavior, and focused tests.

`topics` and `model-init` are one-time initialization services: **exit code 0 is success**. Wait for `model-init` to report `success`. First startup downloads model weights; later starts reuse the persistent volume. Redpanda, Postgres, Connect, and Ollama remain running. Connect starts ingesting with deterministic 1% selection. The worker waits for model initialization, then processes **ten edits** by default and exits successfully. Each ready edit normally takes two model calls, at most four. Set `WORKER_MAX_ITEMS=0` in the selected profile for continuous processing. After model initialization completes, an optional extra connectivity check is:

```sh
make smoke-model
```

Expected: a JSON object with `backend`, `model`, elapsed time, the synthetic prompt, and a nonempty response explaining the shift from uncertain association to a causal claim. This makes one model request. It tests connectivity and feasibility, not model accuracy. Real model output can vary.

Connect readiness and metrics use host loopback port 4195 (configurable with `CONNECT_PORT`). Broker and database ports remain internal. Inspect them through Docker:

```sh
docker compose exec redpanda rpk topic list
docker compose exec postgres psql -U triage -d triage -c 'TABLE schema_migrations;'
```

Expected: four topics (`edits`, `results`, `ingest-errors`, `processing-errors`) and exactly one schema migration row with version `1`. The database currently has no results table.

## Run with a hosted frontier model

The first supported hosted provider is OpenAI, using its Chat Completions API. A user-supplied key and provider billing are required. The model name is configurable; **GPT-6.1 Sol** was verified in the smoke check. Other models/providers are not automatically guaranteed compatible.

Edit `.env.frontier` and set your `OPENAI_API_KEY`. Its template already selects `COMPOSE_FILE=compose.infrastructure.yml`, `LLM_BACKEND=openai`, `LLM_MODEL=gpt-6.1-sol`, and `LLM_BASE_URL=https://api.openai.com/v1`. Then:

```sh
./scripts/start-frontier.sh
```

The script validates the profile, stops the current stack without deleting volumes, copies `.env.frontier` over `.env`, and starts the hosted configuration. **Startup now begins paid model processing**, bounded to ten edits / at most 40 calls per worker run by default. The configuration preflight itself is offline. To make an additional connectivity check afterward:

```sh
make smoke-model
```

Hosted mode starts **no Ollama container and downloads no local weights**. The smoke makes one paid request with a 1,024-token completion budget, including any reasoning tokens. The smoke makes one attempt. Reasoning has a shared four-call budget including repairs/retries; there is no fallback between providers. Secrets stay in `.env` and out of Git, build context, CLI output, and committed evidence. Allow about 4 GiB of Docker memory for this foundation without local inference.

## Use native Ollama or another local model

For native-host Ollama, install/start Ollama and pull your chosen model on the host:

```sh
ollama pull qwen2.5:7b
```

This optional manual path uses native-host Ollama rather than the bundled-local launcher. Set these values in `.env`, then use `docker compose up` / `make smoke-model`:

```dotenv
COMPOSE_FILE=compose.infrastructure.yml
LLM_BACKEND=ollama
LLM_MODEL=qwen2.5:7b
LLM_BASE_URL=http://host.docker.internal:11434
```

The native server must accept connections from Docker; the Compose tool container supplies a host-gateway mapping. If it refuses connections, check the server's listen address and firewall. Native-host inference is an optional path; the recorded local smoke used containerized Ollama. Changing a model requires its own quality check in later phases.

To change the model managed by the local launcher, edit `.env.local`: keep `COMPOSE_FILE=docker-compose.yml` and `LLM_BASE_URL=http://ollama:11434`, and set **both** `OLLAMA_MODEL` (download) and `LLM_MODEL` (request) to the same tag. Rerun `./scripts/start-local.sh`. The local adapter disables thinking where supported and requests deterministic sampling; the worker validates output shape and source quotes. Image digests and Python dependencies are pinned. Model tags can move: record the actual model digest for evaluation runs.

## Stop and resume

```sh
docker compose --profile tools down --remove-orphans
```

This preserves database, broker, and model volumes. Restart with `./scripts/start-local.sh` or `./scripts/start-frontier.sh`; each selects and copies its own profile. Automated infrastructure tests clean up their own separate volumes. Do not use `down --volumes` on a demo stack whose data or downloaded weights you want to keep.

This is the assignment's single-node development deployment: internal broker/database networking, loopback diagnostics, and a development database password. It is not an authenticated, highly available production deployment. The phase records distinguish verified behavior from later operational work.

## Tradeoffs

Reserved for Damien to write independently, in his own words, as requested by the assignment. Choose two of the assignment's pairs and describe the choice, alternative, and when to change it. No AI-authored submission prose has been supplied.

## Surprises and production failure modes

Reserved for Damien's independently written observations after running the system.

## Why this matters

Reserved for Damien's independently written three-to-four-sentence explanation for a non-technical customer stakeholder.
