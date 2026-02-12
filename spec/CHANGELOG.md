# Spec Changelog

All notable changes to the NEM specification (`spec/nem_spec.md`) are documented here.

Tool agents should consult this file at the start of each work session to identify spec changes that require implementation updates.

## Format

Each entry follows this format:

```
## [Date] — Short title

### Changed
- Description of what changed and why.
- Spec section reference (e.g., "Section 4.3 — Task Graph Semantics").

### Impact
- Which tools are affected.
- Whether conformance tests were added/modified.
- Whether contracts were updated.
```

---

## [2026-02-12] — Extract Opcode Signatures into Machine-Readable Registry

### Changed
- **Opcode Registry created:** `spec/registry/opcodes.yaml` now defines the formal operand
  structure, attributes, type family associations, execution unit mapping, and hardware
  support status for all 49 NEM opcodes. This is the single source of truth for opcode
  signatures.
- **Registry schema:** `spec/registry/schema.json` (JSON Schema draft 2020-12) enforces
  structural validity. Validation via `python3 spec/registry/validate.py`.
- **Spec section replaced:** The "Opcode Signatures (Normative)" section previously
  contained ~280 lines of inline opcode definitions. It now contains a normative
  reference to `spec/registry/opcodes.yaml`, delegating opcode catalog ownership to the
  registry while the spec retains ownership of semantic rules (type promotion,
  broadcasting, execution ordering, memory model).
- **Contract added:** `docs/contracts/opcode-registry.md` documents the registry's
  normative status, schema, consumption patterns, and change process.

### Impact
- **All tools affected.** Tools should consume opcode metadata from `spec/registry/opcodes.yaml`
  instead of hand-coding opcode tables. Work items added to each tool's `work.md`.
- **VSCode extension affected.** Syntax highlighting opcode regex
  (`tools/vscode_ext/syntaxes/nem.tmLanguage.json` line 73) should be generated from
  the registry in the future.
- **Conformance tests:** `tests/conformance/registry/test_registry.py` validates
  registry well-formedness and cross-references.
- **Contract updated:** `docs/contracts/README.md` inventory includes the new
  Opcode Registry contract.

---

## [2026-02-12] — Examples, Baseline Update, and Tool Propagation

### Changed
- **Baseline device file verified:** `examples/npm_baseline_1.0.nem` confirmed to contain
  all type family definitions (conv2d.float, conv2d.int8, conv2d.int4, gemm.float,
  gemm.int8, gemm.int4, eltwise, view, norm, softmax, cast, quantize, dequantize) and
  all 17 MUST-class variants in `opcode.mandatory`.

- **New example added:** `examples/gemm_rmsnorm.nem` — GEMM + RMSNorm tiled pipeline
  demonstrating the new `rmsnorm` opcode with `epsilon` FLOAT literal, `@readonly` scale
  vector, `@materialized` intermediate, and token dependency chaining. Represents a
  transformer MLP block pattern.

- **Conformance tests added:** 10 new test files (43 total cases) across 3 directories:
  - `tests/conformance/device_config/` — device_units, memory_sizes,
    unit_characteristics, resource_invalid (19 cases)
  - `tests/conformance/opcodes/` — normalization, softmax, activations (14 cases)
  - `tests/conformance/types/` — float_literal, quant_desc, int4_families (10 cases)

- **Tool propagation work items created:** Work items added to
  `tools/interpreter/work.md`, `tools/compiler/work.md`, `tools/binder/work.md`,
  `tools/simulator/work.md` covering all parser, semantic analysis, and runtime
  changes needed to support the extended device model and new opcodes.

### Impact
- **All tools affected.** Each tool has a new top-priority work item describing the
  required changes. See individual `tools/*/work.md` files.
- **Conformance tests:** 43 new test cases ready for tool implementations to validate
  against. All tests are currently stubs (`pass` bodies) to be wired to parsers.
- **No spec changes.** This work item only adds examples, tests, and tool work items.

---

