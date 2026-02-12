# NEM: An Execution Model for NeuPro-M
**Architectural Whitepaper**

---

## Introduction and Problem Statement

NeuPro-M is a neural network accelerator whose defining characteristic is **explicit, software-managed execution** across a multi-level memory hierarchy (DDR, L2, L1), orchestrated through DMA engines and specialized compute pipelines rather than implicit caching and hardware scheduling. This architectural choice enables high utilization, predictable latency, and precise control over bandwidth and storage. At the same time, it comes with significant challenges related to programming the device.

In NeuPro-M, performance and correctness are no longer primarily determined by which mathematical operators are invoked, but by **how computation, data movement, synchronization, and memory reuse are scheduled over time**. Decisions such as when to prefetch tiles, how many tiles are in flight, where intermediate results are materialized, and when buffers can be safely reused are first-order concerns. These decisions cannot be delegated entirely to hardware, nor can they be expressed meaningfully at the level of raw hardware control buffers without sacrificing portability and maintainability.

Current NeuPro-M software software stack is built around 3 layers of abstractions:

- At the **upper level**, graph-based representations such as ONNX (and most ML frameworks) describe *what* computation should be performed, while intentionally omitting execution semantics.
- At the **intermediate** level, an intermediate representation inherited from compiler framework used to build the graph compiler, aimed at lowering the upper level to the lowest levels. Relay is TVM's itnermediate format (IR) used today, while MLIR is being considered for next generation graph compiler
- At the **lowest level**, Task Control Buffers (TCBs) describe *how* execution occurs in full detail, but in a form that is tightly coupled to microarchitectural specifics and unstable across hardware revisions.

A critical gap is a **proper architectural execution model** tailored to NeuPro-M's software-managed design. Currently, the only representation that captures such view is the lowest level, aka TCB. While TCB is the ultimate machine-level code that needs to be generated to execute a neural network on NPM, using it without a higher, well-defined, architectural execution model, creates the following challenges:
- Seperation of concerns: generating machine code from high-level program descriptions is a known challenging problem. The industry has developer entire methodologies for CPUs, GPUs and DSPs, including the definition of ISA vs Micro-code to separate the HW/SW contract from micro-architecture implementation details. NPM lacks such well-defined abstractions
- Communication between hardware and software teams is difficult, because there is no common "language" / abstract view of the main hardware mechanisms. Specifically, only a handful of software engineers have an in-depth understanding of the NPM hardware, while many more need to understand it to develop software. Conversly, hardware architects need to understand impact of their micro-architecture across many layers of the software stack, given that there is no "isolation" layer keeping micro-architecture optimization hidden from upper software layers
- Without a well-defined architecture spec (separate from micro-architecture), any hardware change may impact multiple software layers, not only with respect to performance, but also functional correctness. It is also difficult for software architects to understand which software layers are impacted by a hardware evolution

NEM (NeuPro-M Execution Model) is introduced to fill this gap, as an intermediate abstraction. The overall stack looks like this: ONNX (and/or other) -> MLIR -> NEM -> TCB. 

Note that although NEM's current specification is in the form of a language specification, it is possible, and in fact, expected, that NEM will have multiple implementations besides the language format:
- an MLIR dialect so that a graph compiler can lower representations to NEM and then simply emit code
- a bytecode representation. Using this representation, it becomes possible ship binaries of pre-compiled NEM codes, with the ability to convert them to TCBs later (similar to PTX)

NEM's main benefits are:
- A well-defined architecture abstraction layer suitable for programming the NPM hardware. The level of abstraction is :
  - "low enough" to expose all meaningful hardware mechanisms that define the essence of the hardware mechanisms so that it becomes possible to generate hardware-optimized code that takes into account its main characteristics,
  - while being "high enough" so that it hides hardware mechanisms that deal with hardware constraints but should be invisble to software engineers (well, except maybe a handful number of software engineers, aka deep firmware engineers) that will have to understand these details. With NEM though, they can focus their knowledge and expertise on a well-bounded scope: understand NEM, TCB, and how to translate from NEM to TCB. These engineers won't have to understand neural networks, and earlier compiler passes
