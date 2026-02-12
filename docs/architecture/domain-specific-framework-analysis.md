# Domain-Specific Framework Analysis

**Work Item**: "Domain-specific framework" from `spec-int-work.md`
**Date**: 2026-02-12
**Status**: Complete

---

## Executive Summary

Evaluated 14 frameworks across two dimensions: language-level alternatives (could NEM be expressed within an existing IR?) and toolchain infrastructure (could NEM's tools leverage existing frameworks?).

**Language-level alternatives evaluated:**
- **MLIR custom dialect**: Closest infrastructure match, but fundamentally incompatible — MLIR does not provide the stability contract NEM requires. NEM is what MLIR lowers *to*, not what it *is*.
- **TOSA / StableHLO**: Stable operator sets, but operate at the graph/computation level — no memory hierarchy, no data movement, no scheduling. Wrong abstraction level.
- **Exo (exocompilation)**: Most conceptually similar — explicit memory hierarchy, user-schedulable. But Exo is a productivity compiler, not an architectural contract. No stability guarantees, no device type families.
- **Halide / TVM / Triton**: Scheduling DSLs and kernel languages. NEM is a *target* for these tools, not a replacement for them.

**Toolchain infrastructure evaluated:**
- **Parser generators (ANTLR, Lark, Tree-sitter)**: NEM's grammar is small (~120 productions) and LL(1)-friendly. Hand-written recursive descent provides better error messages, zero dependencies, and full control. Tree-sitter recommended separately for the VS Code extension.
- **Language workbenches (Langium, Xtext, Spoofax)**: All are Java or TypeScript — incompatible with NEM's Python toolchain decision. Validation complexity far exceeds what workbenches can auto-generate.
- **MLIR/xDSL as infrastructure**: C++ dependency (MLIR) or research instability (xDSL) conflicts with `nemlib`'s zero-dependency pure Python design.

**Recommendation**: Continue building NEM from scratch. No existing framework can serve as NEM's foundation. NEM occupies a unique niche (stable execution contract for a software-managed accelerator) that no existing framework was designed to fill. Two targeted opportunities identified:
1. Tree-sitter grammar for VS Code extension (incremental parsing, syntax highlighting)
2. MLIR Python bindings for the Compiler's input side (consuming MLIR, producing NEM)

---

## 1. Problem Statement

The NEM project currently defines a complete new language (grammar, type system, execution semantics) and plans to build its entire toolchain from scratch (lexer, parser, AST, validation, interpreter, compiler, binder, simulator). The question is whether existing domain-specific languages, IRs, or framework infrastructure could be leveraged instead.

This analysis evaluates two distinct dimensions:

- **A. Language-level alternatives**: Could NEM's semantics be expressed as a dialect, extension, or specialization of an existing IR/language rather than a standalone language?
- **B. Toolchain infrastructure**: Could the tools building NEM (parser, type checker, etc.) leverage existing frameworks to reduce implementation effort?

---

## 2. NEM's Defining Characteristics

Before evaluating alternatives, we must identify the properties that any replacement or augmentation must preserve. These are derived from the NEM spec and whitepaper:

| # | Property | Description |
|---|----------|-------------|
| 1 | **Stability contract** | NEM must be a versioned, backward-compatible architectural contract — not an evolving compiler IR |
| 2 | **Explicit 3-level memory hierarchy** | DDR / L2 / L1 with Engine-local scratchpads; no implicit caching |
| 3 | **Region-centric data model** | Typed bounded views into buffers, not tensors or memrefs |
| 4 | **Token-based async synchronization** | Tasks produce completion tokens; `wait` is the sole ordering primitive |
| 5 | **Bounded pipelining** | `@max_in_flight(N)` on loops — constrains concurrent iterations for safe buffer reuse |
| 6 | **Materialization semantics** | `@materialized` decorator controls fusion boundaries |
| 7 | **Device-aware type conformance** | MUST/MAY type families per device config, with inheritance |
| 8 | **Multi-engine, multi-unit abstract machine** | Engines with NMU/CSTL/DMA unit types; optional `@resource` binding |
| 9 | **Attribute/decorator separation** | Clean distinction between execution-essential properties and binder hints |
| 10 | **Self-contained formal grammar** | EBNF-defined, parseable independently of any compiler framework |
| 11 | **Late binding to hardware** | NEM is not fully bound — the binder maps to TCBs during lowering |
| 12 | **Python toolchain** | Decided: Python 3.10+ for shared library (`nemlib`) and initial tools |

---

## 3. Language-Level Alternatives

### 3.1 MLIR Custom Dialect

**What it is**: MLIR (Multi-Level IR Compiler Framework) allows defining custom "dialects" — sets of operations, types, and attributes — within a shared compiler infrastructure. NEM could be expressed as an MLIR dialect with custom ops for `transfer.async`, `conv2d.async`, `wait`, etc.

**What it provides**:
- Mature infrastructure: operation/type/attribute definitions, verifiers, rewrite patterns, pass management
- Existing relevant dialects: `memref` (memory views), `async` (tokens and await), `linalg` (tensor algebra), `affine` (loop nests), `gpu` (multi-device)
- Tooling: `mlir-opt` for testing, `mlir-translate` for emission, built-in serialization (MLIR bytecode)
- Large community, well-funded (Google, AMD, Intel, etc.)

**Why it does NOT fit NEM**:

| NEM Requirement | MLIR Alignment | Problem |
|-----------------|---------------|---------|
| Stability contract | **Incompatible** | MLIR dialects evolve with the framework. There is no versioned stability guarantee across MLIR releases. MLIR explicitly states it is "not designed to be a stable architectural execution contract" (whitepaper). |
| Self-contained grammar | **Incompatible** | NEM programs must be parseable by standalone tools (interpreter, binder) without linking the MLIR C++ framework. MLIR's generic syntax (`%0 = "dialect.op"(...)`) is not human-writable for NEM's use case. |
| Python toolchain | **Problematic** | MLIR is C++ with Python bindings. The bindings are incomplete and evolve rapidly. Building `nemlib` as a Python library that depends on `mlir-python-bindings` adds a massive C++ build dependency for what is currently a zero-dependency pure Python library. |
| Region-centric model | **Partial** | MLIR's `memref` is similar to NEM regions but lacks the buffer/region/tile three-layer model, materialization semantics, and the attribute/decorator distinction. |
| Device-aware type families | **Not provided** | MLIR has no built-in concept of device-dependent type legality with MUST/MAY conformance classes. This would be entirely custom. |

**The `accfg` dialect (ASPLOS '26)** models a `configure → launch → await` accelerator pattern and is implemented in xDSL (a Python MLIR testbed). While conceptually adjacent, `accfg` focuses on reducing configuration overhead between host and accelerator — a lower-level concern than NEM's execution model.

**Verdict**: MLIR is an excellent tool for *producing* NEM (i.e., an MLIR-to-NEM lowering pass), but NEM should not *be* an MLIR dialect. The stability contract requirement is fundamentally incompatible. NEM explicitly positions itself as the stable layer that MLIR lowers *to*.

---

### 3.2 TOSA (Tensor Operator Set Architecture)

**What it is**: Arm's TOSA defines a stable set of whole-tensor operations for neural network inference, with a formal specification. TOSA 1.0 was released in 2025.

**What it provides**:
- Stable, versioned operator set (similar stability goal to NEM)
- Operator-level type constraints
- Reference model for validation
- MLIR dialect (`tosa`) for compiler integration

**Why it does NOT fit NEM**:

| NEM Requirement | TOSA Alignment | Problem |
|-----------------|---------------|---------|
| Execution semantics | **Not provided** | TOSA defines *what* operations compute, not *how* they execute. No memory hierarchy, no data movement, no synchronization, no scheduling. |
| Memory hierarchy | **Not provided** | TOSA operates on abstract tensors, not regions within explicit memory levels. |
| Bounded pipelining | **Not provided** | No loop constructs, no `@max_in_flight`. |
| Data movement | **Not provided** | No `transfer.async`, no `store.async`, no DMA modeling. |

TOSA occupies the same layer as ONNX — it defines operator semantics for portability, not execution semantics for hardware programming. NEM's whitepaper support matrix shows this clearly: TOSA would score similarly to ONNX (strong on operators, absent on execution).

**Verdict**: TOSA is not an alternative to NEM. They operate at fundamentally different abstraction levels. TOSA could be an *input* to a compiler that produces NEM.

---

### 3.3 StableHLO / IREE

**What it is**: StableHLO is Google's stable ML computation opset (evolved from XLA HLO/MHLO). IREE is an MLIR-based end-to-end compiler and runtime targeting heterogeneous hardware.

**What it provides**:
- Backward/forward compatibility guarantees (similar stability goal to NEM)
- Serialization via MLIR bytecode with versioning
- IREE provides a full compilation pipeline from StableHLO to executable code for various targets

**Why it does NOT fit NEM**:

| NEM Requirement | StableHLO/IREE Alignment | Problem |
|-----------------|-------------------------|---------|
| Execution level | **Too high** | StableHLO operates at the computation graph level (like ONNX but for XLA). No memory hierarchy, no explicit data movement. |
| Hardware specificity | **Too generic** | IREE targets CPUs, GPUs, and generic accelerators. NEM's abstract machine (Engines, NMU/CSTL/DMA) is NeuPro-M-specific by design. |
| Python toolchain | **Problematic** | Both are C++ with MLIR infrastructure. Same build complexity issues as MLIR. |

StableHLO demonstrates that the *stability contract* concept works — it proves the model. But its abstraction level (graph computation) is far above NEM's (execution scheduling on explicit hardware).

**Verdict**: StableHLO validates NEM's design philosophy (stable contract between frameworks and compilers) but operates at a completely different level. Not a substitute.

---

### 3.4 Exo (Exocompilation)

**What it is**: A user-schedulable language from MIT for programming hardware accelerators. Users write algorithms and scheduling transformations; Exo generates optimized code. Exo 2 (ASPLOS 2025) adds user-defined scheduling operators.

**What it provides**:
- Explicit memory hierarchy with user-defined memory specifications (`@DRAM`, `@L1`, etc.)
- User-schedulable transformations (tiling, reordering, parallelism)
- Custom hardware instruction libraries
- Python-based (important for NEM's toolchain choice)

**Why it is the closest match but still does NOT fit NEM**:

| NEM Requirement | Exo Alignment | Problem |
|-----------------|--------------|---------|
| Memory hierarchy | **Strong** | Exo supports user-defined multi-level memories. Closest to NEM's DDR/L2/L1 model. |
| Scheduling control | **Strong** | Exo externalizes scheduling decisions to user code, similar to NEM's explicit task ordering. |
| Stability contract | **Not provided** | Exo is a compiler research tool, not a versioned architectural standard. The language evolves with the research. |
| Async token model | **Not provided** | Exo uses imperative scheduling, not token-based async completion semantics. |
| Device type families | **Not provided** | No concept of MUST/MAY conformance classes, device configs, or type family matching. |
| Region/buffer model | **Different** | Exo uses array windowing, not NEM's buffer → region → tile hierarchy. |
| Abstract machine | **Generic** | Exo is hardware-agnostic by design (externalizes hardware to libraries). NEM defines a specific abstract machine. |

Exo's philosophy ("externalize hardware-specific code generation to user-level code") is philosophically aligned with NEM's late-binding approach. However, NEM is an *execution contract* (like an ISA), while Exo is a *productivity tool* for writing optimized kernels. They serve different purposes.

**Verdict**: Exo is the most conceptually similar framework, but NEM's role as a stable architectural contract with a specific abstract machine makes Exo unsuitable as a replacement. Exo could potentially be used as a *frontend* that generates NEM programs, similar to how Halide programs can target different backends.

---

### 3.5 Halide / TVM

**What they are**: Halide separates algorithm from schedule for image/tensor processing. TVM extends this to deep learning with hardware-specific scheduling primitives (tensorization, memory scope management).

**Why they do NOT fit NEM**:

- Both are *schedule-based compilers* that generate optimized code. NEM is the *target* of such a compilation — it describes what the generated code should do, not how to generate it.
- Halide/TVM output could be NEM programs (i.e., NEM is a backend target). But NEM cannot be expressed *within* Halide/TVM's scheduling language because NEM defines execution semantics at a different level.
- Neither provides a stability contract.
- TVM's TIR is the closest sublanguage, but it evolves rapidly with TVM releases and does not model NEM's specific abstract machine.

**Verdict**: Halide and TVM are potential *producers* of NEM programs (via backend lowering). They are not alternatives to NEM itself.

---

### 3.6 Triton

**What it is**: Python-based DSL for writing GPU kernels using blocked algorithms.

**Why it does NOT fit NEM**: Triton is GPU-specific (CUDA/ROCm), assumes massively parallel threads and implicit hardware scheduling — the opposite of NEM's explicit, software-managed execution model. No relevant overlap.

**Verdict**: Not applicable.

---

### 3.7 Language-Level Summary

| Framework | Stability Contract | Memory Hierarchy | Async Tokens | Device Type Families | NEM Abstract Machine | Verdict |
|-----------|:-:|:-:|:-:|:-:|:-:|---------|
| MLIR dialect | No | Partial | Partial | No | No | Incompatible role |
| TOSA | Yes | No | No | No | No | Wrong level |
| StableHLO | Yes | No | No | No | No | Wrong level |
| Exo | No | Yes | No | No | No | Closest, but different role |
| Halide/TVM | No | Partial | No | No | No | NEM is their target |
| Triton | No | No | No | No | No | Not applicable |

**Conclusion**: No existing language or IR can serve as NEM's foundation. NEM occupies a unique niche (stable execution contract for a software-managed accelerator) that none of these frameworks were designed to fill. The whitepaper's positioning analysis is validated by this review: NEM is neither a graph IR (ONNX/TOSA/StableHLO), nor a compiler IR (MLIR/TVM TIR), nor a scheduling DSL (Halide/Exo/Triton). It is an architectural execution model — analogous to an ISA specification — and must be defined on its own terms.

---

## 4. Toolchain Infrastructure Alternatives

Even if NEM must be its own language, the *tooling* that implements it could leverage existing frameworks. The `nemlib` common infrastructure (described in `docs/architecture/common-infrastructure.md`) plans a hand-written Python toolchain. Could parts of it be replaced?

### 4.1 Parser Generators (ANTLR, Lark, Tree-sitter)

**Option A: ANTLR4 (Python target)**

| Aspect | Assessment |
|--------|------------|
| Grammar expressiveness | ANTLR's LL(*) handles NEM's grammar easily. NEM's EBNF maps directly to ANTLR notation. |
| Python support | ANTLR4 has a Python 3 target. |
| Error recovery | Built-in error recovery with sync tokens. |
| IDE support | ANTLR has VS Code extensions, grammar visualization. |
| Drawback | Adds a Java dependency for grammar compilation (ANTLR tool is Java). Generated Python code is verbose. Runtime dependency on `antlr4-python3-runtime`. Breaks `nemlib`'s zero-dependency policy. |
| Drawback | AST nodes are ANTLR's parse tree types, not custom frozen dataclasses. Requires a parse tree → AST transformation pass. |

**Option B: Lark (pure Python)**

| Aspect | Assessment |
|--------|------------|
| Grammar expressiveness | Earley/LALR parser. Handles NEM's grammar. |
| Python support | Pure Python, pip-installable. |
| Zero dependencies | Lark has zero external dependencies — compatible with `nemlib`'s policy. |
| Error recovery | Basic, less sophisticated than ANTLR or hand-written. |
| Drawback | Parse tree → AST transformer still needed. Less control over error messages and recovery compared to hand-written parser. |

**Option C: Tree-sitter**

| Aspect | Assessment |
|--------|------------|
| Incremental parsing | Excellent for IDE integration (VS Code extension). |
| Error recovery | Best-in-class — never stops on errors. |
| Drawback | Grammars are JavaScript, parsers are C. Python bindings exist but add a C extension dependency. Not suitable as the core `nemlib` parser. |
| Use case | Ideal for the VS Code extension (`tools/vscode_ext/`) as a **secondary** parser, not the canonical `nemlib` parser. |

**Option D: Hand-written recursive descent (current plan)**

| Aspect | Assessment |
|--------|------------|
| Grammar expressiveness | Full control. NEM's grammar is LL(1)-ish — ideal for recursive descent. |
| Error recovery | Fully customizable error messages with NEM-specific diagnostics. |
| Zero dependencies | Yes — pure Python. |
| Source locations | Trivial to attach precise `SourceLocation` to every AST node. |
| Drawback | More initial implementation effort. Must be tested thoroughly. |

**Recommendation**: **Keep hand-written recursive descent for `nemlib`** (Option D). The reasons:

1. NEM's grammar is small and stable (~120 EBNF productions). The implementation effort is bounded and one-time.
2. Error messages are a first-class concern — NEM validation diagnostics (type family mismatches, device validity errors, hazard violations) require domain-specific error reporting that parser generators cannot provide.
3. Zero external dependencies aligns with the `nemlib` design decision.
4. The parser is already designed in the common infrastructure architecture.
5. **However**, Tree-sitter (Option C) should be adopted for the VS Code extension to provide incremental parsing and syntax highlighting. This is a separate, additive investment — not a replacement.

---

### 4.2 Language Workbenches (Langium, Xtext, Spoofax)

**What they provide**: Full DSL development environments — grammar → parser → AST → type checker → IDE support (code completion, hover, go-to-definition) generated from a declarative specification.

| Framework | Language | IDE Integration | Status |
|-----------|----------|----------------|--------|
| **Langium** | TypeScript/JS | VS Code native | Active, growing |
| **Xtext** | Java/Eclipse | Eclipse, VS Code (via LSP) | Mature, declining |
| **Spoofax** | Java/Eclipse | Eclipse, some LSP | Academic, niche |

**Why they are attractive**: A language workbench could auto-generate much of `nemlib` — the parser, basic validation, and IDE integration — from NEM's EBNF grammar.

**Why they do NOT fit NEM**:

1. **Language mismatch**: Langium is TypeScript, Xtext/Spoofax are Java. NEM's toolchain is Python. Using a language workbench means either (a) rewriting the entire toolchain in TypeScript/Java, or (b) maintaining two parallel implementations (workbench-generated for IDE, hand-written Python for tools). Both are worse than the current plan.

2. **Validation complexity**: NEM's validation is not a standard type-checking problem. The 10-pass validation pipeline (name resolution → expression evaluation → buffer validation → region validation → type family matching → dependency validation → hazard checking → engine validation → decorator validation → loop validation) involves domain-specific logic (device-aware conformance, token dependency graphs, region aliasing analysis) that no language workbench can generate from a grammar.

3. **The VS Code extension already exists**: The project has a `tools/vscode_ext/` directory. If IDE support is needed, a Tree-sitter grammar + LSP server (in Python, using `pygls`) is more aligned with the existing architecture than adopting a full language workbench.

**Recommendation**: **Do not adopt a language workbench.** The investment/benefit ratio is poor given NEM's Python toolchain decision and the domain-specific nature of its validation.

---

### 4.3 MLIR as Infrastructure (not as the language)

**Concept**: Use MLIR's C++ infrastructure (operation definitions, verifiers, pass management, serialization) to implement `nemlib`'s functionality, even though NEM's surface syntax is its own language. Parse NEM source → convert to MLIR → use MLIR's infrastructure for validation and transformation.

**Why it does NOT fit**:

1. **Language mismatch** (again): MLIR is C++ with Python bindings. The bindings are generated, incomplete, and version-locked to MLIR releases. This would make `nemlib` dependent on the MLIR C++ build system — exactly the coupling the project wants to avoid.
2. **Impedance mismatch**: NEM's concepts (device type families, MUST/MAY conformance, materialization decorators, bounded pipelining) would need to be encoded as MLIR attributes and verified by custom C++ verifiers. The encoding overhead is substantial with no clear benefit over direct Python implementation.
3. **MLIR is overkill**: `nemlib` doesn't need progressive lowering, rewrite patterns, or pass pipelines. It needs parsing, validation, and a data model. These are straightforward in Python.

**Where MLIR IS relevant**: The **Compiler** tool (which lowers MLIR to NEM) should use MLIR infrastructure on its *input side*. The compiler's job is to consume MLIR and produce NEM — it should use MLIR's Python bindings to read MLIR input, then use `nemlib` to emit valid NEM. This is the natural integration point, not replacing `nemlib` with MLIR.

**Recommendation**: **Do not use MLIR as infrastructure for `nemlib`.** Use MLIR where it belongs: as the input format consumed by the NEM compiler.

---

### 4.4 xDSL (Python MLIR Framework)

**What it is**: xDSL is a Python-native framework for defining MLIR-style dialects, operations, and passes. It reimplements MLIR's core abstractions in pure Python, avoiding the C++ dependency.

**Why it is interesting**: xDSL solves the "MLIR is C++" problem. NEM could theoretically be defined as an xDSL dialect with Python-native infrastructure.

**Why it still does NOT fit**:

1. **Stability**: xDSL is a research tool (University of Edinburgh, initially ETH Zurich). It evolves rapidly and provides no stability guarantees.
2. **Abstraction mismatch**: xDSL uses MLIR's conceptual model (operations in regions in blocks). NEM's conceptual model (buffers → regions → tiles, tasks producing tokens) doesn't map cleanly.
3. **Dependency risk**: Adopting xDSL couples `nemlib` to an external research project's evolution. `nemlib` is intentionally zero-dependency.

**Recommendation**: **Do not adopt xDSL.** Monitor it as a potential tool for the Compiler's MLIR input handling.

---

### 4.5 Toolchain Infrastructure Summary

| Framework | Fits Python? | Zero-dep? | Handles NEM Validation? | Recommendation |
|-----------|:-:|:-:|:-:|---------|
| ANTLR4 | Partial | No | No | Skip |
| Lark | Yes | Yes | No | Viable but marginal benefit |
| Tree-sitter | Via bindings | No | No | **Use for VS Code extension only** |
| Hand-written parser | Yes | Yes | Yes | **Keep (current plan)** |
| Langium/Xtext | No (JS/Java) | N/A | No | Skip |
| MLIR infra | No (C++) | No | No | Use for Compiler input side only |
| xDSL | Yes | No | No | Monitor, don't adopt |

---

## 5. Overall Recommendation

### 5.1 Continue Building NEM from Scratch

The analysis confirms that NEM should remain a standalone language with a custom-built toolchain. The reasons are structural, not incidental:

1. **NEM fills a unique niche.** It is an architectural execution contract — closer to an ISA specification than to a compiler IR or DSL. No existing framework was designed for this role.

2. **The stability requirement is disqualifying for most frameworks.** MLIR, TVM, Exo, and Halide are all evolving compiler tools. NEM must be a stable contract that survives hardware revisions. This is a fundamental incompatibility, not a missing feature that could be added.

3. **The toolchain is appropriately scoped.** The `nemlib` common infrastructure defines a focused, layered Python library. NEM's grammar is small (~120 productions), the type system is enumerable (finite set of type families), and the validation pipeline is domain-specific. This is not a "build everything from scratch" situation — it's a well-scoped implementation of a well-defined spec.

4. **External frameworks would add dependency risk without proportional benefit.** The main cost of NEM's approach is the parser and validation implementation. These are bounded, one-time efforts. The main cost of adopting a framework would be ongoing version tracking, impedance mismatch management, and loss of control over error reporting — recurring costs that compound over time.

### 5.2 Targeted Opportunities

While the core language and toolchain should remain custom, two targeted opportunities exist:

| Opportunity | What | Where | Effort | Benefit |
|-------------|------|-------|--------|---------|
| **Tree-sitter grammar** | Write a Tree-sitter grammar for NEM | `tools/vscode_ext/` | Low–Medium | Incremental parsing, syntax highlighting, code folding in VS Code |
| **MLIR integration in Compiler** | Use MLIR Python bindings to read MLIR input | `tools/compiler/` | Medium | Natural input format for the compiler; leverages MLIR's existing frontend ecosystem |

Neither of these replaces `nemlib` or changes the core architecture. They are additive integrations at the boundaries of the system.

### 5.3 Vindication of the Whitepaper's Positioning

The whitepaper's comparative analysis (Section "Where NEM Fits") correctly identified NEM's unique position. This framework review confirms it from the tooling perspective: the frameworks that are stable (TOSA, StableHLO) operate at the wrong level; the frameworks that operate at the right level (MLIR, Exo, TVM) are not stable; and no framework combines execution-level semantics with a stability contract. NEM must provide both.

---

## 6. Appendix: Framework Reference

| Framework | Origin | Language | License | Key URL |
|-----------|--------|----------|---------|---------|
| MLIR | Google / LLVM | C++ | Apache 2.0 | https://mlir.llvm.org |
| TOSA | Arm | Spec + C++ ref model | Apache 2.0 | https://www.mlplatform.org/tosa/ |
| StableHLO | Google / OpenXLA | C++ (MLIR) | Apache 2.0 | https://openxla.org/stablehlo |
| IREE | Google | C++ (MLIR) | Apache 2.0 | https://iree.dev |
| Exo | MIT / UC Berkeley | Python | MIT | https://exo-lang.dev |
| Halide | MIT / Adobe / Google | C++ | MIT | https://halide-lang.org |
| TVM | Apache | Python/C++ | Apache 2.0 | https://tvm.apache.org |
| Triton | OpenAI | Python/C++ | MIT | https://triton-lang.org |
| xDSL | Edinburgh / ETH | Python | Apache 2.0 | https://xdsl.dev |
| ANTLR4 | Parr | Java + targets | BSD | https://www.antlr.org |
| Lark | — | Python | MIT | https://github.com/lark-parser/lark |
| Tree-sitter | GitHub | Rust/C | MIT | https://tree-sitter.github.io |
| Langium | TypeFox | TypeScript | MIT | https://langium.org |
| `accfg` dialect | TU Delft / Edinburgh | Python (xDSL) | Apache 2.0 | https://github.com/KULeuven-MICAS/snax-mlir |
