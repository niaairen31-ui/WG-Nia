# BRIEF — Step "rollback quarantine contract + script + test (B1)"

## Context

Consequence #2: a code rollback past the constructor version finds `ext_*` tables it
does not know, and — because `PRAGMA foreign_keys=ON` (`db.py:44`) — their FK into
`entity` BLOCKS the old code's `entity` deletes. B1 (locked): quarantine by
construction. The `entity_type` registry is the manifest; a script rebuilds each
runtime table WITHOUT the entity FK (SQLite cannot drop a single FK), preserving data
under `_orphan_ext_*`; roll-forward restore re-attaches and is potentially lossy,
bounded to rows whose `entity` was deleted during the window — and that loss is
LOGGED and PARKED, never silent. This step also EXERCISES the reader (a test),
satisfying "no structure without a reader" for the socle.

## Mini-RECON (Claude Code, pre-implementation — verify live before coding)

Report-only; confirm, then implement.
1. Backup + rollback context: `scripts/backup.py` (manual, 2-file rotation to
   `~/.world_engine/backups/`, CLAUDE.md:471). Quarantine runs AFTER a backup.
2. SQLite FK removal = table rebuild: there is no `ALTER TABLE DROP CONSTRAINT`.
   Confirm the rebuild recipe (create sibling without the FK -> copy rows -> drop
   original -> rename), executed with `PRAGMA foreign_keys` handled correctly during
   the swap. Anchor: `db.py:44`.
3. WHY rename alone fails: while `ext_grimoire.id REFERENCES entity(id)` exists, an
   old-code `DELETE` on `entity` is blocked by a table the old code cannot see.
   Renaming keeps the FK; only the rebuild-without-FK neutralizes it.
4. Manifest + history: `entity_type` (BRIEF-0044-b) statuses include `'quarantined'`;
   `entity_type_history.event` includes `'type_quarantined'` and `'type_restored'`
   (both reserved in the CHECK already). The governed writer's history-append idiom is
   in `writes/schema.py` (BRIEF-0044-c).
5. Test idiom (no pytest in repo): `scripts/test_context.py` — a runnable script that
   asserts + prints, `python scripts/test_*.py`, no live model call.
6. Reconciliation: `_orphan_ext_*` is pattern-accounted by `schema_reconcile.py`
   (BRIEF-0044-d) — confirm quarantine keeps reconciliation green.

## Scope IN

1. **Script `scripts/rollback_quarantine.py`** (manual, deliberate; danger_class
   destructive_data). Two modes:

   **Quarantine (default).** For each `entity_type` row whose `physical_table` is a
   live `ext_*` table (status `active`/`retired`), in one transaction per table:
   - create `_orphan_<physical_table>` with the SAME columns MINUS the entity FK
     (`id TEXT PRIMARY KEY` only; the `REFERENCES entity(id)` dropped) and MINUS any
     other `REFERENCES entity(id)` columns' FK (keep them plain `TEXT`);
   - copy ALL rows across;
   - drop the original `ext_*` table;
   - set `entity_type.status = 'quarantined'`;
   - append `entity_type_history`: `event='type_quarantined'`, `ddl_text=<rebuild DDL>`,
     `definition_snapshot=<current def>`.
   Idempotent + guarded: a type already `quarantined` (its `_orphan_` present) is
   skipped. Print each action.

   **Restore (`--restore`).** For each `quarantined` type, in one transaction:
   - rebuild `<physical_table>` WITH the entity FK restored;
   - for each `_orphan_` row: if its `id`'s `entity` still exists, copy it back; if
     NOT (the lossy edge — `entity` deleted during the window), copy it instead into
     `_orphan_lost_<physical_table>` (created on demand, no FK) and count it;
   - drop the `_orphan_` table only AFTER every row is either re-attached or parked;
   - set `entity_type.status = 'active'`;
   - append `entity_type_history`: `event='type_restored'`, with a
     `definition_snapshot` field recording `lost_count` and the `_orphan_lost_*`
     table name;
   - PRINT a clear summary: N re-attached, M parked in `_orphan_lost_<...>` (never
     silently dropped).

