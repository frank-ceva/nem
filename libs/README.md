# Shared Libraries

This directory contains code shared across multiple tools. It is **libs-agent-owned** — tool agents must not modify it directly. The integration agent reviews all changes but does not build code here.

## When to Extract Shared Code

Code should be extracted to `libs/` when:

- The same logic is needed by 2 or more tools.
- The logic relates to a shared contract (IR parsing, object format reading, diagnostics formatting).
- Duplicating the code across tools would create drift risk.

Code should NOT be extracted when:

- Only one tool uses it (keep it tool-local).
- The logic is tightly coupled to a tool's internal architecture.
- The abstraction is speculative ("we might need this later").

## How to Propose a Shared Library

Tool agents cannot create or modify files in `libs/` directly. To propose shared code:

1. File a Contract Change Proposal using `docs/workflow/templates/proposal-contract-change.md`.
2. Include:
   * The code to be shared (or a reference to existing implementations in tools).
   * Which tools would use it.
   * The proposed API surface.
3. The libs agent will implement the library; the integration agent will review and merge.

## Structure

```
libs/
  <library-name>/
    README.md        # API documentation
    __init__.py      # Public API
    ...
```

Each library must have a README documenting its API and which tools depend on it.
