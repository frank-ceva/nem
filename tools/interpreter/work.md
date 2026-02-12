This file lists all major work items to be worked on, or currently being worked on, in priority order: the upper one is the first to work on.

# NEM interpreter
**Current phase: Architecture spec written** — see [interpreter_spec.md](interpreter_spec.md)

I need to build a NEM interpreter that is capable of executing NEM programs and/or instructions.
I want the interpreter to be built as a python library so that I benefit from all the existing python environment.
The interpreter needs to ensure:
- correct functional behavior
- check for language rules
All as defined in the NEM spec (nem_spec.md)
To help building the interpreter, a python library of all NMU and CSTL compute functions is available and provides bit-true accuracy vs actual hardware.

## Completed: Architecture Specification
status=completed

Architecture specification written in interpreter_spec.md, covering:
- [x] User interface (Python API: load, run, step, inspect, display buffers, breakpoints)
- [x] Threading model (cooperative single-threaded event loop, task graph + ready queue, multi-engine modeling)
- [x] Execution modes: functional (dependency-only) and timed (resource-aware abstract scheduling) — single implementation with mode switch recommended
- [x] Device specification integration (parsing, inheritance resolution, effective type family set, topology enforcement)
- [x] Runtime test environment (DDR/L2/L1 as sized byte arrays, DDR pre-loading/post-read API)
- [x] Compute backend architecture (pluggable: NumPy fallback + NpmPyTorchApi bit-true backend)
- [x] Parser design (recursive descent, full EBNF grammar coverage)
- [x] Semantic analysis (10 validation passes)
- [x] Testing strategy and implementation roadmap (7 phases)

## Add `const` declaration support

**Requested by: spec-int (const declarations work item)**

The NEM spec now includes `const` declarations (see `spec/CHANGELOG.md`). The interpreter must support:

1. **Parser**: Add `const_decl` production: `"const" ID "=" expr`. Add to `decl` alternatives.
2. **AST**: Add `ConstDeclNode(name, expr)` node type.
3. **Semantic analysis**:
   - Evaluate constant expressions at parse/analysis time (integer literals + previously-declared constants + `+`, `-`, `*`, `/`, `mod`, parens).
   - Reject forward references (ID not yet declared as const).
   - Reject duplicate const names.
   - Reject `const` inside loop bodies.
   - Reject name conflicts with buffers, let bindings, token assignments.
   - Reject division by zero.
4. **Runtime**: Substitute constant values in all `expr` evaluation contexts (buffer sizes, region offsets/extents, shape dims, loop bounds, compute attributes).
5. **Conformance**: Pass all tests in `tests/conformance/const/`.

## Remaining: Implementation
The following implementation phases are defined in the spec:
- Phase 1: Core Infrastructure (lexer, parser, AST, device config, memory model)
- Phase 2: Functional Execution (task graph, scheduler, compute backends)
- Phase 3: Semantic Analysis (type families, hazard checking)
- Phase 4: User Interface (NemInterpreter class, DDR management, inspection)
- Phase 5: Timed Mode (cost model, resource contention)
- Phase 6: NpmPyTorchApi Integration (bit-true compute)
- Phase 7: Polish (Jupyter, error messages, packaging)