- An intermediate abstraction capable of simulating all NPM parallel behavior, possibly randomizing execution to ensure that architecture correctness is guaranteed across micro-architecture variants
- An intermediate lowering step enabling software developers (or compilers) to write code without having to understand and master micro-architecture details that affect performance tuning but not functional correctness of the entire dataflow
- A portable layer across:
  - NPM architecture versions
  - Execution environments such as MLIR, TVM, Llama.cpp, etc
- An isolation layer hiding micro-architecture so that:
  - micro-architecture information is structurally kept confined below NEM, rather than propagate throughout the entire compiler stack with no defined layering strategy
  - micro-architecture details are hidden from most of the software developers (except those writing the lowering from NEM to TCB)
- A stable layer that isolates the software stack from hardware evolutions
- A formal specification of hardware features that matter to software programmers, for each hardware variant, and the ability to version-control it and use this information within the compiler stack "automatically"
- Enforce program validity at compile time isntead of debugging program that are invalid "by construction" that could be detected by checking architecture rules
- Validate the functional correctness of a progam at a level of abstraction that is easier to debug than TCB (requires a NEM simulator)
- Use a NEM simulator as reference to check various micro-architecture correctness (same as checking an ISA implementation vs reference ISA simulator for a processor)

---

## Why Existing Abstractions Are Insufficient

### ONNX and Graph-Level Representations

ONNX is an operator-centric, declarative representation intended to express mathematical computation and tensor dependencies. Its purpose is portability of *functional intent*, not control of execution.

As a result, ONNX deliberately omits any notion of: memory hierarchy levels (DDR vs L2 vs L1), explicit data movement, overlapping DMA and compute, buffer lifetime and reuse, partial availability of tensors (e.g., tile-level readiness), and resource constraints such as finite DMA engines or store units.

For NeuPro-M, these omissions are not incidental details; they are central to both correctness and performance. ONNX therefore cannot serve as an execution-level abstraction for NeuPro-M. It defines *what* must be computed, but provides no way to express *how* that computation is scheduled on a software-managed accelerator.

### MLIR (Affine / Async)

MLIR provides a flexible infrastructure for building compilers and lowering high-level representations toward hardware. Its affine and async dialects can express loops, tiling, and asynchronous operations with dependencies, making it well suited as a **compiler internal representation**.

However, MLIR is not designed to be a **stable architectural execution contract**. Its IRs are intended to be transformed aggressively, evolve rapidly, and remain target-agnostic. They do not carry the obligation of long-term backward compatibility or architectural stability.

NeuPro-M requires a representation that: survives hardware revisions, can be produced by multiple independent compilers, can be validated independently of the compiler that produced it, and can be rebound or JIT-compiled to different microarchitectural instances. MLIR is an excellent tool for producing such a representation, but it is not itself that representation.

### PTX as an Analogy

NVIDIA's PTX demonstrates the value of a stable, virtual execution representation that is bound to hardware late, via JIT compilation or install-time lowering. This separation of concerns is highly relevant to NeuPro-M. However, PTX is fundamentally **instruction- and register-centric** and assumes massive numbers of lightweight threads, hardware-managed caches, and implicit scheduling by hardware. NeuPro-M does not share these assumptions. What is adopted is the architectural principle: a **portable execution representation with late binding**, adapted to NeuPro-M's region- and task-based execution semantics.

### Task Control Buffers (TCBs)

TCBs provide the final, hardware-consumable description of execution. They encode exact physical addresses, bank and slice selection, DMA burst configuration, store format modes, arbitration hints, and tag-based synchronization and chaining.

While TCBs are precise and complete, they expose microarchitectural mechanisms rather than architectural intent. Their contents are sensitive to changes in internal buffering, banking, store pipelines, and interconnect topology, even when the architectural behavior of NeuPro-M remains unchanged.

