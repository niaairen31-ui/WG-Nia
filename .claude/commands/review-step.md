Review the latest changes (uncommitted diff, last commit if the tree is
clean, or the commit range given as argument) against the project
invariants: the Invariants section of the root CLAUDE.md and the
`## Invariants` section of every `.claude/rules/*.md` file that has one.

For each invariant, state: TOUCHED or NOT TOUCHED by these changes.
For every TOUCHED invariant, show the relevant code and argue explicitly
why the invariant still holds. When the invariant ends with
`-- enforced by <check>.py`, the full law is that check's docstring: read
it, and run the check. If you cannot argue it convincingly, mark it
VIOLATION SUSPECTED with the exact lines.

Also check: does any new code path inject context without going through a
scoped assembler? Does any new code write canon in response to an AI
proposal outside `_apply_mutation`? Either is an automatic VIOLATION.

End with a one-line verdict: CLEAN / ATTENTION / VIOLATION.

Then, in the same turn: on CLEAN or ATTENTION, continue to /close-step in
the same turn and carry every ATTENTION item into its report. On
VIOLATION, stop and report; do not commit.
