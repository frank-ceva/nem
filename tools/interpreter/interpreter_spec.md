# NEM Interpreter Architecture Specification

## 1. Introduction and Goals

### 1.1 Purpose

This document specifies the architecture of a **NEM Interpreter** — a Python-based execution engine capable of parsing, validating, and executing NEM (NeuPro-M Execution Model) programs as defined in the [NEM Specification](../docs/nem_spec.md).

The interpreter serves as:

1. **A reference execution environment** for NEM programs, providing functionally correct results that can be used to validate compilers, binders, and hardware implementations.
2. **A development and debugging tool** for NEM program authors, offering single-step execution, state inspection, and rule checking.
3. **A validation platform** for hardware teams, where NEM execution results serve as the golden reference against which TCB-level execution and silicon behavior are compared.

### 1.2 Goals

- **Correct functional behavior**: Execute NEM programs producing bit-true results for all supported opcodes, leveraging the existing NMU/CSTL Python compute library (`NpmPyTorchApi`) for hardware-accurate computation.
- **Language rule enforcement**: Validate programs against all normative rules in the NEM spec — type legality, hazard/aliasing rules, buffer bounds, device validity, decorator semantics, and dependency correctness.
- **Interactive usability**: Provide a rich Python API for loading, running, stepping, inspecting, and debugging NEM programs.
- **Dual execution modes**: Support both a pure functional mode (correctness only) and a timed mode (abstract resource-aware scheduling).
- **Device-aware execution**: Configure the interpreter from NEM device specifications, enforcing type family conformance and topology constraints.

### 1.3 Non-Goals

- **Microarchitectural simulation**: The interpreter does not model bank selection, burst modes, store formats, arbitration, or any sub-NEM hardware detail. These are binder/TCB concerns.
- **Performance optimization**: The interpreter prioritizes correctness and observability over execution speed.
- **TCB generation**: The interpreter executes NEM programs directly; it does not lower them to TCBs.

---

## 2. Architecture Overview

### 2.1 Component Diagram

```
                    +------------------+
                    |   User (Python)  |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  NEM Python API   |  <-- Section 3
                    |  (neminterp pkg)  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
    +---------v----+  +------v------+  +----v---------+
    |    Parser    |  |  Semantic   |  |   Device     |
    | (NEM → AST)  |  |  Analyzer   |  |   Model      |
    +---------+----+  +------+------+  +----+---------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    | Execution Engine  |  <-- Section 4, 5
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
    +---------v----+  +------v------+  +----v---------+
    |   Memory     |  |  Scheduler  |  |   Compute    |
    |   Model      |  | (Func/Timed)|  |   Backends   |
    +---------+----+  +------+------+  +----+---------+
              |              |              |
              |              |         +----v---------+
              |              |         | NpmPyTorchApi|
              |              |         | (bit-true)   |
              |              |         +--------------+
              |              |
    +---------v--------------v---------+
    |      Runtime Environment         |  <-- Section 7
    |  (DDR, L2, L1 memory instances)  |
    +----------------------------------+
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Parser** | Lexes and parses NEM source text (programs and device configs) into an AST per the EBNF grammar |
| **Semantic Analyzer** | Type checking, type family matching, buffer bounds validation, hazard analysis, decorator validation |
| **Device Model** | Loads device configurations, resolves inheritance, computes effective type family sets |
| **Execution Engine** | Orchestrates task execution respecting dependencies, manages tokens, drives the scheduler |
| **Memory Model** | Models DDR, L2, and per-engine L1 as sized byte arrays with allocation tracking |
| **Scheduler** | Determines task execution order; functional mode uses dependency-only ordering, timed mode adds resource modeling |
| **Compute Backends** | Implements opcode semantics; primary backend wraps `NpmPyTorchApi` for bit-true accuracy, fallback uses NumPy |
| **Runtime Environment** | Aggregates memory model, device topology, and execution state into a single inspectable runtime |

### 2.3 Package Structure

```
nem/interpreter/
    neminterp/                  # Python package root
        __init__.py             # Public API re-exports
        parser/
            __init__.py
            lexer.py            # Tokenizer for NEM grammar
            ast_nodes.py        # AST node definitions
            parser.py           # Recursive descent parser
        analyzer/
            __init__.py
            type_checker.py     # Type family matching and validation
            hazard_checker.py   # Aliasing and dependency validation
            device_resolver.py  # Device config resolution and inheritance
        engine/
            __init__.py
            executor.py         # Core execution loop
            scheduler_func.py   # Functional mode scheduler
            scheduler_timed.py  # Timed mode scheduler
            token_manager.py    # Token creation, tracking, satisfaction
        memory/
            __init__.py
            memory_model.py     # DDR, L2, L1 memory instances
            buffer_manager.py   # Buffer allocation and lifetime
            region.py           # Region view implementation
        compute/
            __init__.py
            backend_numpy.py    # NumPy fallback compute backend
            backend_npm.py      # NpmPyTorchApi wrapper
            opcode_registry.py  # Maps opcodes to compute functions
        runtime/
            __init__.py
            environment.py      # Runtime environment aggregation
            state.py            # Execution state snapshot
        api/
            __init__.py
            interpreter.py      # Top-level NemInterpreter class
            commands.py         # Interactive commands (step, inspect, etc.)
    tests/
        test_parser.py
        test_type_checker.py
        test_executor_functional.py
        test_executor_timed.py
        test_memory_model.py
        test_integration.py
    setup.py                    # Package installation
