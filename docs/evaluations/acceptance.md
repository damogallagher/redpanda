# Model acceptance rubric

The nine synthetic cases in `tests/fixtures/acceptance/cases.json` were frozen before the first Phase 6 model run. They were not used for the Phase 4 prompt tuning. Seven ready comparisons require the exact declared decision, valid grounded output and two to four calls; two unavailable/empty comparisons require abstention with zero calls. Maximum: 28 calls per run. Technical provider failure stops the run early and fails it; a wrong decision fails the case but the remaining cases continue.

The rubric covers punctuation, reordered facts, reversed negation, changed study population, removed attribution, replaced supporting citation, and two distinct hunks. These are small acceptance examples, not a statistical accuracy benchmark. The program checks decisions, grounding and budgets; read explanations against the per-case rubric as well. No automated judge is used. Damien's independent review is still required.

Run `make test-local` or `make test-frontier`. Each reads its private profile, leaves active `.env` unchanged, saves all visible prompts/responses to ignored `reports/model-local.json` or `reports/model-frontier.json`, and exits nonzero on failure. Only curated synthetic material is evaluated; there are no Wikipedia requests or Kafka writes. Frontier runs incur charges. Repeated runs are regression checks, no longer unseen tests for that model. Never change expected labels just to turn a failure green.

First-run evidence and observations will be appended after execution. Production prompts remain `edit-triage-v2`.
