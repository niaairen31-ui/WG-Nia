<!-- slug: day-chain-world -->
# BRIEF 0128-D — "The day chain takes its world and its character from the day"

Lot: LOT-0128-player-day.md (authoritative on conflict)
Depends on: BRIEF-0128-B (C-05: `routes/day.py` without
`_resolve_player_character`), BRIEF-0128-A (C-01: `pass_play.quest_id`)

## Anchors to confirm (Mini-RECON)

Measured on `055b890`; B removed `_resolve_player_character` (:124-137 and its blank lines)
from `routes/day.py`, so its line numbers moved -- the anchors below are
by content.
- `src/world_engine/cockpit/routes/day.py`: no `def
  _resolve_player_character`; `class DayDeclareBody` holds only
  `declared_action`; `declare_day` calls `missing_usages(` before
  `write_batch(` and `character = _crud._player_character(db, world_id)`;
  `_extract_and_concord` spreads `*extract_places(pass_play.declared_action,
  db)`, `*extract_persons(...)`, `*extract_factions(...)`; `class
  PlanDayBody` holds only `quest_id`; `plan_day`'s first statements after
  its docstring are `world_id = _crud._world_id(db)`, `pass_play =
  _load_plannable_day(batch_id, world_id, db)`, `character =
  _crud._player_character(db, world_id)`; it holds `if body is not None and
  body.quest_id:` with `quest_reads.pinned_plan(body.quest_id, character,
  db)`; `resolve_day` holds `world_id = _crud._world_id(db)` and
  `character = _crud._player_character(db, world_id)`.
- `src/world_engine/day_extract.py:102-104` (`_extract` reads `World.is_active`),
  `:148-157` the three entries `(declaration: str, db: Session)`.
- `src/world_engine/day_feasibility.py:183-184` reads `World.is_active`.
- `src/world_engine/prompt_store.py:53-68` is `premised_prompt(db, template,
  *, entity_type=None)`.
- `src/world_engine/day_plan.py:369`, `day_narration.py:158` and `:185` are
  `version = premised_prompt(db, template)`.
- `src/world_engine/schedule_reads.py:136` `def _active_npc_ids(db:
  Session) -> list[str]:`, `:153` `def who_is_at(location_id: str, phase:
  str, db: Session, *, is_present: bool) -> list[str]:`.
- `src/world_engine/day_concordance.py:252` and `:291` call `who_is_at(
  location_id, phase, db, is_present=True)`.
- `src/world_engine/writes/pipeline.py:78-80` is `def write_pass_play(db:
  Session, *, batch_id: str, session_id: str, character_id: str,
  declared_action: str,) -> PassPlay:`.
- `frontend/src/journee/journee.svelte.js`: `planDay(id, questId)` posts
  `{ quest_id: questId }` when pinned; `submitDeclaration()` posts
  `JSON.stringify({ declared_action: text })`.
- `tooling/verify/checks/quests.py:835-846` is `check_qc3`.
- `.claude/rules/day-chain.md` holds INV-70 and four `paths:` globs (B).
- `grep -nw "_day_world\|_day_character" src/world_engine/cockpit/routes/day.py`
  answers nothing.

Halt if any anchor has moved.

## Facts carried

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

## Context

The plan and the resolution read the active world and the active PC
(R-15, R-16, R-18). Run in the background for a player whose world is
not the active one (K1), they would plan in the wrong world. P1: the
chain takes its world from the day (`batch -> session -> world`) and its
character from `pass_play.character_id`, and hands that world to every
part that used to look up the active one. Q1: the quest pin is chosen
with the declaration and stored on the day. The two routes keep working
as before from Journée until E hands them to the worker.

## Scope IN

1. `src/world_engine/cockpit/routes/day.py`:
   a. C-07's `_day_world` and `_day_character`, right after
      `_get_or_open_session` and before `_day_dict`, each with a one-line
      docstring naming P1.
   b. `plan_day`: signature `plan_day(batch_id: str, db: Session =
      Depends(get_session)) -> dict` (decorator kept); `world_id =
      _day_world(batch_id, db)`; `pass_play = _load_plannable_day(batch_id,
      world_id, db)`; `character = _day_character(pass_play, db)`; the pin
      `if pass_play.quest_id:` calling
      `quest_reads.pinned_plan(pass_play.quest_id, character, db)` (same
      `try` / `except`, same status codes); the docstring's « the batch
      must belong to the active world » becomes « the world is the day's
      own (`_day_world`, P1) » and its O1 sentence « a `quest_id` pins the
      day » becomes « the day's `quest_id`, chosen at the declaration
      (Q1), pins it ». Delete `class PlanDayBody`.
   c. `resolve_day`: `world_id = _day_world(batch_id, db)`; `character =
      _day_character(pass_play, db)` (after `pass_play` is read); docstring
      « the batch must belong to the active world » -> « the world is the
      day's own (P1) ». Nothing else in either function moves (R-17).
   d. `_extract_and_concord`: each `extract_*(pass_play.declared_action,
      db)` call gains `world_id=character.world_id`.
   e. Q1, declaration: `DayDeclareBody` gains `quest_id: Optional[str] =
      None` with a comment « Q1 (TICKET-0128): the quest this day advances,
      chosen with the declaration; None lets the day choose. »;
      `declare_day`, after `character = ...` and before `write_batch(`:
      ```
      if body.quest_id:
          try:
              quest_reads.pinned_plan(body.quest_id, character, db)
          except (LookupError, ValueError) as exc:
              raise HTTPException(status_code=404 if isinstance(exc, LookupError) else 409,
                                  detail=str(exc)) from exc
      ```
      and `write_pass_play(..., quest_id=body.quest_id or None)`.
