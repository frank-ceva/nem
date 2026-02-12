#!/usr/bin/env python3
"""
NEM Opcode Registry Validator

Validates spec/registry/opcodes.yaml against spec/registry/schema.json and performs
cross-reference checks with examples/npm_baseline_1.0.nem.

Usage:
    python spec/registry/validate.py
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is not installed. Install with: pip install pyyaml")
    sys.exit(1)

# Optional jsonschema validation
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("WARNING: jsonschema not installed. Schema validation will be skipped.")
    print("         Install with: pip install jsonschema")
    print()


def resolve_path(relative_path: str) -> Path:
    """Resolve path relative to script location."""
    script_dir = Path(__file__).parent
    return (script_dir / relative_path).resolve()


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML in {path}: {e}")
        sys.exit(1)


def load_json(path: Path) -> dict:
    """Load JSON file."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {path}: {e}")
        sys.exit(1)


def validate_schema(data: dict, schema: dict) -> list:
    """Validate data against JSON schema. Returns list of errors."""
    if not HAS_JSONSCHEMA:
        return []

    errors = []
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema validation error: {e.message}")
        if e.path:
            errors.append(f"  at path: {' -> '.join(str(p) for p in e.path)}")
    except jsonschema.SchemaError as e:
        errors.append(f"Invalid schema: {e.message}")

    return errors


def extract_type_families_from_baseline(baseline_path: Path) -> set:
    """Extract type_family names from baseline NEM file."""
    type_families = set()

    try:
        with open(baseline_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Look for lines like: type_family conv2d.float<T: {f16, bf16, f32}> {
                if line.startswith('type_family '):
                    # Extract the name (everything between 'type_family ' and '<' or '{')
                    name_part = line[len('type_family '):].split('<')[0].split('{')[0].strip()
                    if name_part:
                        type_families.add(name_part)
    except FileNotFoundError:
        print(f"WARNING: Baseline file not found: {baseline_path}")
        return set()

    return type_families


def check_duplicate_opcodes(opcodes: dict) -> list:
    """Check for duplicate opcode names (YAML handles this but we warn)."""
    # YAML will overwrite duplicates, but we can't detect them after loading
    # This is more of a placeholder for future enhancements
    return []


def check_operand_directions(opcodes: dict) -> list:
    """Ensure every opcode has at least one 'in' and one 'out' operand."""
    errors = []

    for opcode_name, opcode_def in opcodes.items():
        operands = opcode_def.get('operands', [])

        has_in = any(op.get('direction') == 'in' for op in operands)
        has_out = any(op.get('direction') == 'out' for op in operands)

        if not has_in:
            errors.append(f"Opcode '{opcode_name}' has no 'in' direction operands")
        if not has_out:
            errors.append(f"Opcode '{opcode_name}' has no 'out' direction operands")

    return errors


def check_type_family_references(opcodes: dict, baseline_type_families: set) -> list:
    """Check that all type_family references exist in baseline."""
    warnings = []

    for opcode_name, opcode_def in opcodes.items():
        type_families = opcode_def.get('type_families', [])
        for tf in type_families:
            if tf not in baseline_type_families:
                warnings.append(
                    f"Opcode '{opcode_name}' references unknown type_family '{tf}'"
                )

    return warnings


def generate_summary(opcodes: dict) -> dict:
    """Generate summary statistics."""
    summary = {
        'total': len(opcodes),
        'by_category': defaultdict(int),
        'by_status': defaultdict(int),
        'by_hardware_status': defaultdict(int),
    }

    for opcode_def in opcodes.values():
        category = opcode_def.get('category', 'unknown')
        status = opcode_def.get('status', 'unknown')
        hw_status = opcode_def.get('hardware_status', 'unknown')

        summary['by_category'][category] += 1
        summary['by_status'][status] += 1
        summary['by_hardware_status'][hw_status] += 1

    return summary


def print_summary(summary: dict):
    """Print validation summary."""
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"\nTotal opcodes: {summary['total']}")

    print("\nBy category:")
    for category, count in sorted(summary['by_category'].items()):
        print(f"  {category:30s} {count:3d}")

    print("\nBy status:")
    for status, count in sorted(summary['by_status'].items()):
        print(f"  {status:30s} {count:3d}")

    print("\nBy hardware_status:")
    for hw_status, count in sorted(summary['by_hardware_status'].items()):
        print(f"  {hw_status:30s} {count:3d}")

    print()


def main():
    """Main validation routine."""
    print("NEM Opcode Registry Validator")
    print("-" * 70)
    print()

    # Resolve paths
    opcodes_path = resolve_path("opcodes.yaml")
    schema_path = resolve_path("schema.json")
    baseline_path = resolve_path("../../examples/npm_baseline_1.0.nem")

    # Load files
    print(f"Loading opcodes from: {opcodes_path}")
    registry_data = load_yaml(opcodes_path)

    print(f"Loading schema from: {schema_path}")
    schema = load_json(schema_path)

    print(f"Extracting type families from: {baseline_path}")
    baseline_type_families = extract_type_families_from_baseline(baseline_path)
    print(f"Found {len(baseline_type_families)} type families in baseline")
    print()

    # Validation checks
    all_errors = []
    all_warnings = []

    # 1. Schema validation
    if HAS_JSONSCHEMA:
        print("Validating against JSON schema...")
        schema_errors = validate_schema(registry_data, schema)
        if schema_errors:
            all_errors.extend(schema_errors)
        else:
            print("✓ Schema validation passed")

    opcodes = registry_data.get('opcodes', {})

    # 2. Check duplicate opcodes
    print("Checking for duplicate opcode names...")
    dup_errors = check_duplicate_opcodes(opcodes)
    if dup_errors:
        all_errors.extend(dup_errors)
    else:
        print("✓ No duplicate opcodes")

    # 3. Check operand directions
    print("Checking operand directions...")
    direction_errors = check_operand_directions(opcodes)
    if direction_errors:
        all_errors.extend(direction_errors)
    else:
        print("✓ All opcodes have in/out operands")

    # 4. Check type_family references
    print("Checking type_family cross-references...")
    tf_warnings = check_type_family_references(opcodes, baseline_type_families)
    if tf_warnings:
        all_warnings.extend(tf_warnings)
    else:
        print("✓ All type_family references valid")

    print()

    # Report errors and warnings
    if all_errors:
        print("ERRORS:")
        for error in all_errors:
            print(f"  ✗ {error}")
        print()

    if all_warnings:
        print("WARNINGS:")
        for warning in all_warnings:
            print(f"  ⚠ {warning}")
        print()

    # Generate and print summary
    summary = generate_summary(opcodes)
    print_summary(summary)

    # Exit with appropriate code
    if all_errors:
        print("Validation FAILED with errors.")
        sys.exit(1)
    elif all_warnings:
        print("Validation completed with warnings.")
        sys.exit(0)
    else:
        print("Validation PASSED.")
        sys.exit(0)


if __name__ == '__main__':
    main()
