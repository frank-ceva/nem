### NEM vs ONNX: Detailed Analysis

ONNX and NEM operate at fundamentally different levels of the compilation stack and are complementary rather than competing. ONNX expresses *what* to compute; NEM expresses *how* to execute it on NeuPro-M. The comparison highlights exactly which execution concerns NEM must address that ONNX intentionally omits.

| # | Concept | ONNX | NEM | Gap Significance |
|---|---------|------|-----|------------------|
| 1 | Stability contract | Versioned schema with backward compatibility | Versioned spec decoupled from silicon revision | Both stable, but ONNX stability covers math semantics while NEM covers execution semantics |
| 2 | Memory hierarchy | Flat — no concept of DDR/L2/L1 | Explicit 3-level hierarchy | **Critical gap.** NeuPro-M correctness depends on memory level awareness. ONNX cannot express where data resides or how it moves. |
| 3 | Buffer allocation | Implicit — framework runtime manages | Explicit — level, size, alignment declared | **Critical gap.** Without explicit allocation, buffer reuse and capacity analysis are impossible. |
| 4 | Buffer lifetime/reuse | Not expressible — tensors are immutable values | Explicit — bounded pipelining enforces safe reuse | **Critical gap.** Ping-pong and ring buffering require explicit lifetime reasoning that ONNX cannot represent. |
| 5 | Region/view model | Tensors are whole, immutable values | Regions are typed views with offset/extent into mutable buffers | **Critical gap.** NeuPro-M operates on tiles (sub-views); ONNX has no concept of partial tensor availability. |
| 6 | Address space | Not applicable | Logical opaque handles | NEM adds addressability without exposing physical layout |
| 7 | Explicit data transfers | No — data flow is implicit between operators | Yes — transfer.async/sync as first-class tasks | **Critical gap.** DMA scheduling is central to NeuPro-M performance. |
| 8 | DMA modeling | No | First-class DMA tasks with tokens | **Critical gap.** |
| 9 | Store semantics | No — outputs appear when operators complete | Distinct store.async/sync commitment step | **Critical gap.** Writeback control is required for multi-level memory correctness. |
| 10 | Transfer/compute overlap | Not expressible | Explicit via tokens + @max_in_flight | **Critical gap.** Overlap is the primary source of utilization on NeuPro-M. |
| 11 | Operation representation | Named operators (string-based, e.g. "Conv") | Dedicated opcodes with fixed signatures (conv2d.async) | NEM opcodes are statically verifiable; ONNX operators are dynamically dispatched |
| 12 | Opcode granularity | Single operators | Single operators (with fusion control via decorators) | Similar granularity, but NEM adds execution semantics |
| 13 | Static typing | Shape inference (may fail at runtime) | Fully static, mandatory before execution | NEM catches type errors at compile time |
| 14 | Type legality per opcode | Minimal — operators accept broad type ranges | Type families with MUST/MAY conformance per device | NEM enables compile-time rejection of unsupported type combinations |
| 15 | Implicit conversions | Some operators auto-cast inputs | Never — explicit cast/quantize required | NEM's strictness prevents silent precision loss |
| 16 | Quantization | Separate QuantizeLinear/DequantizeLinear ops | Region-level quant attribute + typed quantize/dequantize ops | NEM integrates quantization into the type system rather than treating it as a separate operator layer |
| 17 | Tiling model | Not expressible | First-class loops with bounded pipelining | **Critical gap.** Tiling is unavoidable on NeuPro-M and must be explicitly represented. |
| 18 | Tile-level readiness | No — tensors are available atomically | Yes — completion tokens per task | **Critical gap.** Pipelined execution requires partial readiness signaling. |
| 19 | Synchronization | Implicit dataflow (SSA-style) | Explicit tokens (sole primitive) | NEM provides fine-grained, explicit control over ordering |
| 20 | Bounded pipelining | Not applicable | @max_in_flight(N) on loops | Not applicable at ONNX level |
| 21 | Multi-engine | Not applicable | Engine-indexed L1, concurrent execution | Not applicable at ONNX level |
| 22 | Intra-engine parallelism | Not applicable | @resource binding to unit instances | Not applicable at ONNX level |
| 23 | Fusion control | Not expressible — compiler/runtime decides | @materialized decorator gives explicit control | **Significant gap.** Fusion decisions affect correctness on NeuPro-M (buffer sizing, store ordering). |
| 24 | Materialization | All tensor outputs are materialized | Explicit control per region | NEM allows selective materialization for performance |
| 25 | Scheduling freedom | Not applicable (no scheduling concept) | Bounded by deps + decorators; binder fills the rest | NEM gives compilers structured latitude |
| 26 | Device topology | Not applicable | Device configuration with engine/unit counts | Not applicable at ONNX level |
| 27 | Execution unit binding | Not applicable | Optional @resource decorator | Not applicable at ONNX level |
| 28 | Microarch isolation | N/A (too abstract for any HW details) | Strict exclusion of microarch details | Both avoid microarch; NEM does so deliberately at the execution level |
| 29 | Hardware portability | Fully device-agnostic | Portable across NPM revisions | Different kinds of portability; NEM is NPM-family-portable |
| 30 | Late binding | N/A | Yes — binder produces TCBs from NEM | NEM's key architectural contribution |
| 31 | Formal grammar | Protobuf schema (operator schema) | Full EBNF grammar | Both formally specified |
| 32 | Hazard/aliasing rules | N/A (SSA — no aliasing) | Normative rules for overlap, reuse, bounds | NEM must address hazards because it uses mutable buffers |

