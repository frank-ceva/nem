This file lists all major work items to be worked on, or currently being worked on, in priority order: the upper one is the first to work on.

# Phase 1, Step 1: Infrastructure + Lexer + Constants

**Plan reference:** `plan/phase_1/libs.md` Step 1, `plan/phase_1/master.md`

Build the foundation: nemlib package, diagnostics, core types, lexer, parser for `const` declarations, conformance test infrastructure, and build infrastructure.

## nemlib package setup

- `libs/nemlib/pyproject.toml` — Python 3.10+, zero runtime deps, dev deps (pytest, mypy, ruff, pyyaml)
- `libs/nemlib/nemlib/__init__.py` — version, top-level re-exports
- `libs/nemlib/nemlib/py.typed` — PEP 561 marker

## Diagnostics (Layer 0)

- `diagnostics/location.py` — SourceLocation(file, line, col, end_line, end_col)
- `diagnostics/severity.py` — DiagnosticSeverity enum (error, warning, info)
- `diagnostics/diagnostic.py` — Diagnostic(severity, message, location, notes)
- `diagnostics/collector.py` — DiagnosticCollector: error(), warning(), has_errors(), get_all(), format_all()

## Core (Layer 1)

- `core/elements.py` — ElementType enum with bitwidth()
- `core/memory.py` — MemoryLevel enum (DDR, L2, L1)
- `core/expressions.py` — ExprNode types (IntLiteral, Identifier, BinaryOp, UnaryOp, Paren), constant expression evaluator with variable environment

## Parser (Layer 2)

- `parser/tokens.py` — Full TokenKind enum (all NEM keywords, operators, delimiters, FLOAT, INT, STRING, ID, EOF)
- `parser/lexer.py` — Complete tokenizer for NEM programs and device configs (# comments, all literals, compound keywords like `transfer.async`)
- `parser/ast_nodes.py` — ProgramNode, ConstDeclNode, ExprNode variants (frozen dataclasses)
- `parser/parser.py` — parse_program_header(), parse_const_decl(), parse_expr()
- `parser/errors.py` — Basic error reporting with source locations

## Conformance test infrastructure

- `tests/conformance/runner.py` — ConformanceRunner protocol, ValidationResult, ExecutionResult
- `tests/conformance/conftest.py` — Runner fixture with parametrization
- `tests/conformance/runners/__init__.py`
- `tests/conformance/runners/interpreter_runner.py` — InterpreterRunner (validate-only initially)
- Wire up all 10 test files in `tests/conformance/const/` (32 cases) to call runner.validate()

## Build infrastructure

- Root `Makefile` — targets: install, test, test-nemlib, test-interpreter, test-conformance, lint, typecheck, clean

## Unit tests

- `libs/nemlib/tests/test_diagnostics.py`
- `libs/nemlib/tests/test_elements.py`
- `libs/nemlib/tests/test_expressions.py`
- `libs/nemlib/tests/test_lexer.py`
- `libs/nemlib/tests/test_parser_const.py`

## Completion criteria

- `pip install -e libs/nemlib[dev]` succeeds
- Lexer tokenizes all 5 example .nem files without errors
- Parser parses const blocks from all 5 examples
- Expression evaluator handles arithmetic, mod, parens
- All 32 const conformance cases pass via runner.validate()
- `make lint` — zero violations
- `make typecheck` — zero errors

---
