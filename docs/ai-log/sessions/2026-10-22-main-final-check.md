# Main verification and submission packaging advice — 22 October 2026

Record of the read-only main check; included in the subsequent final documentation review. No application, README or study-pack edits, submission ZIP, new commit or PR were part of that check. Its replies describe the state at the time. This session records only the new request and visible replies; it does not recreate previously omitted personal-writing exchanges.

Checked main: `7a3410842e5a9f12813a93d32366c564a8f1dda9`. CI: https://github.com/damogallagher/redpanda/actions/runs/39864138316. Downloaded reports and verification summary are retained locally under ignored `reports/ci-main-walkthrough-7a34108*` paths.

## User

I've merged PR #20. Check main’s latest CI for 100% coverage and no warnings, and confirm the updated walkthrough pack is ready to use. Also, I will be sending a zip file of this repo, is there any documentation I should not send like study guides or what aboiut all my prompts? DO I give away any hints that I did not write the piecs in the README.md myself?

## Assistant — progress

I’ll check the latest main commit and its CI reports, then verify the walkthrough pack on that commit. I’ll also review the assignment’s submission instructions and distinguish what belongs in the ZIP from preparation material, including how the README assistance is recorded.

## Assistant — progress

PR #20 is merged, and main’s new CI run is still running. I’ll wait for its results before confirming coverage and warnings.

The assignment allows AI for the build, but explicitly requires the personal write-up to be written without AI. Your README draft received AI assistance, and the repository records reflect that. Making the prose sound natural or omitting those records would not change its authorship.

## Assistant — progress

The merged walkthrough files exactly match the PDF and interactive pack already checked in PR #20, including the oversized-edit failure trace. They’re ready for study and rehearsal; the saved model results are historical, so a fresh live rehearsal is still worth doing before the screen-share.

For the ZIP, the assignment does not require study guides or development chat logs. They’re optional supporting material. Runtime prompts, tests and evaluation fixtures belong with the application. I’m also checking what a clean Git archive would include so private environment files stay out.

## Assistant — progress

The archive check passed: a ZIP of the tracked commit includes the example environment templates and excludes real `.env` profiles, local reports, virtual environments and Git metadata. Keeping the tracked documentation together is the simplest option because its links already work.

Main’s CI is still completing the integration checks. The setup, lint and dependency-audit steps have passed; final coverage and warning confirmation must wait for the completed reports.

## Assistant — final

Main’s latest CI **passed** on commit `7a34108` after PR #20 merged. I checked the downloaded reports and complete job log:

- **453 unit tests, 32 integration checks and 72 Connect cases passed.**
- **100% application line and branch coverage**, without exclusions.
- **Zero emitted warnings and zero check annotations.**

[Verified main CI run](https://github.com/damogallagher/redpanda/actions/runs/39864138316).

The [updated walkthrough pack](https://github.com/damogallagher/redpanda/tree/7a3410842e5a9f12813a93d32366c564a8f1dda9/docs/study-guide) is ready for study and rehearsal. Its merged files exactly match the verified PDF and interactive materials. Pull current main before rehearsing; the saved model results remain historical, so run your chosen model again before presenting.

For the ZIP, I recommend a clean archive of the final tracked commit:

| Material | Recommendation |
|---|---|
| Code, Compose files, configuration templates, dependencies, tests and fixtures | Include |
| README, run/demo instructions, phase records and sanitized evaluation evidence | Include |
| Study guides and presentation material | Optional preparation material; keeping them preserves existing links |
| Development conversation logs | Not required by the assignment; optional supporting evidence of the AI-assisted build |
| Real `.env` profiles, keys, private reports, caches and virtual environments | Exclude |

Runtime prompt templates and curated model-evaluation transcripts are different from development chats: keep them with the implementation and tests. I inspected a tracked-file archive: it includes only the three example environment profiles, with no real profiles, local reports or virtual environment.

**On the README: yes, the project records show assistance with those sections.** I helped draft and polish them; [PR #19](https://github.com/damogallagher/redpanda/pull/19) records the drafting work, and the handover calls them drafts. They cannot honestly be described as independently written just because they sound natural.

The [assignment explicitly requires the personal write-up without AI assistance](https://github.com/damogallagher/redpanda/blob/7a3410842e5a9f12813a93d32366c564a8f1dda9/docs/assignment/fde-take-home-exercise.md#required-write-up-about-30-minutes). Before submitting, write those three personal sections yourself from your understanding, without AI drafting or polishing—or ask the reviewer how to handle the assistance already received. Omitting logs would not resolve that requirement.

This check’s verification evidence and conversation record are saved locally; no new commit or PR was created.

