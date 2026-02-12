# NPM (Ceva NeuPro‑M / Ceva‑NPM) primer for building a `llama.cpp` accelerator backend

This document is written for engineers who are integrating a **Ceva NeuPro‑M / Ceva‑NPM (“NPM”)** hardware accelerator as a backend for `llama.cpp` (via `ggml` backends). It focuses on *what NPM is* and the *hardware/driver facts you need* to offload parts of transformer inference (primarily GEMM / MatMul, plus selected “streaming” post‑ops).

---

## 1) What “NPM” is (in this project context)

**NPM** refers to the **Ceva NeuPro‑M family of heterogeneous AI/ML processor engines**, renamed in the spec as **Ceva‑NPM4K / 8K / 16K / 32K / 64K** (multi‑engine scaling). In practice, you should think of NPM as:

- A **high‑throughput matrix/convolution compute engine** (NMU) backed by on‑chip SRAM (L1/L2) and DMA engines.
- A **streaming post‑processing pipeline** (CSTL) for elementwise ops, activations, pooling, residuals, normalization, softmax, etc.
- A **controller + sequencer** model that executes graphs/kernels by programming registers/queues and orchestrating DMA + compute.

For `llama.cpp`, the “sweet spot” is: **offload large MatMul / FullyConnected‑style ops** and fuse/chain some post‑ops where feasible (e.g., bias, activation, normalization) to reduce memory traffic.

---

## 2) Configurations and scale knobs you should care about

The product line is described by “K” sizes and number of engines. The spec lists the following product options:

- **Ceva‑NPM4K**: 1 engine, **16K INT4 MACs**, **4K INT8 MACs**, **1K INT16 MACs**, **2K FP16 MACs**
- **Ceva‑NPM8K**: 1 engine, **32K INT4**, **8K INT8**, **2K INT16**, **4K FP16**
- **Ceva‑NPM16K**: 2 engines, **64K INT4**, **16K INT8**, **4K INT16**, **8K FP16**
- **Ceva‑NPM32K**: 4 engines, **128K INT4**, **32K INT8**, **8K INT16**, **16K FP16**
- **Ceva‑NPM64K**: 8 engines, **256K INT4**, **64K INT8**, **16K INT16**, **32K FP16**

Key implication for a `llama.cpp` backend:
- You will likely want **one backend instance per engine** (or per device) and a scheduler that can split large GEMMs across engines if the software stack exposes a clean multi‑engine programming model.

---

## 3) Execution units (mental model)

NPM is a heterogeneous accelerator. The table below is the practical mapping you need:

### 3.1 NMU (Neural Multiplier Unit) — “the GEMM engine”
The **NMU** is responsible for:
- **Conv / deconv**
- **Matrix multiplication (MatMul)**
- **FullyConnected** (i.e., GEMM with typical NN layouts)

This is the unit you target for LLM heavy hitters:
- QKV projections
- attention output projection
- MLP up/down projections

### 3.2 CSTL (Complementary Streaming elementwise Logic) — “the post‑op pipeline”
The **CSTL** handles a lot of transformer “glue” without round‑tripping through a CPU:
- Elementwise add/mul/sub/div, etc.
- activations (e.g., GELU)
- **Softmax / MaskedSoftmax**
- **(RMS)Norm / LayerNorm** (supported operators list includes `LayerNorm` and `RmsNorm`)
- reshapes, transposes, concatenations (some via DMA/Controller)

In a backend, CSTL matters because you can sometimes **fuse**:
- `MatMul + bias + activation`
- `MatMul + residual add`
- (sometimes) `MatMul + normalization`

…which reduces bandwidth pressure on L1/L2 and the system memory interface.

### 3.3 VPU / Controller — “control + scalar/vector glue”
Some operators are listed as **VPU/Controller**, implying:
- Either they run on a programmable DSP/VPU block, or
- they are orchestrated with controller assistance.

