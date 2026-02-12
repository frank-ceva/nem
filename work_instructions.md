Work items being worked on (and history of work items) available in work.md at in the same directory as CLAUDE.md you are using. When you complete a work item, move it to work_history.md so that work.md only contains items to be worked on or currently being worked on.

Specific instructions:
- For each new work item that is not trivial, you will break down the work into tasks with dependencies.
- For each code update:
    * Update documentation accordingly if needed.
    * Add tests to the testing framework.
- Before starting any significant task, ensure that conversation is saved so that if you (claude code) crash while working, we can retrieve the context.
- After you complete a work item listed in work.md, move the item to work_history.md and update the description to indicate that it is completed (add a line after the task title indicating "status=completed"), and include a summary of what was done as subsection(s).
- Each work item should follow the engineering practices defined in docs/engineering/README.md and related files.

## Work Item Size Guidance

A well-sized work item should:

- Be completable in a single work session (one Claude Code conversation).
- Touch one logical concern (e.g., one feature, one refactor, one bug fix).
- Produce a reviewable diff — small enough to reason about in a PR.
- Include its own test coverage.

Examples of well-sized items:
- "Implement lexer tokenization for NEM keywords" (one module, clear scope)
- "Add conformance test for DDR load/store semantics" (one test file, clear spec reference)
- "Refactor parser error recovery to use synchronization tokens" (one concern, contained)

Examples of poorly-sized items:
- "Implement the entire parser" (too large — break into grammar sections)
- "Fix everything" (no clear scope or completion criteria)
- "Refactor and also add new features" (two concerns mixed)

When in doubt, prefer smaller items. A sequence of 5 small, clear work items is better than 1 large, vague one.