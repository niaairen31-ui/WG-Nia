# LOT — TICKET-0128 "The player lives his days; a world may have several player characters"

Lot RECON run in the chat session on `main` at `055b890` (PR #159,
TICKET-0131 merged; TICKET-0127 merged at `e568908`; schema v2.33).
Briefs are executed one per session; this header is authoritative on any
conflict with a brief's embedded copy.

## Objective and cut

A world can hold several player characters. The creator picks the one her
cockpit acts for in the header (« PJ actif »): one resolver, fed by
`world.active_pc_id`, gives that character to every creator surface that
used to refuse a second PC (entities, the bootstrap, the scene, Play,
spatial, Journée's quests, debts and services, the transcript analyzer).
A world with one PC needs no choice; a world with several and no choice is
a clear refusal, « Choisissez le PJ actif. ». Deleting the character
clears the choice.

A player declares what his character does from `/jouer`. The declaration
answers at once; one background worker plans then resolves the day, one
day at a time, taking its world and its character from the day itself,
never from the active world. A failure is never silent: it is written to
`day_run_failure` with its stage, a closed code and the reason, the day
turns `flagged`, and Journée lists it with « Relancer » (resume at the
failed stage) and « Abandonner ». A server stopped mid-day leaves its days
as « interrompue » failures at the next start. A resolved day waits in
« À publier » until no proposal of that day awaits review; the creator may
rewrite the narrative, then publishes it; the narrator's text stays
intact, a published day can never be replayed. A character has at most one
unpublished day. The player sees his days, his declaration, « en cours »
or « en attente de la créatrice », and the published narrative -- the one
text he reads outside a perspective (INV-66 amended). The approval of a
second player character in a world (G2) is lifted.

The lot stops there. Not in it: Play and the scene for the player (I),
dated encounters and the calendar (0120), quests, debts and services on the
player side, showing the gains to the player (D2), moving the model calls
of the plan out of its write transaction (Y2, deferred).

## Briefs in this lot

- A -- `schema-v2-34`: `world.active_pc_id`, `pass_play.quest_id`,
  `published_text`, `published_at`, the table `day_run_failure`, the
  `abandoned` status, the migration (W1 publishes the days already
  resolved), the cascade, the docs, the shape check.
- B -- `active-pc-resolver`: the neutral resolver, the cockpit adapters,
  every call site of the three former resolvers, the writer of the
  column, the deletion path, the routes `/api/active-pc`, INV-70.
- C -- `active-pc-selector`: the selector in the cockpit header.
- D -- `day-chain-world`: the chain takes its world and its character from
  the day (P1), the world reaches the premise, the extraction, the
  feasibility and the presence rung; the quest pin moves to the
  declaration (Q1); INV-71.
- E -- `day-runner`: the declaration core, the background worker, the
  failure journal, « Relancer » / « Abandonner », the startup interruption
  (R1), the banner (Y1), the metric (M1); the plan and resolve HTTP routes
  give way to the worker.
- F -- `day-publication`: « À publier », the rewrite, the review guard,
  the replay refusal, one unpublished day per character (E1).
- G -- `player-day`: the player's day routes and page, INV-66 amended,
  G2 lifted, the ticket's ARCHITECTURE_DECISIONS entry.

## Dependency graph

Strict order: A -> B -> C -> D -> E -> F -> G.

- B needs A's column (C-01). C needs B's routes (C-06). D edits
  `routes/day.py` after B (B removes `_resolve_player_character` from it;
  D's anchors are written against B's result). E needs D's day-scoped
  chain (the worker runs it outside any request) and A's failure table.
  F needs E's declaration core (E1 lives in it) and A's publication
  columns. G needs F's publication (the player reads it) and E's core.
- C -> D is an order, not a dependency: C touches no file D touches. It is
  kept linear so every brief's Mini-RECON reads a single known state.

## RECON

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

### R-14 -- the declaration
Opened: `src/world_engine/cockpit/routes/day.py:140-196`;
`tooling/verify/checks/day_prompt_delivery.py:30-40, 436-466`.
Finding: `DayDeclareBody` (:154-158) holds `declared_action:
str = Field(max_length=MAX_DECLARATION_CHARS)`. `declare_day` (:161-196):
`missing_usages(DAY_CHAIN_USAGES, db)` -> 503 naming the seed script;
`_crud._world_id(db)`; `_get_or_open_session`; the resolver; `write_batch`;
`write_pass_play` (ValueError -> 422); add both, one commit, refresh;
returns `_day_dict` (`id, pass_play_id, day_number, status,
declared_action, created_at`, :140-151). R8 of `day_prompt_delivery.py`
finds `declare_day` in `routes/day.py` by name and requires its
`missing_usages(` call before its `write_batch(` call.
Consequence: E moves the declaration's body into a core shared by both
shells (C-11) and re-points R8 at it.

### R-15 -- the plan
Opened: `src/world_engine/cockpit/routes/day.py:453-608`;
`src/world_engine/quest_reads.py:270-280`.
Finding: `plan_day(batch_id, body: Optional[PlanDayBody] = None, db=...)`
under `@router.post("/api/day/{batch_id}/plan")` (:530-531):
`world_id = _crud._world_id(db)` (:551); `_load_plannable_day(batch_id,
world_id, db)` (404 unless the batch's session is in that world; 409
unless `submitted`, :494-513); the resolver (:553); `_extract_and_concord`
(LlmParseError -> 502); ambiguity -> `_record_refused_choices` (rollback,
write the choice records, commit) then 409 `"ambiguous mention(s),
resolve manually before planning: ..."`; `_write_declaration_rewrite`;
`write_day_mention_choices`; the pin branch `if body is not None and
body.quest_id:` (:581) -> `quest_reads.pinned_plan(body.quest_id,
character, db)` (LookupError -> 404, ValueError -> 409), else
`day_plan_select.select_plan(rendered, day_plans.open_plans(character, db),
db, world_id=world_id)` (502); then `_reconcile_and_finalize`,
`finalize_inquiry_day(world_id, ...)` or `emit_plan` + `_finalize_plan(
world_id, ...)`, each committing and moving `pass_play.status` to
`resolving`. `PlanDayBody` (:526-527) holds only `quest_id`.
`pinned_plan(quest_id, character, db)` raises `LookupError(f"quest
{quest_id!r} not found for this character")` or `ValueError("cette quête
est terminée : elle ne peut plus être avancée")`.
Consequence: D takes `world_id` from the day and the character from
`pass_play.character_id`; the pin is read from `pass_play.quest_id` in the
same `if` (C-07, Q1).

### R-16 -- the resolution
Opened: `src/world_engine/cockpit/routes/day.py:611-903`.
Finding: `resolve_day(batch_id, db=...)` under
`@router.post("/api/day/{batch_id}/resolve")` (:827-828): `world_id =
_crud._world_id(db)` (:851); `_load_resolvable_day` (404 unless in that
world; 409 unless `resolving` or `resolved` -- `resolved` is a replay,
:611-629); the resolver (:859); `_load_active_agenda`;
`_guard_no_pending_agenda_step_change` (BB1, 409); `resolve_steps`;
`_read_day_rewrite_concordance(pass_play, world_id, db)` (409 without a
trace); `freeze_facts`; `_narrate_and_judge` (LlmParseError -> rollback,
502); `_finalize_resolution` (:766-825): judge refused -> one history
entry, commit, `HTTPException(422, detail={"message": ..., "reason": ...,
"offending_words": ..., "prose": ...})`; accepted -> `batch.final_result =
prose`, `pass_play.status = "resolved"`, mutations emitted, one commit.
Consequence: D takes the world and the character from the day; F refuses a
published day in `_load_resolvable_day` (T1).

### R-17 -- every check that reads `routes/day.py` or Journée
Opened: the enumeration below; each check's rules at the lines cited.
Finding:
```
$ grep -ln 'routes/day.py\|"day.py"\|Journee.svelte\|journee.svelte.js\|"routes" / "day.py"\|routes" / "day' tooling/verify/checks/*.py
tooling/verify/checks/day_choice.py
tooling/verify/checks/day_feasibility.py
tooling/verify/checks/day_prompt_delivery.py
tooling/verify/checks/debts.py
tooling/verify/checks/day_mutations.py
tooling/verify/checks/day_narration.py
tooling/verify/checks/day_plan.py
tooling/verify/checks/day_rewrite.py
tooling/verify/checks/journee_inquiry.py
tooling/verify/checks/pipeline_wiring.py
tooling/verify/checks/quests.py
tooling/verify/checks/skill_progression.py
```
What each pins: `day_choice.py` W1-W4 (:505-560) -- `_extract_and_concord`
calls `choose(` once before `emit_germs(`; `plan_day` holds one `if
concordance_result.ambiguous:` whose body calls `_record_refused_choices(`
before `raise`, and calls `write_day_mention_choices(` once, after
`_write_declaration_rewrite(`; `_record_refused_choices` rolls back,
writes, commits. `day_plan.py` R15 (:765-775) -- `plan_day` calls
`day_plan_select.select_plan`. `day_rewrite.py` W6 -- `routes/day.py`
calls each `extract_*` exactly once. `day_narration.py` (:311-347,
:808-810) -- `_narrate_and_judge` (or `resolve_day`) calls the rewrite
pass once. `day_prompt_delivery.py` R8 (R-14). `day_feasibility.py` --
reads `DAY_ROUTE_FILE` and `day_plan_finalize.py` (R4: `feasibility_veto(`
in `_finalize_plan`). `day_mutations.py` R12 (:552-562) -- `resolve_day`
calls `_guard_no_pending_agenda_step_change`; R7 -- `Journee.svelte`
contains neither `agenda_id` nor `step_id`. `pipeline_wiring.py` R5
(:230-275) -- no PUT/PATCH/DELETE decorator in `routes/day.py`, at least
one GET/POST route, no `.history` / `injected_context`. `journee_inquiry.py`
JI7 (:357-363) -- `routes/day.py` within 1000 lines / 40 functions.
`quests.py` `_pin_branch_ok` (:720-731) -- the top-level `plan_day` holds
an `if` whose body calls `quest_reads.pinned_plan(` without `select_plan(`
and whose `else` calls `select_plan(`; QC3 (:835-846) -- `Journee.svelte`
holds `<QuestPanel` and `planDay(id, questState.pin)`,
`journee.svelte.js` holds `JSON.stringify({ quest_id: questId })`.
`debts.py` DD1 (:1012-1025) -- `Journee.svelte`'s `SUB_TABS` is exactly
Journée / Quêtes / Dettes, the Quêtes and Dettes divs verbatim, the Journée
div holds `<ServiceForm />` and `id="journee-declare-panel"`.
`skill_progression.py` D2 (:787-791) -- `Journee.svelte` holds
`account.gains.skill.produced`. No check calls the plan or resolve HTTP
route or `plan_day(` / `resolve_day(` as a function:
```
$ grep -n "/api/day/\|PlanDayBody\|plan_day(\|resolve_day(\|declare_day(" tooling/verify/checks/*.py
(no output)
```
Consequence: D keeps every pinned shape of `plan_day` / `resolve_day` (the
pin `if`, the ambiguity branch, the call order); D updates QC3 for the pin
at declaration; E removes the two decorators (R5 still finds the GET/POST
routes `declare_day`, `list_days`, `get_day`) and re-points R8; the
Journée edits keep DD1's, D2's and R7's tokens.

### R-18 -- where the chain reads the active world
Opened: the enumeration below; `src/world_engine/day_extract.py:49-157`;
`src/world_engine/day_feasibility.py:157-200`;
`src/world_engine/prompt_store.py:53-68`;
`src/world_engine/world_premise.py:78-127`;
`src/world_engine/schedule_reads.py:136-171`;
`src/world_engine/day_concordance.py:246-300, 365-385`;
`src/world_engine/day_plan.py:350-370`;
`src/world_engine/day_narration.py:150-190`; an import-closure walk of
`cockpit/routes/day.py` (stdlib `ast`, 84 modules).
Finding:
```
$ grep -rn "World.is_active\|_world_id(\|active_world_id\|premised_prompt(\|who_is_at(" src/world_engine/day_*.py src/world_engine/cockpit/day_*.py src/world_engine/quest_reads.py src/world_engine/schedule_reads.py
src/world_engine/day_concordance.py:252:            found.update(who_is_at(location_id, phase, db, is_present=True))
src/world_engine/day_concordance.py:291:            present.update(who_is_at(location_id, phase, db, is_present=True))
src/world_engine/day_extract.py:103:    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
src/world_engine/day_feasibility.py:183:    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
src/world_engine/day_narration.py:158:    version = premised_prompt(db, template)
src/world_engine/day_narration.py:185:    version = premised_prompt(db, template)
src/world_engine/schedule_reads.py:137:    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
src/world_engine/schedule_reads.py:153:def who_is_at(location_id: str, phase: str, db: Session, *, is_present: bool) -> list[str]:
src/world_engine/day_plan.py:369:    version = premised_prompt(db, template)
```
`_extract(usage, category, declaration, db)` (:102-145) reads the active
world for the template loader and for `world_frame(world)`;
`extract_places/persons/factions(declaration, db)` (:148-157) are its only
entries, called only from `routes/day.py:463-465`. `veto(budget_result,
character, declaration, db)` reads the active world at :183 for the same
two uses; its caller passes `character`. `premised_prompt(db, template, *,
entity_type=None)` calls `fill(..., entity_type=...)` without a world;
`fill` and `world_premise` already take `world_id: Optional[str] = None`
(None -> the active world, `world_premise.py:86-89`). `emit_plan` loads
its template by `character.world_id` (`day_plan.py:366`); `narrate` and
`rewrite` by `fact_sheet.world_id` (`day_narration.py:155, 182`).
`who_is_at` scopes to `_active_npc_ids(db)`, the active world's NPCs
(:136-146); `day_concordance._rung_presence` and `_cast_presence` call it
with a location of the day's world; its other caller is
`cockpit/crud/locations.py:420`. The closure walk reaches no other
active-world read that the chain calls (`draft_world.active_world_id` is
reached only through `prompt_registry` -> `entity_author`, never called by
the chain). Everything else of the chain derives its world from
`character.world_id` (`day_concordance.py:378-383`, `day_choice.py:279`,
`day_mutations.py:316`, `day_resolve.py:515`).
Consequence: D gives the day's world to the extraction (a keyword), the
feasibility (`character.world_id`), the three premise fills (a keyword of
`premised_prompt`) and the presence rung (a keyword of `who_is_at`); a
static check forbids an active-world read in the chain (C-08, INV-71). The
presence rung is not named by P1 but is the same defect (drafting
decision 4).

### R-19 -- the premise check counts call sites, not signatures
Opened: `tooling/verify/checks/world_premise.py:15-40, 93-110, 340-400`.
Finding: WP3 collects the `path::function` set holding a `premised_prompt(`
call and compares it to the literal `SWAPPED` (31 functions), and the set
holding `current_prompt(` to `STAYS`; WP2 calls `premised_prompt(db,
head)` with two positional arguments.
Consequence: a keyword `world_id` on `premised_prompt` and on its three day
calls changes neither set; WP2's call stays valid.

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

### R-21 -- the plan holds the write lock across its model calls
Opened: `src/world_engine/writes/pipeline.py:238-262`;
`src/world_engine/db.py:89-146`; `routes/day.py:574-605`.
Finding: `write_day_rewrite` does `db.add(rewrite); db.flush()` (:261-262);
`plan_day` calls it (through `_write_declaration_rewrite`) before
`select_plan`, `emit_plan` and the feasibility veto (model calls). The
engine runs WAL with explicit BEGIN and `busy_timeout=5000`
(`_SQLITE_BUSY_TIMEOUT_MS`, :109). A flushed write holds SQLite's write
lock until the commit.
Consequence: while a day plans, another writer waits up to 5 s, then fails
« database is locked ». Locked Y1: accept it, show « Journée en calcul… »
in the cockpit header while the worker runs (C-10's state route, E);
deferral Y2 (C-14).

### R-22 -- threads, startup and the checks
Opened: `src/world_engine/cockpit/browser_open.py:13, 50-62`;
`src/world_engine/cockpit/app.py:136-165, 262-287`; the enumeration below.
Finding: the one thread precedent is `threading.Thread(target=_run,
name="browser-opener", daemon=True)` then `.start()`. Startup hooks are
`@app.on_event("startup")` functions (:262, :269, :276), run in
registration order. No check enters a `TestClient` as a context manager,
so no check runs the startup hooks:
```
$ grep -n "with TestClient" tooling/verify/checks/*.py
(no output)
```
Routers are included by `app.include_router(_routes_<name>.router)` after
`from .routes import <name> as _routes_<name>` (:57-84, :136-165).
Consequence: E's worker starts from a new startup hook, after R1's sweep;
checks drive the worker's job body synchronously (C-10) and never start
the thread.

### R-23 -- the quest pin in Journée
Opened: `frontend/src/journee/quests.svelte.js:1-45`;
`frontend/src/journee/journee.svelte.js:1-135`;
`frontend/src/journee/Journee.svelte:1-263`.
Finding: `questState.pin` (:15) is the quest a planned day advances, ''
for « le jeu choisit »; `apply()` clears a pin that is no longer an open
quest. `planDay(id, questId)` posts `{quest_id}` when pinned (:74-90);
`resolveDay(id)` (:92-104); `submitDeclaration()` posts `{declared_action}`
(:106-125). `Journee.svelte` shows the pin `<select>` and « Émettre le
plan » for a `submitted` day, « Résoudre la journée » for a `resolving`
day (:127-143), and the account of a resolved day (:169-235).
Consequence: D moves the pin to the declaration panel; E removes the plan
and resolve buttons (the worker runs them) and adds the failure panel; F
adds the publish panel.

### R-24 -- abandoning a quest while a day runs on it
Opened: `src/world_engine/writes/quests.py:253-275`.
Finding: `abandon_refusal` refuses while a `pass_play` with that agenda is
`resolving`.
Consequence: a day `flagged` at the resolve stage still holds its agenda
(the plan was written): E widens the test to `resolving` or `flagged`.

### R-25 -- what « awaits in the queue »
Opened: `src/world_engine/cockpit/routes/mutations.py:476-500, 700-750`;
`src/world_engine/dashboard_metrics.py:349-350`;
`src/world_engine/models/pipeline.py:99-170`.
Finding: the review queue lists `status == "proposed"` rows of the active
world; a batch approval whose applier fails leaves the row `approved` with
an `[apply error]` note (« Needs attention », counted by the
`needs_attention` metric). `ProposedMutation.pass_play_id` ties a proposal
to its day (index `idx_mutation_passplay`).
Consequence: C1's guard counts the day's proposals at `proposed` or
`approved` (drafting decision 6).

### R-26 -- the dashboard registry
Opened: `src/world_engine/dashboard_metrics.py:1-80, 300-372`;
`tooling/verify/checks/dashboard_registry.py:1-36, 236-262`;
`frontend/src/creation/Dashboard.svelte:20-80`.
Finding: `Metric(key, title, question, watches, dated, compute)`;
`compute(db, scope) -> (list[Row], note)`; `Row(group, label, value,
of=None)`; `_in_worlds(column, scope)`, `_dated(column, scope)`; `METRICS`
(:330-358). DB2 forbids reading a JSON column in the module; DB3 compares
only the metrics named in its `EXPECTED` and requires every dated metric to
be empty after tomorrow. `Dashboard.svelte` renders any metric generically.
Consequence: E adds one dated metric reading `day_run_failure` only (C-13).

### R-27 -- G2
Opened: `src/world_engine/creation_check.py:40-53, 360-387`;
`tooling/verify/checks/creator_review.py:1-30, 136-153, 320-392`;
`tooling/verify/checks/draft_approval.py:30-46, 296-362, 430-460`; the
enumeration below.
Finding:
```
$ grep -rn "world_has_pc" src tooling/verify --include=*.py
src/world_engine/creation_check.py:52:    "world_has_pc",
src/world_engine/creation_check.py:385:        found.append(Violation("world_has_pc", None, "Ce monde a déjà un personnage joueur : l'approbation "
tooling/verify/checks/creator_review.py:27:   `world_has_pc` alone; Ana holding one -> `pc_exists, world_has_pc`.
tooling/verify/checks/creator_review.py:152:    "world_has_pc": "Ce monde a déjà un personnage joueur : l'approbation attend le sélecteur « PJ actif ».",
tooling/verify/checks/creator_review.py:350:        ("Bea holds a player character", lambda db, d: _add_pc(db, ids, "bea"), ["world_has_pc"]),
tooling/verify/checks/creator_review.py:351:        ("Ana holds a player character", lambda db, d: _add_pc(db, ids, "ana"), ["pc_exists", "world_has_pc"]),
tooling/verify/checks/draft_approval.py:40:   player character in the world (`world_has_pc`). After DA1, the approved
```
`REVIEW_VIOLATION_CODES` (:49-53) ends with `"world_has_pc"`; `check_review`
adds it at :381-386 (the `any_pc` query). CR1 asserts every code of
`REVIEW_VIOLATION_CODES` is reached. DA3's fourth case (« Bea holding a
player character », helpers :336-345, case :356) expects the 409 refusal and then deletes
Bea's PC; DA1 (:430-450; the assertion :442-445) asserts the world's player
characters are exactly Kael.
Consequence: G removes the code, its query and its message; CR1's two rows
read `[]` and `["pc_exists"]`; DA3 drops its fourth case; DA1 runs with
Bea's PC in the world and filters its PC assertion to Ana's profile -- the
proof that a second PC is approved.

### R-28 -- the player's door
Opened: `src/world_engine/cockpit/routes/player.py:1-192`;
`src/world_engine/perspective_view.py:112-124`;
`tooling/verify/checks/player_routes.py:1-60`;
`tooling/verify/checks/player_shell.py:1-60`;
`frontend/src/joueur/` (`JoueurApp.svelte`, `WorldPage.svelte` 90 lines,
`joueur.svelte.js` 217 lines).
Finding: `_open_world(world_id, db)` -> 404 `"Monde introuvable."` unless
`open_to_players`; `_player_profile(profile_id, db)` -> 404 `"Profil
introuvable."` unless an active `role='player'` user; `_own_character`
-> 404 `"Personnage introuvable."`; `player_character_of(db, world_id,
profile_id) -> Optional[(id, name)]` (active PC of that profile in that
world). PR8 applies to `routes/player.py` only (no `chat(`, `select(` on
`User`/`World`/`WorldLaw` only, none of `World.is_active`, `_world_id(`,
`write_usage_event`, `lore_selectors`; paths under `/api/joueur/`). PSH2:
every `fetch(`/`call(` URL literal under `frontend/src/joueur/` starts
with `/api/joueur/`; PSH3: no import leaves the folder. `joueur.svelte.js`
exports `call`, `postJson`, `putJson`; `joueurState.character` is `{id,
name}` or null (`loadCharacter`). `WorldPage.svelte` shows the world, the
creation button, « Mes savoirs ».
Consequence: G's routes sit in a new module with the same guards (imported
from `routes/player.py`); its page reuses `call` / `postJson`.

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

