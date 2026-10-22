# Submission demo: Ollama, then a frontier model

This walkthrough builds on merged Phase 6 and includes the helper-cleanup fix in [PR #13](https://github.com/damogallagher/redpanda/pull/13). Run commands from the repository root, in order, in one terminal. It resets this project's broker/database data between providers, retains downloaded Ollama weights, and limits each worker run to **three consumed events per provider**. Duplicate revisions and processing errors can produce fewer than three stored results. It does not change application code.

This guide reflects merged main `30510a8` after PR #19, including the [evidence-count correction](phases/06-evidence-limits.md) and [security hardening](phases/06-security-quality.md). The test counts below match the current [README](../README.md). Oversized edits abstain before inference, so new model-call counts can differ from the earlier recorded demos.

The commands below are for you to execute. Expected outcomes are based on the implemented contracts; see the [executed demo record](evaluations/submission-demo.md) for actual runs, fixes, and saved evidence. Live Wikipedia edits and model responses vary. The fixed-case evaluations previously passed 9/9 for both configured models. Those recorded model runs predate the final hardening and Ollama image update; they are historical evidence, not a new evaluation of the current images. Rerun the model checks below for your chosen configuration.

## 1. Prepare and stop the existing application

Prerequisites: Docker Desktop with Compose 2.20+, Make, uv/uvx, and internet for initial downloads and live checks. Python 3.13.16 is installed by uv if needed. The local defaults use Qwen2.5 7B (about 4.7 GB of weights); see [README resource guidance](../README.md#run-with-a-local-model) before allocating Docker memory/disk. Hosted mode requires your own OpenAI key, billing and access to the configured model.

These are POSIX-shell commands using Damien's macOS checkout path. Replace the `cd` path with your clone's location; on Linux, replace `open -e` below with your editor. Resolve any local Git changes before switching branches or pulling; do not discard them. Run one operation at a time and stop on any unexpected nonzero exit: these interactive blocks do not automatically stop later lines after an error. Start Docker Desktop and wait until it is ready, then:

```sh
cd /Users/damien/Development/sourceControl/redpanda
git switch main
git pull --ff-only
docker info --format '{{.ServerVersion}}'
docker compose version
export UV='uvx --from uv==0.13.4 uv'
umask 077
mkdir -p reports
test -f .env.local || cp .env.local.example .env.local
test -f .env.frontier || cp .env.frontier.example .env.frontier
test -f .env || cp .env.local .env
./scripts/clean-docker.sh
```

Expected: the merged checkout is selected, Docker reports its version, missing profiles are created with private permissions, and cleanup prints `PASS: project stopped. All data and model weights retained.` Existing profile files and `.env` are preserved by these setup commands. Cleanup uses the project identified by `.env`; verify the printed project name. On a fresh clone it is `redpanda`.

Use a fresh terminal without manually exported application/Compose settings; launchers clear conflicting settings themselves, while direct `docker compose` inspection commands use the terminal environment. Reports use fixed filenames, so save any earlier reports you want to retain before repeating this guide. Do not publish `.env`, raw Compose configuration, or private logs.

## 2. Run the free verification gate

```sh
DEMO_TEST_PROJECT="triage-demo-check-$(date +%s)-$$"
COMPOSE_PROJECT_NAME="$DEMO_TEST_PROJECT" make test
make demo-success
make demo-failures
```

Expected: all exit 0. `make test` reports **453 unit tests, 32 integration/configuration checks, 72 native Connect cases, 100% application line and branch coverage**, and no warnings. It ends with `PASS: Phase 6 deterministic acceptance. Real model/live-source checks are separate.` These totals passed on merged main `30510a8` in [GitHub CI](https://github.com/damogallagher/redpanda/actions/runs/39859001474). The narrower demonstrations repeat subsets so you can watch them individually; they are already included in `make test`.

`demo-success` verifies fixture source → real Connect/broker → actual worker → sink/Postgres → API, using controlled Wikipedia/model responses. Two edits become `review` results with two reasoning stages. `demo-failures` passes only when invalid output, outages, replay and recovery behave as asserted. The integration fixtures remove their own disposable projects. The `make test` build/Connect CLI checks also create helper resources, isolated above by `DEMO_TEST_PROJECT`. Remove that helper project after the gate, including if the gate fails:

```sh
docker compose --env-file /dev/null -f compose.infrastructure.yml \
  -p "$DEMO_TEST_PROJECT" --profile tools down --volumes --remove-orphans
```

Keep this variable in the same terminal and do not substitute your application project name. The commands make no model calls and do not delete your application volumes. Initial dependency downloads and Docker builds still require internet; `make test` does not perform a live model evaluation or a container vulnerability scan.

Optional red-test demonstration, run separately:

```sh
make demo-test-failure
```

Expected: one `FAILED` test and a nonzero Make exit (observed exit 2), because the deliberately wrong expectation accepts an invented quotation. This is intentionally red, not a successful test. It changes no application code. After observing that expected failure, run `make test-unit` to return to the normal green unit gate.

## 3. Configure a short demo in both private profiles

```sh
open -e .env.local .env.frontier
```

In **both** files, replace existing values or add missing lines exactly once:

```dotenv
WORKER_MAX_ITEMS=3
INGEST_SAMPLE_ALL=true
KAFKA_GROUP_ID=triage-v1
SINK_GROUP_ID=triage-store-v1
```

Save the files. Keep the shared `COMPOSE_PROJECT_NAME` and database passwords unchanged and consistent between profiles: `POSTGRES_PASSWORD`, `TRIAGE_READER_PASSWORD`, and `TRIAGE_WRITER_PASSWORD`. The project name must also match the active `.env` so cleanup resets the project you will start. Older profiles without the two service passwords use the documented local defaults; see [database permissions](phases/06-security-quality.md#applying-the-database-permissions). This walkthrough uses the default group IDs above; the diagnostic commands below refer to them explicitly.

For bundled local inference, check `.env.local` has `LLM_BACKEND=ollama`, `LLM_MODEL=qwen2.5:7b`, `OLLAMA_MODEL=qwen2.5:7b`, `LLM_BASE_URL=http://ollama:11434`, and `COMPOSE_FILE=docker-compose.yml`. Check `.env.frontier` has `LLM_BACKEND=openai`, `LLM_MODEL=gpt-6.1-sol`, `LLM_BASE_URL=https://api.openai.com/v1`, and `COMPOSE_FILE=compose.infrastructure.yml`; enter your own `OPENAI_API_KEY` in that private file. The supplied examples contain these provider settings, but the frontier example deliberately has no key. If you choose another supported model, evaluate it and expect its model identifier in the outputs below.

`INGEST_SAMPLE_ALL=true` bypasses the normal 1% sample to shorten the wait for eligible English Wikipedia edits; normal filtering still applies. The three-edit limit bounds inference, not the number of events ingested. Do not use `WORKER_MAX_ITEMS=0` for this bounded demonstration. Setting these in the shell will not override the launchers' authoritative profiles.

The hosted portion below makes at most **40 paid calls per complete attempt**: up to 28 for the fixed-case evaluation, then up to 12 for three live edits. Each call is subject to the profile's token limit. Rerunning an evaluation/start/batch can incur further calls.

## 4. Clean data and verify Ollama on fixed cases

**The next command deletes this project's Kafka topics/offsets and Postgres rows.** Save any existing results you need first. It preserves private profiles and Ollama weights and does not globally prune Docker.

```sh
./scripts/clean-docker.sh --delete-data
./scripts/test-local.sh
```

Expected on a passing evaluation: cleanup identifies your configured project (`redpanda` in the examples); the local test builds the application, starts Ollama, pulls the configured model, and prints `PASS: 9/9 cases. Details: reports/model-local.json`. Cached model layers are reused, although a mutable model tag can resolve to newer weights. Initial download is about 4.7 GB for the default model and can take longer than inference. The test does not start ingestion or the worker and does not overwrite `.env`; Ollama remains running afterward. A different model, a provider error or a wrong decision may fail the evaluation.

Inspect the report with:

```sh
uvx --from uv==0.13.4 uv run --frozen python -m json.tool reports/model-local.json
```

Check `backend=ollama`, the expected model, `passed=9`, `total=9`, `completed=9`, and the per-case result/call transcript. A failed case or provider failure is a real failure: investigate before continuing. A failure before evaluation may leave no new report, so an older JSON file is not proof of a successful current run. Check the command's exit status and the report's `checked_at`. Do not count an unsuccessful invocation as 9/9 or repeatedly retry until an unwanted result disappears. Save reports before rerunning because each completed evaluation replaces its report.

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
docker compose logs --no-color --no-log-prefix worker > "reports/live-$DEMO_MODE-worker.log"
```

Stopping Connect leaves the API, sink and stored results available. The worker deliberately stops before draining all ingested edits; nonzero input lag is expected with this short sample-all demo.

## 6. Verify storage and inspect a complete result

Run this block for **both providers**, after their worker finishes:

```sh
DEMO_API="http://$(docker compose port api 8000)"
curl --fail --silent --show-error --connect-timeout 3 --max-time 15 \
  --write-out '\n' "$DEMO_API/health/ready"
docker compose exec -T redpanda rpk group describe triage-store-v1 </dev/null
curl --fail --silent --show-error --connect-timeout 3 --max-time 15 \
  "$DEMO_API/results?analysis_version=triage-v1&limit=10" \
  -o "reports/live-$DEMO_MODE-results.json"
uvx --from uv==0.13.4 uv run --frozen python -m json.tool "reports/live-$DEMO_MODE-results.json"
```

Expected readiness: `{"status":"ready"}`. After asynchronous sink delivery and offset commit, the storage consumer should have zero lag. Rows can become visible before the sink commits its Kafka offset. If lag is nonzero or the list is initially empty or short, wait a few seconds and repeat the block. Three distinct edits routed to `results` should produce three rows with version `triage-v1`. Every corresponding worker commit should say `output_topic: "results"`. Duplicate source revisions can collapse to one stored row; errors are routed separately and must be investigated.

Save the error-topic snapshots as part of this check:

```sh
docker compose exec -T redpanda rpk topic consume processing-errors --offset :end --format '%v\n' </dev/null \
  > "reports/live-$DEMO_MODE-processing-errors.jsonl"
docker compose exec -T redpanda rpk topic consume sink-errors --offset :end --format '%v\n' </dev/null \
  > "reports/live-$DEMO_MODE-sink-errors.jsonl"
```

For a clean successful batch, both files are empty, all three `record_committed` messages name `results`, and each distinct `output_key` has one corresponding API row. Fewer rows are acceptable only when explained by repeated revision keys; a processing error, quarantined result or unexplained missing row is not a complete successful batch. Zero sink lag alone cannot prove success because quarantined records are also acknowledged. If counts remain inconsistent, use step 8 and preserve the reports instead of resetting the data.

The read-only `rpk` commands use `</dev/null` so they do not consume subsequent command text when the block is run through a shell script or pipe.

Decisions may be `routine`, `review`, or `insufficient_evidence`. An abstention with retained evidence/reasoning metadata demonstrates safe delivery, **not successful semantic assessment**. In the [executed demo](evaluations/submission-demo.md), Ollama assessed one edit and abstained on two invalid outputs; frontier assessed two edits and abstained on incomplete source evidence. Do not promise a particular live classification or use these different live samples as an accuracy benchmark.

Only if the list contains at least one item, fetch its first row's full detail (highest database ID, meaning insertion order, not necessarily latest Wikipedia event time):

```sh
DEMO_REVISION=$(uvx --from uv==0.13.4 uv run --frozen python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["items"][0]["revision_id"])' \
  "reports/live-$DEMO_MODE-results.json")
curl --fail --silent --show-error --connect-timeout 3 --max-time 15 --get \
  "$DEMO_API/results/enwiki/$DEMO_REVISION" \
  --data-urlencode 'analysis_version=triage-v1' \
  -o "reports/live-$DEMO_MODE-detail.json"
uvx --from uv==0.13.4 uv run --frozen python -m json.tool "reports/live-$DEMO_MODE-detail.json"
```

Inspect `result.analysis.backend`, `result.analysis.model`, `result.analysis.decision`, `result.analysis.explanation`, `result.analysis.evidence`, `result.enrichment.provenance`, `result.extraction`, `result.steps`, and `result.outcome`. For an assessed edit, look for valid extraction and assessment stages; abstentions can have no extraction and fewer stages. Confirm exact before/after text and open the top-level `source_url` if checking the underlying Wikipedia revision.

Optional browser view: `open "$DEMO_API/docs"`. The API is read-only. List responses contain summaries; the detail endpoint requires the `analysis_version` query parameter.

## 7. Reset and repeat with the frontier model

Your Ollama model report, list, detail and worker log are saved under `reports/`. They survive this reset. The reset deletes only the application's broker/database data so Ollama rows cannot masquerade as frontier output; cached model weights remain.

```sh
./scripts/clean-docker.sh --delete-data
./scripts/test-frontier.sh
```

Expected on a passing evaluation: `PASS: 9/9 cases. Details: reports/model-frontier.json`. Inspect with `uvx --from uv==0.13.4 uv run --frozen python -m json.tool reports/model-frontier.json`: `backend=openai`, the configured model, `passed=9`, `total=9`, `completed=9`, and a current `checked_at`. A configuration check alone does not prove key validity/model access; this evaluation makes real requests and detects those problems. Stop on failure and do not mistake a stale report for a pass.

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
docker compose logs --no-color --no-log-prefix worker > "reports/live-$DEMO_MODE-worker.log"
```

**Repeat all of step 6 now**, keeping `DEMO_MODE=frontier`. Recompute `DEMO_API`: a configured random port can change after restart. Save the separate frontier list, detail and error-topic files. Compare provider/model metadata, explanations, evidence and stage outcomes. The live edits differ between runs: use the nine identical fixed cases to compare providers on the same inputs.

## 8. Troubleshoot a failed or incomplete run

```sh
docker compose ps -a
docker compose logs --tail=60 worker connect sink api
docker compose exec -T redpanda rpk group describe triage-v1 </dev/null
docker compose exec -T redpanda rpk group describe triage-store-v1 </dev/null
docker compose exec -T redpanda rpk topic consume ingest-errors --offset :end --format '%v\n' </dev/null
docker compose exec -T redpanda rpk topic consume processing-errors --offset :end --format '%v\n' </dev/null
docker compose exec -T redpanda rpk topic consume sink-errors --offset :end --format '%v\n' </dev/null
```

`--offset :end` reads from the beginning of the retained topic to the end offsets captured when consumption starts, then exits. It bounds the records read; broker/network failure can still prevent completion. Empty processing/sink error output is expected on a clean successful path. `ingest-errors` records upstream malformed/oversized frames separately; source filtering also intentionally drops irrelevant edits. Do not mistake a committed processing-error record for a stored triage result.

| Symptom | Next check |
|---|---|
| `FAIL: N/9 cases` | Inspect that provider's report: case failure, invalid output, connection/timeout, or unavailable model. Preserve the failed report before a rerun. |
| Ollama not ready | `docker compose logs --tail=60 model-init ollama`; verify both model names match and download completed. |
| Hosted authentication/model access error | Edit `.env.frontier` locally and rerun its model-only test; never display or commit the key. |
| Worker stopped with fewer than three results | Check `output_topic` in the worker log, both error topics, and sink lag. Error routing can complete a worker batch with exit 0. |
| Error-topic file exists but its command failed | The shell creates/truncates redirection targets before running the command. An empty file alone does not prove an empty topic; verify the consumption command succeeded. |
| API 503 or no persisted result | Check sink/Postgres health and logs; readiness does not prove the expected rows arrived. |
| No eligible input | Check Connect logs/metrics and saved `INGEST_SAMPLE_ALL=true` in the chosen profile; the live source may be unavailable. |
| Worker failed during publication | Delivery remains uncommitted for replay. Diagnose first; `docker compose start worker` starts another bounded batch and can make additional model calls. |

## 9. Finish and retain evidence

```sh
./scripts/clean-docker.sh
```

Expected: all services in the active project stop; data and weights remain. For later normal use, edit **both profiles** back to `INGEST_SAMPLE_ALL=false` and `WORKER_MAX_ITEMS=10`; the next launcher copies those values into `.env`. Keep `reports/model-local.json`, `model-frontier.json`, both live list/detail files, error-topic snapshots, worker logs, JUnit and coverage reports. Reports remain ignored by Git; live Wikipedia records are not automatically published.

Optional, explicitly destructive cleanup after saving anything needed:

```sh
./scripts/clean-docker.sh --delete-data
./scripts/clean-ollama.sh --delete-models
```

The second command deletes this local Compose project's cached Ollama weights and forces a later download. It does not touch native-host Ollama models, unrelated projects, private profiles, Docker images or build caches. For a fully cold local demonstration, you can deliberately use that same weight-deletion command before step 4.

Before submission, confirm the deterministic gate is green, record actual results of both model tests and live runs (including any failures/abstentions), and write the assignment's independent personal README sections yourself. This small demo is not a production capacity, high-availability or general model-accuracy certification.

Command audit, 22 October 2026: the cumulative gate, success/fault demonstrations, intentional failure and subsequent green unit run were executed. Step 6's literal API/detail/error-topic blocks were exercised against isolated controlled data, including delayed sink commits and empty/nonempty error topics. Fresh-profile creation, repeat safety, Compose settings and all 18 shell blocks were checked. [Verification evidence](evidence/demo-guide-verification.json) records results and scope. Local/frontier model instructions were checked against the launchers, adapters and earlier saved runs; this audit made no new real-model calls or live Wikipedia requests, so it does not claim new 9/9 model results.
