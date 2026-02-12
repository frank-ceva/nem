# NEM: NeuPro-M Execution Model
## Formal Architecture and Language Specification (Reference Manual)

---

## Scope and Purpose

This document is the **normative architecture and language specification** of **NEM
(NeuPro-M Execution Model)**.

With this document alone, it MUST be possible to:

1. Write correct **NEM programs manually**
2. Write a **compiler pass lowering MLIR (or equivalent IRs) to NEM**
3. Write a **binder / compiler lowering NEM to NeuPro-M Task Control Buffers (TCBs)**

All execution semantics are defined here. **Microarchitectural binding** (physical addresses,
bank selection, burst shaping, store formats, arbitration hints, tag encoding, etc.) is explicitly
out of scope, except where referenced as binder responsibilities.

---

## Architectural Positioning

NEM is an **execution-level architectural contract** positioned between:

- functional graph representations (e.g. ONNX),
- compiler IRs (e.g. MLIR affine/async),
- hardware-bound control structures (TCBs).

NEM defines **how execution proceeds** on NeuPro-M-class accelerators with explicitly managed
memory hierarchies (DDR/L2/L1), explicit data movement, explicit dependences, bounded concurrency,
and typed intermediate values.

NEM is **not**:
- a mathematical graph language,
- a general-purpose compiler IR,
- a microarchitectural programming interface.

---

## Document Roadmap

This specification introduces concepts in layers. Some sections necessarily reference
concepts defined in later sections. The following roadmap provides orientation:

1. **Abstract Machine Model** — memory hierarchy, engines, resource classes, execution units
2. **Core Program Objects** — buffers, regions, tiles, tasks, tokens
3. **Type System** — element types, bitwidth, shapes, layouts, quantization
4. **Extent Consistency** — size constraints linking types to regions
5. **Task Taxonomy** — the complete set of operations (transfer, store, compute, wait)
6. **Design Principle** — the distinction between object attributes and decorators
7. **Decorators** — optional refinements (`@materialized`, `@resource`, `@deterministic`, etc.)
8. **Execution Semantics** — task readiness, completion, materialization, placement
9. **Hazards and Aliasing** — ordering and safety rules
10. **Loops and Bounded Pipelining** — iteration and `@max_in_flight`
11. **Constant Declarations** — compile-time named integer constants (`const`)
12. **Formal Language Definition** — EBNF grammar, opcode signatures, device configuration
13. **Appendix** — type family definitions

Key terms that appear before their full definition:
- **Decorators** (e.g. `@resource`, `@materialized`) are introduced informally in the
  Abstract Machine and Core Program Objects sections and defined formally in the
  Decorators section.
- **Device Configuration** is referenced in the Execution Units section and defined
  formally in the Formal Language Definition section.
- **Bounded pipelining** is mentioned in the Tiles section and defined in the Loops
  section.

---

## Abstract Machine Model

### Memory Levels

The abstract machine defines three architectural memory levels:

- **DDR** – off-chip memory
- **L2**  – on-chip shared memory
- **L1**  – on-chip scratchpad memory

`L1` memory is Engine-local and is indexed by Engine identifier.
`L1[k]` denotes the local scratchpad memory of Engine `k`.

`L2` and `DDR` memory levels are device-global and shared across Engines.

Memory is:
- explicitly managed,
- non-coherent,
- capacity-limited,
- accessed only through explicit tasks.

No implicit caching or coherence exists.

---

### Engines (Normative)

An NPM device is composed of one or more **Engines**.

An Engine is an execution domain that includes:
- a local control plane (Sequencer),
- a local scratchpad memory instance (`L1[k]`),
- local access to execution resources (TRANSFER, COMPUTE, STORE).

Each Engine is identified by a zero-based index `k` and owns exactly one `L1[k]` memory instance.

Engines execute tasks independently and concurrently. There is no global Sequencer spanning multiple Engines.


### Execution Resources

The abstract machine exposes **resource classes**, not concrete units:

- `TRANSFER`
- `COMPUTE`
- `STORE`

Resource classes describe the nature of operations but do not encode hardware identity,
quantity, or topology. Mapping to concrete hardware units is expressed via Execution Units
(see below) and refined by the binder during lowering.

---

### Execution Units

The abstract machine defines named **execution unit types** that represent physically distinct
hardware blocks. Execution units are classified into two categories based on their scope:

#### Per-Engine Execution Units

Each Engine contains one or more instances of the following unit types:

| Unit Type | Role | Typical Instances/Engine |
|-----------|------|------------------------|
| `NMU` | Linear algebra (GEMM, Conv, MatMul) | 1 (future: N) |
| `CSTL` | Elementwise, activation, normalization, store-back | 1–4 |
| `DMA` | Region transfers between memory levels (L2↔L1) | 1–4 |
| `VPU` | Programmable vector/scalar operations, control logic, fallback execution | 1 |
| `SEQ` | Task dispatch and synchronization (Sequencer) | 1 |

Per-engine instances are identified by a zero-based index within their type and Engine:
`NMU[0]`, `CSTL[0]`..`CSTL[3]`, `DMA[0]`..`DMA[3]`, `VPU[0]`, `SEQ[0]`.

The number of instances per unit type per Engine is declared in the `per_engine` block of
the device configuration (see Device Configuration Grammar in the Formal Language Definition).

#### Device-Level Execution Units

The following unit types exist at the *device level* (not per-engine) and are shared
across all Engines:

| Unit Type | Role | Typical Instances/Device |
|-----------|------|-------------------------|
| `sDMA` | System DMA: region transfers between DDR and L2 | 1–4 |
| `WDM` | Weight Decompression Module: on-the-fly weight decompression | 0–8 |

Device-level units are declared in the `device_units` block of the device configuration.
A count of 0 means the unit type is not present on this device.

The `sDMA` (System DMA) is architecturally distinct from the engine-level `DMA`:
- `sDMA` handles data movement between DDR and L2 (device-level, shared)
- `DMA` handles data movement between L2 and L1 (engine-level, local)

The binder selects the appropriate DMA path based on the memory levels of the source
and destination regions in a transfer task. NEM programs express *what* transfer happens;
the binder decides *which* DMA path is used.

The `WDM` (Weight Decompression Module) enables on-the-fly decompression of compressed
weight data during DDR→L2 or L2→L1 transfers. WDM supports compression modes including
weight sharing, sparse compression, and 4/8-bit compression. When WDM instances are
present (count > 0), the binder MAY route weight transfers through WDM for compressed
data paths. When WDM is absent (count = 0), the binder MUST use uncompressed DMA paths
for all weight transfers.

#### Resource Classes and Task Mapping

**Execution units are orthogonal to resource classes.**
Resource classes (COMPUTE, TRANSFER, STORE) describe *what an operation does*:
COMPUTE generates new data, TRANSFER and STORE move data.
Execution units describe *where an operation runs* on the hardware.

The mapping from task types to eligible execution unit types is:

- Linear algebra operations (`gemm`, `matmul`, `conv*`) → `NMU`
- Elementwise and activation operations (`relu`, `add`, `mul`, `gelu`, `silu`, `softmax`, ...) → `CSTL`
- Normalization operations (`layernorm`, `rmsnorm`) → `CSTL`
- Store operations (`store.async`, `store.sync`) → `CSTL`
- Transfer operations (`transfer.async`, `transfer.sync`) → `DMA` (L2↔L1) or `sDMA` (DDR↔L2)
- Quantize/dequantize (standalone) → `VPU`
- Reduction operations → `VPU`
- Operations not supported by NMU or CSTL → `VPU` (fallback)

`SEQ` is the sequencer — it dispatches tasks and manages synchronization tokens. It is
NOT a task execution target. Programs MUST NOT reference `SEQ` as an execution target.

A given operation MAY be eligible for multiple unit types on future devices.

The CSTLA/CSTLB sub-unit split within each CSTL instance is microarchitectural detail.
At the NEM level, a CSTL instance is a single unit capable of both post-processing
and store-back operations. The binder maps NEM CSTL references to concrete CSTLA/CSTLB
sub-units during lowering.

When no `@resource` decorator is present (defined formally in the Decorators section below),
the binder assigns tasks to execution unit instances freely. Programs that omit `@resource`
are fully portable and behave identically to programs written under prior spec revisions.

---

## Core Program Objects

### Buffers

A **buffer** represents an allocated storage object at a specific memory level.

