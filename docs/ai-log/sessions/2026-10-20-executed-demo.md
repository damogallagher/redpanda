# Executed submission demo — 20 October 2026

Follow-up on open PR #12. The user explicitly authorizes real Ollama/frontier execution and issue fixes. Provider credentials are never logged.

## User

Can you run the full demo for me, first with Ollama and then the frontier model, save the results, fix any issues, and update the docs and prompt log? Keep 100% coverage and open a PR for review.

## Assistant

> I’ll run the full Ollama demo, then the frontier demo, save both sets of results, and fix any issues the runs expose. I’ll keep the hosted calls bounded, verify 100% coverage, and put the evidence, documentation, and prompt log into a review PR.

## Assistant

> The walkthrough PR is still open, so I’ll add the executed results there. I’ll use a fresh demo project with empty data, preserving your existing profiles and volumes. The first hosted run will be limited to the nine fixed cases plus three live edits—at most 40 calls.

## Assistant

> The initial unit suite has passed with 100% line and branch coverage. The real broker/database checks are still running. I’ve also prepared separate evidence folders for model evaluations, worker logs, API results, error records, and consumer offsets so we can verify delivery as well as inference.

## Assistant

> The recovery, persistence, and cleanup checks have passed so far. Once the remaining worker checks finish, I’ll run Ollama with a fresh model volume, then verify that three live edits reach the results API before switching to the frontier model.

## Assistant

> The full deterministic gate passed: 416 unit tests, 29 integration checks, 72 Connect cases, and 100% coverage. Ollama is now downloading fresh Qwen2.5 7B weights for the clean-start demo; the fixed-case evaluation will run immediately afterward.

## Assistant

> Ollama passed all nine fixed cases with 14 calls, and the live pipeline is running. I found a cleanup issue: the topic-creation and database-migration helpers create unused anonymous Docker volumes. I’ll reproduce that with a regression test, then change those helpers to use temporary storage.

## Assistant

> The new regression test reproduced the volume leak and now passes with the fix. The 15 launcher/profile checks also pass. I’ve clarified the startup message so it no longer suggests a ten-edit batch when the selected profile uses three. Ollama’s live run is still processing its bounded batch.

## Assistant

> Ollama’s end-to-end run completed: all three live edits reached Postgres and the API, with zero processing or sink errors. One edit received a review assessment; two safely abstained after invalid model output. I’m saving that distinction, resetting only the demo’s data, and moving on to the frontier model.
