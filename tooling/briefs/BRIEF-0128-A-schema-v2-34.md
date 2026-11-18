<!-- slug: schema-v2-34 -->
# BRIEF 0128-A — "Schema v2.34: the active PC, the day's pin, publication and failures"

Lot: LOT-0128-player-day.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

- `git log --oneline -1` on the branch base is `055b890` (or a descendant
  that touches none of the files below).
- `world-engine-schema.md:3` is `Current schema version: v2.33`;
  `src/world_engine/schema_version.py:15` is
  `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.33"`.
- `src/world_engine/models/canon.py:93` declares `current_phase`, `:94`
  `created_at`; `canon.py:34-44` imports `Column`, `ForeignKey`, `String`.
- `src/world_engine/models/pipeline.py`: `class PassPlay` at `:62`, its last
  field `applied_at: Optional[datetime] = None` at `:93`, the
  `proposed_mutation` section comment at `:96-98`, `class ProposedMutation`
  at `:99`.
- `src/world_engine/writes/pipeline.py:62` is `PASS_PLAY_STATUSES:
  tuple[str, ...] = ("submitted", "resolving", "resolved", "flagged")`.
- `src/world_engine/writes/worlds.py:85-86` ends
  `_DIRECT_WORLD_SCOPED_DELETES` with `"creation_rules", "pc_draft",
  "pc_draft_skill", "pc_draft_sketch",` / `"pc_draft_membership",
  "pc_draft_knowledge",` then `)`.
- `tooling/verify/checks/review_schema.py:271` is `if
  EXPECTED_STATIC_SCHEMA_VERSION != "v2.33":`.
- `tooling/verify/checks/world_cascade.py:168-169` is the `pass_play`
  fixture row; `_build_world` at `:348-360`.
- `grep -rnw "DayRunFailure\|DAY_RUN_STAGES\|DAY_RUN_FAILURE_CODES\|published_at\|published_text\|active_pc_id" src tooling/verify`
  answers nothing.

Halt if any anchor has moved.

## Facts carried

### R-01 -- the base, the version, the free ids
Opened: `git log --oneline -1` (`055b890 Merge pull request #159 from
niaairen31-ui/ticket/0131`); `world-engine-schema.md:3`;
`src/world_engine/schema_version.py:15`; `python
tooling/verify/checks/claude_md_contract.py` (« 69 invariants »).
Finding: `Current schema version: v2.33`; `EXPECTED_STATIC_SCHEMA_VERSION:
str = "v2.33"`; the corpus holds INV-01 to INV-69 (INV-69 in
`.claude/rules/frontend.md:43`).
Consequence: A moves the schema to v2.34; B adds INV-70, D INV-71; G amends
INV-66.

### R-05 -- the world row
Opened: `src/world_engine/models/canon.py:30-46, 65-95` (the declaring file).
Finding: `World` (`__tablename__ = "world"`): `id, name, description, tone,
open_to_players, is_active, current_phase, created_at, updated_at`;
`__table_args__` holds `idx_world_one_active` (unique on `is_active` WHERE
`is_active = 1`) and `ck_world_current_phase`. `current_phase` is at :93,
`created_at` :94, `updated_at` :95. `canon.py` imports `Column`,
`ForeignKey`, `String` from `sqlalchemy` (:34-44). `Character` is declared
later in the same module (:150) with `world_id` FK to `world`. Measured in
a scratch copy of the clone (reverted): adding `active_pc_id:
Optional[str] = Field(default=None, sa_column=Column(String,
ForeignKey("character.id", ondelete="SET NULL"), nullable=True))` after
`current_phase` makes `SQLModel.metadata.create_all` emit `FOREIGN
KEY(active_pc_id) REFERENCES character (id) ON DELETE SET NULL` with no
warning; a raw `DELETE FROM character` of the active PC leaves
`world.active_pc_id` NULL; `world_cascade.py`, `pc_resolution.py`,
`schema_reconciliation.py` and `schema_partition.py` stay green.
Consequence: C-01 declares the column so; the world <-> character FK cycle
is harmless under SQLite.

