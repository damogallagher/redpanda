.PHONY: help sync check test-unit test-foundation test-integration test-container test-connect test-startup verify-phase-1 verify-phase-2 verify-phase-3 inspect-enrichment test-enrichment smoke-enrichment smoke-model smoke-ingestion
.PHONY: verify-phase-4 test-reasoning demo-reasoning evaluate-development
UV ?= uv

help:
	@echo "make verify-phase-4  - cumulative reasoning and durable-delivery checks"
	@echo "make demo-reasoning  - inspect real broker results and failed-publication replay"
	@echo "make evaluate-development - six cases against the selected real model"
	@echo "make verify-phase-3  - cumulative checks plus revision enrichment and fixture inspection"
	@echo "make inspect-enrichment - print attributed before/after evidence, offline"
	@echo "make smoke-enrichment - fetch one public revision pair; no model calls"
	@echo "make verify-phase-2  - cumulative checks plus native Connect ingestion tests"
	@echo "make verify-phase-1  - repeatable checks; Docker required, no LLM/key needed"
	@echo "make test-unit       - offline unit tests with 100% line/branch coverage"
	@echo "make test-startup    - launcher behavior and local/frontier profile contracts"
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
	@for script in scripts/*.sh; do sh -n "$$script" || exit; done
	docker compose -f docker-compose.yml config --quiet
	docker compose -f compose.infrastructure.yml config --quiet

# --cov measures every production module, even if it was never imported.
test-unit: sync
	$(UV) run --frozen pytest -m 'not integration' --cov --cov-report=term-missing --cov-report=json:reports/coverage.json --cov-report=xml:reports/coverage.xml --junitxml=reports/unit.xml
	$(UV) run --frozen python -c 'import json; t=json.load(open("reports/coverage.json"))["totals"]; assert t["missing_lines"] == t["missing_branches"] == 0, t'

test-startup: sync
	$(UV) run --frozen pytest tests/test_launchers.py tests/test_startup_profiles.py --junitxml=reports/startup.xml

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
	$(UV) run --frozen pytest tests/test_live_ingestion.py -s --junitxml=reports/live.xml

# Use the installed wheel so inspection also checks the packaged CLI.
inspect-enrichment: sync
	$(UV) run --frozen --no-editable triage enrich --event tests/fixtures/enrichment/belle-event.json --fixture-response tests/fixtures/enrichment/belle-response.json

test-enrichment: sync
	$(UV) run --frozen pytest tests/test_enrichment.py tests/test_cli.py --junitxml=reports/enrichment.xml

verify-phase-3: check test-unit test-integration test-container test-connect inspect-enrichment
	@echo "PASS: Phase 3 enrichment checks. Live Wikipedia comparison is a separate check."

smoke-enrichment: sync
	$(UV) run --frozen pytest tests/test_live_enrichment.py -s --junitxml=reports/live-enrichment.xml

# Real broker, controlled HTTP/model boundaries; no model or API key required.
test-reasoning: sync
	$(UV) run --frozen pytest tests/test_reasoning.py tests/test_broker.py tests/test_worker.py tests/test_worker_integration.py --junitxml=reports/reasoning.xml

demo-reasoning: sync
	$(UV) run --frozen pytest tests/test_worker_integration.py -k '[valid] or result-replay' -s --junitxml=reports/reasoning-demo.xml

verify-phase-4: check test-unit test-integration test-container test-connect inspect-enrichment
	@echo "PASS: Phase 4 reasoning and durable-delivery checks. Live model evaluation is separate."

# Deliberate live calls using the selected profile. The model must already be ready.
evaluate-development:
	@mkdir -p reports
	docker compose build model-check
	docker compose run --rm --no-deps -v "$(CURDIR)/tests/fixtures:/fixtures:ro" model-check python /fixtures/development/evaluate.py > reports/development.json
	@echo "PASS: six development cases; prompts, responses and outcomes in reports/development.json"
