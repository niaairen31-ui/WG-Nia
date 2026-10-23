<!-- slug: perspective-routes -->
# BRIEF 0125-E — "The perspective routes, the player routes, the journal"

Lot: LOT-0125-player-entry.md (authoritative on conflict)
Depends on: BRIEF-0125-B (journal kind, column), C (`_world_detail` flag), D (the pipeline)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/models/pipeline.py` -> `LORE_USAGE_STEPS["perspective"]` (B).
- `src/world_engine/writes/lore_usage.py` -> `PAYLOAD_KEYS` holds `perspective_ask`, `perspective_resolve` (B).
- `src/world_engine/perspective_query.py` -> `execute_public_plan`, `BindingRefused`, `PERSPECTIVE_VERDICTS` (D).
- `src/world_engine/perspective_audit.py` -> `withheld` (D).
- `src/world_engine/perspective_render.py` -> `render_public` (D).
- `src/world_engine/perspective_selectors.py` -> `PERSPECTIVE_DESCRIPTIONS` (D).
- `src/world_engine/lore_plan.py` -> `draft_plan(..., *, descriptions=None)` (D).
- `src/world_engine/cockpit/routes/lore.py` -> `_serialize_plan`, `_deserialize_plan`, and `ollama_client.ping()` called through the module (R-24).
- `src/world_engine/lore_usage.py` -> `attempt_id`, `record` (R-11).
- `src/world_engine/models/pipeline.py:706-720` -> `User` (R-07).
- `src/world_engine/cockpit/app.py:131-154` -> the `include_router` block (R-29).
- `tooling/verify/checks/lore_usage.py:426-470, 722-762` -> `_seed_prompts`, `_Stub`, `_swap`, the `TestClient` pattern (R-35).

Halt if any has moved.

## Facts carried

### R-07 -- `user` table
Opened: `src/world_engine/models/pipeline.py:706-720` (declaring model);
`grep -rn "User(" src scripts`; `grep -rn "User.role" src`;
`tooling/verify/canon_write_policy.txt:1-13`.
Finding: `User(id, name, email unique nullable, role str NOT NULL
server_default 'player', created_at, is_active bool server_default 1)`. No
CHECK on `role`. No `User(` construction in `src/`; the only `user`
writer in `scripts/` is `seed_pilot.py:3120-3127`
(`get_or_create(session, m.User, "user-creator", name="Creator", ...,
role="creator")`). The only `User.role` reader is
`routes/creator.py:821` (`== "creator"`). `user` is absent from
`[CANON_TABLES]`.
Consequence: a player profile is a `user` row with `role='player'`; no
schema change; its writer is a new commit-free helper in `writes/users.py`,
outside the canon-write gate.
### R-11 -- the Lore usage journal (declaring model and writer)
Opened: `src/world_engine/models/pipeline.py:467-504`,
`src/world_engine/writes/lore_usage.py:1-70`, `src/world_engine/lore_usage.py`.
Finding: `LORE_USAGE_STEPS = {"write": ("questions","draft","commit"),
"consult": ("ask","resolve")}`; `LoreUsageEvent.__table_args__` holds
`ck_lore_usage_event_step` with the literal `"(kind = 'write' AND step IN
('questions','draft','commit')) OR (kind = 'consult' AND step IN
('ask','resolve'))"`, `ck_lore_usage_event_outcome`, `ck_lore_usage_event_entry`
and indexes `idx_lore_usage_event_attempt (attempt_id, created_at)`,
`idx_lore_usage_event_world (world_ref, created_at)`.
`writes/lore_usage.PAYLOAD_KEYS` is keyed by **step** (`questions, draft,
commit, ask, resolve`); `write_usage_event` refuses a step not in
`LORE_USAGE_STEPS[kind]` and a payload whose key set differs from
`PAYLOAD_KEYS[step]`, and requires `payload["error"] is None` iff outcome
`ok`. `lore_usage.stage/record(db, *, attempt, world_id, kind, step,
outcome, payload, exchanges=None, lore_entry_ref=None)`.
Consequence: a perspective kind needs step names unique across kinds
(`perspective_ask`, `perspective_resolve`), two `PAYLOAD_KEYS` entries, and
a table rebuild (the CHECK is in the DDL).
### R-12 -- `lore_usage.py` check (a gate B and E must pass)
Opened: `tooling/verify/checks/lore_usage.py:1-140, 205-217`.
Finding: U0 requires the files under `src/world_engine` naming the journal
to equal `_NAMING_FILES = {models/pipeline.py, models/__init__.py,
writes/lore_usage.py}`, the callers of `write_usage_event` to equal
`{writes/lore_usage.py, lore_usage.py}`, and the scripts naming the journal
to equal `_SCRIPTS = {migrate_v2_13_lore_usage.py, export_lore_usage.py}`.
U1 requires `ck_lore_usage_event_step` to list exactly the pairs of
`LORE_USAGE_STEPS`. U2 runs `migrate_v2_13_lore_usage.py` (its own literal
DDL, lines 72-100) and compares CHECK **names** only. U10 requires the two
routes in `_ROUTES` not to call `write_usage_event`. The check already runs
close to `corpus_gate.py`'s 15-second timeout (TICKET-0123 handover).
Consequence: B adds `migrate_v2_31_player_entry.py` to `_SCRIPTS` (it names
the table) and changes nothing else in this check; the v2.31 migration is
proven in a new check. Routes of E name `lore_usage` (the recorder) only,
never the table, and never call `write_usage_event`.
### R-24 -- the creator consultation route
Opened: `src/world_engine/cockpit/routes/lore.py:1-184`.
Finding: `/api/lore/ask` pings Ollama (503 with
`PLANNER_UNAVAILABLE_MESSAGE`, journaled `unavailable`), drafts the plan
(`OllamaError` -> 503, `LlmParseError` -> 502 `"lore plan drafting failed:
{exc}"`), executes, renders, journals `ok`, answers `{verdict, rows, trace,
plan, candidates, answer, renderer, near}`. `_serialize_plan` /
`_deserialize_plan` (422 on a malformed plan) are module functions. Every
journal row goes through `lore_usage.record`.
Consequence: the perspective routes mirror this flow in new route files and
import `_serialize_plan`/`_deserialize_plan` from `routes/lore.py` rather
than copy them (drafting decision 6).
### R-29 -- the shell server and build
Opened: `src/world_engine/cockpit/app.py:80-160, 285-329`;
`frontend/vite.config.js`; `frontend/index.html`;
`frontend/scripts/write-manifest.mjs:1-55`;
`tooling/verify/checks/frontend_build_fresh.py:30-120`;
`tooling/verify/checks/static_asset_freshness.py:1-52, 288-330`;
`tooling/verify/checks/legacy_mount.py:1-80`.
Finding: `/static` is served by `_FreshnessAwareStaticFiles`; `_SHELL_ROUTES
= ("/", "/play", "/creation", "/creation/{sub_tab}", "/observation",
"/journee", "/lore")` registered in a loop to `_serve_shell`, which returns
`static/index.html` with `cache-control`. Vite: `base: '/static/'`, `outDir:
'../src/world_engine/cockpit/static'`, `emptyOutDir: true`, `external:
['cytoscape']`, no `input` (single page `index.html`). The source-hash set
is `frontend/src/**` plus exactly `package.json, package-lock.json,
vite.config.js, index.html`, written identically in `write-manifest.mjs:31`
and `frontend_build_fresh.py:38` (`ROOT_FILES`). `static_asset_freshness`
rule 4: every decorator-form `HTMLResponse` route must construct its
response with `headers={"cache-control": ...}`; rule 3: every static file is
classified. `legacy_mount` rule 7: `_SHELL_ROUTES` equals `SHELL_ROUTES` in
`router.js`.
Consequence: G adds a page `frontend/jouer.html` as a second Vite input,
served by a decorator route `GET /jouer` returning `static/jouer.html` with
`cache-control`; `/jouer` is not added to `_SHELL_ROUTES` (it is not a
surface of the creator shell). `jouer.html` joins the source-hash set in
both `write-manifest.mjs` and `frontend_build_fresh.py`.
### R-30 -- the origin guard
Opened: `src/world_engine/cockpit/origin_guard.py:1-40`.
Finding: every write method is refused unless `Host` is local and `Origin`,
when sent, is a local http(s) origin; reads pass.
Consequence: `/jouer` is served by the same local server, so its POSTs pass
unchanged. No change.
### R-33 -- seeded users
Opened: `scripts/seed_pilot.py:3115-3130`, `grep -rn "INTO user" scripts src`.
Finding: users are written only by `seed_pilot.py:3120-3127` (one
`creator` user, id `user-creator`); no other script or route creates a
`user` row.
Consequence: profiles are the first runtime writer of `user`; brief E's
fixture creates its creator user itself.
### R-34 -- DB fixture pattern for a check
Opened: `tooling/verify/checks/world_sheet.py:47-62` (`_fresh_engine`),
`:213-240` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_engine()` makes a temp dir, sets
`WORLD_ENGINE_DATABASE_URL=sqlite:///<tmp>/check.db` and
`WORLD_ENGINE_ENV=test` (setdefault), puts `src` on `sys.path`, drops every
cached `world_engine` module, imports `world_engine.models`, then
`SQLModel.metadata.create_all(engine)` with `world_engine.db.engine`. Route
functions are then called directly with a `Session`. `main()` runs each rule
in `try/except Exception`, turning a crash into a failure, and prints
`FAIL:` lines / one `PASS:` line.
Consequence: every new DB-backed check of this lot builds its database with
this `_fresh_engine` body (copied: each check is standalone) and never
touches Nia's database.
### R-35 -- route test pattern with stubbed models
Opened: `tooling/verify/checks/lore_usage.py:426-470` (`_seed_prompts`,
`_Stub`, `_swap`), `:722-762` (`check_u9`).
Finding: `_seed_prompts(db)` imports `scripts/seed_pilot` and writes the
`lore_question_to_plan` and `lore_rows_to_prose` heads through
`seed_pilot.upsert_prompt_template` (ids `pt-lore-question-to-plan`,
`pt-lore-rows-to-prose`). `_Stub(replies)` pops one reply per call (an
`Exception` reply is raised, a dict is JSON-dumped). `_swap(module, stub)`
replaces `module.chat` and returns the original. `check_u9` builds
`TestClient(app, base_url="http://127.0.0.1")` from
`world_engine.cockpit.app`, swaps `lore_plan.chat` and `lore_render.chat`,
replaces `ollama_client.ping` (a raising function for "down", `lambda *a,
**k: []` for "up"), and restores all three in `finally`.
Consequence: brief E's check drives the new routes the same way; the routes
must call `ollama_client.ping()` through the module attribute (as
`routes/lore.py` does) for the stub to take effect.
### R-36 -- sanctioned writers a fixture uses
Opened: `src/world_engine/writes/facts.py:75-108, 175-216`;
`src/world_engine/writes/facets.py:60-69, 193-201`;
`src/world_engine/writes/factions.py:61-80`;
`src/world_engine/writes/relations.py:122-124, 332-412`;
`src/world_engine/writes/config.py:109-129`;
`tooling/verify/checks/fact_facets.py:405-420` (a creator-only note fixture).
Finding: `create_fact(db, *, world_id, content, created_by, facet,
aspect=None, default_level="unaware", relation_id=None, event_id=None,
world_law_id=None)` adds one fact (refuses a NULL/unknown facet);
`attach_participants(db, *, fact, entity_ids, role=None)` (free facts
only); `create_fact_default(db, *, world_id, fact_id, scope_type, scope_id,
level, created_by)`; `write_entity_facets(db, *, entity_id, facets,
created_by, mentions=None) -> list[Fact]` writes a facets payload,
`creator_meta` included -- `fact_facets.py` R8 builds a creator-only note
with `facets={"histoire": ..., "creator_meta": ...}`; a facet whose preset
is `public_world` gets a `world` default only when the entity `is_public`
(`_preset_scope`). `write_membership(db, *, mode="open", world_id,
entity_id, faction_id, role=None, cover_role=None, is_primary=False,
is_secret=False)`; `write_relation(db, *, mode="set" | "delta", ...)`
births the relation's `lien` fact, read back by `lien_fact_of(db, rel)`.
`write_world_laws` writes `world_law` rows only, no fact.
Consequence: brief D's fixture writes facts with `create_fact` +
`attach_participants` + `create_fact_default` (explicit public levels), the
creator-only note with `write_entity_facets(... "creator_meta" ...)`,
memberships with `write_membership(mode="open")`, the relation with
`write_relation(mode="set")` and its fact via `lien_fact_of`; laws are not
facts, so `world_laws` reads `world_law` directly.