### R-06 -- the day row and its statuses
Opened: `src/world_engine/models/pipeline.py:62-93` (the declaring file);
`src/world_engine/writes/pipeline.py:1-66, 78-101`; the enumeration below.
Finding: `PassPlay` (`pass_play`): `id, batch_id, session_id, character_id
(FK entity), agenda_id, declared_action, injected_context JSON,
creator_notes, status (server default 'submitted'), batch_order, history
JSON, submitted_at, applied_at`; indexes `idx_passplay_batch`,
`idx_passplay_agenda`; no CHECK on `status`. `applied_at` is the last
field (:93). `PASS_PLAY_STATUSES: tuple[str, ...] = ("submitted",
"resolving", "resolved", "flagged")` (`writes/pipeline.py:62`); the module
docstring (:23-25) says `flagged` « is reserved for a future input
classifier and is never written by anything in this module ».
`write_pass_play(db, *, batch_id, session_id, character_id,
declared_action)` (:78-101) is the one constructor (pipeline_wiring R3).
Readers of the statuses:
```
$ grep -rn "PASS_PLAY_STATUSES\|\"flagged\"\|'flagged'" src tooling/verify --include=*.py
src/world_engine/writes/__init__.py:213:    PASS_PLAY_STATUSES,
src/world_engine/writes/pipeline.py:23:and commits. `PASS_PLAY_STATUSES` is declared here because `routes/day.py`
src/world_engine/writes/pipeline.py:62:PASS_PLAY_STATUSES: tuple[str, ...] = ("submitted", "resolving", "resolved", "flagged")
src/world_engine/cockpit/routes/day.py:141:    # `status` is the pass_play lifecycle (PASS_PLAY_STATUSES) -- the
tooling/verify/checks/pipeline_wiring.py:13:R4 (no restated literal): `MAX_DECLARATION_CHARS` and `PASS_PLAY_STATUSES`
tooling/verify/checks/pipeline_wiring.py:193:    """R4: MAX_DECLARATION_CHARS and PASS_PLAY_STATUSES are module-level
tooling/verify/checks/pipeline_wiring.py:202:                    if isinstance(target, ast.Name) and target.id in ("MAX_DECLARATION_CHARS", "PASS_PLAY_STATUSES"):
tooling/verify/checks/pipeline_wiring.py:205:                if node.target.id in ("MAX_DECLARATION_CHARS", "PASS_PLAY_STATUSES"):
tooling/verify/checks/pipeline_wiring.py:208:    for required in ("MAX_DECLARATION_CHARS", "PASS_PLAY_STATUSES"):
```
Writers of `pass_play.status`: `cockpit/day_plan_finalize.py:154, 212`,
`cockpit/day_reconcile_apply.py:120, 175` (`"resolving"`),
`routes/day.py` (`_finalize_resolution`, `"resolved"`); readers:
`writes/quests.py:261` (`abandon_refusal`, `== "resolving"`), the day
loaders. `pass_play` is not a canon table (`canon_write_policy.txt:1-13`).
Consequence: `flagged` gets its writer (C-09); `abandoned` joins the tuple
(Z1); the new columns are plain, the status stays CHECK-free.

### R-08 -- the world cascade
Opened: `src/world_engine/writes/worlds.py:37-87, 118-170`;
`tooling/verify/checks/world_cascade.py:1-36, 69-75, 111, 126, 168-169,
275-325, 348-360`.
Finding: `_SUBQUERY_SCOPED_DELETES` (:38-58) deletes `pass_play` by
`session_id`; `_DIRECT_WORLD_SCOPED_DELETES` (:63-87) deletes world-scoped
tables by `world_id`, in any order under `PRAGMA defer_foreign_keys = ON`;
the world row goes last. `world_cascade.py` W1 requires every
world-reaching table of the metadata (a `world_id` column or an FK chain to
`world`; `world` itself excluded, :279-289) to be named exactly once; W3
requires one `_FIXTURE` row per cascaded table; the fixture's PC-capable
row is `("character", {"id": "{w}-char", ..., "character_type": "npc"})`
(:75), its day `("pass_play", {"id": "pp-{w}", "batch_id": "bat-{w}",
"session_id": "ses-{w}", "character_id": "{w}-char", "declared_action":
"a"})` (:168-169); worlds are inserted by `INSERT INTO world (id, name,
is_active) VALUES (:w, :w, 0)` (:353).
Consequence: `day_run_failure` (world_id) joins the direct list and gets a
fixture row; `world.active_pc_id` needs no cascade entry.

