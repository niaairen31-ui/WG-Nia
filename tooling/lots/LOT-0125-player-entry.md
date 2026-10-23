# LOT — TICKET-0125 "The player's entry"

Authoritative on conflict with any brief. RECON run in the chat session on
`main` at `2e4e1403c5e17df268409d62ba58219d2f15f0bc` (PR #152, TICKET-0124
merged, schema v2.30).

## Objective and cut

The player gets a door of his own. A second frontend entry, `/jouer`, lets
Nia pick or create a player profile, lists the worlds she marked open to
players with their description and laws, and lets the player question the
world's **public** lore -- what everybody knows -- through a perspective
pipeline that can never return a creator-only, secret or non-public line.
Nia gets the same pipeline in Lore ("Perspective" tab) with an audit of
every withheld line and its reason; every perspective question is journaled.
Two creator lookups that pick "the first PC" of a world refuse instead (M2),
so the PCs TICKET-0126 will create cannot be confused.

The lot stops before character creation: no designer, no proposal, no
creation budget (R1: those settings move to TICKET-0126 with their readers),
no character perspective (TICKET-0127), no player day (TICKET-0128).

## Briefs in this lot

- **A** -- `pc-resolution` -- commit TICKET-0124's artifacts if they are on
  disk untracked; M2 in `_player_character_id` and `_resolve_player_id`.
- **B** -- `schema-v2-31` -- `world.open_to_players`; `lore_usage_event`
  rebuilt to admit the `perspective` kind; migration and docs.
- **C** -- `open-to-players` -- the flag on Création > Monde (route + page).
- **D** -- `public-perspective` -- the `public` name regime, the perspective
  selectors, executor, audit and renderer; no route.
- **E** -- `perspective-routes` -- the creator perspective routes, the
  player routes (profiles, open worlds, public questions), the journal.
- **F** -- `lore-perspective-tab` -- the "Perspective" tab of the Lore shell.
- **G** -- `player-shell` -- the `/jouer` entry: profile picker, open worlds,
  world page with the public question box; INV-66 and its rule file.

## Dependency graph

- A depends on nothing in this lot and runs first (it lands the 0124
  artifacts before anything else touches `tooling/`).
- B depends on A only by order of commits (no code dependency).
- C depends on B (`World.open_to_players`).
- D depends on nothing in this lot (pure reads over existing tables); it is
  placed after C by choice, not by dependency.
- E depends on B (journal kind, world flag), C (`_world_detail` carries the
  flag) and D (the pipeline).
- F depends on E (creator routes).
- G depends on E (player routes) and C (a world to open).
- Strict execution order: A, B, C, D, E, F, G.

## RECON

### R-01 -- TICKET-0124 artifacts on `main`
Opened: `ls tooling/tickets | grep 0124`, `ls tooling/lots | grep 0124`,
`ls tooling/briefs | grep 0124` at `2e4e140`.
Finding: all three print nothing. `tooling/tickets` ends at
`TICKET-0123-lore-usage-since.md` among numbered tickets. 0124's code is on
`main` (`scripts/migrate_v2_30_world_tone.py`, `world_premise.py`).
Consequence: brief A commits them, as a separate commit, only if they are
present untracked in the working tree; otherwise it reports and goes on.
Nia says Claude Code did not commit them.

### R-02 -- schema version
Opened: `src/world_engine/schema_version.py:15`, `world-engine-schema.md:3`,
`world-engine-schema-changelog.md:16`.
Finding: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.30"`; the schema doc
header reads `Current schema version: v2.30`; the newest changelog entry is
`- **v2.30** -- TICKET-0124, BRIEF-0124-A`.
Consequence: this lot's migration is v2.31 (`schema_version_agreement.py`
and `schema_partition.py` require the constant, the header and the newest
changelog entry to agree).

### R-03 -- `world` table
Opened: `src/world_engine/models/canon.py:65-93` (the declaring model).
Finding: `World` has `id, name, description, tone, is_active,
current_phase, created_at, updated_at`; `__table_args__` holds the partial
unique index `idx_world_one_active` and the CHECK `ck_world_current_phase`.
No player-visibility column. `canon.py` is 961 lines (budget 1000).
Consequence: B adds `open_to_players: bool` (`server_default 0`, NOT NULL)
after `tone`; `canon.py` stays under budget (+4 lines).

### R-04 -- PC lookups that choose "the" PC
Opened: `src/world_engine/cockpit/crud/entities.py:209-220`,
`src/world_engine/analyzer_transcript.py:248-255`,
`src/world_engine/cockpit/routes/day.py:124-137`.
Finding: `_player_character_id(db, world_id)` selects `Character` joined to
`Entity` where `Entity.world_id == world_id` and `character_type ==
"player"`, `.first()`; none -> `HTTPException(400, "No player character in
the active world.")`. `_resolve_player_id(db, world_id)` is the same query,
`.first()`, returns `char.id if char else None`.
`_resolve_player_character(world_id, db)` selects `.all()` and raises 400
`"expected exactly one player character for this world, found {n}"` when
`len(rows) != 1`.
Consequence: M2 touches the first two only; Journée already refuses.

