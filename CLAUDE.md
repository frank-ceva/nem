# Project-wide Claude Code Baseline (Monorepo)

You are working in a monorepo that defines a language and its toolchain:
- spec
- contracts
- interpreter
- compiler
- binder
- simulator
- shared tests and infrastructure

You MUST comply with guidelines defined in @work_instructions.md (if you are running at the top directory, i.e. dealing with the spec and integration, replace work.md by spec-int-work.md) and @tools/tools_instructions.md and also enforce engineering process defined in the engineering directory, using @docs/engineering/README.md as an entry point.

## Core Principles

- Keep changes within your assigned component scope.
- Treat `docs/contracts/**`, `libs/**`, and normative `spec/**` as integration-owned.
- If you need to change an integration-owned area, produce a **Contract Change Proposal** instead of editing directly.
  - Template: `docs/workflow/templates/proposal-contract-change.md`

## Testing

- Run tool-local tests for your component.
- Add conformance tests for semantic behavior changes.

## References

See `docs/engineering/README.md` for operational guidance.
See `docs/ext/README.md`for external documentation needed to design NEM specifications and software
