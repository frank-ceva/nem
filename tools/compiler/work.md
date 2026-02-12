This file lists all major work items to be worked on, or currently being worked on, in priority order.

# Consume opcode registry

**Requested by: spec-int (Extract opcode definitions into a machine-readable registry)**

The NEM spec now delegates opcode signatures to `spec/registry/opcodes.yaml`. See `spec/CHANGELOG.md` and `docs/contracts/opcode-registry.md`.

The compiler should:
- Load `spec/registry/opcodes.yaml` at initialization instead of hardcoding opcode tables.
- Use registry data for operand validation during lowering.
- Use registry data for attribute validation (type, required, defaults).
- Use `type_families` references for type legality checks.
- Use `execution_unit` field for code generation routing (NMU vs CSTL vs DMA).

---

# Extend NEM device model and add new opcodes

**Requested by: spec-int (Extend NEM device model for full NPM architectural coverage)**

The NEM spec has been significantly extended. See `spec/CHANGELOG.md` entries dated 2026-02-12 for:
- Device Topology and Unit Model
- New Opcodes (softmax, layernorm, rmsnorm, gelu, silu)
- Type System Extensions (INT4, per-group quantization)

The compiler must support:

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

## Code generation changes

1. **New opcode lowering**: Generate TCBs for `layernorm`, `rmsnorm`, `softmax`, `log_softmax`, `gelu`, `silu`.
2. **INT4 lowering**: Handle i4 × i8 mixed-precision GEMM and Conv2D TCB generation.
3. **Per-group quant metadata**: Propagate per-group quantization descriptors through lowering.
4. **Memory capacity**: Validate buffer allocations against declared l1/l2 sizes.

## Conformance

Pass all tests in:
- `tests/conformance/device_config/`
- `tests/conformance/opcodes/`
- `tests/conformance/types/`

## Spec references

- Affected sections: Execution Units, Decorators, Device Configuration, Formal Language Definition (Grammar), Opcode Signatures, Type System, Appendix
- Changelog: `spec/CHANGELOG.md` — 3 entries dated 2026-02-12

# Add `const` declaration support

**Requested by: spec-int (const declarations work item)**

The NEM spec now includes `const` declarations (see `spec/CHANGELOG.md`). The compiler must support:

1. **Parser**: Add `const_decl` production: `"const" ID "=" expr`. Add to `decl` alternatives.
2. **AST/IR**: Add `ConstDeclNode(name, expr)`. Evaluate constant expressions during semantic analysis.
3. **Semantic checks**: Forward references, duplicate names, loop body prohibition, division by zero, name conflicts.
4. **Code generation**: Substitute constant values wherever `expr` appears (buffer sizes, region offsets, shapes, loop bounds, compute attrs).
5. **Conformance**: Pass all tests in `tests/conformance/const/`.
