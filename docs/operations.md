# Run, test, stop, and reset

Start Docker Desktop. From the repository folder, use the commands below. Prerequisites: Docker Compose 2.20+, Make, and uv (CI uses 0.13.3). First use downloads Python/packages/images. Do one operation at a time; do not switch profiles or clean up during a test.

## Five-minute reviewer path (cached images)

```sh
make test
make demo-success
make demo-failures
```

All three are **free of model/API calls**. They use disposable Docker projects and remove their own data afterward. `make test` includes all the demonstrations; the narrower commands let you watch them again. A first run takes longer to download/build images. A successful command ends in `PASS` and exits 0. An assertion or infrastructure error exits nonzero; do not continue as though the check passed. Machine-readable test and coverage reports are under `reports/` and attached to GitHub CI runs.

| Command | What you should see |
|---|---|
| `make test` | All unit, integration, native Connect, build and configuration checks pass; exactly 100% line **and** branch coverage |
| `make demo-success` | Two fixture edits traverse Connect → actual worker → Connect → Postgres → API; both are `review` with two reasoning steps and the expected before/after text |
| `make demo-failures` | Invalid model output abstains; model timeout routes an error; failed publication leaves offsets unchanged; database/broker recovery drains pending work; death after publication replays a duplicate into one SQL row |
| `make test-unit` | Fast offline unit checks with coverage; no Docker needed after dependency installation |
| `make test-connect` | Native Redpanda Connect lint and 72 exact input/output cases |

The failure demonstration **passes because the expected failure was detected and recovery was verified**. It does not hide a broken application behind a green exit code. Model/Wikipedia responses are controlled in deterministic infrastructure tests; brokers, Connect, database, API and worker are real.

## See what an actually failed test looks like

```sh
make demo-test-failure
```

This intentionally red demonstration expects an invented quotation to be accepted. The real grounding validator rejects it, so pytest prints one `FAILED` test and Make exits nonzero. That is the expected demonstration outcome, **not a passing test**. It never changes application code, data, or the normal test suite. Run `make test` afterward for the normal green gate. The deliberately wrong test is outside normal test discovery; its report is `reports/intentional-failure.xml`.

## Check a real model without starting the full application

Create the profiles once; these commands preserve existing files:

```sh
test -f .env.local || (umask 077; cp .env.local.example .env.local)
test -f .env.frontier || (umask 077; cp .env.frontier.example .env.frontier)
```

For Ollama:

```sh
./scripts/test-local.sh
```

This builds the test container, starts bundled Ollama and downloads the configured model if necessary, then checks nine fixed cases. Leave `OLLAMA_MODEL` and `LLM_MODEL` equal in `.env.local`. Expect `PASS: 9/9 cases` and `reports/model-local.json`. A smaller/different model may fail the rubric; the report shows exactly which case and its prompts/responses. The default Qwen2.5 7B weights occupy about 4.7 GB. The server remains available afterward; `make clean-ollama` stops it.

For the hosted frontier model, edit `.env.frontier` and enter your own `OPENAI_API_KEY`, then:

```sh
./scripts/test-frontier.sh
```

Expect `PASS: 9/9 cases` and `reports/model-frontier.json`. **This makes up to 28 paid calls**, with the profile's token limit per call. Technical provider failure stops the evaluation early. Wrong decisions fail their cases and the overall command. No provider fallback is allowed. An invalid/missing profile fails before inference. These scripts do not start ingestion or a worker, publish Kafka records, or overwrite `.env`; they use the corresponding private profile directly. Existing running application processes continue independently, so stop the application first if you want to isolate resource use/cost. `make test-local` and `make test-frontier` are aliases.

Reports contain visible model inputs/outputs for synthetic cases and are ignored by Git, created with mode 0600. Each run replaces that mode's report; copy a report before rerunning if you need both. The [rubric and first-run evidence](evaluations/acceptance.md) explain what a pass establishes and its limits.

Optional native Ollama: set `.env.local` to `COMPOSE_FILE=compose.infrastructure.yml` and `LLM_BASE_URL=http://host.docker.internal:11434`, and start/pull the model on the host yourself. The test script then skips bundled bootstrap. Native-host connectivity and alternative models depend on that machine; the recorded acceptance used bundled Ollama.

## Start the actual application

```sh
./scripts/start-local.sh
# Or, after setting the key:
./scripts/start-frontier.sh
```

These existing launchers **copy the selected profile over `.env`**, retain volumes, and start ingestion, worker, storage and API. Frontier startup begins paid inference: by default up to ten edits × four calls. Each ready edit usually needs two calls. `WORKER_MAX_ITEMS=0` explicitly enables continuous inference. Use the model-only test scripts above for a bounded evaluation without application startup.

```sh
docker compose ps -a
curl --fail http://localhost:8000/health/ready
curl --fail 'http://localhost:8000/results?limit=5'
```

Use the `API_PORT` in your selected profile if changed. One-time `topics`, `db-migrate`, `model-init`, and a completed bounded `worker` may show **Exited (0)**: this is successful completion. `docker compose start worker` processes another batch. `make seed-results` adds three explicitly synthetic examples (`demo-v1`) without starting inference; query `/results?analysis_version=demo-v1`. See [startup](startup.md) and [API details](phases/05-serving.md).

