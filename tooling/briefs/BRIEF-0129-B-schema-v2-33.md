<!-- slug: schema-v2-33 -->
# BRIEF 0129-B — "Schema v2.33: the review columns"

Lot: LOT-0129-creator-review.md (authoritative on conflict)
Depends on: nothing in this lot (A may run before or after)

## Anchors to confirm (Mini-RECON)

- `world-engine-schema.md:3` is `Current schema version: v2.32`;
  `src/world_engine/schema_version.py:15` is
  `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.32"`.
- `src/world_engine/models/pc_drafts.py` is 163 lines; `PC_SKETCH_MAX = 8`
  at :22; `class PcDraft` at :29, `class PcDraftSketch` at :94,
  `class PcDraftMembership` at :124.
- `src/world_engine/models/ephemeral.py:167` is `ENCOUNTER_SOURCES =
  ("visit", "gathering", "conversation", "schedule", "relation")`;
  `class NpcBatch` at :282, `class NpcBatchRow` at :303, neither declaring
  `__table_args__` except `NpcBatchRow`'s index.
- `scripts/migrate_v2_32_character_creation.py` holds `_PREVIOUS_VERSION =
  "v2.31"`, `_create_from_model`, `_rebuild`, `_apply`.
- `tooling/verify/checks/creation_schema.py:90-118` is `DRAFT_TABLES`;
  `:332` is `if EXPECTED_STATIC_SCHEMA_VERSION != "v2.32":`.

Halt if any anchor has moved.

## Facts carried

