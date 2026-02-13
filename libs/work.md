This file lists all major work items to be worked on, or currently being worked on, in priority order: the upper one is the first to work on.

# Phase 1, Step 3: Data Movement + Execution Engine (Parser)

**Plan reference:** `plan/phase_1/libs.md` Step 3, `plan/phase_1/master.md`

Extend the parser to handle task statements (transfer, store, wait), token assignments, dependency lists, and inline region expressions in operand positions.

## parser/ast_nodes.py extensions

- `TaskNode` — task statement with opcode, operands, deps, token assignment
- `WaitNode` — `wait tX` or `wait [tX, tY]`
- `InlineRegionNode` — `region(buf, off, ext) type_attrs` in operand position

## parser/parser.py extensions

- `parse_task_statement()` — `tX = transfer.async(...)` or `store(...)` etc.
- `parse_wait()` — `wait` statement
- `parse_deps()` — `deps=[tX, tY]` dependency list
- `parse_operand()` — handles named references and inline `region(...)` expressions

## Unit tests

- `libs/nemlib/tests/test_parser_task.py` — task, wait, deps, operands, inline regions

## Completion criteria

- Parser handles transfer.async, transfer.sync, store, wait statements
- Token assignment (`tX = ...`) is captured
- Dependency lists parsed correctly
- Inline region expressions in operand positions work
- All existing tests still pass (247 unit + 95 conformance)
- New unit tests pass
- `ruff check` — zero violations
- `ruff format` — zero reformats
- `mypy` — zero errors

---