2. `src/world_engine/writes/pipeline.py::write_pass_play`: keyword
   `quest_id: Optional[str] = None`, passed to `PassPlay(quest_id=quest_id)`;
   docstring: « `quest_id` is the quest the day was pinned to at its
   declaration (Q1), stored as given: the caller validated it. »
3. `src/world_engine/day_extract.py`: `_extract(usage, category,
   declaration, db, world_id)` with `world = db.get(World, world_id)`
   replacing the active-world query (`world_id` keeps feeding
   `_load_extract_template`); the three entries take `(declaration: str,
   db: Session, *, world_id: str)` and pass it. Module docstring gains « The
   world is the day's own, given by the caller (TICKET-0128, P1). »
4. `src/world_engine/day_feasibility.py::veto`: `world = db.get(World,
   character.world_id)`; `world_id = character.world_id`.
5. `src/world_engine/prompt_store.py::premised_prompt`: keyword `world_id:
   Optional[str] = None`, passed as `world_id=world_id` to both `fill`
   calls; docstring: « `world_id` names the world whose premise is filled;
   None keeps the active world (TICKET-0128, P1). »
6. `day_plan.py:369` -> `premised_prompt(db, template,
   world_id=character.world_id)`; `day_narration.py:158` and `:185` ->
   `premised_prompt(db, template, world_id=fact_sheet.world_id)`.
7. `src/world_engine/schedule_reads.py`: `_active_npc_ids(db: Session,
   world_id: Optional[str] = None)` -- `world_id` given: that world, else
   the active world as today; `who_is_at(location_id, phase, db, *,
   is_present: bool, world_id: Optional[str] = None)` passes it;
   `unresolved_npcs` unchanged. `day_concordance.py:252` and `:291` pass
   `world_id=ctx.world_id`.
8. `.claude/rules/day-chain.md`: `paths:` gains `"src/world_engine/day_*.py"`
   and `"src/world_engine/cockpit/day_*.py"`; after INV-70:
   ```
   - **INV-71** The day chain takes its world and its character from the
     day (`batch -> session -> world`, `pass_play.character_id`), never
     from the active world nor the active player character; the premise,
     the extraction, the feasibility and the presence rung receive that
     world. -- enforced by `day_chain_world.py`
   ```
9. Frontend:
   a. `frontend/src/journee/journee.svelte.js`: `submitDeclaration(questId)`
      posts `JSON.stringify({ declared_action: text, quest_id: questId || null })`;
      `planDay(id)` posts with no body (`{ method: 'POST' }`).
   b. `frontend/src/journee/Journee.svelte`: the `quest-pin` `<label>` and
      its `<select bind:value={questState.pin}>` move from the `submitted`
      day's block into `#journee-declare-panel`, above « Déclarer », shown
      when `openQuests().length > 0`, disabled while
      `journeeState.submitting`; « Déclarer » calls
      `submitDeclaration(questState.pin)`; the local `plan(id)` calls
      `planDay(id)`; after a successful declaration `questState.pin = ''`
      (in `Journee.svelte`, after the awaited call). The comment of
      `quests.svelte.js:15` reads « O1, Q1: the quest_id the next declared
      day advances, '' = the day chooses ».
   c. `cd frontend && npm run build`; commit the output.
