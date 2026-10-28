# LOT — TICKET-0129 "The creator reviews a submitted character and writes it to canon"

Lot RECON run in the chat session on `main` at `11cafc0` (PR #155,
TICKET-0126 merged; schema v2.32). Briefs are executed one per session;
this header is authoritative on any conflict with a brief's embedded copy.

## Objective and cut

The creator opens a submitted character draft in Création > Personnages
joueurs and reviews it with all the lore: she chooses the starting place
(any visitable place), decides for every person of the story whether it is
created, attached to an existing character or left out, picks the master
of every skill that requires one, keeps or drops each membership, and sets
the feeling each person has for the character. Each logical group of people
to create becomes an NPC batch of the existing generator, anchored on the
character, which she reviews row by row. She either returns the draft to
the player with a note -- he gets his own version back, corrects it and
resubmits -- or approves it: one transaction writes the people, the
masters' rank, the character, his skills (taught by their master), his
memberships, his knowledge, the relations and the encounters, and closes
the draft. The player then sees his character accepted. On a character's
skill pane, a « Joueur » field attaches the character to a player profile
or gives it back to the creator (K1-b).

The review edits nothing of the player's version: the creator's choices
live in review columns the player's reads never name (A1). Ranks are the
player's; the creator adjusts them after the approval with the existing
skill tools (A1 moves L2's « at review » to « right after approval »).
The lot stops there. Not in it: the « PJ actif » selector (0128, which
lifts G2), the character's perspective (0127), dated encounters (0120),
Play, a metric of the designer.

## Briefs in this lot

- A -- `review-groundwork`: the amendment line of TICKET-0126; the
  character recipe leaves `routes/creator.py` for a commit-free writer;
  the NPC row commit leaves the NPC agent route for a cockpit module. Two
  pure moves.
- B -- `schema-v2-33`: the review columns, the draft's character, the
  review batch's draft and group, the row's sketch, the encounter source
  `pc_creation`, the migration, the docs.
- C -- `review-check-and-return`: `check_review`, the review writer, the
  creator's review reads and routes, the return to the player and the
  player's rights on a returned draft.
- D -- `review-lots`: one NPC batch per group anchored on the character,
  kept out of the NPC agent's panel and commit, names and sketches carried
  to the rows.
- E -- `approval`: the one transaction that writes the draft to canon;
  INV-68.
- F -- `review-panel`: the review section of the creator's draft panel.
- G -- `player-return-and-profile-link`: the player's returned and
  accepted states in `/jouer`; K1-b; the decisions entry.

## Dependency graph

- A -> E: E calls the writer A extracts (C-01) and the row commit A moves
  (C-02).
- A -> D: D adds `cockpit/pc_approval.py` to the strata check's sets that
  A re-points (R-13).
- B -> C, D, E, G: every later brief reads or writes B's columns (C-03).
- C -> D: D's lot route lives in C's route module and D fills the `lot`
  key of C's review shape (C-08).
- C, D -> E: E's approval runs `check_review` (C-05) and reads the review
  batches (C-09).
- C, D, E -> F: the panel calls C-08's routes, D's lot route and E's
  approval.
- C -> G: the player's returned state reads C's status rights (C-06); the
  profile routes join C's route module.
- E -> G: the accepted state names the character an approval writes.
- F -> G: G adds CU2 and CU3 to the check F creates
  (`creator_review_ui.py`).

## RECON

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

### R-14 -- every check that reads a moved symbol (protocol step 4)
Opened: the two greps below, run at `11cafc0`.
Finding (pasted):
```
$ grep -rn "routes/creator.py\|routes\.creator\|create_player_character\|_pc_custom_skill_defs\|_write_pc_knowledge\|PlayerKnowledgeItem" tooling/verify/
tooling/verify/checks/player_worlds.py:62:    from world_engine.cockpit.routes.creator import WorldCreateBody, create_world, get_world
tooling/verify/checks/player_worlds.py:79:    from world_engine.cockpit.routes.creator import WorldUpdateBody, update_world
tooling/verify/checks/agenda_assist.py:77:        failures.append("POST /api/agendas/generate route not registered in routes/creator.py")
tooling/verify/checks/npc_skills.py:50:   row held. `_pc_custom_skill_defs` (a new PC's seed) lists no
tooling/verify/checks/npc_skills.py:426:    from world_engine.cockpit.routes.creator import _pc_custom_skill_defs
tooling/verify/checks/npc_skills.py:452:        seeded = {d.name for d in _pc_custom_skill_defs(ids["world"], session)}
tooling/verify/checks/npc_schedule.py:46:(`cockpit/routes/creator.py::set_world_phase`) calls nothing beyond a fixed
tooling/verify/checks/draft_world.py:283:    from world_engine.cockpit.routes.creator import generate_creation_draft
tooling/verify/checks/draft_world.py:306:    from world_engine.cockpit.routes.creator import _ENTITY_CREATION_TYPES
tooling/verify/checks/world_cascade.py:478:    from world_engine.cockpit.routes.creator import delete_world
tooling/verify/checks/creation_budget.py:102:    from world_engine.cockpit.routes.creator import WorldCreateBody, create_world
tooling/verify/checks/germ_attach.py:170:    from world_engine.cockpit.routes.creator import _compose_entity_creation_brief as compose
tooling/verify/checks/germ_attach.py:238:    from world_engine.cockpit.routes.creator import (
tooling/verify/checks/player_routes.py:172:    from world_engine.cockpit.routes.creator import WorldUpdateBody, update_world
tooling/verify/checks/world_sheet.py:91:    from world_engine.cockpit.routes.creator import WorldCreateBody, create_world, get_world
tooling/verify/checks/world_sheet.py:114:    from world_engine.cockpit.routes.creator import (
tooling/verify/checks/zone_placement.py:30:     and `cockpit/routes/creator.py::create_player_character`. A seventh
tooling/verify/checks/zone_placement.py:58:    "world_engine/cockpit/routes/creator.py::create_player_character",
tooling/verify/checks/zone_placement.py:151:    from world_engine.cockpit.routes.creator import PlayerCharacterCreateBody, _validate_pc_creation
tooling/verify/canon_write_policy.txt:147:src/world_engine/cockpit/routes/creator.py::create_player_character       entity character skill
$ grep -rn "routes/npc_agent.py\|routes\.npc_agent\|_commit_npc_row\|NPC_AGENT_ROUTES_FILE\|\"npc_agent.py\"" tooling/verify/
tooling/verify/checks/npc_batch_count_contract.py:16:  c. `create_npc_batch` (`cockpit/routes/npc_agent.py`) accumulates
tooling/verify/checks/npc_batch_count_contract.py:31:ROUTE_FILE = ROOT / "src" / "world_engine" / "cockpit" / "routes" / "npc_agent.py"
tooling/verify/checks/npc_skills.py:411:    if "carrure=" not in (SRC / "cockpit" / "routes" / "npc_agent.py").read_text(encoding="utf-8"):
tooling/verify/checks/npc_agent_strata.py:16:     stratum: `cockpit/routes/npc_agent.py`, `npc_group_author.py`,
tooling/verify/checks/npc_agent_strata.py:20:  3. BRIEF-0037-c: `cockpit/routes/npc_agent.py` and `npc_group_author.py`
tooling/verify/checks/npc_agent_strata.py:24:     tables — the commit path (`_commit_npc_batch`/`_commit_npc_row`) is
tooling/verify/checks/npc_agent_strata.py:46:NPC_AGENT_ROUTES_FILE = SRC / "world_engine" / "cockpit" / "routes" / "npc_agent.py"
tooling/verify/checks/npc_agent_strata.py:53:    "src/world_engine/cockpit/routes/npc_agent.py",
tooling/verify/checks/npc_agent_strata.py:66:    "src/world_engine/cockpit/routes/npc_agent.py": NPC_AGENT_ROUTES_FILE,
```
`agenda_assist.py:24`, `event_assist.py:30` and `npc_schedule.py:80` read
`routes/creator.py` for routes and `set_world_phase`, none of which moves.
`zone_placement.py` (c) (:55-59, `KNOWN_LOCATION_WRITERS`) requires the set
of functions assigning `character.current_location_id` (attribute or
`Character(...)` keyword) to be exactly `writes/characters.py::
write_character_location`, `cockpit/play_stream.py::_perform_travel`,
`cockpit/routes/creator.py::create_player_character`; its (a) imports
`PlayerCharacterCreateBody, _validate_pc_creation` from the route (:151),
which stay. `npc_skills.py` A4 reads `carrure=` in `npc_agent.py` (:411) and
imports `_pc_custom_skill_defs` from the route (:426, :452).
`npc_batch_count_contract.py` (c) and (d) read `create_npc_batch` and
`_commit_npc_batch`, which stay.
Consequence: A's Scope IN carries one line per hit: `zone_placement.py`
(c)'s set gets the writer, `npc_skills.py` reads `carrure=` in
`npc_group_commit.py` and imports `_pc_custom_skill_defs` from the writer
module, `npc_agent_strata.py` per R-13, the policy line per R-15;
every other hit is unchanged because the pattern it asserts stays where it
is.

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

### R-28 -- the creator's frontend
Opened: `frontend/src/creation/PcDraftPanel.svelte:1-140`;
`frontend/src/creation/pcDrafts.svelte.js:1-39`;
`frontend/src/creation/EntityList.svelte:85-110, 190-205, 305-350`;
`frontend/src/creation/PjCreatePanel.svelte:25-35, 135-145`;
`frontend/src/creation/PjSkillFiche.svelte:1-120`;
`tooling/verify/checks/creation_layout.py:1-70`.
Finding: `PcDraftPanel.svelte` loads `loadPcDraft(id)` on
`creationState.selectedPcDraftId`, shows the draft read-only and ends with
`<p class="muted notice">La revue de la créatrice arrive avec un prochain
ticket : rien n'est encore écrit au monde.</p>` (:126). `pcDrafts.svelte.js`
exports `loadSubmittedDrafts`, `selectPcDraft`, `loadPcDraft` with a GET-only
fetch helper. CL5 requires `pcDrafts.svelte.js` to hold `'/api/pc-drafts'`
and no `method:`, and `PcDraftPanel.svelte` to hold none of `alert(`,
`confirm(`, `prompt(`, `method:`. `EntityList.svelte` reloads its lists
(`/api/skills/player-characters` included, which feeds
`creationState.playerCharIds`) when `creationState.entityListActivationTick`
changes (:200-203); `PjCreatePanel.svelte:140` bumps it with
`creationState.entityListActivationTick += 1;` after creating a character.
`PjSkillFiche.svelte` serves the `pj` and `npc` tabs: `characterType` is
`'npc'` on the `npc` tab, else `'player'` (:58); `characterId` holds the
selected character (:47, :64-65).
Consequence: the review UI is a child component with its own store (the
store holds `method:`; `PcDraftPanel.svelte` imports the component and
never a fetch); after approval the panel bumps the tick as
`PjCreatePanel.svelte` does; K1-b's field is a child of `PjSkillFiche`
shown when `characterType === 'player'`.

### R-29 -- the player's frontend
Opened: `frontend/src/joueur/CharacterCreation.svelte:1-91`;
`frontend/src/joueur/character.svelte.js:1-189`;
`tooling/verify/checks/player_shell.py:1-40`.
Finding: `locked` is `characterState.draft && characterState.draft.status
!== 'draft'` (:12); when locked the screen shows `Soumis à la créatrice —
en attente de sa revue.` (:28). `openCreation()` (:111-119) loads the
catalogue, `GET brouillon`, and `POST brouillon` when `body.draft` is null;
`take(body)` stores `draft`, `verdict`, `form`. PSH2: every URL literal
under `frontend/src/joueur/` starts with `/api/joueur/`; PSH5 requires the
three creation components to hold `Soumis à la créatrice — en attente de sa
revue.` among other strings.
Consequence: G locks only `submitted`, shows the note on `returned`, and
reads `character_name` before posting; the PSH5 string stays.

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

### R-35 -- the review's place in the series
Opened: `tooling/tickets/TICKET-0126-character-creation.md:96-160, 196-215`.
Finding: locked for 0129 at 0126: E1' (nothing reaches canon before the
creator's approval), C1 (0126) (a refusal gives back the player's own
version with the note, never her edits; nothing deleted), D1 (0126) (any
visitable place at review), E1 (0126) (master: an existing Maître or one
created at Maître; rejected E2), F'a-1, F-b, F1 (0126) (encounters
present, `first_at` at approval, source `pc_creation`; deferral to
TICKET-0120), G2, H1 (K1-b on the character's sheet, « Créatrice »
detaches), L2, INV-67.
Consequence: these hold unchanged; D2 of this ticket applies F'a-1 to the
letter (one batch per group).

