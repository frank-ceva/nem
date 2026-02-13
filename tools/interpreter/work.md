This file lists all major work items to be worked on, or currently being worked on, in priority order: the upper one is the first to work on.

# Phase 1, Step 1: Project Setup

**Plan reference:** `plan/phase_1/interpreter.md` Step 1, `plan/phase_1/master.md`

Set up the interpreter package. No functional code yet — wait for nemlib parser to be available from the libs agent.

## Tasks

- `tools/interpreter/pyproject.toml` — package metadata, dependencies (nemlib as path dep, numpy, scipy), dev deps (pytest, mypy, ruff)
- `tools/interpreter/neminterp/__init__.py` — skeleton with version
- `tools/interpreter/neminterp/py.typed` — PEP 561 marker
- Verify: `pip install -e tools/interpreter[dev]` succeeds

## Completion criteria

- Package installs in editable mode
- `import neminterp` succeeds
- Empty test suite runs green

---

# Phase 1, Step 2: Memory Model

**Plan reference:** `plan/phase_1/interpreter.md` Step 2

Build the memory subsystem. Depends on nemlib parser for buffer/region declarations (libs agent Step 2).

## Modules

- `memory/memory_model.py` — MemorySystem: DDR, L2, per-engine L1 as bytearray
- `memory/buffer_manager.py` — BufferManager: allocation with alignment, bounds checking
- `memory/region.py` — RegionView: typed view into buffer, read_array()/write_array(), i4 packing

## Tests

- Buffer allocation, alignment, bounds
- Region read/write round-trip
- i4 sub-byte packing

---

# Phase 1, Steps 3-8: Execution Engine through Validation

**Plan reference:** `plan/phase_1/interpreter.md` Steps 3-8

Subsequent steps (data movement, loops, compute, device integration, remaining opcodes, validation) are defined in the plan. Each step will be broken into detailed tasks when the previous step is complete.

Summary:
- Step 3: Task graph, scheduler, executor (transfer/store/wait)
- Step 4: Loop execution, max_in_flight, variable binding
- Step 5: Compute backend, NumPy implementations (all elementwise, gemm, conv2d)
- Step 6: Device config loading, device-aware execution
- Step 7: Remaining opcodes (pooling, norm, softmax, layout, cast, quant, INT4)
- Step 8: Validation pipeline wiring, decorator enforcement

---

# Prior work items (subsumed by Phase 1 plan)

The following items were created before the Phase 1 plan existed. They are now addressed by specific steps in the plan:

- **Consume opcode registry** → Phase 1 Step 5 (libs agent builds opcodes.py loader; interpreter uses it)
- **Extend device model and add new opcodes** → Phase 1 Steps 6-7
- **Add const declaration support** → Phase 1 Step 1 (libs agent builds parser; interpreter benefits automatically via nemlib)
- **Architecture spec** → status=completed (see interpreter_spec.md)

---