### R-01 -- the base, the version, the free ids, the debt of 0126
Opened: `git log -1` (`11cafc0`, « Merge pull request #155 from
niaairen31-ui/ticket/0126 »); `world-engine-schema.md:3`;
`src/world_engine/schema_version.py:15`; `.claude/rules/*.md` (grep
`INV-6`); `tooling/tickets/TICKET-0126-character-creation.md:241-245`;
`ls tooling/lots | grep AMENDMENT-0126`.
Finding: `Current schema version: v2.32`;
`EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.32"`. The highest invariant is
INV-67 (`.claude/rules/character-creation.md:20`). TICKET-0126's
« Amendment log » table holds only the empty row (lines 243-245) although
`tooling/lots/AMENDMENT-0126-01.md` exists.
Consequence: B moves the schema to v2.33; E adds INV-68; A writes the
missing amendment row.
### R-02 -- the draft tables
Opened: `src/world_engine/models/pc_drafts.py:1-163` (the declaring file).
Finding: module constants `PC_DRAFT_STATUSES = ("draft", "submitted",
"returned", "approved")` (:18), `PC_DRAFT_ORIGINS` (:19), `PC_SKETCH_KINDS
= ("family", "master", "faction", "other")` (:20), `PC_KNOWLEDGE_LEVELS =
("rumor", "suspicious", "partial", "knows")` (:21), `PC_SKETCH_MAX = 8`
(:22). `PcDraft` (:29-55): `id, world_id (FK world), user_id (FK user),
status (server default 'draft'), name, story (server default ''),
start_location_id (FK entity), start_location_set_by, creator_note,
submitted_at, created_at, updated_at`; CHECKs `ck_pc_draft_status` (the
four statuses) and `ck_pc_draft_set_by`; indexes `idx_pc_draft_world` and
the partial unique `idx_pc_draft_open (world_id, user_id) WHERE status <>
'approved'`. No column names the character an approval writes.
`PcDraftSkill` (:65-87): `skill_key` (a base domain or a definition id, no
FK), `player_rank`, `designer_rank`, `justification`, `designer_reason`.
`PcDraftSketch` (:94-121): `position, name, role, sentence, group_label
(server default ''), kind, skill_key, existing_entity_id (FK entity),
origin`; CHECKs `ck_pc_draft_sketch_kind`, `ck_pc_draft_sketch_master`
(`(kind = 'master') = (skill_key IS NOT NULL)`),
`ck_pc_draft_sketch_origin`; index `idx_pc_draft_sketch_draft`.
`PcDraftMembership` (:124-140): `faction_id (FK entity), role, origin`,
unique `idx_pc_draft_membership_faction (draft_id, faction_id)`.
`PcDraftKnowledge` (:144-163): `position, level, content, origin` -- free
text, no fact.
Consequence: the review columns are added to these classes (B, C-03); the
approval reads knowledge as text and lets `write_knowledge` make its fact
(R-19).
### R-12 -- the staging tables
Opened: `src/world_engine/models/ephemeral.py:160-190, 270-318`.
Finding: the NOTE (:273-281) marks `npc_batch` / `npc_batch_row`
ephemeral: never canon, never a `proposed_mutation`, purged when closed.
`NpcBatch` (:282-300): `id, world_id (FK world), status (server default
'open'), scope JSON, npcs_total, npcs_done, created_at, closed_at`; no
`__table_args__`. `NpcBatchRow` (:303-318): `id, batch_id (FK npc_batch),
line_index, kind, payload JSON, row_status (server default 'proposed'),
created_at, updated_at`; index `idx_npc_batch_row_batch`.
`ENCOUNTER_SOURCES = ("visit", "gathering", "conversation", "schedule",
"relation")` (:167), a tuple without a database CHECK.
Consequence: B adds `pc_draft_id` and `pc_group_label` to `NpcBatch` and
`pc_draft_sketch_id` to `NpcBatchRow` (C-03), and `pc_creation` to
`ENCOUNTER_SOURCES` (C-04).
### R-17 -- encounters
Opened: `src/world_engine/encounters.py:25, 55-113`; the enumeration below.
Finding: `record_encounter(db, *, world_id, a_id, b_id, source, at=None,
source_ref=None)` refuses a source outside `ENCOUNTER_SOURCES` with
`ValueError`, ignores a self pair, touches an existing pair, else adds and
flushes a `Rencontre`. Enumeration of readers of the tuple:
```
$ grep -rn "ENCOUNTER_SOURCES" src tooling | grep -v "^src/world_engine/models/"
src/world_engine/encounters.py:25:from .models import ENCOUNTER_SOURCES, Gathering, GatheringMember, Rencontre
src/world_engine/encounters.py:69:    `ENCOUNTER_SOURCES` raises `ValueError`. `at` defaults to now (UTC)."""
src/world_engine/encounters.py:70:    if source not in ENCOUNTER_SOURCES:
```
`rencontre` is not a canon table (`canon_write_policy.txt` [CANON_TABLES]).
Consequence: adding `pc_creation` (B) needs no migration and touches no
other reader; F-b's encounters are `record_encounter(source="pc_creation")`.
### R-21 -- the world cascade and the purge
Opened: `src/world_engine/writes/worlds.py:60-90, 125-160`;
`src/world_engine/cockpit/routes/creator.py:679-705`;
`src/world_engine/npc_group_author.py:513-520`; `src/world_engine/cockpit/app.py:200-230`.
Finding: `delete_world_cascade` sets `PRAGMA defer_foreign_keys = ON`
(:154) and deletes `_DIRECT_WORLD_SCOPED_DELETES` (which holds the five
`pc_draft*` tables, :85-86) in any order; the delete route then calls
`purge_world_link_batches` and `purge_world_npc_batches` (which deletes
every batch row then every batch of the world) before its one commit.
`purge_closed_npc_batches` keeps the two most recently closed batches at
startup and deletes the others.
Consequence: an FK `npc_batch.pc_draft_id -> pc_draft.id` is satisfied at
the cascade's commit (both gone); an open review batch is never purged; a
row's sketch reference carries no FK (a returned draft's sketches can be
deleted by the player while an abandoned batch still names them).
### R-22 -- migration and schema documents
Opened: `scripts/migrate_v2_32_character_creation.py:1-200`;
`world-engine-schema.md:3, 1393-1530, 2656-2680, 3421-3472`;
`world-engine-schema-changelog.md:1-30`;
`tooling/verify/checks/schema_partition.py:1-40`;
`tooling/verify/checks/quest_requests.py:79-81, 106`.
Finding: the v2.32 script refuses without `WORLD_ENGINE_ENV` or
`WORLD_ENGINE_DATABASE_URL`, refuses a `schema_meta.static_version` below
`_PREVIOUS_VERSION`, plans only what is missing, adds nullable columns by
`ALTER TABLE ... ADD COLUMN`, rebuilds a table whose CHECK changes with
`_rebuild` (rename, `CREATE TABLE` compiled from the model, copy the
columns, drop), runs in one raw transaction with `foreign_keys=OFF` and
`legacy_alter_table=ON`, post-checks, then moves `schema_meta`. The schema
document holds one `Current schema version:` line and per-table sections
(`pc_draft` :1393, `pc_draft_sketch` :1463, `pc_draft_membership` :1495,
`rencontre` :2656, `npc_batch` :3421, `npc_batch_row` :3451); the changelog
lists entries newest first as `- **vX.YY** — TICKET-...`. A later check
compares versions with `_version_key(...) < _version_key("v2.28")`
(`quest_requests.py:106`).
Consequence: B's script rebuilds `pc_draft_sketch` (two CHECKs) and adds
the other columns by ALTER; the docs sections listed get their columns.
### R-23 -- checks that pin the v2.32 shape
Opened: `tooling/verify/checks/creation_schema.py:1-60, 88-118, 250-345`;
`tooling/verify/checks/creation_budget.py:370-395`.
Finding: CS1 compares each draft table's column set for equality with
`DRAFT_TABLES` (:90-118, :297-300) and asserts
`EXPECTED_STATIC_SCHEMA_VERSION != "v2.32"` fails (:332-333). CS3 runs the
v2.32 script from a v2.31 fixture. CB5 forbids `db.add(`, `.commit(`,
`.flush(`, `chat(` in `creation_rules.py` and `creation_check.py`.
Consequence: B re-pins CS1's sets with the v2.33 columns and relaxes the
version assertion to `>= v2.32` (the `quest_requests.py` precedent);
`check_review` stays read-only.
### R-25 -- name bans across `src/` (the 0126 lesson)
Opened: `tooling/verify/checks/lore_as_facts.py:1-80`;
`knowledge_identity.py:25-40, 844-870`; `skill_progression.py:430-445`;
`npc_skills.py:40-45, 400-410`; `quest_rewards.py:170-182, 210`;
`event_contexts.py:72, 330-336`.
Finding: R1 bans an `ast.Attribute` named `appearance, backstory, secrets,
philosophy, internal_structure, internal_tensions, aversion, goals` outside
`models/`; K3 counts per file every `.subject` attribute, `"subject"`
constant, `subject=` keyword and `subject` parameter against a fixed census;
A4 bans the attribute and keyword `tier` (skill_progression) and the
attribute `.physical_tier` (npc_skills); RA1 bans `.owner_id`,
`.location_id`, `.equipped` on an object whose text mentions `item`;
`DROPPED = ("knowledge_status", "occurred_at", "has_magic_impact",
"consequences")` as attributes.
Tested against every name this lot introduces: `review_location_id`,
`character_id`, `review_action`, `review_entity_id`, `review_relation_type`,
`review_intensity`, `review_dropped`, `pc_draft_id`, `pc_group_label`,
`pc_draft_sketch_id`, `write_player_character`, `set_player_profile`,
`check_review`, `review_view`, `approve_draft`, `prepare_group_lot`,
`public_member_ids`, `character_name`: none is banned.
Consequence: the moved code carries the constant `"physical_tier"` (a dict
key, not an attribute: allowed) and no `subject`; the new code must not
read `.goals` or `.aversion` (a row's goals are read as
`row.payload.get("goals")`, as today).
### R-31 -- the arrow floor
Opened: `tooling/verify/checks/pipeline_state.py:54, 113-120`.
Finding: for a ticket in `brief`, `exec`, `verify`, `live-gate` or `done`,
every Machine-checkable arrow must name an existing file under
`tooling/verify/checks/` (or a retired one), else `pipeline_state.py`
fails, and `corpus_gate.py` with it.
Consequence: while 0129 is in `exec`, `pipeline_state.py` is red for each
arrow whose check a later brief creates (`review_schema.py` until B,
`creator_review.py` until C, `draft_approval.py` until E,
`creator_review_ui.py` until F); each brief's Done means names that red,
never a green `corpus_gate.py` before F.
### R-33 -- no JSON for what the creator sees
Opened: `tooling/verify/checks/json_ui_boundary.py:1-50`.
Finding: volet c fails any `Column(JSON` under `models/` absent from
`JSON_COLUMN_ALLOWLIST`; `NpcBatch.scope` and `NpcBatchRow.payload` are
listed (ephemeral staging).
Consequence: every review value is a column (C-03); a line's `name` and
`pc_draft_sketch_id` travel in `scope["lines"]` exactly as `faction_id`
and `location_id` already do, and the row's sketch is a column.
### R-34 -- the check fixture
Opened: `tooling/verify/checks/submitted_drafts.py:40-60, 155-170`;
`tooling/verify/checks/player_creation.py:90-140`.
Finding: `_fresh_engine()` sets `WORLD_ENGINE_DATABASE_URL` to a temp file
and `WORLD_ENGINE_ENV=test` before any `world_engine` import, purges
`world_engine*` from `sys.modules`, imports `world_engine.models`, runs
`SQLModel.metadata.create_all(engine)`. Routes are called through
`TestClient(app, base_url="http://127.0.0.1")` with `app` from
`world_engine.cockpit.app` (:159-166). Profiles come from
`writes.users.create_player_profile`; drafts from `writes/pc_drafts.py`.
Consequence: the lot's checks build their worlds this way, never on Nia's
database.

