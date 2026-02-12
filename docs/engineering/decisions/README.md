# Architecture Decision Records (ADRs)

This directory contains architecture decision records — lightweight documents that capture significant technical decisions.

## When to Write an ADR

Write an ADR when a decision:

- Affects multiple tools or the overall architecture.
- Involves choosing between meaningful alternatives.
- Would be hard to reverse later.
- Future contributors would need to understand.

## Format

Each ADR is a numbered markdown file: `NNN-<short-title>.md`

```markdown
# ADR-NNN: <Title>

## Status
Accepted | Superseded by ADR-XXX | Deprecated

## Context
What is the issue or situation that motivates this decision?

## Decision
What is the change that is being proposed or decided?

## Consequences
What becomes easier or harder as a result?
```

## Index

| # | Title | Status |
|---|-------|--------|
| 001 | Monorepo strategy | Accepted |
| 002 | Parallel development model | Accepted |
| 003 | Testing architecture (tool-local + conformance) | Accepted |
| 004 | Contract ownership (integration-owned) | Accepted |
| 005 | Three-layer Claude Code scoping | Accepted |
| 006 | Lockstep releases | Accepted |

The six founding decisions are documented in `docs/engineering/principles.md`. Future decisions should be recorded as individual ADR files here.
