# Phase 3: Wikipedia revision enrichment

Status: implemented and verified locally; PR review and GitHub CI are pending.
Branch: `phase/03-enrichment`, based on merged PR #6 (`9749745`). Damien reviews and merges.

## What this phase adds

A validated edit event now produces inspectable before/after evidence, or a specific failure outcome. The CLI and reusable Python client use the same extraction path. This is the evidence boundary for Phase 4; no Kafka consumer, model reasoning, or result publication has been added yet. The existing local/frontier launchers continue to start the Phase 2 services.

- `src/triage/enrichment.py`: read-only MediaWiki client, typed response/provenance/outcome, request and evidence limits, two-attempt retry policy.
- `src/triage/diff.py`: strict extraction of MediaWiki table diffs into plain wikitext hunks. Surrounding context stays with each change; insertions and deletions preserve their direction.
- `triage enrich`: offline fixture inspection or a public revision lookup, independent of model configuration.
- `schemas/enrichment-result.v1.json`: exported boundary contract. Python validation additionally enforces status/evidence/provenance consistency and the total text budget.
- [Attributed fixtures](../../tests/fixtures/enrichment/README.md), exact-output/failure tests, and a separate opt-in live check.

No dependencies or image versions changed. Phase 3 uses HTTPX, Pydantic, and Python's HTML parser already available in the project. Redpanda Connect continues to own ingestion; the cumulative gate reruns its 40 native tests and real broker delivery checks.

## Run the full deterministic gate

Prerequisites: Docker running with Compose 2.20+, Make, and uv. Python 3.13.16 and dependencies are installed by uv. Initial image/dependency downloads need internet; no live Wikipedia, model, credentials, or model downloads are used by these tests.

From the repository root:

```sh
make verify-phase-3
```

To use the same uv version as CI without replacing a global installation:

```sh
make verify-phase-3 UV='uvx --from uv==0.13.3 uv'
```

Expected: lint/format/strict types, configuration checks, **214 unit tests**, **10 integration/configuration tests**, **40 native Connect tests**, a container build/configuration check, and offline fixture inspection pass. Python application coverage is **100% lines and branches**, with zero omissions or exclusions. Shell and Connect behavior has separate tests; it is not included in the Python percentage.

Expected final line:

```text
PASS: Phase 3 enrichment checks. Live Wikipedia comparison is a separate check.
```

Allow roughly 1–3 minutes with cached images, longer on a first download. Reports are in ignored `reports/` and the GitHub Actions `phase-3-test-reports` artifact. The full gate creates unique test projects and removes only their containers/networks/volumes, including tools-profile services. It does not stop the user's running demo.

Focused checks:

```sh
make test-enrichment
make test-unit
```

`test-enrichment` tests the new behavior and the CLI; `test-unit` measures coverage over every application module. Earlier `verify-phase-1` and `verify-phase-2` targets remain available.

## Two-minute walkthrough: inspect actual evidence offline

No Docker, API key, or running model is needed:

```sh
make inspect-enrichment
```

This installs the application as a wheel and reads the committed public comparison for **Belle (Disney character)**, revisions **1380845740 → 1381189012**. The output includes:

```json
{
  "source": "fixture",
  "status": "ready",
  "attempts": 0,
  "content_truncated": false
}
```

The full JSON also includes the original event, Wikipedia endpoint, page ID `4483446`, source comparison URL, canonical titles, and one evidence hunk. Its `before` text names Paige O'Hara, Susan Egan, and Julie Nathanson; its `after` text retains Paige O'Hara. Two surrounding lines on each side are preserved from the API diff. This establishes a content change, not its factual correctness or whether the edit should be reviewed.

Show a controlled unavailable-revision outcome using the same event:

```sh
uv run --frozen --no-editable triage enrich \
  --event tests/fixtures/enrichment/belle-event.json \
  --fixture-response tests/fixtures/enrichment/missing-response.json
```

Expected: JSON with `status: "revision_unavailable"`, `provenance: null`, empty `evidence`, and **exit code 1**. No network request occurs. The missing/deleted/rate-limit fixtures are synthetic and explicitly labelled; only the Belle comparison is a captured Wikipedia response.

Show an evidence limit:

```sh
uv run --frozen --no-editable triage enrich \
  --event tests/fixtures/enrichment/synthetic-event.json \
  --fixture-response tests/fixtures/enrichment/oversized-response.json
```

Expected: `status: "evidence_limit"`, `content_truncated: true`, no evidence hunks, **exit code 1**. An overlong hunk is omitted in its entirety, so we never accidentally display a fragment that hides the changed text while claiming completeness.

CLI exit codes: **0** for `ready` or `no_text_change`; **1** for an incomplete/unavailable/error outcome (JSON remains inspectable); **2** for invalid input files or command usage. No outcome is a model decision. Treat all returned article text, including apparent instructions and escaped HTML, as untrusted data.

## Separate live verification

Internet access to English Wikipedia is required. This performs at most two public GET requests; it makes no model calls and incurs no model cost:

```sh
make smoke-enrichment
```

Expected: the live comparison has `status: "ready"`, the same IDs, provenance, and exact evidence as the attributed fixture. The command prints the result, saves `reports/live-enrichment.json` and JUnit output, and fails if the revisions are unavailable or differ. Public revisions can be hidden or deleted later; a failure does not invalidate the saved fixture. Usually completes in a few seconds; allow about 30 seconds under slow I/O.

For another validated event JSON file:

```sh
uv run --frozen --no-editable triage enrich --event path/to/edit-event.json
```

Omitting `--fixture-response` selects the real API. The event must follow [edit-event.v1.json](../../schemas/edit-event.v1.json). There is no arbitrary API URL option, and event titles/links are never used as request destinations.

