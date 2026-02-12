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
hardware blocks within an Engine:

| Unit Type | Role | Typical Instances/Engine |
|-----------|------|------------------------|
| `NMU` | Linear algebra (GEMM, Conv, MatMul) | 1 (future: N) |
| `CSTL` | Elementwise, activation, normalization, store-back | 1–4 |
| `DMA` | Region transfers between memory levels | 1–4 |

Each Engine contains one or more instances of each unit type.
Instances are identified by a zero-based index within their type and Engine:
`NMU[0]`, `CSTL[0]`..`CSTL[3]`, `DMA[0]`..`DMA[3]`.

The number of instances per unit type per Engine is declared in the Device Capability Descriptor.

**Execution units are orthogonal to resource classes.**
Resource classes (COMPUTE, TRANSFER, STORE) describe *what an operation does*:
COMPUTE generates new data, TRANSFER and STORE move data.
Execution units describe *where an operation runs* on the hardware.

The mapping from task types to eligible execution unit types is:

- Linear algebra operations (`gemm`, `matmul`, `conv*`) → `NMU`
- Elementwise and activation operations (`relu`, `add`, `mul`, `softmax`, ...) → `CSTL`
- Store operations (`store.async`, `store.sync`) → `CSTL`
- Transfer operations (`transfer.async`, `transfer.sync`) → `DMA`

A given operation MAY be eligible for multiple unit types on future devices.

The CSTLA/CSTLB sub-unit split within each CSTL instance is microarchitectural detail.
At the NEM level, a CSTL instance is a single unit capable of both post-processing
and store-back operations. The binder maps NEM CSTL references to concrete CSTLA/CSTLB
sub-units during lowering.

When no `@resource` decorator is present (see Decorators), the binder assigns tasks to
execution unit instances freely. Programs that omit `@resource` are fully portable and
behave identically to programs written under prior spec revisions.

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
- optional import/pinning

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

Tiles exist only to structure iteration and bounded pipelining.

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

Layouts are semantic; binders may remap layouts if semantics are preserved.

---

### Quantization Descriptor

Optional quantization metadata MAY be attached:

- per-tensor: `(scale, zero_point)`
- per-channel: `(axis, scales[], zero_points[])`

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

## Byte Extent Consistency

For a typed region:

the following constraints MUST hold:

- `byte_extent >= num_elements(S) * sizeof(E)`
- Any element addressable via the declared layout or strides MUST fall within the
  `[offset, offset + byte_extent)` range of the underlying buffer.

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

WARNING: NPM does not embedded dedicated hardware operators implementing quantization operations, other than CSTL's capability to store data and apply some quantization on-the-fly. Quantization operators, if needed, MAY be implemented on VPU.

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

- **MUST** — all conformant NEM implementations MUST support this family variant
  instantiation. A binder targeting any NEM device MAY assume MUST variants are
  available without consulting the device configuration.

- **MAY** — implementations MAY support this family variant instantiation; support is
  device-dependent. A program that relies on a MAY variant is portable only to devices
  that explicitly advertise support via the device configuration.

###### Baseline Type Family Set

The **Baseline Type Family Set** is the complete enumeration of all MUST family
variant instantiations defined by a given revision of this specification. It is
identified by a version string of the form `nem_baseline_<major>.<minor>`.

The Baseline Type Family Set for this revision is **`nem_baseline_1.0`** and comprises:

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
| Type Conversion | `cast.any_supported` | `cast` |
| | `quantize<f16, i8>.default` | `quantize` |
| | `dequantize<i8, f16>.default` | `dequantize` |

Formal type family definitions are provided in the Appendix.

###### Optional Type Family Inventory

The following MAY family variant instantiations are defined by this revision.
Devices advertise support for zero or more of these via the device configuration:

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
| Type Conversion | `quantize<f32, i8>.default` | `quantize` |
| | `dequantize<i8, f32>.default` | `dequantize` |

###### Baseline Conformance Rule (Normative)

A conformant NEM implementation MUST support every MUST family variant
instantiation in the Baseline Type Family Set corresponding to the spec revision
it claims conformance with.

An implementation that supports additional MAY family variant instantiations
MUST declare them in its device configuration.

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
2. `baseline` MUST identify the Baseline Type Family Set version. It MUST match
   the baseline defined by `spec_version`.
