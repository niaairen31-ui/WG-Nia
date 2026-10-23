<!-- slug: schema-v2-31 -->
# BRIEF 0125-B — "Schema v2.31: a world opens to players; the journal admits a perspective"

Lot: LOT-0125-player-entry.md (authoritative on conflict)
Depends on: BRIEF-0125-A (commit order only)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.30"` (R-02).
- `world-engine-schema.md:3` -> `Current schema version: v2.30`; newest
  changelog entry `- **v2.30**` (R-02).
- `src/world_engine/models/canon.py:65-93` -> `World` with `tone` then
  `is_active`, no `open_to_players` (R-03).
- `src/world_engine/models/pipeline.py:467-492` -> `LORE_USAGE_STEPS` with
  two kinds and the CHECK literal of R-11.
- `src/world_engine/writes/lore_usage.py:27-33` -> `PAYLOAD_KEYS` with five
  steps (R-11).
- `tooling/verify/checks/lore_usage.py:139` -> `_SCRIPTS` holds exactly
  `migrate_v2_13_lore_usage.py` and `export_lore_usage.py` (R-12).
- `scripts/migrate_v2_29_rank_trials.py:141-157` -> `_create_from_model`
  and `_rebuild` as R-13.

Halt if any has moved.

## Facts carried

### R-02 -- schema version
Opened: `src/world_engine/schema_version.py:15`, `world-engine-schema.md:3`,
`world-engine-schema-changelog.md:16`.
Finding: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.30"`; the schema doc
header reads `Current schema version: v2.30`; the newest changelog entry is
`- **v2.30** -- TICKET-0124, BRIEF-0124-A`.
Consequence: this lot's migration is v2.31 (`schema_version_agreement.py`
and `schema_partition.py` require the constant, the header and the newest
changelog entry to agree).
### R-03 -- `world` table
Opened: `src/world_engine/models/canon.py:65-93` (the declaring model).
Finding: `World` has `id, name, description, tone, is_active,
current_phase, created_at, updated_at`; `__table_args__` holds the partial
unique index `idx_world_one_active` and the CHECK `ck_world_current_phase`.
No player-visibility column. `canon.py` is 961 lines (budget 1000).
Consequence: B adds `open_to_players: bool` (`server_default 0`, NOT NULL)
after `tone`; `canon.py` stays under budget (+4 lines).
### R-11 -- the Lore usage journal (declaring model and writer)
Opened: `src/world_engine/models/pipeline.py:467-504`,
`src/world_engine/writes/lore_usage.py:1-70`, `src/world_engine/lore_usage.py`.
Finding: `LORE_USAGE_STEPS = {"write": ("questions","draft","commit"),
"consult": ("ask","resolve")}`; `LoreUsageEvent.__table_args__` holds
`ck_lore_usage_event_step` with the literal `"(kind = 'write' AND step IN
('questions','draft','commit')) OR (kind = 'consult' AND step IN
('ask','resolve'))"`, `ck_lore_usage_event_outcome`, `ck_lore_usage_event_entry`
and indexes `idx_lore_usage_event_attempt (attempt_id, created_at)`,
`idx_lore_usage_event_world (world_ref, created_at)`.
`writes/lore_usage.PAYLOAD_KEYS` is keyed by **step** (`questions, draft,
commit, ask, resolve`); `write_usage_event` refuses a step not in
`LORE_USAGE_STEPS[kind]` and a payload whose key set differs from
`PAYLOAD_KEYS[step]`, and requires `payload["error"] is None` iff outcome
`ok`. `lore_usage.stage/record(db, *, attempt, world_id, kind, step,
outcome, payload, exchanges=None, lore_entry_ref=None)`.
Consequence: a perspective kind needs step names unique across kinds
(`perspective_ask`, `perspective_resolve`), two `PAYLOAD_KEYS` entries, and
a table rebuild (the CHECK is in the DDL).
### R-12 -- `lore_usage.py` check (a gate B and E must pass)
Opened: `tooling/verify/checks/lore_usage.py:1-140, 205-217`.
Finding: U0 requires the files under `src/world_engine` naming the journal
to equal `_NAMING_FILES = {models/pipeline.py, models/__init__.py,
writes/lore_usage.py}`, the callers of `write_usage_event` to equal
`{writes/lore_usage.py, lore_usage.py}`, and the scripts naming the journal
to equal `_SCRIPTS = {migrate_v2_13_lore_usage.py, export_lore_usage.py}`.
U1 requires `ck_lore_usage_event_step` to list exactly the pairs of
`LORE_USAGE_STEPS`. U2 runs `migrate_v2_13_lore_usage.py` (its own literal
DDL, lines 72-100) and compares CHECK **names** only. U10 requires the two
routes in `_ROUTES` not to call `write_usage_event`. The check already runs
close to `corpus_gate.py`'s 15-second timeout (TICKET-0123 handover).
Consequence: B adds `migrate_v2_31_player_entry.py` to `_SCRIPTS` (it names
the table) and changes nothing else in this check; the v2.31 migration is
proven in a new check. Routes of E name `lore_usage` (the recorder) only,
never the table, and never call `write_usage_event`.
### R-13 -- rebuild migration pattern
Opened: `scripts/migrate_v2_29_rank_trials.py:135-175`,
`scripts/migrate_v2_30_world_tone.py` (whole).
Finding: v2.30 refuses below `_PREVIOUS_VERSION`, applies in one raw
transaction (`PRAGMA foreign_keys=OFF`, `BEGIN`, DDL, `COMMIT`,
`PRAGMA foreign_keys=ON`), post-checks, then converges `schema_meta`.
v2.29's `_rebuild(cursor, model, columns)` drops the table's named indexes,
renames it `<table>_old`, creates it from `CreateTable(model.__table__)` and
its `CreateIndex`es, copies `columns`, drops `_old`.
Consequence: B's migration follows v2.30's skeleton and v2.29's `_rebuild`
(copied into the new script, as each migration script is standalone).
### R-34 -- DB fixture pattern for a check
Opened: `tooling/verify/checks/world_sheet.py:47-62` (`_fresh_engine`),
`:213-240` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_engine()` makes a temp dir, sets
`WORLD_ENGINE_DATABASE_URL=sqlite:///<tmp>/check.db` and
`WORLD_ENGINE_ENV=test` (setdefault), puts `src` on `sys.path`, drops every
cached `world_engine` module, imports `world_engine.models`, then
`SQLModel.metadata.create_all(engine)` with `world_engine.db.engine`. Route
functions are then called directly with a `Session`. `main()` runs each rule
in `try/except Exception`, turning a crash into a failure, and prints
`FAIL:` lines / one `PASS:` line.
Consequence: every new DB-backed check of this lot builds its database with
this `_fresh_engine` body (copied: each check is standalone) and never
touches Nia's database.

