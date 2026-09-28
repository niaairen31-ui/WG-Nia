# LOT — TICKET-0095 "Choice review (K1): Nia reviews the model's choices"

## Objective and cut

H2 (TICKET-0094) lets the model choose among narrowed candidates and stores
every call in `day_mention_choice`. K1 closes the loop: a creator list in the
Lore shell's « Noms à lier » tab shows the model's choices, and Nia agrees or
disagrees. Agreeing proposes an `appellation` for the chosen entity;
disagreeing lets her pick the right entity (or « aucune entité connue ») and
optionally record the appellation for it. The past day is never re-planned.

- **A1** — review state lives in a new append-only table `day_mention_review`
  (schema v2.08).
- **B1** — every write goes through the creator CRUD path
  (`record_appellation`, `changed_by="creator_crud"`).
- **C2** — the appellation's scope is preselected from the cited evidence
  (`world` if the cited fact is known to everyone, else `rencontre`) and Nia
  confirms it with the existing three-way select.
- **D1 / H2** — « pas d'accord » picks the right entity from a selector, or
  « aucune entité connue » (no write); the appellation is optional.
- **E2** — the list shows `accepted` choices and `rejected` ones that carry a
  chosen entity; `declined`/`failed` and `cast` are not shown; a choice from
  a 409 attempt is marked « sans plan ».
- **F1** — candidates are shown by entity name only.
- **G1** — the choice's candidates and evidence become relational (two child
  tables, backfilled from the JSON); the JSON columns stay as an audit copy
  that `src/` never reads.
- **I1** — « d'accord » carries a checkbox, checked by default.
- **J1** — only pending choices are listed; a second review is refused (409).

**Where the lot stops.** No re-review UI, no `cast` rows, no
`reputation`/`statut` writes (unreachable: R-09), no location/faction scope
picker, no change to H2 itself (`choose`, the judge, the prompt), no change to
the world cascade (R-05, deferred), no CLAUDE.md edit.

## Briefs in this lot

- **A** `storage` — closes TICKET-0094's front matter; schema v2.08: three
  tables (C-01), migration with backfill; `write_day_mention_choices` writes
  the children (C-02); `write_day_mention_review` (C-03); W2 extended; the
  0094 store check's fixture fixed (R-18); creates both new checks
  (`day_mention_review_store.py` full, `choice_review.py` with R0).
- **B** `reader` — `day_choice.excerpt_key` (C-04) and
  `lore_choices_read.py` (C-05, C-06); R17 extended; `choice_review.py` gains
  L0-L6.
- **C** `route` — `cockpit/routes/lore_choices.py` (C-07), mounted; R17
  extended; `choice_review.py` gains T1-T10.
- **D** `panel` — the Svelte panel (C-08), mounted in the « Noms à lier » tab;
  frontend build committed.

## Dependency graph

Strict chain A → B → C → D.

- A before all: both new checks must exist before any gate runs (R-22), B reads the
  child tables, C writes review rows.
- B before C: the route calls the reader.
- C before D: the panel calls the route.

## RECON

All findings taken on a fresh clone of `main` at `5349af6` (the merge of
TICKET-0094). `[M]` measured by opening the named file or by running a
prototype over it.

### R-01 — `day_mention_choice` declaration
Opened: `src/world_engine/models/pipeline.py:205-247`
Finding [M]: table `day_mention_choice`; CHECKs `category IN
('place','person','faction')`, `trigger IN ('ambiguous','near')`, `verdict IN
('accepted','rejected','declined','failed')`, `attempts IN (1, 2)`, and the
shape CHECK (`accepted` ⇒ `chosen_entity_id` set; `declined`/`failed` ⇒
NULL). `candidate_ids` and `evidence_fact_ids` are `str` columns holding JSON
arrays in display order. Indexes `idx_day_mention_choice_pass(pass_play_id)`
and `idx_day_mention_choice_world_verdict(world_id, verdict)`. The header
comment says append-only (W2), one row per model call, refused calls
included. `created_at = _created_ts()`; the next block is the
`# skill_resolution` comment at line 250.
Consequence: the table is not altered (no rebuild). The two id lists are
relationalized into two child tables (C-01, decision G1). The JSON columns
stay NOT NULL and keep being written as an audit copy that no code in `src/`
reads.

### R-02 — the choice writer and the flush-before-children precedent
Opened: `src/world_engine/writes/pipeline.py:41`, `49`, `227-264`, `266-319`
Finding [M]: `write_day_mention_choices(db, *, world_id, pass_play_id,
records)` validates every record (`_validate_day_mention_choice`, 266-291),
then constructs one `DayMentionChoice` per record with `json.dumps(...,
ensure_ascii=False)` for both lists, `db.add_all`, returns the rows; no flush,
no commit. `write_day_rewrite`'s docstring (231-240) states the rule for a
parent and its children: "the parent is flushed BEFORE the children are
constructed — without a declared ORM `relationship()` between the two".
Measured on a prototype over `main`: a `day_mention_choice` row and a child
row referencing it, added in one session with no flush in between, fail the
commit with `IntegrityError: FOREIGN KEY constraint failed` (the unit of work
does not order them); the same rows with `db.flush()` after the parent commit
cleanly.
Consequence: C-02 adds the children after one `db.flush()` of the parents.
The validate-then-construct rule is unchanged.