Attributes:
- identifier
- memory level (`DDR | L2 | L1`)
- size in bytes
- optional alignment
- lifetime
- optional import flag (indicates the buffer's contents are provided externally, e.g. pre-loaded weights)

Buffer sizes are expressed in **bytes**. When allocating buffers for sub-byte element
types (e.g. `i4`), the size MUST be at least `⌈total_elements * bitwidth(E) / 8⌉` bytes,
where `bitwidth(E)` is defined in the Type System section. Buffer sizes MUST be
whole numbers of bytes; fractional-byte buffers are not permitted.

Buffers are opaque handles. Programs MUST NOT assume physical addresses, banking, slice mapping,
or interconnect topology.

---

### Regions

A **region** is a bounded view into a buffer.

A region is defined by:
- buffer handle
- byte offset
- byte extent
- element type (`elem`)
- shape (`shape[d]`)
- layout or strides (`layout=<id>` or `strides=[s0,s1,...]`)
- optional quantization descriptor (`quant`)

Byte offset and byte extent are expressed in **bytes**. For sub-byte element types
(e.g. `i4`), the byte extent covers the packed representation: a region of `N`
elements of `i4` requires `⌈N * 4 / 8⌉` bytes of extent (see Extent Consistency).
Byte offsets MUST be byte-aligned; sub-byte offset addressing is not supported.

These attributes are **intrinsic** to the region: they define both the physical byte
window and the interpretation required to execute operations on it.
See *Design Principle: Object Attributes vs. Decorators* for the rationale.

Regions may additionally carry **decorators** (e.g. `@materialized`, `@readonly`)
that refine binder behavior without affecting the region's identity or executability.

Regions are:
- the unit of task operands,
- the unit of hazard and alias analysis,
- the unit of visibility / materialization semantics,
- the unit of typing.

A region is **not required** to correspond 1:1 with a tile.

---

### Tiles

A **tile** is a loop-iteration concept.  
Tiles:
- select regions,
- do not define storage,
- do not imply materialization,
- may map to one or more regions.

Tiles exist only to structure iteration and bounded pipelining
(see Loops and Bounded Pipelining below).

---

### Tasks and Tokens

A **task** is an asynchronous operation that produces exactly one completion token.

Tokens:
- are opaque,
- represent region readiness,
- are the sole synchronization primitive.

---

## Type System (Normative)

### Overview

NEM is a **statically typed execution language**.  
All regions participating in compute tasks MUST have fully specified types.

No implicit type conversion is permitted.

---

### Element Types

Supported element types include:

- Signed integers: `i4`, `i8`, `i16`, `i32`
- Unsigned integers: `u8`, `u16`, `u32`
- Floating point: `f16`, `bf16`, `f32`

The supported set MAY be extended by future revisions.

---

### Element Bitwidth

The function `bitwidth(E)` returns the number of **bits** occupied by a single element of type `E`.

| Element Type | `bitwidth(E)` |
|-------------|---------------|
| `i4` | 4 |
| `i8`, `u8` | 8 |
| `i16`, `u16`, `f16`, `bf16` | 16 |
| `i32`, `u32`, `f32` | 32 |

For types where `bitwidth(E) < 8`, multiple elements pack into a single byte.
The packing order within a byte is device-defined; NEM does not prescribe
MSB-first or LSB-first packing. Programs MUST NOT depend on a specific
intra-byte packing order.

`bitwidth(E)` is the canonical unit for size computations involving element
counts. All extent and allocation consistency rules in this specification
are expressed in terms of `bitwidth(E)`.

---

### Shapes and Rank

Each typed region has a logical tensor shape:

- `rank`: number of dimensions
- `shape[d]`: extent in elements per dimension

---

### Layout and Strides

Layouts define logical-to-linear mapping.

Two representations are permitted:
- explicit `strides[]` in **elements**
- a canonical `layout=<id>` with implicit standard strides (e.g. `NCHW`, `NHWC`, `HWIO`)

Strides are measured in elements regardless of element bitwidth. For sub-byte types
(e.g. `i4`), a stride of 1 means one element (4 bits), not one byte. The conversion
from element strides to byte addresses is performed during lowering using `bitwidth(E)`.

Layouts are semantic; binders may remap layouts if semantics are preserved.

---

### Quantization Descriptor

Optional quantization metadata MAY be attached to a region via the `quant` attribute.
Three forms are supported (see `quant_desc` production in the Formal Language Definition):

- **per-tensor:** `per_tensor(scale=<value>, zero_point=<value>)` — a single scale and
  zero point apply to the entire tensor.
- **per-channel:** `per_channel(axis=<INT>, scales=[...], zero_points=[...])` — per-element
  scale and zero point along the specified axis. `scales` and `zero_points` arrays MUST
  have length equal to `dim[axis]`.
- **per-group:** `per_group(axis=<INT>, group_size=<INT>, scales=[...], zero_points=[...])` —
  groups of `group_size` elements along `axis` share a common scale and zero point.
  `scales` and `zero_points` arrays MUST have length `⌈dim[axis] / group_size⌉`.
  `group_size` MUST be a positive integer. If `dim[axis]` is not evenly divisible by
  `group_size`, the last group contains fewer elements; the binder handles any padding.

Per-group quantization is the dominant format for INT4 LLM weight compression (e.g.,
groups of 32 or 128 elements sharing a scale factor).

Quantization semantics MUST be preserved by binders.

---

### Accumulation Type

Ops involving reduction (e.g. Conv, GEMM) require an explicit or defaulted `accum_type`
specifying accumulation precision.

---

### Region Type Syntax

Typing is expressed as intrinsic region attributes:

```text
region(buffer, offset, extent,
  elem=<elem_type>,
  shape=[d0,d1,...],
  layout=<layout_id> | strides=[s0,s1,...],
  quant=<quant_desc?>
)
```

The `elem`, `shape`, and `layout`/`strides` attributes are required for all regions that
participate as compute task operands. The `quant` attribute is required only for regions
carrying quantized integer data (see Quantization Descriptor above).

Transfer and store tasks operate on raw byte ranges and do not require type attributes;
however, type attributes MAY be present for documentation or validation purposes.

## Extent Consistency

For a typed region with element type `E`, shape `S`, and byte extent `byte_extent`,
the following constraints MUST hold:

- `byte_extent >= ⌈num_elements(S) * bitwidth(E) / 8⌉`

  where `bitwidth(E)` is the element bitwidth defined in the Type System section,
  and `⌈x⌉` denotes the ceiling function (round up to the nearest integer).

  For element types where `bitwidth(E)` is a multiple of 8, this simplifies to:
  `byte_extent >= num_elements(S) * (bitwidth(E) / 8)`

- Any element addressable via the declared layout or strides MUST fall within the
  `[offset, offset + byte_extent)` range of the underlying buffer.

**Sub-byte packing.** For element types with `bitwidth(E) < 8` (e.g. `i4`),
multiple elements are packed into each byte. The minimum byte extent for a region
of `N` elements of type `i4` is `⌈N * 4 / 8⌉ = ⌈N / 2⌉` bytes.

Violations of these constraints result in undefined behavior.

---

## Task Taxonomy (Exhaustive)

This section defines the complete set of task categories in NEM. All executable
behavior in NEM is expressed using these task forms.

### Transfer Tasks

Transfer tasks move data between regions located in possibly different memory levels.

#### `transfer.async`

Asynchronous region-to-region copy.

Semantics:
- Copies the full extent of the source region into the destination region.
- Source and destination regions MUST have compatible types.
- Overlapping source and destination regions are illegal unless `@memmove` is present.

Produces one completion token.

#### `transfer.sync`

Synchronous variant of `transfer.async`.

Equivalent to:
- `transfer.async`
- followed immediately by `wait` on the produced token.

---

### Store Tasks

Store tasks represent architectural commitment of region contents to their declared
memory level.

#### `store.async`

Asynchronously commits a region’s contents such that subsequent tasks reading from
the destination memory level observe valid data.

Produces one completion token.

#### `store.sync`

Synchronous variant of `store.async`.

---

### Compute Tasks (Explicit Opcode Set)

Compute tasks perform mathematical operations on typed regions. Each compute task is
expressed as a **dedicated opcode** with fixed operand structure.

All compute tasks have `.async` and `.sync` forms.

#### Elementwise Operations

Unary:
- `relu`
- `leaky_relu`
- `sigmoid`
- `tanh`
- `exp`
- `log`
- `sqrt`
- `abs`
- `neg`

Binary:
- `add`
- `sub`
- `mul`
- `div`
- `min`
- `max`
- `pow`

Other:
- `clamp`

Typing rules:
- Input and output shapes MUST be identical.
- Element types MUST match unless an explicit `cast` is present.

---

#### Linear Algebra Operations

- `gemm`
- `matmul`

Typing rules:
- Operand ranks and dimensions MUST be compatible.
- An accumulation type (`accum_type`) MUST be specified or defaulted.
- Output element type is derived from accumulation semantics.

---

#### Convolution Operations

- `conv1d`
- `conv2d`
- `conv3d`
- `depthwise_conv2d`

Typing rules:
- Input, weight, and optional bias regions MUST satisfy rank and layout constraints.
- Output shape is derived from input shape, kernel shape, pads, strides, dilations, and groups.
- `accum_type` MUST be specified or defaulted.

---

#### Pooling Operations

- `maxpool`
- `avgpool`

Typing rules:
- Output shape is derived from input shape and pooling attributes.
- Element type is preserved.

---

#### Layout / Tensor View Operations

- `transpose`
- `reshape`
- `slice`
- `concat`
- `split`
- `pad`
- `gather`

Typing rules:
- Output type is derived deterministically from input type and attributes.
- These operations do not change element values, only their interpretation.

---

#### Reduction Operations

- `reduce_sum`
- `reduce_max`
- `reduce_min`
- `argmax`
- `argmin`

Typing rules:
- Output rank is derived from reduction axes and `keepdims`.
- `argmax` / `argmin` output integer index types.

---

#### Casting and Quantization Operations

- `cast`
- `quantize`
- `dequantize`

Typing rules:
- Explicit type conversion only.
- No implicit casts are permitted elsewhere in NEM.

WARNING: NPM does not embed dedicated hardware operators implementing quantization operations, other than CSTL's capability to store data and apply some quantization on-the-fly. Standalone quantization operators, if needed, MAY be implemented on `VPU` (see Execution Units). The `VPU` is a declared per-engine execution unit type and a valid `@resource` target.

---

#### Generic Compute Escape Hatch

- `compute.async(op="<string>", attrs={...})`

Used for forward compatibility. Binders MAY reject unknown operations.

---

#### Opcode Type Legality and Type Families (Normative)

##### Purpose and Model

NEM is a statically typed execution language: each region operand carries a concrete type via
the region's intrinsic type attributes (`elem`, `shape`, `layout`/`strides`, `quant`).

However, **not all operators support all element types**. Therefore, NEM defines **opcode-specific
type legality**:

For each opcode `op`, the specification defines:

1) A set of **type families** with named **variants** and type-parameter instantiations
2) A predicate `LEGAL_op(instance)`, which holds iff the instance matches one of the family variants
3) A type derivation function `TYPE_op(instance)` that determines output element types (when not fixed)

A program is **well-typed** only if every opcode instance is well-formed AND matches a legal
family variant instantiation.

Binders and compilers MUST reject any program where an opcode instance does not match a legal
family variant.

##### Type Families and Matching

Opcode type legality is expressed through **type families** — parameterized definitions
that capture regular type patterns across a domain of opcodes. Each family declares
type parameters, operand bindings, attribute constraints, and named **variants** with
per-instantiation conformance classes.

A concrete opcode-type combination is identified by a **variant reference ID** of the form
`family_id<T_instantiation>.variant` — e.g., `gemm.float<f16>.no_bias`,
`conv2d.int8<i8>.with_bias`, `eltwise<f32>.default`.

The formal grammar for type family declarations is defined in the **Type Family Grammar**
section of the Formal Language Definition.

