"""Interpreter-based conformance runner using nemlib."""

from nemlib.parser import parse
from nemlib.parser.ast_nodes import ConstDeclNode
from nemlib.core.expressions import evaluate_const_expr, ConstEvalError
from nemlib.parser.lexer import Lexer
from nemlib.parser.tokens import TokenKind
from tests.conformance.runner import ValidationResult


class InterpreterRunner:
    """Conformance runner that uses the nemlib interpreter for validation."""

    name = "interpreter"

    def validate(self, source: str, device_config: str | None = None) -> ValidationResult:
        """Parse and validate a NEM program using the interpreter.

        For Step 1 (const declarations only):
        1. Parse the source
        2. If no parse errors, evaluate all const declarations in order
        3. Return validation result

        Args:
            source: NEM source code to validate
            device_config: Optional device configuration (unused in Step 1)

        Returns:
            ValidationResult with success status and any diagnostics
        """
        program, diag = parse(source, "<test>")

        if diag.has_errors():
            return ValidationResult(
                valid=False,
                diagnostics=[str(d) for d in diag.get_all()]
            )

        # Pre-scan tokens for buffer and const names with their positions
        lexer = Lexer(source, "<test>")
        tokens = lexer.tokenize()
        buffer_decls: dict[str, int] = {}  # name -> line number
        const_positions: dict[str, int] = {}  # name -> line number (from AST)

        for i, tok in enumerate(tokens):
            if tok.kind == TokenKind.BUFFER and i + 1 < len(tokens):
                next_tok = tokens[i + 1]
                if next_tok.kind == TokenKind.IDENT:
                    buffer_decls[next_tok.lexeme] = tok.location.line if tok.location else 0

        # Evaluate const declarations in order
        env: dict[str, int] = {}
        errors: list[str] = []
        for stmt in program.statements:
            if isinstance(stmt, ConstDeclNode):
                # Track const position
                const_line = stmt.location.line if stmt.location else 0
                const_positions[stmt.name] = const_line

                # Check for name conflict with buffer declared BEFORE this const
                if stmt.name in buffer_decls:
                    buffer_line = buffer_decls[stmt.name]
                    if buffer_line < const_line:
                        errors.append(f"Name conflict - {stmt.name} already declared as buffer")
                        continue

                # Check for duplicate const
                if stmt.name in env:
                    errors.append(f"Duplicate constant declaration {stmt.name}")
                    continue
                try:
                    value = evaluate_const_expr(stmt.value, env)
                    env[stmt.name] = value
                except ConstEvalError as e:
                    errors.append(str(e))

        # Check for buffer-after-const conflicts
        for buffer_name, buffer_line in buffer_decls.items():
            if buffer_name in const_positions:
                const_line = const_positions[buffer_name]
                if const_line < buffer_line:
                    errors.append(f"Name conflict - {buffer_name} already declared as const")

        all_diags = [str(d) for d in diag.get_all()] + errors
        return ValidationResult(
            valid=len(errors) == 0 and not diag.has_errors(),
            diagnostics=all_diags
        )