### R-09 -- the migration shape
Opened: `scripts/migrate_v2_33_creator_review.py:1-245`.
Finding: the env guard (:41-50: refuses without `WORLD_ENGINE_ENV` or
`WORLD_ENGINE_DATABASE_URL`); `_PREVIOUS_VERSION` / `_THIS_VERSION`;
`_version_key`, `_refuse` (below the previous version: `SystemExit` naming
the stored version), `_tables`, `_columns`, `_indexes`,
`_create_from_model` (CREATE TABLE and its indexes compiled from the
model), `_plan()` returning only what is missing, `_apply()` in one raw
transaction (`PRAGMA foreign_keys=OFF`, `legacy_alter_table=ON`, `BEGIN`
... `COMMIT`), `_post_checks` (`SystemExit` on any problem),
`_converge_schema_meta`, `main()` printing « Applied: ... » or « Nothing to
do. ».
Consequence: A's script copies these pieces; its idempotence key for the
W1 backfill is « `pass_play.published_at` absent before the run » (C-01).

### R-10 -- the schema documents and their checks
Opened: `world-engine-schema.md:1-46, 913-980`;
`world-engine-schema-changelog.md:1-20`;
`tooling/verify/checks/schema_partition.py:1-60`;
`tooling/verify/checks/schema_version_agreement.py` (run: PASS v2.33);
`tooling/verify/checks/review_schema.py:262-275`.
Finding: one `Current schema version: v2.33` line (:3); the `world` section
(:22-46) lists the columns in a `CREATE TABLE world (...)` block with a
comment per column; the `pass_play` section (:950-978) likewise; the
changelog lists `- **vX.YY** — TICKET-..., BRIEF-...: ...` newest first
under `## CHANGELOG` (:14-16). `schema_partition.py` asserts the newest
changelog entry equals the header version. `review_schema.py:271` asserts
`EXPECTED_STATIC_SCHEMA_VERSION != "v2.33"` is a failure -- it goes red
the moment the version moves. `creation_schema.py:342` already reads
`_version_key(EXPECTED_STATIC_SCHEMA_VERSION) < _version_key("v2.32")`.
Consequence: A edits the doc and the changelog per C-01 and relaxes
`review_schema.py:271` to « at least v2.33 » in the `creation_schema.py:342`
form.

### R-30 -- name bans across `src/`
Opened: `tooling/verify/checks/lore_as_facts.py:36-46`;
`knowledge_identity.py:25-35`; `event_contexts.py:72`;
`quest_rewards.py:170-180`; `skill_progression.py:180`.
Finding: an attribute named `appearance, backstory, secrets, philosophy,
internal_structure, internal_tensions, aversion, goals` is banned outside
`models/`; K3 counts `subject` references against a census; `DROPPED =
("knowledge_status", "occurred_at", "has_magic_impact", "consequences")`;
RA1 bans `.owner_id`, `.location_id`, `.equipped` on an item-shaped read;
`tier` is banned as a skill key.
Tested against every name this lot introduces (`active_pc_id`,
`quest_id`, `published_text`, `published_at`, `day_run_failure`, `stage`,
`code`, `reason`, `resolve_active_pc`, `active_pc_id_or_none`,
`world_player_characters`, `write_active_pc`, `clear_active_pc_of`,
`enqueue_day`, `run_day`, `interrupt_stale_days`, `start_day_runner`,
`running_day`, `queued_count`, `failure_of`, `write_day_run_failure`,
`reopen_day`, `abandon_day`, `publish_day`, `declare`, `_day_world`,
`_day_character`, `can_declare`, `state`, `text`): none is banned; no new
code reads `.subject`.
Consequence: none.

### R-32 -- the arrow floor and the gate
Opened: `tooling/verify/checks/pipeline_state.py:54, 113-120`;
`tooling/verify/checks/corpus_gate.py:20-60`.
Finding: for a ticket in `brief`, `exec`, `verify`, `live-gate` or `done`,
every Machine-checkable arrow must name an existing file under
`tooling/verify/checks/`; `corpus_gate.py` runs each check with a 15 s
timeout (`TIMEOUT_SECONDS`) unless listed in `SLOW_CHECK_TIMEOUTS`.
Consequence: while 0128 is in `exec`, `pipeline_state.py` (and with it
`corpus_gate.py`) is red for each arrow whose check a later brief creates:
`day_schema.py` until A, `active_pc_selector.py` until C,
`day_chain_world.py` until D, `day_runs.py` until E, `day_publication.py`
until F, `player_journee.py` until G. Every Done means names that red.

