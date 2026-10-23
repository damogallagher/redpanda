# Redpanda FDE exercise

Wikipedia edit triage in Python, using Redpanda and a selectable local or hosted model.

Redpanda Connect ingests Wikipedia edits; a Python worker enriches and reasons over revision evidence; a second Connect pipeline validates and upserts results into Postgres. The API exposes decisions, evidence, versions, and step outcomes with bounded pagination.

- [Presentation study pack: PDF, interactive walkthrough and rehearsal](docs/study-guide/README.md)
- [Simple run/test/cleanup guide](docs/operations.md)
- [Security and code-quality audit: fixes, checks and remaining risks](docs/phases/06-security-quality.md)
- [Evidence-count fix: boundaries, compatibility and tests](docs/phases/06-evidence-limits.md)
- [Phase 6: acceptance evidence and handover](docs/phases/06-acceptance.md)
- [Code/data flow and assignment checklist](docs/handover.md)
- [Phase 5: persistence, results API, replay, and recovery](docs/phases/05-serving.md)
- [Phase 4: reasoning, delivery, and a repeatable walkthrough](docs/phases/04-reasoning.md)
- [Phase 3: inspect revision evidence and test failure behavior](docs/phases/03-enrichment.md)
- [Start or switch local/frontier mode](docs/startup.md)
- [Original assignment, unchanged](docs/assignment/fde-take-home-exercise.md)
- [Phase 2: ingestion, exact test commands, and live evidence](docs/phases/02-ingestion.md)
- [Phase 1: what changed, how to test, and evidence](docs/phases/01-foundation.md)
- [Phase 1 dependency updates and database upgrade check](docs/phases/01-dependency-updates.md)
- [Verify every phase](docs/phase-verification.md) · [Implementation plan](docs/implementation-plan.md)
- [Test policy](docs/testing.md) · [Progress](docs/progress.md) · [Prompt/response log](docs/ai-log/README.md)

For a clean Ollama → frontier submission walkthrough with exact commands and expected results, see [the demo guide](docs/submission-demo.md).

## Getting started

