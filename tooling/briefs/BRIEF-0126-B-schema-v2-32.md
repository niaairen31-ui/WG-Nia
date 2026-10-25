<!-- slug: schema-v2-32 -->
# BRIEF 0126-B — "Schema v2.32: creation rules, overrides, drafts, the creation journal"

Lot: LOT-0126-character-creation.md (authoritative on conflict)
Depends on: BRIEF-0126-A

## Anchors to confirm (Mini-RECON)

- `src/world_engine/models/canon_skill.py` exists and declares `SkillSystem`,
  `SkillDefinition`, `Skill` (brief A); each of the first two ends its
  columns with `trial_to_rank_5` then `created_at`/`updated_at`
  (`requires_master` between them for the definition).
- `src/world_engine/schema_version.py:15` reads `"v2.31"`;
  `world-engine-schema.md:3` reads `Current schema version: v2.31`.
- `src/world_engine/models/pipeline.py:467-471` defines `LORE_USAGE_STEPS`
  with `write`, `consult`, `perspective`; :479-485 the CHECK
  `ck_lore_usage_event_step` whose last line names `perspective_resolve`.
- `src/world_engine/writes/lore_usage.py:29-39` defines `PAYLOAD_KEYS` ending
  with `perspective_resolve`.
- `scripts/migrate_v2_31_player_entry.py` defines `_create_from_model`,
  `_rebuild`, `_JOURNAL_COLUMNS`, `_converge_schema_meta`.
- `src/world_engine/writes/worlds.py:84` is `    "quest_request",` inside
  `_DIRECT_WORLD_SCOPED_DELETES`.
- `tooling/verify/checks/world_cascade.py:336-345` `_build_world` inserts the
  world row then `_FIXTURE`, and no `user` row.

Halt if any anchor has moved.

## Facts carried

