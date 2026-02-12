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
