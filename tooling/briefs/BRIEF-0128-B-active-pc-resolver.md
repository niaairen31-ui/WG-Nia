<!-- slug: active-pc-resolver -->
# BRIEF 0128-B — "One resolver for the active player character"

Lot: LOT-0128-player-day.md (authoritative on conflict)
Depends on: BRIEF-0128-A (C-01: `world.active_pc_id`)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/models/canon.py`: `World.active_pc_id` exists (A).
- `src/world_engine/cockpit/crud/entities.py:209-229` is
  `_player_character_id`; `:886-897` is `delete_entity` (soft delete,
  `close_open_memberships`, one commit).
- `src/world_engine/cockpit/routes/day.py:124-137` is
  `_resolve_player_character`; its calls at `:176`, `:553`, `:859`.
- `src/world_engine/analyzer_transcript.py:248-258` is `_resolve_player_id`,
  its call at `:281`; `:63` imports `Character, Entity, Fact, Knowledge,
  ProposedMutation, PromptTemplate` from `.models`.
- `src/world_engine/cockpit/routes/creator.py:767-771`: `world_id =
  _crud._world_id(db)` then `try: player_id = _crud._player_character_id(db,
  world_id)` / `except HTTPException: player_id = None`.
- `src/world_engine/cockpit/routes/quests.py:45` and `debts.py:33` are
  `from .day import _resolve_player_character`.
- `src/world_engine/cockpit/crud/__init__.py:82` lists
  `_player_character_id,` in the `from .entities import (...)` block.
- `src/world_engine/cockpit/crud/_shared.py:57-61` is `_world_id`.
- `tooling/verify/canon_write_policy.txt:146` is the `update_world` line.
- `.claude/rules/` holds 12 files; `CLAUDE.md`'s « Path-scoped rules »
  list ends with `- \`verify-checks.md\` — how a verify check is written.`
- `grep -rnw "_player_character\|resolve_active_pc\|active_pc_id_or_none\|write_active_pc\|clear_active_pc_of" src tooling/verify`
  answers nothing; `grep -nw "active_pc_id_or_none\|clear_active_pc_of\|resolve_active_pc" src/world_engine/cockpit/routes/creator.py src/world_engine/cockpit/crud/entities.py src/world_engine/analyzer_transcript.py src/world_engine/cockpit/crud/_shared.py`
  answers nothing (no local name to collide with an import).

Halt if any anchor has moved.

## Facts carried

