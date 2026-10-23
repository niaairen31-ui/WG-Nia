<!-- slug: public-perspective -->
# BRIEF 0125-D — "The public perspective: what everybody knows"

Lot: LOT-0125-player-entry.md (authoritative on conflict)
Depends on: nothing in this lot (placed after C by choice)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/knowledge_resolve.py:312` -> `resolve_public_levels(db, world_id) -> dict[str, str]`, every fact of the world, world default else `fact.default_level` (R-14).
- `src/world_engine/facet_reads.py:58-63` -> `creator_only_fact_ids(db, fact_ids) -> set[str]` (R-15).
- `src/world_engine/name_index.py:33-56` -> `REGIMES` (4 regimes), `_APPELLATION_RULES`, `NameScope.__post_init__` as R-16.
- `src/world_engine/name_index.py` `surfaces` -> names of every active entity, then `_kept_pairs` (R-16).
- `src/world_engine/lore_resolve.py:143-144` -> `resolve_named(surface_form, category, world_id, db, *, scope)` (R-18).
- `src/world_engine/lore_query.py:66` -> `def validate_plan(plan: LorePlan, db: Session) -> PlanValidation:` reading `SELECTORS` / `_SELECTOR_LOOKUPS` (R-19).
- `src/world_engine/lore_query.py:157` -> `_call_args(call_args, arg_kinds, world_id, resolutions)` (R-19).
- `src/world_engine/lore_selectors.py` -> `SelectorSpec(fn, arity, row_cap, arg_kinds, context_sections=())` (R-20).
- `src/world_engine/lore_plan.py` -> `draft_plan(question, world_id, db, exchanges=None)` filling `{selectors}` from `_SELECTOR_DESCRIPTIONS` via `_render_selectors()` (R-22).
- `src/world_engine/lore_render.py:114-125` -> `_SECTION_FORMATTERS` with the ten sections of R-23; `render(result, question, spec, candidates, exchanges=None)` (R-23).
- `src/world_engine/context.py:161` -> `read_public_memberships(entity_id, session)` (R-25).
- `src/world_engine/relation_orientation.py:30` -> `MAP_TOPOLOGY_TYPES` (R-26).
- `src/world_engine/facets.py:85` -> `FACETS`; `prose_render.py:71` -> `fact_texts` (R-27).

Halt if any has moved.

## Facts carried

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
### R-31 -- module budgets of edited files
Opened: `wc -l` at `2e4e140`.
Finding: `routes/creator.py` 963, `models/canon.py` 961,
`models/pipeline.py` 811, `crud/entities.py` 923, `analyzer_transcript.py`
931, `lore_query.py` 244, `lore_plan.py` 130, `lore_render.py` 320,
`name_index.py` 138, `routes/lore.py` 184, `app.py` 329,
`frontend/src/lore/Lore.svelte` 237.
Consequence: every edit in this lot adds under 30 lines to any of these;
none crosses 1000. New modules start small.
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

## Context

The player may question the lore on what everybody knows (E1', N1). The
creator pipeline cannot serve him even filtered (R-20): this brief builds a
sibling pipeline -- public name regime, four public selectors, an executor,
an audit of what was withheld, a renderer -- reusing the planner, the plan
validation and the prose renderer. No route here (E).

## Scope IN

Commit 1 -- **the shared pieces** (behavior unchanged for every existing caller):
1. `name_index.py`: `REGIMES` gains `"public"` (last); `_APPELLATION_RULES`
   gains `"public": (True, True, False, True)`; `NameScope.__post_init__`
   requires `known_fact_ids` for `perceiver` and `public` and refuses it for
   every other regime (messages: `"the {regime} regime needs known_fact_ids"`,
   `"known_fact_ids is only for the perceiver and public regimes, not {regime!r}"`);
   in `surfaces`, when `scope.regime == "public"`, the entity list keeps only
   `e.is_public` entities (filter applied where `exclude_entity_id` is
   applied, before names and appellations are built). Docstring: add the
   `public` bullet: "`public`: like `perceiver` with the public fact set,
   and only entities whose `is_public` is true (TICKET-0125, U1)."
2. `lore_query.py`: `validate_plan(plan, db, *, lookups=None)`; inside,
   `lookups = _SELECTOR_LOOKUPS if lookups is None else lookups`, and the
   membership test reads `call.selector not in lookups`. Docstring sentence:
   "`lookups` (TICKET-0125, C-02) validates against another selector table;
   omitted, the creator's." No other line of `lore_query.py` changes (R-21:
   no verdict literal added).
3. `lore_plan.py`: `draft_plan(question, world_id, db, exchanges=None, *,
   descriptions=None)`; `_render_selectors(descriptions)` renders the given
   dict, `None` -> `_SELECTOR_DESCRIPTIONS`. Docstring sentence:
   "`descriptions` (TICKET-0125, C-03) plans over another selector list with
   the same prompt."
4. `lore_render.py`: three formatters and three `_SECTION_FORMATTERS`
   entries, per C-08:
   ```python
   def _format_members(row: dict) -> str:
       role = f" ({row['role']})" if row.get("role") else ""
       return f"{row.get('member_name')}{role}"

   def _format_laws(row: dict) -> str:
       return f"{row.get('text')}"

   def _format_public_mentions(row: dict) -> str:
       line = f"« {row.get('content')} »"
       if row.get("participants"):
           line += " -- " + ", ".join(row["participants"])
       return line
   ```
   keys `"members"`, `"laws"`, `"public_mentions"`. The module docstring's
   section-contract comment gains: "members, laws, public_mentions from the
   public perspective (TICKET-0125)."

Commit 2 -- **the perspective modules** (new files, each with a module
docstring whose first sentence names its role):
5. `src/world_engine/perspective_selectors.py` -- C-04, exactly. Notes:
   - `public_view`: one `resolve_public_levels` call, one
     `creator_only_fact_ids` call over the facts it keeps, one entity query
     (`Entity.world_id == world_id`, `Entity.status == "active"`,
     `Entity.is_public == True`).
   - A participant fact of `public_dossier`: `select(Fact)` joined to
     `FactParticipant` on the entity, `Fact.world_id == world_id`, then kept
     iff `fact.id in view.fact_ids`; ordered by facet (registry order of
     `FACETS`, unknown last), then `created_at`, then id.
   - A relation fact: `select(Fact, Relation)` with `Fact.relation_id ==
     Relation.id`, `Relation.world_id == world_id`, the entity on either end,
     `Relation.type.not_in(MAP_TOPOLOGY_TYPES)`, the other end in
     `view.entity_ids`, `fact.id in view.fact_ids`; label `Lien`.
   - Members of a faction: `select(FactionMembership)` where
     `faction_id == entity_id`, `left_at IS NULL`, `is_secret == False`,
     member in `view.entity_ids`; role `cover_role if cover_role is not None
     else role`; ordered by member name. Comment above it: "Third sanctioned
     reader of `faction_membership` for a model prompt (INV-03, INV-66): the
     same WHERE triplet as `read_public_memberships`, keyed by faction."
   - `PERSPECTIVE_DESCRIPTIONS`, verbatim:
     ```python
     PERSPECTIVE_DESCRIPTIONS: dict[str, str] = {
         "public_dossier": (
             "public_dossier(entity_id, $world) -- ce que tout le monde sait sur UNE "
             "entite nommee : son nom, ses faits publics, ses liens et appartenances publics."
         ),
         "public_factions": (
             "public_factions($world) -- une ligne par faction connue de tous."
         ),
         "public_facts_mentioning": (
             'public_facts_mentioning("text:<mots>", $world) -- les faits connus de tous '
             "dont le texte contient ces mots (un sujet qui n'est pas une entite nommee)."
         ),
         "world_laws": (
             "world_laws($world) -- les lois fondamentales du monde, connues de tous."
         ),
     }
     ```
   - Every `select(` carries a `world_id` constraint in its `.where(`, or
     joins `Entity` with one.
6. `src/world_engine/perspective_query.py` -- C-05 and C-06, exactly.
   `BindingRefused(ValueError)`. Imports `LorePlan`, `TEXT_PREFIX`,
   `validate_plan`, `_call_args` from `lore_query`; `resolve_named` from
   `lore_resolve`; `NameScope` from `name_index`. Candidate names and types
   read from `Entity` restricted to `view.entity_ids`. A `verdict = "..."`
   literal appears only with the four values of `PERSPECTIVE_VERDICTS`.
7. `src/world_engine/perspective_audit.py` -- C-07, exactly. It reuses
   `perspective_selectors` helpers for the fact/relation/membership queries
   (no second copy of a query: the selectors module exposes them as private
   functions the audit imports, e.g. `_participant_facts`,
   `_relation_facts`, `_current_memberships`).
8. `src/world_engine/perspective_render.py` -- C-08, exactly. No `Session`
   identifier, no `select(`, no `chat(`.

Commit 3 -- **the check** `tooling/verify/checks/perspective_isolation.py`,
docstring first sentence "G1 check for TICKET-0125 (BRIEF-0125-D) -- the
public perspective returns only what everybody knows, and its audit names
every line it withheld.", rules:
- **PI1** -- static isolation: `perspective_selectors.py`,
  `perspective_query.py`, `perspective_audit.py`, `perspective_render.py`
  contain no `chat(`, `db.add(`, `.commit(`, `include_creator_only`,
  `CREATOR`, `NameScope("creator"`, `near_candidates`, `validate_binding`,
  and import none of `entity_dossier`, `who_knows_about`,
  `facts_mentioning`, `world_factions` from `lore_selectors`.
  `perspective_render.py` contains no `Session` and no `select(`.
- **PI2** -- tables: `PERSPECTIVE_SELECTORS`, `_PERSPECTIVE_LOOKUPS`,
  `PERSPECTIVE_DESCRIPTIONS` have the same four keys, in that order for the
  tuple; every `SelectorSpec` of `_PERSPECTIVE_LOOKUPS` has a non-zero
  `row_cap`; every `context_sections` string is a `"section"` literal of
  `perspective_selectors.py`.
- **PI3** -- closed verdicts: the string literals assigned to `verdict` in
  `perspective_query.py` equal `PERSPECTIVE_VERDICTS`.
- **PI4** -- fixture (R-34 database, R-36 writers). One world holding:
  `Hero` (character, public), `Shade` (character, `is_public=False`),
  `Guild`, `Guild2` (factions, public), `Cabal` (faction, `is_public=False`),
  two characters `Twin` (both public). Facts, each written with
  `create_fact` + `attach_participants` and given its public level
  explicitly (`create_fact_default` at `world`, or `default_level`):
  F1 `description` of Hero, world default `knows`; F2 `histoire` of Hero,
  `default_level` `unaware`, no default; F4 `description` of Shade, world
  default `knows`; F6 `information` about Shade, text holding the word
  `tunnel`, world default `knows`; F7 a free fact (no participant) holding
  `tunnel`, `default_level` `unaware`. F3: the creator-only note of Hero,
  written with `write_entity_facets(entity_id=Hero, facets={"creator_meta":
  "..."})`, then given a world default `knows` with `create_fact_default`
  (so only the creator-only test excludes it). F5: `write_relation(mode="set")`
  Hero -> Guild, a social type, its fact read by `lien_fact_of` and given a
  world default `knows`. Memberships (`write_membership(mode="open")`):
  Hero in Guild (public), Hero in Cabal (not secret), Hero in Guild2
  (`is_secret=True`). One law through `write_world_laws`. If a facet name
  above is refused by `create_fact`, use another non-typed facet of
  `FACETS` and report it. Cases, each with exact set equality:
  a. `public_view`: `fact_ids` = {F1, F4, F5, F6}; `entity_ids` = {Hero,
     Guild, Guild2, Twin1, Twin2}.
  b. `execute_public_plan`, dossier on « Hero » -> `answered`; `facets`
     contents = {text of F1, text of F5}; `memberships` faction names =
     {Guild}; no row holds a key forbidden by C-04.
  c. dossier on « Shade » -> `nothing_known`, no rows (its public F4
     notwithstanding: Shade is not public).
  d. dossier on « Nobody » -> `nothing_known`, no rows.
  e. `public_facts_mentioning("tunnel")` -> one `public_mentions` row (F6),
     `participants` = [] (Shade is not public).
  f. `public_factions` -> names {Guild, Guild2}; `world_laws` -> the law.
  g. `withheld`: for b exactly {(`not_public`, Hero, F2 text),
     (`creator_only`, Hero, F3 text), (`faction_not_public`, Hero, <Cabal
     row>), (`secret_membership`, Hero, <Guild2 row>)}; for c exactly
     {(`entity_not_public`, Shade, "Shade")}; for e exactly {(`not_public`,
     <subject>, F7 text)} where `<subject>` is the searched text `tunnel`.
  h. a binding `{m1: <Shade id>}` on a plan mentioning « Shade » raises
     `BindingRefused`; « Twin » -> `ambiguous_mention` with both Twins
     (keys exactly `entity_id, name, type`), and a binding to either is
     accepted (verdict `nothing_known` or `answered`, never an exception).
  i. `NameScope("public")` without `known_fact_ids` raises `ValueError`.
- **PI5** -- render, `chat` stubbed (R-35 `_Stub`/`_swap` copied): each
  non-`answered` verdict renders its constant with renderer
  `deterministic` and no model call; `answered` makes exactly one call.
PASS line: `PASS: perspective_isolation -- public view, selectors, executor, audit and renderer: nothing creator-only, secret or non-public reaches the public answer`.

## Scope OUT

- No route, no journal write, no frontend (E, F, G).
- No change to any creator selector, to `execute_plan`, to the creator
  verdicts, to `routes/lore.py`.
- No character perspective, no `known_facts_of` reuse (TICKET-0127).
- No new prompt usage, no seed change (drafting decision 3).
- Event facts in the dossier (drafting decision 8).
- Every later brief of this lot.

## Invariants to defend

- **INV-01** -- secrets and the creator's note are excluded by query
  construction: `public_view` subtracts creator-only facts; no
  `include_creator_only`; PI1 and PI4g prove it.
- **INV-03** -- memberships reach a prompt only through the sanctioned
  accessors; the new faction-keyed reader carries the same WHERE triplet and
  is named in INV-66 by brief G.
- **INV-06** -- the relation scan excludes `MAP_TOPOLOGY_TYPES`.
- **INV-58** -- the renderer receives rows, never a `Session`; empty
  verdicts never reach a model (PI5).
- **INV-62** -- the spirit of it: a player surface never writes out what the
  player may not know.

## Decision rights

STOP:
- an anchor has moved;
- a fact the fixture needs cannot be written through the R-36 writers
  (name it and stop);
- a `lore_isolation.py`, `lore_selectors.py` or `name_index.py` rule turns
  red after commit 1.
ADAPT:
- `import_cycle.py` reports a cycle through `perspective_selectors` ->
  `knowledge_resolve`: move that import inside `public_view` (function-local,
  as `name_index.surfaces` does for `facet_reads`) and report;
- the exact `content` wording of a membership audit row (`<Cabal row>`,
  `<Guild2 row>` above): use `"<faction name> (<role or ->)"`, assert it in
  PI4g, report it.
REPORT-ONLY:
- a public fact whose text renders a token naming a non-public entity (it is
  the creator's public text).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `perspective_isolation.py` PASS.
- [ ] `name_index.py`, `name_resolution.py`, `lore_selectors.py`,
      `lore_isolation.py`, `lore_facts_mentioning.py`, `lore_usage.py` PASS.
- [ ] Named mutation PI4a: removing the `creator_only_fact_ids` subtraction
      in `public_view` makes PI4a and PI4b fail (then revert).
- [ ] Named mutation PI4c: removing the `is_public` filter in
      `name_index.surfaces` for `public` makes PI4c fail (then revert).
- [ ] Named mutation PI4e: dropping the `view.entity_ids` test on
      participants makes PI4e fail (then revert).
- [ ] Named mutation PI1: adding `include_creator_only=True` to a call in
      `perspective_selectors.py` makes PI1 fail (then revert).
- [ ] `corpus_gate.py` passes.
- [ ] `/review-step` and `/close-step` on each commit.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry above the footer:
  `## The public perspective (BRIEF-0125-D, no schema change)` -- U1, V1,
  W1, the four selectors, the single "nothing known" sentence, the audit
  reasons, why the creator selectors cannot serve it (R-20).
- `.claude/rules/authoring-lore.md` is not edited here (G adds the player
  rule file).
- Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.
