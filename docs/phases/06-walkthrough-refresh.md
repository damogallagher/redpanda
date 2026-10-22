# Walkthrough material refresh - 22 October 2026

Branch `docs/walkthrough-refresh` starts from merged main `30510a88e54f7f75b374773c5ec725be090974f1`, after PR #19. This is a documentation/artifact update. The complete root README, original assignment, application, tests, schemas, dependencies and CI workflow are unchanged. Damien reviews and merges the PR.

## What changed and why

The phase-verification page still marked Phase 6 as planned. The original study pack described snapshot `859b166`, before the shared evidence limit, database role separation and subsequent security/CI work. This refresh brings its current-system descriptions to the merged implementation while preserving historical phase counts and model evidence.

- Corrected the phase matrix and cumulative command, the testing guide's integration total, and startup instructions for the current gate and all three database passwords.
- Updated the PDF, editable guide, offline companion and 14 presentation slides to source snapshot `30510a8`: 453 unit / 32 integration / 72 Connect checks; eight-hunk processing with zero-call oversized abstention; historical 20-hunk read compatibility; restricted database roles; Ollama 0.40.8; and the recorded image findings that remain open.
- Added an interactive nine-hunk example. It keeps model calls at zero, publishes an explicit `incomplete_source` result, commits only after publication, and exposes one logical stored row.
- Corrected API detail paths to the `result` envelope. Made diagnostic snippets bounded/read-only and kept the complete execution sequence in `docs/submission-demo.md` so shortened study excerpts do not omit setup, report capture or cleanup.
- Updated rehearsal and extension preparation. The extension has not yet been supplied; no hypothetical feature is represented as implemented.
- Preserved every embedded model transcript exactly. The 20 October observations predate final hardening and the Ollama image update, and remain labelled historical. No new live-model success is claimed.

The earlier pack and its verification record remain recoverable in Git history. The old `study-guide-verification.json` is deliberately unchanged; this refresh has its own [verification record](../evidence/study-guide-refresh-verification.json) and updated artifact checksums.

## How to check it

Prerequisites: a browser/PDF viewer for the pack; Docker Desktop, Make and uv for application checks. Run from the repository root. A cached cumulative run takes several minutes; first-use downloads/builds take longer. Model credentials are not needed.

1. Open `docs/phase-verification.md`: phases 0-6 are available, Phase 6 is implemented and the current gate is `make verify-phase-6` / `make test`.
2. Open `docs/study-guide/redpanda-study-companion.html` directly in a browser. Exercise all seven phase buttons. In **Trace an edit**, select **Nine-hunk edit** and advance to the last step: expect model calls 0, committed next input offset 1 and logical SQL rows 1. Restart it, then inspect successful assessment, invalid output, missing evidence, failed publication, crash/replay and database recovery.
3. In **Model evidence**, inspect both providers and the nine cases each. Confirm the historical-date notice, exact saved prompts/responses and no model invocation. In **Present**, navigate all 14 slides, Home/End and Full screen, and open a detailed chapter. Check desktop and narrow/mobile widths for clipping.
4. Open `docs/study-guide/redpanda-study-guide.pdf`: 36 pages, 34 chapters. Contents links lead to the named chapters. Review chapters 11/14 for evidence limits, 16 for database roles, 19 for current test counts, 21 for historical model results, 24-26 for demo/code inspection and 29-32 for security/rehearsal/extension.
5. Run the [demo guide's isolated free gate and helper cleanup](../submission-demo.md#2-run-the-free-verification-gate). It uses `make test`, an alias of `make verify-phase-6`. Expect 453 unit tests, 32 integration checks, 72 native Connect cases and 100% application line/branch coverage. Stop on an unexpected nonzero exit; inspect `reports/` and the guide's troubleshooting section. The guide also distinguishes expected fault handling from the intentionally red test.

Verify artifact identity without extra packages:

```sh
python3 - <<'PY'
import hashlib
import json
from pathlib import Path
root = Path('docs/study-guide')
for name, expected in json.loads((root / 'study-pack-checksums.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
print('PASS: study-pack checksums match')
PY
```

## Observed verification

The unchanged application at base `30510a8` passed local `make verify-phase-6` during this refresh: **453 unit, 32 integration and 72 Connect cases**, **1,172/1,172 lines and 286/286 branches**, zero missing/excluded lines, zero skips, zero emitted warnings. The integration portion took 271.13 seconds. Final Docker inspection found no remaining containers; no application profiles or retained data/model volumes were removed.

Browser automation passed all seven phases, seven traces (46 forward transitions), 18 provider/case views, ten rehearsal items and 14 slides at 1440/768/390/320-pixel widths. Full-screen controls stayed visible; embedded reports exactly match the committed source JSON. No page errors, unexpected network calls or horizontal page overflow were observed. All 36 PDF pages were rendered and visually reviewed; contents destinations and page bounds passed. Changed API/diagnostic pages were re-rendered after the final edits. Markdown file links, shell-block syntax, source targets, artifact hashes and unchanged README/assignment/application comparisons are checked separately.

Application coverage, artifact QA, model quality and vulnerability scans are separate evidence. This refresh made no real model calls, Wikipedia requests or new vulnerability scans. Follow the live-model sections of the demo guide before the actual screen-share, using your chosen configuration and fresh reports.

## Handover

Review the documentation diff and artifacts, then merge when satisfied. The original demo checkout must pull merged main before rehearsal. The [current prompt log](../ai-log/sessions/2026-10-22-walkthrough-refresh.md) records this requested refresh; it does not recreate previously omitted personal-README exchanges. Personal README editing remains outside this change.