### R-37 -- a quest for a check's fixture
Opened: `tooling/verify/checks/quests.py:456-500`;
`src/world_engine/writes/quests.py:222-225, 253-285`.
Finding: `quests._qb_world(session) -> dict` builds an inactive world with
a PC (`ids["pc"]`), two NPCs, a faction, a place and an active agenda of
the PC, and commits; `quests._offer_kwargs(ids, **over) -> dict` gives
`write_quest_offer`'s keyword arguments (two steps, giver `ids["npc"]`),
any key overridable (`eligibility=None` drops the faction condition).
`accept_quest(db, *, offer, character) -> Quest` gives the character the
quest (its agenda born `paused`); `abandon_quest(db, *, quest)` moves the
agenda to `abandoned` (refused while a day is `resolving` on it, R-24).
Consequence: D's and F's checks build a real quest this way (the
`pass_play.quest_id` FK needs a real row) by importing the two helpers
from `quests.py`, never copying them.

## Contract sheet

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

### C-07 -- the day's world and character, the chain's keywords
Produced by: D   Consumed by: E, F
In `cockpit/routes/day.py`:
```
def _day_world(batch_id: str, db: Session) -> str
def _day_character(pass_play: PassPlay, db: Session) -> Character
```
`_day_world`: the `GameSession.world_id` of the batch's session (`Batch`
joined to `GameSession`); no row -> `HTTPException(404, f"day {batch_id!r}
not found")`. `_day_character`: `db.get(Character,
pass_play.character_id)`; None, or not `character_type == "player"` ->
`HTTPException(409, f"day {pass_play.id!r}'s character
{pass_play.character_id!r} is missing")`.
`plan_day(batch_id: str, db: Session) -> dict` and `resolve_day(batch_id:
str, db: Session) -> dict` (D keeps their `@router.post` decorators with
`db: Session = Depends(get_session)`; E removes the decorators and the
`Depends` default): `world_id = _day_world(batch_id, db)` replaces
`_crud._world_id(db)`; `character = _day_character(pass_play, db)`
replaces the resolver; the pin `if` reads `if pass_play.quest_id:` and
calls `quest_reads.pinned_plan(pass_play.quest_id, character, db)`.
`PlanDayBody` is gone. Every other statement of both functions is
unchanged.
Keywords: `day_extract.extract_places/extract_persons/extract_factions(
declaration, db, *, world_id: str)` -> `_extract(usage, category,
declaration, db, world_id)` loads `db.get(World, world_id)`;
`day_feasibility.veto` reads `db.get(World, character.world_id)`;
`prompt_store.premised_prompt(db, template, *, entity_type=None, world_id:
Optional[str] = None)` passes `world_id=world_id` to both `fill` calls;
`day_plan.emit_plan` passes `world_id=character.world_id`,
`day_narration.narrate` and `rewrite` pass `world_id=fact_sheet.world_id`;
`schedule_reads.who_is_at(location_id, phase, db, *, is_present: bool,
world_id: Optional[str] = None)` and `_active_npc_ids(db, world_id:
Optional[str] = None)` (None: the active world, as today);
`day_concordance._rung_presence` and `_cast_presence` pass
`world_id=ctx.world_id`.
Declaration (Q1): `DayDeclareBody` gains `quest_id: Optional[str] = None`;
`declare_day` validates a pin with `quest_reads.pinned_plan(quest_id,
character, db)` before any write (LookupError -> 404, ValueError -> 409,
each with `str(exc)`), and passes it to `write_pass_play(...,
quest_id=...)`; `write_pass_play` gains `quest_id: Optional[str] = None`,
stored as is.

