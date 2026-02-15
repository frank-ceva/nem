This file lists all major work items to be worked on, or currently being worked on, in priority order: the upper one is the first to work on.

# Add Python project configuration and dependency management

Create the files necessary for any developer (or agent) to set up a complete working environment from a fresh clone. Currently there is no `pyproject.toml`, `requirements.txt`, `Makefile`, or equivalent — anyone who clones the repo must guess what to install by reading import statements.

## Scope

### Dependency management

- Add a top-level `pyproject.toml` as the single source of truth for all Python dependencies, using dependency groups:
  - **Core dependencies** — packages needed at runtime by tools (e.g. `pyyaml` for registry consumption).
  - **`[project.optional-dependencies] test`** — test-time dependencies (`pytest`, `jsonschema`).
  - **`[project.optional-dependencies] dev`** — development tools (`ruff`, `mypy`).
- Installation commands:
  - `pip install .` — runtime only
  - `pip install ".[test]"` — runtime + test
  - `pip install ".[dev,test]"` — everything

### Build/task runner

- Add a top-level `Makefile` with standardised commands:
  - `make install` — install all deps (dev + test)
  - `make test-conformance` — run conformance tests
  - `make test-tool TOOL=<name>` — run tool-local tests
  - `make lint` — format/lint checks
  - `make ci` — run everything CI would run, locally

### Documentation

- Document the setup steps in a short top-level developer guide (e.g. section in the existing README or a `CONTRIBUTING.md`).

## Acceptance criteria

- A fresh clone + `pip install ".[test]"` + `pytest tests/conformance/ -v` succeeds.
- `pip install ".[dev,test]"` installs all development and test tooling.
- The same commands CI will use (next work item) are available locally via `make ci`.
- No ad-hoc `requirements-*.txt` files — `pyproject.toml` is the single source.

---

# Add GitHub Actions CI workflow for PRs to integration/main

Implement the CI checks described in `docs/engineering/github-process.md` Section 5, which are currently documented but not wired up. PRs to `integration/main` currently merge with zero automated validation.

## Depends on

- "Add Python project configuration and dependency declarations" (previous work item).

## Scope

### Phase A — CI workflow

- Add `.github/workflows/ci.yml` triggered on PRs to `integration/main`.
- Jobs:
  1. **Conformance tests** — install Python + deps, run `pytest tests/conformance/ -v`.
  2. **Path-based tool tests** — detect which `tools/<name>` paths changed, run that tool's local tests (skip if none exist yet).
  3. **Lint/format** — run ruff (or chosen linter) if configured.
- Report pass/fail as GitHub status checks on the PR.

### Phase B — Branch protection

- Enable branch protection on `integration/main`:
  - Require CI workflow to pass before merge.
  - Require at least 1 review approval.
  - Dismiss stale approvals on new pushes.
  - Block direct pushes.
- Enable matching protection on `main` for the promotion step.

## Acceptance criteria

- Opening a PR to `integration/main` automatically triggers the CI workflow.
- A PR with a failing conformance test cannot be merged.
- The github-process.md Section 5 requirements are enforced, not just documented.

---

# Deferred device model extensions

These items were identified during the "Extend NEM device model for full NPM architectural coverage" initiative but deferred as separate future work items.

- **Fusion chain capability declaration:** Declaring what NMU->CSTL fusion paths a device supports. To be addressed as a separate work item.
- **DMA connectivity matrix:** Declaring which DMA instances connect to which memory paths. May be addressed together with fusion or separately.

---
