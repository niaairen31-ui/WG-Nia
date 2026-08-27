# BRIEF — Step "engine transactional-DDL setup (unblocks A1 atomicity)"

## Context

BRIEF-0044-c's live gate proved the A1 invariant does not hold on this engine:
`db.py`'s pysqlite setup uses the driver default, under which `CREATE TABLE`
auto-commits and does NOT roll back with the surrounding row writes. A1 (the
"(CREATE + INSERT entity_type + INSERT history) are one transaction" guarantee) is
structural, so it stays as written; the engine must be made to honor it. This is a
SHARED-engine change (every canon-write path and every migration uses this engine),
so it lands as its own brief and COMMITS BEFORE BRIEF-0044-c. 0044-c's code is
complete and correct; only its acceptance test fails, and that test must pass
UNCHANGED once this brief lands.

**Lesson carried in (do not repeat it):** 0044-c's mini-RECON asserted this
behavior "(it does)" and was wrong. This brief's mini-RECON below therefore requires
EMPIRICAL confirmation of every engine/driver claim against the installed
SQLAlchemy version. Treat the recipe in Scope IN as a starting point to verify, not
as trusted fact.

## Mini-RECON (Claude Code, pre-implementation — verify live, REPORT before coding)

Report-only. Do NOT trust any claim below without reproducing it.
1. Installed SQLAlchemy major version (`pip show sqlalchemy`; `sqlmodel>=0.0.16`
   pins 1.4.x or 2.0.x). The exact incantation for the "begin" listener differs by
   major version — confirm which, and confirm the working call
   (`conn.exec_driver_sql("BEGIN")` vs `conn.execute(text("BEGIN"))`) by running it.
2. Current `db.py` engine setup: the `@event.listens_for(Engine, "connect")`
   listener `_enable_sqlite_foreign_keys` (db.py ~:44), guarded by
   `engine.dialect.name == "sqlite"`, which runs `PRAGMA foreign_keys=ON`. Confirm
   whether it listens on the `Engine` CLASS or the `engine` INSTANCE, and whether the
   PRAGMA must (as expected) run outside any transaction — with `isolation_level=None`
   the connect-time PRAGMA runs in autocommit, which is correct; VERIFY it still fires.
3. **Regression surface — enumerate and empirically replay (this is the gate):**
   a. Every `scripts/migrate_*.py` that does `Model.__table__.create(engine)` or raw
      DDL outside a session: replay each on a SCRATCH DB copy under the new setup and
      confirm the table/index actually lands and commits (the risk: explicit BEGIN
      changes when the DDL commits).
   b. `scripts/init_db.py` (`create_db_and_tables()` -> `metadata.create_all`) — confirm
      a virgin DB still fully creates under the new setup.
   c. Session usage across canon-write paths: `engine.begin()` vs `Session(engine)`
      vs bare `connect()` — confirm no path relied on pysqlite's implicit
      commit-before-DDL (expected: none; FLAG any found).
   d. The BRIEF-0044-a boot guard + BRIEF-0044-d reconciliation (if already landed):
      confirm they still read `schema_meta` / enumerate tables normally.
   Put this replay result in the RECON note / QUESTION file so the regression is
   documented, not assumed.

## Scope IN

1. **`src/world_engine/db.py` — transactional-DDL configuration**, SQLite-guarded so
   the stated future Postgres/Supabase path is untouched. Starting recipe (VERIFY per
   mini-RECON before trusting):
   - In the existing connect listener (or a sibling connect listener, same
     `dialect.name == "sqlite"` guard), set
     `dbapi_connection.isolation_level = None` — disables pysqlite's automatic BEGIN
     emission and its COMMIT-before-DDL. Keep the existing `PRAGMA foreign_keys=ON`
     in the same connect path (it runs in autocommit at connect time — correct).
   - Add an engine `"begin"` listener that emits an explicit `BEGIN` (the exact call
     confirmed empirically in mini-RECON), guarded to sqlite.
   The net structural guarantee (state it in the module docstring, verbatim):
   `"On SQLite, DDL participates in the surrounding transaction: a CREATE TABLE emitted before a failed commit is rolled back with the rest. Transactional DDL is a structural guarantee of this engine, not a per-site precaution."`