## Stop or clean up — safe defaults

| Goal | Command | What remains |
|---|---|---|
| Stop this application's Docker services | `./scripts/clean-docker.sh` | Broker/database data, model weights, private profiles, images and build cache |
| Release bundled Ollama memory | `./scripts/clean-ollama.sh` | All data and downloaded weights; the entire local project's stack stops so its worker does not keep calling a stopped model |
| Reset application data | `./scripts/clean-docker.sh --delete-data` | Model weights and private profiles; **all broker topics/offsets and database rows for the selected project are deleted** |
| Reclaim downloaded model disk space | `./scripts/clean-ollama.sh --delete-models` | Broker/database data and private profiles; **all bundled model weights for the local project are deleted** |

`make clean-docker` and `make clean-ollama` are the safe stop aliases. Docker cleanup uses active `.env`; Ollama cleanup uses `.env.local`. Both profiles normally share project name `redpanda`. The scripts print the project name, stop its containers, and only delete volumes whose Compose project and logical volume labels match. External volumes are refused. They never globally prune Docker, delete images/caches, touch another project, or delete native-host Ollama models. No implicit confirmation prompt: the explicit deletion flag is the destructive choice. Back up anything needed before using it. Do not combine cleanup with running tests/startup.

To resume, use either startup script. After deleting data, topics/schema are recreated empty. After deleting weights, the next local start/test downloads them again. If you use native Ollama, `ollama list` identifies your models; `ollama stop MODEL` unloads the explicitly named model and `ollama rm MODEL` removes that named model. Substitute the exact model you intend to remove. These native operations are manual because the app does not own your host's models. See [Ollama CLI](https://docs.ollama.com/cli).

## Full fresh-start acceptance (optional, slow)

```sh
make accept-live-local
```

Requires internet and enough free space/memory for **another** Qwen2.5 7B stack. It exports the current committed `HEAD` into a clean temporary checkout with no `.env` or virtualenv, uses a unique Compose project and empty volumes, and runs the normal `docker compose up --build -d`. It verifies fresh model bootstrap, synthetic stored examples and current Wikipedia edits reaching the results API. It limits the worker to three edits (at most 12 local model calls), temporarily accepts all eligible feed edits to shorten the observation, and uses random host ports. Other defaults are unchanged. Allow up to 40 minutes for bootstrap and 15 minutes for the batch, depending on downloads/CPU/upstream availability. The terminal announces bootstrap; the final report is `reports/live-acceptance.json`.

It removes **only that test's** containers/networks/volumes, including the fresh weights. It does not reuse/delete your application data or model weights. The tested version is `HEAD`, so commit changes before using this check. A live outage or model timeout fails visibly; this check is excluded from deterministic CI.

## When something fails

| Symptom | Next action |
|---|---|
| Docker cannot connect | Start Docker Desktop, wait until ready, retry the same command |
| Missing profile | Copy the matching example using the guarded commands above and edit it |
| Local model missing/mismatched | Keep both model tags equal; rerun `test-local.sh`; native Ollama needs its own `ollama pull MODEL` |
| Out of memory / local timeout | Close other stacks, increase Docker memory, or select a smaller model and evaluate it; hosted mode avoids local weights |
| Hosted check fails | Check provider billing/key/model access in `.env.frontier`; inspect the sanitized report; never paste a key into an issue |
| `FAIL: 8/9` or fewer cases | Inspect `cases[].passed`, `expected`, `calls`, and `output` in the report. Do not change expected labels to force a pass |
| API 503 / sink retrying | Restore Postgres with `docker compose up -d --wait postgres`; inspect health and consumer lag; pending results remain in Kafka |
| Worker exits 1 after broker failure | Restore broker, then `docker compose start worker`; uncommitted input replays and may incur another inference call |
| Worker exits 0 but backlog grows | The default ten-edit batch finished. Start another batch, or deliberately enable continuous mode; monitor resource use/cost |
| Port already used | Change `API_PORT`, `CONNECT_PORT`, `SINK_PORT` in both profiles, then rerun the selected startup script |
| Startup says a lock exists | Check for another startup first. Only after confirming none is running, remove the stale empty `.env.switch.lock` directory |
| Test interrupted / leftover test project | Identify its exact `triage-test-*` or `triage-live-*` project with `docker compose ls -a`. Use its recorded Compose file, project name and `--profile tools down --volumes --remove-orphans` only after confirming it is disposable |

Useful inspection (selected application, read-only):

```sh
docker compose logs --tail=50 worker sink connect
docker compose exec redpanda rpk group describe triage-v1
docker compose exec redpanda rpk group describe triage-store-v1
curl --fail http://localhost:4195/metrics
curl --fail http://localhost:4196/metrics
```

Lag is unconsumed work, not necessarily data loss. The single sequential worker has no autoscaling or sustainable-throughput guarantee. Model latency dominates; the acceptance report records measured call times, while recovery tests prove backlog drains with controlled fast responses. Do not publish raw Compose configuration, `.env`, container inspection environments, or private logs: these can contain credentials.

If your uv version differs: `make test UV='uvx --from uv==0.13.3 uv'`, or `UV='uvx --from uv==0.13.3 uv' ./scripts/test-local.sh`. Run scripts from any directory; they resolve their own repository root.
