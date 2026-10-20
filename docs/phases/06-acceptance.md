# Phase 06: Operational acceptance and handover

Status: not started.
Branch: `phase/06-acceptance`. Base: `main` after the previous phase merges.

## Scope

Prove the complete system is reproducible, robust within its stated limits, and easy to defend in a walkthrough.

## Planned work

Finish clean-clone startup, restart/replay drills, backlog/capacity observations, held-out model evaluation, dependency/security review, secret/log-redaction checks, exact run/troubleshooting documentation, and a concise code/data-flow guide. Reconcile every assignment requirement and phase result. Damien independently writes the required personal README sections.

## How to test

See the [phase verification guide](../phase-verification.md) for this phase’s exact behavioral checkpoints and evidence requirements.

Implement `make verify-phase-6`: all prior checks and end-to-end acceptance. Run default `docker compose up` with fresh application volumes, verify model bootstrap, process seeded and live edits, inspect lag, and test worker/model/broker/database failures and recovery. Record environment, timings, evaluation results, and remaining deployment limits.

Planned deterministic entry point (not implemented yet):

```sh
make verify-phase-6
```

Live source/model checks are separate from this deterministic command. Before this phase is completed, document actual prerequisites, live commands, representative output, runtime, cleanup, and troubleshooting here. See [testing policy](../testing.md).

## Acceptance

All deterministic gates pass; 100% application line/branch coverage is evidenced; the reviewer can reproduce startup and trace normal/failure cases. Submission remains incomplete until Damien supplies his independently written README sections.

## Actual work and evidence

Not implemented. At completion record changed files/behavior, exact commands, expected versus observed output, coverage, tested commit, CI/PR links, and remaining limitations here.

## Walkthrough checkpoint

Demonstrate the new behavior from one known input. Explain which component owns it and show one meaningful failure case. Keep the demonstration short enough that Damien can repeat it himself.
