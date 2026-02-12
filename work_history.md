# Work History

Completed work items are recorded here.

---

# Multi-agent workflow
status=completed

Defined and validated a multi-agent concurrent engineering workflow for the NEM toolchain.

## Summary

### Process Documentation
- Reviewed and fixed all engineering process docs (principles, general-dev-process, spec-int-dev-process, tool-dev-process, github-process)
- Fixed cross-reference errors (wrong filenames, truncated sentences, broken links)
- Resolved binder/assembler naming collision — adopted "binder" per the NEM spec
- Fixed "interpretor" typo — renamed directory and all references to "interpreter"
- Deleted 9 empty workflow stub files, consolidated into engineering docs
- Updated parallel development model: clones as default (multi-machine), worktrees as optional local optimization

### Infrastructure Created
- Contract change proposal template (`docs/workflow/templates/proposal-contract-change.md`)
- Conformance test infrastructure (`tests/conformance/README.md` — pytest format, naming, capability markers)
- Contracts directory (`docs/contracts/README.md` — inventory of 4 expected contracts, MAJOR.MINOR versioning)
- PR template (`.github/pull_request_template.md`)
- CODEOWNERS file mapping tool dirs to agents, shared areas to integration
- Spec changelog (`spec/CHANGELOG.md`)
- Architecture decision records directory (`docs/engineering/decisions/README.md`)
- Shared library protocol (`libs/README.md`)

### Tool Scaffolding
- Created CLAUDE.md and work.md for compiler, binder, and simulator
- Each tool agent has role definition, scope boundaries, and references to engineering process

### Process Additions
- Inter-agent communication protocol (Section 4 in general-dev-process.md): tool→integration requests, integration→tool work items, session start protocol, conformance test coordination
- Work item size guidance with examples of well-sized vs poorly-sized items
- Provisional conformance provision in spec-int-dev-process.md (addresses interpreter-first serial bottleneck)

### GitHub Setup
- Initialized git repository, pushed to `git@github.com:frank-ceva/nem.git`
- Created branch structure: `main`, `integration/main`, `agent/interpreter/main`, `agent/compiler/main`, `agent/binder/main`, `agent/simulator/main`
