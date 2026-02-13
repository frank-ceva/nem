# Engineering Principles

## 1. Repository Strategy

Decision:
Single monorepo containing spec, contracts, tools, and tests.

Rationale:
High coupling during language evolution requires atomic updates across components.

Alternatives Considered:
Multi-repo with umbrella project.

Consequences:
Simpler integration; requires strict internal boundaries.

---

## 2. Parallel Development Model

Decision:
One dedicated agent per tool.
One dedicated agent for shared libraries, tests, examples, and infrastructure (shared agent).
One dedicated agent for spec evolution, integration validation, and coordination (integration agent).
Each agent works on its own clone (or worktree) of the repository, on a dedicated branch.
Each agent uses dedicated CLAUDE.md and work.md files to manage its work.
All coordination happens through GitHub PRs — agents may run on the same machine, different machines, or different accounts.

The shared agent builds shared code (nemlib, test infrastructure, examples, build config). The integration agent validates cross-component consistency, runs tests, and reports failures — it does not write production code. This separation ensures the quality gate is independent of the code it validates.

Rationale:
Enables concurrent work with full isolation. Separating code building from integration validation prevents the same agent from judging its own work. Clone-based model supports distributed execution across machines and accounts. Worktrees are an optional local optimization when all agents run on the same machine.

Consequences:
Requires discipline around branch merging and scope enforcement. Three-way coordination (shared, tool, integration) adds overhead but improves quality assurance.

---

## 3. Testing Architecture

Decision:
Tool-local unit tests + top-level conformance and e2e tests.

Rationale:
Separates implementation correctness from language correctness.

---

## 4. Contract Ownership

Decision:
Contracts and spec are integration-owned. Shared libraries, tests, and examples are shared-agent-owned. Both are protected from direct modification by tool agents.

Rationale:
Prevents drift between tools. The shared agent builds shared code under integration agent review; the integration agent owns spec/contracts and validates cross-component consistency.

---

## 5. Claude Code Scoping

Decision:
Three-layer model:
1. Root CLAUDE.md baseline
2. Path-scoped .claude/rules
3. Tool-local CLAUDE.md

Rationale:
Supports multiple operational modes while preventing scope violations.

---

## 6. Release Model

Decision:
Lockstep ecosystem releases until contracts stabilize.

Rationale:
Reduces compatibility fragmentation early in project lifecycle.

