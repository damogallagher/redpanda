# Phase 4: Multi-step reasoning and durable delivery

Status: implemented; final verification and PR handover are being recorded below.
Branch: `phase/04-reasoning`, based on merged PR #7 (`efbd03a`). Damien reviews and merges.

## What changed

A sequential Python worker now consumes `edits`, fetches the actual revision evidence, performs two distinct model tasks, and publishes to `results` or `processing-errors`. Redpanda Connect continues to own ingestion. PostgreSQL persistence and the readable API are Phase 5.

1. **Extract:** identify changes in meaning/support, with exact before/after quotes from the same source hunk.
2. **Assess:** check the extraction against the original text and recommend `routine`, `review`, or `insufficient_evidence` with an explanation.
3. **Review or repair when needed:** low confidence (below 0.8) or a routine decision conflicting with substantive extraction triggers a second assessment. Invalid schema/quotes trigger one fresh repair attempt for that step. Model transport failures get one bounded retry for that step. All steps share **four model calls maximum** per edit.
4. **Deliver:** publish the validated result or technical error, wait for Redpanda acknowledgement, synchronously commit the input offset, then process another edit.

The code is deliberately small: [prompts](../../src/triage/prompts.py), [reasoning](../../src/triage/reasoning.py), [broker adapter](../../src/triage/broker.py), and [worker](../../src/triage/worker.py). The existing model adapters are shared; the new dependency is pinned `confluent-kafka==2.16.0`. No agent framework or additional service is required.

Results use [reasoned-edit.v1.json](../../schemas/reasoned-edit.v1.json), including the Phase 1 analysis contract and Phase 3 source/provenance contract. Technical errors use [processing-error.v1.json](../../schemas/processing-error.v1.json). Analysis attempts now permit zero for unavailable evidence; other validation stays strict. Prompts are versioned `edit-triage-v2`; the analysis key version is `triage-v1`.

## Run the cumulative checks

Prerequisites: running Docker/Compose 2.20+, Make, and uv. Initial images/dependencies need internet; tests make no live Wikipedia or model calls, need no API key, and download no model.

```sh
make verify-phase-4
```

Or use the exact CI tool version:

```sh
make verify-phase-4 UV='uvx --from uv==0.13.3 uv'
```

Expected: **331 unit tests**, **21 integration/configuration tests**, **40 native Connect tests**, lint/format/strict types, shell/Compose checks, container build, and offline enrichment inspection pass. Application coverage must be exactly **100% lines and branches**, with zero excluded or missing lines/branches. Shell, Compose and Connect tests are separate from that Python metric.

```text
PASS: Phase 4 reasoning and durable-delivery checks. Live model evaluation is separate.
```

Allow roughly two minutes with cached images, longer on initial download. JUnit, coverage, and per-scenario broker results are in ignored `reports/`; CI uploads `phase-4-test-reports`. Each integration module creates a unique `triage-test-*` project and verifies removal of its own containers, networks and volumes. Existing demo services/data are preserved.

Focused checks:

```sh
make test-reasoning
make test-unit
make test-startup
```

## Short walkthrough: result plus failed-publication replay

```sh
make demo-reasoning
```

This runs two named scenarios against a disposable real Redpanda with controlled Wikipedia/model HTTP responses. It prints records consumed by **rpk**, not just mocked publisher calls. Fixtures are test-only and excluded from the application image.

The valid input changes “found an association, without proving causation” to “proved that the treatment causes recovery.” Expected result:

- Kafka key `enwiki:101:triage-v1`.
- `analysis.decision: "review"`, `attempts: 2`, exact before/after evidence, model/prompt versions.
- `steps`: `extract/valid`, then `assess/valid`; `outcome: "assessed"`.
- Consumer offset moves from no committed offset (`-1001` in this client) to `1`, the next input offset.

The replay scenario seeds **two** edits and deliberately leaves the result topic absent with automatic topic creation disabled. The real producer cannot obtain a delivery acknowledgement. Expected:

```json
{"initial_offset": -1001, "failure_offset": -1001, "final_offset": 2, "output_count": 2}
```

The test creates the missing result topic and restarts the worker with the same consumer group. Both edits appear in results, then the offset reaches 2. The first edit incurs inference again: durable delivery is **at least once**, not exactly once. Topic/group names contain a random suffix; assertions do not depend on that suffix. Reports are `reports/worker-valid.json` and `reports/worker-result-replay.json`.

Other integration scenarios cover invalid output, repair, low-confidence review, unresolved uncertainty, model timeout, malformed input, failure publishing an error, failure committing after a real output acknowledgement, and SIGTERM during inference. The commit-failure case intentionally produces duplicate output with the same key after restart. SIGTERM drains and commits only the current edit (offset 1), leaving the second for a later run. A test-only commit failure is injected at the commit boundary; output publication and offset inspection still use real Redpanda.

## Run the application

The [local/frontier launchers](../startup.md) now build and start the worker as well as ingestion. Preflight still makes no model call. Local mode waits for model initialization. Hosted startup **does make paid model calls** once evidence is ready.

Set these in the selected private profile (existing profiles inherit these defaults):

```dotenv
WORKER_MAX_ITEMS=10
KAFKA_GROUP_ID=triage-v1
```

Ten committed edits is a bounded demo batch: normally 20 model calls, maximum 40. Missing/unusable evidence makes no model calls. Set `WORKER_MAX_ITEMS=0` explicitly for continuous processing; the live feed may then produce ongoing provider charges. No automatic provider fallback or worker restart is configured. `worker` exiting **0** after the batch is success; it can remain idle waiting for input.