As a result, TCBs are unsuitable as a software-facing programming interface or long-term contract. They are the correct *output* of a binding process, not the appropriate level at which execution intent should be expressed.

---

## The NEM Proposal: Key Concepts

NEM defines an explicit **architectural execution model** positioned between graph-level IRs and hardware-bound TCBs. It is executable but not fully bound: it defines *what must happen* and *what may overlap*, while leaving *how exactly it happens* to the binder that produces TCBs.

### Region-Centric Data Model

All computation and data movement operate on **regions** — bounded, typed views into buffers at explicit memory levels (DDR, L2, L1). Regions carry intrinsic attributes (buffer handle, offset, extent, element type, shape, layout) and optional decorators that refine binder behavior. This enables tiles to be expressed as views into larger tensors, supports halo regions and partial overlaps, and enables explicit reasoning about reuse and aliasing.

### Explicit Three-Level Memory Hierarchy

The abstract machine defines three memory levels: DDR (off-chip), L2 (on-chip shared), and L1 (on-chip Engine-local scratchpad). Memory is explicitly managed, non-coherent, capacity-limited, and accessed only through explicit tasks. There is no implicit caching or coherence.

### Multi-Engine, Multi-Unit Abstract Machine

An NPM device is composed of one or more **Engines**, each with a local Sequencer, local L1 scratchpad, and local access to execution resources. Within each Engine, named execution unit types (NMU for linear algebra, CSTL for elementwise/activation/store, DMA for transfers) may exist in multiple instances. Programs may optionally bind tasks to specific units via the `@resource` decorator, or leave assignment to the binder for portability.

### Explicit Tasks with Dedicated Opcodes

Both data transfers and computation are represented as explicit tasks. Compute tasks use dedicated opcodes (`gemm`, `conv2d`, `relu`, etc.) with fixed operand structure, enabling static validation and type checking. Tasks may execute asynchronously and produce completion tokens for synchronization.

### Token-Based Dependency Model

Ordering and readiness are expressed via explicit tokens produced by tasks. There is no implicit global sequencing. The `wait` task blocks until specified tokens are satisfied. This gives the binder maximum freedom to reorder and overlap operations within the dependency constraints.

### Bounded Pipelining

Tiling is unavoidable on NeuPro-M and is expressed using first-class loop constructs. The `@max_in_flight(N)` decorator bounds the number of concurrently active iterations, simultaneously constraining memory safety (safe buffer reuse via ping-pong or ring schemes), resource consumption (analyzable worst-case demand), and execution predictability (no unbounded queues or implicit backpressure).

### Fusion via Materialization Semantics

Fusion is controlled through the `@materialized` decorator. Regions marked `@materialized` must be produced as architectural values; unmarked regions may be fused, streamed, or bypassed by the binder. This gives the programmer explicit control over fusion boundaries without encoding fusion decisions directly.

### Static Type System with Device-Aware Conformance

All regions carry explicit element types, shapes, and layouts. Opcode type legality is defined through type families with conformance classes (MUST/MAY). Device configurations declare which type combinations are available, enabling compile-time validation that a program is legal for its target device.

### Clean Separation of Attributes and Decorators

Object attributes (buffer handle, offset, extent, element type, shape, layout) are intrinsic — a program cannot execute without them. Decorators (`@materialized`, `@resource`, `@readonly`, `@max_in_flight`, etc.) refine binder behavior but can be removed without affecting correctness. This yields a clean, layered validation model.

### Strict Separation from Microarchitecture

Bank selection, burst modes, store formats, arbitration, and path legality are explicitly excluded from the model. This ensures that NEM programs survive hardware evolution — microarchitectural churn is isolated in the binder; everything above NEM remains stable.

---

## NEM in Action

The following examples show NEM applied to common neural-network building blocks. Each example targets a minimal single-engine device and demonstrates the core execution pattern: declare buffers at each memory level, tile the computation with bounded pipelining, prefetch via DMA, compute, and store back.

### Example 1 — Conv2D + ReLU (Tiled Inference Pipeline)