```

---

## 3. User Interface (Python API)

The interpreter is exposed as a Python library (`neminterp`) with a primary class `NemInterpreter` that provides all user-facing functionality.

### 3.1 Core Interpreter Class

```python
from neminterp import NemInterpreter

# Create interpreter with device configuration
interp = NemInterpreter(device="path/to/device.cfg")

# Or with inline device config
interp = NemInterpreter(device="npm_lite")  # built-in device name

# Or with no device (device-agnostic mode — only baseline types)
interp = NemInterpreter()
```

### 3.2 Program Loading

```python
# Load a NEM program from file
program = interp.load("path/to/program.nem")

# Load from string
program = interp.load_string("""
    program matmul_example:
    buffer A_DDR : DDR (size=4096, align=64)
    buffer B_DDR : DDR (size=4096, align=64)
    ...
""")

# Parse only (no execution setup)
ast = interp.parse("path/to/program.nem")

# Validate without executing (type check, hazard analysis, device validity)
diagnostics = interp.validate(program)
for d in diagnostics:
    print(f"{d.severity}: {d.message} at {d.location}")
```

### 3.3 Execution Control

```python
# === Full execution ===
result = interp.run(program)
# result.status: "completed" | "error"
# result.cycle_count: (timed mode only) total abstract cycles

# === Execution modes ===
interp.set_mode("functional")   # Default: dependency-only scheduling
interp.set_mode("timed")        # Resource-aware abstract scheduling

# === Step-by-step execution ===
session = interp.start(program)

# Step: execute the next ready task
task_result = session.step()
# task_result.task_id: e.g., "tX"
# task_result.task_type: e.g., "transfer.async"
# task_result.status: "completed" | "waiting"
# task_result.token: produced token (if any)

# Step N tasks
results = session.step(n=5)

# Run until a specific token is satisfied
session.run_until(token="tC")

# Run until a breakpoint
session.add_breakpoint(task="tR")       # Break before executing task tR
session.add_breakpoint(line=42)         # Break at source line 42
session.add_breakpoint(loop_iter=3)     # Break at loop iteration 3
session.run()  # Runs until breakpoint or completion

# Continue after breakpoint
session.continue_()

# Run one full loop iteration
session.step_iteration()
```

### 3.4 State Inspection

```python
# === Memory inspection ===
# Read raw bytes from a memory level
data = session.read_memory("DDR", offset=0, size=256)

# Read a region as a typed NumPy array
arr = session.read_region("X_pp_i")
# arr is a numpy array with shape and dtype matching the region definition

# Read a buffer's full contents
buf_data = session.read_buffer("X_L2")

# === Token / dependency inspection ===
tokens = session.get_tokens()
# Returns dict: {token_name: {"satisfied": bool, "produced_by": task_id}}

pending = session.get_pending_tasks()
ready = session.get_ready_tasks()
completed = session.get_completed_tasks()

# === Execution state ===
state = session.get_state()
# state.current_loop_iteration: int or None
# state.active_tasks: list of in-flight tasks
# state.satisfied_tokens: set of token names
# state.engine_states: per-engine resource utilization (timed mode)

# === Device info ===
dev = interp.get_device_info()
# dev.name: "npm_lite"
# dev.num_engines: 1
# dev.per_engine: {"NMU": 1, "CSTL": 2, "DMA": 2}
# dev.effective_types: dict of opcode -> list of legal family variants
```

### 3.5 DDR Data Management (Runtime Test Environment)

```python
# === Pre-load data into DDR before execution ===
import numpy as np

# Load raw bytes
interp.ddr_write(offset=0, data=bytes(4096))

# Load a typed tensor at a DDR offset (auto-converts to byte representation)
weights = np.random.randn(64, 64).astype(np.float16)
interp.ddr_write_tensor(offset=0, tensor=weights)

# Load from file (binary or .npy)
interp.ddr_load_file(offset=0, path="weights.bin")
interp.ddr_load_npy(offset=0, path="weights.npy")

# === Read results from DDR after execution ===
output = interp.ddr_read(offset=0, size=4096)
output_tensor = interp.ddr_read_tensor(offset=0, shape=(64, 64), dtype=np.float16)

# === DDR configuration ===
# DDR size is configurable (default: 256 MB)
interp = NemInterpreter(device="npm_lite", ddr_size=512 * 1024 * 1024)

# Query DDR info
info = interp.ddr_info()
# info.size: total DDR size in bytes
# info.allocated: bytes allocated by buffers
# info.free: remaining bytes
```

### 3.6 Display and Debugging Commands

```python
# === Pretty-print AST ===
interp.dump_ast(program)

# === Display buffer map ===
session.dump_buffers()
# Output:
#   Buffer      Level  Offset    Size    Align  Status
#   X_L2        L2     0x0000    65536   64     allocated
#   W_L2        L2     0x10000   16384   64     allocated
#   X_L1[0]     L1[0]  0x0000    8192    64     allocated
#   ...