### R-33 -- the module map and the build
Opened: `tooling/verify/checks/file_map.py:1-40`;
`tooling/verify/checks/frontend_build_fresh.py` (run: PASS, 168 sources,
3 assets).
Finding: `FILE_MAP.md` must equal a fresh render of every module's first
docstring sentence (`python tooling/glue/gen_file_map.py`); the committed
frontend build must match its sources' hash.
Consequence: every brief that adds a Python module regenerates the map;
every brief that edits `frontend/src` runs `npm run build` in `frontend/`
and commits the output.

### R-34 -- no JSON for what anyone sees
Opened: `tooling/verify/checks/json_ui_boundary.py` (run: PASS).
Finding: volet c fails any `Column(JSON` under `models/` absent from its
allowlist.
Consequence: every new column is relational (C-01); the failure reason is a
text column, never `pass_play.history` (L1).

### R-35 -- the check fixture idiom
Opened: `tooling/verify/checks/pc_resolution.py:44-58`;
`tooling/verify/checks/draft_approval.py:541-570`;
`tooling/verify/checks/player_routes.py:60-80`.
Finding: `_fresh_engine()` sets `WORLD_ENGINE_DATABASE_URL` to a temp file
and `WORLD_ENGINE_ENV=test` before any `world_engine` import, purges
`world_engine*` from `sys.modules`, imports `world_engine.models`, runs
`SQLModel.metadata.create_all(engine)`. Routes are exercised through
`TestClient(app, base_url="http://127.0.0.1")` with `app` from
`world_engine.cockpit.app`; a module function is swapped by assignment and
restored in `finally`.
Consequence: every check of this lot builds its world this way, never on
Nia's database.

