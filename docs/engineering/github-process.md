# GitHub PR Process

This document defines how GitHub Pull Requests are used as the official integration mechanism for this repository.

PRs replace any separate “integration queue” mechanism. A PR is the only valid signal that work is ready for integration.

---

## 1. Branch Model

### Long-Lived Branches

* `main`
  Production-ready, always green.

* `integration/main`
  Staging branch for validated PRs prior to promotion to `main`.

* `agent/<tool>/main`
  Long-lived branch owned by a specific tool agent (e.g., interpreter, compiler).

---

### Feature Branches

Feature work is developed on:

```
agent/<tool>/feat/<feature-name>
```

Flow:

1. Develop feature on `agent/<tool>/feat/<feature-name>`.
2. Merge into `agent/<tool>/main` once validated locally.
3. Open PR from `agent/<tool>/main` → `integration/main`.

No direct PRs from feature branches to `integration/main`.

---

## 2. Ready for Integration (RFI)

A Pull Request is considered Ready for Integration when:

* It targets `integration/main`.
* It is not marked as Draft.
* It has the `rfi` label.
* Required CI checks are green.
* Required reviews (per CODEOWNERS) are satisfied.

If any of these are missing, the PR is not ready.

---

## 3. PR Requirements

All PRs to `integration/main` must include:

* Clear summary of the change.
* Scope of affected paths.
* Tests run (tool-local + conformance smoke).
* Statement of contract impact:

  * None
  * Updated
  * Breaking (version bumped)
* Risk notes if applicable.

Use `.github/pull_request_template.md` to standardize this format.

---

## 4. Labels

Recommended labels:

* `rfi` — Ready for Integration
* `contracts` — Affects shared contracts
* `spec` — Affects language spec
* `blocked` — Waiting on dependency or clarification
* `breaking` — Introduces breaking change

Labels are governance signals, not decorative metadata.

---

## 5. CI and Required Checks

Branch protection must enforce:

* PR required for `integration/main` and `main`
* Required status checks:

  * Formatting / lint
  * Tool-local tests (based on changed paths)
  * Conformance smoke
* Required review approvals
* Dismiss stale approvals on new commits

No direct pushes to protected branches.

---

## 6. Integration Procedure

For each PR labeled `rfi`:

1. Integrator reviews changes.
2. CI must be green.
3. Merge into `integration/main`.
4. Validate integration branch stability.
5. Periodically merge `integration/main` → `main`.

If integration fails:

* Do not merge.
* Remove `rfi` label.
* Add `blocked` label with explanation.
* Assign back to responsible agent.

---

## 7. Promotion to Main

Promotion from `integration/main` to `main` requires:

* Integration branch green.
* No open blocking issues.
* No pending contract conflicts.

Promotion may occur via PR or fast-forward, depending on branch protection rules.

---

## 8. Contract and Spec Changes

If a PR modifies:

* `docs/contracts/**`
* `spec/**`
* `libs/**`

Then:

* It must include explicit documentation of the change.
* Version bump must be applied if breaking.
* Integration review is mandatory.

---

## 9. Authority

The integration lane owns:

* Final merge decisions.
* Conflict resolution.
* Enforcement of this process.

This document defines repository governance for GitHub-based integration.