## Contracts

### C-03 -- `draft_plan` over given descriptions
Produced by: D   Consumed by: E
Signature: `draft_plan(question, world_id, db, exchanges=None, *, descriptions: dict[str, str] = _SELECTOR_DESCRIPTIONS) -> LorePlan`.
Rule: `{selectors}` is filled from `descriptions` (one `- name: desc` line
each, as `_render_selectors` does today); everything else unchanged.
### C-05 -- the perspective executor
Produced by: D   Consumed by: E
Module: `src/world_engine/perspective_query.py`.
`PERSPECTIVE_VERDICTS = ("answered", "ambiguous_mention", "nothing_known", "unsupported_selector")`.
`PerspectiveResult(verdict: str, rows: tuple[dict, ...], ambiguous: tuple[dict, ...], rejection_reason: Optional[str])`,
frozen; `ambiguous` items `{"ref": str, "candidates": [{"entity_id","name","type"}]}`
sorted by name then id.
`execute_public_plan(plan, world_id, db, bindings=None) -> PerspectiveResult`:
1. `validate_plan(plan, db, lookups=_PERSPECTIVE_LOOKUPS)`; failure ->
   `unsupported_selector`, `rejection_reason` set, nothing read.
2. `view = public_view(db, world_id)`; each mention resolved by
   `resolve_named(..., scope=NameScope("public", known_fact_ids=view.fact_ids))`,
   or, when bound, checked by C-06's rule.