### R-05 -- every lookup by `character_type == "player"` in `src/`
Opened: `grep -rln '\.first()' src/world_engine | xargs grep -ln
'character_type == "player"'` and `grep -rn '_player_character_id(' src`.
Finding (pasted):
```
src/world_engine/writes/events.py
src/world_engine/cockpit/crud/entities.py
src/world_engine/cockpit/crud/skills.py
src/world_engine/cockpit/routes/day.py
src/world_engine/analyzer_transcript.py
---
cockpit/routes/creator.py:769   player_id = _crud._player_character_id(db, world_id)
cockpit/routes/scene.py:82,110,183,391   player_id = <given> or _crud._player_character_id(...)
cockpit/routes/play.py:97,381,436        player_id = <given> or _crud._player_character_id(...)
cockpit/routes/spatial.py:69,117         player_id = <given> or _crud._player_character_id(...)
```
`writes/events.py:179` and `crud/skills.py:204` are predicates on one
character (`character.character_type == "player"`), not lookups;
`crud/skills.py:526` loops over every PC of a world (`_backfill_open_skill`),
correctly. `routes/day.py` refuses (R-04). The bootstrap
(`routes/creator.py:767-771`) catches `HTTPException` and returns
`player_id: None`.
Consequence: the M2 sites are exactly `_player_character_id` and
`_resolve_player_id`. The 10 callers need no edit: a refusal raised inside
`_player_character_id` reaches them as an `HTTPException`, and the bootstrap
already turns one into `player_id: None`.

### R-06 -- one PC per user and world
Opened: `src/world_engine/models/canon.py:154-158`.
Finding: `Index("idx_character_one_pc_per_user_world", "world_id",
"user_id", unique=True, sqlite_where=text("character_type = 'player'"))`.
`create_player_character` binds every PC to the lone `role == "creator"`
user (`routes/creator.py:821`).
Consequence: today a world holds at most one PC; a second one can only
appear once TICKET-0126 binds PCs to player profiles. M2 is preventive and
proven by a fixture (brief A), not live.

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

### R-08 -- world routes
Opened: `src/world_engine/cockpit/routes/creator.py:532-538` (`list_worlds`),
`:560-571` (`WorldCreateBody`, `WorldUpdateBody`), `:607-621`
(`_world_detail`), `:623-630` (`get_world`), `:632-652` (`update_world`).
`creator.py` is 963 lines.
Finding: `WorldUpdateBody(name: str, description: str = "", tone: str = "",
laws: list[str] = [])`. `_world_detail` returns `{id, name, description,
tone, laws, is_active}`, laws = `WorldLaw.text_` by `position`.
`update_world` strips name (empty -> 422 `"Le nom est requis."`), sets
description/tone (empty -> None), `updated_at`, rewrites laws through
`write_world_laws`, one commit; never touches `is_active` or
`current_phase`. `list_worlds` returns `{id, name, is_active}` per world.
`canon_write_policy.txt:143` allows `routes/creator.py::update_world` to
write `world`.
Consequence: C adds `open_to_players: Optional[bool] = None` to
`WorldUpdateBody` (None = unchanged) and the key to `_world_detail`;
`creator.py` +5 lines stays under 1000.

### R-09 -- `world_sheet.py` (a gate C must pass)
Opened: `tooling/verify/checks/world_sheet.py:1-30, 65-71, 95-165, 205-212`.
Finding: WS2/WS3 compare `get_world`/`update_world` answers through
`_expect`, which checks only the keys it lists (`got.get(key) != value`);
WG1 requires `WorldSheet.svelte` to hold `/api/worlds/`, `method: 'PUT'`,
`Ton et style`, `refreshServerState` and none of `alert(`, `confirm(`,
`prompt(`.
Consequence: a new key in `_world_detail` and a checkbox in
`WorldSheet.svelte` keep `world_sheet.py` green unchanged.

### R-10 -- the Monde page
Opened: `frontend/src/creation/WorldSheet.svelte` (121 lines).
Finding: `$state` fields `name, description, tone, laws`; `load(worldId)`
reads `GET /api/worlds/{id}`; `save()` sends `PUT` with body
`JSON.stringify({ name, description, tone, laws: ... })` (line 62); the
form has labelled fields `Nom *`, `Contexte du monde`, `Ton et style`, then
the laws list.
After a successful PUT only `laws` is reset from the answer (line 75,
`laws = [...(world.laws ?? [])]`), then `refreshServerState()`.
Consequence: C adds `openToPlayers` state, a checkbox labelled
`Ouvert aux joueurs`, and `open_to_players: openToPlayers` in the PUT body.

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

### R-13 -- rebuild migration pattern
Opened: `scripts/migrate_v2_29_rank_trials.py:135-175`,
`scripts/migrate_v2_30_world_tone.py` (whole).
Finding: v2.30 refuses below `_PREVIOUS_VERSION`, applies in one raw
transaction (`PRAGMA foreign_keys=OFF`, `BEGIN`, DDL, `COMMIT`,
`PRAGMA foreign_keys=ON`), post-checks, then converges `schema_meta`.
v2.29's `_rebuild(cursor, model, columns)` drops the table's named indexes,
renames it `<table>_old`, creates it from `CreateTable(model.__table__)` and
its `CreateIndex`es, copies `columns`, drops `_old`.
Consequence: B's migration follows v2.30's skeleton and v2.29's `_rebuild`
(copied into the new script, as each migration script is standalone).