### C-08 -- the day modules never read the active world
Produced by: D   Consumed by: E, F (their new modules must satisfy it)
The « day modules » are every file matching `src/world_engine/day_*.py`
and `src/world_engine/cockpit/day_*.py`, plus, in
`src/world_engine/cockpit/routes/day.py`, the functions `plan_day`,
`resolve_day`, `_day_world`, `_day_character`, `_load_plannable_day`,
`_load_resolvable_day`, `_extract_and_concord`,
`_write_declaration_rewrite`, `_record_refused_choices`,
`_load_active_agenda`, `_guard_no_pending_agenda_step_change`,
`_read_day_rewrite_concordance`, `_narrate_and_judge`,
`_finalize_resolution`. None of them holds the token `World.is_active`,
`_world_id(`, `active_world_id(`, `_player_character` or
`resolve_active_pc` (code tokens; strings and comments dropped). Every
`premised_prompt(` call in a day module passes the keyword `world_id`;
every `who_is_at(` call in `day_concordance.py` passes `world_id`; each
`extract_*(` call in `routes/day.py` passes `world_id`. A routed cockpit
handler of `routes/day.py` outside that list (`declare_day`, `list_days`,
`get_day`) acts for the active world and is not a day module.

### C-09 -- the day writers
Produced by: E (failure, reopen, abandon), F (publish)   Consumed by: E, F
Module `src/world_engine/writes/day_runs.py`, docstring first sentence:
« The writers of a day's run: its failures, its reopening, its abandonment
and its publication (TICKET-0128, L1, M1, Z1, C1, T1). » Commit-free;
never touches `pass_play.history`.
```
DAY_NOT_FLAGGED = "Cette journée n'est pas en échec."
def write_day_run_failure(db: Session, *, pass_play: PassPlay, world_id: str,
                          stage: str, code: str, reason: str) -> DayRunFailure
def reopen_day(db: Session, *, pass_play: PassPlay) -> str
def abandon_day(db: Session, *, pass_play: PassPlay) -> None
```
`write_day_run_failure`: `stage` in `DAY_RUN_STAGES` and `code` in
`DAY_RUN_FAILURE_CODES` else `ValueError`; `reason` stripped, cut to 2000
characters, `"—"` when empty; adds the row; `pass_play.status =
"flagged"`; adds the pass_play; returns the row.
`reopen_day`: `ValueError(DAY_NOT_FLAGGED)` unless `pass_play.status ==
"flagged"`; the latest failure (`day_run_reads.latest_failure`) gives the
stage; `"plan"` -> status `submitted`, `"resolve"` -> status `resolving`;
returns the stage.
`abandon_day`: `ValueError(DAY_NOT_FLAGGED)` unless `flagged`; status
`abandoned`.
F adds:
```
DAY_NOT_PUBLISHABLE = "Cette journée n'est pas à publier."
EMPTY_NARRATIVE = "Le récit publié est vide."
def publish_day(db: Session, *, pass_play: PassPlay, text: str) -> PassPlay
```
`publish_day`: `ValueError(DAY_NOT_PUBLISHABLE)` unless `status ==
"resolved"` and `published_at is None`; `text.strip()` empty ->
`ValueError(EMPTY_NARRATIVE)`; sets `published_text` (stripped),
`published_at = datetime.now(UTC)`; never touches `batch.final_result`.

