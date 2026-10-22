# Wikipedia edit triage - presentation study pack

Updated for Damien Gallagher, 22 October 2026. System reference: merged main `30510a88e54f7f75b374773c5ec725be090974f1` (PRs #1-19 merged).

## Start here

1. Open [the interactive companion](redpanda-study-companion.html) in a browser. It runs directly from disk without a server, API key or model calls. GitHub shows the HTML source; download the files together or open your local copy to use it.
2. Use **Phase explorer** for the build sequence and **Trace an edit** for seven success/failure paths, including oversized evidence producing a zero-call abstention. These traces are labelled teaching simulations.
3. Use **Model evidence** to inspect the unchanged saved local/frontier synthetic prompts and responses. These are historical 20 October results, before final hardening and the Ollama image update.
4. Choose **Present** for 14 slides. Previous/Next, arrow keys, Home/End and Full screen navigate the presentation. Each slide opens its detailed chapter.
5. Read the [36-page PDF](redpanda-study-guide.pdf) or [editable guide](redpanda-study-guide.md) for all 34 chapters. Chapter 26 is the code tour; 30 has rehearsal questions; 31 is the 60-minute agenda; 32 prepares for the extension.

Keep the files together so the HTML links to the PDF and editable guide work. External source links need internet. For real execution, follow the [current demo guide](../submission-demo.md) in order; the companion does not launch the application.

## What changed in this refresh

- Phase 6 is implemented. The current cumulative gate is `make verify-phase-6`, also available as `make test`.
- Current totals are **453 unit tests, 32 integration/configuration checks and 72 Connect cases**, with **100% of 1,172 application lines and 286 branches** covered. Main [CI run 39859001474](https://github.com/damogallagher/redpanda/actions/runs/39859001474) passed without emitted warnings or check annotations.
- New enrichment and reasoning share an **eight-hunk capacity**. Larger inputs abstain before model calls; historical v1 records with 20 hunks remain readable. See the [boundary regression record](../phases/06-evidence-limits.md).
- The API, sink and migration helper have separate database permissions. Host validation, private atomic reports and stronger code-quality gates are implemented. The current bundled Ollama image is **0.40.8**.
- The security discussion reflects the broader recorded image scans, including remaining findings. Passing functional CI does not mean the images are vulnerability-free or the deployment is ready for public access.
- Demo preparation accounts for private profiles, all three database passwords, isolated test helpers, asynchronous delivery and events versus distinct result rows. The actual extension is still pending from Redpanda; the pack explains how to implement, test and defend its diff once supplied.

## Evidence and scope

Repository source links are pinned to `30510a8`. Earlier phase checkpoints retain their historical counts. The model transcripts and live observations are unchanged historical evidence, not a new evaluation of the current images. Rerun the chosen model configuration before presenting; a small fixed-case pass does not establish general accuracy.

The original 20 October pack remains available through Git history and [PR #14](https://github.com/damogallagher/redpanda/pull/14). This revision supersedes that pack's current-system descriptions. It is AI-assisted study material; the personal README sections and original assignment are unchanged by this refresh.

## How the refreshed pack was checked

The [refresh record](../phases/06-walkthrough-refresh.md) and [verification evidence](../evidence/study-guide-refresh-verification.json) describe the current checks. All 36 PDF pages were rendered and visually reviewed, with 34 contents destinations and page bounds checked. Browser checks covered seven phases, seven traces, 18 provider/case views, ten rehearsal items and 14 slides at widths 1440, 768, 390 and 320. No JavaScript errors, unexpected network requests or horizontal page overflow were observed; full-screen navigation and exact transcript correspondence passed.

The cumulative application gate was rerun separately. No real model calls, public-feed requests or new vulnerability scans were made for this documentation change. [Artifact checksums](study-pack-checksums.json) identify this revision; the original [verification record](../evidence/study-guide-verification.json) remains historical.