## Contracts

### C-03 -- schema v2.33
Produced by: B   Consumed by: C, D, E, G
`PcDraft` gains, after `submitted_at`:
- `review_location_id: Optional[str] = Field(default=None, foreign_key="entity.id")`
  -- the creator's starting place; NULL keeps the player's;
- `character_id: Optional[str] = Field(default=None, foreign_key="entity.id")`
  -- the character the approval wrote; NULL until then.
`PcDraftSketch` gains, after `origin`:
- `review_action: Optional[str] = None` -- NULL undecided, else one of
  `PC_REVIEW_ACTIONS`;
- `review_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")`
  -- the existing character an `attach` names;
- `review_relation_type: str = Field(default="ally", sa_column_kwargs={"server_default": text("'ally'")})`;
- `review_intensity: int = Field(default=60, sa_column_kwargs={"server_default": text("60")})`;
and three CHECKs in `__table_args__`:
`CheckConstraint("review_action IS NULL OR review_action IN ('create','attach','drop')", name="ck_pc_draft_sketch_review_action")`,
`CheckConstraint("(review_action IS 'attach') = (review_entity_id IS NOT NULL)", name="ck_pc_draft_sketch_review_entity")`,
`CheckConstraint("review_intensity BETWEEN 1 AND 100", name="ck_pc_draft_sketch_review_intensity")`.
`PcDraftMembership` gains, after `origin`:
- `review_dropped: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})`.
`NpcBatch` gains, after `closed_at`:
- `pc_draft_id: Optional[str] = Field(default=None, foreign_key="pc_draft.id")`
  -- set only on a review batch;