### R-14 -- public knowledge resolution
Opened: `src/world_engine/knowledge_resolve.py:1-50, 288-330`.
Finding: `resolve_public_levels(db, world_id) -> dict[str, str]` gives every
fact of the world its level "with NO entity": the `fact_default` row at
`scope_type='world'` if any, else `fact.default_level`; it includes every
fact regardless of level. The module docstring: "A resolved default never
carries is_secret."
Consequence: the public fact set of a world is `{fid | level != 'unaware'}`
from `resolve_public_levels`, minus creator-only facts (R-15). No new
knowledge rule.

### R-15 -- creator-only facts
Opened: `src/world_engine/facet_reads.py:58-80`; CLAUDE.md INV-01.
Finding: `creator_only_fact_ids(db, fact_ids) -> set[str]` returns the
creator-only subset in one query. `facts_of(db, *, entity_id, facets,
aspect=None, notorious_at_location=None, include_creator_only=False)` drops
creator-only facts in the query unless `include_creator_only` ("legal only
in `lore_selectors.py`").
Consequence: perspective selectors call `facts_of` without
`include_creator_only`, and also subtract `creator_only_fact_ids` from the
public set (a creator-only note whose fact has a public default must still
never show).

### R-16 -- the name index
Opened: `src/world_engine/name_index.py` (whole, 138 lines).
Finding: `REGIMES = ("names_only", "creator", "prose", "perceiver")`;
`_APPELLATION_RULES` maps each to `(appellations counted, creator-only
dropped, scope required, known required)`; `NameScope(regime,
known_fact_ids=None, exclude_entity_id=None)` raises `ValueError` when
`perceiver` lacks `known_fact_ids` or another regime carries them.
`surfaces(db, world_id, scope)` lists names of **every active entity** of
the world (no `is_public` filter, in any regime), then appellation facts
filtered by `_kept_pairs`. `creator_only_fact_ids` is imported inside
`surfaces` (lazy, cycle R-07 of 0092).
Consequence: D adds a regime `public`: appellations counted, creator-only
dropped, known required (`known_fact_ids` = the public fact set), and
**names and appellations of non-public entities dropped**. The entity filter
is new code in `surfaces`, applied only for `public`.

### R-17 -- `name_index.py` check (a gate D must pass)
Opened: `tooling/verify/checks/name_index.py:1-40`.
Finding: R3 -- `REGIMES` literal equals the key set of `_APPELLATION_RULES`.
R5 -- `CREATOR` / `NameScope("creator")` only in a listed set of files.
R6 -- every `resolve_named`/`near_candidates` call passes `scope=`; every
`surfaces`/`name_surfaces` call has three positional args or `scope=`.
F1 -- the TICKET-0092 lot's regimes case table against `surfaces`, and
malformed `NameScope`s raise.
Consequence: D adds `public` to both `REGIMES` and `_APPELLATION_RULES`;
perspective modules never use `CREATOR`; every call passes `scope=`. F1's
existing rows are unchanged (the entity filter applies to `public` only).

### R-18 -- name resolution
Opened: `src/world_engine/lore_resolve.py:135-175, 230-260`.
Finding: `resolve_named(surface_form, category, world_id, db, *, scope) ->
NamedResolution(verdict, entity_id, candidate_ids, rung, rungs_tried)`,
verdict in `matched | ambiguous | unmatched`; `named_partial` runs only for
the `creator` regime. `near_candidates(..., *, scope)` exists;
`pre_resolved(entity_id)`; `validate_binding(entity_id, category,
world_id, db) -> bool`.
Consequence: the perspective executor resolves under `NameScope("public",
known_fact_ids=...)`, never calls `near_candidates`, and validates a player
binding by re-resolving the mention under the same scope and requiring the
bound id among `candidate_ids` (never `validate_binding`, which knows
nothing of `is_public`).

### R-19 -- the creator executor
Opened: `src/world_engine/lore_query.py:1-244` (whole).
Finding: `LorePlan(mentions, calls)`, `PlanMention(ref, surface_form,
category)`, `PlanCall(selector, args)`, `LoreResult(verdict, rows, trace,
ambiguous_mentions, unmatched_surface_forms, rejection_reason, near=())`,
`TEXT_PREFIX = "text:"`. `validate_plan(plan, db)` (line 66) reads
`SELECTORS` and `_SELECTOR_LOOKUPS` from `lore_selectors` directly.
`_call_args(call_args, arg_kinds, world_id, resolutions)` (line 157) maps
`text:` / `$world` / mention refs. `execute_plan` resolves under `CREATOR`,
returns `unknown_entity` with `near`, and decides `answered` vs
`silent_canon` by rows outside `spec.context_sections`.
Consequence: D gives `validate_plan` a keyword-only `lookups` parameter
defaulting to `_SELECTOR_LOOKUPS` (behavior unchanged for every existing
caller) and reuses `_call_args`; the perspective executor lives in its own
module (no verdict literal added to `lore_query.py`, R-21).

### R-20 -- the creator selectors
Opened: `src/world_engine/lore_selectors.py` (whole, 392 lines).
Finding: `SelectorSpec(fn, arity, row_cap, arg_kinds, context_sections=())`.
`entity_dossier` returns identity (with `is_public`, `internal_name`,
`current_location_id`, `vital_status`), facets **including creator-only**
(tagged `secret`), relations with `intensity`, knowledge rows with
`is_secret`/`is_incorrect`, memberships via `read_public_memberships`,
goals. `who_knows_about` and `facts_mentioning` list knowers with
`is_secret`; `facts_mentioning` flags `creator_only` and includes those facts.
`world_factions` lists every active faction with doctrine, organisation,
tension facets and `magic_knowledge_level`.
Consequence: no creator selector may serve a perspective, even filtered
afterwards. The perspective selectors are new functions in a new module.

### R-21 -- `lore_selectors.py` and `lore_isolation.py` checks (gates D, E pass)
Opened: `tooling/verify/checks/lore_selectors.py:1-36`,
`tooling/verify/checks/lore_isolation.py:1-80`.
Finding: lore_selectors R1 bijection `SELECTORS`/`_SELECTOR_LOOKUPS`; R2 no
selector function name in `lore_query.py`; R4 in `execute_plan`, every use
of `_SELECTOR_LOOKUPS` after the failed-validation return; R5 the verdict
literals assigned in `lore_query.py` are exactly the five creator verdicts.
lore_isolation R1/R4 no `chat(`, `db.add(`, `.commit(` in `lore_selectors.py`
and `lore_query.py`; R5 `lore_plan.py` selects no canon table; R6
`routes/lore.py` has no `chat(`/`select(`; R8 `lore_plan._SELECTOR_DESCRIPTIONS`
keys equal `SELECTORS`; R10 `lore_render.py` has no `select(`, `db.add(`,
`.commit(`, no `Session` identifier; R11 no `chat(` reachable from
`render`'s non-answered branch; R12 the `OllamaError` fallback; R13 six
named message constants; R14 `render_template` raises on an unknown section;
R17 the panel modules import none of the five pipeline modules.
Consequence: the `lookups` keyword (C-02) and `descriptions` keyword (C-03)
keep every rule true; new formatters in `lore_render.py` add no `select(`
and no `Session`; perspective modules are new files these checks do not
read, guarded by a new check.

### R-22 -- the planner
Opened: `src/world_engine/lore_plan.py` (whole, 130 lines);
`scripts/seed_pilot.py:1894-1928`; `prompt_registry.py:285-300`.
Finding: `draft_plan(question, world_id, db, exchanges=None)` fills the
template's `{selectors}` from the module constant `_SELECTOR_DESCRIPTIONS`
(through `_render_selectors()`) and `{question}`; categories are
`_MENTION_CATEGORIES`. The seeded prompt names no selector itself (the list
arrives through `{selectors}`). `lore_question_to_plan` is `premise="none"`,
"carries no world content".
Consequence: D adds a keyword-only `descriptions` parameter (default the
module constant) so the same prompt plans over the perspective selectors.
No new prompt usage in this lot (drafting decision 3).

### R-23 -- the renderer
Opened: `src/world_engine/lore_render.py:1-320`; `scripts/seed_pilot.py:1929-1960`.
Finding: `_SECTION_FORMATTERS` maps `identity, facets, relations, knowledge,
memberships, goals, factions, knowers, coverage, mentions`;
`_group_rows_by_section` raises `ValueError` on an unknown section.
`_format_identity` prints `name (type)`; `_format_facets` prints `label
(aspect) : content` plus ` [secret]` when `secret` is truthy;
`_format_memberships` prints `faction_name (role)`; `_format_factions`
prints `name (faction_type) : description`; `_format_relations` prints the
intensity; `_format_mentions` prints `su de personne` for an empty knowers
list. `render(result, question, spec, candidates, exchanges=None)` renders
every non-`answered` verdict by code (`_render_deterministic`) and calls the
model only on `answered`, falling back to `render_template` on
`OllamaError`. `PROSE_USAGE = "lore_rows_to_prose"`;
`PLANNER_UNAVAILABLE_MESSAGE` is a module constant. The seeded prose prompt
asks to signal an `is_incorrect` line as false.
Consequence: public rows reuse `identity`, `facets` (`secret: False`),
`memberships`, `factions`; three new sections need formatters: `members`,
`laws`, `public_mentions`. Public rows never carry `is_incorrect`. The
perspective's own empty-verdict messages live in a new module (R11, R13
untouched).

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