### R-36 -- the v2.33 shape of `world` and `pass_play`
Opened: a fresh `SQLModel.metadata.create_all` on a temp database at
`055b890`, then `sqlite_master` for both tables and their indexes; then,
on that database, the four ALTERs and the W1 `UPDATE` of C-01 in one raw
transaction (`foreign_keys=OFF`, `legacy_alter_table=ON`) followed by
`PRAGMA foreign_key_check`.
Finding: the stored DDL (the literal A's check rebuilds, `\n\t` as stored):
```
CREATE TABLE world (\n\tid VARCHAR NOT NULL, \n\tname VARCHAR NOT NULL, \n\tdescription VARCHAR, \n\ttone VARCHAR, \n\topen_to_players BOOLEAN DEFAULT 0 NOT NULL, \n\tis_active BOOLEAN DEFAULT 0 NOT NULL, \n\tcurrent_phase VARCHAR DEFAULT 'matin' NOT NULL, \n\tcreated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_world_current_phase CHECK (current_phase IN ('matin','apres-midi','soir','nuit'))\n)
CREATE UNIQUE INDEX idx_world_one_active ON world (is_active) WHERE is_active = 1
CREATE TABLE pass_play (\n\tid VARCHAR NOT NULL, \n\tbatch_id VARCHAR NOT NULL, \n\tsession_id VARCHAR NOT NULL, \n\tcharacter_id VARCHAR NOT NULL, \n\tagenda_id VARCHAR, \n\tdeclared_action VARCHAR NOT NULL, \n\tinjected_context JSON, \n\tcreator_notes VARCHAR, \n\tstatus VARCHAR DEFAULT 'submitted' NOT NULL, \n\tbatch_order INTEGER, \n\thistory JSON DEFAULT '[]' NOT NULL, \n\tsubmitted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tapplied_at DATETIME, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(batch_id) REFERENCES batch (id), \n\tFOREIGN KEY(session_id) REFERENCES session (id), \n\tFOREIGN KEY(character_id) REFERENCES entity (id), \n\tFOREIGN KEY(agenda_id) REFERENCES agenda (id)\n)
CREATE INDEX idx_passplay_batch ON pass_play (batch_id)
CREATE INDEX idx_passplay_agenda ON pass_play (agenda_id)
```
The ALTERs (including `REFERENCES character (id) ON DELETE SET NULL`) and
the `UPDATE` run; `foreign_key_check` is empty.
Consequence: A's migration is feasible as C-01 states; its check rebuilds
both tables from this literal to stand a v2.33 database.

## Contracts

### C-01 -- schema v2.34
Produced by: A   Consumed by: B, D, E, F, G
`World` (`models/canon.py`) gains, after `current_phase`:
- `active_pc_id: Optional[str] = Field(default=None, sa_column=Column(String,
  ForeignKey("character.id", ondelete="SET NULL"), nullable=True))` -- the
  player character the creator's cockpit acts for; NULL: none chosen.
`PassPlay` (`models/pipeline.py`) gains, after `applied_at`:
- `quest_id: Optional[str] = Field(default=None, foreign_key="quest.id")` --
  the quest a day was pinned to at its declaration (Q1);
- `published_text: Optional[str] = None` -- the narrative the player reads;
- `published_at: Optional[datetime] = None` -- set once, at publication;
  a day is published iff this is not NULL (T1).
In `models/pipeline.py`, after `PassPlay`:
- `DAY_RUN_STAGES: tuple[str, ...] = ("plan", "resolve")`;
- `DAY_RUN_FAILURE_CODES: tuple[str, ...] = ("model_failed", "blocked",
  "rejected", "refused", "crashed", "interrupted")`;
- `class DayRunFailure(SQLModel, table=True)`, `__tablename__ =
  "day_run_failure"`: `id: str` (uuid pk), `world_id: str` (FK `world.id`,
  not null), `pass_play_id: str` (FK `pass_play.id`, not null), `stage:
  str`, `code: str`, `reason: str`, `created_at: datetime =
  _created_ts()`; `__table_args__`: `Index("idx_day_run_failure_pass_play",
  "pass_play_id", "created_at")`, `Index("idx_day_run_failure_world",
  "world_id", "created_at")`, `CheckConstraint("stage IN
  ('plan','resolve')", name="ck_day_run_failure_stage")`,
  `CheckConstraint("code IN ('model_failed','blocked','rejected','refused',
  'crashed','interrupted')", name="ck_day_run_failure_code")`. Append-only:
  no row is ever updated or deleted outside the world cascade. Non-canon.
`models/__init__.py` imports and exports `DayRunFailure`,
`DAY_RUN_STAGES`, `DAY_RUN_FAILURE_CODES` beside `PassPlay`.
`writes/pipeline.py`: `PASS_PLAY_STATUSES = ("submitted", "resolving",
"resolved", "flagged", "abandoned")`; the docstring sentence on `flagged`
becomes « `flagged` is a day whose chain failed (`day_run_failure`, written
by `writes/day_runs.py`); `abandoned` a failed day the creator gave up
(TICKET-0128). »
`writes/worlds.py`: `"day_run_failure"` appended to
`_DIRECT_WORLD_SCOPED_DELETES`.
Migration `scripts/migrate_v2_34_player_day.py`: `_PREVIOUS_VERSION =
"v2.33"`, `_THIS_VERSION = "v2.34"`; the env guard, `_version_key`,
`_refuse`, `_tables`, `_columns`, `_indexes`, `_create_from_model`,
`_converge_schema_meta` and `main()`'s shape copied from
`migrate_v2_33_creator_review.py` (R-09) with the file name and versions
changed. `_NEW_COLUMNS = (("world", "active_pc_id", "VARCHAR REFERENCES
character (id) ON DELETE SET NULL"), ("pass_play", "quest_id", "VARCHAR
REFERENCES quest (id)"), ("pass_play", "published_text", "VARCHAR"),
("pass_play", "published_at", "DATETIME"))`. `_plan()` returns: the
`day_run_failure` table (with its indexes) while absent; each ALTER whose
column is absent; the W1 backfill statement iff `published_at` is absent
from `pass_play` before the run:
```
UPDATE pass_play SET
  published_at = COALESCE((SELECT processed_at FROM batch WHERE batch.id = pass_play.batch_id), submitted_at),
  published_text = (SELECT final_result FROM batch WHERE batch.id = pass_play.batch_id)
WHERE status = 'resolved' AND published_at IS NULL
```
run after the ALTERs, in the same raw transaction (`foreign_keys=OFF`,
`legacy_alter_table=ON`). Post-checks before `schema_meta` moves: the four
columns and the table exist with both indexes; the `pass_play` row count is
unchanged; no `pass_play` row has `status = 'resolved'` and `published_at
IS NULL` when the backfill ran in this run; prints the number of days
published by W1.

## Context

TICKET-0128 gives a world several player characters (the creator's
« PJ actif », A1) and gives the player his days: a background chain that
records its failures (L1), a pin chosen at the declaration (Q1), a
publication by the creator (C1, C′2, T1), the abandonment of a failed day
(Z1), and the days already resolved published by the migration (W1). This
brief is the schema step: models, migration, cascade, docs, the shape
check. Nothing reads the new columns yet.

## Scope IN

1. `src/world_engine/models/canon.py`, `World`, after `current_phase`:
   ```
   # Creator-set « PJ actif » (v2.34, TICKET-0128, A1): the player character
   # her cockpit acts for; NULL when none is chosen. Read only through
   # `active_pc.resolve_active_pc`; cleared when that character is deleted.
   active_pc_id: Optional[str] = Field(
       default=None,
       sa_column=Column(String, ForeignKey("character.id", ondelete="SET NULL"), nullable=True),
   )
   ```
2. `src/world_engine/models/pipeline.py`:
   a. `PassPlay`, after `applied_at`:
      ```
      # TICKET-0128 (v2.34): the quest pinned at the declaration (Q1); the
      # narrative the creator published and when (C1, C′2, T1). Published
      # iff `published_at` is set; `batch.final_result` keeps the narrator's.
      quest_id: Optional[str] = Field(default=None, foreign_key="quest.id")
      published_text: Optional[str] = None
      published_at: Optional[datetime] = None
      ```
   b. After `PassPlay` and before the `proposed_mutation` section comment,
      a section in the module's comment style:
      ```
      # -----------------------------------------------------------------------------
      # day_run_failure  (one row per failed run of a day's chain, schema v2.34,
      # TICKET-0128, L1)
      #
      # The background chain plans then resolves a declared day; each failure
      # leaves one row (stage, closed code, the reason as text) and turns the
      # day `flagged`. Append-only; written only by `writes/day_runs.py`;
      # non-canon; deleted with its world.
      # -----------------------------------------------------------------------------
      DAY_RUN_STAGES: tuple[str, ...] = ("plan", "resolve")
      DAY_RUN_FAILURE_CODES: tuple[str, ...] = (
          "model_failed", "blocked", "rejected", "refused", "crashed", "interrupted",
      )


      class DayRunFailure(SQLModel, table=True):
          __tablename__ = "day_run_failure"
          __table_args__ = (
              Index("idx_day_run_failure_pass_play", "pass_play_id", "created_at"),
              Index("idx_day_run_failure_world", "world_id", "created_at"),
              CheckConstraint("stage IN ('plan','resolve')", name="ck_day_run_failure_stage"),
              CheckConstraint(
                  "code IN ('model_failed','blocked','rejected','refused','crashed','interrupted')",
                  name="ck_day_run_failure_code",
              ),
          )

          id: str = Field(default_factory=_uuid, primary_key=True)
          world_id: str = Field(foreign_key="world.id", nullable=False)
          pass_play_id: str = Field(foreign_key="pass_play.id", nullable=False)
          stage: str
          code: str
          reason: str
          created_at: datetime = _created_ts()
      ```
3. `src/world_engine/models/__init__.py`: import `DayRunFailure`,
   `DAY_RUN_STAGES`, `DAY_RUN_FAILURE_CODES` in the `from .pipeline import
   (...)` block and add the three names to `__all__` next to `"PassPlay"`.
4. `src/world_engine/writes/pipeline.py`: `:62` becomes
   `PASS_PLAY_STATUSES: tuple[str, ...] = ("submitted", "resolving",
   "resolved", "flagged", "abandoned")`. In the module docstring, the words
   « `flagged` is reserved for a future input classifier and is never
   written by anything in this module. » become « `flagged` is a day whose
   chain failed (`day_run_failure`, written by `writes/day_runs.py`);
   `abandoned` a failed day the creator gave up (TICKET-0128). » (re-wrap
   the paragraph, nothing else changes).
5. `src/world_engine/writes/worlds.py`: append `"day_run_failure",` to
   `_DIRECT_WORLD_SCOPED_DELETES` after `"pc_draft_knowledge",`.
6. `src/world_engine/schema_version.py`: `"v2.34"`;
   `world-engine-schema.md:3`: `Current schema version: v2.34`.
7. New `scripts/migrate_v2_34_player_day.py` per C-01. Docstring in the
   v2.33 script's shape: first line « Migration v2.34 — the active player
   character, the day's pin, publication and failures (TICKET-0128,
   BRIEF-0128-A). »; what it adds; W1 (« the days already resolved are
   published with the narrator's text, once: only in the run that adds
   `pass_play.published_at` »); refusal below v2.33; idempotent; one raw
   transaction; post-checks; how to run. `main()` prints « Migration v2.34
   — ... », « Applied: ... » or « Nothing to do. », the post-check line
   (« W1: N day(s) published. » when the backfill ran) and « Migration
   v2.34 applied. ».