### R-02 -- the three resolvers of the player character
Opened: `src/world_engine/cockpit/crud/entities.py:209-229`;
`src/world_engine/cockpit/routes/day.py:124-137`;
`src/world_engine/analyzer_transcript.py:248-258, 276-285`; the
enumeration below.
Finding: `_player_character_id(db, world_id) -> str` selects the world's
`Character` rows with `character_type == "player"` (joined to `Entity`,
no status filter) and raises `HTTPException(400, "No player character in
the active world.")` at none, `HTTPException(409, "Plusieurs personnages
joueurs dans ce monde : précisez lequel.")` at two or more.
`_resolve_player_character(world_id, db) -> Character` (no join, no status
filter) raises `HTTPException(400, "expected exactly one player character
for this world, found N")` unless exactly one. `_resolve_player_id(db,
world_id) -> Optional[str]` returns the id when exactly one, else None; its
one caller `_build_payload_new_knowledge` uses it only as a hint among
`player_hints`. Enumeration (21 call sites, plus the definitions, the
re-export and two imports):
```
$ grep -rnw "_player_character_id\|_resolve_player_character\|_resolve_player_id" src tooling/verify --include=*.py
src/world_engine/analyzer_transcript.py:248:def _resolve_player_id(db: Session, world_id: str) -> str | None:
src/world_engine/analyzer_transcript.py:281:    resolved_player_id = _resolve_player_id(db, world_id)
src/world_engine/cockpit/crud/__init__.py:82:    _player_character_id,
src/world_engine/cockpit/routes/day.py:124:def _resolve_player_character(world_id: str, db: Session) -> Character:
src/world_engine/cockpit/routes/day.py:176:    character = _resolve_player_character(world_id, db)
src/world_engine/cockpit/routes/day.py:553:    character = _resolve_player_character(world_id, db)
src/world_engine/cockpit/routes/day.py:859:    character = _resolve_player_character(world_id, db)
src/world_engine/cockpit/routes/creator.py:769:        player_id = _crud._player_character_id(db, world_id)
src/world_engine/cockpit/routes/debts.py:33:from .day import _resolve_player_character
src/world_engine/cockpit/routes/debts.py:126:    character = _resolve_player_character(_crud._world_id(db), db)
src/world_engine/cockpit/routes/debts.py:132:    character = _resolve_player_character(_crud._world_id(db), db)
src/world_engine/cockpit/routes/play.py:97:    player_id   = body.player_id   or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/routes/play.py:381:    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/routes/play.py:436:    player_id = body.player_id or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/crud/entities.py:209:def _player_character_id(db: DbSession, world_id: str) -> str:
src/world_engine/cockpit/routes/quests.py:45:from .day import _resolve_player_character
src/world_engine/cockpit/routes/quests.py:138:    character = _resolve_player_character(_crud._world_id(db), db)
src/world_engine/cockpit/routes/quests.py:145:    character = _resolve_player_character(world_id, db)
src/world_engine/cockpit/routes/quests.py:161:    character = _resolve_player_character(world_id, db)
src/world_engine/cockpit/routes/quests.py:175:    character = _resolve_player_character(_crud._world_id(db), db)
src/world_engine/cockpit/routes/scene.py:82:    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/routes/scene.py:110:    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/routes/scene.py:183:    player_id = body.player_id or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/routes/scene.py:391:    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/routes/spatial.py:69:    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
src/world_engine/cockpit/routes/spatial.py:117:    player_id = player_id or _crud._player_character_id(db, world_id)
tooling/verify/checks/pc_resolution.py:74:    from world_engine.cockpit.crud.entities import _player_character_id
tooling/verify/checks/pc_resolution.py:77:        got = _player_character_id(db, world_id)
tooling/verify/checks/pc_resolution.py:87:    from world_engine.cockpit.crud.entities import _player_character_id
tooling/verify/checks/pc_resolution.py:89:    got = _player_character_id(db, world_id)
tooling/verify/checks/pc_resolution.py:95:    from world_engine.analyzer_transcript import _resolve_player_id
tooling/verify/checks/pc_resolution.py:97:    got = _resolve_player_id(db, world_id)
tooling/verify/checks/pc_resolution.py:141:    for path, name in ((ENTITIES, "_player_character_id"), (TRANSCRIPT, "_resolve_player_id")):
```
(The docstring lines of `pc_resolution.py` naming the functions, :6-12,
are text, not imports.) The only callers that import a resolver by name
are `debts.py:33` and `quests.py:45` (`from .day import
_resolve_player_character`); every `_player_character_id` caller goes
through `_crud.` (re-exported by `crud/__init__.py:82` from `.entities`).
Play, the scene and spatial accept an optional `player_id` and fall back
to the resolver.
Consequence: one neutral resolver (C-02) and two cockpit adapters in
`crud/_shared.py` (C-03) replace the three. `_player_character_id` keeps its
name at `_crud.`, so the 12 `_crud._player_character_id(` sites stay
textually unchanged; the 9 `_resolve_player_character(` sites become
`_crud._player_character(db, <world>)`; the analyzer calls
`active_pc_id_or_none`.