# === Display region details ===
session.dump_region("X_pp_i")
# Output:
#   Region: X_pp_i
#     Buffer: X_L1, offset=0, extent=4096
#     Type: i8, shape=[1,8,8,64], layout=NHWC
#     Decorators: (none)
#     Contents: [0x00, 0x01, ...]  (first 32 bytes)

# === Display execution trace ===
session.dump_trace()
# Output (functional mode):
#   Step  Task    Type              Status     Token   Deps
#   1     tX      transfer.async    completed  tX      []
#   2     tW      transfer.async    completed  tW      []
#   3     -       wait(tX, tW)      completed  -       [tX, tW]
#   4     tC      conv2d.async      completed  tC      [tX, tW]
#   ...

# Output (timed mode, adds timing columns):
#   Step  Task    Type              Start  End   Unit     Engine
#   1     tX      transfer.async    0      12    DMA[0]   0
#   2     tW      transfer.async    0      10    DMA[1]   0
#   3     tC      conv2d.async      12     45    NMU[0]   0
#   ...

# === Export trace ===
session.export_trace("trace.json")   # JSON format
session.export_trace("trace.csv")    # CSV format
```

### 3.7 Convenience: Jupyter / REPL Integration

```python
# In Jupyter, regions display as formatted tables/arrays
session.read_region("Y_pp_i")  # Renders as styled numpy array

# Session objects have rich __repr__
session  # Shows current state summary

# Context manager for automatic cleanup
with interp.start(program) as session:
    session.run()
    result = session.read_region("Y_tile_0")
```

---

## 4. Threading Model

### 4.1 Concurrency in the NPM Abstract Machine

The NEM abstract machine defines several levels of concurrency:

1. **Inter-engine parallelism**: Multiple Engines execute independently and concurrently, each with its own Sequencer and L1.
2. **Intra-engine parallelism**: Within an Engine, multiple execution units (NMU, CSTL instances, DMA channels) can operate concurrently on independent tasks.
3. **Bounded pipelining**: `@max_in_flight(N)` allows N loop iterations to overlap.
4. **Async tasks**: Tasks marked `.async` produce tokens and may execute concurrently with subsequent tasks (subject to dependencies).

### 4.2 Interpreter Threading Strategy

The interpreter uses a **cooperative, single-threaded event-driven model** rather than OS-level threads. This is the recommended approach for both execution modes.

**Rationale:**
- NEM's concurrency is **logical**, not physical. Tasks don't truly execute in parallel on the interpreter — they execute in a valid order consistent with dependencies.
- A single-threaded event loop is deterministic, debuggable, and avoids race conditions in the interpreter itself.
- The NEM spec states: "READY tasks may execute in any order consistent with dependencies." The interpreter picks one valid order.
- For the **timed mode**, abstract time advances discretely; no real-time simulation is needed.

### 4.3 Execution Model: Task Graph + Ready Queue

```
                    +-------------------+
                    |  Program Counter  |
                    | (statement index) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Task Instantiation|
                    |  (expand loops,    |
                    |   evaluate exprs)  |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   Task Graph       |
                    | (DAG of tasks with |
                    |  token deps)       |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v----------+     +------------v---------+
    | Ready Queue        |     | Waiting Set          |
    | (deps satisfied)   |     | (deps not satisfied) |
    +--------------------+     +----------------------+
```

**Algorithm (per step):**

1. **Instantiate**: If the program counter points to a new statement, instantiate it (evaluate expressions, create task node, register token, add to task graph).
2. **Check readiness**: For all tasks in the waiting set, check if their dependency tokens are all satisfied. Move newly-ready tasks to the ready queue.
3. **Select**: Pick the next task from the ready queue:
   - **Functional mode**: Any ready task (deterministic tie-breaking by source order, or randomizable for robustness testing).
   - **Timed mode**: The task whose resource becomes available earliest (see Section 5.2).
4. **Execute**: Run the selected task's operation (transfer, compute, store, wait).
5. **Complete**: Mark the task's output token as satisfied. Advance the program counter if needed.
6. **Repeat** until all tasks are complete or an error occurs.

### 4.4 Multi-Engine Modeling

Each Engine is modeled as a separate execution domain with:
- Its own L1 memory instance (`L1[k]`)
- Its own set of execution unit instances (NMU, CSTL, DMA)
- Its own ready queue (in timed mode)

The interpreter maintains a list of `EngineState` objects. Task-to-engine assignment follows the NEM placement rules:

- If a task references `L1[k]`, it executes on Engine `k`.
- Tasks referencing only L2/DDR are Engine-agnostic; the interpreter assigns them round-robin or to the least-loaded engine (timed mode).

In functional mode, multi-engine execution is serialized (one task at a time across all engines) since order doesn't affect functional results. In timed mode, engines advance their local abstract clocks independently.

### 4.5 Loop Unrolling and `@max_in_flight`

Loops are expanded lazily: the interpreter instantiates iteration `i+1` only when the `@max_in_flight` bound permits it.

```
max_in_flight = N
active_iterations = set of iterations with at least one incomplete task

while loop has more iterations OR active_iterations is non-empty:
    if len(active_iterations) < N and loop has more iterations:
        instantiate next iteration's tasks
        add iteration to active_iterations

    execute one ready task from any active iteration

    if all tasks of iteration j are complete:
        remove j from active_iterations