3. MUST family variant instantiations are **implicitly available** on any conformant device.
   They MUST NOT appear in `opcode.mandatory` or `opcode.extended` blocks. A binder
   encountering a MUST variant in either block SHOULD emit a diagnostic warning and
   MUST ignore the redundant entry.
4. `opcode.mandatory` lists MAY family variant instantiations that are **guaranteed**
   on this device. A compiler targeting this device MAY unconditionally use any variant
   in `opcode.mandatory` without runtime capability queries.
5. `opcode.extended` lists MAY family variant instantiations that are **conditionally
   available** on this device. Their presence indicates the device supports these
   variants, but a compiler targeting a family of devices (via inheritance) SHOULD
   confirm per-device support.
6. `opcode.mandatory ∩ opcode.extended` MUST be empty. A variant MUST NOT appear in
   both blocks. A binder encountering a duplicate SHOULD emit a diagnostic warning
   and MUST ignore the redundant entry.
7. All topology fields MUST be ≥ 1.
8. After device resolution (including inheritance), `opcode.mandatory` MUST be
   non-empty. Every conformant device MUST guarantee at least one MAY family
   variant instantiation beyond the baseline. A resolved device with an empty
   `opcode.mandatory` set is invalid.

###### Effective Type Family Set

For a given target device (after resolving inheritance, if applicable), the
**effective type family set** for opcode `op` is:

```text
effective[op] = baseline_must[op]
              ∪ opcode.mandatory[op]
              ∪ opcode.extended[op]
```

where `baseline_must[op]` is the subset of the Baseline Type Family Set applicable
to `op`, `opcode.mandatory[op]` is the set of MAY family variants listed in the
device's `opcode.mandatory` block (empty if not declared), and `opcode.extended[op]`
is the set of MAY family variants listed in the device's `opcode.extended` block
(empty if not declared).

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

**Minimal device (baseline + minimal BF16):**

```text
device npm_lite {
    spec_version = "NEM-1.0"
    baseline     = "nem_baseline_1.0"

    topology {
        num_engines = 1
        per_engine {
            NMU  = 1
            CSTL = 2
            DMA  = 2
        }
    }

    opcode.mandatory {
        gemm.float<bf16>.no_bias
        eltwise<bf16>.default
        view<bf16>.default
    }
}
```

Effective set: baseline MUST variants + BF16 GEMM, elementwise, and view.

**Mid-range device with BF16 support:**