### R-03 -- every other read of a player character
Opened: the enumeration below; each site at its line.
Finding:
```
$ grep -rn 'character_type == "player"' src --include=*.py | grep -v "^src/world_engine/models/"
src/world_engine/analyzer_transcript.py:256:        .where(Entity.world_id == world_id, Character.character_type == "player")
src/world_engine/writes/events.py:179:    return character is not None and character.character_type == "player"
src/world_engine/cockpit/crud/entities.py:219:            Character.character_type == "player",
src/world_engine/cockpit/routes/day.py:127:            Character.world_id == world_id, Character.character_type == "player",
src/world_engine/cockpit/routes/player_creation.py:192:                Character.character_type == "player",
src/world_engine/perspective_view.py:120:            Character.character_type == "player",
src/world_engine/creation_check.py:265:        Character.character_type == "player",
src/world_engine/creation_check.py:308:            if character is None or character.character_type == "player":
src/world_engine/creation_check.py:377:        Character.character_type == "player",
src/world_engine/creation_check.py:382:        Character.world_id == world_id, Character.character_type == "player",
src/world_engine/writes/pc_drafts.py:102:        Character.character_type == "player",
src/world_engine/cockpit/spatial_presence.py:32:            if character is not None and character.character_type == "player":
src/world_engine/cockpit/crud/skills.py:258:        if character.character_type == "player" and not definition.requires_master:
src/world_engine/cockpit/crud/skills.py:608:        .where(Character.character_type == "player")
```
The criterion: apart from the three resolvers (`analyzer_transcript.py:256`,
`entities.py:219`, `day.py:127`) and G2 (`creation_check.py:382`), every
line is either a test of one given entity (`events.py:179`,
`creation_check.py:308`, `spatial_presence.py:32`, `skills.py:258`), a
per-profile lookup (`player_creation.py:192`, `perspective_view.py:120`,
`creation_check.py:265, 377`, `pc_drafts.py:102`) or the whole set of PCs
on purpose (`skills.py:608`, INV-43 gives an open skill to every PC).
Consequence: only the three resolvers and `creation_check.py:381-386` change
in this lot.

### R-04 -- the check that pins the resolvers
Opened: `tooling/verify/checks/pc_resolution.py:1-180`.
Finding: PR1 builds one world, two users, walks 0 / 1 / 2 PCs and asserts
`crud.entities._player_character_id` answers 400 `"No player character in
the active world."`, the id, 409 `"Plusieurs personnages joueurs dans ce
monde : précisez lequel."`, and `analyzer_transcript._resolve_player_id`
None / id / None; PR2 parses the two functions by name in `entities.py` and
`analyzer_transcript.py` and forbids `.first()`. `_fresh_engine()` sets
`WORLD_ENGINE_DATABASE_URL` to a temp file before any `world_engine` import.
It passes on `055b890`.
Consequence: B rewrites `pc_resolution.py` around the new resolver (C-02,
C-03, C-06) -- the functions it imports are gone.

### R-07 -- how a character is deleted
Opened: `src/world_engine/cockpit/crud/entities.py:820-897`;
`src/world_engine/cockpit/crud/__init__.py:28`.
Finding: `delete_entity` (`POST /entities/{entity_id}/delete`, :886-897) is
a soft delete: `entity.status = "inactive"`, closes open memberships,
commits. `update_entity` (:852-857) can also move a status off `active`.
No route hard-deletes a character; only `delete_world_cascade` does.
Consequence: an FK `ON DELETE SET NULL` covers the cascade only. A1's
« mise à NULL à la suppression » is written in `delete_entity` (C-04's
`clear_active_pc_of`); the resolver ignores an inactive PC, so any other
path that deactivates the active PC falls back as if no choice were made.

### R-11 -- the canon-write policy and its check
Opened: `tooling/verify/canon_write_policy.txt:1-13, 135-151, 165-168`;
`tooling/verify/checks/single_canon_write.py:1-30, 405-445`.
Finding: `world` is a canon table (:2). Its sanctioned writers are
`routes/creator.py::activate_world`, `create_world`,
`_activate_world_core`, `set_world_phase`, `update_world` (:135-146).
`crud/entities.py::delete_entity` is sanctioned for `entity` only (:168).
The check resolves a write's table from a parameter annotation (:416-420),
an annotated assignment `name: Model = ...` (:433-436) or a resolvable
value; a write whose table cannot be resolved fails.
Consequence: the writer of `world.active_pc_id` is a `writes/` module named
in the policy (C-04), each `db.add(` of it on a name annotated `World`.
`delete_entity` calls that writer and keeps its own `entity` line.

### R-12 -- the cockpit's shared accessors
Opened: `src/world_engine/cockpit/crud/_shared.py:1-61`;
`src/world_engine/cockpit/crud/__init__.py:60-90, 252-259`;
`src/world_engine/cockpit/crud/entities.py:94-105`.
Finding: `_shared.py` is « a closed, package-private set » whose docstring
lists each entry and why; « adding a new entry requires a brief ».
`_world_id(db)` (:57-61) raises `HTTPException(400, "No active world.
Activate a world before proceeding.")`. `_shared.py` imports
`HTTPException` and `Entity, Fact, FactParticipant, Knowledge, Relation,
World` from `...models` (:44-47). `crud/__init__.py` re-exports
`_player_character_id` and `_world_id` from `.entities` (:64-92);
`entities.py` imports `_world_id` from `._shared` (:94-105).
Consequence: B adds `_player_character` and `_player_character_id` to
`_shared.py` (docstring list extended) and re-exports both from
`crud/__init__.py`.

