# Phase 1: Shared Library Plan (nemlib)

## Overview

`nemlib` is the shared Python library in `libs/nemlib-py/` used by all NEM tools. It provides parsing, type system, device model, and validation — everything except tool-specific execution logic.

Architecture is defined in `docs/architecture/common-infrastructure.md`. This plan aligns with that document.

## Package Structure

```
libs/nemlib-py/
  pyproject.toml              # Python 3.10+, zero runtime deps
  nemlib/
    __init__.py               # Version, top-level re-exports
    py.typed                  # PEP 561 marker

    diagnostics/              # Layer 0: zero dependencies
      __init__.py
      location.py             # SourceLocation(file, line, col, end_line, end_col)
      severity.py             # DiagnosticSeverity enum (error, warning, info)
      diagnostic.py           # Diagnostic(severity, message, location, notes)
      collector.py            # DiagnosticCollector — accumulates and reports

    core/                     # Layer 1: depends on diagnostics
      __init__.py
      elements.py             # ElementType enum, bitwidth(), is_integer(), is_float()
      memory.py               # MemoryLevel enum (DDR, L2, L1)
      opcodes.py              # OpcodeInfo, load registry from opcodes.yaml, query API
      decorators.py           # DecoratorKind enum, argument specs, validation rules
      expressions.py          # ExprNode types, const evaluator, runtime evaluator with variable env

    parser/                   # Layer 2: depends on core, diagnostics
      __init__.py
      tokens.py               # TokenKind enum, Token(kind, lexeme, location)
      lexer.py                # Lexer: NEM source -> token stream
      ast_nodes.py            # Full AST (frozen dataclasses): ProgramNode, BufferDeclNode, etc.
      parser.py               # Recursive descent: tokens -> AST
      errors.py               # Parse error recovery, synchronization tokens

    device/                   # Layer 3: depends on parser, core, diagnostics
      __init__.py
      model.py                # DeviceConfig dataclass
      resolver.py             # Inheritance resolution, effective type family set
      builtins.py             # Built-in device presets

    types/                    # Layer 4: depends on core, device, diagnostics
      __init__.py
      families.py             # TypeFamily, TypeVariant definitions from spec appendix
      registry.py             # TypeFamilyRegistry — index by opcode
      matching.py             # match_opcode_instance() -> MatchResult
      conformance.py          # MUST/MAY variant classification

    validation/               # Layer 5: depends on all above
      __init__.py
      name_resolver.py        # Pass 1: Identifier resolution, scope checking
      expr_evaluator.py       # Pass 2: Constant expression evaluation
      buffer_validator.py     # Pass 3: Buffer size > 0, alignment, capacity
      region_validator.py     # Pass 4: Offset+extent bounds, byte-extent consistency
      type_checker.py         # Pass 5: Opcode-type legality via type family matching
      dep_validator.py        # Pass 6: Token references, dependency ordering
      hazard_checker.py       # Pass 7: Overlapping regions, @memmove
      engine_validator.py     # Pass 8: No cross-engine L1 references
      deco_validator.py       # Pass 9: Decorator validity, @resource targets
      loop_validator.py       # Pass 10: @max_in_flight, bounds, no const in body
      pipeline.py             # ValidationPipeline — orchestrates passes in order
```

**Layer dependency rule**: A module may only import from its own layer or lower layers. No upward or circular imports.

## Per-Step Build Plan

### Step 1: Diagnostics + Core + Lexer + Parser (const)

**Modules built**:
- `diagnostics/` — complete (all 4 files)
- `core/elements.py` — ElementType enum with bitwidth()
- `core/memory.py` — MemoryLevel enum
- `core/expressions.py` — ExprNode types (IntLiteral, Identifier, BinaryOp, UnaryOp, Paren), constant expression evaluator with variable environment for future loop variable support
- `parser/tokens.py` — Full TokenKind enum (all NEM keywords, operators, delimiters, FLOAT, INT, STRING, ID, EOF)
- `parser/lexer.py` — Complete tokenizer for NEM programs and device configs (handles `#` comments, all literals, compound keywords like `transfer.async`)
- `parser/ast_nodes.py` — ProgramNode, ConstDeclNode, ExprNode variants
- `parser/parser.py` — `parse_program_header()`, `parse_const_decl()`, `parse_expr()`
- `parser/errors.py` — Basic error reporting with source locations