**Summary:** ONNX and NEM are complementary. ONNX's deliberate omission of 13 concepts marked as "critical gap" above makes it unsuitable as an execution-level interface for NeuPro-M. These gaps — memory hierarchy, data movement, tiling, synchronization, buffer reuse — are precisely what NEM was designed to fill. ONNX remains the appropriate input representation; NEM is the appropriate execution representation.

---

### NEM vs MLIR: Detailed Analysis

MLIR is the closest existing technology to NEM in terms of capability. Several MLIR dialects (affine, async, memref) can express concepts that NEM also expresses. The key distinction is one of **role**: MLIR is a compiler infrastructure for building transformations; NEM is an architectural contract for programming a specific class of hardware. The comparison identifies where MLIR's generality creates gaps that NEM fills with NeuPro-M-specific semantics.

| # | Concept | MLIR | NEM | Gap Significance |
|---|---------|------|-----|------------------|
| 1 | Stability contract | No stability obligation — IRs evolve rapidly | Versioned, backward-compatible spec | **Critical gap.** MLIR dialects change freely; NEM must survive hardware generations |
| 2 | Memory hierarchy | memref address spaces (abstract, user-defined) | Explicit 3-level (DDR/L2/L1) with architectural semantics | **Significant gap.** MLIR can model memory levels but assigns no NeuPro-M-specific meaning. NEM gives DDR/L2/L1 architectural status with defined access rules. |
| 3 | Buffer allocation | memref.alloc with layout maps | Explicit buffer declaration (level, size, align) | NEM's buffers carry memory-level identity; MLIR memrefs require lowering passes to assign hardware meaning |
| 4 | Buffer lifetime/reuse | Analyzable via dominance and liveness | Explicit via bounded pipelining (@max_in_flight) | NEM makes reuse explicit and verifiable; MLIR requires analysis passes to infer it |
| 5 | Region/view model | memref with affine layout maps | Typed region views (offset, extent, elem, shape) | Similar capability; NEM's regions are purpose-built for NeuPro-M's tile-based access |
| 6 | Address space | Abstract (integer-tagged, user-defined) | Opaque logical handles | Both abstract; NEM handles carry explicit memory-level semantics |
| 7 | Explicit data transfers | Expressible (e.g., memref.copy, async dialect) | First-class transfer.async/sync tasks | MLIR can express transfers but they are not architecturally distinguished. NEM's transfers are first-class with token-based completion. |
| 8 | DMA modeling | Not first-class (implementable via custom ops) | First-class DMA tasks | **Significant gap.** NEM treats DMA as an architectural primitive; MLIR requires custom lowering |
| 9 | Store semantics | No built-in concept | store.async/sync as distinct task type | **Critical gap.** NeuPro-M's store-back step (L1 → L2) is architecturally distinct from compute. MLIR has no built-in representation for this. |
| 10 | Transfer/compute overlap | Expressible (async tokens, groups) | Explicit (tokens + @max_in_flight bound) | MLIR's async dialect can express overlap but provides no built-in bound on concurrency |
| 11 | Operation representation | Operations defined per dialect | Dedicated opcodes with fixed signatures | NEM's opcodes are NeuPro-M-specific and statically verifiable; MLIR ops are general-purpose |
| 12 | Opcode granularity | Any (single ops to fused subgraphs) | Single operators with fusion via decorators | NEM separates the question "what to compute" from "what to fuse" |
| 13 | Static typing | Verifier-based (per dialect) | Fully static, mandatory | Both support static typing; NEM makes it non-optional |
| 14 | Type legality per opcode | Dialect verifier rules (general) | Type families with MUST/MAY conformance classes | **Significant gap.** NEM's type families model device-dependent legality; MLIR verifiers are dialect-level, not device-level |
| 15 | Implicit conversions | Dialect-dependent | Never allowed | NEM is stricter by design |
| 16 | Quantization | Dialect-dependent (e.g., quant dialect) | Region-level quant attribute integrated into type system | NEM integrates quantization at the region level; MLIR's quant dialect is a separate layer |
| 17 | Tiling model | Affine maps, scf.for, tiling transformations | First-class loops with @max_in_flight | Both can express tiling; NEM's loops carry pipelining semantics by design |
| 18 | Tile-level readiness | Expressible (async tokens) | Yes (completion tokens per task) | Similar capability |
| 19 | Synchronization | Multiple models (async tokens, barriers, etc.) | Single model (tokens only) | NEM's simplicity is deliberate — one mechanism, no ambiguity |
| 20 | Bounded pipelining | Not a built-in concept (implementable) | @max_in_flight(N) as first-class decorator | **Critical gap.** NEM makes bounded pipelining an architectural guarantee; MLIR would need custom passes to enforce it |
| 21 | Multi-engine | Not built-in (implementable via custom dialect) | Engine-indexed L1, architectural concept | **Significant gap.** NEM's Engine model is purpose-built for NeuPro-M; MLIR requires custom work |
| 22 | Intra-engine parallelism | Not built-in | @resource(unit[idx]) binding | **Significant gap.** NEM can exploit multi-CSTL configurations directly |
| 23 | Fusion control | Compiler pass-based (no programmer control) | @materialized decorator (explicit programmer control) | **Significant gap.** In MLIR, fusion is a compiler decision; in NEM, the programmer can assert materialization boundaries |
| 24 | Materialization | Dialect-dependent | Explicit @materialized decorator | NEM's materialization is a first-class concept with architectural guarantees |
| 25 | Scheduling freedom | Full — compiler decides everything | Bounded — deps + decorators constrain, binder fills the rest | NEM gives the compiler structured latitude rather than unlimited freedom |
| 26 | Device topology | Not built-in (custom attribute possible) | Device configuration as part of the language | **Significant gap.** NEM programs can declare and validate against a target device topology |
| 27 | Execution unit binding | Not built-in | Optional @resource decorator with validation rules | **Significant gap.** NEM provides portable resource binding with graceful degradation |
| 28 | Microarch isolation | N/A (general-purpose, no specific HW) | Strict, deliberate exclusion of microarch details | NEM draws an explicit line; MLIR doesn't address this because it's not HW-specific |
| 29 | Hardware portability | Fully target-agnostic | Portable across NPM architecture revisions | Different kinds: MLIR is target-agnostic; NEM is NPM-family-portable |
| 30 | Late binding | N/A (compiles to target code) | Yes — NEM programs rebound to TCBs per silicon | NEM's defining architectural contribution |
| 31 | Formal grammar | EBNF per dialect | Full EBNF grammar for the complete language | Both formally defined; NEM's is self-contained |
| 32 | Hazard/aliasing rules | Dialect-dependent (affine has some) | Normative rules for overlap, reuse, bounds | NEM provides a single, complete hazard model; MLIR's is fragmented across dialects |

