# 21 October 2026 — Evidence-count fix

Scope: requested correctness fix, regression tests, documentation, coverage and review PR. Based on merged main `447920f`; other open PRs remain separate. No real model calls are required for this count/compatibility fix. The previous gap review is recorded in PR #14.

## User

Go ahead and fix the evidence-size mismatch. Keep it simple, add regression tests, maintain 100% coverage, update the docs and prompt log, and open a PR for me to review. Make sure any changes we make from here on in are production ready. If we have count mismatches, make sure our processing can handle it. Make this production ready

## Assistant — progress

I’ll align the evidence limits, add regression tests for larger edits, and verify that unsupported input is handled explicitly before any model calls. I’ll run the full checks, update the docs and prompt log, and open a separate PR for your review.

## Assistant — progress

I’m keeping the existing eight-section reasoning budget and applying it consistently. Larger edits will return an explicit “insufficient evidence” result with zero model calls; the system won’t classify a partial edit. Historical results containing up to 20 sections will remain readable, and I’ll test that compatibility through storage and the API.

## Assistant — progress

The new regressions failed on the original code and now pass with the fix. They cover the eight-section boundary, oversized edits, historical inputs, and model responses with missing, duplicate or extra sections.

I’m now checking that these results travel correctly through the real broker, Connect, Postgres and API, including older 20-section records.

## Assistant — progress

The broker-to-API check passed: the eight-section edit was assessed, the nine-, 20- and 21-section edits were stored as explicit abstentions with zero model calls, and an older 20-section result remained readable unchanged.

The fix preserves the existing schema and inference budgets. I’m running the full acceptance and coverage checks now.

## Assistant — progress

All 438 unit tests passed with 100% line and branch coverage, with no exclusions. The full suite is now working through the broker and database recovery checks. The docs include a single command, `make test-evidence-limits`, to verify the count handling and compatibility behavior.

## Assistant — progress

[PR #15](https://github.com/damogallagher/redpanda/pull/15) is open for review. The local suite has passed the recovery checks and the new compatibility scenario so far; GitHub CI is also running. I’ll record the final results in the PR before handing it over.

## Assistant — progress

The full local acceptance suite passed: 438 unit tests, 30 integration checks and 72 Connect tests, with 100% line and branch coverage. Test resources were cleaned up, and the pre-existing Docker volume list is unchanged.

I’m waiting for GitHub CI to finish so I can include its result in the handover.

## Assistant — progress

The code, regression tests and local verification are complete. GitHub’s acceptance run is the only remaining check before I finish the PR evidence and handover.

## Assistant — progress

The local results are recorded in the follow-up guide. GitHub is still running the acceptance job; I’ll leave the PR unmerged for your review once that result is confirmed.

## Assistant — progress

GitHub CI passed too. I’m checking its downloaded reports against the local results, then saving the final verification record and prompt log to PR #15.

## Assistant — final

Implemented in [PR #15](https://github.com/damogallagher/redpanda/pull/15), ready for your review.

- Enrichment and reasoning now share an **eight-section limit**. Larger edits return explicit insufficient evidence with **zero model calls**; partial edits are never classified.
- Missing, duplicate or excess model-output sections must be repaired within the existing retry budget, or the system abstains.
- Historical 20-section records remain readable through Connect, Postgres and the API.

**Verified:** 438 unit tests, 30 integration checks, 72 Connect cases, and **100% line and branch coverage**, without exclusions. [GitHub CI passed](https://github.com/damogallagher/redpanda/actions/runs/39686956340), with no emitted warnings.

Docs, test evidence and the prompt log are included. To verify:

```sh
gh pr checkout 15
make test-evidence-limits
make test
```

The focused check should report **23 passed**. No real model calls or API key are needed. PR remains unmerged.