## [2026-02-12] — Type System Extensions (INT4, per-group quantization)

### Changed
- **`quant_desc` grammar formalized:** Added `quant_desc`, `per_tensor_quant`,
  `per_channel_quant`, and `per_group_quant` productions to the EBNF. Previously
  `quant_desc` was referenced in `type_attrs` but never formally defined.
  Section: "Formal Language Definition > Grammar".

- **Per-group quantization descriptor added:** New `per_group(axis=<INT>,
  group_size=<INT>, scales=[...], zero_points=[...])` form. Groups of `group_size`
  elements along the specified axis share a common scale and zero point. Array lengths
  MUST equal `⌈dim[axis] / group_size⌉`. This is the dominant format for INT4 LLM
  weight compression.
  Section: "Type System > Quantization Descriptor".

- **Quantization Descriptor section rewritten:** Expanded from a brief two-line
  description to a complete reference covering all three forms (per-tensor, per-channel,
  per-group) with formal rules for array lengths and group size constraints.
  Section: "Type System > Quantization Descriptor".

- **`conv2d.int4` type family added (new):** Non-parameterized mixed-precision family
  (i4 weights × i8 activations, i32 accumulation, quant required). Two MAY variants:
  `no_bias` and `with_bias`. Section: "Appendix: Type Family Definitions > conv2d".

- **`gemm.int4` type family added (new):** Non-parameterized mixed-precision family
  (i4 weights × i8 activations, i32 accumulation, quant required). Two MAY variants:
  `no_bias` and `with_bias`. Section: "Appendix: Type Family Definitions > gemm".

- **MAY Variant Inventory updated:** Added `gemm.int4.no_bias`, `gemm.int4.with_bias`,
  `conv2d.int4.no_bias`, `conv2d.int4.with_bias`.
  Section: "MAY Variant Inventory".

- **NPM Hardware Support Status updated:** Added rows for Linear Algebra (INT4) and
  Convolution (INT4), both Supported on NMU.
  Section: "NPM Hardware Support Status".

- **Implementation Priority updated:** Added `gemm.int4`/`conv2d.int4` and
  `quant_desc` (all three forms) to Priority 1.
  Section: "Implementation Priority".

- **Variant Expansion tables updated:** Added `conv2d.int4` and `gemm.int4` rows to
  conv2d and gemm expansion tables.
  Section: "Variant Expansion Reference".

- **Baseline device file updated:** Added `conv2d.int4` and `gemm.int4` type family
  definitions to `examples/npm_baseline_1.0.nem`. These are MAY-class families (not
  added to `opcode.mandatory` — devices opt in via `opcode.extended`).

### Impact
- **All tools affected.** Parser must support `quant_desc` grammar with all three
  forms (per-tensor, per-channel, per-group). Must handle `gemm.int4` and `conv2d.int4`
  as non-parameterized type families.
- **Binder especially affected:** Must handle per-group quantization descriptor
  unpacking/repacking and INT4 weight layout.
- **Conformance tests needed:** `quant_desc` parsing (all three forms), INT4 type family
  validation, per-group array length rules. Tests will be added in Work Item D.
- **No contract changes.** IR schema, CLI, and diagnostics contracts are not affected.

---

## [2026-02-12] — New Opcodes (softmax, layernorm, rmsnorm, gelu, silu)

### Changed
- **FLOAT literal grammar added:** New lexical production
  `FLOAT ::= DIGIT+ "." DIGIT+ ( [eE] [+-]? DIGIT+ )?`. Extended `primary` to accept
  FLOAT. FLOAT literals are permitted only in compute attribute values (e.g., `epsilon`,
  `alpha`). Buffer sizes, region offsets, shape dimensions, loop bounds, and `const`
  declarations remain integer-only.
  Section: "Formal Language Definition > Grammar".

- **Normalization opcodes added:** `layernorm.async` and `rmsnorm.async` with operands
  X, optional scale/bias, output Y, and required attributes `axis` (INT) and `epsilon`
  (FLOAT). New "Normalization" subsection in Opcode Signatures.
  Section: "Opcode Signatures > Normalization".

