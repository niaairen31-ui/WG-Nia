<!-- slug: review-groundwork -->
# BRIEF 0129-A — "Two pure moves and the amendment row of 0126"

Lot: LOT-0129-creator-review.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

- `tooling/tickets/TICKET-0126-character-creation.md:241-245` is the
  « Amendment log » table holding only its empty row;
  `tooling/lots/AMENDMENT-0126-01.md` exists.
- `src/world_engine/cockpit/routes/creator.py` is 968 lines;
  `_pc_custom_skill_defs` starts at :833, `_write_pc_knowledge` at :844,
  `@router.post("/api/characters/player")` at :864, `@router.get("/api/npcs")`
  at :944.
- `src/world_engine/cockpit/routes/npc_agent.py` is 298 lines;
  `_commit_npc_row_goals` starts at :178, `_commit_npc_row` at :198,
  `_commit_npc_batch` at :238; :31 is `from ...writes import write_npc_goal`.
- `tooling/verify/canon_write_policy.txt:147` is
  `src/world_engine/cockpit/routes/creator.py::create_player_character       entity character skill`.
- `tooling/verify/checks/zone_placement.py:58` names
  `"world_engine/cockpit/routes/creator.py::create_player_character"`;
  `npc_skills.py:411` reads `carrure=` in `npc_agent.py`, `:426` imports
  `_pc_custom_skill_defs` from `world_engine.cockpit.routes.creator`.
- `tooling/verify/checks/npc_agent_strata.py:52` opens
  `ALLOWED_REFERENCE_FILES = {`, `:65` opens `DIRECT_WRITE_SCAN_FILES = {`.
- `CLAUDE.md:172-173` reads « at write time by the accept route
  (`create_player_character` via `writes.write_knowledge`), never by the
  generator. [no check] ».

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

## Context

TICKET-0129 lets the creator review a submitted character and write it to
canon in one transaction (E1). That transaction needs the character
recipe and the NPC row commit as functions it can call without a route:
today the first lives inside the route `create_player_character`, the
second inside the NPC agent's route module (R-08, R-10). This brief moves
both, behavior unchanged, and repairs TICKET-0126's amendment log. No
schema change.

## Scope IN

1. `tooling/tickets/TICKET-0126-character-creation.md`: replace the empty
   row of the « Amendment log » table (the line `|    |                 |               |                               |`
   right under the header separator) with this line, verbatim:
   ```
   | AMENDMENT-0126-01 | F | two name bans the lot missed (lore_as_facts R1, knowledge_identity K3): `pc_draft.story`, `backstory_terms`; the arrow floor | G, H, I |
   ```
   Commit: « TICKET-0126: record AMENDMENT-0126-01 in the amendment log ».
   (Its header: « Brief in flight: F »; its « Briefs regenerated »: G, H,
   I.) If the file says otherwise when you open it, copy its words and
   report.
2. Create `src/world_engine/writes/player_characters.py` per C-01: the
   docstring sentence of C-01, `from __future__ import annotations`, the
   imports C-01 lists, `_pc_custom_skill_defs` and `_write_pc_knowledge`
   copied byte for byte from `routes/creator.py:833-861`, then
   `write_player_character` whose body is the statements of
   `create_player_character` from `entity = Entity(` through
   `_write_pc_knowledge(entity.id, body.knowledge, db)` with the four
   renamings of C-01, then `return entity`. Keep each moved comment.
3. In `routes/creator.py`: delete `_pc_custom_skill_defs` and
   `_write_pc_knowledge` (and the blank lines that separated them); in
   `create_player_character`, replace the moved statements inside `try:`
   by C-01's call, keeping `db.commit()` and both `except` blocks and the
   success answer unchanged; add `from ...writes.player_characters import
   write_player_character` to the imports. Remove from the route's imports
   only the names nothing in `routes/creator.py` uses any more (check each
   of `KNOWLEDGE_LEVELS`, `write_entity_facets`, `write_knowledge`,
   `BASE_SKILL_DOMAINS`, `Skill`, `SkillDefinition`, `Character` with a
   grep before removing it). Update the route's docstring sentence
   « Mirrors `seed_pilot.py`'s `char-player` creation » to add « through
   `writes/player_characters.write_player_character` (TICKET-0129,
   BRIEF-0129-A) ».
4. `tooling/verify/canon_write_policy.txt`: replace line 147 by
   `src/world_engine/writes/player_characters.py::write_player_character entity character skill`
   preceded by the comment line
   `# TICKET-0129, BRIEF-0129-A: create_player_character's body relocated to writes/player_characters.py::write_player_character, commit-free; the route keeps the transaction. Same tables, same site count: a relocation, not a broadening.`
5. `tooling/verify/checks/zone_placement.py`: in `KNOWN_LOCATION_WRITERS`
   (:55-59) replace `"world_engine/cockpit/routes/creator.py::create_player_character"`
   by `"world_engine/writes/player_characters.py::write_player_character"`;
   in the docstring (c) (:27-31) replace `` `cockpit/routes/creator.py::
   create_player_character` `` by `` `writes/player_characters.py::
   write_player_character` (TICKET-0129, BRIEF-0129-A) ``. Rule (a)'s
   import of the route's `PlayerCharacterCreateBody, _validate_pc_creation`
   is unchanged (both stay in the route).
6. `tooling/verify/checks/npc_skills.py`: `:426` imports
   `_pc_custom_skill_defs` from `world_engine.writes.player_characters`;
   the docstring line :50 names « `writes/player_characters.py`'s
   `_pc_custom_skill_defs` ». (Item 9 changes :411.)
