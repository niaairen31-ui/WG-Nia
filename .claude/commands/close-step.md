Run the step-closure checklist for the work just completed:

1. **Tests** — confirm the live test(s) for this step passed. If none were
   run, say so explicitly and stop.
2. **Changelog** — if the schema was touched: read the
   `Current schema version: vX.YY` line in `world-engine-schema.md`,
   compute the new version (minor + 1), prepend the new entry to
   `world-engine-schema-changelog.md`, and update the header line to the
   new version. If the schema was not touched, confirm no entry is needed.

**Decisions index** — if a decision record was added to
tooling/standards/ARCHITECTURE_DECISIONS.md, run
python tooling/glue/gen_decisions_index.py and commit the regenerated
DECISIONS_INDEX.md.
3. **Docs sync** diff what tooling/standards/ARCHITECTURE_DECISIONS.md and the root CLAUDE.md claim against what the code now does. Update any stale statement.
   Quote each correction made.
4. **Debts** — list any shortcuts, deferred decisions, or new debts
   introduced in this step. Propose a changelog or backlog note for each.
5. **Invariants** — re-read the Invariants section of CLAUDE.md and confirm
   none was weakened. Flag anything ambiguous.
6. **Commit** — propose a commit message summarizing the step. Wait for
   approval before committing.

Unattended mode: when invoked from /pipeline (the invoker will say
so), skip the approval wait and commit directly. All other steps
(changelog, decisions index, message quality) unchanged.

Report as a numbered checklist with PASS / FIXED / ATTENTION per item.
