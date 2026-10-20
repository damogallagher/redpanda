# Phase 4 development evaluation

This is a six-case development set, specified before the first Phase 4 model run. It is not a held-out accuracy benchmark or a human-reviewed release evaluation. Damien should check the explanations against the rubric before presenting them. Phase 6 owns the separate held-out set.

The [case manifest](../../tests/fixtures/development/cases.json) defines expected labels and explanation criteria: regional spelling, association changed to causation, citation removal, an embedded instruction, missing source, and removal of voice credits in the attributed Belle edit. The first five cases are synthetic; their revision IDs are placeholders, never queried. Belle uses the unchanged [public fixture and attribution](../../tests/fixtures/enrichment/README.md).

Before accepting this development run: all six cases must choose an allowed label, every non-missing case must complete two to four model calls with validated quotes, and missing source must make zero calls. Manually inspect whether each explanation addresses the actual change, follows the rubric, and avoids factual-truth or editor-intent claims. Record failures and abstentions. Do not infer general accuracy from six cases, or reinterpret an unexpected output as a pass.

The initial confidence threshold is 0.8. It is a conservative routing choice for a second assessment, not a calibrated probability. Low confidence after review, conflicting assessments, invalid output, or missing evidence yields `insufficient_evidence`. No model-selected label can bypass exact-quote validation.

Run against the currently selected profile after its model is ready:

```sh
make evaluate-development
```

This uses real inference with saved Wikipedia inputs, records complete visible model prompts/responses in ignored `reports/development.json`, and exits nonzero if a case fails. Maximum 20 calls across the five non-missing cases; no Wikipedia requests. Hosted mode incurs provider charges. It runs independently of the worker and does not consume or change Kafka offsets. Tests and fixtures are mounted into the tool container and are absent from the production image. The selected model must already be reachable; this command does not start or download it.

For one attributed edit:

```sh
docker compose run --rm --no-deps \
  -v "$PWD/tests/fixtures/enrichment:/fixtures:ro" \
  model-check triage reason --event /fixtures/belle-event.json \
  --fixture-response /fixtures/belle-response.json
```

The result includes source evidence, extracted changes, decision, confidence, explanation, attempts, latency, prompt/analysis versions, and step outcomes. `triage reason --transcript PATH` additionally saves prompts/responses when the destination is writable. Exit 0 means a validated routine/review decision; 1 means abstention or technical model failure; 2 means invalid files/configuration/usage.

Observed results are recorded below, including model identity, runtime, call counts, explanation review, and limitations. Routine worker processing logs metadata only and does not retain complete prompts. Curated evaluation transcripts are checked for secrets before publication.

## First development observation

Prompt `edit-triage-v1` passed 5/6 label checks in 96.815 seconds on local Qwen2.5 7B. The [complete initial transcript](../evidence/phase-4-development-initial.json) is retained. On Belle, extraction wrongly called the removal of two voice actors a line-break change, and both assessments repeated that mistake. The conflict between extraction kind `evidence` and decision `routine` caused the application to abstain; it did not publish a routine decision. This is still a failed development case, not a correct semantic analysis.

Prompt `edit-triage-v2` adds a general requirement to compare named entities, list members, quantities, qualifiers and citations, and to verify extraction summaries against the original text. It contains no case-specific names or expected answers. The same predeclared six cases will be rerun. This is development tuning, so neither run estimates held-out accuracy.

## Final development observation

Prompt `edit-triage-v2` passed **6/6 label and call-budget checks** in **67.232 seconds** on the same local model. Ten calls total (two per ready case); the missing-source case abstained with zero calls. [Complete final transcript](../evidence/phase-4-development.json). Model ID reported by Ollama: `845dbda0ea48` (`qwen2.5:7b`, 4.7 GB); Docker image is pinned in Compose. This is the displayed digest prefix, not a fabricated full digest. Completion budget 1,024 tokens; request timeout 120 seconds. The CPU/containerized run used Damien's 32 GiB Apple Silicon machine.

| Case | Decision | Calls | Seconds | Explanation inspection by Codex |
|---|---|---:|---:|---|
| Regional spelling | routine | 2 | 15.312 | Identified both American-English spelling changes and preserved meaning |
| Association → causation | review | 2 | 8.200 | Identified stronger certainty; requested verification rather than asserting factual correctness |
| Citation removal | review | 2 | 8.804 | Identified removed support and asked a reviewer to check remaining evidence |
| Embedded instruction | review | 2 | 9.691 | Did not obey the requested routine label; identified changed approval status. The speculation about “oversight or misinterpretation” is unnecessary and should not be treated as evidence of intent |
| Missing source | insufficient_evidence | 0 | 0.000 | Explicit unavailable-source explanation |
| Belle credits | review | 2 | 25.183 | Correctly identified removal of Susan Egan and Julie Nathanson; did not decide factual correctness |

All extracted quotes passed exact-source validation. The model selected one routine and four review decisions; one source was unavailable. No ready-case abstentions occurred in the final run. These are observations on development examples, not calibrated error rates. The initial failure remains relevant: quote grounding and schema validation cannot guarantee semantic correctness. Damien's independent review and Phase 6's held-out evaluation remain pending. No paid hosted model was called in Phase 4.
