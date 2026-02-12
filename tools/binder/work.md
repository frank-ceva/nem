This file lists all major work items to be worked on, or currently being worked on, in priority order.

# Add `const` declaration support

**Requested by: spec-int (const declarations work item)**

The NEM spec now includes `const` declarations (see `spec/CHANGELOG.md`). The binder must support:

1. **Parser**: Add `const_decl` production: `"const" ID "=" expr`. Add to `decl` alternatives.
2. **AST/IR**: Add `ConstDeclNode(name, expr)`. Evaluate constant expressions during semantic analysis.
3. **Semantic checks**: Forward references, duplicate names, loop body prohibition, division by zero, name conflicts.
4. **Lowering**: All constant values must be resolved before TCB generation. Buffer sizes, region offsets, shapes, and loop bounds must use concrete integer values.
5. **Conformance**: Pass all tests in `tests/conformance/const/`.
