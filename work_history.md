# Work History

Completed work items are recorded here.

---

# Phase 1, Step 2: Storage Declarations + Memory Model
status=completed

Extended the parser to handle buffer declarations, region declarations (let bindings), type attributes, quantization descriptors, and decorators (syntax only).

## Summary

### core/decorators.py (new file)
- `DecoratorKind` enum with 9 members: MATERIALIZED, DETERMINISTIC, MEMMOVE, READONLY, WRITEONLY, MAX_IN_FLIGHT, RESOURCE, DEBUG, PROFILE
- `from_name()` classmethod for source-level name lookup

### parser/ast_nodes.py extensions
- `StringLiteral(ExprNode)` — string literal in value positions
- `ArrayLiteral(ExprNode)` — array literal `[val, val, ...]`
- `PerTensorQuantNode`, `PerChannelQuantNode`, `PerGroupQuantNode` — quant descriptor variants
- `QuantDescNode` — Union type of the three quant forms
- `TypeAttrsNode` — elem, shape, layout, strides, quant
- `DecoratorNode` — `@name` or `@name(args)`
- `BufferDeclNode` — `buffer NAME : level (size=expr, align=INT) @decos`
- `RegionDeclNode` — `let NAME = region(buf, off, ext) type_attrs @decos`
- `LetDeclNode` — `let NAME = value` (non-region)
- `StmtNode` union updated to include all statement types
- `ProgramNode.statements` updated from `tuple[ConstDeclNode, ...]` to `tuple[StmtNode, ...]`

### parser/parser.py extensions
- `_peek_past_newlines()` — continuation line detection for type_attrs and decorators
- `parse_buffer_decl()` — buffer with DDR/L2/L1/L1[expr] memory level, size/align props, decorators
- `parse_let_decl()` — dispatches to region or simple let
- `_parse_region_body()` — region(buf, offset, extent) with optional type_attrs and decorators
- `_try_parse_type_attrs()` / `_parse_type_attrs()` — elem=, shape=[], layout= or strides=[], optional quant=
- `_parse_quant_desc()` — per_tensor, per_channel, per_group
- `_parse_decorators()` / `_parse_decorator()` — zero or more decorators looking past newlines
- `_parse_deco_args()` — handles value lists and @resource(unit_type[expr]) syntax
- `_parse_value()` — expr, STRING, [array]
- Updated `_parse_body()` to handle BUFFER and LET tokens

### Tests
- `tests/test_parser_storage.py` — 71 new tests covering:
  - Buffer declarations (13 tests): DDR/L2/L1, L1[expr], size/align props, decorators
  - Let declarations (8 tests): int, float, expression, string, array, nested array, trailing comma
  - Region declarations (6 tests): basic, with type_attrs, with decorators, combined
  - Type attributes (5 tests): layout, strides, all 13 elem types, expression shapes, minimal
  - Quantization descriptors (3 tests): per_tensor, per_channel, per_group
  - Decorators (6 tests): simple, with args, multiple, continuation lines
  - Value parsing (7 tests): strings, arrays, nested, deeply nested, mixed
  - Mixed programs (4 tests): const+buffer, buffer+region, all types, full program with headers
  - Multi-line continuation (4 tests): type_attrs, decorators, both, multiple
  - Error cases (12 tests): missing colon, invalid mem level, missing paren, invalid elem type, etc.
  - Integration (2 tests): realistic matmul program, quantized conv program
- Updated 3 Step 1 tests that used buffer/let as "unknown" statements — replaced with truly unknown opcodes (store, emit)
- Total: 247 unit tests pass, ruff check zero violations, ruff format zero reformats, mypy zero errors

---

# Phase 1, Step 1: Infrastructure + Lexer + Constants
status=completed

Built the nemlib foundation: package setup, diagnostics (Layer 0), core types (Layer 1), full lexer and parser for const declarations (Layer 2), conformance test infrastructure, and build infrastructure.

## Summary

### Package & Infrastructure
- `pyproject.toml` (Python 3.10+, zero runtime deps), `__init__.py`, `py.typed`, root `Makefile`
- Virtual environment requires Python 3.10+ via `uv venv`

### Diagnostics (Layer 0)
- `SourceLocation`, `DiagnosticSeverity`, `Diagnostic`, `DiagnosticCollector` — all frozen dataclasses

