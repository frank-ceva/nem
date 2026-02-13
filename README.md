# NEM: NeuPro-M Execution Model

NEM is an **execution-level architectural contract** for NeuPro-M neural network accelerators. It sits between high-level graph representations (ONNX, MLIR) and hardware-bound Task Control Buffers (TCBs), defining how computation, data movement, synchronization, and memory reuse are scheduled across NeuPro-M's software-managed memory hierarchy (DDR, L2, L1).

NEM provides:

- A **stable HW/SW contract** that isolates the software stack from microarchitectural changes
- **Explicit control** over tiling, DMA transfers, buffer allocation, and bounded pipelining
- A **formal specification** of device capabilities, conformance classes, and type legality
- A **simulatable model** for validating functional correctness before TCB lowering

## Repository Structure

```
nem/
├── spec/                        # Language specification (normative)
│   ├── nem_spec.md              # Formal architecture and language spec
│   ├── nem_whitepaper.md        # Architectural whitepaper with motivation and examples
│   ├── examples.md              # Annotated NEM program and device config examples
│   ├── comparison_tables.md     # Comparison with ONNX, MLIR, TVM, Triton, etc.
│   └── CHANGELOG.md             # Spec change log
│
├── examples/                    # Standalone NEM programs and device configs
│   ├── conv2d_relu.nem          # Conv2D + ReLU tiled pipeline (i8)
│   ├── gemm_bias_relu.nem       # GEMM + Bias + ReLU fully-connected layer (f16)
│   ├── conv2d_maxpool.nem       # Conv2D + MaxPool two-stage pipeline (i8)
│   ├── npm_baseline_1.0.nem     # Standard baseline device (all MUST-class variants)
│   └── npm_lite_.nem            # Example derived device configuration
│
├── tools/                       # Toolchain implementations
│   ├── interpreter/             # Reference interpreter (Python) — executes NEM programs
│   ├── compiler/                # Compiler — lowers MLIR to NEM
│   ├── binder/                  # Binder — lowers NEM to TCBs
│   ├── simulator/               # Simulator — executes encoded programs
│   └── vscode_ext/              # VS Code extension (syntax highlighting, examples)
│
├── tests/
│   └── conformance/             # Conformance tests (pytest) — shared truth for all tools
│
├── docs/
│   ├── engineering/             # Development process and practices
│   ├── architecture/            # System architecture and design analysis
│   ├── contracts/               # Shared interface definitions between tools
│   ├── workflow/                # Templates (contract change proposals, etc.)
│   └── ext/                     # External reference documentation
│
├── libs/                        # Shared libraries (integration-owned)
├── infra/                       # Build and CI infrastructure
├── spec-int-work.md             # Active work items (spec and integration)
└── work_history.md              # Completed work items
```

## Specification

The normative spec ([spec/nem_spec.md](spec/nem_spec.md)) defines everything needed to write NEM programs, build a compiler targeting NEM, and lower NEM to hardware. Key topics include:

- **Abstract Machine Model** — memory hierarchy (DDR/L2/L1), engines, execution units (NMU, CSTL, DMA)
- **Core Program Objects** — buffers, regions, tiles, tasks, tokens
- **Type System** — element types (i4..f32), shapes, layouts, quantization, bitwidth
- **Task Taxonomy** — transfer, store, compute, wait operations with async tokens
- **Loops and Bounded Pipelining** — `@max_in_flight` for overlapped execution
- **Constant Declarations** — compile-time named integer constants
- **Device Configuration** — type families, conformance classes (MUST/MAY), device inheritance
- **EBNF Grammar** — complete formal language definition

The whitepaper ([spec/nem_whitepaper.md](spec/nem_whitepaper.md)) provides architectural motivation and annotated examples.

## Toolchain

| Tool | Purpose | Status |
|------|---------|--------|
| **Interpreter** | Reference execution of NEM programs; validates functional correctness and language rules | Architecture spec written |
| **Compiler** | Lowers MLIR (or equivalent IR) to NEM programs | Scaffolded |
| **Binder** | Lowers NEM programs to NeuPro-M Task Control Buffers (TCBs) | Scaffolded |
| **Simulator** | Executes encoded programs; validates architecture correctness across microarchitecture variants | Scaffolded |
| **VS Code Extension** | Syntax highlighting for `.nem` and device config files | Basic syntax support |

All tools share a pure-Python, zero-dependency design (`nemlib`). Shared interfaces are defined in [docs/contracts/](docs/contracts/).

## Quick Start

Browse the examples to see NEM in action:

- [whitepaper.md](/spec/whitepaper.md) - Whitepaper describing the problem statement, high-level positioning and comparison
- [npm_baseline_1.0](examples/npm_baseline_1.0) - NPM device definition
- [conv2d_relu.nem](examples/conv2d_relu.nem) — Tiled Conv2D + ReLU with ping-pong buffers
- [gemm_bias_relu.nem](examples/gemm_bias_relu.nem) — GEMM + Bias + ReLU for fully-connected layers
- [conv2d_maxpool.nem](examples/conv2d_maxpool.nem) — Two-stage Conv2D + MaxPool pipeline

Each program demonstrates explicit buffer allocation, DMA transfers, async compute tasks with token dependencies, and bounded pipelining via `@max_in_flight`.

## Development

See [docs/engineering/README.md](docs/engineering/README.md) for development process, practices, and contribution guidelines. Conformance tests serve as the shared correctness reference across all tools:

```bash
pytest tests/conformance/ -v
```
