# ADR-007: Multi-Language Strategy for Shared Infrastructure

## Status

Accepted

## Context

The NEM toolchain has four tools that share substantial infrastructure through `nemlib` (see `docs/architecture/common-infrastructure.md`):

- **Parser** (lexer, token stream, recursive-descent parser, AST) — needed by Interpreter, Compiler
- **Core types** (ElementType, MemoryLevel, OpcodeKind, DecoratorKind, expressions) — needed by all 4 tools
- **Device model** (config parsing, inheritance resolution) — needed by all 4 tools
- **Type system** (type families, MUST/MAY variant matching) — needed by Interpreter, Compiler, Binder
- **Validation** (10-pass semantic analysis pipeline) — needed by Interpreter, Compiler
- **Diagnostics** (source locations, error/warning reporting) — needed by all 4 tools

The original architecture document (section 4.2) chose Python 3.10+ for all shared infrastructure, with the caveat: *"If a tool is later implemented in another language, the shared library can serve as a reference implementation."*

That caveat is now being exercised:

| Tool | Language | Rationale |
|------|----------|-----------|
| **Interpreter** | Python | Already decided, well-specified |
| **Compiler** | C++ | MLIR is C++-native; custom dialects and passes require the C++ API |
| **Binder** | Rust | Internal tool, no external ecosystem constraint |
| **Simulator** | TBD | |

The Compiler and Binder both require full parser capability and most shared layers. Maintaining a single Python implementation that other languages must reimplement independently creates ongoing drift risk — especially during active spec evolution.

### Timing

No nemlib implementation code exists yet — only architecture documents and API sketches. The opcode registry (`spec/registry/opcodes.yaml`) is already language-agnostic. This is the right time to make this decision.

### Scale of shared logic

The shared concerns include:
- A custom grammar with recursive-descent parsing and error recovery
- Expression evaluation with variable binding
- Device configuration inheritance resolution
- Type family matching with MUST/MAY semantics
- 10 semantic analysis passes with cross-referencing

### MLIR and language choice

