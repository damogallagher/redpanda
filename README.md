# Redpanda FDE exercise

Wikipedia edit triage in Python, using Redpanda and a selectable local or hosted model.

**Phase 1 builds the foundation.** It starts the broker/database/local model, creates topics, validates event/result contracts, and checks model connectivity. Ingestion, multi-step reasoning, storage of results, and the API arrive in later phases; there is no review queue yet.

- [Original assignment, unchanged](docs/assignment/fde-take-home-exercise.md)
- [Phase 1: what changed, how to test, and evidence](docs/phases/01-foundation.md)
- [Verify every phase](docs/phase-verification.md) · [Implementation plan](docs/implementation-plan.md)
- [Test policy](docs/testing.md) · [Progress](docs/progress.md) · [Prompt/response log](docs/ai-log/README.md)

## Quick verification — no model or API key needed

Prerequisites: Docker with Compose **2.20 or newer**, Make, and [uv](https://docs.astral.sh/uv/getting-started/installation/) (tested/pinned in CI: 0.13.1). Start Docker first. Python 3.13.16 is installed automatically by uv if needed.

From the repository root:

```sh
make verify-phase-1
```

This runs formatting/lint/type checks, unit tests with **100% line and branch coverage**, configuration checks, real broker/database tests, and an application-container build/configuration check. The infrastructure tests create unique disposable projects and remove only their own volumes. Initial dependency/image downloads need internet; subsequent unit tests require no network. Test reports appear in `reports/` and as PR workflow artifacts.

Expected final line:

```text
PASS: Phase 1 deterministic checks. Real model smoke is a separate check.
```

For narrower checks use `make test-unit` or `make test-integration`. See [Phase 1](docs/phases/01-foundation.md) for expected counts, failure demonstrations, cleanup, and troubleshooting.

## Run with a local model

The default local model is **Qwen2.5 7B** (about 4.7 GB of weights). Allow approximately 12 GB free disk for the local setup and 12 GiB of Docker memory; the recorded run used a 32 GiB Apple Silicon machine. These are practical starting allocations, not validated minimums. Use hosted inference on smaller machines.

If `.env` does not exist, create it without overwriting existing credentials:

```sh
test -f .env || cp .env.example .env
docker compose up
```

`topics` and `model-init` are one-time initialization services: **exit code 0 is success**. Wait for `model-init` to report `success`. First startup downloads model weights; later starts reuse the persistent volume. Redpanda, Postgres, and Ollama remain running. In a second terminal:

```sh
make smoke-model
```

Expected: a JSON object with `backend`, `model`, elapsed time, the synthetic prompt, and a nonempty response explaining the shift from uncertain association to a causal claim. This makes one model request. It tests connectivity and feasibility, not model accuracy. Real model output can vary.

No services are published on host ports. Inspect the internal broker and database through Docker:

```sh
docker compose exec redpanda rpk topic list
docker compose exec postgres psql -U triage -d triage -c 'TABLE schema_migrations;'
```

Expected: four topics (`edits`, `results`, `ingest-errors`, `processing-errors`) and exactly one schema migration row with version `1`. The database currently has no results table.

## Run with a hosted frontier model

The first supported hosted provider is OpenAI, using its Chat Completions API. A user-supplied key and provider billing are required. The model name is configurable; **GPT-6.1 Sol** was verified in the smoke check. Other models/providers are not automatically guaranteed compatible.

When switching modes, first run `docker compose down` using the old settings; this stops containers and preserves volumes. Edit your untracked `.env` to set:

```dotenv
COMPOSE_FILE=compose.infrastructure.yml
LLM_BACKEND=openai
LLM_MODEL=gpt-6.1-sol
LLM_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-own-key
LLM_TIMEOUT_SECONDS=120
LLM_MAX_TOKENS=1024
```

Then:

```sh
docker compose up
```

In another terminal:

```sh
make smoke-model
```

Hosted mode starts **no Ollama container and downloads no local weights**. The smoke makes one paid request with a 1,024-token completion budget, including any reasoning tokens. There is no automatic retry or fallback between providers. Secrets stay in `.env` and out of Git, build context, CLI output, and committed evidence. Allow about 4 GiB of Docker memory for this foundation without local inference.

## Use native Ollama or another local model

For native-host Ollama, install/start Ollama and pull your chosen model on the host:

```sh
ollama pull qwen2.5:7b
```

Set these values in `.env`, then use the same `docker compose up` / `make smoke-model` commands:

```dotenv
COMPOSE_FILE=compose.infrastructure.yml
LLM_BACKEND=ollama
LLM_MODEL=qwen2.5:7b
LLM_BASE_URL=http://host.docker.internal:11434
```

The native server must accept connections from Docker; the Compose tool container supplies a host-gateway mapping. If it refuses connections, check the server's listen address and firewall. Native-host inference is an optional path; the recorded local smoke used containerized Ollama. Changing a model requires its own quality check in later phases.

To change the model managed by Docker, use `COMPOSE_FILE=docker-compose.yml`, `LLM_BASE_URL=http://ollama:11434`, and set **both** `OLLAMA_MODEL` (download) and `LLM_MODEL` (request) to the same tag. The local adapter disables thinking where supported and requests deterministic sampling; output shape still requires later application validation. Image digests and Python dependencies are pinned. Model tags can move: record the actual model digest for evaluation runs.

## Stop and resume

```sh
docker compose down
```

This preserves database, broker, and model volumes. Restart with `docker compose up`. Automated infrastructure tests clean up their own separate volumes. Do not use `down --volumes` on a demo stack whose data or downloaded weights you want to keep.

This is the assignment's single-node development deployment: internal-only networking and a development database password. It is not an authenticated, highly available production deployment. The phase records distinguish verified behavior from later operational work.

## Tradeoffs

Reserved for Damien to write independently, in his own words, as requested by the assignment. Choose two of the assignment's pairs and describe the choice, alternative, and when to change it. No AI-authored submission prose has been supplied.

## Surprises and production failure modes

Reserved for Damien's independently written observations after running the system.

## Why this matters

Reserved for Damien's independently written three-to-four-sentence explanation for a non-technical customer stakeholder.