- **Softmax opcodes added:** `softmax.async` and `log_softmax.async` with operands X,
  output Y, and required attribute `axis` (INT). New "Softmax" subsection in Opcode
  Signatures.
  Section: "Opcode Signatures > Softmax".

- **Activation opcodes added:** `gelu.async` and `silu.async` added to the existing
  unary elementwise operations list. Reuse existing `eltwise<T>` type family (AD-5).
  Section: "Opcode Signatures > Elementwise > Unary Operations".

- **`norm` type family added (new):** `norm<T: {f16, bf16, f32}>` covering `layernorm`
  and `rmsnorm` opcodes. Conformance: MUST `<f16>`, MAY `<bf16>`, MAY `<f32>`.
  Section: "Appendix: Type Family Definitions > Normalization Type Families".

- **`softmax` type family added (new):** `softmax<T: {f16, bf16, f32}>` covering
  `softmax` and `log_softmax` opcodes. Conformance: MUST `<f16>`, MAY `<bf16>`,
  MAY `<f32>`.
  Section: "Appendix: Type Family Definitions > Softmax Type Families".

- **MUST Variant Reference updated:** Added `norm<f16>.default` and
  `softmax<f16>.default` to the MUST variant table.
  Section: "MUST Variant Reference (Informative)".

- **MAY Variant Inventory updated:** Added `norm<bf16>.default`, `norm<f32>.default`,
  `softmax<bf16>.default`, `softmax<f32>.default` to the MAY variant table.
  Section: "MAY Variant Inventory".

- **NPM Hardware Support Status updated:** Added rows for Normalization (`layernorm`,
  `rmsnorm` — Supported on CSTL), Softmax (`softmax`, `log_softmax` — Supported on
  CSTL), and updated Elementwise row to include `gelu`, `silu`.
  Section: "NPM Hardware Support Status".

- **Implementation Priority updated:** Moved `softmax` from Priority 2 to Priority 1.
  Added `layernorm`, `rmsnorm`, `log_softmax`, `gelu`, `silu`, and FLOAT literals to
  Priority 1. Section: "Implementation Priority".

- **Variant Expansion tables added:** New `norm Expansion` and `softmax Expansion`
  tables in the appendix.
  Section: "Variant Expansion Reference".

- **Baseline device file updated:** Added `norm` and `softmax` type family definitions
  and MUST variants (`norm<f16>.default`, `softmax<f16>.default`) to
  `examples/npm_baseline_1.0.nem`.

### Impact
- **All tools affected.** Parser must support FLOAT lexical token, extended `primary`
  production, and 6 new opcode names (`layernorm`, `rmsnorm`, `softmax`, `log_softmax`,
  `gelu`, `silu`). Semantic analysis must validate `epsilon` and `axis` attributes,
  check operand shapes and types against `norm` and `softmax` type families.
- **Binder affected:** Must handle normalization and softmax op lowering to CSTL.
- **Baseline device:** Updated — tools parsing `npm_baseline_1.0.nem` must handle the
  new type families.
- **Conformance tests needed:** New opcode parsing, type family validation, FLOAT literal
  parsing, epsilon/axis attribute validation. Tests will be added in Work Item D.
- **No contract changes.** IR schema, CLI, and diagnostics contracts are not affected.

---

## [2026-02-12] — Device Topology and Unit Model

### Changed
- **Execution Units section rewritten:** Added Per-Engine unit table (NMU, CSTL, DMA, VPU,
  SEQ) and Device-Level unit table (sDMA, WDM). Added detailed descriptions of the sDMA vs
  engine DMA distinction (DDR<->L2 vs L2<->L1), WDM role (on-the-fly weight decompression),
  VPU role (programmable vector/scalar operations), and SEQ role (task dispatch and
  synchronization). Expanded task-to-unit mapping with new operations and units.
  Section: "Execution Units".

