# LOT — TICKET-0092 "Names: appellations, partial and near names, every category"

## Objective and cut

The Lore question « qu'est-ce que la reine sait ? » fails today because the
resolver reads entity names only, and "la reine" is a title. This lot makes
every name surface of an entity — its name and its `appellation` facts —
resolvable through one index, under an explicit regime that says whose
surfaces count (N1c, N2b). It adds a partial-name rung (B1/N4a), near
candidates with a displayed resemblance score (B3/N5c/N9b), every entity
category on the creator surfaces (B4/N6a), and a way to record a missed
name as an appellation from the names panel (N7c, N13a).

It also closes two leaks found during RECON: the tokenizer indexed
creator-only appellations (R-01), and would have indexed appellations with
no scope (N17a). An appellation's own text is never tokenized against
itself or another appellation (N15b); its default scope becomes `rencontre`
(N14b).

**Where the lot stops.** The day chain keeps its three categories, its
`day_mention_resolution` CHECK and its `day_extract` passes (N6a); it gains
only the appellations the character knows, in `named_exact`/`named_token`
(N12a, N16a). `knowledge.subject` resolution is unchanged (N10a).
Generator `mentions` vocabulary is unchanged (R-18). No schema change, no
migration.

## Briefs in this lot

- **A** `name-index` — `name_index.py` (regimes, surfaces), both new checks, the tokenizer
  rebuilt on it (creator-only and unscoped appellations excluded; an
  appellation's own text tokenized names-only without its owner), the
  `appellation` preset becomes `rencontre`, CLAUDE.md invariant amended.
- **B** `resolver` — `lore_resolve` rungs read surfaces; `named_partial`;
  `near_candidates`; every `resolve_named` caller passes an explicit scope;
  the day chain resolves names plus known appellations; `subject_resolve`
  frozen to names and three categories.
- **C** `categories` — `object` and `other` categories for the Lore surface,
  the names panel and the tokenizer; planner vocabulary and prompt version.
- **D** `lore-and-panel-api` — near candidates in the Lore answer; the names
  panel's lookup, appellation write and bind-and-record.
- **E** `frontend` — Lore link to the panel, near candidates and appellation
  recording in the panel, `appellation` in the facts editor for every type,
  rebuilt static output.

## Dependency graph

```
A -> B -> C -> D -> E
```

- B needs A (`name_index.surfaces`, C-03).
- C needs B (`category_of_type` is introduced by B with three categories,
  C-07 widens it).
- D needs B (`near_candidates`, C-06) and C (panel candidates cover every
  category; `validate_binding` accepts `other`).
- E needs D (routes C-11, response field C-10).
- Nothing in the lot runs in parallel. Every "Done means" before E is
  verified on fixtures; the live gate runs after E.

## RECON

Fresh tarball of `main` (schema `v2.06`, TICKET-0091 artifacts present).
`[M]` measured, `[P]` measured on a scratch copy with the change simulated.
Enumerations are pasted in Gate output (c).

### R-01 — the tokenizer's name index, today
Opened: `src/world_engine/prose_tokens.py:1-222` [M].
Finding: `_build_index` (`:82-105`) selects the active entities of the world,
then `select(Fact, FactParticipant.entity_id)` joined on
`FactParticipant.fact_id == Fact.id` where `Fact.world_id == world_id` and
`Fact.facet == "appellation"` (`:88-93`), keeps pairs whose participant is an
active entity, and reads their text through `prose_render.fact_texts`
(`:95`). No creator-only filter and no scope filter exist on that query.
`tokenize(db, *, world_id, text, mentions=None)` (`:201`) builds the index on
every call. `_mention_spans` (`:179-199`) resolves generator mentions with
`resolve_named(name, category, world_id, db)` (`:191`) and accepts only
categories in `_CATEGORY_OF_TYPE.values()` (`:185`); `_CATEGORY_OF_TYPE`
(`:39`) mirrors `lore_resolve._CATEGORY_ENTITY_TYPE`; `_category` (`:174-176`)
names the category of an ambiguous span. Index keys are
`_key_words(surface)` (`:74-75`, through `normalize_surface`).
Consequence: A moves the surface query into `name_index.py` and closes the
creator-only leak there. Keys stay computed in `prose_tokens`.

### R-02 — the Lore resolver
Opened: `src/world_engine/lore_resolve.py:1-169` [M];
`tooling/verify/checks/lore_resolve.py:1-230` [M].
Finding: `_CATEGORY_ENTITY_TYPE: dict[str, str]` (`:28`, three keys);
`NAMED_RUNGS = ("named_exact", "named_token")` (`:33`); `normalize_surface`
(`:42-59`) casefolds, strips accents, drops up to three leading tokens from
`_LEADING_TOKENS` (`:35-37`: chez, le, la, les, l, du, de, des, au, aux, a), splits on
whitespace and apostrophes. `rung_named_exact` (`:62-73`) and
`rung_named_token` (`:76-94`) each `select(Entity)` of one type in the world,
names only; the token rung requires the name's tokens to be a subset of the
surface's tokens with one token of 3+ characters. `_NAMED_RUNG_LOOKUPS`
(`:97-100`). `NamedResolution` (`:103-109`). `resolve_named` (`:112-137`):
first rung with a hit; one id -> `matched`, two or more -> `ambiguous`, none
-> `unmatched`. `pre_resolved` (`:140-149`). `validate_binding` (`:152-169`)
selects an active entity of the category's type in the world.
Check rules: R1 no `db.add(`/`.commit(`/`chat(` in `lore_resolve.py`; R2 none
of the identifiers `_cast_one`, `CAST_PRECEDENCE`, `who_is_at`, `Character`
(`:33`); R3 `NAMED_RUNGS`/`_NAMED_RUNG_LOOKUPS` bijection (`:137-165`); R4
every `select(` in `lore_resolve.py` has `world_id` among the names of its
`.where(` call, and zero `select(` calls is a failure (`:167-207`); R5 no
`_normalize_surface` def in `day_concordance.py`.
Consequence: rungs become pure functions over surfaces; `validate_binding`
keeps the module's one `select(` (R4 stays non-vacuous). No identifier
`Character` may enter this module (R2), so the perceiver's known facts are
computed by the day chain, not here.

### R-03 — every caller of the resolver
Opened: enumeration E1, E5 (Gate output (c)); `subject_resolve.py:1-107`;
`lore_mentions_read.py:1-99`; `lore_query.py:94-118`;
`day_mutations.py:240-250`; `cockpit/crud/knowledge.py:56` [M].
Finding: `resolve_named` is called at `lore_query.py:108` (Lore question),
`lore_mentions_read.py:67` (names panel), `prose_tokens.py:191` (tokenizer
mentions), `subject_resolve.py:48` (reached from `day_mutations.py:246` in
play, from `cockpit/crud/knowledge.py:56` through `unresolved_subjects`, and
from `scripts/apply_ticket_0087_subject_participants.py:62`). The day chain
calls `rung_named_exact`/`rung_named_token` directly
(`day_concordance.py:147`, `:153`). `validate_binding` is called at
`lore_mentions_read.py:46` and `cockpit/routes/lore.py:123`. Six callers in
total; no other in `src/`, `scripts/`, `tooling/verify/`.
Consequence: every one of them receives an explicit scope (C-05). A default
scope would silently give the creator regime to a caller that forgot one.

### R-04 — the day concordance
Opened: `src/world_engine/day_concordance.py:1-501`;
`tooling/verify/checks/day_concordance.py:1-80, 290-320` [M]; scratch
import probe [P].
Finding: imports `normalize_surface, rung_named_exact, rung_named_token`
(`:60`). `MATCHING_RUNGS` (`:75-77`) = named_exact, named_token, named_alias,
occupation, presence. `_ConcordContext` (`:132-137`) holds `world_id`,
`place_candidate_ids`, `reachable_location_ids`. `_rung_named_exact`/
`_rung_named_token` (`:144-153`) skip non-`named` mentions and delegate.
`_rung_named_alias` (`:156-161`) returns None; its comment calls it a
structural no-op forever. `_resolve_place_candidates` (`:255-268`) builds its
own context (`:260`) and calls `_rung_named_exact`. `concord` (`:353-406`)
builds the context at `:361-365`. Check R6 pins
`EXPECTED_RUNGS = {"named_exact", "named_token", "named_alias",
"occupation", "presence"}` (`checks/day_concordance.py:74`).
Probe [P]: with `lore_resolve` importing a `name_index` that imports
`facet_reads` only inside a function, adding a module-level
`from .knowledge_resolve import resolve_levels_for_entity` to
`day_concordance.py` imports cleanly (`day_concordance`, `facet_reads`,
`prose_tokens`, `knowledge_resolve`, `day_mutations`, `cockpit.app`) and
`import_cycle.py` passes.
Consequence: the context carries the perceiver's surfaces, built once per
`concord` call; `named_alias` and its comment stay as they are (N16a).

### R-05 — what a character knows
Opened: `src/world_engine/knowledge_resolve.py:1-80, 220-232`;
`src/world_engine/facet_reads.py:108-123` [M].
Finding: resolution order (docstring `:5-27`): stored row, self (participant
of a descriptive-facet fact), rencontre, location chain, faction, world,
`fact.default_level`. `resolve_levels_for_entity(db, entity_id)` (`:220`)
returns `fact_id -> level` for every fact of the entity's world resolving
above `'unaware'`, in one pass. `known_facts_of` uses exactly this as
"known" (`facet_reads.py:108-123`).
Consequence: the perceiver regime's known set is
`frozenset(resolve_levels_for_entity(db, character.id))`.

### R-06 — creator-only facts
Opened: `src/world_engine/facet_reads.py:1-61`; `lore_selectors.py:100-120`;
`tooling/verify/checks/fact_facets.py:30-45`; `CLAUDE.md:146-153` [M].
Finding: creator-only = a stored `knowledge` row on the fact, belonging to
one of the fact's own participants, at `level = 'unaware'` and
`is_secret = 1` (`_creator_only_select`, `:42-53`).
`creator_only_fact_ids(db, fact_ids) -> set[str]` (`:56-61`) returns that
subset in one query. `include_creator_only=True` appears only at
`lore_selectors.py:116` (E7); `fact_facets.py` R7 forbids a non-`False`
`include_creator_only` keyword elsewhere. CLAUDE.md `:147-149` says "only the
Lore dossier opts in".
Consequence: `name_index` excludes creator-only appellations by calling
`creator_only_fact_ids`, never by re-deriving the shape. Its `creator`
regime does not exclude them (N2b); that is a second opt-in and the CLAUDE.md
invariant is amended to name it (A).

### R-07 — the import graph around a name index
Opened: module-level imports of `facet_reads.py:27-30`,
`knowledge_resolve.py:48-54`, `writes/knowledge.py:53-58`,
`prose_tokens.py:32-34`; `tooling/verify/checks/import_cycle.py:1-16`;
scratch probe [P].
Finding: `facet_reads -> knowledge_resolve -> writes.knowledge ->
prose_tokens -> lore_resolve` at module level. Probe [P]: a `name_index.py`
with a module-level `from .facet_reads import creator_only_fact_ids`,
imported by `lore_resolve`, makes importing any of `facet_reads`,
`lore_resolve`, `prose_tokens`, `day_concordance`, `knowledge_resolve` raise
`ImportError` (partially initialized module). With the import inside the
function, all of them import and `import_cycle.py` passes.
`import_cycle.py` (`:1-16`) builds its graph from module-level imports only
and names the function-local import the established idiom for breaking a
cycle.
Consequence: `name_index` imports `facet_reads` inside `surfaces()` only
(C-03), and a check rule forbids the module-level form.

### R-08 — the appellation facet, its preset and its writers
Opened: `src/world_engine/facets.py:30-60`; `writes/facets.py:1-261`;
`writes/facts.py:50-80`; `models/canon_knowledge.py:90-120, 163-192`;
`tooling/verify/checks/fact_facets.py:60-90` [M].
Finding: `FacetSpec("appellation", "identite", "affirmation", "location",
"Appellations", ...)` (`facets.py:38-39`). `_preset_scope`
(`writes/facets.py:58-67`): preset `"location"` gives a location scope only
when `entity.type == "location"`, else `none`; preset `"rencontre"` gives
`ScopeChoice("rencontre", entity.id)`. `add_entity_fact` (`:91-133`) calls
`tokenize` on every content (`:124`) and writes the default at level `knows`
when the scope is not `none` (`:133-137`). `edit_entity_fact` (`:241-255`)
tokenizes new text (`:252`). `create_fact`'s `default_level` defaults to
`"unaware"` (`writes/facts.py:58`). `FactDefault` (`canon_knowledge.py:163-192`)
carries `world_id`, `fact_id`, `scope_type` in world/faction/location/
rencontre, `scope_id`, `level`. `fact_facets.py:71` pins
`("appellation", "identite", "affirmation", "location", ())`.
Consequence: N14b changes one registry field and one check line. N17a reads
"has a scope" as: `fact.default_level != 'unaware'` or a `fact_default` row
with `level != 'unaware'`. Appellations written before this lot keep their
defaults (no backfill, N14b).

### R-09 — tokenizer consumers and fixtures
Opened: enumeration E4; `writes/knowledge.py:160-180`;
`tooling/verify/checks/identity_tokens.py:1-30, 170-245` [M].
Finding: `tokenize` is called at `writes/facets.py:124`, `:252`,
`writes/knowledge.py:173`, and in the fixture `identity_tokens.py:222`.
The fixture writes the appellation "la Rousse" on Maelis with
`add_entity_fact` (`:215`) and expects "La Rousse arrive." to tokenize to
Maelis (`:182`). Check R1 confines the identifier `content_raw` to models,
`writes/*.py`, `prose_render.py`, `knowledge_resolve.py`, migrations; R4
forbids `chat(` and `ollama_client` in `prose_tokens.py`.
Consequence: that fixture case holds after A only if "la Rousse" gets a
scope (N14b gives it `rencontre`) and its own text stays plain (N15b). A and
N14b ship together.

### R-10 — the Lore query
Opened: `src/world_engine/lore_query.py:1-197`;
`tooling/verify/checks/lore_isolation.py:1-70` [M].
Finding: `LoreResult` (`:48-55`) fields: verdict, rows, trace,
ambiguous_mentions, unmatched_surface_forms, rejection_reason. Four
constructions (E8: `:138`, `:151`, `:161`, `:193`); `unknown_entity` at
`:161-165`. `_resolve_mentions` (`:94-118`). lore_isolation R1/R4: no
`chat(`, `db.add(`, `.commit(` in `lore_query.py` and `lore_selectors.py`.
Consequence: `near` is a new last field with a default, set only by the
`unknown_entity` construction.

### R-11 — the Lore renderer
Opened: `src/world_engine/lore_render.py:150-260`;
`tooling/verify/checks/lore_isolation.py:36-52, 521-635` [M].
Finding: `_UNKNOWN_ENTITY_WITH_NEAR` (`:155-157`) and
`_UNKNOWN_ENTITY_WITHOUT_NEAR` (`:158-160`); `_render_unknown_entity`
(`:178-187`) always renders WITHOUT, and its docstring says no
near-candidate source exists. R10: no `select(`, `db.add(`, `.commit(`,
`Session` identifier in `lore_render.py`; R11: no model call on an empty
verdict; R13: the six message constants exist by name.
Consequence: near candidates reach the renderer inside `LoreResult`, never
through a query.

### R-12 — the Lore routes
Opened: `src/world_engine/cockpit/routes/lore.py:1-133` [M].
Finding: `_result_body` (`:76-94`) returns verdict, rows, trace, plan,
candidates, answer, renderer. lore_isolation R6: no `chat(` and no `select(`
in this file.
Consequence: the body gains `near`, copied from the result.

### R-13 — the names panel backend
Opened: `src/world_engine/lore_mentions_read.py:1-99`;
`cockpit/routes/lore_mentions.py:1-72`; `writes/mentions.py:85-113`;
`tooling/verify/checks/lore_isolation.py:57-62, 699-718` [M].
Finding: `binding_is_valid` (`:43-46`) accepts any category when the
mention's is NULL; `_candidates` (`:63-71`) unions `resolve_named` over the
categories and sorts by name; `list_open_mentions` (`:82-99`) rows carry id,
surface, reason, category, excerpt, owner, candidates. Routes (`:48-73`):
GET `/api/lore/mentions`, POST `.../{id}/resolve` (body
`MentionResolveBody{entity_id}`, `:30-31`), POST `.../{id}/dismiss`; one
commit per request; `_CHANGED_BY = "creator_crud"` (`:27`).
`bind_mention(db, *, mention, entity_id, changed_by)` (`:91-111`) raises
`ValueError` when the surface no longer occurs plain. R17: these two modules
import none of `lore_selectors`, `lore_query`, `lore_plan`, `lore_render`,
`lore_prompt`, and those import neither.
Consequence: D adds its routes here and its reads in `lore_mentions_read`;
R17 needs no change.

### R-14 — the planner's category vocabulary
Opened: `src/world_engine/lore_plan.py:1-70`;
`tooling/verify/checks/lore_isolation.py:445-476` [M].
Finding: `_MENTION_CATEGORIES = ("place", "person", "faction")` (`:23`),
kept independent of `lore_resolve` on purpose (`:18-22`); `_coerce_mention`
rejects any other category (`:58-62`). R9 compares the literals of
`_MENTION_CATEGORIES` with the key set of the dict literal assigned to
`_CATEGORY_ENTITY_TYPE` in `lore_resolve.py`, whatever its values
(`_named_dict`, `:144-153`).
Consequence: C edits both literals together; R9 needs no change.

### R-15 — the planner prompt
Opened: `scripts/seed_pilot.py:1725-1765, 2750-2764`;
`scripts/apply_ticket_0087_subject_prompt.py:1-70`;
`src/world_engine/prompt_registry.py:246-259` [M].
Finding: `LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT` (`:1734-1757`) says, at
`:1737-1739`, "(des lieux, des personnages ou des factions)" and, at
`:1741-1742`, "Chaque mention identifiée porte une catégorie parmi
EXACTEMENT trois : \"place\", \"person\", \"faction\". Il n'y a pas de
quatrième catégorie." The head is `"pt-lore-question-to-plan"`, variables
`["selectors", "question"]` (`:2754-2762`). Precedent for a live update:
`apply_ticket_0087_subject_prompt.py` refuses to run unless
`WORLD_ENGINE_ENV` is prod or test, imports the text from `seed_pilot`, and
appends a `prompt_version` through `write_prompt_version` only when the text
differs (idempotent).
Consequence: C edits the seed text verbatim and ships the same kind of
script. `danger_class: db_write`.

### R-16 — entity types and categories
Opened: `src/world_engine/models/canon.py:117-137, 482-560`;
`cockpit/crud/entities.py:123-200, 475-483, 636-650` [M];
`grep -rn '"artifact"' src` [M].
Finding: `entity.type` is free text with no CHECK. The creator CRUD registry
declares `character`, `location`, `faction`, `item`
(`ENTITY_TYPE_REGISTRY`, `:123-200`). A runtime entity is created with
`entity.type = <slug>` (`:648`). `event` is its own table with a `title`
(`canon.py:482-500`), not an entity, and cannot carry a fact participant.
`artifact` extends `entity` (`canon.py:527-546`) but no writer sets
`entity.type = "artifact"` (grep: `writes/worlds.py:33` deletion order,
`analyzer_transcript.py:96` only). `GET /api/entities` without `type`
returns every entity of the active world (`:475-483`).
Consequence: `object` claims `item`; `other` is every type no other category
claims. Events stay out (N6c, named deferral).

### R-17 — knowledge-subject resolution
Opened: `src/world_engine/subject_resolve.py:1-107`;
`tooling/verify/checks/subject_resolution.py:1-30, 140-180` [M].
Finding: `resolve_subject` walks `sorted(_CATEGORY_ENTITY_TYPE)` (`:47`),
which is `("faction", "person", "place")` today. `subject_resolution.py` A2
requires at least one `resolve_named(` Name-call in `subject_resolve.py` and
no raw bypass.
Consequence: B freezes the walk to a local tuple with the same three values
and passes the names-only scope; A2 still holds.

### R-18 — closed category sets this lot leaves alone
Opened: enumeration E6; `writes/pipeline.py:40-46`;
`entity_author.py:96-120`; `day_extract.py:40-47`;
`models/pipeline.py:175-200` [M].
Finding: `writes/pipeline.py:44` (day-mention writer), the
`day_mention_resolution` CHECK (`models/pipeline.py:179`), `day_extract`'s
`Mention.category` (`:43`), and the generator mention vocabulary
(`entity_author.py:99-106`) each hold the three categories.
Consequence: all stay (N6a; generator prompts are out of scope). The
tokenizer's index covers every entity type anyway (R-01).

### R-19 — the frontend
Opened: `frontend/src/lore/Lore.svelte:1-195`; `lore.svelte.js:1-88`;
`NamesPanel.svelte:1-86`; `namesPanel.svelte.js:1-104`;
`frontend/src/creation/FactsEditor.svelte:1-60`; `CLAUDE.md:532-534`;
`frontend/scripts/write-manifest.mjs:1-40` [M].
Finding: `Lore.svelte` switches tabs with `loreTab` (`:21`, `:84-85`) and
mounts `NamesPanel` only while the names tab is shown (`:87-88`).
`NamesPanel.svelte` labels categories in `CATEGORY_LABEL` (`:15`) and calls
`reloadForWorld()` in an `$effect` on `serverState.worldId` (`:17-20`), which
also runs on mount. `namesPanel.svelte.js` mirrors the categories in
`CATEGORY_TYPE` (`:11`), loads entities per type (`loadEntities`, `:29-35`),
builds options from candidates then search (`optionsFor`, `:52-61`), posts
`{entity_id}` on bind (`bindMention`, `:88-92`). `FactsEditor.svelte` shows, for a type
outside `TYPE_FAMILIES` (`:34-38`), only `description` (`:40-46`). The build
is `npm ci && npm run build` in `frontend/`, output committed
(`CLAUDE.md:532-534`); the manifest hashes the raw bytes of `frontend/src/**`
and four root files.
Consequence: E edits these files and rebuilds.

### R-20 — the build gate fails on the tarball
Opened: `python tooling/verify/checks/corpus_gate.py` on the tarball with
`requirements-dev.txt` installed [M].
Finding: two failures before any change. `frontend_build_fresh.py`: manifest
`source_hash 9f5b6c831fe5...` differs from the recomputed `34f53ebe8ed0...`.
`day_mutations.py` crashed under the corpus run; run alone with
`WORLD_ENGINE_ENV=test` it passes.
Consequence: briefs A-D verify the checks they name, not the full corpus.
E rebuilds, which clears the first; the corpus is run with
`WORLD_ENGINE_ENV=test` set. Whether the stale manifest is real on `main` or
an artifact of this environment was not decided here.

### R-21 — budgets
Opened: `wc -l`, `grep -c "^\s*def "` on each file this lot edits [M].
Finding (lines / functions): `lore_resolve.py` 169/6; `prose_tokens.py`
222/12; `day_concordance.py` 501/16; `lore_query.py` 197/3;
`lore_mentions_read.py` 99/7; `subject_resolve.py` 107/2; `lore_render.py`
276/18; `writes/facets.py` 261; `cockpit/routes/lore_mentions.py` 72;
`cockpit/routes/lore.py` 133; `facets.py` 103. Ceilings: 1000 lines and 40
functions per module, 80 lines per function (`module_budget.py`,
`function_length.py`).
Consequence: no module is near a ceiling; no extraction is planned.

### R-22 — canon writes from routes
Opened: `tooling/verify/checks/single_canon_write.py:1-30`;
`tooling/verify/canon_write_policy.txt:150-160`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:16100-16135` [M].
Finding: the policy attributes ORM write sites (`.add()`/`.delete()`, raw
execute) to tables; a route that calls a `writes/*` function adds no site.
0091's names panel records exactly this ("`bind_mention` calls chokepoints
only, so the canon-write policy needs no new site").
Consequence: the new appellation route calls `record_appellation`, which
calls `add_entity_fact`; no policy edit.

### R-23 — governance files
Opened: `tooling/verify/checks/claude_md_contract.py:60-180`;
`tooling/verify/checks/decisions_index.py:1-30`;
`tooling/glue/gen_decisions_index.py:40-55`; `wc -c CLAUDE.md` [M].
Finding: CLAUDE.md is 35 625 characters of a 38 000 budget, lines at most
100 characters, no `TICKET-\d`/`BRIEF-\d` in the Invariants section.
`decisions_index.py` requires `DECISIONS_INDEX.md` to equal a regeneration
(`python tooling/glue/gen_decisions_index.py`) and new headers to match
`^## .+ \(BRIEF-\d{4}(-[a-z])?..., (schema vX.YY|no schema change)\)$`.
Consequence: each brief appends one decision entry with a strict header and
regenerates the index.

### R-24 — route authentication
Opened: carried from LOT-0091 R-27 [M there].
Finding: no route authenticates; the cockpit binds `127.0.0.1:8000`.
Consequence: the new routes are guarded as Creation is. Deferral stands.

### R-25 — check fixture idioms
Opened: `tooling/verify/checks/identity_tokens.py:108-133`;
`tooling/verify/checks/day_concordance_golden.py:78-150` [M].
Finding: `identity_tokens.py` `_fresh_engine()` (`:108-118`) sets
`WORLD_ENGINE_DATABASE_URL` to a temp SQLite file, purges `world_engine`
modules from `sys.modules`, then `create_db_and_tables()`; `_world(session,
label)` (`:121-133`) adds a `World` and returns an `entity(kind, name)`
factory. `day_concordance_golden.py` builds a `Character` row per NPC or PC
with `id=entity.id, world_id, character_type, current_location_id`
(`:125-145`) and calls `concord` with `Mention(category, surface_form,
kind)` (`:223`).
Consequence: the new checks copy these two helpers (by name and body) and
this `Character` construction; they never touch Nia's DB.

## Contract sheet

Families first: the regime family (C-01, C-03) is written before any caller
(C-05); the rung family (C-04) before `resolve_named` (C-05); the panel route
family (C-11) as one entry.

### C-01 — `NameScope` and the regime family (`src/world_engine/name_index.py`, new)
Produced by: A   Consumed by: A, B, C, D
```python
REGIMES: tuple[str, ...] = ("names_only", "creator", "prose", "perceiver")

@dataclass(frozen=True)
class NameScope:
    regime: str                                   # one of REGIMES
    known_fact_ids: Optional[frozenset[str]] = None
    exclude_entity_id: Optional[str] = None
    # __post_init__ raises ValueError when: regime not in REGIMES;
    # regime == "perceiver" and known_fact_ids is None;
    # regime != "perceiver" and known_fact_ids is not None.

NAMES_ONLY = NameScope("names_only")
CREATOR = NameScope("creator")
PROSE = NameScope("prose")
```
Regime semantics (which appellation facts count; names always count):

| regime | active entity names | appellation of an active entity |
|---|---|---|
| `names_only` | all | none |
| `creator` | all | all, creator-only included |
| `prose` | all | not creator-only AND has a scope |
| `perceiver` | all | not creator-only AND `fact_id in known_fact_ids` |

"Has a scope" (N17a): `fact.default_level != 'unaware'`, or at least one
`fact_default` row for the fact with `level != 'unaware'`.
"Creator-only": the fact id is in `facet_reads.creator_only_fact_ids(db, ids)`.
`exclude_entity_id`, when set, removes that entity's name and all its
appellations, in every regime.
The regime rules live in one module-level dict literal
`_APPELLATION_RULES` keyed exactly by `REGIMES`.
Who may use `CREATOR` (or construct `NameScope("creator", ...)`):
`name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
`writes/facets.py`. Nowhere else.
Error and empty cases: see `__post_init__`.

### C-02 — `NameSurface` (`name_index.py`)
Produced by: A   Consumed by: A, B, D
```python
@dataclass(frozen=True)
class NameSurface:
    text: str               # entity.name, or the appellation rendered by prose_render.fact_texts
    entity_id: str
    entity_name: str        # entity.name, for display
    entity_type: str        # entity.type
    source: str             # "name" | "appellation"
    fact_id: Optional[str]  # None iff source == "name"
```
Text is never normalized here; callers normalize (`lore_resolve.normalize_surface`).

### C-03 — `surfaces` (`name_index.py`)
Produced by: A   Consumed by: A (`prose_tokens`), B (`lore_resolve`,
`day_concordance`), D (`writes/facets.record_appellation`)
Signature: `surfaces(db: Session, world_id: str, scope: NameScope) -> tuple[NameSurface, ...]`
Behaviour:
1. Active entities of `world_id` (`Entity.status == "active"`), minus
   `scope.exclude_entity_id`: one `source="name"` surface each.
2. Unless the regime is `names_only`: every `fact` with
   `Fact.world_id == world_id` and `Fact.facet == "appellation"`, joined to
   its `fact_participant`, whose participant is one of the entities kept in
   step 1; filtered per C-01's table; text through
   `prose_render.fact_texts`; a surface whose text is empty or None is
   skipped.
3. Order: names first, by `entity_id`; then appellations by
   `(entity_id, fact_id)`.
Every `select(` in the module has `world_id` among the names of its
`.where(` call. `creator_only_fact_ids` is imported inside `surfaces`, never
at module level (R-07). No `db.add(`, `.commit(`, `chat(`.
Error and empty cases: a world with no active entity returns `()`.

### C-04 — the rung family (`src/world_engine/lore_resolve.py`)
Produced by: B   Consumed by: B (`resolve_named`, `day_concordance`)
Every rung has the signature
`(surface_form: str, category: str, surfaces: Sequence[NameSurface]) -> Optional[list[str]]`,
considers only surfaces with `category_of_type(s.entity_type) == category`,
and returns the sorted distinct `entity_id`s that match, or `None` when none
does. Let `F = normalize_surface(surface_form)`, `TF = set(F.split())`,
`K = normalize_surface(s.text)`, `TK = set(K.split())`.

| rung | a surface matches when |
|---|---|
| `named_exact` | `F != ""` and `K == F` |
| `named_token` | `TK` non-empty, `TK <= TF`, and some token of `TK` has 3+ characters |
| `named_partial` | `TF` non-empty, every token of `TF` has 3+ characters, and `TF <= TK` |

A name and an appellation matching at the same rung are candidates of equal
rank (N11a): two distinct entity ids make the verdict `ambiguous`.
`NAMED_RUNGS = ("named_exact", "named_token", "named_partial")`, in
bijection with `_NAMED_RUNG_LOOKUPS`.

### C-05 — `resolve_named` and its callers (`lore_resolve.py`)
Produced by: B   Consumed by: B, C, D
Signature:
`resolve_named(surface_form: str, category: str, world_id: str, db: Session, *, scope: NameScope) -> NamedResolution`
(`scope` is keyword-only, no default). Builds `name_index.surfaces(db,
world_id, scope)` once, walks `NAMED_RUNGS` in order and skips
`named_partial` unless `scope.regime == "creator"` (N12a). `NamedResolution`
and its three verdicts are unchanged.
Caller table (every caller, R-03):

| caller | scope |
|---|---|
| `lore_query._resolve_mentions` | `CREATOR` |
| `lore_mentions_read._candidates` | `CREATOR` |
| `lore_mentions_read.lookup_surface` (D) | `CREATOR` |
| `prose_tokens._mention_spans` | the scope `tokenize` received (C-08) |
| `subject_resolve.resolve_subject` | `NAMES_ONLY`, categories frozen to `("faction", "person", "place")` |
| `day_concordance` (`_rung_named_exact`, `_rung_named_token`) | `NameScope("perceiver", known_fact_ids=frozenset(resolve_levels_for_entity(db, character.id)))`, surfaces built once per `concord` and carried in `_ConcordContext.surfaces` |

Error and empty cases: `KeyError`-free for any category in
`_CATEGORY_ENTITY_TYPE`; an empty surface form walks every rung and returns
`unmatched`.

### C-06 — `near_candidates` (`lore_resolve.py`)
Produced by: B   Consumed by: D
```python
NEAR_RATIO = 0.8
NEAR_LIMIT = 5

@dataclass(frozen=True)
class NearCandidate:
    entity_id: str
    name: str          # entity.name
    entity_type: str
    surface: str       # the surface text that scored highest
    score: int         # 0-100, round(ratio * 100)

def near_candidates(surface_form: str, world_id: str, db: Session, *,
                    scope: NameScope, exclude_ids: frozenset[str] = frozenset()
                    ) -> tuple[NearCandidate, ...]
```
Raises `ValueError` unless `scope.regime == "creator"` (N12a). Ignores the
category (every surface counts). With `F`, `K`, `TF`, `TK` as in C-04 and
`ratio = difflib.SequenceMatcher(None, F, K).ratio()`, a surface qualifies
when `ratio >= NEAR_RATIO`, or when `{t in TF : len(t) >= 3}` and
`{t in TK : len(t) >= 3}` share a token. Per entity keep the qualifying
surface with the highest ratio. Drop ids in `exclude_ids`. Sort by
`(-score, name.casefold(), entity_id)`, keep the first `NEAR_LIMIT`.
Empty cases: `F == ""` returns `()`; no qualifying surface returns `()`.
Never picks; display only (N5c, N9b).

### C-07 — categories (`lore_resolve.py`, `lore_plan.py`)
Produced by: B (three categories), widened by C   Consumed by: B, C, D, E
After B:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
}
def category_of_type(entity_type: str) -> Optional[str]   # None when no category claims the type
```
After C:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
    "object": ("item",), "other": (),
}
OTHER_CATEGORY = "other"
CATEGORIES: tuple[str, ...] = tuple(_CATEGORY_ENTITY_TYPE)
def category_of_type(entity_type: str) -> str   # the claiming category, else "other"
```
`validate_binding(entity_id, category, world_id, db)`: for `other`, the
entity's type is claimed by no other category; otherwise its type is in the
category's tuple; always active and in `world_id`; unknown category ->
`False`.
`lore_plan._MENTION_CATEGORIES = ("place", "person", "faction", "object", "other")`
after C (R9 parity with the dict keys).

### C-08 — `tokenize`, amended (`prose_tokens.py`)
Produced by: A (scope), B (mention path)   Consumed by: A (`writes/facets`),
`writes/knowledge.py:173` (unchanged call)
Signature:
`tokenize(db, *, world_id, text, mentions=None, scope: NameScope = PROSE) -> Tokenized`
Raises `ValueError` when `scope.regime` is not `"prose"` or `"names_only"`.
The index is built from `name_index.surfaces(db, world_id, scope)`; keys and
matching are unchanged. From B on, `_mention_spans` passes the same `scope`
to `resolve_named`. Callers for an appellation's own text pass
`NameScope("names_only", exclude_entity_id=<owner id>)` (N15b):
- `add_entity_fact` with `facet == "appellation"`: owner = `entity_id`.
- `edit_entity_fact` on a fact whose `facet == "appellation"`: owner = the
  fact's participant when it has exactly one; `NameScope("names_only")` with
  no exclusion otherwise.
Every other call keeps `PROSE`.

### C-09 — `record_appellation` (`writes/facets.py`)
Produced by: D   Consumed by: D (routes C-11)
Signature:
`record_appellation(db, *, entity_id: str, surface: str, scope_type: str, created_by: str) -> Optional[Fact]`
- `scope_type` in `("rencontre", "world", "none")`, else `ValueError`.
- `surface.strip()` empty -> `ValueError`; unknown entity -> `ValueError`.
- Duplicate: when `normalize_surface(surface)` equals `normalize_surface(s.text)`
  for some `s` in `name_index.surfaces(db, entity.world_id, CREATOR)` with
  `s.entity_id == entity_id`, return `None` and write nothing.
- Otherwise `add_entity_fact(db, entity_id=entity_id, facet="appellation",
  content=surface.strip(), created_by=created_by, scope=...)` with
  rencontre -> `ScopeChoice("rencontre", entity_id)`, world ->
  `ScopeChoice("world")`, none -> `ScopeChoice("none")`; return the fact.
- Never commits.

### C-10 — near candidates in the Lore answer
Produced by: D   Consumed by: E
`LoreResult` gains a last field `near: tuple[dict, ...] = ()`. Only the
`unknown_entity` construction sets it: one dict per unmatched surface form,
in plan order, `{"surface_form": str, "candidates": [{"entity_id", "name",
"type", "score"}, ...]}` from
`near_candidates(surface_form, world_id, db, scope=CREATOR)`.
`lore_render` adds one constant, verbatim:
```python
_NEAR_ITEM = "{nom} (ressemblance {pct} %)"
```
and `_render_unknown_entity` renders each block with
`_UNKNOWN_ENTITY_WITH_NEAR.format(surface_form=..., noms=", ".join(_NEAR_ITEM.format(nom=c["name"], pct=c["score"]) for c in candidates))`
when the surface's candidates are non-empty, else
`_UNKNOWN_ENTITY_WITHOUT_NEAR` as today. The six existing constants are not
edited. `/api/lore/ask` and `/api/lore/resolve` bodies gain
`"near": list(result.near)`.

### C-11 — the names panel API, amended (`cockpit/routes/lore_mentions.py`, `lore_mentions_read.py`)
Produced by: D   Consumed by: E
- `GET /api/lore/mentions`: each row gains `"near": [{"id", "name",
  "type", "score"}]` =
  `near_candidates(m.surface, world, db, scope=CREATOR, exclude_ids=<candidate ids>)`.
- `GET /api/lore/names/lookup?surface=<str>` -> 422 when the stripped
  surface is empty; else `{"surface": str, "candidates": [{"id", "name",
  "type"}], "near": [{"id", "name", "type", "score"}]}`; candidates = union
  over `CATEGORIES` of `resolve_named(surface, c, world, db,
  scope=CREATOR).candidate_ids`, sorted by name; near excludes them. Read in
  `lore_mentions_read.lookup_surface(db, world_id, surface) -> dict`.
- `POST /api/lore/appellations` body `{"entity_id": str, "surface": str,
  "scope_type": str = "rencontre"}` -> 422 when the entity is not an active
  entity of the world (`lore_mentions_read.entity_is_valid`: any category);
  `record_appellation(..., created_by="creator_crud")`; `ValueError` ->
  rollback, 422 with the message; one commit; returns `{"ok": true,
  "written": bool, "fact_id": str | null}`.
- `POST /api/lore/mentions/{id}/resolve` body gains
  `"record_appellation": bool = false` and `"scope_type": str =
  "rencontre"`. After `bind_mention`, when `record_appellation` is true,
  `record_appellation(db, entity_id=..., surface=mention.surface, ...)` in
  the same transaction; one commit; the response gains
  `"appellation_written": bool`.
Error cases: as today for 404 and bind's 422.

## Gate output

### (a) Property trace

One line per property a brief asserts about existing code: property ->
finding -> declaring file opened.

- tokenizer index has no creator-only or scope filter -> R-01 -> `prose_tokens.py:82-105`
- `tokenize` signature and call sites -> R-01, R-09 -> `prose_tokens.py:201`; E4
- `_mention_spans` calls `resolve_named` and filters categories -> R-01 -> `prose_tokens.py:179-199`
- `_CATEGORY_OF_TYPE` mirrors the resolver map -> R-01 -> `prose_tokens.py:38-39`
- resolver map, rungs, verdicts, `validate_binding` -> R-02 -> `lore_resolve.py:28-169`
- `lore_resolve` check rules R1-R5 (incl. R4 vacuity on zero `select(`) -> R-02 -> `checks/lore_resolve.py:1-230`
- the six resolver callers -> R-03 -> E1, E5 (grep over `src/`, `scripts/`, `tooling/verify/`)
- concordance context, rung wrappers, place helper, `named_alias` no-op -> R-04 -> `day_concordance.py:60-406`
- `EXPECTED_RUNGS` pin -> R-04 -> `checks/day_concordance.py:74`
- module-level `knowledge_resolve` import in `day_concordance` is cycle-free -> R-04 -> probe [P]
- known = above `'unaware'` via `resolve_levels_for_entity` -> R-05 -> `knowledge_resolve.py:220`; `facet_reads.py:108-123`
- creator-only shape and `creator_only_fact_ids` -> R-06 -> `facet_reads.py:42-61`
- `include_creator_only` only in `lore_selectors` -> R-06 -> E7; `checks/fact_facets.py:35-39`
- CLAUDE.md "only the Lore dossier opts in" -> R-06 -> `CLAUDE.md:146-153`
- module-level import of `facet_reads` from a name index cycles; function-local does not -> R-07 -> probe [P]; `checks/import_cycle.py:1-16`
- `appellation` preset `location` -> R-08 -> `facets.py:38-39`
- preset semantics, `add_entity_fact`/`edit_entity_fact` tokenize -> R-08 -> `writes/facets.py:58-67, 91-137, 241-255`
- `create_fact` default level `unaware` -> R-08 -> `writes/facts.py:58`
- `fact_default` columns and scope set -> R-08 -> `models/canon_knowledge.py:163-192`
- preset pinned by the facets check -> R-08 -> `checks/fact_facets.py:71`
- identity-token fixture "la Rousse" -> R-09 -> `checks/identity_tokens.py:182, 215`
- `LoreResult` fields and constructions -> R-10 -> `lore_query.py:48-55`; E8
- lore_isolation R1/R4/R6/R9/R10/R11/R13/R17 -> R-10..R-14 -> `checks/lore_isolation.py:1-70, 144-153, 445-476, 699-718`
- near messages and "never reachable" docstring -> R-11 -> `lore_render.py:155-187`
- Lore route body -> R-12 -> `cockpit/routes/lore.py:76-94`
- names panel reads, routes, bind -> R-13 -> `lore_mentions_read.py:1-99`; `cockpit/routes/lore_mentions.py:1-72`; `writes/mentions.py:91-111`
- planner categories and coercion -> R-14 -> `lore_plan.py:18-62`
- planner prompt sentences, head id, variables -> R-15 -> `scripts/seed_pilot.py:1734-1757, 2754-2762`
- live prompt update precedent -> R-15 -> `scripts/apply_ticket_0087_subject_prompt.py:1-70`
- entity types, runtime slug, `event` is not an entity, no `artifact` writer -> R-16 -> `models/canon.py:117-137, 482-546`; `cockpit/crud/entities.py:123-200, 648`; grep
- `/api/entities` without type returns all entities -> R-16 -> `cockpit/crud/entities.py:475-483`
- subject walk order and A2 -> R-17 -> `subject_resolve.py:47`; `checks/subject_resolution.py:140-180`
- closed category sets left alone -> R-18 -> E6; `writes/pipeline.py:44`; `entity_author.py:99-106`; `models/pipeline.py:179`
- frontend state, mirrors, editor filter, build -> R-19 -> the files of R-19; `CLAUDE.md:532-534`
- baseline gate failures -> R-20 -> corpus run [M]
- budgets -> R-21 -> `wc -l` [M]
- route calling a writer needs no policy site -> R-22 -> `checks/single_canon_write.py:1-30`; `ARCHITECTURE_DECISIONS.md:16100-16135`
- CLAUDE.md budgets and archaeology ban; decisions index regeneration -> R-23 -> `checks/claude_md_contract.py:60-180`; `checks/decisions_index.py:1-30`
- check fixture helpers and `Character` construction -> R-25 -> `checks/identity_tokens.py:108-133`; `checks/day_concordance_golden.py:125-145`

### (b) Case tables

**Regimes (C-01, C-03).** Fixture: entity Q (active) with appellations
a1 (scope `rencontre`), a2 (no scope, `default_level` unaware), a3
(creator-only, scope `world`); entity X (inactive) with appellation a4
(scope `world`); perceiver P knows a2 only.

| scope | Q name | a1 | a2 | a3 | X name | a4 |
|---|---|---|---|---|---|---|
| `names_only` | yes | no | no | no | no | no |
| `creator` | yes | yes | yes | yes | no | no |
| `prose` | yes | yes | no | no | no | no |
| `perceiver` (P) | yes | no | yes | no | no | no |
| `prose`, `exclude_entity_id=Q` | no | no | no | no | no | no |

Every outcome is reachable and matches N2b, N17a, N16a.

**Rungs (C-04, C-05).** Names: "Maelis Varn" (person), "La Reine Grise"
(place). Appellation "la reine" on Ysolde (person).

| surface, category, scope | exact | token | partial | verdict |
|---|---|---|---|---|
| "la reine", person, creator | Ysolde | — | — | matched Ysolde |
| "la reine", place, creator | none | none | La Reine Grise | matched (partial) |
| "Varn", person, creator | none | none | Maelis Varn | matched (partial) |
| "Varn", person, names_only | none | none | skipped | unmatched |
| "Ma", person, creator | none | none | none (token < 3) | unmatched |
| "la reine", person, creator, plus a person named "Reine" | Ysolde, Reine | — | — | ambiguous (N11a) |

**Tokenizer scope (C-08).**

| write | scope | "la reine" in text (Y holds it, scoped) | owner's own name in text |
|---|---|---|---|
| any non-appellation fact / knowledge | `prose` | token to Y | token to owner |
| appellation of X | `names_only`, exclude X | plain | plain |
| appellation of X citing "Aldric" ("la fille du vieil Aldric") | `names_only`, exclude X | plain | Aldric -> token |
| edit of an appellation with 2+ participants | `names_only` | plain | token |

**Near (C-06).** Ratios computed with `difflib` on normalized strings [P].

| `F` | surface | normalized | ratio | shared 3+ token | qualifies | score |
|---|---|---|---|---|---|---|
| maelys | Maelis | maelis | 0.833 | no | yes | 83 |
| maelys | Maelis Varn | maelis varn | 0.588 | no | no | — |
| maelys | Reine Ysolde | reine ysolde | 0.333 | no | no | — |
| reine | Reine Ysolde | reine ysolde | 0.588 | yes | yes | 59 |
| reine | La Reine Grise | reine grise | 0.625 | yes | yes | 63 |

For `F` = "reine" the order is La Reine Grise (63), then Reine Ysolde (59).

**Categories after C (C-07).**

| entity.type | `category_of_type` |
|---|---|
| location | place |
| character | person |
| faction | faction |
| item | object |
| artifact, any runtime slug, anything else | other |

**`record_appellation` (C-09).**

| input | outcome |
|---|---|
| scope_type outside the three | ValueError |
| blank surface / unknown entity | ValueError |
| surface normalizes to the entity's name or one of its appellations | None, no write |
| otherwise | one `appellation` fact, participant = entity, default per scope |

**Resolve route with `record_appellation` (C-11).**

| bind outcome | record flag | appellation outcome | response |
|---|---|---|---|
| ValueError (surface gone) | any | not attempted | 422, rollback |
| ok | false | not attempted | 200, `appellation_written: false` |
| ok | true | duplicate | 200, `appellation_written: false` |
| ok | true | written | 200, `appellation_written: true` |
| ok | true | ValueError (bad scope) | 422, rollback of both |

### (c) Enumerations

Commands run from the tarball root over `src/`, `scripts/`,
`tooling/verify/` (and `frontend/src` for E3, E6). Raw output:

```
### E1 resolve_named / pre_resolved / validate_binding call sites
src/world_engine/lore_query.py:108:            resolution = resolve_named(mention.surface_form, mention.category, world_id, db)
src/world_engine/lore_mentions_read.py:46:    return any(validate_binding(entity_id, c, mention.world_id, db) for c in categories)
src/world_engine/lore_mentions_read.py:67:        ids.update(resolve_named(mention.surface, category, mention.world_id, db).candidate_ids)
src/world_engine/prose_tokens.py:191:        resolution = resolve_named(name, category, world_id, db)
src/world_engine/lore_resolve.py:112:def resolve_named(surface_form: str, category: str, world_id: str, db: Session) -> NamedResolution:
src/world_engine/lore_resolve.py:152:def validate_binding(entity_id: str, category: str, world_id: str, db: Session) -> bool:
src/world_engine/subject_resolve.py:31:    `resolve_named(subject, category, world_id, db)` for each.
src/world_engine/subject_resolve.py:48:        result = resolve_named(subject, category, world_id, db)
src/world_engine/cockpit/routes/lore.py:123:        if not _lore_resolve.validate_binding(entity_id, mention.category, body.world_id, db):
tooling/verify/checks/subject_resolution.py:25:     to `resolve_named(` and zero `db.exec(`/`text(` calls, so the
tooling/verify/checks/subject_resolution.py:160:            "and zero resolve_named( calls — vacuous, the resolver reaches canon through neither path"

### E2 _CATEGORY_ENTITY_TYPE references
src/world_engine/lore_mentions_read.py:21:from .lore_resolve import _CATEGORY_ENTITY_TYPE, resolve_named, validate_binding
src/world_engine/lore_mentions_read.py:45:    categories = (mention.category,) if mention.category else tuple(_CATEGORY_ENTITY_TYPE)
src/world_engine/lore_mentions_read.py:64:    categories = (mention.category,) if mention.category in _CATEGORY_ENTITY_TYPE else tuple(_CATEGORY_ENTITY_TYPE)
src/world_engine/prose_tokens.py:38:# Mirror of `lore_resolve._CATEGORY_ENTITY_TYPE`, keyed by entity type.
src/world_engine/prose_tokens.py:39:_CATEGORY_OF_TYPE = {"location": "place", "character": "person", "faction": "faction"}
src/world_engine/prose_tokens.py:175:    categories = {_CATEGORY_OF_TYPE.get(info[i][1]) for i in ids if i in info}
src/world_engine/prose_tokens.py:185:        if not key or category not in _CATEGORY_OF_TYPE.values() or any(s.key == key for s in spans):
src/world_engine/lore_resolve.py:28:_CATEGORY_ENTITY_TYPE: dict[str, str] = {"place": "location", "person": "character", "faction": "faction"}
src/world_engine/lore_resolve.py:63:    entity_type = _CATEGORY_ENTITY_TYPE[category]
src/world_engine/lore_resolve.py:77:    entity_type = _CATEGORY_ENTITY_TYPE[category]
src/world_engine/lore_resolve.py:154:    matches `_CATEGORY_ENTITY_TYPE[category]`. Used by `/api/lore/resolve`
src/world_engine/lore_resolve.py:158:    entity_type = _CATEGORY_ENTITY_TYPE.get(category)
src/world_engine/subject_resolve.py:17:from .lore_resolve import _CATEGORY_ENTITY_TYPE, resolve_named
src/world_engine/subject_resolve.py:30:    """Walk `_CATEGORY_ENTITY_TYPE` in sorted key order, calling
src/world_engine/subject_resolve.py:47:    for category in sorted(_CATEGORY_ENTITY_TYPE):
src/world_engine/lore_plan.py:18:# Independent of lore_resolve._CATEGORY_ENTITY_TYPE on purpose: this is the
src/world_engine/lore_plan.py:61:        # _CATEGORY_ENTITY_TYPE lookup would KeyError on anything else.
tooling/verify/checks/lore_isolation.py:30:`_CATEGORY_ENTITY_TYPE`.
tooling/verify/checks/lore_isolation.py:447:    `lore_resolve.py`'s `_CATEGORY_ENTITY_TYPE`."""
tooling/verify/checks/lore_isolation.py:461:    entity_type_dict = _named_dict(resolve_tree, "_CATEGORY_ENTITY_TYPE")
tooling/verify/checks/lore_isolation.py:463:        fail(f"lore_isolation R9: {_rel(LORE_RESOLVE_FILE)}: _CATEGORY_ENTITY_TYPE dict literal not found")
tooling/verify/checks/lore_isolation.py:467:        fail("lore_isolation R9: _CATEGORY_ENTITY_TYPE located but holds zero keys")
tooling/verify/checks/lore_isolation.py:472:        fail(f"lore_isolation R9: _CATEGORY_ENTITY_TYPE key(s) {sorted(missing)!r} are missing from _MENTION_CATEGORIES")
tooling/verify/checks/lore_isolation.py:475:        fail(f"lore_isolation R9: _MENTION_CATEGORIES value(s) {sorted(orphan)!r} are not in _CATEGORY_ENTITY_TYPE")

### E3 appellation literals
src/world_engine/prose_tokens.py:92:        .where(Fact.world_id == world_id, Fact.facet == "appellation")
src/world_engine/facets.py:38:    FacetSpec("appellation", "identite", "affirmation", "location", "Appellations",
tooling/verify/checks/identity_tokens.py:182:        ("appellation", "La Rousse arrive.", None, "{maelis} arrive.", ()),
tooling/verify/checks/identity_tokens.py:215:        add_entity_fact(session, entity_id=maelis.id, facet="appellation", content="la Rousse",
tooling/verify/checks/fact_facets.py:71:    ("appellation", "identite", "affirmation", "location", ()),

### E4 tokenize( call sites
src/world_engine/prose_tokens.py:201:def tokenize(db: Session, *, world_id: str, text: str, mentions: Optional[list] = None) -> Tokenized:
src/world_engine/writes/facets.py:124:    tokens = tokenize(db, world_id=entity.world_id, text=content, mentions=mentions)
src/world_engine/writes/facets.py:252:    tokens = tokenize(db, world_id=fact.world_id, text=content)
src/world_engine/writes/knowledge.py:173:    result = tokenize(db, world_id=entity.world_id, text=content)
tooling/verify/checks/identity_tokens.py:200:def check_tokenize(engine) -> None:
tooling/verify/checks/identity_tokens.py:222:            result = tokenize(session, world_id=world.id, text=text.format(**tokens), mentions=mentions)
tooling/verify/checks/identity_tokens.py:244:    check_tokenize(engine)

### E5 rung functions
src/world_engine/day_concordance.py:60:from .lore_resolve import normalize_surface, rung_named_exact, rung_named_token
src/world_engine/day_concordance.py:144:def _rung_named_exact(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
src/world_engine/day_concordance.py:147:    return rung_named_exact(mention.surface_form, mention.category, ctx.world_id, db)
src/world_engine/day_concordance.py:150:def _rung_named_token(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
src/world_engine/day_concordance.py:153:    return rung_named_token(mention.surface_form, mention.category, ctx.world_id, db)
src/world_engine/day_concordance.py:247:    "named_exact": _rung_named_exact,
src/world_engine/day_concordance.py:248:    "named_token": _rung_named_token,
src/world_engine/day_concordance.py:256:    # `_rung_named_exact` ONLY — an inferred place mention never reaches this
src/world_engine/day_concordance.py:265:        result = _rung_named_exact(mention, ctx, db)
src/world_engine/lore_resolve.py:33:NAMED_RUNGS: tuple[str, ...] = ("named_exact", "named_token")
src/world_engine/lore_resolve.py:62:def rung_named_exact(surface_form: str, category: str, world_id: str, db: Session) -> Optional[list[str]]:
src/world_engine/lore_resolve.py:76:def rung_named_token(surface_form: str, category: str, world_id: str, db: Session) -> Optional[list[str]]:
src/world_engine/lore_resolve.py:98:    "named_exact": rung_named_exact,
src/world_engine/lore_resolve.py:99:    "named_token": rung_named_token,
src/world_engine/lore_resolve.py:113:    """Walks `NAMED_RUNGS` in order, stopping at the first rung whose lookup
src/world_engine/lore_resolve.py:119:    for rung_name in NAMED_RUNGS:
tooling/verify/checks/lore_resolve.py:10:R3 (bijection): `NAMED_RUNGS` and `_NAMED_RUNG_LOOKUPS` are in bijection —
tooling/verify/checks/lore_resolve.py:141:    rungs_tuple = _tuple_assign(tree, "NAMED_RUNGS")
tooling/verify/checks/lore_resolve.py:143:        fail(f"lore_resolve R3: {_rel(LORE_RESOLVE_FILE)}: NAMED_RUNGS tuple not found")
tooling/verify/checks/lore_resolve.py:147:        fail("lore_resolve R3: NAMED_RUNGS located but holds zero values")
tooling/verify/checks/lore_resolve.py:161:        fail(f"lore_resolve R3: NAMED_RUNGS value(s) {sorted(missing)!r} have no _NAMED_RUNG_LOOKUPS key")
tooling/verify/checks/lore_resolve.py:164:        fail(f"lore_resolve R3: _NAMED_RUNG_LOOKUPS key(s) {sorted(orphan)!r} are not in NAMED_RUNGS")

### E6 the three-category closed set
src/world_engine/writes/pipeline.py:44:_MENTION_CATEGORIES: tuple[str, ...] = ("place", "person", "faction")
src/world_engine/lore_plan.py:23:_MENTION_CATEGORIES: tuple[str, ...] = ("place", "person", "faction")
src/world_engine/entity_author.py:106:_MENTION_CATEGORIES = ("place", "person", "faction")
src/world_engine/models/pipeline.py:179:        CheckConstraint("category IN ('place','person','faction')", name="ck_day_mention_resolution_category"),
scripts/seed_pilot.py:1742:"place", "person", "faction". Il n'y a pas de quatrième catégorie.
frontend/src/lore/NamesPanel.svelte:15:  const CATEGORY_LABEL = Object.freeze({ place: 'lieu', person: 'personne', faction: 'faction' });
frontend/src/lore/namesPanel.svelte.js:11:const CATEGORY_TYPE = Object.freeze({ place: 'location', person: 'character', faction: 'faction' });

### E7 creator-only opt-in
src/world_engine/facet_reads.py:14:— may pass `include_creator_only=True`; `known_facts_of` has no override.
src/world_engine/facet_reads.py:56:def creator_only_fact_ids(db: Session, fact_ids: Iterable[str]) -> set[str]:
src/world_engine/facet_reads.py:71:    include_creator_only: bool = False,
src/world_engine/facet_reads.py:77:    `include_creator_only` (legal only in `lore_selectors.py`). Empty list
src/world_engine/facet_reads.py:94:    if not include_creator_only:
src/world_engine/lore_selectors.py:19:from .facet_reads import creator_only_fact_ids, facts_of, joined
src/world_engine/lore_selectors.py:107:    legal `include_creator_only=True` call site (AMENDMENT-0091-01): the
src/world_engine/lore_selectors.py:116:    rows = facts_of(db, entity_id=entity_id, facets=facets, include_creator_only=True)
src/world_engine/lore_selectors.py:117:    secret_ids = creator_only_fact_ids(db, [row.fact_id for row in rows])

### E8 LoreResult constructions
src/world_engine/lore_query.py:138:        return LoreResult(
src/world_engine/lore_query.py:151:        return LoreResult(
src/world_engine/lore_query.py:161:        return LoreResult(
src/world_engine/lore_query.py:193:    return LoreResult(
```

Negative claims and their positive look:
- "No writer sets `entity.type = "artifact"`": `grep -rn '"artifact"' src`
  -> `writes/worlds.py:33`, `analyzer_transcript.py:96` only [M].
- "No other `resolve_named` caller": E1 is the complete output.
- "`name_index` must not import `facet_reads` at module level": probe [P],
  R-07.

### (d) Family contracts

- [x] Regime family (C-01) written before `surfaces` (C-03) and before every
  caller (C-05); re-read after C-11: every scope a caller uses is one of the
  four regimes; `CREATOR` users match the C-01 list (`lore_query`,
  `lore_mentions_read`, `writes/facets`).
- [x] Rung family (C-04) written before `resolve_named` (C-05); re-read
  after C-06: `near_candidates` reuses C-04's `F`/`K`/`TF`/`TK` definitions.
- [x] Panel route family (C-11) written as one entry; re-read after C-10:
  response shapes do not collide (`near` items use `id` in C-11, `entity_id`
  in C-10; E reads each where it is produced).

### (e) Check satisfaction

Proposed gates:
- `tooling/verify/checks/name_index.py` (new, A; R6 added by B). Satisfied
  by `src/world_engine/name_index.py`. That module needs a function-local
  import of `facet_reads` (R-07): the check's rule forbids only the
  module-level import, and requires the `creator_only_fact_ids` call inside a
  function. It needs `select(` over `Fact`, `FactParticipant`, `FactDefault`,
  `Entity`: each carries `world_id` in its `.where(`. The `CREATOR`
  confinement rule reads an allow-list of four files; a listed file that
  does not use it passes (negative-existence rule).
- `tooling/verify/checks/name_resolution.py` (new in A with one
  baseline case so the ticket's arrow resolves; cases added by B, C, D). Satisfied by `lore_resolve.py`, `prose_tokens.py`,
  `day_concordance.py`, `subject_resolve.py` (B), `lore_plan.py` and the seed
  text (C), `lore_query.py`, `lore_render.py`, `lore_mentions_read.py`,
  `writes/facets.py`, `cockpit/routes/lore_mentions.py` (D). Fixtures on a
  temp SQLite file, `WORLD_ENGINE_DATABASE_URL` set before import (the
  `identity_tokens.py` idiom, R-09).

Gates merely passed:
- `lore_resolve.py` R4 (a `select(` with `world_id`): satisfied by
  `validate_binding`, which B keeps as a query.
- `lore_resolve.py` R2 (no `Character`): the perceiver set is built in
  `day_concordance.py`, not in `lore_resolve.py`.
- `lore_isolation.py` R9: `lore_plan.py` and `lore_resolve.py` edited
  together in C. R10: `lore_render.py` reads `result.near`, no Session.
  R13: the six constants untouched, a seventh added. R17: D's new reads and
  routes live in the two panel modules and import no pipeline module;
  `lore_query.py` imports `name_index` and `lore_resolve` only (neither is a
  panel module).
- `fact_facets.py` `EXPECTED_FACETS`: edited in A with the preset change.
- `identity_tokens.py` R1: `name_index.py` reads text only through
  `prose_render.fact_texts` (no `content_raw`). R3 "la Rousse": satisfied
  by N14b + N15b in A. R4: `prose_tokens.py` imports `name_index`, no model.
- `day_concordance.py` R6: `MATCHING_RUNGS` unchanged.
- `subject_resolution.py` A2: `subject_resolve.py` still calls
  `resolve_named(`.
- `import_cycle.py`: function-local import in `name_index.surfaces`
  (probe [P]).
- `single_canon_write.py`: the new route calls `record_appellation` ->
  `add_entity_fact`; no new site (R-22).
- `claude_md_contract.py`: A's amendment adds under 300 characters, no
  ticket id, lines under 100.
- `decisions_index.py`: each brief regenerates the index.
- `frontend_build_fresh.py`, `static_asset_freshness.py`,
  `effect_self_write.py`, `page_contract.py`: satisfied by E's rebuild and
  by `namesPanel.svelte.js`'s world guard (E).
- `module_budget.py`, `function_length.py`: R-21 headroom.

## Amendments

(none)