### R-25 -- public memberships
Opened: `src/world_engine/context.py:161-197`.
Finding: `read_public_memberships(entity_id, session) -> list[(faction_name,
promptable_role)]`: `left_at IS NULL`, `is_secret == False`, role =
`cover_role ?? role`, primary first then oldest; it does not look at the
faction's or the member's `is_public`. INV-03: membership reaches a prompt
only through this accessor (or `read_public_membership_faction_ids`).
Consequence: the public dossier reads memberships through
`read_public_memberships` and keeps only factions whose entity is in the
public entity set (W1). The faction's member list (new) is the same WHERE
triplet keyed by `faction_id`, member public, written in the perspective
selectors module and named in INV-66 as the third sanctioned reader for
prompts (drafting decision 7).

### R-26 -- relations as facts
Opened: `src/world_engine/models/canon_knowledge.py:22-50, 87-146`;
`src/world_engine/relation_orientation.py:30`.
Finding: `Fact.relation_id` (nullable FK), `world_law_id`, `event_id` --
`ck_fact_spine_exclusive` allows at most one. A typed fact carries no
`fact_participant` (comment at `:129-131`). `Relation(world_id, entity_a_id,
entity_b_id, type, ...)`. `MAP_TOPOLOGY_TYPES = ("connects_to", "borde")`.
Consequence: the public dossier finds an entity's relations through facts
with `relation_id` in its relations (topology types excluded), the other
end public, and renders each as a `facets` row labelled `Lien` with the
fact's text; it never reads `intensity`. Event facts are out of the dossier
in this lot (drafting decision 8).

