# Opcode Registry Contract

**Version:** 1.0
**Status:** Active
**Location:** `spec/registry/opcodes.yaml`

## Purpose

The opcode registry is the single source of truth for NEM opcode signatures — operand structure, attributes, type family associations, and hardware support status. The NEM specification (`spec/nem_spec.md`) references this registry normatively rather than inlining opcode definitions.

## Normative Status

The registry is **normative**. Tools MUST treat it as authoritative for:

- Which opcodes exist and their names
- Operand count, direction (in/out), and optionality per opcode
- Required and optional attributes with types and defaults
- Type family associations (which type families govern each opcode's type legality)
- Hardware support status (supported, future, partial, escape_hatch)

The NEM specification retains ownership of **semantic rules** (type promotion, broadcasting, execution ordering, memory model) that apply across all opcodes.

## Schema

The registry schema is defined in `spec/registry/schema.json` (JSON Schema draft 2020-12). All entries in `opcodes.yaml` MUST validate against this schema.

Validation: `python3 spec/registry/validate.py`

## Structure

```yaml
version: "1.0"
opcodes:
  <opcode_name>:
    category: <enum>          # data_movement, linear_algebra, convolution, ...
    status: <enum>            # stable, provisional, future
    forms: [async, sync]      # supported execution forms
    operands:                 # ordered list of operands
      - name: <string>
        direction: in | out
        required: <boolean>
        role: <string>        # human-readable role description
        constraints: <string> # optional shape/rank constraints
    attributes:               # optional; omit if opcode has no attributes
      - name: <string>
        type: <enum>          # int, float, bool, elem_type, int_list, string, id
        required: <boolean>
        default: <value>      # optional; only if not required
        description: <string> # optional
    type_families: [<string>] # optional; references to baseline type families
    execution_unit: <enum>    # optional; NMU, CSTL, DMA, sDMA, VPU, SEQ, varies
    hardware_status: <enum>   # optional; supported, future, partial, escape_hatch
    notes: <string>           # optional
    variadic_inputs: <bool>   # optional; true if variable input count (e.g., concat)
    variadic_outputs: <bool>  # optional; true if variable output count (e.g., split)
```

## How Tools Consume the Registry

Tools load `spec/registry/opcodes.yaml` at initialization and use it for:

| Tool | Usage |
|------|-------|
| **Interpreter** | Semantic validation (attribute types, operand counts), opcode dispatch |
| **Compiler** | Opcode signature validation during lowering, type family resolution |
| **Binder** | Execution unit routing, operand validation |
| **Simulator** | Opcode dispatch, attribute validation |
| **VSCode Extension** | Syntax highlighting keyword generation (replace hardcoded regex) |
| **Conformance Tests** | Parameterized test generation from opcode metadata |

### Python example

```python
import yaml
from pathlib import Path

registry_path = Path(__file__).resolve().parents[1] / "spec" / "registry" / "opcodes.yaml"
with open(registry_path) as f:
    registry = yaml.safe_load(f)

def get_opcode(name: str) -> dict:
    return registry["opcodes"][name]

def get_required_attributes(name: str) -> list[str]:
    opcode = get_opcode(name)
    return [a["name"] for a in opcode.get("attributes", []) if a["required"]]
```

## Change Process

This contract is **integration-owned**. Tool agents MUST NOT modify registry files directly.

To propose changes:
1. File a Contract Change Proposal using `docs/workflow/templates/proposal-contract-change.md`.
2. The integration agent will review, update the registry, and propagate changes to tool work queues.

## Versioning

The registry `version` field follows `MAJOR.MINOR`:
- **MAJOR** bump: breaking change (opcode removed, operand semantics changed, attribute renamed).
- **MINOR** bump: additive change (new opcode added, new optional attribute, status change).
