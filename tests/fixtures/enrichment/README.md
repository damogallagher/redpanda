# Revision enrichment fixtures

## Captured Wikipedia example

`belle-event.json` is the validated article event observed in the [Phase 2 live run](../../../docs/evidence/phase-2-live.json). `belle-response.json` is the JSON comparison retrieved on **20 October 2026** from the English Wikipedia Action API, using `action=compare`, `format=json`, `formatversion=2`, `prop=diff|ids|title|diffsize`, `maxlag=5`, `fromrev=1380845740`, and `torev=1381189012`.

Article: **Belle (Disney character)**, page ID `4483446`.

- [Original comparison](https://en.wikipedia.org/w/index.php?diff=1381189012&oldid=1380845740)
- [Before revision](https://en.wikipedia.org/w/index.php?oldid=1380845740)
- [After revision](https://en.wikipedia.org/w/index.php?oldid=1381189012)
- [Contributor history and attribution](https://en.wikipedia.org/w/index.php?title=Belle_(Disney_character)&action=history)
- Wikipedia article text is by its contributors, available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), subject to [Wikimedia's terms](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use). This attribution applies to the excerpt and its derived before/after evidence; it does not assign that license to unrelated project code.

The saved API body is unchanged except a trailing newline. It includes only requested comparison fields, not editor names/IPs or comments. The current client no longer requests the unnecessary `diffsize` field; additive fields remain accepted. Extracted evidence removes diff presentation markup, decodes HTML entities once, and groups the text with its surrounding context. No article claims were rewritten. This example removes two names/credits; it is a content test, not a labelled vandalism or factuality judgment.

## Synthetic cases

The other files are authored test data, not claims about actual Wikipedia revisions:

| File | Purpose |
|---|---|
| `synthetic-event.json` | Example IDs 100 → 101 and a synthetic title |
| `wording-response.json` | Same sentence with `colour` → `color`; exact text extraction, not an automated routine judgment |
| `oversized-response.json` | A 4,097-character before-side hunk; must report `evidence_limit` and omit the entire hunk |
| `missing-response.json` | API `nosuchrevid` → `revision_unavailable` |
| `deleted-response.json` | API `baddiff` → `revision_unavailable`; cannot distinguish permissions from deletion |
| `rate-limited-response.json` | HTTP-200 API `maxlag`; live client waits within its retry budget |

Tests also generate exact 256 KiB and 256 KiB + 1 payloads, 20/21 hunks, 16,000-character boundaries, malformed structures, escaped citations/instructions, delayed streams, HTTP 429/503, and Retry-After seconds/dates. Generated boundary payloads avoid committing hundreds of kilobytes of repetitive text.

Run `make inspect-enrichment` to inspect the attributed example and `make test-enrichment` for all enrichment/CLI assertions. See the [Phase 3 guide](../../../docs/phases/03-enrichment.md) for failure demonstrations and the separate live check.
