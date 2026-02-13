# Phase 1 Master Plan: Incremental NEM Development

## Goal

Build a working NEM interpreter with shared library infrastructure, progressing incrementally through language constructs. Each step produces testable, verifiable output.

## Scope

| In Scope | Out of Scope |
|----------|-------------|
| nemlib shared library (libs/nemlib/) | Compiler, Binder, Simulator |
| Interpreter (tools/interpreter/) | Timed execution mode |
| Conformance tests (tests/conformance/) | NpmPyTorchApi bit-true compute |
| Infrastructure (Makefile, pyproject.toml, CI) | Jupyter/notebook support |
| All stable opcodes (41 of 49) | Future opcodes (conv1d, conv3d, depthwise_conv2d, reductions) |
| | Multi-engine execution |
| | IR schema, object format, CLI, diagnostics contracts |

## 8-Step Overview

| Step | Language Constructs | Milestone |
|------|-------------------|-----------|
| **1** | `program`, `const`, integer expressions | Parse + evaluate const blocks from all examples |
| **2** | `buffer`, `region`/`let`, elem types, shapes, layouts, decorators (syntax) | Parse full declarations from all examples |
| **3** | `transfer.async/sync`, `store.async/sync`, `wait`, tokens, `deps` | Execute synthetic transfer programs |
| **4** | `loop`/`endloop`, `@max_in_flight`, `mod`, loop variables | All examples execute with data movement (compute = placeholder) |
| **5** | All compute syntax, elementwise ops, `gemm`, `matmul`, `conv2d` | `conv2d_relu.nem` + `gemm_bias_relu.nem` produce correct output |
| **6** | `device` config, `extends`, `include`, `topology`, `type_family`, opcode registry | Device configs load with inheritance; type family sets resolved |
| **7** | Pooling, normalization, softmax, layout, cast, quantize/dequantize, INT4, FLOAT attrs | All 5 examples produce correct output; all opcodes work |
| **8** | Decorators (semantic), full validation pipeline (10 passes) | Complete language coverage; invalid programs rejected |

## Dependency Graph

```
Step 1: Infrastructure + Lexer + Constants
  |
  v
Step 2: Storage + Memory Model
  |                        \
  v                         v
Step 3: Data Movement     Step 6: Device Config + Registry   << PARALLEL TRACKS
  |                         |
  v                         |
Step 4: Loops               |
  |                         |
  v                         |
Step 5: Compute Ops         |
  |                        /
  v                       v
Step 7: Remaining Ops + Type Extensions
  |
  v
Step 8: Semantic Analysis + Decorators
```

**Key parallelism opportunity**: Steps 3-5 (execution path) and Step 6 (device config) are independent tracks. The interpreter agent works on execution while the libs agent builds device support in nemlib. They converge at Step 7.

## Agent Model

Three agents collaborate in Phase 1:

| Agent | Role | Builds Code? |
|-------|------|-------------|
| **Libs agent** | Builds shared library (nemlib), test infrastructure, build infra | Yes |
| **Interpreter agent** | Builds interpreter-specific code | Yes |
| **Integration agent** | Runs cross-component tests, validates, reports failures, merges PRs | No (read-only) |

The libs agent and interpreter agent are **builders**. The integration agent is a **quality gate** — it never writes production code, only runs tests, validates cross-component consistency, and reports failures back to the responsible builder agent.

## Agent Responsibilities

| Step | Libs Agent | Interpreter Agent | Integration Agent |
|------|------------|-------------------|-------------------|
| 1 | nemlib setup, diagnostics, core, lexer, parser (const), conformance infra, Makefile | Interpreter project setup | Validate: both packages install, const conformance passes |
| 2 | Parser (buffers, regions, types), decorators (syntax) | Memory model, buffer manager, region views | Validate: interpreter builds against latest nemlib |
| 3 | Parser (tasks, tokens, wait, deps) | Task graph, scheduler, executor, transfer/store | Validate: transfer programs execute correctly |
| 4 | Parser (loops) | Loop execution, max_in_flight, variable binding | Validate: all examples parse and execute (compute=placeholder) |
| 5 | opcodes.py (registry loader), parser (compute) | Compute backend, NumPy implementations | Validate: conv2d_relu + gemm_bias_relu produce correct output |
| 6 | Device config parser, resolver, inheritance | Device loading, wiring into interpreter | Validate: device configs resolve, device_config conformance passes |
| 7 | (Support as needed) | Remaining opcode implementations | Validate: all 5 examples produce correct output |
| 8 | Validation pipeline (10 passes), type families | Decorator enforcement, error reporting | Validate: full conformance suite passes, invalid programs rejected |

## Git Strategy

Per `docs/engineering/github-process.md`:

**Libs agent** (libs/, tests/conformance/ infra, Makefile):
- Branch: `agent/libs/main`
- Features: `agent/libs/feat/step-N-<description>`

**Interpreter agent** (tools/interpreter/):
- Branch: `agent/interpreter/main`
- Features: `agent/interpreter/feat/step-N-<description>`

**Integration agent** (validation, merging):
- Branch: `integration/main`
- Does not create feature branches — works directly on `integration/main` for validation runs and merge decisions

**Per-step workflow**:
1. Libs agent and interpreter agent create feature branches for the step
2. Implement and test locally
3. Merge to agent's main branch
4. Open PR to `integration/main`
5. Integration agent runs `make test`, validates cross-component consistency
6. Integration agent merges if green, or reports failures back to responsible agent

**Synchronization points**: After Steps 2, 5, 6, and 8, all agents must synchronize before proceeding.

## Component Ownership

| Component | Owner | Location |
|-----------|-------|----------|
| nemlib (shared library) | Libs agent | `libs/nemlib/` |
| Interpreter | Interpreter agent | `tools/interpreter/` |
| Conformance test framework | Libs agent | `tests/conformance/runner.py`, `conftest.py`, `runners/` |
| Conformance test cases | Libs agent (wiring), Integration agent (defines what to test) | `tests/conformance/` |
| Infrastructure | Libs agent | Root `Makefile`, `pyproject.toml` files |
| Plan documents | Integration agent | `plan/phase_1/` |
| Spec and contracts | Integration agent | `spec/`, `docs/contracts/` |

## Related Documents

- [libs.md](libs.md) — nemlib shared library plan
- [interpreter.md](interpreter.md) — Interpreter plan
- [tests.md](tests.md) — Conformance test architecture and plan
- [infra.md](infra.md) — Infrastructure plan
- [integration.md](integration.md) — Integration validation and completion criteria

## Reference Files

| File | Role |
|------|------|
| `spec/nem_spec.md` | Normative spec — all implementation decisions trace here |
| `docs/architecture/common-infrastructure.md` | Defines nemlib architecture |
| `spec/registry/opcodes.yaml` | Machine-readable opcode definitions (49 opcodes) |
| `tools/interpreter/interpreter_spec.md` | Interpreter architecture spec |
| `examples/*.nem` | End-to-end test targets |
| `docs/engineering/github-process.md` | Git branching strategy |
