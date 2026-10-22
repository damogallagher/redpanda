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
