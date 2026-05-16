.PHONY: install install-dev test lint clean help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install       Install hermes-voice from source"
	@echo "  install-dev   Install in editable mode with dev deps"
	@echo "  test          Run tests"
	@echo "  lint          Check code style"
	@echo "  clean         Remove build artifacts and caches"

install:
	pip install .

install-dev:
	pip install -e .

test:
	python -m pytest tests/ -q

lint:
	python -m pip install -q ruff
	python -m ruff check src/ tests/
	python -m ruff format --check src/ tests/

clean:
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
