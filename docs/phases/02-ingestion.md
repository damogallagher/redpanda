# Phase 02: Connect ingestion and routing

Status: not started.
Branch: `phase/02-ingestion`. Base: `main` after the previous phase merges.

## Scope

Turn the public stream into a bounded stream of clean events that can be inspected independently.

## Planned work

Implement SSE framing/JSON parsing; fail-closed heartbeat/malformed handling; wiki/namespace/bot filters; deterministic sampling; event projection and timestamps; route accepted events and invalid candidate records to named topics; add a fixture source using the same processors and provenance metadata.

## How to test

Implement `make verify-phase-2`: cumulative checks plus native Connect tests for each filter/projection/error path. Feed a fixed SSE fixture through Connect to real Redpanda; use rpk to assert exact expected records/keys and error routing. Separately demonstrate a short live-feed run.

Commands are target interfaces until implemented. See [testing policy](../testing.md).

## Acceptance

The reviewer can see which inputs were accepted, dropped, or rejected and inspect resulting topic records without an LLM.

## Actual work and evidence

Not implemented. At completion record changed files/behavior, exact commands, expected versus observed output, coverage, tested commit, CI/PR links, and remaining limitations here.

## Walkthrough checkpoint

Demonstrate the new behavior from one known input. Explain which component owns it and show one meaningful failure case. Keep the demonstration short enough that Damien can repeat it himself.