## Contract sheet

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

### C-14 -- K1-b
Produced by: G   Consumed by: G's frontend
In `writes/player_characters.py`:
```
PROFILE_UNKNOWN = "Profil inconnu."
NOT_A_PC = "Ce personnage n'est pas un personnage joueur."
PROFILE_CREATING = "Ce profil crée déjà un personnage dans ce monde."
def set_player_profile(db: Session, *, character_id: str, user_id: str) -> Character
```
The `Character` must exist with `character_type == "player"`
(`ValueError(NOT_A_PC)`); the `User` must exist with `role` in `("player",
"creator")` (`ValueError(PROFILE_UNKNOWN)`); a `player` user holding a
not-approved draft in the character's world -> `ValueError(PROFILE_CREATING)`;
sets `user_id`, adds, flushes (an `IntegrityError` propagates).
In `cockpit/routes/pc_review.py`:
- `GET /api/pc-profiles?character_id=` (a player character of the active
  world, else 404 `Personnage introuvable.`) -> `{"profiles": [{"id",
  "name"}], "current_profile_id": str | null}`: active `player` users by
  name; `current_profile_id` the character's `user_id` when that user is a
  `player`, else null.
- `PUT /api/pc-profiles/{character_id}` body `{"profile_id": str | null}`
  -> null means the `creator` user; `set_player_profile`, commit, the GET
  shape. `ValueError` -> 422; `IntegrityError` -> rollback, 409 « Ce profil
  a déjà un personnage dans ce monde. ».