10. `tooling/verify/checks/quests.py::check_qc3` (and the docstring's QC3):
    `Journee.svelte` holds `<QuestPanel` and
    `submitDeclaration(questState.pin)`; `journee.svelte.js` holds
    `quest_id: questId || null`. `_pin_branch_ok` is unchanged (the
    `if pass_play.quest_id:` keeps its shape).
11. New check `tooling/verify/checks/day_chain_world.py`, first sentence «
    G1 check for TICKET-0128 (BRIEF-0128-D) -- the day chain takes its
    world and its character from the day, never from the active world
    (INV-71). », fresh database per R-35:
    - **DW1** static, code tokens (strings and comments dropped): C-08
      exactly -- the day modules (the two globs, at least 16 files, plus
      the 14 named functions of `routes/day.py`, each found) hold none of
      the five tokens; every `premised_prompt(` call in a day module
      passes `world_id=`; both `who_is_at(` calls of `day_concordance.py`
      pass `world_id=`; the three `extract_*(` calls of `routes/day.py`
      pass `world_id=`. Zero files or a function not found is a FAILURE.
    - **DW2** fixture: world A active (one PC « Ana », description « A »),
      world B inactive (description « Monde B », PC « Bea », NPC « Garde »
      with a schedule row or a gathering placing him at B's place « Port »
      -- whichever `where_is` resolves with `is_present=True`), a session,
      batch and day of Bea in B. `_day_world(<B's batch>, db)` == B;
      unknown batch -> 404; `_day_character(<the day>, db)` is Bea; a day
      whose `character_id` is Garde -> 409. A `day_plan` head seeded with
      `world_premise._seed_head(db, "day_plan", "{world_premise}X")`
      (imported from the check `world_premise.py`): `premised_prompt(db,
      head, world_id=B)` holds « Monde B » and not « A »; `premised_prompt(db,
      head)` holds A's. `who_is_at(<Port>, <phase>, db, is_present=True,
      world_id=B)` holds Garde; without `world_id` it does not.
    - **DW3** the pin at the declaration, `TestClient(app,
      base_url="http://127.0.0.1")`, `routes.day.missing_usages` swapped for
      `lambda *a, **k: []` and restored in `finally`, on the world of
      `quests._qb_world` made active (its PC the only one), an offer
      written with `write_quest_offer(**quests._offer_kwargs(ids,
      eligibility=None))` and accepted by the PC (R-37): `POST
      /api/day/declare` with that quest -> 200 and the day's `quest_id` is
      it; with an unknown quest id -> 404 and no new day; after
      `abandon_quest` -> 409 « cette quête est terminée : elle ne peut plus
      être avancée » and no new day; with no `quest_id` -> 200, `quest_id`
      NULL.
    A rule not reached is a FAILURE.
12. `python tooling/glue/gen_file_map.py`.

## Scope OUT

- Removing the plan / resolve HTTP routes and the Journée buttons, the
  worker, the declaration core (E).
- `/api/days`, `get_day` and `declare_day`'s own world: they act for the
  active world (cockpit), C-08's last sentence.
- Moving the model calls of the plan out of its write transaction (Y2,
  deferred, R-21).
- `unresolved_npcs` and `crud/locations.py`'s readers (unchanged: the
  active world).
- Any change to `select_plan`, `emit_plan`, `narrate`, the concordance
  rungs other than the presence world, or a prompt text.
- P2 (advance only if the player's world is active, rejected).

## Invariants to defend

- **INV-71** (new, this brief).
- **INV-48** (a stored prompt version is never rewritten): the premise is
  filled at call time; `world_premise.py` WP2 stays green.
- The shapes the 12 checks of R-17 pin in `routes/day.py` and Journée.

## Decision rights

STOP: an anchor that does not hold; a check of R-17 turning red; a day
module that reads the active world in a way C-08 does not list.
ADAPT: Garde cannot be placed by a schedule row in DW2 -> place him by
an open gathering at Port (`where_is` precedence), report which; a line of
the rule file passes 100 characters -> re-wrap. Report each.
REPORT-ONLY: a reader of `premised_prompt` outside the day modules that
would also benefit from a world (not in this ticket).
> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_chain_world.py` -> PASS (DW1-DW3).
- [ ] `quests.py`, `day_choice.py`, `day_plan.py`, `day_rewrite.py`,
      `day_narration.py`, `day_prompt_delivery.py`, `day_feasibility.py`,
      `day_mutations.py`, `journee_inquiry.py`, `pipeline_wiring.py`,
      `world_premise.py`, `npc_schedule.py`, `day_concordance.py`,
      `claude_md_contract.py` (« 71 invariants »), `module_budget.py`,
      `frontend_build_fresh.py`, `debts.py`, `skill_progression.py`,
      `file_map.py` -> PASS.
- [ ] `pipeline_state.py` / `corpus_gate.py` red only for the arrows of E,
      F, G.
- [ ] Live, test database: in Journée, pin a quest in the declaration
      panel, declare, « Émettre le plan », « Résoudre la journée »: the day
      advances that quest, as before.
- [ ] /review-step, then /close-step.

## Docs to update

`.claude/rules/day-chain.md` (Scope IN 8). No schema change (A added the
column).