- **`unit_type` grammar extended:** Changed from `"NMU" | "CSTL" | "DMA"` to
  `"NMU" | "CSTL" | "DMA" | "VPU" | "SEQ" | "sDMA" | "WDM"`.
  Section: "Formal Language Definition > Grammar".

- **`topology_block` grammar extended:** Added `l2_size_bytes` (required, integer expression)
  at the topology level. Added `device_units_block` for device-level units (sDMA, WDM counts).
  Added `l1_size_bytes` (required, integer expression) inside `per_engine`. Added
  `device_units_block ::= "device_units" "{" { unit_decl } "}"`.
  Section: "Formal Language Definition > Grammar".

- **`unit_characteristics` grammar added:** New `unit_chars_block`, `unit_chars_group`, and
  `char_decl` productions for declaring per-unit-type key-value properties (e.g.,
  `NMU.int4_macs`, `SEQ.max_active_tokens`). Added to both `config_body` and `derived_body`.
  Section: "Formal Language Definition > Grammar".

- **@resource-invalid rule added:** SEQ, sDMA, and WDM are NOT valid `@resource` targets.
  Programs MUST NOT use `@resource` with these unit types; such usage is a static error.
  Valid `@resource` targets: NMU, CSTL, DMA, VPU.
  Section: "Decorators".

- **Schema Rules updated:** Added Rule 5 (per-engine unit counts ≥ 1, device_units MAY be 0,
  memory sizes > 0). Added Rule 6 (memory capacity — sum of buffer sizes at a given memory
  level MUST NOT exceed declared capacity). Renumbered MUST variant rule to Rule 7.
  Section: "Schema Rules".

- **Inheritance Rules updated:** Now 8 rules (was 7). Added Rule 4: `unit_characteristics`
  from a derived device merges with the parent's (per-key override within a unit type;
  additive across unit types). Updated Rules 1-2 to include `unit_characteristics` in the
  set of blocks that participate in inheritance.
  Section: "Inheritance Rules".

- **Device config examples updated:** All 4 device config examples in the spec (npm_lite,
  npm_mid, npm_pro, multi-file npm_pro) now include `l2_size_bytes`, `device_units` (sDMA,
  WDM), `per_engine` with VPU, SEQ, `l1_size_bytes`, and `unit_characteristics` blocks.
  Section: "Device Configuration" examples.

- **Standalone example files updated:** `examples/npm_lite_.nem` updated with full new
  topology. Section: companion file.

- **`spec/examples.md` device configs updated:** Both device configs (npm_lite,
  npm_quad_cstl) updated with full new topology including device_units, memory sizes,
  VPU, SEQ, and unit_characteristics.
  Section: companion document `examples.md`.

- **Quantization WARNING updated:** Reference to VPU as a declared unit type for standalone
  quantize/dequantize operations. Section: "Type System > Quantization".

### Impact
- **All tools affected.** Parser must support extended `unit_type` production (VPU, SEQ,
  sDMA, WDM), `device_units_block`, `l1_size_bytes`/`l2_size_bytes`, and
  `unit_characteristics` grammar. Semantic analysis must enforce @resource-invalid rule,
  memory capacity rule, and unit_characteristics merge inheritance.
- **Binder especially affected:** Must consume `unit_characteristics` for scheduling
  decisions, use `l1_size_bytes`/`l2_size_bytes` for buffer allocation validation, and
  be aware of sDMA/WDM counts for transfer path selection.
- **Conformance tests needed:** Device config parsing (new topology fields), @resource
  with invalid unit types (should be rejected), memory capacity validation, unit
  characteristics inheritance. Tests will be added in Work Item D.
- **No contract changes.** IR schema, CLI, and diagnostics contracts are not affected.

---

## [2026-02-12] — Add `const` declarations

### Changed
- **Grammar — `const_decl` added:** New production `const_decl ::= "const" ID "=" expr`
  added to `decl` alternatives. Section: "Formal Language Definition > Grammar".

