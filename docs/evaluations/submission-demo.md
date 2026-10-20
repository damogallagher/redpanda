# Executed submission demo — 20 October 2026

Requested after PR #11 merged. Extends the walkthrough in PR #12. The execution uses project `triage-submission-20261020`, private copies of the selected profiles, random loopback ports, empty broker/database/model volumes, and exactly three live edits per provider. Existing user data/model volumes and private profiles are retained. The application implementation at the start is unchanged from `55fdf4e`; execution begins at documentation commit `92262eb`.

## Reproduction

Follow [the walkthrough](../submission-demo.md). The recorded execution uses a separate project and port 0 in its private profile copies, with `WORKER_MAX_ITEMS=3` and `INGEST_SAMPLE_ALL=true`; commands and application code are otherwise the same. Run Ollama's fixed cases and live batch first, reset only this demonstration's data, then run frontier fixed cases and live batch. The maximum initial hosted budget is 40 requests. Original profiles are restored afterward.

Fixed cases and prompt templates are frozen before this run, identified by hashes in the evidence manifest. These are regression checks of previously used cases, not newly held-out evaluation. All actual failures, fixes, reruns and abstentions will be retained. Live source content/model behavior varies; safe abstention does not establish semantic accuracy.

## Verified baseline

`make test UV='uvx --from uv==0.13.4 uv'` exited 0: 416 unit tests, 29 integration/configuration checks, 72 native Connect cases, 1,082/1,082 application lines and 276/276 branches covered, no warnings or exclusions. This is the baseline before live execution. Provider execution evidence follows after completion.

## Issues reproduced and fixed

The `topics` helper inherits the broker image's anonymous `/var/lib/redpanda/data` volume, and `db-migrate` inherits Postgres's anonymous `/var/lib/postgresql/data` volume. Both are CLI clients and need neither data directory. Actual container inspection identified these two unused volumes in the clean demo. A new real-Docker regression test failed before the change and passes afterward, checking that both helpers finish successfully without persistent-volume mounts. Both paths now use small temporary filesystems; the real broker/database named volumes are unchanged. Existing unrelated anonymous volumes are not removed.

The startup hint previously mentioned the default ten edits even when the selected profile requested three. It now states that the selected profile controls batch size; runtime logs still record the actual limit. All 15 existing launcher/profile checks pass. No model prompts or expected labels were changed.

## Ollama result

The first clean run passed 9/9 fixed cases using 14 calls in 97.904 seconds; evaluation plus fresh weight bootstrap took 165.757 seconds. The live batch used six further local calls and stored three rows, with no processing/sink errors and zero storage-consumer lag. One edit was assessed as `review`; two became `insufficient_evidence` after invalid extraction output. Total evaluation/startup/live execution took 362.216 seconds. This run used the original helper storage configuration and exposed the volume issue above; inference prompts/application Python were unchanged by its fix. Full private details and logs are retained under `reports/submission-demo/`; curated evidence will be linked after the hosted run.
