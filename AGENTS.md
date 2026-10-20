# Working on this exercise

- Read `docs/progress.md` and the relevant `docs/phases/` record before continuing. Work only on the phase the user has requested. Create its branch from merged main and open a PR; Damien reviews and merges.
- Keep code small and explicit. Run `make verify-phase-3` for the current cumulative gate (`make verify-phase-1` retains foundation checks); add later phase targets as implemented. All first-party application Python modules must retain 100% line and branch unit coverage without exclusions. Runtime/infrastructure evidence is separate from coverage.
- Keep the original assignment unchanged. Damien writes the personal README sections independently; do not fill them in with AI-authored prose.
- Append visible user prompts, clarification answers, and assistant responses to the session log under `docs/ai-log/sessions/`. Preserve wording; explicitly mark any sensitive-data redaction. Do not log secrets, hidden reasoning, system/developer instructions, or raw credential-bearing tool output.
- Record what changed, exact test commands, expected versus observed behavior, tested commit, limitations, and next step in the phase record. Do not call a planned command available or a skipped check passed.
- `.env` is untracked and must never enter commits or the Docker build context. Real hosted model checks incur a charge; deterministic tests must use stubs and no credentials. Never silently change providers.
- Test cleanup may remove only resources created for that test. Preserve user data/model volumes and existing work. After the initial user-requested reset, do not rewrite main or force-push phase history.