**Type Family Matching Rule (Normative):**
An opcode instance matches a type family variant at a specific type instantiation if and only if:
- it supplies the required operands (and only allowed optional operands as defined by the variant),
- the `elem` attribute of each operand region matches the operand binding after type-parameter substitution,
- required attributes (e.g., `accum_type`) satisfy the family's attribute constraints,
- and any additional family conditions (quantization fields, etc.) are satisfied.

If multiple family variants match, the instance is still valid; the binder MAY choose any
matching variant unless constrained by `@deterministic` or other semantic decorators.

##### Type Family Conformance Registry (Normative)

###### Classification

The type family definitions (Appendix) classify each family variant instantiation into
exactly one conformance class:

- **MUST** — all conformant NEM device configurations MUST include this family variant
  instantiation in their `opcode.mandatory` block (either directly or via inheritance
  from the standard baseline device). A binder MAY assume MUST variants are present
  in any conformant device's `opcode.mandatory` set.

- **MAY** — implementations MAY support this family variant instantiation; support is
  device-dependent. A program that relies on a MAY variant is portable only to devices
  that explicitly list it in `opcode.mandatory` or `opcode.extended`.

###### MUST Variant Reference (Informative)

The following table enumerates all MUST-class family variant instantiations defined
by this revision of the specification. These are the variants that every conformant
NEM device MUST list in its `opcode.mandatory` block (either directly or via
inheritance from the standard baseline device `nem_baseline_1_0`).

| Domain | Family Variant | Opcode |
|--------|---------------|--------|
| Linear Algebra | `gemm.int8<i8>.no_bias` | `gemm` / `matmul` |
| | `gemm.int8<i8>.with_bias` | `gemm` / `matmul` |
| | `gemm.float<f16>.no_bias` | `gemm` / `matmul` |
| | `gemm.float<f16>.with_bias` | `gemm` / `matmul` |
| Convolution | `conv2d.int8<i8>.no_bias` | `conv2d` |
| | `conv2d.int8<i8>.with_bias` | `conv2d` |
| | `conv2d.float<f16>.no_bias` | `conv2d` |
| | `conv2d.float<f16>.with_bias` | `conv2d` |
| Elementwise | `eltwise<i8>.default` | `relu`, `add`, `mul`, ... |
| | `eltwise<f16>.default` | `relu`, `add`, `mul`, ... |
| View / Layout | `view<i8>.default` | `transpose`, `reshape`, ... |
| | `view<f16>.default` | `transpose`, `reshape`, ... |
| Normalization | `norm<f16>.default` | `layernorm`, `rmsnorm` |
| Softmax | `softmax<f16>.default` | `softmax`, `log_softmax` |
| Type Conversion | `cast.default` | `cast` |
| | `quantize<f16, i8>.default` | `quantize` |
| | `dequantize<i8, f16>.default` | `dequantize` |

The standard baseline device file `nem_baseline_1.0.nem` provides both these MUST
variant listings (as a device `nem_baseline_1_0`) and the exhaustive type family
definitions. All conformant devices SHOULD inherit from this baseline device.

Formal type family definitions are provided in the Appendix and in the baseline file.

###### MAY Variant Inventory

The following MAY-class family variant instantiations are defined by this revision.
Devices advertise support for zero or more of these via their `opcode.mandatory`
(guaranteed) or `opcode.extended` (conditionally available) blocks:

| Domain | Family Variant | Opcode |
|--------|---------------|--------|
| Linear Algebra | `gemm.int8<i16>.with_bias` | `gemm` / `matmul` |
| | `gemm.float<bf16>.no_bias` | `gemm` / `matmul` |
| | `gemm.float<f32>.no_bias` | `gemm` / `matmul` |
| Convolution | `conv2d.int8<i16>.with_bias` | `conv2d` |
| | `conv2d.float<bf16>.no_bias` | `conv2d` |
| | `conv2d.float<bf16>.with_bias` | `conv2d` |
| | `conv2d.float<f32>.no_bias` | `conv2d` |
| | `conv2d.float<f32>.with_bias` | `conv2d` |
| Elementwise | `eltwise<i16>.default` | elementwise ops |
| | `eltwise<i32>.default` | elementwise ops |
| | `eltwise<bf16>.default` | elementwise ops |
| | `eltwise<f32>.default` | elementwise ops |
| View / Layout | `view<i16>.default` | view ops |
| | `view<i32>.default` | view ops |
| | `view<bf16>.default` | view ops |
| | `view<f32>.default` | view ops |
| Normalization | `norm<bf16>.default` | `layernorm`, `rmsnorm` |
| | `norm<f32>.default` | `layernorm`, `rmsnorm` |
| Softmax | `softmax<bf16>.default` | `softmax`, `log_softmax` |
| | `softmax<f32>.default` | `softmax`, `log_softmax` |
| Linear Algebra (INT4) | `gemm.int4.no_bias` | `gemm` / `matmul` |
| | `gemm.int4.with_bias` | `gemm` / `matmul` |
| Convolution (INT4) | `conv2d.int4.no_bias` | `conv2d` |
| | `conv2d.int4.with_bias` | `conv2d` |
| Type Conversion | `quantize<f32, i8>.default` | `quantize` |
| | `dequantize<i8, f32>.default` | `dequantize` |

###### Conformance Rule (Normative)

A conformant NEM device configuration MUST include every MUST-class family variant
instantiation (as listed in the table above and defined in the type family appendix)
in its `opcode.mandatory` block, either directly or via inheritance from a parent
device. The standard baseline device `nem_baseline_1_0` (defined in
`nem_baseline_1.0.nem`) provides these MUST variants and SHOULD be used as the
base device for all conformant device configurations.

A device that supports additional MAY-class family variant instantiations MUST
declare them in its `opcode.mandatory` or `opcode.extended` block.

---

##### Device Configuration (Normative)

Datatype support may vary by NPM configuration (number of engines, NMU/CSTL versions, etc.).
Conformance and validation use a **device configuration** — a target-specific
artifact exposed out of band (compile-time configuration, device query, or platform manifest),
or declared inline in a NEM program via the `device` directive.

The formal grammar for device configurations is defined in the **Device Configuration Grammar**
section of the Formal Language Definition.

###### Schema Rules (Normative)

1. `spec_version` MUST identify the spec revision the device conforms to.
2. `opcode.mandatory` lists all family variant instantiations that are **guaranteed**
   on this device, including all MUST-class variants. A compiler targeting this device
   MAY unconditionally use any variant in `opcode.mandatory` without runtime capability
   queries.
3. `opcode.extended` lists family variant instantiations that are **conditionally
   available** on this device. Their presence indicates the device supports these
   variants, but a compiler targeting a family of devices (via inheritance) SHOULD
   confirm per-device support.
4. `opcode.mandatory ∩ opcode.extended` MUST be empty. A variant MUST NOT appear in
   both blocks. A binder encountering a duplicate SHOULD emit a diagnostic warning
   and MUST ignore the redundant entry.
5. All per-engine unit counts and `num_engines` MUST be ≥ 1. Device-level unit
   counts (`device_units`) MAY be 0 (meaning the unit type is absent).
   `l1_size_bytes` and `l2_size_bytes` MUST be > 0.
   After device resolution (including inheritance), a `topology` block MUST be
   present.
6. **Memory capacity rule**: The sum of all buffer sizes declared at a given memory
   level MUST NOT exceed the declared capacity for that level (`l1_size_bytes` for
   L1, `l2_size_bytes` for L2). For single-engine programs this is a static check;
   for multi-engine scheduling the binder is responsible for enforcement.
7. After device resolution (including inheritance), `opcode.mandatory` MUST include
   every MUST-class family variant instantiation defined by the spec revision
   identified in `spec_version`. A resolved device whose `opcode.mandatory` set
   does not contain all MUST variants is invalid.

###### Effective Type Family Set

For a given target device (after resolving inheritance, if applicable), the
**effective type family set** for opcode `op` is:

```text
effective[op] = opcode.mandatory[op] ∪ opcode.extended[op]
```

where `opcode.mandatory[op]` is the set of family variants listed in the
device's resolved `opcode.mandatory` block, and `opcode.extended[op]`
is the set of family variants listed in the device's resolved `opcode.extended`
block (empty if not declared).

Since all MUST-class variants are explicitly listed in `opcode.mandatory` (either
directly or inherited from the baseline device), they are naturally included in the
effective set. No implicit inclusion mechanism is needed.

A compiler targeting a concrete device (possibly resolved via `extends`) knows the
full effective set and MAY unconditionally use any variant in it.

---

##### Device Validity Rule (Normative)

A program is valid for a specific target device if and only if every opcode instance
matches at least one family variant instantiation in the target's **effective type family set**
for that opcode.

Binders MUST reject programs that use type combinations not present in the effective type family set.

Binders SHOULD emit a diagnostic identifying the failing opcode instance and the
nearest available family variant, to aid program authors.

---

##### Target Resource Validity Rule (Normative)

A `@resource` decorator is valid for a specific target device according to the following
binding rules, evaluated in order:

1. **Exact match**: The target device provides the specified unit type and the index is
   within bounds (`index < per_engine.units[type]`). The binder MUST assign the task to
   that exact instance.

2. **Same-type remap**: The target device provides the specified unit type but the index
   exceeds available instances (`index >= per_engine.units[type]`). The binder MUST remap
   to an available instance of the same type. The specific instance is binder-chosen.

3. **Cross-type translation**: The target device does not provide the specified unit type.
   The binder MUST translate the operation to an equivalent execution on an available unit
   type that supports the operation, or reject the program.

A program is resource-valid for a target device if every `@resource` decorator can be
satisfied by rules 1, 2, or 3 above.

---

##### Example Device Configurations

All examples below assume the standard baseline file has been included:

```text
include "nem_baseline_1.0.nem"
```

**Minimal device (MUST variants + minimal BF16):**

```text
include "nem_baseline_1.0.nem"

device npm_lite extends nem_baseline_1_0 {
    topology {
        num_engines = 1
        l2_size_bytes = 1048576          # 1 MB L2
        device_units {
            sDMA = 1
            WDM  = 0                     # no weight decompression
        }
        per_engine {
            NMU  = 1
            CSTL = 2
            DMA  = 2
            VPU  = 1
            SEQ  = 1
            l1_size_bytes = 524288       # 512 KB L1
        }
    }

    unit_characteristics {
        NMU {
            int8_macs = 4096
            fp16_macs = 2048
        }
        SEQ {
            max_active_tokens = 16
        }
    }

    opcode.mandatory {
        gemm.float<bf16>.no_bias
        eltwise<bf16>.default
        view<bf16>.default
    }
}
```

