# Executed submission demo — 20 October 2026

Started as a follow-up on PR #12, which merged during execution. The new fix/evidence review is PR #13. The user explicitly authorizes real Ollama/frontier execution and issue fixes. Provider credentials are never logged.

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

## Assistant

> The frontier model also passed all nine fixed cases with 14 calls. Its three-edit live batch is now running. PR #12 was merged during execution, so I’ll put the demo evidence and cleanup fix into a new PR based on the updated main branch.

## Assistant

> The frontier demo also delivered all three rows with zero errors: one review, one routine assessment, and one abstention because source evidence was incomplete. It used 18 paid calls in total, below the 40-call cap. I’m now checking that saved results survive shutdown, then running the final verification and failure demonstrations.

## Assistant

> The saved frontier results survived a full stop and a storage-only restart without extra model calls. The cleanup checks also passed: all demo resources are gone, the pre-existing volume set is unchanged, and the private profiles are preserved. The success demonstration has passed; the fault demonstrations and final test gate are underway.

## Assistant

> The fault demonstrations passed, and the deliberately failing test failed exactly as intended. PR #13 is open as a draft while the final local and GitHub checks finish. I’m updating the walkthrough with the observed results, including the local model’s two abstentions, and saving the full reports in your checkout.

## Assistant

> The final unit run still has 100% line and branch coverage, and the new Docker cleanup regression passes. The remaining checks cover delivery and recovery against real services. The original assignment and your personal README sections are unchanged.

## Assistant

> The complete local gate passed: 416 unit tests, 30 integration checks, 72 Connect cases, and 100% line and branch coverage, with no warnings. Both real-model demos and the cleanup checks are complete. I’m checking the GitHub run’s artifacts before marking PR #13 ready for review.

## Assistant

> GitHub CI passed too; its downloaded artifacts confirm the test counts and 100% coverage, with zero warnings or annotations. I’ve saved 80 private evidence files in your checkout and added sanitized results to the PR. I’m finishing the documentation and prompt log, then marking PR #13 ready for your review.

## Assistant — final

Completed. [PR #13 is ready for review](https://github.com/damogallagher/redpanda/pull/13).

| Demo | Fixed cases | Live results saved |
|---|---|---|
| Ollama | 9/9 passed | 1 assessment, 2 safe abstentions |
| Frontier | 9/9 passed | 2 assessments, 1 safe abstention |

Fixed the Docker helper volume leak and clarified the startup message. Local checks and Linux CI passed: **416 unit tests, 30 integration checks, 72 Connect cases, 100% line and branch coverage**, with zero warnings. Success, failure/recovery, persistence and cleanup demonstrations behaved as expected.

[Results and reproduction steps](https://github.com/damogallagher/redpanda/blob/fix/submission-demo/docs/evaluations/submission-demo.md) and the prompt log are updated. Full private reports are saved in your checkout under `reports/submission-demo-20261020/`.

Used **18 hosted calls**. Your existing data, model weights and private profiles were preserved. PR remains unmerged.
