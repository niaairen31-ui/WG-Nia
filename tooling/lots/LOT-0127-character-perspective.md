# LOT — TICKET-0127 "A character's perspective"

Lot RECON run in the chat session on `main` at `6f4b578` (PR #157,
TICKET-0130 merged; schema v2.33). Briefs are executed one per session;
this header is authoritative on any conflict with a brief's embedded copy.

## Objective and cut

The pipeline TICKET-0125 built answers « as everybody ». This lot adds a
second perspective, one character's, on the same code (A1): a view of what he
knows -- the facts the engine's one knowledge authority gives him, minus the
creator's notes, each in the version he last saw and in his own words, with
its certainty (B1); the entities he can name (D1, D1-a); his visible and held
skills -- and every selector, the executor, the audit and the renderer read
through that view. Known events enter the dossier for both perspectives
(F1). A « self » selector gives the character the people he met and his
skills (E1). The creator asks as any character in Lore and sees what he
conceals marked as such, plus the audit (C1, H1-b, H1-c, I1); the player asks
as his own character in `/jouer` and never receives a concealed row (G1).
Every question and resolution is journaled with the character (H1-d, H1),
and a G1 check with named mutations proves the secret stays at the
creator's door.

The lot stops there. Not in it: several characters per profile in a world
(TICKET-0128), dated encounters (TICKET-0120), Play, a per-character metric
in « Suivi » (H2).

## Briefs in this lot

- A -- `neutral-selector-names`: `PublicView` -> `PerspectiveView` and the
  four selectors' neutral names; pure rename.
- B -- `character-view`: the belief, the character's view
  (`perspective_view.py`), the `character` name regime; check CP1-CP3.
- C -- `character-selectors`: every selector through the view, events in the
  dossier, the self sheet, the character's table, the renderer's suffixes;
  CP4-CP5.
- D -- `character-flow-and-doors`: executor, audit and renderer over a view;
  the flow and its journal; the creator's and the player's routes; CP6-CP7.
- E -- `screens-and-docs`: Lore « Un personnage », the player's « Mes
  savoirs », PSH6; INV-01, INV-66, the decision entry.

## Dependency graph

Strictly sequential: A -> B -> C -> D -> E.
- A -> B: B extends the class A names `PerspectiveView` (C-01, C-02).
- B -> C: C's selectors read the view's beliefs, `member_of` and entities
  (C-02, C-03) and C's rules extend B's fixture (C-15).
- C -> D: D's executor validates against `lookups_for`, its audit mirrors
  C-06's dossier, its flow plans over `descriptions_for` (C-07).
- D -> E: E's screens call D's routes (C-13); PSH6 checks their URLs.
No order here comes from a locked decision alone.

