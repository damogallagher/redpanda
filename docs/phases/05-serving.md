# Phase 05: Persistence and readable results

Status: not started.
Branch: `phase/05-serving`. Base: `main` after the previous phase merges.

## Scope

Complete the source-to-result path with durable storage and a simple query interface.

## Planned work

Implement Connect validation/routing and parameterized Postgres upsert; schema/migrations and unique analysis key; read-only API with bounded pagination/filters; health/readiness; deterministic seeds; safe display of evidence and source links; replay instructions.

## How to test

Implement `make verify-phase-5`: cumulative checks plus real database sink/upsert tests, API unit/integration tests, and fixture end-to-end tests. Replay the same event and assert one logical stored result; interrupt the sink/database, restore it, and verify eventual delivery.

Commands are target interfaces until implemented. See [testing policy](../testing.md).

## Acceptance

The reviewer can run the documented commands and retrieve the expected persisted decision/evidence for a known seeded edit.

## Actual work and evidence

Not implemented. At completion record changed files/behavior, exact commands, expected versus observed output, coverage, tested commit, CI/PR links, and remaining limitations here.

## Walkthrough checkpoint

Demonstrate the new behavior from one known input. Explain which component owns it and show one meaningful failure case. Keep the demonstration short enough that Damien can repeat it himself.
