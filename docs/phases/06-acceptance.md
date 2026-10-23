# Phase 06: Operational acceptance and handover

Historical checkpoint, merged in [PR #11](https://github.com/damogallagher/redpanda/pull/11). Behavior, versions, counts and handover statements below describe their recorded commits. Check out the recorded revision to reproduce that checkpoint. For the current system, use the [README](../../README.md), [verification commands](../phase-verification.md) and [handover](../handover.md).

Branch: `phase/06-acceptance`, from merged main `f9375ff` (PR #10). Status: implemented and verified; [PR #11](https://github.com/damogallagher/redpanda/pull/11) was merged by Damien. Damien reviews and merges.

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

The first three exit 0 when their assertions pass. The fourth **intentionally exits nonzero**, showing an invented quotation rejected by the real grounding validator. It is outside normal discovery, changes no production code and is not counted as a passing test. To see normal green results afterward run `make test` again. See the operator guide for the narrower commands and expected output. The pinned-tool equivalent is `make test UV='uvx --from uv==0.13.4 uv'`.

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

## Actions and dependency follow-up

The [CI maintenance record](06-ci-maintenance.md) documents the reported main-branch failure, current action/dependency pins, strict warning policy, and follow-up verification. Earlier phase results above remain tied to their recorded commits.

## Executed submission follow-up

After PR #11 and the walkthrough PR #12 merged, Damien requested an actual Ollama-then-frontier demo, saved evidence and any fixes. [PR #13](https://github.com/damogallagher/redpanda/pull/13) contains the [execution record](../evaluations/submission-demo.md), exact reproduction commands, [verification summary](../evidence/submission-demo-verification.json), and [visible conversation](../ai-log/sessions/2026-10-20-executed-demo.md). Both providers passed nine frozen cases and delivered three live results, including documented abstentions. A reproduced anonymous-volume leak in the two CLI helpers is fixed; the added real-Docker regression increases the cumulative integration count to 30. The original 416 unit tests still cover every application line and branch. Earlier results above remain attached to their original commits. Next step: Damien reviews PR #13 and completes his independent README observations before submission.

## Demo guide command audit — 22 October 2026

At Damien's request, [PR #18](https://github.com/damogallagher/redpanda/pull/18) now also audits the [current demo guide](../submission-demo.md) against the implementation. The changes add missing-profile setup before cleanup, isolate and remove Make's helper resources, specify group IDs and all shared passwords, distinguish consumed events from unique stored revisions, check error topics as well as API rows, and wait for asynchronous sink commits. The guide explains mutable model tags, stale reports, exact JSON fields, insertion ordering and failure exits. The operator guide's helper-cleanup description is corrected too.

The application/test/configuration tree is unchanged from `f792301` (and merged main `54e3157`). Executed locally with Docker 29.9.2 / Compose 5.6.0 and pinned uv 0.13.4:

| Check | Command / method | Observed result |
|---|---|---|
| Cumulative gate | `COMPOSE_PROJECT_NAME="$DEMO_TEST_PROJECT" make verify-phase-6 UV='uvx --from uv==0.13.4 uv'` (`make test` is the same target) | 453 unit / 32 integration / 72 Connect cases; 1,172/1,172 lines and 286/286 branches; no coverage exclusions; exit 0 |
| Successful path | `make demo-success UV='uvx --from uv==0.13.4 uv'` | One scenario passed; two controlled edits reached the API as `review` |
| Fault/recovery paths | `make demo-failures UV='uvx --from uv==0.13.4 uv'` | All 19 scenarios passed; exit 0 |
| Deliberately red test | `make demo-test-failure UV='uvx --from uv==0.13.4 uv'` | One failed test; Make exit 2, as intended |
| Return to green | `make test-unit UV='uvx --from uv==0.13.4 uv'` | 453 tests passed, still 100% line/branch coverage |
| Exact inspection commands | Execute step 6's three shell blocks with `DEMO_MODE=guide-fixture` against an isolated fixture pipeline | Readiness, list/detail JSON and empty error snapshots passed; a second inspection reached zero sink lag; an injected synthetic error was visible in a bounded topic snapshot |
| Setup and syntax | Execute profile creation twice in a temporary directory; resolve both example Compose configurations; `sh -n` on every demo shell block | New profiles mode 0600, existing bytes preserved, three-event/group/provider settings correct; 18 shell blocks valid |
| Cleanup | Use the guide's helper cleanup; integration/inspection fixtures delete only their own projects | Same 24 pre-existing volumes before/after, zero containers before/after; no application data/profile changes |

The first temporary inspection harness passed its shell program on stdin, which a Docker exec command consumed, so its expected output file was absent. The harness was corrected to run a script file; the guide's read-only commands also detach stdin explicitly. Subsequent exact-block execution passed. This harness failure is retained in ignored reports and is not represented as an application test failure or a successful initial audit.

[Verification JSON](../evidence/demo-guide-verification.json) records scope, commands, report hashes and the checked guide hash. No new application tests were added for these documentation edits. No real model calls, live Wikipedia requests or fresh vulnerability scans were made: model results remain historical and provider availability/semantic outputs remain variable. README.md (including the personal sections), the original assignment and frozen study pack are unchanged. Damien reviews/merges PR #18. The [conversation record](../ai-log/sessions/2026-10-22-submission-readiness.md) includes this audit.
