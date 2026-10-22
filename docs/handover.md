# Handover and assignment checklist

Begin with the [simple operator guide](operations.md). The supported deployment is a single local Docker stack with selectable Ollama/OpenAI inference. The scripts and tests are designed for review and recovery; 100% unit coverage is not a claim of perfect models, gap-free upstream delivery, or a production hosting platform.

## Follow one edit

```mermaid
flowchart LR
    W[Wikipedia recent changes] --> C[Connect: SSE, filter, project, sample]
    C --> E[(edits)]
    E --> P[Python: fetch revision diff]
    P --> X[Extract grounded changes]
    X --> A[Assess meaning and support]
    A --> R[Review uncertain or conflicting output]
    A --> O[(results)]
    R --> O
    O --> S[Connect: validate and upsert]
    S --> D[(Postgres)]
    D --> API[Read-only results API]
```

Connect discards bots and non-article/non-English edits, projects only necessary fields, then selects a deterministic 1% by event identity. The worker fetches the actual before/after revision comparison from the fixed Wikipedia API endpoint. It extracts exact quoted changes, assesses their meaning and evidence, and may request a second assessment. Validation, four-call and time budgets are shared across repairs/retries. Unavailable evidence produces abstention; technical failures produce explicit error records. A result is a suggestion for human review, not a claim of factual truth or an automatic Wikipedia action.

Output acknowledgement precedes input offset commit. A crash between them can repeat inference and publish duplicate results. Connect persists only valid envelopes; a unique `(wiki, revision_id, analysis_version)` key and monotonic source offset preserve one logical SQL row. This assumes a single results partition and stable topic history; do not delete/recreate the topic while retaining its database and assume offsets remain comparable. Reset broker and database together with the documented data-cleanup command when discarding the demo.

New inference is limited to eight complete source hunks, sharing the extraction count limit. Larger edits are recorded as `insufficient_evidence` with `evidence_limit`, `content_truncated: true`, zero attempts and no model calls. Historical v1 records with 20 source hunks remain readable; passing such an input to reasoning applies the same safe limit before inference. [Boundary behavior and regression proof](phases/06-evidence-limits.md).

## Code map

| Question | Read |
|---|---|
| What comes in and what is discarded? | `connect/ingest.yaml`, `connect/ingest_test.yaml` |
| What are the contracts and bounds? | `src/triage/schema.py`, `src/triage/enrichment.py`, `schemas/` |
| How is an HTML revision diff parsed safely? | `src/triage/diff.py` |
| What does the model see and how is it validated? | `src/triage/prompts.py`, `src/triage/reasoning.py`, `src/triage/llm.py` |
| When are offsets committed? | `src/triage/broker.py`, `src/triage/worker.py` |
| How are results deduplicated and served? | `connect/sink.yaml`, `db/002-results.sql`, `src/triage/storage.py`, `src/triage/api.py` |
| How are database permissions separated? | `db/003-service-roles.sql`, `tests/test_database_security.py` |
| How do model tests and cleanup work? | `src/triage/evaluation.py`, `src/triage/operations.py`, thin wrappers in `scripts/` |
| Where are recovery proofs? | `tests/test_worker_integration.py`, `tests/test_serving_integration.py`, `tests/test_acceptance_integration.py` |

## Assignment requirements

| Original requirement | Delivered proof / remaining work |
|---|---|
| Public free source requiring no authentication | Wikimedia recent-change stream and revision API; live checks and attributed fixture |
| Redpanda Connect selects and transforms data | Native SSE/filter/projection/routing pipeline, 40 ingestion cases, real broker integration |
| Worker in chosen language using a local model | Python, bundled Ollama by default; optional explicit OpenAI profile |
| Reasoning depends on actual content | Revision enrichment plus grounded extraction → assessment → optional review; nine frozen acceptance cases per provider |
| More than a single prompt invocation | Ready successful examples have at least extraction and assessment calls; review/repair paths tested |
| Dirty output and uncertainty handled | Strict JSON/quotes/enums, shared retry budget, abstention and error topics; deterministic negative cases |
| Structured/enriched output consumed downstream | Versioned envelopes, second Connect pipeline, transactional SQL upsert and paginated read-only API |
| Focused tests of risky behavior | Parser/budget/delivery/idempotency tests, fault/restart drills and documented mutation evidence; 100% line/branch unit gate |
| Runs locally with Docker Compose | Root default Compose includes broker, Connect, model/bootstrap, worker, Postgres and API; fresh-volume live acceptance command |
| Redpanda tools used where sensible | Connect for both transport pipelines, native Connect tests/lint, `rpk` for topics/groups/lag/replay inspection |
| Public code and original assignment | This repository, unchanged [assignment](assignment/fde-take-home-exercise.md), phase branches/PRs |
| AI prompts and visible responses retained | [Conversation audit](ai-log/README.md), source prompt versions, sanitized curated model transcripts |
| README: tradeoffs, surprises/production failure modes, customer value | Draft sections are present in [README](../README.md#tradeoffs). Damien must finalise the write-up in accordance with the assignment's independent-authorship requirement |

## Deployment limits and next operational decisions

- Single-node, single-partition, sequential consumer; no HA, automated supervision or capacity guarantee. The worker intentionally stops after ten edits by default. Increasing batch length does not increase processing rate. Ingestion can outpace inference; monitor `triage-v1` and `triage-store-v1` lag with `rpk`.
- Wikimedia's live HTTP stream has no durable source checkpoint here. Reconnect can miss events; delivery guarantees begin once an edit is acknowledged in Kafka. Public revisions can later disappear. Oversized/unsupported evidence is not silently treated as routine.
- A model timeout is bounded and routed to `processing-errors`; it is not silently retried forever or automatically replayed later. Restore the provider, inspect the error and deliberately requeue the event if needed. Broker publication/commit failure instead stops the worker and leaves input pending for restart.
- API and diagnostic ports bind to loopback; broker/database are internal. The API uses the restricted `triage_reader` role (SELECT); the sink uses `triage_writer` (SELECT/INSERT/UPDATE plus sequence usage). Neither service receives the administrator password. The migration helper reconciles these permissions on startup; see [database permissions and rotation](phases/06-security-quality.md#applying-the-database-permissions). API user authentication, TLS, a rate-limit gateway, backup/restore and deployment-specific network/secret controls are still required before exposing the system outside a local review machine.
- Image/Python/action pins make builds reproducible; model tags and provider internals can change. Evaluate the selected model, record its digest/ID, and set explicit cost limits. A tiny acceptance set does not establish general classification accuracy.
- The [security review](security-review.md) describes exactly what was audited and any limits. Do not equate no reported package advisories with absence of vulnerabilities.

PRs #1-#19 are merged. Main `30510a8` passed [the cumulative CI gate](https://github.com/damogallagher/redpanda/actions/runs/39859001474): 453 unit tests, 32 integration checks, 72 Connect cases, 100% application line/branch coverage, and zero emitted warnings or check annotations. Historical phase records retain their tested counts. The [refreshed study pack](study-guide/README.md) describes this current system while keeping earlier model observations explicitly dated.

Before submission: finalise the three personal README sections in your own words, review/merge any final documentation PR, confirm CI is green on the submitted commit, choose and verify a model path using the [current demo guide](submission-demo.md), rehearse one success and one failure recovery, and inspect the original assignment. The previous live-model evaluations predate the final hardening and Ollama image update. No further feature phase is required by the assignment; known upstream image vulnerabilities and deployment limitations remain disclosed in the [security review](security-review.md).