3. any `ambiguous` -> `ambiguous_mention` with public candidates.
4. any `unmatched` -> `nothing_known`, no rows, no names.
5. each call through `_PERSPECTIVE_LOOKUPS`, args by `lore_query._call_args`,
   truncated at `row_cap`; `answered` iff a row outside the spec's
   `context_sections` exists, else `nothing_known`.
Error cases: `BindingRefused(ValueError)` raised before any row is read when
a binding names an unknown ref or an id outside that mention's public
candidates.
### C-07 -- the audit
Produced by: D   Consumed by: E
Module: `src/world_engine/perspective_audit.py`.
`WITHHELD_REASONS = ("creator_only", "not_public", "entity_not_public", "secret_membership", "faction_not_public")`.
`withheld(plan, world_id, db, bindings=None) -> list[dict]`, rows
`{"reason", "subject", "content"}` (`subject` = the dossier entity's name,
or the searched text), sorted by subject then reason then
content. For each call of a valid plan whose mentions all resolve
(creator scope is NOT used: the audit resolves under the public scope, and
for a mention that does not resolve publicly it resolves under
`NameScope("names_only")` to name the entity withheld):
- `public_dossier` on X: X not public -> one `entity_not_public` row
  (`content` = X's name) and nothing else for X; else every fact with X as
  participant or on a relation of X that is not in `view.fact_ids`, as
  `creator_only` (in `creator_only_fact_ids`) or `not_public`; every current
  membership of X (and, for a faction, of its members) that the dossier
  dropped, as `secret_membership` or `faction_not_public`.
- `public_facts_mentioning`: every matching fact not in `view.fact_ids`, as
  `creator_only` or `not_public`, with `subject` = the searched text.
- `public_factions`: every active non-public faction, `entity_not_public`,
  `subject` and `content` = its name.
- `world_laws`: nothing.
Invalid plan or `ambiguous_mention`: `[]`. `content` of a fact row is its
`fact_texts` text. Reads only. Never imported by a player-facing module
other than `routes/player.py` (which journals it and never returns it).
### C-08 -- the perspective renderer
Produced by: D   Consumed by: E
Module: `src/world_engine/perspective_render.py`.
Constants (verbatim):
- `NOTHING_KNOWN_MESSAGE = "Rien de ce que tout le monde sait ne répond à cette question."`
- `UNSUPPORTED_MESSAGE = "Cette question ne peut pas recevoir de réponse à partir de ce que tout le monde sait."`
- `AMBIGUOUS_MESSAGE = "Plusieurs entités connues portent ce nom. Laquelle ?"`
`render_public(result, question, spec, exchanges=None) -> RenderedAnswer`:
non-`answered` verdicts -> `RenderedAnswer(<constant>, "deterministic", [])`
with no model call; `answered` -> `lore_render.render(LoreResult(verdict=
"answered", rows=result.rows, trace=[], ambiguous_mentions=(),
unmatched_surface_forms=(), rejection_reason=None), question, spec, {},
exchanges)`. No `Session` parameter.
`lore_render._SECTION_FORMATTERS` gains `members` (`member_name (role)`, role
omitted when None), `laws` (the law's `text`), `public_mentions`
(`« content » -- participants` joined by `, `, the dash part omitted when
empty).
### C-09 -- journal kind `perspective`
Produced by: B   Consumed by: E
`LORE_USAGE_STEPS["perspective"] = ("perspective_ask", "perspective_resolve")`.
`PAYLOAD_KEYS["perspective_ask"] = {"question","perspective","asked_by","response","withheld","error"}`;
`PAYLOAD_KEYS["perspective_resolve"] = {"question","perspective","asked_by","plan","bindings","response","withheld","error"}`.
`perspective` is `"public"`; `asked_by` is `"creator"` or
`"player:<user_id>"`; `withheld` is C-07's list, or `[]` when the step did
not execute a plan.
CHECK `ck_lore_usage_event_step` gains `OR (kind = 'perspective' AND step IN
('perspective_ask','perspective_resolve'))`.
### C-10 -- creator perspective routes
Produced by: E   Consumed by: F
Module: `src/world_engine/cockpit/routes/lore_perspective.py`.
`POST /api/lore/perspective/ask` body `{question, world_id, perspective,
attempt_id?}`; `POST /api/lore/perspective/resolve` body `{plan, bindings,
world_id, question, perspective, attempt_id?}`. `perspective` must be
`"public"` (else 422 `"Perspective inconnue."`). Answer:
`{verdict, answer, renderer, candidates, plan, rows, withheld}` where
`candidates` is `{ref: [{entity_id,name,type}]}` from
`PerspectiveResult.ambiguous`. Errors as `/api/lore/ask` (503 / 502), a
refused binding -> 422 `"Choix refusé."`. Each request journals one row
(kind `perspective`, `asked_by "creator"`).
### C-11 -- player routes
Produced by: E   Consumed by: G
Module: `src/world_engine/cockpit/routes/player.py`, all paths under `/api/joueur`.
- `GET /api/joueur/profils` -> `[{id, name}]`, active `role='player'` users by name.
- `POST /api/joueur/profils` body `{name}` -> `{id, name}` (201). 422
  `"Le nom est requis."` when empty after strip; 422 `"Nom trop long (80 caractères au plus)."`
  over 80; 409 `"Ce nom de joueur existe déjà."` when an active player's
  name equals it under `normalize_surface`.
- `GET /api/joueur/mondes` -> `[{id, name, description, laws}]` for
  `open_to_players` worlds by name; laws by position.
- `POST /api/joueur/savoir/ask` body `{profile_id, world_id, question,
  attempt_id?}`; `POST /api/joueur/savoir/resolve` body `{profile_id,
  world_id, plan, bindings, question, attempt_id?}`. Answer keys exactly
  `{verdict, answer, renderer, candidates, plan}`. 404 `"Monde introuvable."`
  for a world unknown or not open; 404 `"Profil introuvable."` for a profile
  unknown, inactive or not `player`; 503/502/422 as C-10. Journal as C-10
  with `asked_by "player:<profile_id>"`, `withheld` computed and journaled,
  never returned.
Writer: C-12.
### C-12 -- profile writer
Produced by: E   Consumed by: E
`writes/users.py::create_player_profile(db, name: str) -> User`:
commit-free; strips; raises `ValueError` with the messages of C-11 (route
maps empty/too long -> 422, duplicate -> 409 by a `ProfileNameTaken(ValueError)`
subclass); adds and flushes one `User(name=..., role="player")`.
### C-13 -- world detail and update
Produced by: C   Consumed by: E, G
`_world_detail` gains `"open_to_players": bool`. `WorldUpdateBody` gains
`open_to_players: Optional[bool] = None`; `update_world` sets the column
only when it is not None.
### C-15 -- the shared perspective flow
Produced by: E   Consumed by: E (both route modules)
Module: `src/world_engine/cockpit/perspective_flow.py` (not a route module).
`ask_flow(db, *, question, world_id, asked_by, attempt) -> dict` and
`resolve_flow(db, *, plan_raw, bindings, question, world_id, asked_by,
attempt) -> dict`: run the steps of C-10 (ping, plan with
`PERSPECTIVE_DESCRIPTIONS`, execute, audit, render, journal) and return the
full creator body `{verdict, answer, renderer, candidates, plan, rows,
withheld}`; raise `HTTPException` with C-10's statuses after journaling.
The creator route returns the body as is; the player route returns only
`{verdict, answer, renderer, candidates, plan}` of it. One implementation,
two doors.

## Context

The pipeline of brief D gets its doors: one for Nia (Lore, "as the public",
with the audit) and one for the player (`/api/joueur`, answer only). Both
journal every question (H1-c). The player routes also list profiles and
open worlds.

## Scope IN

Commit 1 -- **profiles writer**:
1. New `src/world_engine/writes/users.py` -- C-12, exactly. Module
   docstring first sentence: "Player profiles (TICKET-0125, K1): the only
   runtime writer of `user`." `MAX_PROFILE_NAME = 80`. The duplicate test
   reads active `role == "player"` users of any world (users are not
   world-scoped) and compares `normalize_surface` of both names
   (`from ..lore_resolve import normalize_surface`; function-local if
   `import_cycle.py` objects). Not exported from `writes/__init__.py`.

Commit 2 -- **the creator perspective routes**:
2. New `src/world_engine/cockpit/routes/lore_perspective.py` -- C-10,
   exactly. Module docstring: thin orchestration, no `chat(`, no
   `select(` (as `routes/lore.py`). Flow of `ask`: `perspective != "public"`
   -> 422 `"Perspective inconnue."` (not journaled); `ollama_client.ping()`
   (down -> 503 `PLANNER_UNAVAILABLE_MESSAGE`, journaled `unavailable`);
   `draft_plan(question, world_id, db, exchanges,
   descriptions=PERSPECTIVE_DESCRIPTIONS)` (`OllamaError` -> 503,
   `LlmParseError` -> 502 `"lore plan drafting failed: {exc}"`, both
   journaled); `execute_public_plan`; `withheld(plan, world_id, db)`;
   `render_public` with the spec of `lore_prompt.load(db,
   lore_render.PROSE_USAGE)`; journal `ok`; answer. `resolve`: deserialize
   the plan (422 on malformed), `execute_public_plan(..., bindings)`;
   `BindingRefused` -> 422 `"Choix refusé."` journaled `refused`; never
   calls `draft_plan`. Journal rows: kind `perspective`, steps
   `perspective_ask` / `perspective_resolve`, payload keys of C-09,
   `perspective "public"`, `asked_by "creator"`, `response` = the answer
   body (None when the step did not answer), `withheld` = the audit (`[]`
   when no plan ran), through `lore_usage.record`.
3. New `src/world_engine/cockpit/perspective_flow.py` -- C-15, exactly; the
   creator route of item 2 is a thin wrapper over it. Its docstring names
   its two callers. It imports `_serialize_plan`, `_deserialize_plan` from
   `routes/lore.py`. PR8 below applies to it too.

Commit 3 -- **the player routes**:
4. New `src/world_engine/cockpit/routes/player.py` -- C-11, exactly.
   `router = APIRouter()`, every path literal starting `/api/joueur/`.
   `GET /mondes` reads `World` where `open_to_players == True`, ordered by
   name, laws by position (the same `WorldLaw` read as `_world_detail`;
   import `_world_detail` from `routes/creator.py` and keep `id, name,
   description, laws` of it). The savoir routes check the world (open) and
   the profile (active, `role == "player"`) before anything else; then call
   the shared flow with `asked_by=f"player:{profile_id}"`; answer
   exactly `{verdict, answer, renderer, candidates, plan}`. Never
   `World.is_active`, never `_crud._world_id` (B2).
5. `cockpit/app.py`: import and `include_router` the two new route modules,
   after `_routes_lore_write`.

Commit 4 -- **the check** `tooling/verify/checks/player_routes.py`,
docstring first sentence "G1 check for TICKET-0125 (BRIEF-0125-E) -- the
perspective and player routes answer only what everybody knows, refuse a
closed world, and journal every question.", fixture R-34 + R-35
(`_seed_prompts`, `_Stub`, `_swap` copied; `lore_plan.chat`,
`lore_render.chat`, `ollama_client.ping` swapped and restored in `finally`),
world built as brief D's PI4 (copy its builder, or import it if D made it a
function -- name which in the report), rules:
- **PR1** -- profiles: POST "Ana" -> 201 `{id, name}`; POST " ana " -> 409
  with C-11's message; POST "" -> 422; POST 81 characters -> 422; GET lists
  exactly the created player profiles (the seeded creator user absent).
- **PR2** -- worlds: with the fixture world closed, GET `/api/joueur/mondes`
  -> `[]`; opened through `update_world(..., open_to_players=True)` -> one
  item with keys exactly `{id, name, description, laws}`.
- **PR3** -- savoir on a closed world -> 404 `"Monde introuvable."`; an
  unknown profile -> 404 `"Profil introuvable."`; neither journals.
- **PR4** -- savoir answered (stubbed plan: `public_dossier` on « Hero »;
  stubbed prose) -> 200, answer keys exactly `{verdict, answer, renderer,
  candidates, plan}`; the response text (`json.dumps`) contains neither
  F2's nor F3's text nor `withheld`; one journal row kind `perspective`,
  step `perspective_ask`, outcome `ok`, `asked_by "player:<id>"`, its
  `withheld` equal to `perspective_audit.withheld` for that plan.
- **PR5** -- creator ask, same plan -> keys exactly `{verdict, answer,
  renderer, candidates, plan, rows, withheld}`, `withheld` non-empty;
  journal `asked_by "creator"`; `perspective: "x"` -> 422 and no row.
- **PR6** -- ping down -> 503, one `unavailable` row; unparsable plan ->
  502, one `parse_error` row.
- **PR7** -- resolve: a binding to Shade -> 422 `"Choix refusé."`, one
  `perspective_resolve/refused` row; a binding to a Twin -> 200.
- **PR8** -- static: `routes/lore_perspective.py` and `perspective_flow.py`
  hold no `chat(` and no `select(`; `routes/player.py` holds no `chat(` and
  its `select(` calls name only `User`, `World` or `WorldLaw`; none of the
  three holds `World.is_active`, `_world_id(`, `write_usage_event` or an import of
  `lore_selectors`; every route path literal of `player.py` starts with
  `/api/joueur/`.
PASS line: `PASS: player_routes -- profiles, open worlds and public questions for the player; the creator's perspective with its audit; every question journaled`.

## Scope OUT

- No frontend (F, G).
- No character perspective, no PC, no profile-to-PC link (0126, 0127).
- No edit to `routes/lore.py`: its plan helpers are imported, not changed.
- No session or cookie for the profile: the profile id travels in the body
  (drafting decision 9).
- Every later brief of this lot.

## Invariants to defend

- **INV-01 / INV-02** -- the player answer is built only from the public
  pipeline; PR4 proves no withheld text crosses.
- **INV-19** -- the model calls go through `lore_prompt.load` /
  `effective_model` as today (reused functions).
- **INV-58** -- empty verdicts never reach a model (D's renderer).
- **INV-59** -- the journal is written only through `lore_usage`; the new
  routes never call `write_usage_event` and nothing reads the journal.
- "Injected context depends on the active role, never the account" -- the
  player route has no role switch: it serves only the public perspective.

## Decision rights

STOP:
- an anchor has moved;
- serving the player answer would require a creator selector or the
  creator name regime;
- `lore_usage.py` U0 turns red because a new module names the journal
  table (only `lore_usage` may be named).
ADAPT:
- `_world_detail`'s import into `routes/player.py` creates a cycle: read
  the world laws with the same query in `player.py` and report;
- `TestClient` needs `base_url="http://127.0.0.1"` for the origin guard
  (R-30, R-35): use it.
REPORT-ONLY:
- latency of the stubbed flows.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `player_routes.py`, `lore_usage.py`, `lore_isolation.py`,
      `perspective_isolation.py` PASS.
- [ ] Named mutation PR4: returning the creator answer body from the player
      route (adding `withheld` to its keys) makes PR4 fail (then revert).
- [ ] Named mutation PR3: removing the `open_to_players` test makes PR3
      fail (then revert).
- [ ] Named mutation PR1: dropping the duplicate test in
      `create_player_profile` makes PR1 fail (then revert).
- [ ] `corpus_gate.py` passes.
- [ ] `/review-step` and `/close-step` on each commit.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry above the footer:
  `## Player profiles and the player's door (BRIEF-0125-E, no schema change)`
  -- K1, A1', B2, the five player routes, the journal fields, why the
  profile id travels in the body.
- Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.
