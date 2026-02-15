# Common Infrastructure Architecture

## 1. Motivation

The NEM toolchain comprises four tools — Interpreter, Compiler, Binder, Simulator — that share significant conceptual overlap. Without a shared library, each tool would independently implement NEM parsing, device configuration resolution, type family matching, and diagnostic reporting. This leads to:

- **Code duplication** across tools.
- **Semantic drift** where tools disagree on language rules.
- **Higher maintenance cost** when the spec evolves.

This document defines the common infrastructure that should be extracted into `libs/` before tool implementation begins.

---

## 2. Analysis: What Each Tool Needs

### 2.1 Tool Responsibilities

| Tool | Input | Output | Role |
|------|-------|--------|------|
| **Interpreter** | NEM source text | Execution results, validation diagnostics | Reference execution and validation |
| **Compiler** | NEM source text | IR / object format | Lowers source to portable binary |
| **Binder** | IR / object format | TCB stream | Lowers to hardware-specific descriptors |
| **Simulator** | Encoded programs (object format) | Cycle-accurate execution trace | Models hardware execution |

### 2.2 Shared Concern Matrix

| Concern | Interpreter | Compiler | Binder | Simulator | Count |
|---------|:-----------:|:--------:|:------:|:---------:|:-----:|
| NEM source lexer/parser | Yes | Yes | — | — | 2 |
| AST node definitions | Yes | Yes | — | — | 2 |
| Device config parsing | Yes | Yes | Yes | Yes | 4 |
| Device resolution/inheritance | Yes | Yes | Yes | Yes | 4 |
| Element type model | Yes | Yes | Yes | Yes | 4 |
| Memory level model (DDR/L2/L1) | Yes | Yes | Yes | Yes | 4 |
| Opcode definitions/signatures | Yes | Yes | Yes | — | 3 |
| Decorator definitions | Yes | Yes | Yes | — | 3 |
| Type family definitions | Yes | Yes | Yes | — | 3 |
| Type family matching | Yes | Yes | Yes | — | 3 |
| Expression AST and evaluation | Yes | Yes | — | — | 2 |
| Semantic validation pipeline | Yes | Yes | — | — | 2 |
| Diagnostics (errors/warnings) | Yes | Yes | Yes | Yes | 4 |
| Source location tracking | Yes | Yes | Yes | Yes | 4 |

### 2.3 What Is NOT Shared

These are tool-specific and belong in each tool's own codebase:

| Concern | Owner | Reason |
|---------|-------|--------|
| Memory model (byte arrays, allocation) | Interpreter | Execution-specific state |
| Execution engine / scheduler | Interpreter | Execution-specific logic |
| Compute backends (NumPy, NpmPyTorchApi) | Interpreter | Execution-specific |
| IR generation / optimization | Compiler | Compiler-specific lowering |
| TCB generation / address mapping | Binder | Hardware-specific lowering |
| Cycle-accurate timing model | Simulator | Simulation-specific |
| Interactive API (step, breakpoints) | Interpreter | User interface |

---

## 3. Proposed Architecture

### 3.1 Single Shared Package: `nemlib`

All shared infrastructure lives in a single package `nemlib` organized into layered submodules. A single package avoids the overhead of managing multiple independent packages while maintaining clear internal boundaries through the layer system.

The package has two implementations (see ADR-007): `libs/nemlib-py/` (Python, Phase 1) and `libs/nemlib-cpp/` (C++, Phase 2+). Both follow the same layered structure. The Python package structure is shown below; the C++ structure mirrors it with `.hpp`/`.cpp` files.

### 3.2 Package Structure (Python — `libs/nemlib-py/`)