**Summary:** MLIR is the best available infrastructure for *producing* NEM programs — it should sit above NEM in the compilation stack. However, MLIR cannot *be* NEM because it lacks: (a) stability guarantees, (b) NeuPro-M-specific memory and execution semantics as built-in architectural concepts, (c) device-aware type conformance, (d) bounded pipelining as a first-class concept, and (e) the explicit role of serving as a long-term contract between compilers and hardware. The relationship is: MLIR is the compiler technology; NEM is the architectural specification that MLIR lowers to.

---

### NEM vs TCB: Detailed Analysis

TCBs are the hardware-consumable endpoint — they encode exactly how execution proceeds on a specific NeuPro-M silicon revision. NEM sits directly above TCBs and provides the abstraction that makes TCB generation portable and maintainable. The comparison highlights what NEM intentionally excludes (microarchitectural detail) and what it provides that TCBs lack (abstraction, portability, validation).

| # | Concept | TCB | NEM | Gap Significance |
|---|---------|-----|-----|------------------|
| 1 | Stability contract | Tied to silicon revision — changes with HW | Versioned, hardware-decoupled | **Critical gap.** TCBs break across revisions; NEM programs survive them |
| 2 | Memory hierarchy | Physical addresses + bank/slice selection | Explicit 3-level with opaque handles | Both are hierarchy-aware; NEM abstracts away physical mapping |
| 3 | Buffer allocation | Physical allocation by toolchain | Logical (level, size, alignment) | NEM defers physical placement to the binder |
| 4 | Buffer lifetime/reuse | Implicit in address reuse patterns | Explicit via @max_in_flight | NEM makes reuse analyzable; TCBs rely on the programmer getting addresses right |
| 5 | Region/view model | Raw byte ranges + register field encoding | Typed regions with offset/extent/elem/shape | **Significant gap.** NEM regions carry semantic information; TCBs carry only physical parameters |
| 6 | Address space | Physical addresses | Opaque logical handles | NEM's key abstraction — programs don't depend on physical layout |
| 7 | Explicit data transfers | DMA descriptors (channel, burst, address) | transfer.async/sync (logical src/dst) | Both explicit; NEM omits channel/burst configuration |
| 8 | DMA modeling | Channel-level configuration (burst shape, stride) | First-class tasks (logical) | Both model DMA; TCBs include microarch parameters NEM excludes |
| 9 | Store semantics | Store format registers, sub-unit selection | store.async/sync (logical commitment) | Both have store semantics; TCBs encode HW-specific format modes |
| 10 | Transfer/compute overlap | Implicit in HW pipeline + tag arbitration | Explicit (tokens + @max_in_flight) | NEM makes overlap intent explicit; TCBs rely on tag timing |
| 11 | Operation representation | Register configurations (TCB headers, fields) | Dedicated opcodes with typed operands | **Critical gap.** NEM is human-readable and compiler-friendly; TCBs are binary configurations |
| 12 | Opcode granularity | Micro-operations (individual TCB actions) | Single operators | NEM is higher-level; one NEM op may expand to multiple TCBs |
| 13 | Static typing | N/A — raw register values | Fully static, mandatory | **Critical gap.** NEM catches type errors before reaching hardware |
| 14 | Type legality per opcode | Implicit in HW behavior (wrong config = wrong result) | Type families with conformance classes | **Critical gap.** NEM validates legality at compile time; TCBs fail silently at runtime |
| 15 | Implicit conversions | N/A | Never allowed | NEM prevents silent precision errors |
| 16 | Quantization | Implicit in data format and store path config | Explicit quant attribute on regions | NEM makes quantization parameters visible and verifiable |
| 17 | Tiling model | Embedded in TCB chaining and iteration | First-class loops with decorators | NEM's tiling is structured; TCB chaining is flat |
| 18 | Tile-level readiness | Tag-based synchronization (HW mechanism) | Completion tokens (architectural concept) | NEM tokens abstract over HW tag implementation |
| 19 | Synchronization | Tag matching + HW arbitration | Explicit tokens (sole primitive) | NEM simplifies synchronization to a single mechanism |
| 20 | Bounded pipelining | Implicit in buffer count and tag setup | @max_in_flight(N) — explicit, analyzable | **Significant gap.** NEM bounds are declared and verified; TCB pipelining depth is implicit in the tag/buffer setup |
| 21 | Multi-engine | Engine-specific TCB streams | Engine-indexed L1, architectural concept | Both support multi-engine; NEM's model is hardware-agnostic |
| 22 | Intra-engine parallelism | Explicit sub-unit targeting (CSTLA/CSTLB) | @resource(unit[idx]) — unit-type level | NEM abstracts CSTLA/CSTLB split; TCBs target sub-units directly |
| 23 | Fusion control | N/A (already fully expanded) | @materialized decorator | Not applicable — TCBs are the output of fusion decisions made at NEM level |
| 24 | Materialization | All values materialized (no fusion possible) | Selective (@materialized or fusible) | NEM provides optimization latitude that TCBs cannot |
| 25 | Scheduling freedom | None — fully determined | Bounded — deps constrain, binder completes | NEM gives the binder freedom; TCBs are the binder's output |
| 26 | Device topology | Implicit (toolchain has HW knowledge) | Explicit device configuration | NEM makes topology declarative and portable |
| 27 | Execution unit binding | Explicit per-TCB (to specific sub-unit) | Optional @resource (graceful degradation) | NEM's binding is portable — it degrades gracefully on smaller devices |
| 28 | Microarch isolation | No — *is* the microarchitecture interface | Yes — strict exclusion | **Defining gap.** This is the fundamental reason NEM exists |
| 29 | Hardware portability | No — revision-specific | Yes — across NPM revisions | **Critical gap.** TCBs must be regenerated per silicon; NEM programs are reusable |
| 30 | Late binding | N/A (already fully bound) | Yes — NEM → TCB via binder | NEM enables late binding; TCBs are the bound result |
| 31 | Formal grammar | Register-level encoding specification | Full EBNF grammar | Different kinds of formalization; both are precise |
| 32 | Hazard/aliasing rules | Programmer responsibility (HW may not check) | Normative rules with defined UB | **Significant gap.** NEM provides a safety model; TCBs offer no safety net |

**Summary:** NEM and TCBs are in a producer-consumer relationship: NEM programs are the input to a binder that produces TCBs. NEM provides what TCBs cannot: portability across silicon revisions, compile-time type and safety validation, human-readable representation, multi-frontend support, and structured abstraction of microarchitectural details. TCBs provide what NEM intentionally omits: physical addresses, bank selection, burst configuration, arbitration hints, and sub-unit targeting. Together, they form a clean architectural stack where the binder translates architectural intent (NEM) into hardware reality (TCBs).

---
