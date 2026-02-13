# Phase 1: Interpreter Plan

## Overview

The interpreter is the NEM reference execution engine. It imports all parsing, validation, device model, and type system from `nemlib`. It owns only execution-specific code: memory model, task graph, scheduler, and compute backends.

Architecture is defined in `tools/interpreter/interpreter_spec.md`. This plan covers Phase 1-4 of that spec (Core Infrastructure through User Interface). Phases 5-7 (Timed Mode, NpmPyTorchApi, Polish) are deferred.

## Package Structure

```
tools/interpreter/
  pyproject.toml                # Depends on nemlib, numpy, scipy
  neminterp/
    __init__.py                 # NemInterpreter re-export
    interpreter.py              # NemInterpreter class (load, run, step, inspect)

    memory/
      __init__.py
      memory_model.py           # MemorySystem: DDR/L2/L1 byte arrays
      buffer_manager.py         # BufferManager: allocation with alignment
      region.py                 # RegionView: typed view into buffer

    engine/
      __init__.py
      task_graph.py             # TaskGraph: DAG of tasks + dependencies
      scheduler.py              # FunctionalScheduler: dependency-driven ready queue
      token_manager.py          # TokenManager: token creation, tracking, satisfaction
      executor.py               # Executor: core execution loop

    compute/
      __init__.py
      backend.py                # ComputeBackend protocol
      numpy_backend.py          # NumPyBackend: reference implementations

  tests/                        # Interpreter-specific unit tests
    test_memory.py
    test_buffer_manager.py
    test_region.py
    test_task_graph.py
    test_scheduler.py
    test_executor.py
    test_compute_*.py           # Per-opcode tests
```

## Per-Step Build Plan

### Step 1: Project Setup

- `pyproject.toml`: package metadata, dependencies (nemlib as path dep, numpy, scipy)
- Skeleton `neminterp/__init__.py`
- No functional code yet — interpreter agent waits for nemlib parser

### Step 2: Memory Model

**Modules built**:
- `memory/memory_model.py`:
  - `MemorySystem` class: holds DDR, L2, per-engine L1 as `bytearray` instances
  - Configurable sizes (default: generous for testing; device config overrides later)
  - `read_bytes(level, offset, length) -> bytes`
  - `write_bytes(level, offset, data) -> None`

- `memory/buffer_manager.py`:
  - `BufferManager` class: tracks allocated buffers per memory level
  - `allocate(name, level, size, alignment) -> BufferHandle`
  - Alignment: round up offset to next multiple of alignment
  - Bounds checking: reject if cumulative allocation exceeds level capacity

- `memory/region.py`:
  - `RegionView` class: typed view into a buffer
  - Fields: buffer_handle, offset, extent, elem_type, shape, layout, quant_desc
  - `read_array() -> np.ndarray`: read bytes, cast to elem_type, reshape
  - `write_array(data: np.ndarray) -> None`: reshape, cast, write bytes
  - Sub-byte packing for i4 (2 elements per byte)

**Tests**: Buffer allocation, alignment, bounds; region read/write round-trip; i4 packing

### Step 3: Execution Engine

**Modules built**:
- `engine/token_manager.py`:
  - `TokenManager`: creates tokens (unique IDs), tracks satisfaction state
  - `create_token(name) -> TokenId`
  - `satisfy(token_id) -> None`
  - `is_satisfied(token_id) -> bool`
  - `wait_all(token_ids) -> None` (in functional mode: assert all satisfied)

- `engine/task_graph.py`:
  - `TaskGraph`: DAG of TaskNode entries with dependency edges
  - `add_task(task, deps) -> TaskId`
  - `get_ready_tasks() -> list[TaskId]` (tasks with all deps satisfied)
  - Topological order validation

- `engine/scheduler.py`:
  - `FunctionalScheduler`: simple dependency-driven scheduling
  - Picks any ready task (no resource modeling)
  - Executes immediately (functional mode = no timing)

- `engine/executor.py`:
  - `Executor`: core loop
  - `execute_program(ast, memory_system) -> None`
  - Walks AST, builds task graph, runs scheduler
  - Transfer execution: `memory_system.read_bytes()` from source → `memory_system.write_bytes()` to destination
  - Store execution: same as transfer (in functional mode)
  - Wait execution: verify all referenced tokens satisfied
  - `.sync` variants: execute + immediate wait