7. Create `src/world_engine/cockpit/npc_group_commit.py` per C-02:
   C-02's docstring sentence, `from __future__ import annotations`, the
   imports C-02 lists, then `_commit_npc_row_goals` and `_commit_npc_row`
   copied byte for byte from `npc_agent.py:178-235`.
8. In `routes/npc_agent.py`: delete those two functions; add `from
   ..npc_group_commit import _commit_npc_row`; delete `from ...writes
   import write_npc_goal` (:31) after a grep shows no other use. In the
   module docstring, the sentence naming the commit route as « this
   module's one canon-write site » gains « -- its row commit,
   `_commit_npc_row`, lives in `cockpit/npc_group_commit.py` since
   TICKET-0129 (BRIEF-0129-A) ».
9. `tooling/verify/checks/npc_skills.py:411-412`: read `carrure=` in
   `SRC / "cockpit" / "npc_group_commit.py"`; message
   `"A4: npc_group_commit.py does not pass the carrure"`; the docstring
   (:43) names `npc_group_commit.py` instead of `npc_agent.py`.
10. `tooling/verify/checks/npc_agent_strata.py`: add
    `"src/world_engine/cockpit/npc_group_commit.py"` to
    `ALLOWED_REFERENCE_FILES`; add a constant `NPC_GROUP_COMMIT_FILE = SRC
    / "world_engine" / "cockpit" / "npc_group_commit.py"` next to
    `NPC_AGENT_ROUTES_FILE` and the entry
    `"src/world_engine/cockpit/npc_group_commit.py": NPC_GROUP_COMMIT_FILE`
    to `DIRECT_WRITE_SCAN_FILES`; in the docstring, guarantee 2's list and
    guarantee 3's files name `cockpit/npc_group_commit.py` (TICKET-0129,
    BRIEF-0129-A).
11. `CLAUDE.md`, INV-07: replace `(`create_player_character` via
    `writes.write_knowledge`)` by `(`write_player_character` via
    `writes.write_knowledge`)`, keeping each line under 100 characters.
12. Commits: (1) item 1; (2) items 2-6, 11 (« TICKET-0129 A: the character
    recipe moves to writes/player_characters.py (pure move) »); (3) items
    7-10 (« TICKET-0129 A: the NPC row commit moves to
    cockpit/npc_group_commit.py (pure move) »).

## Scope OUT

- Any change of behavior: ranks, teachers, masters (E, C-12); the review
  batches and the agent's exclusions (D).
- Moving `_validate_pc_creation`, `PlayerKnowledgeItem`,
  `PlayerCharacterCreateBody` or `_commit_npc_batch`: they stay.
- `cockpit/pc_approval.py` and its strata entries (D).
- Any schema change (B).

## Invariants to defend

- INV-07: the moved `_write_pc_knowledge` still writes `is_secret=False`;
  its text is re-pointed (item 11), never weakened.
- INV-08: the character's rows stay on the creator-CRUD path; the policy
  relocates a site, never adds a table to it.
- INV-18: both moved bodies stay commit-free; the commit stays in the
  routes.
- INV-43: `_pc_custom_skill_defs` is moved unchanged (open skills only).

## Decision rights

STOP:
- An anchor does not hold.
- `single_canon_write.py` attributes a site of the new writer to a table
  other than `entity`, `character`, `skill` (beyond the `write_*` calls it
  already resolves).
- A check other than those of Scope IN 4-6, 9, 10 turns red.

ADAPT:
- The moved code needs an import C-01 or C-02 does not list: add exactly
  it, report.
- A name the route still uses would be removed by item 3: keep it, report.
- `AMENDMENT-0126-01.md` words differ from item 1's row: copy its words,
  report.

REPORT-ONLY:
- Imports of `routes/creator.py` or `npc_agent.py` left unused that item 3
  or 8 does not name.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python -c "import sys; sys.path.insert(0,'src'); from world_engine.schema_reconcile import static_table_names; print(sorted(static_table_names()))"`
      prints the same list before and after (paste both).
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/<name>.py` PASS for
      `single_canon_write.py`, `zone_placement.py`, `npc_skills.py`,
      `npc_agent_strata.py`, `npc_batch_count_contract.py`,
      `module_budget.py`, `claude_md_contract.py`, `player_worlds.py`,
      `world_sheet.py`, `germ_attach.py`, `draft_world.py`.
- [ ] Named mutations, each red then reverted: put `db.add(Character(...))`
      back into `create_player_character` -> `single_canon_write.py` red;
      remove `npc_group_commit.py` from `ALLOWED_REFERENCE_FILES` ->
      `npc_agent_strata.py` red; delete `carrure=` from
      `npc_group_commit.py` -> `npc_skills.py` A4 red.
- [ ] `routes/creator.py` has 33 functions and fewer than 968 lines;
      `routes/npc_agent.py` 10 functions.
- [ ] `corpus_gate.py`: every check PASS except `pipeline_state.py`, red
      only on the four arrows whose checks later briefs create
      (`review_schema.py`, `creator_review.py`, `draft_approval.py`,
      `creator_review_ui.py`) -- paste its lines.
- [ ] `/review-step` then `/close-step` (FILE_MAP regenerated).

## Docs to update

- `CLAUDE.md` INV-07 (Scope IN 11); the two route docstrings. No schema
  change, no changelog, no decision entry: this step is two pure moves.
