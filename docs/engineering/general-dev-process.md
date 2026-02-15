# General Development Process

This document defines the overall engineering model of the repository and clarifies the distinction between **project-wide work** and **subproject work**.

---

## 1. Two Levels of Engineering Work

### A. Project-Wide Engineering

Project-wide work affects multiple tools or defines shared behavior. It is split across two agents:

**Spec, contracts, and integration validation** (owned by Integration agent):

* Language semantics and spec evolution
* Contracts (IR, object format, CLI, diagnostics)
* Cross-tool integration validation (running tests, verifying consistency)
* Release coordination
* Merge decisions for `integration/main`

The integration agent does not write production code. It validates, coordinates, and reports failures.

**Shared libraries and infrastructure** (owned by Shared agent):

* Shared library development (`libs/nemlib-py/`)
* Test infrastructure (conformance runner framework, fixtures)
* Build infrastructure (`Makefile`, `pyproject.toml` files)
* Conformance test implementation (wiring test stubs to runner calls)
* Example programs (`examples/`)

The shared agent builds shared code, subject to integration agent review.

---

### B. Subproject Engineering

Scope:

* Implementation of a specific tool:

  * Interpreter
  * Compiler
  * Binder
  * Simulator
* Internal refactors
* Performance improvements
* Tool-local bug fixes

Owned by:

* Tool agent, one agent per tool

Subproject work must respect contracts and the overall engineering model.

---

## 2. Determining Work Type

Before starting, classify the change:

* Does it affect language semantics or shared contracts?
  → Follow `spec-int-dev-process.md`

* Is it internal to a single tool and does not change externally observable behavior?
  → Follow `tool-dev-process.md`

If unsure, escalate to the manager.

---

## 3. Shared Global Rules

Each agent works on its own branch. For each feature, the agent creates a feature branch, merges it into its agent branch when validated, and then opens a PR to `integration/main`.

Applies to all work:

* Respect scope boundaries.
* Do not modify integration-owned areas without proposal.
* Keep `main` green.
* Ensure deterministic tests.
* No undocumented semantic decisions.

---

## 4. Inter-Agent Communication Protocol

Agents work in isolated clones (or worktrees). The following protocol ensures coordination without direct communication. All inter-agent coordination flows through committed files and GitHub PRs.

### Tool Agent → Integration Agent

When a tool agent needs a change to integration-owned areas (contracts, spec):

1. Fill out a Contract Change Proposal using `docs/workflow/templates/proposal-contract-change.md`.
2. Add a work item entry to `spec-int-work.md` referencing the proposal.
3. Continue working on non-blocked tasks.

### Tool Agent → Shared Agent

When a tool agent needs a change to shared libraries (`libs/`), tests, or examples:

1. Fill out a Contract Change Proposal using `docs/workflow/templates/proposal-contract-change.md`.
2. Add a work item entry to `libs/work.md` (or `spec-int-work.md` if the change also affects spec).
3. Continue working on non-blocked tasks.

### Integration Agent → Tool Agents / Shared Agent

When a spec or contract change requires updates:

1. The integration agent adds a work item to the relevant `work.md`:
   * `tools/<tool>/work.md` for tool-specific changes
   * `libs/work.md` for shared library changes
2. The work item must include:
   * Summary of the change.
   * Reference to `spec/CHANGELOG.md` entry.
   * Affected contracts or spec sections.
   * Conformance tests to validate against.

### Integration Agent → Failure Reports

When cross-component validation fails:

1. The integration agent identifies the responsible builder agent (shared or tool).
2. Adds a work item to the responsible agent's `work.md` describing the failure.
3. Blocks the PR until the failure is resolved.

### Session Start Protocol

Each agent must, at the start of every work session:

1. Read its own `work.md` for new items added by the integration agent.
2. Tool agents: check `spec/CHANGELOG.md` for spec updates since last session.
3. Shared agent: check `spec/CHANGELOG.md` and `spec-int-work.md` for spec changes affecting shared code.
4. Integration agent: scan `spec-int-work.md` for new proposals from tool or shared agents.

### Conformance Test Coordination

The shared agent owns the conformance test framework (`tests/conformance/runner.py`, `conftest.py`, `runners/`). Tool agents may add tests to `tests/conformance/**`. To avoid merge conflicts:

* Use tool-namespaced subdirectories when adding tests for tool-specific validation (e.g., `tests/conformance/interpreter/`, `tests/conformance/compiler/`).
* Shared behavioral tests go in feature-area directories (e.g., `tests/conformance/memory/`).
* Prefer adding new files over modifying existing ones.

---

## 5. Related Documents

* Project-wide process: `spec-int-dev-process.md`
* Subproject process: `tool-dev-process.md`
* Engineering principles: `principles.md`
* GitHub integration: `github-process.md`
