# Submission demo walkthrough — 20 October 2026

Context: PR #11 merged as `2b8b62c`; documentation follow-up. Commands are supplied for Damien to run; the assistant does not execute resets or paid inference during this turn.

## User

I've merged PR #11. Can you walk me through a clean end-to-end demo using Ollama, then a frontier model, with the exact commands and expected results so I can verify everything before submitting?

## Assistant

> I’ll check the merged instructions and scripts, then give you an exact walkthrough for a clean Ollama demo followed by the frontier model, including expected results and how to diagnose failures.

## Assistant

> Your checkout is already on the merged main branch. I’ll use a three-edit demo for each provider, with a data reset between runs so old results cannot be mistaken for new ones. The walkthrough will separate fixed-case model tests from live Wikipedia processing, since live edits can legitimately produce an abstention.

## Assistant

> The walkthrough now includes a clear pass/fail check for each stage. A three-edit hosted demo plus its fixed-case evaluation is capped at 40 paid calls per attempt. It also shows how to save separate reports and inspect full result details, so a completed worker is not mistaken for proof that all three results reached Postgres.