### R-13 -- the bootstrap and the shell's server mirror
Opened: `src/world_engine/cockpit/routes/creator.py:753-776`;
`src/world_engine/cockpit/legacy.html:1742-1760, 2752`;
`frontend/src/lib/serverState.svelte.js:1-35`;
`frontend/src/Header.svelte:1-98`; `frontend/src/creation/tabs.js:825-850`;
`frontend/src/creation/PjCreatePanel.svelte:130-138`;
`tooling/verify/checks/legacy_call.py:1-50`;
`tooling/verify/checks/module_budget.py:28-65`.
Finding: `get_bootstrap` returns `{world_id, player_id,
current_location_id}`; `player_id` comes from
`_crud._player_character_id` with `except HTTPException: player_id = None`
(:767-771). The legacy document reads `/api/bootstrap` once, at boot
(`loadBootstrap`, :1743-1749, called at :2752), into `PLAYER_ID`, used to
leave the PC out of member lists and to show his name. The shell's
`refreshServerState()` reads `/api/bootstrap` and `/api/worlds` into
`serverState.{worldId, playerId, worlds}`; `serverState.playerId`'s only
other reader is `PjCreatePanel.svelte:133-137`. `Header.svelte` (145
lines) holds the world `<select id="world-selector">` (:83) whose change
runs `activateWorldCascade(id, refreshServerState)`, which ends with
`handleWorldChanged()` (Création's refresh, `tabs.js:825-833`). The bridge
census (`legacy_call.py`) may only shrink: no new call into the legacy
window. `legacy.html` is held by a line ratchet (`module_budget.py`,
`LEGACY_DOCUMENT_LINE_CEILING = 2762`).
Consequence: the selector refreshes the shell mirror and Création; the
legacy document is not touched (its `PLAYER_ID` follows at its next load;
Play is out of scope). The bootstrap keeps its three keys.

### R-20 -- module budgets of the files this lot edits
Opened: `wc -l` and an `ast` function count of each file;
`tooling/verify/checks/module_budget.py:1-65`.
Finding (lines / top-level functions + methods):
`cockpit/routes/day.py` 903 / 28 (caps 1000 / 40, also JI7);
`cockpit/crud/entities.py` 932; `cockpit/routes/creator.py` 913;
`cockpit/crud/_shared.py` 296; `models/pipeline.py` 816;
`models/canon.py` 822; `writes/pipeline.py` 380; `cockpit/app.py` 360;
`dashboard_metrics.py` 372; `cockpit/routes/player.py` 192;
`frontend/src/journee/Journee.svelte` 263;
`frontend/src/Header.svelte` 145; `frontend/src/creation/tabs.js` 899
(frontend cap 1000 lines). `routes/day.py`'s functions are listed in R-15,
R-16 and :96-208.
Consequence: no logic beyond the P1 edits enters `routes/day.py`; every new
route or worker lives in a new module (C-06, C-10, C-11, C-12, C-13).

### R-29 -- the instruction corpus
Opened: `.claude/rules/player-surface.md` (1 626 characters);
`CLAUDE.md:236-262` (20 872 characters); character counts of every rule
file; `tooling/verify/checks/claude_md_contract.py:1-80, 240-312`;
`tooling/standards/ARCHITECTURE_DECISIONS.md` (last 40 lines).
Finding: root budget 22 000 characters, each rule file 4 000, no line
over 100; every Invariants bullet starts `- **INV-NN**` and ends `--
enforced by` plus check files or `[no check]`; ids run from INV-01 to the
highest with no gap; each rule file opens with a `paths:` front matter
whose globs (no `{` or `[`) each match a file; the root's « Path-scoped
rules » list equals the files on disk. INV-66 is
`.claude/rules/player-surface.md:21-34`. No rule file covers the day
chain. ARCHITECTURE_DECISIONS ends with `---`, a blank line and
`*Co-built with Claude, June 2026.*`; an entry goes above that footer.
Consequence: B creates `.claude/rules/day-chain.md` (INV-70) and its root
line; D adds INV-71 and the day globs; G amends INV-66 and writes the
ticket's decision entry.

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

### R-31 -- names this lot introduces do not exist yet
Opened: `grep -rnw <name> src tooling/verify frontend/src` per name.
Finding: zero hits for `active_pc`, `resolve_active_pc`,
`active_pc_id_or_none`, `world_player_characters`, `NoPlayerCharacter`,
`ActivePcUnchosen`, `_player_character`, `write_active_pc`,
`clear_active_pc_of`, `DayRunFailure`, `day_run_failure`, `published_text`,
`published_at`, `enqueue_day`, `run_day`, `interrupt_stale_days`,
`start_day_runner`, `day_runner`, `day_declare`, `day_run_reads`,
`day_runs`, `player_day`, `_day_world`, `_day_character`, `abandon_day`,
`reopen_day`, `publish_day`, `write_day_run_failure`, `DAY_RUN_STAGES`,
`DAY_RUN_FAILURE_CODES`. `quest_id` has 69 existing hits (quests,
offers, requests); `pass_play.quest_id` is new on that table.
Consequence: no imported name collides with a local binding in a file this
lot edits (the AMENDMENT-0131-01 lesson); each brief that adds an import
to an existing file greps it with `-nw` in its Mini-RECON.

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

## Contracts

### C-02 -- the active player character, one resolver
Produced by: B   Consumed by: B (C-03, C-06, the analyzer), G (none: the
player side keys on its profile)
Module `src/world_engine/active_pc.py`, docstring first sentence: « The
player character a creator surface acts for: one resolver for every
surface of the cockpit (TICKET-0128, A1; INV-70). » Reads only; imports
`sqlmodel` and `.models` only (no `fastapi`).
```
NO_PC_MESSAGE = "Aucun personnage joueur dans ce monde."
CHOOSE_PC_MESSAGE = "Choisissez le PJ actif."
class NoPlayerCharacter(LookupError)
class ActivePcUnchosen(LookupError)
def world_player_characters(db: Session, world_id: str) -> list[tuple[Character, str]]
def resolve_active_pc(db: Session, world_id: str) -> Character
def active_pc_id_or_none(db: Session, world_id: str) -> Optional[str]
```
`world_player_characters`: every `(Character, Entity.name)` with
`Character.world_id == world_id`, `Character.character_type == "player"`,
`Entity.status == "active"` (joined on `Entity.id == Character.id`), ordered
by `Entity.name`, then `Entity.id`.
`resolve_active_pc`: `pcs` = the characters above; `world = db.get(World,
world_id)`; if `world` is not None and `world.active_pc_id` is the id of
one of `pcs` -> that character; elif exactly one -> it; elif none -> raise
`NoPlayerCharacter(NO_PC_MESSAGE)`; else raise
`ActivePcUnchosen(CHOOSE_PC_MESSAGE)`. Never `.first()`.
`active_pc_id_or_none`: the resolved id, or None on either exception.

### C-03 -- the cockpit's two adapters
Produced by: B   Consumed by: B (every call site), D, E, F
In `src/world_engine/cockpit/crud/_shared.py`, after `_world_id`:
```
def _player_character(db: DbSession, world_id: str) -> Character
def _player_character_id(db: DbSession, world_id: str) -> str
```
`_player_character` returns `resolve_active_pc(db, world_id)`;
`NoPlayerCharacter` -> `HTTPException(status_code=400,
detail=NO_PC_MESSAGE)`; `ActivePcUnchosen` -> `HTTPException(status_code=409,
detail=CHOOSE_PC_MESSAGE)`. `_player_character_id` returns
`_player_character(db, world_id).id`. Both re-exported by
`cockpit/crud/__init__.py` (`_crud._player_character`,
`_crud._player_character_id`).

### C-04 -- the writer of `world.active_pc_id`
Produced by: B   Consumed by: B (C-06, `delete_entity`)
Module `src/world_engine/writes/active_pc.py`, docstring first sentence:
« The one writer of `world.active_pc_id`, the creator's choice of the
player character her cockpit acts for (TICKET-0128, A1). » Commit-free.
```
ACTIVE_PC_REFUSED = "Ce personnage ne peut pas être le PJ actif."
def write_active_pc(db: Session, *, world: World, character_id: Optional[str]) -> World
def clear_active_pc_of(db: Session, *, character_id: str) -> int
```
`write_active_pc`: `character_id` None clears; otherwise it must be the id
of one of `world_player_characters(db, world.id)`, else
`ValueError(ACTIVE_PC_REFUSED)` with nothing changed. Sets
`world.active_pc_id`, `world.updated_at = datetime.now(UTC)`,
`db.add(world)`; returns `world`.
`clear_active_pc_of`: for each world id whose `active_pc_id ==
character_id`, `row: World = db.get(World, world_id)`, clears it, sets
`updated_at`, `db.add(row)`; returns the count.
`canon_write_policy.txt` gains, with a comment line « # TICKET-0128,
BRIEF-0128-B (A1): the creator's choice of the active player character,
one column of `world`; set from the cockpit header, cleared when the
character is deleted. »:
```
src/world_engine/writes/active_pc.py::write_active_pc           world
src/world_engine/writes/active_pc.py::clear_active_pc_of        world
```

### C-05 -- the call sites of the former resolvers
Produced by: B   Consumed by: D (anchors), E
After B: `cockpit/crud/entities.py` defines no `_player_character_id`; the
12 `_crud._player_character_id(` call sites of R-02 are unchanged text;
`routes/day.py` defines no `_resolve_player_character`, and its three
calls (`declare_day`, `plan_day`, `resolve_day`) read
`_crud._player_character(db, world_id)`; `routes/quests.py` (4 calls) and
`routes/debts.py` (2 calls) read `_crud._player_character(db, <the world
expression they passed before>)` and import nothing from `.day`;
`routes/creator.py::get_bootstrap` reads `player_id =
active_pc_id_or_none(db, world_id)` (no `try`); `analyzer_transcript.py`
defines no `_resolve_player_id` and calls `active_pc_id_or_none(db,
world_id)`. `crud/entities.py::delete_entity` calls
`clear_active_pc_of(db, character_id=entity_id)` before its commit when
`entity.type == "character"`.

### C-06 -- the active-PC routes
Produced by: B   Consumed by: C
Module `src/world_engine/cockpit/routes/active_pc.py`, included in
`cockpit/app.py` after `_routes_day`. Both routes act on the active world
(`_crud._world_id`).
- `GET /api/active-pc` -> `{"world_id": str, "active_pc_id": str | None,
  "chosen": bool, "characters": [{"id": str, "name": str}]}`;
  `active_pc_id` is `active_pc_id_or_none`; `chosen` is
  `world.active_pc_id is not None and world.active_pc_id ==
  active_pc_id`; `characters` is `world_player_characters` as `{id,
  name}`, in its order.
- `PUT /api/active-pc` with body `{"character_id": str | None}` ->
  `write_active_pc`; `ValueError` -> 422 with its message, nothing
  committed; else one commit and the GET shape.
- No active world -> `_world_id`'s 400.

## Context

Three functions answer « which player character » today, each refusing a
second PC differently (R-02). A1 replaces them with one resolver in a
neutral module, fed by the creator's choice (`world.active_pc_id`, brief
A), and gives the cockpit the routes its header selector will use (C).
This brief changes no behaviour of a world with one PC; a world with
several answers « Choisissez le PJ actif. » until she picks one.

