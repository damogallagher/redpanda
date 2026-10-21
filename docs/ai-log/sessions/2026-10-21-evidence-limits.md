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