Effective set: inherited MUST variants (from `nem_baseline_1_0`) + BF16 GEMM, elementwise, and view.

**Mid-range device with BF16 support:**

```text
include "nem_baseline_1.0.nem"

device npm_mid extends nem_baseline_1_0 {
    topology {
        num_engines = 2
        l2_size_bytes = 4194304          # 4 MB L2
        device_units {
            sDMA = 2
            WDM  = 2
        }
        per_engine {
            NMU  = 1
            CSTL = 2
            DMA  = 2
            VPU  = 1
            SEQ  = 1
            l1_size_bytes = 1048576      # 1 MB L1
        }
    }

    unit_characteristics {
        NMU {
            int4_macs = 16384
            int8_macs = 4096
            int16_macs = 1024
            fp16_macs = 2048
        }
        SEQ {
            max_active_tokens = 16
        }
    }

    opcode.mandatory {
        gemm.float<bf16>.no_bias
        conv2d.float<bf16>.no_bias
        conv2d.float<bf16>.with_bias
        eltwise<bf16>.default
        view<bf16>.default
    }
}
```

Effective set: inherited MUST + device-specific BF16 variants in `opcode.mandatory`.

**High-end base device with BF16 mandatory and selective FP32:**

```text
include "nem_baseline_1.0.nem"

device npm_pro extends nem_baseline_1_0 {
    topology {
        num_engines = 4
        l2_size_bytes = 8388608          # 8 MB L2
        device_units {
            sDMA = 4
            WDM  = 4
        }
        per_engine {
            NMU  = 2
            CSTL = 4
            DMA  = 4
            VPU  = 1
            SEQ  = 1
            l1_size_bytes = 1048576      # 1 MB L1
        }
    }

    unit_characteristics {
        NMU {
            int4_macs = 32768
            int8_macs = 8192
            int16_macs = 2048
            fp16_macs = 4096
        }
        SEQ {
            max_active_tokens = 32
        }
    }

    opcode.mandatory {
        gemm.float<bf16>.no_bias
        conv2d.float<bf16>.no_bias
        conv2d.float<bf16>.with_bias
        eltwise<bf16>.default
        view<bf16>.default
    }

    opcode.extended {
        gemm.float<f32>.no_bias
    }
}
```

Effective set: inherited MUST + `opcode.mandatory` BF16 + `opcode.extended` FP32 GEMM.

**SKU extending base device with additional FP32 support:**

```text
device npm_pro_x1 extends npm_pro {
    opcode.extended {
        conv2d.float<f32>.no_bias
        eltwise<f32>.default
    }
}
```

Resolved `npm_pro_x1`: inherits all of `npm_pro`'s fields (spec_version, topology,
`unit_characteristics`, `opcode.mandatory`). The `opcode.extended` set is the union of
parent and child: `{ gemm.float<f32>.no_bias, conv2d.float<f32>.no_bias, eltwise<f32>.default }`.

**Multi-file example:**

```text
# file: devices/npm_pro.nem
include "nem_baseline_1.0.nem"

device npm_pro extends nem_baseline_1_0 {
    topology {
        num_engines = 4
        l2_size_bytes = 8388608
        device_units { sDMA = 4  WDM = 4 }
        per_engine {
            NMU = 2  CSTL = 4  DMA = 4  VPU = 1  SEQ = 1
            l1_size_bytes = 1048576
        }
    }
    unit_characteristics {
        NMU { int4_macs = 32768  int8_macs = 8192  fp16_macs = 4096 }
        SEQ { max_active_tokens = 32 }
    }
    opcode.mandatory {
        gemm.float<bf16>.no_bias
        conv2d.float<bf16>.no_bias
        conv2d.float<bf16>.with_bias
        eltwise<bf16>.default
        view<bf16>.default
    }
    opcode.extended {
        gemm.float<f32>.no_bias
    }
}

device npm_pro_x1 extends npm_pro {
    opcode.extended {
        conv2d.float<f32>.no_bias
        eltwise<f32>.default
    }
}

# file: kernels/matmul.nem
include "devices/npm_pro.nem"

device npm_pro_x1

program matmul_tiled:
    # program body uses effective type family set of npm_pro_x1
    # ...
```

---

Formal type family definitions are provided in the Appendix at the end of this document.

##### No Implicit Casts

NEM does not perform implicit type conversions. If a program needs a type conversion to match a legal
family variant for an opcode, it MUST insert explicit conversion ops (cast, quantize, dequantize)
and/or choose different operand types.

##### Quantization Constraints

Family variants that involve quantized integer inference MAY require that operands carry
quantization metadata in the region's `quant` attribute.

Unless specified otherwise by a family variant:
for INT8 inference variants, X and W MUST have valid quant descriptors
bias type and scale rules are family-variant-defined
output quantization may be explicit (quantize) or implied by family variant (device-specific)

### Control Tasks

#### `wait`

Waits for one or more task completion tokens.

Semantics:
- The `wait` completes only when all specified tokens are satisfied.
- Does not produce a new token.

---

## Design Principle: Object Attributes vs. Decorators

NEM distinguishes between **object attributes** and **decorators** based on one
operational rule:

> **If a program cannot execute without the property, it is an object attribute.**
> **If a program executes correctly without the property, it is a decorator.**

Object attributes define what an object IS and what is needed to operate on it.
A region without its buffer handle, byte extent, or element type cannot be used as
a compute operand — the system would not know which bytes to read or how to interpret them.
These properties are intrinsic and always present.

Decorators refine HOW an object is processed — they constrain binder choices,
assert optimization permissions, or attach diagnostic metadata. A program with all
decorators removed still executes correctly: the binder uses conservative defaults
(sequential iteration, free placement, no fusion barriers, read+write access).

This separation yields a clean validation model:

1. **Structural validation** — all objects are well-formed (attributes present and consistent)
2. **Decorator validation** — all decorators are syntactically correct and applicable to their target object type
3. **Per-task validation** — each task's operands satisfy the task's requirements (e.g. compute operands carry type attributes)

Each layer catches a different class of errors.

### Classification of Properties

| Property | Can execute without it? | Classification |
|----------|------------------------|----------------|
| buffer handle, offset, extent | No | Region attribute |
| elem, shape, layout/strides | No (for compute operands) | Region attribute |
| quant descriptor | No (for quantized data) | Region attribute |
| `@materialized` | Yes — binder may fuse more aggressively | Decorator |
| `@deterministic` | Yes — binder may choose non-deterministic tiling | Decorator |
| `@readonly` / `@writeonly` | Yes — assume conservative read+write | Decorator |
| `@resource(unit[idx])` | Yes — binder assigns freely | Decorator |
| `@memmove` | Yes — overlapping transfers are UB without it, but non-overlapping transfers run fine | Decorator |
| `@max_in_flight(N)` | Yes — default to sequential (N=1) | Decorator |
| `@debug` / `@profile` | Yes — no effect on execution | Decorator |

---

## Decorators

Decorators attach optional refinements to program objects. They constrain binder behavior,
assert optimization permissions, or carry diagnostic metadata. A well-formed program
executes correctly with any or all decorators removed (see Design Principle above).

### Semantic Decorators (Normative)

- `@materialized`
  Requires the region to exist as an architectural value boundary. The binder MUST NOT
  bypass or fuse away this region.

- `@deterministic`
  Constrains the binder to select a lowering that preserves bitwise-deterministic results.

- `@memmove`
  Allows overlapping source and destination semantics for transfer tasks.

- `@readonly`, `@writeonly`
  Assert access intent for regions. When absent, the region is assumed read+write
  (conservative default).

- `@max_in_flight(N)`
  Applies to loops; bounds the number of simultaneously active iterations.
  When absent, the default is sequential execution (N=1).

- `@resource(unit_type[index])`
  Constrains the binder to assign this task to the specified execution unit instance
  on the task's assigned Engine. Binding follows the Target Resource Validity Rule.
  When absent, the binder assigns freely. See Execution Units.

  **Resource-invalid unit types (Normative):** The following unit types are NOT valid
  `@resource` targets:
  - `SEQ` — control plane unit; dispatches tasks, not a compute or transfer unit.
  - `sDMA` — device-level unit; the binder selects sDMA vs engine DMA based on the
    memory levels involved in a transfer.
  - `WDM` — device-level unit; a transparent data-path modifier for compressed weight
    transfers, not directly schedulable.

  Programs MUST NOT use `@resource` with these unit types; such usage is a static error.
  Valid `@resource` targets are: `NMU`, `CSTL`, `DMA`, `VPU`.

Unknown semantic decorators are errors.

---

### Informational Decorators

- `@debug(name)`
- `@profile(tag)`

Informational decorators MAY be ignored by binders.

---

## Execution Semantics (Normative)

### Task Readiness

A task becomes READY when:
- all dependency tokens are satisfied, and
- required abstract resources are available, and
- if `@resource` is present: the bound execution unit instance (after applying
  the Target Resource Validity Rule) is not occupied by another active task.

READY tasks may execute in any order consistent with dependencies.

---

### Completion Semantics

A task is COMPLETE when:
- all output regions are architecturally valid per their types, and
- any required materialization constraints are satisfied.

Completion produces exactly one token.

---

### Materialization Semantics

Regions marked `@materialized` MUST be produced as architectural values.

Regions not marked `@materialized` MAY be bypassed by fusion, provided all consuming
tasks observe correct semantics.

---

### Determinism Semantics

If `@deterministic` is present, the binder MUST choose tiling, fusion, accumulation,
and scheduling strategies that preserve bitwise results. If this is not possible,
the program MUST be rejected.

---

### Task Placement and Engine Assignment (Normative)

Task placement is determined as follows:

- If a task references any region residing in `L1[k]`, the task executes on Engine `k`.
- A task MUST NOT reference regions in `L1[k]` and `L1[j]` for `k ≠ j`.
- Tasks that reference only `L2` and/or `DDR` regions are Engine-agnostic.
  Such tasks are assigned to an Engine during lowering.
