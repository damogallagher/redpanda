# Wikipedia edit triage — presentation study pack

Prepared for Damien Gallagher, 20 October 2026.

GitHub review: https://github.com/damogallagher/redpanda/pull/14

## Start here

1. Open `redpanda-study-companion.html` in Chrome, Safari or another modern browser. It works directly from disk: no installation, server, API key or model calls.
2. Use **Phase explorer** for the project story and **Trace an edit** for success/failure paths. Those traces are labelled teaching simulations.
3. Use **Model evidence** to inspect the actual saved local/frontier synthetic prompts and responses. These are embedded offline; selecting a case never calls a model.
4. Choose **Present** for 14 slides. Use Previous/Next or left/right arrows, Home/End, and Full screen. Escape exits full screen. Each slide links back to its detailed chapter.
5. Read `redpanda-study-guide.pdf` for the complete 36-page, 34-chapter guide. Its contents page and source links are clickable. `redpanda-study-guide.md` is the editable text version and includes the presentation outline.

Keep the files together so the HTML links to the PDF and editable guide continue to work. External source links require internet; the study content and interactions do not.

## What is covered

Assignment requirements; planning and six implementation phases; each phase's purpose, inputs, outputs, tests and handoff; architecture; Kafka/Redpanda and Connect; Docker and mode profiles; local versus frontier inference; enrichment and grounding; reasoning budgets; offset/replay semantics; Postgres and the API; actual demo results; cleanup; testing history; improvements; code tour; glossary; rehearsal questions and a 60-minute presentation plan.

## Evidence and scope

The source snapshot is `859b1662f574a6ff749689834f2dfc3ef48c9748`, including the PR #13 follow-up. PR #13 was open when this pack was prepared; main before that fix has 29 integration tests, while its tested follow-up has 30. All repository source links are pinned to the snapshot. Model scores are recorded regression observations, not a general-accuracy benchmark. Current local deployment limitations are explicit.

This is AI-assisted study material, not the assignment's independently authored personal README write-up. The original assignment, application code and personal README sections are unchanged. Creation of this pack made no new model calls and did not run or modify application containers.

## Artifact checks

All 36 PDF pages were rendered and visually reviewed; contents targets and text bounds were verified. The HTML's seven phases, six trace scenarios, 18 provider/case views, ten rehearsal items and 14 slides were checked in a real browser. Desktop/tablet/mobile widths (1440, 768, 390 and 320 pixels) had no page overflow, JavaScript errors or unexpected network requests. Embedded model transcripts match the saved source JSON exactly. Full-screen presentation was also verified.

## Changes after the frozen snapshot

This pack still describes tested snapshot `859b166`; its PDF/HTML/Markdown assets and recorded model runs are unchanged. Current main additionally contains the [evidence-count fix](../phases/06-evidence-limits.md) and [security hardening](../phases/06-security-quality.md). Use those guides and the current repository README for present limits, service-role permissions and test counts. Historical observations in the pack are not new measurements of the hardened code.
