# Conformance Tests

Conformance tests define **language correctness**. They are the shared truth that all tools must satisfy.

## Purpose

- Validate that tool implementations match the NEM spec.
- Provide regression coverage for semantic behavior.
- Act as the canonical reference when tools disagree.

## Test Format

Each conformance test is a directory under `tests/conformance/` organized by feature area:

```
tests/conformance/
  memory/
    test_ddr_load_store.py
    test_l2_transfer.py
  compute/
    test_nmu_matmul.py
  tasks/
    test_task_graph_basic.py
  ...
```

### Test File Structure

Tests are written in Python using `pytest`:

```python
"""
Conformance: <feature area> - <specific behavior>
Spec reference: <section number or name from nem_spec.md>
"""

def test_<behavior_name>():
    """<One-line description of what is being validated>."""
    # Setup
    # Execute
    # Assert deterministic expected result
```

### Rules

- Each test must reference the spec section it validates.
- Expected results must be deterministic and documented.
- Tests must not depend on tool-internal implementation details.
- Tests should be additive — avoid modifying existing passing tests.
- Tag tests with capability markers if they require specific features:

```python
import pytest

@pytest.mark.capability("timed_mode")
def test_resource_contention():
    ...
```

## Running Tests

```bash
pytest tests/conformance/ -v
```

To run a specific feature area:

```bash
pytest tests/conformance/memory/ -v
```

## Adding Tests

1. Identify the spec section being tested.
2. Create or extend a test file in the appropriate feature directory.
3. Follow the naming convention: `test_<feature>_<behavior>.py`.
4. Ensure the test is self-contained and deterministic.
