This file lists all major work items to be worked on, or currently being worked on, in priority order.

# Consume opcode registry

**Requested by: spec-int (Extract opcode definitions into a machine-readable registry)**

The NEM spec now delegates opcode signatures to `spec/registry/opcodes.yaml`. See `spec/CHANGELOG.md` and `docs/contracts/opcode-registry.md`.

The binder should:
- Load `spec/registry/opcodes.yaml` at initialization instead of hardcoding opcode tables.
- Use registry data for operand validation.
- Use `execution_unit` field for execution unit routing (which unit handles each opcode).
- Use `hardware_status` field to flag unsupported opcodes during binding.

---

# Extend NEM device model and add new opcodes

**Requested by: spec-int (Extend NEM device model for full NPM architectural coverage)**

The NEM spec has been significantly extended. See `spec/CHANGELOG.md` entries dated 2026-02-12 for:
- Device Topology and Unit Model
- New Opcodes (softmax, layernorm, rmsnorm, gelu, silu)
- Type System Extensions (INT4, per-group quantization)

The binder must support:

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

## Binder-specific changes

1. **Memory capacity validation**: Validate that sum of buffer sizes at each level fits within declared l1_size_bytes/l2_size_bytes.
2. **unit_characteristics consumption**: Use NMU MAC counts for scheduling/tiling decisions, SEQ.max_active_tokens for token limit enforcement.
3. **sDMA/WDM awareness**: Select sDMA for DDR↔L2 transfers, engine DMA for L2↔L1. Use WDM count for compressed weight transfer scheduling.
4. **New opcode support**: Handle `layernorm`, `rmsnorm`, `softmax`, `log_softmax`, `gelu`, `silu` in lowering to TCB.
5. **INT4 support**: Handle i4 × i8 mixed-precision GEMM and Conv2D, weight layout for i4 packing.
6. **Per-group quantization**: Handle per-group quant descriptor unpacking/repacking during lowering.

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

The NEM spec now includes `const` declarations (see `spec/CHANGELOG.md`). The binder must support:

1. **Parser**: Add `const_decl` production: `"const" ID "=" expr`. Add to `decl` alternatives.
2. **AST/IR**: Add `ConstDeclNode(name, expr)`. Evaluate constant expressions during semantic analysis.
3. **Semantic checks**: Forward references, duplicate names, loop body prohibition, division by zero, name conflicts.
4. **Lowering**: All constant values must be resolved before TCB generation. Buffer sizes, region offsets, shapes, and loop bounds must use concrete integer values.
5. **Conformance**: Pass all tests in `tests/conformance/const/`.
