# BRIEF -- Step "Fix purge child-before-parent delete ordering" (TICKET-0037, BRIEF-0037-e)

## Context

The shared retention purge `_purge_closed_batches`
(`src/world_engine/cockpit/app.py`) crashes the app at startup with
`sqlite3.IntegrityError: FOREIGN KEY constraint failed` on
`DELETE FROM link_batch WHERE link_batch.id = ?`. The crash fires in
`_purge_closed_batches_on_startup` on the FIRST call
(`purge_closed_link_batches`), before the app can serve a single request --
so it blocks TICKET-0037's live gate outright.

**Root cause (reproduced verbatim at RECON, 2026-07-21).** The helper marks
row-children then the batch for deletion with ORM `db.delete(...)`, then
relies on the SQLAlchemy unit-of-work to order the emitted DELETEs
(children before parents). There is NO `relationship()` between the batch
model and its row model -- only a column-level `foreign_key=` on
`*_batch_row.batch_id`. Without a relationship, the UOW has no per-object
dependency edge, so it does NOT guarantee child-before-parent delete order.
The `select(...)` at the top of the next loop iteration triggers an
**autoflush**, and at that flush the UOW emits `DELETE FROM link_batch`
before the child `link_batch_row` deletes. With `PRAGMA foreign_keys=ON`
(set by the `connect` listener in `db.py`), SQLite rejects it. Reproduced
in isolation with the real models (5 closed batches x 3 rows): identical
error, identical failing statement.

**This is a latent TICKET-0036 defect, not a 0037 regression.** The
0036 `purge_closed_link_batches` had the structurally identical
delete-rows / delete-batch / commit body. 0037 preserved it verbatim when
it generalized the loop into the shared helper, and SURFACED it: a second
agent (npc group agent) now also closes batches, so the DB finally
accumulated more than 2 closed batches, `.offset(2)` finally returned rows
to purge, and the latent ordering bug fired. The fix belongs to 0037
because 0037 owns the shared helper and is still pre-merge; fixing the
shared helper repairs BOTH agents' purges in one edit.

**Why G1 was green while the live gate crashed.**
`verify/checks/npc_batch_purge.py` is AST-only ("stdlib only") -- it asserts
the function exists, calls the shared helper with `(NpcBatch, NpcBatchRow)`,
carries `.offset(2)`, and is wired at startup. It never executes the purge
against a real FK-enforcing DB with >2 closed batches, so it structurally
cannot see a runtime delete-ordering fault. This brief adds the missing
runtime check.

**This is a pure plumbing fix.** No schema, no migration, no schema-version
bump, no model change, no canon-write-site change, no retention-semantics
change, no journal touch. `git diff` is: one import line, the helper body,
one new check file, and the TICKET-0037 criteria delta.

The current helper (0037 branch tip, `cockpit/app.py`), verbatim:

```python
def _purge_closed_batches(
    db: Session, batch_model: Type[SQLModel], row_model: Type[SQLModel], row_fk_attr: str
) -> None:
    """..."""
    to_purge = db.exec(
        select(batch_model)
        .where(batch_model.status.in_(("committed", "abandoned")))
        .order_by(batch_model.closed_at.desc())
        .offset(2)
    ).all()
    row_fk_column = getattr(row_model, row_fk_attr)
    for batch in to_purge:
        for row in db.exec(select(row_model).where(row_fk_column == batch.id)).all():
            db.delete(row)
        db.delete(batch)
    db.commit()
```

## Scope IN

1. **Import -- `src/world_engine/cockpit/app.py`.** Add `from sqlalchemy
   import delete` to the third-party import group, on the line ABOVE the
   existing `from sqlmodel import Session, SQLModel, select` (sqlalchemy
   sorts before sqlmodel). Do not touch any other import.

