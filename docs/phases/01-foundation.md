# Phase 01: Foundation and feasibility

Status: not started.
Branch: `phase/01-foundation`. Base: `main` after the previous phase merges.

## Scope

Provide reproducible dependencies, container setup, topic initialization, schemas, and the first working checks.

## Planned work

Pin Python/dependencies and container images; add `.env.example`/ignore rules; start Redpanda in dev-container mode and Postgres 16; establish selectable Ollama/hosted model configuration, local model bootstrap/readiness, and documented provider-specific setup; test a representative diff for resource/quality feasibility; define versioned event/result contracts; introduce CI and 100% coverage when production code appears.

## How to test

Implement `make verify-phase-1`: Compose validation, relevant unit/schema tests, broker readiness/topic setup via rpk, database readiness, and a real model readiness/request smoke for each backend (hosted credentials required; do not claim verification without them). Confirm hosted mode starts without downloading a local model. Re-run startup to prove initialization is idempotent.

Commands are target interfaces until implemented. See [testing policy](../testing.md).

## Acceptance

A fresh environment starts dependencies and the selected model; prerequisites, download size, measured startup/response time, hardware, and failure diagnostics are documented.

## Actual work and evidence

Not implemented. At completion record changed files/behavior, exact commands, expected versus observed output, coverage, tested commit, CI/PR links, and remaining limitations here.

## Walkthrough checkpoint

Demonstrate the new behavior from one known input. Explain which component owns it and show one meaningful failure case. Keep the demonstration short enough that Damien can repeat it himself.
