# 20 October 2026 — Local/frontier startup profiles

Follow-up on open Phase 2 PR #6, branch `phase/02-ingestion`.
Visible user/assistant messages are preserved in order. Tool activity and verification outcomes are recorded in the startup guide/evidence. No secrets or raw environment contents are included.

## 01. User

Also, lets create a script for starting the application / applications against a local model and a script to run against a frontier model. Have a .env for local and a .env for frontier. Does this make sense? When we execute the script, it copies the correct .env file to overwrite .env. make this work for me and update the documentation accordingly

## 02. Assistant

I’ll add local and frontier startup scripts that copy the selected configuration over `.env` and start the matching services. I’ll preserve your existing credentials, keep both configuration files out of Git, and document how to switch modes.

## 03. Assistant

I’ll add this to the open Phase 2 PR. Each launcher will validate the selected profile, stop the current stack while retaining its data and model volumes, replace `.env`, and start the chosen mode. Frontier startup will check the configuration without making a paid model request.

## 04. Assistant

The launcher checks pass, including missing-profile errors, failed validation, concurrent starts, and paths containing spaces. Shell variables also can’t silently override the selected profile. I’m now preparing your private profiles and testing both modes against Docker using your existing model and data volumes.

## 05. Assistant

Both modes started successfully on your machine. Frontier mode ran without Ollama, and the database migration record survived the switch. The full suite also passes: 99 unit tests, 10 integration/configuration checks, 40 native Connect tests, and 100% Python coverage. I’m restoring local mode and finishing the documentation and prompt log.

## 06. Assistant

PR #6 now includes the startup scripts and guide. Your private profiles are configured, your existing key is retained in `.env.frontier`, and local mode is running again. I’m checking the updated PR’s Linux CI result before the handover.

## 07. Assistant — final response

Done—added to [PR #6](https://github.com/damogallagher/redpanda/pull/6).

From your repository:

- **Local:** `./scripts/start-local.sh` copies `.env.local` over `.env`.
- **Frontier:** `./scripts/start-frontier.sh` copies `.env.frontier` over `.env`.

Both validate the configuration and start the matching services while preserving data and model volumes. Your private profiles are configured, including your existing frontier API key.

I tested both modes and left **local mode running**. All checks and GitHub CI passed; **100% Python line and branch coverage** is retained.

The [startup guide](https://github.com/damogallagher/redpanda/blob/phase/02-ingestion/docs/startup.md) covers setup, switching, and troubleshooting. Documentation and our prompt log are updated; the PR remains unmerged.