```sh
./scripts/start-local.sh       # or ./scripts/start-frontier.sh
docker compose logs -f worker
docker compose exec redpanda rpk topic consume results --num 1 --format '%k\t%v\n'
docker compose exec redpanda rpk topic consume processing-errors --num 1 --format '%k\t%v\n'
docker compose exec redpanda rpk group describe triage-v1
```

The topic-consume commands wait if the selected topic is empty; Ctrl-C stops inspection. `docker compose start worker` starts the next batch or retries after a delivery failure is fixed. It resumes the group's committed offsets. Changing models does not reanalyse already committed input; use a separate deliberate replay group for reanalysis and expect duplicate logical result keys. Phase 5 will deduplicate storage by `(wiki, revision_id, analysis_version)`.

## Live model evaluation

```sh
make evaluate-development
```

The selected model must already be ready. Six predeclared cases use saved inputs, including the attributed Belle edit: no Wikipedia requests or Kafka offset changes. Maximum 20 model calls. Local inference uses existing weights; hosted inference incurs charges. Full visible prompts/responses and results are saved to `reports/development.json`; failures exit nonzero. See the [rubric and observed model limitations](../evaluations/development.md).

This is development tuning, not held-out accuracy. Both providers have deterministic HTTP contract tests; Phase 4's live quality check uses local Qwen2.5 7B. No new paid hosted run is claimed. Phase 1 retains the separate real hosted connectivity evidence.

## Failure boundaries and delivery semantics

| Boundary | Behavior |
|---|---|
| Evidence | Missing, truncated, oversized, or empty source yields explicit insufficient evidence, zero calls. Other enrichment failures become processing errors |
| Model JSON | Strict types/enums, finite confidence, no unknown fields or duplicate JSON keys. A single JSON object or exact Markdown fence is accepted; surrounding prose/multiple objects require repair |
| Grounding | Every source hunk must be represented; quotes must be exact, changed excerpts from the same hunk. Empty quote only for an entirely empty side. At most eight extracted changes, 512 characters per quote; edits needing more abstain rather than silently drop hunks |
| Uncertainty | Repeated invalid output, unresolved confidence or contradictions become insufficient evidence. Confidence is a model routing signal, not calibrated accuracy. A valid-looking semantic error can still escape detection |
| Time/calls | Four calls maximum, two attempts per step, one-second technical retry wait. Shared 240-second cooperative budget starts before enrichment. Model I/O waits are capped by the smaller of configured timeout and remaining budget; checks occur between chunks and after responses. An in-flight operation can overshoot by a bounded wait; there is no hard cancellation guarantee |
| Bytes/tokens | Input event 8 KiB, prompt 32,000 characters, model response 64 KiB, completion budget defaults to 1,024 tokens. Streaming checks bound application buffering and reject unexpected compression. Existing Phase 3 evidence limits still apply |
| Errors | Malformed event/key, exhausted model transport retries/deadline, and technical enrichment failure go to `processing-errors`. Envelope includes position, optional validated event, payload hash and step outcomes, not raw malformed content or credentials |
| Acknowledgements | Auto-commit and auto-offset-store disabled. Idempotent producer, `acks=all`, explicit delivery callback, then synchronous offset+1 commit with per-partition errors checked. Either failure stops the worker |
| Replay | Crash/commit failure after acknowledged output may repeat inference and output. Idempotent producer does not deduplicate across worker restarts. No distributed transaction or exactly-once claim |
| Shutdown | SIGINT/SIGTERM stops fetching new work and drains the current record. Broker maximum poll interval is ten minutes; Compose stop grace is nine minutes. Forced kill can replay the current item |
| Logs | JSON startup/commit/stop/failure metadata; no full prompts, text, API keys/secrets or upstream error bodies. Output keys and offsets are logged. Docker rotates worker logs at 10 MiB × 3 files |

`acks=all` in this single-node assignment deployment acknowledges one replica; it does not provide multi-node fault tolerance. Topic retention still bounds how long records survive, and model throughput may lag ingestion. Processing errors are delivered outcomes, not automatically rescheduled jobs; retrying them requires a deliberate replay. There is no sink, API, durable deduplication, calibrated classifier, or citation retrieval in Phase 4.

## Troubleshooting

- Worker exits after ten edits: expected; inspect results, then start the next batch or set continuous mode and relaunch.
- `worker_failed`: inspect the named broker operation, topic availability and group state; fix delivery, then restart. Do not reset offsets to hide a failure.
- `model_failed`: inspect provider/model availability and configured limits; no automatic fallback occurs. Technical failures are inspectable in `processing-errors`.
- `invalid_output`/`low_confidence`/`contradiction`: inspect the saved evaluation transcript and exact quotes. A larger model may help but must pass its own evaluation. Do not bypass validation.
- Long stop: current inference is draining. Forced termination may cause duplicate work on restart.

Test cleanup is automatic. To stop the user's application while keeping data and downloaded weights, use `docker compose --profile tools down --remove-orphans` without `--volumes`.

## Observed verification

The final tested commit, counts, timings, mutation check, model results, CI and PR links are recorded here before handover. No later phase has started.

## References

The adapter follows the official [Confluent Python API](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html) for delivery callbacks and synchronous commits, and [librdkafka configuration](https://docs.confluent.io/platform/current/clients/librdkafka/html/md_CONFIGURATION.html) for manual offset control, idempotence and poll limits. The pinned [2.16.0 package](https://pypi.org/project/confluent-kafka/2.16.0/) provides Python 3.13 wheels for the tested macOS ARM64/Linux environments.