- `pc_group_label: Optional[str] = None` -- the sketches' `group_label`;
and `__table_args__ = (Index("idx_npc_batch_review_open", "pc_draft_id",
"pc_group_label", unique=True, sqlite_where=text("status = 'open' AND
pc_draft_id IS NOT NULL")),)`.
`NpcBatchRow` gains, after `updated_at`:
- `pc_draft_sketch_id: Optional[str] = None` -- no FK (R-21).
No JSON column. Migration `scripts/migrate_v2_33_creator_review.py`:
`_PREVIOUS_VERSION = "v2.32"`, `_THIS_VERSION = "v2.33"`, the env guard of
`migrate_v2_32_character_creation.py` (its lines 39-52 with the file name
changed), `_refuse` / `_tables` / `_columns` / `_create_from_model` /
`_rebuild` copied from that script; it rebuilds `pc_draft_sketch` (copying
`id, draft_id, world_id, position, name, role, sentence, group_label,
kind, skill_key, existing_entity_id, origin`) while its stored SQL lacks
`ck_pc_draft_sketch_review_action`; adds `pc_draft.review_location_id
VARCHAR REFERENCES entity (id)`, `pc_draft.character_id VARCHAR REFERENCES
entity (id)`, `pc_draft_membership.review_dropped BOOLEAN NOT NULL DEFAULT
0`, `npc_batch.pc_draft_id VARCHAR REFERENCES pc_draft (id)`,
`npc_batch.pc_group_label VARCHAR`, `npc_batch_row.pc_draft_sketch_id
VARCHAR`, each only while absent; creates `idx_npc_batch_review_open`
(compiled from the model) while absent; one raw transaction with
`foreign_keys=OFF` and `legacy_alter_table=ON`; post-checks (every column
and the index present, the sketch SQL holds the three CHECK names, the
sketch row count unchanged) before `schema_meta` moves to v2.33.
### C-04 -- review constants and the encounter source
Produced by: B   Consumed by: C, D, E
In `models/pc_drafts.py`, after `PC_SKETCH_MAX`:
`PC_REVIEW_ACTIONS: tuple[str, ...] = ("create", "attach", "drop")`,
`PC_REVIEW_DEFAULT_RELATION = "ally"`, `PC_REVIEW_DEFAULT_INTENSITY = 60`;
exported by `models/__init__.py` beside the other `PC_*` names.
`ENCOUNTER_SOURCES = ("visit", "gathering", "conversation", "schedule",
"relation", "pc_creation")`.

