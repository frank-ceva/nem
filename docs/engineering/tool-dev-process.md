# Subproject Development Process

This document defines the lifecycle for work confined to a single tool.

Applies to interpreter, compiler, binder, or simulator internal work that does not modify shared contracts or language semantics.

---

## 1. Trigger Conditions

Use this process when:

* The change is internal to one tool.
* No language semantics change.
* No contract modification required.
* No externally observable behavior change.

If the change affects observable behavior, escalate to `spec-int-dev-process.md`.

---

## 2. Subproject Feature / Refactor Lifecycle

### Step 1 — Confirm Scope

* Ensure all edits remain under:

  * `tools/<tool>/**`
* Do not modify:

  * `docs/contracts/**`
  * `spec/**`
  * Other tools

---

### Step 2 — Implement Change

* Maintain clarity and determinism.
* Avoid altering external behavior unless intentional.

---

### Step 3 — Add or Update Tests

If internal-only:

* Add regression/unit tests under:

  * `tools/<tool>/tests/**`

If externally observable:

* Escalate to project-level process.

---

### Step 4 — Validate

* Tool-local tests pass.
* Conformance tests still pass.
* No unintended side effects.

---

## 3. Subproject Bug Fixes

1. Reproduce locally.
2. Determine impact:

   * Internal-only → tool-local regression test.
   * Externally observable → follow project-level process.
3. Fix.
4. Validate determinism.

---

## 4. Definition of Done

* Scope boundaries respected.
* Tool-local tests pass.
* Conformance remains green.
* No contract changes introduced.
* Ready for integration merge.