8. `world-engine-schema.md`:
   - `world` section: in the `CREATE TABLE world` block, after
     `current_phase`'s comment lines:
     `  active_pc_id          TEXT REFERENCES character(id) ON DELETE SET NULL,  -- creator-set « PJ actif » (v2.34, TICKET-0128, A1)`
     (keep the block's column alignment; wrap the comment onto a `--`
     line below if the line passes 100 characters);
   - `pass_play` section: after `applied_at`, three lines
     `quest_id TEXT REFERENCES quest(id), -- pinned at the declaration (v2.34, TICKET-0128, Q1)`,
     `published_text TEXT, -- the narrative the player reads (v2.34, TICKET-0128, C′2)`,
     `published_at DATETIME -- published iff set; never replayed after (v2.34, TICKET-0128, T1)`
     (commas adjusted so the block stays valid SQL), and under the block a
     line « `status`: submitted | resolving | resolved | flagged |
     abandoned (v2.34) — `flagged` when the chain failed (`day_run_failure`),
     `abandoned` when the creator gave it up. »;
   - a new section `### \`day_run_failure\`` right after the `pass_play`
     section, in the file's section form: one paragraph (« One row per
     failed run of a day's chain (schema v2.34, TICKET-0128, L1): the
     stage, a closed code, the reason as text. The day turns `flagged`.
     Append-only; non-canon; deleted with its world. ») and a `CREATE
     TABLE day_run_failure` block with its two CHECKs and two indexes.