2. **Replace the body of `_purge_closed_batches` with Option A -- bulk Core
   deletes, children then parents, executed in statement order.** Keep the
   signature UNCHANGED. Keep the existing docstring, and APPEND to it the
   verbatim NOTE below so the ordering rationale is recorded at the call
   site. Exact body:

   ```python
   def _purge_closed_batches(
       db: Session, batch_model: Type[SQLModel], row_model: Type[SQLModel], row_fk_attr: str
   ) -> None:
       """<existing docstring text, unchanged>

       NOTE (BRIEF-0037-e): children are deleted before the batch via two
       explicit Core DELETEs in statement order, NOT via per-object
       `db.delete(...)`. These models declare only a column-level
       `foreign_key=` (no ORM `relationship()`), so the unit-of-work gives
       no child-before-parent delete ordering; under `PRAGMA
       foreign_keys=ON` an autoflush would emit the parent DELETE first and
       SQLite would reject it. Statement-ordered Core deletes make the
       order explicit and independent of flush timing.
       """
       ids = db.exec(
           select(batch_model.id)
           .where(batch_model.status.in_(("committed", "abandoned")))
           .order_by(batch_model.closed_at.desc())
           .offset(2)
       ).all()
       if not ids:
           return
       row_fk_column = getattr(row_model, row_fk_attr)
       db.exec(delete(row_model).where(row_fk_column.in_(ids)))
       db.exec(delete(batch_model).where(batch_model.id.in_(ids)))
       db.commit()
   ```

   `select(batch_model.id)` yields the id scalars; `if not ids: return`
   guards against an empty `IN ()` and a pointless commit. `db.exec(...)`
   is the confirmed-working call for these Core `delete()` statements
   (validated at RECON) -- do NOT swap it to `db.execute(...)` on a hunch;
   if SQLModel raises on `exec` with a delete statement, REPORT rather than
   silently switching.

3. **Behavior parity -- no semantic change.** After the swap the purge must
   still: act only on `status in ("committed", "abandoned")`; retain the 2
   most-recently-closed batches (`closed_at` desc, `.offset(2)`); delete
   every row-child of each purged batch; and leave retained batches, their
   rows, and all `open` batches untouched. The two wrapper functions
   (`purge_closed_link_batches`, `purge_closed_npc_batches`) and the
   `@app.on_event("startup")` handler are UNCHANGED -- only the shared
   helper's body changes.

4. **New runtime verify check --
   `tooling/verify/checks/purge_fk_ordering.py`.** Follow the
   `scene_join_target.py` runtime idiom EXACTLY: set
   `WORLD_ENGINE_DATABASE_URL` to a fresh temp-file SQLite path BEFORE
   importing anything under `world_engine` (so the real `db.py` engine and
   its `PRAGMA foreign_keys=ON` connect-listener are the ones in force, and
   the real DB is never touched); purge `world_engine*` from `sys.modules`
   first; `FAILURES` list + `fail()`; `main() -> int` printing a single
   `PASS: ...` / `FAIL: ...` last line; `sys.exit(main())`. Import the real
   `_purge_closed_batches`, `LinkBatch`, `LinkBatchRow`, `NpcBatch`,
   `NpcBatchRow` from `world_engine.cockpit.app` /
   `world_engine.models`. The check must exercise the helper through BOTH
   table pairs (parametrize over
   `(LinkBatch, LinkBatchRow, "batch_id")` and
   `(NpcBatch, NpcBatchRow, "batch_id")`), and for each:
   - seed 3 closed batches (`status="committed"`, distinct ascending
     `closed_at`) each with >=1 row-child, plus 1 `open` batch with a
     row-child;
   - call `_purge_closed_batches(...)` and assert it does NOT raise
     (the regression: it raised `IntegrityError`);
   - assert exactly 2 batches survive, and they are the 2 with the LATEST
     `closed_at`;
   - assert the purged batch's row-children are gone AND the retained
     batches' row-children remain;
   - assert the `open` batch and its row-child are untouched.
   Fail-closed: a missing helper, missing model, or zero assertions
   executed is a FAILURE, never a vacuous pass (npc_batch_purge.py idiom).

5. **Wire the new check into the G1 gate.** TICKET-0037's Machine-checkable
   section gains one criterion with the arrow
   `-> verify/checks/purge_fk_ordering.py` (delivered in the amended
   ticket). After this brief, `python tooling/verify/run.py --ticket
   TICKET-0037` runs 9 checks and must be green.