## Context

The creator's review (A1) needs columns of its own beside the player's
version, the draft must lead to the character it gave (C1), a review batch
must know its draft and group (D2) and a batch row its sketch, and F-b's
encounters need their source. This brief is the schema step: models,
migration, docs, the shape checks. Nothing reads the new columns yet.

## Scope IN

1. `models/pc_drafts.py`: C-04's three constants after `PC_SKETCH_MAX`;
   C-03's columns and CHECKs on `PcDraft`, `PcDraftSketch`,
   `PcDraftMembership`, each column with a one-line comment (the C-03
   gloss). The module docstring gains a sentence: « v2.33 (TICKET-0129,
   BRIEF-0129-B): the creator's review choices (`review_*`) and the
   approved character (`character_id`) sit beside the player's version;
   the player's reads never name them. »
2. `models/__init__.py`: import and export `PC_REVIEW_ACTIONS`,
   `PC_REVIEW_DEFAULT_RELATION`, `PC_REVIEW_DEFAULT_INTENSITY` beside the
   other `PC_*` names.
3. `models/ephemeral.py`: `ENCOUNTER_SOURCES` per C-04; `NpcBatch` gets
   C-03's two columns and its `__table_args__`; `NpcBatchRow` gets
   `pc_draft_sketch_id`. The `npc_batch` NOTE gains: « TICKET-0129
   (BRIEF-0129-B, D2): a batch with `pc_draft_id` is a creator review
   batch, one open per draft and group; it is written to canon only by the
   character approval. `npc_batch_row.pc_draft_sketch_id` names the sketch
   a review row develops, without an FK: a returned draft's sketches may
   be deleted while an abandoned batch still names them. » Keep `import`s
   as needed (`Index`, `text` are already imported there; add only what is
   missing).