```text
device npm_mid {
    spec_version = "NEM-1.0"
    baseline     = "nem_baseline_1.0"

    topology {
        num_engines = 2
        per_engine {
            NMU  = 1
            CSTL = 2
            DMA  = 2
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

Effective set: baseline MUST + `opcode.mandatory` BF16 variants.

**High-end base device with BF16 mandatory and selective FP32:**

```text
device npm_pro {
    spec_version = "NEM-1.0"
    baseline     = "nem_baseline_1.0"

    topology {
        num_engines = 4
        per_engine {
            NMU  = 2
            CSTL = 4
            DMA  = 4
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

Effective set: baseline MUST + `opcode.mandatory` BF16 + `opcode.extended` FP32 GEMM.

**SKU extending base device with additional FP32 support:**

```text
device npm_pro_x1 extends npm_pro {
    opcode.extended {
        conv2d.float<f32>.no_bias
        eltwise<f32>.default
    }
}
```

Resolved `npm_pro_x1`: inherits all of `npm_pro`'s fields (spec_version, baseline,
topology, `opcode.mandatory`). The `opcode.extended` set is the union of parent and
child: `{ gemm.float<f32>.no_bias, conv2d.float<f32>.no_bias, eltwise<f32>.default }`.

**Multi-file example:**

```text
# file: devices/npm_pro.nem
device npm_pro {
    spec_version = "NEM-1.0"
    baseline     = "nem_baseline_1.0"
    topology {
        num_engines = 4
        per_engine { NMU = 2  CSTL = 4  DMA = 4 }
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

## Formal Language Definition (EBNF)

### Grammar

```ebnf
(* --- Lexical --- *)

comment        ::= "#" { any_char_except_newline } NEWLINE ;

(* Comments begin with '#' and extend to end of line.
   They may appear on their own line or after any token.
   Comments are stripped before parsing. *)

(* --- Top Level --- *)

document       ::= { include_decl } top_level ;
top_level      ::= program | device_config ;
include_decl   ::= "include" STRING ;

program        ::= device_decl? program_header? { stmt } ;
program_header ::= "program" ID ":" ;
stmt           ::= decl | task | loop | ";" ;

(* --- Declarations --- *)

decl           ::= buffer_decl | region_decl | let_decl ;
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
primary        ::= INT | ID | "(" expr ")" ;
binop          ::= "+" | "-" | "*" | "/" | "mod" ;

(* --- Values --- *)

value          ::= expr | STRING | "[" value_list? "]" | region_expr ;
value_list     ::= value { "," value } ;

(* --- Decorators --- *)

decos          ::= { deco } ;
deco           ::= "@" ID ( "(" deco_args ")" )? ;
deco_args      ::= value { "," value }
                  | unit_type "[" expr "]" ;           (* for @resource *)
unit_type      ::= "NMU" | "CSTL" | "DMA" ;
```

**Document Model (Normative Note):**
A NEM file is a `document` — a sequence of zero or more `include` declarations followed
by exactly one top-level construct: either a `program` or a `device_config`. This means
device configuration files and program files share the same document grammar but differ
in their top-level content.

**Include Semantics (Normative):**

1. An `include` declaration makes named device configurations from the referenced file
   visible in the current file's scope.
2. The include path (a STRING literal) is resolved **relative to the directory of the
   including file**.
3. Circular includes (A includes B includes A) are an error. Implementations MUST
   detect and reject circular include chains.
4. Include is **textual name-resolution only** — it makes device identifiers available
   for `extends` clauses and `device` directives. It does not perform textual
   substitution or macro expansion.
5. An included file MUST be a valid `document`. If the included file contains a
   `program` (rather than a `device_config`), the program is ignored — only device
   configurations are imported.
6. Duplicate device identifiers (same name defined in multiple included files) are
   an error.

**Program Header (Normative Note):**
A NEM program file contains exactly one program, terminated by end-of-file. The `program`
header is optional and provides a human-readable name for the compilation unit. When present,
the name serves as a label for diagnostics and cross-reference in documentation.
When absent, the program is anonymous. The `program` header carries no
execution semantics — it does not affect scheduling, binding, or device validity.

---

### Opcode Signatures (Normative)

This section defines the formal operand structure and attributes for each opcode.
The `OPCODE` terminal in the grammar matches one of the opcodes listed below.

Operand roles:
- Operands listed as **required** MUST be present.
- Operands listed as **optional** (in brackets `[]`) MAY be omitted.
- All required attributes MUST be specified; optional attributes have stated defaults.

#### Linear Algebra

##### `gemm` / `matmul`

```text
gemm.async
    in   A, B [, C]
    out  Y
    accum_type = <elem_type>          // required
```

| Operand | Role | Notes |
|---------|------|-------|
| `A` | Input activation | Rank ≥ 2 |
| `B` | Weights / second operand | Rank ≥ 2, inner dims must match A |
| `C` | Bias / addend (optional) | Broadcastable to Y shape |
| `Y` | Output | Shape derived from A, B dims |

Required attributes: `accum_type`.

#### Convolution

##### `conv2d`

```text
conv2d.async
    in   X, W [, B]
    out  Y
    pads       = [pad_top, pad_left, pad_bottom, pad_right]
    strides    = [stride_h, stride_w]
    dilations  = [dilation_h, dilation_w]
    groups     = <INT>                // default: 1
    accum_type = <elem_type>          // required
```

| Operand | Role | Notes |
|---------|------|-------|
| `X` | Input activation | Rank 4, layout NHWC |
| `W` | Weights | Rank 4, layout HWIO |
| `B` | Bias (optional) | Rank 1, shape [Cout] |
| `Y` | Output | Shape derived from X, W, pads, strides, dilations, groups |

Required attributes: `pads`, `strides`, `dilations`, `accum_type`.
Optional attributes: `groups` (default 1).

##### `conv1d`

```text
conv1d.async
    in   X, W [, B]
    out  Y
    pads       = [pad_left, pad_right]
    strides    = [stride_w]
    dilations  = [dilation_w]
    groups     = <INT>                // default: 1
    accum_type = <elem_type>          // required
```

Operand roles follow the same pattern as `conv2d` with rank reduced by one.

##### `conv3d`

```text
conv3d.async
    in   X, W [, B]
    out  Y
    pads       = [pad_d0, pad_h0, pad_w0, pad_d1, pad_h1, pad_w1]
    strides    = [stride_d, stride_h, stride_w]
    dilations  = [dilation_d, dilation_h, dilation_w]
    groups     = <INT>                // default: 1
    accum_type = <elem_type>          // required
```

Operand roles follow the same pattern as `conv2d` with rank increased by one.

##### `depthwise_conv2d`

```text
depthwise_conv2d.async
    in   X, W [, B]
    out  Y
    pads       = [pad_top, pad_left, pad_bottom, pad_right]
    strides    = [stride_h, stride_w]
    dilations  = [dilation_h, dilation_w]
    accum_type = <elem_type>          // required
```

Equivalent to `conv2d` with `groups = Cin` (each input channel convolved independently).

#### Elementwise

##### Unary Operations

```text
relu.async          in X    out Y
leaky_relu.async    in X    out Y    alpha = <FLOAT>
sigmoid.async       in X    out Y
tanh.async          in X    out Y
exp.async           in X    out Y
log.async           in X    out Y
sqrt.async          in X    out Y
abs.async           in X    out Y
neg.async           in X    out Y
```

Input and output shapes MUST be identical. Element types MUST match.
`leaky_relu` requires the `alpha` attribute (slope for negative values).

##### Binary Operations

```text
add.async     in A, B    out Y
sub.async     in A, B    out Y
mul.async     in A, B    out Y
div.async     in A, B    out Y
min.async     in A, B    out Y
max.async     in A, B    out Y
pow.async     in A, B    out Y
```

A and B shapes MUST be identical (no implicit broadcasting).
Element types of A, B, and Y MUST match.

##### Other

```text
clamp.async   in X    out Y    min_val = <value>    max_val = <value>
```

#### Pooling

##### `maxpool` / `avgpool`

```text
maxpool.async
    in   X
    out  Y
    kernel_shape = [kh, kw]
    pads         = [pad_top, pad_left, pad_bottom, pad_right]
    strides      = [stride_h, stride_w]
```

| Operand | Role | Notes |
|---------|------|-------|
| `X` | Input | Rank 4, layout NHWC |
| `Y` | Output | Shape derived from X, kernel_shape, pads, strides |

Element type is preserved. `avgpool` follows the same signature.

#### Layout / Tensor View

```text
transpose.async     in X    out Y    perm = [<INT>, ...]
reshape.async       in X    out Y    target_shape = [<INT>, ...]
slice.async         in X    out Y    starts = [...]  ends = [...]  axes = [...]  steps = [...]
concat.async        in X0, X1, ...   out Y    axis = <INT>
split.async         in X    out Y0, Y1, ...   axis = <INT>  split_sizes = [...]
pad.async           in X    out Y    pads = [...]  mode = <ID>  constant_value = <value>
gather.async        in X, indices    out Y    axis = <INT>
```

These operations do not change element values, only their interpretation.
Element count MUST be preserved for `reshape`. Output types match input types.

#### Reduction

```text
reduce_sum.async    in X    out Y    axes = [<INT>, ...]    keepdims = <BOOL>
reduce_max.async    in X    out Y    axes = [<INT>, ...]    keepdims = <BOOL>
reduce_min.async    in X    out Y    axes = [<INT>, ...]    keepdims = <BOOL>
argmax.async        in X    out Y    axis = <INT>           keepdims = <BOOL>
argmin.async        in X    out Y    axis = <INT>           keepdims = <BOOL>
```

Output rank is derived from reduction axes and `keepdims`.
`argmax` / `argmin` output integer index types.

#### Type Conversion

```text
cast.async          in X    out Y
quantize.async      in X    out Y                    // Y.quant MUST be set
dequantize.async    in X    out Y                    // X.quant MUST be set
```

`cast` converts between any supported element types. No implicit casts elsewhere.
`quantize` requires the output region to carry a quantization descriptor.
`dequantize` requires the source region to carry a quantization descriptor.

#### Generic Escape Hatch

```text
compute.async
    in   ...
    out  ...
    op   = <STRING>
    attrs = { ... }
```

Used for forward compatibility. Binders MAY reject unknown operations.

---

#### NPM Hardware Support Status

Not all opcodes listed above are currently implemented in NPM hardware.
The following table summarizes the hardware support status:

| Category | Opcodes | NPM Hardware Status |
|----------|---------|-------------------|
| Linear Algebra | `gemm`, `matmul` | Supported (NMU) |
| Convolution | `conv2d` | Supported (NMU) |
| Convolution | `conv1d`, `conv3d`, `depthwise_conv2d` | Future |
| Elementwise | `relu`, `add`, `mul`, `sub`, ... | Supported (CSTL) |
| Pooling | `maxpool`, `avgpool` | Supported (CSTL) |
| Layout / View | `transpose`, `reshape`, ... | Supported (CSTL / DMA) |
| Reduction | `reduce_sum`, `reduce_max`, ... | Future |
| Type Conversion | `cast`, `quantize`, `dequantize` | Partial (CSTL store-path quantization) |
| Generic | `compute` | Escape hatch only |

Opcodes marked "Future" are defined in NEM for completeness and forward compatibility.
Programs using future opcodes are syntactically and type-legally valid but will be rejected
by binders targeting current NPM silicon.

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

family_id         ::= ID "." ID ;                     (* e.g. gemm.float, conv2d.int8 *)

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
                         | opcode_extended_block ;         (* derived device: only opcode.extended *)

config_body            ::= spec_clause
                           baseline_clause
                           topology_block
                           opcode_mandatory_block?
                           opcode_extended_block? ;

spec_clause            ::= "spec_version" "=" STRING ;
baseline_clause        ::= "baseline" "=" STRING ;

topology_block         ::= "topology" "{"
                              "num_engines" "=" INT
                              "per_engine" "{" { unit_decl } "}"
                            "}" ;
unit_decl              ::= unit_type "=" INT ;

opcode_mandatory_block ::= "opcode.mandatory" "{" { variant_ref } "}" ;
opcode_extended_block  ::= "opcode.extended"  "{" { variant_ref } "}" ;
variant_ref            ::= family_id type_instantiation "." ID ;
                           (* e.g. gemm.float<bf16>.no_bias *)
```

`opcode.mandatory` and `opcode.extended` are compound keywords (lexed as single tokens).
The `opcode.` prefix is a namespace qualifier making it explicit that these blocks list
opcode family variant references. This avoids ambiguity with any future non-opcode device
capability blocks (e.g. `memory.features`, `interconnect.modes`).

The `variant_ref` production is shared between `opcode.mandatory` and `opcode.extended`
blocks in device configurations.

### Device Inheritance (Normative)

A device configuration may extend another device configuration via the `extends` clause.
Inheritance enables SKU differentiation: a base device defines the common configuration
and derived devices add to the `opcode.extended` set.

**Inheritance Rules:**

1. A derived device inherits **all** parent fields: `spec_version`, `baseline`,
   `topology`, `opcode.mandatory`, and `opcode.extended`.
2. The body of a derived device MUST contain **only** an `opcode.extended` block.
   Any other field (spec_version, baseline, topology, opcode.mandatory) in a derived
   device body is a parse error.
3. The derived device's `opcode.extended` set is the **union** of the parent's
   `opcode.extended` and the child's `opcode.extended`. Inheritance is additive only —
   a child cannot remove variants from the parent.
4. The parent device MUST be a concrete device (not forward-declared) and MUST be
   defined before the child, either in the same file or made visible via `include`.
5. Multi-level inheritance is permitted (A extends B extends C). Single parent only —
   multiple inheritance is not supported.
6. The resolved device is the parent's full configuration with the child's
   `opcode.extended` variants appended to the parent's `opcode.extended` set.
7. The `opcode.mandatory ∩ opcode.extended` disjointness rule (Schema Rule 6) applies
   to the **resolved** device, not just to individual declarations.

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

### Elementwise Type Families

Elementwise ops (`relu`, `add`, `sub`, `mul`, `min`, `max`, `clamp`, ...) preserve shape
and typically preserve element type.

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