## Scope IN

1. New `src/world_engine/active_pc.py` per C-02. `world_player_characters`
   returns `list(db.exec(select(Character, Entity.name).join(Entity,
   Entity.id == Character.id).where(...).order_by(Entity.name,
   Entity.id)).all())` as `(Character, name)` tuples; `resolve_active_pc`
   walks them per C-02's order. No `.first()` anywhere in the module.
2. `src/world_engine/cockpit/crud/_shared.py`: add `Character` to the
   `...models` import; import `CHOOSE_PC_MESSAGE, NO_PC_MESSAGE,
   ActivePcUnchosen, NoPlayerCharacter, resolve_active_pc` from
   `...active_pc`; C-03's two functions right after `_world_id`, each with a
   one-line docstring. The module docstring's list gains, after the
   `_iso, _world_id, _get_entity` entry: « `_player_character`,
   `_player_character_id` (TICKET-0128, BRIEF-0128-B, A1) -- the player
   character every cockpit surface acts for: the HTTP face of
   `active_pc.resolve_active_pc` (400 none, 409 several and none chosen). »
3. `src/world_engine/cockpit/crud/entities.py`: delete `_player_character_id`
   (:209-229, with its blank lines); `delete_entity` calls
   `clear_active_pc_of(db, character_id=entity_id)` right before its
   `db.commit()` when `entity.type == "character"`; import
   `clear_active_pc_of` from `...writes.active_pc`. Its docstring gains:
   « A deleted character is no longer any world's active PC (TICKET-0128,
   A1). »
