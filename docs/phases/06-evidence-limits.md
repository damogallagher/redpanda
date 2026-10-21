# Evidence-count follow-up

Requested 21 October 2026 after the solution-gap review. Branch `fix/evidence-count-limits` starts from merged main `447920f`. PR #13 (executed-demo cleanup) and PR #14 (frozen study pack) remain separate reviews; this change does not merge them or duplicate their changes.

## Problem and behavior

Previously enrichment accepted a complete nine-to-20-hunk edit, but extraction allowed at most eight changes and required every hunk to be represented. No model response could satisfy both rules. The worker spent two calls and reported `invalid_output` even when the limitation was knowable before inference.

`MAX_REASONING_HUNKS = 8` in `src/triage/schema.py` now supplies the new-diff cap, extraction capacity and defensive reasoning check. The existing four-call, token, quote-length, source-text, response-byte and time budgets remain in force. Eight is a processing capacity, not a claim that every eight-hunk edit will produce a correct model judgment.

| Input / response | Expected result |
|---|---|
| No textual change | `no_text_change` enrichment; `no_change` outcome; insufficient evidence; zero calls |
| One through eight complete hunks within other limits | Normal extraction and assessment; all hunks must be covered; normally two calls |
| Nine or more source hunks | Retain at most eight whole diagnostic hunks, set `evidence_limit` and `content_truncated: true`; `incomplete_source` outcome, insufficient evidence, confidence 0, attempts 0, no extraction/steps or model calls |
| Historical `ready` input with nine to 20 hunks passed to reasoning | Apply the same limit before inference without mutating the original input; retain event/provenance; zero calls |
| Model omits a hunk, duplicates one in place of another, references an absent hunk, or exceeds extraction capacity | Reject output, allow the bounded repair; assess only a complete valid repair; repeated invalid output abstains after two extraction calls |
| A previously stored v1 result with 20 source hunks | Remains accepted by Connect and readable through the API unchanged |

The service never classifies the retained prefix of an oversized edit. Omitted content is explicit in the result; these are handled capacity outcomes, not successful semantic assessments. Very large edits would require separately designed bounded processing and evaluation. This fix does not increase capacity or introduce additional inference spending.

## Compatibility and deployment

The v1 schemas intentionally retain their historical 20-hunk read bound. Tightening that wire limit would break stored results and replay. Only new processing is capped at eight; the reasoning entry check also handles historical or separately supplied valid v1 evidence. Exported schemas, database migration/version, result keys, prompts and dependency pins are unchanged. No data reset is required. Rebuild/restart the application with the existing selected-profile launcher when deploying this change; startup resumes the existing consumer offsets. Historical stored outputs are not automatically reanalysed.

The study pack in PR #14 is explicitly pinned to an earlier snapshot. This follow-up records the corrected behavior; its historical observations should not be overwritten as if the fix existed during earlier demos.

## Verify this change

From this review branch, with Docker running:

```sh
make test-evidence-limits
```

Expected: **23 passed** (22 unit cases and one integration scenario), exit 0. The integration scenario prints:

```json
{"evidence_boundaries": "passed", "rows": 5, "real_model_calls": 0}
```

It processes four edits through the real Kafka worker and Connect/Postgres/API path: eight hunks receive a controlled two-step review; nine, 20 and 21 hunks make no model calls and persist explicit abstentions. The worker commits all four inputs. A fifth historical 20-hunk record is published and served unchanged. The sink commits five records; processing/sink error topics remain empty. Wikipedia/model HTTP responses are deterministic doubles. Test resources use a unique disposable project and are removed afterward.

For the fast, Docker-free checks after dependencies are installed:

```sh
uv run --frozen pytest tests/test_evidence_limits.py -q
```

Expected: **22 passed**. Both Ollama and OpenAI adapter paths are tested with HTTP doubles; no key or live provider is required. The tests also verify zero-change behavior, the exact eight-hunk boundary, oversized historical inputs, and malformed model counts followed by a valid or invalid repair.

Run the complete cumulative acceptance and coverage gate:

```sh
make test
```

Use `UV='uvx --from uv==0.13.4 uv'` with either Make command if the global uv version differs. Expected on this branch: 438 unit tests, 30 integration/configuration tests, 72 native Connect cases, 100% application line and branch coverage without exclusions. PR #13 independently adds another integration case; counts will increase once both changes are merged.

Reports: `reports/evidence-limits.xml`, `reports/evidence-limits-delivery.json`, `reports/unit.xml`, `reports/integration.xml`, and `reports/coverage.json`. Normal CI discovers both new test files automatically. A test assertion failure returns nonzero; do not treat an abstention itself as a test failure when it is the declared expected outcome.

## Verification record

Before changing the application, the new unit file produced **8 failures / 14 passes** on main `447920f`: oversized processing tried to call the model, retained too many hunks, or bypassed the required early guard. After the fix, the focused enrichment/reasoning suite passed 187 cases, and the new 23-case boundary/delivery command passed, including the five API rows and committed offsets. Docker Desktop was initially stopped; starting it enabled the integration run. No live source/model request was made.

Final cumulative coverage and CI evidence will be recorded after their runs complete.
