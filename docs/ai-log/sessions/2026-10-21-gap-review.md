# 21 October 2026 — Study-pack location and solution gap review

Scope: review only. Application snapshot: main `447920f`; executed-demo evidence: `859b166`; study pack: `c440e66`. PRs #13 and #14 were open with successful checks when inspected. No application changes, real model requests, full-stack rerun or merge were performed. The boundary reproduction uses synthetic evidence and a stubbed model; it is separate from the existing coverage evidence.

## User

is this pack stored in github?

## Assistant — final

Yes—the **PDF, interactive HTML companion, editable guide and instructions** are stored in GitHub:

- [Open the study-pack folder](https://github.com/damogallagher/redpanda/tree/c440e661ff65cb0b54ff7db25e13e74922a997f0/docs/study-guide)
- [Review PR #14](https://github.com/damogallagher/redpanda/pull/14)

Download the HTML file to use its interactive features; GitHub itself displays the source.

## User

are there any gaps in the solution we developed?

## Assistant — progress

I’ll check the code, tests and recorded demo results against the assignment, then separate submission gaps from improvements that would matter in production.

## Assistant — progress

The core assignment requirements are covered, but there are real gaps. The personal README sections are still blank, and PRs #13 and #14 are still open. The strongest technical concern is model reliability on real edits: the final Ollama demo stored all three results safely, but two were abstentions after invalid output.

## Assistant — progress

I reproduced a concrete boundary bug: enrichment accepts up to 20 changed sections, but extraction allows only eight while requiring every section to be covered. A valid nine-section edit therefore cannot succeed; it makes two futile model calls before abstaining.

I’m recording the findings in the GitHub prompt log. I haven’t changed the application or made any paid model calls.

## Review verification

Read the original assignment, README, operational/security/evaluation evidence, and the ingestion, enrichment, reasoning, worker, broker, model adapter and storage boundaries. Checked live GitHub PR state. A synthetic valid nine-hunk enrichment was tested twice: once with all nine exact grounded changes, once with the maximum eight schema-permitted changes. Both returned `insufficient_evidence` / `invalid_output` after two stubbed calls and zero real calls. The first violates the extraction maximum; the second cannot satisfy all-hunk coverage. No application files were modified.

## Assistant — final

Yes. **The core take-home functionality is delivered, but there are gaps—and I would not describe the whole system as fully production-ready.**

Before submission, I would prioritize these:

1. **Fix the evidence-size mismatch.** Enrichment accepts up to 20 changed sections, while extraction permits only eight and requires every section to be covered. I reproduced a nine-section edit that inevitably abstains after two wasted calls. The simplest fix is to align the limits, explicitly handle oversized edits before inference, and add a regression test. [Reasoning code](https://github.com/damogallagher/redpanda/blob/447920f0c543f50ee2ce1a822ab8c6e8cdc6024d/src/triage/reasoning.py#L40)

2. **Complete your personal README sections.** Tradeoffs, surprises/production failure modes, and customer value still contain placeholders. These are required submission material that the assignment asks you to write independently. [README](https://github.com/damogallagher/redpanda/blob/447920f0c543f50ee2ce1a822ab8c6e8cdc6024d/README.md#tradeoffs)

3. **Strengthen evidence of model usefulness.** Both models passed nine curated cases, but the final live Ollama run assessed only one of three edits; two abstained after invalid output. Safe handling worked, but useful classification remains inconsistent. We need more realistic, independently labelled examples and measurements of incorrect decisions, abstentions and latency. The current repair attempt also provides no specific validation feedback. [Recorded results](https://github.com/damogallagher/redpanda/blob/859b1662f574a6ff749689834f2dfc3ef48c9748/docs/evaluations/submission-demo.md)

4. **Finish the review/merge process.** [PR #13](https://github.com/damogallagher/redpanda/pull/13), containing the executed-demo evidence and cleanup fix, and [PR #14](https://github.com/damogallagher/redpanda/pull/14), containing the study pack, are still open. Both had successful checks when inspected. Their changes are on GitHub but are not yet in `main`.

The main production gaps are:

- **Source completeness and capacity:** reconnecting to Wikipedia can miss events; there is no durable source checkpoint. Inference is sequential, sampling is not a rate limit, and the worker stops after ten edits by default. We have no sustained-load guarantee.
- **Operational recovery:** logs, error topics and recovery tests exist, but there is no integrated alerting or automated, controlled requeue workflow. An available results API does not prove that the pipeline is keeping up.
- **Deployment hardening:** this is a single-node local stack without HA, authentication/TLS, tested backup/restore or separated database roles. The recorded container scan also retained unresolved OS advisories. [Operational limits](https://github.com/damogallagher/redpanda/blob/447920f0c543f50ee2ce1a822ab8c6e8cdc6024d/docs/handover.md#deployment-limits-and-next-operational-decisions) · [Security review](https://github.com/damogallagher/redpanda/blob/447920f0c543f50ee2ce1a822ab8c6e8cdc6024d/docs/security-review.md)
- **Analysis history:** the storage key uses revision and analysis version, not model or prompt version. Reprocessing the same edit with another model under the same analysis version can replace the earlier result. Side-by-side comparisons or a full audit history need explicit run/version identities. [Storage contract](https://github.com/damogallagher/redpanda/blob/447920f0c543f50ee2ce1a822ab8c6e8cdc6024d/db/002-results.sql#L14)

**100% unit coverage remains valuable, but it does not establish model accuracy, complete input coverage or production readiness.** This review used code inspection, saved demo evidence and a stubbed boundary reproduction; I did not rerun the full stack or change application code. The findings and conversation are recorded in PR #14.

My recommendation is to fix the boundary bug before submission, finish your README, and present the broader limitations candidly. Avoid a large last-minute expansion of scope.