Use a POSIX shell (the recorded runs used macOS and Linux). Install and start Docker with Compose **2.20 or newer**. The application launchers need only Docker and a shell; **Make and [uv](https://docs.astral.sh/uv/getting-started/installation/)** are also needed for tests, model evaluations and the cleanup helpers. CI pins uv to **0.13.4**; uv installs Python **3.13.16** when needed. First use needs internet for packages, images and local model weights.

Clone the repository, or extract the submitted ZIP and open its root folder:

```sh
git clone https://github.com/damogallagher/redpanda.git
cd redpanda
```

Run the remaining commands from that folder, one operation at a time. Stop and inspect any unexpected nonzero exit before continuing. Use a fresh terminal without exported application/Compose settings so direct inspection commands use the selected `.env`.

| First task | Follow |
|---|---|
| Verify the code without a model or key | [Quick verification](#quick-verification--no-model-or-api-key-needed) |
| Run the full application with bundled Ollama | [Local setup](#run-with-a-local-model) |
| Run the full application with OpenAI, without local weights | [Frontier setup](#run-with-a-hosted-frontier-model) |
| Test only the selected model, then rehearse a bounded live run | [Operator guide](docs/operations.md#check-a-real-model-without-starting-the-full-application) and [submission demo](docs/submission-demo.md) |

Create the private profile using the guarded copy command in your chosen setup path; the launcher copies it over active `.env`. Never put a key in a tracked example file. Both modes share data by default. Keep `COMPOSE_PROJECT_NAME`, `POSTGRES_PASSWORD`, `TRIAGE_READER_PASSWORD` and `TRIAGE_WRITER_PASSWORD` consistent when switching. The provided passwords are for the isolated local demo; keep an existing database's administrator password. See [profile setup and permissions](docs/startup.md).

## Simple command menu

| I want to… | Run |
|---|---|
| Check everything without a model/key | `make test` |
| Check evidence counts and historical-result compatibility | `make test-evidence-limits` |
| Watch a successful end-to-end fixture | `make demo-success` |
| Verify faults and recovery | `make demo-failures` |
| See an intentionally failed test | `make demo-test-failure` (expected nonzero exit) |
| Test the model in `.env.local` | `./scripts/test-local.sh` |
| Test the model in `.env.frontier` | `./scripts/test-frontier.sh` (up to 28 paid calls) |
| Stop Docker, retain data/weights | `./scripts/clean-docker.sh` |
| Stop bundled Ollama, retain weights | `./scripts/clean-ollama.sh` |
| Delete this project's broker/database data | `./scripts/clean-docker.sh --delete-data` |
| Delete this project's downloaded model weights | `./scripts/clean-ollama.sh --delete-models` |

The [operator guide](docs/operations.md) gives profile setup, expected pass/fail output, report locations, fresh-start acceptance, restart steps and troubleshooting. Cleanup is scoped to this project. Model tests preserve active `.env`; the startup scripts below copy the selected profile over it. Run one operation at a time.

## Quick verification — no model or API key needed

Prerequisites: Docker, Make and uv as described in [Getting started](#getting-started). Start Docker first.

From the repository root:

```sh
README_TEST_PROJECT="triage-readme-check-$(date +%s)-$$"
COMPOSE_PROJECT_NAME="$README_TEST_PROJECT" make test
```

This runs formatting/lint/type checks, unit tests with **100% line and branch coverage**, configuration checks, real broker/database and HTTP ingestion tests, native Connect tests, an application-container build/configuration check, offline inspection of an attributed Wikipedia diff, real-broker acknowledgement/replay/shutdown tests, and a real Connect/Postgres/API fixture path including database outage recovery. The infrastructure tests create unique disposable projects and remove only their own volumes. Initial dependency/image downloads need internet; subsequent unit tests require no network. Test reports appear in `reports/` and as PR workflow artifacts.

Expected final line:

```text
PASS: Phase 6 deterministic acceptance. Real model/live-source checks are separate.
```

Expected for the current implementation: **453 unit tests, 32 integration/configuration tests, 72 native Connect tests, 100% application Python line and branch coverage**. For narrower checks use `make test-unit`, `make test-connect`, or `make test-integration`. `make verify-phase-1` still checks the foundation only. If your global uv differs, add `UV='uvx --from uv==0.13.4 uv'` to the Make command.

After the gate, including on failure, remove its build/Connect helper project in the same terminal. Keep the generated test project name; do not substitute your application project:

```sh
docker compose --env-file /dev/null -f compose.infrastructure.yml \
  -p "$README_TEST_PROJECT" --profile tools down --volumes --remove-orphans
```

Integration fixtures clean up their own separate test projects. The command above removes only the named helper project, without deleting application data or downloaded model weights. The complete [demo guide](docs/submission-demo.md#2-run-the-free-verification-gate) explains the success, expected-fault and intentionally red demonstrations.

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

New edits must fit **eight complete changed sections**, plus the existing text/byte limits, before inference. An edit exceeding those limits returns `insufficient_evidence`, `evidence_limit` and `content_truncated: true` with **zero model calls**. Retained sections are diagnostic evidence; no partial-edit classification is made. Existing v1 records containing up to 20 sections remain readable. See the [count-boundary checks](docs/phases/06-evidence-limits.md).

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

`results` contains decisions, source evidence, extracted changes, and step outcomes. Technical errors go to `processing-errors`. After a successful ten-edit batch, `docker compose start worker` processes the next batch. A failed publication stops the worker and leaves the input uncommitted for restart; acknowledged output may duplicate if an offset commit fails. The Phase 5 sink deduplicates storage by analysis key.

## Inspect persisted results — no model needed

```sh
make demo-results
```

This isolated demonstration proves seed/upsert/pagination, replay, invalid-record routing, database outage plus sink restart, and the fixture source-to-API path. It removes only its own test resources. To browse synthetic results in your selected demo stack:

```sh
make seed-results
curl --fail 'http://localhost:8000/results?analysis_version=demo-v1'
curl --fail 'http://localhost:8000/results/enwiki/101?analysis_version=demo-v1'
```

Allow a few seconds after publication. Expect three synthetic decisions; revision 101 is `review`, with before/after evidence and model `fixture-not-a-real-model`. Repeating the seed leaves three logical rows. The script starts storage/API prerequisites without starting inference and prints URLs for your configured port. The [Phase 5 guide](docs/phases/05-serving.md) documents filters, exact responses, replay, health/metrics, cleanup, and limits. The API binds to loopback port 8000 (`API_PORT`); sink diagnostics use 4196 (`SINK_PORT`).

## Run with a local model

The default local model is **Qwen2.5 7B** (about 4.7 GB of weights). Allow approximately 12 GB free disk for the local setup and 12 GiB of Docker memory; the recorded run used a 32 GiB Apple Silicon machine. These are practical starting allocations, not validated minimums. Use hosted inference on smaller machines.

Create the local profile once, preserving any existing file:

```sh
test -f .env.local || (umask 077; cp .env.local.example .env.local)
```

Start local mode:

```sh
./scripts/start-local.sh
docker compose ps -a
docker compose logs -f model-init
```

The script validates `.env.local`, stops the previous mode while retaining volumes, copies it over `.env`, and starts the stack in the background. Edit `.env.local` for lasting local settings. See the [startup guide](docs/startup.md) for switching, failure behavior, and focused tests.

`topics`, `db-migrate`, and `model-init` are one-time initialization services: **exit code 0 is success**. Wait for `model-init` to report `success`; Ctrl+C ends log viewing if it remains open, without stopping services. First startup downloads model weights; later starts reuse the persistent volume. Redpanda, Postgres, both Connect pipelines, the results API, and Ollama remain running. Connect starts ingesting with deterministic 1% selection. The worker waits for model initialization, then processes **ten edits** by default and exits successfully. Each ready edit normally takes two model calls, at most four. Set `WORKER_MAX_ITEMS=0` in the selected profile for continuous processing. After model initialization completes, an optional extra connectivity check is:

```sh
make smoke-model
```

Expected: a JSON object with `backend`, `model`, elapsed time, the synthetic prompt, and a nonempty response explaining the shift from uncertain association to a causal claim. This makes one model request. It tests connectivity and feasibility, not model accuracy. Real model output can vary.

Connect readiness and metrics use host loopback port 4195 (configurable with `CONNECT_PORT`). Broker and database ports remain internal. Inspect them through Docker:

```sh
docker compose exec redpanda rpk topic list
docker compose exec -T postgres psql -U triage -d triage \
  -c 'TABLE schema_migrations;' -c "SELECT to_regclass('public.triage_results');" </dev/null
```

Expected: five topics (`edits`, `results`, `ingest-errors`, `processing-errors`, `sink-errors`), migration versions `1` and `2`, and the `triage_results` table. Existing Phase 1 volumes are migrated automatically; retain their administrator database password. Startup also reconciles restricted `triage_reader` and `triage_writer` roles. See the [security follow-up](docs/phases/06-security-quality.md#applying-the-database-permissions) for service passwords and rotation.

## Run with a hosted frontier model

The supported hosted provider is OpenAI, using its Chat Completions API. A user-supplied key, billing and access to the selected model are required. The model name is configurable; **GPT-6.1 Sol** has [recorded 20 October evaluation evidence](docs/evaluations/submission-demo.md). Recheck your chosen model now; other models/providers are not automatically guaranteed compatible.

You can start here without running Ollama. Create the frontier profile once, preserving any existing file:

```sh
test -f .env.frontier || (umask 077; cp .env.frontier.example .env.frontier)
```

Edit `.env.frontier` and set your `OPENAI_API_KEY`. Its template already selects `COMPOSE_FILE=compose.infrastructure.yml`, `LLM_BACKEND=openai`, `LLM_MODEL=gpt-6.1-sol`, and `LLM_BASE_URL=https://api.openai.com/v1`. Then:

```sh
./scripts/start-frontier.sh
docker compose ps -a
```

The script validates the profile, stops the current stack without deleting volumes, copies `.env.frontier` over `.env`, and starts the hosted configuration. **Startup now begins paid model processing**, bounded to ten edits / at most 40 calls per worker run by default. The configuration preflight itself is offline. To make an additional connectivity check afterward:

```sh
make smoke-model
```

Hosted mode starts **no Ollama container and downloads no local weights**. The smoke makes one paid request with the profile's completion budget (1,024 tokens by default), including any reasoning tokens. The smoke makes one attempt. Reasoning has a shared four-call budget including repairs/retries; there is no fallback between providers. Private keys stay in the untracked frontier profile and active `.env`, outside the Docker build context and committed evidence. Allow about 4 GiB of Docker memory as a starting allocation without local inference; this is not a validated minimum.

## Check the selected mode and view results

After either launcher, inspect the worker and query the read-only API (default port 8000):

```sh
docker compose logs --tail=20 worker
curl --fail --silent --show-error --connect-timeout 3 --max-time 15 \
  --write-out '\n' http://localhost:8000/health/ready
curl --fail --silent --show-error --connect-timeout 3 --max-time 15 \
  --write-out '\n' 'http://localhost:8000/results?analysis_version=triage-v1&limit=5'
```

Expected readiness is `{"status":"ready"}`. The results response has `items` and `next_before_id`; an empty list is normal before selected edits finish and the asynchronous sink stores them. If startup is still in progress, wait and retry. Use your configured `API_PORT` if changed. A successful ten-edit batch logs `worker_stopped` with `processed: 10`; run `docker compose start worker` for the next batch. The fixed 1% sample and model speed affect how long that takes. Unusable evidence may produce `insufficient_evidence`; technical failures go to `processing-errors`, so consumed-event counts need not equal stored-row counts.

For a bounded nine-case model evaluation, use `./scripts/test-local.sh` or `./scripts/test-frontier.sh` after creating that mode's profile. These leave active `.env` unchanged and do not start ingestion or a worker; any existing application continues independently. A pass prints `PASS: 9/9 cases` and saves `reports/model-local.json` or `reports/model-frontier.json`. A failure exits nonzero and must be investigated; a small fixed-case pass does not establish general accuracy. Hosted evaluation makes up to 28 paid calls. See the [operator guide](docs/operations.md#check-a-real-model-without-starting-the-full-application) for isolation, report freshness and cleanup.

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

The native server must accept connections from Docker; both the worker and model-check container supply a host-gateway mapping. If it refuses connections, check the server's listen address and firewall. Native-host inference is an optional path; the recorded local smoke used containerized Ollama. Re-evaluate any different model using the current [model-test instructions](docs/operations.md#check-a-real-model-without-starting-the-full-application).

To change the model managed by the local launcher, edit `.env.local`: keep `COMPOSE_FILE=docker-compose.yml` and `LLM_BASE_URL=http://ollama:11434`, and set **both** `OLLAMA_MODEL` (download) and `LLM_MODEL` (request) to the same tag. Rerun `./scripts/start-local.sh`. The local adapter disables thinking where supported and requests deterministic sampling; the worker validates output shape and source quotes. Image digests and Python dependencies are pinned. Model tags can move: record the actual model digest for evaluation runs.

## Stop and resume

```sh
docker compose --profile tools down --remove-orphans
```

This preserves database, broker, and model volumes. Restart with `./scripts/start-local.sh` or `./scripts/start-frontier.sh`; each selects and copies its own profile. Automated infrastructure tests clean up their own separate volumes. Do not use `down --volumes` on a demo stack whose data or downloaded weights you want to keep.

This is the assignment's single-node development deployment: internal broker/database networking, loopback diagnostics, and a development database password. It is not an authenticated, highly available production deployment. The phase records distinguish verified behavior from later operational work.

## Tradeoffs

I split the model work into extraction and assessment so I could inspect how it reached a decision. First it identifies changes and quotes the exact revision text. Then it assesses those changes against the original, with another review or a repair attempt if needed. This makes it easier to check the evidence and see where something went wrong. A single classification call could reduce latency and use fewer requests, although it would put extraction and judgment in the same response. The normal path now takes two model calls, and there are more validation and failure paths to maintain. Everything, including repairs and retries, has to fit within four calls per edit. Unusable evidence or repeatedly invalid output produces an insufficient-evidence result. The extra steps still leave room for mistakes: during development, extraction and assessment repeated the same wrong interpretation. I'd consider a single call if it performed comparably on representative edits, including difficult cases and cases where it should abstain, and the saving in cost or latency made the change worthwhile.

I kept the database writes in Connect. The Python worker publishes a result to Kafka, then Connect checks it and inserts or updates the Postgres row. That leaves Python responsible for fetching and interpreting evidence, while Connect handles delivery to the database and retries. Results can wait in the topic during a database outage and be written after recovery. Writing directly from Python would remove a pipeline and keep more of the system in one language, but the worker would then need to manage database connections, SQL retries and when to commit its Kafka offset after a write. Keeping the sink separate has its own drawbacks. Python, Connect and Postgres must agree on the result format, and tracing a failure means checking more than one service. Replaying a result leaves one logical database row; a worker crash can still repeat the model calls, so processing is at least once. I'd move the writes into Python if the application needed complex business transactions or database logic that was becoming awkward to express and test in Connect. The current result schema is small, and the persistence tests cover replay and recovery from a database outage.

## Surprises and production failure modes

I was surprised by the quality of the model I could run locally on my laptop. That led me to support both local and frontier models, so reviewers can use their own hardware or choose hosted inference without changing the processing flow. The app only uses the selected provider; it doesn't switch automatically. The local demo also showed the limits of a small test set. Ollama passed all nine fixed cases, then abstained on two of three live edits because its extraction output failed validation. Those results don't establish how well it will handle other edits. Before using this with a customer, I'd test the model against their content and review criteria. The worker handles one edit at a time and can fall behind the feed; reconnecting to Wikipedia can also miss events. Public deployment would need authentication, TLS, backup and restore, and availability work. The 100% code coverage doesn't answer those questions.

## Why this matters

People reviewing Wikipedia edits could use this to decide which changes deserve a closer look. They get the before-and-after text and a reason to check an edit, while keeping the final decision themselves. False alarms waste their time, and a missed change or unavailable result can leave a misleading edit unnoticed. Wikipedia is the example here; using the same approach for a customer's knowledge base would need its own evaluation against that team's content and review process.

## Supporting records

- [Development evaluation](docs/evaluations/development.md)
- [Reasoning and delivery tests](docs/phases/04-reasoning.md)
- [Persistence and recovery tests](docs/phases/05-serving.md)
- [Recorded local and frontier demo](docs/evaluations/submission-demo.md)
- [Deployment limits](docs/handover.md#deployment-limits-and-next-operational-decisions)
