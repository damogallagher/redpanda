# Phase index

Start with the [phase verification guide](../phase-verification.md) for the command matrix, inputs, expected results, and reviewer workflow.

Phases 0–6 and their follow-ups through PR #20 are merged. Each record below is a historical checkpoint: its test counts, versions and original handover statements apply to its recorded commits. Do not read an old “awaiting review” or “not started” statement as current status. Use the [handover](../handover.md) for the verified baseline and the README for current setup.

- [Phase 00: Planning and audit trail](00-plan.md)
- [Phase 01: Foundation and feasibility](01-foundation.md)
- [Phase 02: Connect ingestion and routing](02-ingestion.md)
- [Phase 03: Revision content enrichment](03-enrichment.md)
- [Phase 04: Multi-step reasoning and durable delivery](04-reasoning.md)
- [Phase 05: Persistence and readable results](05-serving.md)
- [Phase 06: Operational acceptance and handover](06-acceptance.md)
- [Correctness follow-up: evidence-count boundaries and compatibility](06-evidence-limits.md)

Phases are sequential because each checkpoint extends the previous working system. Phases 1–6 have executable checks. Running a phase target on current main uses current code and may include later tests; check out the recorded commit to reproduce a historical count.

- [Walkthrough follow-up: refreshed guides, PDF and interactive study pack](06-walkthrough-refresh.md)

- [Dependency maintenance after Phase 1](01-dependency-updates.md)
- [CI/action maintenance during Phase 6](06-ci-maintenance.md)
- [Security and code-quality hardening](06-security-quality.md)

- [Final repository review: first-run instructions and historical-record clarity](06-final-review.md)
