<!-- slug: approval -->
# BRIEF 0129-E — "The approval: one transaction to canon"

Lot: LOT-0129-creator-review.md (authoritative on conflict)
Depends on: A (C-01, C-02), B (C-03, C-04), C (C-05, C-06, C-08), D (C-09, C-10)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/writes/player_characters.py` defines
  `write_player_character(db, *, world_id, user_id, name,
  current_location_id, facets, knowledge)` (A landed).
- `src/world_engine/cockpit/npc_group_commit.py` defines
  `_commit_npc_row(row, batch, db) -> dict` (A landed).
- `src/world_engine/cockpit/pc_approval.py` defines `review_groups`,
  `open_review_lots`, `prepare_group_lot`, `abandon_review_lots`,
  `review_blockers` (D landed).
- `src/world_engine/creation_check.py` defines `check_review`,
  `review_place_id` (C landed).
- `src/world_engine/perspective_selectors.py`: `def _public_members` at
  :119, its select ending at :130.
- `src/world_engine/writes/characters.py`: `def write_skill_rank` at :68,
  `def write_skill_row` at :109.
- `.claude/rules/character-creation.md` holds INV-67 only; INV-67 is the
  highest id of the corpus.

Halt if any anchor has moved.

## Facts carried

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
### R-08 -- the character recipe
Opened: `src/world_engine/cockpit/routes/creator.py:1-64, 786-942`
(968 lines; 35 functions by `ast`).
Finding: imports `BASE_SKILL_DOMAINS, Character, Entity, Skill,
SkillDefinition, User` from `...models` (:33-45) and `KNOWLEDGE_LEVELS,
write_entity_facets, write_knowledge` from `...writes` (:46-53),
`ZoneRefusal, require_visitable` (:54). `PlayerKnowledgeItem` (:787-790:
`level`, `content`), `PlayerCharacterCreateBody` (:793-799).
`_validate_pc_creation` (:802-830) checks the name, the active world, the
location (an active-world `location`, visitable) and returns the
`role == "creator"` user. `_pc_custom_skill_defs(world_id, db)` (:833-841)
selects the world's definitions with `requires_master == False`.
`_write_pc_knowledge(entity_id, knowledge_items, db)` (:844-861) writes
each item's `level` (else `rumor`) and `content` through `write_knowledge`
(`source="pc_creation"`, `is_secret=False`, `share_threshold=50`).
`create_player_character` (:864-941): inside `try`, adds `Entity(world_id,
type="character", name)`, flushes, adds `Character(id, world_id,
character_type="player", user_id=creator_user.id, current_location_id)`,
flushes, `write_entity_facets(db, entity_id, facets=body.facets or {},
created_by="creator_crud")`, one `Skill(character_id, domain)` per
`BASE_SKILL_DOMAINS`, one `Skill(character_id, domain=definition.base_domain,
skill_definition_id)` per `_pc_custom_skill_defs`, `_write_pc_knowledge`,
then `db.commit()`; `IntegrityError` -> rollback and `{"ok": False, "error":
"A player character already exists for this user in this world."}`; any
other exception -> rollback and `{"ok": False, "error": str(exc)}`;
success -> `{"ok": True, "id", "name"}`. The only frontend caller is
`frontend/src/creation/PjCreatePanel.svelte` (grep
`/api/characters/player"`).
Consequence: A extracts the body between `try:` and `db.commit()` into
`writes/player_characters.py::write_player_character` (C-01) with
`_pc_custom_skill_defs` and `_write_pc_knowledge`; the route keeps its body
class, its validation, its transaction and its answers. E adds the ranks
and the teachers to the writer (C-12). `routes/creator.py` sheds three
functions.
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
### R-15 -- the canon-write policy
Opened: `tooling/verify/canon_write_policy.txt:1-147`;
`tooling/verify/checks/single_canon_write.py:1-70, 337-366, 557-580`.
Finding: `[CANON_TABLES]` holds `entity character ... faction_membership
relation knowledge ... skill ...`; `[ALLOWED_SITES]` lines are
`path::function   tables`, a relocation carrying a `#` comment above it;
`creator.py::create_player_character  entity character skill` (:147). The
check attributes each `.add()`/`.delete()` on a session to a table,
following a variable through the declared return type of the function that
produced it (`build_return_types`, :337), and fails a canon table written
from an unlisted site or an unattributable site. `write_membership`
(`writes/factions.py:61-108`), `write_relation` (`writes/relations.py:402`),
`write_skill_row` (`writes/characters.py:145`) and `write_knowledge` add
their row themselves; `write_skill_rank` leaves the add to its caller.
Consequence: A replaces line 147 by `writes/player_characters.py::
write_player_character  entity character skill` with a relocation
comment; E adds `writes/player_characters.py::write_master_rank  skill`
(`write_skill_rank` leaves the add to its caller); G adds
`writes/player_characters.py::set_player_profile  character`. No other module of the lot calls `db.add` on a row a writer
returned; `write_skill_rank`'s row is added inside the writer module that
calls it (E's master step lives in `writes/player_characters.py`, C-12).
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
### R-18 -- memberships and public members
Opened: `src/world_engine/writes/factions.py:61-108`;
`src/world_engine/perspective_selectors.py:13-58, 106-140` (321 lines);
`tooling/verify/checks/perspective_isolation.py:1-60`.
Finding: `write_membership(db, *, mode, world_id, entity_id, faction_id,
role=None, cover_role=None, is_primary=False, is_secret=False)` with
`mode="open"` adds the row itself; a second active membership in the same
faction violates `idx_membership_unique_active`. `_public_members(
faction_id, world_id, view, db)` (:119-139) selects memberships of the
faction with `left_at IS NULL` and `is_secret == False`, joined to the
member's entity of the world, keeps members in `view.entity_ids`, and
returns names only -- « the same WHERE triplet as
`read_public_memberships` » (W1 of 0125). `public_view` (:41-58).
PI1 forbids `chat(`, `db.add(`, `.commit(`, `include_creator_only`,
`CREATOR`, `NameScope("creator"`, `near_candidates`, `validate_binding`
in `perspective_selectors.py`.
Consequence: E adds `public_member_ids(faction_id, world_id, view, db)` next
to `_public_members` with the same WHERE triplet, returning ids (C-13);
F-b reads it, so « public member » keeps one definition.
### R-19 -- knowledge, facets, INV-07
Opened: `src/world_engine/writes/knowledge.py:65-67, 241-275`;
`src/world_engine/facets.py:57, 85`; `src/world_engine/writes/facets.py:193-205`;
`CLAUDE.md:169-173`.
Finding: `KNOWLEDGE_LEVELS` holds `unaware, rumor, suspicious, partial,
knows, fully_understands`. `write_knowledge(db, *, entity_id, level,
content, source, is_incorrect, is_secret, share_threshold, session_id,
...)` adds its row and its fact. `FACETS["histoire"]` is an `affirmation`
facet (one fact per non-empty line), category `interiorite`.
`write_entity_facets(db, *, entity_id, facets, created_by)`. INV-07 reads:
« PC knowledge is written `is_secret=False`; [...] `False` is applied at
write time by the accept route (`create_player_character` via
`writes.write_knowledge`), never by the generator. [no check] ».
Consequence: the approval passes the draft's knowledge rows to
`_write_pc_knowledge` (they carry `level` and `content`), and the story as
`facets={"histoire": draft.story}`; A re-points INV-07's parenthesis to
`write_player_character`.
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
### R-26 -- the instruction corpus
Opened: `tooling/verify/checks/claude_md_contract.py:1-80`; `CLAUDE.md`
(20 663 bytes) lines 145-151, 169-177, 204-218; `.claude/rules/character-creation.md`
(1 066 bytes, 20 lines); `tooling/standards/ARCHITECTURE_DECISIONS.md` (last 5 lines).
Finding: root budget 22 000 characters, each rule file 4 000, no line over
100 characters; every Invariants bullet starts `- **INV-NN**` and ends with
`-- enforced by` and checks under `tooling/verify/checks/`, or
`[no check]`; ids run INV-01 to the highest without a gap; a rule file
opens with `paths:` globs that each match a file; no `TICKET-\d` or
`BRIEF-\d` inside an Invariants section. `character-creation.md`'s paths
are `creation_rules.py`, `creation_check.py`, `writes/creation_rules.py`,
`writes/pc_drafts.py`, `pc_draft_reads.py`, `routes/player_creation.py`;
its one invariant is INV-67. INV-08 names the two canon-write paths for
rows (`_apply_mutation`, creator CRUD). ARCHITECTURE_DECISIONS ends with a
blank line, `---`, a blank line, `*Co-built with Claude, June 2026.*`.
Consequence: E adds INV-68 to `character-creation.md` with its new paths;
A edits INV-07's parenthesis (R-19); G inserts the decisions entry above
the footer. The approval is a creator-direct write (INV-08's creator path),
like the NPC agent's commit of model-generated rows (R-10).
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

### C-01 -- the character writer
Produced by: A   Consumed by: E (extends it, C-12), the route
`create_player_character`
Module: `src/world_engine/writes/player_characters.py`, docstring first
sentence « The one writer of a new player character (TICKET-0129,
BRIEF-0129-A): the entity, its `character` row, its base-domain and open
skills, its facets and its knowledge, in the caller's transaction. ».
Holds, moved verbatim from `routes/creator.py` at `11cafc0`:
`_pc_custom_skill_defs(world_id, db)` (:833-841) and
`_write_pc_knowledge(entity_id, knowledge_items, db)` (:844-861), and
```
def write_player_character(db: Session, *, world_id: str, user_id: str, name: str,
                           current_location_id: str, facets: Optional[dict],
                           knowledge: Optional[list]) -> Entity:
```
whose body is `create_player_character`'s statements from `entity =
Entity(` to `_write_pc_knowledge(entity.id, body.knowledge, db)` with
`creator_user.id` -> `user_id`, `body.current_location_id` ->
`current_location_id`, `body.facets` -> `facets`, `body.knowledge` ->
`knowledge`, then `return entity`. Adds and flushes; never commits; never
validates the place (its callers do). `knowledge` items carry `.level` and
`.content`. Imports: `Optional`; `Session, select` from sqlmodel;
`BASE_SKILL_DOMAINS, Character, Entity, Skill, SkillDefinition` from
`..models`; `write_entity_facets` from `.facets`; `KNOWLEDGE_LEVELS,
write_knowledge` from `.knowledge`.
The route keeps `PlayerKnowledgeItem`, `PlayerCharacterCreateBody`,
`_validate_pc_creation`, its `try` / `except IntegrityError` / `except
Exception` and its three answers; inside `try` it calls
`write_player_character(db, world_id=world_id, user_id=creator_user.id,
name=name, current_location_id=body.current_location_id,
facets=body.facets, knowledge=body.knowledge)` then `db.commit()`.
### C-02 -- the NPC row commit
Produced by: A   Consumed by: the NPC agent's `_commit_npc_batch`, E
Module: `src/world_engine/cockpit/npc_group_commit.py`, docstring first
sentence « The NPC group agent's row commit (TICKET-0129, BRIEF-0129-A):
one staged row written to canon through the creator-direct cores, in the
caller's transaction; shared by the agent's batch commit and the
character approval. ». Holds, moved verbatim from
`cockpit/routes/npc_agent.py` at `11cafc0`: `_commit_npc_row_goals(db,
world_id, npc_id, goals) -> None` (:178-195) and `_commit_npc_row(row,
batch, db) -> dict` (:198-235), returning `{"row_id", "entity_id",
"name"}`. Imports: `Session` from sqlmodel; `NpcBatch, NpcBatchRow` from
`..models`; `write_npc_goal` from `..writes`; `from . import crud as _crud`.
`npc_agent.py` imports `_commit_npc_row` from `..npc_group_commit` and
drops its `from ...writes import write_npc_goal` line (no other use).
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
### C-11 -- the approval
Produced by: E   Consumed by: C-08's approve route
In `cockpit/pc_approval.py`:
```
APPROVAL_REFUSED = "Ce personnage ne peut pas encore être approuvé."
class ApprovalRefused(ValueError): ...
def approve_draft(db, draft) -> dict    # {"character_id", "name", "npc_ids", "lot_ids"}
```
Never commits. In order:
0. `draft.status == "submitted"` (`DraftLocked` otherwise); `check_review`
   and `review_blockers` both empty (`ApprovalRefused(APPROVAL_REFUSED)`
   otherwise).
1. For each `open_review_lots` batch: each row with `kind == "draft"` and
   `row_status in ("proposed", "edited")`, by `created_at`: its sketch is
   `db.get(PcDraftSketch, row.pc_draft_sketch_id)`; when that sketch is
   missing, of another draft, or not `create`, the row becomes `rejected`;
   else `_commit_npc_row(row, batch, db)` (C-02), the sketch maps to the
   new entity, the row becomes `committed`. Each batch then becomes
   `committed` with `closed_at`.
2. Each `create` sketch of kind `master`, by `(position, id)`:
   `write_master_rank(db, character_id=<its NPC>, skill_key=sketch.skill_key)`
   (C-12).
3. `teachers`: for each skill key of the draft with `player_rank >= 1`
   whose `start_sheet` line `requires_master`, the first non-`drop` master
   sketch of that key by `(position, id)` -> its `review_entity_id`
   (`attach`) or its new NPC (`create`). `ranks` = `{skill_key:
   player_rank}` for the draft's rows with a `player_rank`.
   `write_player_character(db, world_id, user_id=draft.user_id,
   name=draft.name.strip(), current_location_id=review_place_id(draft),
   facets={"histoire": draft.story}, knowledge=<the draft's knowledge rows
   by (position, id)>, ranks=ranks, teachers=teachers)` (C-12).
4. `view = public_view(db, world_id)` taken before step 1; each membership
   not `review_dropped`: `write_membership(db, mode="open", world_id,
   entity_id=pc.id, faction_id, role=membership.role)`, then for each id of
   `public_member_ids(faction_id, world_id, view, db)` (C-13):
   `record_encounter(db, world_id, a_id=pc.id, b_id=member_id,
   source="pc_creation", source_ref=draft.id)`.
5. Each `create` or `attach` sketch by `(position, id)`: `write_relation(db,
   mode="set", world_id, entity_a_id=<its NPC or review_entity_id>,
   entity_b_id=pc.id, type=review_relation_type.strip(),
   value=review_intensity, direction="a_to_b", notes=role or None,
   changed_by="creator_crud")`.
6. `mark_approved(db, draft, character_id=pc.id)` (C-06).
No `db.add`, no `db.commit` in this module: every canon row goes through
a writer named here.
### C-12 -- the character writer, extended
Produced by: E   Consumed by: C-11
`write_player_character` gains `ranks: Optional[Mapping[str, int]] =
None, teachers: Optional[Mapping[str, str]] = None`. Each base-domain
`Skill` is created with `rank=(ranks or {}).get(domain, DEFAULT_RANK)`;
each open definition's with `rank=(ranks or {}).get(definition.id,
DEFAULT_RANK)`; then, for each definition of the world with
`requires_master` and `(ranks or {}).get(definition.id, 0) >= 1`:
`write_skill_row(db, character_id=entity.id, rank=...,
skill_definition_id=definition.id, taught_by_id=(teachers or
{})[definition.id])` -- a missing teacher raises `ValueError(f"« {name} »
: il manque le maître de « {definition.name} ».")` before any row of that
skill. A `ranks` key that is not a base domain nor a definition of the
world raises `ValueError` before any write. `ranks=None` and
`teachers=None` behave exactly as C-01.
Same module:
```
def write_master_rank(db: Session, *, character_id: str, skill_key: str) -> Skill
```
The character's row for that skill (a base domain when `skill_key` is in
`BASE_SKILL_DOMAINS`, else a definition id) set to `MAX_RANK` by
`write_skill_rank(..., changed_by="creator")` and added, or created by
`write_skill_row(..., rank=MAX_RANK)` when absent.
### C-13 -- the public members of a faction, by id
Produced by: E   Consumed by: C-11
In `perspective_selectors.py`, right after `_public_members`:
```
def public_member_ids(faction_id: str, world_id: str, view: PublicView, db: Session) -> tuple[str, ...]
```
The same select and WHERE as `_public_members` (the member entity of the
world, the faction, `left_at IS NULL`, `is_secret == False`), members in
`view.entity_ids`, ordered by `(name, id)`, their ids.

## Context

E1: once the creator has reviewed the draft and every group's batch, one
transaction writes everything -- the NPCs of the batches (masters
included, F1), the masters' Maître rank, the character at the player's
ranks with each taught skill naming its master, his memberships and the
encounters with the factions' public members (F-b), his knowledge, the
relation every person of his story has for him (G1, K1), and the draft
closed with its character (C1). If any step fails, nothing is written.
G2 refuses the approval in a world that already holds a player character.

## Scope IN

1. `writes/player_characters.py`: C-12 -- `ranks` and `teachers` on
   `write_player_character` (the taught rows after the open ones), and
   `write_master_rank`. Imports `Mapping`, `DEFAULT_RANK, MAX_RANK` from
   `..skill_ranks`, `write_skill_rank, write_skill_row` from `.characters`.
   The docstring gains « `ranks` and `teachers` (TICKET-0129, BRIEF-0129-E):
   the approval writes the player's ranks, and each skill that requires a
   master with its teacher; the route passes neither. »
2. `canon_write_policy.txt`: after the `write_player_character` line,
   `src/world_engine/writes/player_characters.py::write_master_rank skill`
   with the comment `# TICKET-0129, BRIEF-0129-E: write_master_rank sets a
   master's skill to Maître at a character's approval -- write_skill_rank's
   row added here, or write_skill_row's.`
3. `perspective_selectors.py`: C-13's `public_member_ids` right after
   `_public_members`, with the comment « Same WHERE triplet as
   `_public_members` (INV-03): ids for the approval's encounters
   (TICKET-0129, F-b); never rendered into a prompt. »
4. `writes/pc_drafts.py`: C-06's `mark_approved`.
5. `cockpit/pc_approval.py`: C-11's `APPROVAL_REFUSED`, `ApprovalRefused`,
   `approve_draft`. Imports `_commit_npc_row` from `.npc_group_commit`,
   `write_player_character, write_master_rank` from
   `..writes.player_characters`, `write_membership`, `write_relation` from
   `..writes`, `record_encounter` from `..encounters`, `public_view,
   public_member_ids` from `..perspective_selectors`, `check_review` from
   `..creation_check`, `mark_approved` from `..writes.pc_drafts`,
   `start_sheet` from `..creation_rules`, `PcDraftKnowledge,
   PcDraftMembership, PcDraftSkill` from `..models`. The module holds no
   `db.add(` and no `.commit(`; batch and row status changes are attribute
   assignments on rows already in the session (they are ephemeral tables,
   R-12).
6. `routes/pc_review.py`: C-08's `POST /api/pc-reviews/{draft_id}/approuver`
   -- `_submitted` (404), then `approve_draft` inside `try`; on
   `ApprovalRefused` or `DraftLocked` rollback and 409 `APPROVAL_REFUSED`;
   on `ValueError` or `IntegrityError` rollback and 409 `str(exc)`;
   success: one `db.commit()`, then one `journal_append(lot_id, {"event":
   "commit_by_approval", "pc_draft_id": draft.id, "character_id": ...})`
   per lot, answer `{"ok": True, "character_id", "name"}`.
7. `.claude/rules/character-creation.md`: `paths:` gains
   `"src/world_engine/pc_review_reads.py"`,
   `"src/world_engine/cockpit/routes/pc_review.py"`,
   `"src/world_engine/cockpit/pc_approval.py"`,
   `"src/world_engine/writes/player_characters.py"`; a short prose line
   before `## Invariants`: « The creator reviews a submitted draft beside
   the player's version, prepares one NPC batch per group of people to
   create, returns the draft with a note or approves it in one
   transaction. »; under `## Invariants`, verbatim (each line under 100
   characters):
   ```
   - **INV-68** A drafted character reaches canon only through
     `pc_approval.approve_draft`: one transaction, refused unless
     `check_review` and `review_blockers` find nothing; the review never
     edits the player's version (`pc_draft_reads.py` names no review
     column), and a review batch is written only by the approval.
     -- enforced by `draft_approval.py`, `creator_review.py`
   ```
8. New check `tooling/verify/checks/draft_approval.py`, first sentence « G1
   check for TICKET-0129 (BRIEF-0129-E) -- the approval writes a drafted
   character to canon in one transaction, or nothing. », fresh database
   per R-34, the batch generator stubbed as in `creator_review.py` CR5.
   Fixture: an active world; `Port`, `Quai` (visitable); `Nécromancie`
   (`requires_master`) and `Lame` (open) in a system; NPCs `Vieux`
   (Nécromancie 5, public) and `Ami`; faction `Guild` (public) with
   members `Membre` (public, open membership), `Espion` (public, secret
   membership), `Cache` (not public, open membership); profile Ana; one
   submitted draft: name `Kael`, a story of two lines, place `Port`,
   reviewed to `Quai`; ranks Lame 2, perception 2, Nécromancie 1; sketches
   -- `Mère` (family, group `Famille`, create, `ally` 70), `Maître Sol`
   (master of Nécromancie, group `Famille`, create, `fascination` 80),
   `Ami` (other, attach to `Ami`, `interest` 55), `Rival` (other, drop);
   a membership in `Guild` (role `apprenti`) and one dropped in a second
   faction; two knowledge lines (`rumor`, `knows`). Batch `Famille`
   prepared and generated (two rows).
   - **DA1** success: `POST /api/pc-reviews/{id}/approuver` -> 200 with
     `character_id` and `name == "Kael"`. Then: one `character` row,
     `character_type` `player`, `user_id` Ana, `current_location_id` Quai;
     the draft `approved` with that `character_id`; the batch `committed`,
     both rows `committed`; NPCs `Mère` and `Maître Sol` exist (named as
     their sketches); `Maître Sol` holds Nécromancie at 5 and
     `skill_masters` for Nécromancie holds Vieux and Maître Sol; Kael's
     skills: the four base domains (perception 2, the others 1), Lame 2,
     Nécromancie 1 with `taught_by_id` Maître Sol; one active membership
     in `Guild` with role `apprenti`, none in the dropped faction; two
     `knowledge` rows with `is_secret` false and the levels given; a
     `histoire` fact per story line about Kael; relations `Mère -> Kael`
     (`ally`, 70), `Maître Sol -> Kael` (`fascination`, 80), `Ami -> Kael`
     (`interest`, 55), each with the sketch's role as `notes`, none for
     `Rival`; `rencontre` rows Kael-Membre with source `pc_creation`, and
     none Kael-Espion nor Kael-Cache; Kael-Mère, Kael-Maître Sol, Kael-Ami
     with source `relation`.
   - **DA2** atomicity: on a copy of the fixture, `write_relation` inside
     `pc_approval` is replaced by a stub raising `ValueError("boom")`
     (assignment on the module attribute, restored in `finally`) ->
     409 `boom`; every count (`entity`, `character`, `skill`,
     `faction_membership`, `knowledge`, `relation`, `rencontre`, `fact`)
     equals its count before the call; the draft is `submitted` with no
     `character_id`; the batch is `open` and its rows `proposed`.
   - **DA3** refusals, each 409 `Ce personnage ne peut pas encore être
     approuvé.` with nothing written: a sketch undecided; group `Famille`'s
     batch abandoned (`lot_missing`); a row rejected (`row_missing`); the
     world holding another profile's player character (`world_has_pc`);
     the approved draft approved again -> 404 `Brouillon introuvable.`
     (not submitted).
   - **DA4** the route `POST /api/characters/player` still creates a
     character at the four base domains and the open skills at rank 1
     (`ranks` and `teachers` absent), and refuses a second one for the
     creator with its `{"ok": false}` answer.
   - **DA5** static (code tokens): `cockpit/pc_approval.py` holds no
     `db.add(`, `.commit(`, `.flush(`, `chat(`; `routes/pc_review.py`'s
     approval function holds exactly one `db.commit()`;
     `writes/player_characters.py` names neither `npc_batch` nor `NpcBatch`.
   A case not reached is a FAILURE.
9. Commits: (1) items 1-4 with DA4; (2) items 5-6 with DA1-DA3, DA5; (3)
   item 7.

## Scope OUT

- The screens (F, G); K1-b (G).
- Ranks or skills set by the creator before the write (A1: she uses the
  skill tools after the approval).
- Dated encounters (TICKET-0120); a second player character in a world
  (G2, TICKET-0128).
- Raising an existing NPC to Maître (E2 (0126), rejected): an attached
  master is already Maître (`check_review`).

## Invariants to defend

- INV-68 (new), INV-67: nothing of the draft reaches canon before
  `approve_draft`; `check_review` judges the final version.
- INV-07: the knowledge goes through `_write_pc_knowledge`, `is_secret`
  false.
- INV-03, INV-66: membership secrecy decides the encounters
  (`public_member_ids`), never a prompt.
- INV-08, INV-18: every canon row through a listed writer, one commit at
  the route.
- INV-43: open skills come from `_pc_custom_skill_defs`; a skill that
  requires a master is written only when taught.
- INV-10: no existing relation or knowledge is edited.

## Decision rights

STOP:
- An anchor does not hold.
- `single_canon_write.py` cannot attribute a write of `pc_approval.py` or
  `player_characters.py` to a listed site.
- A step of C-11 needs a commit or a flush outside a writer to work.
- `perspective_isolation.py` turns red on `public_member_ids`.

ADAPT:
- `write_relation` refuses a type C-05 accepts: let `check_review` refuse
  it too (add the condition, same message), report.
- `record_encounter` needs `at`: pass none (now), report.
- The NPC created by `_commit_npc_row` already holds the master's skill
  (a base domain carrure): `write_master_rank` takes the `write_skill_rank`
  branch, as C-12 says; report if it happens in the fixture.

REPORT-ONLY:
- The draft's `existing_entity_id` (the player's suggestion) is never
  written: only the creator's `review_entity_id` counts.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/draft_approval.py`
      PASS (DA1-DA5); `creator_review.py`, `single_canon_write.py`,
      `npc_agent_strata.py`, `perspective_isolation.py`, `zone_placement.py`,
      `npc_skills.py`, `claude_md_contract.py`, `module_budget.py` PASS.
- [ ] Named mutations, each red then reverted: drop the teacher from the
      taught row -> DA1; commit the batches before the character (a
      `db.commit()` after step 1) -> DA2 and DA5; drop `is_secret == False`
      from `public_member_ids` -> DA1 (Espion met); skip `review_blockers`
      in step 0 -> DA3.
- [ ] `corpus_gate.py`: every check PASS except `pipeline_state.py`, red
      only on the arrow to `creator_review_ui.py`.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `.claude/rules/character-creation.md` (Scope IN 7); the docstrings of
  Scope IN 1 and 5. The decisions entry is G's.
