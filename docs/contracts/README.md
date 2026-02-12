# Contracts

Contracts define the **shared interfaces** between tools in the NEM toolchain. They are integration-owned and must not be modified by tool agents directly.

## Contract Inventory

| Contract | File | Status | Description |
|----------|------|--------|-------------|
| IR Schema | `ir-schema.md` | TBD | Intermediate representation format between compiler and binder |
| Object/Bytecode Format | `object-format.md` | TBD | Binary format for encoded programs consumed by the simulator |
| CLI Contract | `cli-contract.md` | TBD | Command-line interface conventions shared across tools |
| Diagnostics Contract | `diagnostics-contract.md` | TBD | Error/warning message format and severity levels |
| Opcode Registry | `opcode-registry.md` | Active | Machine-readable opcode signatures, operands, and attributes |

## Versioning

Each contract document contains a version field. Versions follow `MAJOR.MINOR` format:

- **MAJOR** bump: breaking change (tools must update).
- **MINOR** bump: additive change (backward compatible).

## Proposing Changes

Tool agents must not edit contracts directly. To request a change:

1. Fill out the template at `docs/workflow/templates/proposal-contract-change.md`.
2. Add the proposal as a work item in `spec-int-work.md`.
3. The integration agent will review, update contracts, and propagate changes.

## Related

- Engineering process: `docs/engineering/spec-int-dev-process.md`
- Proposal template: `docs/workflow/templates/proposal-contract-change.md`