2. **The rollback contract (doc, not code).** State verbatim in ARCHITECTURE_DECISIONS
   and CLAUDE.md: `"Once a runtime type exists, rolling code back past the constructor version requires running scripts/rollback_quarantine.py first (after a backup). Roll-forward restoration (--restore) is potentially lossy, bounded to rows whose entity row was deleted during the rollback window; every lost row is preserved in _orphan_lost_* and reported — never silently dropped. This contract is SQLite-scoped (the rebuild-without-FK recipe is SQLite-specific), matching the engine's current single-backend reality."`

3. **Test `scripts/test_rollback_quarantine.py`** (the B1 reader; runnable, asserts +
   prints, no model call). Against a scratch DB (or clearly-namespaced scratch rows):
   - via `create_entity_type` (BRIEF-0044-c) build a throwaway type `qtest`
     (`ext_qtest`) with one enum column;
   - insert 2 matching `entity` rows + 2 `ext_qtest` rows;
   - run quarantine -> ASSERT: `_orphan_ext_qtest` exists WITHOUT the entity FK,
     `ext_qtest` gone, both rows preserved, `entity_type.status='quarantined'`, a
     `type_quarantined` history row present, and `unaccounted_tables()` returns none
     (orphan pattern-accounted);
   - delete ONE of the two `entity` rows (simulating an old-code delete during the
     window);
   - run `--restore` -> ASSERT: the surviving row is re-attached into a rebuilt
     `ext_qtest` WITH the FK, the orphaned-of-entity row is parked in
     `_orphan_lost_ext_qtest` (NOT dropped), the summary reports `lost=1`, a
     `type_restored` history row records `lost_count=1`, status back to `active`;
   - clean up the scratch artifacts at the end.

## Scope OUT

- Automatic/triggered rollback. Quarantine is manual and deliberate, like
  `backup.py` — no hook, no scheduler, no boot integration.
- Non-SQLite backends. The rebuild-without-FK recipe is SQLite-specific; the contract
  says so. Do not add a Postgres path.
- Preventing the lossy edge (it is inherent: one cannot both let old code mutate
  `entity` freely and guarantee lossless re-attach). The step BOUNDS and LOGS it, it
  does not eliminate it.
- Changing `entity_type`/`entity_type_history` shape beyond USING the already-reserved
  `'quarantined'` status and `'type_quarantined'`/`'type_restored'` events. If a
  CHECK constraint must change to admit them, that is a schema touch -> version bump
  (Claude Code assigns) — but BRIEF-0044-b already reserved all values, so no ALTER
  should be needed; verify.
- UI, AI dispatch, traits.

## Invariants to defend

- **History is sacred** on both quarantine and restore — every transition appends an
  `entity_type_history` row; no in-place erasure.
- **The lossy edge is logged and parked, never silent** — `_orphan_lost_*` + a printed
  summary + a `type_restored` snapshot field. This is the load-bearing honesty
  guarantee of B1.
- **Reconciliation stays green** through quarantine (`_orphan_ext_*` pattern-accounted).
- **Backup before running** (danger_class destructive_data): the script prints a
  refusal-to-run-without-backup reminder or checks for a recent backup file.

## Done means

- [ ] `scripts/rollback_quarantine.py` exists with quarantine + `--restore`, both
      idempotent and guarded.
- [ ] `python scripts/test_rollback_quarantine.py` passes all assertions above and
      prints a clear PASS.
- [ ] After a live quarantine run, `python -m world_engine.schema_reconcile` still
      exits 0.
- [ ] A restore with one entity deleted during the window parks exactly that row in
      `_orphan_lost_*`, reports `lost=1`, and re-attaches the rest.
- [ ] The rollback contract text is present verbatim in ARCHITECTURE_DECISIONS and
      CLAUDE.md.
- [ ] `/review-step` then `/close-step` run.

**Deployment sequence (danger_class: destructive_data):**
backup (`python scripts/backup.py`) -> `python scripts/rollback_quarantine.py`
-> `python -m world_engine.schema_reconcile` (green) -> (on roll-forward)
`python scripts/rollback_quarantine.py --restore` -> review the parked-rows summary.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: "ENTITY-TYPE CONSTRUCTOR — rollback quarantine (B1)";
  the rebuild-without-FK rationale (re `PRAGMA foreign_keys=ON`), the lossy
  roll-forward edge, and the verbatim contract.
- `CLAUDE.md`: the rollback-contract pointer (one-line law + pointer to the ADR).
- Schema changelog: applicatif addendum (or a version bump only if a CHECK actually
  changed — it should not, per BRIEF-0044-b's reservations).