```

This naturally models ping-pong and ring-buffer semantics: iteration `i` and `i+N` never overlap, so buffer slots indexed by `i mod N` are safe to reuse.

### 4.6 Non-Deterministic Scheduling (Optional)

For robustness testing, the interpreter can optionally randomize the selection among ready tasks:

```python
interp.set_scheduling("deterministic")   # Default: source-order tie-breaking
interp.set_scheduling("random", seed=42) # Random selection among ready tasks
```

This helps detect programs that accidentally depend on a specific execution order rather than explicit token dependencies, which would be a latent correctness bug.

---

## 5. Execution Modes

### 5.1 Functional Mode (Default)

**Goal**: Execute NEM programs producing correct output, enforcing all language rules, without modeling timing or resource contention.

**Characteristics:**
- Tasks execute one at a time in dependency order.
- No notion of time, cycles, or resource availability.
- All `.async` and `.sync` task variants behave identically (both complete before returning).
- `wait` tasks simply verify that the listed tokens are satisfied (they always are by the time `wait` is reached, since async tasks complete immediately in functional mode).
- `@resource` decorators are recorded for validation but have no scheduling effect.
- `@max_in_flight` is enforced for buffer safety (limiting active iterations) but does not create real overlap.

**Validation performed:**
- Type family matching for all compute tasks
- Device validity (effective type family set check)
- Buffer bounds (region offset + extent within buffer)
- Region type consistency (byte extent >= num_elements * sizeof(elem))
- Hazard/aliasing rules (overlapping regions with write access must be dependency-ordered)
- Decorator validity (known decorators, correct argument types)
- `@max_in_flight` enforcement (no more than N active iterations)
- Engine placement rules (no cross-engine L1 references)

**Output**: Functional results (buffer contents) + validation diagnostics.

### 5.2 Timed Mode

**Goal**: Model abstract timing to expose resource contention, pipeline stalls, and scheduling inefficiencies without full cycle-accurate microarchitectural simulation.

**Characteristics:**
- Each execution unit instance (e.g., NMU[0], CSTL[0], DMA[0]) has a local clock representing its next-available time.
- Each task type has an abstract cost model (configurable):

  | Task Type | Default Cost Model |
  |-----------|-------------------|
  | `transfer.async` / `transfer.sync` | `ceil(byte_extent / bandwidth) + latency` |
  | `store.async` / `store.sync` | `ceil(byte_extent / bandwidth) + latency` |
  | `gemm` / `matmul` | `ceil(M * N * K / mac_throughput)` |
  | `conv2d` | `ceil(output_elements * K_h * K_w * C_in / mac_throughput)` |
  | elementwise ops | `ceil(num_elements / eltwise_throughput)` |
  | `wait` | 0 (synchronization only) |

- Cost model parameters are derived from the device configuration or user-supplied timing profiles:

  ```python
  interp.set_timing_profile({
      "NMU": {"mac_throughput": 4096, "latency": 2},    # MACs per cycle, startup latency
      "CSTL": {"eltwise_throughput": 256, "latency": 1},
      "DMA": {"bandwidth": 32, "latency": 4},            # bytes per cycle
  })
  ```

- Task scheduling respects resource availability:
  1. A task is ready when all dependency tokens are satisfied **AND** its assigned execution unit is available (its clock <= current global time).
  2. When multiple tasks are ready, the one with the earliest available unit is selected.
  3. The global clock advances to the minimum completion time across all in-flight tasks when no tasks are ready at the current time.

- `@resource` decorators bind tasks to specific unit instances, affecting the availability check.
- Without `@resource`, the scheduler assigns tasks to the first available instance of the eligible unit type.

**Output**: Functional results + timing trace (per-task start/end cycles, unit assignment, stall analysis).

### 5.3 Recommendation: Single Implementation with Mode Switch

A single implementation is recommended, with the execution mode as a configuration flag. The core loop is identical — only the **task selection strategy** differs:

- **Functional mode**: `select_task = ready_queue.pop(0)` (first ready task by source order)
- **Timed mode**: `select_task = min(ready_queue, key=lambda t: available_time(t.unit))` (earliest-available unit)

The timed mode is a strict superset of functional mode's state. The cost model is simply a no-op in functional mode (all costs are 0, all units are always available).

This approach avoids code duplication while keeping functional mode lightweight. The mode switch is:

```python
class Scheduler:
    def select_next(self, ready_tasks: list[Task]) -> Task:
        if self.mode == "functional":
            return self._select_functional(ready_tasks)  # source order
        else:
            return self._select_timed(ready_tasks)        # earliest unit

    def complete_task(self, task: Task, cost: int):
        if self.mode == "timed":
            self._advance_unit_clock(task.unit, cost)