A fused convolution-activation pipeline, the most common pattern in CNN inference. Two tiles overlap in flight (`@max_in_flight(2)`) using ping-pong L1 buffers.

```text
device "npm_lite.cfg"

program conv2d_relu:

# --- Compile-time constants ---
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

buffer X_L1 : L1 (size=2*tileX_bytes, align=64)
buffer W_L1 : L1 (size=tileW_bytes,   align=64)
buffer Y_L1 : L1 (size=2*tileY_bytes, align=64)

loop i in [0..T-1] @max_in_flight(2):

  let X_tile_i = region(X_L2, i * tileX_bytes, tileX_bytes)
                 elem=i8, shape=[1,TiH,TiW,Cin], layout=NHWC

  let Y_tile_i = region(Y_L2, i * tileY_bytes, tileY_bytes)
                 elem=i8, shape=[1,ToH,ToW,Cout], layout=NHWC
                 @materialized

  let X_pp_i = region(X_L1, (i mod 2)*tileX_bytes, tileX_bytes)
               elem=i8, shape=[1,TiH,TiW,Cin], layout=NHWC

  let Y_pp_i = region(Y_L1, (i mod 2)*tileY_bytes, tileY_bytes)
               elem=i8, shape=[1,ToH,ToW,Cout], layout=NHWC
               @materialized

  let W_l1 = region(W_L1, 0, tileW_bytes)
             elem=i8, shape=[Kh,Kw,Cin,Cout], layout=HWIO

  let B_l2 = region(B_L2, 0, bias_bytes)
             elem=i32, shape=[Cout], layout=C
             @readonly

  tX = transfer.async(dst=X_pp_i, src=X_tile_i)
  tW = transfer.async(
         dst=W_l1,
         src=region(W_L2, 0, tileW_bytes)
             elem=i8, shape=[Kh,Kw,Cin,Cout], layout=HWIO
       )
  wait(tX, tW)

  tC = conv2d.async
          in  X_pp_i, W_l1, B_l2
          out Y_pp_i
          deps=[tX, tW]
          pads=[1,1,1,1]
          strides=[1,1]
          dilations=[1,1]
          groups=1
          accum_type=i32

  tR = relu.async
          in  Y_pp_i
          out Y_pp_i @materialized
          deps=[tC]

  tS = store.async(dst=Y_tile_i, src=Y_pp_i, deps=[tR])

endloop
```

**What to notice:**
- **Buffers** are declared at L2 (full tensors) and L1 (working tiles). L1 buffers are sized for 2 slots to support ping-pong.
- **Regions** are typed views: `X_pp_i` selects the current ping-pong slot using `(i mod 2)`.
- **Tokens** (`tX`, `tW`, `tC`, `tR`, `tS`) thread dependencies through the pipeline — the binder is free to overlap anything not ordered by tokens.
- **`@max_in_flight(2)`** bounds concurrent iterations to 2, guaranteeing safe L1 reuse.
- **`@materialized`** on `Y_pp_i` tells the binder that the ReLU output must exist as a real value (no fusing it away).

### Example 2 — GEMM + Bias + ReLU (Fully-Connected / Attention Layer)

A tiled matrix multiply typical of transformer attention or MLP layers. The same execution pattern applies — only the compute opcode changes from `conv2d` to `gemm`.

