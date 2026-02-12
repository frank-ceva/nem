# Project-wide Claude Code Baseline (Monorepo)

You are working in a monorepo that defines a language and its toolchain:
- spec
- contracts
- interpreter
- compiler
- binder
- simulator
- shared tests and infrastructure

## Core Principles

- Keep changes within your assigned component scope.
- Treat `docs/contracts/**`, `libs/**`, and normative `spec/**` as integration-owned.
- If you need to change an integration-owned area, produce a **Contract Change Proposal** instead of editing directly.
  - Template: `docs/workflow/templates/proposal-contract-change.md`

## Testing

- Run tool-local tests for your component.
- Add conformance tests for semantic behavior changes.

## Software engineering

See `docs/engineering/README.md` for operational guidance.