- If a task carries a `@seq_engine(k)` decorator, it MUST be assigned to Engine `k` 
(this is relevant for L2 and DDR DMA operations)


## Hazards and Aliasing Rules (Normative)

1. Overlapping regions with WRITE access MUST be ordered by dependencies.
2. Overlapping transfers require `@memmove`.
3. Region reuse MUST be proven safe via dependencies and bounded pipelining.
4. Out-of-bounds access is invalid.
5. Imported buffers are assumed to alias unless constrained.

Violations result in undefined behavior.

---

## Loops and Bounded Pipelining

Loops define iteration spaces and may carry `@max_in_flight(N)`.

`@max_in_flight(N)` limits the number of concurrently active iterations, enabling
safe reuse of ping-pong or ring-buffer regions.

Unbounded overlap is disallowed.

---

## Constant Declarations (Normative)

NEM programs describe static execution plans. All compile-time parameters — tensor
dimensions, tile byte sizes, loop bounds — are integer constants known before execution.
The `const` declaration introduces named constants into the program.

### Syntax

```text
const ID = expr
```

A `const` declaration binds `ID` to the integer value of `expr`, evaluated at compile time.

### Semantics

1. **Immutability.** A `const` binding is immutable. The same identifier MUST NOT be
   declared more than once. Duplicate `const` declarations are a static error.

2. **Integer-valued.** All constants are integer-valued. No type annotation is required
   or permitted — the type is always integer.

3. **Constant expressions.** The right-hand side MUST be a **constant expression**: an
   expression composed exclusively of:
   - Integer literals (`INT`),
   - Previously-declared constant names,
   - The binary operators `+`, `-`, `*`, `/` (integer division), `mod`,
   - Parenthesized sub-expressions.

   The expression grammar for constant expressions is the same `expr` production used
   elsewhere in NEM (see Formal Language Definition).

4. **Evaluation order.** Constants are evaluated in declaration order. An `expr` in a
   `const` declaration MUST NOT reference any identifier that has not been declared as a
   `const` on a preceding line. Forward references are a static error.

5. **Division semantics.** Integer division (`/`) truncates toward zero. Division by
   zero in a constant expression is a static error.

6. **Program scope.** Constants are program-scoped: they are visible from the point of
   declaration to the end of the program, including inside loop bodies. However, `const`
   declarations MUST NOT appear inside a `loop` body. A `const` inside a loop is a
   static error. (Constants are iteration-invariant by definition; placing them inside
   a loop would be misleading.)

7. **Name uniqueness.** A `const` identifier MUST NOT conflict with any other identifier
   in the same scope — including `let` bindings, buffer names, and token assignments.
   Name conflicts are a static error.

### Usage

Constants may appear anywhere an `expr` is accepted in a NEM program:

- Buffer sizes: `buffer X_L1 : L1 (size=2*tileX_bytes, align=64)`
- Region offsets and extents: `region(X_L2, i * tileX_bytes, tileX_bytes)`
- Shape dimensions: `shape=[1, TiH, TiW, Cin]`
- Loop bounds: `loop i in [0..T-1]`
- Compute attributes: `groups=1`, `accum_type=i32`

### Example

```text
const TiH = 16
const TiW = 16
const Cin = 64
const Cout = 128
const Kh = 3
const Kw = 3
const ToH = 14
const ToW = 14
const T = 4

const tileX_bytes = TiH * TiW * Cin        # 16384
const tileW_bytes = Kh * Kw * Cin * Cout    # 294912
const tileY_bytes = ToH * ToW * Cout        # 25088
const bias_bytes = Cout * 4                 # i32 = 4 bytes per element

buffer X_L2 : L2 (size=T * tileX_bytes, align=64)
buffer W_L2 : L2 (size=tileW_bytes, align=64)
buffer B_L2 : L2 (size=bias_bytes, align=64)
buffer Y_L2 : L2 (size=T * tileY_bytes, align=64)
```

---

## Formal Language Definition (EBNF)

### Grammar

```ebnf
(* --- Lexical --- *)

comment        ::= "#" { any_char_except_newline } NEWLINE ;
FLOAT          ::= DIGIT+ "." DIGIT+ ( [eE] [+-]? DIGIT+ )? ;

(* Comments begin with '#' and extend to end of line.
   They may appear on their own line or after any token.
   Comments are stripped before parsing.

   FLOAT literals consist of one or more digits, a decimal point, one or more
   fractional digits, and an optional scientific-notation exponent (e.g., 1.0,
   0.00001, 1.0e-5).  FLOAT literals are permitted only in compute attribute
   values (e.g., epsilon, alpha).  Buffer sizes, region offsets/extents, shape
   dimensions, loop bounds, and const declarations remain integer-only. *)

(* --- Top Level --- *)

document       ::= { include_decl } top_level ;
top_level      ::= program | config_document ;
config_document::= { type_family_decl | device_config } ;
include_decl   ::= "include" STRING ;

program        ::= device_decl? program_header? { stmt } ;
program_header ::= "program" ID ":" ;
stmt           ::= decl | task | loop | ";" ;

(* --- Declarations --- *)

decl           ::= buffer_decl | region_decl | let_decl | const_decl ;
const_decl     ::= "const" ID "=" expr ;
let_decl       ::= "let" ID "=" value ;

buffer_decl    ::= "buffer" ID ":" mem_level "(" buffer_props ")" decos? ;
buffer_props   ::= buffer_prop { "," buffer_prop } ;
buffer_prop    ::= "size" "=" expr | "align" "=" INT ;

region_decl    ::= ID "=" "region" "(" ID "," expr "," expr ")" type_attrs? decos? ;

type_attrs     ::= "elem" "=" elem_type ","
                    "shape" "=" "[" expr { "," expr } "]" ","
                    ( "layout" "=" ID | "strides" "=" "[" expr { "," expr } "]" )
                    ( "," "quant" "=" quant_desc )? ;
elem_type      ::= "i4" | "i8" | "i16" | "i32"
                  | "u8" | "u16" | "u32"
                  | "f16" | "bf16" | "f32" ;

quant_desc     ::= per_tensor_quant | per_channel_quant | per_group_quant ;
per_tensor_quant  ::= "per_tensor" "(" "scale" "=" value "," "zero_point" "=" value ")" ;
per_channel_quant ::= "per_channel" "(" "axis" "=" INT ","
                       "scales" "=" "[" value_list "]" ","
                       "zero_points" "=" "[" value_list "]" ")" ;
per_group_quant   ::= "per_group" "(" "axis" "=" INT "," "group_size" "=" INT ","
                       "scales" "=" "[" value_list "]" ","
                       "zero_points" "=" "[" value_list "]" ")" ;

mem_level      ::= "DDR" | "L2" | L1_indexed ;
L1_indexed     ::= "L1" ( "[" expr "]" )? ;

(* --- Loop --- *)

loop           ::= "loop" ID "in" "[" expr ".." expr "]" decos? ":"
                     { stmt }
                   "endloop" ;

(* --- Tasks --- *)

task           ::= assign? call decos? ;
assign         ::= ID "=" ;
call           ::= xfer | store | wait | compute ;

(* --- Transfer --- *)

xfer           ::= ( "transfer.async" | "transfer.sync" )
                   "(" "dst" "=" operand "," "src" "=" operand
                       ( "," "deps" "=" "[" id_list "]" )? ")" ;

(* --- Store --- *)

store          ::= ( "store.async" | "store.sync" )
                   "(" "dst" "=" operand "," "src" "=" operand
                       ( "," "deps" "=" "[" id_list "]" )? ")" ;

(* --- Wait --- *)

wait           ::= "wait" "(" id_list ")" ;

(* --- Compute --- *)

compute        ::= compute_op
                   "in" operand_list
                   "out" operand_list
                   { compute_attr } ;
compute_op     ::= OPCODE "." ( "async" | "sync" ) ;
compute_attr   ::= "deps" "=" "[" id_list "]"
                  | ID "=" value ;

(* --- Common --- *)

operand        ::= ID decos? | region_expr decos? ;
operand_list   ::= operand { "," operand } ;
region_expr    ::= "region" "(" ID "," expr "," expr ")" type_attrs? ;
id_list        ::= ID { "," ID } ;

(* --- Expressions --- *)

expr           ::= primary { binop primary } ;
primary        ::= INT | FLOAT | ID | "(" expr ")" ;
binop          ::= "+" | "-" | "*" | "/" | "mod" ;

(* --- Values --- *)

value          ::= expr | STRING | "[" value_list? "]" | region_expr ;
value_list     ::= value { "," value } ;

(* --- Decorators --- *)

decos          ::= { deco } ;
deco           ::= "@" ID ( "(" deco_args ")" )? ;
deco_args      ::= value { "," value }
                  | unit_type "[" expr "]" ;           (* for @resource *)
unit_type      ::= "NMU" | "CSTL" | "DMA" | "VPU" | "SEQ"
                  | "sDMA" | "WDM" ;
```

**Document Model (Normative Note):**
A NEM file is a `document` — a sequence of zero or more `include` declarations followed
by exactly one top-level construct: either a `program` or a `config_document`. A
`config_document` may contain any mix of `type_family_decl` and `device_config`
declarations. This means program files, device configuration files, and type family
catalog files all share the same document grammar but differ in their top-level content.

**Include Semantics (Normative):**

1. An `include` declaration makes named device configurations and type family
   definitions from the referenced file visible in the current file's scope.
2. The include path (a STRING literal) is resolved **relative to the directory of the
   including file**.
3. Circular includes (A includes B includes A) are an error. Implementations MUST
   detect and reject circular include chains.
4. Include is **textual name-resolution only** — it makes device identifiers and type
   family identifiers available for `extends` clauses, `device` directives, and type
   family matching. It does not perform textual substitution or macro expansion.
5. An included file MUST be a valid `document`. If the included file contains a
   `program` (rather than a `config_document`), the program is ignored — only device
   configurations and type family definitions are imported.
6. Duplicate device identifiers (same name defined in multiple included files) are
   an error. Duplicate type family identifiers are also an error.

**Program Header (Normative Note):**
A NEM program file contains exactly one program, terminated by end-of-file. The `program`
header is optional and provides a human-readable name for the compilation unit. When present,
the name serves as a label for diagnostics and cross-reference in documentation.
When absent, the program is anonymous. The `program` header carries no
execution semantics — it does not affect scheduling, binding, or device validity.

