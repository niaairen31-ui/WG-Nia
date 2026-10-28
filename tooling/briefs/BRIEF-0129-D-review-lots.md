<!-- slug: review-lots -->
# BRIEF 0129-D — "One NPC batch per group, anchored on the character"

Lot: LOT-0129-creator-review.md (authoritative on conflict)
Depends on: A (strata check sets, R-13), B (C-03), C (C-05, C-08's module)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/cockpit/routes/npc_agent.py`: `_open_batch` at :50
  (filters `world_id` and `status == "open"`), `list_npc_batches` at
  :115, `_commit_npc_batch` with its first guard `if batch.status !=
  "open":` (line numbers after A: confirm by grep, not by number).
- `src/world_engine/npc_group_author.py:380-383` forces
  `draft["public"]["faction_id"]`; `:393` builds `NpcBatchRow(batch_id=...,
  line_index=..., kind="draft", payload=payload, row_status="proposed")`.
- `src/world_engine/cockpit/routes/pc_review.py` exists with the GET, PUT
  and `renvoyer` routes (C landed); its GET answers `groups` with `lot:
  None` and `blockers: []`.
- `tooling/verify/checks/npc_agent_strata.py` lists
  `cockpit/npc_group_commit.py` in both sets (A landed).
- `models/ephemeral.py` declares `NpcBatch.pc_draft_id`,
  `pc_group_label`, `NpcBatchRow.pc_draft_sketch_id` (B landed).

Halt if any anchor has moved.

## Facts carried

### R-10 -- the NPC agent's route
Opened: `src/world_engine/cockpit/routes/npc_agent.py:1-298`.
Finding: imports `NpcBatch, NpcBatchRow` (:29), `journal_append,
patch_npc_row, resolve_vocabulary, run_next_npc` (:30), `write_npc_goal`
(:31), `crud as _crud` (:32). `_open_batch(world_id, db)` (:50-55) is the
first `open` batch of the world; `create_npc_batch` (:65-112) 409s when it
finds one, validates each line (`count >= 1`, non-empty `description`,
`faction_id` in the vocabulary, `location_id` in the expanded set), sums
`total += count`, 422s above 30, stores `scope = {root_location_id,
expanded_location_ids, lines, group_brief}`, commits. `list_npc_batches`
(:115-125) returns every batch of the world. `get_npc_batch` (:128-136),
`abandon_npc_batch` (:139-153), `run_next_npc_batch` (:156-163),
`patch_npc_batch_row` (:166-175) take a batch id and no world filter.
`_commit_npc_row_goals(db, world_id, npc_id, goals)` (:178-195) writes the
long and short goals through `write_npc_goal`. `_commit_npc_row(row,
batch, db)` (:198-235) builds `EntityWriteBody(entity={"type":
"character", "name"}, extension={"character_type": "npc",
"current_location_id": row.payload["location_id"], ["faction_id"]},
facets=draft["facets"], carrure=pub.get("physical_tier"))`, calls
`_crud._create_entity_core`, writes each secret knowledge through
`_crud._create_knowledge_core` (`is_secret=True`), the goals, and returns
`{"row_id", "entity_id", "name"}`; it never commits and writes no
relation. `_commit_npc_batch` (:238-290) refuses a non-open batch and
`npcs_done != npcs_total`, commits rows `proposed`/`edited` of kind
`draft`, marks them and the batch `committed`, one `db.commit()`, journals.
Consequence: A moves `_commit_npc_row_goals` and `_commit_npc_row`
verbatim to `cockpit/npc_group_commit.py` (C-02); D filters review batches
out of `_open_batch` and `list_npc_batches` and refuses them in
`_commit_npc_batch` (C-09); the id routes serve review batches unchanged.
### R-11 -- the NPC group author
Opened: `src/world_engine/npc_group_author.py:30-56, 56-91, 170-235, 341-403, 405-470`
(520 lines).
Finding: `JOURNAL_DIR = Path.home() / ".world_engine" / "npc_agent_journal"`
(:41), read by `journal_append` at call time. `resolve_vocabulary(db,
root_location_id)` (:56-91) expands the root (zones dropped) and lists the
factions of the world where `World.is_active == True` (:74).
`plan_placements` (:170-191) calls the model only for lines without a
`location_id`. `_resolve_unit_location` (:203-222) returns a line's pinned
`location_id` first. `run_next_npc(db, batch)` (:341-403) refuses a
non-open batch, composes the brief, calls `generate_entity_draft(
"character", brief, db)` -- a name imported into the module (:33) --
forces `draft["public"]["faction_id"]` from the line (:380-383), checks the
name for collisions, calls `_generate_row_goals` (which calls the imported
`generate_npc_goals`), builds `NpcBatchRow(batch_id, line_index,
kind="draft", payload, row_status="proposed")` (:393), bumps
`npcs_done`, commits. `patch_npc_row` (:456-) edits `name`, the facet
strings, `physical_tier`, `faction_id`, `location_id` (within the
expanded set), the goals, and `row_status` in `("proposed", "rejected")`
(:407).
Consequence: a review batch pins every line's `location_id` to its root,
so no placement call is made; D forces the line's `name` and copies its
`pc_draft_sketch_id` to the row next to the faction forcing (C-10); a
check stubs `npc_group_author.generate_entity_draft`,
`npc_group_author.generate_npc_goals` and `npc_group_author.JOURNAL_DIR`
by assignment (they are module attributes read at call time).
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
### R-13 -- the strata check of the NPC agent
Opened: `tooling/verify/checks/npc_agent_strata.py:1-210`.
Finding: guarantee 1 (:97-106): the strings `npc_batch` and
`npc_batch_row` appear in no file of `src/world_engine/writes/` and not in
`canon_write_policy.txt`. Guarantee 2 (:121-150): a module referencing
`NpcBatch` or `NpcBatchRow` (an `ast.Name` or an `ImportFrom` alias) must
be in `ALLOWED_REFERENCE_FILES` (:52-58: `cockpit/routes/npc_agent.py`,
`npc_group_author.py`, `models/ephemeral.py`, `models/__init__.py`,
`cockpit/app.py`). Guarantee 3 (:155-200): the files of
`DIRECT_WRITE_SCAN_FILES` (:65-68: the route and the author) hold no
`db.add(<Entity|Character|FactionMembership|Knowledge|NpcGoal>(...))` and
no raw INSERT/UPDATE on those tables.
Consequence: A adds `src/world_engine/cockpit/npc_group_commit.py` to both
sets; D adds `src/world_engine/cockpit/pc_approval.py` to both; no
`writes/` module may name the staging tables, so the approval's
orchestration lives in `cockpit/pc_approval.py` (J1) and the character
writer in `writes/` never mentions them.
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
### R-27 -- module budgets of the files this lot edits
Opened: `ast` count (module functions plus methods of module classes) and
`wc -l` at `11cafc0`; `tooling/verify/checks/module_budget.py:1-60`.
Finding: caps 1000 lines and 40 functions (`src/**/*.py`), 1000 lines
(`frontend/src/**`). `routes/creator.py` 968 / 35; `routes/npc_agent.py`
298 / 12; `npc_group_author.py` 520 / 18; `writes/pc_drafts.py` 325 / 18;
`creation_check.py` 257 / 8; `perspective_selectors.py` 321 / 14;
`models/pc_drafts.py` 163; `models/ephemeral.py` 318;
`routes/player_creation.py` 326 / 15; `cockpit/app.py` 347 / 12;
`writes/characters.py` 272 / 5; `PcDraftPanel.svelte` 140;
`PjSkillFiche.svelte` 249; `CharacterCreation.svelte` 91;
`character.svelte.js` 189; `tabs.js` 898; `WorldPage.svelte` 90.
Consequence: nothing new enters `routes/creator.py` (it shrinks by three
functions in A); every other file stays far under its caps; `tabs.js` is
not edited.
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
### C-05 -- the review check
Produced by: C   Consumed by: C's routes, D (blockers sit beside it), E
In `creation_check.py`:
```
REVIEW_VIOLATION_CODES: tuple[str, ...] = (
    "review_place_invalid", "sketch_undecided", "attach_invalid",
    "attach_duplicate", "master_not_master", "relation_type_invalid",
    "world_has_pc",
)
def review_place_id(draft: PcDraft) -> Optional[str]
def check_review(db: Session, draft: PcDraft) -> tuple[Violation, ...]
```
`review_place_id` is `draft.review_location_id` when set, else
`draft.start_location_id`. `check_review` reads only, never through the
public view, in this order:
1. `name_missing`, `story_missing` -- `check_draft`'s messages.
2. No place -> `start_place_missing` (« Choisis un lieu de départ. »); a
   place that is not an active `location` entity of the draft's world, or
   is in `zone_ids(db, world_id)` -> `review_place_invalid` « Ce lieu de
   départ ne peut pas être choisi. ».
3. `check_creation(db, world_id, {skill_key: player_rank ...},
   enforce_visibility=True).violations`.
4. `too_many_sketches` -- `check_draft`'s rule and message.
5. `master_without_sketch` -- `check_draft`'s rule and message, counting
   only master sketches whose `review_action` is not `drop`.
6. Each sketch by `(position, id)`:
   - `review_action` NULL -> `sketch_undecided` « « {name} » : choisis de
     créer cette personne, de la rattacher ou de l'écarter. »;
   - `attach` whose `review_entity_id` is not an active `character` entity
     of the world with a `character_type` other than `player` ->
     `attach_invalid` « « {name} » : le personnage choisi n'existe pas
     dans ce monde. »; else an entity an earlier `attach` sketch already
     names -> `attach_duplicate` « « {name} » : ce personnage est déjà
     choisi pour une autre personne. »; else a `master` sketch whose entity
     is not in
     `skill_masters(...)` for its `skill_key` -> `master_not_master`
     « « {name} » n'est pas Maître en « {skill} ». » (`{skill}` the
     `start_sheet` name of the key);
   - `create` or `attach` whose `review_relation_type` (stripped) is empty,
     not `is_social`, or in `RETIRED_RELATION_TYPES` ->
     `relation_type_invalid` « « {name} » : le lien « {type} » ne peut
     pas être choisi. ».