### C-15 -- the review's frontend store
Produced by: F   Consumed by: F's component
`frontend/src/creation/pcReview.svelte.js` exports `loadReview(id)`,
`saveReview(id, body)`, `returnDraft(id, note)`, `prepareLot(id, label)`,
`loadLot(batchId)` (`GET /api/npc-batches/{id}`), `runLot(batchId)`
(`POST /api/npc-batches/{id}/run-next` until `npcs_done ===
npcs_total`), `setLotRow(batchId, rowId, patch)` (`PATCH
/api/npc-batches/{id}/rows/{rowId}`), `abandonLot(batchId)`,
`approveDraft(id)`, each through `api(path, options)` imported from
`./sheetRequest.svelte.js` (the shared helper `PjSkillFiche.svelte`
uses: it throws the response's `detail`); a write passes `{ method,
headers: { 'Content-Type': 'application/json' }, body:
JSON.stringify(...) }`. `afterApproval()` sets
`creationState.selectedPcDraftId = null`, calls `loadSubmittedDrafts()`
(from `./pcDrafts.svelte.js`) and bumps
`creationState.entityListActivationTick += 1;` (the
`PjCreatePanel.svelte:140` precedent); `afterReturn()` does the first two.

### C-16 -- the player's accepted and returned states
Produced by: G   Consumed by: G's frontend
`get_draft`'s branch with no open draft answers `{"draft": None, "verdict":
None, "character_name": name}`, `name` the entity name of the player
character the profile holds in the world (`Character.world_id`,
`Character.user_id == profile_id`, `character_type == "player"`) --
approved from a draft or attached by K1-b --, else null. The branch with
an open draft keeps its two keys. A `returned` draft is answered as any
open draft (`status: "returned"`, `creator_note` set).

### C-17 -- K1-b's frontend
Produced by: G   Consumed by: `PjSkillFiche.svelte`
`frontend/src/creation/pcProfiles.svelte.js` exports
`loadProfiles(characterId)` (`GET /api/pc-profiles?character_id=`) and
`setProfile(characterId, profileId)` (`PUT /api/pc-profiles/{id}`, body
`{profile_id}`), through the same `api`. `PjProfileField.svelte` (prop
`characterId`) shows a `<select>` labelled « Joueur » whose first option
is « Créatrice » (value `''`, sent as `null`), then one option per
profile; a change saves at once and shows the server's message on a
refusal, in place; no `alert(`, `confirm(`, `prompt(`.
`PjSkillFiche.svelte` imports it and renders `<PjProfileField
{characterId} />` above its skill list when `characterType === 'player'`
and `characterId` is set.

## Gate output

### (a) Property trace

One line per property the lot asserts about existing code: property -> finding -> file opened (the declaring file).

- `pc_draft` columns, CHECKs, `idx_pc_draft_open`; sketch / membership / knowledge columns -> R-02 -> `models/pc_drafts.py`
- `_require_open` refuses all but `draft`; `DRAFT_LOCKED_MESSAGE` text; save keeps sketches by id and deletes unlisted; `apply_design` deletes designer rows; `submit_draft` shape -> R-03 -> `writes/pc_drafts.py`
- `_writable` refuses all but `draft`; `get_draft`'s None branch; route prefix -> R-04 -> `cockpit/routes/player_creation.py`
- `DRAFT_VIOLATION_CODES` members; `check_draft` rules and messages; `check_creation` signature -> R-05 -> `creation_check.py`
- `draft_view` keys and `view` semantics; `open_draft_of` -> R-06 -> `pc_draft_reads.py`
- detail route keys and 404 text -> R-07 -> `cockpit/routes/pc_drafts.py`; SD2 equality and SD3 tokens -> R-07 -> `checks/submitted_drafts.py` (implementation lines :35, :122)
- the character recipe's statements, imports, answers; `_pc_custom_skill_defs`, `_write_pc_knowledge` bodies -> R-08 -> `cockpit/routes/creator.py`
- `RANKS`, `MAX_RANK`, `DEFAULT_RANK` -> R-09 -> `skill_ranks.py`; `Skill.rank` default and CHECK -> R-09 -> `models/canon_skill.py`; `write_skill_row` adds itself and its refusals; `write_skill_rank` leaves the add -> R-09 -> `writes/characters.py`; `skill_masters` -> R-09 -> `skill_access.py`; start ranks of `start_sheet` -> R-09 -> `creation_rules.py`
- NPC route functions, singleton, list, id routes without world filter, row commit shape, batch commit guards -> R-10 -> `cockpit/routes/npc_agent.py`
- `JOURNAL_DIR`, `resolve_vocabulary` reads the active world, pinned lines skip the placement call, faction forcing at :380-383, row built at :393, patchable fields -> R-11 -> `npc_group_author.py`
- staging tables' columns, JSON scope and payload, ENCOUNTER_SOURCES members -> R-12 -> `models/ephemeral.py`
- strata guarantees and their sets -> R-13 -> `checks/npc_agent_strata.py` (implementation, :52-68, :97-200)
- `zone_placement.py` (c) set; `npc_skills.py` A4 path and import -> R-14 -> those checks' implementations (:55-59, :151; :411, :426)
- policy line format and the PC site; return-type attribution -> R-15 -> `canon_write_policy.txt`, `checks/single_canon_write.py` (implementation :337-366)
- `write_membership` adds itself -> R-15/R-18 -> `writes/factions.py`; `write_relation` adds itself, social `a_to_b`, birth encounter -> R-16 -> `writes/relations.py`; `is_social`, excluded and retired types -> R-16 -> `relation_orientation.py`; `RELATION_TYPES` -> R-16 -> `cockpit/crud/_shared.py`
- `record_encounter` signature and refusal -> R-17 -> `encounters.py`; `rencontre` not canon -> R-17 -> `canon_write_policy.txt`
- `_public_members` WHERE triplet; PI1 tokens -> R-18 -> `perspective_selectors.py`, `checks/perspective_isolation.py` (docstring and its token list)
- `KNOWLEDGE_LEVELS` -> R-19 -> `writes/knowledge.py`; `histoire` is an affirmation facet -> R-19 -> `facets.py`; INV-07 text -> R-19 -> `CLAUDE.md`
- `idx_character_one_pc_per_user_world`, `user_id` without FK -> R-20 -> `models/canon.py`; `User.role` -> R-20 -> `models/pipeline.py`
- deferred FKs in the cascade; purge order; startup purge keeps two closed -> R-21 -> `writes/worlds.py`, `cockpit/routes/creator.py`, `npc_group_author.py`, `cockpit/app.py`
- migration helpers, guard and transaction shape -> R-22 -> `scripts/migrate_v2_32_character_creation.py`; schema doc sections -> R-22 -> `world-engine-schema.md`
- CS1 equality and version pin; CB5 tokens -> R-23 -> `checks/creation_schema.py`, `checks/creation_budget.py` (implementations)
- PC3 iterates `DRAFT_VIOLATION_CODES`; PC5; PC7 tokens -> R-24 -> `checks/player_creation.py` (implementation :288-339)
- banned names -> R-25 -> each check's implementation lines listed there
- budgets, INV id rules, rule-file front matter -> R-26 -> `checks/claude_md_contract.py`
- line and function counts -> R-27 -> the files, measured
- `PcDraftPanel` notice text; CL5 tokens; the list reload tick and its bump precedent; `characterType` / `characterId` -> R-28 -> those Svelte files and `checks/creation_layout.py`
- `locked` expression and PSH5 string; `openCreation` flow -> R-29 -> `CharacterCreation.svelte`, `character.svelte.js`, `checks/player_shell.py`
- router imports and includes -> R-30 -> `cockpit/app.py`
- the arrow floor -> R-31 -> `checks/pipeline_state.py` (implementation :54, :113-120)
- `_player_character_id` 409 -> R-32 -> `cockpit/crud/entities.py`
- JSON allow-list -> R-33 -> `checks/json_ui_boundary.py`
- fixture recipe -> R-34 -> `checks/submitted_drafts.py`

Presuppositions: no brief says « follow the existing pattern ». Where a brief
mirrors something, it names the file and lines: the v2.32 migration helpers
(R-22), the tick bump of `PjCreatePanel.svelte:140` (R-28), the fixture of
`submitted_drafts.py:40-60, 155-170` (R-34), the faction forcing of
`npc_group_author.py:380-383` (R-11).

### (b) Case tables

**Table 1 -- draft status x writer call** (C-06; `_require_open` /
`_require_submitted`):

| status | save_player_draft / apply_design | submit_draft | save_review / return_draft / mark_approved |
|---|---|---|---|
| draft | written | -> submitted (when no violation) | DraftLocked (REVIEW_LOCKED_MESSAGE) |
| submitted | DraftLocked (DRAFT_LOCKED_MESSAGE) | DraftLocked | written; return -> returned; approve -> approved |
| returned | written (B1) | -> submitted (when no violation) | DraftLocked (REVIEW_LOCKED_MESSAGE) |
| approved | DraftLocked; unreachable from the player's routes (`open_draft_of` skips it -> 404) | DraftLocked | DraftLocked |

Every cell is reached: CR3 (returned rows), PC5 (submitted, player side),
CR2 (draft and returned on the review side), DA3 (approved twice).

**Table 2 -- a sketch's review x its kind -> approval** (C-05, C-11):

| review_action | kind | check_review | approval |
|---|---|---|---|
| NULL | any | `sketch_undecided` | refused |
| create | not master | relation type checked | a lot line; its row -> NPC; relation NPC -> PC |
| create | master | relation type checked | a lot line (master text); NPC; Maître row; teacher of its skill when that skill requires a master and rank >= 1; relation |
| attach | not master | entity an active non-player character, not named twice; relation type | relation existing -> PC |
| attach | master | as above, and in `skill_masters` (`master_not_master`) | relation; teacher of its skill |
| drop | not master | nothing | nothing |
| drop | master | not counted as a master: `master_without_sketch` when its skill requires a master at rank >= 1 and no other master sketch remains | nothing |

**Table 3 -- `check_review`'s codes, each reachable alone** (CR1): every
code of `REVIEW_VIOLATION_CODES` plus `name_missing`, `story_missing`,
`start_place_missing`, `too_many_sketches`, `master_without_sketch`,
`membership_invalid`, `pc_exists`, and one `check_creation` code
(`over_pool`), each on a draft where only that rule fails. `world_has_pc`
and `pc_exists` are reached apart: `world_has_pc` alone with another
profile's character in the world; `pc_exists` always comes with
`world_has_pc` (the profile's own character is a player character of the
world), so CR1 asserts the pair `[pc_exists, world_has_pc]` for that
state, never `pc_exists` alone.

**Table 4 -- `review_blockers`** (C-09):

| state of a `create` sketch's group | blocker |
|---|---|
| no open review batch for the group | `lot_missing` (once per group) |
| open, `npcs_done < npcs_total` | `lot_incomplete` (once per group) |
| complete, the sketch's row rejected, failed or absent | `row_missing` |
| complete, a retained row for the sketch | none |

**Table 5 -- K1-b** (C-14):

| character | target | result |
|---|---|---|
| a player character | a player profile without a character nor an open draft in that world | attached |
| a player character | `null` (the creator) | detached to the creator user |
| a player character | a profile holding another character in the world | 409 (`IntegrityError`) |
| a player character | a profile with a not-approved draft in the world | 422 `PROFILE_CREATING` |
| an NPC | any | 422 `NOT_A_PC` |
| unknown or other-world id | any | 404 `Personnage introuvable.` |

**Table 6 -- a batch by kind x the NPC agent** (C-09):

| batch | `_open_batch` (singleton) | `GET /api/npc-batches` | id routes (get, run-next, patch, abandon) | `/commit` |
|---|---|---|---|---|
| agent batch (`pc_draft_id` NULL) | counted | listed | served | committed |
| review batch | ignored | not listed | served | 409 |

### (c) Enumerations

Pasted in their findings: the checks reading the moved symbols (R-14), the
readers of `ENCOUNTER_SOURCES` (R-17), the name bans and the lot's new
names (R-25). The checks naming the staging tables, and those naming the
draft and creation modules this lot edits (run at `11cafc0`):
```
$ grep -rln "npc_batch\b\|NpcBatch\b\|npc_batch_row" tooling/verify/checks/
tooling/verify/checks/json_ui_boundary.py
tooling/verify/checks/npc_batch_purge.py
tooling/verify/checks/npc_batch_count_contract.py
tooling/verify/checks/world_cascade.py
tooling/verify/checks/env_guard.py
tooling/verify/checks/purge_fk_ordering.py
tooling/verify/checks/npc_agent_strata.py
$ grep -rln "pc_draft_reads\|writes/pc_drafts\|writes.pc_drafts\|player_creation.py\|PcDraftPanel\|CharacterCreation\|PjSkillFiche" tooling/verify/checks/
tooling/verify/checks/player_creation.py
tooling/verify/checks/creation_layout.py
tooling/verify/checks/npc_skills.py
tooling/verify/checks/graph_primitive.py
tooling/verify/checks/player_shell.py
tooling/verify/checks/submitted_drafts.py
tooling/verify/checks/skill_progression.py
tooling/verify/checks/rank_trials.py
```
Each, against the lot: `json_ui_boundary.py` lists the two JSON columns by
name, unchanged; `npc_batch_purge.py` reads `cockpit/app.py`'s purge,
untouched; `npc_batch_count_contract.py` reads `_line_units`,
`create_npc_batch`, `_commit_npc_batch`, which keep their loops and
guards (D adds a guard after the existing one); `world_cascade.py` inserts
raw rows that the v2.33 defaults and NULLs admit; `env_guard.py` requires
the guard C-03 copies; `purge_fk_ordering.py` creates batches through the
models (new columns nullable); `npc_agent_strata.py` per R-13;
`player_creation.py` per R-24 (PC5 still holds: a submitted draft stays
locked); `creation_layout.py` per R-28 (CL5 holds: `PcDraftPanel.svelte`
gains an import and a component, no `method:`); `npc_skills.py` per R-14
and its C2 needles in `PjSkillFiche.svelte` (G adds an import and one
component line, removes nothing); `graph_primitive.py` names
`PjSkillFiche.svelte` in a comment only (:271); `player_shell.py` per R-29;
`submitted_drafts.py` per R-07; `skill_progression.py` bans the word
`tier` in `PjSkillFiche.svelte` (:444-446) -- G's edit holds none;
`rank_trials.py` pins `s.trial_ready` and « épreuve de rang à passer » in
it, untouched.

### (d) Families

Family contracts written before their members and re-read after the last:
the review routes (C-08: GET shape fixed first, then each POST/PUT by its
brief), the review codes (C-05: the code tuple before the rules), the
blockers (C-09: one table, three codes). Re-read after C-14: every
route of C-08 is keyed by the active world and answers 404 on a draft of
another world; every refusal string is in French and quoted once.

### (e) Gates and the modules that satisfy them

Proposed:
- `review_schema.py` (B) -- satisfied by `models/pc_drafts.py`,
  `models/ephemeral.py`, `schema_version.py`,
  `scripts/migrate_v2_33_creator_review.py`. Needs no forbidden module.
- `creator_review.py` (C, D, G) -- satisfied by `creation_check.py`
  (`check_review`, read-only, CB5 holds), `writes/pc_drafts.py`,
  `pc_review_reads.py`, `cockpit/routes/pc_review.py`,
  `cockpit/pc_approval.py` (D), `npc_group_author.py` (D), the NPC route
  (D), `writes/player_characters.py` (G). The lot generator is stubbed by
  assignment (R-11); no model is called.
- `draft_approval.py` (E) -- satisfied by `cockpit/pc_approval.py`,
  `writes/player_characters.py`, `perspective_selectors.py`. Its static
  rule forbids `db.add(` and `.commit(` in `cockpit/pc_approval.py`; every
  write there is a writer call (C-11), so nothing legitimate is forbidden.
- `creator_review_ui.py` (F, G) -- satisfied by `PcReviewSection.svelte`,
  `pcReview.svelte.js`, `PcDraftPanel.svelte`, `CharacterCreation.svelte`,
  `character.svelte.js`, `PjProfileField.svelte`, `pcProfiles.svelte.js`,
  `PjSkillFiche.svelte`, and the built assets.
Passed, by the module that satisfies them:
- `single_canon_write.py` -- the policy lines A, E, G write (R-15).
- `npc_agent_strata.py` -- `npc_group_commit.py` and `pc_approval.py`
  named in both sets (A, D); no `writes/` file names the staging tables.
- `zone_placement.py` -- the writer named in (c) (A); the approval assigns
  no location itself.
- `npc_skills.py` -- `carrure=` in `npc_group_commit.py`, the import from
  the writer module (A).
- `creation_schema.py` -- re-pinned by B.
- `json_ui_boundary.py`, `world_cascade.py`, `player_creation.py`,
  `submitted_drafts.py`, `creation_layout.py`, `player_shell.py`,
  `skill_progression.py`, `rank_trials.py` -- unchanged, held per (c).
- `module_budget.py` -- R-27; `claude_md_contract.py` -- R-26 (E's INV-68
  line under 100 characters, the rule file under 4 000).
- `pipeline_state.py` -- red until F per R-31, named in each Done means.
No brief moves or renames a file; A moves functions between files, and
R-14 is its grep with a line per hit.

## Amendments

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