4. `src/world_engine/cockpit/crud/__init__.py`: remove `_player_character_id,`
   from the `from .entities import (...)` block; add `from ._shared import
   _player_character, _player_character_id` beside the other single-line
   imports (`from .items import ...`).
5. `src/world_engine/cockpit/routes/day.py`: delete
   `_resolve_player_character` (:124-137); its three calls become
   `character = _crud._player_character(db, world_id)`.
6. `src/world_engine/cockpit/routes/quests.py`: delete `from .day import
   _resolve_player_character`; each of the four calls becomes
   `_crud._player_character(db, <the world expression it passed>)`
   (`_crud._world_id(db)` or `world_id`, argument order swapped to `(db,
   world)`).
7. `src/world_engine/cockpit/routes/debts.py`: the same for its import and
   two calls.
8. `src/world_engine/cockpit/routes/creator.py::get_bootstrap`: `player_id =
   active_pc_id_or_none(db, world_id)` replaces the `try` / `except`;
   import `active_pc_id_or_none` from `...active_pc`. The docstring's
   sentence on `player_id` reads « `player_id` is the active player
   character (`active_pc.active_pc_id_or_none`, TICKET-0128): null when the
   world has none, or several and none chosen. » The response keys are
   unchanged.
9. `src/world_engine/analyzer_transcript.py`: delete `_resolve_player_id`;
   `:281` becomes `resolved_player_id = active_pc_id_or_none(db, world_id)`;
   import it from `.active_pc`; drop `Character` from the `.models` import
   if nothing else in the module names it (R-02: only the deleted body
   does).
