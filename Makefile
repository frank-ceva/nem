.PHONY: install test test-nemlib test-interpreter test-conformance lint typecheck clean

# Install nemlib in editable mode with dev dependencies
install:
	pip install -e libs/nemlib-py[dev]

# Run all tests
test: test-nemlib test-conformance

# Run nemlib unit tests only
test-nemlib:
	python -m pytest libs/nemlib-py/tests/ -v

# Run interpreter tests (placeholder — will be added later)
test-interpreter:
	@echo "Interpreter tests not yet available"

# Run conformance tests
test-conformance:
	python -m pytest tests/conformance/ -v

# Run ruff linter on nemlib
lint:
	ruff check libs/nemlib-py/nemlib/
	ruff format --check libs/nemlib-py/nemlib/

# Run mypy type checking on nemlib
typecheck:
	mypy libs/nemlib-py/nemlib/

# Clean build artifacts and caches
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
