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

## User

Check PR #18’s latest CI run and confirm everything passes with 100% coverage and no warnings before I merge it.

## Assistant — progress

I’ll check PR #18’s latest commit, download its test reports, and inspect the CI logs and warning annotations before confirming it’s ready to merge.

## Latest-commit CI verification

Run `39845228516` passed on PR #18 head `4eb60676e149b2f77e1f3b16267c100982ce7336`. Downloaded artifacts verify 453 unit tests, 32 integration checks, both native Connect suites (72 cases), 1,172/1,172 lines and 286/286 branches covered, zero failures/errors/skips and no coverage exclusions. All job steps and GitGuardian checks passed. Bandit reports no findings; the dependency audit found no advisories or skipped packages among 63 dependencies.

The full CI log contains no emitted warning markers or reported warning lines, and both checks have zero annotations. A literal-word search also matched tar's `--warning=no-unknown-keyword` command argument; inspection confirms this is a command flag, not a warning emitted by the tool. Raw downloaded evidence and a verification summary are retained under ignored `reports/ci-pr18-4eb6067*` paths. A final read confirmed the verified SHA is still the PR head, open and mergeable.

This verification-only exchange is appended locally for the next documentation update. No new commit is pushed, so the commit being recommended for merge remains the one whose completed CI was inspected.

## Assistant — response

