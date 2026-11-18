<!-- slug: day-publication -->
# BRIEF 0128-F — "The creator publishes a day; one unpublished day per character"

Lot: LOT-0128-player-day.md (authoritative on conflict)
Depends on: BRIEF-0128-E (C-09, C-11, C-12, C-13, C-15: the writers, the
declaration core, the reads, the routes, the Journée state),
BRIEF-0128-A (C-01: `published_text`, `published_at`)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/writes/day_runs.py` defines `DAY_NOT_FLAGGED`,
  `write_day_run_failure`, `reopen_day`, `abandon_day` and no
  `publish_day` (E).
- `src/world_engine/day_run_reads.py` defines `STAGE_LABELS_FR`,
  `CODE_LABELS_FR`, `latest_failure`, `failed_days` and no
  `unpublished_day` (E).
- `src/world_engine/cockpit/day_declare.py::declare` calls
  `missing_usages(` then the pin check then `write_batch(` (E).
- `src/world_engine/cockpit/routes/day_runs.py` holds `echecs`,
  `relancer`, `abandonner`, `etat` (E).
- `src/world_engine/cockpit/routes/day.py`: `_load_resolvable_day`
  accepts `resolving` and `resolved`; `get_day` ends with `if
  pass_play.status == "resolved": result["account"] = ...; return result`;
  `_day_dict` returns the six keys of R-14.
- `frontend/src/journee/dayRuns.svelte.js` exports `dayRunsState`,
  `loadFailures`, `relaunch`, `abandon` (E); `Journee.svelte` holds
  `<DayFailures />` and the status label map (E).
- `grep -rnw "publish_day\|days_to_publish\|pending_proposals\|unpublished_day\|DayPublish" src tooling/verify frontend/src`
  answers nothing.

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

E runs the day and records its failures. A resolved day now waits for the
creator: she reads it in « À publier », may rewrite the narrative (C′2),
and publishes it once no proposal of that day awaits her review (C1). A
published day is never replayed (T1). A character declares his next day
only once the previous one is published or abandoned (E1). The player
reads the published text in G.

## Scope IN

1. `src/world_engine/writes/day_runs.py`: C-09's F part (`DAY_NOT_PUBLISHABLE`,
   `EMPTY_NARRATIVE`, `publish_day`).
2. `src/world_engine/day_run_reads.py`: C-12's F part (`DAY_IN_PROGRESS`,
   `PENDING_REVIEW`, `unpublished_day`, `pending_proposals`,
   `days_to_publish`).
3. `src/world_engine/cockpit/day_declare.py::declare`: right after the
   `missing_usages` refusal and before the pin check, E1:
   `if unpublished_day(db, character.id) is not None: raise
   HTTPException(status_code=409, detail=DAY_IN_PROGRESS)`; the docstring
   gains « E1: one unpublished day per character. »
4. `src/world_engine/cockpit/routes/day.py`:
   a. `_load_resolvable_day`: after the status test, `if
      pass_play.published_at is not None: raise HTTPException(409,
      f"day {batch_id!r} is published and cannot be replayed")` (T1).
   b. `_day_dict` gains `"published_at": pass_play.published_at.isoformat()
      if pass_play.published_at else None`.
   c. `get_day` adds `result["published_text"] = pass_play.published_text`.
5. `src/world_engine/cockpit/routes/day_runs.py`: C-13's F part
   (`a-publier`, `publier`, a pydantic `PublishBody(text: Optional[str] =
   None)`); the batch's 404 as in E's routes.
6. Frontend (every request through `api`, INV-69):
   a. `dayRuns.svelte.js`: C-15's F part. `loadToPublish()` keeps an
      existing `drafts[batch_id]` and fills a missing one with
      `narrator_text || ''`.
   b. New `frontend/src/journee/DayPublish.svelte`: a `queue-panel` « À
      publier », one block per day -- « Jour N — <PJ> », the declaration,
      a `<textarea>` bound to `dayRunsState.drafts[batch_id]` (rows 8),
      when `pending_proposals > 0` the line « N proposition(s) de cette
      journée à revoir d'abord » and « Publier » disabled; « Publier »
      disabled too while the text is empty or `busy`; a hint « Le texte du
      narrateur reste gardé ; le joueur lira ce texte-ci. »; « Rien à
      publier. » when empty.
   c. `Journee.svelte`: `<DayPublish />` right after `<DayFailures />`;
      the failures `$effect` also calls `loadToPublish()`; the status label
      of a day reads `'publiée'` when `published_at` is set; the detail of
      a published day shows « Récit publié » with
      `journeeState.detail.published_text` above the account.
   d. `cd frontend && npm run build`; commit the output.
7. New check `tooling/verify/checks/day_publication.py`, first sentence «
   G1 check for TICKET-0128 (BRIEF-0128-F) -- a resolved day is published
   by the creator once its proposals are reviewed; one unpublished day per
   character; a published day is never replayed. », fresh database per
   R-35, swapped names restored in `finally`:
   - **DP1** `publish_day` walks lot (b)'s writer rows: a `resolved`
     unpublished day with « Mon texte » -> `published_text` « Mon texte »,
     `published_at` set, `batch.final_result` unchanged; with « » ->
     `EMPTY_NARRATIVE`; published again -> `DAY_NOT_PUBLISHABLE`; a
     `flagged` day -> `DAY_NOT_PUBLISHABLE`; it never commits.
   - **DP2** routes, `TestClient(app, base_url="http://127.0.0.1")`, the
     active world: `GET /api/day-runs/a-publier` -> exactly C-12's keys,
     oldest first, `narrator_text` the batch's `final_result`; a day with
     one proposal at `proposed` -> `publier` 409 `PENDING_REVIEW`; at
     `approved` -> 409; once `applied` or `rejected` -> `publier` with
     `{"text": "  Réécrit  "}` -> 200, `published_text` « Réécrit »;
     another day with `{"text": null}` -> the narrator's text;
     `{"text": ""}` -> 422 `EMPTY_NARRATIVE`; a published day -> 409
     `DAY_NOT_PUBLISHABLE`; another world's batch -> 404; `GET
     /api/day/{id}` of the published day holds `published_text` and
     `published_at`.
   - **DP3** E1, `POST /api/day/declare` with `day_declare.missing_usages`
     and `day_declare.enqueue_day` swapped: a PC with a `resolved`
     unpublished day -> 409 `DAY_IN_PROGRESS`, no new day; with a
     `flagged` day -> 409; with only published and `abandoned` days ->
     200.
   - **DP4** T1: `_load_resolvable_day` on a published `resolved` day ->
     409 « ... is published and cannot be replayed »; on an unpublished
     `resolved` day -> returns it.
   - **DP5** static: `DayPublish.svelte` holds « À publier » and
     `publish(`; `Journee.svelte` holds `<DayPublish />` and
     `published_text`; a built asset carries « À publier ».
   A rule not reached is a FAILURE.
8. `python tooling/glue/gen_file_map.py` (the new check).

## Scope OUT

- The player's page and routes (G).
- Showing the gains to the player (D2, rejected for now).
- Publishing without review (C2, rejected) or showing the narrative as
  soon as it resolves (C3, rejected); publishing as is with no rewrite
  (C′1, rejected).
- A `day_publication` table (T2, rejected); editing a published text.
- Declaring freely (E2, rejected).

## Invariants to defend

- **History is sacred**: `batch.final_result` (the narrator's text) is never
  written by the publication (C′2); `published_at` is written once.
- **INV-20**: the published text is a column.
- **INV-71**: `day_run_reads.py` stays a day module (no active-world read).
- **INV-69**, **INV-55** as in E.

## Decision rights

STOP: an anchor that does not hold; a proposal status other than
`proposed`, `approved`, `applied`, `rejected` found in the queue's code
(R-25 names those four).
ADAPT: the `textarea` binding to a keyed `$state` entry needs a local
copy in Svelte 5 -> keep a component-local `$state` per row and write it
back on input; report it.
REPORT-ONLY: published days whose `published_text` is NULL (W1 days whose
narrator text was NULL).
> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/day_publication.py` -> PASS (DP1-DP5).
- [ ] `day_runs.py`, `day_chain_world.py`, `day_prompt_delivery.py`,
      `pipeline_wiring.py`, `day_mutations.py`, `quests.py`, `debts.py`,
      `skill_progression.py`, `module_budget.py`,
      `frontend_build_fresh.py`, `frontend_error_message.py`,
      `effect_self_write.py`, `file_map.py` -> PASS.
- [ ] `pipeline_state.py` / `corpus_gate.py` red only for G's arrow.
- [ ] Live, test database: a resolved day appears in « À publier » with
      its pending count; after the review queue is cleared, rewrite a
      sentence and « Publier »: the day reads `publiée`, its detail shows
      the rewritten text; declaring a second day before publishing is
      refused with « Ce personnage a déjà une journée en cours... ».
- [ ] /review-step, then /close-step.

## Docs to update

None beyond docstrings. The ticket's ARCHITECTURE_DECISIONS entry is G's.
