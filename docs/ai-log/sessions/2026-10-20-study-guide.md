# Presentation study pack — 20 October 2026

Privacy redaction: local artifact paths have been removed. Where available, local file links now point to the corresponding files in the repository; the historical ZIP path is redacted.

Documentation/artifact authoring from frozen repository snapshot 859b166. No application or model execution is claimed.

## User

Can  you generate document and / or pdf / and or presentation / and or interactive html demo highlighting how we approached this project, how we broke it into phases, what was built in each phase, its purpose , how we tested it, the inputs / responses at each phase, how subsequent phases built on top of each other and then finally talk about the complete system and potential areas for improvement. Highlight key components such as local vs frontier models, kafka, connect, docker and any key pieces listed. Make this professional and accurate. This will be a study guide for me as I prepare to present my solution. Does this make sense? Make this as professional and as detailed as possible for me

## Assistant

> I’ll build a detailed study guide and an interactive HTML walkthrough, grounded in the repository, phase records and saved test evidence. I’ll include architecture diagrams, phase-by-phase examples, local versus frontier model results, presentation talking points and honest improvement areas, with a PDF for offline study.

## Assistant

> I’m using the PDF skill to produce and visually check the offline guide. The HTML version will work without a server and include a phase explorer, a step-through of event processing, and rehearsal questions. I’ll clearly distinguish implemented behavior, recorded test results and proposed improvements.

## Assistant

> The project has a clear progression: establish the runtime, ingest trustworthy events, fetch the actual revision evidence, add bounded reasoning, persist and serve results, then prove recovery and cleanup. I’m making those dependencies central to the guide. I’m also checking details that matter in an interview, especially why Kafka delivery is at least once, what 100% coverage proves, and why an abstention can be the correct outcome.

## Assistant

> I’ll deliver one cohesive study pack: a detailed PDF, an editable written guide, and an HTML companion with presentation mode. The examples will label synthetic fixtures and real observations separately. The guide will also explain the fixes discovered during development, including malformed revision keys, deadline handling, replay behavior and Docker volume cleanup.

## Assistant

> The draft now covers all six implementation phases plus planning, with worked inputs and outputs, a failure-routing map, a code tour and an interview rehearsal section. One important finding is called out explicitly: the source parser accepts up to 20 hunks, while extraction allows eight changes and must cover every hunk. That helps explain why larger real edits can abstain even when the small acceptance set passes.

## Assistant

> The written guide and HTML companion are built. The HTML includes the actual saved synthetic model prompts and responses, plus six clearly labelled simulations covering success, abstention, publication failure, replay and database recovery. I’m now checking the PDF page layouts and exercising the interactive controls at desktop and phone widths.

## Assistant

> The content review is complete, and the PDF now has 36 pages with a linked contents page and source references throughout. Browser testing found a small-screen overflow issue, which I’m correcting before delivery. I’m also keeping the presentation separate from the actual application: its traces are simulations, while its model-evidence view shows saved real responses.

## Assistant

> The checks now pass: all seven phase views, six event traces, both providers’ nine saved cases, rehearsal questions and all 14 slides work offline, including full-screen presentation. I’ve also reviewed every PDF page and checked its contents links. I’m packaging the files and adding the study materials and this conversation to a separate documentation PR.

## Assistant

> The study pack is saved in GitHub as PR #14. I’m doing the final download and presentation check; application code and your personal README sections remain unchanged. Start with the phase explorer, then use the detailed chapters and rehearsal questions to prepare for the walkthrough.

## Assistant — final

Created a detailed study pack grounded in the repository and recorded test evidence.

- Download the complete pack — [REDACTED: local ZIP artifact path]
- [Open the interactive companion](../../study-guide/redpanda-study-companion.html) — phase explorer, six event traces, saved model responses, rehearsal questions and **14-slide presentation mode**.
- [Editable written guide](../../study-guide/redpanda-study-guide.md)

The **36-page PDF** covers each phase’s purpose, inputs, outputs, tests and dependencies, plus architecture, failure handling, actual results, code walkthroughs and prioritized improvements.

[PDF guide](../../study-guide/redpanda-study-guide.pdf)

Everything is saved in [PR #14](https://github.com/damogallagher/redpanda/pull/14), including the updated prompt log. The PDF was visually reviewed and the HTML tested offline at desktop and mobile widths.

Start with **Phase explorer**, then use **Present** to rehearse. Your independent README sections remain unchanged.