2. **Atomicity test `scripts/test_ddl_atomicity.py`** (runnable, asserts + prints, no
   model call — `scripts/test_context.py` idiom). Against a scratch DB:
   - open a transaction, `CREATE TABLE ext_attest (id TEXT PRIMARY KEY)`, then raise
     before commit / call `rollback()`; ASSERT `ext_attest` does NOT exist afterwards;
   - open a transaction, create it, commit; ASSERT it DOES exist; clean up.
   This is the engine-level proof; 0044-c's A1 test (3-write atomicity through
   `create_entity_type`) is the higher-level proof and is NOT part of this brief.

## Scope OUT

- `writes/schema.py` / `create_entity_type` and its A1 acceptance test (BRIEF-0044-c).
  This brief only makes the engine honor atomicity; 0044-c consumes it unchanged.
- Any change to WHAT the canon-write paths write, or to the canon-write policy.
- 0045's `ADD COLUMN` and 0044-e's rebuilds — they benefit from this fix but are not
  wired here.
- A Postgres/Supabase transactional path — untouched; the change is sqlite-guarded.
- Broadening or narrowing A1 (it stays exactly as authored in 0044-c).

## Invariants to defend

- **Commit before touching any canon-writing path (hard).** This IS the shared engine
  every canon-write path uses — the maximally sensitive version of the rule. Commit a
  clean tree before editing `db.py`. (Operationally: 0044-c's uncommitted work is
  parked/stashed by Nia before this brief runs, so this brief starts on a clean tree.)
- **Transactional DDL is now a structural guarantee** (module docstring) — not a
  claim any future brief may weaken to a per-site workaround.
- **No migration regresses.** Every existing `migrate_*.py` must still land its
  DDL and commit under the new setup — proven by the mini-RECON replay, not assumed.
- FK enforcement (`PRAGMA foreign_keys=ON`) must still fire on every connection.

## Done means

- [ ] `python scripts/test_ddl_atomicity.py` passes: DDL rolls back with the
      transaction, and commits when the transaction commits.
- [ ] Mini-RECON replay result recorded: every `migrate_*.py` + `init_db.py` still
      creates + commits its tables/indexes on a scratch DB under the new engine.
- [ ] `PRAGMA foreign_keys=ON` still verified active on a fresh connection.
- [ ] Existing verify suite green (no `no_print_in_src` / `import_cycle` /
      `function_length` regression from the `db.py` edit).
- [ ] The change is sqlite-guarded (a non-sqlite URL path is unaffected — reasoned or
      shown).
- [ ] **Handoff check:** after this commits, re-running BRIEF-0044-c's A1 acceptance
      test (force a failure between `CREATE TABLE` and the second INSERT) leaves NONE
      of the three — WITHOUT any edit to 0044-c's code.
- [ ] `/review-step` then `/close-step` run.

**Deployment sequence (danger_class: db_write; shared engine):**
Nia parks 0044-c's uncommitted work (stash / WIP) -> clean tree -> commit boundary ->
backup (`python scripts/backup.py`) -> implement `db.py` + test -> mini-RECON replay ->
`python scripts/test_ddl_atomicity.py` -> `/review-step` -> `/verify` -> **commit f** ->
Nia restores 0044-c's work -> re-run 0044-c A1 test (must pass unchanged) -> commit c.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: section "ENGINE — transactional DDL on SQLite
  (unblocks A1)"; record the pysqlite default that broke atomicity, the
  isolation_level=None + explicit-BEGIN fix, the sqlite guard, AND the process lesson
  (a mini-RECON "confirm X (it does)" proved false; engine/driver claims in briefs are
  asserted-then-verified, never trusted — the verify step is load-bearing for exactly
  this).
- `CLAUDE.md`: invariant "on SQLite, DDL participates in the surrounding transaction
  (transactional DDL is a structural engine guarantee)"; File-structure note if a new
  test script is added.
- Schema changelog: applicatif addendum (engine transaction semantics — no schema
  version bump; no table changed).