```
libs/nemlib-py/
    pyproject.toml              # Package metadata, dependencies
    nemlib/
        __init__.py             # Version, top-level re-exports
        py.typed                # PEP 561 marker

        # ── Layer 0: Diagnostics (zero dependencies) ──────────
        diagnostics/
            __init__.py
            location.py         # SourceLocation(file, line, col, end_line, end_col)
            severity.py         # DiagnosticSeverity enum (error, warning, info)
            diagnostic.py       # Diagnostic(severity, message, location, notes)
            collector.py        # DiagnosticCollector — accumulates and reports

        # ── Layer 1: Core data model (depends on: diagnostics) ─
        core/
            __init__.py
            elements.py         # ElementType enum, sizeof(), is_integer(), is_float()
            memory.py           # MemoryLevel enum (DDR, L2, L1), L1 indexing
            opcodes.py          # OpcodeKind enum, opcode metadata, operand signatures
            decorators.py       # DecoratorKind enum, argument specs, validation
            expressions.py      # ExprNode AST, constant-folder, evaluator

        # ── Layer 2: Parser (depends on: core, diagnostics) ────
        parser/
            __init__.py
            tokens.py           # TokenKind enum, Token(kind, lexeme, location)
            lexer.py            # Lexer: NEM source → token stream
            ast_nodes.py        # Full AST: ProgramNode, BufferDeclNode, RegionDeclNode,
                                #   TaskNode, LoopNode, WaitNode, DeviceConfigNode, etc.
            parser.py           # Recursive descent parser: tokens → AST
            errors.py           # Parse error recovery and reporting

        # ── Layer 3: Device model (depends on: parser, core, diagnostics)
        device/
            __init__.py
            model.py            # DeviceConfig dataclass (topology, mandatory, extended)
            resolver.py         # Inheritance resolution, effective type family set
            builtins.py         # Built-in device presets (npm_lite, etc.)

        # ── Layer 4: Type system (depends on: core, device, diagnostics)
        types/
            __init__.py
            families.py         # TypeFamily, TypeVariant definitions from spec appendix
            registry.py         # TypeFamilyRegistry — all families, lookup by opcode
            matching.py         # match_opcode_instance() → matched variant or error
            conformance.py      # MUST/MAY variant classification

        # ── Layer 5: Validation (depends on: all above) ────────
        validation/
            __init__.py
            name_resolver.py    # Pass 1: Identifier resolution, scope checking
            expr_evaluator.py   # Pass 2: Constant expression evaluation
            buffer_validator.py # Pass 3: Buffer size > 0, alignment power-of-2
            region_validator.py # Pass 4: Offset+extent bounds, byte-extent consistency
            type_checker.py     # Pass 5: Opcode-type legality via type family matching
            dep_validator.py    # Pass 6: Token references resolve to earlier tasks
            hazard_checker.py   # Pass 7: Overlapping regions, @memmove
            engine_validator.py # Pass 8: No cross-engine L1 references
            deco_validator.py   # Pass 9: Known decorators, correct argument types
            loop_validator.py   # Pass 10: @max_in_flight >= 1, valid bounds
            pipeline.py         # ValidationPipeline — orchestrates passes in order
```

### 3.3 Layer Dependency Rules

```
Layer 5: validation
    ↑ depends on
Layer 4: types
    ↑ depends on
Layer 3: device
    ↑ depends on
Layer 2: parser
    ↑ depends on
Layer 1: core
    ↑ depends on
Layer 0: diagnostics
```

**Strict rule**: A module may only import from its own layer or lower layers. No upward or circular dependencies.

### 3.4 What Each Tool Imports

```
Interpreter:  nemlib.* (all layers)
Compiler:     nemlib.* (all layers)
Binder:       nemlib.core, nemlib.device, nemlib.types, nemlib.diagnostics
Simulator:    nemlib.core, nemlib.device, nemlib.diagnostics
```

The Binder and Simulator do not parse NEM source text (they consume IR/object format), but they do need device configuration parsing. Since device configs use NEM grammar, they transitively pull in `nemlib.parser`. This is acceptable — the parser is lightweight and device config parsing is a universal need.

---

## 4. Key Design Decisions

