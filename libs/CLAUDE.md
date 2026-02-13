## Role

The libs agent builds the **shared library (nemlib)** used by all NEM tools, plus test infrastructure and build configuration.
Correctness, API clarity, and zero runtime dependencies take precedence over performance.

You MAY modify code under the following paths:
- `libs/**`
- `tests/conformance/runner.py`, `tests/conformance/conftest.py`, `tests/conformance/runners/**`
- `tests/conformance/` test files (wiring test stubs to call `runner.validate()` / `runner.execute()`)
- Root `Makefile`
- Root-level `pyproject.toml` files (if any)

You MUST NOT modify:
- `spec/**`
- `docs/contracts/**`
- `tools/**`

You MUST comply with guidelines defined in @work_instructions.md and also enforce engineering process defined in the engineering directory, using @docs/engineering/README.md as an entry point.

## Development Plan

Follow the Phase 1 incremental plan in `plan/phase_1/`:
- `plan/phase_1/master.md` — overall plan and your step-by-step responsibilities
- `plan/phase_1/libs.md` — nemlib modules to build per step
- `plan/phase_1/tests.md` — conformance test architecture you own
- `plan/phase_1/infra.md` — packaging and build configuration
- `plan/phase_1/integration.md` — completion criteria per step

## Architecture

nemlib follows a 6-layer dependency model (see `docs/architecture/common-infrastructure.md`):
1. `diagnostics/` — Layer 0 (zero internal dependencies)
2. `core/` — Layer 1 (depends on diagnostics)
3. `parser/` — Layer 2 (depends on core, diagnostics)
4. `device/` — Layer 3 (depends on parser, core, diagnostics)
5. `types/` — Layer 4 (depends on core, device, diagnostics)
6. `validation/` — Layer 5 (depends on all above)

**Layer dependency rule**: A module may only import from its own layer or lower layers.

## Git Workflow

- Branch: `agent/libs/main`
- Feature branches: `agent/libs/feat/step-N-<description>`
- PRs target `integration/main` — the integration agent reviews and merges