9. `world-engine-schema-changelog.md`, newest first under `## CHANGELOG`,
   verbatim:
   ```
   - **v2.34** — TICKET-0128, BRIEF-0128-A: several player characters and
     the player's days. `world` gains `active_pc_id` (FK `character`, ON
     DELETE SET NULL); `pass_play` gains `quest_id` (FK `quest`),
     `published_text` and `published_at`; `PASS_PLAY_STATUSES` adds
     `abandoned` (no CHECK); new table `day_run_failure` (stage, closed
     code, reason, two CHECKs, two indexes), cascaded with its world.
     `migrate_v2_34_player_day.py` publishes every day already resolved
     with the narrator's text (W1), once.
   ```
10. `tooling/verify/checks/world_cascade.py`:
    - `_FIXTURE`, right after the `pass_play` row:
      `("day_run_failure", {"id": "drf-{w}", "world_id": "{w}", "pass_play_id": "pp-{w}", "stage": "plan", "code": "crashed", "reason": "r"}),`
    - `_build_world`, after the `_FIXTURE` loop and before `db.commit()`:
      `db.execute(text("UPDATE world SET active_pc_id = :c WHERE id = :w"), {"c": f"{world_id}-char", "w": world_id})`
      with a comment « # v2.34: a world naming its active PC still deletes
      under FK enforcement (TICKET-0128, BRIEF-0128-A). »
11. `tooling/verify/checks/review_schema.py`: `:271` becomes `if
    _version_key(EXPECTED_STATIC_SCHEMA_VERSION) <
    _version_key("v2.33"):` with `_version_key` defined in the module as
    in `creation_schema.py` (`major, minor = version.lstrip("v").split(".")`
    -> `(int(major), int(minor))`) unless one already exists there; the
    docstring's RS1 sentence reads « `EXPECTED_STATIC_SCHEMA_VERSION` is at
    least v2.33 ».