### C-10 -- the day worker
Produced by: E   Consumed by: F, G (through C-11)
Module `src/world_engine/cockpit/day_runner.py`, docstring first sentence:
« One background worker plans then resolves each declared day, one at a
time, in arrival order; a failure is written, never silent (TICKET-0128,
B2, K1, S1, R1, L1). » It satisfies C-08. It imports
`cockpit/routes/day.py` only inside `run_day` (`from .routes import day as
_day`), never at module level.
```
INTERRUPTED_REASON = "Interrompue : le serveur s'est arrêté pendant la journée."
def failure_of(exc: BaseException) -> tuple[str, str]
def run_day(batch_id: str) -> Optional[str]
def enqueue_day(batch_id: str) -> None
def interrupt_stale_days() -> int
def start_day_runner() -> None
def running_day() -> Optional[str]
def queued_count() -> int
```
`failure_of`: an `HTTPException` gives a code by status -- 502
`model_failed`, 409 `blocked`, 422 `rejected`, any other 4xx `refused`,
anything else `crashed` -- and a reason: its `detail` when a string, its
`detail["message"]` when a dict holding one, else `str(detail)`; any other
exception gives `crashed` and `str(exc)` or its class name.
`run_day`: opens `Session(engine)`; reads the batch's `pass_play` (none ->
returns None); status `submitted` -> stage `plan`, calls
`_day.plan_day(batch_id, db)`; then re-reads the status (`db.expire_all()`)
and, when `resolving`, stage `resolve`, calls `_day.resolve_day(batch_id,
db)`; any other status -> returns None. On an exception: `db.rollback()`;
in a new `Session(engine)`, `write_day_run_failure(...)` with the day's
world (`batch -> session -> world`), the stage, `failure_of(exc)`; commit;
returns the code. Returns None on success. Sets the running batch id for
`running_day()` while it works, clears it in `finally`.
`enqueue_day`: puts the batch id on the module-level `_QUEUE: "queue.Queue[str]"`;
`queued_count()` is `_QUEUE.qsize()`.
`interrupt_stale_days`: every `pass_play` at `submitted` (stage `plan`) or
`resolving` (stage `resolve`), every world, gets
`write_day_run_failure(..., code="interrupted",
reason=INTERRUPTED_REASON)`; one commit; returns the count.
`start_day_runner`: idempotent; starts one
`threading.Thread(target=<loop>, name="day-runner", daemon=True)` whose
loop takes a batch id from the queue and calls `run_day`, logging (never
`print`) and continuing on any exception.
`cockpit/app.py` gains, after the last startup hook:
```
@app.on_event("startup")
def _start_day_runner_on_startup() -> None:
    interrupt_stale_days()
    start_day_runner()
```