```text
device "npm_lite.cfg"

program gemm_bias_relu:

# --- Compile-time constants ---
const TiM = 64
const K = 256
const N = 128
const T = 4

const elem_bytes = 2                        # f16 = 2 bytes per element
const tileA_bytes = TiM * K * elem_bytes     # 32768
const tileB_bytes = K * N * elem_bytes       # 65536
const tileY_bytes = TiM * N * elem_bytes     # 16384
const bias_bytes = N * elem_bytes            # 256

buffer A_L2 : L2 (size=T * tileA_bytes, align=64)
buffer B_L2 : L2 (size=tileB_bytes, align=64)
buffer C_L2 : L2 (size=bias_bytes, align=64)
buffer Y_L2 : L2 (size=T * tileY_bytes, align=64)

buffer A_L1 : L1 (size=2*tileA_bytes, align=64)
buffer B_L1 : L1 (size=tileB_bytes,   align=64)
buffer Y_L1 : L1 (size=2*tileY_bytes, align=64)

loop i in [0..T-1] @max_in_flight(2):

  let A_tile_i = region(A_L2, i * tileA_bytes, tileA_bytes)
                 elem=f16, shape=[TiM, K], layout=MK

  let Y_tile_i = region(Y_L2, i * tileY_bytes, tileY_bytes)
                 elem=f16, shape=[TiM, N], layout=MN
                 @materialized

  let A_pp_i = region(A_L1, (i mod 2)*tileA_bytes, tileA_bytes)
               elem=f16, shape=[TiM, K], layout=MK

  let Y_pp_i = region(Y_L1, (i mod 2)*tileY_bytes, tileY_bytes)
               elem=f16, shape=[TiM, N], layout=MN
               @materialized

  let B_l1 = region(B_L1, 0, tileB_bytes)
             elem=f16, shape=[K, N], layout=KN

  let C_l2 = region(C_L2, 0, bias_bytes)
             elem=f16, shape=[N], layout=N
             @readonly

  tA = transfer.async(dst=A_pp_i, src=A_tile_i)
  tB = transfer.async(
         dst=B_l1,
         src=region(B_L2, 0, tileB_bytes)
             elem=f16, shape=[K, N], layout=KN
       )
  wait(tA, tB)

  tG = gemm.async
         in  A_pp_i, B_l1, C_l2
         out Y_pp_i
         deps=[tA, tB]
         accum_type=f32

  tR = relu.async
         in  Y_pp_i
         out Y_pp_i @materialized
         deps=[tG]

  tS = store.async(dst=Y_tile_i, src=Y_pp_i, deps=[tR])

endloop
```

**What to notice:**
- The structure is identical to Conv2D — NEM's execution model is **uniform** across operation types. The programming pattern (prefetch → compute → post-op → store) remains the same.
- **`gemm.async`** with `accum_type=f32` uses f16 inputs but accumulates in f32 for precision — matching the `gemm.float<f16>.with_bias` type family.
- Bias `C_l2` is marked `@readonly` — the binder knows it can be shared across iterations without hazard.

### Example 3 — Conv2D + MaxPool (Multi-Op Pipeline)

A two-stage pipeline common in classification networks. The convolution output is an intermediate value that feeds into spatial down-sampling via max-pooling.