6. **Docs** (see Docs to update).

## Scope OUT

- **Adding a `relationship()` / `cascade="all, delete-orphan"` on the
  models** -- the ephemeral models are deliberately thin
  schema-fidelity classes with no relationships (models/ephemeral.py
  docstring). The design option to fix ordering via an ORM relationship
  was considered and rejected at design; do NOT resurrect it. REPORT if you
  believe it is necessary.
- **`ON DELETE CASCADE` at the DDL + `passive_deletes`** -- that is a schema
  change requiring a migration and a schema-version bump. Explicitly out;
  this fix is code-only.
- **Any schema, migration, or `schema_version_touched` change**, and any
  edit to `models/ephemeral.py`.
- **Touching `purge_closed_link_batches`, `purge_closed_npc_batches`, or the
  startup handler** -- the fix lives entirely in the shared helper body.
- **Changing retention (still last-2), the status filter, the ordering key,
  or adding a per-world scope** to the purge -- pre-existing semantics,
  preserved exactly.
- **"Fixing" or deleting `verify/checks/npc_batch_purge.py`** -- it stays as
  the structural guard. The runtime check is ADDITIVE, not a replacement.
- **Any reformat / tidy / "while I'm here" edit to `app.py`** -- the diff is
  the import line plus the helper body, nothing else. REPORT anything more.
- **Touching the append-only journals or any other purge-adjacent code.**

## Invariants to defend

- **FK-safe by construction.** Row-children are physically deleted before
  the parent batch in every path, via statement-ordered Core DELETEs -- no
  reliance on unit-of-work flush ordering and no dependence on autoflush
  timing. App boots clean with >2 closed batches of each agent present
  (the exact condition that crashes today).
- **One fix, both agents.** The link and npc purges route through the same
  shared helper; there is no per-agent divergence and no second code path
  to keep in sync.
- **Semantic parity.** Retention is exactly last-2 (`committed`/`abandoned`,
  `closed_at` desc, offset 2); open batches are never touched;
  `if not ids: return` makes the empty case a clean no-op (no empty
  `IN ()`, no stray commit).
- **The runtime check is the point of this ticket.** `purge_fk_ordering.py`
  must FAIL against the pre-fix helper body and PASS against the fixed one;
  if it passes against the old body, it is not exercising FK enforcement --
  REPORT.
- **`module_budget` / `function_length` hold** on `app.py`: the helper stays
  well under 80 lines; the module gains no def.

## Done means

- [ ] App boots with >=3 closed `link_batch` AND >=3 closed `npc_batch`
      (each with row-children) present: startup purge runs, no
      `IntegrityError`, exactly 2 of each table retained (the latest-closed
      2), older batches and their rows gone.
- [ ] `tooling/verify/checks/purge_fk_ordering.py` exists, exercises both
      table pairs under real FK enforcement, fails-closed, and is green;
      confirmed to FAIL against the pre-fix helper body.
- [ ] TICKET-0037's Machine-checkable section links
      `verify/checks/purge_fk_ordering.py`; `python tooling/verify/run.py
      --ticket TICKET-0037` is green across all 9 checks.
- [ ] `git diff` reads as exactly: `from sqlalchemy import delete` added to
      `app.py`; the `_purge_closed_batches` body swapped to the Core-delete
      form with the appended NOTE; one new check file; the TICKET-0037
      frontmatter + criteria delta. Anything else -> REPORT.
- [ ] `function_length.py` and `module_budget.py` green on `app.py`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` -- one entry: ephemeral batch purge uses
  explicit statement-ordered Core child-then-parent deletes because the
  models carry no ORM relationship and FK enforcement is on; UOW flush
  ordering is not relied upon. Add to `DECISIONS_INDEX.md`.
- `CLAUDE.md` -- only if it references the startup purge as current state /
  next step; keep to current-state-plus-next-step, no historical
  accumulation.
- No `world-engine-schema.md` / changelog entry (no schema change).
- No `canon_write_policy.txt` change (the purge is ephemeral stratum, not a
  canon write site) -- if execution produces any diff there, something
  moved that should not have: STOP and REPORT.