### C-11 -- the declaration core
Produced by: E   Consumed by: F (E1), G
Module `src/world_engine/cockpit/day_declare.py`, docstring first
sentence: « A declared day, from either shell: written at once, then
handed to the day worker (TICKET-0128, K1). » Satisfies C-08 (it receives
its world).
```
def declare(db: Session, *, world_id: str, character: Character,
            declared_action: str, quest_id: Optional[str], changed_by: str) -> tuple[Batch, PassPlay]
```
In order: `missing_usages(DAY_CHAIN_USAGES, db)` -> the 503 of R-14,
verbatim; [F: the E1 guard, C-12]; the pin of C-07 (404 / 409); the
session (`_get_or_open_session(world_id, db)` imported from `routes/day.py`
inside the function); `write_batch(db, session_id=..., changed_by=changed_by)`;
`write_pass_play(...)` (ValueError -> 422); add both; one commit; refresh;
`enqueue_day(batch.id)`; returns `(batch, pass_play)`.
`routes/day.py::declare_day` becomes: `world_id = _crud._world_id(db)`;
`character = _crud._player_character(db, world_id)`; `batch, pass_play =
declare(db, world_id=world_id, character=character,
declared_action=body.declared_action, quest_id=body.quest_id,
changed_by="creator")`; `return _day_dict(batch, pass_play)`.

