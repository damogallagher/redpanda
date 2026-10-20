# Synthetic ingestion fixtures

These are invented protocol examples, not captured Wikipedia edits. They do not demonstrate model quality or refer to real revision content.

- `phase-2.sse`: six input segments: initial heartbeat, accepted article edit, bot edit, talk-page edit, second accepted article edit with multiline `data:`, and a candidate with an invalid revision ID.
- `phase-2-crlf.sse`: the same fixture with CRLF line endings.
- `expected-edits.json` / `expected-error.json`: exact projected output for the LF fixture with sampling disabled.
- `incomplete.sse`: valid JSON in an SSE frame whose final blank line is missing.
- `garbage.sse`: an unrecognized frame, which must not be treated as a heartbeat.
- `oversized.sse`: a valid candidate with synthetic padding exceeding the 64 KiB frame limit. The long repeated string is intentional boundary-test data.

The deterministic integration tests serve these files over local HTTP through the same Connect scanner, processor chain, and Redpanda output used by live ingestion. Replays may create duplicate records; keys remain stable.