```text
device "npm_lite.cfg"

program conv2d_maxpool:

# --- Compile-time constants ---
const TiH = 16
const TiW = 16
const Cin = 64
const Cout = 128
const Kh = 3
const Kw = 3
const ToH = 14
const ToW = 14
const ToH_p = 7                              # pooled output height (ToH / 2)
const ToW_p = 7                              # pooled output width  (ToW / 2)
const T = 4

const tileX_bytes = TiH * TiW * Cin         # 16384
const tileW_bytes = Kh * Kw * Cin * Cout     # 294912
const tileC_bytes = ToH * ToW * Cout         # 25088 (conv output)
const tileY_bytes = ToH_p * ToW_p * Cout     # 6272  (pooled output)

buffer X_L2 : L2 (size=T * tileX_bytes, align=64)
buffer W_L2 : L2 (size=tileW_bytes, align=64)
buffer Y_L2 : L2 (size=T * tileY_bytes, align=64)

buffer X_L1 : L1 (size=2*tileX_bytes, align=64)
buffer W_L1 : L1 (size=tileW_bytes,   align=64)
buffer C_L1 : L1 (size=2*tileC_bytes, align=64)   # conv output / pool input
buffer Y_L1 : L1 (size=2*tileY_bytes, align=64)

loop i in [0..T-1] @max_in_flight(2):

  let X_tile_i = region(X_L2, i * tileX_bytes, tileX_bytes)
                 elem=i8, shape=[1, TiH, TiW, Cin], layout=NHWC

  let Y_tile_i = region(Y_L2, i * tileY_bytes, tileY_bytes)
                 elem=i8, shape=[1, ToH_p, ToW_p, Cout], layout=NHWC
                 @materialized

  let X_pp_i = region(X_L1, (i mod 2)*tileX_bytes, tileX_bytes)
               elem=i8, shape=[1, TiH, TiW, Cin], layout=NHWC

  # Intermediate: conv output, marked @materialized so the binder
  # keeps it as a real value boundary between conv2d and maxpool.
  let C_pp_i = region(C_L1, (i mod 2)*tileC_bytes, tileC_bytes)
               elem=i8, shape=[1, ToH, ToW, Cout], layout=NHWC
               @materialized

  let Y_pp_i = region(Y_L1, (i mod 2)*tileY_bytes, tileY_bytes)
               elem=i8, shape=[1, ToH_p, ToW_p, Cout], layout=NHWC
               @materialized

  let W_l1 = region(W_L1, 0, tileW_bytes)
             elem=i8, shape=[Kh, Kw, Cin, Cout], layout=HWIO

  tX = transfer.async(dst=X_pp_i, src=X_tile_i)
  tW = transfer.async(
         dst=W_l1,
         src=region(W_L2, 0, tileW_bytes)
             elem=i8, shape=[Kh, Kw, Cin, Cout], layout=HWIO
       )
  wait(tX, tW)

  tC = conv2d.async
         in  X_pp_i, W_l1
         out C_pp_i
         deps=[tX, tW]
         pads=[1,1,1,1]
         strides=[1,1]
         dilations=[1,1]
         groups=1
         accum_type=i32

  tP = maxpool.async
         in  C_pp_i
         out Y_pp_i @materialized
         deps=[tC]
         kernel_shape=[2,2]
         pads=[0,0,0,0]
         strides=[2,2]

  tS = store.async(dst=Y_tile_i, src=Y_pp_i, deps=[tP])

endloop
```

**What to notice:**
- **Two compute stages** chain through tokens: `tC` (conv2d) feeds `tP` (maxpool). The binder cannot reorder them because `tP` depends on `tC`.
- **`C_pp_i` is `@materialized`** — this prevents the binder from fusing conv2d and maxpool into a single opaque operation. The intermediate convolution result must exist as an architecturally visible value.
- **Three L1 buffer pools** (`X_L1`, `C_L1`, `Y_L1`) hold different stages of the pipeline. The conv output (`C_L1`) is distinct from the final pooled output (`Y_L1`) because maxpool changes spatial dimensions.
- Removing `@materialized` from `C_pp_i` would permit the binder to fuse the two stages — a deliberate optimization choice left to the programmer.

---

## Where NEM Fits

NEM occupies a precise niche in the compilation stack: above graph-level representations (ONNX) and compiler IRs (MLIR), and below hardware-bound control structures (TCBs). Each layer has a distinct zone of competence, and NEM fills the execution-level gap that the others intentionally leave open.

The following support matrix makes this positioning concrete. It covers 48 concepts spanning five domains — from graph/ML abstractions through execution semantics to microarchitectural detail — so that each model's intentional exclusions are as visible as its strengths.

**Legend:** ✓ = supported | ~ = partial or dialect/context-dependent | ✗ = not supported

