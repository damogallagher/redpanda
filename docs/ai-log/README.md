# AI interaction audit trail

Track the user's development prompts and the assistant's visible replies from this conversation onward. Store them in ordered Markdown session files under `sessions/`, preserving exact wording except explicitly marked sensitive-data redactions. Preserve clarifying questions and user answers, not just final results. Record date, phase, actor, and related PR/commit when known. Do not invent exact timestamps, model identifiers, or replies.

This is a visible conversation log, not hidden reasoning, system/developer instructions, or a dump of tool credentials. Tool activity is summarized as evidence in phase records; relevant commands and sanitized outcomes are included there. This is a fresh build and fresh history; do not import earlier work or earlier interaction logs.

At each phase boundary, append the latest prompts and responses and check the log before committing. This initial log is maintained explicitly in this chat; no background capture or capture of other chats/tools has been installed or promised. Prompts used elsewhere must be supplied or explicitly imported before they can appear here. Reconcile each session at close, recording any known gaps rather than claiming completeness.

This repository is public. Never commit access tokens, passwords, private customer content, raw environment dumps, or secret-bearing tool output. Replace sensitive spans with `[REDACTED: reason]` and record the redaction. Do not silently paraphrase a transcript. No secrets have been requested for logging.

Runtime model prompts are a separate artifact: version the actual prompt templates in source, and retain model input/output plus provenance for curated, sanitized evaluation runs. The Phase 4 worker retains metadata logs only (Docker rotation: 10 MiB × 3 files), not complete routine prompts/responses. Explicit curated evaluation runs save transcripts to ignored reports for review before publication; do not automatically publish every live record to GitHub.

Latest demo: [Executed submission demo](sessions/2026-10-20-executed-demo.md). Earlier: [walkthrough](sessions/2026-10-20-submission-demo.md), [Actions maintenance](sessions/2026-10-20-actions-maintenance.md), [Phase 6](sessions/2026-10-20-phase-6.md).

Latest study session: [Presentation study pack](sessions/2026-10-20-study-guide.md).

Latest review: [Study-pack location and solution gaps](sessions/2026-10-21-gap-review.md).

Latest correctness fix: [Evidence-count boundaries](sessions/2026-10-21-evidence-limits.md).

Latest hardening: [Security and code quality](sessions/2026-10-21-security-quality.md).

Conflict resolution: [PR #13 and PR #14](sessions/2026-10-22-conflict-resolution.md).

Latest submission check and documentation cleanup: [Submission readiness](sessions/2026-10-22-submission-readiness.md).

Latest walkthrough maintenance: [Current-system study-pack refresh](sessions/2026-10-22-walkthrough-refresh.md).