### R-27 -- facet labels and texts
Opened: `src/world_engine/facets.py:30-40, 85`;
`src/world_engine/prose_render.py:71-74`.
Finding: `FACETS: dict[str, FacetSpec]`, `FacetSpec.label` the French UI
label. `fact_texts(db, facts) -> list[str]` renders identity tokens to
current names, one entity query.
Consequence: a public fact row's label is `FACETS[fact.facet].label`, or
`Fait` when `fact.facet` is None or unknown; its content is `fact_texts`.

### R-28 -- the Lore shell
Opened: `frontend/src/lore/Lore.svelte:1-120`, `frontend/src/lore/lore.svelte.js`.
Finding: tabs `question`, `names`, `write` (buttons at lines 106-108);
`loreTab = $state('question')`; panels rendered by `{#if loreTab === ...}`.
`lore.svelte.js` posts through `api` from `../creation/sheetRequest.svelte.js`
with `world_id: serverState.worldId` and `attempt_id: crypto.randomUUID()`.
Checks reading `Lore.svelte`: `quest_request_panel.py` RP4 (a `$effect`
reading `writeState.questRequestId`).
Consequence: F adds a fourth tab `perspective` and a panel component with
its own state module; RP4's effect is untouched.

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

### R-31 -- module budgets of edited files
Opened: `wc -l` at `2e4e140`.
Finding: `routes/creator.py` 963, `models/canon.py` 961,
`models/pipeline.py` 811, `crud/entities.py` 923, `analyzer_transcript.py`
931, `lore_query.py` 244, `lore_plan.py` 130, `lore_render.py` 320,
`name_index.py` 138, `routes/lore.py` 184, `app.py` 329,
`frontend/src/lore/Lore.svelte` 237.
Consequence: every edit in this lot adds under 30 lines to any of these;
none crosses 1000. New modules start small.

### R-32 -- invariant ids and CLAUDE.md budget
Opened: `CLAUDE.md` (Invariants, Path-scoped rules), `.claude/rules/*.md`,
`tooling/verify/checks/claude_md_contract.py:77-80`.
Finding: highest live id INV-65 (`.claude/rules/prompts.md`); budgets
`ROOT_CHAR_BUDGET = 22_000`, `RULE_CHAR_BUDGET = 4_000`; `wc -c CLAUDE.md`
= 20448. The Path-scoped rules section lists one line per rule file.
Consequence: G adds `.claude/rules/player-surface.md` holding INV-66 and one
list line in CLAUDE.md (about 70 characters).

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

### R-37 -- the creator shell entry
Opened: `frontend/src/main.js` (whole, 4 lines).
Finding: `import App from './App.svelte'; import { mount } from 'svelte';
mount(App, { target: document.getElementById('app') });`
Consequence: the player entry `frontend/src/joueur/main.js` is the same
three lines with `JoueurApp.svelte`.

## Contract sheet

### C-01 -- name regime `public`
Produced by: BRIEF-0125-D   Consumed by: BRIEF-0125-D (executor), E (routes, indirectly)
Signature: `NameScope("public", known_fact_ids=<frozenset[str]>)`.
Rule: `_APPELLATION_RULES["public"] = (True, True, False, True)`; in
`surfaces`, when `scope.regime == "public"`, entities with `is_public`
false are dropped before names and appellations are built (so neither their
name nor their appellations are surfaces). `NameScope.__post_init__`:
`known_fact_ids` is required for `perceiver` and `public`, refused for every
other regime.
Error and empty cases: `ValueError` for `NameScope("public")` without
`known_fact_ids`; an empty world -> `()`.

### C-02 -- `validate_plan` over a given table
Produced by: D   Consumed by: D
Signature: `validate_plan(plan, db, *, lookups: dict[str, SelectorSpec] = _SELECTOR_LOOKUPS) -> PlanValidation`.
Rule: identical to today with `SELECTORS` read as `lookups.keys()` and the
spec read from `lookups`. Every existing call passes no `lookups`.

### C-03 -- `draft_plan` over given descriptions
Produced by: D   Consumed by: E
Signature: `draft_plan(question, world_id, db, exchanges=None, *, descriptions: dict[str, str] = _SELECTOR_DESCRIPTIONS) -> LorePlan`.
Rule: `{selectors}` is filled from `descriptions` (one `- name: desc` line
each, as `_render_selectors` does today); everything else unchanged.

