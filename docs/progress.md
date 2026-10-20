# Progress

## 20 October 2026 — Phase 0

Completed planning activities:

- Read the assignment and distinguished its requirements from Damien's additional requirements.
- Confirmed GitHub access and that the repository is public.
- Checked official Redpanda Connect, testing, licensing, HTTP input, rpk, local startup, and MediaWiki Compare documentation.
- Prepared six implementation phases, test checkpoints, coverage policy, PR template, and visible interaction logging policy.
- Confirmed Wikipedia edit triage, Python, selectable local/hosted inference, Friday 23 October deadline, and Damien's review/merge of each phase.
- Received an explicit correction to start with entirely new repository history. The initial history reset is authorized; implementation must not reuse prior work.

Planning PR #1 is merged. All implementation and runtime tests remain pending. Phase 1 must measure this machine's resources, choose pinned model/provider versions, and verify both model paths.

No model, application, Docker stack, or unit suite has been run in this planning phase. No production-readiness or coverage result is claimed.

Planning PR: [#1](https://github.com/damogallagher/redpanda/pull/1). Merged by Damien.

Executed Phase 0 validation:

- Verified all relative links across 15 Markdown files: zero broken links.
- `git diff --cached --check`: passed; documentation only, no runtime tests applicable.
- Created fresh root commit `c7a42ba` and replaced GitHub main using a lease against the previously observed remote tip. Main now starts with the new empty baseline.
- Planning branch: `phase/00-plan`. All implementation phases remain unstarted.

Next step: after the planning PR is merged, create `phase/01-foundation` from updated main and perform the hardware/model feasibility checkpoint.


## 20 October 2026 — Assignment and verification documentation follow-up

- Copied the original assignment unchanged into `docs/assignment/fde-take-home-exercise.md` and recorded its SHA-256 and provenance.
- Added `docs/phase-verification.md`: a command matrix, reviewer workflow, concrete success/failure assertions per phase, and an evidence template.
- Linked the assignment and guide prominently from README; added each phase's proposed command to its record; strengthened the PR template with setup, expected output, cleanup, and troubleshooting requirements.
- Updated the visible conversation log. No application work was started.
- Validation: assignment matches the supplied file byte for byte; 18 Markdown files checked with zero broken relative links; all six implementation phase records contain the expected command and not-yet-implemented warning; staged whitespace check passed.

Branch: `docs/assignment-and-phase-verification`. Review/merge remains Damien's responsibility. Phase 1 should start from main after these documentation additions are merged.

Documentation follow-up PR: [#2](https://github.com/damogallagher/redpanda/pull/2), opened for Damien's review. Verified content commit: `7c7a3c3`; the following audit-only commit records the PR and closing response.


## 20 October 2026 — Phase 1 foundation

PR #2 is merged. Created `phase/01-foundation` from main at `8e0fa6e`.

Built the local infrastructure, repeatable topic/database initialization, typed settings, versioned schemas, explicit Ollama/OpenAI model adapters, diagnostics CLI, non-root container, locked dependencies, Make commands, and CI workflow. README now has local/hosted/native-host setup and executable Phase 1 verification instructions. Added repository continuation instructions and this session's visible interaction log.

Real smoke requests succeeded for local Qwen2.5 7B and hosted GPT-6.1 Sol. The selected local model returned a concise semantic comparison; the smaller Qwen3 4B candidate returned unwanted verbose content. Both candidate and selected evidence are retained. No claim of model accuracy is made from these individual probes.

The API key was read only from the user-supplied untracked `.env` for the authorized hosted smoke, never copied to repository files or printed. Tests do not call paid inference. No subsequent phase was started.

Final local verification passed on application commit `e278b5b`: 86 unit tests, 3 real infrastructure tests, 100% line coverage (176/176) and branch coverage (32/32), no excluded lines. Both real model smoke checks passed. Machine-readable results are in `docs/evidence/phase-1-verification.json`. Review [PR #3](https://github.com/damogallagher/redpanda/pull/3). The initial GitHub Linux CI run passed; the PR displays current checks after the final review fixes. Next step: Damien reviews the Phase 1 PR; after merge, request Phase 2 to add Connect ingestion.

Local handover: the verification demo used Compose project `redpanda-phase1`. Its containers are stopped after verification, with volumes retained. To reuse those downloaded weights on this machine, set `COMPOSE_PROJECT_NAME=redpanda-phase1` in the untracked `.env` before following the README; preserve the existing API key. This is optional and unnecessary for reviewers on other machines. Disposable integration projects were removed by their test fixture.

## 20 October 2026 — Dependency version review

Damien merged Phase 1 PR #3; main is now `62f2330`. In response to the question about PostgreSQL 17 and latest libraries, compared the current pins with official upstream sources. The [version review](dependency-versions.md) records the findings, sources, recommendations, and how to verify an upgrade.

Recommendation: retain PostgreSQL major 16 as named in the assignment, but update its maintenance release from 16.14 to 16.15. HTTPX, Pydantic, and the direct test/lint/type dependencies already match current releases. Hatchling and uv have newer stable releases worth updating with build verification. Python 3.13 remains supported; keep the tested runtime for this exercise.

This follow-up changes documentation and the visible interaction log only. Runtime files, dependency pins, and previous test evidence remain unchanged. Phase 2 has not started.

Documentation validation: all 22 relative file links across the four changed Markdown files resolve; `git diff --check` passed. No runtime tests were rerun for this documentation-only review.

## 20 October 2026 — Phase 1 dependency updates

PR #4 is merged. Created `maintenance/phase-1-dependency-updates` from main `cf664e1` for the requested PostgreSQL 16.15, Hatchling 1.32.4, and uv 0.13.3 upgrades. Docker and CI use the same uv pin. PostgreSQL uses a verified ARM64/AMD64 manifest digest. The runtime/test lockfile passes `uv lock --check` without changes.

Added a disposable PostgreSQL upgrade integration test: seed 16.14, stop it, recreate with 16.15 using the same test volume, verify unchanged data and migration timestamp, then verify new writes. Cleanup targets only the test's unique Compose project.

Implementation commit `68d33a3` passed `make verify-phase-1 UV='uvx --from uv==0.13.3 uv'`: 86 unit tests, 4 integration tests, 176/176 executable lines and 32/32 branches covered, zero failures/skips/exclusions. Formatting, lint, strict types, Compose validation, and the rebuilt packaged CLI passed. The [maintenance guide](phases/01-dependency-updates.md) and [verification JSON](evidence/phase-1-dependency-updates.json) record exact commands and outcomes.

The user's global uv installation, `.env`, and demo data volumes were not modified. No live model calls were made. Restored the previous review's final response to the log because its commit landed on the branch after PR #4 merged. Phase 2 remains unstarted; Damien reviews and merges this maintenance PR.

Review [PR #5](https://github.com/damogallagher/redpanda/pull/5). GitHub Linux CI passed on `e853a1f` in 1 minute 7 seconds ([run](https://github.com/damogallagher/redpanda/actions/runs/39418079879)). All 83 relative documentation links resolved; the original assignment checksum and whitespace checks passed. Test-owned containers and volumes were confirmed removed. The clean user checkout was switched to `maintenance/phase-1-dependency-updates`, preserving ignored local configuration.

## 20 October 2026 — Phase 2 ingestion

PR #5 is merged. Created `phase/02-ingestion` from main `cf2cf4c`. Added pinned Redpanda Connect 4.114.0 with native HTTP streaming, Wikimedia-specific SSE framing, filters, deterministic 1% selection, existing event-contract projection, provenance headers, bounded error envelopes, and Prometheus counters. Both local and hosted Compose modes now include ingestion; diagnostic port 4195 is loopback only.

Added synthetic LF/CRLF fixtures, 40 native processor tests, four real HTTP-to-broker tests, and a separate bounded live smoke. The cumulative gate passed on `0b9e370`: 86 unit tests, 8 integration tests, 176/176 executable Python lines and 32/32 branches covered, no failures/skips/exclusions. Native lint, formatting, types, Compose validation and the packaged CLI also passed. See [Phase 2](phases/02-ingestion.md) and its [verification evidence](evidence/phase-2-verification.json).

A real live run exposed scientific notation in large revision keys; two regression cases failed before the decimal formatting fix and pass afterward. A deliberate bot-filter mutation in a scratch copy also failed as expected. The corrected 30-second live observation processed 789 segments at snapshot and left 27 valid edits / zero errors after draining, with zero model calls. [Live evidence](evidence/phase-2-live.json) contains only projected public examples and counts.

The guide documents exact commands, expected fixture records, replay, error routing, metrics, cleanup, and limits: event-first LF/CRLF framing, one-event lookahead, separate frame/scanner bounds, no durable source checkpoint or gap-free guarantee. The original assignment and independent personal README sections are preserved. Next step: Damien reviews/merges this phase; Phase 3 enrichment starts only when requested.

Final cleanup inspection found the optional fixture server was excluded by Compose profiles. Fixed cleanup to enable the tools profile, removed only the four verified test-owned leftovers, and added assertions that test containers/volumes/networks are gone. The cumulative gate passed again after this fix.

Review [PR #6](https://github.com/damogallagher/redpanda/pull/6). The clean user checkout is on `phase/02-ingestion`; ignored `.env` and existing demo data were preserved. All 91 relative documentation links resolve, the original assignment checksum matches, and the final external cleanup inspection found no disposable Phase 2 fixture containers or volumes.

GitHub Ubuntu 24.04 CI passed on `621802f` in 1 minute 42 seconds ([run and artifacts](https://github.com/damogallagher/redpanda/actions/runs/39450490259)). The closing commit records this result and the final visible response only. PR #6 is left open for Damien; no Phase 3 work started.

## 20 October 2026 — Local/frontier startup follow-up

Damien requested separate scripts and private environment profiles, copied over `.env` on selection. Added `scripts/start-local.sh`, `scripts/start-frontier.sh`, their shared implementation, and complete secret-free `.env.local.example` / `.env.frontier.example` templates to the open Phase 2 PR #6. Private profile files stay ignored and outside the Docker build context.

The launchers validate with Compose and the existing configuration CLI before stopping the old stack, retain all named volumes, atomically install a private `.env`, and start services in the background. Profile selection clears conflicting inherited settings, never executes dotenv as shell, and uses a lock against simultaneous switches. Failed preflight/shutdown keeps the old `.env`; failed startup keeps the selected profile for retry.

Implementation/tests `d550e78` passed the cumulative gate: 99 unit tests (13 new launcher checks), 10 integration/configuration tests (two new profile contracts), 40 native Connect tests, 100% Python line and branch coverage with no exclusions. The focused `make test-startup` target passed all 15 cases. See [startup guide](startup.md) and [evidence](evidence/startup-launchers.json).

Created Damien's private profiles from his existing settings, preserving the project/database configuration and copying the existing API key into `.env.frontier` without displaying it. Ran local → frontier → local successfully: frontier ran no Ollama, Connect was ready in both modes, the database migration and downloaded model IDs survived, and local mode is running again. No paid model requests were made. The three private environment files have mode 0600 and are ignored by Git; startup logs were checked for absence of the API key.

The updated PR #6 passed GitHub Linux CI on `a3a127e` ([run and artifacts](https://github.com/damogallagher/redpanda/actions/runs/39453543842)). All 99 relative documentation links resolved and the original assignment checksum remained unchanged. The final audit-only commit records CI and the visible handover; the PR stays open for Damien to merge.


## 20 October 2026 — Phase 3 enrichment

PR #6 is merged. Created `phase/03-enrichment` from main `9749745`. Added the fixed-endpoint MediaWiki client, strict diff extraction with context, typed provenance/outcomes, bounded I/O/retries/evidence, offline inspection CLI, attributed fixtures, and separate live smoke. No reasoning worker or later phase has been started.

The [Phase 3 guide](phases/03-enrichment.md) documents exact success/failure commands, limits, cleanup, and troubleshooting. Implementation commit `29bf3c3` passed the full gate: 214 unit tests, 10 integration/configuration checks, 40 native Connect cases, and 451/451 lines plus 142/142 branches covered. The live comparison matched the fixture exactly in one request (0.287 seconds). A direction-reversal mutation was detected; a slow-stream deadline regression was reproduced and fixed. The user’s local stack remains running and test resources were cleaned up. Prompt/response logging continues in the [Phase 3 session](ai-log/sessions/2026-10-20-phase-3.md).

[PR #7](https://github.com/damogallagher/redpanda/pull/7) is open for Damien’s review; [Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39458242006) passed on `375902a`. The local checkout is on the review branch; success and both failure walkthroughs were verified there with private profiles unchanged. The PR remains unmerged.

## 20 October 2026 — Phase 4 reasoning and durable delivery

PR #7 is merged. Created `phase/04-reasoning` from `efbd03a`. Added versioned extraction/assessment/review prompts, strict JSON and exact-quote validation, a shared four-call budget, confidence routing, explicit abstention/errors, and a sequential Kafka worker. Output acknowledgement precedes synchronous offset commit; publication/commit failures stop processing for replay. Local/frontier startup now builds and starts the worker, with ten edits per run by default and explicit continuous mode.

The [Phase 4 guide](phases/04-reasoning.md) gives the cumulative gate, rpk walkthrough, failure/replay expectations and limitations. Eleven new real-broker scenarios cover normal output, repair, uncertainty, technical errors, failed publication, duplicate replay and SIGTERM. Two deliberate parser/confidence mutations were detected and restored. Application unit coverage remains enforced at 100% lines and branches without exclusions.

The first local development run passed 5/6 cases; the Belle semantic mistake caused abstention. General prompt improvements passed the same 6/6 cases in 67.232 seconds with ten calls. Both full transcripts and the predeclared rubric are retained in the [development record](evaluations/development.md). This is development tuning, not held-out accuracy or human review. No paid hosted calls were made. Phase 5 has not started. Final verification and PR handover are recorded in the phase guide and [session log](ai-log/sessions/2026-10-20-phase-4.md).

Phase 4 review: [PR #8](https://github.com/damogallagher/redpanda/pull/8), unmerged. Final implementation `63de01e` passed 333 unit tests, 21 integration/configuration tests, 40 native Connect cases, and 829/829 lines plus 236/236 branches (100%, no exclusions). Deeply nested JSON is handled as invalid output. Initial Linux CI passed on `1d56d5a`; current checks are attached to the PR. The two-case reviewer demo passed in Damien's checkout with all private profiles unchanged.

Final Phase 4 [Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39472093773) passed on `1154c86`, including the nesting fix. The local review checkout also passed all 333 unit tests at 100% coverage. The closing commit records verification and the final visible response only; PR #8 remains open for Damien.