```

---

## 6. Device Specification Integration

### 6.1 Device Configuration Loading

The interpreter parses device configurations using the same parser as NEM programs (they share the grammar). Device configs can come from:

1. **File reference**: `device "path/to/device.cfg"` in the program
2. **Named reference via include**: `device npm_lite` (after `include "devices.nem"`)
3. **Inline in program**: `device npm_lite { ... }` block
4. **Interpreter constructor**: `NemInterpreter(device="path/to/device.cfg")`
5. **Built-in presets**: The interpreter ships with built-in device configs for common NPM SKUs

### 6.2 Device Resolution

The `DeviceResolver` component:

1. Parses the device configuration block(s)
2. Resolves `extends` inheritance chains (single-parent, multi-level allowed)
3. Validates schema rules (spec_version, baseline, topology constraints)
4. Computes the **effective type family set**:
   ```
   effective[op] = baseline_must[op] ∪ opcode.mandatory[op] ∪ opcode.extended[op]
   ```
5. Validates disjointness: `opcode.mandatory ∩ opcode.extended == ∅`
6. Validates that resolved `opcode.mandatory` is non-empty

The resolved device is stored as a `DeviceConfig` object:

```python
@dataclass
class DeviceConfig:
    name: str
    spec_version: str
    baseline: str
    num_engines: int
    per_engine: dict[str, int]    # {"NMU": 1, "CSTL": 2, "DMA": 2}
    mandatory_variants: set[str]  # {"gemm.float<bf16>.no_bias", ...}
    extended_variants: set[str]   # {"gemm.float<f32>.no_bias", ...}
    effective_set: dict[str, set[str]]  # opcode -> set of legal variant refs
```

### 6.3 Type Family Validation

Before execution, the semantic analyzer checks every compute task instance against the device's effective type family set:

1. **Identify the opcode** (e.g., `gemm`, `conv2d`, `relu`)
2. **Extract operand types** from region attributes (`elem`, `shape`, `quant`)
3. **Match against type families**: iterate over the effective set for this opcode, attempt to match the operand types against each family variant's operand bindings
4. **Report errors**: if no variant matches, report the failing opcode instance and the nearest available variant

```python
# Example validation error:
# ERROR: gemm.async at line 42: operand A has elem=f32, but no matching
#        family variant in effective set for device 'npm_lite'.
#        Nearest match: gemm.float<f16>.no_bias (requires A: f16)
#        Available variants: gemm.float<f16>.no_bias, gemm.float<f16>.with_bias,
#                           gemm.int8<i8>.no_bias, gemm.int8<i8>.with_bias
```

### 6.4 Topology Enforcement

The device topology constrains:
- Number of engines (tasks referencing `L1[k]` require `k < num_engines`)
- Number of unit instances per engine (`@resource(CSTL[3])` requires `per_engine.CSTL >= 4`)
- Resource binding rules (exact match → same-type remap → cross-type translation)

---

## 7. Runtime Test Environment

### 7.1 Memory Hierarchy Model

The runtime models the three memory levels as sized byte arrays:

```
+--------------------------------------------------+
|                      DDR                          |
|  (configurable size, default 256 MB)             |
|  Shared across all engines                        |
+--------------------------------------------------+

+--------------------------------------------------+
|                       L2                          |
|  (configurable size, default 4 MB)               |
|  Shared across all engines                        |
+--------------------------------------------------+

+------------------+  +------------------+
|    L1[0]         |  |    L1[1]         |  ...
| (config size,    |  | (config size,    |
|  default 1 MB)   |  |  default 1 MB)   |
| Engine 0 local   |  | Engine 1 local   |
+------------------+  +------------------+
```

Each memory level is implemented as:

```python
class MemoryLevel:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size
        self.data = bytearray(size)           # Raw storage
        self.allocations: list[Allocation] = []  # Track buffer allocations

    def read(self, offset: int, length: int) -> bytes: ...
    def write(self, offset: int, data: bytes): ...
    def allocate(self, size: int, align: int) -> int: ...  # Returns offset
```

### 7.2 Buffer Allocation

When the interpreter encounters a `buffer` declaration:

1. **Determine memory level** (DDR, L2, or L1[k])
2. **Allocate** within that level's byte array, respecting alignment
3. **Track allocation** (name, offset, size, align, status)
4. **Initialize to zero** (or uninitialized pattern for debugging)

Buffer allocation follows declaration order. The interpreter does not perform automatic packing or optimization — it allocates linearly with alignment padding. This mimics a simple allocator and makes buffer overlap/aliasing analysis straightforward.

### 7.3 DDR Pre-loading and Post-read

The DDR is the primary interface for loading test data and reading results. The user workflow is:

```python
# 1. Create interpreter and load program
interp = NemInterpreter(device="npm_lite", ddr_size=256 * 1024 * 1024)
program = interp.load("conv2d_relu.nem")

# 2. Pre-load input data and weights into DDR
#    Offsets must match the buffer declarations in the NEM program
input_data = np.random.randint(-128, 127, size=(1,64,64,64), dtype=np.int8)
weights = np.random.randint(-128, 127, size=(3,3,64,64), dtype=np.int8)
bias = np.zeros(64, dtype=np.int32)

interp.ddr_write_tensor(offset=0,     tensor=input_data)     # matches X_DDR
interp.ddr_write_tensor(offset=262144, tensor=weights)        # matches W_DDR
interp.ddr_write_tensor(offset=278528, tensor=bias)           # matches B_DDR

# 3. Run the program
result = interp.run(program)

# 4. Read output from DDR
output = interp.ddr_read_tensor(
    offset=278784,                 # matches Y_DDR buffer offset
    shape=(1, 64, 64, 64),
    dtype=np.int8
)

