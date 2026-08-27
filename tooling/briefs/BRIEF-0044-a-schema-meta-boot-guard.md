# BRIEF — Step "schema_meta + fail-closed boot guard (C2 plane 1)"

## Context

TICKET-0044 introduces a third structural-write authority (D2). Consequence #3:
once tables can be born outside migration, the schema version stops describing the
base. Today the version is a doc string only (`world-engine-schema.md:3`, currently
v1.85); no `schema_meta` table exists, and nothing detects DB-vs-code drift
(RECON F2). This step ships plane 1 of the locked C2 two-plane design: a stored
static-plane version plus a fail-closed boot guard. It deliberately does NOT touch
runtime types — plane 2 (reconciliation) is BRIEF-0044-d, and the registry is
BRIEF-0044-b.

## Mini-RECON (Claude Code, pre-implementation — verify live before coding)

Report-only; confirm each anchor on the updated branch, then implement.
1. Boot path: `src/world_engine/cockpit/app.py` startup event exists
   (`@app.on_event("startup")` around app.py:138, currently only a purge). The app
   does NOT call `create_db_and_tables()` on startup — only `scripts/init_db.py:26`
   and some migrations do. Confirm the startup hook is the right guard site.
2. Version source of truth today: `world-engine-schema.md:3`
   (`Current schema version: v1.85`). The changelog header
   (`world-engine-schema-changelog.md`) states the version lives ONLY there — this
   step intentionally adds a code-side constant as the code's expected value;
   confirm the exact header wording before amending it.
3. Infra-stratum models: `src/world_engine/models/pipeline.py` holds app/account
   infra (e.g. `User`). Confirm `schema_meta` belongs there, NOT in `canon.py`
   (it is engine infra, never a world-domain canon table, and MUST stay out of
   `[CANON_TABLES]`).
4. Virgin-head vs migration-backfill pattern: `src/world_engine/writes/prompts.py:63`
   documents the "migration v1 backfill AND seed virgin-head both" idiom. Reuse it
   so a brand-new DB and a migrated DB both end with a seeded singleton.

## Scope IN

1. **New table `schema_meta`** in `src/world_engine/models/pipeline.py` (infra
   stratum). Single-row:
   - `id INTEGER PRIMARY KEY` with `CHECK (id = 1)` (singleton enforced structurally).
   - `static_version TEXT NOT NULL` (e.g. `"v1.86"`).
   - `updated_at TIMESTAMP`.
   Export from `models/__init__.py` alongside the other infra classes.
   `schema_meta` is NOT added to `canon_write_policy.txt [CANON_TABLES]` — it is
   migration-only infra.

2. **Code-side expected-version constant.** New module
   `src/world_engine/schema_version.py` exposing a single constant:
   `EXPECTED_STATIC_SCHEMA_VERSION: str = "vX.YY"` (Claude Code sets the number to
   the version this ticket lands at). This is the code's single source of truth for
   "what static schema the code expects". Add a module docstring stating: migrations
   bump this constant, the `schema_meta` row, and the `world-engine-schema.md`
   header together, in the same commit.

3. **Fail-closed boot guard** in `cockpit/app.py` startup. On startup, open a
   session and read `schema_meta` (single row). Fail closed — refuse to start
   (raise `RuntimeError` with the message below) when:
   - the `schema_meta` table is absent, OR the singleton row is absent, OR
   - `schema_meta.static_version != EXPECTED_STATIC_SCHEMA_VERSION`.
   Verbatim message shape (fill the two versions):
   `"schema_meta says DB is at {db_version!r}, code expects {EXPECTED_STATIC_SCHEMA_VERSION!r} — run pending migrations (scripts/migrate_*.py) before starting."`
   For the absent-table/absent-row case: `"schema_meta is not initialized — run scripts/init_db.py then the migrations."`
   On match: start normally, no log noise.

4. **Migration `scripts/migrate_vX_YY_schema_meta.py`** (guarded, idempotent, two
   independent guards per the v1.77/v1.84 lesson):
   - create `schema_meta` table if absent (`SchemaMeta.__table__.create(engine)`);
   - seed the `id=1` row with the current version if absent; if present, update
     `static_version` to the current version and `updated_at` (a migration is the
     ONLY writer of this row);
   - print what it did; roll back the whole transaction on any error.
   Follow the `migrate_v1_84_location_type_catalog.py` structure exactly.

