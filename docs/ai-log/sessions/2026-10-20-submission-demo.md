# Submission demo walkthrough — 20 October 2026

Context: PR #11 merged as `2b8b62c`; documentation follow-up. Commands are supplied for Damien to run; the assistant does not execute resets or paid inference during this turn.

## User

I've merged PR #11. Can you walk me through a clean end-to-end demo using Ollama, then a frontier model, with the exact commands and expected results so I can verify everything before submitting?

## Assistant

> I’ll check the merged instructions and scripts, then give you an exact walkthrough for a clean Ollama demo followed by the frontier model, including expected results and how to diagnose failures.

## Assistant

> Your checkout is already on the merged main branch. I’ll use a three-edit demo for each provider, with a data reset between runs so old results cannot be mistaken for new ones. The walkthrough will separate fixed-case model tests from live Wikipedia processing, since live edits can legitimately produce an abstention.

## Assistant

> The walkthrough now includes a clear pass/fail check for each stage. A three-edit hosted demo plus its fixed-case evaluation is capped at 40 paid calls per attempt. It also shows how to save separate reports and inspect full result details, so a completed worker is not mistaken for proof that all three results reached Postgres.

## Assistant final response

Use this sequence **one block at a time**. I saved the [complete walkthrough](https://github.com/damogallagher/redpanda/blob/docs/submission-demo/docs/submission-demo.md) and prompt log in [documentation PR #12](https://github.com/damogallagher/redpanda/pull/12). These commands work on your already-merged main branch.

**1. Prepare and run the free checks**

Start Docker Desktop, then:

```sh
cd /Users/damien/Development/sourceControl/redpanda
git switch main
git pull --ff-only
export UV='uvx --from uv==0.13.4 uv'
umask 077
mkdir -p reports
./scripts/clean-docker.sh
make test
```

Expected: **416 unit tests, 29 integration checks, 72 Connect cases, 100% line and branch coverage**, with no warnings. Cleanup stops the application but retains data and model weights. Stop if an unexpected check fails.

**2. Configure a small demo**

```sh
open -e .env.local .env.frontier
```

In **both files**, replace existing values or add these lines once, then save:

```dotenv
WORKER_MAX_ITEMS=3
INGEST_SAMPLE_ALL=true
```

Your existing profiles select Qwen2.5 7B through Ollama and the configured OpenAI frontier model. Preserve their other settings and private key. These changes process three edits and avoid waiting for the normal 1% sample.

**3. Verify Ollama, then start the live application**

The next cleanup **deletes this project's Kafka data and Postgres rows**, while retaining model weights and private profiles. Save anything you need first.

```sh
./scripts/clean-docker.sh --delete-data
./scripts/test-local.sh
```

Expected: `PASS: 9/9 cases. Details: reports/model-local.json`. A missing model is downloaded first. This checks fixed cases with real inference; if it fails, inspect the report before continuing.

Then:

```sh
DEMO_MODE=local
./scripts/start-local.sh
docker compose ps -a
docker compose logs -f worker
```

Look for:

- `worker_started` with `backend: "ollama"` and `max_items: 3`.
- Three `record_committed` messages with `output_topic: "results"`.
- `worker_stopped` with `processed: 3`.

Press Ctrl+C after completion if log following remains open. A completed worker or initialization service showing `Exited (0)` is normal. The launcher's generic “ten edits by default” hint does not override your three-edit profile.

**4. Verify delivery and save evidence**

```sh
docker compose stop connect
docker compose logs --no-color worker > "reports/live-$DEMO_MODE-worker.log"
DEMO_API="http://$(docker compose port api 8000)"
curl --fail --silent --show-error --write-out '\n' "$DEMO_API/health/ready"
docker compose exec -T redpanda rpk group describe triage-store-v1
curl --fail --silent --show-error \
  "$DEMO_API/results?analysis_version=triage-v1&limit=10" \
  -o "reports/live-$DEMO_MODE-results.json"
uvx --from uv==0.13.4 uv run --frozen python -m json.tool \
  "reports/live-$DEMO_MODE-results.json"
```

Expected: readiness is `{"status":"ready"}`, storage-consumer lag reaches zero, and three distinct successful inputs produce three stored rows. Allow a few seconds for the sink and repeat the queries if needed.

Once the list contains results, fetch the newest full detail:

```sh
DEMO_REVISION=$(uvx --from uv==0.13.4 uv run --frozen python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["items"][0]["revision_id"])' \
  "reports/live-$DEMO_MODE-results.json")
curl --fail --silent --show-error --get \
  "$DEMO_API/results/enwiki/$DEMO_REVISION" \
  --data-urlencode 'analysis_version=triage-v1' \
  -o "reports/live-$DEMO_MODE-detail.json"
uvx --from uv==0.13.4 uv run --frozen python -m json.tool \
  "reports/live-$DEMO_MODE-detail.json"
```

Check the provider/model in `result.analysis`, the before/after evidence, revision provenance, reasoning `steps`, and `outcome`.

**Live classifications are not predetermined.** `insufficient_evidence` can demonstrate safe abstention and successful storage; it does not demonstrate a successful semantic assessment. A commit to `processing-errors` needs investigation and does not count as a stored result.

**5. Repeat with the frontier model**

This resets the application data again; the local reports remain saved. One evaluation plus one three-edit batch makes **at most 40 paid calls**. Repeating either can incur further calls.

```sh
./scripts/clean-docker.sh --delete-data
./scripts/test-frontier.sh
```

Expected: `PASS: 9/9 cases. Details: reports/model-frontier.json`.

```sh
DEMO_MODE=frontier
./scripts/start-frontier.sh
docker compose ps -a
docker compose logs -f worker
```

Expected: `.env.frontier` replaces `.env`; no bundled Ollama service runs. The worker reports `backend: "openai"`, the configured model, three commits, and `processed: 3`.

**Repeat step 4 with `DEMO_MODE=frontier`.** It saves separate frontier reports. Confirm their provider/model metadata. The live Wikipedia edits will differ; compare the fixed-case reports for a comparison using identical inputs.

**6. Demonstrate success and failure handling**

```sh
make demo-success
make demo-failures
```

Both should pass. The second proves that expected faults are detected and recovery works. Neither makes model calls.

For an intentionally red test, run separately:

```sh
make demo-test-failure
```

Expected: one failed test and a nonzero exit. Its deliberately wrong expectation accepts an invented quote; the application correctly rejects it. Run `make test-unit` afterward to show the normal green suite.

If live delivery is incomplete, inspect:

```sh
docker compose logs --tail=60 worker connect sink api
docker compose exec -T redpanda rpk topic consume processing-errors --offset :end --format '%v\n'
docker compose exec -T redpanda rpk topic consume sink-errors --offset :end --format '%v\n'
```

**7. Finish**

```sh
./scripts/clean-docker.sh
```

This stops everything while retaining data and weights. Restore both profiles to `INGEST_SAMPLE_ALL=false` and `WORKER_MAX_ITEMS=10` for normal use; the next startup copies those settings into `.env`.

Keep the reports, including any failures or abstentions. Before submitting, complete your independently written personal README sections.

## Reconciliation

All visible user and assistant messages in this walkthrough turn are recorded. Read-only service/CLI inspection and documentation syntax checks were performed. No live model evaluation, data reset or paid request was executed in this turn.