---

### Opcode Signatures (Normative)

The formal operand structure and attributes for each NEM opcode are defined in the
**Opcode Registry** (`spec/registry/opcodes.yaml`). The registry is the single source of
truth for opcode signatures and is referenced normatively by this specification.

The `OPCODE` terminal in the grammar matches one of the opcodes listed in the registry.

For each opcode, the registry defines:

- **Operands:** name, direction (in/out), required/optional, role, and shape/rank constraints.
- **Attributes:** name, value type, required/optional, and defaults.
- **Type families:** references to the type family definitions that govern type legality.
- **Execution unit:** primary NPM hardware unit (NMU, CSTL, DMA, etc.).
- **Hardware status:** current NPM hardware support level.
- **Status:** whether the opcode is stable, provisional, or planned for future hardware.

Operand rules:
- Operands marked **required** in the registry MUST be present in a NEM program.
- Operands marked **optional** MAY be omitted.
- All required attributes MUST be specified; optional attributes have stated defaults.

The registry schema is defined in `spec/registry/schema.json`. Tools MUST validate their
opcode tables against the registry. The contract governing the registry is documented
in `docs/contracts/opcode-registry.md`.

---

#### NPM Hardware Support Status

Not all opcodes listed above are currently implemented in NPM hardware.
The following table summarizes the hardware support status:

| Category | Opcodes | NPM Hardware Status |
|----------|---------|-------------------|
| Linear Algebra | `gemm`, `matmul` | Supported (NMU) |
| Linear Algebra (INT4) | `gemm` (i4×i8 mixed-precision) | Supported (NMU) |
| Convolution | `conv2d` | Supported (NMU) |
| Convolution (INT4) | `conv2d` (i4×i8 mixed-precision) | Supported (NMU) |
| Convolution | `conv1d`, `conv3d`, `depthwise_conv2d` | Future |
| Elementwise | `relu`, `gelu`, `silu`, `add`, `mul`, `sub`, ... | Supported (CSTL) |
| Pooling | `maxpool`, `avgpool` | Supported (CSTL) |
| Normalization | `layernorm`, `rmsnorm` | Supported (CSTL) |
| Softmax | `softmax`, `log_softmax` | Supported (CSTL) |
| Layout / View | `transpose`, `reshape`, ... | Supported (CSTL / DMA) |
| Reduction | `reduce_sum`, `reduce_max`, ... | Future |
| Type Conversion | `cast`, `quantize`, `dequantize` | Partial (CSTL store-path quantization) |
| Generic | `compute` | Escape hatch only |

Opcodes marked "Future" are defined in NEM for completeness and forward compatibility.
Programs using future opcodes are syntactically and type-legally valid but will be rejected
by binders targeting current NPM silicon.

---

#### Implementation Priority (Informative)

Beyond opcode-level hardware support, several NEM language features are defined for
completeness but are not required for current NPM hardware generations. Implementations
MAY defer these features to later stages. The following table classifies spec features
by implementation priority:

**Priority 1 — Required for current NPM hardware:**

| Feature | Spec Section | Notes |
|---------|-------------|-------|
| `const` declarations | Constant Declarations | Required for self-contained, parseable programs |
| Buffers, regions, tasks, tokens | Core Program Objects | Fundamental execution model |
| `transfer.async/sync`, `store.async/sync`, `wait` | Task Taxonomy | Core data movement and synchronization |
| `conv2d`, `gemm`/`matmul` | Compute Tasks | Supported on NMU |
| Elementwise ops (`relu`, `gelu`, `silu`, `add`, `mul`, etc.) | Compute Tasks | Supported on CSTL |
| `maxpool`, `avgpool` | Compute Tasks | Supported on CSTL |
| `layernorm`, `rmsnorm` | Compute Tasks | Supported on CSTL |
| `softmax`, `log_softmax` | Compute Tasks | Supported on CSTL |
| FLOAT literals | Formal Language Definition | Required for `epsilon`, `alpha` attributes |
| Layout/view ops (`transpose`, `reshape`, etc.) | Compute Tasks | Supported on CSTL/DMA |
| `cast` (partial), store-path quantization | Type Conversion | Partial CSTL support |
| `gemm.int4`, `conv2d.int4` (mixed-precision) | Compute Tasks | INT4 weights × INT8 activations on NMU |
| `quant_desc` (per-tensor, per-channel, per-group) | Type System | Quantization descriptors for INT4/INT8 |
| `i4`, `i8`, `u8`, `f16`, `bf16` element types | Type System | Current NPM datapath widths |
| MUST type family variants | Type Family Conformance | Listed in `opcode.mandatory` via baseline device |
| Single-engine execution | Abstract Machine Model | Minimum viable configuration |
| `@materialized`, `@readonly`, `@writeonly` | Decorators | Essential binder hints |
| `@max_in_flight(N)`, loops | Loops and Bounded Pipelining | Required for tiled pipelines |
| Device configuration (non-inherited) | Device Configuration | Single-device targeting |

**Priority 2 — Defined, may be deferred to later implementation stages:**

| Feature | Spec Section | Rationale for Deferral |
|---------|-------------|----------------------|
| `conv1d`, `conv3d`, `depthwise_conv2d` | Compute Tasks | No current NPM hardware support |
| Reduction ops (`reduce_sum`, `argmax`, etc.) | Compute Tasks | No current NPM hardware support |
| `quantize`, `dequantize` (as standalone ops) | Type Conversion | Only store-path quantization in hardware; standalone ops may require VPU |
| `compute.async` generic escape hatch | Compute Tasks | Forward-compatibility mechanism only |
| `i16`, `i32`, `u16`, `u32`, `f32` element types | Type System | MAY variants; not all devices support these widths natively |
| MAY type family variants | Type Family Conformance | Device-dependent; not guaranteed |
| Multi-engine execution (Engine `k > 0`) | Abstract Machine Model | Single-engine devices are the initial target |
| Multi-NMU instances (`NMU[k > 0]`) | Execution Units | Future hardware capability |
| `@resource` decorator | Decorators | Useful for multi-instance targets; single-instance binders assign freely |
| `@deterministic` decorator | Decorators | Requires binder support for bitwise reproducibility |
| `@memmove` decorator | Decorators | Rare use case; overlapping transfers uncommon |
| `@debug`, `@profile` decorators | Decorators | Tooling support, not execution |
| Device inheritance (`extends`) | Device Configuration | SKU differentiation; single-device configs sufficient initially |

Implementations SHOULD prioritize Priority 1 features for initial bringup and conformance.
Priority 2 features are fully specified and MUST be implemented to claim full NEM conformance,
but MAY be deferred without affecting the ability to target current NPM hardware.

---

### Type Family Grammar

Type families formalize opcode type legality. A type family declares a parameterized
set of operand-type combinations for a domain of opcodes, with named variants and
per-instantiation conformance classes.

```ebnf
(* --- Type Family Definitions --- *)

type_family_decl  ::= "type_family" family_id type_params? "{"
                        family_body
                      "}" ;

family_id         ::= ID ( "." ID )? ;                 (* e.g. gemm.float, conv2d.int8, eltwise, cast *)

type_params       ::= "<" type_param { "," type_param } ">" ;
type_param        ::= ID ":" "{" elem_type { "," elem_type } "}" ;
                                                        (* e.g. T: {f16, bf16, f32} *)

family_body       ::= { operand_binding }
                      { attribute_binding }
                      variants_block ;

operand_binding   ::= ID ":" type_expr ;               (* e.g. X: T, B: absent *)
attribute_binding ::= ID "=" attr_value ;              (* e.g. accum = f32, quant = required *)
attr_value        ::= elem_type | ID | "required" | "absent" ;

type_expr         ::= elem_type                        (* concrete: i8, f16 *)
                     | ID                               (* type variable: T, T_out *)
                     | "absent" ;                       (* operand not present *)

variants_block    ::= "variants" ":" { variant_decl } ;
variant_decl      ::= ID ":" "{" { operand_binding } "}" conformance_block ;

conformance_block ::= "conformance" ":" "{" { conformance_entry } "}" ;
conformance_entry ::= conformance_class type_instantiation ;
conformance_class ::= "MUST" | "MAY" ;
type_instantiation::= "<" elem_type { "," elem_type } ">"
                     | "" ;                             (* for non-parameterized families *)
```

**Variant Reference IDs:**
The canonical reference for device descriptors and diagnostics uses the form
`FAMILY_ID<T_instantiation>.variant` — e.g.:
- `gemm.float<f16>.no_bias`
- `gemm.int8<i16>.with_bias`
- `conv2d.float<bf16>.no_bias`
- `eltwise<f32>.default`
- `quantize<f32, i8>.default`

### Device Configuration Grammar

A device configuration declares hardware topology and supported type families/variants.
Device configurations may appear as standalone documents, included via `include`, or
inline within a NEM program.

A device may optionally extend a parent device via the `extends` clause (see Device
Inheritance below).

```ebnf
(* --- Device Configuration --- *)

device_config          ::= "device" ID extends_clause? "{" config_body_or_ext "}" ;
extends_clause         ::= "extends" ID ;

config_body_or_ext     ::= config_body                    (* base device *)
                         | derived_body ;                  (* derived device *)

config_body            ::= spec_clause
                           topology_block?
                           unit_chars_block?
                           opcode_mandatory_block
                           opcode_extended_block? ;

derived_body           ::= topology_block?
                           unit_chars_block?
                           opcode_mandatory_block?
                           opcode_extended_block? ;

spec_clause            ::= "spec_version" "=" STRING ;

topology_block         ::= "topology" "{"
                              "num_engines" "=" INT
                              "l2_size_bytes" "=" expr
                              device_units_block?
                              "per_engine" "{"
                                  { unit_decl }
                                  "l1_size_bytes" "=" expr
                              "}"
                            "}" ;
device_units_block     ::= "device_units" "{" { unit_decl } "}" ;
unit_decl              ::= unit_type "=" INT ;

(* --- Unit Characteristics --- *)

unit_chars_block       ::= "unit_characteristics" "{" { unit_chars_group } "}" ;
unit_chars_group       ::= unit_type "{" { char_decl } "}" ;
char_decl              ::= ID "=" INT ;

opcode_mandatory_block ::= "opcode.mandatory" "{" { variant_ref } "}" ;
opcode_extended_block  ::= "opcode.extended"  "{" { variant_ref } "}" ;
variant_ref            ::= family_id type_instantiation? "." ID ;
                           (* e.g. gemm.float<bf16>.no_bias, cast.default *)
```

