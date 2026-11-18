<!-- slug: player-day -->
# BRIEF 0128-G — "The player lives his days; a second player character is approved"

Lot: LOT-0128-player-day.md (authoritative on conflict)
Depends on: BRIEF-0128-F (C-12: `unpublished_day`; the publication),
BRIEF-0128-E (C-11: `declare`), BRIEF-0128-B (C-02: the active PC, which
makes G2 obsolete)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/cockpit/day_declare.py::declare` refuses with
  `DAY_IN_PROGRESS` before the pin (F); `src/world_engine/day_run_reads.py`
  defines `unpublished_day` (F).
- `src/world_engine/cockpit/routes/player.py` defines `_open_world`,
  `_player_profile`, `CHARACTER_NOT_FOUND = "Personnage introuvable."`
  (:33-35, :77-96); `src/world_engine/perspective_view.py:112` is
  `player_character_of`.
- `src/world_engine/cockpit/app.py`: `app.include_router(_routes_player.router)`.
- `src/world_engine/creation_check.py:49-53` is `REVIEW_VIOLATION_CODES`
  ending with `"world_has_pc",`; `:381-386` the `any_pc` query and its
  violation.
- `tooling/verify/checks/creator_review.py:27`, `:152`, `:350-351` and
  `tooling/verify/checks/draft_approval.py:37-41` (DA3's docstring),
  `:336-345` (`bea_pc`, `no_bea_pc`), `:356` (the case), `:442-445` (DA1's
  PC assertion).
- `.claude/rules/player-surface.md:21-34` is INV-66, ending `--
  enforced by \`perspective_isolation.py\`, \`player_routes.py\`,` /
  `\`player_shell.py\`, \`creation_designer.py\`, \`player_creation.py\`,` /
  `\`character_perspective.py\``.
- `frontend/src/joueur/WorldPage.svelte` (90 lines) holds `{#if
  characterState.open}<CharacterCreation />...` then `<section
  class="savoir">`; `joueur.svelte.js` exports `call`, `postJson`.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank
  line, `*Co-built with Claude, June 2026.*`.
- `grep -rnw "player_day\|PlayerDay\|loadPlayerDays\|declarePlayerDay" src tooling/verify frontend/src`
  answers nothing.

Halt if any anchor has moved.

## Facts carried

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

## Contracts

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

## Context

The player declares what his character does, the creator validates in her
review and publishes, then he reads the narrative (G1). This brief gives
him that page in `/jouer` and its routes. The published narrative is the
one text he reads outside a perspective, because she read it (D1, INV-66
amended). With the active PC in place, a world may approve a second
player character: G2 falls.

## Scope IN

1. New `src/world_engine/cockpit/routes/player_day.py` per C-14, docstring
   first sentence « The player's days (TICKET-0128, BRIEF-0128-G; G1, D1,
   E1): he declares, the worker runs, the creator publishes, he reads the
   published narrative only. »; pydantic `DayDeclareBody(profile_id: str,
   world_id: str, declared_action: str = Field(max_length=MAX_DECLARATION_CHARS))`
   (`MAX_DECLARATION_CHARS` from `...writes`); every path literal starts
   with `/api/joueur/`; its `select(` calls name only `Batch`, `PassPlay`
   (it reads `PassPlay` joined to `Batch` for `day_number`). `cockpit/app.py`:
   import and `app.include_router(_routes_player_day.router)` right after
   `_routes_player`'s line.
2. New `frontend/src/joueur/day.svelte.js` (comment header « TICKET-0128
   (BRIEF-0128-G). The player's days: he declares, then reads what the
   creator published. Only /api/joueur/ (PSH2); imports stay in this folder
   (PSH3). »): `export const DAY_POLL_MS = 5000`; `export const dayState =
   $state({ days: [], canDeclare: false, characterId: null, declaration:
   '', loading: false, submitting: false, error: '' })`;
   `loadPlayerDays()` (GET `/api/joueur/journee?profile_id=...&world_id=...`
   through `call` from `./joueur.svelte.js`), `declarePlayerDay()`
   (`postJson('/api/joueur/journee/declarer', {...})`); after each load,
   while a day is `en_cours`, one `setTimeout` (cleared before it is set
   again) reloads after `DAY_POLL_MS`.