| # | Domain | Concept | ONNX | MLIR | NEM | TCB |
|---|--------|---------|:----:|:----:|:---:|:---:|
| 1 | Purpose | Stability contract | ✓ | ✗ | ✓ | ✗ |
| 2 | Memory | Memory hierarchy awareness | ✗ | ~ | ✓ | ✓ |
| 3 | Memory | Buffer allocation | ✗ | ~ | ✓ | ✓ |
| 4 | Memory | Buffer lifetime/reuse | ✗ | ~ | ✓ | ~ |
| 5 | Memory | Region/view model | ✗ | ✓ | ✓ | ~ |
| 6 | Memory | Address space model | ✗ | ✓ | ✓ | ✓ |
| 7 | Data Movement | Explicit data transfers | ✗ | ~ | ✓ | ✓ |
| 8 | Data Movement | DMA modeling | ✗ | ✗ | ✓ | ✓ |
| 9 | Data Movement | Store semantics | ✗ | ✗ | ✓ | ✓ |
| 10 | Data Movement | Transfer/compute overlap | ✗ | ~ | ✓ | ~ |
| 11 | Compute | Operation representation | ✓ | ✓ | ✓ | ✓ |
| 12 | Compute | Opcode granularity | ✓ | ✓ | ✓ | ✓ |
| 13 | Type System | Static typing | ~ | ~ | ✓ | ✗ |
| 14 | Type System | Type legality per opcode | ✗ | ~ | ✓ | ✗ |
| 15 | Type System | Type conversion control | ✗ | ~ | ✓ | ✗ |
| 16 | Type System | Quantization modeling | ~ | ~ | ✓ | ~ |
| 17 | Tiling | Tiling model | ✗ | ~ | ✓ | ~ |
| 18 | Tiling | Tile-level readiness | ✗ | ~ | ✓ | ✓ |
| 19 | Concurrency | Synchronization model | ~ | ~ | ✓ | ✓ |
| 20 | Concurrency | Bounded pipelining | ✗ | ✗ | ✓ | ~ |
| 21 | Concurrency | Multi-engine parallelism | ✗ | ✗ | ✓ | ✓ |
| 22 | Concurrency | Intra-engine parallelism | ✗ | ✗ | ✓ | ✓ |
| 23 | Optimization | Fusion control | ✗ | ✗ | ✓ | ✗ |
| 24 | Optimization | Materialization semantics | ✗ | ~ | ✓ | ✗ |
| 25 | Optimization | Scheduling freedom | ✗ | ✓ | ✓ | ✗ |
| 26 | Hardware | Device topology description | ✗ | ✗ | ✓ | ~ |
| 27 | Hardware | Execution unit binding | ✗ | ✗ | ✓ | ✓ |
| 28 | Hardware | Microarchitecture isolation | ✗ | ✗ | ✓ | ✗ |
| 29 | Hardware | Hardware portability | ✓ | ✓ | ✓ | ✗ |
| 30 | Hardware | Late binding | ✗ | ✗ | ✓ | ✗ |
| 31 | Specification | Formal grammar | ✓ | ✓ | ✓ | ✓ |
| 32 | Specification | Hazard/aliasing rules | ✗ | ~ | ✓ | ✗ |
| | | | | | | |
| 33 | Graph / ML | Declarative dataflow graph | ✓ | ✓ | ✗ | ✗ |
| 34 | Graph / ML | Shape inference | ✓ | ✓ | ✗ | ✗ |
| 35 | Graph / ML | Dynamic / symbolic shapes | ✓ | ✓ | ✗ | ✗ |
| 36 | Graph / ML | Broad operator polymorphism | ✓ | ✓ | ✗ | ✗ |
| 37 | Graph / ML | Training / gradient support | ✓ | ✓ | ✗ | ✗ |
| 38 | Graph / ML | Control flow subgraphs | ✓ | ✓ | ✗ | ✗ |
| | | | | | | |
| 39 | Compiler IR | Progressive multi-level lowering | ✗ | ✓ | ✗ | ✗ |
| 40 | Compiler IR | Aggressive IR transformations | ✗ | ✓ | ✗ | ✗ |
| 41 | Compiler IR | Custom dialect / extension system | ~ | ✓ | ✗ | ✗ |
| | | | | | | |
| 42 | Microarchitecture | Physical address mapping | ✗ | ✗ | ✗ | ✓ |
| 43 | Microarchitecture | Bank / slice selection | ✗ | ✗ | ✗ | ✓ |
| 44 | Microarchitecture | DMA burst / stride configuration | ✗ | ✗ | ✗ | ✓ |
| 45 | Microarchitecture | Store format / writeback modes | ✗ | ✗ | ✗ | ✓ |
| 46 | Microarchitecture | HW arbitration and priority | ✗ | ✗ | ✗ | ✓ |
| 47 | Microarchitecture | Sub-unit targeting | ✗ | ✗ | ✗ | ✓ |
| 48 | Microarchitecture | Tag-based HW chaining | ✗ | ✗ | ✗ | ✓ |
| | | | | | | |
| | | **Totals (48)** | **11✓  4~  33✗** | **16✓  14~  18✗** | **32✓  16✗** | **21✓  7~  20✗** |

