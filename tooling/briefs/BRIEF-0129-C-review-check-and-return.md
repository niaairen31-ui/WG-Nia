<!-- slug: review-check-and-return -->
# BRIEF 0129-C — "The review check, the review routes and the return"

Lot: LOT-0129-creator-review.md (authoritative on conflict)
Depends on: B (the review columns, C-03, C-04)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/creation_check.py` is 257 lines; `DRAFT_VIOLATION_CODES`
  at :37-41; `def check_draft` at :203.
- `src/world_engine/writes/pc_drafts.py`: `def _require_open` at :54,
  `if draft.status != "draft":` at :55; `DRAFT_LOCKED_MESSAGE` at :35.
- `src/world_engine/cockpit/routes/player_creation.py:127-129` is
  `_writable`, testing `draft.status != "draft"`.
- `src/world_engine/cockpit/app.py:76` imports `pc_drafts as
  _routes_pc_drafts`, `:155` includes its router.
- `src/world_engine/models/pc_drafts.py` declares C-03's sketch columns and
  `PC_REVIEW_ACTIONS` (B landed).
- `src/world_engine/relation_orientation.py:36` declares
  `RETIRED_RELATION_TYPES`, `:39` `def is_social`;
  `src/world_engine/cockpit/crud/_shared.py:144` `RELATION_TYPES = (`.

Halt if any anchor has moved.

## Facts carried

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
### R-03 -- the draft writer
Opened: `src/world_engine/writes/pc_drafts.py:1-325` (325 lines).
Finding: the docstring names it « the one writer of a player's character
draft », never committing, never writing canon. `_require_open(draft)`
(:54-56) raises `DraftLocked(DRAFT_LOCKED_MESSAGE)` when `draft.status !=
"draft"`; `DRAFT_LOCKED_MESSAGE = "Ce personnage est soumis : il ne peut
plus être modifié."` (:35). `open_draft` (:84-101) refuses `PcExists` when
the user holds a player character in the world, else returns the user's
not-approved draft or a new one. `save_player_draft` (:229-248) calls
`_require_open`, then `_save_skills`, `_save_sketches` (keeps a stored
sketch row by `id`, deletes the stored rows the screen did not list),
`_save_memberships` (keeps rows by `faction_id`, deletes the others),
`_save_knowledge`. `apply_design` (:251-309) calls `_require_open` and
deletes every `designer`-origin sketch, membership and knowledge row before
laying the new ones. `submit_draft(db, draft, violations)` (:314-325)
calls `_require_open`, refuses a non-empty `violations`, sets `status =
"submitted"`, `submitted_at` and `updated_at`, adds and flushes.
Consequence: B1 widens `_require_open` to `draft` and `returned` (C);
a sketch row kept by `id` keeps its review columns across a player save,
a deleted one loses them (a drafting decision, flagged); the review
writer functions join this module (C-06), never a second writer.
### R-04 -- the player's creation routes
Opened: `src/world_engine/cockpit/routes/player_creation.py:1-326`.
Finding: `_writable(draft)` (:127-129) raises 409 `DRAFT_LOCKED_MESSAGE`
when `draft.status != "draft"`; `ask_designer` (:254-311) and
`submit_player_draft` (:314-326) call it; `save_draft` (:204-224) relies on
`save_player_draft`'s `DraftLocked`. `get_draft` (:182-188) answers
`{"draft": None, "verdict": None}` when `open_draft_of` finds nothing, else
`_draft_body` = `{"draft": draft_view(..., view=public_view(...)),
"verdict": ...}`. Every path starts with `/api/joueur/creation/`.
Consequence: C changes `_writable` with `_require_open` (one rule, two
places, both named in Scope IN); G adds `character_name` to `get_draft`'s
`None` branch (C-16).
### R-05 -- the one check
Opened: `src/world_engine/creation_check.py:1-257` (257 lines).
Finding: `VIOLATION_CODES` (:33-36), `DRAFT_VIOLATION_CODES` (:37-41:
`name_missing, story_missing, start_place_missing, start_place_invalid,
too_many_sketches, master_without_sketch, sketch_existing_invalid,
membership_invalid, pc_exists`). `Violation(code, skill_key, message)`
(:44-48). `check_creation(db, world_id, choices, *, enforce_visibility)`
(:113-177). `verdict_dict(verdict, violations)` (:180-190).
`_public_of_type` (:193-200). `check_draft(db, draft)` (:203-257): the
start place must be a public active location of the world and not a zone
(:215-219); the sheet is `check_creation` over `player_rank` only, with
visibility (:221-224); the master rule counts `kind == "master"` sketches by
`skill_key` (:232-239); an `existing_entity_id` must be a public character
(:240-244); memberships must name a public faction (:246-249); `pc_exists`
when the draft's user holds a player character in the world (:251-256).
The module imports `public_view` (:29) and `zone_ids` (:31).
Consequence: `check_review` (C-05) is a sibling in this module, with its
own code tuple (R-24 forbids extending `DRAFT_VIOLATION_CODES`); it reads
only (R-23's CB5 tokens).
### R-06 -- the draft's read shape
Opened: `src/world_engine/pc_draft_reads.py:1-82`.
Finding: `draft_view(db, draft, *, view)` (:34-75) returns `id, world_id,
status, name, story, start_location, start_location_set_by, creator_note,
submitted_at, skills, sketches, memberships, knowledge`; with a `view` an
entity outside it is answered with `name: None`; the player's routes pass
`public_view`, the creator's `None`. `open_draft_of(db, *, world_id,
user_id)` (:78-82) returns the not-approved draft. Both callers share
`draft_view`.
Consequence: the review columns are read by a separate module
(`pc_review_reads.py`, C-07) so the shared player shape cannot carry them
(C1 (0126): the player never sees the creator's edits). `creator_note` is
already in the player's shape.
### R-07 -- the creator's read routes and their check
Opened: `src/world_engine/cockpit/routes/pc_drafts.py:1-63`;
`tooling/verify/checks/submitted_drafts.py:1-40, 100-125`.
Finding: `GET /api/pc-drafts` lists the active world's `submitted` drafts
(`_world_id(db)` from `..crud._shared`); `GET /api/pc-drafts/{id}` 404s
`Brouillon introuvable.` unless the draft is `submitted` in the active
world, and answers exactly `{"draft", "player_name", "verdict",
"skill_names", "ranks"}`. SD2 asserts `set(body) == DETAIL_KEYS` (:35,
:122); SD3 forbids `db.add(`, `.commit(`, `.flush(`, `@router.post`,
`@router.put`, `@router.delete` in `routes/pc_drafts.py`.
Consequence: every review route lives in a new module
`cockpit/routes/pc_review.py` (C-08); the detail route keeps its keys.
### R-09 -- skills: rows, ranks, masters
Opened: `src/world_engine/writes/characters.py:68-146`;
`src/world_engine/skill_ranks.py:35-38`; `src/world_engine/skill_access.py:113-124`;
`src/world_engine/creation_rules.py:121-148`;
`src/world_engine/models/canon_skill.py` (`Skill`, :132-170);
`src/world_engine/cockpit/crud/skills.py:275-305`.
Finding: `RANKS = (0, 1, 2, 3, 4, 5)`, `MAX_RANK = 5`, `DEFAULT_RANK = 1`.
`Skill.rank` defaults to 1 with CHECK `rank BETWEEN 0 AND 5`.
`write_skill_row(db, *, character_id, rank, domain=None,
skill_definition_id=None, taught_by_id=None)` adds the row itself
(`db.add(row)`, :145) and raises `ValueError` on a rank outside `RANKS`,
both or neither of domain and definition, an unknown definition, a base
domain outside `BASE_SKILL_DOMAINS`, or a row the character already holds.
`write_skill_rank(db, *, skill_id, rank, changed_by="creator")` appends the
previous rank to `change_history`, sets `rank`, restarts `xp`; the caller
adds the row. `skill_masters(db, world_id, *, definition_id, domain)` lists
the world's characters holding `rank == MAX_RANK` in that skill. The route
`grant_skill` checks `taught_by_id` against `skill_masters` before
`write_skill_row`. `start_sheet` gives base domains `start_rank =
DEFAULT_RANK`, `requires_master = False`, and definitions `start_rank = 0
if requires_master else DEFAULT_RANK`.
Consequence: at approval a master's Maître row is `write_skill_row(rank=5)`
or, when the NPC already holds that skill, `write_skill_rank(rank=5)`; the
character's taught rows are `write_skill_row(..., taught_by_id=...)` after
the masters exist in the session; a skill key is a base domain when it is
in `BASE_SKILL_DOMAINS`, else a definition id.
### R-16 -- relations
Opened: `src/world_engine/writes/relations.py:215-233, 296-331, 332-405` (`_on_relation_born` :223);
`src/world_engine/relation_orientation.py:24, 36, 39-48`;
`src/world_engine/cockpit/crud/_shared.py:140-155`.
Finding: `write_relation(db, *, mode, relation_id=None, world_id,
entity_a_id, entity_b_id, type, value=0, direction="a_to_b",
visible_to_b=True, notes=None, mutation_id=None, changed_by=None)`;
`mode="set"` with no `relation_id` creates an edge of intensity
`_clamp(value)` (1-100); a social type with a direction other than `a_to_b`
raises `ValueError`; a retired type (`RETIRED_RELATION_TYPES = ("debt",)`)
raises; the writer adds the row, flushes and runs `_on_relation_born`,
which births the typed fact and, for a social type, `record_encounter(...,
source="relation", source_ref=rel.id)`. `is_social(t)` is `t not in
RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to", "borde", "controls")`.
The fiche's datalist `RELATION_TYPES` (`crud/_shared.py:144-148`) is
`ally, enemy, fear, fascination, shared_secret, instrumentalizes, interest,
indifference, rejection, passive_attention, other, connects_to, controls`.
Consequence: K1's relation is `write_relation(mode="set", entity_a=NPC,
entity_b=character, direction="a_to_b")`, which also records the
encounter; the review offers `[t for t in RELATION_TYPES if is_social(t)]`
and `check_review` accepts a non-empty social, non-retired type (no third
copy of the list).
### R-20 -- the character and the profile
Opened: `src/world_engine/models/canon.py:149-175`;
`src/world_engine/models/pipeline.py:711-726`.
Finding: `Character` declares `idx_character_one_pc_per_user_world
(world_id, user_id) UNIQUE WHERE character_type = 'player'` (:158-161),
`character_type: str` (:169), `user_id: Optional[str]` with no FK (:170).
`User`: `id, name, email, role (server default 'player'), created_at,
is_active`; the creator is the user with `role == "creator"`
(`routes/creator.py:826`).
Consequence: K1-b (G) sets `Character.user_id` to a player profile's id or
to the creator's; a collision is the unique index's `IntegrityError`.
### R-24 -- the player's creation check
Opened: `tooling/verify/checks/player_creation.py:1-90, 280-340`.
Finding: PC3 requires every code of `DRAFT_VIOLATION_CODES` to be reached
with its message in `MESSAGES` (:74-84, :338-339). PC5: after a clean
submit, `PUT`, designer and submit answer 409 `DRAFT_LOCKED_MESSAGE`. PC7
forbids `chat(`, `World.is_active`, `_world_id(`, `lore_selectors`,
`CREATOR` in `routes/player_creation.py`, `writes/pc_drafts.py`,
`pc_draft_reads.py`, and requires every route path to start with
`/api/joueur/creation/`.
Consequence: review codes live in a new `REVIEW_VIOLATION_CODES`;
`writes/pc_drafts.py` takes no `_world_id(` (the review writer receives the
draft); a submitted draft stays locked (PC5 holds); the player's route
module gains no non-`/api/joueur/creation/` path.
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
### R-30 -- router registration
Opened: `src/world_engine/cockpit/app.py:70-90, 150-165`.
Finding: `from .routes import player_creation as _routes_player_creation`
(:75), `from .routes import pc_drafts as _routes_pc_drafts` (:76);
`app.include_router(_routes_player_creation.router)` (:154),
`app.include_router(_routes_pc_drafts.router)` (:155).
Consequence: C adds `from .routes import pc_review as _routes_pc_review`
after :76 and `app.include_router(_routes_pc_review.router)` after :155.
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
### R-32 -- G2's reason
Opened: `src/world_engine/cockpit/crud/entities.py:209-229`.
Finding: `_player_character_id(db, world_id)` answers 409 « Plusieurs
personnages joueurs dans ce monde : précisez lequel. » when the world holds
more than one `character_type == "player"` character.
Consequence: `check_review` refuses while the world holds any player
character (`world_has_pc`, G2 (0126)).
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
### C-06 -- the draft writer's review functions
Produced by: C (E adds `mark_approved`)   Consumed by: C's routes, E, G
In `writes/pc_drafts.py`:
```
OPEN_STATUSES: tuple[str, ...] = ("draft", "returned")
REVIEW_LOCKED_MESSAGE = "Ce personnage n'est pas soumis : il ne peut pas être revu."
RETURN_NOTE_MISSING = "Écris une note pour le joueur."
def _require_open(draft) -> None        # status not in OPEN_STATUSES -> DraftLocked(DRAFT_LOCKED_MESSAGE)
def _require_submitted(draft) -> None   # status != "submitted" -> DraftLocked(REVIEW_LOCKED_MESSAGE)
def save_review(db, draft, *, review_location_id: Optional[str],
                sketches: list[dict], memberships: list[dict]) -> None
def return_draft(db, draft, *, note: str) -> None
def mark_approved(db, draft, *, character_id: str) -> None     # E
```
`save_review`: `_require_submitted`; `review_location_id` None or an
existing entity id (`ValueError("Entité inconnue.")`); each sketch item
`{"id", "action", "entity_id", "relation_type", "intensity"}` names a
sketch of this draft (`ValueError("Personne inconnue.")`), `action` is
None or in `PC_REVIEW_ACTIONS` (`ValueError("Choix inconnu.")`),
`entity_id` is kept only for `attach` (an existing entity, else
`ValueError("Entité inconnue.")`; None for every other action), an empty
`relation_type` becomes `PC_REVIEW_DEFAULT_RELATION`, `intensity` is an int
in 1..100 (`ValueError("L'intensité va de 1 à 100.")`); each membership
item `{"id", "dropped"}` names a membership of this draft
(`ValueError("Appartenance inconnue.")`). An unlisted row keeps its
values. Sets `updated_at`, flushes. `return_draft`: `_require_submitted`;
a stripped empty note -> `ValueError(RETURN_NOTE_MISSING)`; `status =
"returned"`, `creator_note = note` (stripped), `updated_at`; flushes. The
review columns are left as they are. `mark_approved`:
`_require_submitted`; `status = "approved"`, `character_id`, `updated_at`;
flushes. `submit_draft`, `save_player_draft`, `apply_design` keep their
code and reach a `returned` draft through the widened `_require_open`.
### C-07 -- the review's read shape
Produced by: C   Consumed by: C's routes, F
Module `src/world_engine/pc_review_reads.py` (reads only):
```
def review_view(db, draft) -> dict
def review_choices(db, draft) -> dict
```
`review_view` returns `{"review_location": {"entity_id", "name"} | None,
"place": {"entity_id", "name"} | None, "character_id": str | None,
"sketches": [{"id", "action", "entity": {"entity_id", "name"} | None,
"relation_type", "intensity"}], "memberships": [{"id", "dropped"}]}`;
`place` is `review_place_id(draft)`'s entity; sketches by `(position, id)`.
`review_choices` returns `{"places": [{"entity_id", "name"}], "characters":
[{"entity_id", "name"}], "masters": {skill_key: [{"id", "name"}]}}`:
`places` the world's active `location` entities not in `zone_ids`, by
name; `characters` the world's active `character` entities whose
`character_type` is not `player`, by name; `masters` one key per master
sketch's `skill_key`, the `skill_masters` list.
`pc_draft_reads.py` is not edited and never names a review column.
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

## Context

The creator now reviews a submitted draft. This brief gives her the check
of her final version (`check_review`, INV-67's sibling), the writer of her
choices, the read of her choices and her pick lists, the review routes,
and the return to the player with a note (B1: the player gets his own
version back and may edit it). The batches per group (D), the approval
(E) and the screens (F, G) follow.

## Scope IN

1. `creation_check.py`: C-05's tuple, `review_place_id` and
   `check_review`, after `check_draft`, with their imports
   (`RETIRED_RELATION_TYPES, is_social` from `.relation_orientation`,
   `skill_masters` from `.skill_access`, `BASE_SKILL_DOMAINS` from
   `.models`). The module docstring gains a paragraph: « `check_review`
   judges the creator's final version (TICKET-0129, BRIEF-0129-C): the
   player's sheet and story, the creator's place, people, masters,
   relations and memberships, with all the lore -- never through the
   public view. » It writes nothing (CB5).
2. `writes/pc_drafts.py`: C-06 except `mark_approved` (E): the constants,
   the widened `_require_open`, `_require_submitted`, `save_review`,
   `return_draft`. Import `Entity` and C-04's constants from `..models`.
   Docstring: the « Only `draft` status is writable » sentence becomes
   « A `draft` or `returned` draft is writable by its player
   (`DraftLocked` otherwise); a `submitted` one by the creator's review
   functions only. », and the list of functions gains `save_review` and
   `return_draft`.
3. `routes/player_creation.py`: `_writable` refuses when `draft.status not
   in OPEN_STATUSES` (imported from `...writes.pc_drafts`), message
   unchanged.
4. New `src/world_engine/pc_review_reads.py` per C-07 (docstring first
   sentence « The creator's review of a character draft, as the screens
   read it (TICKET-0129, BRIEF-0129-C). Reads only. »), importing
   `review_place_id` from `.creation_check`, `skill_masters` from
   `.skill_access`, `zone_ids` from `.zone_rules`.
5. New `src/world_engine/cockpit/routes/pc_review.py` with C-08's GET,
   PUT and `renvoyer` routes (docstring first sentence « The creator's
   review of a submitted character draft (TICKET-0129): her choices, the
   check of her final version, the return to the player, the approval.
   Keyed by the active world, as every Création surface. »). Bodies:
   `PcReviewSketchItem {id: str, action: Optional[str] = None, entity_id:
   Optional[str] = None, relation_type: str = "", intensity: int = 60}`,
   `PcReviewMembershipItem {id: str, dropped: bool = False}`,
   `PcReviewBody {review_location_id: Optional[str] = None, sketches:
   list[PcReviewSketchItem] = [], memberships: list[PcReviewMembershipItem]
   = []}`, `PcReturnBody {note: str = ""}`. A private `_submitted(draft_id,
   db)` returns the draft or raises 404 `Brouillon introuvable.`;
   `_review_body(db, draft)` builds C-08's GET shape (`groups` with `lot:
   None`, `blockers: []`). `player_name` as `routes/pc_drafts.py:29-31`
   computes it.
6. `cockpit/app.py`: import and include the router after the `pc_drafts`
   lines (R-30).
7. New check `tooling/verify/checks/creator_review.py`, first sentence « G1
   check for TICKET-0129 -- the creator reviews a submitted character: the
   one check of her final version, her choices beside the player's
   version, the return with a note. », fresh database per R-34. Fixture:
   an active world open to players; locations `Port` (public), `Cave` (not
   public), zone `Région` with child `Quai`; a system with `Nécromancie`
   (`requires_master`, visible) and `Lame` (open); characters `Vieux` (NPC,
   Nécromancie at rank 5), `Garde` (NPC, no rank 5), `Ombre` (NPC, not
   public); factions `Guild` (active) and `Ancienne` (status not
   `active`); profiles Ana and Bea (`create_player_profile`). Canon fixture
   rows may be inserted directly through the models on this fresh
   database; drafts are written through `writes/pc_drafts.py`.
   - **CR1** `check_review`: one clean submitted draft (name, story, Port,
     Nécromancie 1, a `master` sketch for it attached to Vieux, a `family`
     sketch to create, a membership in Guild) answers `()`. Then each of
     these states, alone on a copy of that draft, gives exactly the listed
     codes with C-05's messages: empty name -> `name_missing`; empty story
     -> `story_missing`; no place on either column -> `start_place_missing`;
     review place `Région` -> `review_place_invalid`; Lame 5 over the pool
     -> the `check_creation` codes it yields (asserted equal to
     `check_creation`'s own list); nine sketches written directly ->
     `too_many_sketches`; the master sketch `drop` -> `master_without_sketch`;
     the family sketch undecided -> `sketch_undecided`; the family sketch
     attached to an unknown id -> `attach_invalid`; two sketches attached
     to Garde -> `attach_duplicate` on the second; the master attached to
     Garde -> `master_not_master`; relation type `connects_to` ->
     `relation_type_invalid`; the membership on `Ancienne` ->
     `membership_invalid`; Bea holding a player character in the world ->
     `world_has_pc` alone; Ana holding one -> `[pc_exists, world_has_pc]`.
     Also: review place `Cave` (not public) and the master attached to
     `Ombre` once Ombre is made a Maître -> no violation (the review reads
     all the lore). Every code of `REVIEW_VIOLATION_CODES` is reached.
   - **CR2** routes: `GET /api/pc-reviews/{id}` answers exactly C-08's
     keys; `choices.relation_types` equals the social subset of
     `RELATION_TYPES`; `choices.places` holds Port, Cave, Quai and not
     Région; `choices.characters` holds Vieux, Garde, Ombre and no player
     character; `choices.masters` maps Nécromancie to `[Vieux]`; `groups`
     lists the family's group with `lot: None`. `PUT` with a place, every
     sketch's action and a dropped membership -> 200, the GET shape shows
     them, `verdict.violations` empty; an unknown sketch id, action `x`,
     intensity 0 -> 422 with C-06's messages and nothing changed; a
     `draft`-status draft -> 404; a draft of a non-active world -> 404.
   - **CR3** return: `POST renvoyer` with an empty note -> 422
     `Écris une note pour le joueur.`; with a note -> 200, status
     `returned`, `creator_note` stripped; `GET /api/pc-drafts` no longer
     lists it; the player's `GET /api/joueur/creation/brouillon` answers
     the draft with `status: "returned"`, the note, and keys equal to
     `draft_view`'s (no review key); the player's `PUT` answers 200 and
     `_writable(draft)` called directly on the `returned` draft raises
     nothing;
     `soumettre` -> `submitted: true`; the review columns of the sketches
     the player kept are unchanged; `PUT /api/pc-reviews/{id}` on a
     `returned` draft -> 404 (not submitted).
   - **CR4** static (code tokens): `pc_draft_reads.py` and
     `routes/player_creation.py` contain no `review_`; every path of
     `routes/pc_review.py` starts with `/api/pc-reviews/` or
     `/api/pc-profiles`; `routes/pc_review.py` and `pc_review_reads.py`
     contain no `chat(` and no `public_view(`; the body of `check_review`
     (by `ast`) calls no `public_view`;
     `app.py` holds `app.include_router(_routes_pc_review.router)`.
   A case not reached is a FAILURE.
8. Commits: (1) items 1-2 and CR1; (2) items 3-6 and CR2-CR4.

## Scope OUT

- The batches per group and the `lot` / `blockers` values (D); the
  approval route and `mark_approved` (E); K1-b (G); every screen (F, G).
- Editing `pc_draft_reads.py` or `routes/pc_drafts.py` (R-06, R-07).
- Showing the creator's choices to the player (C1 (0126)).
- Ranks at review (A1: after the approval).

## Invariants to defend

- INV-67: `check_review` is a sibling in `creation_check.py`; it calls
  `check_creation` for the sheet and computes no cost of its own.
- INV-66: nothing of the review reaches a player surface: the player's
  reads stay `draft_view` with the public view; CR3 and CR4 hold it.
- INV-20: the creator's choices are columns.
- INV-18: the writer never commits; each route commits once.

## Decision rights

STOP:
- An anchor does not hold.
- `player_creation.py`, `submitted_drafts.py`, `creation_budget.py` or
  `creation_designer.py` turns red.
- Importing `skill_access` or `relation_orientation` into
  `creation_check.py` creates an import cycle.

ADAPT:
- A C-05 message reads awkwardly in a fixture case: keep C-05's text,
  report.
- `_review_body` needs a helper of `routes/pc_drafts.py` (`_player_name`):
  re-implement those three lines in `pc_review.py` rather than import a
  private name across routes, report.

REPORT-ONLY:
- A sketch whose `existing_entity_id` (the player's suggestion) differs
  from the creator's `review_entity_id`: both are kept; the panel (F)
  shows the suggestion.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/creator_review.py`
      PASS (CR1-CR4); `player_creation.py`, `submitted_drafts.py`,
      `creation_budget.py`, `creation_designer.py`, `module_budget.py`,
      `review_schema.py` PASS.
- [ ] Named mutations, each red then reverted: `check_review` reads the
      place through `check_draft`'s public test -> CR1 (Cave); `_writable`
      back to `!= "draft"` -> CR3; `review_view` merged into `draft_view`
      -> CR3 keys and CR4.
- [ ] `corpus_gate.py`: every check PASS except `pipeline_state.py`, red
      only on the arrows to `draft_approval.py` and `creator_review_ui.py`.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- The docstrings of Scope IN 1-2. No schema change. INV-68 arrives with E.
