#!/bin/sh
# Shared implementation; dotenv files are parsed by Compose, never executed as shell.
set -eu
umask 077

if [ "$#" -ne 1 ]; then
    echo "Usage: scripts/start-local.sh or scripts/start-frontier.sh" >&2
    exit 2
fi
case "$1" in
    local|frontier) mode=$1 ;;
    *) echo "Unknown mode: choose local or frontier." >&2; exit 2 ;;
esac
cd "$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
profile=".env.$mode"
if [ ! -f "$profile" ]; then
    echo "Missing $profile. Copy $profile.example to $profile and edit its settings." >&2
    exit 1
fi

# The profile is authoritative; an exported variable must not silently change mode,
# project, credentials, or ingestion settings. Docker connection settings are retained.
unset COMPOSE_FILE COMPOSE_PROJECT_NAME COMPOSE_PROFILES COMPOSE_ENV_FILES \
    COMPOSE_DISABLE_ENV_FILE COMPOSE_PATH_SEPARATOR \
    LLM_BACKEND LLM_MODEL LLM_BASE_URL LLM_TIMEOUT_SECONDS LLM_MAX_TOKENS OPENAI_API_KEY \
    OLLAMA_MODEL POSTGRES_PASSWORD CONNECT_PORT KAFKA_BROKERS KAFKA_GROUP_ID WORKER_MAX_ITEMS \
    INGEST_STREAM_URL INGEST_RECONNECT INGEST_SOURCE INGEST_SAMPLE_ALL \
    API_PORT SINK_PORT SINK_GROUP_ID PGHOST PGPORT PGPASSWORD

if ! mkdir .env.switch.lock 2>/dev/null; then
    echo "Another startup holds .env.switch.lock. Wait for it to finish." >&2
    exit 1
fi
temporary=
cleanup() {
    [ -z "$temporary" ] || rm -f "$temporary"
    rmdir .env.switch.lock
}
trap cleanup 0
trap 'exit 130' INT
trap 'exit 143' TERM HUP

# Snapshot the selected profile and validate it before stopping the current stack.
temporary=$(mktemp .env.switch.XXXXXX)
cp "$profile" "$temporary"
chmod 600 "$temporary"
docker compose --env-file "$temporary" config --quiet
docker compose --env-file "$temporary" run --build --rm --no-deps model-check triage check-config

if [ -f .env ]; then
    # Include optional tools when stopping; keep every named data/model volume.
    docker compose --env-file .env --profile tools down --remove-orphans
fi
mv -f "$temporary" .env
temporary=
docker compose --env-file .env up --build -d --remove-orphans
printf 'Started %s mode using %s -> .env.\n' "$mode" "$profile"
echo 'The selected profile controls the batch size; model calls begin when evidence is ready.'
echo 'Inspect services: docker compose ps -a'
if [ "$mode" = local ]; then
    echo 'Wait for model initialization: docker compose logs -f model-init'
fi