### C-12 -- the day reads
Produced by: E (failures, labels), F (unpublished, pending, to publish)
Consumed by: E, F, G
Module `src/world_engine/day_run_reads.py`, docstring first sentence:
« What the day's run looks like: its failures, what awaits publication,
what a character may still declare (TICKET-0128). » Reads only; satisfies
C-08.
```
STAGE_LABELS_FR = {"plan": "Plan", "resolve": "Résolution"}
CODE_LABELS_FR = {"model_failed": "Modèle indisponible ou réponse illisible",
                  "blocked": "Bloquée : quelque chose est à régler dans le monde",
                  "rejected": "Récit refusé par le juge", "refused": "Refusée",
                  "crashed": "Erreur inattendue", "interrupted": "Interrompue (serveur arrêté)"}
def latest_failure(db: Session, pass_play_id: str) -> Optional[DayRunFailure]
def failed_days(db: Session, world_id: str) -> list[dict]
```
`failed_days`: the world's `flagged` days, newest failure first, each
`{"batch_id", "day_number", "character_name", "declared_action", "stage",
"stage_label", "code", "code_label", "reason", "failed_at"}` from its
latest failure (`failed_at` ISO).
`latest_failure`: the day's failure with the greatest `created_at`, then
`id`.
F adds:
```
DAY_IN_PROGRESS = "Ce personnage a déjà une journée en cours : elle doit être publiée avant la suivante."
PENDING_REVIEW = "Des propositions de cette journée attendent encore ta revue."
def unpublished_day(db: Session, character_id: str) -> Optional[PassPlay]
def pending_proposals(db: Session, pass_play_id: str) -> int
def days_to_publish(db: Session, world_id: str) -> list[dict]
```
`unpublished_day`: the character's `pass_play` with `published_at IS NULL`
and `status != "abandoned"` (the oldest by `submitted_at`, then `id`), or
None (E1).
`pending_proposals`: `ProposedMutation` rows with that `pass_play_id` and
`status` in `("proposed", "approved")`.
`days_to_publish`: the world's days with `status == "resolved"` and
`published_at IS NULL`, oldest first, each `{"batch_id", "day_number",
"character_name", "declared_action", "narrator_text"
(batch.final_result), "pending_proposals"}`.
E1 (F): `declare` raises `HTTPException(409, DAY_IN_PROGRESS)` when
`unpublished_day(db, character.id)` is not None, before the pin check.

### C-13 -- the creator's day-run routes and the metric
Produced by: E (failures, relaunch, abandon, state, metric), F (to
publish, publish)   Consumed by: the Journée frontend (E, F), the header (E)
Module `src/world_engine/cockpit/routes/day_runs.py`, included in
`cockpit/app.py` after `_routes_day`. A batch outside the active world ->
404 `"Journée introuvable."`.
- `GET /api/day-runs/echecs` -> `failed_days(db, _crud._world_id(db))`.
- `POST /api/day-runs/{batch_id}/relancer` -> `reopen_day` (ValueError ->
  409 with its message), commit, `enqueue_day(batch_id)`, `{"ok": true,
  "stage": <stage>}`.
- `POST /api/day-runs/{batch_id}/abandonner` -> `abandon_day` (409 as
  above), commit, `{"ok": true}`.
- `GET /api/day-runs/etat` -> `{"running": None | {"batch_id",
  "day_number", "character_name", "world_name"}, "queued":
  queued_count()}` (every world: the worker is one).
F adds:
- `GET /api/day-runs/a-publier` -> `days_to_publish(db, world)`.
- `POST /api/day-runs/{batch_id}/publier` body `{"text": str | None}` ->
  `pending_proposals > 0` -> 409 `PENDING_REVIEW`; `publish_day(...,
  text=body.text if body.text is not None else (batch.final_result or
  ""))` (ValueError -> 409 for `DAY_NOT_PUBLISHABLE`, 422 for
  `EMPTY_NARRATIVE`); commit; `{"ok": true, "published_at": <iso>}`.
Metric (E), in `dashboard_metrics.py`: `Metric("day_run_failures",
"Chaîne de la journée", "Où la chaîne de la journée échoue-t-elle ?",
("B1", "B2"), True, _day_run_failures)`; `_day_run_failures(db, scope)`
reads `DayRunFailure.stage`, `.code` only, `_in_worlds(DayRunFailure.world_id,
scope)`, `_dated(DayRunFailure.created_at, scope)`; rows `Row(group=
STAGE_LABELS_FR[stage], label=CODE_LABELS_FR[code], value=n, of=<the
stage's total>)`, stages in `DAY_RUN_STAGES` order, codes in
`DAY_RUN_FAILURE_CODES` order, zero rows omitted; note « Chaque échec de la
chaîne, par étape et par raison ; B1 se réactive si les échecs sont
nombreux. »

### C-14 -- the player's day routes
Produced by: G   Consumed by: the player frontend (G)
Module `src/world_engine/cockpit/routes/player_day.py`, included in
`cockpit/app.py` after `_routes_player`. Guards imported from
`routes/player.py` (`_open_world`, `_player_profile`, `CHARACTER_NOT_FOUND`)
and `perspective_view.player_character_of`.
- `GET /api/joueur/journee?profile_id=&world_id=` -> `{"character_id": str
  | None, "can_declare": bool, "days": [{"day_number", "declared_action",
  "state", "text"}]}`. No character -> `{"character_id": None,
  "can_declare": False, "days": []}`. `days`: the character's days, newest
  declaration first; `state` is `"publiee"` when `published_at` is set,
  `"abandonnee"` when `abandoned`, `"en_cours"` when `submitted` or
  `resolving`, else `"en_attente"` (`flagged`, or `resolved` not
  published); `text` is `published_text` when `publiee`, else None.
  `can_declare` is `unpublished_day(...) is None`.
- `POST /api/joueur/journee/declarer` body `{"profile_id", "world_id",
  "declared_action"}` -> no own character -> 404 `CHARACTER_NOT_FOUND`;
  `declare(db, world_id=..., character=<own>, declared_action=...,
  quest_id=None, changed_by="player")`; 201 with the GET shape.
- Nothing else of a day reaches the player: no `batch.final_result`, no
  failure, no proposal, no account, no feasibility.

### C-15 -- the Journée state of the day runs
Produced by: E   Consumed by: F
`frontend/src/journee/dayRuns.svelte.js`: `export const dayRunsState =
$state({ failures: [], failuresError: '', busy: null, actionError: '' })`;
`loadFailures()` (GET `/api/day-runs/echecs`), `relaunch(batchId)`,
`abandon(batchId)` (POST, then `loadFailures()` and `loadDays()`); every
request through `api` of `../creation/sheetRequest.svelte.js` (INV-69).
F adds `toPublish: []`, `toPublishError: ''`, `drafts: {}` (batch id ->
edited text), `loadToPublish()` and `publish(batchId)` (POST with `{text:
drafts[batchId]}`, then reload both lists and the days).
`DAY_POLL_MS = 5000` is exported by `journee.svelte.js` (E) and by
`frontend/src/joueur/day.svelte.js` (G), each its own constant (PSH3: the
player shell imports nothing outside its folder).

## Gate output

### (a) Property trace
One line per property the lot asserts about existing code: property --
finding -- the declaring file opened.
- three resolvers, their refusals and bodies -- R-02 -- `crud/entities.py`,
  `routes/day.py`, `analyzer_transcript.py`
- 21 call sites, two `from .day import` lines, the `crud/__init__.py`
  re-export -- R-02 -- the grep (pasted) and each file
