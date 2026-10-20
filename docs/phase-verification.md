# Verify each phase

**Current status: Phase 1 is implemented.** Run `make verify-phase-1` for its deterministic checks; use the [README](../README.md) and [Phase 1 record](phases/01-foundation.md) for the separate real-model smoke. Phases 2–6 remain planned and their commands do not exist yet.

[Original assignment](assignment/fde-take-home-exercise.md) · [Phase records](phases/README.md) · [Testing policy](testing.md) · [Progress](progress.md)

## Reviewer workflow

1. Open the phase PR and read its linked phase record: what changed, prerequisites, known limitations, and tested commit.
2. Check out that PR, or use the merged commit recorded for that phase. Run commands from the repository root. Check `git status` before switching so local work is preserved. To inspect a historical phase, use its recorded commit rather than assuming current main behaves identically.
3. Run the phase's verification command. It must run the applicable earlier checks as well as new assertions, print a summary, and exit nonzero on a failure. Read the behavioral evidence below as well as the exit status.
4. Run any separately documented live smoke test. It must name the provider/model, prerequisites, costs or downloads, and timeout. A skipped live check is **not verified**, not a pass.
5. Compare actual output with the phase's expected result and inspect the saved evidence. Record the tested commit, command, exit status, fixture IDs, and artifact location in the phase record.

Commands must use isolated test resources. Every implemented phase record must include setup and cleanup steps, expected duration, failure troubleshooting, and exact example outputs from a real run. Do not ask reviewers to infer an endpoint, topic name, environment variable, or fixture identifier.

## Commands at a glance

Phases 0 and 1 are available now. `make verify-phase-N` is the agreed entry point for deterministic verification; external-source/model smoke tests are separate so the repeatable checks do not depend on live services.

| Phase | Command from repository root | Evidence of intended behavior | Availability |
|---|---|---|---|
| [0: planning](phases/00-plan.md) | `shasum -a 256 docs/assignment/fde-take-home-exercise.md` | Hash matches the [recorded original](assignment/README.md); documentation links and phase criteria are present | Available |
| [1: foundation](phases/01-foundation.md) | `make verify-phase-1` | Configuration and schema tests pass; broker/database become ready; setup can run twice safely | Implemented |
| [2: ingestion](phases/02-ingestion.md) | `make verify-phase-2` | Known fixture records reach the correct topics with exact keys/fields; unwanted records are absent | Planned |
| [3: enrichment](phases/03-enrichment.md) | `make verify-phase-3` | Known revisions yield expected before/after evidence; unavailable content has an explicit status | Planned |
| [4: reasoning](phases/04-reasoning.md) | `make verify-phase-4` | Valid extraction/assessment results; bounded retries and abstention; no offset commit on publish failure | Planned |
| [5: serving](phases/05-serving.md) | `make verify-phase-5` | Seeded event reaches the API; replay leaves one logical stored result; sink recovers after outage | Planned |
| [6: acceptance](phases/06-acceptance.md) | `make verify-phase-6` | Cumulative tests, clean-start fixture path, and recovery drills pass; coverage has no missing lines/branches | Planned |

The table specifies assertions; actual Phase 1 observations are in its linked phase record. Live model quality and hardware feasibility require additional evidence even when deterministic checks pass.

## Phase 0 — inspect the plan and original

**Prerequisites:** Git, a SHA-256 utility, and this branch checked out. No Docker or model is needed.

```sh
shasum -a 256 docs/assignment/fde-take-home-exercise.md
git diff --check origin/main...HEAD
```

**Expected:** the hash matches the [assignment provenance record](assignment/README.md). The whitespace check exits zero without output. Check that the README links to the assignment, this guide, every phase, and the AI log. A whitespace check does not establish application behavior.

**Cleanup:** none. These commands only read files. If the hash differs, compare the committed file against the supplied original; do not silently update the expected hash.

## Phase 1 — prove the foundation starts

**Available command:** `make verify-phase-1`. See the [Phase 1 record](phases/01-foundation.md) for exact setup, actual outcomes, and troubleshooting.

- Validate configuration and event/result schemas; reject missing/invalid configuration with a useful error.
- Start real broker/database test instances and verify readiness. Initialize topics/schema twice and assert the second run succeeds without duplication.
- Assert both model adapters' configuration contracts using stubs, including no silent hosted fallback.

**Separate live demonstration:** use the README's exact local setup and hosted setup commands, once each. Local mode must initialize/download its selected model; hosted mode must not download local weights. Submit one small real request to each provider and record the model/version and response. Missing hosted credentials mean hosted smoke remains pending.

