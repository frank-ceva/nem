# Phase 1: Integration and Validation Plan

## Overview

This document defines how to validate cross-component consistency at each step and the completion criteria for the phase.

## Per-Step Completion Criteria

### Step 1: Infrastructure + Lexer + Constants

| Criterion | Verification |
|-----------|-------------|
| nemlib installs | `pip install -e libs/nemlib-py[dev]` succeeds |
| Interpreter installs | `pip install -e tools/interpreter[dev]` succeeds |
| Lexer tokenizes all examples | Unit test: lex each .nem file, no errors |
| Const parser works | Unit test: parse const blocks from all 5 examples |
| Const evaluator works | Unit test: evaluate expressions (arithmetic, mod, parens) |
| Conformance infra works | `pytest tests/conformance/const/ -v` — 32 cases pass |
| Lint clean | `make lint` — zero violations |
| Type check clean | `make typecheck` — zero errors |

### Step 2: Storage Declarations + Memory Model

| Criterion | Verification |
|-----------|-------------|
| Buffer/region parser | Parse full declarations from all 5 example programs |
| Memory model | Allocate buffers at DDR/L2/L1 with alignment |
| Region views | Construct typed regions, verify read/write round-trip |
| Quant descriptor parsing | Parse all 3 quant forms (per_tensor, per_channel, per_group) |
| Tests pass | `make test` — all tests green |

### Step 3: Data Movement + Execution Engine

| Criterion | Verification |
|-----------|-------------|
| Task parser | Parse all task forms from examples (transfer, store, wait) |
| Inline regions | Parse `src=region(...)` inline expressions |
| Task graph | Construct DAG from parsed tasks |
| Execution | Execute synthetic transfer program, verify byte-level copy |
| First execution conformance | `pytest tests/conformance/execution/transfer_basic/` passes |
| Tests pass | `make test` |

### Step 4: Loops + Pipelining

| Criterion | Verification |
|-----------|-------------|
| Loop parser | Parse loop/endloop with @max_in_flight |
| Loop execution | Iterate with variable binding |
| Max-in-flight | Enforce concurrency limit |
| Ping-pong | Verify `(i mod 2)` indexing produces correct offsets |
| All examples parse+execute | All 5 .nem examples execute (compute = placeholder output) |
| Tests pass | `make test` |

### Step 5: Compute Operations

| Criterion | Verification |
|-----------|-------------|
| Compute parser | Parse all compute task forms (opcode.async, in/out, attrs) |
| Registry loader | Load opcodes.yaml, query by opcode name |
| All elementwise ops | Per-op unit tests with known data |
| GEMM | Verify against np.matmul + bias |
| Conv2D | Verify against reference implementation |
| End-to-end | `conv2d_relu.nem` and `gemm_bias_relu.nem` produce correct output |
| Execution conformance | `pytest tests/conformance/execution/conv2d_relu/` passes |
| Tests pass | `make test` |

### Step 6: Device Configuration + Registry

| Criterion | Verification |
|-----------|-------------|
| Device config parser | Parse full device config grammar |
| Include resolution | Load `npm_baseline_1.0.nem` via `include` directive |
| Inheritance | Resolve `npm_lite_ extends nem_baseline_1_0` |
| Effective set | Compute correct effective type family set |
| Memory sizes | Extract l1_size_bytes, l2_size_bytes from topology |
| Conformance | `pytest tests/conformance/device_config/` + `registry/` — all pass |
| Tests pass | `make test` |

### Step 7: Remaining Opcodes + Type Extensions

| Criterion | Verification |
|-----------|-------------|
| All stable opcodes | Per-op unit tests for pooling, norm, softmax, layout, cast, quant/dequant |
| INT4 compute | i4 x i8 GEMM and Conv2D |
| Per-group quant | Dequantize with per-group descriptors |
| FLOAT attributes | epsilon, alpha parsed and used in normalization/leaky_relu |
| All examples correct | All 5 .nem examples produce correct numeric output |
| Execution conformance | All execution tier tests pass |
| Validation conformance | opcodes/ and types/ tests pass |
| Tests pass | `make test` |

### Step 8: Semantic Analysis + Decorators

| Criterion | Verification |
|-----------|-------------|
| Type family matching | All MUST and MAY variants matched correctly |
| Validation pipeline | All 10 passes implemented and tested |
| Error programs rejected | Invalid programs produce correct error diagnostics |
| Decorator enforcement | @materialized, @readonly, @writeonly enforced during execution |
| @resource validation | SEQ, sDMA, WDM rejected as targets |
| All conformance tests | `pytest tests/conformance/ -v` — all pass |
| Full test suite | `make test` — all green |
| Lint + type check | `make lint && make typecheck` — zero issues |

## Phase 1 Definition of Done

All of the following must be true:

1. **All conformance tests pass**: Both validation and execution tiers
2. **All unit tests pass**: nemlib and interpreter
3. **All 5 example programs execute correctly**: Verified by execution conformance tests
4. **Device configs resolve**: npm_baseline_1.0 + npm_lite_ load and resolve correctly
5. **Invalid programs rejected**: Programs violating spec rules produce diagnostics
6. **Type checking clean**: `mypy` reports zero errors
7. **Linting clean**: `ruff` reports zero violations
8. **Runner extensible**: PipelineRunner can be added later by implementing ConformanceRunner protocol
9. **Documentation updated**: work_history.md updated, spec-int-work.md updated

## Cross-Component Validation Points

### nemlib ↔ Interpreter

| Validation Point | How |
|-----------------|-----|
| Parser produces correct AST | Interpreter can execute programs parsed by nemlib |
| Expression evaluator handles loop vars | Interpreter binds loop variable, nemlib evaluator resolves |
| Device config flows through | nemlib resolver → DeviceConfig → interpreter memory sizing |
| Validation catches errors | nemlib validation → interpreter refuses invalid programs |
| Opcode registry aligns | nemlib registry data matches interpreter compute backend dispatch |

### nemlib ↔ Conformance Tests

| Validation Point | How |
|-----------------|-----|
| Validation tier tests | Call runner.validate() → nemlib parse + validate |
| Error messages match | Test asserts expected error text in diagnostics |
| Source locations accurate | Diagnostics include correct file/line/column |

### Interpreter ↔ Conformance Tests

| Validation Point | How |
|-----------------|-----|
| Execution tier tests | Call runner.execute() → interpreter runs program |
| Numeric correctness | Output arrays match expected .npy data within tolerance |
| Buffer naming | Input/output buffer names in test match program declarations |

## Synchronization Protocol

After each step:

1. **Shared agent**: Opens PR from `agent/shared/main` to `integration/main`
2. **Interpreter agent**: Opens PR from `agent/interpreter/main` to `integration/main`
3. **Integration agent**: Merges shared PR first, then interpreter PR
4. **Integration agent**: Runs `make test` to verify cross-component consistency
5. **Integration agent**: Reports any failures back to the responsible builder agent (shared or interpreter)

At parallel track convergence (after Steps 5 + 6):
1. Integration agent merges both tracks into `integration/main`
2. Integration agent runs full test suite
3. Integration agent verifies device-aware execution works
4. Failures reported back to shared agent or interpreter agent as appropriate
