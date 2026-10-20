# Phase 06: Operational acceptance and handover

Branch: `phase/06-acceptance`, from merged main `f9375ff` (PR #10). Status: implemented and verified; [PR #11](https://github.com/damogallagher/redpanda/pull/11) is for Damien’s review. Damien reviews and merges.

## What changed

Added a short command menu and [operator guide](../operations.md) covering setup, local/frontier model checks, success/failure demonstrations, safe stopping, explicit data/weight deletion, recovery and troubleshooting. Existing startup scripts still copy the selected private profile over `.env`; model tests read their own profile without switching the active application.

Added two small Python utilities: bounded acceptance evaluation and Compose operations, with thin shell entry points. Model checks run nine frozen cases with at most 28 calls, preserve visible inputs/outputs in private reports, return nonzero on any failed case, and stop early on technical provider failure. Cleanup verifies project/volume ownership, rejects external volumes and never globally prunes Docker or touches native-host models.

Added real broker-outage and process-death drills, observing offsets, backlog, duplicates and eventual unique SQL rows. Added real selective-volume cleanup tests and a non-root runtime/build-tool exclusion check. `make test` / `make verify-phase-6` runs the cumulative deterministic gate. `make demo-success`, `make demo-failures`, and the deliberately red `make demo-test-failure` make outcomes easy to inspect.

The security review found build-tool and Debian 12 advisories. The runtime now uses a pinned Python 3.13.16 Debian 13 base and copies only the installed application environment from a build stage; pip, uv, ensurepip and source/build tooling are absent. Postgres remains 16.15. All remaining scan findings and scope limits are disclosed in the [security review](../security-review.md).

Added an [assignment/code-flow checklist](../handover.md), [frozen model evaluation](../evaluations/acceptance.md), and [conversation log](../ai-log/sessions/2026-10-20-phase-6.md). Original assignment and Damien's reserved personal README sections remain unchanged.

## Exact verification

Prerequisites: running Docker with Compose 2.20+, Make, uv; initial downloads need internet. Run from the repository root, one operation at a time:

```sh
make test
make demo-success
make demo-failures
make demo-test-failure
```

The first three exit 0 when their assertions pass. The fourth **intentionally exits nonzero**, showing an invented quotation rejected by the real grounding validator. It is outside normal discovery, changes no production code and is not counted as a passing test. To see normal green results afterward run `make test` again. See the operator guide for the narrower commands and expected output. The pinned-tool equivalent is `make test UV='uvx --from uv==0.13.3 uv'`.

| Check | Expected / observed |
|---|---|
| Unit gate | 416 passing tests; all 1,082 executable application lines and 276 branches covered; zero exclusions/missing coverage |
| Integration/configuration | 29 passing checks, including real Connect, broker, Postgres, API, process death, broker outage and cleanup |
| Native Connect | 72 passing cases (40 ingestion + 32 sink), both configurations lint clean |
| Static/build | Ruff, formatting, strict types, shell syntax, both Compose modes and installed container CLI pass |
| Worker crash after publication | Input remains uncommitted; restart consumes two pending edits; three Kafka outputs become two logical SQL rows |
| Broker outage during publication | Publication fails without offset advancement; restart after broker recovery drains two edits; two SQL rows |
| Database outage and sink restart | API returns 503, sink offset remains unchanged, restored DB receives pending work and advances offset |
| Cleanup | Default retains all volumes; data reset retains weights; model reset retains data; other-project sentinel survives |
| Deliberately wrong test | One pytest failure / Make nonzero; grounding validator rejects invented quote as designed |

Machine evidence and exact tested commits: [verification](../evidence/phase-6-verification.json). Reports under ignored `reports/` and CI artifacts include JUnit and coverage JSON/XML. The initial new acceptance requests omitted the API's mandatory `analysis_version`; the tests failed, were corrected in `a826e4a`, and pass afterward. No application API contract was weakened to accommodate the tests. The first GitHub run also exposed exact floating-point timeout equality; `8ea8ec4` gives that unit test a fixed clock without changing application timeout behavior.

## Live acceptance

```sh
./scripts/test-local.sh
./scripts/test-frontier.sh
make accept-live-local
```

Private profiles must exist; hosted mode requires a key and incurs charges. The first two check the frozen synthetic cases without Kafka/Wikipedia requests. First real runs passed **9/9 each**, with 14 calls each: Qwen2.5 7B in 135.600 seconds and GPT-6.1 Sol in 46.662 seconds. Prompts and expected labels were not tuned after viewing these cases. Read the [rubric and full transcripts](../evaluations/acceptance.md); this small result does not establish general accuracy or independent human review.

The last command exports committed HEAD into a clean temporary checkout, uses fresh application/model volumes and random ports, bootstraps the default local model and runs real public edits through the API. It bounds the worker to three edits (maximum 12 local calls) and enables all eligible edits for a short observation; normal default sampling remains 1%. It also stores the three canned synthetic examples. It removes only its own project and fresh weights. See [live evidence](../evidence/phase-6-live.json) for exact commit, timings, revision IDs, decisions, model ID and lag. The first API-query test mistake also affected the initial live test; it is recorded as failed, not silently discarded.

The final hardened-image run (`7fc26f1`) bootstrapped in 89.665 seconds and completed in 578.754 seconds. Three live outcomes and three synthetic rows reached the API; all three live edits abstained after two invalid extraction attempts each. **This is a startup/safe-delivery pass, not a model-quality pass on those edits.** The earlier live run (`a826e4a`) completed in 200.270 seconds with two routine and one review assessment; [its evidence is retained](../evidence/phase-6-live-earlier.json). Do not cherry-pick either run as representative accuracy. At shutdown the final test had processed three of 611 accepted edits (lag 608), because sampling was disabled for the observation and the worker deliberately stops at three. This demonstrates why inference latency and backlog require monitoring. The large-edit abstentions were not retuned away during acceptance.

## Handover and limits

On this 32 GiB ARM64 Mac, use the ready command menu; reviewers can select hosted inference instead of downloading weights. A first image/model download depends on bandwidth; real-model performance depends on machine and provider. Acceptance is bounded, not a throughput/load benchmark. Recovery demonstrations with fast model doubles show delivery semantics, not inference capacity.

The original assignment still requires Damien's independently written Tradeoffs, Surprises/production-failure observations and customer-value README sections. Those remain his work. The single-node deployment has no HA, TLS/auth, backup/restore or production database-role separation; upstream SSE delivery is not gap-free. The security scan retains upstream base-image findings. Review [deployment limits](../handover.md) before exposing the application beyond a local machine.

[Linux CI passed](https://github.com/damogallagher/redpanda/actions/runs/39483507050) on `8ea8ec4` in 5 minutes 36 seconds, with 416 unit / 29 integration checks and 100% line/branch coverage. The local final gate passed on application commit `7fc26f1`; the subsequent test-only clock fix passed 33 focused adapter tests and full Linux CI. Closing commits record evidence/conversation only. The user checkout is on the review branch with profiles preserved. No further phase is started and the PR is not merged by the agent.
