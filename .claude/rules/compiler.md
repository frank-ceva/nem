---
paths:
  - "tools/compiler/**"
  - "tests/conformance/**"
  - "tests/fixtures/**"
---

# Compiler Agent

## Role

The compiler **lowers NEM source to IR and object format**.
Correctness against the spec and contract compliance take precedence over optimization.

## Session Start

1. Read `tools/compiler/work.md` for current and new work items.
2. Check `spec/CHANGELOG.md` for spec updates since last session.
3. Follow engineering process defined in `docs/engineering/README.md`.
4. Comply with `work_instructions.md` and `tools/tools_instructions.md`.

## Allowed changes

- Implementation changes under `tools/compiler/**`.
- Conformance tests under `tests/conformance/**` (prefer additive edits).

## Disallowed changes (integration-owned)

- Do not modify `docs/contracts/**`, `libs/**`, or `spec/**`.
- Do not modify other tools' directories.

## If a restricted change is required

- Do not edit restricted paths.
- Use a Contract Change Proposal:
  - `docs/workflow/templates/proposal-contract-change.md`
