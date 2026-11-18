<!-- slug: day-runner -->
# BRIEF 0128-E — "The day runs in the background; a failure is written, listed and relaunched"

Lot: LOT-0128-player-day.md (authoritative on conflict)
Depends on: BRIEF-0128-D (C-07, C-08: the day-scoped chain),
BRIEF-0128-A (C-01: `day_run_failure`, `abandoned`), BRIEF-0128-C (the
header holds `<ActivePcSelector />`)

## Anchors to confirm (Mini-RECON)

By content (B and D moved lines of `routes/day.py`):
- `src/world_engine/cockpit/routes/day.py`: `plan_day(batch_id: str, db:
  Session = Depends(get_session))` under `@router.post("/api/day/{batch_id}/plan")`
  and `resolve_day(batch_id: str, db: Session = Depends(get_session))`
  under `@router.post("/api/day/{batch_id}/resolve")`; both start with
  `world_id = _day_world(batch_id, db)`; `declare_day` validates
  `body.quest_id` with `quest_reads.pinned_plan` and calls
  `missing_usages(` before `write_batch(`; `list_days` returns
  `[_day_dict(batch, pass_play) for batch, pass_play in rows]`;
  `_get_or_open_session(world_id, db)` exists.
- `src/world_engine/cockpit/app.py`: the last startup hook is
  `_check_frontend_build_on_startup` (:276-287 on `055b890`, + B's two
  lines above it); the routers include `_routes_active_pc` after
  `_routes_day` (B).
- `src/world_engine/writes/quests.py:260-261`: `abandon_refusal` tests
  `PassPlay.status == "resolving"`.
- `src/world_engine/dashboard_metrics.py`: `METRICS` ends with the
  `"germs"` entry.
- `tooling/verify/checks/day_prompt_delivery.py`: `check_guard_before_write_batch`
  finds `declare_day` in `DAY_ROUTE_FILE`.
- `tooling/verify/checks/day_chain_world.py` DW3 swaps
  `routes.day.missing_usages` (D).
- `frontend/src/journee/journee.svelte.js` exports `planDay(id)`,
  `resolveDay(id)`; `Journee.svelte` holds « Émettre le plan » and
  « Résoudre la journée »; `frontend/src/Header.svelte` holds
  `<ActivePcSelector />`.
- `grep -rnw "enqueue_day\|run_day\|day_runner\|day_declare\|day_run_reads\|day_runs\|DayFailures\|DayRunBanner\|dayRunsState" src tooling/verify frontend/src`
  answers nothing; `grep -nw "declare\|interrupt_stale_days\|start_day_runner" src/world_engine/cockpit/routes/day.py src/world_engine/cockpit/app.py`
  answers only the route path `@router.post("/api/day/declare")` and an
  `app.py` comment (« These models declare only ... ») -- no binding named
  `declare`.

Halt if any anchor has moved.

## Facts carried

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

## Contracts

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

## Context

D made the chain day-scoped. This brief makes it run by itself (B2): the
declaration answers at once and hands the day to one background worker
(K1, S1); a failure leaves a `day_run_failure` row and a `flagged` day
(L1), listed in Journée with its reason, « Relancer » and « Abandonner »
(M1, Z1); a server stopped mid-day leaves « interrompue » failures (R1);
the header says « Journée en calcul… » while the worker runs (Y1); « Suivi »
counts the failures (M1). The plan and resolve HTTP routes give way to the
worker; Journée loses its two buttons. Publication is F's.

## Scope IN

1. New `src/world_engine/writes/day_runs.py` per C-09 (E's part:
   `DAY_NOT_FLAGGED`, `write_day_run_failure`, `reopen_day`,
   `abandon_day`).
2. New `src/world_engine/day_run_reads.py` per C-12 (E's part:
   `STAGE_LABELS_FR`, `CODE_LABELS_FR`, `latest_failure`, `failed_days`).
3. New `src/world_engine/cockpit/day_runner.py` per C-10, with
   `logging.getLogger(__name__)`; `run_day` reads the day by
   `select(PassPlay).where(PassPlay.batch_id == batch_id)`, its world by
   `Batch` -> `GameSession.world_id`.