**Tests**: Task graph construction, dependency ordering, transfer byte correctness, token satisfaction

### Step 4: Loop Execution

**Extensions**:
- `engine/executor.py`:
  - Loop iteration: for each `i` in `[start..end]`, expand loop body with `i` bound in expression environment
  - `@max_in_flight(N)` enforcement: track active iterations, block when N reached, release when iteration's final task completes
  - Region expressions with loop variables: `(i mod 2) * tileX_bytes` evaluated at runtime via nemlib expression evaluator

**Tests**: Ping-pong buffer indexing; max_in_flight enforcement; all examples execute with transfers

### Step 5: Compute Backend

**Modules built**:
- `compute/backend.py`:
  ```python
  class ComputeBackend(Protocol):
      def execute(self, opcode: str, inputs: list[np.ndarray],
                  outputs: list[RegionView], attributes: dict[str, Any]) -> None: ...
      def supports(self, opcode: str) -> bool: ...
  ```

- `compute/numpy_backend.py`:
  - `NumPyBackend`: implements all stable opcodes using NumPy/SciPy

  **Elementwise unary**: relu (`np.maximum(x, 0)`), leaky_relu, sigmoid, tanh, exp, log, sqrt, abs, neg, gelu, silu
  **Elementwise binary**: add, sub, mul, div, min, max, pow
  **Other elementwise**: clamp
  **Linear algebra**: gemm (`np.matmul` + optional bias, with accum_type casting), matmul
  **Convolution**: conv2d (manual implementation with pads, strides, dilations, groups — or scipy.signal)

- `engine/executor.py`:
  - Compute task execution: read input regions → call backend.execute() → write output regions
  - Attribute forwarding (accum_type, pads, strides, etc.)

**Tests**: Per-opcode unit tests with known input/expected output pairs

### Step 6: Device Integration

**Extensions**:
- `interpreter.py`:
  - `NemInterpreter` class takes shape:
  ```python
  class NemInterpreter:
      def load(self, source: str, device_config: str | None = None) -> None: ...
      def run(self, inputs: dict[str, np.ndarray] | None = None) -> dict[str, np.ndarray]: ...
  ```
  - Load device config via nemlib device resolver
  - Configure memory system sizes from device topology (l1_size_bytes, l2_size_bytes)
  - Pass device config to validation (when available in Step 8)

### Step 7: Remaining Opcodes

**Extensions to `compute/numpy_backend.py`**:

| Category | Opcodes | Implementation |
|----------|---------|---------------|
| Pooling | maxpool, avgpool | Sliding window with kernel_size, strides, pads |
| Normalization | layernorm, rmsnorm | Per-axis normalization with epsilon |
| Softmax | softmax, log_softmax | exp / sum with axis |
| Layout | transpose | `np.transpose` with perm |
| Layout | reshape | `np.reshape` |
| Layout | slice | `np.ndarray` slicing |
| Layout | concat | `np.concatenate` with axis |
| Layout | split | `np.split` with sections/axis |
| Layout | pad | `np.pad` with pads array |
| Layout | gather | `np.take` with axis/indices |
| Type conversion | cast | `array.astype()` |
| Type conversion | quantize | Scale + zero-point quantization |
| Type conversion | dequantize | Inverse quantization (per-tensor/channel/group) |
| INT4 | gemm.int4, conv2d.int4 | i4 unpack → i8 → compute |

### Step 8: Validation + Decorator Enforcement

**Extensions**:
- `interpreter.py`: Call `nemlib.validation.validate()` before execution
- `engine/executor.py`: Enforce decorator semantics during execution:
  - `@materialized`: after task writes region, verify full region committed to memory
  - `@readonly`: reject any write to region
  - `@writeonly`: reject any read from region
  - `@resource`: validate target unit against device topology
  - `@deterministic`: flag to compute backend (for future bit-true mode)
- Error reporting: surface nemlib diagnostics with source locations

## Dependencies

```
neminterp runtime dependencies:
  nemlib (path: ../../libs/nemlib)
  numpy >= 1.24
  scipy >= 1.10  (for conv2d reference)

neminterp dev dependencies:
  pytest >= 7.0
  mypy
  ruff
```
