---
paths:
  - "tests/conformance/**"
  - "tests/fixtures/**"
---

# Conformance Tests

## Ownership

Conformance test **infrastructure** (runner protocol, fixtures, conftest) is owned by the shared agent. Test **cases** are defined by the integration agent and wired by the shared agent.

Tool agents may add tests to `tests/conformance/**` (prefer additive edits, use tool-namespaced subdirectories to avoid merge conflicts).

## Architecture

Testing uses a two-tier conformance architecture with a pluggable runner protocol:

| Tier | Purpose | Tests against |
|------|---------|--------------|
| **Validation** | Is this NEM source accepted/rejected? | All validation-capable runners |
| **Execution** | Given inputs, does execution produce correct outputs? | Only execution-capable runners |

### Runner Capability Model

| Runner | validate | execute | When available |
|--------|:--------:|:-------:|----------------|
| nemlib-py | Yes | No | Phase 2+ |
| nemlib-cpp | Yes | No | Phase 2+ |
| interpreter | Yes | Yes | Phase 1+ |
| pipeline | Yes | Yes | Future |

### Cross-Implementation Tests (Phase 2)

When both nemlib implementations are available, `tests/conformance/cross_impl/` compares their behavior directly — AST structural agreement and diagnostic consistency.

## Key Files

- `tests/conformance/runner.py` — ConformanceRunner protocol, ValidationResult, ExecutionResult
- `tests/conformance/conftest.py` — Runner fixtures (`validation_runner`, `execution_runner`)
- `tests/conformance/runners/` — Runner implementations

## References

See `plan/phase_1/tests.md` for the full test plan.
