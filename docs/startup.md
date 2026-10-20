# Start and switch model modes

Use one command for the local model and one for the hosted frontier model:

```sh
./scripts/start-local.sh
./scripts/start-frontier.sh
```

Run one at a time. Each script selects its private profile, validates it, stops the currently configured stack while retaining named volumes, copies the selected profile over `.env`, and starts services in the background. You can run a script by absolute path from another directory. Docker/Compose 2.20+ must be installed and running; these launchers do not require host Python or uv.

## One-time setup on a fresh clone

Create each profile once without overwriting existing settings:

```sh
test -f .env.local || (umask 077; cp .env.local.example .env.local)
test -f .env.frontier || (umask 077; cp .env.frontier.example .env.frontier)
```

Edit `.env.frontier` in your editor and set `OPENAI_API_KEY` to your own key. The default frontier backend is OpenAI with `gpt-6.1-sol`; `LLM_MODEL` is configurable within the supported backend. An empty key fails the startup configuration check before `.env` or the existing stack is changed. This check validates configuration, not the key's authentication status or model access.

For local inference, `.env.local` defaults to containerized Ollama and `qwen2.5:7b`. Set both `LLM_MODEL` and `OLLAMA_MODEL` to the same tag when choosing another bundled model. Local startup may download weights; the README describes the measured hardware needs and hosted alternative.

| File | Purpose | In Git? |
|---|---|---|
| `.env.local.example` | Complete local-mode template, with an empty API key | Yes |
| `.env.frontier.example` | Complete OpenAI-mode template, with an empty API key | Yes |
| `.env.local` | Your local model settings | No |
| `.env.frontier` | Your frontier model settings and private API key | No |
| `.env` | Active copy, replaced on every successful selection | No |

Edit the **profile** when changing settings; edits made only to `.env` are replaced on the next launch. The resulting `.env` has owner-only read/write permissions. Profiles, temporary files, and `.env` are ignored by Git and excluded from the Docker build context. The launchers never execute dotenv contents as shell commands.

Keep `COMPOSE_PROJECT_NAME` and `POSTGRES_PASSWORD` identical in both profiles when reusing data. The examples use project `redpanda`, so switching keeps the same broker/database/model volumes. If you already have a configured stack, retain its project name, database password, and port in both profiles. This update prepared Damien's two profiles from his existing configuration and retained his key only in the frontier profile.

## What each command does

1. Find the repository from the script path and require the selected profile.
2. Acquire a lock to prevent concurrent mode switches. Copy the profile to a private temporary file so the configuration being validated is the one being installed.
3. Ask Compose to validate the file, then build/run the existing `model-check` tool with `triage check-config`. This makes **no model request**. Relevant inherited shell variables are cleared so they cannot silently override the chosen profile; Docker connection settings remain available.
4. If `.env` exists, stop its stack, including optional tool services, without removing named volumes. A failure here leaves `.env` unchanged.
5. Atomically replace `.env` with the selected configuration and start the corresponding Compose services. Remove temporary files and release the lock.

Local mode uses `docker-compose.yml`: Redpanda, Postgres, Connect, Ollama, and one-time topic/model initialization. Frontier mode uses `compose.infrastructure.yml`: Redpanda, Postgres, Connect, and topic initialization, with no Ollama container or local weight download. At Phase 2, ingestion runs but no reasoning worker calls a model automatically. Switching modes briefly stops ingestion; the existing public-stream gap limitations still apply.

`Started` means Compose started the services successfully. Local weights may still be downloading. Check initialization before sending a model smoke request:

```sh
docker compose ps -a
docker compose logs -f model-init  # bundled local mode only; wait for success
curl --fail http://127.0.0.1:4195/ready
```

Use your configured `CONNECT_PORT` if different. `topics` and `model-init` exiting with code 0 is normal. Readiness confirms Connect's input/output connection state, not model readiness or gap-free delivery.

An optional real model request remains explicit:

```sh
make smoke-model
```

In frontier mode this calls the paid API. Startup itself only validates the settings; it does not make this request. For native-host Ollama, use the README's optional manual path rather than the bundled-local startup profile.

To stop the current mode while retaining data and downloaded weights:

```sh
docker compose --profile tools down --remove-orphans
```

Do not add `--volumes` if you want to retain this stack's data. Launch either script to resume.

## Verify and troubleshoot

```sh
make test-startup UV='uvx --from uv==0.13.3 uv'
make verify-phase-2 UV='uvx --from uv==0.13.3 uv'
```

The focused target runs 13 launcher tests against a recording Docker boundary and two real Compose/profile contract tests. Assertions cover both modes, file copying and permissions, source-profile preservation, startup order, no volume deletion, inherited-variable isolation, missing profiles, preflight/shutdown/startup failure, concurrent execution, and working directories containing spaces. Native Compose tests establish the actual service/backend/model settings and rejection of an empty hosted key. The cumulative gate also keeps 100% Python application line and branch coverage; shell glue is verified through behavior tests rather than counted as Python coverage.

- **Missing profile:** follow the copy command in the error, then edit that profile.
- **Configuration or missing-key error:** correct the selected profile and rerun. Existing `.env` and services are unchanged when preflight fails.
- **Docker unavailable or build failure:** start Docker/check network access, then rerun. Initial tool-image/dependency downloads need internet.
- **Failure during `up`:** `.env` contains the attempted profile; inspect `docker compose ps -a` and `docker compose logs`, fix the issue, and rerun the same launcher. The script exits nonzero and does not print `Started` on failure. There is no automatic rollback of partially started containers.
- **Lock error:** wait for the other launcher. Only if no launcher is running (for example after a forced process kill), remove the empty lock directory with `rmdir .env.switch.lock` and retry.
- **Model still loading:** wait for successful `model-init` completion before `make smoke-model`; hosted mode avoids this download.

Verified implementation/tests: `d550e78`. The cumulative gate passed with 99 unit tests, 10 integration/configuration checks, 40 native Connect tests, and 176/176 Python lines plus 32/32 branches covered (zero missing/excluded lines). Both launchers ran successfully on Damien’s machine; local → frontier → local retained the migration record and downloaded model IDs, and local mode was left running. No paid model call was made.

Recorded verification and manual switch results are in [startup evidence](evidence/startup-launchers.json). See [Docker's variable precedence](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/) and [volume-preserving shutdown behavior](https://docs.docker.com/reference/cli/docker/compose/down/) for the underlying Compose semantics.