10. New `src/world_engine/writes/active_pc.py` per C-04, every `db.add(` on a
    name annotated `World` (R-11). `tooling/verify/canon_write_policy.txt`:
    C-04's comment and two lines, right after the `update_world` line
    (:146).
11. New `src/world_engine/cockpit/routes/active_pc.py` per C-06 (docstring
    first sentence « The creator's choice of the player character her
    cockpit acts for (TICKET-0128, BRIEF-0128-B, A1). »; a pydantic
    `ActivePcBody(character_id: Optional[str] = None)`); `cockpit/app.py`:
    `from .routes import active_pc as _routes_active_pc` with the other
    route imports and `app.include_router(_routes_active_pc.router)` right
    after `app.include_router(_routes_day.router)`.
12. New rule file `.claude/rules/day-chain.md`:
    ```
    ---
    paths:
      - "src/world_engine/active_pc.py"
      - "src/world_engine/writes/active_pc.py"
      - "src/world_engine/cockpit/routes/active_pc.py"
      - "src/world_engine/cockpit/routes/day.py"
    ---

    # The active player character and the day chain

    A world may hold several player characters. The creator's cockpit acts
    for one of them, the active PC; a player acts for his own.

    ## Invariants

    - **INV-70** A creator surface's player character comes from one
      resolver, `active_pc.resolve_active_pc`: the world's `active_pc_id`
      when it names an active player character of the world, else the
      world's only one. Several and none chosen is a refusal, never a pick.
      -- enforced by `pc_resolution.py`
    ```
    `CLAUDE.md`, « Path-scoped rules » list, after the `character-creation.md`
    line: ``- `day-chain.md` — the active player character, the day chain.``
