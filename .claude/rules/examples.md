---
paths:
  - "examples/**"
---

# Example Programs

## Ownership

Example NEM programs are owned by the shared agent. They serve as end-to-end test targets and documentation of language features.

## Guidelines

- Examples must remain valid NEM programs as the grammar evolves.
- Each example should demonstrate a distinct language feature or pattern.
- Examples are used as parsing targets in Phase 1 (all examples must lex/parse without errors).
- Examples are used as execution targets in later phases (must produce correct output).

## Allowed changes

- Adding new example programs.
- Updating existing examples to match grammar changes.

## Disallowed changes

- Do not modify `spec/**`, `docs/contracts/**`, or `tools/**`.
