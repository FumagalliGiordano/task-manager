# Makefile — Shortcut per la test suite
# Utilizzo: make <target>

.PHONY: test test-unit test-integration test-concurrency test-regression coverage help

# ─── Default ──────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make test              → Esegui tutta la suite"
	@echo "  make test-unit         → Solo unit test"
	@echo "  make test-integration  → Solo integration test"
	@echo "  make test-concurrency  → Solo concurrency test"
	@echo "  make test-regression   → Solo regression test"
	@echo "  make coverage          → Suite completa + report HTML coverage"
	@echo "  make fast              → Suite senza test lenti (parallelo x4)"
	@echo ""

# ─── Suite completa ───────────────────────────────────────────────────────────

test:
	pytest tests/ -v

# ─── Per layer ────────────────────────────────────────────────────────────────

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-concurrency:
	pytest tests/concurrency/ -v -s

test-regression:
	pytest tests/regression/ -v

# ─── Coverage ─────────────────────────────────────────────────────────────────

coverage:
	pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "📊 Report HTML: coverage_html/index.html"

# ─── Rapido (CI-friendly) ─────────────────────────────────────────────────────

fast:
	pytest tests/ -n 4 --ignore=tests/concurrency/ -q