`opcode.mandatory` and `opcode.extended` are compound keywords (lexed as single tokens).
The `opcode.` prefix is a namespace qualifier making it explicit that these blocks list
opcode family variant references. This avoids ambiguity with any future non-opcode device
capability blocks (e.g. `memory.features`, `interconnect.modes`).

The `variant_ref` production is shared between `opcode.mandatory` and `opcode.extended`
blocks in device configurations.

**Memory Capacity Fields (Normative):**
`l2_size_bytes` declares the total L2 (on-chip shared) memory capacity in bytes.
`l1_size_bytes` declares the per-engine L1 (on-chip scratchpad) memory capacity in bytes.
Both fields are required in the `topology` block. The binder uses these values to
validate buffer allocations and choose tile sizes.

**Device-Level Units (`device_units`):**
The `device_units` block declares execution units that exist at the device level, shared
across all Engines. These units are NOT valid `@resource` targets (see Decorators).
Their counts inform the binder's scheduling decisions — for example, how many concurrent
DDR↔L2 transfers can be overlapped via `sDMA`, or how many weight decompression streams
are available via `WDM`. If `device_units` is absent, the device has no device-level units.

**Unit Characteristics (`unit_characteristics`):**
The `unit_characteristics` block declares per-unit-type properties as key-value pairs
(integer values only). This mechanism serves two purposes: (a) the binder uses
characteristics for code generation decisions (e.g., choosing tile sizes based on
MAC throughput), and (b) NEM programs can be validated against device capabilities
(e.g., checking that a program's synchronization token usage does not exceed the
sequencer's limit).

The set of recognized characteristic keys is **open-ended**: unknown keys are permitted
and MUST be preserved by tools (forward compatibility). The following well-known keys
have normative semantics in this revision:

- `NMU.int4_macs`, `NMU.int8_macs`, `NMU.int16_macs`, `NMU.fp16_macs` — MACs per
  cycle per NMU instance, by datatype. Used by the binder for performance estimation.
- `SEQ.max_active_tokens` — maximum number of simultaneously live synchronization
  tokens the sequencer supports. The binder MUST ensure the lowered TCB stream does
  not exceed this limit.

### Device Inheritance (Normative)

A device configuration may extend another device configuration via the `extends` clause.
Inheritance enables both SKU differentiation and baseline reuse: the standard baseline
device (`nem_baseline_1_0`) defines MUST-class variants, and concrete devices extend it
with topology and additional opcode support.

**Inheritance Rules:**

1. A derived device inherits **all** parent fields: `spec_version`, `topology`,
   `unit_characteristics`, `opcode.mandatory`, and `opcode.extended`.
2. A derived device body (`derived_body`) MAY contain any combination of:
   `topology`, `unit_characteristics`, `opcode.mandatory`, and/or `opcode.extended`.
   A derived device MUST NOT specify `spec_version` — it is always inherited from
   the parent.
3. **Topology**: If a derived device specifies a `topology` block, it **replaces**
   the parent's topology (including `l1_size_bytes`, `l2_size_bytes`, `device_units`,
   and all `per_engine` declarations). If the parent has no topology (abstract device),
   the derived device MUST provide one.
4. **`unit_characteristics`**: The resolved `unit_characteristics` is the **merge**
   of the parent's and child's blocks. Within a unit type, child keys override
   parent keys with the same name. Across unit types, the union of all declared
   unit type groups is taken. A child cannot remove characteristics from the parent;
   it can only override or add.
5. **`opcode.mandatory`**: The resolved `opcode.mandatory` set is the **union** of
   the parent's and child's `opcode.mandatory`. Inheritance is additive only — a
   child cannot remove variants from the parent.
6. **`opcode.extended`**: The resolved `opcode.extended` set is the **union** of
   the parent's and child's `opcode.extended`. Inheritance is additive only.
7. The parent device MUST be defined before the child, either in the same file or
   made visible via `include`. The parent MAY be an abstract device (no topology).
   Multi-level inheritance is permitted (A extends B extends C). Single parent only —
   multiple inheritance is not supported.
8. **Resolution validity**: After inheritance resolution, the resolved device MUST
   satisfy all Schema Rules: topology MUST be present, `opcode.mandatory` MUST be
   non-empty, and `opcode.mandatory ∩ opcode.extended` MUST be empty.

### Program Device Directive

A NEM program may declare its target device configuration via a `device` directive
at the top of the program. Three forms are supported:

```ebnf
(* --- Program Device Directive --- *)

device_decl    ::= "device" STRING                     (* reference to external config file *)
                 | "device" ID                          (* named reference via include *)
                 | device_config ;                      (* inline device config *)
```

- **`device STRING`** — references an external device configuration file by path.
  The file is loaded and its device configuration used as the target.
- **`device ID`** — references a named device made visible via an `include` declaration.
  The identifier must match a device defined in an included file.
- **`device_config` (inline)** — defines the device configuration directly in the program.

When present, the device directive constrains the program's effective type family set
to those supported by the declared device. When absent, the program is device-agnostic
and a binder MUST determine the target device by other means.

## Worked Examples

Worked examples illustrating end-to-end lowering (ONNX → MLIR → NEM → TCB) are
provided in the companion document [examples.md](examples.md).

Examples included:

- **Conv2D + ReLU** — single-engine tiled pipeline with ping-pong buffers, device
  configuration, NEM program, and fully expanded TCB-level realization (two tiles
  plus generator rule).
- **Multi-CSTL Pipeline with @resource** — intra-engine parallelism across 4 CSTL
  instances, explicit resource binding, and graceful degradation on smaller devices.

---

## Restructuring Recommendations (Informative)

The following observations identify places where the current document order introduces
concepts before their formal definition. These are recommendations for a future
editorial revision and do not affect the normative content of this specification.

**1. Move "Design Principle: Object Attributes vs. Decorators" before "Core Program Objects".**

The distinction between attributes and decorators is foundational — it determines how
readers interpret every region and task definition. Currently it appears after the
full Task Taxonomy. Moving it earlier (between "Abstract Machine Model" and "Core
Program Objects") would allow the Regions and Tasks sections to reference the
principle without a forward jump.

**2. Introduce a brief "Decorators (Overview)" section before the Task Taxonomy.**

The Regions section references `@materialized` and `@readonly` before decorators
are formally defined. A short overview (2–3 paragraphs listing decorator categories
with one-line descriptions) placed after Core Program Objects would provide
sufficient context. The full Decorators section with normative semantics would
remain in its current position.

**3. Move "Device Configuration" into its own top-level section before the Task Taxonomy.**

The Execution Units section references the device configuration (instance counts),
and the Type Family Conformance section depends on it heavily. Currently, device
configuration is buried inside the Formal Language Definition (grammar section).
Extracting it into a standalone section would reduce forward references and make
the device model easier to find.

**4. Consolidate the Type System and Extent Consistency sections.**

The Extent Consistency section currently sits between the Type System and the
Task Taxonomy. Since it directly depends on type system concepts (`bitwidth(E)`,
`elem`, `shape`), it would read more naturally as a subsection within the Type
System.

**5. Define "import" semantics for buffers.**

The buffer attribute list references an "import flag" but does not define the
associated semantics (ownership, mutability, lifetime constraints). A brief
subsection under Buffers or a dedicated paragraph would close this gap.

---

## Appendix: Type Family Definitions (Normative)

The following type family definitions are the normative specification of opcode type
legality. Each family declares type parameters, operand bindings, attribute constraints,
and named variants with per-instantiation conformance classes (MUST/MAY).

### `conv2d` Type Families

Operands: `X` (input activation), `W` (weights), optional `B` (bias), `Y` (output).
Required attribute: `accum_type`.

```text
type_family conv2d.float<T: {f16, bf16, f32}> {
    X: T
    W: T
    Y: T
    accum = f32
    quant = absent

    variants:
      no_bias: { B: absent }
        conformance: { MUST <f16>   MAY <bf16>   MAY <f32> }
      with_bias: { B: T }
        conformance: { MUST <f16>   MAY <bf16>   MAY <f32> }
}
```

```text
type_family conv2d.int8<T_out: {i8, i16}> {
    X: i8
    W: i8
    Y: T_out
    accum = i32
    quant = required

    variants:
      no_bias: { B: absent }
        conformance: { MUST <i8> }
      with_bias: { B: i32 }
        conformance: { MUST <i8>   MAY <i16> }
}
```

Normative notes:
1) If the variant includes `B`, the program MUST provide a bias operand; if `B` is `absent`, bias MUST NOT be provided.
2) For INT8 family variants, bias type is fixed at i32 (when present). If the program has bias in a different type, it MUST insert `cast`.
3) `accum_type` MUST equal the family's `accum` attribute.
4) Additional constraints (layout NHWC/HWIO, groups, etc.) are defined by the `conv2d` opcode semantics and must be satisfied independently.

#### `conv2d.int4` (Mixed-Precision)

INT4 mixed-precision convolution: i4 weights with i8 activations (AD-6).
Quantization is required for the i4 weight operand.

```text
type_family conv2d.int4 {
    X: i8
    W: i4
    Y: i8
    accum = i32
    quant = required

    variants:
      no_bias: { B: absent }
        conformance: { MAY }
      with_bias: { B: i32 }
        conformance: { MAY }
}
```

Normative notes:
1) This family is not parameterized — it has a single fixed type combination (i4 weights × i8 activations).
2) The `W` operand MUST carry a `quant` attribute (per-tensor, per-channel, or per-group).
3) Per-group quantization (e.g., `group_size=32` or `group_size=128`) is the expected format for INT4 LLM weight compression.

### `gemm` / `matmul` Type Families

Operands: `A`, `B`, optional `C` (bias/addend), `Y` (output).
Required attribute: `accum_type`.