5. **Extend `scripts/init_db.py` virgin-head path**: after `create_db_and_tables()`,
   seed the `schema_meta` singleton to `EXPECTED_STATIC_SCHEMA_VERSION` if absent
   (so a brand-new DB boots past the guard without a separate migration run).

6. **New verify check `tooling/verify/checks/schema_version_agreement.py`**
   (static, no DB, fail-closed): parse `EXPECTED_STATIC_SCHEMA_VERSION` from
   `schema_version.py` and the `Current schema version:` line from
   `world-engine-schema.md`; FAIL if they differ, if either is unparseable, or if
   zero values were parsed (vacuous-proof). Register it in `tooling/verify/run.py`.

## Scope OUT

- `entity_type` / `entity_type_history` (BRIEF-0044-b) — this step ships no
  registry, no runtime-type awareness.
- The runtime-DDL writer (BRIEF-0044-c).
- Reconciliation / "every physical table accounted for" (BRIEF-0044-d). The boot
  guard here checks the VERSION only, not the physical table set. Do not add any
  table-enumeration logic to this guard.
- Rollback / quarantine (BRIEF-0044-e).
- Per-world versioning. `schema_meta` is GLOBAL static-plane. Runtime types are the
  per-world plane and are not this step's concern — do not add `world_id`.
- Any change to migration NUMBERING policy beyond adding the constant/row bump.

## Invariants to defend

- This step ADDS a boot invariant (version agreement, fail-closed). It threatens no
  existing invariant directly.
- `schema_meta` MUST remain non-canon and migration-only — never reachable from any
  AI-proposal or constructor path. Structural: no writer of it exists outside the
  migration script.
- "Commit before touching any canon-writing path" (CLAUDE.md): the startup hook is
  playability-critical though not itself a canon-write path — commit before editing
  `app.py` startup.

## Done means

- [ ] `schema_meta` table exists with the `CHECK (id = 1)` singleton constraint;
      `SchemaMeta` exported from `models/__init__.py`.
- [ ] `schema_version.py` defines `EXPECTED_STATIC_SCHEMA_VERSION`, equal to the
      `world-engine-schema.md` header line.
- [ ] `python scripts/migrate_vX_YY_schema_meta.py` on an existing DB: creates +
      seeds the row; re-running reports "already present", zero changes.
- [ ] Starting the app with the row absent, or with `static_version` hand-edited to
      a wrong value: app refuses to start with the exact message; restoring the
      correct value -> app starts.
- [ ] `python scripts/init_db.py` on a virgin DB path leaves `schema_meta` seeded so
      the app boots past the guard.
- [ ] `python tooling/verify/run.py --ticket TICKET-0044-socle-entity-type` runs the
      new check; deliberately mismatching the constant vs the doc line turns it red.
- [ ] `/review-step` then `/close-step` run (engine code touched).

**Deployment sequence (danger_class: migration):**
backup (`python scripts/backup.py`) -> `python scripts/migrate_vX_YY_schema_meta.py`
-> (virgin DBs) `python scripts/init_db.py` -> `python tooling/verify/run.py --ticket TICKET-0044-socle-entity-type`.

## Docs to update

- Schema changelog entry (next version `vX.YY`): `schema_meta` table, singleton
  constraint, boot guard, the two-plane rationale (static-plane version, not the
  per-world runtime plane).
- `world-engine-schema-changelog.md` header note: the version now ALSO lives in the
  `schema_version.py` code constant (the doc line and the constant are kept equal by
  `schema_version_agreement.py`); the doc remains the human-facing source.
- `ARCHITECTURE_DECISIONS.md`: new section "SCHEMA VERSION — two-plane governance
  (C2), plane 1: stored static version + fail-closed boot guard" (TICKET-0044,
  BRIEF-0044-a).
- `CLAUDE.md`: invariant "the app refuses to boot when `schema_meta.static_version`
  != `EXPECTED_STATIC_SCHEMA_VERSION`"; File-structure pointer for `schema_version.py`.
