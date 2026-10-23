# Model acceptance rubric

The rubric is used by the current model-test scripts. The observations below are historical 20 October 2026 runs, before later evidence-limit/security changes and the Ollama image update. Use the [current demo guide](../submission-demo.md) to evaluate your selected configuration.

The nine synthetic cases in `tests/fixtures/acceptance/cases.json` were frozen before the first Phase 6 model run. They were not used for the Phase 4 prompt tuning. Seven ready comparisons require the exact declared decision, valid grounded output and two to four calls; two unavailable/empty comparisons require abstention with zero calls. Maximum: 28 calls per run. Technical provider failure stops the run early and fails it; a wrong decision fails the case but the remaining cases continue.

The rubric covers punctuation, reordered facts, reversed negation, changed study population, removed attribution, replaced supporting citation, and two distinct hunks. These are small acceptance examples, not a statistical accuracy benchmark. The program checks decisions, grounding and budgets; read explanations against the per-case rubric as well. No automated judge is used. Damien's independent review is still required.

Run `make test-local` or `make test-frontier`. Each reads its private profile, leaves active `.env` unchanged, saves all visible prompts/responses to ignored `reports/model-local.json` or `reports/model-frontier.json`, and exits nonzero on failure. Only curated synthetic material is evaluated; there are no Wikipedia requests or Kafka writes. Frontier runs incur charges. Repeated runs are regression checks, no longer unseen tests for that model. Never change expected labels just to turn a failure green.

Production prompts remain `edit-triage-v2`. Frozen rubric commit: `f5f132a`. Both first evaluations used the Phase 6 evaluator implementation subsequently committed in `634467e` (formatting/type-only fixes afterward); no model prompt or case label changed.

## First real runs — 20 October 2026

| Provider/model | Passed | Calls | Evaluation time |
|---|---|---|---|
| local / `qwen2.5:7b` | 9/9 | 14 | 135.6 s |
| frontier / `gpt-6.1-sol` | 9/9 | 14 | 46.662 s |

Both runs produced two calls per ready case and zero per abstention case, with no repair/retry. On this small set there were zero false alarms among two routine cases and zero missed review labels among five substantive cases. Both abstention cases passed. These are counts, not a general accuracy estimate.

Codex inspected the explanations and grounded extractions against the rubrics: all substantive changes were identified; the two-hunk extraction covered both changes. Local wording sometimes discusses a source's credibility more broadly than the narrower hosted explanation; neither run establishes external factual truth. This is an AI-assisted inspection, not Damien's independent human signoff. More realistic ambiguous/adversarial cases would be required before operational use; the development set and deterministic tests additionally cover embedded instructions and uncertainty.

Full synthetic prompts, visible responses, model metadata, and outcomes: [Ollama](../evidence/phase-6-model-local.json), [frontier](../evidence/phase-6-model-frontier.json). The local downloaded model digest is recorded in the fresh-start evidence. These first-run reports remain unchanged when later regression checks run. Maximum output budget was 1,024 tokens/call; cost in currency was not measured.

After the runtime image was hardened (commit `7fc26f1`), one additional hosted smoke request passed in 2.631 seconds. This verifies the real provider/TLS path on the new base, not another quality evaluation. [Visible smoke prompt/response](../evidence/phase-6-frontier-hardened-smoke.json). Total Phase 6 hosted requests: 15.

## Live-feed quality is separate

The fresh-start observation on the image hardened during Phase 6 produced three `insufficient_evidence` results, all after invalid extraction output (two attempts each). It verified safe abstention/delivery but **zero successful semantic assessments** in that sample. The earlier public-feed observation produced two routine and one review result. Both are retained in the Phase 6 record; neither is a representative accuracy estimate. The small nine-case success should not be extrapolated to large, messy Wikipedia diffs. No prompt tuning or expected-label changes were made to erase this limitation.