### 4.1 Single Package vs. Multiple Packages

**Decision**: Single `nemlib` package.

**Rationale**: The layers have tight conceptual coupling (parser produces AST nodes defined in core, device model uses parser, etc.). Separate packages would create version coordination overhead with no practical benefit — all tools pin to the same monorepo revision anyway.

### 4.2 Implementation Language Strategy

**Decision**: Phased dual-implementation approach — Python first, C++ later, converge to C++. See ADR-007 for full rationale.

**Phase 1** (current): `libs/nemlib-py/` — Pure Python 3.10+ with type annotations throughout. Fast iteration during spec exploration. The interpreter consumes it natively.

**Phase 2** (compiler/binder start): `libs/nemlib-cpp/` — C++ implementation added alongside the Python version. The compiler (C++, MLIR-based) consumes `nemlib-cpp` directly. The binder (Rust) consumes via FFI. The interpreter continues using `nemlib-py`. Conformance tests run against both implementations for differential bug detection.

**Phase 3** (grammar stabilizes): `nemlib-cpp` becomes the sole implementation. The interpreter switches to pybind11-wrapped C++ nemlib. `nemlib-py` is archived.

**Rationale**: The compiler requires C++ for MLIR integration. The binder is Rust. A Python-only nemlib forces these tools to reimplement shared logic independently, creating drift risk. Starting with Python captures fast-iteration benefits during spec exploration. Adding C++ when tools need it avoids premature complexity. Converging to one implementation eliminates long-term dual maintenance.

### 4.3 Parser Scope: Programs AND Device Configs

**Decision**: A single parser handles both NEM programs and device configurations.

**Rationale**: The NEM spec defines a unified grammar where programs and device configs share lexical conventions, expression syntax, and structural patterns. A single parser avoids duplicating lexer/token definitions.

### 4.4 Validation as Shared Library vs. Tool-Specific

**Decision**: The 10-pass semantic validation pipeline is shared.

**Rationale**: Both the Interpreter and Compiler must perform identical validation. If each tool implemented its own validation, they could disagree on what constitutes a valid program. The Binder may also use subsets of validation (type checking) when processing IR that references NEM types. A shared validation pipeline is the single source of truth for "is this program valid?"

### 4.5 Immutable AST

**Decision**: AST nodes are immutable dataclasses (frozen=True).

**Rationale**: The AST is produced by the parser and consumed by multiple downstream components (validation, interpreter engine, compiler IR gen). Immutability prevents accidental mutation and makes the AST safe to share across tool stages. Tools that need to annotate the AST (e.g., attaching resolved types) use a separate side-table rather than mutating nodes.

---

## 5. Key Interfaces

### 5.1 Diagnostics

```python
@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None

class DiagnosticSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass(frozen=True)
class Diagnostic:
    severity: DiagnosticSeverity
    message: str
    location: SourceLocation | None
    notes: list[str] = field(default_factory=list)

class DiagnosticCollector:
    """Accumulates diagnostics during parsing/validation."""
    def error(self, msg: str, loc: SourceLocation | None = None) -> None: ...
    def warning(self, msg: str, loc: SourceLocation | None = None) -> None: ...
    def info(self, msg: str, loc: SourceLocation | None = None) -> None: ...
    def has_errors(self) -> bool: ...
    def get_all(self) -> list[Diagnostic]: ...
    def format_all(self) -> str: ...
```

### 5.2 Core Data Model

```python
class ElementType(Enum):
    I4 = "i4"
    I8 = "i8"
    I16 = "i16"
    I32 = "i32"
    U8 = "u8"
    U16 = "u16"
    U32 = "u32"
    F16 = "f16"
    BF16 = "bf16"
    F32 = "f32"

    def sizeof(self) -> int: ...
    def is_integer(self) -> bool: ...
    def is_float(self) -> bool: ...

class MemoryLevel(Enum):
    DDR = "DDR"
    L2 = "L2"
    L1 = "L1"  # L1 instances are indexed separately
```