4. New `src/world_engine/cockpit/day_declare.py` per C-11: the body of
   `declare_day` (missing usages, the pin of D, `write_batch`,
   `write_pass_play`, the commit) moves there unchanged in substance, plus
   `enqueue_day(batch.id)` after the refresh. `routes/day.py::declare_day`
   becomes C-11's four lines; its docstring: « The creator declares a day
   for the active PC; the worker plans and resolves it (TICKET-0128, K1,
   B2). » Remove from `routes/day.py` the imports this leaves unused
   (`missing_usages`, `DAY_CHAIN_USAGES`, `write_batch`, `write_pass_play`
   when no other line names them -- grep each with `-nw` first).
5. `src/world_engine/cockpit/routes/day.py`:
   a. `plan_day` and `resolve_day` lose their `@router.post` decorators;
      their signatures become `(batch_id: str, db: Session) -> dict`;
      each docstring gains, first: « Run by the day worker
      (`cockpit/day_runner.py`), never by a request (TICKET-0128, K1,
      S1). »
   b. `list_days` returns `{**_day_dict(batch, pass_play),
      "character_name": <the day's character's Entity.name>}` (one join
      on `Entity.id == PassPlay.character_id`; order unchanged).
6. `src/world_engine/writes/quests.py::abandon_refusal`: the day test
   reads `PassPlay.status.in_(("resolving", "flagged"))`; the message is
   unchanged; the docstring gains « (or failed at its resolution,
   TICKET-0128) ».
7. New `src/world_engine/cockpit/routes/day_runs.py` per C-13 (E's part:
   `echecs`, `relancer`, `abandonner`, `etat`); docstring first sentence «
   The creator's view of the day worker: failed days, relaunch, abandon,
   what runs now (TICKET-0128, M1, Z1, Y1). » `cockpit/app.py`: import and
   `app.include_router(_routes_day_runs.router)` right after
   `_routes_active_pc`'s line.
8. `cockpit/app.py`: C-10's startup hook after
   `_check_frontend_build_on_startup`, importing `interrupt_stale_days`,
   `start_day_runner` from `.day_runner`; the module docstring's list of
   what lives here gains « the day worker's start (`day_runner`,
   TICKET-0128) ».
9. `src/world_engine/dashboard_metrics.py`: C-13's metric appended to
   `METRICS`; imports `DayRunFailure`, `DAY_RUN_STAGES`,
   `DAY_RUN_FAILURE_CODES` from `.models` and the labels from
   `.day_run_reads`.
10. `tooling/verify/checks/day_prompt_delivery.py` R8: reads
    `src/world_engine/cockpit/day_declare.py` and finds `declare` there
    (a constant `DAY_DECLARE_FILE`); messages and docstring say
    « `day_declare.declare` ». `tooling/verify/checks/day_chain_world.py`
    DW3 swaps `world_engine.cockpit.day_declare.missing_usages` and
    `world_engine.cockpit.day_declare.enqueue_day` (a recorder), both
    restored in `finally`.
