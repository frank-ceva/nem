---
paths:
  - "tools/simulator/**"
  - "tests/conformance/**"
  - "tests/fixtures/**"
---

# Simulator Agent

## Role

The simulator **executes encoded NEM programs on a modeled hardware target**.
Correctness against the spec and cycle-accurate behavior take precedence over host performance.

## Session Start

1. Read `tools/simulator/work.md` for current and new work items.
2. Check `spec/CHANGELOG.md` for spec updates since last session.
3. Follow engineering process defined in `docs/engineering/README.md`.
4. Comply with `work_instructions.md` and `tools/tools_instructions.md`.

## Allowed changes

- Implementation changes under `tools/simulator/**`.
- Conformance tests under `tests/conformance/**` (prefer additive edits).

## Disallowed changes (integration-owned)

- Do not modify `docs/contracts/**`, `libs/**`, or `spec/**`.
- Do not modify other tools' directories.

## If a restricted change is required

- Do not edit restricted paths.
- Use a Contract Change Proposal:
  - `docs/workflow/templates/proposal-contract-change.md`
