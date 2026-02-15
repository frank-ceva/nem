# Shared Libraries

This directory contains the shared NEM library (`nemlib`) used by all NEM tools. It is **shared-agent-owned** — tool agents must not modify it directly. The integration agent reviews all changes but does not build code here.

## Multi-Language Strategy (ADR-007)

The toolchain spans multiple languages: Python (Interpreter), C++ (Compiler/MLIR), and Rust (Binder). To avoid drift, nemlib follows a phased approach:

| Phase | Directory | Description |
|-------|-----------|-------------|
| **1** (current) | `nemlib-py/` | Python implementation. Fast iteration during spec exploration. Interpreter consumes natively. |
| **2** (compiler/binder start) | `nemlib-py/` + `nemlib-cpp/` | C++ implementation added. Compiler and Binder consume C++ natively. Interpreter stays on Python. Differential conformance testing validates both agree. |
| **3** (grammar stabilizes) | `nemlib-cpp/` only | C++ becomes sole implementation. Interpreter switches to pybind11 bindings. Python version archived. |

See `docs/engineering/decisions/007-multi-language-shared-library.md` for full rationale.

## Directory Structure

```
libs/
  nemlib-py/                  # Python implementation (Phase 1+)
    pyproject.toml
    nemlib/                   # 6-layer architecture (see below)
    tests/                    # Python unit tests

  nemlib-cpp/                 # C++ implementation (Phase 2+)
    CMakeLists.txt
    include/nemlib/           # Public C++ headers
    src/                      # Implementation
    tests/                    # C++ unit tests
    bindings/python/          # pybind11 bindings
```

## Architecture

Both implementations follow the same 6-layer dependency model (see `docs/architecture/common-infrastructure.md`):

```
Layer 5: validation    (depends on all below)
Layer 4: types         (depends on core, device, diagnostics)
Layer 3: device        (depends on parser, core, diagnostics)
Layer 2: parser        (depends on core, diagnostics)
Layer 1: core          (depends on diagnostics)
Layer 0: diagnostics   (zero dependencies)
```

**Strict rule**: A module may only import from its own layer or lower layers. No upward or circular dependencies.

## What Each Tool Imports

```
Interpreter:  nemlib.* (all layers)
Compiler:     nemlib.* (all layers)
Binder:       nemlib.core, nemlib.device, nemlib.types, nemlib.diagnostics
Simulator:    nemlib.core, nemlib.device, nemlib.diagnostics
```

## When to Extract Shared Code

Code should be extracted to `libs/` when:

- The same logic is needed by 2 or more tools.
- The logic relates to a shared contract (IR parsing, object format reading, diagnostics formatting).
- Duplicating the code across tools would create drift risk.

Code should NOT be extracted when:

- Only one tool uses it (keep it tool-local).
- The logic is tightly coupled to a tool's internal architecture.
- The abstraction is speculative ("we might need this later").

## How to Propose a Shared Library

Tool agents cannot create or modify files in `libs/` directly. To propose shared code:

1. File a Contract Change Proposal using `docs/workflow/templates/proposal-contract-change.md`.
2. Include:
   * The code to be shared (or a reference to existing implementations in tools).
   * Which tools would use it.
   * The proposed API surface.
3. The shared agent will implement the library; the integration agent will review and merge.
