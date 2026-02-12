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
One dedicated agent for spec and integration work.
Each agent works on its own clone (or worktree) of the repository, on a dedicated branch.
Each agent uses dedicated CLAUDE.md and work.md files to manage its work.
All coordination happens through GitHub PRs — agents may run on the same machine, different machines, or different accounts.

Rationale:
Enables concurrent work with full isolation. Clone-based model supports distributed execution across machines and accounts. Worktrees are an optional local optimization when all agents run on the same machine.

Consequences:
Requires discipline around branch merging and scope enforcement.

---

## 3. Testing Architecture

Decision:
Tool-local unit tests + top-level conformance and e2e tests.

Rationale:
Separates implementation correctness from language correctness.

---

## 4. Contract Ownership

Decision:
Contracts and shared libraries are integration-owned.

Rationale:
Prevents drift between tools.

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