```text
type_family gemm.float<T: {f16, bf16, f32}> {
    A: T
    B: T
    Y: T
    accum = f32
    quant = absent

    variants:
      no_bias: { C: absent }
        conformance: { MUST <f16>   MAY <bf16>   MAY <f32> }
      with_bias: { C: T }
        conformance: { MUST <f16> }
}
```

```text
type_family gemm.int8<T_out: {i8, i16}> {
    A: i8
    B: i8
    Y: T_out
    accum = i32
    quant = required

    variants:
      no_bias: { C: absent }
        conformance: { MUST <i8> }
      with_bias: { C: i32 }
        conformance: { MUST <i8>   MAY <i16> }
}
```

Normative notes:
1) `matmul` shares the same type family legality as `gemm` unless stated otherwise by opcode definition.
2) Shape/rank legality and transpose attributes (if any) are defined by opcode semantics.

#### `gemm.int4` (Mixed-Precision)

INT4 mixed-precision matrix multiply: i4 weights with i8 activations (AD-6).
Quantization is required for the i4 weight operand.

```text
type_family gemm.int4 {
    A: i8
    B: i4
    Y: i8
    accum = i32
    quant = required

    variants:
      no_bias: { C: absent }
        conformance: { MAY }
      with_bias: { C: i32 }
        conformance: { MAY }
}
```

Normative notes:
1) This family is not parameterized — it has a single fixed type combination (i4 weights × i8 activations).
2) The `B` operand MUST carry a `quant` attribute (per-tensor, per-channel, or per-group).
3) `matmul` shares the same type family legality as `gemm.int4`.

### Elementwise Type Families

Elementwise ops (`relu`, `gelu`, `silu`, `add`, `sub`, `mul`, `min`, `max`, `clamp`, ...)
preserve shape and typically preserve element type. `gelu` and `silu` are unary
activations that reuse this family (AD-5).

```text
type_family eltwise<T: {i8, i16, i32, f16, bf16, f32}> {
    input: T
    output: T

    variants:
      default: {}
        conformance: { MUST <i8>   MUST <f16>   MAY <i16>   MAY <i32>   MAY <bf16>   MAY <f32> }
}
```

Normative notes:
1) For binary ops, both inputs MUST have the same element type unless the opcode explicitly supports mixed-type variants (which must be expressed as separate family definitions).
2) If an implementation supports saturation or special rounding for integer elementwise ops, it MUST be specified as opcode attributes; the element-type legality remains controlled by type families.

### View Type Families

View ops (`transpose`, `reshape`, ...) do not change element values, only interpretation.

```text
type_family view<T: {i8, i16, i32, f16, bf16, f32}> {
    input: T
    output: T

    variants:
      default: {}
        conformance: { MUST <i8>   MUST <f16>   MAY <i16>   MAY <i32>   MAY <bf16>   MAY <f32> }
}
```

Normative notes:
1) If the opcode changes layout/strides, the region byte-extent consistency rules MUST still hold.
2) For `reshape`, element count MUST be preserved.

### Normalization Type Families

Normalization ops (`layernorm`, `rmsnorm`) compute normalized output along a specified axis.

```text
type_family norm<T: {f16, bf16, f32}> {
    input: T
    output: T

    variants:
      default: {}
        conformance: { MUST <f16>   MAY <bf16>   MAY <f32> }
}
```

Normative notes:
1) This family covers both `layernorm` and `rmsnorm` opcodes. The opcode signature determines which optional operands (`scale`, `bias`) are permitted.
2) When `scale` and/or `bias` operands are present, their element type MUST match `T`.
3) The `epsilon` attribute is a FLOAT literal; it is not constrained by the type family.

### Softmax Type Families

Softmax ops (`softmax`, `log_softmax`) compute probability distributions along a specified axis.

```text
type_family softmax<T: {f16, bf16, f32}> {
    input: T
    output: T

    variants:
      default: {}
        conformance: { MUST <f16>   MAY <bf16>   MAY <f32> }
}
```

Normative notes:
1) This family covers both `softmax` and `log_softmax` opcodes.
2) Input and output shapes MUST be identical; the `axis` attribute selects the normalization dimension but does not alter shape.

### Type Conversion Families

#### `cast`

`cast` converts between supported element types explicitly. It is not parameterized.

```text
type_family cast {
    src: any_supported
    dst: any_supported

    variants:
      default: {}
        conformance: { MUST }
}
```

Normative notes:
1) `cast` MUST be explicit; no other opcode performs implicit type conversion.
2) Rounding/saturation behavior (if relevant) MUST be specified as opcode attributes.

#### `quantize`

`quantize` converts floating types to integer quantized types, producing `quant` metadata
on the output region.

```text
type_family quantize<T_src: {f16, f32}, T_dst: {i8}> {
    src: T_src
    dst: T_dst
    quant = required on dst

    variants:
      default: {}
        conformance: { MUST <f16, i8>   MAY <f32, i8> }
}
```

Normative notes:
1) Destination MUST carry quant metadata (scale/zero_point); the quantization parameters may be explicit attributes or derived from the region's `quant` attribute per opcode definition.

#### `dequantize`

`dequantize` converts quantized integer types to floating types.

```text
type_family dequantize<T_src: {i8}, T_dst: {f16, f32}> {
    src: T_src
    dst: T_dst
    quant = required on src

    variants:
      default: {}
        conformance: { MUST <i8, f16>   MAY <i8, f32> }
}
```

Normative notes:
1) Source MUST carry valid quant metadata.

---

### Variant Expansion Reference (Informative)

The following tables enumerate every concrete variant instantiation for implementers
who wish to cross-check against the formal type family definitions above. These tables
are **informative** — the type family definitions are normative.

#### conv2d Expansion

| Variant Reference | Class | X | W | B | Y | accum | quant |
|---|---:|---|---|---|---|---|---|
| `conv2d.int8<i8>.no_bias` | MUST | i8 | i8 | — | i8 | i32 | required |
| `conv2d.int8<i8>.with_bias` | MUST | i8 | i8 | i32 | i8 | i32 | required |
| `conv2d.int8<i16>.with_bias` | MAY | i8 | i8 | i32 | i16 | i32 | required |
| `conv2d.float<f16>.no_bias` | MUST | f16 | f16 | — | f16 | f32 | absent |
| `conv2d.float<f16>.with_bias` | MUST | f16 | f16 | f16 | f16 | f32 | absent |
| `conv2d.float<bf16>.no_bias` | MAY | bf16 | bf16 | — | bf16 | f32 | absent |
| `conv2d.float<bf16>.with_bias` | MAY | bf16 | bf16 | bf16 | bf16 | f32 | absent |
| `conv2d.float<f32>.no_bias` | MAY | f32 | f32 | — | f32 | f32 | absent |
| `conv2d.float<f32>.with_bias` | MAY | f32 | f32 | f32 | f32 | f32 | absent |
| `conv2d.int4.no_bias` | MAY | i8 | i4 | — | i8 | i32 | required |
| `conv2d.int4.with_bias` | MAY | i8 | i4 | i32 | i8 | i32 | required |

#### gemm / matmul Expansion

| Variant Reference | Class | A | B | C | Y | accum | quant |
|---|---:|---|---|---|---|---|---|
| `gemm.int8<i8>.no_bias` | MUST | i8 | i8 | — | i8 | i32 | required |
| `gemm.int8<i8>.with_bias` | MUST | i8 | i8 | i32 | i8 | i32 | required |
| `gemm.int8<i16>.with_bias` | MAY | i8 | i8 | i32 | i16 | i32 | required |
| `gemm.float<f16>.no_bias` | MUST | f16 | f16 | — | f16 | f32 | absent |
| `gemm.float<f16>.with_bias` | MUST | f16 | f16 | f16 | f16 | f32 | absent |
| `gemm.float<bf16>.no_bias` | MAY | bf16 | bf16 | — | bf16 | f32 | absent |
| `gemm.float<f32>.no_bias` | MAY | f32 | f32 | — | f32 | f32 | absent |
| `gemm.int4.no_bias` | MAY | i8 | i4 | — | i8 | i32 | required |
| `gemm.int4.with_bias` | MAY | i8 | i4 | i32 | i8 | i32 | required |

#### eltwise Expansion

| Variant Reference | Class | Input | Output |
|---|---:|---|---|
| `eltwise<i8>.default` | MUST | i8 | i8 |
| `eltwise<i16>.default` | MAY | i16 | i16 |
| `eltwise<i32>.default` | MAY | i32 | i32 |
| `eltwise<f16>.default` | MUST | f16 | f16 |
| `eltwise<bf16>.default` | MAY | bf16 | bf16 |
| `eltwise<f32>.default` | MAY | f32 | f32 |

#### view Expansion

| Variant Reference | Class | Input | Output |
|---|---:|---|---|
| `view<i8>.default` | MUST | i8 | i8 |
| `view<i16>.default` | MAY | i16 | i16 |
| `view<i32>.default` | MAY | i32 | i32 |
| `view<f16>.default` | MUST | f16 | f16 |
| `view<bf16>.default` | MAY | bf16 | bf16 |
| `view<f32>.default` | MAY | f32 | f32 |

#### norm Expansion

| Variant Reference | Class | Input | Output |
|---|---:|---|---|
| `norm<f16>.default` | MUST | f16 | f16 |
| `norm<bf16>.default` | MAY | bf16 | bf16 |
| `norm<f32>.default` | MAY | f32 | f32 |

#### softmax Expansion

| Variant Reference | Class | Input | Output |
|---|---:|---|---|
| `softmax<f16>.default` | MUST | f16 | f16 |
| `softmax<bf16>.default` | MAY | bf16 | bf16 |
| `softmax<f32>.default` | MAY | f32 | f32 |

#### cast Expansion

| Variant Reference | Class | Src | Dst |
|---|---:|---|---|
| `cast.default` | MUST | any supported | any supported |

#### quantize Expansion

| Variant Reference | Class | Src | Dst |
|---|---:|---|---|
| `quantize<f16, i8>.default` | MUST | f16 | i8 |
| `quantize<f32, i8>.default` | MAY | f32 | i8 |

#### dequantize Expansion

| Variant Reference | Class | Src | Dst |
|---|---:|---|---|
| `dequantize<i8, f16>.default` | MUST | i8 | f16 |
| `dequantize<i8, f32>.default` | MAY | i8 | f32 |

