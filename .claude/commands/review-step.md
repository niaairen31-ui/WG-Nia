Review the latest changes (uncommitted diff, last commit if the tree is
clean, or the commit range given as argument) against the project
invariants in CLAUDE.md:

For each invariant, state: TOUCHED or NOT TOUCHED by these changes.
For every TOUCHED invariant, show the relevant code and argue explicitly
why the invariant still holds. If you cannot argue it convincingly, mark
it VIOLATION SUSPECTED with the exact lines.

Also check: does any new code path inject context without going through a
scoped assembler? Does any new code write canon in response to an AI
proposal outside `_apply_mutation`? Either is an automatic VIOLATION.

End with a one-line verdict: CLEAN / ATTENTION / VIOLATION.