3. New `frontend/src/joueur/PlayerDay.svelte`: `<section class="journee">`
   titled « Ma journée »; when `dayState.canDeclare`, a `<textarea>`
   (placeholder « Que fait ton personnage aujourd'hui ? ») and « Déclarer »;
   otherwise « Ta journée suit son cours ; la suivante viendra une fois
   celle-ci publiée. »; the days, newest first: « Jour N », the
   declaration, then by `state`: `en_cours` « en cours… », `en_attente` «
   en attente de la créatrice », `abandonnee` « abandonnée », `publiee`
   the text (`white-space: pre-wrap`); `dayState.error` in red. A
   `$effect` `void joueurState.character; loadPlayerDays();`.
4. `frontend/src/joueur/WorldPage.svelte`: import `PlayerDay`;
   `{#if joueurState.character}<PlayerDay />{/if}` right before `<section
   class="savoir">`; the header comment gains « « Ma journée »
   (TICKET-0128, BRIEF-0128-G). ».
5. `cd frontend && npm run build`; commit the output.
6. G2 falls: `src/world_engine/creation_check.py` -- `"world_has_pc",`
   leaves `REVIEW_VIOLATION_CODES`; the `any_pc` query and its violation
   (:381-386) are deleted; the `pc_exists` line above them (:380) stays. `tooling/verify/checks/creator_review.py`: the
   `"world_has_pc"` entry of `MESSAGES` goes; « Bea holds a player
   character » expects `[]`, « Ana holds a player character » expects
   `["pc_exists"]`; its docstring's CR1 sentence reads « Bea holding a
   player character in the world -> no violation (G2 lifted,
   TICKET-0128); Ana holding one -> `pc_exists`. ».
   `tooling/verify/checks/draft_approval.py`: DA3 drops the « Bea holding a
   player character » case (and its helpers if nothing else uses them --
   else keep `bea_pc`); before DA1, Bea's player character is added (the
   former `bea_pc` body) and stays; DA1's PC assertion reads only the
   world's player characters whose `user_id` is Ana's (still exactly
   `[(kael, ana, quai)]`) and asserts the world then holds two player
   characters; the docstring says « DA1 runs with Bea's character in the
   world: a second player character is approved (G2 lifted, TICKET-0128).
   ».
7. `.claude/rules/player-surface.md`: `paths:` gains
   `"src/world_engine/cockpit/routes/player_day.py"`; INV-66's text gains,
   before its « -- enforced by »: « The one text a player reads outside a
   perspective is a day's published narrative (`pass_play.published_text`),
   which the creator read before publishing; the narrator's own text, the
   gains and a failure's reason never reach him. »; its enforced-by list
   gains `player_journee.py`. Re-wrap at 100 characters; the file stays
   under 4 000 characters.
