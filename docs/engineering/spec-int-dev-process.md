# Project Development Process

This document defines the lifecycle for **spec, contract, and integration-level work**.

Applies when changes affect language semantics, contracts, or multiple tools.

---

## 1. Trigger Conditions

Use this process if the change affects:

* Language semantics
* IR schema
* Object/bytecode format
* CLI contract
* Diagnostics contract
* Conformance structure
* Cross-tool integration behavior

---

## 2. Project-Level Feature Lifecycle

### Step 1 — Define or Clarify Semantics

* Update or clarify:

  * `docs/contracts/**`
  * `spec/**`
  * `spec/notes/**`
* If breaking:

  * Bump version
  * Document compatibility impact

---

### Step 2 — Add Conformance Tests

* Add canonical tests under `tests/conformance/**`.
* Define deterministic expected results.
* Tag required capabilities.

Conformance defines correctness.

---

### Step 3 — Reference Implementation

* Implement in the interpreter first (unless justified otherwise).
* Ensure:

  * Tool-local tests pass.
  * Conformance smoke passes.

**Provisional conformance:** If the interpreter agent is occupied with other work, other tools may begin implementation against the new conformance tests before the interpreter reference is complete. This is permitted under these conditions:

* The conformance tests from Step 2 are already merged.
* The tool agent marks its implementation as "provisional" in its work.md.
* Once the interpreter reference implementation is complete, the tool agent must reconcile and re-validate against it.

---

### Step 4 — Propagate to Other Tools

Update:

* Compiler
* Binder
* Simulator

All tools must comply with updated contracts. The update should be done by defining a work item (in work.md) of the relevant subproject(s)

---

### Step 5 — Integration Validation

* Run integration tests.
* Ensure no contract drift.
* Confirm cross-tool behavior consistency.

Merge through integration lane only.

---

## 3. Project-Level Bug Fixes

If a bug affects externally observable behavior:

1. Add regression test in `tests/conformance/**`.
2. Fix implementation(s).
3. Validate across tools.

---

## 4. Definition of Done

* Contracts updated if required.
* Conformance coverage exists.
* At least one reference implementation passes.
* No undocumented behavior changes.
* Integration lane validates and merges.