**Key decisions**:
- Lexer tokenizes the FULL NEM grammar from Step 1 (all keywords, operators). Parser only consumes a subset initially.
- ExprNode supports integer literals + identifiers + binary ops (+, -, *, /, mod) + unary minus + parentheses
- Expression evaluator takes an `env: dict[str, int]` parameter for variable binding (used by const evaluation now, loop variables later)

### Step 2: Parser (buffers, regions, types, decorators)

**Modules built/extended**:
- `core/decorators.py` — DecoratorKind enum (MATERIALIZED, READONLY, WRITEONLY, RESOURCE, DETERMINISTIC, MEMMOVE, DEBUG, PROFILE), argument specs
- `parser/ast_nodes.py` — Add: BufferDeclNode, RegionDeclNode (let binding), DecoratorNode, TypeAttrsNode (elem, shape, layout, strides), QuantDescNode (per_tensor, per_channel, per_group)
- `parser/parser.py` — Add: `parse_buffer_decl()`, `parse_let_decl()`, `parse_type_attrs()`, `parse_quant_desc()`, `parse_decorator()`

**Key decisions**:
- Region declarations use `let` keyword with `= region(buffer, offset, extent)` followed by type attributes on continuation lines
- Decorators parsed as syntax only (no semantic enforcement yet — that's Step 8)
- Quantization descriptor parsed for all 3 forms: `per_tensor(scale, zp)`, `per_channel(axis, scales[], zps[])`, `per_group(axis, group_size, scales[], zps[])`

### Step 3: Parser (tasks, tokens, wait, deps)

**Modules extended**:
- `parser/ast_nodes.py` — Add: TaskNode (with opcode, operands, deps, token assignment), WaitNode, InlineRegionNode (region expression in operand position)
- `parser/parser.py` — Add: `parse_task_statement()`, `parse_wait()`, `parse_deps()`, `parse_operand()` (handles both named references and inline `region(...)` expressions)

**Key decisions**:
- Token assignments: `tX = transfer.async(...)` — the `tX` is captured as the token name
- Inline region expressions in operands: `src=region(W_L2, 0, tileW_bytes) elem=i8, shape=[...]` — parser handles the continuation
- `deps=[tX, tY]` parsed as a list of token name references

### Step 4: Parser (loops)

**Modules extended**:
- `parser/ast_nodes.py` — Add: LoopNode (variable, start, end, max_in_flight, body)
- `parser/parser.py` — Add: `parse_loop()`
- `core/expressions.py` — Verify runtime evaluator handles loop variable binding

### Step 5: Opcode registry loader + Parser (compute)

**Modules built/extended**:
- `core/opcodes.py` — Load `spec/registry/opcodes.yaml`, OpcodeInfo dataclass (category, status, forms, operands, attributes, type_families, execution_unit, hardware_status), query API: `get_opcode(name)`, `get_operands(name)`, `get_attributes(name)`, `is_supported(name)`
- `parser/ast_nodes.py` — Add: ComputeTaskNode (opcode, in_operands, out_operands, attributes, deps, token)
- `parser/parser.py` — Add: `parse_compute_task()` — handles `opcode.async/sync in OP1, OP2 out OP3 deps=[...] attr1=val1 attr2=val2`

### Step 6: Device config parser + resolver

**Modules built**:
- `parser/ast_nodes.py` — Add: DeviceConfigNode, TopologyNode, PerEngineNode, DeviceUnitsNode, UnitCharacteristicsNode, OpcodeMandatoryNode, OpcodeExtendedNode, VariantRefNode, TypeFamilyDeclNode, IncludeDeclNode, SpecClauseNode
- `parser/parser.py` — Add: `parse_device_config()`, `parse_topology()`, `parse_type_family_decl()`, `parse_include()`, document-type dispatch (program vs config_document)
- `device/model.py` — DeviceConfig dataclass: name, spec_version, parent, num_engines, per_engine (dict), device_units (dict), unit_characteristics (dict), l1_size_bytes, l2_size_bytes, mandatory_variants (frozenset), extended_variants (frozenset), type_families (list). Methods: `effective_set(opcode)`
- `device/resolver.py` — `resolve_device()`: include file loading (relative paths, circular detection), inheritance resolution (extends), topology merge, opcode set union, unit_characteristics merge
- `device/builtins.py` — Pre-parsed npm_baseline_1_0 (if needed)

### Step 7: (Support as needed)

- Verify FLOAT token handling in lexer
- Verify FLOAT accepted in compute attribute positions only
- Verify i4 element type handling in core/elements.py

### Step 8: Type system + Validation pipeline

**Modules built**:
- `types/families.py` — TypeFamily, TypeVariant dataclasses, all 13 family definitions from spec appendix (gemm.float, gemm.int8, gemm.int4, conv2d.float, conv2d.int8, conv2d.int4, eltwise, view, norm, softmax, cast, quantize, dequantize)
- `types/registry.py` — TypeFamilyRegistry: index families by opcode name, lookup
- `types/matching.py` — `match_opcode_instance(opcode, operand_types, attributes, device, registry) -> MatchResult`
- `types/conformance.py` — MUST/MAY classification, device conformance checking
- `validation/` — All 10 passes (see package structure above)
- `validation/pipeline.py` — `validate(program, device, diag)`: runs passes in order, stops on critical errors

## Key Interfaces

### Diagnostics (Layer 0)

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
    def error(self, msg: str, loc: SourceLocation | None = None) -> None: ...
    def warning(self, msg: str, loc: SourceLocation | None = None) -> None: ...
    def has_errors(self) -> bool: ...
    def get_all(self) -> list[Diagnostic]: ...
    def format_all(self) -> str: ...
```

### Parser (Layer 2)

```python
def lex(source: str, filename: str = "<string>") -> list[Token]: ...
def parse_program(tokens: list[Token], diag: DiagnosticCollector) -> ProgramNode: ...
def parse_device_config(tokens: list[Token], diag: DiagnosticCollector) -> DeviceConfigNode: ...
def parse(source: str, filename: str = "<string>") -> tuple[ProgramNode | DeviceConfigNode, list[Diagnostic]]: ...
```

### Device Resolution (Layer 3)

```python
@dataclass(frozen=True)
class DeviceConfig:
    name: str
    spec_version: str
    parent: str | None
    num_engines: int
    per_engine: dict[str, int]
    device_units: dict[str, int]
    l1_size_bytes: int
    l2_size_bytes: int
    mandatory_variants: frozenset[str]
    extended_variants: frozenset[str]

    def effective_set(self, opcode: str) -> frozenset[str]: ...

def resolve_device(node: DeviceConfigNode, parents: dict[str, DeviceConfig], diag: DiagnosticCollector) -> DeviceConfig: ...
```

### Type Family Matching (Layer 4)

```python
@dataclass(frozen=True)
class MatchResult:
    matched: bool
    variant_ref: str | None
    conformance: str | None      # "MUST" or "MAY"
    error_detail: str | None

def match_opcode_instance(opcode, operand_types, attributes, device, registry) -> MatchResult: ...
```

### Validation Pipeline (Layer 5)

```python
def validate(program: ProgramNode, device: DeviceConfig | None, diag: DiagnosticCollector) -> None: ...
```

## Dependencies

```
nemlib runtime dependencies: None (pure Python 3.10+)
nemlib dev dependencies: pytest >= 7.0, mypy, ruff
```

## Testing

Each layer has unit tests under `libs/nemlib-py/tests/`:

```
libs/nemlib-py/tests/
  test_diagnostics.py
  test_elements.py
  test_expressions.py
  test_lexer.py
  test_parser_const.py
  test_parser_buffer.py
  test_parser_task.py
  test_parser_loop.py
  test_parser_compute.py
  test_parser_device.py
  test_opcodes.py
  test_device_resolver.py
  test_type_families.py
  test_type_matching.py
  test_validation_*.py        # One per validation pass
```