## Contracts

### C-09 -- journal kind `perspective`
Produced by: B   Consumed by: E
`LORE_USAGE_STEPS["perspective"] = ("perspective_ask", "perspective_resolve")`.
`PAYLOAD_KEYS["perspective_ask"] = {"question","perspective","asked_by","response","withheld","error"}`;
`PAYLOAD_KEYS["perspective_resolve"] = {"question","perspective","asked_by","plan","bindings","response","withheld","error"}`.
`perspective` is `"public"`; `asked_by` is `"creator"` or
`"player:<user_id>"`; `withheld` is C-07's list, or `[]` when the step did
not execute a plan.
CHECK `ck_lore_usage_event_step` gains `OR (kind = 'perspective' AND step IN
('perspective_ask','perspective_resolve'))`.

## Context

The player sees only worlds Nia opened (C1), and every perspective question
is journaled (H1-c). Both need schema: a column on `world`, and a journal
CHECK that admits a third kind. This brief is the only migration of the lot.

## Scope IN

1. `models/canon.py`, `World`, right after `tone`:
   ```python
   # Creator-set « Ouvert aux joueurs » (v2.31, TICKET-0125, C1): the world
   # is listed in the player shell. Player routes never read `is_active`.
   open_to_players: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
   ```
2. `models/pipeline.py`: `LORE_USAGE_STEPS` gains
   `"perspective": ("perspective_ask", "perspective_resolve")`; the CHECK
   `ck_lore_usage_event_step` literal becomes
   `"(kind = 'write' AND step IN ('questions','draft','commit')) "`
   `"OR (kind = 'consult' AND step IN ('ask','resolve')) "`
   `"OR (kind = 'perspective' AND step IN ('perspective_ask','perspective_resolve'))"`.