**Yes—[PR #18](https://github.com/damogallagher/redpanda/pull/18) is ready for you to merge.** Its [latest CI run](https://github.com/damogallagher/redpanda/actions/runs/39845228516) passed on the current commit, `4eb6067`.

- **453 unit tests, 32 integration checks, 72 Connect cases passed.**
- **100% line and branch coverage:** 1,172 lines and 286 branches; no exclusions.
- **Zero CI warnings or check annotations.**
- All workflow steps and GitGuardian checks passed; no test failures or skips.

I verified the downloaded reports and full logs. The PR is mergeable.

## User

I've merged PR #18. Check main’s final CI run and confirm we’re ready to submit once I finish my personal README sections.

## Assistant — progress

I’ll confirm PR #18’s merge, check main’s final CI reports and warnings, and verify that only your personal README sections remain before submission.

## Assistant — progress

GitHub still reports PR #18 as open, with its checks passing. I’ll give the merge status a moment to update and check again; the current main run predates PR #18.

## Verification

GitHub GraphQL and REST both reported PR #18 open; REST returned `merged: false`, `merged_at: null`, and no auto-merge configuration. A further read after a 15-second delay returned the same result. Main remained `54e31574266d33723fa4f69ce4feb1ab4e2848cd`, with successful run `39840801993`, which predates PR #18. PR head `4eb6067` still had successful foundation and GitGuardian checks with zero annotations. No open issues were returned. The personal README sections remain reserved. No merge, commit or push was performed; this verification-only exchange remains a local transcript addition for the next documentation update.

## Assistant — response

GitHub still shows [PR #18](https://github.com/damogallagher/redpanda/pull/18) as **open, not merged**, even after rechecking. Please check whether the final merge confirmation completed.

Its latest checks passed with **100% line and branch coverage and zero warnings**. Main is also green, but that run predates PR #18, so I can’t confirm a post-merge run yet.

Once PR #18 is merged, its main checks pass, and you finish **Tradeoffs**, **Surprises and production failure modes**, and **Why this matters**, I consider the take-home ready to submit. No further feature work is needed.

## User

PR #18 is merged now. Recheck main’s latest CI for 100% coverage and no warnings, and confirm we’re ready to submit once I finish my personal README sections.

## Assistant — progress

I’ll recheck the merge and main’s latest CI, including the coverage reports and warnings, then confirm what remains before submission.

## Assistant — progress

The API still reports PR #18 as open. I’m checking the remote branch directly and making a fresh API request to see whether that status is stale.

## Assistant — clarification request

GitHub’s API and a direct Git check both still show PR #18 open, with main at 54e3157. Can you share the merged PR URL or the new main CI run URL that you’re seeing?

## Assistant — progress

The current main run is verified: 453 unit tests, 32 integration checks, 72 Connect cases, 100% line and branch coverage, and zero warnings or annotations. The remaining check is whether GitHub has published a new main commit and run for PR #18.

## Verification

Fresh GitHub requests with cache-control and a unique query parameter still reported PR #18 open, `merged: false`, with no merged timestamp. Direct `git ls-remote` independently returned main `54e3157` and documentation branch `4eb6067`. A later recheck returned the same PR state and main run. The REST `merge_commit_sha` field is not evidence of a completed merge while `merged` remains false.

Run `39840801993` remains GitHub's latest main run. Artifacts and its full log were downloaded again to ignored `reports/ci-main-recheck-54e3157*`. They confirm 453 unit / 32 integration / 72 Connect cases; 1,172/1,172 lines and 286/286 branches; zero failures/errors/skips/exclusions, zero reported warnings and zero check annotations. No new main run for PR #18 was visible. No reply to the clarification request arrived before this handover. No merge, commit or push was performed; this exchange remains a local transcript addition for the next documentation update.

## Assistant — response

The [latest visible main CI run](https://github.com/damogallagher/redpanda/actions/runs/39840801993) passes: **453 unit tests, 32 integration checks, 72 Connect cases, 100% line/branch coverage, and zero warnings or annotations**.

However, both GitHub and a direct remote-branch check still show [PR #18](https://github.com/damogallagher/redpanda/pull/18) as **open**, with main at `54e3157`. There is no post-merge run available for me to confirm.

Please send the merged PR or new CI-run link you’re seeing. Once that merge’s checks pass and your three personal README sections are finished, the take-home is ready to submit—no further feature work is needed.

## User — clarification answer

[https://github.com/damogallagher/redpanda/pull/18](https://github.com/damogallagher/redpanda/pull/18)

## Assistant — progress

Thanks—that’s the same PR I’ve been checking. I’ll refresh its status and check for a new main CI run.

## Assistant — progress

PR #18 is now confirmed merged. The new main CI run is still running; the lint checks and dependency audit have passed. I’ll wait for completion, then inspect the coverage reports and warning output before confirming readiness.

## Assistant — progress

The run is testing the merged main commit, `23c63d5`, and there are no remaining open PRs. Acceptance tests are still in progress. The README’s three personal sections remain reserved for you.

## Assistant — progress

The final acceptance step is still running. I’ll verify the downloaded reports as well as the green status, so the coverage and “no warnings” confirmation comes from this main run’s actual output.

## Assistant — progress

Main’s CI has passed. I’m downloading the test reports and full log now to verify the exact coverage figures and check for warnings.

## Final main verification — PR #18 merged

GitHub confirms PR #18 merged at `2026-10-22T20:34:22Z`, with main at `23c63d524d29ae523b262a34ad4e3848fdfb0be4`. The new main run `39850025900` completed successfully. A final remote read confirmed it is still the latest main commit and run, and no open PRs remain.

Downloaded artifacts verify 453 unit tests, 32 integration checks, zero failures/errors/skips, and 100% application line and branch coverage: 1,172/1,172 lines and 286/286 branches, with no exclusions. Both Connect suites passed; the exact main test-file hashes match the locally counted 40 ingestion and 32 sink cases. Every workflow step and the main foundation check passed. The full log has zero emitted warning markers or reported warning lines; the main check has zero annotations. The single literal warning-word match is tar's command argument, not an emitted warning. Bandit has zero findings/errors; all 63 audited Python dependencies have zero advisories and no skipped entries.

Evidence, full logs, run/check metadata, artifact hashes and the machine-readable summary are saved locally under ignored `reports/ci-main-final-23c63d5*`. The verification commands were `gh run view 39850025900 --repo damogallagher/redpanda --json status,conclusion,headSha,url,jobs`, `gh run download 39850025900 --repo damogallagher/redpanda --dir reports/ci-main-final-23c63d5`, `gh run view 39850025900 --repo damogallagher/redpanda --log`, and the GitHub commit check-runs API, followed by explicit assertions over JUnit, coverage, audit JSON and log output. These are deterministic CI results; no new real-model evaluation, live-feed run or image vulnerability scan was performed. Submission readiness retains the existing documented deployment limits.

This verification-only exchange is appended locally for the next documentation update. No new commit or push was made; personal README sections remain untouched. Damien still needs to complete and commit his independent write-up and let that final commit's CI pass.

## Assistant — response

**Confirmed: PR #18 is merged, and main’s [final CI run](https://github.com/damogallagher/redpanda/actions/runs/39850025900) passed on `23c63d5`.**

- **453 unit tests, 32 integration checks and 72 Connect cases passed.**
- **100% line and branch coverage:** 1,172 lines and 286 branches, with no exclusions.
- **Zero CI warnings or check annotations.**
- Every workflow step passed; no test failures or skips.

The take-home is ready to submit once you finish your own **Tradeoffs**, **Surprises and production failure modes**, and **Why this matters** sections. Commit those changes and let their CI pass before sharing the repository.

No further feature work is needed. Verification evidence and this exchange are saved locally; your README remains untouched.

## User

Can you give me a simple checklist for completing my personal README sections and submitting the project, without writing those sections for me?

## Assistant — progress

I’ll keep this to a checklist and leave all personal wording to you. I’ll also add this exchange to the local prompt log.

## Assistant — response

- [ ] **Tradeoffs:** Choose two pairs from the assignment. Write one paragraph per pair covering your choice, the alternative, and when you would switch. Aim for half a page to one page total; cite anything that influenced you.
- [ ] **Surprises and production failure modes:** Write a short paragraph about what surprised you and where the system would break in production, based on your own observations.
- [ ] **Why this matters:** Write 3–4 sentences for a non-technical customer: who uses it, what decision it supports, and the cost of wrong or missing results. Explain the real use case your demo represents.
- [ ] **Finish the README:** Remove the reserved-section placeholders and the notice saying your personal sections are unfinished. Read everything back in your own words.
- [ ] **Check accuracy:** Keep your claims consistent with the saved evidence and documented limitations. Review the demo guide and make sure you can explain the flow and failure handling.
- [ ] **Commit and publish:** Review and commit your README changes and pending prompt-log updates. Push them, and merge the PR if working on a branch.
- [ ] **Check final main CI:** Confirm the resulting main commit passes with **100% line and branch coverage and zero warnings**.
- [ ] **Submit:** Confirm reviewers can access [the repository](https://github.com/damogallagher/redpanda), then send its link through the requested submission channel. Include the final commit hash so they know exactly what you submitted.

Your personal sections remain entirely yours to write; no additional feature work is needed.

## User

CAn you help give me points for my personal readme section? Help me write it

## Assistant — progress

I can help you identify points from the project. One caution: the assignment explicitly asks for these sections without AI help, so AI-written arguments or paragraphs could hurt your submission. I’ll pull together factual reminders and questions you can use to work out your own views.

## Assistant — response

Yes—here are **factual reminders and questions to help you find your own points**. The [assignment](/Users/damien/Documents/ChatGPT/Redpanda/repo/docs/assignment/fde-take-home-exercise.md:96) asks for these sections without AI help, so your conclusions and wording should come from you.

For **Tradeoffs**, these two decisions have clear implementation evidence:

| Decision to examine | What we built | Questions to answer yourself |
|---|---|---|
| Multi-step reasoning versus one classification call | Extraction of changes with exact quotes, assessment, and optional review or repair; a shared limit of four calls per edit. | What did inspecting the separate steps teach you? What extra complexity, latency or cost did you observe? What evidence would make you choose a single call? |
| Connect as the sink versus database writes in Python | Python publishes results to Kafka. Connect validates and upserts them into Postgres. Replayed results retain one logical database row. | Which responsibilities did this separation make easier or harder to understand? What was awkward about maintaining the Connect configuration? Under what requirements would you move writes into Python? |

Use the [reasoning record](/Users/damien/Documents/ChatGPT/Redpanda/repo/docs/phases/04-reasoning.md) and [persistence record](/Users/damien/Documents/ChatGPT/Redpanda/repo/docs/phases/05-serving.md) to check details. Choose these pairs only if you feel comfortable defending them.

For **Surprises and production failure modes**, revisit these actual observations:

- **Passing fixed model cases did not guarantee success on live edits.** Ollama passed nine fixed cases, then abstained on two of three live edits after invalid extraction output. See the [executed demo](/Users/damien/Documents/ChatGPT/Redpanda/repo/docs/evaluations/submission-demo.md).
- **Two individually valid limits conflicted.** Enrichment previously accepted up to 20 change blocks, while extraction could represent only eight. The [fix](/Users/damien/Documents/ChatGPT/Redpanda/repo/docs/phases/06-evidence-limits.md) detects oversized evidence before spending model calls.
- **Production limits remain explicit.** A sequential worker can fall behind ingestion; the upstream stream can lose events across reconnects; public deployment needs additional security and operational controls. See the [handover](/Users/damien/Documents/ChatGPT/Redpanda/repo/docs/handover.md).

Which observation actually surprised you? What assumption did it change? Which failure would you address first, and why?

For **Why this matters**, answer these four questions in plain language:

1. Who specifically would use the results?
2. What decision or action would they take?
3. What would a false alarm, missed issue or unavailable result cost them?
4. Is Wikipedia the intended use case, or does it represent another customer workflow?

Write rough answers first, then select the points you can explain confidently. Avoid claiming that 100% code coverage proves model accuracy or complete production readiness.

## Scope of this exchange

Read the original write-up requirements and existing implementation/evaluation records. Provided factual reminders and reflection questions; did not edit README.md, supply first-person submission paragraphs, change application code, rerun tests, or push a commit. This exchange is retained locally with the other pending transcript updates.

## User

Send an email to damien.gallagher@gmail.com with keypoints I should add to any section that I need to update

## Assistant — progress

I’ll email you a concise checklist for each README section, with factual reminders and links to the project evidence. I’ll keep the personal judgments and wording for you to write.

## Sent email

Recipient: damien.gallagher@gmail.com

Subject: Redpanda submission — README sections to finish and final checklist

Exact HTML body sent through Gmail, under the user's explicit authorization:

```html
<html><body>
<p>Hi Damien,</p>
<p>Here are the remaining README updates and project facts to revisit. The <a href="https://github.com/damogallagher/redpanda/blob/23c63d524d29ae523b262a34ad4e3848fdfb0be4/docs/assignment/fde-take-home-exercise.md#required-write-up-about-30-minutes">assignment</a> asks you to write the personal sections independently, so use these as reference notes and questions for your own judgment.</p>

<p><strong>1. Tradeoffs — half a page to one page</strong></p>
<p>Choose two pairs from the assignment. For each, explain your choice, the alternative, and when you would switch. Cite anything that influenced your thinking. Two implemented decisions to examine:</p>
<ul>
<li><strong>Multi-step reasoning versus one classification call:</strong> the worker extracts changes with exact source quotes, assesses them, and optionally reviews or repairs the output. All steps share a maximum of four model calls per edit. What did the separate steps help you inspect? What complexity, latency or cost did you observe? What evidence would justify a single call? <a href="https://github.com/damogallagher/redpanda/blob/23c63d524d29ae523b262a34ad4e3848fdfb0be4/docs/phases/04-reasoning.md">Reasoning record</a>.</li>
<li><strong>Connect sink versus Python database writes:</strong> Python publishes results to Kafka; Connect validates and upserts them into Postgres; the read-only API serves stored results. Replays retain one logical SQL row, although inference can run again. What did this separation make easier or harder for you? Under what requirements would you move database writes into Python? <a href="https://github.com/damogallagher/redpanda/blob/23c63d524d29ae523b262a34ad4e3848fdfb0be4/docs/phases/05-serving.md">Persistence record</a>.</li>
</ul>

<p><strong>2. Surprises and production failure modes — a short paragraph</strong></p>
<p>Pick observations that actually changed your understanding. Recorded examples:</p>
<ul>
<li>Ollama passed nine fixed evaluation cases, then abstained on two of three live edits after invalid extraction output. Those historical results distinguish controlled evaluation from live behavior; they do not establish general accuracy. <a href="https://github.com/damogallagher/redpanda/blob/23c63d524d29ae523b262a34ad4e3848fdfb0be4/docs/evaluations/submission-demo.md">Executed demo</a>.</li>
<li>Enrichment previously accepted up to 20 change blocks while extraction could represent only eight. Oversized inputs could never satisfy both requirements. The fix detects this before inference and records an explicit abstention with zero model calls. <a href="https://github.com/damogallagher/redpanda/blob/23c63d524d29ae523b262a34ad4e3848fdfb0be4/docs/phases/06-evidence-limits.md">Boundary fix and regression evidence</a>.</li>
<li>Production limits include a sequential worker that can fall behind ingestion, possible upstream feed gaps across reconnects, and additional authentication, TLS, backup/restore and availability work before public deployment. Choose the failure you would address first and explain your reasoning. <a href="https://github.com/damogallagher/redpanda/blob/23c63d524d29ae523b262a34ad4e3848fdfb0be4/docs/handover.md#deployment-limits-and-next-operational-decisions">Deployment limits</a>.</li>
</ul>

<p><strong>3. Why this matters — 3–4 sentences for a non-technical customer</strong></p>
<ul>
<li>Who specifically would use the results?</li>
<li>What decision or action would they take?</li>
<li>What would a false alarm, missed issue or unavailable result cost them?</li>
<li>Is Wikipedia the intended use case, or does it represent another customer workflow?</li>
</ul>
<p>The current system suggests edits for human review; it does not automatically change Wikipedia or establish factual truth.</p>

<p><strong>4. Final README cleanup and accuracy</strong></p>
<ul>
<li>Replace all three reserved-section placeholders and remove the earlier notice saying your personal sections are unfinished.</li>
<li>Keep claims tied to recorded evidence: 100% code coverage does not mean perfect model judgments, exactly-once inference or complete production readiness.</li>
<li>Local/frontier context: Ollama uses local model resources; the hosted OpenAI path requires a key and billing. Selection is explicit, with no automatic provider fallback. Model performance depends on hardware, model and input.</li>
<li>Review the <a href="https://github.com/damogallagher/redpanda/blob/23c63d524d29ae523b262a34ad4e3848fdfb0be4/docs/submission-demo.md">current demo guide</a> and practise explaining one successful edit and one failure/recovery path.</li>
</ul>

<p><strong>5. Publish and submit</strong></p>
<ul>
<li>Review and commit your README changes and the pending local prompt-log updates, push them, and merge their PR if using a branch.</li>
<li>Check CI on the final main commit. The last verified run on 22 October 2026, commit <code>23c63d5</code>, passed 453 unit tests, 32 integration checks and 72 Connect cases, with 100% application line/branch coverage and zero CI warnings or annotations. <a href="https://github.com/damogallagher/redpanda/actions/runs/39850025900">Verified run</a>. Your README commit will need its own passing run.</li>
<li>Confirm reviewer access, then submit <a href="https://github.com/damogallagher/redpanda">the repository link</a> with the final commit hash through the requested submission channel.</li>
</ul>
<p>No further feature work is required for the take-home scope.</p>
<p>Codex</p>
</body></html>
```

Gmail confirmed successful sending with the SENT label. No README, application, test, CI or other mailbox content was changed. This exchange and the sent content remain in the local prompt log pending the next documentation commit.

## Assistant — response

Sent to **damien.gallagher@gmail.com** with section-by-section points, links to the project evidence, and the final submission checklist.