### C-04 -- the public view and the perspective selectors (family)
Produced by: D   Consumed by: D (executor, audit), E
Module: `src/world_engine/perspective_selectors.py`.
`PublicView(world_id: str, fact_ids: frozenset[str], entity_ids: frozenset[str])`,
frozen dataclass. `public_view(db, world_id) -> PublicView`: `fact_ids` =
facts of the world whose `resolve_public_levels` level is not `unaware`,
minus `creator_only_fact_ids`; `entity_ids` = active entities of the world
with `is_public` true.
Family rule (every member): signature `fn(*args, view: PublicView, db) ->
list[dict]`; every row carries `"section"`; reads only; never a fact outside
`view.fact_ids`, never an entity outside `view.entity_ids`; never a key
`is_secret`, `is_incorrect`, `intensity`, `internal_name`, `knowers`,
`creator_only`, `level`.
Members:
- `public_dossier(entity_id, world_id, view, db)` -- arity 2, kinds
  `("entity_id", "world_id")`, row_cap 400, context_sections `("identity",)`.
  Empty list when `entity_id` is not in `view.entity_ids`. Rows, in order:
  `{"section":"identity","entity_id","name","type"}`; one
  `{"section":"facets","label","aspect","content","secret":False}` per public
  fact having the entity as participant (any facet, `facts_of`-style creator
  exclusion), label per R-27; one `facets` row labelled `Lien` per public
  relation fact (R-26); one `{"section":"memberships","faction_name","role"}`
  per `read_public_memberships` row whose faction is public; when the entity
  is a faction, one `{"section":"members","member_name","role"}` per current,
  non-secret membership whose member is public (role `cover_role ?? role`).
- `public_factions(world_id, view, db)` -- arity 1, kinds `("world_id",)`,
  row_cap 200. One `{"section":"factions","entity_id","name","faction_type",
  "description"}` per public active faction; `description` = the joined
  public `description` facts, else None.
- `public_facts_mentioning(text, world_id, view, db)` -- arity 2, kinds
  `("text", "world_id")`, row_cap 200. Tokens as `lore_selectors.facts_mentioning`
  (`normalize_surface`, length >= 3, every token present); only facts in
  `view.fact_ids`; one `{"section":"public_mentions","content","participants"}`
  per match, `participants` = names of its participants in `view.entity_ids`,
  sorted by text then id. No token of 3+ letters: `[]`.
- `world_laws(world_id, view, db)` -- arity 1, kinds `("world_id",)`,
  row_cap 100. One `{"section":"laws","position","text"}` per `world_law`
  row by `position`.
Tables: `PERSPECTIVE_SELECTORS` (the four names, in this order),
`_PERSPECTIVE_LOOKUPS: dict[str, SelectorSpec]` (same keys),
`PERSPECTIVE_DESCRIPTIONS: dict[str, str]` (same keys, French one-liners in
the style of `_SELECTOR_DESCRIPTIONS`, given verbatim in brief D).
`SelectorSpec` is imported from `lore_selectors`; its `fn` here takes `view`
before `db`.

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

### C-06 -- binding rule
Produced by: D   Consumed by: E
A binding `{ref: entity_id}` is accepted iff `ref` is a mention of the plan
and `entity_id` is in `resolve_named(mention.surface_form, mention.category,
world_id, db, scope=<C-01 public scope>).candidate_ids`. Never
`validate_binding`, never `pre_resolved` without that test.

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

### C-14 -- the player shell
Produced by: G   Consumed by: (live gate)
Files: `frontend/jouer.html` (loads `/src/joueur/main.js`),
`frontend/src/joueur/main.js`, `JoueurApp.svelte`, `joueur.svelte.js`
(state + fetch helpers), `ProfilePicker.svelte`, `WorldList.svelte`,
`WorldPage.svelte`. Every `fetch` URL under `frontend/src/joueur/` starts
with `/api/joueur/`; no import leaves `frontend/src/joueur/`. Server:
`GET /jouer` in `app.py` returns `static/jouer.html` with
`headers={"cache-control": _REVALIDATE_CACHE_CONTROL}`.

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

## Gate output

(a) Property trace:
- `_player_character_id` uses `.first()`, raises 400 when none -> R-04,
  `crud/entities.py:209-220`.
- `_resolve_player_id` uses `.first()`, returns None when none -> R-04,
  `analyzer_transcript.py:248-255`.
- `_resolve_player_character` refuses when not exactly one -> R-04,
  `routes/day.py:124-137`.
- bootstrap turns `HTTPException` into `player_id: None` -> R-05,
  `routes/creator.py:767-771`.
- one PC per (world, user) unique partial index -> R-06, `models/canon.py:154-158`.
- PCs bind to the creator user -> R-06, `routes/creator.py:821`.
- `user.role` is a free string with default `player`, no CHECK -> R-07,
  `models/pipeline.py:706-720`.