7. Each membership not `review_dropped` whose faction is not an active
   `faction` entity of the world -> `membership_invalid` (`check_draft`'s
   message).
8. `pc_exists` -- `check_draft`'s rule and message.
9. Any `character_type == "player"` character in the world ->
   `world_has_pc` « Ce monde a déjà un personnage joueur : l'approbation
   attend le sélecteur « PJ actif ». ».
A skill key is a base domain when it is in `BASE_SKILL_DOMAINS` (then
`skill_masters(..., definition_id=None, domain=key)`), else a definition id
(`definition_id=key, domain=None`). `DRAFT_VIOLATION_CODES` is unchanged.
### C-08 -- the review routes
Produced by: C (D, E, G add routes)   Consumed by: F, G's frontend
Module `src/world_engine/cockpit/routes/pc_review.py`, keyed by the active
world (`_world_id` from `..crud._shared`); a draft of another world, or not
`submitted` where a submitted one is required, answers 404 `Brouillon
introuvable.`.
- `GET /api/pc-reviews/{draft_id}` -> exactly `{"draft", "player_name",
  "review", "choices", "verdict", "skill_names", "ranks", "groups",
  "blockers"}`: `draft` is `draft_view(db, draft, view=None)`; `review` is
  C-07's `review_view`; `choices` is `review_choices` plus
  `"relation_types": [t for t in RELATION_TYPES if is_social(t)]`;
  `verdict` is `verdict_dict(check_creation(... player ranks ...,
  enforce_visibility=True), check_review(db, draft))`; `skill_names` and
  `ranks` as `GET /api/pc-drafts/{id}`; `groups` is `[{"label",
  "sketch_ids", "lot"}]` for the sketches whose action is `create`, groups
  by first position, `lot` null until D; `blockers` `[]` until D.