11. Frontend, Journée (every request through `api`, INV-69):
    a. New `frontend/src/journee/dayRuns.svelte.js` per C-15 (E's part).
    b. New `frontend/src/journee/DayFailures.svelte`: a `queue-panel` «
       Journées en échec », one row per failure -- « Jour N — <PJ> »,
       `stage_label`, `code_label`, the reason, « Relancer », «
       Abandonner » (disabled while `dayRunsState.busy === batch_id`);
       « Aucune journée en échec. » when empty.
    c. `journee.svelte.js`: delete `planDay`, `resolveDay` and the state
       fields `planning`, `planError`, `resolving`, `resolveError`,
       `reconciliation`; `export const DAY_POLL_MS = 5000`; at the end of
       `loadDays`, while a listed day is `submitted` or `resolving`, one
       `setTimeout` (cleared before it is set again) reloads the days and
       the selected day's detail after `DAY_POLL_MS`.
    d. `Journee.svelte`: delete the plan and resolve buttons, their error
       lines, the local `plan` / `resolve` functions and the
       `reconciliation` note; a status label map `{submitted: 'plan en
       cours', resolving: 'résolution en cours', resolved: 'résolue',
       flagged: 'en échec', abandoned: 'abandonnée'}` used in the list and
       the detail title; each list row shows `d.character_name`;
       `<DayFailures />` right above `#journee-list-panel` in the « Journée
       » sub-tab; a `$effect` `void journeeState.days; loadFailures();`.
       Keep `<ServiceForm />`, `#journee-declare-panel`, `<QuestPanel`,
       `submitDeclaration(questState.pin)`, `account.gains.skill.produced`
       and the sub-tab divs verbatim (R-17).
12. Frontend, header: new `frontend/src/DayRunBanner.svelte` -- in
    `onMount`, an interval of 5000 ms (cleared in the returned cleanup)
    reads `/api/day-runs/etat` through `api`; when `running` is set it
    shows « Journée en calcul… (Jour N — <PJ>, <monde>) » and, when
    `queued > 0`, « + n en attente »; nothing otherwise; a failed read
    shows nothing. `Header.svelte` imports it and holds `<DayRunBanner />`
    right after `<ActivePcSelector />`.
13. `cd frontend && npm run build`; commit the output.
14. New check `tooling/verify/checks/day_runs.py`, first sentence « G1
    check for TICKET-0128 (BRIEF-0128-E) -- a declared day runs in the
    background; every failure is written, listed, relaunched or
    abandoned. », fresh database per R-35; the thread is never started;
    every swapped name is restored in `finally`:
    - **DR1** `failure_of` walks lot (b)'s table row by row.
    - **DR2** `run_day`, with `world_engine.cockpit.routes.day.plan_day` /
      `resolve_day` swapped for stubs, on a day of Bea in a world B that
      is not the active one: (a) the plan stub sets the day `resolving`
      and commits, the resolve stub sets it `resolved` and commits -> None,
      both stubs called with the batch id, no failure row; (b) the plan
      stub raises `HTTPException(409, "ambigu")` -> `"blocked"`, one row
      `(plan, blocked, "ambigu")` whose `world_id` is B, the day `flagged`,
      the resolve stub not called; (c) a `resolving` day whose resolve stub
      raises `HTTPException(422, detail={"message": "m", "reason": "r"})`
      -> `(resolve, rejected, "m")`; (d) the plan stub raises
      `RuntimeError("boom")` -> `(plan, crashed, "boom")`; (e) a
      `resolved` day -> None, no stub called; (f) a batch id with no day
      -> None.
    - **DR3** `interrupt_stale_days`: a `submitted` and a `resolving` day
      and a `resolved` one -> 2; rows `(plan, interrupted,
      INTERRUPTED_REASON)` and `(resolve, interrupted, ...)`; both
      `flagged`; the `resolved` day untouched; a second call -> 0.
    - **DR4** routes, `TestClient(app, base_url="http://127.0.0.1")`, the
      active world A: `GET /api/day-runs/echecs` -> exactly C-12's keys per
      item, newest failure first, French labels; `relancer` on a
      plan-stage failure -> 200 `{"ok": true, "stage": "plan"}`, the day
      `submitted`, `queued_count()` one more (the queue drained after);
      again -> 409 `DAY_NOT_FLAGGED`; on a resolve-stage failure -> the day
      `resolving`; `abandonner` -> 200, `abandoned`; a batch of world B ->
      404 « Journée introuvable. »; `GET /api/day-runs/etat` -> `{"running":
      None, "queued": <n>}`.
    - **DR5** the declaration: `day_declare.missing_usages` and
      `day_declare.enqueue_day` swapped (a recorder); `POST /api/day/declare`
      on A's only PC -> 200 at once, the day `submitted`, its batch id
      recorded once; the recorder not called on a 422 (empty
      declaration).
    - **DR6** `compute_metrics` with two `plan` failures (`blocked`,
      `crashed`) and one `resolve` failure in A: the `day_run_failures`
      rows are exactly `[("Plan", <blocked label>, 1, 2), ("Plan",
      <crashed label>, 1, 2), ("Résolution", <its label>, 1, 1)]`.
    - **DR7** static (code tokens): `plan_day` and `resolve_day` carry no
      decorator; `app.py`'s `_start_day_runner_on_startup` calls
      `interrupt_stale_days()` before `start_day_runner()`;
      `day_runner.py` holds exactly one `threading.Thread(` with
      `daemon=True` and `name="day-runner"`, no `print(`, and no
      module-level import naming `routes`; `writes/quests.py`'s
      `abandon_refusal` names `"flagged"`; `Journee.svelte` holds neither
      `planDay(` nor `resolveDay(`, holds `<DayFailures />`; `Header.svelte`
      holds `<DayRunBanner />`; a built asset carries « Journées en échec »
      and « Journée en calcul ».
    A rule not reached is a FAILURE.
15. `python tooling/glue/gen_file_map.py`.

## Scope OUT

- « À publier », the publication, the E1 guard, the replay refusal (F).
- The player's routes and page (G).
- Restarting a day automatically at startup (R2, rejected), one thread
  per day (S2, rejected), running the chain inside the declaration
  request (K2, rejected), the failure in `pass_play.history` (L2,
  rejected).
- Moving the plan's model calls out of its transaction (Y2, deferred).
- A replay button: no caller reaches `_load_resolvable_day`'s `resolved`
  branch after this brief (drafting decision 5).
- The legacy document.

## Invariants to defend

- **INV-71**: the new `cockpit/day_runner.py`, `cockpit/day_declare.py`
  and `day_run_reads.py` are day modules (C-08, `day_chain_world.py` DW1).
- **INV-20**: the reason is a text column, never JSON.
- **INV-69**: Journée's and the banner's requests go through `api`.
- **INV-55**: the new `$effect` assigns nothing it reads.
- **No silent failure** (B2's condition): every exception of `run_day`
  writes a row; the worker's loop never dies on one.

## Decision rights

STOP: an anchor that does not hold; a check of R-17 turning red;
`import_cycle.py` reporting a cycle through `day_runner`; a reason why
`run_day` cannot catch an exception of the chain (report it).
ADAPT: `routes/day.py` still needs one of the imports of Scope IN 4 ->
keep it; `failed_days` needs the character's name through a second query
-> write it so. Report each.
REPORT-ONLY: the plan's reconciliation note no longer shown in Journée
(it lived in the plan route's response).
> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_runs.py` -> PASS (DR1-DR7).
- [ ] `day_chain_world.py`, `day_prompt_delivery.py`, `pipeline_wiring.py`,
      `day_choice.py`, `day_plan.py`, `day_rewrite.py`, `day_narration.py`,
      `day_mutations.py`, `day_feasibility.py`, `journee_inquiry.py`,
      `quests.py`, `debts.py`, `skill_progression.py`,
      `dashboard_registry.py`, `import_cycle.py`, `undefined_names.py`,
      `module_budget.py`, `frontend_build_fresh.py`,
      `frontend_error_message.py`, `effect_self_write.py`,
      `active_pc_selector.py`, `file_map.py` -> PASS.
- [ ] `pipeline_state.py` / `corpus_gate.py` red only for the arrows of F
      and G.
- [ ] Live, test database (Ollama up): declare a day in Journée -> the
      answer is immediate, the header shows « Journée en calcul… », the
      day moves to `résolue` without a click. With Ollama stopped: the day
      lands in « Journées en échec » with its reason; « Relancer » after
      Ollama is back resolves it; « Abandonner » marks it `abandonnée`.
      Stop the cockpit while a day plans, start it again: the day is in
      « Journées en échec », « Interrompue (serveur arrêté) ».
- [ ] /review-step, then /close-step.

## Docs to update

None beyond the module docstrings (no rule, no schema). The ticket's
ARCHITECTURE_DECISIONS entry is G's.