**Key observations:**

- **Every model has intentional exclusions.** NEM's 16 ✗ (graph abstractions, compiler IR, microarchitecture) define its architectural boundaries as precisely as its 32 ✓. No model attempts to cover the full stack.
- **Four distinct zones of competence** emerge:
  - **ONNX** dominates Graph / ML (6/6 ✓) but is absent from execution, hardware, and microarchitecture (33 ✗).
  - **MLIR** has the broadest reach (16✓) but the most partial coverage (14 ~), reflecting its "expressible but not guaranteed" nature — strong as a compiler tool, weak as a contract.
  - **NEM** covers all 32 execution-level concepts with zero partial entries, while intentionally excluding the 16 concepts above and below its scope.
  - **TCB** dominates Microarchitecture (7/7 ✓) and hardware-facing execution, but cannot express software-facing concerns like stability, portability, or optimization (20 ✗).
- **NEM occupies the only unclaimed niche.** The execution-level concepts (rows 1–32) that NEM fully covers are exactly those where ONNX shows ✗ and TCB shows either ✗ or ~. MLIR can partially express many of them (~) but commits to none.
- **The Optimization domain** (rows 23–25) uniquely distinguishes NEM: it is the only model where all three concepts (fusion control, materialization, scheduling freedom) are explicitly supported.

For detailed per-model analysis (NEM vs ONNX, NEM vs MLIR, NEM vs TCB), see the companion document [comparison_tables.md](comparison_tables.md).

---

## Engineering Value

NEM enables:

- **Performance portability** across NeuPro-M revisions — programs written to NEM survive changes in banking, store pipelines, and interconnect topology.
- **Multi-frontend reuse** — the same NEM binder serves compilers from MLIR, TVM, llama.cpp, and other frameworks.
- **Device-aware validation** — type families, device configurations (with `opcode.mandatory`/`opcode.extended` blocks and inheritance), allow compile-time rejection of programs that target unsupported type combinations or topologies.
- **Incremental migration** — operators can be progressively moved from VPU to NPM accelerator pipelines without rewriting the execution framework.
- **Validation and debugging** — NEM programs can be analyzed for hazards, buffer safety, and type legality before hardware binding.
- **Long-term maintainability** — microarchitectural churn is isolated in the binder; everything above NEM remains stable.

---

## Conclusion

NEM defines the architectural execution semantics required to program NeuPro-M effectively. By making execution explicit while deferring microarchitectural binding, it provides a stable foundation for performance, portability, and evolution across both software and hardware generations.

The model's key contributions are:

- A **region-centric data model** with typed, bounded views into explicitly managed memory.
- A **multi-engine, multi-unit abstract machine** that exposes hardware parallelism without encoding microarchitectural details.
- A **static type system with device-aware conformance** that enables compile-time validation.
- **Bounded pipelining** and **materialization semantics** that control overlap and fusion safely.
- A **clean attribute/decorator separation** that distinguishes execution-essential properties from binder hints.

The comparative analysis demonstrates that NEM fills a precise and necessary gap: it addresses the 13+ execution concerns that ONNX intentionally omits, provides NeuPro-M-specific semantics that MLIR's general-purpose infrastructure cannot guarantee, and abstracts away the microarchitectural fragility that makes TCBs unsuitable as a programming interface. No existing abstraction covers this combination of requirements.

The formal specification, formal language grammar, and complete worked examples are provided in the companion documents [nem_spec.md](nem_spec.md), [examples.md](examples.md) and [comparison_tables.md](comparison_tables.md).

---