- **Constant Declarations (new normative section):** Defines compile-time named integer
  constants. Semantics: immutable, integer-valued, program-scoped, evaluated in declaration
  order using existing `expr` grammar. Forward references, duplicate names, loop body
  placement, and division by zero are static errors. Constants usable anywhere `expr` is
  accepted (buffer sizes, region offsets/extents, shape dimensions, loop bounds, compute
  attributes). Section: "Constant Declarations".

- **Document Roadmap updated:** Added "Constant Declarations" as item 11.
  Section: "Document Roadmap".

- **Implementation Priority updated:** Added `const` declarations to Priority 1 table
  (required for self-contained, parseable programs). Section: "Implementation Priority".

- **Whitepaper examples updated:** All three examples (conv2d_relu, gemm_bias_relu,
  conv2d_maxpool) now include `const` preambles with realistic values. L2 buffer `size=...`
  placeholders replaced with computed expressions. Section: companion document
  `nem_whitepaper.md`.

- **examples.md updated:** Both NEM program examples (conv2d_relu, gemm_relu_multi_cstl)
  now include `const` preambles. L2 buffer `size=...` placeholders replaced with computed
  expressions. Section: companion document `examples.md`.

### Impact
- **All tools affected.** Parser must add `const_decl` production. Semantic analysis must
  evaluate constant expressions, enforce forward-reference prohibition, and check name
  uniqueness. Expression evaluation must substitute constant values in all contexts.
- **Conformance tests added:** 10 new test files (32 cases) under
  `tests/conformance/const/` covering valid declarations, operator evaluation, usage
  contexts, and all error conditions.
- **No contract changes.** IR schema, CLI, and diagnostics contracts are not affected.

---

## [2026-02-12] — Remove baseline keyword; explicit device inheritance

### Changed
- **Device Configuration Grammar — baseline removed:** Removed the `baseline_clause`
  production (`baseline = "nem_baseline_1.0"`) from device configuration grammar. Devices
  now explicitly list MUST-class variants in `opcode.mandatory` (via inheritance from a
  baseline device file). Section: "Device Configuration".

- **Device Configuration Grammar — inheritance relaxed:** Derived devices (`extends`)
  can now set/override `topology` and add to `opcode.mandatory` (previously only
  `opcode.extended` was allowed). New `derived_body` production:
  `derived_body ::= topology_block? opcode_mandatory_block? opcode_extended_block?`.
  Abstract devices (no topology) are now permitted. Section: "Device Configuration".

- **Document Grammar — config documents:** Extended `top_level` to support config
  documents containing type_family declarations and device configs:
  `config_document ::= { type_family_decl | device_config }`.
  Section: "Document Model".

- **Include Semantics — type_family imports:** Include declarations now import both
  device configurations and type_family definitions from referenced files.
  Section: "Include Semantics".

- **family_id grammar fix:** Changed `family_id ::= ID "." ID` to
  `family_id ::= ID ( "." ID )?` to support single-ID families (`eltwise`, `view`,
  `cast`, `quantize`, `dequantize`). Section: "Device Configuration".

- **variant_ref grammar fix:** Made type_instantiation optional in variant references:
  `variant_ref ::= family_id type_instantiation? "." ID`. Supports `cast.default`
  (no type parameters). Section: "Device Configuration".

- **Schema Rules rewritten:** Removed rules 2-3 (baseline match, implicit MUST).
  Rewrote rule 4: `opcode.mandatory` now lists all guaranteed variants including
  MUST-class. Reduced from 8 to 6 rules. Section: "Schema Rules".

- **Effective Type Family Set simplified:** Formula changed from
  `effective[op] = baseline_must[op] ∪ opcode.mandatory[op] ∪ opcode.extended[op]`
  to `effective[op] = opcode.mandatory[op] ∪ opcode.extended[op]`.
  Section: "Effective Type Family Set".

- **Conformance Rule updated:** Devices must include all MUST-class variants in
  `opcode.mandatory` (previously implicit via baseline string). Section: "Conformance Rule".