MLIR (used by the Compiler) is part of the LLVM project, written in C++. Its C API exists but is alpha-quality, incomplete (notably: custom dialects as shared libraries don't work the same way), and unstable. The Rust bindings (melior crate) wrap this C API and inherit its limitations. Writing a production MLIR-based compiler in C++ is the natural choice — it uses the native API with full ecosystem support.

A Rust-only shared library (nemlib in Rust) would require the C++ compiler to consume it via FFI (cxx or cbindgen), adding a binding layer. A C++ shared library lets the compiler consume it directly. Since the Binder (Rust) can consume C++ via FFI just as well, and the Interpreter (Python) needs bindings regardless, C++ nemlib minimizes the total number of binding layers.

---

## Options Evaluated

### Option A: Single C++ nemlib with bindings

Write all of nemlib in C++. Python interpreter consumes via pybind11. Rust binder consumes via FFI (cxx/bindgen). Compiler and Binder link directly.

**Pros**: Single implementation, zero drift, compiler consumes natively, only 2 languages in the project (Python + C++, or Python + C++ + Rust for binder).
**Cons**: C++ is slower to iterate on than Python during spec exploration. Parser development loop is heavier.

### Option B: Single Rust nemlib with bindings

Write all of nemlib in Rust. Python via PyO3. C++ compiler via C ABI (cbindgen) or cxx.

**Pros**: Rust's type system is excellent for parsers. Single implementation.
**Cons**: Adds Rust as a 3rd language. C++ compiler must cross an FFI boundary to use nemlib — ironic given the compiler is C++. MLIR can't share types with nemlib naturally.

### Option C: Python reference + reimplement

Keep the current plan. Build nemlib in Python. C++/Rust tools reimplement independently.

**Pros**: Fastest to start. Pure Python interpreter.
**Cons**: 2-3 implementations of the parser, AST, type system, validation. Drift risk grows with every spec change. Every grammar update must be applied N times.

### Option D: Phased — Python first, C++ later, converge

Build nemlib in Python first (fast iteration during spec exploration). When compiler/binder start, build a C++ implementation using Python as reference. Run differential conformance tests during the overlap period. Eventually converge to C++ as the single source of truth.

**Pros**: Fast Python iteration during design phase. Differential testing between implementations finds bugs. Interpreter stays pure Python during Phase 1. Converges to single implementation long-term.
**Cons**: Temporary dual-maintenance period. Requires careful directory structure and conformance infrastructure.

---

## Decision

**Option D: Phased approach — Python first, C++ later, converge.**

### Phase 1: Python nemlib (current → grammar stabilizes)

- Build `libs/nemlib-py/` as a pure Python package. Fast iteration, interpreter uses it natively.
- Compiler/binder don't exist yet, so no C++ needed.
- Conformance tests accumulate against the Python implementation.

### Phase 2: Dual implementations (compiler/binder start)

- Build `libs/nemlib-cpp/` in C++ using the Python implementation as the reference specification.
- Compiler links against `nemlib-cpp` directly (native C++).
- Binder consumes `nemlib-cpp` via Rust FFI (cxx or bindgen).
- Interpreter continues using `nemlib-py` (pure Python).
- Conformance tests run against **both** implementations — this is where differential testing finds bugs.
- Cross-implementation comparison tests validate AST structural agreement and diagnostic consistency.

### Phase 3: Convergence (grammar stabilizes)

- `nemlib-cpp` becomes the single source of truth.
- Interpreter switches from `nemlib-py` to pybind11-wrapped `nemlib-cpp`.
- `nemlib-py` is archived (or kept read-only as documentation, no longer maintained).
- One implementation going forward.

### Directory structure

```
libs/
  README.md                         # Dual-implementation strategy and phase plan

  nemlib-py/                        # Python implementation (Phase 1 → archived in Phase 3)
    pyproject.toml                  # Package name: nemlib
    nemlib/
      __init__.py
      diagnostics/                  # Layer 0
      core/                         # Layer 1
      parser/                       # Layer 2
      device/                       # Layer 3
      types/                        # Layer 4
      validation/                   # Layer 5
    tests/                          # Python unit tests

  nemlib-cpp/                       # C++ implementation (Phase 2 → sole impl in Phase 3)
    CMakeLists.txt
    include/nemlib/                 # Public C++ headers
      diagnostics.hpp
      core/
        elements.hpp
        memory.hpp
        opcodes.hpp
        decorators.hpp
        expressions.hpp
      parser/
        tokens.hpp
        lexer.hpp
        ast_nodes.hpp
        parser.hpp
      device/
        model.hpp
        resolver.hpp
      types/
        families.hpp
        matching.hpp
      validation/
        pipeline.hpp
    src/                            # Implementation (.cpp)
    tests/                          # C++ unit tests (GoogleTest or Catch2)
    bindings/
      python/                       # pybind11 bindings → 'nemlib_native' during Phase 2,
        CMakeLists.txt              #   renamed to 'nemlib' in Phase 3
        src/bindings.cpp
```

### Python module naming during Phase 2

Both implementations produce a Python-importable package. To allow coexistence in the same environment during Phase 2:

- `nemlib-py` installs as `nemlib` (unchanged)
- `nemlib-cpp` pybind11 bindings install as `nemlib_native`
- Conformance runners import the appropriate one
- In Phase 3, `nemlib-cpp` bindings rename to `nemlib` and `nemlib-py` is removed

### Conformance testing

The existing pluggable runner protocol (`ConformanceRunner`) already supports parametrized testing across multiple backends. Changes for Phase 2:

**New library-level runners** that test nemlib directly (parse + validate only, no execution):

```
tests/conformance/runners/
    interpreter_runner.py         # Existing — uses nemlib-py + neminterp
    nemlib_py_runner.py           # NEW (Phase 2) — uses nemlib (Python) directly
    nemlib_cpp_runner.py          # NEW (Phase 2) — uses nemlib_native (C++ pybind11)
    pipeline_runner.py            # Future — compiler + binder + simulator
```

**Runner capability model** — runners declare what they support:

| Runner | validate | execute |
|--------|:--------:|:-------:|
| nemlib-py | Yes | No |
| nemlib-cpp | Yes | No |
| interpreter | Yes | Yes |
| pipeline | Yes | Yes |

Validation-tier tests run against all runners. Execution-tier tests run against only execution-capable runners.

**Cross-implementation comparison tests** (Phase 2 only):

```
tests/conformance/cross_impl/
    test_ast_agreement.py           # Parse programs with both, compare AST structure
    test_diagnostic_agreement.py    # Validate invalid programs, compare diagnostics
    programs/                       # Test corpus of valid + invalid NEM programs
```

---

## Consequences

### What becomes easier

- **Phase 1 velocity**: Python nemlib is fast to develop and debug during active spec exploration.
- **Bug finding**: Differential testing during Phase 2 catches parser edge cases, validation disagreements, and spec ambiguities that a single implementation would miss.
- **Interpreter simplicity**: The interpreter stays pure Python through Phase 1 and Phase 2 — no FFI friction during its primary development period.
- **Compiler/Binder integration**: C++ nemlib is consumed natively by the compiler (C++) and via standard FFI by the binder (Rust). No awkward cross-language bridging for the core tools.

### What becomes harder

- **Phase 2 maintenance**: Two nemlib implementations must be kept in sync. Every grammar change is applied twice.
- **Build complexity**: Phase 2 requires both Python and C++ build infrastructure (pip + CMake). Phase 3 simplifies to CMake + pybind11.
- **Conformance infrastructure**: The runner protocol must support library-level runners and cross-implementation comparison.

### What changes

- `libs/` directory structure changes from `libs/nemlib/` to `libs/nemlib-py/` (Phase 1) and `libs/nemlib-cpp/` (Phase 2).
- `docs/architecture/common-infrastructure.md` section 4.2 must be updated.
- The shared agent's scope expands to include C++ in Phase 2 (or a new agent owns `nemlib-cpp`).
- `plan/phase_1/` references to `libs/nemlib/` become `libs/nemlib-py/`.
- Conformance test infrastructure adds library-level runners and cross-implementation tests.
- Phase 1 plan is otherwise unchanged — same layers, same interfaces, same order, just in `nemlib-py/`.

### Risk mitigation

- **Drift during Phase 2**: Mitigated by conformance tests running against both implementations on every change. CI must gate on cross-implementation agreement.
- **Phase 2 duration**: Bounded by grammar stabilization. Once the grammar is stable, the C++ implementation catches up and converges. The Python implementation is not maintained indefinitely.
- **Interpreter Phase 3 migration**: The pybind11 API mirrors the Python API exactly (same function names, same types). The interpreter's `import nemlib` doesn't change — only the underlying implementation does.