### 5.3 Parser

```python
def lex(source: str, filename: str = "<string>") -> list[Token]: ...

def parse_program(tokens: list[Token], diag: DiagnosticCollector) -> ProgramNode: ...

def parse_device_config(tokens: list[Token], diag: DiagnosticCollector) -> DeviceConfigNode: ...

# Convenience: source text → AST in one call
def parse(source: str, filename: str = "<string>") -> tuple[ProgramNode | DeviceConfigNode, list[Diagnostic]]: ...
```

### 5.4 Device Resolution

```python
@dataclass(frozen=True)
class DeviceConfig:
    name: str
    spec_version: str
    parent: str | None                   # parent device name (from extends), or None
    num_engines: int
    per_engine: dict[str, int]           # {"NMU": 1, "CSTL": 2, "DMA": 2}
    mandatory_variants: frozenset[str]   # {"gemm.float<bf16>.no_bias", ...}
    extended_variants: frozenset[str]    # {"gemm.float<f32>.no_bias", ...}

    def effective_set(self, opcode: str) -> frozenset[str]:
        """Returns the effective type family set for a specific opcode."""
        ...

def resolve_device(
    node: DeviceConfigNode,
    parent_devices: dict[str, DeviceConfig],
    diag: DiagnosticCollector
) -> DeviceConfig: ...
```

### 5.5 Type Family Matching

```python
@dataclass(frozen=True)
class MatchResult:
    matched: bool
    variant_ref: str | None       # e.g., "gemm.float<f16>.no_bias"
    conformance: str | None       # "MUST" or "MAY"
    error_detail: str | None      # Why matching failed (if !matched)

def match_opcode_instance(
    opcode: str,
    operand_types: dict[str, ElementType],  # {"A": i8, "B": i8, "Y": i8, ...}
    attributes: dict[str, Any],             # {"accum_type": "i32", ...}
    device: DeviceConfig | None,
    registry: TypeFamilyRegistry
) -> MatchResult: ...
```

### 5.6 Validation Pipeline

```python
def validate(
    program: ProgramNode,
    device: DeviceConfig | None,
    diag: DiagnosticCollector
) -> None:
    """
    Runs all 10 validation passes in order.
    Errors are accumulated in `diag`.
    Stops after name resolution if critical errors prevent later passes.
    """
    ...
```

---

## 6. Impact on Existing Tool Specs

### 6.1 Interpreter

The interpreter architecture spec (`tools/interpreter/interpreter_spec.md`) defines its own `parser/`, `analyzer/`, and `device_resolver` modules. With `nemlib`, these become thin wrappers or direct imports:

| Interpreter Spec Module | Replacement |
|------------------------|-------------|
| `neminterp.parser.lexer` | `nemlib.parser.lexer` |
| `neminterp.parser.ast_nodes` | `nemlib.parser.ast_nodes` |
| `neminterp.parser.parser` | `nemlib.parser.parser` |
| `neminterp.analyzer.type_checker` | `nemlib.validation.type_checker` |
| `neminterp.analyzer.hazard_checker` | `nemlib.validation.hazard_checker` |
| `neminterp.analyzer.device_resolver` | `nemlib.device.resolver` |

The interpreter retains ownership of:
- `engine/` (execution engine, schedulers, token management)
- `memory/` (memory model, buffer allocation, region views)
- `compute/` (NumPy/NpmPyTorchApi backends)
- `runtime/` (environment, state snapshots)
- `api/` (NemInterpreter class, interactive commands)

### 6.2 Compiler, Binder, Simulator

These tools have no implementation specs yet. Their future specs should reference `nemlib` for parsing, device model, type system, and validation rather than defining their own.

---

## 7. Relationship to Contracts

The four TBD contracts in `docs/contracts/` are complementary to `nemlib`:

| Contract | Relationship to nemlib |
|----------|----------------------|
| **IR Schema** | `nemlib` does not define the IR format. The IR schema is a data format contract between Compiler and Binder. However, IR may reference `nemlib` types (ElementType, MemoryLevel, opcode names). |
| **Object/Bytecode Format** | Same as IR — data format contract. May reference `nemlib` types. |
| **CLI Contract** | Independent of `nemlib`. Defines command-line conventions. |
| **Diagnostics Contract** | `nemlib.diagnostics` implements the canonical diagnostic model. The Diagnostics Contract should formalize the `Diagnostic` structure from `nemlib` as the standard. |

---

## 8. Dependencies

```
nemlib dependencies:
    Python >= 3.10        (required)
    pytest >= 7.0         (dev only — testing)
    No external runtime dependencies.
```

`nemlib` intentionally has zero external runtime dependencies. It is a pure Python library dealing with parsing, data models, and validation — none of which require NumPy or other scientific libraries. Tools that need NumPy (Interpreter) or other libraries add those dependencies in their own `pyproject.toml`.

---

## 9. Testing Strategy

### 9.1 Unit Tests

Each layer has its own test suite:

| Layer | Test Focus |
|-------|------------|
| `diagnostics` | Collector accumulation, formatting, severity filtering |
| `core` | ElementType properties, expression evaluation, opcode metadata |
| `parser` | Token stream for all token types; AST structure for each grammar production; error recovery; round-trip (parse → format → parse) |
| `device` | Inheritance resolution; effective set computation; schema rule validation; built-in presets |
| `types` | Family matching for all MUST/MAY variants; rejection of illegal combinations; nearest-variant suggestion |
| `validation` | Each of the 10 passes tested independently with valid/invalid programs |

### 9.2 Conformance Integration

`nemlib`'s parser and validator are the reference for the `tests/conformance/` suite. Conformance tests parse and validate NEM programs using `nemlib`, then tools execute them.

### 9.3 Test Data

Tests use NEM source fragments from the spec examples and purpose-built test programs covering edge cases (empty programs, maximum nesting, all opcodes, all element types, device inheritance chains, etc.).

---

## 10. Implementation Order

The layers should be implemented bottom-up:

1. **Phase 1**: `diagnostics/` — Foundation for error reporting.
2. **Phase 2**: `core/` — Element types, memory levels, opcodes, decorators, expressions.
3. **Phase 3**: `parser/` — Lexer, AST nodes, recursive descent parser.
4. **Phase 4**: `device/` — Device config model, inheritance resolution.
5. **Phase 5**: `types/` — Type family definitions, matching engine.
6. **Phase 6**: `validation/` — All 10 semantic analysis passes.

Each phase produces a tested, usable layer. The Interpreter can begin implementation after Phase 3 (it can parse programs), and progressively adopt later layers as they complete.

---

## 11. Open Questions

1. **Expression evaluation scope**: The NEM spec allows loop-variable-dependent expressions in region offsets and buffer sizes (e.g., `i * tile_bytes`). Should `nemlib` include a full expression evaluator with variable binding, or only a constant-folder? *Recommendation*: Include a full evaluator with a variable environment — both Interpreter and Compiler need it, and it's small.

2. **AST annotation strategy**: Tools need to attach analysis results to AST nodes (resolved types, matched variants, computed offsets). Should `nemlib` define an `AnnotatedAST` wrapper, or leave annotation strategy to each tool? *Recommendation*: Provide a generic `ASTAnnotations` side-table in `nemlib` that maps `NodeId → dict[str, Any]`. This avoids mutable AST nodes while giving tools a standard attachment mechanism.

3. **Parser error recovery**: How aggressive should error recovery be? The interpreter spec mentions source-location-aware errors but doesn't detail recovery. *Recommendation*: Implement synchronization-token recovery (skip to next statement boundary on error) to enable reporting multiple errors per parse. This is standard practice and benefits all tools.
