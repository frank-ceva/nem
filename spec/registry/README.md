# NEM Opcode Registry

Machine-readable registry of all NEM opcode signatures, operands, and attributes.

## Files

| File | Purpose |
|------|---------|
| `opcodes.yaml` | Normative opcode definitions (single source of truth) |
| `schema.json` | JSON Schema for validating `opcodes.yaml` |
| `validate.py` | Validation script (schema + cross-reference checks) |

## Usage

### Validate the registry

```bash
python spec/registry/validate.py
```

### Consume from Python

```python
import yaml

with open("spec/registry/opcodes.yaml") as f:
    registry = yaml.safe_load(f)

# Look up an opcode
gemm = registry["opcodes"]["gemm"]
print(gemm["category"])       # "linear_algebra"
print(gemm["operands"])       # [{name: "A", ...}, ...]
print(gemm["type_families"])  # ["gemm.float", "gemm.int8", "gemm.int4"]
```

## Schema

See `schema.json` for the full schema. Each opcode entry contains:

- **category** — classification (linear_algebra, elementwise_unary, etc.)
- **status** — stable, provisional, or future
- **forms** — async, sync, or both
- **operands** — list of input/output operands with roles and constraints
- **attributes** — list of static parameters with types and defaults
- **type_families** — references to type family names in the baseline device file
- **execution_unit** — primary NPM hardware unit (NMU, CSTL, DMA, etc.)
- **hardware_status** — current NPM hardware support level

## Normative Status

This registry is normative and referenced by the NEM specification. Changes follow the contract change process described in `docs/contracts/opcode-registry.md`.