### R-03 — the JSON invariant and its check
Opened: `CLAUDE.md` (Invariants: "UI-visible data never lives in JSON —
relational only; enforced fail-closed by `json_ui_boundary`");
`tooling/verify/checks/json_ui_boundary.py:1-100`, `170-190` (volet c's scan)
Finding [M]: volet c scans only `Column(JSON` occurrences in `models/`; a
TEXT column holding JSON is invisible to it. The allow-list's stated doctrine
(for `Event.consequences` and others): "The FIRST UI consumer of any of these
MUST migrate it to relational storage in the same brief." K1 is the first UI
consumer of the choice's candidates and evidence.
Enumeration of today's readers (the only hits in `src/` that touch the stored
columns are the writer's `json.dumps` and the model fields; every other
`candidate_ids` is a dataclass attribute of another type):
```
$ grep -rn "candidate_ids\|evidence_fact_ids" src --include=*.py \
    | grep -v "^src/world_engine/day_concordance.py"
lore_query.py:167, lore_mentions_read.py:73, lore_resolve.py:138-236,
subject_resolve.py:30-74, cockpit/crud/knowledge.py:158, routes/day.py:448-476,
routes/lore.py:80, lore_render.py:223, day_rewrite.py:119, lore_candidates.py:*
    -> resolver / concordance dataclasses, not the stored column
writes/pipeline.py:288, 310, 311   -> the writer (validate, json.dumps)
day_choice.py:103, 186, 187        -> AmbiguousMention attr, record dict keys
models/pipeline.py:211-212, 238-239 -> the model
$ grep -rn "json.loads" src/world_engine --include=*.py | grep -i "choice\|candidate\|evidence"
llm_parse.py:55, 73                -> model-output parsing, unrelated
```
Consequence: decision G1 (relationalize). A new rule (R0 in
`choice_review.py`) keeps the JSON columns write-only in `src/`.

### R-04 — which ids can disappear: facts are hard-deleted, entities are not
Opened: `src/world_engine/writes/facts.py:121-139`;
`src/world_engine/writes/facets.py:300-304`;
`src/world_engine/cockpit/crud/facets.py:130-133`;
`src/world_engine/cockpit/crud/entities.py:817-828`; `src/world_engine/db.py:116-126`
Finding [M]: `delete_free_fact` hard-deletes a free fact after its knowledge,
defaults and participants; `remove_entity_fact` calls it for any descriptive
fact, and the creator route `delete_entity_fact` calls that. Entity deletion
in CRUD is a soft delete (`status = 'inactive'`). SQLite FK enforcement is on
(`PRAGMA foreign_keys=ON` on every connection).
Consequence: an FK from a history row to `fact(id)` would make every fact
ever cited as evidence, or written as a reviewed appellation, undeletable.
So `day_mention_choice_evidence.fact_id` and
`day_mention_review.appellation_fact_id` carry **no FK** (plain TEXT, as the
JSON was). Entity ids keep their FK, as `chosen_entity_id` does.

### R-05 — the world cascade does not know the day tables (pre-existing)
Opened: `src/world_engine/writes/worlds.py:22-95`
Finding [M]: `_SUBQUERY_SCOPED_DELETES` = conversation_message, gathering_member,
batch, pass_play, knowledge, skill, location, faction, artifact, item;
`_DIRECT_WORLD_SCOPED_DELETES` = faction_membership, relation, character,
discoverable_detail, proposed_mutation, ledger, event, gathering,
conversation, session, skill_definition, entity. None of `day_rewrite`,
`day_mention_resolution`, `day_mention_choice` appears. Measured on a
prototype over `main`: `delete_world_cascade` on a world holding one planned
day (a `day_rewrite` and a `day_mention_choice` row) fails its commit with
`IntegrityError: FOREIGN KEY constraint failed`.
Consequence: a pre-existing defect, outside this lot (a destructive path).
Named deferral: the cascade learns every day-chain table, including this
lot's three, in a ticket numbered above 0095. This lot adds no world-cascade
edit.

### R-06 — `record_appellation`
Opened: `src/world_engine/writes/facets.py:60-70`, `92-145`, `239-259`
Finding [M]: `record_appellation(db, *, entity_id, surface, scope_type,
created_by) -> Optional[Fact]`; `_APPELLATION_SCOPES = ("rencontre", "world",
"none")` (line 239). `ValueError` on a scope outside it, a blank surface or an
unknown entity. Returns `None` and writes nothing when `normalize_surface(
surface)` equals the entity's name or one of its appellations (CREATOR
regime). Otherwise `add_entity_fact(facet="appellation", content=surface.strip(),
scope=...)`: `rencontre` → a `fact_default(rencontre, entity_id, knows)`,
`world` → `fact_default(world, NULL, knows)`, `none` → no default (creator-only
by scope). Never commits. Measured on a prototype (entities "Maelis Varn",
"Maelis Orn"): appellation "Maelis" on Varn at `world` is stored plain
(`content_raw == "Maelis"`), one default `('world', 'knows')`, zero
`unresolved_mention` rows; a second call with "maelis" returns `None`;
"Maelis" on Orn at `none` writes a fact with no default.
Consequence: « agree » and « disagree » write through this function only
(decision B1, creator CRUD, `created_by="creator_crud"`). The review row's
scope vocabulary equals `_APPELLATION_SCOPES` (asserted by V7, C-03).

### R-07 — what "known to everyone" means for a fact
Opened: `src/world_engine/knowledge_resolve.py:1-37` (docstring) and `195-205`,
`255-265`, `315-330` (the `world` default and `default_level` fallback in code);
`src/world_engine/models/canon_knowledge.py:86-124` (`Fact`), `163-192`
(`FactDefault`); `src/world_engine/name_index.py:1-43`
Finding [M]: resolution tiers, most specific first: stored `knowledge` row;
self (participant of a descriptive fact); `fact_default` `rencontre`
(acquaintances); `location` (nearest ancestor); `faction` (active
membership); `world`; finally `fact.default_level` (NOT NULL, default
`'unaware'`). `fact_default` columns: `fact_id`, `scope_type` (CHECK
`world|faction|location|rencontre`), `scope_id` (NULL iff `world`, FK
entity), `level` (the six-value ladder). The `perceiver` name regime counts an
appellation only when its fact id is in the perceiver's known set.
Consequence: a cited fact is "known to everyone" when it has a
`fact_default` with `scope_type='world'` and `level <> 'unaware'`, or when its
`fact.default_level <> 'unaware'` (tier 7). That, and only that, preselects
`world` (C-05, decision C2).

### R-08 — how a written appellation changes the next concordance
Opened: `src/world_engine/day_concordance.py:81-83`, `365-425`;
`src/world_engine/lore_resolve.py:48`, `93-122`
Finding [M]: `concord` walks `MATCHING_RUNGS = ("named_exact", "named_token",
"named_alias", "occupation", "presence")` and stops at the first rung with a
hit. `named_exact`: normalized surface form equals a normalized name surface.
`named_token`: every token of the name surface is in the surface form (the
mention contains the whole name). `named_partial` (surface form ⊆ name) is NOT
a matching rung; H2 uses it only to build `near` requests. Measured on a
prototype (PC Aldric; "Maelis Varn", "Maelis Orn"): "Maelis" hits neither
`named_exact` nor `named_token` (it becomes a `near` request with both as
partial candidates); after an appellation "Maelys" on Orn at `world`, "Maelys"
hits `named_exact` on Orn alone; after an appellation "Maelis" on Varn at
`rencontre`, a PC who never met Varn still hits nothing.
Consequence: agreeing with an appellation the character can know makes the
same name resolve at `named_exact` next time, with no model call; at
`rencontre`, only for characters who met the entity. The live gate is built on
this.