### Core (Layer 1)
- `ElementType` (13 types with `bitwidth()`, `is_integer()`, `is_float()`)
- `MemoryLevel` enum (DDR, L2, L1)
- Expression AST nodes (IntLiteral, FloatLiteral, Identifier, BinaryOp, UnaryOp, ParenExpr)
- `evaluate_const_expr()` with variable environment

### Parser (Layer 2)
- Full `TokenKind` enum (106 token types including `LANGLE`/`RANGLE` for device config)
- Complete lexer handling comments, all literals, compound keywords, angle brackets
- `ProgramNode`, `ConstDeclNode` AST nodes
- Recursive-descent parser: program header, const declarations, expressions with precedence
- Error recovery (skip to newline on parse error)

### Conformance Test Infrastructure
- `ConformanceRunner` protocol, `ValidationResult`, `InterpreterRunner`
- Parametrized pytest fixture runs all tests against all available runners
- 32 const conformance cases + 63 other conformance tests (registry, device_config, opcodes, types)

### Tests
- 176 nemlib unit tests (diagnostics, elements, expressions, lexer, parser)
- 95 conformance tests pass, 1 skipped (schema validation needs jsonschema)
- `ruff check` zero violations, `ruff format` zero reformats, `mypy` zero errors (strict)

### Crash Recovery Fixes
- Fixed line-too-long in `expressions.py`, unused import in `parser.py`
- Added `LANGLE`/`RANGLE` tokens (lexer failed on device config `<`/`>` syntax)
- Ran `ruff format` on 6 files
- Recreated polluted `.venv` with `uv venv --python 3.10 --clear`

---

# Extract opcode definitions into a machine-readable registry
status=completed

Extracted all NEM opcode signatures from spec prose into a machine-readable YAML registry, updated the spec to reference it normatively, and created the supporting infrastructure.

## Summary