3. `writes/lore_usage.py`: `PAYLOAD_KEYS` gains the two entries of C-09,
   verbatim; its comment gains one line: "perspective steps (TICKET-0125):
   `perspective` is `public`, `asked_by` `creator` or `player:<user_id>`,
   `withheld` the audit's lines."
4. New `scripts/migrate_v2_31_player_entry.py`, built on
   `migrate_v2_30_world_tone.py`'s skeleton (R-13: env guard, `_refuse`
   below `v2.30`, one raw transaction with `PRAGMA foreign_keys=OFF` /
   `BEGIN` / `COMMIT` / `PRAGMA foreign_keys=ON`, `_post_checks`,
   `_converge_schema_meta` to `v2.31`), docstring "Migration v2.31 — a world
   opens to players; the Lore journal admits the perspective kind
   (TICKET-0125, BRIEF-0125-B; decisions C1, H1-c)." Applies, each only when
   still needed:
   - `ALTER TABLE world ADD COLUMN open_to_players BOOLEAN NOT NULL DEFAULT 0`
     (needed when the column is absent);
   - `lore_usage_event` rebuilt with v2.29's `_rebuild` procedure (copied
     with `_create_from_model` into this script), columns `id, attempt_id,
     world_ref, world_name, kind, step, outcome, payload, model_calls,
     lore_entry_ref, created_at` (needed when the stored table SQL, read
     from `sqlite_master`, lacks `'perspective'`).
   Post-checks: `world` holds `open_to_players`; the stored
   `lore_usage_event` SQL holds `'perspective_ask'`; the journal's row
   count is unchanged by the rebuild (count before, count after).
   Writes no data other than the copy.
5. `schema_version.py`: `"v2.31"`. `world-engine-schema.md`: header
   `Current schema version: v2.31`; in `CREATE TABLE world`, after `tone`,
   `open_to_players       BOOLEAN NOT NULL DEFAULT FALSE,  -- creator-set « Ouvert aux joueurs » (v2.31, TICKET-0125, C1); player shell lists it`;
   in `### lore_usage_event`, the CHECK gains the perspective line and the
   prose gains: "Perspective questions (v2.31, TICKET-0125) are journaled
   as kind `perspective`, steps `perspective_ask` / `perspective_resolve`,
   with who asked and the lines withheld."
6. `world-engine-schema-changelog.md`, newest entry first:
   `- **v2.31** — TICKET-0125, BRIEF-0125-B: a world opens to players, and
   the Lore journal admits the perspective kind. `world` gains
   `open_to_players` (BOOLEAN NOT NULL DEFAULT 0, C1). `lore_usage_event` is
   rebuilt: its step CHECK admits `kind = 'perspective'` with steps
   `perspective_ask` and `perspective_resolve` (H1-c); rows are copied
   unchanged. `migrate_v2_31_player_entry.py` writes no other data.`
7. `tooling/verify/checks/lore_usage.py`: `_SCRIPTS` gains
   `"migrate_v2_31_player_entry.py"` (it names the table, R-12). Nothing
   else in this file changes.