## RECON
### R-01 -- the base, the version, the free ids
Opened: `git log -1` (`6f4b578`, « Merge pull request #157 from
niaairen31-ui/ticket/0130 »); `world-engine-schema.md:3`;
`src/world_engine/schema_version.py:15`; `.claude/rules/*.md` (grep `INV-6`);
`ls tooling/lots tooling/briefs | grep 0127`.
Finding: `Current schema version: v2.33`;
`EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.33"`. The highest invariant is
INV-68 (`.claude/rules/character-creation.md:36`). No artifact of 0127 exists.
Consequence: no schema change, no migration, no new invariant in this lot;
E amends INV-01 and INV-66 in place.
### R-02 -- the public selectors
Opened: `src/world_engine/perspective_selectors.py:1-338` (whole).
Finding: `PublicView(world_id, fact_ids, entity_ids, skill_ids)`, frozen
dataclass (:33-38), built only by `public_view(db, world_id)` (:41-58: facts
whose public level is not `unaware`, minus `creator_only_fact_ids`; active
entities with `is_public`; `visible_skill_ids`). Helpers:
`_participant_facts(entity_id, world_id, db)` (:70-84) joins
`FactParticipant` and keeps `Fact.event_id.is_(None)` (:80), sorted by
registry facet order, `created_at`, id; `_relation_facts` (:87-99, lien facts,
`MAP_TOPOLOGY_TYPES` excluded); `_other_end` (:102-103);
`_current_memberships` (:106-116, any secrecy, audit only); `_public_members`
(:119-139, the `read_public_memberships` WHERE triplet keyed by faction, rows
`{section: "members", member_name, role}` kept when the member is in
`view.entity_ids`); `public_member_ids` (:142-156, ids for TICKET-0129's
approval); `_public_membership_rows` (:159-172, `read_public_memberships`
names kept only when every current membership of that name resolves to a
public faction). Members: `public_dossier` (:175-201: `[]` when the entity is
not in the view; rows `identity {section, entity_id, name, type}`, `facets
{section, label, aspect, content, secret}` with `secret: False`, lien rows
labelled `"Lien"` kept when the fact and the other end are in the view,
memberships, members for a faction); `public_factions` (:204-228, SQL filter
`Entity.is_public == True` at :210, rows `{section: "factions", entity_id,
name, faction_type, description}`); `_facts_matching` (:231-243, every fact of
the world whose CURRENT rendered text holds every token of 3+ letters);
`public_facts_mentioning` (:246-263, rows `{section: "public_mentions",
content, participants}`, participants from `FactParticipant` in the view);
`world_laws` (:266-269, `{section: "laws", position, text}`); `public_skills`
(:272-293, `{section: "skills", skill_id, name, base_domain, system,
description, requires_master}`). Tables (:296-338): `PERSPECTIVE_SELECTORS`
(five names), `_PERSPECTIVE_LOOKUPS` (`public_dossier` with
`context_sections=("identity",)`, arity/row caps 2/400, 1/200, 2/200, 1/100,
1/200), `PERSPECTIVE_DESCRIPTIONS`.
Consequence: A renames the members and the view class (C-01); B extends the
view (C-02); C makes every member read through the view's facts, entities
and texts (C-05, C-06) and adds a sixth member for a character (C-07).
### R-03 -- every reference to a symbol A renames (protocol step 4)
Opened: the grep below at `6f4b578`, history folders excluded.
Finding (pasted):
```
$ grep -rn "public_dossier\|public_factions\|public_facts_mentioning\|public_skills\|PublicView" src/world_engine tooling/verify/checks frontend/src --include=*.py --include=*.js --include=*.svelte | grep -v "/static/"   (lines per file)
src/world_engine/cockpit/routes/player_creation.py: 31 160 173
src/world_engine/creation_designer.py: 32 122 225 235 310
src/world_engine/creation_lore.py: 5 6 20 37 90 95 99
src/world_engine/pc_draft_reads.py: 4 18 21 28 34
src/world_engine/perspective_audit.py: 26 46 55 81 90 117 120 124
src/world_engine/perspective_query.py: 23 41 46 70
src/world_engine/perspective_selectors.py: 6 34 41 55 119 142 159 175 204 246 266 272 297 301 302 305 306 308 309 314 315 320 321 324 325 327 328 334 335
tooling/verify/checks/creation_designer.py: 19 241 242
tooling/verify/checks/perspective_isolation.py: 32 34 49 51 292 305 306 315 322 351 432 458 460 468 471 476
tooling/verify/checks/player_routes.py: 12 63 65
```
No frontend file names a selector. `tooling/verify/checks/creation_designer.py:241`
counts `facts_mentioning(` against `public_facts_mentioning(`;
`player_routes.py:62-65` holds `HERO_PLAN` and `TWIN_PLAN` on
`"public_dossier"`. `world_laws` also names `writes.write_world_laws`; that
symbol is not renamed.
Consequence: A updates exactly these files (each hit, docstrings included);
the counter of `creation_designer.py` CD3 counts `known_facts_mentioning(`
after A (the new name still contains `facts_mentioning(`). Historical
artifacts (`tooling/tickets`, `lots`, `briefs`, `recon`,
`ARCHITECTURE_DECISIONS.md`) are never edited.
### R-04 -- the public executor
Opened: `src/world_engine/perspective_query.py:1-122` (whole).
Finding: `PERSPECTIVE_VERDICTS = ("answered", "ambiguous_mention",
"nothing_known", "unsupported_selector")` (:25); `BindingRefused(ValueError)`
(:28); `PerspectiveResult(verdict, rows, ambiguous, rejection_reason)` (:33-38);
`public_scope(view)` -> `NameScope("public", known_fact_ids=view.fact_ids)`
(:41-42); `resolve_public_mentions(plan, world_id, db, view, bindings=None)`
(:45-67: unknown binding refs and a binding outside the mention's candidates
raise `BindingRefused`, a valid binding becomes `pre_resolved`);
`_ambiguous_items` (:70-86, candidates kept in `view.entity_ids`, keys
`entity_id, name, type`); `execute_public_plan(plan, world_id, db,
bindings=None)` (:89-122): `validate_plan(..., lookups=_PERSPECTIVE_LOOKUPS)`
first (invalid -> `unsupported_selector`), then `public_view`, resolutions,
`ambiguous_mention`, any `unmatched` -> `nothing_known`, every call through
`_PERSPECTIVE_LOOKUPS` with `_call_args`, a row without `"section"` raises,
truncation at `row_cap`, `answered` iff a row lies outside the spec's
`context_sections`. Callers (grep `execute_public_plan|resolve_public_mentions|public_scope`):
`cockpit/perspective_flow.py:27,44`; `perspective_audit.py:23,103`;
`creation_lore.py:19,79` and `creation_designer.py:31,228` (`public_scope`);
`perspective_isolation.py:278,293,307,310,316,322,325,347,352,359,431,474`.
Consequence: D generalizes the executor over a view (C-09) and keeps
`execute_public_plan` and `public_scope` with their signatures for these
callers.
### R-05 -- the public audit
Opened: `src/world_engine/perspective_audit.py:1-137` (whole).
Finding: `WITHHELD_REASONS` (:35-38, six values: `creator_only, not_public,
entity_not_public, secret_membership, faction_not_public, skill_not_visible`);
`_membership_line(name, membership)` -> `"Name (role or -)"` (:41-43);
`_withheld_facts` (:46-52: facts not in the view, `creator_only` when
creator-only else `not_public`); `_withheld_dossier` (:55-78);
`_withheld_factions` (:81-87); `_withheld_skills` (:90-92);
`withheld(plan, world_id, db, bindings=None)` (:95-137): `[]` for an invalid
plan or an ambiguous mention, an unmatched mention re-resolved under
`NAMES_ONLY`, per call: `world_laws` nothing, `public_factions`,
`public_skills`, `public_facts_mentioning` (`_facts_matching` on the searched
text), else the dossier of the bound entity; rows `{"reason", "subject",
"content"}` sorted. The literal `"subject"` occurs once in the module (:135).
Consequence: D adds the character's reasons and a view-taking entry point
(C-10); the public output stays byte-identical; no new `subject` reference
(R-25).
### R-06 -- the public renderer
Opened: `src/world_engine/perspective_render.py:1-42` (whole).
Finding: `NOTHING_KNOWN_MESSAGE`, `UNSUPPORTED_MESSAGE`, `AMBIGUOUS_MESSAGE`
(:19-21), `_DETERMINISTIC` (:23-27), `render_public(result, question, spec,
exchanges=None)` (:30-42): a non-`answered` verdict is its constant with
renderer `deterministic`; `answered` goes through `lore_render.render` on a
`LoreResult` built from the rows. No `Session`, no `select(` (PI1).
Consequence: D adds the character's two constants and `render_perspective`
(C-11); `render_public` keeps its signature.
### R-07 -- the shared flow and the creator's routes
Opened: `src/world_engine/cockpit/perspective_flow.py:1-113`;
`src/world_engine/cockpit/routes/lore_perspective.py:1-62`.
Finding: the flow imports `withheld as _withheld`, `execute_public_plan`,
`render_public`, `PERSPECTIVE_DESCRIPTIONS` (:26-29); `PERSPECTIVE = "public"`
(:32); `_journal` -> `lore_usage.record(kind="perspective", ...)` (:36-39);
`_answer(plan, world_id, question, db, exchanges, bindings=None)` (:42-56)
returns `{verdict, answer, renderer, candidates, plan, rows, withheld}`;
`ask_flow(db, *, question, world_id, asked_by, attempt)` (:59-89): payload
`{question, perspective, asked_by, response, withheld}` (+ `error`), ping ->
503 journaled `unavailable`, `draft_plan(..., descriptions=PERSPECTIVE_DESCRIPTIONS)`,
parse error -> 502 journaled `parse_error`, `ok` journaled;
`resolve_flow(db, *, plan_raw, bindings, question, world_id, asked_by,
attempt)` (:92-113): malformed plan or `BindingRefused` -> 422 journaled
`refused` (`"Choix refusé."`). The route module: `UNKNOWN_PERSPECTIVE_MESSAGE
= "Perspective inconnue."` (:25), `ASKED_BY = "creator"` (:26), bodies
`PerspectiveAskBody(question, world_id, perspective, attempt_id=None)` (:29-33)
and `PerspectiveResolveBody(plan, bindings, world_id, question, perspective,
attempt_id=None)` (:36-42), `_check_perspective` (:45-47, 422 before any
journal row), `POST /api/lore/perspective/ask` (:50-54) and `/resolve`
(:57-62). Registered at `cockpit/app.py:69,153`.
Consequence: D threads the view through the flow (C-12) and widens the
route's perspective check (C-13); both modules keep no `select(` and no
`chat(` (R-22, PR8).
### R-08 -- the player's door
Opened: `src/world_engine/cockpit/routes/player.py:1-129` (whole).
Finding: `WORLD_NOT_FOUND = "Monde introuvable."`, `PROFILE_NOT_FOUND =
"Profil introuvable."`, `PLAYER_ANSWER_KEYS = ("verdict", "answer",
"renderer", "candidates", "plan")` (:30-32); `SavoirAskBody(profile_id,
world_id, question, attempt_id=None)` (:39-43), `SavoirResolveBody(profile_id,
world_id, plan, bindings, question, attempt_id=None)` (:46-52);
`_open_world` (:56-60, 404 unless `open_to_players`), `_player_profile`
(:63-67, 404 unless an active `player` user), `_player_answer` (:70-71);
`POST /api/joueur/savoir/ask` (:111-118) and `/resolve` (:121-129) run the
flow as `player:<profile_id>`. Its `select(` calls name only `User`, `World`
(PR8, R-22).
Consequence: D adds the character's GET and its two POST routes here, with
the character lookup in `perspective_view.py` so this module selects nothing
new (C-13).
### R-09 -- the name index's regimes
Opened: `src/world_engine/name_index.py:1-175`.
Finding: `REGIMES = ("names_only", "creator", "prose", "perceiver",
"public")` (:35); `_APPELLATION_RULES` (:38-44, `perceiver` and `public` both
`(True, True, False, True)`); `NameScope(regime, known_fact_ids=None,
exclude_entity_id=None)` frozen (:47-62): `__post_init__` raises on an unknown
regime, on a missing `known_fact_ids` for `perceiver`/`public` and on a
`known_fact_ids` given to any other regime; `surfaces(db, world_id, scope)`
(:110-175) keeps active entities, `exclude_entity_id` out, and
`(scope.regime != "public" or e.is_public)` (:123): the `perceiver` regime
counts the NAME of every active entity, known or not. Check
`tooling/verify/checks/name_index.py`: R3 `REGIMES` == the keys of
`_APPELLATION_RULES` (:144-155); F1's malformed scopes (:305-308) assert
only that `ValueError` is raised.
Consequence: B adds a `character` regime restricted to the view's entities
(C-04): under `perceiver`, an unknown homonym would surface in « Laquelle ? »
(D1).
### R-10 -- what an entity knows
Opened: `src/world_engine/knowledge_resolve.py:1-53, 81-86, 203-283`.
Finding: `Known(level, as_of)` (:81-86). `resolve_known_for_entity(db,
entity_id)` (:253-280) returns `fact_id -> Known` for every fact of the
entity's world resolving above `unaware`, by the seven tiers of the
docstring; a stored `knowledge` row wins outright whatever its `is_secret`
(`_resolve_fact`, :217-221). `as_of` is `None` for a world-default fact and
one's own descriptive facts, else the last contact (`_as_of`, :203-214).
Measured on the CP fixture (R-27): Mira's stored secret rumor resolves
(`F7 rumor`), the creator's note on Hero resolves `knows` (world default) and
must be subtracted as creator-only.
Consequence: B builds the character's facts on this one authority, subtracts
creator-only facts and, at the player's door, its holder's secret rows
(C-03).
### R-11 -- the knowledge row
Opened: `src/world_engine/models/canon_knowledge.py:199-240`.
Finding: `Knowledge(entity_id, fact_id, level, content_raw` (SQL `content`),
`source, is_incorrect, is_secret, share_threshold, ...)`, unique
`(entity_id, fact_id)` (`idx_knowledge_entity_fact`). `content` is the
holder's own wording, rendered by `prose_render.knowledge_texts`.
Consequence: a belief's text is the holder's `content` when it has one (B1);
`is_incorrect` and `is_secret` come from this row only.
### R-12 -- texts and versions
Opened: `src/world_engine/prose_render.py:67-89`;
`src/world_engine/fact_versions.py:42-56`.
Finding: `fact_texts(db, facts)` (:71-73) renders current texts;
`knowledge_texts(db, rows)` (:76-78) renders `content_raw`;
`fact_texts_at(db, pairs)` (:81-84) renders each `(fact, as_of)` at its
version (`version_text`: the content before the first `changement` after
`as_of`, current when `as_of` is `None`); `fact_is_stale(fact, as_of)`
(:87-89).
Consequence: C-05 renders a character's facts at the version he knows;
C-10's `stale_version` reads `fact_is_stale`.
### R-13 -- creator-only facts and the holder's own secrets
Opened: `src/world_engine/facet_reads.py:58-63`;
`src/world_engine/tick_context.py:125-133`; `CLAUDE.md:133-141` (INV-01).
Finding: `creator_only_fact_ids(db, fact_ids) -> set[str]`, one query.
`tick_context._knowledge_line` renders an NPC's own `is_secret` rows into
that NPC's own context, prefixed `[SECRET] ` -- the precedent C1 follows.
INV-01 reads « excluded at every assembler AND every propagation path ».
Consequence: C1 (the creator's door shows the holder's own secrets) is
written into INV-01 by E; the player's door drops them by construction
(C-03 step 3).
### R-14 -- encounters
Opened: `src/world_engine/encounters.py:140-147`;
`src/world_engine/models/ephemeral.py:170-190`.
Finding: `acquaintances(db, entity_id) -> set[str]`, every entity paired
with it in `rencontre`. `record_encounter(db, *, world_id, a_id, b_id,
source, at=None, source_ref=None)` (:55-...) is the sanctioned writer.
Consequence: D1's « rencontrées » and E1's acquaintance rows read
`acquaintances`.
### R-15 -- events and their facts
Opened: `src/world_engine/models/canon_event.py:152-172`;
`src/world_engine/writes/events.py:85-125, 139-142, 418-445`;
`src/world_engine/facets.py:77-93`;
`tooling/verify/checks/event_contexts.py:114-152`.
Finding: `EventParticipant(world_id, event_id, role_id, entity_id | sorte_id,
position)`; an event's fact is `create_fact(..., facet="evenement",
event_id=event.id)` with no `fact_participant` (measured, R-27); its text is
`event_fact_text(title, description)` (= the title when no description);
the participants' knowledge and the type's scopes are written by
`record_event`. `FACETS["evenement"].label == "Événements"`,
`FACETS["lien"].label == "Liens"`. Fixture recipe: `write_event_type(db,
world_id, spec=EventTypeSpec(name, roles=(RoleSpec("qui", ("character",
"faction")),)))`, `type_view(db, type_id).roles[0].id`, `write_event(db,
world_id, created_by, spec=EventSpec(type_id, title, participants=(
ParticipantSpec(role_id, entity_id=...),), scopes=(EventScopeSpec("world",
None, "knows"),)))`, `event_fact(db, event_id)`.
Consequence: F1 finds an entity's event facts through `EventParticipant`
(C-06), labelled `"Événement"` as a lien is labelled `"Lien"`.
### R-16 -- memberships
Opened: `src/world_engine/context.py:161-215`;
`src/world_engine/models/canon_faction.py:92-130`.
Finding: `read_public_memberships(entity_id, session)` returns
`(faction_name, cover_role ?? role)` for current non-secret memberships;
`read_public_membership_faction_ids(entity_id, session) -> set[str]`
(:200-215), the same WHERE triplet, ids only. `FactionMembership(entity_id,
faction_id, role, cover_role, is_secret, left_at, ...)`.
Consequence: the holder's own factions are read through
`read_public_membership_faction_ids` (never a secret row, INV-03); rows still
come through `read_public_memberships` and the faction-keyed triplet (C-06).
### R-17 -- skills
Opened: `src/world_engine/models/canon_skill.py:21, 34-166`;
`src/world_engine/creation_rules.py:89-118`;
`src/world_engine/skill_ranks.py:35-48, 69-90`.
Finding: `BASE_SKILL_DOMAINS = ("physical", "agility", "perception",
"composure")`. `Skill(character_id, domain, rank 0-5, skill_definition_id
nullable, ...)`. `SkillSystem(world_id, name, ...)` (:34), unique name per world.
`SkillDefinition(world_id, name, base_domain, system_id
nullable, visible_at_creation nullable, requires_master, ...)`.
`visible_skill_ids(db, world_id) -> frozenset[str]`. `world_ladder(db,
world_id) -> tuple[RankStep, ...]`, index = rank, `.label`; default labels
`Inexpérimenté, Initié, Apprenti, Confirmé, Expert, Maître`.
Consequence: a character's view knows the visible skills plus the
definitions it holds (C-03); E1's skill rows read `world_ladder` labels.
### R-18 -- the character row
Opened: `src/world_engine/models/canon.py:123-175`.
Finding: `Character(id -> entity.id, world_id, character_type ("player" |
"npc"), user_id, current_location_id, ...)`; unique
`idx_character_one_pc_per_user_world` on `(world_id, user_id)` where
`character_type = 'player'`. `Entity(world_id, type, name, status,
is_public, ...)`.
Consequence: `player_character_of` reads at most one row (C-03).
### R-19 -- the Lore renderer's section vocabulary
Opened: `src/world_engine/lore_render.py:1-350`;
`tooling/verify/checks/lore_isolation.py:44-60`.
Finding: `_format_facets` (:41-44) prints `label (aspect) : content [secret]`;
`_format_public_mentions` (:124-128) prints `« content » -- participants`;
`_format_skills` (:131-137). `_SECTION_FORMATTERS` (:140-155, fourteen
sections); `_group_rows_by_section` raises on an unknown section (:158-172).
lore_isolation R10-R14 forbid `select(`, `db.add(`, a model call on an empty
verdict, inline message literals and a dropped section in `lore_render.py`.
No check pins the formatter set (grep `_SECTION_FORMATTERS` in
`tooling/verify/checks`: empty).
Consequence: C adds two sections and two suffixes (C-08) without touching
the guarded paths.
### R-20 -- plans, validation, the planner
Opened: `src/world_engine/lore_selectors.py:30-46`;
`src/world_engine/lore_query.py:66-100, 163-171`;
`src/world_engine/lore_plan.py:51-53, 89-115`.
Finding: `SelectorSpec(fn, arity, row_cap, arg_kinds, context_sections=())`.
`validate_plan(plan, db, *, lookups=None)` rejects a selector outside
`lookups`, a wrong arity, an unknown ref or an `arg_kinds` mismatch (kinds
`entity_id`, `world_id`, `text`). `_call_args` maps `$world`, `text:` and
refs. `draft_plan(question, world_id, db, exchanges=None, *,
descriptions=None)` renders `descriptions` as `- name: description` lines.
Consequence: a character's table adds one selector of kind `("world_id",)`;
the public table refuses it as `unsupported_selector` (C-07).
### R-21 -- the usage journal
Opened: `src/world_engine/writes/lore_usage.py:20-45, 55-90`;
`src/world_engine/lore_usage.py:68-71`; `src/world_engine/models/pipeline.py:471,
482-487`; `tooling/verify/checks/player_entry_schema.py:35-41, 196-205`.
Finding: `PAYLOAD_KEYS["perspective_ask"] = {question, perspective, asked_by,
response, withheld, error}`, `["perspective_resolve"]` the same plus `plan,
bindings`; `write_usage_event` refuses a payload whose key set differs. The
SQL CHECK names only kinds and steps. `player_entry_schema.py` pins both key
sets in `C09_KEYS` (:38-40) and builds PS2d's payload from them (:200-201).
Consequence: D adds `character_id` to both key sets and to `C09_KEYS`; no
migration.
### R-22 -- the checks of the perspective, the player's door and the shell
Opened: `tooling/verify/checks/perspective_isolation.py:1-80, 108-153, 182-270`;
`player_routes.py:1-70, 74-165, 308-358`; `player_shell.py:1-40, 80-100`;
`name_index.py:1-40, 285-310`; `creation_designer.py:14-24, 228-250`;
`knowledge_identity.py:31-34, 125-131, 842-863`.
Finding: PI1 (`MODULES` :70; `FORBIDDEN` :71-72 holds `chat(`, `db.add(`,
`.commit(`, `include_creator_only`, `CREATOR`, `NameScope("creator"`,
`near_candidates`, `validate_binding`; `CREATOR_SELECTORS` :73);
`FORBIDDEN_KEYS = {"is_secret", "is_incorrect", "intensity", "internal_name",
"knowers", "creator_only", "level"}` (:74); PI2 (:137-152) requires five
public names and the three tables in their order; PI3 the verdict literals;
PI4 builds the world `_build_world(engine)` (:182-255: Hero, Shade
(non-public), Guild, Guild2, Cabal (non-public), two public Twins; F1-F7;
Hero in Guild, Cabal and secretly Guild2; one law) and plans with
`_plan(selector, *, mention=None, text=None)` (:258-265). player_routes:
harness `_fresh_engine` (:74), `_seed_prompts(db)` (:91), `_Stub(replies)`
with `.messages` (:113-122), `_swap(module, stub)` (:125-128), `_events`
(:131), `_all_events` (:140), `_attempt(n)` (:149), `_one` (:153);
`PLAYER_KEYS`, `CREATOR_KEYS` (:58-59); PR8 (:320-358): `lore_perspective.py`
and `perspective_flow.py` hold no `chat(` nor `select(`, `player.py` no
`chat(` and `select(` naming only `User`, `World`, `WorldLaw`, none holds
`World.is_active`, `_world_id(`, `write_usage_event`, `lore_selectors`, and
every route path of `player.py` starts `/api/joueur/`. player_shell PSH1
requires five French reason labels in `PerspectivePanel.svelte`; PSH2 every
URL literal under `frontend/src/joueur/` starts `/api/joueur/`; PSH3 no
import out of that folder; PSH5 a built asset carries a creation string.
knowledge_identity K3 pins one `subject` reference in `perspective_audit.py`.
Consequence: each brief names which of these it must keep green or extend;
CP (the new check, C-15) imports `_build_world`, `_plan` and the harness of
`player_routes.py` rather than copying them.
### R-23 -- the frontend surfaces
Opened: `frontend/src/lore/PerspectivePanel.svelte:1-143`;
`frontend/src/lore/perspective.svelte.js:1-101`; `frontend/src/lore/Lore.svelte:24,
110, 118-119`; `frontend/src/joueur/WorldPage.svelte:1-90`;
`frontend/src/joueur/joueur.svelte.js:1-179`;
`frontend/src/joueur/character.svelte.js:112-123`;
`src/world_engine/cockpit/routes/player_creation.py:183-197`;
`src/world_engine/cockpit/crud/entities.py:522-531`; `.claude/rules/frontend.md`.
Finding: the panel's `REASON_LABEL` (:13-19) holds five reasons
(`skill_not_visible` has none); the perspective `<select>` (:44-49) one option
`public`; the answer heading is « Ce que voit le joueur » (:71); the state
(:14-22) holds `perspective, question, asking, error, result, selections,
attemptId`; the ask body (:38-43) and resolve body (:74-81) send
`perspective`; `resetPerspectiveForWorld` (:92-101). `WorldPage.svelte`'s
section « Ce que tout le monde sait » (:38-78) calls `askSavoir`,
`selectSavoirCandidate`, `allSavoirChoicesMade`, `confirmSavoir`.
`joueur.svelte.js`: state (:12-23), `clearQuestion` (:56), `openWorld`
(:121-125), `askSavoir` (:127-147, `/api/joueur/savoir/ask`), `confirmSavoir`
(:159-179, `/resolve`). The player sees an accepted character only through
`character_name` of `GET /api/joueur/creation/brouillon`. `GET /api/entities`
reads the active world and returns no `character_type`. Every frontend edit
is rebuilt and the build under `src/world_engine/cockpit/static/` committed.
Consequence: E reads the characters through a perspective route (C-13) and
the player's character through `GET /api/joueur/personnage` (C-13).
### R-24 -- budgets
Opened: `tooling/verify/checks/module_budget.py:58-59`;
`tooling/verify/checks/claude_md_contract.py:77-80, 132-138`; `wc -l`/`wc -c`.
Finding: 40 top-level functions and 1000 lines per module (frontend 1000
lines). Today: `perspective_selectors.py` 338, `perspective_audit.py` 137,
`perspective_query.py` 122, `perspective_render.py` 42, `perspective_flow.py`
113, `lore_perspective.py` 62, `player.py` 129, `lore_render.py` 350,
`name_index.py` 175, `PerspectivePanel.svelte` 143, `joueur.svelte.js` 179.
`CLAUDE.md` 20 895 of 22 000 characters; `.claude/rules/player-surface.md`
body 1 038 of 4 000; no line over 100 characters.
Consequence: no extraction is needed; E's amendments fit the budgets.
### R-25 -- name bans across `src/`
Opened: `tooling/verify/checks/knowledge_identity.py:31-34, 842-863` (K3:
attribute `.subject`, constant `"subject"`, keyword or parameter `subject`,
counted per file); `lore_as_facts.py:8-11` (R1: no attribute `appearance,
backstory, secrets, philosophy, internal_structure, internal_tensions,
aversion, goals` outside `models/`); `event_contexts.py:72, 334-337` (ED4:
no attribute `knowledge_status, occurred_at, has_magic_impact,
consequences`, no `EventEntity`); PI1 `FORBIDDEN` (R-22); PR8 `FORBIDDEN_ALL`.
Finding: every name this lot introduces was tested against them: `Belief`,
`beliefs`, `certainty`, `door`, `kind`, `member_of`, `character_name`,
`character_view`, `player_character_of`, `world_characters`,
`UnknownCharacter`, `CERTAINTY_LABELS`, `known_dossier`, `known_factions`,
`known_facts_mentioning`, `known_skills`, `self_sheet`, `acquaintances`,
`own_skills`, `rank_label`, `view_texts`, `lookups_for`, `descriptions_for`,
`perspective_scope`, `resolve_view_mentions`, `execute_perspective_plan`,
`withheld_for`, `render_perspective`: none is banned.
Consequence: no brief writes the literal `"subject"`, a `subject=` keyword or
parameter, nor any banned attribute; the audit keeps its one dict line.
### R-26 -- the generated maps and the decisions file
Opened: `tooling/standards/FILE_MAP.md:1-8, 231-234, 286, 334, 547-554`;
`tooling/standards/DECISIONS_INDEX.md:1-3`; `tooling/glue/gen_file_map.py:36`;
`tail -5 tooling/standards/ARCHITECTURE_DECISIONS.md`.
Finding: `FILE_MAP.md` is generated by `python tooling/glue/gen_file_map.py`
from the first docstring sentence of every module of `scripts/`, `src/` and
`tooling/` (checks included); `file_map.py` fails when it is stale.
`DECISIONS_INDEX.md` is generated by `python tooling/glue/gen_decisions_index.py`.
`ARCHITECTURE_DECISIONS.md` ends with `---` / blank / `*Co-built with
Claude, June 2026.*`; the last entry is `## TICKET-0130 -- ...` (:20921).
Consequence: every brief that adds a module or changes a first sentence
regenerates `FILE_MAP.md`; E inserts the decision entry above the footer and
regenerates `DECISIONS_INDEX.md`.
### R-27 -- the CP fixture, measured
Opened: a scratch script on a temp-file SQLite database at `6f4b578`:
`perspective_isolation._build_world(engine)` plus the additions of C-15's
`_extend`, then `resolve_known_for_entity`, `creator_only_fact_ids`,
`acquaintances`, `read_public_membership_faction_ids`, the
`FactParticipant`/`EventParticipant` joins, `visible_skill_ids`,
`fact_is_stale`, `world_ladder`.
Finding (pasted):
```
facts creator ['E1', 'E2', 'F1', 'F2', 'F4', 'F5', 'F6', 'F7', 'F8']
player minus ['F7']
entities ['cabal', 'guild', 'guild2', 'hero', 'mira', 'shade', 'twin1', 'twin2']
skills ['ombre']
F8 stale True 2026-11-14 18:09:40.250526+00:00
F5 text Hero éprouve « ally » envers Guild.
F3 text Hero trahira la guilde
['Inexpérimenté', 'Initié', 'Apprenti', 'Confirmé', 'Expert', 'Maître']
```
and, before the events: `shade knows {F1, F4, F6, F3, F5}` (F3, the creator's
note, resolves `knows` for anyone through its world default); an event
fact carries no `fact_participant` row; `public sacre knows, fuite unaware`.
Consequence: C-15's exact sets are these; the creator-only subtraction and
the player-door filter are each load-bearing (named mutations).
### R-28 -- the fixture's writers
Opened: `src/world_engine/writes/knowledge.py:241-300`;
`src/world_engine/writes/facts.py:56-75, 130-139, 175, 204`;
`src/world_engine/writes/factions.py:61-75`; `src/world_engine/writes/users.py:28-31`;
`src/world_engine/encounters.py:55-70`; `tooling/verify/checks/perspective_isolation.py:216-252`.
Finding: `write_knowledge(db, *, mode="update", knowledge_id=None,
entity_id=None, level=None, content=None, source=None, is_incorrect=False,
is_secret=False, ..., changed_by="creator_crud", fact_id=None, ...)` -- the
single sanctioned writer; without `knowledge_id` its default mode inserts the
row for `(entity_id, fact_id)` (`level_change` is the only other mode).
`create_fact(db, *, world_id, content, created_by, facet, ...)`,
`attach_participants(db, *, fact, entity_ids)`, `create_fact_default(db, *,
world_id, fact_id, scope_type, scope_id, level, created_by)` (as
`_build_world` calls them, :216-226); `update_fact_content(db, *, fact,
content, changed_by, kind)` appends the previous text with `kind` in
`FACT_CHANGE_KINDS = ("correction", "changement")`. `write_membership(db, *,
mode, ..., world_id, entity_id, faction_id, ..., is_secret)` returns the row
the caller adds (`_build_world` :248-250). `create_player_profile(db, name)`
adds and flushes one `User(name, role="player")`, never commits.
`record_encounter(db, *, world_id, a_id, b_id, source, at=None, ...)`.
Consequence: C-15's fixture uses exactly these writers, the way R-27's
measure did (the measure called `write_knowledge` with `mode="create"`,
which takes the default insert path; the brief passes no `mode`).

## Contract sheet

### C-01 -- neutral names (pure rename)
Produced by: BRIEF-0127-A   Consumed by: BRIEF-0127-B, C, D, E
Renames, exactly, and nothing else:
- `perspective_selectors.PublicView` -> `PerspectiveView` (same fields, same
  order, same `public_view` constructor).
- `public_dossier` -> `known_dossier`; `public_factions` -> `known_factions`;
  `public_facts_mentioning` -> `known_facts_mentioning`; `public_skills` ->
  `known_skills`. `world_laws` keeps its name.
- `PERSPECTIVE_SELECTORS == ("known_dossier", "known_factions",
  "known_facts_mentioning", "world_laws", "known_skills")`; the keys of
  `_PERSPECTIVE_LOOKUPS` and `PERSPECTIVE_DESCRIPTIONS` alike, same order. In
  each description string only the leading selector name changes.
Unchanged: `public_view`, `public_member_ids`, every private helper,
`public_scope`, `resolve_public_mentions`, `execute_public_plan`, `withheld`,
`render_public`, section names (`public_mentions` included), row keys,
`WITHHELD_REASONS`, behaviour.
Error and empty cases: none (no behaviour change).

### C-02 -- the perspective view and the belief
Produced by: BRIEF-0127-B   Consumed by: BRIEF-0127-C, D
In `src/world_engine/perspective_selectors.py`, replacing the class of C-01:
```python
PERSPECTIVE_KINDS: tuple[str, ...] = ("public", "character")
PERSPECTIVE_DOORS: tuple[str, ...] = ("creator", "player")


@dataclass(frozen=True)
class Belief:
    text: Optional[str]        # the holder's own wording (knowledge content); None: the fact's text at as_of
    as_of: Optional[datetime]  # Known.as_of
    certainty: Optional[str]   # "rumeur" | "soupçon" | "partiel" | None
    secret: bool               # the holder's knowledge row is is_secret
    incorrect: bool            # the holder's knowledge row is is_incorrect -- never a row key


@dataclass(frozen=True)
class PerspectiveView:
    world_id: str
    fact_ids: frozenset[str]
    entity_ids: frozenset[str]
    skill_ids: frozenset[str]
    kind: str = "public"
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    door: str = "creator"
    member_of: frozenset[str] = frozenset()
    beliefs: Mapping[str, Belief] = field(default_factory=dict, hash=False)
```
Required: `kind in PERSPECTIVE_KINDS`, `door in PERSPECTIVE_DOORS`. A public
view (built by `public_view`, unchanged) has every default: no character, an
empty `member_of`, no beliefs. A character view sets `character_id`,
`character_name`, `door`, `member_of` (the holder's current non-secret
factions) and one `Belief` per id of `fact_ids`, no other key.
Error and empty cases: none at construction (no `__post_init__`); C-03 is the
only builder of a character view.

### C-03 -- `perspective_view.py`
Produced by: BRIEF-0127-B   Consumed by: BRIEF-0127-C (fixture), D
New module `src/world_engine/perspective_view.py`, read-only (no `db.add(`,
no `.commit(`, no `chat(`). First docstring sentence: « A character's
perspective view: what one character knows of his world, and the player's
own character (TICKET-0127, BRIEF-0127-B, C-03). »
```python
CERTAINTY_LABELS: dict[str, str] = {"rumor": "rumeur", "suspicious": "soupçon", "partial": "partiel"}

class UnknownCharacter(ValueError): ...

def character_view(db: Session, world_id: str, character_id: str, *, door: str) -> PerspectiveView
def player_character_of(db: Session, world_id: str, profile_id: str) -> Optional[tuple[str, str]]
def world_characters(db: Session, world_id: str) -> list[dict]
```
`character_view`, in this order:
0. `door` outside `PERSPECTIVE_DOORS` -> `ValueError`. No `(Character,
   Entity)` pair with `Character.id == character_id`, `Entity.id ==
   character_id`, `Entity.world_id == world_id`, `Entity.status == "active"`
   -> `UnknownCharacter`.
1. `known = resolve_known_for_entity(db, character_id)`.
2. `stored = {row.fact_id: row}` for the character's `Knowledge` rows.
3. `fact_ids = set(known) - creator_only_fact_ids(db, known)`; when `door ==
   "player"`, also minus every id whose `stored` row has `is_secret`.
4. For each id of `fact_ids`: `Belief(text, as_of, certainty, secret,
   incorrect)` with `text` = that stored row's rendered content
   (`prose_render.knowledge_texts`, one call over the stored rows of
   `fact_ids` whose `content_raw is not None`) else `None`; `as_of =
   known[id].as_of`; `certainty = CERTAINTY_LABELS.get(known[id].level)`;
   `secret` / `incorrect` = the stored row's flags, `False` without a row.
5. `member_of = frozenset(read_public_membership_faction_ids(character_id, db))`.
6. `entity_ids` = the ids of the world's entities with `status == "active"`
   among: every `is_public` entity; `character_id`;
   `encounters.acquaintances(db, character_id)`; `member_of`; the
   `FactParticipant.entity_id` of every fact of `fact_ids`; the non-null
   `EventParticipant.entity_id` of every event whose fact
   (`Fact.event_id`) is in `fact_ids`.
7. `skill_ids = visible_skill_ids(db, world_id)` union the non-null
   `Skill.skill_definition_id` of the character's skill rows.
8. Return `PerspectiveView(world_id, frozenset(fact_ids),
   frozenset(entity_ids), skill_ids, kind="character",
   character_id=character_id, character_name=<entity name>, door=door,
   member_of=member_of, beliefs=<the dict of step 4>)`.
`player_character_of`: the `(Character.id, Entity.name)` with
`Character.world_id == world_id`, `Character.user_id == profile_id`,
`Character.character_type == "player"`, `Entity.status == "active"`; `None`
when there is none.
`world_characters`: one `{"id", "name", "character_type"}` per active
character of the world, players first, then by name, then id; `[]` for a
world without one.
Error and empty cases: as stated; never writes.

### C-04 -- the `character` name regime
Produced by: BRIEF-0127-B   Consumed by: BRIEF-0127-D
In `src/world_engine/name_index.py`:
- `REGIMES` gains `"character"` (last); `_APPELLATION_RULES["character"] =
  (True, True, False, True)`.
- `NameScope` gains a last field `entity_ids: Optional[frozenset[str]] =
  None`. `__post_init__`: `known_fact_ids` is required for `perceiver`,
  `public` and `character`, refused for the others (message « known_fact_ids
  is only for the perceiver, public and character regimes, not {regime!r} »);
  `entity_ids` is required for `character` (« the character regime needs
  entity_ids ») and refused for every other regime (« entity_ids is only for
  the character regime, not {regime!r} »).
- `surfaces`: an entity counts only when `(scope.regime != "character" or
  e.id in scope.entity_ids)`, beside the existing `public` condition.
- The module docstring lists the regime: « `character`: like `perceiver`,
  and only the entities of the character's view (TICKET-0127, D1). »
Error and empty cases: `ValueError` as stated.

### C-05 -- the text a view gives a fact
Produced by: BRIEF-0127-C   Consumed by: BRIEF-0127-C, D
In `perspective_selectors.py`:
```python
def view_texts(db: Session, view: PerspectiveView, facts: list) -> list[str]
```
Public view: `fact_texts(db, facts)`. Character view: for each fact, its
belief's `text` when not `None`, else its text at the belief's `as_of`
(`fact_texts_at`, one call for those facts), in the input order.
Error and empty cases: `[]` for `[]`; a fact without a belief on a character
view -> `ValueError` (selectors pass only facts of `view.fact_ids`).

### C-06 -- the selector family over a view
Produced by: BRIEF-0127-C   Consumed by: BRIEF-0127-D, E
Family rule (every member): `fn(*args, view: PerspectiveView, db) ->
list[dict]`; every row carries `"section"`; a row never carries a key of
`perspective_isolation.FORBIDDEN_KEYS`; a fact is shown only when its id is
in `view.fact_ids`, with `view_texts` (C-05); an entity is named only when its
id is in `view.entity_ids`. `secret` on a row is `view.kind == "character"
and view.beliefs[fact.id].secret`; `certainty` is the belief's on a
character view, `None` on a public one.
Rows (sections):
- `identity {section, entity_id, name, type}` (unchanged);
- `facets {section, label, aspect, content, secret, certainty}`;
- `memberships {section, faction_name, role}` (unchanged);
- `members {section, member_name, role}` (unchanged);
- `factions {section, entity_id, name, faction_type, description}` (unchanged);
- `public_mentions {section, content, participants, secret, certainty}`;
- `laws`, `skills` (unchanged);
- `acquaintances {section, name, type}`;
- `own_skills {section, name, base_domain, system, rank_label}`.
Rule M (a current non-secret membership of member E in faction F is shown):
`F in view.entity_ids and E in view.entity_ids and ((E.is_public and
F.is_public) or E == view.character_id or F in view.member_of)`. On a public
view this is today's rule.
Members:
1. `known_dossier(entity_id, world_id, view, db)`: `[]` when the entity is not
   in `view.entity_ids` or not of the world. `identity`; then `facets` rows
   for `_participant_facts` -- which now also returns the facts of the events
   the entity takes part in (`EventParticipant.entity_id`, F1), in the same
   sort -- kept in `view.fact_ids`, labelled `"Événement"` when the fact has
   an `event_id`, else `_label(fact)`; then lien rows (`label "Lien"`) kept
   when the fact is in the view and the other end in `view.entity_ids`; then
   `memberships` (the `read_public_memberships` names kept when every current
   membership of the entity bearing that faction name passes rule M -- a
   secret one never does); then, for a faction, `members` from the
   faction-keyed WHERE triplet kept by rule M.
2. `known_factions(world_id, view, db)`: one row per active faction whose id is
   in `view.entity_ids` (no SQL `is_public` filter), by name then id; its
   `description` the `view_texts` of its `description` facts in the view,
   joined by `\n`, or `None`.
3. `known_facts_mentioning(text, world_id, view, db)`: the facts of
   `view.fact_ids` whose `view_texts` text holds every token of 3+ letters of
   `text` (as today), by (that text, id); `participants` the names of their
   `FactParticipant` entities in `view.entity_ids` (as today).
4. `world_laws(world_id, view, db)` unchanged.
5. `known_skills(world_id, view, db)` unchanged (reads `view.skill_ids`).
6. `self_sheet(world_id, view, db)`: `[]` unless `view.kind ==
   "character"`. `acquaintances` rows for `encounters.acquaintances(db,
   view.character_id)` in `view.entity_ids`, by (name, id); then `own_skills`
   rows for the character's `Skill` rows: base domains first in
   `BASE_SKILL_DOMAINS` order, then definitions by name; `name` = the
   definition's name or the domain key; `base_domain`; `system` = the
   definition's system name or `None`; `rank_label = world_ladder(db,
   world_id)[rank].label`.
`public_member_ids` (TICKET-0129) is unchanged.
Error and empty cases: as stated; no member raises on an absent entity.

### C-07 -- the two selector tables
Produced by: BRIEF-0127-C   Consumed by: BRIEF-0127-D
In `perspective_selectors.py`: the three public tables of C-01, unchanged.
Then:
```python
CHARACTER_SELECTORS: tuple[str, ...] = PERSPECTIVE_SELECTORS + ("self_sheet",)
_CHARACTER_LOOKUPS: dict[str, SelectorSpec] = {
    **_PERSPECTIVE_LOOKUPS,
    "self_sheet": SelectorSpec(fn=self_sheet, arity=1, row_cap=200, arg_kinds=("world_id",)),
}
CHARACTER_DESCRIPTIONS: dict[str, str] = { ... }   # verbatim below, CHARACTER_SELECTORS order

def lookups_for(view: PerspectiveView) -> dict[str, SelectorSpec]   # public -> _PERSPECTIVE_LOOKUPS, character -> _CHARACTER_LOOKUPS
def descriptions_for(view: PerspectiveView) -> dict[str, str]       # public -> PERSPECTIVE_DESCRIPTIONS, character -> CHARACTER_DESCRIPTIONS
```
`CHARACTER_DESCRIPTIONS`, verbatim:
- `known_dossier`: `"known_dossier(entity_id, $world) -- ce que ce personnage sait sur UNE entite nommee : son nom, les faits qu'il connait, ses liens et appartenances connus."`
- `known_factions`: `"known_factions($world) -- une ligne par faction que ce personnage connait."`
- `known_facts_mentioning`: `'known_facts_mentioning("text:<mots>", $world) -- les faits que ce personnage connait dont le texte contient ces mots (un sujet qui n\'est pas une entite nommee).'`
- `world_laws`: `"world_laws($world) -- les lois fondamentales du monde, connues de tous."`
- `known_skills`: `"known_skills($world) -- les compétences de ce monde que ce personnage connait."`
- `self_sheet`: `"self_sheet($world) -- ce personnage lui-même : les personnes qu'il a rencontrées et ses compétences avec leur rang (« qui ai-je rencontré ? », « que sais-je faire ? »)."`
Error and empty cases: a `self_sheet` call against a public view's table is
`unsupported_selector` (validation, R-20).

### C-08 -- the renderer's new suffixes and sections
Produced by: BRIEF-0127-C   Consumed by: BRIEF-0127-D
In `src/world_engine/lore_render.py`:
- `_format_facets`: `f"{label}{aspect} : {content}{certainty}{secret}"`,
  `certainty = f" (certitude : {row['certainty']})" if row.get("certainty") else ""`
  (the `aspect` and `secret` parts unchanged).
- `_format_public_mentions`: the current line, then the same `certainty`
  suffix, then `" [secret]"` when `row.get("secret")`.
- `_format_acquaintances(row)`: `f"{row.get('name')} ({row.get('type')})"`.
- `_format_own_skills(row)`: `f"{row.get('name')} ({row.get('system') or 'sans système'}, {row.get('base_domain')}) : {row.get('rank_label')}"`.
- `_SECTION_FORMATTERS` gains `"acquaintances"` then `"own_skills"` after
  `"skills"`; the section-vocabulary comment above the formatters names them
  (« acquaintances, own_skills from the character perspective (TICKET-0127) »).
Error and empty cases: a public row (`certainty None`, `secret False`)
renders exactly as before.

### C-09 -- the executor over a view
Produced by: BRIEF-0127-D   Consumed by: BRIEF-0127-D (flow), E (check)
In `perspective_query.py`:
```python
def perspective_scope(view: PerspectiveView) -> NameScope
def resolve_view_mentions(plan, world_id, db, view, bindings=None) -> dict[str, NamedResolution]
def execute_perspective_plan(plan, view, db, bindings=None) -> PerspectiveResult
def execute_public_plan(plan, world_id, db, bindings=None) -> PerspectiveResult
```
- `perspective_scope`: public -> `public_scope(view)` (unchanged);
  character -> `NameScope("character", known_fact_ids=view.fact_ids,
  entity_ids=view.entity_ids)`.
- `resolve_view_mentions` is today's `resolve_public_mentions` (renamed, its
  one caller in the audit follows) with `perspective_scope(view)`;
  `BindingRefused` text « binding {ref!r} is not one of the mention's
  candidates in this perspective ».
- `execute_perspective_plan` is today's `execute_public_plan` body with
  `lookups_for(view)` for validation and dispatch and the given view (no
  `public_view` call).
- `execute_public_plan(plan, world_id, db, bindings)` returns
  `execute_perspective_plan(plan, public_view(db, world_id), db, bindings)`.
Verdicts: `PERSPECTIVE_VERDICTS` unchanged (PI3).
Error and empty cases: as today.

### C-10 -- the audit over a view
Produced by: BRIEF-0127-D   Consumed by: BRIEF-0127-D (flow), E (panel labels)
In `perspective_audit.py`:
- `WITHHELD_REASONS` = today's six, then `"not_known", "entity_unknown",
  "membership_unknown", "skill_unknown", "false_belief", "stale_version",
  "concealed"`.
- `withheld_for(plan, view, db, bindings=None) -> list[dict]`;
  `withheld(plan, world_id, db, bindings=None)` returns `withheld_for(plan,
  public_view(db, world_id), db, bindings)`.
- A public view: exactly today's lines.
- A character view, per call (`subject` = the dossier entity's name or the
  searched text, `content` as below):
  | call | line | reason | content |
  |---|---|---|---|
  | `known_dossier` on E not in `view.entity_ids` (E matched under `NAMES_ONLY`) | one | `entity_unknown` | E's name |
  | `known_dossier` / `known_facts_mentioning`: a fact not in `view.fact_ids` | per fact | `creator_only` if creator-only; else `concealed` if `view.door == "player"` and the holder's stored row on it is `is_secret` and not `unaware`; else `not_known` | the fact's current text |
  | same, a fact in `view.fact_ids` whose belief is `incorrect` | per fact | `false_belief` | the fact's current text |
  | same, a fact in the view, belief `text is None`, `fact_is_stale(fact, as_of)` | per fact | `stale_version` | the fact's current text |
  | `known_dossier`: a secret membership of E, or a secret member of faction E | per row | `secret_membership` | `_membership_line(...)` |
  | `known_dossier`: a non-secret membership or member failing rule M | per row | `membership_unknown` | `_membership_line(...)` |
  | `known_factions`: an active faction not in `view.entity_ids` | per faction | `entity_unknown` | its name |
  | `known_skills`: a definition not in `view.skill_ids` | per definition | `skill_unknown` | its name |
  | `world_laws`, `self_sheet` | none | -- | -- |
  The dossier's facts are those of C-06 member 1 (participants, events,
  liens); `known_facts_mentioning` audits `_facts_matching` on current texts.
- Rows `{reason, subject, content}` sorted as today, through the module's one
  existing dict line (R-25).
Error and empty cases: `[]` for an invalid plan or an ambiguous mention.

### C-11 -- the renderer of a character's answer
Produced by: BRIEF-0127-D   Consumed by: BRIEF-0127-D (flow)
In `perspective_render.py`:
```python
CHARACTER_NOTHING_KNOWN_MESSAGE = "Rien de ce que {nom} sait ne répond à cette question."
CHARACTER_UNSUPPORTED_MESSAGE = "Cette question ne peut pas recevoir de réponse à partir de ce que {nom} sait."

def render_perspective(result, question, spec, *, nom=None, exchanges=None) -> RenderedAnswer
def render_public(result, question, spec, exchanges=None) -> RenderedAnswer   # = render_perspective(..., nom=None, exchanges=exchanges)
```
`nom is None`: today's constants. Otherwise `nothing_known` and
`unsupported_selector` are the two constants formatted with `nom`,
`ambiguous_mention` is `AMBIGUOUS_MESSAGE`; renderer `deterministic`, no model
call. `answered`: `lore_render.render` over the rows, as today.
Error and empty cases: as today.

### C-12 -- the flow and its journal
Produced by: BRIEF-0127-D   Consumed by: BRIEF-0127-D (routes)
In `cockpit/perspective_flow.py`:
```python
UNKNOWN_CHARACTER_MESSAGE = "Personnage inconnu."
def ask_flow(db, *, question, world_id, asked_by, attempt, character_id=None, door="creator") -> dict
def resolve_flow(db, *, plan_raw, bindings, question, world_id, asked_by, attempt,
                 character_id=None, door="creator") -> dict
```
- The view first: `public_view(db, world_id)` when `character_id is None`,
  else `character_view(db, world_id, character_id, door=door)`;
  `UnknownCharacter` -> `HTTPException(422, UNKNOWN_CHARACTER_MESSAGE)` before
  the ping and before any journal row.
- Planner `descriptions=descriptions_for(view)`; executor
  `execute_perspective_plan(plan, view, db, bindings)`; audit
  `withheld_for(plan, view, db, bindings)`; renderer
  `render_perspective(result, question, spec, nom=view.character_name,
  exchanges=exchanges)`.
- The response keys are unchanged: `{verdict, answer, renderer, candidates,
  plan, rows, withheld}`.
- Payloads: today's keys with `"perspective": view.kind` and
  `"character_id": character_id`. `PERSPECTIVE = "public"` is removed.
- `writes/lore_usage.PAYLOAD_KEYS["perspective_ask"]` and
  `["perspective_resolve"]` gain `"character_id"`; the comment above them
  reads « perspective steps (TICKET-0125, TICKET-0127): `perspective` is
  `public` or `character`, `character_id` the character asked as (None for
  public), `asked_by` `creator` or `player:<user_id>`, `withheld` the
  audit's lines. »
Error and empty cases: 503 / 502 / 422 refused as today.

### C-13 -- the routes
Produced by: BRIEF-0127-D   Consumed by: BRIEF-0127-E
Creator, `cockpit/routes/lore_perspective.py`:
- both bodies gain `character_id: Optional[str] = None`;
- `_check_perspective(perspective, character_id)`: accepted only `("public",
  None)` and `("character", <non-empty>)`; otherwise 422
  `UNKNOWN_PERSPECTIVE_MESSAGE`, before any journal row;
- ask / resolve pass `character_id=body.character_id, door="creator"`;
- `GET /api/lore/perspective/characters?world_id=<id>` ->
  `perspective_view.world_characters(db, world_id)`.
Player, `cockpit/routes/player.py`:
- `CHARACTER_NOT_FOUND = "Personnage introuvable."`;
- `GET /api/joueur/personnage?profile_id=&world_id=` -> `_open_world`,
  `_player_profile`, then `{"character_id": id, "name": name}` from
  `player_character_of`, or `{"character_id": None, "name": None}`;
- `CharacterSavoirAskBody(profile_id, world_id, character_id, question,
  attempt_id=None)`, `CharacterSavoirResolveBody(profile_id, world_id,
  character_id, plan, bindings, question, attempt_id=None)`;
- `_own_character(profile_id, world_id, character_id, db)`: 404
  `CHARACTER_NOT_FOUND` unless `player_character_of(...)` names that id;
- `POST /api/joueur/personnage/savoir/ask` and `/resolve`: `_open_world`,
  `_player_profile`, `_own_character` (none journals), then the flow with
  `character_id`, `door="player"`, `asked_by=f"player:{profile_id}"`; the
  answer through `_player_answer`.
Neither module gains a `select(` (PR8).
Error and empty cases: as stated.

### C-14 -- the two screens
Produced by: BRIEF-0127-E   Consumed by: the live gate
Lore (`frontend/src/lore/`):
- `perspectiveState` gains `characterId: ''` and `characters: []`;
  `loadPerspectiveCharacters()` reads `GET
  /api/lore/perspective/characters?world_id=<serverState.worldId>`; the ask
  and resolve bodies send `character_id: perspectiveState.perspective ===
  'character' ? perspectiveState.characterId : null`;
  `resetPerspectiveForWorld` also empties `characterId` and `characters`.
- `PerspectivePanel.svelte`: a second option `<option value="character">Un
  personnage — ce qu'il sait</option>`; when chosen, a character `<select>`
  with `<optgroup label="Personnages joueurs">` (type `player`) and
  `<optgroup label="PNJ">`; « Interroger » disabled until a character is
  chosen; the answer heading reads « Ce que voit le joueur » for public and
  « Ce que sait <name> » for a character; `REASON_LABEL` gains
  `skill_not_visible: 'compétence invisible à la création'`, `not_known:
  'inconnu de ce personnage'`, `entity_unknown: 'entité inconnue de ce
  personnage'`, `membership_unknown: 'appartenance inconnue de ce
  personnage'`, `skill_unknown: 'compétence inconnue de ce personnage'`,
  `false_belief: 'croyance fausse — la vérité'`, `stale_version: 'version
  périmée — le texte actuel'`, `concealed: 'su mais caché (porte joueur)'`.
Player (`frontend/src/joueur/`):
- `joueurState` gains `character: null`; `loadCharacter()` reads `GET
  /api/joueur/personnage?profile_id=<id>&world_id=<id>` and sets
  `character` to `{id, name}` or `null`; `openWorld(w)` calls it when `w`
  is set;
- `askSavoir` / `confirmSavoir` post to `/api/joueur/personnage/savoir/ask`
  / `/resolve` with `character_id` when `joueurState.character`, else to
  today's public routes;
- `WorldPage.svelte`'s section heading reads « Mes savoirs — <name> » when
  `joueurState.character`, else « Ce que tout le monde sait »; the rest of
  the section is unchanged.
Rebuilt; the build committed.

### C-15 -- the check `character_perspective.py` (family)
Produced by: BRIEF-0127-B (CP1-CP3), C (CP4-CP5), D (CP6-CP7)
Consumed by: the ticket's acceptance arrows; fixture writers: R-28
`tooling/verify/checks/character_perspective.py`, first docstring sentence:
« G1 check for TICKET-0127 -- a character's perspective answers only what he
knows, keeps a secret from the player's door, and journals every question. »
Fresh temp-file SQLite (`WORLD_ENGINE_DATABASE_URL` set before any
`world_engine` import, as `player_routes._fresh_engine`); never Nia's DB; a
rule that collected nothing is a FAILURE; exit 1 on any failure.
Fixture `_extend(engine, ids)` on top of `perspective_isolation._build_world`
(imported), through sanctioned writers, in this order:
1. entities (non-public unless said): `mira` « Mira » NPC; `vex` « Vex » NPC;
   `twin3` « Twin » NPC; `ordre` « Ordre » faction; `lune` « Lune » player
   character with `user_id` = a profile « Ana » (`create_player_profile`),
   and a second profile « Bo »; the world `open_to_players = True`;
2. `F8` « Shade porte un masque » (`description`, participant Shade), a
   `rencontre` default on Shade at `knows`; `record_encounter(mira, shade,
   source="relation")`; then `update_fact_content(F8, "Shade a ote son
   masque", kind="changement")`;
3. knowledge (`write_knowledge(db, entity_id=..., fact_id=..., level=...)`,
   its default mode, which inserts): Mira on F7 `rumor`,
   `is_secret=True`; Mira on F2 `knows`, content « Hero fut affranchi »,
   `is_incorrect=True`; Lune on F7 `rumor`, `is_secret=True` (a deliberate
   breach of INV-07: the player's door must hold even so);
4. Mira's membership in Cabal, not secret (`write_membership`);
5. `F9` « Vex vend des secrets » (`description`, participant Vex, no default);
6. an event type « Fait » (role « qui », characters and factions); `E1`
   « Le sacre de Hero » (Hero, scope world `knows`); `E2` « La fuite de
   Shade » (Shade and Mira, no scope);
7. `SkillDefinition` « Ombre » (`perception`, `visible_at_creation=False`,
   no system); Mira's `Skill` rows: `agility` rank 2, `perception` rank 1 on
   Ombre; `SkillDefinition` « Lame » (`agility`, `visible_at_creation=False`,
   no system), held by nobody;
8. `F10` « Hero cache une dague » (`information`, participant Hero, no
   default); Shade's membership in Guild, not secret.
Rules (exact sets; R-27 measured them):
- CP1 (B, static): `perspective_view.py` holds none of
  `perspective_isolation.FORBIDDEN` and imports none of its
  `CREATOR_SELECTORS`.
- CP2 (B): `character_view(db, wid, mira, door="creator")`: `fact_ids ==
  {F1, F2, F4, F5, F6, F7, F8, E1, E2}`; `entity_ids == {hero, guild,
  guild2, twin1, twin2, mira, shade, cabal}`; `skill_ids == {ombre}`;
  `member_of == {cabal}`; `beliefs[F2]` text « Hero fut affranchi »,
  `incorrect`; `beliefs[F7]` certainty « rumeur », `secret`, text `None`;
  `beliefs[F8]` text `None`, `fact_is_stale(F8, as_of)`; `beliefs[F1].as_of
  is None`; `set(beliefs) == fact_ids`. `door="player"`: the same minus F7.
  `character_view` on `ordre` (a faction), on an unknown id, and on `mira`
  under the world id `"no-world"` raise `UnknownCharacter`; `door="x"`
  raises `ValueError`.
  `public_view(db, wid)` has the defaults of C-02.
- CP3 (B): the names of `surfaces(db, wid, NameScope("character",
  known_fact_ids=v.fact_ids, entity_ids=v.entity_ids))` (Mira's creator view
  `v`) belong exactly to `v.entity_ids`; `resolve_named("Twin", "person",
  ...)` under it is `ambiguous` with exactly `{twin1, twin2}`; « Vex » is
  `unmatched`; `NameScope("character", known_fact_ids=frozenset())` and
  `NameScope("public", known_fact_ids=frozenset(), entity_ids=frozenset())`
  raise `ValueError`.
- CP4 (C): selectors on Mira's creator view (labels from `FACETS`):
  `known_dossier(hero)` facets `{(Description, « Hero porte une cape
  rouge », False, None), (Histoire, « Hero fut affranchi », False, None),
  (Événement, « Le sacre de Hero », False, None), (Lien, F5's text, False,
  None)}` as `(label, content, secret, certainty)`; memberships `{Guild,
  Cabal}`; `known_dossier(shade)` facets contents `{« Shade est une ombre »,
  « Shade creuse un tunnel », « Shade porte un masque », « La fuite de
  Shade »}`; `known_dossier(cabal)` members `{Hero, Mira}`;
  `known_dossier(vex)` and `(ordre)` are `[]`; `known_factions` names
  `[Cabal, Guild, Guild2]`; `known_facts_mentioning("tunnel")` is `[(« Le
  tunnel cache un tresor », [], True, « rumeur »), (« Shade creuse un
  tunnel », [Shade], False, None)]` as `(content, participants, secret,
  certainty)`, and on the player's view only the second; `self_sheet`
  acquaintances `[(Shade, character)]`, own_skills `[(agility, agility,
  None, Apprenti), (Ombre, perception, None, Initié)]`; `known_skills` names
  `[Ombre]`. On `public_view`: `known_dossier(hero)` facets contents `{F1,
  « Le sacre de Hero », F5}`, memberships `{Guild}`; `self_sheet` is `[]`.
  No row of any call holds a key of `FORBIDDEN_KEYS`.
- CP5 (C): `lore_render._serialize_rows_by_section` over the tunnel rows
  holds `« Le tunnel cache un tresor » (certitude : rumeur) [secret]` and
  `« Shade creuse un tunnel » -- Shade`; over `self_sheet`'s rows `Shade
  (character)` and `agility (sans système, agility) : Apprenti`; over
  public `known_dossier(hero)` the F1 line `Description : Hero porte une cape
  rouge` with no suffix.
- CP6 (D): executor and audit on Mira's views (`_plan` of
  `perspective_isolation`): `known_dossier` « Hero » answered with C-06's
  rows; « Vex » `nothing_known`; « Twin » `ambiguous_mention` with exactly
  the two public Twins; a binding to `twin3` raises `BindingRefused`;
  `_plan("self_sheet")` on `public_view` is `unsupported_selector`.
  `withheld_for` as `(reason, subject, content)`: « Hero », creator door ->
  `{(creator_only, Hero, « Hero trahira la guilde »), (false_belief, Hero,
  « Hero fut esclave »), (not_known, Hero, « Hero cache une dague »),
  (secret_membership, Hero, « Guild2 (-) »)}`; « Shade » ->
  `{(stale_version, Shade, « Shade a ote son masque »), (membership_unknown,
  Shade, « Guild (-) »)}`;
  `text:tunnel` creator door -> `[]`, player door -> `{(concealed, tunnel,
  « Le tunnel cache un tresor »)}`; `known_factions` -> `{(entity_unknown,
  Ordre, Ordre)}`; « Vex » -> `{(entity_unknown, Vex, Vex)}`; `known_skills`
  -> `{(skill_unknown, Lame, Lame)}`, and on `public_view`
  `{(skill_not_visible, Lame, Lame), (skill_not_visible, Ombre, Ombre)}`.
  `withheld` (public) of « Hero » is PI4g's four lines plus `(not_public,
  Hero, « Hero cache une dague »)`.
  `render_perspective(nothing_known, ..., nom="Mira")` prose is « Rien de ce
  que Mira sait ne répond à cette question. ».
- CP7 (D, TestClient, `player_routes` harness imported: `_seed_prompts`,
  `_Stub`, `_swap`, `_events`, `_all_events`, `_attempt`): (a) `GET
  /api/lore/perspective/characters` lists Lune first, then Hero, Mira,
  Shade, Twin, Twin, Twin, Vex, keys exactly `{id, name, character_type}`; (b)
  `perspective "character"` without `character_id`, `"public"` with one, and
  an unknown id -> 422 (`Perspective inconnue.` / `Personnage inconnu.`), no
  journal row; (c) creator ask as Mira, plan `known_facts_mentioning`
  « tunnel » -> 200 with `CREATOR_KEYS`, the render stub's user message holds
  « Le tunnel cache un tresor » and `[secret]`, one row `perspective_ask/ok`
  with `perspective "character"`, `character_id` Mira, `asked_by "creator"`;
  (d) `GET /api/joueur/personnage` -> `{character_id: lune, name: "Lune"}`
  for Ana, both `None` for Bo; (e) Ana asks as Lune, same plan -> 200 with
  `PLAYER_KEYS`, the render stub's user message does NOT hold « Le tunnel
  cache un tresor », the journal row's `withheld` holds `(concealed, tunnel,
  « Le tunnel cache un tresor »)` and `character_id` Lune, `asked_by
  "player:<ana>"`; (f) Bo asks with Lune's id -> 404 `Personnage
  introuvable.`, no row; (g) resolve as Lune, plan « Twin » bound to `twin3`
  -> 422 `Choix refusé.`, one `perspective_resolve/refused` row.
Named mutations (each must turn the named rule red): drop the creator-only
subtraction of `character_view` -> CP2; drop its player-door `is_secret`
filter -> CP2 and CP7e; drop the `character` condition of `surfaces` -> CP3;
drop rule M's `member_of` branch -> CP4; return `public_view` from the flow
for a character -> CP7c.

## Gate output

(a) Property trace -- property, finding, declaring file opened:
- `PublicView` fields, sole builder `public_view` -- R-02 -- `perspective_selectors.py`
- `public_*` selector names, row keys, sections, table order and caps -- R-02 -- `perspective_selectors.py`
- every reference to a renamed symbol -- R-03 -- the grep itself
- `execute_public_plan` order, verdicts, `context_sections` rule; callers -- R-04 -- `perspective_query.py`
- `public_scope` returns `NameScope("public", known_fact_ids=...)` -- R-04 -- `perspective_query.py`
- audit reasons, branches, one `"subject"` literal -- R-05 -- `perspective_audit.py`
- the three verdict constants, `render_public` order -- R-06 -- `perspective_render.py`
- flow imports, `PERSPECTIVE`, payload keys, 503/502/422 journaling -- R-07 -- `cockpit/perspective_flow.py`
- route bodies, `_check_perspective`, `UNKNOWN_PERSPECTIVE_MESSAGE` -- R-07 -- `cockpit/routes/lore_perspective.py`
- `PLAYER_ANSWER_KEYS`, `_open_world`, `_player_profile`, `select(` names -- R-08 -- `cockpit/routes/player.py`
- `REGIMES`, `_APPELLATION_RULES`, `NameScope` validation, `surfaces` entity filter -- R-09 -- `name_index.py`
- `resolve_known_for_entity` scope, stored row wins whatever `is_secret`, `as_of` -- R-10 -- `knowledge_resolve.py`
- `Knowledge.content_raw`, `is_incorrect`, `is_secret`, unique `(entity_id, fact_id)` -- R-11 -- `models/canon_knowledge.py`
- `fact_texts`, `knowledge_texts`, `fact_texts_at`, `fact_is_stale`, `version_text` -- R-12 -- `prose_render.py`, `fact_versions.py`
- `creator_only_fact_ids` signature; the tick's `[SECRET]` precedent; INV-01 text -- R-13 -- `facet_reads.py`, `tick_context.py`, `CLAUDE.md`
- `acquaintances` returns every paired id; `record_encounter` signature -- R-14 -- `encounters.py`
- `EventParticipant` columns; event fact has no `fact_participant`; event fact text; `FACETS` labels; event writers -- R-15 -- `models/canon_event.py`, `writes/events.py`, `facets.py`, R-27 measure
- `read_public_memberships`, `read_public_membership_faction_ids` WHERE triplet -- R-16 -- `context.py`
- `Skill`, `SkillDefinition` nullable columns, `visible_skill_ids`, `world_ladder` labels, `BASE_SKILL_DOMAINS` -- R-17 -- `models/canon_skill.py`, `creation_rules.py`, `skill_ranks.py`
- `Character.character_type`, `user_id`, one PC per user per world -- R-18 -- `models/canon.py`
- formatters, `_SECTION_FORMATTERS`, unknown section raises; lore_isolation R10-R14 -- R-19 -- `lore_render.py`, `checks/lore_isolation.py`
- `SelectorSpec` fields, `validate_plan(lookups=)`, `_call_args`, `draft_plan(descriptions=)` -- R-20 -- `lore_selectors.py`, `lore_query.py`, `lore_plan.py`
- `PAYLOAD_KEYS` exactness, CHECK on kind/step only, `C09_KEYS` pin -- R-21 -- `writes/lore_usage.py`, `models/pipeline.py`, `checks/player_entry_schema.py`
- PI1-PI6, PR1-PR8, PSH1-PSH5, CD3, K3, name_index R3/F1 rules and helpers -- R-22 -- each check's implementation
- panel labels, state keys, bodies, world page section, player state -- R-23 -- the five frontend files
- module and CLAUDE.md budgets -- R-24 -- `module_budget.py`, `claude_md_contract.py`
- name bans -- R-25 -- `knowledge_identity.py`, `lore_as_facts.py`, `event_contexts.py`
- FILE_MAP / DECISIONS_INDEX generators; ARCHITECTURE footer -- R-26 -- `gen_file_map.py`, the two standards files
- CP fixture sets -- R-27 -- measured
- fixture writers' signatures and modes -- R-28 -- `writes/knowledge.py`, `writes/facts.py`, `writes/factions.py`, `writes/users.py`, `encounters.py`

(b) Case tables.

Rule M (C-06) -- membership (member E, faction F), current and not secret:
| F in view | E in view | E, F public | E is holder | holder in F | shown |
|---|---|---|---|---|---|
| no | -- | -- | -- | -- | no |
| yes | no | -- | -- | -- | no |
| yes | yes | yes | -- | -- | yes |
| yes | yes | no | yes | -- | yes |
| yes | yes | no | no | yes | yes |
| yes | yes | no | no | no | no |
A secret membership: never shown (audit `secret_membership`). Public view:
E, F in view <=> both public, so row 3 or rows 1-2 only -- today's rule.

`character_view` (C-03) -- facts and doors:
| fact | creator door | player door |
|---|---|---|
| resolves `unaware` | out | out |
| creator-only | out | out |
| holder's stored row `is_secret`, above `unaware` | in, `secret` | out |
| otherwise above `unaware` | in | in |
And: `door` outside `PERSPECTIVE_DOORS` -> `ValueError`; not an active
character of the world -> `UnknownCharacter`.

Name scopes (C-04):
| regime | known_fact_ids | entity_ids | result |
|---|---|---|---|
| perceiver / public | given | absent | valid |
| perceiver / public | absent | -- | ValueError |
| perceiver / public / others | -- | given | ValueError |
| character | given | given | valid; only entities in `entity_ids` |
| character | absent or entity_ids absent | -- | ValueError |
| names_only / creator / prose | given | -- | ValueError (unchanged) |

Selector tables (C-07) by view:
| plan selector | public view | character view |
|---|---|---|
| the five public names | dispatched | dispatched |
| `self_sheet` | `unsupported_selector` | dispatched |
| any other | `unsupported_selector` | `unsupported_selector` |

Audit (C-10): the case table of C-10; every row is reached by CP6:
`entity_unknown` (« Vex », `known_factions` -> Ordre), `creator_only`,
`false_belief`, `not_known`, `secret_membership` (« Hero »),
`stale_version`, `membership_unknown` (« Shade »), `concealed`
(`text:tunnel` at the player's door), `skill_unknown` (`known_skills` ->
Lame); the public reasons by PI4g and CP6's public lines.

Creator route perspective check (C-13):
| perspective | character_id | outcome |
|---|---|---|
| public | None | flow, public view |
| public | set | 422 `Perspective inconnue.`, no row |
| character | set, active character of the world | flow, character view |
| character | set, unknown | 422 `Personnage inconnu.`, no row |
| character | None or empty | 422 `Perspective inconnue.`, no row |
| other | -- | 422 `Perspective inconnue.`, no row |

Player routes (C-13):
| world open | profile active player | character is the profile's in this world | outcome |
|---|---|---|---|
| no | -- | -- | 404 `Monde introuvable.`, no row |
| yes | no | -- | 404 `Profil introuvable.`, no row |
| yes | yes | no | 404 `Personnage introuvable.`, no row |
| yes | yes | yes | flow at the player's door |

Renderer (C-11):
| nom | verdict | prose |
|---|---|---|
| None | each | today's constant / model |
| name | nothing_known | `CHARACTER_NOTHING_KNOWN_MESSAGE` with the name |
| name | unsupported_selector | `CHARACTER_UNSUPPORTED_MESSAGE` with the name |
| name | ambiguous_mention | `AMBIGUOUS_MESSAGE` |
| name | answered | model over rows, template fallback |

(c) Enumerations (pasted):

(c)-1 -- the rename's footprint: R-03.

(c)-2 -- the checks that read the touched modules:
```
$ grep -rln "perspective_\|routes/player\|lore_render\|name_index\|lore_usage\|creation_lore\|creation_designer\|pc_draft_reads\|player_creation\|pc_approval" tooling/verify/checks | sort
tooling/verify/checks/corpus_gate.py
tooling/verify/checks/creation_designer.py
tooling/verify/checks/creation_schema.py
tooling/verify/checks/creator_review.py
tooling/verify/checks/day_choice.py
tooling/verify/checks/draft_approval.py
tooling/verify/checks/json_ui_boundary.py
tooling/verify/checks/knowledge_identity.py
tooling/verify/checks/lore_facts_mentioning.py
tooling/verify/checks/lore_isolation.py
tooling/verify/checks/lore_usage.py
tooling/verify/checks/lore_write.py
tooling/verify/checks/name_index.py
tooling/verify/checks/name_resolution.py
tooling/verify/checks/npc_agent_strata.py
tooling/verify/checks/perspective_isolation.py
tooling/verify/checks/player_creation.py
tooling/verify/checks/player_entry_schema.py
tooling/verify/checks/player_routes.py
```
plus `player_shell.py`, which reads the frontend files (R-22). All
twenty were PASS at `6f4b578` (run in the RECON). A changes the code of
three of them (R-03); D changes `player_entry_schema.py`; E changes
`player_shell.py`; B creates `character_perspective.py`. The others are
kept green by contract, each named in a brief's Done means.

(c)-3 -- every `NameScope` built with a known-facts regime, and the one
regime test of `surfaces`:
```
$ grep -rn 'NameScope("perceiver"\|NameScope("public"\|"perceiver", known_fact_ids\|regime == "public"\|regime != "public"\|NameScope($' src --include=*.py
src/world_engine/day_concordance.py:378:    surfaces = name_surfaces(db, character.world_id, NameScope(
src/world_engine/day_concordance.py:379:        "perceiver", known_fact_ids=frozenset(resolve_levels_for_entity(db, character.id)),
src/world_engine/day_choice.py:108:        surfaces = name_surfaces(db, character.world_id, NameScope(
src/world_engine/day_choice.py:109:            "perceiver", known_fact_ids=frozenset(known),
src/world_engine/perspective_query.py:42:    return NameScope("public", known_fact_ids=view.fact_ids)
src/world_engine/name_index.py:123:        and (scope.regime != "public" or e.is_public)
```
None passes `entity_ids`; C-04's new field defaults to `None`, so none
changes.

(c)-4 -- every pin of the perspective payload keys:
```
$ grep -rn "asked_by\|\"withheld\"\|'withheld'" tooling/verify/checks/*.py | grep -v player_routes.py
tooling/verify/checks/player_entry_schema.py:38:    "perspective_ask": {"question", "perspective", "asked_by", "response", "withheld", "error"},
tooling/verify/checks/player_entry_schema.py:39:    "perspective_resolve": {"question", "perspective", "asked_by", "plan", "bindings", "response",
tooling/verify/checks/player_entry_schema.py:40:                            "withheld", "error"},
tooling/verify/checks/player_entry_schema.py:201:        payload.update(question="q", perspective="public", asked_by="creator", withheld=[])
tooling/verify/checks/creation_schema.py:128:    "creation_subject": {"draft_id", "asked_by", "story", "names", "keywords", "error"},
tooling/verify/checks/creation_schema.py:129:    "creation_design": {"draft_id", "asked_by", "lore", "proposal", "violations", "notes", "error"},
tooling/verify/checks/creation_schema.py:448:        payload.update(draft_id="d1", asked_by="player:u1", violations=[], notes=[])
tooling/verify/checks/player_creation.py:404:    elif any(p["asked_by"] != f"player:{ana}" for _, _, p in rows):
```
Only `player_entry_schema.py:38-40` pins the perspective keys (D edits it).

(c)-5 -- pins of the renderer's section set:
```
$ grep -rn "_SECTION_FORMATTERS" tooling/ --include=*.py
(empty)
```

(c)-6 -- callers of the public entry points D keeps as delegates: R-04's
list, plus `perspective_audit.withheld` imported by
`perspective_isolation.py:276,430` and `player_routes.py:175`, and
`render_public` called by `perspective_isolation.py:406,413`.

(d) Family contracts: C-06 (selectors) was written before its six members
and re-read after `self_sheet`: every member carries `"section"`, none emits
a forbidden key, each filters by the view. C-15 (the check) was written
before CP1 and re-read after CP7: every rule names exact sets, every set was
measured (R-27), every named mutation names the rule it turns red. C-10's
case table was re-read against C-06 member 1 (the same facts). Ticked.

(e) Gates and the modules that satisfy them:
- CP1 -- `perspective_view.py` (B): needs `Session`, `select`, models,
  `knowledge_resolve`, `facet_reads`, `context`, `encounters`,
  `creation_rules`, `prose_render`; PI1's `FORBIDDEN` forbids none of them.
- CP2-CP3 -- `perspective_view.py`, `name_index.py` (B).
- CP4-CP5 -- `perspective_selectors.py`, `lore_render.py` (C).
- CP6 -- `perspective_query.py`, `perspective_audit.py`,
  `perspective_render.py` (D).
- CP7 -- `cockpit/perspective_flow.py`, `routes/lore_perspective.py`,
  `routes/player.py`, `writes/lore_usage.py` (D); needs `select(` for the
  character lookups, which PR8 forbids in the three route/flow modules --
  satisfied by `perspective_view.py` (`player_character_of`,
  `world_characters`, `character_view`).
- PSH6 -- `perspective.svelte.js`, `PerspectivePanel.svelte`,
  `joueur.svelte.js`, `WorldPage.svelte`, the build (E).
Gates merely passed: PI1-PI6 (`perspective_selectors.py`, public behaviour
kept; PI4's world holds no event, so F1 changes none of its sets); PR1-PR8
(the routes keep their answer keys; no `select(` added to `player.py`); PSH1
(E keeps the five labels); PSH2-PSH3 (E's URLs start `/api/joueur/`, no
import leaves the folder); CD3 (A edits its counter; `creation_lore.py`
calls only `known_facts_mentioning(`); K3 (no new `subject` reference,
R-25); name_index R3 (B adds the regime to both literals); lore_isolation
R10-R14 (C adds formatters only); PS1 (D edits `C09_KEYS` with
`PAYLOAD_KEYS`); file_map (B, C, D, E regenerate); module_budget (R-24:
largest growth `perspective_selectors.py`, from 338 to about 480 lines and
21 top-level functions); claude_md_contract (E's texts within budget, R-24);
frontend_build_fresh / static_asset_freshness (E rebuilds).

## Drafting decisions flagged to Nia

1. Rule M: a membership the character did not take part in is shown only when
   both ends are public, or he is the member, or he belongs to that faction.
   « Qui fait partie de la Cabale ? » asked as a Cabal member names its
   non-public members he knows.
2. A known event appears in the dossier of each entity that took part in it,
   even when the event's text does not name that entity (F1 read
   literally).
3. The player's door does not filter on « is a PC »: the door alone decides
   (C1). The check proves it with a deliberately secret PC row.
4. The deterministic messages name the character in both doors (« Rien de ce
   que Lune sait... »), not « tu ».
5. The answer keys are unchanged: the Lore panel takes the character's name
   from its own list for the heading « Ce que sait <nom> ».
6. Belief text: the holder's own `content` wins over the version he saw;
   « croyance fausse » is never a row key, only an audit line with the true
   text.
7. `known_facts_mentioning` matches the words against the text the character
   knows (his version), while the audit matches on the current text, so a
   fact whose new text holds the words but whose old one does not shows in
   the audit only.
8. `world_characters` lists every active character of the world, the creator's
   own PC included, players first.
9. The public routes `/api/joueur/savoir/*` stay as they are; « Mes savoirs »
    switches by the presence of a character, read once when the world opens.

## Amendments

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
