# Executed submission demo — 20 October 2026

Historical execution evidence for the commits and images recorded here. Later evidence-limit/security changes and the Ollama image update are not a new model evaluation. Follow the [current demo guide](../submission-demo.md) for a fresh run; it includes subsequent setup and diagnostic corrections.

Requested after PR #11 merged. Extends the walkthrough in PR #12, which merged during execution; the fix is on `fix/submission-demo` from main `447920f`. The execution uses project `triage-submission-20261020`, private copies of the selected profiles, random loopback ports, empty broker/database/model volumes, and exactly three live edits per provider. Existing user data/model volumes and private profiles are retained. The application implementation at the start is unchanged from `55fdf4e`; execution begins at documentation commit `92262eb`.

## Reproduction

Follow [the walkthrough](../submission-demo.md). The recorded execution uses a separate project and port 0 in its private profile copies, with `WORKER_MAX_ITEMS=3` and `INGEST_SAMPLE_ALL=true`; the original execution used the application code identified above. Current instructions and behavior include later fixes, so new outcomes and model-call counts may differ. Run Ollama's fixed cases and live batch first, reset only this demonstration's data, then run frontier fixed cases and live batch. The maximum initial hosted budget is 40 requests. Original profiles are restored afterward.

Fixed cases and prompt templates are frozen before this run, identified by hashes in the evidence manifest. These are regression checks of previously used cases, not newly held-out evaluation. Actual failures, fixes, reruns and abstentions are retained. Live source content/model behavior varies; safe abstention does not establish semantic accuracy.

## Verified baseline

`make test UV='uvx --from uv==0.13.4 uv'` exited 0: 416 unit tests, 29 integration/configuration checks, 72 native Connect cases, 1,082/1,082 application lines and 276/276 branches covered, no warnings or exclusions. This is the baseline before live execution; the final gate below includes the new helper regression.

## Issues reproduced and fixed

The `topics` helper inherits the broker image's anonymous `/var/lib/redpanda/data` volume, and `db-migrate` inherits Postgres's anonymous `/var/lib/postgresql/data` volume. Both are CLI clients and need neither data directory. Actual container inspection identified these two unused volumes in the clean demo. A new real-Docker regression test failed before the change and passes afterward, checking that both helpers finish successfully without persistent-volume mounts. Both paths now use small temporary filesystems; the real broker/database named volumes are unchanged. Existing unrelated anonymous volumes are not removed.

The startup hint previously mentioned the default ten edits even when the selected profile requested three. It now states that the selected profile controls batch size; runtime logs still record the actual limit. All 15 existing launcher/profile checks pass. No model prompts or expected labels were changed.

## Ollama result

The first clean run passed 9/9 fixed cases using 14 calls in 97.904 seconds; evaluation plus fresh weight bootstrap took 165.757 seconds. The live batch used six further local calls and stored three rows, with no processing/sink errors and zero storage-consumer lag. One edit was assessed as `review`; two became `insufficient_evidence` after invalid extraction output. Total evaluation/startup/live execution took 362.216 seconds. This run used the original helper storage configuration and exposed the volume issue above; inference prompts/application Python were unchanged by its fix. Full private details and logs are retained under `reports/submission-demo/` in the execution checkout; curated evidence is linked below.

## Frontier result and saved evidence

Frontier passed 9/9 fixed cases using 14 calls in 39.756 seconds. Its live batch made four calls and stored three rows: one assessed `review`, one assessed `routine`, and one `insufficient_evidence` due to incomplete source evidence (zero calls for that edit). There were no processing/sink errors and storage-consumer lag was zero. Total evaluation/startup/live execution took 64.240 seconds. Total hosted requests for this turn: **18**, below the initial maximum of 40. Currency cost was not measured. No retry evaluation or extra paid smoke was needed.

The frontier run used `da0969e`; its tracked tree is identical to `ce40ca6`, the same fix cherry-picked onto merged main after PR #12 closed. It also verified the corrected helpers have no persistent-volume mounts. The initial local run used the original helper configuration and exposed the issue. Application Python, model prompts, and frozen cases are unchanged across both runs.

Full curated synthetic prompts/responses: [Ollama](../evidence/submission-model-local.json), [frontier](../evidence/submission-model-frontier.json). [Verification summary](../evidence/submission-demo-verification.json) includes timings, revision IDs, decisions/outcomes, offsets/lag summaries, request counts, frozen-input hashes, cleanup, and limits. Complete live API pages/details and worker/service logs remain in ignored private reports; routine live content is not automatically published. These different live inputs do not support a paired provider-quality comparison.

## Shutdown, retained data and cleanup

After frontier completion, the default stop preserved all three demonstration volumes. Starting only `sink api` restored the exact same three-row API page, without starting the worker, ingestion or Ollama and without additional inference. Explicit data cleanup removed only the demo broker/database volumes and retained its weights; explicit model cleanup then removed only those demo weights. All demo containers/networks/volumes were gone, and the complete pre-existing volume-name set remained identical. The two identified original helper leaks were removed by their exact recorded demo-owned names; no global prune was used. Private working profiles were restored byte-for-byte and with their original permissions; the user's profiles were never modified.

## Reviewer commands and expected results

From a clean checkout, use `gh pr checkout 13` while the [review PR](https://github.com/damogallagher/redpanda/pull/13) is open, or update `main` after Damien merges it. Docker must be running. These checks make no model requests:

```sh
export UV='uvx --from uv==0.13.4 uv'
make test
make demo-success
make demo-failures
make demo-test-failure
```

The first three commands must exit 0. `make test` includes the helper regression and requires 416 unit tests, 30 integration checks, 72 native Connect cases, and 100% line/branch coverage. `make demo-test-failure` must exit nonzero (Make exit 2, one intentionally failed assertion); it demonstrates rejection of invented quotations and is excluded from the normal passing suite. Use `make test-unit` afterward for a green unit result.

The [walkthrough](../submission-demo.md) contains exact local/frontier setup, API inspection and cleanup commands. To repeat this particular three-edit observation, use the same profile bounds and model names; live input and decisions will vary. Preserve previous reports before rerunning. Full private logs, API details, JUnit and coverage evidence for this execution are copied to `reports/submission-demo-20261020/` in Damien's checkout. That folder is ignored by Git; the sanitized evidence above is available in the PR.

## Final deterministic verification

The completed final local gate passed on `71a0680` (implementation `ce40ca6`): **416 unit tests, 30 integration/configuration checks, 72 native Connect cases, 1,082/1,082 executable lines and 276/276 branches**, zero missing/excluded coverage and zero warnings. The gate took 248.928 seconds. `demo-success` passed its one end-to-end scenario; `demo-failures` passed all 19 selected fault/recovery scenarios; `demo-test-failure` produced exactly one expected failure and Make exit 2. The normal gate ran afterward and was green. No unexpected failures were discarded.

The assignment checksum and Damien's reserved README paragraphs match merged main. All 193 local Markdown links resolve and all 16 shell blocks in the walkthrough parse. The new changes contain no credentials; complete live content remains private. This change leaves model prompts, model output validation, dependency pins, and application Python unchanged.

[GitHub Linux CI](https://github.com/damogallagher/redpanda/actions/runs/39494682046) also passed on `71a0680`. Downloaded JUnit and coverage artifacts confirm 416 unit / 30 integration checks, all 1,082 lines and 276 branches covered without exclusions. Native Connect cases passed, both configurations linted clean, and the complete job log and check annotations contain zero warnings. Subsequent closeout changes are documentation/evidence only.