### Format decision: YAML
- Chose YAML over NEM syntax to avoid circular dependency (NEM parsers don't exist yet).
- JSON Schema (`spec/registry/schema.json`) enforces structural validity.
- Pragmatic migration path to NEM syntax once parsers are mature.

### Registry created (`spec/registry/opcodes.yaml`)
- 49 opcodes across 13 categories: data_movement (2), linear_algebra (2), convolution (4), elementwise_unary (11), elementwise_binary (7), elementwise_other (1), pooling (2), layout (7), reduction (5), normalization (2), softmax (2), type_conversion (3), generic (1).
- Per-opcode fields: category, status, forms (async/sync), operands (name, direction, required, role, constraints), attributes (name, type, required, default), type_families, execution_unit, hardware_status.
- 41 stable opcodes, 8 future opcodes.
- All type_family references validated against `examples/npm_baseline_1.0.nem` (13 families).
- All opcodes used in example `.nem` files have registry entries.

### Validation infrastructure
- `spec/registry/schema.json` — JSON Schema draft 2020-12
- `spec/registry/validate.py` — validates schema conformance + cross-references
- `registry/README.md` — usage documentation
- `tests/conformance/registry/test_registry.py` — pytest conformance suite (structure, schema, cross-references, category coverage)

### Spec update (`spec/nem_spec.md`)
- Replaced ~280-line inline "Opcode Signatures (Normative)" section with a normative reference to `spec/registry/opcodes.yaml`.
- Kept Task Taxonomy, Type Legality, Type Family Grammar, Hardware Support Status, and Appendix sections unchanged.
- Spec now delegates opcode catalog to registry; retains semantic rules.

### Contract (`docs/contracts/opcode-registry.md`)
- Documents normative status, schema, tool consumption patterns, change process, versioning.
- Added to `docs/contracts/README.md` inventory.

### Tool propagation
- Added "Consume opcode registry" work item (top priority) to:
  - `tools/interpreter/work.md`
  - `tools/compiler/work.md`
  - `tools/binder/work.md`
  - `tools/simulator/work.md`
- VSCode extension noted for future syntax highlighting generation from registry.

### Changelog
- Updated `spec/CHANGELOG.md` with detailed entry.

---

# Multi-agent workflow
status=completed

Defined and validated a multi-agent concurrent engineering workflow for the NEM toolchain.

## Summary

### Process Documentation
- Reviewed and fixed all engineering process docs (principles, general-dev-process, spec-int-dev-process, tool-dev-process, github-process)
- Fixed cross-reference errors (wrong filenames, truncated sentences, broken links)
- Resolved binder/assembler naming collision — adopted "binder" per the NEM spec
- Fixed "interpretor" typo — renamed directory and all references to "interpreter"
- Deleted 9 empty workflow stub files, consolidated into engineering docs
- Updated parallel development model: clones as default (multi-machine), worktrees as optional local optimization

### Infrastructure Created
- Contract change proposal template (`docs/workflow/templates/proposal-contract-change.md`)
- Conformance test infrastructure (`tests/conformance/README.md` — pytest format, naming, capability markers)
- Contracts directory (`docs/contracts/README.md` — inventory of 4 expected contracts, MAJOR.MINOR versioning)
- PR template (`.github/pull_request_template.md`)
- CODEOWNERS file mapping tool dirs to agents, shared areas to integration
- Spec changelog (`spec/CHANGELOG.md`)
- Architecture decision records directory (`docs/engineering/decisions/README.md`)
- Shared library protocol (`libs/README.md`)

### Tool Scaffolding
- Created CLAUDE.md and work.md for compiler, binder, and simulator
- Each tool agent has role definition, scope boundaries, and references to engineering process

### Process Additions
- Inter-agent communication protocol (Section 4 in general-dev-process.md): tool→integration requests, integration→tool work items, session start protocol, conformance test coordination
- Work item size guidance with examples of well-sized vs poorly-sized items
- Provisional conformance provision in spec-int-dev-process.md (addresses interpreter-first serial bottleneck)

### GitHub Setup
- Initialized git repository, pushed to `git@github.com:frank-ceva/nem.git`
- Created branch structure: `main`, `integration/main`, `agent/interpreter/main`, `agent/compiler/main`, `agent/binder/main`, `agent/simulator/main`

---

# NEM spec update
status=completed

Updated the NEM specification to support sub-byte element types, classify implementation priorities, and improve document navigability.

## Summary

### Sub-byte type support (bitwidth)
- Defined `bitwidth(E)` formally in a new "Element Bitwidth" subsection of the Type System, with a table mapping all element types to their bit widths
- Renamed "Byte Extent Consistency" to "Extent Consistency" and replaced `sizeof(E)` (undefined, byte-based) with `bitwidth(E)` (formally defined, bit-based)
- Updated the extent formula to `byte_extent >= ⌈num_elements(S) * bitwidth(E) / 8⌉` to correctly handle sub-byte types like `i4`
- Added sub-byte packing notes to Buffers, Regions, and Layout/Strides sections
- Added normative note that intra-byte packing order is device-defined

### Implementation priority for deferred features
- Added "Implementation Priority (Informative)" subsection after the NPM Hardware Support Status table
- Classified all spec features into Priority 1 (required for current NPM hardware) and Priority 2 (may be deferred)
- Priority 2 includes: conv1d/conv3d/depthwise_conv2d, reduction ops, standalone quantize/dequantize, multi-engine/multi-NMU, @resource/@deterministic/@memmove decorators, device inheritance, softmax

### Document structure improvements
- Added "Document Roadmap" section after Architectural Positioning listing section order and noting key forward references
- Added explicit forward-reference annotations for: @resource decorator, device configuration, bounded pipelining
- Replaced undefined "Device Capability Descriptor" reference with correct "device configuration" cross-reference
- Clarified previously undefined "import/pinning" buffer attribute as an import flag
- Added "Restructuring Recommendations (Informative)" section with 5 concrete editorial suggestions:
  1. Move Design Principle before Core Program Objects
  2. Add a brief Decorators overview before Task Taxonomy
  3. Extract Device Configuration into its own top-level section
  4. Consolidate Type System and Extent Consistency
  5. Define buffer import semantics

### Changelog
- Updated `spec/CHANGELOG.md` with detailed entry covering all changes and their impact on tools

---

# Whitepaper update
status=completed

Restructured the NEM whitepaper for easier reading, reduced comparison tables, and added three annotated examples.

## Summary

### Whitepaper restructuring (`spec/nem_whitepaper.md`)
- Added new "NEM in Action" section with 3 annotated examples placed before the comparison section, so readers see concrete NEM code early
- Reduced "Comparative Analysis" to "Where NEM Fits": removed the Concept Template table and Master Comparison Table (both already available in `comparison_tables.md`), kept only the Quick-Reference Support Matrix (visual checkmark table)
- Added explicit cross-reference to `comparison_tables.md` for detailed per-model analysis
- Each example includes a "What to notice" callout highlighting key NEM concepts demonstrated
- Net effect: comparison section reduced from ~158 lines (3 dense tables) to ~76 lines (1 visual matrix + observations); examples section adds ~230 lines of annotated code

### New example files in `examples/`
- `examples/gemm_bias_relu.nem` — Tiled GEMM + bias + ReLU pipeline (f16, fully-connected / transformer attention layer)
- `examples/conv2d_maxpool.nem` — Two-stage Conv2D + MaxPool pipeline (i8, classification network pattern)
- Both follow the same structural patterns as the existing `examples/conv2d_relu.nem`

### Examples integrated into whitepaper
- **Example 1 — Conv2D + ReLU**: Tiled inference pipeline with ping-pong buffers (integrated from existing `conv2d_relu.nem`)
- **Example 2 — GEMM + Bias + ReLU**: Demonstrates uniform execution model across operation types, f16/f32 accumulation, `@readonly` bias
- **Example 3 — Conv2D + MaxPool**: Multi-op pipeline showing token chaining between stages, `@materialized` intermediate, and fusion control

---

# Domain-specific framework
status=completed

Reviewed existing domain-specific languages, IRs, and toolchain frameworks for relevance to NEM. Produced a comparative analysis concluding that NEM should remain a standalone language with a custom-built toolchain.

## Summary

### Language-level alternatives evaluated
- **MLIR custom dialect**: Closest infrastructure match, but fundamentally incompatible — MLIR does not provide the stability contract NEM requires. NEM is what MLIR lowers *to*, not what it *is*.
- **TOSA / StableHLO**: Stable operator sets, but operate at the graph/computation level — no memory hierarchy, no data movement, no scheduling. Wrong abstraction level.
- **Exo (exocompilation)**: Most conceptually similar — explicit memory hierarchy, user-schedulable. But Exo is a productivity compiler, not an architectural contract. No stability guarantees, no device type families.
- **Halide / TVM / Triton**: Scheduling DSLs and kernel languages. NEM is a *target* for these tools, not a replacement for them.

### Toolchain infrastructure evaluated
- **Parser generators (ANTLR, Lark, Tree-sitter)**: NEM's grammar is small (~120 productions) and LL(1)-friendly. Hand-written recursive descent provides better error messages, zero dependencies, and full control. Tree-sitter recommended separately for the VS Code extension.
- **Language workbenches (Langium, Xtext, Spoofax)**: All are Java or TypeScript — incompatible with NEM's Python toolchain decision. Validation complexity far exceeds what workbenches can auto-generate.
- **MLIR/xDSL as infrastructure**: C++ dependency (MLIR) or research instability (xDSL) conflicts with `nemlib`'s zero-dependency pure Python design.

### Conclusion
No existing framework can serve as NEM's foundation. NEM occupies a unique niche (stable execution contract for a software-managed accelerator) that no existing framework was designed to fill. The whitepaper's positioning analysis is validated. Two targeted opportunities identified:
1. Tree-sitter grammar for VS Code extension (incremental parsing, syntax highlighting)
2. MLIR Python bindings for the Compiler's input side (consuming MLIR, producing NEM)

### Artifact produced
- `docs/architecture/domain-specific-framework-analysis.md` — full 359-line comparative analysis

---

# Remove baseline keyword
status=completed

Replaced the implicit `baseline` keyword mechanism with explicit device inheritance and parseable NEM code. All conformant devices now inherit from a standard baseline device file instead of referencing a magic string.

## Summary

### New baseline device file (`examples/nem_baseline_1.0.nem`)
- Created standard baseline file containing all type_family definitions (conv2d, gemm, eltwise, view, cast, quantize, dequantize) and an abstract device `nem_baseline_1_0` listing all 15 MUST-class variants in `opcode.mandatory`
- All conformant NEM 1.0 devices MUST inherit from this device

### Spec grammar changes (`spec/nem_spec.md`)
- Removed `baseline_clause` production entirely
- Relaxed inheritance: derived devices can now set `topology` and add to `opcode.mandatory` (previously only `opcode.extended` allowed)
- Added `derived_body ::= topology_block? opcode_mandatory_block? opcode_extended_block?`
- Abstract devices (no topology) now permitted
- Extended document grammar: `config_document ::= { type_family_decl | device_config }`
- Fixed `family_id ::= ID ( "." ID )?` (was `ID "." ID`, broke for eltwise/cast/view)
- Made type_instantiation optional in `variant_ref` (supports `cast.default`)

### Spec semantic changes (`spec/nem_spec.md`)
- Replaced "Baseline Type Family Set" with "MUST Variant Reference (Informative)"
- Fixed `cast.any_supported` → `cast.default` variant reference inconsistency
- Rewrote Schema Rules: removed baseline-match and implicit-MUST rules (8 → 6 rules)
- Simplified effective set: `effective[op] = opcode.mandatory[op] ∪ opcode.extended[op]`
- Updated Conformance Rule: devices must list MUST variants in `opcode.mandatory`
- Rewrote 7 Inheritance Rules for topology override, opcode.mandatory union, abstract parents
- Extended Include Semantics for type_family imports

### Examples updated
- All device config examples in spec, whitepaper, and `examples.md` now use `include "nem_baseline_1.0.nem"` and `extends nem_baseline_1_0`
- `examples/device.nem` updated (removed inline type_family defs, added include/extends)
- `tools/vscode_ext/examples/npm_lite.cfg` updated

### Tool updates
- VS Code extension: removed `baseline` from keyword-config syntax pattern
- Interpreter spec: removed `baseline` field from DeviceConfigNode/DeviceConfig, updated device resolution algorithm and effective set formula

### Changelog
- Updated `spec/CHANGELOG.md` with detailed entry covering all changes and their impact

---

# Add `const` declarations to NEM
status=completed

Added compile-time named integer constant declarations to the NEM language, resolving the problem of undeclared variables in all NEM code examples.

## Summary

### Spec changes (`spec/nem_spec.md`)
- Added `const_decl ::= "const" ID "=" expr` to the grammar's `decl` production
- Added new normative section "Constant Declarations" (between Loops and Formal Language Definition) defining:
  - Immutable, integer-valued, program-scoped constants
  - Constant expression evaluation rules (integer literals + previously-declared constants + `+`, `-`, `*`, `/`, `mod`, parentheses)
  - Forward reference prohibition, duplicate name prohibition, loop body prohibition
  - Division by zero as a static error, name uniqueness with let/buffer/token names
  - Usage in all `expr` contexts (buffer sizes, region offsets/extents, shape dims, loop bounds, compute attrs)
- Updated Document Roadmap: added "Constant Declarations" as item 11
- Updated Implementation Priority: added `const` declarations to Priority 1 table

### Whitepaper examples (`spec/nem_whitepaper.md`)
- Added `const` preambles to all 3 examples (conv2d_relu, gemm_bias_relu, conv2d_maxpool)
- Replaced all `size=...` L2 buffer placeholders with computed expressions using declared constants
- Used realistic values (e.g., TiH=16, TiW=16, Cin=64, Cout=128)

### Examples.md (`spec/examples.md`)
- Added `const` preambles to both NEM programs (conv2d_relu, gemm_relu_multi_cstl)
- Replaced all `size=...` L2 buffer placeholders with computed expressions

### Conformance tests (`tests/conformance/const/`)
- Created 10 test files with 32 test cases covering:
  - Basic declarations, derived constants, all operators
  - Usage in buffer/region/shape/loop contexts
  - Error conditions: forward references, duplicates, loop body placement, division by zero, name shadowing
  - Full program end-to-end test

### Tool propagation
- Created work items in `tools/interpreter/work.md`, `tools/compiler/work.md`, `tools/binder/work.md`, `tools/simulator/work.md` for parser + semantic support of `const`

### Changelog
- Updated `spec/CHANGELOG.md` with detailed entry covering all changes and impact on tools

---

# Align all NEM code with latest spec (const declarations and spec compliance)
status=completed

Reviewed all NEM code across the project (standalone .nem files and embedded examples in .md files) and fixed spec compliance issues introduced after the `const` declaration feature was added.

## Summary

### Standalone .nem files updated with const declarations
- **`examples/conv2d_relu.nem`** — Added 13 `const` declarations (TiH, TiW, Cin, Cout, Kh, Kw, ToH, ToW, T, tileX_bytes, tileW_bytes, tileY_bytes, bias_bytes). Replaced `size=...` placeholders with computed expressions.
- **`examples/gemm_bias_relu.nem`** — Added 9 `const` declarations (TiM, K, N, T, elem_bytes, tileA_bytes, tileB_bytes, tileY_bytes, bias_bytes). Replaced `size=...` placeholders with computed expressions.
- **`examples/conv2d_maxpool.nem`** — Added 15 `const` declarations (TiH, TiW, Cin, Cout, Kh, Kw, ToH, ToW, ToH_p, ToW_p, T, tileX_bytes, tileW_bytes, tileC_bytes, tileY_bytes). Replaced `size=...` placeholders with computed expressions.

### Device config spec compliance fixes
- **`examples/npm_lite_.nem`** — Removed `spec_version = "NEM-1.0"` from derived device. Per spec: "A derived device MUST NOT specify spec_version — it is always inherited from the parent."
- **`tools/vscode_ext/examples/npm_lite.cfg`** — Same fix: removed `spec_version` from derived device.

### Grammar compliance fixes
- **`tools/vscode_ext/examples/conv2d_relu.nem`** — Changed `IN`/`OUT` (capitalized) to `in`/`out` (lowercase) to match the EBNF grammar which defines `"in"` and `"out"` as lowercase keywords.
- **`spec/examples.md`** — Changed `//` comments to `#` comments in two device config code blocks. The NEM grammar defines `comment ::= "#" { any_char_except_newline } NEWLINE`; `//` is not a valid NEM comment syntax.

### Files already correct (no changes needed)
- `spec/nem_spec.md` — Spec examples already had const declarations
- `spec/nem_whitepaper.md` — All 3 embedded examples already had const declarations
- `spec/examples.md` — NEM program code blocks already had const declarations (only device config comment syntax fixed)
- `examples/npm_baseline_1.0.nem` — Type family catalog, no constants needed
- `spec/comparison_tables.md` — No NEM code
- `docs/architecture/domain-specific-framework-analysis.md` — No NEM code
- `tools/interpreter/interpreter_spec.md` — Python API snippets only, not full NEM programs

---

# Incremental NEM development plan
status=completed

Defined a detailed 8-step incremental development plan for Phase 1 of the NEM toolchain, covering nemlib (shared library), interpreter, conformance tests, and infrastructure. The "Common infrastructure" work item was folded into this plan as Step 1 builds nemlib as the shared foundation.

## Summary

### Plan structure (`plan/phase_1/`)
- **master.md** — Overall 8-step plan with dependency graph, agent responsibilities (integration agent vs interpreter agent), git branch strategy, milestones, and explicitly deferred items
- **libs.md** — nemlib shared library: 6-layer architecture (diagnostics → core → parser → device → types → validation), per-step module build plan, key interfaces (DiagnosticCollector, parse(), DeviceConfig, match_opcode_instance(), validate())
- **interpreter.md** — Interpreter: per-step module build plan (memory model, execution engine, compute backend, device integration, validation wiring), package structure under neminterp/
- **tests.md** — Two-tier tool-agnostic conformance test architecture with ConformanceRunner protocol enabling the same tests to run against both the interpreter and future compiler+binder+simulator pipeline
- **infra.md** — Python packaging (pyproject.toml for nemlib and interpreter), Makefile targets, ruff + mypy configuration, opcode registry loading strategy
- **integration.md** — Per-step completion criteria, Phase 1 definition of done (9 criteria), cross-component validation points, synchronization protocol

### 8-step incremental plan
1. Infrastructure + Lexer + Constants (program header, const declarations, integer expressions)
2. Storage Declarations + Memory Model (buffers, regions, decorators syntax-only)
3. Data Movement + Execution Engine (transfer, store, wait, token assignments, deps)
4. Loops + Pipelining (loop/endloop, @max_in_flight, runtime expressions)
5. Compute Operations (all compute task syntax, elementwise ops, gemm, conv2d)
6. Device Configuration + Registry (device config grammar, inheritance, include, resolver) — parallel with Steps 3-5
7. Remaining Opcodes + Type Extensions (pooling, norm, softmax, layout, cast, quantize, INT4)
8. Semantic Analysis + Decorators (10 validation passes, type family matching, decorator enforcement)

### Key design decisions
- **Libs-first strategy**: nemlib built before interpreter, providing shared parsing/validation/device model
- **Common infrastructure folded in**: The separate "Common infrastructure" work item was subsumed — nemlib IS the common infrastructure
- **Tool-agnostic conformance**: ConformanceRunner protocol with validate() and execute() methods, parametrized pytest fixture runs all tests against all available backends
- **Two-tier testing**: Validation tier (accept/reject NEM source) + Execution tier (input → output with .npy fixtures)
- **Parallel tracks**: Steps 3-5 (execution) and Step 6 (device config) can proceed independently, converging at Step 7
- **~8 steps**: Each step adds specific language constructs, building from minimal parseable programs to full language coverage

---

# Common infrastructure
status=completed

Folded into the "Incremental NEM development plan" work item above. The common infrastructure is nemlib (`libs/nemlib/`), a 6-layer shared Python library providing diagnostics, core types, parser, device model, type system, and validation pipeline. All tools import from nemlib rather than duplicating parsing or validation logic. See `plan/phase_1/libs.md` for the detailed build plan.

---

# Extend NEM device model for full NPM architectural coverage
status=completed

Extended the NEM specification's device configuration model, opcode set, and type system to cover the full NPM hardware architecture. Decomposed into 4 work items (A-D) with 8 architectural decisions.

## Summary

### Work Item A: Device Topology and Unit Model
- Extended Execution Units section with Per-Engine table (NMU, CSTL, DMA, VPU, SEQ) and Device-Level table (sDMA, WDM)
- Added sDMA (DDR↔L2 transfers), WDM (weight decompression), VPU (programmable vector), SEQ (sequencer) descriptions
- Extended `unit_type` grammar: added VPU, SEQ, sDMA, WDM
- Extended `topology_block` grammar: added `l2_size_bytes`, `device_units_block`, `l1_size_bytes`
- Added `unit_characteristics` grammar: per-unit-type key-value properties (e.g., NMU.int8_macs, SEQ.max_active_tokens)
- Added @resource-invalid rule: SEQ, sDMA, WDM are NOT valid @resource targets
- Updated Schema Rules: unit counts, memory capacity, MUST variants
- Updated Inheritance Rules: 8 rules (was 7), added unit_characteristics merge inheritance
- Updated all device config examples in spec, examples.md, and standalone .nem files

### Work Item B: New Opcodes
- Added FLOAT literal grammar: `FLOAT ::= DIGIT+ "." DIGIT+ ( [eE] [+-]? DIGIT+ )?`
- Extended `primary` to accept FLOAT (restricted to compute attributes only)
- Added 6 new opcodes: `layernorm`, `rmsnorm`, `softmax`, `log_softmax`, `gelu`, `silu`
- Added `norm<T>` type family (MUST f16, MAY bf16/f32) covering layernorm/rmsnorm
- Added `softmax<T>` type family (MUST f16, MAY bf16/f32) covering softmax/log_softmax
- gelu/silu reuse existing `eltwise<T>` family (AD-5)
- Updated NPM Hardware Support Status, Priority tables, MUST/MAY Variant tables
- Updated baseline device file with norm/softmax type families and MUST variants

### Work Item C: Type System Extensions
- Formalized `quant_desc` grammar: `per_tensor_quant`, `per_channel_quant`, `per_group_quant` productions
- Added per-group quantization: `per_group(axis, group_size, scales[], zero_points[])`
- Added `gemm.int4` type family: non-parameterized, i4 weights × i8 activations, MAY-class
- Added `conv2d.int4` type family: non-parameterized, i4 weights × i8 activations, MAY-class
- Updated MAY Variant Inventory, Hardware Support Status, Priority tables
- Updated baseline device file with INT4 type family definitions

### Work Item D: Examples, Baseline Update, and Tool Propagation
- Verified baseline device file: 13 type families, 17 MUST variants
- Created `examples/gemm_rmsnorm.nem`: GEMM + RMSNorm transformer MLP pipeline
- Added 10 conformance test files (43 test cases) across device_config, opcodes, types directories
- Created tool propagation work items in all 4 tool work.md files

### Architectural Decisions
- AD-1: @resource-invalid unit types (SEQ, sDMA, WDM)
- AD-2: Device-level units are informational for the binder
- AD-3: Memory sizes as required fields (breaking change)
- AD-4: Unit characteristics merge inheritance
- AD-5: gelu/silu reuse eltwise type family
- AD-6: INT4 type families use non-parameterized form
- AD-7: quant_desc grammar formalization
- AD-8: FLOAT literal grammar extension