- the other 14 PC reads are legitimate -- R-03 -- each file at its line
- PR1 / PR2 of `pc_resolution.py` -- R-04 -- `pc_resolution.py`
- `World`'s columns, indexes, CHECK, imports -- R-05 -- `models/canon.py`
- the FK cycle is harmless, SET NULL on hard delete -- R-05 -- measured
  in a scratch copy (create_all, raw DELETE, four checks run)
- `PassPlay`'s columns, no status CHECK, `PASS_PLAY_STATUSES` -- R-06 --
  `models/pipeline.py`, `writes/pipeline.py`
- `pass_play` is not canon -- R-06 -- `canon_write_policy.txt:1-13`
- deletion is soft; only the cascade hard-deletes -- R-07 --
  `crud/entities.py`
- cascade lists, W1 / W3 rules, the fixture rows -- R-08 --
  `writes/worlds.py`, `world_cascade.py`
- the migration's pieces -- R-09 -- `migrate_v2_33_creator_review.py`
- doc header, sections, changelog form; `review_schema.py:271` pins v2.33
  -- R-10 -- `world-engine-schema.md`, the changelog, `review_schema.py`,
  `creation_schema.py`
- `world` is canon; its sanctioned writers; how the check resolves a table
  -- R-11 -- `canon_write_policy.txt`, `single_canon_write.py`
- `_shared.py` is a closed set; `_world_id`'s refusal; the re-export path
  -- R-12 -- `crud/_shared.py`, `crud/__init__.py`, `crud/entities.py`
- bootstrap shape and its `except`; legacy reads it once; the shell mirror;
  the header's select and cascade; the bridge census only shrinks; the
  legacy ratchet -- R-13 -- `routes/creator.py`, `legacy.html`,
  `serverState.svelte.js`, `Header.svelte`, `tabs.js`, `legacy_call.py`,
  `module_budget.py`
- the declaration's steps; R8's order rule -- R-14 -- `routes/day.py`,
  `day_prompt_delivery.py`
- the plan's world, resolver, pin `if`, refusals, commits; `pinned_plan`'s
  exceptions -- R-15 -- `routes/day.py`, `quest_reads.py`
- the resolution's world, replay, judge path -- R-16 -- `routes/day.py`
- what each of the 12 checks pins in `routes/day.py` / Journée; no check
  calls the routes -- R-17 -- each check's implementation (lines cited),
  two greps (pasted)
- the chain's active-world reads; `who_is_at`'s scope; template loaders by
  world; `fill` already takes a world -- R-18 -- `day_extract.py`,
  `day_feasibility.py`, `prompt_store.py`, `world_premise.py`,
  `schedule_reads.py`, `day_concordance.py`, `day_plan.py`,
  `day_narration.py`, the grep (pasted), the closure walk
- WP3 counts call sites -- R-19 -- `world_premise.py` (the check)
- line and function counts -- R-20 -- `wc -l` / `ast`, `module_budget.py`
- the plan flushes before its model calls; busy timeout 5000 -- R-21 --
  `writes/pipeline.py`, `db.py`, `routes/day.py`
- the thread precedent; startup hooks in order; no check runs them;
  router inclusion -- R-22 -- `browser_open.py`, `app.py`, the grep
  (pasted)
- the pin's state and the Journée functions -- R-23 --
  `quests.svelte.js`, `journee.svelte.js`, `Journee.svelte`
- `abandon_refusal` tests `resolving` -- R-24 -- `writes/quests.py`
- the queue's `proposed`, Needs attention's `approved` -- R-25 --
  `routes/mutations.py`, `dashboard_metrics.py`, `models/pipeline.py`
- `Metric` / `Row` / helpers; DB2 / DB3 -- R-26 -- `dashboard_metrics.py`,
  `dashboard_registry.py`, `Dashboard.svelte`
- G2's code, query, message; CR1 / DA3 / DA1 expectations -- R-27 --
  `creation_check.py`, `creator_review.py`, `draft_approval.py`, the grep
  (pasted)
- the player guards, `player_character_of`; PR8, PSH2, PSH3; the player
  store -- R-28 -- `routes/player.py`, `perspective_view.py`,
  `player_routes.py`, `player_shell.py`, `joueur.svelte.js`
- corpus budgets, id rule, rule-file front matter, INV-66's lines, the ADR
  footer -- R-29 -- `claude_md_contract.py`, `player-surface.md`,
  `CLAUDE.md`, `ARCHITECTURE_DECISIONS.md`
- name bans -- R-30 -- the five checks
- no new name exists yet -- R-31 -- the greps
- arrow floor, 15 s -- R-32 -- `pipeline_state.py`, `corpus_gate.py`
- map freshness, build freshness -- R-33 -- `file_map.py`,
  `frontend_build_fresh.py`
- no new JSON column -- R-34 -- `json_ui_boundary.py`
- the v2.33 DDL; the migration statements run -- R-36 -- `create_all` at
  `055b890`, `sqlite_master`, a raw run
- the quest helpers of `quests.py`; `accept_quest`, `abandon_quest` --
  R-37 -- `quests.py` (the check), `writes/quests.py`
- the fixture idiom -- R-35 -- `pc_resolution.py`, `draft_approval.py`,
  `player_routes.py`

### (b) Case tables

`resolve_active_pc` (C-02), PCs counted active only:

| active PCs | `world.active_pc_id` | result |
|---|---|---|
| 0 | any | `NoPlayerCharacter` (400 at the adapter) |
| 1 (P) | NULL | P |
| 1 (P) | P | P |
| 1 (P) | an inactive PC Q | P |
| 2 (P, Q) | NULL | `ActivePcUnchosen` (409) |
| 2 (P, Q) | P | P |
| 2 (P, Q) | an inactive PC R | `ActivePcUnchosen` (409) |
| any | world row missing | as if NULL |

`write_active_pc` (C-04): None -> cleared; an active PC of the world -> set;
a PC of another world, an NPC, an inactive PC, an unknown id -> ValueError,
nothing changed.

`failure_of` (C-10):

| exception | code | reason |
|---|---|---|
| HTTPException 502 | `model_failed` | detail |
| HTTPException 409 | `blocked` | detail |
| HTTPException 422, detail a dict with `message` | `rejected` | `detail["message"]` |
| HTTPException 422, detail a string | `rejected` | detail |
| HTTPException 400 / 404 | `refused` | detail |
| HTTPException 500 / 503 | `crashed` | detail |
| any other exception | `crashed` | `str(exc)` or the class name |

`run_day` by the day's status at entry (C-10):

| status | stage(s) run | on success | on exception |
|---|---|---|---|
| `submitted` | plan, then resolve if `resolving` | None | failure at the stage that raised, `flagged` |
| `resolving` | resolve | None | failure (`resolve`), `flagged` |
| `resolved`, `flagged`, `abandoned`, no day | none | None | -- |

R1 (`interrupt_stale_days`): `submitted` -> `plan`, `interrupted`;
`resolving` -> `resolve`, `interrupted`; any other status untouched.

`reopen_day` / `abandon_day` (C-09): `flagged` with a latest `plan`
failure -> `submitted`; with a latest `resolve` failure -> `resolving`;
`flagged` -> `abandoned`; any other status -> ValueError
(`DAY_NOT_FLAGGED`).