# 5. Compare against reference
reference = compute_reference_conv2d_relu(input_data, weights, bias)
np.testing.assert_array_equal(output, reference)
```

### 7.4 L2 and L1 Inspection

While DDR is the primary user-facing data interface, L2 and L1 contents can also be inspected during debugging:

```python
# During step-by-step execution
session = interp.start(program)
session.step()  # Execute first transfer

# Inspect L1 after transfer
l1_data = session.read_memory("L1", engine=0, offset=0, size=4096)

# Read L2 buffer contents
l2_data = session.read_memory("L2", offset=0, size=65536)
```

### 7.5 Memory Hierarchy Data Flow

The interpreter enforces that data only moves between memory levels through explicit `transfer` and `store` tasks:

```
DDR  ←→  L2  ←→  L1[k]       (via transfer.async / store.async)
                   ↕
              Compute units     (read from / write to L1)
```

Direct DDR ↔ L1 transfers are allowed by NEM (the spec does not restrict transfer level pairs). The interpreter models the transfer by copying bytes from the source region's memory level to the destination region's memory level.

Compute tasks read input regions from L1 (or L2 for bias/scalar operands) and write output regions to L1 (or L2).

---

## 8. Compute Function Integration

### 8.1 Backend Architecture

The interpreter uses a pluggable compute backend system:

```python
class ComputeBackend(Protocol):
    def execute(self, opcode: str, inputs: list[RegionView],
                output: RegionView, attrs: dict) -> None:
        """Execute an opcode on the given input/output regions."""
        ...

    def supports(self, opcode: str) -> bool:
        """Check if this backend supports the given opcode."""
        ...
```

Two backends are provided:

### 8.2 NumPy Backend (Default Fallback)

A pure Python/NumPy implementation of all NEM opcodes. This is always available and serves as:
- The default backend when `NpmPyTorchApi` is not installed
- A reference for validating the `NpmPyTorchApi` backend
- A fast path for simple operations

Implementation sketch for key opcodes:

```python
class NumpyBackend:
    def _gemm(self, A, B, C_bias, Y, attrs):
        # A: (M, K), B: (K, N) or (N, K) depending on layout
        accum = A.astype(np.float32) @ B.astype(np.float32)  # FP32 accumulator
        if C_bias is not None:
            accum += C_bias.astype(np.float32)
        Y[:] = accum.astype(Y.dtype)

    def _relu(self, X, Y, attrs):
        Y[:] = np.maximum(X, 0)

    def _transfer(self, src_region, dst_region):
        dst_region.write_bytes(src_region.read_bytes())
```

### 8.3 NpmPyTorchApi Backend (Bit-True)

Wraps the existing `NpmPyTorchApi` Python library to provide hardware-accurate, bit-true results for NMU and CSTL operations. This backend is used when:
- `NpmPyTorchApi` is installed and importable
- The user explicitly requests it: `interp.set_compute_backend("npm")`

```python
class NpmBackend:
    def __init__(self):
        import NpmPyTorchApi  # or equivalent import path
        self.api = NpmPyTorchApi

    def _gemm(self, A, B, C_bias, Y, attrs):
        # Translate NEM operands to NpmPyTorchApi function signature
        # This uses the same NMU compute functions that the func-sim
        # kernel in npm-kernel-funcsim.cpp wraps at the C++ level
        result = self.api.nmu_gemm(
            data=A, weights=B, bias=C_bias,
            accum_type=attrs["accum_type"],
            precision=attrs.get("precision", "fp16")
        )
        Y[:] = result

    def _relu(self, X, Y, attrs):
        Y[:] = self.api.cstl_relu(X)

    def _conv2d(self, X, W, B, Y, attrs):
        Y[:] = self.api.nmu_conv2d(
            data=X, weights=W, bias=B,
            pads=attrs["pads"],
            strides=attrs["strides"],
            dilations=attrs["dilations"],
            groups=attrs.get("groups", 1),
            accum_type=attrs["accum_type"]
        )
```

The exact function names and signatures of `NpmPyTorchApi` will be determined during implementation based on the library's actual API. The backend is designed to adapt to the library's interface.

### 8.4 Backend Selection

```python
# Auto-detect (prefer NpmPyTorchApi if available)
interp.set_compute_backend("auto")

# Force NumPy backend
interp.set_compute_backend("numpy")

# Force NpmPyTorchApi backend (error if not installed)
interp.set_compute_backend("npm")