12. New check `tooling/verify/checks/day_schema.py`, first sentence « G1
    check for TICKET-0128 (BRIEF-0128-A) -- schema v2.34: the active player
    character, the day's pin, its publication and its failures. », fresh
    temp-file database per R-35:
    - **DS1** static, by import: `World.active_pc_id` is nullable with one
      FK to `character.id` whose `ondelete` is `SET NULL`;
      `PassPlay.quest_id` nullable, FK `quest.id`; `published_text`,
      `published_at` nullable, no FK; `day_run_failure` has exactly the
      columns of C-01 (`world_id`, `pass_play_id` not null with their FKs),
      the two CHECK names, the two indexes on their columns; no JSON
      column on `day_run_failure`, `world`'s new column or `pass_play`'s
      three; `models.DAY_RUN_STAGES == ("plan", "resolve")`,
      `models.DAY_RUN_FAILURE_CODES` equals C-01's tuple, both and
      `DayRunFailure` in `models.__all__`; `writes.pipeline.PASS_PLAY_STATUSES[-1]
      == "abandoned"`; `"day_run_failure"` in
      `writes.worlds._DIRECT_WORLD_SCOPED_DELETES`;
      `EXPECTED_STATIC_SCHEMA_VERSION == "v2.34"`; the migration exists
      and its `_PREVIOUS_VERSION` is `"v2.33"` (read by `ast`).
    - **DS2** fixture after `create_all`, raw INSERTs: a failure with stage
      `"x"` refused, with code `"x"` refused, with `("plan", "crashed")`
      admitted; a world whose `active_pc_id` names a player character: a
      raw `DELETE FROM character` of it (then of its `entity`) leaves
      `world.active_pc_id` NULL.
    - **DS3** migration, subprocess, the `review_schema.py` RS3 idiom: the
      fixture creates every table, then drops `day_run_failure` and
      rebuilds `world` and `pass_play` from R-36's literal DDL (as
      `V233_DDL`, with their indexes), inserts one world, one session,
      one batch with `processed_at` and `final_result = "Récit"`, and
      three days on it -- `resolved`, `resolving`, `submitted` -- (unique
      batch per day: three batches), sets `schema_meta` to v2.32: (a) the
      script exits non-zero and nothing changes; at v2.33: (b) it exits
      zero; the four columns, the table and both indexes exist; the
      `resolved` day reads `published_text = "Récit"` and `published_at`
      = its batch's `processed_at`; the other two read NULL; `schema_meta`
      reads v2.34; (c) the `resolving` day is then set to `resolved` raw
      and the script run again: it exits zero, prints « Nothing to do. »,
      and that day stays unpublished (W1 ran once).
    A sub-rule not reached is a FAILURE; the PASS line names DS1-DS3.
13. `python tooling/glue/gen_file_map.py` (two new modules: the script and
    the check).

## Scope OUT

- Any reader or writer of the new columns and table: the resolver (B),
  the selector (C), the chain (D), the worker and its writers (E), the
  publication (F), the player routes (G).
- A CHECK on `pass_play.status` (none today; adding one rebuilds the
  table): not in this ticket.
- `day_run_failure` in `pass_play.history` or any JSON (L2, rejected).
- A `day_publication` table (T2, rejected).
- Any change to the cascade's order or to `_SUBQUERY_SCOPED_DELETES`.
- Running the migration on Nia's production database (she does it after
  the merge, ticket note).

## Invariants to defend

- **INV-20** (a value shown in the UI is relational, never JSON): every new
  column is a plain column (`json_ui_boundary.py` volet c).
- **INV-12** (the world cascade deletes every world-scoped row):
  `day_run_failure` is named and has a fixture row (`world_cascade.py` W1,
  W3, W4).
- **History is sacred**: the backfill writes only rows whose
  `published_at` is NULL, once, and touches neither `batch.final_result`
  nor `pass_play.history`.

## Decision rights

STOP: an anchor that does not hold; `create_all` warning about or failing
on the `world` <-> `character` FK cycle (R-05 measured none); SQLite
refusing an ALTER of C-01 on the test database; any check other than
`pipeline_state.py` / `corpus_gate.py` turning red.
ADAPT: `review_schema.py` already defines a `_version_key` -> reuse it;
`world-engine-schema.md`'s `world` block alignment differs from the
anchor -> keep its own alignment; `models/__init__.py` lists names in a
different order -> insert beside `PassPlay`. Report each.
REPORT-ONLY: other checks pinning `"v2.33"` in a migration-run assertion
(`meta[0] != "v2.33"` after their own script runs is correct and stays).
> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_schema.py` -> PASS (DS1-DS3).
- [ ] `world_cascade.py`, `review_schema.py`, `creation_schema.py`,
      `schema_version_agreement.py`, `schema_partition.py`,
      `schema_reconciliation.py`, `pipeline_wiring.py`,
      `json_ui_boundary.py`, `single_canon_write.py`, `module_budget.py`,
      `file_map.py`, `pc_resolution.py` -> PASS.
- [ ] `WORLD_ENGINE_ENV=test python scripts/migrate_v2_34_player_day.py`
      on the test database -> « Migration v2.34 applied. »; a second run
      -> « Nothing to do. ».
- [ ] `pipeline_state.py` and `corpus_gate.py` are red only for the
      arrows of later briefs (R-32: `active_pc_selector.py`,
      `day_chain_world.py`, `day_runs.py`, `day_publication.py`,
      `player_journee.py`); every other check of the corpus is green.
- [ ] /review-step, then /close-step.

## Docs to update

This brief is the schema doc update (Scope IN 6, 8, 9). No CLAUDE.md, no
rule file, no ARCHITECTURE_DECISIONS entry (G writes the ticket's).