### R-09 — H2 requests are named only; the judge's excerpt key
Opened: `src/world_engine/day_choice.py:39`, `93-114`, `151-178`, `181-192`
Finding [M]: `choice_requests` builds requests only from `result.ambiguous`
(named by construction, `day_concordance.py:357-358`) and from unmatched
mentions with `kind == "named"`. `judge_choice` computes
`normalized = normalize_surface(answer["extrait"].strip(_EXCERPT_EDGE))`
(line 164) with `_EXCERPT_EDGE = " \t\n\"'«»“”.,;:!?…"` (line 39) and tests
substring inclusion in `normalize_surface(" ".join(facts))` or in
`normalize_surface(declaration)`. `record_of` stores `excerpt =
answer["extrait"].strip() or None`.
Consequence: every reviewable surface form is a name, so « agree » only ever
proposes an `appellation`; the `reputation`/`statut` branch of K1 is
unreachable until `cast` rows are reviewed (Y2c, deferred). K1 must find the
cited fact with the judge's own key: C-04 extracts `excerpt_key` from the
judge, with no behaviour change (day_choice J1-J8 unchanged).

### R-10 — the evidence reader
Opened: `src/world_engine/facet_reads.py:62-104`; `src/world_engine/facets.py:37-60`
Finding [M]: `facts_of(db, *, entity_id, facets, ...) -> list[FactRow]`
(`fact_id, facet, aspect, content, created_at`), content rendered through
`prose_render.fact_texts`, creator-only facts excluded in the query, ordered by
`facets` order, `created_at`, id. `FACETS` is the registry dict. Measured: a
fact written "Elle chante à la taverne." on a world holding the location
"La Taverne" renders as "Elle chante à La Taverne." (the name was tokenized).
Consequence: K1 reads the cited facts through `facts_of(db,
entity_id=chosen, facets=tuple(FACETS))` filtered to the choice's evidence
ids, never raw `content_raw` (`identity_tokens.py` R1). Expected strings in
the checks are rendered strings.

### R-11 — plan-route ordering and timestamps ("sans plan")
Opened: `src/world_engine/cockpit/routes/day.py:506-520`, `537-541`,
`590-594`, `615-622`, `655-669`; `src/world_engine/models/canon.py:48-59`
Finding [M]: a day is planned once: `_load_plannable_day` refuses a
`pass_play` whose `status != 'submitted'`, and a successful plan sets
`status = 'resolving'` in its single commit. On the plan path,
`_write_declaration_rewrite` constructs the `DayRewrite` (generation 1)
BEFORE `write_day_mention_choices` constructs the records, both in the plan's
one transaction. On the 409 path, `_record_refused_choices` rolls back and
commits the records alone; no rewrite exists. A plan failure after the rewrite
(502) commits nothing. `_created_ts()` is a Python `default_factory`
(`datetime.now(UTC)`) evaluated at construction. Measured on a prototype: a
409-path row stamped before the rewrite, and a plan-path row stamped after it;
`any(rw.created_at <= choice.created_at)` gives `False` then `True`.
Consequence: a choice is "planned" iff some `day_rewrite` of its `pass_play`
has `created_at <= choice.created_at` (C-05). Otherwise the panel shows
"sans plan".

### R-12 — the names panel's route and reads
Opened: `src/world_engine/cockpit/routes/lore_mentions.py:1-110`;
`src/world_engine/lore_mentions_read.py:27-67`;
`src/world_engine/lore_resolve.py:38-43`, `60-65`, `241-261`
Finding [M]: the route module holds `router = APIRouter()`,
`_CHANGED_BY = "creator_crud"`, a `_world_id(db)` helper raising 400 `"No
active world. Activate a world before proceeding."`, one commit per request,
`ValueError` → `db.rollback()` + 422. `lore_mentions_read.active_world_id(db)`
returns the active world's id or `None`; `excerpt(text, surface)` returns up
to `EXCERPT_LENGTH` (80) characters around the surface (the whole text when
shorter). `validate_binding(entity_id, category, world_id, db)` is True iff
the entity is active, in the world, and of the category's types;
`CATEGORIES = ("place", "person", "faction", "object", "other")`;
`category_of_type(entity_type)`.
Consequence: the new route copies that module's shape (named, not gestured
at: C-07). The reader reuses `active_world_id` and `excerpt`.

### R-13 — the panel/pipeline isolation rule
Opened: `tooling/verify/checks/lore_isolation.py:57-63`, `86-87`, `684-720`
Finding [M]: R17 fails when a file of `PANEL_FILES`
(`cockpit/routes/lore_mentions.py`, `lore_mentions_read.py`) imports a module
whose stem is in `PIPELINE_FILES` (`lore_selectors`, `lore_query`,
`lore_plan`, `lore_render`, `lore_prompt`), or the reverse; import names are
compared by last dotted component. A file in `PANEL_FILES` that does not exist
is a failure (`_parse`).
Consequence: B adds `lore_choices_read.py` to `PANEL_FILES`; C adds
`cockpit/routes/lore_choices.py`. Each brief adds the file it creates.