13. `tooling/verify/checks/pc_resolution.py`, rewritten (first sentence « G1
    check for TICKET-0128 (BRIEF-0128-B; first written for TICKET-0125) --
    one resolver gives the cockpit its player character; several and none
    chosen is a refusal. »), fresh database per R-35:
    - **PR1** -- `resolve_active_pc` walks lot (b)'s table row by row on one
      world (users Ana and Bea, PCs P and Q, an inactive PC R): every row's
      result or exception type and message (`NO_PC_MESSAGE`,
      `CHOOSE_PC_MESSAGE`); `active_pc_id_or_none` answers the id or None
      on each row; `world_player_characters` lists active PCs only, by
      name.
    - **PR2** -- static: no function named `_resolve_player_character`,
      `_resolve_player_id` or `_player_character_id` is defined under
      `src/world_engine` except `_player_character_id` in
      `cockpit/crud/_shared.py`; `routes/quests.py` and `routes/debts.py`
      import nothing from `.day`; no `.first()` call in `active_pc.py`;
      `active_pc.py` imports no `fastapi`.
    - **PR3** -- the adapters: `_crud._player_character` raises 400
      `NO_PC_MESSAGE` with no PC, 409 `CHOOSE_PC_MESSAGE` with two and none
      chosen, returns the chosen one; `_crud._player_character_id` its id.
    - **PR4** -- routes, through `TestClient(app,
      base_url="http://127.0.0.1")` on the active world: `GET
      /api/active-pc` with two PCs and none chosen -> exactly C-06's keys,
      `active_pc_id` None, `chosen` false, both characters; `PUT` Q -> 200,
      `active_pc_id` Q, `chosen` true; `PUT` an NPC, another world's PC,
      the inactive R and an unknown id -> 422 `ACTIVE_PC_REFUSED`, the
      column unchanged; `PUT` null -> 200, `chosen` false; `GET
      /api/bootstrap` answers Q's id when chosen, None when not.
    - **PR5** -- deletion: with Q chosen, `POST /api/entities/{Q}/delete`
      -> 200 and `world.active_pc_id` NULL; `write_active_pc` and
      `clear_active_pc_of` never commit (a rollback after each leaves the
      row unchanged).
    A row not reached is a FAILURE.
14. `python tooling/glue/gen_file_map.py`.

## Scope OUT

- The header selector and any frontend (C).
- The day chain's own character (D takes it from the day, not from the
  resolver), the player side (G keys on the profile).
- `legacy.html` (its `PLAYER_ID` follows at its next load; no new bridge
  call, `legacy_call.py`).
- Setting the active PC automatically at a character's approval or
  creation: not decided; a world with one PC needs no choice.
- Clearing the column on a status change other than `delete_entity`
  (`update_entity`, a `status_change` proposal): the resolver ignores an
  inactive PC (R-07, lot (b)).
- A2 (the choice kept in the browser, rejected).

## Invariants to defend

- **INV-70** (new, this brief): one resolver.
- **Two sanctioned canon-write paths** (`single_canon_write.py`): `world`
  is canon; its new writer is named in the policy (C-04).
- **INV-03** and the soft-delete rule: `delete_entity` stays a soft delete;
  it only also clears a world's choice.

## Decision rights

STOP: an anchor that does not hold; a call site of R-02 not listed there;
`single_canon_write.py` unable to attribute a write of `writes/active_pc.py`
after the annotation of C-04; `claude_md_contract.py` refusing the rule file
for a reason other than wording length.
ADAPT: a line of the rule file or of CLAUDE.md passes 100 characters ->
re-wrap it; `analyzer_transcript.py` still names `Character` elsewhere ->
keep the import. Report each.
REPORT-ONLY: a frontend reader of `serverState.playerId` other than
`PjCreatePanel.svelte`.
> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/pc_resolution.py` -> PASS (PR1-PR5).
- [ ] `single_canon_write.py`, `claude_md_contract.py` (« 70 invariants »),
      `file_map.py`, `module_budget.py`, `undefined_names.py`,
      `import_cycle.py`, `quests.py`, `debts.py`, `day_prompt_delivery.py`,
      `day_choice.py`, `day_plan.py`, `day_mutations.py`,
      `pipeline_wiring.py`, `creator_review.py`, `draft_approval.py`,
      `day_schema.py` -> PASS.
- [ ] `pipeline_state.py` / `corpus_gate.py` red only for the arrows of C,
      D, E, F, G (R-32).
- [ ] Live, test database: a world with one PC behaves as before in
      Journée (quests, debts) and Play.
- [ ] /review-step, then /close-step.

## Docs to update

`.claude/rules/day-chain.md` and its `CLAUDE.md` line (Scope IN 12).
`canon_write_policy.txt` (Scope IN 10). No schema change. The ticket's
ARCHITECTURE_DECISIONS entry is G's.