### R-01 -- schema version and the migration skeleton
Opened: `src/world_engine/schema_version.py:15`; `world-engine-schema.md:3`;
`world-engine-schema-changelog.md:1-25`; `scripts/migrate_v2_31_player_entry.py`
(whole, 194 lines).
Finding: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.31"`; the doc reads
`Current schema version: v2.31`; the changelog lists newest first under
`## CHANGELOG`. The v2.31 script refuses to run without `WORLD_ENGINE_ENV`
or `WORLD_ENGINE_DATABASE_URL`; `_refuse()` exits when `schema_meta` is older
than `_PREVIOUS_VERSION`; `_plan()` returns ADD COLUMN statements and
`(model, columns)` rebuilds still needed; `_apply()` runs them in one raw
transaction (`PRAGMA foreign_keys=OFF`, `PRAGMA legacy_alter_table=ON`,
`BEGIN` ... `COMMIT`, both pragmas reset); `_rebuild(cursor, model, columns)`
drops the table's named indexes, renames it `<table>_old`, creates it from
`CreateTable(model.__table__)` and its `CreateIndex`es (`_create_from_model`),
copies `columns`, drops `_old`; `_post_checks` raises `SystemExit` with every
problem; `_converge_schema_meta()` moves `schema_meta` forward. It writes no
data besides the journal copy.
Consequence: B's migration is a standalone copy of this skeleton at
`_PREVIOUS_VERSION = "v2.31"`, `_THIS_VERSION = "v2.32"`; it creates its new
tables through `_create_from_model` (the helper creates indexes too).
### R-03 -- the skill system and skill definition columns
Opened: `src/world_engine/models/canon.py:597-682`.
Finding: `SkillSystem` (`skill_system`): `id, world_id, name, description,
points_to_rank_1..5 (Optional[int]), trial_to_rank_1..5 (Optional[bool]),
created_at, updated_at`; CHECK `ck_skill_system_rank_points`
(`RANK_POINTS_CHECK`); unique index `idx_skill_system_world_name`.
`SkillDefinition` (`skill_definition`): `id, world_id, name, base_domain,
system_id (FK skill_system.id ON DELETE RESTRICT, nullable), description,
points_to_rank_1..5, trial_to_rank_1..5, requires_master (bool, server
default 0), created_at, updated_at`; CHECKs
`ck_skill_definition_base_domain`, `ck_skill_definition_rank_points`; unique
`idx_skill_definition_world_name`. NULL in an override column inherits.
Consequence: B adds nullable override columns to both models by ADD COLUMN
(R-04's v2.29 precedent: nullable, no CHECK); their bounds are enforced by
the creator CRUD bodies (C), not the database.
### R-04 -- how v2.29 added columns to the skill tables
Opened: `scripts/migrate_v2_29_rank_trials.py:1-20, 147-195`;
`tooling/verify/checks/rank_trial_schema.py:1-60, 380-470`.
Finding: v2.29 added `skill_rank.trial_to_next` as `BOOLEAN NOT NULL DEFAULT
0` and `trial_to_rank_1..5` to `skill_system` and `skill_definition` as
plain `BOOLEAN` by ADD COLUMN, no CHECK. `rank_trial_schema.py` TS3
recreates the six tables in their v2.28 DDL (literal `V228_DDL`), runs the
v2.29 script and checks the eleven columns and rows; the v2.29 script adds
columns, it does not rebuild those three tables.
Consequence: columns added in v2.32 must be nullable (or carry a default)
so that a v2.28-shaped fixture migrated by v2.29 still loads; ADD COLUMN in
v2.32 leaves TS3 untouched.
### R-19 -- the Lore usage journal
Opened: `src/world_engine/models/pipeline.py:450-505`;
`src/world_engine/writes/lore_usage.py:1-90`; `src/world_engine/lore_usage.py`
(whole, 71 lines); `tooling/verify/checks/lore_usage.py:1-80, 225-250`;
`tooling/verify/checks/player_entry_schema.py:1-40, 70-92, 150-215`.
Finding: `LORE_USAGE_STEPS` (:467-471) maps `write`, `consult`,
`perspective` to their steps; `LoreUsageEvent` carries the CHECK
`ck_lore_usage_event_step` listing the same pairs as literal SQL (:479-485),
no `world_id`, kept out of the world cascade by construction.
`PAYLOAD_KEYS` (`writes/lore_usage.py:29-39`) gives each step's exact
payload keys; `write_usage_event` refuses a payload whose keys differ, an
`error` set when the outcome is `ok`, a step outside its kind.
`lore_usage.attempt_id(raw)` canonicalises or mints a UUID; `stage(db, *,
attempt, world_id, kind, step, outcome, payload, exchanges=None,
lore_entry_ref=None)` adds a row to the caller's transaction; `record`
stages and commits. `lore_usage.py` U1 reads the CHECK pairs from a fresh
`create_all` and compares them with `LORE_USAGE_STEPS`;
`player_entry_schema.py` PS2 reshapes the journal to its v2.13 DDL and runs
the v2.31 script, which rebuilds the table from the current model, then
asserts `'perspective_ask'` in the stored SQL.
Consequence: B adds the kind `creation` to `LORE_USAGE_STEPS` and the CHECK
text, two `PAYLOAD_KEYS` entries, and rebuilds the table in v2.32 when the
stored SQL lacks `'creation'` (C-02). U1 and PS1/PS2 stay true.
### R-27 -- the world cascade
Opened: `src/world_engine/writes/worlds.py:1-25, 39-91`;
`tooling/verify/checks/world_cascade.py:1-40, 67-215, 310-345`.
Finding: `_DIRECT_WORLD_SCOPED_DELETES` (:65-85) lists tables deleted by
`world_id`, order free under the FK deferral, ending with
`"quest_request",`. W1 requires the world-reaching tables of the metadata
(a `world_id` column, or a foreign key to a world-reaching table) to equal
the tables the module names; W3 requires `_FIXTURE` (:67) to name exactly
the cascaded tables; W4 builds two worlds through `_build_world(engine,
world_id)` (:336-345), which inserts the `world` row then every
`_FIXTURE` row (`{w}` formatted) by raw INSERT, and requires every fixture
table to grow. No `user` row is inserted. `user` is not world-reaching.
Consequence: B adds `creation_rules` and the five `pc_draft*` tables to
`_DIRECT_WORLD_SCOPED_DELETES` (each carries `world_id`), adds their rows
to `_FIXTURE`, and makes `_build_world` insert a `user` row `u-{w}` before
the fixture so `pc_draft.user_id` resolves.
### R-28 -- the JSON boundary
Opened: `tooling/verify/checks/json_ui_boundary.py:1-60, 215-230`.
Finding: every JSON column of the metadata must be a named entry of
`JSON_COLUMN_ALLOWLIST`; an unlisted one fails volet c.
Consequence: no table of this lot has a JSON column (B1, INV-20); the
allowlist is untouched.
### R-29 -- the models package layout
Opened: `src/world_engine/models/__init__.py:1-58, 109-205`.
Finding: the docstring lists each stratum module with its tables; the
import order is canon, canon_faction, canon_knowledge, canon_attribute,
canon_event, config, ephemeral, pipeline, observation, quests; each module
imports `_created_ts, _uuid` from `.canon`.
Consequence: A adds `canon_skill.py` after `canon` in the docstring and the
imports; B adds `pc_drafts.py` (non-canon, pending player drafts) last.
### R-30 -- a relational pending request, the precedent
Opened: `src/world_engine/models/pipeline.py:578-640`.
Finding: `QuestRequest` is non-canon, world-scoped, deleted with its world,
its states a CHECK list, its skill named by a text `skill_key` (a base
domain or a skill definition id, TICKET-0116), written only by its own
`writes/` module, which never commits.
Consequence: `pc_draft_skill.skill_key` follows that shape (no FK: a
deleted definition leaves an `unknown_skill` the check reports) and the
draft writer never commits (C-12).
### R-35 -- the check fixture and the stubbed model
Opened: `tooling/verify/checks/world_sheet.py:48-62`;
`tooling/verify/checks/lore_usage.py:427-466, 655-665`;
`tooling/verify/checks/player_routes.py:88-130, 180-185`;
`.claude/rules/verify-checks.md`.
Finding: `_fresh_engine()` points `WORLD_ENGINE_DATABASE_URL` at a temp
file, sets `WORLD_ENGINE_ENV=test`, drops cached `world_engine` modules,
imports `world_engine.models` and runs `SQLModel.metadata.create_all`.
`_Stub(replies)` pops one reply per call (an `Exception` is raised, a dict
is JSON-dumped); `_swap(module, stub)` replaces `module.chat` and returns
the original; route tests use `TestClient(app,
base_url="http://127.0.0.1")`; `_seed_prompts` upserts heads through
`seed_pilot.upsert_prompt_template` after `sys.path.insert(0, scripts)`.
Rules: fail-closed, never Nia's DB, rows through sanctioned writers, every
rule proven by a named mutation.
Consequence: every DB check of this lot copies `_fresh_engine`'s body, and
the designer and route checks stub `chat` with `_Stub`/`_swap` and
`ollama_client.ping` by attribute.
### R-37 -- the corpus gate
Opened: `tooling/verify/checks/corpus_gate.py:1-60, 150-165`.
Finding: every `*.py` of `tooling/verify/checks/` is discovered and run as
a subprocess, 15 seconds each (`TIMEOUT_SECONDS`) unless listed in
`SLOW_CHECK_TIMEOUTS`.
Consequence: every new check of this lot must finish in 15 seconds; the
schema check's migration subprocess runs once per sub-rule, not per table.
### R-42 -- the schema document's layout
Opened: `world-engine-schema.md:1-20, 1209-1240, 1319-1390, 2048-2120,
2201-2230, 3451-3460`.
Finding: each table is a `### \`<table>\`` section: one or more prose
paragraphs (what it is, ticket and version), a ```sql``` block with the
`CREATE TABLE` (one column per line, a `--` comment for a column added
later, e.g. `trial_to_rank_1  BOOLEAN,  -- reaching rank n asks a trial
(v2.29); NULL = inherited`), its `CREATE ... INDEX` lines inside the same
block, then `-- NOTE:` lines and `-----`. The journal section names each
kind in prose (« Perspective questions (v2.31, TICKET-0125) are journaled
as kind `perspective` ... »). `## INDEXES` (:3451) repeats every index
grouped by purpose. `quest_request` (:1319) is the last pipeline table
section before `skill_resolution`; `skill_rank` (:2201) is the last of the
skill sections.
Consequence: B documents `creation_rules` after `skill_rank`, the five
draft tables after `quest_request`, the six override columns inside the two
existing `CREATE TABLE` blocks with a `-- ... (v2.32)` comment, the journal
kind in the journal section's prose and CHECK, and every new index in
`## INDEXES`.

## Contracts

### C-01 -- the skill stratum module
Produced by: A   Consumed by: B, C
Module: `src/world_engine/models/canon_skill.py`. Holds, verbatim and in
this order, `canon.py` lines 580-719 at `fb8557a`: the comment and
`BASE_SKILL_DOMAINS`, the comment and `RANK_POINTS_CHECK`, `SkillSystem`,
`SkillDefinition`, `Skill`, with their section comments. Its own docstring
(the `canon_faction.py` shape: « extracted from ``canon.py`` (TICKET-0126,
BRIEF-0126-A) to keep each stratum module under the `module_budget.py`
line cap »). Imports exactly what those lines use: `datetime`, `Optional`,
`Column, CheckConstraint, ForeignKey, Index, JSON, text` from sqlalchemy,
`Field, SQLModel` from sqlmodel, `_created_ts, _uuid` from `.canon`.
`canon.py` no longer holds lines 580-719; its imports are unchanged.
`models/__init__.py` imports `BASE_SKILL_DOMAINS, Skill, SkillDefinition,
SkillSystem` from `.canon_skill`; `__all__` unchanged; the docstring lists
`canon_skill.py` after `canon.py`. Table set unchanged
(`static_table_names()` identical).
### C-02 -- schema v2.32
Produced by: B   Consumed by: C, D, F, G, I
**`models/canon_skill.py` gains:**
```python
CREATION_COST_COLUMNS: tuple[str, ...] = tuple(f"cost_to_rank_{n}" for n in range(1, 6))
CREATION_CAP_RANKS: tuple[int, ...] = (0, 2, 3, 4, 5)
CREATION_CAP_COLUMNS: tuple[str, ...] = tuple(f"cap_at_rank_{r}" for r in CREATION_CAP_RANKS)
CREATION_RULES_CHECK = " AND ".join(
    ["pool >= 0", "max_rank BETWEEN 1 AND 5", "max_master_skills >= 0"]
    + [f"{c} >= 0" for c in CREATION_COST_COLUMNS]
    + [f"({c} IS NULL OR {c} >= 0)" for c in CREATION_CAP_COLUMNS]
)

class CreationRules(SQLModel, table=True):
    __tablename__ = "creation_rules"
    __table_args__ = (
        Index("idx_creation_rules_world", "world_id", unique=True),
        CheckConstraint(CREATION_RULES_CHECK, name="ck_creation_rules_values"),
    )
    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    pool: int = Field(default=6, sa_column_kwargs={"server_default": text("6")})
    cost_to_rank_1: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    cost_to_rank_2: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    cost_to_rank_3: int = Field(default=2, sa_column_kwargs={"server_default": text("2")})
    cost_to_rank_4: int = Field(default=3, sa_column_kwargs={"server_default": text("3")})
    cost_to_rank_5: int = Field(default=4, sa_column_kwargs={"server_default": text("4")})
    cap_at_rank_0: Optional[int] = Field(default=2, sa_column_kwargs={"server_default": text("2")})
    cap_at_rank_2: Optional[int] = None
    cap_at_rank_3: Optional[int] = None
    cap_at_rank_4: Optional[int] = None
    cap_at_rank_5: Optional[int] = None
    max_rank: int = Field(default=5, sa_column_kwargs={"server_default": text("5")})
    max_master_skills: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    skills_visible: bool = Field(default=True, sa_column_kwargs={"server_default": text("1")})
    updated_at: datetime = _created_ts()
```
A cap of NULL is « no cap »; a missing row is every default above.
`SkillSystem` gains, after `trial_to_rank_5`: `visible_at_creation:
Optional[bool] = None`, `max_rank_at_creation: Optional[int] = None`,
`cap_raised_at_creation: Optional[int] = None`, `cap_held_at_creation:
Optional[int] = None`. `SkillDefinition` gains, after `trial_to_rank_5`:
`visible_at_creation: Optional[bool] = None`, `max_rank_at_creation:
Optional[int] = None`. NULL inherits. No CHECK on them (R-04).

**`models/pc_drafts.py`** (non-canon; a player's character draft):
```python
PC_DRAFT_STATUSES: tuple[str, ...] = ("draft", "submitted", "returned", "approved")
PC_DRAFT_ORIGINS: tuple[str, ...] = ("player", "designer")
PC_SKETCH_KINDS: tuple[str, ...] = ("family", "master", "faction", "other")
PC_KNOWLEDGE_LEVELS: tuple[str, ...] = ("rumor", "suspicious", "partial", "knows")
PC_SKETCH_MAX = 8
```
- `PcDraft` (`pc_draft`): `id`; `world_id` FK world NOT NULL; `user_id` FK
  `user.id` NOT NULL; `status: str` default `'draft'` (server default);
  `name: str` default `''`; `backstory: str` default `''`;
  `start_location_id: Optional[str]` FK entity; `start_location_set_by:
  Optional[str]`; `creator_note: Optional[str]`; `submitted_at:
  Optional[datetime]`; `created_at`, `updated_at` (`_created_ts()`).
  CHECKs `ck_pc_draft_status` (`status IN ('draft','submitted','returned',
  'approved')`), `ck_pc_draft_set_by` (`start_location_set_by IS NULL OR
  start_location_set_by IN ('player','designer')`). Indexes
  `idx_pc_draft_world` (`world_id`), `idx_pc_draft_open` unique on
  `(world_id, user_id)` where `status <> 'approved'`.
- `PcDraftSkill` (`pc_draft_skill`): `id`; `draft_id` FK `pc_draft.id` NOT
  NULL; `world_id` FK world NOT NULL; `skill_key: str`; `player_rank:
  Optional[int]`; `designer_rank: Optional[int]`; `justification:
  Optional[str]`; `designer_reason: Optional[str]`. CHECKs
  `ck_pc_draft_skill_ranks` (`(player_rank IS NULL OR player_rank BETWEEN 0
  AND 5) AND (designer_rank IS NULL OR designer_rank BETWEEN 0 AND 5)`),
  `ck_pc_draft_skill_some` (`player_rank IS NOT NULL OR designer_rank IS NOT
  NULL`). Unique index `idx_pc_draft_skill_key` (`draft_id, skill_key`).
- `PcDraftSketch` (`pc_draft_sketch`): `id`; `draft_id`; `world_id`;
  `position: int`; `name: str`; `role: str` default `''`; `sentence: str`
  default `''`; `group_label: str` default `''`; `kind: str`; `skill_key:
  Optional[str]`; `existing_entity_id: Optional[str]` FK entity; `origin:
  str`. CHECKs `ck_pc_draft_sketch_kind` (`kind IN ('family','master',
  'faction','other')`), `ck_pc_draft_sketch_master` (`(kind = 'master') =
  (skill_key IS NOT NULL)`), `ck_pc_draft_sketch_origin` (`origin IN
  ('player','designer')`). Index `idx_pc_draft_sketch_draft` (`draft_id`).
- `PcDraftMembership` (`pc_draft_membership`): `id`; `draft_id`;
  `world_id`; `faction_id` FK entity NOT NULL; `role: Optional[str]`;
  `origin: str`. CHECK `ck_pc_draft_membership_origin`; unique index
  `idx_pc_draft_membership_faction` (`draft_id, faction_id`).
- `PcDraftKnowledge` (`pc_draft_knowledge`): `id`; `draft_id`; `world_id`;
  `position: int`; `level: str`; `content: str`; `origin: str`. CHECKs
  `ck_pc_draft_knowledge_level` (`level IN ('rumor','suspicious','partial',
  'knows')`), `ck_pc_draft_knowledge_origin`. Index
  `idx_pc_draft_knowledge_draft` (`draft_id`).
Every string default carries `server_default text("''")`; `status` carries
`text("'draft'")`. No JSON column, no `change_history`.

**Journal.** `LORE_USAGE_STEPS["creation"] = ("creation_subject",
"creation_design")`, appended after `perspective`; the CHECK
`ck_lore_usage_event_step` gains `OR (kind = 'creation' AND step IN
('creation_subject','creation_design'))` at its end. `PAYLOAD_KEYS` gains:
- `"creation_subject": frozenset({"draft_id", "asked_by", "backstory",
  "names", "keywords", "error"})`
- `"creation_design": frozenset({"draft_id", "asked_by", "lore",
  "proposal", "violations", "notes", "error"})`

**Migration** `scripts/migrate_v2_32_character_creation.py`: R-01's
skeleton, `_PREVIOUS_VERSION = "v2.31"`, `_THIS_VERSION = "v2.32"`.
`_plan()` returns (a) `CreationRules` and the five draft models to create
when their table is absent (created by `_create_from_model`, parents before
children: `creation_rules`, `pc_draft`, `pc_draft_skill`, `pc_draft_sketch`,
`pc_draft_membership`, `pc_draft_knowledge`); (b) `ALTER TABLE skill_system
ADD COLUMN visible_at_creation BOOLEAN`, `... max_rank_at_creation INTEGER`,
`... cap_raised_at_creation INTEGER`, `... cap_held_at_creation INTEGER`,
`ALTER TABLE skill_definition ADD COLUMN visible_at_creation BOOLEAN`,
`... max_rank_at_creation INTEGER`, each only when the column is absent;
(c) a rebuild of `lore_usage_event` (`models.LoreUsageEvent`, the v2.31
script's `_JOURNAL_COLUMNS`) when its stored SQL lacks `'creation'`. Writes
no data. Post-checks: the six tables exist; the six columns exist;
`'creation_design'` is in the stored journal SQL; the journal row count is
unchanged. Then `schema_meta` -> v2.32. Output lines as v2.31's.

**Cascade.** `_DIRECT_WORLD_SCOPED_DELETES` gains, after `"quest_request",`:
`"creation_rules", "pc_draft", "pc_draft_skill", "pc_draft_sketch",
"pc_draft_membership", "pc_draft_knowledge",`.

## Context

Brief A made room in the models. This step lays down every table and
column of TICKET-0126 at once, as a schema-only migration that writes no
data: the world's creation rules (J1'), the overrides on systems and skills
(L2, Q-limits), the player's relational draft (B1), and the journal kind
`creation` for the designer's calls (U1). Nothing reads or writes them yet.

## Scope IN

1. `models/canon_skill.py`: add C-02's constants and `CreationRules` after
   `Skill`, under a section comment `# creation_rules (a world's character
   creation rules -- schema v2.32, TICKET-0126, BRIEF-0126-B, J1')` with a
   NOTE: « One row per world; a missing row is every default. A cap of NULL
   is no cap. Curated config, no change_history; written only by
   `writes.creation_rules.write_creation_rules`, read only by
   `creation_rules.py`, which never writes on read. » Add the four
   `SkillSystem` and two `SkillDefinition` fields of C-02 after
   `trial_to_rank_5`, under one comment each: `# Character creation (v2.32,
   TICKET-0126, L2/Q-limits): NULL inherits -- the definition, then its
   system, then the world's creation_rules.`
2. Create `models/pc_drafts.py`: docstring « A player's character draft
   (schema v2.32, TICKET-0126, BRIEF-0126-B, B1) -- non-canon, pending:
   nothing here reaches canon before the creator approves it (TICKET-0129).
   Relational by INV-20: the player sees and edits every row. Written only
   by `writes/pc_drafts.py`, which never commits. World tables, deleted with
   their world. », `from .canon import _created_ts, _uuid`, C-02's constants
   and five models exactly.
3. `models/__init__.py`: import `CreationRules`, `CREATION_COST_COLUMNS`,
   `CREATION_CAP_RANKS`, `CREATION_CAP_COLUMNS` from `.canon_skill`; import
   the five draft models and their five constants from `.pc_drafts` after
   `.quests`; add every new name to `__all__`; docstring layout gains
   `pc_drafts.py    — a player's character draft (PcDraft and its four child
   tables; TICKET-0126, schema v2.32), non-canon, pending.` and `pc_drafts`
   last in the « Import order » sentence; `canon_skill.py`'s entry gains
   `CreationRules (v2.32)`.
4. `models/pipeline.py`: `LORE_USAGE_STEPS` gains `"creation":
   ("creation_subject", "creation_design"),` after `perspective`; the CHECK
   string gains `"OR (kind = 'creation' AND step IN
   ('creation_subject','creation_design'))"` as its last line; the section
   comment above gains: `# Character-designer calls (v2.32, TICKET-0126) are
   journaled as kind \`creation\`.`
5. `writes/lore_usage.py`: `PAYLOAD_KEYS` gains C-02's two entries after
   `perspective_resolve`, with the comment `# creation steps (TICKET-0126):
   the draft, who asked (\`player:<user_id>\`), what the designer read and
   proposed, the violations left and the notes.`
6. `scripts/migrate_v2_32_character_creation.py` per C-02, a standalone copy
   of R-01's skeleton (docstring in v2.31's shape: what it adds, refuses
   below v2.31, idempotent, one raw transaction, post-checks, run line).
7. `schema_version.py`: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.32"`.
8. `world-engine-schema.md` (R-42): version line `v2.32`; a `###
   \`creation_rules\`` section after `skill_rank`'s; `### \`pc_draft\``,
   `### \`pc_draft_skill\``, `### \`pc_draft_sketch\``, `###
   \`pc_draft_membership\``, `### \`pc_draft_knowledge\`` after
   `quest_request`'s; the six override columns in the `skill_system` and
   `skill_definition` blocks after `trial_to_rank_5` with a `-- creation
   (v2.32): NULL = inherited` comment on the first of each; the journal
   section's prose gains « Character-designer calls (v2.32, TICKET-0126)
   are journaled as kind `creation`, steps `creation_subject` /
   `creation_design`. » and its CHECK the new pair; every new index in
   `## INDEXES` under a comment `-- character creation (v2.32)`.
9. `world-engine-schema-changelog.md`, a new first entry, verbatim:
   ```
   - **v2.32** — TICKET-0126, BRIEF-0126-B: a world sets its character
     creation rules, and a player's character draft is stored relationally.
     New `creation_rules` (one row per world: the pool, the cost to reach
     each rank, a cap per rank for Inexpérimenté and Apprenti to Maître, the
     maximum rank, the number of skills that require a master, whether
     skills are visible by default; a missing row is every default).
     `skill_system` gains `visible_at_creation`, `max_rank_at_creation`,
     `cap_raised_at_creation`, `cap_held_at_creation`; `skill_definition`
     gains `visible_at_creation`, `max_rank_at_creation` (nullable: NULL
     inherits). New `pc_draft`, `pc_draft_skill`, `pc_draft_sketch`,
     `pc_draft_membership`, `pc_draft_knowledge` (non-canon, pending). The
     Lore journal is rebuilt: its step CHECK admits `kind = 'creation'`
     with `creation_subject` and `creation_design`; rows are copied
     unchanged. `migrate_v2_32_character_creation.py` writes no other data.
   ```
10. `writes/worlds.py`: C-02's six names after `"quest_request",`.
11. `tooling/verify/checks/world_cascade.py`: `_FIXTURE` gains, after the
    `quest_request` row:
    ```python
    ("creation_rules", {"id": "cr-{w}", "world_id": "{w}"}),
    ("pc_draft", {"id": "pcd-{w}", "world_id": "{w}", "user_id": "u-{w}", "status": "draft"}),
    ("pc_draft_skill", {"id": "pcds-{w}", "draft_id": "pcd-{w}", "world_id": "{w}",
                        "skill_key": "agility", "player_rank": 2}),
    ("pc_draft_sketch", {"id": "pcdk-{w}", "draft_id": "pcd-{w}", "world_id": "{w}", "position": 0,
                         "name": "N", "kind": "family", "origin": "player"}),
    ("pc_draft_membership", {"id": "pcdm-{w}", "draft_id": "pcd-{w}", "world_id": "{w}",
                             "faction_id": "{w}-fac", "origin": "player"}),
    ("pc_draft_knowledge", {"id": "pcdn-{w}", "draft_id": "pcd-{w}", "world_id": "{w}", "position": 0,
                            "level": "rumor", "content": "c", "origin": "player"}),
    ```
    and `_build_world` inserts, right after the world row, `INSERT INTO user
    (id, name, role) VALUES (:u, :u, 'player')` with `u = f"u-{world_id}"`
    (a `user` row is not a world table: W1 is unchanged, W4 does not count
    it).
12. New check `tooling/verify/checks/creation_schema.py` (docstring first
    sentence: « G1 check for TICKET-0126 (BRIEF-0126-B) -- schema v2.32: the
    creation rules, the overrides, the draft tables and the creation
    journal kind. »), fresh temp-file DB per R-35:
    - **CS1 static.** By AST: `canon_skill.py` declares classes
      `SkillSystem`, `SkillDefinition`, `Skill`, `CreationRules` and
      assigns `BASE_SKILL_DOMAINS`, `RANK_POINTS_CHECK`; `canon.py` declares
      none of them. By import: `CreationRules`' columns, defaults and the
      CHECK name of C-02; the six override columns exist and are nullable;
      each draft table's columns, CHECK names and index names equal C-02's
      (`idx_pc_draft_open` unique with its WHERE); no JSON column on any of
      the six new tables; `LORE_USAGE_STEPS["creation"] ==
      ("creation_subject", "creation_design")`; the two `PAYLOAD_KEYS`
      entries equal C-02's; `EXPECTED_STATIC_SCHEMA_VERSION == "v2.32"`; the
      migration exists and `_PREVIOUS_VERSION == "v2.31"`.
    - **CS2 CHECKs** (fresh `create_all`, raw INSERTs, parents raw): a
      `creation_rules` row with only `id, world_id` reads back every default;
      `pool = -1`, `cost_to_rank_3 = -1`, `max_rank = 0`, `cap_at_rank_2 =
      -1`, and a second row for the same world each raise `IntegrityError`;
      a `pc_draft` with status `x` raises; two `draft` rows for one (world,
      user) raise, an `approved` plus a `draft` insert; a `pc_draft_skill`
      with both ranks NULL raises, with `player_rank = 6` raises; a sketch
      `master` without `skill_key` raises, a `family` with one raises; a
      knowledge `unaware` raises; `write_usage_event` with kind `creation`,
      step `creation_design`, C-02's keys and outcome `ok` writes; a raw
      INSERT kind `creation`, step `ask` raises.
    - **CS3 migration** (subprocess, `WORLD_ENGINE_DATABASE_URL` the
      fixture, `WORLD_ENGINE_ENV=test`): `create_all`, then the six new
      tables dropped and `skill_system`, `skill_definition`,
      `lore_usage_event` recreated from the literal `V231_DDL` (their
      `CREATE TABLE` and index statements compiled from the models at
      `fb8557a`, as `rank_trial_schema.py`'s `V228_DDL`); one system, one
      definition and one journal row inserted raw. (a) At `schema_meta`
      v2.30 the script exits non-zero and nothing changes; (b) at v2.31 it
      exits zero: the six tables and six columns exist, the stored journal
      SQL holds `'creation_design'`, the three rows are kept with their
      ids, `schema_meta` reads v2.32; (c) a second run exits zero and
      changes nothing.
    A rule that collected nothing fails; each sub-rule counted.
13. Commits: (1) models, journal, migration, schema docs, cascade (items
    1-11); (2) the check (item 12).

## Scope OUT

- Any reader or writer of the new tables (C, G), any route or UI.
- `canon_write_policy.txt` (C lists `creation_rules` with its writer).
- `skill_rank` (J1'): no column, no writer change.
- Data: no row is written; worlds without a `creation_rules` row read the
  defaults (C).
- `prompt_template` heads for the designer (F).
- Any 0129 column (approval, the created character's id): the status list
  already names `returned` and `approved`, nothing else is added.

## Invariants to defend

- INV-20 (UI-visible data never in JSON): every new column is relational;
  CS1 asserts no JSON column on the six tables. `json_ui_boundary.py` must
  stay green with an untouched allowlist.
- INV-60 (boot guard): the constant and the migration move together; Nia
  runs the migration before booting.
- History is sacred: the journal rebuild copies every row (post-check on
  the count).
- INV-41..46: the override columns are nullable and change no existing
  behavior.

## Decision rights

STOP:
- An anchor does not hold.
- The rebuild of `lore_usage_event` would lose or alter a row.
- `world_cascade.py` W1 lists a new table as world-reaching that C-02 does
  not name, or W4 fails on a foreign key the fixture cannot satisfy without
  touching a table outside C-02.

ADAPT:
- `_created_ts()` lacks a server default so a raw fixture INSERT fails on
  `created_at`/`updated_at`: add those columns to the fixture rows with
  `CURRENT_TIMESTAMP` text, report it.
- SQLite refuses `INSERT INTO user` unquoted: quote the table name, report.
- The check takes longer than 12 seconds under `corpus_gate.py`: add
  `"creation_schema.py": 30` to `SLOW_CHECK_TIMEOUTS` in `corpus_gate.py`
  (R-37), report the timing. Never drop a sub-rule to save time.

REPORT-ONLY:
- Existing rows of `skill_system` / `skill_definition` in Nia's database
  (they read NULL, which inherits).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/creation_schema.py`
      PASS (CS1-CS3).
- [ ] Named mutations, each turning the named rule red, then reverted:
      CS1 -- remove `cap_at_rank_0`'s server default; CS2 -- drop
      `ck_pc_draft_sketch_master`; CS3 -- delete the journal rebuild from
      `_plan()`.
- [ ] `world_cascade.py`, `json_ui_boundary.py`, `lore_usage.py`,
      `player_entry_schema.py`, `rank_trial_schema.py`,
      `schema_version_agreement.py`, `module_budget.py`, `corpus_gate.py`
      PASS.
- [ ] A copy of a v2.31 database migrated by the script reports the six
      tables and six columns added and boots (`cockpit` start, then stop by
      PID).
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `world-engine-schema.md` and its changelog (Scope IN 8, 9).
- The run line for Nia, in the report: `$env:WORLD_ENGINE_ENV="prod";
  python scripts/migrate_v2_32_character_creation.py` after a backup.
- No CLAUDE.md change in this step.