For LLM inference, you should assume:
- **the core performance path is NMU + CSTL**, and
- VPU/Controller is for edge ops, control, and less throughput‑critical work (or when a fused pipeline isn’t available).

### 3.4 DMA engines — “the lifeline”
There are multiple DMA roles:
- **System DMA** for external memory (DDR) transfers.
- **L1 DMAs** for moving data/weights between L2 and L1.
- Optional **weight decompression** support (WDM is mentioned as optional in the feature list).

For `llama.cpp`, the DMA design dictates:
- how you do **tensor uploads** (weights, KV cache blocks, activations),
- how you overlap **transfer with compute**, and
- what minimum **tile sizes** are needed to keep NMU busy.

---

## 4) Memory hierarchy and why it dominates backend design

At a high level:
- **L1M**: low‑latency on‑chip SRAM local to an engine (the text describes 1MB in NPM4K and higher).
- **L2M**: shared SRAM across engines, configurable **~1MB to 32MB** (common to all engines in multi‑engine setups).
- **DDR / system memory**: accessed via system DMA/external AXI interface.

Backend implications:
1. **You can’t treat NPM like a GPU** with a giant flat VRAM. You’ll be **tiling** everything.
2. For transformer workloads, you want:
   - weights resident in L2 (if they fit) or streamed from DDR with overlap,
   - activations tiled through L1,
   - KV cache carefully placed (often DDR, sometimes partially staged in L2 depending on size).

---

## 5) Data types and quantization (what matters for `llama.cpp`)

The spec highlights:
- supported bit‑width pairs such as **4×4, 4×8, 4×16, 8×8, 8×16, 16×16, FP16×FP16**
- “dynamic quantization flow” and “dynamic quantization by channel/tensor per group of elements…”

Practical guidance for a `llama.cpp` backend:
- Start with **FP16 (or INT8) activations** + **INT8/INT4 weights** if the NPM software stack supports them efficiently.
- `llama.cpp` commonly uses **int4 weight formats** (e.g., Q4_0/Q4_K variants). You will likely need:
  - a **repacking step** into the layout NPM expects, and
  - either (a) device‑side dequant, or (b) use NPM’s mixed‑precision paths if supported in your runtime.
- If NPM supports **dynamic quantization** on‑the‑fly, consider mapping `ggml` quantization to NPM’s preferred grouping to avoid format thrash.

---

## 6) Operator coverage relevant to transformer inference

The NPM spec provides a supported operator list. The following entries are the most relevant to LLM inference:

- **MatMul** — *NMU/Controller*
- **FullyConnected** — *NMU*
- **Softmax / LogSoftmax / MaskedSoftmax** — *CSTL*
- **LayerNorm / RmsNorm** — *CSTL (and/or VPU/Controller for RMSNorm)*
- **Elementwise** ops: Add, Multiply, Subtract, Divide, Exp, Tanh, etc. — *CSTL/Controller (varies)*
- **Gelu / biasgelu** — *CSTL/Controller*
- **Reshape / Transpose / Split / Concat / Flatten** — *DMA/CSTL/Controller (varies)*

This is enough coverage to build a “mostly‑accelerated” transformer path where the CPU only coordinates, and most FLOPs are in NMU.

---

## 7) How this maps onto a `llama.cpp` backend (what the engineer should implement)

### 7.1 Where to plug in: `ggml` backends
`llama.cpp` uses `ggml` to represent computation graphs. Backends typically provide:
- tensor allocation / memory management hooks
- kernel dispatch for common ops (GEMM / matmul / elementwise)
- graph planning (topological order + fusion opportunities)

Your NPM backend should aim for:
- **MatMul / “FullyConnected”** offload first (highest ROI)
- Add **RMSNorm / LayerNorm** and **Softmax** next
- Add selected elementwise ops (residual add, mul, activation) to unlock fusions

### 7.2 Minimal viable backend (“matmul offload”)
A good MVP that proves feasibility:

1. **Device abstraction**
   - open device / map registers / init DMA
   - discover NPM config (NPM4K vs 8K, L2 size, engine count)
2. **Memory manager**
   - allocate pinned host buffers (if required by DMA)
   - manage L2 “weight cache” region for hot weights
   - manage L1 scratch for tiles
3. **MatMul kernel**
   - accept A (activations), B (weights), produce C (output)
   - implement tiling: `M×K` times `K×N` in chunks that fit L1
   - schedule DMA prefetch of next tiles while NMU computes current tile
4. **Integration with `ggml`**
   - implement `GGML_OP_MUL_MAT` mapping to NPM MatMul
   - fall back to CPU for unsupported shapes or edge cases

### 7.3 Next step: fuse post‑ops using CSTL
Once MatMul works, the next large wins come from reducing memory traffic:

- `MatMul + bias` (bias add)
- `MatMul + activation` (GELU / SiLU variants if available; `llama.cpp` commonly uses SiLU for some models, GELU for others)
- `MatMul + residual add`
- `RMSNorm` (most modern LLMs) or `LayerNorm` (some older ones)

A typical fused “block” in a transformer layer:
- QKV projection: `MatMul` (+ bias)  
- attention score path: `MatMul` → `MaskedSoftmax`  
- output projection: `MatMul` + residual add  
- MLP: `MatMul` → activation → `MatMul` + residual add  
- norms: RMSNorm/LayerNorm

If NPM’s runtime supports chaining NMU→CSTL without storing intermediate tensors back to system memory, you should leverage that aggressively.

---

## 8) Engineering checklist (what you must clarify from the NPM software stack)

The architecture spec tells you what blocks exist, but **integration depends on the software interface** you have (driver/runtime/compiler). To build a `llama.cpp` backend, the engineer needs answers to these:

### 8.1 Programming model / command submission
- Is there a **ring buffer / command queue**? Or is it pure MMIO register programming?
- Can you submit **asynchronous jobs** and get completion interrupts/fences?

### 8.2 Supported tensor layouts
- What are the required layouts for MatMul inputs (row/col major, blocked formats)?
- Are there “reshape on the fly” features you can invoke rather than repacking?

### 8.3 Quantized weight formats
- Can NMU consume **packed INT4** weights directly?
- If yes: what packing order (nibbles, interleave, block size)?
- If no: do you rely on device dequant to INT8/FP16, or host pre‑expand?

### 8.4 Multi‑engine scaling
- Does the runtime expose engines independently?
- Can you **split a single GEMM** across engines, or is it “one graph per engine”?

### 8.5 Synchronization with host
- How do fences work (polling register, interrupt FD, event object)?
- Are DMA buffers required to be physically contiguous / cache‑coherent?

---

## 9) Suggested vocabulary (so software and hardware teams align)

Use these terms consistently in code and docs:

- **Engine**: one NPM engine instance (may contain one or two NMUs depending on SKU).
- **NMU job**: a MatMul/Conv compute submission.
- **CSTL job**: a streaming post‑op submission or a fused pipeline stage.
- **Tile**: the chunk of a tensor moved through L1 for one compute step.
- **Weight cache**: region of L2 (or pinned DDR) holding frequently used weights.
- **DMA prefetch**: overlapping transfer of the next tile while current tile computes.

---

## 10) Appendix: the transformer ops you typically offload first

In order of ROI:

1. **GEMM / MatMul** (QKV, proj, MLP up/down)  
2. **RMSNorm / LayerNorm**  
3. **Softmax / MaskedSoftmax**  
4. Elementwise **residual add**, **mul**, **activation (GELU/SiLU)**  
5. Smaller shape ops (reshape/transpose) only if they unblock fusion and reduce copies

---

### Source
This document is based on: **“Ceva‑NeuPro‑M™ High‑Level Architecture Specification, Rev. 1.4.2.GA (June 2025)”**.