# Per-opcode override (e.g., use npm for GEMM, numpy for everything else)
interp.set_compute_backend("numpy")
interp.set_opcode_backend("gemm", "npm")
interp.set_opcode_backend("conv2d", "npm")
```

---

## 9. Parser Design

### 9.1 Lexer

The lexer tokenizes NEM source text into a stream of tokens. Token types include:

| Category | Tokens |
|----------|--------|
| Keywords | `program`, `buffer`, `region`, `loop`, `endloop`, `let`, `wait`, `device`, `include`, `topology`, `per_engine` |
| Task keywords | `transfer.async`, `transfer.sync`, `store.async`, `store.sync` |
| Compound keywords | `opcode.mandatory`, `opcode.extended` |
| Opcodes | `gemm`, `matmul`, `conv2d`, `conv1d`, `conv3d`, `depthwise_conv2d`, `relu`, `add`, `sub`, `mul`, `div`, `sigmoid`, `tanh`, `exp`, `log`, `sqrt`, `abs`, `neg`, `leaky_relu`, `clamp`, `min`, `max`, `pow`, `maxpool`, `avgpool`, `transpose`, `reshape`, `slice`, `concat`, `split`, `pad`, `gather`, `reduce_sum`, `reduce_max`, `reduce_min`, `argmax`, `argmin`, `cast`, `quantize`, `dequantize`, `compute` |
| Memory levels | `DDR`, `L2`, `L1` |
| Unit types | `NMU`, `CSTL`, `DMA` |
| Element types | `i4`, `i8`, `i16`, `i32`, `u8`, `u16`, `u32`, `f16`, `bf16`, `f32` |
| Type attrs | `elem`, `shape`, `layout`, `strides`, `quant` |
| Task attrs | `IN`, `OUT`, `deps`, `dst`, `src` |
| Operators | `+`, `-`, `*`, `/`, `mod` |
| Delimiters | `(`, `)`, `[`, `]`, `{`, `}`, `,`, `:`, `=`, `..`, `.`, `@`, `"`, `#` |
| Literals | `INT` (integer), `STRING` (quoted string), `FLOAT` (floating-point), `BOOL` (`true`/`false`) |
| Identifiers | `ID` (user-defined names) |

Comments (`# ...`) are stripped during lexing. The `.async` and `.sync` suffixes are parsed as part of compound tokens (e.g., `transfer.async` is a single token).

### 9.2 Parser

A **recursive descent parser** implements the EBNF grammar from the NEM spec. The parser produces an AST (Abstract Syntax Tree) with the following key node types:

```python
@dataclass
class ProgramNode:
    name: str | None
    device_decl: DeviceDeclNode | None
    statements: list[StmtNode]

@dataclass
class BufferDeclNode:
    name: str
    mem_level: MemLevel          # DDR, L2, L1[expr]
    size: ExprNode
    align: int | None
    decorators: list[DecoratorNode]

@dataclass
class RegionDeclNode:
    name: str
    buffer_name: str
    offset: ExprNode
    extent: ExprNode
    elem: str | None             # Element type
    shape: list[ExprNode] | None
    layout: str | None
    strides: list[ExprNode] | None
    quant: QuantDescNode | None
    decorators: list[DecoratorNode]

@dataclass
class TaskNode:
    token_name: str | None       # The assigned token (e.g., "tX")
    task_type: str               # "transfer.async", "gemm.async", etc.
    operands: dict[str, ...]     # Named operands (src, dst, IN, OUT)
    attributes: dict[str, ...]   # Task attributes (deps, pads, strides, etc.)
    decorators: list[DecoratorNode]

@dataclass
class LoopNode:
    var: str
    start: ExprNode
    end: ExprNode
    decorators: list[DecoratorNode]  # @max_in_flight, etc.
    body: list[StmtNode]

@dataclass
class WaitNode:
    tokens: list[str]

@dataclass
class DeviceConfigNode:
    name: str
    extends: str | None
    spec_version: str | None
    baseline: str | None
    topology: TopologyNode | None
    mandatory: list[str]
    extended: list[str]
```

### 9.3 Error Reporting

The parser produces source-location-aware errors:

```
conv2d_relu.nem:42:5: error: expected 'OUT' after input operand list
    tC = conv2d.async IN X_pp_i, W_l1
                                      ^
conv2d_relu.nem:15:1: error: buffer size expression references undefined variable 'tile_sz'
    buffer X_L1 : L1 (size=2*tile_sz, align=64)
                              ^^^^^^^
```

---

## 10. Semantic Analysis

### 10.1 Validation Passes

The semantic analyzer runs the following passes in order:

| Pass | Checks |
|------|--------|
| **1. Name resolution** | All identifiers (buffers, regions, tokens, loop variables) resolve to declarations. No duplicate names in the same scope. |
| **2. Expression evaluation** | Constant expressions can be evaluated (sizes, offsets). Loop variable expressions are deferred. |
| **3. Buffer validation** | Sizes > 0, alignment is power-of-2, memory level is valid for device. |
| **4. Region validation** | Offset + extent <= buffer size. For typed regions: byte_extent >= num_elements * sizeof(elem). Layout/strides are consistent with shape. |
| **5. Type checking** | Every compute task's operand types match a legal type family variant in the effective set. Required attributes (accum_type, pads, etc.) are present. |
| **6. Dependency validation** | All tokens referenced in `deps` lists and `wait` are produced by earlier tasks (in source order or within the same loop scope). |
| **7. Hazard analysis** | Overlapping regions with write access are ordered by explicit dependencies. Overlapping transfers have `@memmove`. |
| **8. Engine placement** | No task references L1 from two different engines. Loop body tasks referencing L1[k] are consistent. |
| **9. Decorator validation** | All decorators are known. Arguments are correct types. `@resource` unit types match device topology. |
| **10. Loop validation** | `@max_in_flight(N)` with N >= 1. Loop bounds are valid (start <= end). |

### 10.2 Diagnostic Severity Levels

