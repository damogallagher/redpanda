.PHONY: help sync check test-unit test-foundation test-integration test-container test-connect verify-phase-1 verify-phase-2 smoke-model smoke-ingestion
UV ?= uv

help:
	@echo "make verify-phase-2  - cumulative checks plus native Connect ingestion tests"
	@echo "make verify-phase-1  - repeatable checks; Docker required, no LLM/key needed"
	@echo "make test-unit       - offline unit tests with 100% line/branch coverage"
	@echo "make test-foundation - Phase 1 broker/database checks only"
	@echo "make test-integration - isolated broker/database tests and cleanup"
	@echo "make smoke-model     - one real model call; selected backend must be ready"
	@echo "make smoke-ingestion - isolated 30-second public-feed check; no model calls"

sync:
	$(UV) sync --frozen

check: sync
	$(UV) run --frozen ruff check src tests
	$(UV) run --frozen ruff format --check src tests
	$(UV) run --frozen mypy src
	docker compose -f docker-compose.yml config --quiet
	docker compose -f compose.infrastructure.yml config --quiet

# --cov measures every production module, even if it was never imported.
test-unit: sync
	$(UV) run --frozen pytest -m 'not integration' --cov --cov-report=term-missing --cov-report=json:reports/coverage.json --cov-report=xml:reports/coverage.xml --junitxml=reports/unit.xml
	$(UV) run --frozen python -c 'import json; t=json.load(open("reports/coverage.json"))["totals"]; assert t["missing_lines"] == t["missing_branches"] == 0, t'

test-foundation: sync
	$(UV) run --frozen pytest tests/test_infrastructure.py tests/test_postgres_upgrade.py --junitxml=reports/integration.xml

test-integration: sync
	$(UV) run --frozen pytest -m 'integration and not live' --junitxml=reports/integration.xml

test-container:
	docker compose --env-file /dev/null -f compose.infrastructure.yml build model-check
	docker compose --env-file /dev/null -f compose.infrastructure.yml run --rm --no-deps \
		-e LLM_BACKEND=ollama -e LLM_MODEL=qwen2.5:7b -e LLM_BASE_URL=http://ollama:11434 \
		-e LLM_TIMEOUT_SECONDS=120 -e LLM_MAX_TOKENS=1024 -e OPENAI_API_KEY= \
		model-check triage check-config

verify-phase-1: check test-unit test-foundation test-container
	@echo "PASS: Phase 1 deterministic checks. Real model smoke is a separate check."

test-connect:
	docker compose --env-file /dev/null -f compose.infrastructure.yml run --rm --no-deps connect lint /config/ingest.yaml
	docker compose --env-file /dev/null -f compose.infrastructure.yml run --rm --no-deps connect test /config/ingest_test.yaml

verify-phase-2: check test-unit test-integration test-container test-connect
	@echo "PASS: Phase 2 ingestion checks. Live source smoke is a separate check."

smoke-model:
	docker compose run --build --rm --no-deps model-check

smoke-ingestion: sync
	$(UV) run --frozen pytest -m live -s --junitxml=reports/live.xml