8. New check `tooling/verify/checks/player_journee.py`, first sentence «
   G1 check for TICKET-0128 (BRIEF-0128-G) -- the player declares his day
   and reads only what the creator published (INV-66, D1, E1). », fresh
   database per R-35, `day_declare.missing_usages` and
   `day_declare.enqueue_day` swapped and restored in `finally`:
   - **PJ1** shape: on an open world with Ana's PC, `GET
     /api/joueur/journee` -> exactly `{character_id, can_declare, days}`,
     each day exactly `{day_number, declared_action, state, text}`; a
     profile with no character -> `{character_id: None, can_declare:
     False, days: []}`; a closed world -> 404 « Monde introuvable. »; an
     unknown profile -> 404 « Profil introuvable. ».
   - **PJ2** states: four days of Ana set raw to `submitted`, `flagged`,
     `abandoned`, and `resolved` + published (`published_text` « Publié »,
     `batch.final_result` « Narrateur secret »), then one `resolved`
     unpublished (`final_result` « Pas encore ») -> lot (b)'s table
     row by row; the response text holds « Publié » and neither «
     Narrateur secret » nor « Pas encore », nor any `day_run_failure`
     reason written for the flagged day, nor any proposal's rationale of
     those days.
   - **PJ3** declare: with an unpublished day -> `POST
     /api/joueur/journee/declarer` 409 `DAY_IN_PROGRESS`; once it is
     published -> 201, a `submitted` day of Ana whose world is the open
     world even though another world is active, its batch id recorded by
     the swapped `enqueue_day`; a profile with no character -> 404 «
     Personnage introuvable. »; an empty declaration -> 422.
   - **PJ4** static, code tokens: `routes/player_day.py` holds no `chat(`,
     no `World.is_active`, `_world_id(`, `final_result`, `write_usage_event`
     or `lore_selectors`; every route path literal starts with
     `/api/joueur/`; `creation_check.py` holds no `world_has_pc`;
     `joueur/day.svelte.js` holds `/api/joueur/journee` and
     `/api/joueur/journee/declarer`; `WorldPage.svelte` holds `<PlayerDay
     />`; a built asset carries « Ma journée »;
     `.claude/rules/player-surface.md` holds `pass_play.published_text`.
   A rule not reached is a FAILURE.
9. `tooling/standards/ARCHITECTURE_DECISIONS.md`, inserted above the
   footer (`---` / `*Co-built...*`), verbatim:
   ```
   ## TICKET-0128 -- the player's day and the active player character (BRIEF-0128-a to BRIEF-0128-g, schema v2.34)

   A world may hold several player characters, and the player lives his
   days. A1 -- `world.active_pc_id`, chosen in the cockpit header; one
   resolver, `active_pc.resolve_active_pc`, replaces the three that refused
   a second PC (`_player_character_id`, `_resolve_player_character`,
   `_resolve_player_id`); one PC needs no choice, several and none chosen
   answer « Choisissez le PJ actif. »; deleting the character clears the
   choice. Rejected: A2, the choice kept in the browser (reactivation: two
   cockpit tabs on two PCs at once).

   B2, K1, S1 -- the declaration answers at once; one background worker
   (`cockpit/day_runner.py`) plans then resolves each day in arrival order;
   the plan and resolve HTTP routes are gone. Rejected: B1, each step
   launched by hand (reactivation: « Suivi » shows many failures); K2, the
   chain in the declaration request; S2, one thread per day.
   P1 -- the chain takes its world and its character from the day, never
   the active world; the premise, the extraction, the feasibility and the
   presence rung receive that world. Rejected: P2, advancing only when the
   player's world is active. Q1 -- the quest pin is chosen with the
   declaration (`pass_play.quest_id`); none on the player's side.
   Rejected: Q2, manual days in the cockpit.

   L1, M1, R1, Z1 -- a failure writes `day_run_failure` (stage, closed code,
   reason) and turns the day `flagged`; Journée lists it with « Relancer »
   (resume at the failed stage) and « Abandonner » (`abandoned`); the player
   sees only « en attente de la créatrice »; « Suivi » counts failures by
   stage and code. At startup every day left `submitted` or `resolving` is
   an « interrompue » failure. Rejected: L2, the failure in
   `pass_play.history` (JSON, INV-20); M2, no metric; R2, relaunching at
   startup; Z2, « Relancer » only.

   C1, C′2, T1, E1, W1 -- a resolved day waits in « À publier » until no
   proposal of that day is `proposed` or `approved`; the creator may
   rewrite it; `pass_play.published_text` / `published_at` hold the
   publication, `batch.final_result` keeps the narrator's text; a published
   day is never replayed; a character has at most one unpublished day; the
   migration published the days already resolved with the narrator's text.
   Rejected: C2, publishing without review; C3, the narrative visible at
   resolution; C′1, publishing as is; T2, a `day_publication` table; E2,
   declaring freely; W2, the old days in « À publier ».

   D1 -- the player sees the day, his declaration, « en cours » / « en
   attente de la créatrice » and the published narrative; his knowledge
   still comes through « Mes savoirs ». INV-66 amended. Rejected: D2,
   showing the gains (reactivation: Nia asks after the live gate). F1 --
   the day counter stays the world's, shared by its PCs. Rejected: F2, a
   counter per PC (reactivation: TICKET-0120 opens). G2 (TICKET-0129)
   lifted: a world approves a second player character. J1 -- one ticket.

   **INV-70.** A creator surface's player character comes from one
   resolver, `active_pc.resolve_active_pc`. Held in
   `.claude/rules/day-chain.md`. Gate: `pc_resolution.py`.

   **INV-71.** The day chain takes its world and its character from the
   day, never from the active world nor the active PC. Held in
   `.claude/rules/day-chain.md`. Gate: `day_chain_world.py`.

   **INV-66 (amended).** The one text a player reads outside a perspective
   is a day's published narrative. Gate: `player_journee.py`.

   Deferred: Y2, the plan's model calls outside its write transaction
   (reactivation: a write fails « database is locked » while a day plans);
   dated encounters and the calendar (TICKET-0120); Play and the scene for
   the player (I); quests, debts and services on the player's side.
   ```
10. `python tooling/glue/gen_file_map.py`.

## Scope OUT

- Play and the scene for the player (I); quests, debts, services on the
  player's side; « Mes savoirs » (0127, unchanged).
- Showing gains, the account, a failure's reason or the narrator's text
  to the player (D2, D1).
- Automatic choice of the active PC at the approval of the second PC.
- The creation button's visibility on `WorldPage.svelte` (unchanged).

## Invariants to defend

- **INV-66** (amended here): the player route never reads
  `batch.final_result` nor a failure, nor a proposal; PJ2's text test.
- **INV-67** / **INV-68**: `check_review` keeps every other code; the
  approval path is unchanged but for G2.
- PSH2 / PSH3 (`player_shell.py`): the new player files call only
  `/api/joueur/` and import only from their folder.

## Decision rights

STOP: an anchor that does not hold; `player_shell.py` or `player_routes.py`
turning red; `draft_approval.py` DA1 failing with Bea's character present
for a reason other than its PC assertion (that would be a real second-PC
defect).
ADAPT: `draft_approval.py`'s `bea_pc` helper is shared by another rule ->
keep it; INV-66's amended text passes the rule file's budget -> shorten
the sentence to « The one text a player reads outside a perspective is a
day's published narrative (`pass_play.published_text`). ». Report each.
REPORT-ONLY: the player's « Créer mon personnage » button still shown when
he has a character.
> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/player_journee.py` -> PASS (PJ1-PJ4).
- [ ] `creator_review.py`, `draft_approval.py`, `player_routes.py`,
      `player_shell.py`, `player_creation.py`, `character_perspective.py`,
      `perspective_isolation.py`, `claude_md_contract.py`, `file_map.py`,
      `module_budget.py`, `frontend_build_fresh.py`, `day_runs.py`,
      `day_publication.py`, `day_chain_world.py`, `pc_resolution.py`,
      `day_schema.py`, `active_pc_selector.py` -> PASS.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> PASS (every arrow
      of the ticket now resolves).
- [ ] Live gate per the ticket.
- [ ] /review-step, then /close-step.

## Docs to update

`.claude/rules/player-surface.md` (Scope IN 7); ARCHITECTURE_DECISIONS
(Scope IN 9). No schema change.
