This file lists all major work items to be worked on, or currently being worked on, in priority order: the upper one is the first to work on.

# Consume opcode registry

**Requested by: spec-int (Extract opcode definitions into a machine-readable registry)**

The NEM spec now delegates opcode signatures to `spec/registry/opcodes.yaml`. See `spec/CHANGELOG.md` and `docs/contracts/opcode-registry.md`.

The interpreter should:
- Load `spec/registry/opcodes.yaml` at initialization instead of hardcoding opcode tables.
- Use registry data for operand validation (count, direction, required/optional).
- Use registry data for attribute validation (type, required, defaults).
- Use `type_families` references for type legality checks against the active device config.
- Validate the registry against `spec/registry/schema.json` on load (optional, for development builds).

---

# Extend NEM device model and add new opcodes

**Requested by: spec-int (Extend NEM device model for full NPM architectural coverage)**

The NEM spec has been significantly extended. See `spec/CHANGELOG.md` entries dated 2026-02-12 for:
- Device Topology and Unit Model
- New Opcodes (softmax, layernorm, rmsnorm, gelu, silu)
- Type System Extensions (INT4, per-group quantization)

The interpreter must support:

## Parser changes

1. **FLOAT literal**: New lexical token `FLOAT`. Extend `primary` to accept FLOAT. FLOAT is valid only in compute attribute values (epsilon, alpha).
2. **Extended topology_block**: `l2_size_bytes`, `device_units` block (sDMA, WDM counts), `l1_size_bytes` in per_engine.
3. **New unit_type values**: `VPU`, `SEQ`, `sDMA`, `WDM` (in addition to existing NMU, CSTL, DMA).
4. **unit_characteristics block**: Per-unit-type key-value attributes in device configs.
5. **quant_desc grammar**: Formalize `per_tensor`, `per_channel`, `per_group` quantization descriptor productions.
6. **New opcodes**: `layernorm`, `rmsnorm`, `softmax`, `log_softmax`, `gelu`, `silu`.
7. **New type families**: `norm<T>`, `softmax<T>`, `gemm.int4`, `conv2d.int4`.

## Semantic analysis changes

1. **@resource validation**: SEQ, sDMA, WDM are NOT valid @resource targets (static error).
2. **Memory capacity rule**: Sum of buffer sizes at a given level MUST NOT exceed declared capacity.
3. **unit_characteristics inheritance**: Merge semantics (per-key override within unit type).
4. **FLOAT restriction**: FLOAT literals only in compute attributes, not in buffer sizes/region offsets/shapes/loop bounds/const.
5. **Normalization validation**: `epsilon` (FLOAT, required), `axis` (INT, required), optional scale/bias operands.
6. **Softmax validation**: `axis` (INT, required), shapes must match.
7. **INT4 type family checking**: `gemm.int4` and `conv2d.int4` with fixed type combinations.
8. **Per-group quant validation**: `group_size` must be positive, array lengths must equal ⌈dim[axis]/group_size⌉.

## Runtime changes

1. **New opcode execution**: Implement `layernorm`, `rmsnorm`, `softmax`, `log_softmax`, `gelu`, `silu` in compute backend.
2. **INT4 compute**: Support i4 × i8 mixed-precision GEMM and Conv2D.
3. **Per-group dequantization**: Support per-group quant descriptor unpacking.

## Conformance

Pass all tests in:
- `tests/conformance/device_config/`
- `tests/conformance/opcodes/`
- `tests/conformance/types/`

## Spec references

- Affected sections: Execution Units, Decorators, Device Configuration, Formal Language Definition (Grammar), Opcode Signatures, Type System, Appendix
- Changelog: `spec/CHANGELOG.md` — 3 entries dated 2026-02-12

# NEM interpreter
**Current phase: Architecture spec written** — see [interpreter_spec.md](interpreter_spec.md)

I need to build a NEM interpreter that is capable of executing NEM programs and/or instructions.
I want the interpreter to be built as a python library so that I benefit from all the existing python environment.
The interpreter needs to ensure:
- correct functional behavior
- check for language rules
All as defined in the NEM spec (nem_spec.md)
To help building the interpreter, a python library of all NMU and CSTL compute functions is available and provides bit-true accuracy vs actual hardware.

## Completed: Architecture Specification
status=completed

Architecture specification written in interpreter_spec.md, covering:
- [x] User interface (Python API: load, run, step, inspect, display buffers, breakpoints)
- [x] Threading model (cooperative single-threaded event loop, task graph + ready queue, multi-engine modeling)
- [x] Execution modes: functional (dependency-only) and timed (resource-aware abstract scheduling) — single implementation with mode switch recommended
- [x] Device specification integration (parsing, inheritance resolution, effective type family set, topology enforcement)
- [x] Runtime test environment (DDR/L2/L1 as sized byte arrays, DDR pre-loading/post-read API)
- [x] Compute backend architecture (pluggable: NumPy fallback + NpmPyTorchApi bit-true backend)
- [x] Parser design (recursive descent, full EBNF grammar coverage)
- [x] Semantic analysis (10 validation passes)
- [x] Testing strategy and implementation roadmap (7 phases)

## Add `const` declaration support

**Requested by: spec-int (const declarations work item)**

The NEM spec now includes `const` declarations (see `spec/CHANGELOG.md`). The interpreter must support:

1. **Parser**: Add `const_decl` production: `"const" ID "=" expr`. Add to `decl` alternatives.
2. **AST**: Add `ConstDeclNode(name, expr)` node type.
3. **Semantic analysis**:
   - Evaluate constant expressions at parse/analysis time (integer literals + previously-declared constants + `+`, `-`, `*`, `/`, `mod`, parens).
   - Reject forward references (ID not yet declared as const).
   - Reject duplicate const names.
   - Reject `const` inside loop bodies.
   - Reject name conflicts with buffers, let bindings, token assignments.
   - Reject division by zero.
4. **Runtime**: Substitute constant values in all `expr` evaluation contexts (buffer sizes, region offsets/extents, shape dims, loop bounds, compute attributes).
5. **Conformance**: Pass all tests in `tests/conformance/const/`.

## Remaining: Implementation
The following implementation phases are defined in the spec:
- Phase 1: Core Infrastructure (lexer, parser, AST, device config, memory model)
- Phase 2: Functional Execution (task graph, scheduler, compute backends)
- Phase 3: Semantic Analysis (type families, hazard checking)
- Phase 4: User Interface (NemInterpreter class, DDR management, inspection)
- Phase 5: Timed Mode (cost model, resource contention)
- Phase 6: NpmPyTorchApi Integration (bit-true compute)
- Phase 7: Polish (Jupyter, error messages, packaging)