- `PUT /api/pc-reviews/{draft_id}` body `{"review_location_id": str |
  null, "sketches": [{"id", "action", "entity_id", "relation_type",
  "intensity"}], "memberships": [{"id", "dropped"}]}` -> `save_review`,
  commit, the GET shape. `DraftLocked` -> 409; `ValueError` -> 422.
- `POST /api/pc-reviews/{draft_id}/renvoyer` body `{"note"}` ->
  (D: `abandon_review_lots` first) `return_draft`, commit, `{"ok": true,
  "status": "returned"}`; `ValueError` -> 422.
- D: `POST /api/pc-reviews/{draft_id}/lots` body `{"group_label"}` ->
  C-09's `prepare_group_lot`, commit, then `journal_append(batch.id,
  {"event": "batch_created", "scope": batch.scope, "pc_draft_id":
  draft.id})`, answer `{"batch_id", "npcs_total"}`; `ValueError` -> 422.
- E: `POST /api/pc-reviews/{draft_id}/approuver` -> C-11, commit, then
  one `journal_append(lot_id, {"event": "commit_by_approval",
  "pc_draft_id", "character_id"})` per committed lot, answer `{"ok": true,
  "character_id", "name"}`; `ApprovalRefused` or `DraftLocked` -> 409
  `Ce personnage ne peut pas encore être approuvé.`; `ValueError` or
  `IntegrityError` -> 409 with its text; every refusal rolls back first.
- G: C-14's two profile routes.
`app.py` registers the router (R-30).
### C-09 -- the review batches
Produced by: D   Consumed by: C-08 (D's additions), E
Module `src/world_engine/cockpit/pc_approval.py` (allowed by
`npc_agent_strata.py`, R-13):
```
def review_groups(db, draft) -> list[dict]          # [{"label", "sketch_ids"}]
def open_review_lots(db, draft) -> list[NpcBatch]    # open batches with pc_draft_id = draft.id, by created_at
def lot_view(batch: NpcBatch) -> dict                # {"batch_id", "status", "npcs_done", "npcs_total"}
def prepare_group_lot(db, draft, group_label: str) -> NpcBatch
def abandon_review_lots(db, draft) -> list[str]
def review_blockers(db, draft) -> list[dict]         # [{"code", "label", "sketch_id", "message"}]
```
`review_groups`: the draft's `create` sketches by `(position, id)`,
grouped by `group_label`, groups in order of first appearance.
`prepare_group_lot`: the draft is `submitted` (`DraftLocked` otherwise);
the group has a `create` sketch (`ValueError("Ce groupe n'a personne à
créer.")`); no open batch for `(draft.id, group_label)`
(`ValueError("Un lot est déjà ouvert pour ce groupe.")`); `root =
review_place_id(draft)` (C-05); `vocabulary = resolve_vocabulary(db,
root)`; one line per `create` sketch of the group, in order:
`{"count": 1, "description": D, "faction_id": None, "location_id": root,
"name": sketch.name, "pc_draft_sketch_id": sketch.id}` with `D =
f"{sketch.name}, {sketch.role or 'une personne de son histoire'}."`, then
`f" {sketch.sentence}"` when the sentence is not empty, then, for a
`master`, `f" Maître en « {skill} », il a enseigné cette compétence à
{draft.name}."`; `group_brief` verbatim:
```
Ces personnes viennent de l'histoire de {draft.name}, un personnage joueur qui entre dans le monde. Chacune le connaît ; développe-la avec tout ce que le monde sait.
Groupe : {group_label or 'sans groupe'}.

Histoire de {draft.name} :
{draft.story}
```
`NpcBatch(world_id=draft.world_id, scope={"root_location_id": root,
"expanded_location_ids": vocabulary["expanded_location_ids"], "lines":
lines, "group_brief": brief}, npcs_total=len(lines),
pc_draft_id=draft.id, pc_group_label=group_label)`, added and flushed;
never commits. `abandon_review_lots`: every open batch of the draft ->
`status = "abandoned"`, `closed_at = now`; returns their ids.
`review_blockers`, for each `create` sketch by `(position, id)`: no open
batch for its group -> `lot_missing` « « {label} » : prépare le lot de ce
groupe. »; else `npcs_done < npcs_total` -> `lot_incomplete` « « {label} »
: la génération du lot n'est pas terminée. »; else no row of that batch
with `pc_draft_sketch_id == sketch.id`, `kind == "draft"` and
`row_status in ("proposed", "edited")` -> `row_missing` « « {name} » :
aucune fiche retenue dans le lot. ». `{label}` is the label or `sans
groupe`. One blocker per sketch at most; a group's `lot_missing` /
`lot_incomplete` is listed once per group.
In `cockpit/routes/npc_agent.py`: `_open_batch` and `list_npc_batches`
add `.where(NpcBatch.pc_draft_id.is_(None))`; `_commit_npc_batch`, right
after its `status != "open"` guard, raises 409 « Ce lot appartient à la
revue d'un personnage : il s'écrit à l'approbation. » when
`batch.pc_draft_id is not None`.
### C-10 -- a review line reaches its row
Produced by: D   Consumed by: E
In `npc_group_author.run_next_npc`, right after the faction forcing
(:380-383): `name_override = (line.get("name") or "").strip()` and, when
not empty, `draft["public"]["name"] = name_override`; the
`NpcBatchRow(...)` of :393 also receives
`pc_draft_sketch_id=line.get("pc_draft_sketch_id")`. A line without those
keys (every agent batch) behaves as before.

## Context

F'a-1, applied to the letter (D2): each logical group of people the
creator chose to create becomes one batch of the existing NPC generator,
anchored on the character -- his story and his starting place --, which
she generates and reviews row by row with the agent's existing id routes.
These batches must never reach the agent's own panel, its « one open
batch » rule or its commit: only the approval (E) writes them.

## Scope IN

1. New `src/world_engine/cockpit/pc_approval.py` with C-09's functions
   (docstring first sentence « The creator's approval of a character
   draft (TICKET-0129): the review batches, one per group of people to
   create, and the one transaction that writes the draft to canon. Never
   commits. »). Imports `NpcBatch, NpcBatchRow, PcDraft, PcDraftSketch`
   from `..models`, `resolve_vocabulary` from `..npc_group_author`,
   `review_place_id` from `..creation_check`, `start_sheet` from
   `..creation_rules` (the master's skill name), `DraftLocked` and
   `REVIEW_LOCKED_MESSAGE` from `..writes.pc_drafts`.
2. `routes/pc_review.py`: C-08's `POST /api/pc-reviews/{draft_id}/lots`
   (body `PcLotBody {group_label: str = ""}`; `DraftLocked` -> 404
   `Brouillon introuvable.`, `ValueError` -> 422); `renvoyer` calls
   `abandon_review_lots` before `return_draft`, and journals
   `{"event": "batch_abandoned", "pc_draft_id": ...}` per abandoned id
   after the commit; `_review_body` fills each group's `lot` with
   `lot_view` of its open batch (else None) and `blockers` with
   `review_blockers`. `journal_append` is imported from
   `...npc_group_author`.
3. `routes/npc_agent.py`, per C-09: the `pc_draft_id IS NULL` filter in
   `_open_batch` and `list_npc_batches`, the 409 guard in
   `_commit_npc_batch` right after its `status != "open"` guard. Docstring:
   « Review batches (`pc_draft_id` set, TICKET-0129) are served by the id
   routes, never listed, never counted as the open batch, never committed
   here. »
4. `npc_group_author.run_next_npc` per C-10.
5. `tooling/verify/checks/npc_agent_strata.py`: add
   `"src/world_engine/cockpit/pc_approval.py"` to `ALLOWED_REFERENCE_FILES`
   and, with a constant `PC_APPROVAL_FILE`, to `DIRECT_WRITE_SCAN_FILES`;
   the docstring names it (TICKET-0129, BRIEF-0129-D).
6. `tooling/verify/checks/creator_review.py`, new rule **CR5** (and the
   docstring's line): `npc_group_author.generate_entity_draft`,
   `npc_group_author.generate_npc_goals` and `npc_group_author.JOURNAL_DIR`
   are replaced by assignment (a stub returning `{"ok": True, "draft":
   {"public": {"name": "Autre nom", "physical_tier": 0}, "secret":
   {"knowledge": []}, "facets": {}}, "notes": []}`, a stub returning `{"ok":
   False, "error": "stub"}`, a temp directory) and restored in `finally`.
   On CR1's clean draft, reviewed so that its master sketch is `create`
   in group `Famille`, its family sketch `create` in `Famille`, and a third
   (family) sketch `create` in group `""` (submitted):
   - `POST lots` for `Famille` -> 200, `npcs_total == 2`; the batch's
     `pc_draft_id`, `pc_group_label == "Famille"`, `scope["lines"]` one per
     sketch in order with C-09's keys, `location_id` the review place,
     `description` per C-09, the master's line holding « Maître en »;
     `group_brief` holds the draft's name and story; a second `POST` for
     `Famille` -> 422 `Un lot est déjà ouvert pour ce groupe.`; a group
     with no `create` sketch -> 422.
   - An agent batch can be created (`POST /api/npc-batches`) while the
     review batch is open, and a review batch prepared while an agent
     batch is open; `GET /api/npc-batches` lists only the agent batch.
   - `POST /api/npc-batches/{id}/run-next` twice on the review batch ->
     two rows named as their sketches (not `Autre nom`), each with its
     `pc_draft_sketch_id`; a run-next on the agent batch keeps the
     stub's name and a NULL sketch id.
   - `POST /api/npc-batches/{id}/commit` on the review batch -> 409 C-09's
     message, nothing written.
   - `GET /api/pc-reviews/{id}`: `Famille`'s `lot` is `{batch_id, status
     "open", npcs_done 2, npcs_total 2}`; `blockers` holds exactly one
     `lot_missing` for group `""`; after a row of `Famille` is rejected
     (`PATCH` row_status `rejected`), `row_missing` for its sketch.
   - `renvoyer` -> both open review batches `abandoned`; the agent batch
     still `open`.
7. Commits: (1) items 1, 4 and the C-09 functions' rule cases; (2) items
   2-3, 5 and the rest of CR5.

## Scope OUT

- `approve_draft` (E); writing any canon row here.
- A batch per draft (D1, rejected); a placement model call (every line is
  pinned to the review place).
- Editing the agent's panel (`NpcAgent.svelte`, `npcAgent.svelte.js`):
  it no longer sees review batches because the list filters them.
- Patching a review row's location outside the root's expansion
  (`patch_npc_row`'s rule holds).

## Invariants to defend

- INV-08 and the strata guarantees: no canon write in this brief; the
  review batch stays ephemeral staging; `pc_approval.py` joins the strata
  check before it references the models.
- INV-20: the line's `name` and `pc_draft_sketch_id` travel in the scope
  as `faction_id` already does (R-33); the row's sketch is a column.
- `npc_batch_count_contract.py`: `_line_units`, `create_npc_batch`'s
  `total += count` and `_commit_npc_batch`'s count guard are untouched; a
  review batch's `npcs_total` is its line count.

## Decision rights

STOP:
- An anchor does not hold.
- `npc_batch_count_contract.py`, `npc_batch_purge.py`,
  `purge_fk_ordering.py` or `npc_agent_strata.py` turns red on a rule this
  brief cannot satisfy by Scope IN 5.
- The NPC agent's panel needs a change to keep working.

ADAPT:
- `resolve_vocabulary` returns the review place outside
  `expanded_location_ids` (it is a zone): `prepare_group_lot` raises
  `ValueError("Ce lieu de départ ne peut pas être choisi.")`; report.
- The stubbed draft lacks a key `run_next_npc` reads: add it to the stub,
  report.

REPORT-ONLY:
- Review batches left open by a world switch (the review is keyed by the
  active world).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/creator_review.py`
      PASS (CR1-CR5); `npc_agent_strata.py`, `npc_batch_count_contract.py`,
      `npc_batch_purge.py`, `purge_fk_ordering.py`, `module_budget.py`
      PASS.
- [ ] Named mutations, each red then reverted: drop the filter in
      `list_npc_batches` -> CR5; drop the name override in `run_next_npc`
      -> CR5; drop the commit guard -> CR5; remove `pc_approval.py` from
      `ALLOWED_REFERENCE_FILES` -> `npc_agent_strata.py`.
- [ ] `corpus_gate.py`: every check PASS except `pipeline_state.py`, red
      only on the arrows to `draft_approval.py` and `creator_review_ui.py`.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- The docstrings of Scope IN 1 and 3. No schema change.
