"""
Conformance: Opcode Registry well-formedness and cross-reference checks.
Spec reference: Opcode Signatures (Normative) — spec/registry/opcodes.yaml
"""
import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "spec" / "registry" / "opcodes.yaml"
SCHEMA_PATH = REPO_ROOT / "spec" / "registry" / "schema.json"
BASELINE_PATH = REPO_ROOT / "examples" / "npm_baseline_1.0.nem"
EXAMPLES_DIR = REPO_ROOT / "examples"


@pytest.fixture(scope="module")
def registry():
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def baseline_type_families():
    """Extract type_family names from the baseline device file."""
    families = set()
    with open(BASELINE_PATH) as f:
        for line in f:
            m = re.match(r"\s*type_family\s+([\w.]+)", line)
            if m:
                families.add(m.group(1))
    return families


@pytest.fixture(scope="module")
def example_opcodes():
    """Extract opcode names used in .nem example files."""
    opcodes = set()
    pattern = re.compile(r"\b(\w+)\.(async|sync)\b")
    for nem_file in EXAMPLES_DIR.glob("*.nem"):
        with open(nem_file) as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    opcodes.add(m.group(1))
    return opcodes


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_registry_loads(registry):
    """Registry YAML parses successfully."""
    assert registry is not None
    assert "version" in registry
    assert "opcodes" in registry


def test_registry_version_format(registry):
    """Version follows MAJOR.MINOR format."""
    assert re.match(r"^\d+\.\d+$", registry["version"])


def test_registry_has_opcodes(registry):
    """Registry contains at least one opcode."""
    assert len(registry["opcodes"]) > 0


def test_no_empty_opcode_names(registry):
    """No empty-string opcode names."""
    for name in registry["opcodes"]:
        assert name.strip() != "", f"Empty opcode name found"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_schema_validation(registry, schema):
    """Registry validates against JSON Schema."""
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    jsonschema.validate(registry, schema)


# ---------------------------------------------------------------------------
# Per-opcode structural tests
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "data_movement", "linear_algebra", "convolution",
    "elementwise_unary", "elementwise_binary", "elementwise_other",
    "pooling", "layout", "reduction", "normalization",
    "softmax", "type_conversion", "generic",
}

VALID_STATUSES = {"stable", "provisional", "future"}
VALID_FORMS = {"async", "sync"}
VALID_DIRECTIONS = {"in", "out"}
VALID_ATTR_TYPES = {"int", "float", "bool", "elem_type", "int_list", "string", "id"}


@pytest.fixture(scope="module")
def opcode_items(registry):
    return list(registry["opcodes"].items())


def test_all_opcodes_have_valid_category(opcode_items):
    for name, defn in opcode_items:
        assert defn["category"] in VALID_CATEGORIES, \
            f"{name}: invalid category '{defn['category']}'"


def test_all_opcodes_have_valid_status(opcode_items):
    for name, defn in opcode_items:
        assert defn["status"] in VALID_STATUSES, \
            f"{name}: invalid status '{defn['status']}'"


def test_all_opcodes_have_valid_forms(opcode_items):
    for name, defn in opcode_items:
        for form in defn["forms"]:
            assert form in VALID_FORMS, \
                f"{name}: invalid form '{form}'"


def test_all_opcodes_have_in_operand(opcode_items):
    for name, defn in opcode_items:
        directions = {op["direction"] for op in defn["operands"]}
        assert "in" in directions, f"{name}: no 'in' operand"


def test_all_opcodes_have_out_operand(opcode_items):
    for name, defn in opcode_items:
        directions = {op["direction"] for op in defn["operands"]}
        assert "out" in directions, f"{name}: no 'out' operand"


def test_operand_directions_valid(opcode_items):
    for name, defn in opcode_items:
        for op in defn["operands"]:
            assert op["direction"] in VALID_DIRECTIONS, \
                f"{name}.{op['name']}: invalid direction '{op['direction']}'"


def test_attribute_types_valid(opcode_items):
    for name, defn in opcode_items:
        for attr in defn.get("attributes", []):
            assert attr["type"] in VALID_ATTR_TYPES, \
                f"{name}.{attr['name']}: invalid attribute type '{attr['type']}'"


def test_optional_attributes_have_defaults(opcode_items):
    """Non-required attributes should have a default value."""
    for name, defn in opcode_items:
        for attr in defn.get("attributes", []):
            if not attr["required"]:
                assert "default" in attr, \
                    f"{name}.{attr['name']}: optional attribute missing 'default'"


# ---------------------------------------------------------------------------
# Cross-reference tests
# ---------------------------------------------------------------------------

def test_type_family_references_valid(opcode_items, baseline_type_families):
    """All type_family references resolve to families in the baseline device file."""
    for name, defn in opcode_items:
        for family in defn.get("type_families", []):
            assert family in baseline_type_families, \
                f"{name}: type_family '{family}' not found in baseline " \
                f"(available: {sorted(baseline_type_families)})"


def test_example_opcodes_in_registry(registry, example_opcodes):
    """Every opcode used in example .nem files has a registry entry."""
    registry_names = set(registry["opcodes"].keys())
    # Some names in examples may be compound (e.g., transfer, store, compute)
    for opcode in example_opcodes:
        assert opcode in registry_names, \
            f"Opcode '{opcode}' used in examples but missing from registry"


# ---------------------------------------------------------------------------
# Category coverage tests
# ---------------------------------------------------------------------------

def test_all_categories_populated(registry):
    """Every defined category has at least one opcode."""
    categories_used = {defn["category"] for defn in registry["opcodes"].values()}
    for cat in VALID_CATEGORIES:
        assert cat in categories_used, f"Category '{cat}' has no opcodes"


# ---------------------------------------------------------------------------
# Opcode count sanity
# ---------------------------------------------------------------------------

def test_minimum_opcode_count(registry):
    """Registry should have at least 40 opcodes (spec defines ~45+)."""
    assert len(registry["opcodes"]) >= 40, \
        f"Expected >= 40 opcodes, got {len(registry['opcodes'])}"
