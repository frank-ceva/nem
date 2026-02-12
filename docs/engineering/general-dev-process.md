# General Development Process

This document defines the overall engineering model of the repository and clarifies the distinction between **project-wide work** and **subproject work**.

---

## 1. Two Levels of Engineering Work

### A. Project-Wide Engineering

Scope:

* Language semantics
* Spec evolution
* Cross-tool integration
* Contracts (IR, object format, CLI, diagnostics)
* Conformance structure
* Release coordination

Owned by:

* Integration agent

Project-wide work affects multiple tools or defines shared behavior.

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

When a tool agent needs a change to integration-owned areas (contracts, spec, libs):

1. Fill out a Contract Change Proposal using `docs/workflow/templates/proposal-contract-change.md`.
2. Add a work item entry to `spec-int-work.md` referencing the proposal.
3. Continue working on non-blocked tasks.

### Integration Agent → Tool Agents

When a spec or contract change requires tool updates:

1. The integration agent adds a work item to `tools/<tool>/work.md` for each affected tool.
2. The work item must include:
   * Summary of the change.
   * Reference to `spec/CHANGELOG.md` entry.
   * Affected contracts or spec sections.
   * Conformance tests to validate against.

### Session Start Protocol

Each agent must, at the start of every work session:

1. Read its own `work.md` for new items added by the integration agent.
2. Tool agents: check `spec/CHANGELOG.md` for spec updates since last session.
3. Integration agent: scan `spec-int-work.md` for new proposals from tool agents.

### Conformance Test Coordination

All tool agents may add tests to `tests/conformance/**`. To avoid merge conflicts:

* Use tool-namespaced subdirectories when adding tests for tool-specific validation (e.g., `tests/conformance/interpreter/`, `tests/conformance/compiler/`).
* Shared behavioral tests go in feature-area directories (e.g., `tests/conformance/memory/`).
* Prefer adding new files over modifying existing ones.

---

## 5. Related Documents

* Project-wide process: `spec-int-dev-process.md`
* Subproject process: `tool-dev-process.md`
* Engineering principles: `principles.md`
* GitHub integration: `github-process.md`
