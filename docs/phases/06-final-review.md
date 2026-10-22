# Final repository documentation review — 22–23 October 2026

Branch `docs/final-repository-review`, based on merged main `7a3410842e5a9f12813a93d32366c564a8f1dda9` after PR #20. This review changes documentation and the visible conversation log. Application code, tests, configuration, dependencies, workflow, the original assignment, personal README sections and study-pack artifacts are unchanged.

## What changed and why

- Added a first-run README path with prerequisites, clone/ZIP guidance, separate local and frontier entry points, private-profile setup, shared database passwords, model costs, readiness, result inspection and bounded model evaluations. Frontier-only setup no longer relies on first following the local section.
- Made the README's database command actually show `triage_results`, matching its expected output. Added isolated helper-project cleanup after the deterministic gate, alongside the existing test-owned resource cleanup.
- Corrected the current focused foundation count to five: the helper-volume regression is part of that target. The cumulative totals remain 453 unit / 32 integration / 72 Connect cases.
- Corrected the development evaluation's claim that Phase 6 evaluation was pending. The separate acceptance runs were completed on 20 October; repeated runs are regression checks, not unseen accuracy evidence.
- Clearly labelled the original implementation plan, phase checkpoints, progress history, dependency reviews and model/scan observations by their dates and commits. Historical counts, failures and conversation wording are retained. Earlier plans are not instructions to reset history or repeat work.
- Updated the handover/demo baseline to the verified post-PR-20 main commit. Clarified that the optional fresh-checkout live acceptance requires Git history, while normal startup/tests work from a tracked-file ZIP.

The existing study pack describes the same unchanged runtime. All five artifact hashes still match its manifest; no PDF or interactive material was regenerated. The entire README from `## Tradeoffs` onward is byte-for-byte unchanged. Independent authorship and human review remain the candidate's responsibility.

## Repeat the checks

Start Docker; use a POSIX shell, Make and uv from the repository root. The complete commands and expected output are in the [README](../../README.md#getting-started) and [demo guide](../submission-demo.md). For the model-free gate:

```sh
REVIEW_TEST_PROJECT="triage-doc-review-$(date +%s)-$$"
COMPOSE_PROJECT_NAME="$REVIEW_TEST_PROJECT" make verify-phase-6 UV='uvx --from uv==0.13.4 uv'
```

Expect exit 0, 453 unit tests, 32 integration checks, 72 native Connect cases, and 100% application line and branch coverage. Reports are in `reports/`. Stop on an unexpected failure and inspect the report; do not treat a later cleanup exit code as the test's outcome. Remove the helper project in the same terminal, including after a failed gate:

```sh
docker compose --env-file /dev/null -f compose.infrastructure.yml \
  -p "$REVIEW_TEST_PROJECT" --profile tools down --volumes --remove-orphans
```

Keep the generated test project name. This cleanup must not target a retained application project. Integration fixtures remove their own disposable projects.

For the revised README inspection commands, select a private profile and follow [synthetic stored results](../../README.md#inspect-persisted-results--no-model-needed). `make seed-results` starts storage/API dependencies without inference. Expect the five topics, schema versions 1 and 2, `triage_results`, readiness `{"status":"ready"}`, and three `demo-v1` decisions: revision 101 `review`, 102 `routine`, 103 `insufficient_evidence`. The detail response for 101 names model `fixture-not-a-real-model`. A fresh synthetic-only stack has an empty `triage-v1` list; that is expected, not a live inference result. Results arrive asynchronously; allow the sink to catch up before asserting counts.

## Observed verification

The cumulative local gate passed on the unchanged application from `7a34108`: **453 unit / 32 integration / 72 Connect**, **1,172/1,172 lines and 286/286 branches**, zero failures, skips, exclusions or emitted warnings. Existing launcher/profile tests verify mode selection and failure handling; test collection separately confirmed 15 startup cases and five foundation cases.

A clean tracked-file export, with no Git metadata, ran the README's guarded profile-copy commands. Both profiles were created with mode 0600 and preserved existing settings when repeated. The synthetic seed command and topic/database/API/detail examples passed in a unique Docker project with random loopback ports. No ingestion, worker or model was started for this synthetic inspection. Only the audit's projects were removed; all 24 pre-existing volume names were preserved and no containers remained.

The [machine-readable review](../evidence/final-repository-review.json) records documentation links/anchors, shell syntax, command-target checks, unchanged-file assertions and report hashes. These static checks exclude historical conversation transcripts from link/command validation; their wording is preserved as evidence. The local audit initially used the host's older Python for temporary archive extraction; it rejected the modern safe-extraction argument before extraction or application startup. Repeating that preparation with the project's Python 3.13 succeeded. This was an audit-tool invocation issue, not an application change.

Baseline main [CI run 39864138316](https://github.com/damogallagher/redpanda/actions/runs/39864138316) already passed these totals with no warnings or annotations. The review PR's separate checks must pass before merge, and the final submitted main commit needs its own passing run.

## Scope and handover

No real model requests, live Wikipedia calls, new vulnerability scans or external-link availability sweep were performed. Earlier real-model results and vendor-image findings remain dated evidence, not fresh validation. Run the chosen local/frontier configuration before presenting, using the [current demo guide](../submission-demo.md), and retain actual failures or abstentions.

Review this documentation PR and merge it when satisfied. This audit checks the documented contracts against the current code and executed tests; it is not a guarantee of perfect model judgments, universal hardware compatibility or complete production security. The [review conversation](../ai-log/sessions/2026-10-22-final-repository-review.md) and preceding [main check](../ai-log/sessions/2026-10-22-main-final-check.md) retain the visible audit trail without recreating previously omitted personal-writing exchanges.