4. `schema_version.py`: `"v2.33"`; `world-engine-schema.md:3`:
   `Current schema version: v2.33`.
5. `scripts/migrate_v2_33_creator_review.py` per C-03: docstring in the
   v2.32 script's shape (what it does, refusal below v2.32, idempotent,
   one raw transaction, post-checks, how to run); `_NEW_COLUMNS` holds the
   six ALTER column clauses of C-03 exactly; `_plan()` returns the sketch
   rebuild when the stored `pc_draft_sketch` SQL lacks
   `ck_pc_draft_sketch_review_action`, the ALTERs whose column is absent,
   the index when absent; `_post_checks` per C-03; prints what it did, or
   « Nothing to do. » as the v2.32 script does.
6. `world-engine-schema.md`: the `pc_draft`, `pc_draft_sketch`,
   `pc_draft_membership`, `npc_batch`, `npc_batch_row` and `rencontre`
   sections (:1393, :1463, :1495, :3421, :3451, :2656) list the new
   columns / CHECKs / index / source with one gloss each, « (v2.33,
   TICKET-0129) ».
7. `world-engine-schema-changelog.md`, newest first, verbatim:
   ```
   - **v2.33** — TICKET-0129, BRIEF-0129-B: the creator reviews a
     submitted character. `pc_draft` gains `review_location_id` (her
     starting place) and `character_id` (the character the approval
     wrote); `pc_draft_sketch` gains `review_action` (create, attach,
     drop), `review_entity_id`, `review_relation_type` ('ally'),
     `review_intensity` (60) and three CHECKs (the table is rebuilt);
     `pc_draft_membership` gains `review_dropped`; `npc_batch` gains
     `pc_draft_id`, `pc_group_label` and the partial unique index
     `idx_npc_batch_review_open`; `npc_batch_row` gains
     `pc_draft_sketch_id` (no FK). `rencontre.source` admits
     `pc_creation` (a tuple, no CHECK). `migrate_v2_33_creator_review.py`
     writes no other data.
   ```
8. `tooling/verify/checks/creation_schema.py`: CS1's `DRAFT_TABLES` sets
   gain the v2.33 columns and CHECK names of `pc_draft`, `pc_draft_sketch`,
   `pc_draft_membership` (a comment above: « v2.33 columns (TICKET-0129,
   BRIEF-0129-B); `review_schema.py` owns their shape »); `:332` becomes a
   `_version_key(EXPECTED_STATIC_SCHEMA_VERSION) < _version_key("v2.32")`
   test, with `_version_key` as in `quest_requests.py:79-81`; docstring
   CS1 says « at least v2.32 ». CS3 is unchanged: the v2.32 script creates
   the draft tables from the current models.