## Boundaries and failure behavior

| Boundary | Behavior |
|---|---|
| Request identity | Fixed HTTPS English Wikipedia endpoint; positive, distinct revision IDs; explicit from/to direction; redirects disabled; descriptive User-Agent; `maxlag=5` |
| Response identity | Both returned revision IDs must match the request, both namespaces must be article namespace `0`, and both page IDs must match. Renames are retained as canonical from/to titles |
| Response bytes | Maximum 256 KiB, streamed as network chunks arrive, with deadline checks before buffering each chunk. Request identity encoding and reject unrequested compression before decoding. Stop/close on overflow; `response_too_large` marks content truncated |
| Evidence | Whole hunks, at most 4,096 characters per side, 20 hunks, and 16,000 characters total. Oversized/excess hunks are omitted and `evidence_limit` is explicit, even if some hunks remain |
| Markup | Decode entities once; preserve wikitext, spaces, citations, and before/after direction. Accept only supported table structure and inline formatting; nesting capped at 16. Unsupported/malformed markup becomes `unsupported_diff` |
| Missing/deleted | `nosuchrevid`, `baddiff`, and missing-content API errors become `revision_unavailable`; do not pretend to distinguish deletion from permission restrictions |
| Retry | At most two serial requests for HTTP 429/5xx and API rate-limit/upstream errors. Default wait 5 seconds; honor a valid Retry-After integer/date. If it exceeds 10 seconds or the remaining budget, return the explicit failure without retrying early |
| Time | Each connect/read/write/pool wait is at most 5 seconds, reduced to the remaining 20-second budget. Check the budget between streamed chunks, after responses, and before requests/retries. This is a cooperative deadline: an in-flight I/O operation can overshoot it by one bounded wait; it is not a hard wall-clock cancellation guarantee |
| Other failures | Distinct `http_error`, `timeout`, `network_error`, `invalid_response`, `provenance_mismatch`, and `deadline_exceeded` statuses; no raw upstream error text in output |

Only a valid empty diff yields `no_text_change`. A nonempty diff without a reliable extractable change is `unsupported_diff`. `ready` means the supported diff fits the limits; it does not mean the full article or cited sources were fetched. The API's bounded surrounding context is retained; reference URLs and templates are never fetched or executed. Complex/changed upstream diff layouts may abstain and need a separately tested parser extension.

The client has no durable cache or global rate coordinator. Phase 4 must call it with bounded concurrency and treat every non-ready outcome explicitly. Larger local/frontier model context windows do not override these evidence limits. Supporting very large edits, template expansion, full article context, or independent citation verification would need additional design and tests.

## Troubleshooting and cleanup

- Docker unavailable/port conflict: start Docker and rerun the full gate; the offline inspection command works independently.
- `revision_unavailable`: inspect the saved fixture and source IDs. Wikipedia may have removed or restricted a revision.
- `rate_limited` / `upstream_unavailable`: wait and run the opt-in smoke later; do not loop aggressively. Deterministic fixture tests remain available.
- `unsupported_diff` / `invalid_response`: inspect the small saved outcome. Do not bypass validation or call the content complete.
- Invalid event input: use the committed event as a template; arbitrary fields, wrong types, nonpositive/equal IDs, or a missing timezone are rejected. Event files are limited to 8 KiB.

The enrichment commands create no services or persistent data. `reports/` contains local verification artifacts and can be deleted when no longer needed. Infrastructure test cleanup is automatic and scoped to its unique project. Never remove the user's demo volumes to fix a test.

## Observed verification

Tested implementation commit: `29bf3c3b0a4f06a301cd73fa0c571c0bf4ded7ef`. Full evidence: [verification JSON](../evidence/phase-3-verification.json) and [live response](../evidence/phase-3-live.json).

- `make verify-phase-3 UV='uvx --from uv==0.13.3 uv'`: **exit 0**. All 214 unit tests, 10 integration/configuration tests, and 40 native Connect cases passed. Unit time 2.46 seconds; integration time 46.37 seconds. The complete cached run took about one minute.
- Coverage: **451/451 executable lines and 142/142 branches**, zero missing or excluded lines. Lint, formatting, strict types, shell/Compose validation, container packaging, and offline inspection passed.
- `make smoke-enrichment UV='uvx --from uv==0.13.3 uv'`: **exit 0**, one successful public comparison in **0.287 seconds**. Exact evidence and provenance matched the fixture. No model calls were made.
- Reversing the extracted before/after text made the exact-evidence test fail (exit 1); restoring the source and clearing that test's generated bytecode cache made it pass (exit 0).
- Added a slow-stream regression after review: the previous buffered implementation read all 100 simulated chunks before checking the deadline; the fixed version stops at chunk 5, reports `deadline_exceeded`, and closes the stream. The new test failed before the fix and passes afterward.
- Verified the original assignment SHA-256 is unchanged. Checked 107 relative Markdown links before adding the final evidence links; none were broken.
- The user's existing local stack remains running. Test fixtures verified their own containers/networks/volumes were removed. Private profiles and model/data volumes were not changed.

PR and Linux CI links will be recorded after publication. Later commits only add audit/verification documentation unless explicitly stated.

Next: Damien reviews this PR; Phase 4 begins only after merge and a new request.

## References

Request fields and response semantics follow [MediaWiki Compare](https://www.mediawiki.org/wiki/API:Compare). User-Agent, serial requests, and load handling follow [API etiquette](https://www.mediawiki.org/wiki/API:Etiquette) and [maxlag](https://www.mediawiki.org/wiki/Manual:Maxlag_parameter). The [fixture provenance](../../tests/fixtures/enrichment/README.md) links the original revisions and attribution.
