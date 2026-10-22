# Phase index

Start with the [phase verification guide](../phase-verification.md) for the command matrix, inputs, expected results, and reviewer workflow.

Every phase has its own branch and PR into `main`. Status and test evidence must reflect actual work.

- [Phase 00: Planning and audit trail](00-plan.md)
- [Phase 01: Foundation and feasibility](01-foundation.md)
- [Phase 02: Connect ingestion and routing](02-ingestion.md)
- [Phase 03: Revision content enrichment](03-enrichment.md)
- [Phase 04: Multi-step reasoning and durable delivery](04-reasoning.md)
- [Phase 05: Persistence and readable results](05-serving.md)
- [Phase 06: Operational acceptance and handover](06-acceptance.md)
- [Correctness follow-up: evidence-count boundaries and compatibility](06-evidence-limits.md)

Phases are sequential because each checkpoint extends the previous working system. Phases 1–6 have executable checks; each record distinguishes observed evidence at its tested commit from pending checks and later follow-ups.

- [Walkthrough follow-up: refreshed guides, PDF and interactive study pack](06-walkthrough-refresh.md)
