# Submission readiness — 22 October 2026

Initial read-only assessment of merged PR #17 (`54e31574266d33723fa4f69ce4feb1ab4e2848cd`), followed by the requested documentation cleanup. No application, profile, model, or container was changed. GitHub confirmed the repository is public and there were no open PRs/issues at the assessment. The merged tree matches the PR's closing tree. Main CI `39840801993` was still running during the initial assessment; its completed lint/dependency steps passed, with no check annotations at that point. The later completed result is recorded below; earlier replies retain their original wording.

## User

PR 17 is merged in

## Assistant — progress

I’ll confirm the merge and check main’s CI status.

## Assistant — response

Confirmed—[PR #17](https://github.com/damogallagher/redpanda/pull/17) is merged. The final evidence and documentation are now on `main`.

[Main’s checks](https://github.com/damogallagher/redpanda/actions/runs/39840801993) are still running. Pre-merge verification passed with **100% coverage and no CI warnings**; remaining upstream image vulnerabilities are documented.

## User

Is ther anything else I need to do bar rhe readme or are we ready to submit this project?

## Assistant — progress

I’ll check the final build, the assignment requirements, and any outstanding work so I can give you a clear submission recommendation.

## Assistant — progress

The assignment’s functional requirements are covered, and there are no open PRs or issues. I found two small documentation inconsistencies: the demo guide has old test counts, and the handover still says separate database roles are missing, although we added them. The final main-branch checks are still running.

## Assistant — response

**Almost ready. I found no missing assignment feature or need for another development phase.** All PRs are merged, and the repository is public.

Before sending the link:

1. **Finish your personal README sections:** Tradeoffs, Surprises and production failure modes, and Why this matters. The assignment explicitly requires your own unaided writing.
2. **Let [main’s final checks](https://github.com/damogallagher/redpanda/actions/runs/39840801993) finish successfully.** They are still running. The verified pre-merge suite passed **453 unit tests, 32 integration checks and 72 Connect cases, with 100% line and branch coverage**.
3. **Make one small documentation/log cleanup:** update the demo guide’s old test counts and correct the handover’s claim that separate database roles are missing. Those roles are implemented. Include this latest conversation in that update.

I also recommend one personal rehearsal using the [demo guide](https://github.com/damogallagher/redpanda/blob/main/docs/submission-demo.md): start the system, explain one successful result, and demonstrate one failure/recovery path. Both models have recorded passing evaluations; those runs predate the final hardening and Ollama image update.

Submit it as a tested local take-home implementation with documented limitations. **Known high/critical upstream image vulnerabilities remain**, so we should not describe it as fully secure or approved for public production deployment.

Once the README, documentation tidy-up and final green check are complete, I would submit rather than add more features.

## User

Go ahead and fix the documentation inconsistencies, update the prompt log, confirm main’s checks pass, and open a PR for me to review. Leave the personal README sections for me.

## Assistant — progress

I’ll correct the documentation, update the prompt log, and verify main’s checks before opening a PR. Your personal README sections will stay untouched.

## Assistant — progress

Main’s checks passed. The downloaded reports confirm 453 unit tests, 32 integration checks, 100% line and branch coverage, and no CI warnings or annotations. I’m updating the current guides while preserving historical results and the frozen study pack.

## Assistant — progress

The documentation corrections are complete. All 248 relative Markdown links resolve, and all 16 demo command blocks pass syntax checks. I also confirmed that the entire README, original assignment, and study pack are unchanged. I’m opening the documentation PR now.

## Verification and review

Main `54e31574266d33723fa4f69ce4feb1ab4e2848cd` passed run `39840801993`. Downloaded JUnit/coverage artifacts verify 453 unit tests, 32 integration checks, 1,172/1,172 lines and 286/286 branches covered without exclusions. Both native Connect suites passed, totaling 72 cases. The full log has zero emitted warning markers; the main check has zero annotations. Evidence hashes are retained in `docs/evidence/security-quality-verification.json`. This is deterministic evidence, not a fresh paid/local model evaluation or vulnerability scan.

Documentation commit `d155419` is in PR #18, created against main and attached to this chat. All PRs #1–#17 are confirmed merged. No merge of PR #18 is performed. The separate PR workflow is running; the closing commit contains review links and this transcript only. README.md, assignment and frozen study-pack bytes remain identical to main. No profile, secret, application file, test, dependency or workflow was changed.

## Assistant — final handover

Opened [PR #18](https://github.com/damogallagher/redpanda/pull/18) for your review.

- Corrected test counts, database-role documentation and outdated checkout instructions.
- Updated the prompt log and saved main’s verification evidence.
- Confirmed **main passed: 453 unit tests, 32 integration checks, 72 Connect cases, 100% coverage, zero CI warnings**.
- Verified documentation links and command syntax. Your entire README remains untouched.

The new PR’s checks are running. I haven’t merged it.

## User

Ensure the demo guide is up to date and 100% accurate

## Assistant — progress

I’ll check every command and expected result in the demo guide against the current code and configuration, then correct any discrepancies and update the PR.

## Assistant — progress

I found a few practical gaps: a fresh clone needs profiles created before cleanup, the free test gate can leave helper resources that need separate cleanup, and the result checks need to distinguish missing rows from duplicate revisions and error routing. I’m correcting those steps and validating the commands with disposable test resources.

## Assistant — progress

The guide now includes fresh-clone setup, isolated test cleanup, and checks that match stored rows to the worker’s committed result keys. I also verified the error-topic command against the pinned Redpanda CLI. The full deterministic suite is running; next I’ll exercise the guide’s API and report commands against controlled data.

## Assistant — progress

The full local gate passed, and PR #18’s existing checks are green. Coverage remains 100% for all 1,172 application lines and 286 branches. I’m now checking the exact API/report commands and the demonstration targets, including the intentionally failing test.

## Assistant — progress

The API commands worked against the fixture pipeline. They also exposed a useful timing detail: rows can be visible before the sink’s Kafka lag reaches zero. The guide now tells you to wait for both conditions. Empty and populated error-topic reads behaved as documented, and I’m finishing the success/failure demonstrations.

## Assistant — progress

The success demo passed, and the API inspection reached zero sink lag after the documented wait. Fresh-profile setup also passed: it creates private files and preserves them when repeated. The remaining checks are the fault/recovery demo, the expected red test, and confirmation that all pre-existing Docker volumes are retained.

## Assistant — progress

All checks are complete: the success demo passed, all 19 fault/recovery checks passed, and the intentional test failed exactly as documented. The subsequent unit run passed with 100% coverage. All 24 pre-existing Docker volumes were preserved, with no containers left behind. I’m saving the evidence and updating PR #18.

## Demo audit verification

Source/test/configuration tree: `f792301`, identical to main `54e3157`. The full local gate passed 453 unit / 32 integration / 72 Connect cases, all 1,172 lines and 286 branches covered without exclusions. The exact success target passed one scenario; the fault/recovery target passed 19. The intentionally wrong test failed once with Make exit 2; the following unit run passed all 453 cases at 100% coverage.

Step 6's three literal shell blocks were run against controlled data in an isolated project. Readiness/list/detail output and empty error snapshots matched the guide; two inspections reached zero sink lag. A populated synthetic processing-error topic was consumed to its current end. Fresh-profile setup created mode-0600 files, preserved existing files on repeat, and both Compose profiles resolved to the documented settings. All 18 demo shell blocks passed syntax checks and all 255 relative Markdown file targets resolved. All 24 pre-existing volumes were retained, with zero containers before and after.

The first scratch inspection harness failed because Docker exec consumed commands supplied on stdin; the corrected harness ran a script file, and the guide now detaches stdin for read-only inspection commands. The initial failure log and subsequent passing evidence remain in ignored reports. The audit made no real model calls, live Wikipedia requests or new vulnerability scans. Current model results are explicitly distinguished from the earlier saved evaluations. Evidence and hashes: `docs/evidence/demo-guide-verification.json`.

## Assistant — final handover

Updated [PR #18](https://github.com/damogallagher/redpanda/pull/18) with the audited demo guide and prompt log.

- Fixed fresh-clone setup, test cleanup, result counts, error checks and sink-lag timing.
- Executed the API commands, success/recovery demos and intentional failure.
- Full suite passed with **100% line and branch coverage**; existing Docker data was preserved.

Your README is untouched. Live-model outcomes are clearly marked as variable; this audit made no new model calls. The updated PR’s CI will run separately.