- `user` is not a canon table -> R-07, `canon_write_policy.txt:1-13`.
- no runtime writer of `user` -> R-07/R-33, grep over `src` and `scripts`.
- `world` columns and constraints -> R-03, `models/canon.py:65-93`.
- `update_world` is an allowed `world` writer -> R-08, `canon_write_policy.txt:143`.
- `WorldUpdateBody` fields, `_world_detail` keys -> R-08, `routes/creator.py:560-621`.
- `world_sheet.py` compares listed keys only -> R-09, `checks/world_sheet.py:65-71`.
- WorldSheet PUT body -> R-10, `WorldSheet.svelte:62`.
- journal CHECK literal and step tables -> R-11, `models/pipeline.py:467-492`.
- `PAYLOAD_KEYS` keyed by step, writer validations -> R-11, `writes/lore_usage.py:27-70`.
- recorder signature -> R-11, `lore_usage.py` (whole).
- lore_usage check U0/U1/U2/U10 -> R-12, `checks/lore_usage.py:1-140, 205-217`.
- rebuild procedure -> R-13, `scripts/migrate_v2_29_rank_trials.py:141-157`.
- migration skeleton -> R-13, `scripts/migrate_v2_30_world_tone.py`.
- `resolve_public_levels` semantics -> R-14, `knowledge_resolve.py:288-330`.
- defaults never carry secrets -> R-14, `knowledge_resolve.py` docstring.
- creator-only helpers -> R-15, `facet_reads.py:58-80`.
- name regimes and `surfaces` behavior -> R-16, `name_index.py`.
- name_index check rules -> R-17, `checks/name_index.py:1-40`.
- `resolve_named` signature and verdicts -> R-18, `lore_resolve.py:143-175`.
- executor shapes and `_call_args` -> R-19, `lore_query.py`.
- creator selectors expose secrets -> R-20, `lore_selectors.py`.
- lore_selectors / lore_isolation rules -> R-21, `checks/lore_selectors.py:1-36`,
  `checks/lore_isolation.py:1-80`.
- planner fills `{selectors}` from a module constant -> R-22, `lore_plan.py:105-130`.
- planner prompt carries no selector of its own -> R-22, `seed_pilot.py:1894-1928`.
- formatters and the unknown-section raise -> R-23, `lore_render.py:37-160`.
- `render` signature and verdict gate -> R-23, `lore_render.py:295-320`.
- consultation route flow and answer keys -> R-24, `routes/lore.py`.
- `read_public_memberships` WHERE triplet, no `is_public` test -> R-25,
  `context.py:161-197`.
- typed facts have no participants; `relation_id` spine -> R-26,
  `models/canon_knowledge.py:87-146`.
- `MAP_TOPOLOGY_TYPES` -> R-26, `relation_orientation.py:30`.
- `FacetSpec.label`, `fact_texts` -> R-27, `facets.py:36, 85`, `prose_render.py:71-74`.
- Lore tabs and `$state` -> R-28, `Lore.svelte:29-31, 105-108`.
- shell routes, static serving, Vite inputs, hash source set, freshness
  rules -> R-29 (files listed there).
- origin guard -> R-30, `origin_guard.py`.
- line counts -> R-31.
- check fixture and stub patterns -> R-34, R-35 (files listed there).
- fixture writers and their signatures; laws are not facts -> R-36 (files listed there).
- the shell's mount lines -> R-37, `frontend/src/main.js`.
- INV-65 highest, budgets -> R-32.

(b) Case tables.

M2 (brief A), `_player_character_id(db, w)` / `_resolve_player_id(db, w)`:

| PCs in `w` | `_player_character_id` | `_resolve_player_id` |
|---|---|---|
| 0 | 400 `"No player character in the active world."` (unchanged) | None |
| 1 | that PC's id | that PC's id |
| 2+ | 409 `"Plusieurs personnages joueurs dans ce monde : précisez lequel."` | None |

Perspective verdicts (C-05), one row per input class:

| plan | mentions | rows outside context | verdict | rows returned |
|---|---|---|---|---|
| names a selector outside `PERSPECTIVE_SELECTORS` | -- | -- | `unsupported_selector` | none |
| valid | one ambiguous under public scope | -- | `ambiguous_mention` | none |
| valid | one unmatched (unknown, non-public, or name of a non-public entity) | -- | `nothing_known` | none |
| valid | all matched | none (identity only) | `nothing_known` | none |
| valid | all matched | some | `answered` | all |
| valid, no mention (`public_factions`, `world_laws`) | -- | some / none | `answered` / `nothing_known` | all / none |

Withheld reasons (C-07), by what the audit meets:

| met | reason |
|---|---|
| dossier subject not public | `entity_not_public` |
| fact about subject, creator-only | `creator_only` |
| fact about subject, public level `unaware` | `not_public` |
| current membership, `is_secret` | `secret_membership` |
| current membership in a non-public faction | `faction_not_public` |
| faction not public, `public_factions` | `entity_not_public` |
| matching fact not public, `public_facts_mentioning` | `creator_only` / `not_public` |
| `world_laws` | (none) |

A creator-only fact is reported `creator_only` even when its public level is
above `unaware` (creator-only is tested first).

Name regime `public` (C-01), one row per surface class:

| surface | kept |
|---|---|
| name of an active public entity | yes |
| name of an active non-public entity | no |
| name of an inactive entity | no (as every regime) |
| appellation of a public entity, fact public, not creator-only | yes |
| appellation of a public entity, fact not public | no |
| appellation of a public entity, creator-only | no |
| appellation of a non-public entity | no |

Player route answers (C-11), one row per request class:

| request | status | journaled |
|---|---|---|
| world unknown or not open | 404 `Monde introuvable.` | no |
| profile unknown / inactive / not player | 404 `Profil introuvable.` | no |
| Ollama down at ping | 503 | `perspective_ask/unavailable` |
| plan unparsable | 502 | `perspective_ask/parse_error` |
| answered or empty verdict | 200, 5 keys | `perspective_ask/ok` |
| resolve, binding refused | 422 `Choix refusé.` | `perspective_resolve/refused` |
| resolve, valid | 200, 5 keys | `perspective_resolve/ok` |

