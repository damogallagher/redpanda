# Phase 03: Revision content enrichment

Status: not started.
Branch: `phase/03-enrichment`. Base: `main` after the previous phase merges.

## Scope

Fetch the content the model needs and establish safe, bounded behavior around the public API.

## Planned work

Implement a typed MediaWiki client and diff extraction; allowlist the endpoint; validate revision IDs; include provenance and before/after evidence; handle deletion, missing revision, rate limits, timeouts, truncation, and size limits; preserve representative attributed fixtures.

## How to test

See the [phase verification guide](../phase-verification.md) for this phase’s exact behavioral checkpoints and evidence requirements.

Implement `make verify-phase-3`: cumulative checks plus 100% unit coverage for enrichment and a fixture-based inspection command. Exercise exact evidence extraction and failure statuses; run one real comparison request separately and record its revision IDs.

Planned deterministic entry point (not implemented yet):

```sh
make verify-phase-3
```

Live source/model checks are separate from this deterministic command. Before this phase is completed, document actual prerequisites, live commands, representative output, runtime, cleanup, and troubleshooting here. See [testing policy](../testing.md).

## Acceptance

An input event yields readable before/after evidence or a specific incomplete/error outcome; the reviewer can inspect the model input before reasoning is added.

## Actual work and evidence

Not implemented. At completion record changed files/behavior, exact commands, expected versus observed output, coverage, tested commit, CI/PR links, and remaining limitations here.

## Walkthrough checkpoint

Demonstrate the new behavior from one known input. Explain which component owns it and show one meaningful failure case. Keep the demonstration short enough that Damien can repeat it himself.
