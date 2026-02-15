# Phase 1: Infrastructure Plan

## Overview

Infrastructure setup happens in Step 1 and provides the foundation for all subsequent steps: Python packaging, test runner configuration, linting, type checking, and build targets.

## Python Packaging

### nemlib (libs/nemlib-py/pyproject.toml)

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "nemlib"
version = "0.1.0"
description = "NEM shared library: parser, type system, device model, validation"
requires-python = ">=3.10"
# Zero runtime dependencies — pure Python library

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
    "pyyaml>=6.0",       # For opcode registry loading
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

Note: `pyyaml` is listed as dev dependency since the opcode registry (opcodes.yaml) is loaded at runtime. If tools need it at runtime, promote to a regular dependency. Alternatively, use a JSON copy of the registry to avoid the YAML dependency.

### Interpreter (tools/interpreter/pyproject.toml)

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "neminterp"
version = "0.1.0"
description = "NEM reference interpreter"
requires-python = ">=3.10"
dependencies = [
    "nemlib",
    "numpy>=1.24",
    "scipy>=1.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

### Development Install

Both packages installed in editable mode from the repo root:

```bash
pip install -e libs/nemlib-py[dev]
pip install -e tools/interpreter[dev]
```

## Makefile

Top-level Makefile at repo root:

```makefile
.PHONY: install test test-nemlib test-interpreter test-conformance lint typecheck clean

install:
	pip install -e libs/nemlib-py[dev]
	pip install -e tools/interpreter[dev]

test: test-nemlib test-interpreter test-conformance

test-nemlib:
	pytest libs/nemlib-py/tests/ -v

test-interpreter:
	pytest tools/interpreter/tests/ -v

test-conformance:
	pytest tests/conformance/ -v

test-conformance-validation:
	pytest tests/conformance/ -k "not execution" -v

test-conformance-execution:
	pytest tests/conformance/execution/ -v

lint:
	ruff check libs/nemlib-py/ tools/interpreter/ tests/
	ruff format --check libs/nemlib-py/ tools/interpreter/ tests/

typecheck:
	mypy libs/nemlib-py/nemlib/
	mypy tools/interpreter/neminterp/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
```

## CI Configuration

Deferred to when GitHub Actions are set up. The Makefile targets serve as CI steps:

1. `make install` — install packages
2. `make lint` — ruff check + format check
3. `make typecheck` — mypy
4. `make test` — all tests

## Directory Conventions

```
libs/
  nemlib-py/
    pyproject.toml
    nemlib/                     # Source package (Python, Phase 1)
    tests/                      # nemlib unit tests

tools/
  interpreter/
    pyproject.toml
    neminterp/                  # Source package
    tests/                      # Interpreter unit tests

tests/
  conformance/                  # Shared conformance tests (both tiers)

plan/
  phase_1/                      # This plan

Makefile                        # Top-level build/test targets
```

## Python Version

Python 3.10+ required for:
- `match` statements (optional, but available)
- `X | Y` union type syntax
- `dataclass(frozen=True, slots=True)` with `kw_only`
- `typing.Protocol` without `typing_extensions`

## Opcode Registry Loading

The opcode registry at `spec/registry/opcodes.yaml` needs to be loadable at runtime by nemlib. Options:

1. **PyYAML dependency**: Add `pyyaml` as runtime dependency of nemlib. Simple but adds external dependency.
2. **JSON mirror**: Generate a JSON copy of the registry during development; load JSON at runtime (stdlib `json`). Zero dependencies.
3. **Vendored YAML parser**: Small YAML subset parser for the registry format.

**Recommendation**: Option 1 (PyYAML) for simplicity. The registry is loaded once at initialization. If zero-dependency is critical, Option 2 with a generation script.
