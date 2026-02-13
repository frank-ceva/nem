# Phase 1: Test Plan

## Overview

Testing uses a two-tier conformance architecture with a pluggable runner protocol. The same conformance tests run against the interpreter today and against the compiler+binder+simulator pipeline in the future.

## Architecture

### Two Tiers

| Tier | Purpose | Format | Current Coverage |
|------|---------|--------|-----------------|
| **Validation** | Is this NEM source accepted/rejected? | NEM source + expected outcome ("valid" or "error: ...") | const/ (32), device_config/ (4 files), opcodes/ (3 files), types/ (3 files), registry/ (1 file) |
| **Execution** | Given inputs, does execution produce correct outputs? | NEM source + device config + .npy input data + .npy expected output | New — to be created |

### ConformanceRunner Protocol

```python
# tests/conformance/runner.py

from dataclasses import dataclass, field
from typing import Protocol
import numpy as np

@dataclass
class ValidationResult:
    valid: bool
    diagnostics: list[str] = field(default_factory=list)

@dataclass
class ExecutionResult:
    outputs: dict[str, np.ndarray] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

class ConformanceRunner(Protocol):
    """Tool-agnostic interface for conformance testing."""
    name: str

    def validate(self, source: str, device_config: str | None = None) -> ValidationResult:
        """Parse and validate a NEM program."""
        ...

    def execute(
        self, source: str, device_config: str | None,
        inputs: dict[str, np.ndarray]
    ) -> ExecutionResult:
        """Execute a NEM program with given inputs."""
        ...
```

### Runner Implementations

```
tests/conformance/
  runner.py                         # Protocol + result types
  runners/
    __init__.py
    interpreter_runner.py           # Uses nemlib + neminterp
    pipeline_runner.py              # Uses compiler + binder + simulator (future)
  conftest.py                       # Pytest fixture: parametrize by runner
```

**InterpreterRunner** (Phase 1):
```python
# tests/conformance/runners/interpreter_runner.py

class InterpreterRunner:
    name = "interpreter"

    def validate(self, source, device_config=None):
        diag = DiagnosticCollector()
        ast = parse(source, diag)
        if not diag.has_errors():
            validate(ast, device, diag)
        return ValidationResult(valid=not diag.has_errors(),
                                diagnostics=[d.message for d in diag.get_all()])

    def execute(self, source, device_config, inputs):
        interp = NemInterpreter()
        interp.load(source, device_config)
        outputs = interp.run(inputs)
        return ExecutionResult(outputs=outputs)
```

**PipelineRunner** (future, Phase 2+):
```python
class PipelineRunner:
    name = "pipeline"

    def validate(self, source, device_config=None):
        # compiler validates during lowering
        ...

    def execute(self, source, device_config, inputs):
        ir = compiler.compile(source, device_config)
        tcb = binder.bind(ir, device_config)
        outputs = simulator.execute(tcb, inputs)
        return ExecutionResult(outputs=outputs)
```

### Pytest Fixture

```python
# tests/conformance/conftest.py

from tests.conformance.runners.interpreter_runner import InterpreterRunner

def get_available_runners():
    runners = [InterpreterRunner()]
    try:
        from tests.conformance.runners.pipeline_runner import PipelineRunner
        runners.append(PipelineRunner())
    except ImportError:
        pass
    return runners

@pytest.fixture(params=get_available_runners(), ids=lambda r: r.name)
def runner(request):
    return request.param
```

## Directory Structure

```
tests/
  conformance/
    runner.py                       # ConformanceRunner protocol
    conftest.py                     # Runner fixture
    runners/
      __init__.py
      interpreter_runner.py
    const/                          # Validation tier (existing, 10 files, 32 cases)
      test_basic_const.py
      test_derived_const.py
      ...
    device_config/                  # Validation tier (existing, 4 files)
      test_device_units.py
      ...
    opcodes/                        # Validation tier (existing, 3 files)
      test_activations.py
      ...
    types/                          # Validation tier (existing, 3 files)
      test_quant_descriptors.py
      ...
    registry/                       # Validation tier (existing, 1 file)
      test_registry.py
    execution/                      # Execution tier (NEW)
      conftest.py                   # Execution-specific fixtures (load .npy)
      transfer_basic/               # Step 3 milestone
        program.nem
        inputs/ *.npy
        expected/ *.npy
        test_transfer.py
      conv2d_relu/                  # Step 5 milestone
        program.nem
        device.nem
        inputs/ *.npy
        expected/ *.npy
        test_conv2d_relu.py
      gemm_bias_relu/               # Step 5 milestone
        ...
      conv2d_maxpool/               # Step 7 milestone
        ...
      gemm_rmsnorm/                 # Step 7 milestone
        ...
```