`publish_day` and the route (C-09, C-13):

| state | pending proposals | text | answer |
|---|---|---|---|
| `resolved`, not published | 0 | non-empty | 200, published |
| `resolved`, not published | 0 | given empty | 422 `EMPTY_NARRATIVE` |
| `resolved`, not published | 0 | None, narrator text present | 200, the narrator's text |
| `resolved`, not published | >= 1 (`proposed` or `approved`) | any | 409 `PENDING_REVIEW` |
| `resolved`, published | 0 | any | 409 `DAY_NOT_PUBLISHABLE` |
| any other status | 0 | any | 409 `DAY_NOT_PUBLISHABLE` |
| another world's batch | any | any | 404 |

E1 (`unpublished_day`, C-12): a character with no day, or only published
or abandoned days, may declare; a day `submitted`, `resolving`,
`resolved` unpublished or `flagged` blocks with 409 `DAY_IN_PROGRESS`.

The player's state of a day (C-14):

| `status` | `published_at` | `state` | `text` |
|---|---|---|---|
| any | set | `publiee` | `published_text` |
| `abandoned` | NULL | `abandonnee` | None |
| `submitted`, `resolving` | NULL | `en_cours` | None |
| `flagged`, `resolved` | NULL | `en_attente` | None |

`_load_resolvable_day` after F: `resolving` -> first resolve; `resolved`
not published -> replay (unchanged, no caller reaches it after E);
`resolved` published -> 409; other -> 409 (unchanged).

### (c) Enumerations
Pasted in their findings: the resolvers and their call sites (R-02); every
other PC read (R-03); the statuses' readers (R-06); the checks reading
`routes/day.py` or Journée and the absence of any route call (R-17); the
chain's active-world reads (R-18); the absence of `with TestClient` (R-22);
G2 (R-27); the new names (R-31).

### (d) Families
- The day writers (C-09) were written as a family -- one module, one
  status precondition shape (`ValueError` with a module constant), no
  commit -- before `write_day_run_failure`, `reopen_day`, `abandon_day`
  and `publish_day`; re-read after `publish_day`: each names its
  precondition, its status move and its constant.
- The day reads (C-12): each takes `(db, <id>)`, reads only, and returns a
  dict list or a row; re-read after `days_to_publish`.
- The creator's day-run routes (C-13): every path under `/api/day-runs/`,
  every batch scoped to the active world with the same 404, every
  ValueError mapped by its constant; re-read after `publier`.
- The schema family (C-01): every new column nullable, no JSON, the new
  table append-only; re-read after the migration.

### (e) Gates and the modules that satisfy them
Proposed:
- `day_schema.py` (A) -- satisfied by `models/canon.py`,
  `models/pipeline.py`, `writes/pipeline.py`, `writes/worlds.py`,
  `scripts/migrate_v2_34_player_day.py`. It needs the migration to run as
  a subprocess on a temp database (the `review_schema.py` RS3 idiom).
- `pc_resolution.py` (B, rewritten) -- `active_pc.py`, `crud/_shared.py`,
  `writes/active_pc.py`, `routes/active_pc.py`, `crud/entities.py`. PR2
  forbids `.first()` in `resolve_active_pc` and `world_player_characters`
  and any resolver body elsewhere: satisfied, the resolver lives in one
  module.
- `active_pc_selector.py` (C) -- `frontend/src/ActivePcSelector.svelte`,
  `frontend/src/lib/activePc.svelte.js`, `Header.svelte`, the build.
- `day_chain_world.py` (D) -- `routes/day.py`, `day_extract.py`,
  `day_feasibility.py`, `prompt_store.py`, `day_plan.py`,
  `day_narration.py`, `schedule_reads.py`, `day_concordance.py`. It forbids
  `World.is_active` in every `day_*.py`: `day_choice.py`,
  `day_feasibility.py`, `day_extract.py`, `day_plan.py`,
  `day_plan_select.py`, `day_narration.py`, `day_reconcile.py` spell
  `PromptTemplate.is_active` (a different token) -- the ban is on the
  exact token `World.is_active`, so they pass; E's and F's new modules
  (`cockpit/day_runner.py`, `cockpit/day_declare.py`, `day_run_reads.py`)
  take their world as a parameter or from the day (C-10, C-11, C-12).
- `day_runs.py` (E) -- `cockpit/day_runner.py`, `cockpit/day_declare.py`,
  `writes/day_runs.py`, `day_run_reads.py`, `routes/day_runs.py`,
  `dashboard_metrics.py`, `app.py`, the Journée files, the header banner.
  It drives `run_day` synchronously with `routes.day.plan_day` /
  `resolve_day` swapped by assignment (no thread, no model).
- `day_publication.py` (F) -- `writes/day_runs.py`, `day_run_reads.py`,
  `routes/day_runs.py`, `cockpit/day_declare.py`, `routes/day.py`
  (`_load_resolvable_day`, `get_day`), the Journée files.
- `player_journee.py` (G) -- `routes/player_day.py`, `joueur/day.svelte.js`,
  `joueur/PlayerDay.svelte`, `WorldPage.svelte`, `creation_check.py`,
  `.claude/rules/player-surface.md`.
Passed (existing gates each brief must keep green), with the module that
satisfies each after the brief: `world_cascade.py` (A: `writes/worlds.py`
and its fixture row), `review_schema.py` (A: relaxed),
`schema_version_agreement.py` / `schema_partition.py` (A: doc, constant,
changelog), `single_canon_write.py` (B: the policy lines),
`claude_md_contract.py` (B, D, G: the rule file and the root line),
`file_map.py` (every brief adding a module: the regenerated map),
`module_budget.py` (every brief: R-20), `day_choice.py`, `day_plan.py`,
`day_rewrite.py`, `day_narration.py`, `day_mutations.py`,
`journee_inquiry.py`, `pipeline_wiring.py` (D, E: `routes/day.py` keeps
their shapes), `quests.py` (D: QC3 rewritten for the pin at
declaration; `_pin_branch_ok` satisfied by the unchanged `if`),
`day_prompt_delivery.py` (E: R8 re-pointed at `cockpit/day_declare.py`),
`debts.py` DD1, `skill_progression.py` D2, `day_mutations.py` R7 (E, F:
their tokens kept in `Journee.svelte`), `dashboard_registry.py` (E: a
dated relational metric), `world_premise.py` (D: call sites unchanged),
`npc_schedule.py` (D: `who_is_at` keeps its keyword-only `is_present`),
`creator_review.py`, `draft_approval.py` (G: updated per R-27),
`player_routes.py`, `player_shell.py` (G: the new module and folder obey
PR8's tokens and PSH2 / PSH3), `frontend_build_fresh.py` (every frontend
brief: rebuilt), `legacy_call.py` (C: no new bridge call), `import_cycle.py`
(E: `day_runner` imports `routes.day` lazily), `undefined_names.py`.

## Amendments

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