### R-14 — creator-regime confinement
Opened: `tooling/verify/checks/name_index.py:17-30`, `51-58`
Finding [M]: R5 allows `CREATOR` (or `NameScope("creator")`) only in
`name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
`writes/facets.py`.
Consequence: `lore_choices_read.py` and `routes/lore_choices.py` never name
`CREATOR`; the creator regime is used only inside `record_appellation`
(allowed file).

### R-15 — append-only rule W2
Opened: `tooling/verify/checks/day_rewrite.py:9-12`, `43`, `113-165`
Finding [M]: `_TRACKED_MODELS = {"DayRewrite", "DayMentionResolution",
"DayMentionChoice"}`. W2 fails on any attribute assignment on a name bound to
a tracked instance (constructor, `db.get(Model, ...)`, or a `for` over a query
naming it) and on `db.delete(` of one, anywhere in `src/`. Vacuity: every
tracked model must be constructed somewhere in `src/`.
Consequence: A adds the three new models to `_TRACKED_MODELS` in the same
commit as the writers that construct them.

### R-16 — schema governance and the migration idiom
Opened: `src/world_engine/schema_version.py:15`; `world-engine-schema.md:3`,
`1031-1068`, `1071`; `world-engine-schema-changelog.md:14-17`;
`tooling/verify/checks/schema_partition.py:1-60`;
`scripts/migrate_v2_07_day_mention_choice.py` (whole); `src/world_engine/db.py:116-124`
Finding [M]: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.07"`; doc header
`Current schema version: v2.07`; the `### \`day_mention_choice\`` section runs
1031-1068 and `### \`skill_resolution\`` starts at 1071; newest changelog entry
`- **v2.07** — TICKET-0094, BRIEF-0094-A: ...`. The three must agree
(`schema_partition`, `schema_version_agreement`). The v2.07 script: env guard
before imports, raw `CREATE TABLE` + indexes when the table is absent, a
post-check, `_converge_schema_meta()`. Its post-check demands zero rows on
every run. `db.py` sets `isolation_level = None` so that DDL and writes share
one transaction; measured: a `CREATE TABLE` inside `engine.begin()` followed
by an exception leaves no table.
Consequence: A bumps the triple to v2.08 in one commit and ships
`scripts/migrate_v2_08_choice_review.py`. The two child tables and their
backfill run in ONE `engine.begin()` (all-or-nothing). The review table's
zero-rows post-check applies only on the run that creates it.

### R-17 — exports
Opened: `src/world_engine/models/__init__.py:98-112`, `121-190`;
`src/world_engine/writes/__init__.py:112-127`, `144`
Finding [M]: `DayMentionChoice`, `DayMentionResolution`, `DayRewrite` are
imported in the `from .pipeline import (...)` block of `models/__init__.py`
and are absent from its `__all__`. `write_day_mention_choices` and
`write_day_rewrite` are imported in the `from .pipeline import (...)` block of
`writes/__init__.py` and are absent from its `__all__`.
`record_appellation` is not re-exported (callers import
`writes.facets.record_appellation`).
Consequence: new models and the new writer join those two import blocks,
alphabetically, and stay out of `__all__`.

### R-18 — the 0094 store check's fixture
Opened: `tooling/verify/checks/day_mention_choice_store.py:52-100`, `102-195`
Finding [M]: S1 writes an `accepted` record with `candidate_ids=[maelis_id,
"autre"]` (line 119) and asserts `json.loads(row.candidate_ids) == [maelis_id,
"autre"]` (line 134). `"autre"` is not an entity id. `_record()` defaults
`candidate_ids=[]`, `evidence_fact_ids=[]`. `_parents` builds World → Session
→ Batch → two character entities → PassPlay, flushing each.
Consequence: once C-02 writes candidate rows with an FK to `entity`, S1's
`"autre"` fails the flush. A replaces it with a second real entity (S1 only);
S2-S5 are unchanged.

### R-19 — the Lore shell and the names panel (frontend)
Opened: `frontend/src/lore/Lore.svelte:1-100`; `frontend/src/lore/NamesPanel.svelte`
(whole); `frontend/src/lore/namesPanel.svelte.js:14-44`, `160-175`;
`frontend/src/creation/sheetRequest.svelte.js:30-35`;
`src/world_engine/cockpit/crud/entities.py:217-226`, `474-483`
Finding [M]: `Lore.svelte` imports `NamesPanel` (line 16) and renders it
inside `{#if loreTab === 'names'}` (96-98), after a tab bar whose second button
reads "Noms à lier". `NamesPanel.svelte` declares `SCOPE_OPTIONS` (rencontre →
"Ceux qui l'ont rencontré", world → "Tout le monde", none → "Personne"),
reloads on `serverState.worldId` in one `$effect` and loads when `visible` in
a second, and renders an entity search (`input type=search` + `select`).
`namesPanel.svelte.js` exports `DEFAULT_SCOPE = 'rencontre'` and
`categoryOf(type)`; its private `loadEntities` calls `api('/api/entities')`
and keeps `status === 'active'` rows. `GET /api/entities` returns
`_entity_summary` dicts (`id, world_id, type, name, internal_name, status,
is_public`) for the active world, ordered by type then name. `api(path,
options)` throws `Error(detail)` on a non-2xx.
Consequence: D builds a sibling component in the same tab, reusing
`categoryOf` and `api`, and fetching `/api/entities` the same way.

### R-20 — router mounting
Opened: `src/world_engine/cockpit/app.py:54-67`, `118-132`
Finding [M]: each route module is imported as `from .routes import <name> as
_routes_<name>` (alphabetical, `lore_mentions` at 58) and mounted with
`app.include_router(_routes_<name>.router)` (`lore_mentions` last, at 132).
`/api/lore/*` today: `ask`, `resolve` (`routes/lore.py`); `mentions`,
`mentions/{id}/resolve`, `names/lookup`, `appellations`,
`mentions/{id}/dismiss` (`routes/lore_mentions.py`). No `/api/lore/choices`.
Consequence: C mounts `lore_choices` right after `lore_mentions` in both
places.

### R-21 — route testing precedent
Opened: `tooling/verify/checks/name_resolution.py:38-46`, `430-460`
Finding [M]: G11 imports `fastapi.testclient.TestClient` and
`world_engine.cockpit.app.app` after `_fresh_engine()` has pointed
`WORLD_ENGINE_DATABASE_URL` at a temp file, builds its world with
`is_active=True`, and posts JSON bodies; no `with TestClient(...)` block (the
startup boot guard does not run).
Consequence: C's T rules follow G11's setup exactly.

### R-22 — governance files
Opened: `tooling/tickets/TICKET-0094-concordance-h2.md:1-15`;
`tooling/verify/checks/claude_md_contract.py:12-14`, `71`, `149-153`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:16502`, `16669-16720`;
`tooling/verify/checks/decisions_index.py:15-17`;
`tooling/verify/checks/pipeline_state.py:1-60`
Finding [M]: TICKET-0094 line 5 reads `status: live-gate`, `current_brief:`
empty (Nia reports it passed). CLAUDE.md's File-structure section is capped at
80 lines, and 0094-D recorded it at the cap (no line added). Its file-map line
`lore_*.py, subject_resolve.py  # resolver/selectors/plan/names-panel reads;
subject<->entity` already covers a `lore_choices_read.py`. Decision headers
must match `^## .+ \(BRIEF-\d{4}(-[a-z])?(, ...)*, (schema v\d+\.\d+|no schema
change)\)$`. `pipeline_state.py`'s docstring (line 22) says "at least one
arrow resolving to a real file"; its implementation (`check_section_shape`,
lines 107-114) fails on EVERY Machine-checkable arrow that does not resolve,
once `status` is in `{brief, exec, verify, live-gate, done}`. Measured: this
lot's ticket at `status: brief` fails pipeline_state on the two new checks
until they exist.
Consequence: A closes 0094 in its own commit and creates both new checks
before running any gate (pipeline_state stays red on this ticket from its
deposit until A's check files exist). No CLAUDE.md edit in this lot.
Decision headers use the lowercase brief letter.

## Contract sheet

Two families are written here first and re-read after their last member:

- **review verdict** — the values `agreed` / `disagreed` and the appellation
  scopes `rencontre` / `world` / `none`: the table CHECKs (C-01), the writer
  (C-03), the route (C-07), the panel (C-08).
- **pending row** — the dict one reviewable choice becomes (C-06): built only
  by `list_pending_choices` (C-05), returned unchanged by the GET route
  (C-07), rendered by the panel (C-08).

### C-01 — tables `day_mention_choice_candidate`, `day_mention_choice_evidence`, `day_mention_review`
Produced by: A   Consumed by: C-02, C-03, C-05, the migration
DDL (schema v2.08):
```sql
CREATE TABLE day_mention_choice_candidate (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  entity_id  TEXT NOT NULL REFERENCES entity(id)
);
CREATE UNIQUE INDEX idx_day_mention_choice_candidate_choice
  ON day_mention_choice_candidate(choice_id, ordinal);