- **Inheritance Rules rewritten:** 7 new rules supporting topology override,
  `opcode.mandatory` union, abstract parent devices, and post-resolution validation.
  Section: "Inheritance Rules".

- **Baseline Type Family Set → MUST Variant Reference:** Renamed section, kept table
  as informative reference. Fixed `cast.any_supported` → `cast.default`.
  Section: "MUST Variant Reference (Informative)".

- **New file: `examples/nem_baseline_1.0.nem`:** Standard baseline device file containing
  all type_family definitions and an abstract device `nem_baseline_1_0` with all 15
  MUST-class variants. All conformant devices inherit from this file.

- **All device config examples updated:** All examples in spec, whitepaper, and
  `examples.md` now use `include "nem_baseline_1.0.nem"` and
  `extends nem_baseline_1_0` instead of `baseline = "nem_baseline_1.0"`.

### Impact
- **All tools affected.** Parser must remove `baseline` keyword, support relaxed
  inheritance, and handle config documents with type_family declarations.
- **Interpreter:** `DeviceConfigNode` loses `baseline` field. Device resolution
  algorithm simplified (no baseline resolution step). Effective set formula updated.
- **VS Code extension:** `baseline` removed from keyword-config syntax pattern.
- **Conformance tests:** Device config parsing tests must be updated for new grammar.
- **No contract changes.** IR schema and CLI contracts are not affected.

---

## [2026-02-12] — Sub-byte type support, implementation priority, document structure

### Changed
- **Type System — Element Bitwidth (new subsection):** Defined `bitwidth(E)` formally
  as the number of bits per element. Added a bitwidth table for all element types.
  Added normative notes on sub-byte packing and intra-byte packing order (device-defined).
  Section: "Type System > Element Bitwidth".

- **Extent Consistency (renamed from "Byte Extent Consistency"):** Replaced `sizeof(E)`
  with `bitwidth(E)` (returning bits). Updated the extent formula to
  `byte_extent >= ⌈num_elements(S) * bitwidth(E) / 8⌉`. Added sub-byte packing example
  for `i4`. Section: "Extent Consistency".

- **Buffers:** Added normative note that buffer sizes must account for sub-byte packing
  via the `bitwidth(E)` formula. Clarified that buffer sizes are always whole bytes.
  Section: "Core Program Objects > Buffers".

- **Regions:** Added normative note that byte offsets and extents remain in bytes for
  sub-byte types, with packed representation. Clarified byte-aligned offset requirement.
  Section: "Core Program Objects > Regions".

- **Layout and Strides:** Added clarification that strides are in elements regardless of
  element bitwidth, with byte conversion performed during lowering.
  Section: "Type System > Layout and Strides".

- **Implementation Priority (new subsection, informative):** Added Priority 1 / Priority 2
  classification of all spec features, identifying which features are required for current
  NPM hardware and which may be deferred.
  Section: "NPM Hardware Support Status > Implementation Priority".

- **Document Roadmap (new section):** Added a roadmap listing the document's section
  order and noting key forward references.
  Section: "Document Roadmap" (after Architectural Positioning).

- **Forward reference annotations:** Added explicit forward-reference notes for
  `@resource` decorator, device configuration, bounded pipelining, and the
  attribute/decorator design principle.

- **Restructuring Recommendations (new section, informative):** Added five concrete
  recommendations for a future editorial revision to reduce forward references.
  Section: "Restructuring Recommendations".

- **Buffers — import flag:** Clarified the previously undefined "import/pinning"
  attribute as an import flag for externally-provided buffer contents.

### Impact
- **All tools affected.** Buffer size computation, region extent validation, and any
  code using `sizeof(E)` must migrate to `bitwidth(E)` (returning bits, not bytes).
- **Conformance tests:** Extent consistency tests should be updated to verify the
  bit-based formula, especially for `i4` element types.
- **No contract changes.** IR schema, CLI, and diagnostics contracts are not affected.