## Validation Test Refactoring

Existing conformance test stubs (currently `pass` bodies) are refactored to call `runner.validate()`:

```python
# Example: tests/conformance/const/test_basic_const.py

CASES = [
    ("integer_literal", 'program t:\nconst X = 42\n', "valid"),
    ("negative_literal", 'program t:\nconst X = -1\n', "valid"),
    ...
]

@pytest.mark.parametrize("description,source,expected", CASES, ids=[c[0] for c in CASES])
def test_basic_const(runner, description, source, expected):
    result = runner.validate(source)
    if expected == "valid":
        assert result.valid, f"Expected valid: {result.diagnostics}"
    else:
        assert not result.valid
        error_text = expected.removeprefix("error: ")
        assert any(error_text in d for d in result.diagnostics), \
            f"Expected '{error_text}' in diagnostics: {result.diagnostics}"
```

## Execution Test Data Format

Each execution test is a directory containing:

| File | Purpose |
|------|---------|
| `program.nem` | NEM source program |
| `device.nem` | Device configuration (optional) |
| `inputs/*.npy` | Input buffer data as NumPy arrays |
| `expected/*.npy` | Expected output buffer data as NumPy arrays |
| `test_*.py` | Pytest test file |
| `metadata.json` | Optional: tolerances, buffer-to-region mapping |

**Input/output naming convention**: Files are named after the L2 buffer they populate/check: `X_L2.npy`, `W_L2.npy`, `Y_L2.npy`, etc.

**Data generation**: A helper script generates .npy fixture data from known-good NumPy reference computations. This script runs once to create fixtures, not during testing.

```python
# Example: tests/conformance/execution/conv2d_relu/test_conv2d_relu.py

def test_conv2d_relu_execution(runner):
    source = Path(__file__).parent / "program.nem"
    device = Path(__file__).parent / "device.nem"
    inputs = load_npy_dir(Path(__file__).parent / "inputs")
    expected = load_npy_dir(Path(__file__).parent / "expected")

    result = runner.execute(source.read_text(), device.read_text(), inputs)

    for name, expected_array in expected.items():
        assert name in result.outputs, f"Missing output: {name}"
        np.testing.assert_allclose(result.outputs[name], expected_array,
                                   rtol=1e-5, atol=1e-6)
```

## Per-Step Test Plan

### Step 1

- **nemlib unit tests**: lexer (all token types), parser (const declarations, all expression operators), diagnostics (collector, formatting)
- **Conformance infra**: runner.py, conftest.py, interpreter_runner.py (validate-only initially)
- **Validation tests**: Wire up const/ (32 cases)

### Step 2

- **nemlib unit tests**: parser (buffer declarations, region/let declarations, type attributes, quant descriptors, decorators)
- **Interpreter unit tests**: memory model (alloc, read, write), buffer manager (alignment, bounds), region (typed view, i4 packing)

### Step 3

- **nemlib unit tests**: parser (task statements, wait, deps, inline regions)
- **Interpreter unit tests**: token manager, task graph (DAG construction, ready tasks), scheduler, executor (transfer, store, wait)
- **Execution tests**: First execution tier tests — synthetic transfer programs

### Step 4

- **nemlib unit tests**: parser (loop, max_in_flight)
- **Interpreter unit tests**: loop iteration, variable binding, max_in_flight enforcement, ping-pong indexing
- **Execution tests**: Loop + transfer programs

### Step 5

- **nemlib unit tests**: parser (compute tasks), opcode registry loading
- **Interpreter unit tests**: per-opcode tests (all elementwise, gemm, matmul, conv2d) with known input/output
- **Validation tests**: Wire up opcodes/ stubs
- **Execution tests**: conv2d_relu, gemm_bias_relu end-to-end

### Step 6

- **nemlib unit tests**: parser (device config syntax), device resolver (inheritance, merge, effective set)
- **Validation tests**: Wire up device_config/ (4 files), registry/ (1 file)
- **Integration tests**: Parse + resolve npm_baseline_1.0.nem and npm_lite_.nem

### Step 7

- **Interpreter unit tests**: per-opcode tests for all remaining ops (pooling, norm, softmax, layout, cast, quantize, dequantize)
- **Validation tests**: Wire up remaining opcodes/ and types/ stubs
- **Execution tests**: conv2d_maxpool, gemm_rmsnorm end-to-end

### Step 8

- **nemlib unit tests**: type family matching (all MUST + MAY variants), per-pass validation tests
- **Validation tests**: error programs (one per validation pass), decorator validation
- **Execution tests**: All examples with full validation enabled
- **Regression**: All previous tests remain green