CREATE TABLE day_mention_choice_evidence (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  fact_id    TEXT NOT NULL    -- no FK: a descriptive fact can be hard-deleted (R-04)
);
CREATE UNIQUE INDEX idx_day_mention_choice_evidence_choice
  ON day_mention_choice_evidence(choice_id, ordinal);

CREATE TABLE day_mention_review (
  id                   TEXT PRIMARY KEY,
  world_id             TEXT NOT NULL REFERENCES world(id),
  choice_id            TEXT NOT NULL REFERENCES day_mention_choice(id),
  verdict              TEXT NOT NULL CHECK (verdict IN ('agreed','disagreed')),
  entity_id            TEXT REFERENCES entity(id),
  appellation_fact_id  TEXT,  -- no FK: the appellation can be hard-deleted later (R-04)
  appellation_scope    TEXT CHECK (appellation_scope IS NULL
                                   OR appellation_scope IN ('rencontre','world','none')),
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (verdict <> 'agreed' OR entity_id IS NOT NULL)
    AND (appellation_fact_id IS NULL OR entity_id IS NOT NULL)
    AND ((appellation_fact_id IS NULL) = (appellation_scope IS NULL))
  )
);
CREATE INDEX idx_day_mention_review_choice ON day_mention_review(choice_id);
```
Meaning: a candidate row is the `ordinal`-th candidate shown to the model;
an evidence row is the `ordinal`-th fact shown, flattened across candidates
in display order (the JSON order). A review row is Nia's verdict on one
choice: `agreed` → `entity_id` is the model's choice; `disagreed` →
`entity_id` is the entity she picked, or NULL for "no known entity" (H2).
`appellation_fact_id` / `appellation_scope` are set only when an appellation
was actually written. All three tables are append-only (W2), non-canon.
`choice_id` on the review is NOT unique: J1's "one review per choice" is the
route's rule (C-07), so a later re-review needs no rebuild (A1).
Models (`src/world_engine/models/pipeline.py`): `DayMentionChoiceCandidate`,
`DayMentionChoiceEvidence`, `DayMentionReview`, fields in DDL order,
`created_at = _created_ts()` on the review only, ids `default_factory=_uuid`,
CHECK names `ck_day_mention_choice_candidate_ordinal`,
`ck_day_mention_choice_evidence_ordinal`, `ck_day_mention_review_verdict`,
`ck_day_mention_review_scope`, `ck_day_mention_review_shape`.

### C-02 — `write_day_mention_choices` (amended)
Produced by: A   Consumed by: the plan route (unchanged call sites)
Signature unchanged: `def write_day_mention_choices(db: Session, *, world_id:
str, pass_play_id: str, records: list[dict]) -> list[DayMentionChoice]`.
Record keys unchanged (the 0094 family shape: `category, surface_form,
trigger, candidate_ids, evidence_fact_ids, verdict, chosen_entity_id,
excerpt, reason, verdict_detail, attempts`).
Behaviour:
1. `records == []` → return `[]`, nothing added, no flush.
2. Validate every record (`_validate_day_mention_choice`, unchanged); any
   violation raises `ValueError` with nothing added.
3. Construct the `DayMentionChoice` rows exactly as today (the two JSON
   columns still written with `json.dumps(..., ensure_ascii=False)`: the
   audit copy), `db.add_all(rows)`, then `db.flush()`.
4. For each record and its row: one `DayMentionChoiceCandidate(choice_id=
   row.id, ordinal=i, entity_id=e)` per `e` of `record["candidate_ids"]`,
   `i` from 1; one `DayMentionChoiceEvidence(choice_id=row.id, ordinal=i,
   fact_id=f)` per `f` of `record["evidence_fact_ids"]`, `i` from 1;
   `db.add_all(children)`.
5. Return the parent rows. No commit.

### C-03 — `write_day_mention_review`
Produced by: A   Consumed by: C-07
In `src/world_engine/writes/pipeline.py`, with module constants
`_REVIEW_VERDICTS: tuple[str, ...] = ("agreed", "disagreed")` and
`_REVIEW_SCOPES: tuple[str, ...] = ("rencontre", "world", "none")` (must equal
`writes.facets._APPELLATION_SCOPES`; V7 asserts it).
Signature: `def write_day_mention_review(db: Session, *, world_id: str,
choice_id: str, verdict: str, entity_id: Optional[str],
appellation_fact_id: Optional[str], appellation_scope: Optional[str]) ->
DayMentionReview`.
Behaviour: validate, in this order, each failure raising `ValueError` whose
message starts `write_day_mention_review: ` and adding nothing:
1. `verdict` not in `_REVIEW_VERDICTS`;
2. `verdict == "agreed"` and `entity_id is None`;
3. `appellation_fact_id is not None` and `entity_id is None`;
4. `(appellation_fact_id is None) != (appellation_scope is None)`;
5. `appellation_scope is not None` and not in `_REVIEW_SCOPES`.
Then construct one `DayMentionReview`, `db.add` it, return it. No flush, no
commit.

### C-04 — `day_choice.excerpt_key`
Produced by: B   Consumed by: `judge_choice`, C-05
Signature: `def excerpt_key(excerpt: str) -> str` in
`src/world_engine/day_choice.py`, placed right above `judge_choice`. Pure.
Returns `normalize_surface(excerpt.strip(_EXCERPT_EDGE))`. `judge_choice`
line 164 becomes `normalized = excerpt_key(answer["extrait"])`; nothing else
in `judge_choice` changes.
Measured: `excerpt_key("« la forge du port. »") == "forge du port"`;
`excerpt_key(" à ") == ""`.

### C-05 — `lore_choices_read` (the reader)
Produced by: B   Consumed by: C-07
New module `src/world_engine/lore_choices_read.py`. Read-only: no `db.add`,
no commit, no `chat(`, no `CREATOR`, no import of a pipeline module (R-13,
R-14), no identifier `candidate_ids` / `evidence_fact_ids`.
- `REVIEWABLE_VERDICTS: tuple[str, ...] = ("accepted", "rejected")`.
- `is_reviewable(choice: DayMentionChoice) -> bool` — pure:
  `choice.verdict == "accepted" or (choice.verdict == "rejected" and
  choice.chosen_entity_id is not None)` (E2).
- `reviewable_choice(db, choice_id: str, world_id: str) ->
  Optional[DayMentionChoice]` — `db.get(DayMentionChoice, choice_id)`;
  `None` if absent, of another world, or not `is_reviewable`. Reviewed or
  not.
- `is_reviewed(db, choice_id: str) -> bool` — any `DayMentionReview` row with
  that `choice_id`.
- `cited_evidence(db, choice: DayMentionChoice, declaration: str) ->
  tuple[str, list[dict]]` — `key = excerpt_key(choice.excerpt or "")`;
  `len(key) < 3` → `("none", [])`. Else: the choice's evidence fact ids
  (`DayMentionChoiceEvidence` rows, ordinal order); the rows of
  `facts_of(db, entity_id=choice.chosen_entity_id, facets=tuple(FACETS))`
  whose `fact_id` is among them, in `facts_of` order; the hits are those
  rows with `key in normalize_surface(row.content)`. Hits → `("facts",
  [{"fact_id", "content", "scopes"}...])`. No hit and `key in
  normalize_surface(declaration)` → `("declaration", [])`. Otherwise
  `("none", [])`.
  `scopes` of one fact: first `{"scope_type": "world", "scope_name": None}`
  if `fact.default_level != "unaware"`; then, for each `FactDefault` of the
  fact with `level != "unaware"`, ordered by `(scope_type, id)`,
  `{"scope_type": d.scope_type, "scope_name": <entity name of d.scope_id, or
  None>}`, an entry equal to one already listed skipped.
- `preselected_scope(source: str, evidence: list[dict]) -> str` — pure:
  `"world"` iff `source == "facts"` and some entry of some evidence item's
  `scopes` has `scope_type == "world"`; else `"rencontre"` (C2).
- `list_pending_choices(db, world_id: str) -> list[dict]` — every
  `DayMentionChoice` of `world_id` with `verdict in REVIEWABLE_VERDICTS`,
  kept if `is_reviewable` and not reviewed (J1), ordered by `(created_at,
  id)`; each becomes one pending row (C-06). "planned" = some `DayRewrite`
  of the row's `pass_play_id` has `created_at <= choice.created_at` (R-11).
  Empty list when none.

### C-06 — the pending row (family)
Produced by: C-05   Consumed by: C-07 (GET, unchanged), C-08
Every key required:
```python
{
  "id": str,                      # the day_mention_choice id
  "surface_form": str, "category": str, "trigger": str,
  "verdict": str,                 # "accepted" | "rejected"
  "verdict_detail": Optional[str], "excerpt": Optional[str], "reason": Optional[str],
  "day": {
    "day_number": int,            # batch.day_number
    "character_name": str,        # entity.name of pass_play.character_id
    "declaration": str,           # lore_mentions_read.excerpt(declared_action, surface_form)
    "planned": bool,              # R-11
  },
  "chosen": {"id": str, "name": str, "type": str},
  "candidates": [{"id": str, "name": str, "type": str}, ...],   # ordinal order
  "excerpt_source": str,          # "facts" | "declaration" | "none"
  "evidence": [{"fact_id": str, "content": str,
                "scopes": [{"scope_type": str, "scope_name": Optional[str]}]}],
  "preselected_scope": str,       # "world" | "rencontre"
}
```

### C-07 — routes `/api/lore/choices`
Produced by: C   Consumed by: C-08, live play
New module `src/world_engine/cockpit/routes/lore_choices.py`, shaped like
`routes/lore_mentions.py` (R-12): `router = APIRouter()`, `_CHANGED_BY =
"creator_crud"`, a `_world_id(db)` helper raising 400 with the same detail,
one commit per request. No `select(`, no `chat(`.
- `GET /api/lore/choices` → `{"choices": list_pending_choices(db, world_id)}`.
- `POST /api/lore/choices/{choice_id}/review`, body
  `ChoiceReviewBody(verdict: str, entity_id: Optional[str] = None,
  record_appellation: bool = False, scope_type: str = "rencontre")`.
  Steps, first failure wins:
  1. no active world → 400;
  2. `reviewable_choice(...)` is `None` → 404
     `f"reviewable choice {choice_id!r} not found"`;
  3. `is_reviewed(...)` → 409 `f"choice {choice_id!r} is already reviewed"` (J1);
  4. `verdict` not in `("agreed", "disagreed")` → 422
     `"verdict must be 'agreed' or 'disagreed'"`;
  5. `agreed`: `entity_id` not `None` and `!= choice.chosen_entity_id` → 422
     `"agreed: entity_id must be omitted or equal the model's choice"`;
     the effective entity is `choice.chosen_entity_id`;
  6. `disagreed`: `entity_id is None` and `record_appellation` → 422
     `"disagreed without an entity cannot record an appellation"`;
     `entity_id == choice.chosen_entity_id` → 422
     `"disagreed: entity_id equals the model's choice"`; the effective
     entity is `entity_id` (may be `None`: H2);
  7. effective entity not `None` and not `validate_binding(effective,
     choice.category, world_id, db)` → 422
     `"entity_id is not an active entity of this category in the world"`;
  8. inside `try`: if `record_appellation`, `fact = record_appellation(db,
     entity_id=effective, surface=choice.surface_form, scope_type=
     body.scope_type, created_by=_CHANGED_BY)` (else `fact = None`); then
     `write_day_mention_review(db, world_id=world_id, choice_id=choice.id,
     verdict=body.verdict, entity_id=effective, appellation_fact_id=fact.id
     if fact else None, appellation_scope=body.scope_type if fact else None)`;
     `except ValueError` → `db.rollback()`, 422 `str(exc)`;
  9. `db.commit()`; return `{"ok": True, "id": choice_id,
     "appellation_written": fact is not None}`.
  Nothing is written on any failure path. The past day, its rewrite and its
  resolutions are never touched.
Mounted in `cockpit/app.py` right after `lore_mentions`.

### C-08 — the review panel
Produced by: D   Consumed by: Nia (live gate)
Files: `frontend/src/lore/ChoiceReviewPanel.svelte`,
`frontend/src/lore/choiceReview.svelte.js`; `Lore.svelte` renders
`<ChoiceReviewPanel visible={active} />` right after `<NamesPanel ... />`,
inside the same `{#if loreTab === 'names'}` block.
State module (`choiceReview.svelte.js`), same shape as
`namesPanel.svelte.js`: `reviewState = $state({loading, error, choices: [],
entities: null, record: {}, scope: {}, target: {}, query: {}, busy: {}})`;
`loadChoices()` (GET, then the active entities via `api('/api/entities')`
filtered to `status === 'active'`), `reloadForWorld()`, setters, and
`agree(id)` / `disagree(id)` (POST; on success the row leaves `choices`).
Per row the panel shows, in French:
- head: « {surface_form} » · catégorie · « ambigu » (`ambiguous`) or « nom
  proche » (`near`) · « Jour {day_number} — {character_name} » and, when
  `!day.planned`, a « sans plan » badge;
- the declaration excerpt;
- « Choix du modèle : {chosen.name} », then « accepté » or « refusé par le
  juge — {verdict_detail} »;
- « Extrait : « {excerpt} » » and « Raison : {reason} » when present;
- « Candidats : » the candidate names, comma-separated (F1: names only);
- evidence: each cited fact's content with its scopes (world → « tout le
  monde », location/faction/rencontre → « lieu / faction / rencontre :
  {scope_name} »); `declaration` → « extrait tiré de la déclaration »;
  `none` → « preuve introuvable »;
- « D'accord » block: a checkbox « Enregistrer « {surface_form} » comme
  appellation de {chosen.name} », **checked by default** (I1), and the scope
  select (the three `SCOPE_OPTIONS` labels) preset to `preselected_scope`;
  button « D'accord » → `{verdict: "agreed", record_appellation, scope_type}`;
- « Pas d'accord » block: a search input and a select whose options are
  « — choisir — » (value `""`), « Aucune entité connue » (value `"none"`,
  H2), then the active entities of the row's category (`categoryOf`), the
  model's choice excluded, filtered by the search text; a checkbox
  « Enregistrer aussi comme appellation », **unchecked by default**, disabled
  unless an entity is selected; a scope select preset to `rencontre`; button
  « Pas d'accord », disabled while the select is on « — choisir — » →
  `{verdict: "disagreed", entity_id: <id, or null for "none">,
  record_appellation, scope_type}`.
- empty list → « Aucun choix à revoir. »

## Gate output

### (a) Property trace

| Property | Finding | Declaring file opened |
|---|---|---|
| choice table columns, CHECKs, JSON-in-TEXT, indexes | R-01 | `models/pipeline.py` |
| writer validates then constructs; flush-before-children rule; FK failure without flush (measured) | R-02 | `writes/pipeline.py` |
| JSON invariant; volet c scope; first-UI-consumer doctrine; zero readers | R-03 | `CLAUDE.md`, `checks/json_ui_boundary.py`, grep of `src/` |
| facts hard-deletable, entities soft-deleted, FK pragma | R-04 | `writes/facts.py`, `writes/facets.py`, `crud/facets.py`, `crud/entities.py`, `db.py` |
| cascade lists omit day tables; failure measured | R-05 | `writes/worlds.py` |
| `record_appellation` contract and measured outputs | R-06 | `writes/facets.py` |
| resolution tiers; `default_level`; `fact_default` shape; perceiver regime | R-07 | `knowledge_resolve.py`, `models/canon_knowledge.py`, `name_index.py` |
| rung order and semantics; appellation effect measured | R-08 | `day_concordance.py`, `lore_resolve.py` |
| requests named only; judge key; stored excerpt | R-09 | `day_choice.py` |
| `facts_of` shape and rendering (measured) | R-10 | `facet_reads.py`, `facets.py` |
| plan once; rewrite before records; `_created_ts` at construction; detection measured | R-11 | `routes/day.py`, `models/canon.py` |
| route module shape; `active_world_id`; `excerpt`; `validate_binding` | R-12 | `routes/lore_mentions.py`, `lore_mentions_read.py`, `lore_resolve.py` |
| R17 mechanics | R-13 | `checks/lore_isolation.py` |
| CREATOR allow-list | R-14 | `checks/name_index.py` |
| W2 mechanics and vacuity | R-15 | `checks/day_rewrite.py` |
| version triple; migration idiom; DDL atomicity (measured) | R-16 | `schema_version.py`, schema doc, changelog, `checks/schema_partition.py`, v2.07 script, `db.py` |
| export blocks, `__all__` absence | R-17 | `models/__init__.py`, `writes/__init__.py` |
| 0094 fixture's `"autre"` id | R-18 | `checks/day_mention_choice_store.py` |
| Lore shell, names panel, `categoryOf`, `api`, `/api/entities` shape | R-19 | the four frontend files, `crud/entities.py` |
| router import/mount lines; `/api/lore/*` inventory | R-20 | `cockpit/app.py`, `routes/lore.py`, `routes/lore_mentions.py` |
| TestClient setup | R-21 | `checks/name_resolution.py` |
| 0094 status; File-structure cap; header regex; arrow rule | R-22 | `TICKET-0094-...md`, `checks/claude_md_contract.py`, `ARCHITECTURE_DECISIONS.md`, `checks/decisions_index.py`, `checks/pipeline_state.py` |

Presuppositions named: "shaped like `routes/lore_mentions.py`" (R-12),
"copy the v2.07 migration idiom" (R-16), "same shape as
`namesPanel.svelte.js`" (R-19), "the G11 setup" (R-21), "the `_parents`
fixture of `day_mention_choice_store.py`" (R-18). Every expected literal in
the briefs (L and T rules, V rules, `excerpt_key`) comes from a prototype run
over `main` at `5349af6`.

### (b) Case tables

**(b1) Inclusion in the pending list (C-05):**

| choice | reviewed? | listed |
|---|---|---|
| `accepted` (chosen set) | no | yes |
| `accepted` | yes | no (J1) |
| `rejected`, chosen set | no | yes (E2) |
| `rejected`, chosen NULL (out of range) | — | no |
| `declined` / `failed` | — | no (E2) |
| another world | — | no |

**(b2) Excerpt source and preselected scope (C-05):**

| excerpt key | in a cited fact of the chosen entity | in declaration | source | preselect |
|---|---|---|---|---|
| < 3 chars (or NULL) | — | — | none | rencontre |
| ≥ 3 | yes, a hit has a `world` scope | — | facts | world |
| ≥ 3 | yes, no hit has a `world` scope | — | facts | rencontre |
| ≥ 3 | no | yes | declaration | rencontre |
| ≥ 3 | no (fact edited, deleted, or excerpt spans two facts) | no | none | rencontre |

A `world` scope = `fact.default_level != 'unaware'` or a `fact_default`
`world` above `unaware` (R-07). « Pas d'accord »'s scope is always preset to
`rencontre` (the evidence speaks for the wrong entity).

**(b3) Review route (C-07):**

| input | status | writes |
|---|---|---|
| no active world | 400 | nothing |
| unknown / other world / not reviewable | 404 | nothing |
| already reviewed | 409 | nothing |
| verdict not agreed/disagreed | 422 | nothing |
| agreed, entity_id ≠ chosen | 422 | nothing |
| agreed, no record | 200, `appellation_written: false` | review(agreed, chosen) |
| agreed, record, new surface | 200, `true` | appellation + review(fact, scope) |
| agreed, record, surface already known | 200, `false` | review(agreed, chosen), no fact |
| any record with bad scope | 422 | nothing (rollback) |
| disagreed, entity NULL, no record | 200, `false` | review(disagreed, NULL) |
| disagreed, entity NULL, record | 422 | nothing |
| disagreed, entity = chosen | 422 | nothing |
| disagreed, entity of another category / inactive | 422 | nothing |
| disagreed, entity, record | 200, `true`/`false` | [appellation +] review(disagreed, entity) |

**(b4) "planned" (R-11):**

| path that wrote the choice | rewrite of that pass_play before it? | planned |
|---|---|---|
| 409 (`_record_refused_choices`) | no (a day plans once, after) | false → « sans plan » |
| plan path | yes (generation 1, same transaction, constructed first) | true |
| plan path that failed later (502) | — | never stored |

**(b5) Migration states (R-16):**

| candidate table | evidence table | review table | action |
|---|---|---|---|
| absent | absent | any | create both + backfill, one transaction |
| present | present | any | skip children |
| exactly one present | | | abort, no write (impossible after an atomic run) |
| any | any | absent | create; post-check 0 rows |
| any | any | present | skip; no row-count demand |

Backfill aborts, writing nothing, when a JSON value is not a list of str or
a candidate id is not an `entity.id`. Post-check (every run): candidate rows ==
Σ len(candidate_ids), evidence rows == Σ len(evidence_fact_ids).

### (c) Enumerations

```
$ grep -rn "candidate_ids\|evidence_fact_ids" src --include=*.py   (see R-03: zero reads of the stored columns)
$ grep -rn "@router\.\(get\|post\)(\"/api/lore" src/world_engine/cockpit/routes/
routes/lore.py:97 /api/lore/ask ; :115 /api/lore/resolve
routes/lore_mentions.py:59 /mentions ; :64 /mentions/{id}/resolve ; :83 /names/lookup ;
                        :91 /appellations ; :105 /mentions/{id}/dismiss
$ grep -rn "write_day_mention_choices\|DayMentionChoice" tooling/verify/checks/*.py
day_choice.py:541-553 (static W4/W3 call names only) ; day_rewrite.py:10, 43 ; day_mention_choice_store.py
$ grep -rln "Lore.svelte\|NamesPanel\|namesPanel" tooling/verify/checks/   -> (none)
$ cascade lists: see R-05 (no day table)
```
Consequences: no route collision; only the 0094 store check writes choice
rows with fake ids (R-18); no check pins the Lore shell's markup.

### (d) Contracts
Families "review verdict" and "pending row" written first (C-00), re-read
after C-08: the verdict values appear in C-01's CHECK, C-03's
`_REVIEW_VERDICTS`, C-07 step 4 and C-08's two buttons; the scopes in C-01,
C-03 (`_REVIEW_SCOPES` == `_APPELLATION_SCOPES`, V7) and C-08's select; the
pending-row keys are produced once (C-05) and read unchanged by C-07/C-08
(prototype output carried every key). ✔

### (e) Gates and satisfying modules

| Gate | Satisfied by | Needs vs forbids |
|---|---|---|
| `day_mention_review_store.py` (new, A) | models + both writers (A) | temp SQLite only |
| `choice_review.py` (new) | A: writers keep `json.dumps` (R0 vacuity); B: `lore_choices_read.py`, `excerpt_key`; C: `routes/lore_choices.py` via TestClient | no Ollama, no prod DB |
| `day_mention_choice_store.py` (existing) | A's fixture fix (R-18) | real entity ids |
| `day_choice.py` J1-J8, W1-W5 | `excerpt_key` is behaviour-identical; route untouched | nothing |
| `day_rewrite.py` W2 | three new models, constructed only in writers | no attribute assignment after add |
| `lore_isolation.py` R17 | new panel files import no pipeline module | nothing |
| `name_index.py` R5 | new files never name `CREATOR` | nothing |
| `identity_tokens.py` R1 | reader uses `facts_of`, never `content_raw` | nothing |
| `json_ui_boundary.py` | no new `Column(JSON` | nothing |
| `single_canon_write.py` | new tables non-canon; appellation through `add_entity_fact` chokepoints | nothing |
| `schema_version_agreement.py`, `schema_partition.py` | A's triple bump | nothing |
| `module_budget.py`, `function_length.py` | `writes/pipeline.py` 319 → ~390; new modules < 250; Svelte < 300 | nothing |
| `import_cycle.py` | `lore_choices_read` imports `day_choice`, `facet_reads`, `lore_mentions_read`; nothing imports it but the route | verified in B |
| `frontend_build_fresh.py` | D rebuilds and commits `static/` | Node at build time |
| `decisions_index.py`, `pipeline_state.py`, `corpus_gate.py` | per brief | nothing |

## Amendments

(none)
