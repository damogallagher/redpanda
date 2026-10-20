# Phase 04: Multi-step reasoning and durable delivery

Status: not started.
Branch: `phase/04-reasoning`. Base: `main` after the previous phase merges.

## Scope

Implement the core reasoning service with meaningful model work and explicit failure behavior.

## Planned work

Implement the shared model interface with Ollama and hosted adapters; add extraction then assessment prompts; strict output/evidence validation; confidence-based review; bounded repairs/retries/deadlines; versioned prompts; Kafka consumer/producer adapters; result/error publication; offset acknowledgements; graceful shutdown; structured operational logs; a small development evaluation set.

## How to test

Implement `make verify-phase-4`: cumulative checks, full unit coverage including both provider contracts, real-broker fixture integration with a model stub, deliberate parser/branch mutation checks, and a recorded real-model run. Force publish failure and prove the input is not committed. Trace low-confidence and malformed-response paths.

Commands are target interfaces until implemented. See [testing policy](../testing.md).

## Acceptance

rpk displays validated results and explicit failures; all model calls are bounded; a reviewer can follow one edit through each decision in application code.

## Actual work and evidence

Not implemented. At completion record changed files/behavior, exact commands, expected versus observed output, coverage, tested commit, CI/PR links, and remaining limitations here.

## Walkthrough checkpoint

Demonstrate the new behavior from one known input. Explain which component owns it and show one meaningful failure case. Keep the demonstration short enough that Damien can repeat it himself.