9. New check `tooling/verify/checks/review_schema.py`, first sentence « G1
   check for TICKET-0129 (BRIEF-0129-B) -- schema v2.33: the creator's
   review columns, the approved character, the review batches and the
   encounter source. », fresh database per R-34:
   - **RS1** static, by import: every C-03 column on its model with its
     nullability, server default and FK target; the three CHECK names on
     `pc_draft_sketch`; `idx_npc_batch_review_open` unique on
     `(pc_draft_id, pc_group_label)` with `WHERE status = 'open' AND
     pc_draft_id IS NOT NULL`; `NpcBatchRow.pc_draft_sketch_id` has no FK;
     C-04's constants; `ENCOUNTER_SOURCES[-1] == "pc_creation"`;
     `EXPECTED_STATIC_SCHEMA_VERSION == "v2.33"`; the migration exists with
     `_PREVIOUS_VERSION = "v2.32"`; no new `Column(JSON` (the JSON columns
     of the five tables are exactly `npc_batch.scope` and
     `npc_batch_row.payload`).
   - **RS2** CHECKs, raw INSERTs after a fresh `create_all`, each refusal
     paired with an admitted row of the same table: a sketch with
     `review_action = 'x'`; `'attach'` with no entity; NULL action with an
     entity; intensity 0 and 101 -- refused; `'create'` with no entity and
     `'attach'` with one -- admitted; a sketch inserted without the review
     columns reads `ally` and 60; a membership without `review_dropped`
     reads 0; two `open` batches with the same `(pc_draft_id,
     pc_group_label)` refused; an `abandoned` and an `open` one admitted;
     two `open` batches with `pc_draft_id` NULL admitted.
   - **RS3** migration as a subprocess (`WORLD_ENGINE_DATABASE_URL` set):
     the fixture creates every table, then recreates `pc_draft`,
     `pc_draft_sketch`, `pc_draft_membership`, `npc_batch`, `npc_batch_row`
     from literal v2.32 DDL (compile the five `CreateTable` statements and
     their indexes from the models at `11cafc0`, before this brief's
     edits, and paste them as constants), one row each inserted raw, then:
     (a) at `schema_meta` v2.31 the script exits non-zero and nothing
     changes; (b) at v2.32 it exits zero: every C-03 column and the index
     exist, the stored sketch SQL holds the three CHECK names, the five
     rows keep their ids and values, the sketch reads `ally` and 60, the
     membership 0, `schema_meta` reads v2.33; (c) a second run exits zero
     and changes nothing.
   A sub-rule not reached is a FAILURE.
10. Commits: (1) items 1-4, 6-7 (models and docs); (2) item 5 and RS3;
    (3) items 8-9.

## Scope OUT

- Any reader or writer of the new columns (C, D, E, G).
- A CHECK on `npc_batch.pc_group_label` or on `rencontre.source`.
- Changing the v2.32 script.
- Editing `world_cascade.py`: its raw inserts stay valid (R-21, gate (c)).

## Invariants to defend

- INV-20: every value the creator sees is a column; the JSON allow-list
  is untouched (RS1).
- INV-12: no new hard delete; the world cascade still deletes the draft
  tables, and the review batches with the world's batches (R-21).
- INV-67: no draft row reaches canon here.

## Decision rights

STOP:
- An anchor does not hold.
- `ALTER TABLE ... ADD COLUMN ... REFERENCES` is refused by the SQLite of
  this machine: report the error; do not rebuild `pc_draft` instead.
- `world_cascade.py`, `purge_fk_ordering.py` or `npc_batch_purge.py` turns
  red.

ADAPT:
- `models/ephemeral.py` lacks an import the new columns need: add it,
  report.
- The v2.32 helpers need a small signature change to serve both tables:
  copy and adapt them in the new script (never edit the v2.32 script),
  report.

REPORT-ONLY:
- Rows of Nia's database the migration would touch (it runs on her copy
  only after the merge).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/review_schema.py`
      PASS (RS1-RS3); `creation_schema.py`, `schema_version_agreement.py`,
      `schema_partition.py`, `json_ui_boundary.py`, `world_cascade.py`,
      `purge_fk_ordering.py`, `npc_batch_purge.py`, `env_guard.py`,
      `module_budget.py` PASS.
- [ ] Named mutations, each red then reverted: drop
      `ck_pc_draft_sketch_review_entity` -> RS2; give
      `pc_draft_sketch_id` an FK -> RS1; make the script skip the sketch
      rebuild -> RS3 (b).
- [ ] `corpus_gate.py`: every check PASS except `pipeline_state.py`, red
      only on the arrows to `creator_review.py`, `draft_approval.py`,
      `creator_review_ui.py`.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- Schema document and changelog (Scope IN 6-7), the `npc_batch` NOTE and
  the `pc_drafts.py` docstring. After the merge, Nia runs, after a backup:
  `python scripts/migrate_v2_33_creator_review.py`.