**Pass evidence:** readiness output, topic/schema inspection, configuration tests, model smoke outcomes, and measured resource/startup requirements. No claim that a stub verifies a real provider.

## Phase 2 — prove filtering, projection, and routing

**Future automated command:** `make verify-phase-2`.

Use a named, committed six-record SSE fixture: two accepted article edits, one bot edit, one non-article namespace edit, one heartbeat, and one malformed candidate event. Disable sampling for this fixture run only; test sampling separately.

**Expected:** exactly two projected records with the expected event keys and revision IDs in the edits topic, one error record in the ingest-errors topic, and no output for the three intentionally ignored records. Native Connect tests assert exact fields and timestamp formats. The test must fail on a missing or extra record, not merely check that a topic exists.

**Separate live demonstration:** bounded live ingestion with the exact `rpk` inspection command documented in the phase PR. Record input/accepted/filtered/error counts; do not require a particular live event to arrive.

## Phase 3 — prove actual content is fetched

**Future automated command:** `make verify-phase-3`.

Use committed API fixtures for a known substantive edit, a routine wording edit, a missing/deleted revision, a rate-limited response, and oversized content.

**Expected:** exact before/after text and source IDs for the normal cases; explicit unavailable/truncated/error status for failures; bounded requests and correct retry handling. A fixture containing HTML or instructions must remain untrusted content. Assert the permitted endpoint rather than following arbitrary URLs from the event.

**Separate live demonstration:** fetch a documented pair of public revision IDs and inspect the extracted evidence. Record that public revisions can later become unavailable; the committed fixtures remain the deterministic reference.

## Phase 4 — prove reasoning and safe failure behavior

**Future automated command:** `make verify-phase-4`.

Run real broker tests with deterministic model responses for: valid extraction plus assessment, dirty/invalid JSON, low confidence, unsupported evidence, exhausted retries, model timeout, and output publication failure.

**Expected:** a valid result contains evidence and prompt/model versions; invalid or uncertain content cannot become a confident routine result; every item obeys the call/deadline budget. Force publication failure and inspect the consumer offset: it must not advance past that item. Then allow publication and verify it completes. Check graceful shutdown and replay as well.

**Test strength:** deliberately break a risky parser/branch behavior in an isolated test change, show the relevant test failing, restore it, and show the suite passing. Preserve the evidence without committing a broken implementation.

**Separate live demonstration:** run the development evaluation set against the selected real model, showing that the result depends on the actual revision content. Record quality separately from unit coverage.

## Phase 5 — prove results are persisted and served

**Future automated command:** `make verify-phase-5`.

Send one known event through the full fixture pipeline and query the documented API endpoint by its ID. The phase PR must supply an exact copy-paste request and expected JSON example.

**Expected:** source ID, decision, evidence, and model/prompt version match the fixture. Replay the event and assert one row for its logical analysis key. Stop the test database/sink, deliver another event, restore it, and assert eventual queryability without lost output. Invalid pagination and missing IDs must return the documented responses.

Inspect both storage and API output: a successful HTTP status alone is insufficient. Record the sink's error routing and recovery behavior.

## Phase 6 — prove the submission is reproducible

**Future automated command:** `make verify-phase-6`.

Run all prior deterministic checks, including 100% application line and branch coverage, against isolated fresh test volumes. Rehearse worker/broker/database/model failure and recovery, checking results and offsets rather than just container restarts.

**Separate live acceptance:** from a clean clone, follow the final README exactly using `docker compose up`. Verify local bootstrap and the documented hosted alternative, then process a live event. Run the held-out model evaluation using a predeclared rubric and report false alarms, missed review cases, evidence quality, abstention, and latency. Record limitations honestly.

**Submission gate:** all required deterministic and live checks have evidence; no required check is silently skipped; the original assignment's deliverables exist; Damien has supplied his independent README sections. Use test-owned volumes for cleanup and never remove existing user data.

## Evidence template for each phase PR

| Field | Required entry |
|---|---|
| Tested version | Commit SHA and PR link |
| Setup | Exact commands, dependencies, model/backend, environment requirements without secrets |
| Verification | Copy-paste command, actual exit status, test totals, expected versus actual behavior |
| Coverage | Line and branch percentages plus zero missing lines/branches, or explicitly not applicable |
| Demonstration | Fixture/source IDs, topic or API command, expected output, actual output |
| Failure case | Trigger, expected recovery/failure, observed result |
| Artifacts | CI report link or committed small sanitized evidence file |
| Live checks | Provider/model/version, command, result, latency; clearly identify anything not verified |
| Cleanup | Exact commands scoped to test-owned resources |
| Handover | Remaining issue and the next reproducible step |