| Severity | Meaning |
|----------|---------|
| **error** | Program is invalid; execution is refused |
| **warning** | Program is valid but likely contains a mistake (e.g., redundant MUST variant in device config) |
| **info** | Informational diagnostic (e.g., "task tW can be hoisted out of loop") |

---

## 11. Testing Strategy

### 11.1 Unit Tests

| Component | Test Focus |
|-----------|------------|
| Lexer | Token stream for all token types, comments, edge cases |
| Parser | AST structure for each grammar production; error recovery |
| Type checker | MUST/MAY variant matching; rejection of illegal types; device-aware validation |
| Hazard checker | Overlap detection; dependency ordering verification; @memmove |
| Memory model | Allocation, alignment, bounds checking, read/write correctness |
| Scheduler (functional) | Correct execution order for known dependency graphs |
| Scheduler (timed) | Resource contention, stall detection, clock advancement |

### 11.2 Integration Tests

1. **Reference programs**: Execute the examples from the NEM spec ([conv2d_relu.nem](../docs/vscode_ext/examples/conv2d_relu.nem), multi-CSTL pipeline) and verify buffer contents.
2. **Device validity**: Programs that should be rejected by device X but accepted by device Y.
3. **Hazard detection**: Programs with intentional aliasing errors.
4. **Loop pipelining**: Verify that `@max_in_flight(N)` correctly bounds active iterations.
5. **Multi-engine**: Programs with L1[0] and L1[1] tasks executing on separate engines.

### 11.3 Golden Reference Tests

When `NpmPyTorchApi` is available:
- Execute programs with both NumPy and npm backends
- Verify bit-exact match for integer operations
- Verify acceptable tolerance for floating-point operations (matching the tolerance defined by the bit-true library)

### 11.4 Randomized Scheduling Tests

Run programs with randomized task selection order and verify:
- Functional results are identical regardless of scheduling order
- No assertion failures or buffer safety violations
- This catches programs that accidentally depend on a specific execution order

---

## 12. Implementation Roadmap

### Phase 1: Core Infrastructure
- [ ] Lexer and parser for NEM grammar (programs + device configs)
- [ ] AST node definitions
- [ ] Device configuration resolution (with inheritance)
- [ ] Memory model (DDR, L2, L1 as byte arrays)
- [ ] Buffer and region management

### Phase 2: Functional Execution
- [ ] Task graph construction from AST
- [ ] Token management (creation, satisfaction)
- [ ] Functional scheduler (dependency-only ordering)
- [ ] Transfer task execution (byte copy between memory levels)
- [ ] Wait task execution
- [ ] Store task execution
- [ ] NumPy compute backend (gemm, conv2d, elementwise ops)
- [ ] Loop expansion with `@max_in_flight`

### Phase 3: Semantic Analysis
- [ ] Type family definitions (all families from spec appendix)
- [ ] Type family matching engine
- [ ] Hazard/aliasing analysis
- [ ] Full validation pipeline

### Phase 4: User Interface
- [ ] `NemInterpreter` class with load/run/step API
- [ ] DDR data management (write_tensor, read_tensor)
- [ ] State inspection (dump_buffers, dump_trace, read_region)
- [ ] Breakpoints and stepping
- [ ] Trace export (JSON, CSV)

### Phase 5: Timed Mode
- [ ] Abstract cost model for each task type
- [ ] Per-unit-instance clock tracking
- [ ] Timed scheduler with resource contention
- [ ] Timing trace output
- [ ] Stall analysis reporting

### Phase 6: NpmPyTorchApi Integration
- [ ] Backend wrapper for NMU operations (gemm, conv2d)
- [ ] Backend wrapper for CSTL operations (relu, add, etc.)
- [ ] Backend selection and per-opcode override
- [ ] Bit-true validation test suite

### Phase 7: Polish
- [ ] Jupyter integration (__repr__, display)
- [ ] Error message quality (source location, suggestions)
- [ ] Documentation and usage examples
- [ ] Package setup (pip installable)

---

## 13. Dependencies

| Dependency | Purpose | Required? |
|------------|---------|-----------|
| Python 3.10+ | Language runtime | Yes |
| NumPy | Array operations, fallback compute backend | Yes |
| NpmPyTorchApi | Bit-true NMU/CSTL compute | Optional (recommended) |
| pytest | Test framework | Dev only |

---

## 14. Open Questions

1. **NpmPyTorchApi API surface**: The exact Python API of the NpmPyTorchApi library needs to be documented. The interpreter's npm backend will adapt to whatever interface it exposes. A mapping document from NEM opcodes to NpmPyTorchApi functions should be created during Phase 6.

2. **L1/L2 size defaults**: The NEM spec does not prescribe memory sizes. Default sizes should be configurable and match common NPM SKU configurations (e.g., L1=1MB, L2=4MB).

3. **Expression evaluation scope**: NEM allows expressions in buffer sizes and region offsets. Some may reference loop variables (e.g., `i * tileX_bytes`). The interpreter needs a lightweight expression evaluator that can handle both compile-time constants and loop-iteration-dependent values.

4. **Quantization descriptor representation**: The NEM spec mentions `quant` attributes with `(scale, zero_point)` or per-channel variants. The exact syntax for quantization descriptors in NEM source text needs to be finalized (it is not fully specified in the current grammar — the `quant_desc` production is referenced but not expanded).