(c) Enumerations: R-01 (empty listings), R-05 (pasted), R-07 (`user`
writers: one, `seed_pilot.py:3120-3127`; `User.role` readers: one), R-12
(the census sets), R-29 (the hash source set, as written in both files),
R-31 (line counts). Negative claim "no runtime `user` writer": R-07/R-33,
from `grep -rn "User(" src scripts` and `grep -rn "INTO user" src scripts`.

(d) Family contracts: C-04 (the perspective selectors) was written before its
four members and re-read after `world_laws`; every member's row keys were
checked against the family's forbidden-key list and its formatter (C-08).
C-09 / C-10 / C-11 (the journal and both route sets) were re-read together
for the payload keys.

(e) Gates:
- `pc_resolution.py` (new, A) -- satisfied by `crud/entities.py` and
  `analyzer_transcript.py`; needs two PCs in one world, which needs two
  `user` rows (R-06): the fixture writes them directly (non-canon, R-07).
- `player_entry_schema.py` (new, B) -- satisfied by
  `migrate_v2_31_player_entry.py`; builds a v2.30-shaped database from the
  current models then `ALTER`/rebuild back to v2.30's shape for the two
  objects (drops `open_to_players`, recreates `lore_usage_event` with the
  v2.13 DDL of `migrate_v2_13_lore_usage.py`).
- `player_worlds.py` (new, C) -- satisfied by `routes/creator.py`
  (`update_world`, `_world_detail`) and `WorldSheet.svelte`; fixture R-34,
  route functions called directly as `world_sheet.py` does.
- `perspective_isolation.py` (new, D) -- satisfied by
  `perspective_selectors.py`, `perspective_query.py`, `perspective_audit.py`,
  `perspective_render.py`, `name_index.py`; needs Ollama nowhere (render is
  exercised on non-`answered` verdicts and with `chat` stubbed).
- `player_routes.py` (new, E) -- satisfied by `routes/player.py`,
  `routes/lore_perspective.py`, `writes/users.py`; `chat` and
  `ollama_client.ping` stubbed in `lore_plan`, `lore_render` and the route
  modules, as `lore_usage.py` U9 does.
- `player_shell.py` (new, F and G) -- satisfied by `Lore.svelte`,
  `PerspectivePanel.svelte`, `perspective.svelte.js`, the `frontend/src/joueur/`
  files, `app.py`, `vite.config.js`; static only.
Gates merely passed: `world_sheet.py` (R-09) by `routes/creator.py`;
`lore_usage.py` (R-12) by `models/pipeline.py`, `writes/lore_usage.py` and
the `_SCRIPTS` line; `name_index.py` (R-17) by `name_index.py`;
`lore_selectors.py`, `lore_isolation.py` (R-21) by `lore_query.py`,
`lore_plan.py`, `lore_render.py`; `static_asset_freshness.py`,
`frontend_build_fresh.py`, `legacy_mount.py` (R-29) by `app.py`,
`write-manifest.mjs`, `frontend_build_fresh.py`; `schema_version_agreement.py`,
`schema_partition.py` (R-02) by brief B's three version edits;
`claude_md_contract.py` (R-32) by brief G; `single_canon_write.py` by
`update_world` (allowed, R-08) and `user` being non-canon (R-07);
`file_map.py` by a docstring on every new module and a regenerated
`FILE_MAP.md`; `module_budget.py` (R-31).
No file is moved or renamed in this lot, so step 4's move grep does not apply.

## Drafting decisions flagged to Nia

1. Profile names are unique among active players (compared by
   `normalize_surface`), at most 80 characters.
2. `WorldUpdateBody.open_to_players` is optional; an omitted flag leaves the
   world as it is (an older client never closes a world by accident).
3. No new prompt usage: the planner and the prose prompts are reused for the
   public perspective (public rows never carry `is_incorrect`). TICKET-0127
   may add its own when beliefs must be rendered without the "false" mark.
4. The public perspective answers four kinds of question: a public dossier,
   the public factions, public facts by their words, the world's laws.
   "Who knows what" and NPC goals never reach it.
5. A name that is not public, unknown, or public with nothing public behind
   it all answer the same sentence (NOTHING_KNOWN_MESSAGE): nothing reveals
   that a hidden entity exists.
6. The perspective routes reuse `_serialize_plan` / `_deserialize_plan` from
   `routes/lore.py` by import.
7. A faction's public dossier lists its public members (W1). This makes the
   perspective selectors module a third sanctioned reader of
   `faction_membership` for prompts, with the same WHERE triplet as
   `read_public_memberships`; INV-66 names it.
8. Public event facts are not in the dossier in this lot (they are typed
   facts, reached through `event_participant`); they are still found by
   `public_facts_mentioning`.
9. The player shell keeps the chosen profile in the browser
   (`localStorage`, wrapped in try/catch); the server keeps no session.
10. The creator cockpit gets no link to `/jouer` in this lot (Nia types the
    address); a link can come with TICKET-0126.

## Amendments

(none)
