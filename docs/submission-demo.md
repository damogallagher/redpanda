# Submission demo: Ollama, then a frontier model

This walkthrough builds on merged Phase 6 and includes the helper-cleanup fix in [PR #13](https://github.com/damogallagher/redpanda/pull/13). Run commands from the repository root, in order, in one terminal. It resets this project's broker/database data between providers, retains downloaded Ollama weights, and processes at most **three live edits per provider**. It does not change application code.

This guide reflects merged main after PR #17, including the [evidence-count correction](phases/06-evidence-limits.md) and [security hardening](phases/06-security-quality.md). The test counts below match the current [README](../README.md). Oversized edits abstain before inference, so new model-call counts can differ from the earlier recorded demos.

The commands below are for you to execute. Expected outcomes are based on the implemented contracts; see the [executed demo record](evaluations/submission-demo.md) for actual runs, fixes, and saved evidence. Live Wikipedia edits and model responses vary. The fixed-case evaluations previously passed 9/9 for both configured models. Those recorded model runs predate the final hardening and Ollama image update; they are historical evidence, not a new evaluation of the current images. Rerun the model checks below for your chosen configuration.

## 1. Prepare and stop the existing application

Start Docker Desktop, then:

```sh
cd /Users/damien/Development/sourceControl/redpanda
git switch main
git pull --ff-only
export UV='uvx --from uv==0.13.4 uv'
umask 077
mkdir -p reports
./scripts/clean-docker.sh
```

Expected: the clean merged checkout is selected; cleanup prints `PASS: project stopped. All data and model weights retained.` Existing `.env` is required and is already present on Damien's machine. For a new clone, create the profiles from the examples and select/copy one to `.env` first, as described in the [operator guide](operations.md). Stop if Git reports local changes that prevent switching; do not discard them.

Use a fresh terminal without manually exported application/Compose settings; launchers clear conflicting settings themselves, while direct `docker compose` inspection commands use the terminal environment.

## 2. Run the free verification gate

```sh
make test
make demo-success
make demo-failures
```

Expected: all exit 0. `make test` reports **453 unit tests, 32 integration/configuration checks, 72 native Connect cases, 100% application line and branch coverage**, and no warnings. It ends with `PASS: Phase 6 deterministic acceptance. Real model/live-source checks are separate.` These totals passed on merged main `54e3157` in [GitHub CI](https://github.com/damogallagher/redpanda/actions/runs/39840801993). The narrower demonstrations repeat subsets so you can watch them individually; they are already included in `make test`.

`demo-success` verifies fixture source → real Connect/broker → actual worker → sink/Postgres → API, using controlled Wikipedia/model responses. Two edits become `review` results with two reasoning stages. `demo-failures` passes only when invalid output, outages, replay and recovery behave as asserted. These commands create and remove disposable projects, make no model calls, and do not change your application volumes.

Optional red-test demonstration, run separately:

```sh
make demo-test-failure
```

Expected: one `FAILED` test and nonzero exit, because the deliberately wrong expectation accepts an invented quotation. This is intentionally red, not a successful test. It changes no application code; `make test-unit` returns to the normal green gate.

## 3. Configure a short demo in both private profiles

```sh
open -e .env.local .env.frontier
```

In **both** files, replace existing values or add missing lines exactly once:

```dotenv
WORKER_MAX_ITEMS=3
INGEST_SAMPLE_ALL=true
```

Save the files. Keep the shared project name and database passwords unchanged and consistent between profiles: `POSTGRES_PASSWORD`, `TRIAGE_READER_PASSWORD`, and `TRIAGE_WRITER_PASSWORD`. Older profiles without the two service passwords use the documented local defaults; see [database permissions](phases/06-security-quality.md#applying-the-database-permissions). Keep `.env.local` on `LLM_BACKEND=ollama`, `LLM_MODEL=qwen2.5:7b`, `OLLAMA_MODEL=qwen2.5:7b`, and `COMPOSE_FILE=docker-compose.yml`. Keep `.env.frontier` on `LLM_BACKEND=openai`, `LLM_MODEL=gpt-6.1-sol`, `LLM_BASE_URL=https://api.openai.com/v1`, and `COMPOSE_FILE=compose.infrastructure.yml`, with your private key configured. The existing profiles already have these provider settings.

`INGEST_SAMPLE_ALL=true` bypasses the normal 1% sample to shorten the wait for eligible English Wikipedia edits; normal filtering still applies. The three-edit limit bounds inference, not the number of events ingested. Do not use `WORKER_MAX_ITEMS=0` for this bounded demonstration. Setting these in the shell will not override the launchers' authoritative profiles.

The hosted portion below makes at most **40 paid calls per complete attempt**: up to 28 for the fixed-case evaluation, then up to 12 for three live edits. Each call is subject to the profile's token limit. Rerunning an evaluation/start/batch can incur further calls.

## 4. Clean data and verify Ollama on fixed cases

**The next command deletes this project's Kafka topics/offsets and Postgres rows.** Save any existing results you need first. It preserves private profiles and Ollama weights and does not globally prune Docker.

```sh
./scripts/clean-docker.sh --delete-data
./scripts/test-local.sh
```

Expected: cleanup identifies project `redpanda`; the local test builds the application, starts Ollama, downloads the configured model if missing, and prints `PASS: 9/9 cases. Details: reports/model-local.json`. Initial download is about 4.7 GB for the default model and can take longer than inference. This test does not start ingestion or the worker and does not overwrite `.env`.

Inspect the report with:

```sh
uvx --from uv==0.13.4 uv run --frozen python -m json.tool reports/model-local.json
```

Check `backend=ollama`, the expected model, `passed=9`, `total=9`, and the per-case result/call transcript. A failed case or provider failure is a real failure: investigate before continuing. Do not count an unsuccessful invocation as 9/9 or repeatedly retry until an unwanted result disappears. Save reports before rerunning because each evaluation replaces its report.

## 5. Run the live Ollama pipeline

```sh
DEMO_MODE=local
./scripts/start-local.sh
docker compose ps -a
docker compose logs -f worker
```

Expected: the launcher prints `Started local mode using .env.local -> .env.` The selected profile controls the batch size; your authoritative check is `worker_started` with `max_items: 3`, `backend: "ollama"`, and the configured model. Wait for three `record_committed` messages and `worker_stopped` with `processed: 3`. Press Ctrl+C if log following remains open after that message; this ends log viewing, not the containers.

`model-init`, `topics`, `db-migrate`, and the completed worker may show `Exited (0)`, which is successful completion. Broker/Postgres/Ollama/API should be running and healthy; Connect and the sink should remain running. Model initialization and current feed availability affect elapsed time. If the worker has not completed after roughly 15 minutes with weights already ready, inspect the troubleshooting section instead of launching another batch.

Now stop additional ingestion and save this run's logs:

```sh
docker compose stop connect
docker compose logs --no-color worker > "reports/live-$DEMO_MODE-worker.log"
```

Stopping Connect leaves the API, sink and stored results available. The worker deliberately stops before draining all ingested edits; nonzero input lag is expected with this short sample-all demo.

## 6. Verify storage and inspect a complete result

Run this block for **both providers**, after their worker finishes:

```sh
DEMO_API="http://$(docker compose port api 8000)"
curl --fail --silent --show-error --write-out '\n' "$DEMO_API/health/ready"
docker compose exec -T redpanda rpk group describe triage-store-v1
curl --fail --silent --show-error \
  "$DEMO_API/results?analysis_version=triage-v1&limit=10" \
  -o "reports/live-$DEMO_MODE-results.json"
uvx --from uv==0.13.4 uv run --frozen python -m json.tool "reports/live-$DEMO_MODE-results.json"
```

Expected readiness: `{"status":"ready"}`. After asynchronous sink delivery, the storage consumer should have zero lag. If the list is initially empty or short, wait a few seconds and repeat the block. Three distinct edits routed to `results` should produce three rows with version `triage-v1`. Every corresponding worker commit should say `output_topic: "results"`. Duplicate source revisions can collapse to one stored row; errors are routed separately and must be investigated.

Decisions may be `routine`, `review`, or `insufficient_evidence`. An abstention with retained evidence/reasoning metadata demonstrates safe delivery, **not successful semantic assessment**. In the [executed demo](evaluations/submission-demo.md), Ollama assessed one edit and abstained on two invalid outputs; frontier assessed two edits and abstained on incomplete source evidence. Do not promise a particular live classification or use these different live samples as an accuracy benchmark.

If the list contains at least one item, fetch the newest row's full detail automatically:

```sh
DEMO_REVISION=$(uvx --from uv==0.13.4 uv run --frozen python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["items"][0]["revision_id"])' \
  "reports/live-$DEMO_MODE-results.json")
curl --fail --silent --show-error --get \
  "$DEMO_API/results/enwiki/$DEMO_REVISION" \
  --data-urlencode 'analysis_version=triage-v1' \
  -o "reports/live-$DEMO_MODE-detail.json"
uvx --from uv==0.13.4 uv run --frozen python -m json.tool "reports/live-$DEMO_MODE-detail.json"
```

Inspect `result.analysis.backend/model`, `result.analysis.decision/explanation/evidence`, `result.enrichment.provenance`, `result.extraction`, `result.steps`, and `result.outcome`. For an assessed edit, look for valid extraction and assessment stages; abstentions can have no extraction and fewer stages. Confirm exact before/after text and open `source_url` if checking the underlying Wikipedia revision.

Optional browser view: `open "$DEMO_API/docs"`. The API is read-only. List responses contain summaries; the detail endpoint requires the `analysis_version` query parameter.

## 7. Reset and repeat with the frontier model

Your Ollama model report, list, detail and worker log are saved under `reports/`. They survive this reset. The reset deletes only the application's broker/database data so Ollama rows cannot masquerade as frontier output; cached model weights remain.

```sh
./scripts/clean-docker.sh --delete-data
./scripts/test-frontier.sh
```

Expected: `PASS: 9/9 cases. Details: reports/model-frontier.json`. Inspect with `uvx --from uv==0.13.4 uv run --frozen python -m json.tool reports/model-frontier.json`: `backend=openai`, the configured model, nine passes. A configuration check alone does not prove key validity/model access; this evaluation makes real requests and detects those problems. Stop on failure.

Then start the real hosted pipeline:

```sh
DEMO_MODE=frontier
./scripts/start-frontier.sh
docker compose ps -a
docker compose logs -f worker
```

Expected: `.env.frontier` replaces `.env`; there is no bundled Ollama service in this mode. The worker starts with `max_items: 3`, `backend: "openai"` and your configured frontier model, then logs three commits and `worker_stopped` with `processed: 3`. As with local mode, verify outputs, not just a zero worker exit code.

```sh
docker compose stop connect
docker compose logs --no-color worker > "reports/live-$DEMO_MODE-worker.log"
```

**Repeat all of step 6 now**, keeping `DEMO_MODE=frontier`. It saves separate `live-frontier-results.json` and `live-frontier-detail.json` files. Compare provider/model metadata, explanations, evidence and stage outcomes. The live edits differ between runs: use the nine identical fixed cases to compare providers on the same inputs.

## 8. Troubleshoot a failed or incomplete run

```sh
docker compose ps -a
docker compose logs --tail=60 worker connect sink api
docker compose exec -T redpanda rpk group describe triage-v1
docker compose exec -T redpanda rpk group describe triage-store-v1
docker compose exec -T redpanda rpk topic consume processing-errors --offset :end --format '%v\n'
docker compose exec -T redpanda rpk topic consume sink-errors --offset :end --format '%v\n'
```

`--offset :end` reads only up to the current topic end rather than waiting indefinitely for new errors. Empty error-topic output is expected on a clean successful path. Do not mistake a committed processing-error record for a stored triage result.

| Symptom | Next check |
|---|---|
| `FAIL: N/9 cases` | Inspect that provider's report: case failure, invalid output, connection/timeout, or unavailable model. Preserve the failed report before a rerun. |
| Ollama not ready | `docker compose logs --tail=60 model-init ollama`; verify both model names match and download completed. |
| Hosted authentication/model access error | Edit `.env.frontier` locally and rerun its model-only test; never display or commit the key. |
| Worker stopped with fewer than three results | Check `output_topic` in the worker log, both error topics, and sink lag. Error routing can complete a worker batch with exit 0. |
| API 503 or no persisted result | Check sink/Postgres health and logs; readiness does not prove the expected rows arrived. |
| No eligible input | Check Connect logs/metrics and saved `INGEST_SAMPLE_ALL=true` in the chosen profile; the live source may be unavailable. |
| Worker failed during publication | Delivery remains uncommitted for replay. Diagnose first; `docker compose start worker` starts another bounded batch and can make additional model calls. |

## 9. Finish and retain evidence

```sh
./scripts/clean-docker.sh
```

Expected: all services stop, data and weights remain. For later normal use, edit **both profiles** back to `INGEST_SAMPLE_ALL=false` and `WORKER_MAX_ITEMS=10`; the next launcher copies those values into `.env`. Keep `reports/model-local.json`, `model-frontier.json`, both live list/detail files, worker logs, JUnit and coverage reports. Reports remain ignored by Git; live Wikipedia records are not automatically published.

Optional, explicitly destructive cleanup after saving anything needed:

```sh
./scripts/clean-docker.sh --delete-data
./scripts/clean-ollama.sh --delete-models
```

The second command deletes this local Compose project's cached Ollama weights and forces a later download. It does not touch native-host Ollama models, unrelated projects, private profiles, Docker images or build caches. For a fully cold local demonstration, you can deliberately use that same weight-deletion command before step 4.

Before submission, confirm the deterministic gate is green, record actual results of both model tests and live runs (including any failures/abstentions), and write the assignment's independent personal README sections yourself. This small demo is not a production capacity, high-availability or general model-accuracy certification.
