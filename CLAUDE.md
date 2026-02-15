# Project-wide Claude Code Baseline (Monorepo)

You are working in a monorepo that defines a language (NEM) and its toolchain:
- spec — language specification and opcode registry
- contracts — IR schema, object format, CLI, diagnostics (TBD)
- interpreter — reference implementation (Python)
- compiler — MLIR-based lowering to IR (C++)
- binder — lowers IR to hardware-specific TCBs (Rust)
- simulator — cycle-accurate execution model (TBD)
- shared library (nemlib) — parser, type system, device model, validation
- shared tests and infrastructure

You MUST comply with guidelines defined in @work_instructions.md (if you are running at the top directory, i.e. dealing with the spec and integration, replace work.md by spec-int-work.md) and @tools/tools_instructions.md and also enforce engineering process defined in the engineering directory, using @docs/engineering/README.md as an entry point.

## Agent Model

Six agent roles operate in this monorepo. Each agent works on its own branch and communicates through work items and PRs.

| Agent | Owns | Work items file | Branch |
|-------|------|----------------|--------|
| **Integration** | `spec/`, `docs/contracts/`, coordination, validation | `spec-int-work.md` | `integration/main` |
| **Shared** | `libs/`, `tests/`, `examples/`, root `Makefile`, root `pyproject.toml` | `libs/work.md` | `agent/shared/main` |
| **Interpreter** | `tools/interpreter/` | `tools/interpreter/work.md` | `agent/interpreter/main` |
| **Compiler** | `tools/compiler/` | `tools/compiler/work.md` | `agent/compiler/main` |
| **Binder** | `tools/binder/` | `tools/binder/work.md` | `agent/binder/main` |
| **Simulator** | `tools/simulator/` | `tools/simulator/work.md` | `agent/simulator/main` |

### Delegation protocol

- **To delegate work to an agent**: Add a work item to their `work.md` file.
- **To request changes to integration-owned areas** (`spec/`, `docs/contracts/`): Use a Contract Change Proposal (`docs/workflow/templates/proposal-contract-change.md`) and add a work item to `spec-int-work.md`.
- **To request changes to shared areas** (`libs/`, `tests/`): Use a Contract Change Proposal and add a work item to `libs/work.md`.

### Agent scoping

Each agent has path-scoped rules in `.claude/rules/` that define its role, allowed modifications, and session protocol. These rules auto-load when editing files in the agent's owned directories.

See `docs/engineering/general-dev-process.md` for the full inter-agent communication protocol.

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
See `docs/ext/README.md` for external documentation needed to design NEM specifications and software.
See `docs/engineering/decisions/` for architecture decision records.