8. New check `tooling/verify/checks/player_entry_schema.py`, docstring first
   sentence "G1 check for TICKET-0125 (BRIEF-0125-B) -- schema v2.31: a world
   opens to players and the Lore journal admits the perspective kind.",
   rules:
   - **PS1** -- static: `World.open_to_players` exists, NOT NULL, server
     default `0`; `LORE_USAGE_STEPS["perspective"] == ("perspective_ask",
     "perspective_resolve")`; `PAYLOAD_KEYS` holds both steps with exactly
     C-09's keys.
   - **PS2** -- migration, on a fixture (R-34 `_fresh_engine`, then reshaped
     to v2.30: `ALTER TABLE world DROP COLUMN open_to_players`; drop
     `lore_usage_event` and recreate it with the literal DDL of
     `migrate_v2_13_lore_usage.py`'s `_create_table`, imported, not copied;
     one journal row inserted raw; `schema_meta` set to `v2.30`): (a) at
     `v2.29` the script exits non-zero and changes nothing; (b) at `v2.30`
     it exits zero, `world.open_to_players` exists with default 0, the
     stored journal SQL holds `'perspective_ask'`, the raw row is still
     there unchanged, `schema_meta` reads `v2.31`; (c) a second run exits
     zero and changes nothing; (d) a row written by `write_usage_event`
     with kind `perspective` reads back, and a raw INSERT with kind
     `perspective`, step `ask` is refused by the database.
   The script runs as a subprocess with `WORLD_ENGINE_DATABASE_URL` set to
   the fixture. PASS line: `PASS: player_entry_schema -- v2.31: world.open_to_players and the perspective journal kind, migration idempotent and refusing below v2.30`.

## Scope OUT

- No reader of `open_to_players` in this brief (C reads it).
- No perspective route, no journal write of the new kind (E).
- `migrate_v2_13_lore_usage.py` is not edited.
- No new index, no new table.
- Every later brief of this lot.

## Invariants to defend

- INV-59: the journal is written only through `lore_usage` and read only by
  `export_lore_usage.py`. The migration copies rows; nothing in `src/`
  reads them.
- INV-60: the boot guard compares `schema_meta` with the constant; both move
  to v2.31 in this brief, only through the migration for `schema_meta`.
- History is sacred: the rebuild copies every row; the post-check counts
  them.

## Decision rights

STOP:
- an anchor has moved;
- the rebuild would lose or alter a row (post-check count differs);
- SQLite refuses `ALTER TABLE ... DROP COLUMN` in the fixture (the check
  then needs another way to build a v2.30 shape: a decision for Nia).
ADAPT:
- the Python attribute order in `World` differs from the anchor: place the
  column right after `tone` anyway;
- `_fresh_engine` in the new check needs `scripts` on `sys.path` to import
  `migrate_v2_13_lore_usage`: add it.
REPORT-ONLY:
- the U2 rule of `lore_usage.py` takes longer than before.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/player_entry_schema.py` PASS.
- [ ] `python tooling/verify/checks/lore_usage.py` PASS (U0 with the new
      script, U1 with the new CHECK).
- [ ] `schema_version_agreement.py` and `schema_partition.py` PASS.
- [ ] Named mutation PS2b: removing the journal rebuild from the script's
      plan makes PS2b fail (then revert).
- [ ] Named mutation PS1: dropping `"perspective"` from `LORE_USAGE_STEPS`
      makes PS1 fail (then revert).
- [ ] `corpus_gate.py` passes (`WORLD_ENGINE_ENV=test`).
- [ ] Live (Nia): after a backup (`scripts/backup.py`), the migration runs
      on her database and the cockpit boots.
- [ ] `/review-step` and `/close-step`.

## Docs to update

- Schema doc and changelog (Scope IN 5, 6).
- `ARCHITECTURE_DECISIONS.md` entry above the footer:
  `## A world opens to players; the journal admits perspectives (BRIEF-0125-B, schema v2.31)`.
- Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.
