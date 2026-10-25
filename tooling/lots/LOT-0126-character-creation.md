# LOT — TICKET-0126 "The player creates a character"

Lot RECON run in the chat session on `main` at `fb8557a` (PR #154; schema
v2.31). Briefs are executed one per session; this header is authoritative
on any conflict with a brief's embedded copy.

## Objective and cut

A player, in `/jouer`, creates a character in an open world: he writes who
he is, sets his skills within the world's creation rules, asks a designer
that reads only what everybody knows for a counter-proposal (skills, people
from his story, a starting place, memberships, knowledge), corrects it and
submits it. The creator sets the rules per world in Création and sees the
submitted drafts, read-only. One function judges every sheet. The visible
skills join the public view, so Lore's « Ce que tout le monde sait » can
answer about them.

The lot stops at the submission (L2, cut). The creator's review, the write
to canon, the NPC batches anchored on the character, masters, encounters,
G2 and K1-b are TICKET-0129.

## Briefs in this lot

- A -- `skill-stratum-move`: the skill models leave `canon.py` for
  `canon_skill.py`, a pure move.
- B -- `schema-v2-32`: the creation rules, the overrides, the five draft
  tables, the journal kind `creation`, the migration, the cascade, the docs.
- C -- `creation-rules-and-check`: the rules reader, the one check, the
  writer, the creator's routes and override fields; INV-67.
- D -- `public-skills`: the visible skills in the public view, a fifth
  public selector (planner included), the audit and the renderer; INV-66
  amended.
- E -- `creation-rules-ui`: Création > Compétences, the « Création de
  personnage » record and the override fields.
- F -- `character-designer`: the premise of a chosen world, the creation
  lore, the designer and its two prompts.
- G -- `player-creation-routes`: the draft writer and read shape, the
  player's creation routes, the journal.
- H -- `player-creation-screen`: the creation screen in `/jouer`.
- I -- `submitted-drafts-panel`: the creator's list and read-only panel in
  « Personnages joueurs »; the decisions entry.

## Dependency graph

- A -> B: B adds columns to the skill models where A put them (R-40).
- B -> C: C reads and writes B's tables.
- C -> D: `public_view` reads `visible_skill_ids` (C-03).
- C -> E: E calls C's routes (C-06).
- B, C -> F: the designer journals into B's kind and checks with C-04.
- D, F -> G: the catalogue reads `public_skills` (C-07); the designer route
  runs C-11.
- G -> H: the screen calls C-14.
- G -> I: the panel reads C-13 and the drafts G writes.
- E may run at any point after C; D before F is an order chosen to keep
  the INV-66 edits in sequence (D amends it, F extends it), not a
  dependency of F on D's code.

## RECON

### R-01 -- schema version and the migration skeleton
Opened: `src/world_engine/schema_version.py:15`; `world-engine-schema.md:3`;
`world-engine-schema-changelog.md:1-25`; `scripts/migrate_v2_31_player_entry.py`
(whole, 194 lines).
Finding: `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.31"`; the doc reads
`Current schema version: v2.31`; the changelog lists newest first under
`## CHANGELOG`. The v2.31 script refuses to run without `WORLD_ENGINE_ENV`
or `WORLD_ENGINE_DATABASE_URL`; `_refuse()` exits when `schema_meta` is older
than `_PREVIOUS_VERSION`; `_plan()` returns ADD COLUMN statements and
`(model, columns)` rebuilds still needed; `_apply()` runs them in one raw
transaction (`PRAGMA foreign_keys=OFF`, `PRAGMA legacy_alter_table=ON`,
`BEGIN` ... `COMMIT`, both pragmas reset); `_rebuild(cursor, model, columns)`
drops the table's named indexes, renames it `<table>_old`, creates it from
`CreateTable(model.__table__)` and its `CreateIndex`es (`_create_from_model`),
copies `columns`, drops `_old`; `_post_checks` raises `SystemExit` with every
problem; `_converge_schema_meta()` moves `schema_meta` forward. It writes no
data besides the journal copy.
Consequence: B's migration is a standalone copy of this skeleton at
`_PREVIOUS_VERSION = "v2.31"`, `_THIS_VERSION = "v2.32"`; it creates its new
tables through `_create_from_model` (the helper creates indexes too).

### R-02 -- the skill stratum in `models/canon.py`
Opened: `src/world_engine/models/canon.py:1-46, 576-724` (964 lines);
`src/world_engine/models/__init__.py:1-62, 84-86, 205-330`;
`src/world_engine/models/canon_faction.py:1-17`; the enumerations of (c).
Finding: lines 580-719 hold, in order, the comment and literal
`BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")`
(:584), `RANK_POINTS_CHECK` (:588-590), `SkillSystem` (:597-626),
`SkillDefinition` (:629-682) and `Skill` (:685-719); :720-721 are blank and
:722 opens the `discoverable_detail` header. No line of `canon.py` outside
580-719 names `BASE_SKILL_DOMAINS`, `RANK_POINTS_CHECK`, `SkillSystem`,
`SkillDefinition` or `Skill` (enumeration (c)-1). `canon.py` imports
`JSON, CheckConstraint, Column, DateTime, ForeignKey, Index, String, func,
text` from sqlalchemy (:34-44) and `Field, SQLModel` from sqlmodel (:45).
`canon_faction.py` is the extraction precedent: its own docstring, `from
.canon import _created_ts, _uuid` (:16). `models/__init__.py` imports
`BASE_SKILL_DOMAINS` (:62), `Skill`, `SkillDefinition`, `SkillSystem`
(:84-86) from `.canon` and lists them in `__all__` (:280-283, :321);
`RANK_POINTS_CHECK` is not exported and has no reader outside `canon.py`
(enumeration (c)-2). No module imports `models.canon` by path for these
names and no check reads `canon.py` for them (enumerations (c)-1, (c)-3).
Consequence: A moves lines 580-719 verbatim into `models/canon_skill.py`
and re-points the four `__init__` imports; `canon.py` drops to 822
lines, which is what lets B add columns. `static_table_names()` before and
after is the proof of a pure move (R-41).

### R-03 -- the skill system and skill definition columns
Opened: `src/world_engine/models/canon.py:597-682`.
Finding: `SkillSystem` (`skill_system`): `id, world_id, name, description,
points_to_rank_1..5 (Optional[int]), trial_to_rank_1..5 (Optional[bool]),
created_at, updated_at`; CHECK `ck_skill_system_rank_points`
(`RANK_POINTS_CHECK`); unique index `idx_skill_system_world_name`.
`SkillDefinition` (`skill_definition`): `id, world_id, name, base_domain,
system_id (FK skill_system.id ON DELETE RESTRICT, nullable), description,
points_to_rank_1..5, trial_to_rank_1..5, requires_master (bool, server
default 0), created_at, updated_at`; CHECKs
`ck_skill_definition_base_domain`, `ck_skill_definition_rank_points`; unique
`idx_skill_definition_world_name`. NULL in an override column inherits.
Consequence: B adds nullable override columns to both models by ADD COLUMN
(R-04's v2.29 precedent: nullable, no CHECK); their bounds are enforced by
the creator CRUD bodies (C), not the database.

### R-04 -- how v2.29 added columns to the skill tables
Opened: `scripts/migrate_v2_29_rank_trials.py:1-20, 147-195`;
`tooling/verify/checks/rank_trial_schema.py:1-60, 380-470`.
Finding: v2.29 added `skill_rank.trial_to_next` as `BOOLEAN NOT NULL DEFAULT
0` and `trial_to_rank_1..5` to `skill_system` and `skill_definition` as
plain `BOOLEAN` by ADD COLUMN, no CHECK. `rank_trial_schema.py` TS3
recreates the six tables in their v2.28 DDL (literal `V228_DDL`), runs the
v2.29 script and checks the eleven columns and rows; the v2.29 script adds
columns, it does not rebuild those three tables.
Consequence: columns added in v2.32 must be nullable (or carry a default)
so that a v2.28-shaped fixture migrated by v2.29 still loads; ADD COLUMN in
v2.32 leaves TS3 untouched.

### R-05 -- `skill_rank` and its one writer
Opened: `src/world_engine/models/config.py:230-259`;
`src/world_engine/writes/config.py:536-577`;
`tooling/verify/canon_write_policy.txt:50-51`.
Finding: `SkillRank` (`skill_rank`): at most one row per (world, rank), the
rank's label, `points_to_next`, `trial_to_next`; a missing row reads the
engine default. `upsert_skill_rank(db, *, world_id, rank, label,
points_to_next, trial_to_next=False)` is « the one writer of skill_rank »
(policy line 50 says so); `PUT /api/skill-ranks` rewrites all six rows.
Consequence: nothing in this lot writes or adds a column to `skill_rank`
(J1'); creation reads its labels through `skill_ranks.world_ladder` only.

### R-06 -- the rank ladder reader
Opened: `src/world_engine/skill_ranks.py` (whole, 163 lines).
Finding: `RANKS = (0, 1, 2, 3, 4, 5)`, `MAX_RANK = 5`, `DEFAULT_RANK = 1`
(« A new skill row starts here: Initié »), `DEFAULT_RANK_LABELS =
("Inexpérimenté", "Initié", "Apprenti", "Confirmé", "Expert", "Maître")`.
`world_ladder(db, world_id)` returns six `RankStep(rank, label,
points_to_next, trial_to_next)` over the engine defaults and never writes.
`points_to_next` and `trial_required` read the most specific override:
`definition`, then `system`, then the ladder (`getattr(owner, column, None)`
when the owner is not None). `skill_owners(db, skill_definition_id)` returns
`(system, definition)`, `(None, None)` for a base domain. Reads only.
Consequence: `creation_rules` (C-03) follows the same cascade order --
definition, then system, then the world's row, then the engine default --
and is reads only. The ladder's labels name the ranks in every French
message of C-04.

### R-07 -- the skills CRUD
Opened: `src/world_engine/cockpit/crud/skills.py` (whole, 667 lines, 23
top-level functions and methods, R-40).
Finding: routes on the shared `/api` router (`crud/_router.py`): `GET/PUT
/skill-ranks` (:124-159), `GET /skills/player-characters`, `GET
/skills/learnable`, `POST /skills` (`grant_skill`, :220-251: `rank` default
0, a `taught_by_id` must be another character at Maître in the skill, 422
otherwise), `GET /skills`, `PATCH /skills/{id}`, `GET/POST /skill-systems`,
`PUT/DELETE /skill-systems/{id}` (:318-445), `GET /skill-gaps`, `GET/POST
/skill-definitions`, `PUT/DELETE /skill-definitions/{id}` (:497-667).
`RankPointsBody` (:329-344) holds the ten optional threshold/trial fields;
`_rank_points(row)` (:346-347) and `_set_rank_points(row, body)` (:350-352)
copy them; `SkillSystemWriteBody(RankPointsBody)` adds `name, description`
(:355-357); `SkillDefinitionWriteBody(RankPointsBody)` adds `name,
base_domain, system_id, description, requires_master` (:508-515).
`_skill_system_dict` (:303-315) and `_skill_definition_dict` (:483-494)
return the row fields plus `**_rank_points(row)`. `create_skill_system`
(:360-383) and `update_skill_system` (:386-409) and
`update_skill_definition` (:581-641) set every body field, a PUT replacing
all of them. Every route reads the active world through `_world_id(db)`
(`crud/_shared.py:57-61`: the `is_active` world, 400 when none).
Consequence: C adds `GET/PUT /api/creation-rules` here and the override
fields to the two write bodies, their dicts and their setters (C-06). The
creator CRUD is keyed by the active world -- Création's posture, untouched.

### R-08 -- the canon write policy
Opened: `tooling/verify/canon_write_policy.txt:1-14, 44-60, 140-180`;
`tooling/verify/checks/single_canon_write.py:1-12`.
Finding: `[CANON_TABLES]` lists `skill skill_definition skill_system` and
`skill_rank` among others; `[ALLOWED_SITES]` lists `path::function tables`,
a comment line above each addition naming its ticket and brief; the six
skill-system and skill-definition routes of `crud/skills.py` are listed
(:175-180). `single_canon_write.py` fails when a canon table is written
from a site not listed; sites on non-canon tables are ignored; an
unattributable write site always fails.
Consequence: `creation_rules` is canon curated config (a world's rules, the
`skill_rank` family): C adds it to `[CANON_TABLES]` and adds
`src/world_engine/writes/creation_rules.py::write_creation_rules
creation_rules` with its comment line. The five `pc_draft*` tables are not
canon (pending, non-canon, the `quest_request` posture) and are never added.

### R-09 -- one player character per user and world
Opened: `src/world_engine/models/canon.py:149-175`.
Finding: `Character` declares the partial unique index
`idx_character_one_pc_per_user_world` on `(world_id, user_id)` where
`character_type = 'player'`; `user_id` is a plain column, `NULL` for NPCs.
Consequence: a profile that already holds a character of the world cannot
open a draft there (V1): the check is `Character.world_id == world_id,
Character.user_id == user_id, Character.character_type == "player"`.

### R-10 -- users and profiles
Opened: `src/world_engine/models/pipeline.py:708-722`;
`src/world_engine/writes/users.py:28-48`;
`src/world_engine/cockpit/routes/player.py:56-67`.
Finding: `User(id, name, email, role default 'player', created_at,
is_active)`. `create_player_profile` adds `User(name, role="player")`.
`routes/player.py` defines `WORLD_NOT_FOUND = "Monde introuvable."`,
`PROFILE_NOT_FOUND = "Profil introuvable."`, `_open_world(world_id, db)`
(404 unless the world exists and `open_to_players`) and
`_player_profile(profile_id, db)` (404 unless an active `player` user).
Consequence: the creation routes import `_open_world` and `_player_profile`
from `routes/player.py` (R-11 allows it: they are functions, not selects
added to `player.py`); a draft's `user_id` is a profile id.

### R-11 -- the player routes and their static guard
Opened: `src/world_engine/cockpit/routes/player.py` (whole, 129 lines);
`tooling/verify/checks/player_routes.py:1-60, 300-360`.
Finding: every route of `player.py` is under `/api/joueur/`; PR8 holds
`routes/lore_perspective.py` and `cockpit/perspective_flow.py` to no
`chat(` and no `select(`, `routes/player.py` to no `chat(` and `select(`
calls naming only `User`, `World` or `WorldLaw`; none of the three may hold
`World.is_active`, `_world_id(`, `write_usage_event` or an import of
`lore_selectors`; every route path literal of `player.py` starts with
`/api/joueur/`. `player.py` imports `_world_detail` from `routes/creator.py`.
Consequence: the creation routes live in `cockpit/routes/player_creation.py`
(G), held by rules of their own in `player_creation.py` (the check) in
PR8's spirit: no `chat(`, no `World.is_active`, no `_world_id(`, no import
of `lore_selectors`, every path under `/api/joueur/creation/`.

### R-12 -- the public view and the perspective selectors
Opened: `src/world_engine/perspective_selectors.py` (whole, 281 lines); the
enumeration (c)-4.
Finding: `PublicView(world_id, fact_ids, entity_ids)` is a frozen dataclass
(:29-33) built only by `public_view(db, world_id)` (:36-49): facts whose
public level is not `unaware` minus creator-only notes, and active
`is_public` entities. Members take `(*args, view, db)` and return rows
carrying `"section"`: `public_dossier` (:149-175, sections `identity`,
`facets`, `memberships`, `members`), `public_factions` (:178-202, section
`factions`, keys `entity_id, name, faction_type, description`),
`public_facts_mentioning` (:220-237, section `public_mentions`, every token
of 3+ letters present), `world_laws` (:240-243). `PERSPECTIVE_SELECTORS`
(:246-248), `_PERSPECTIVE_LOOKUPS` (:250-264, `SelectorSpec(fn, arity,
row_cap, arg_kinds, context_sections)`) and `PERSPECTIVE_DESCRIPTIONS`
(:266-281) share the four keys. The module imports `Entity, Fact,
FactionMembership, FactParticipant, Faction, Relation, WorldLaw` from
`.models`.
Consequence: D adds `skill_ids` to `PublicView` (built only at :49), a fifth
member `public_skills`, and its entries in the three tables, in that order
(C-07). The creation surfaces read places, factions and people through
this module's view (N2).

### R-13 -- the public executor and name scope
Opened: `src/world_engine/perspective_query.py` (whole, 122 lines);
`src/world_engine/name_index.py:48-68`; `src/world_engine/lore_resolve.py:30-75,
135-160`.
Finding: `public_scope(view)` is `NameScope("public",
known_fact_ids=view.fact_ids)`; `execute_public_plan` validates against
`_PERSPECTIVE_LOOKUPS`, resolves mentions under that scope and raises
`ValueError` on a row without `"section"`. `NameScope` requires
`known_fact_ids` for the `public` regime. `resolve_named(surface_form,
category, world_id, db, *, scope)` returns `NamedResolution(verdict,
entity_id, candidate_ids, rung, rungs_tried)`, verdict `matched` (one
candidate), `ambiguous` or `unmatched`; `CATEGORIES = ("place", "person",
"faction", "object", "other")` (:43); `normalize_surface(text)` (:73).
Consequence: the creation lore resolves the backstory's names with
`resolve_named(..., scope=public_scope(view))`, keeping `matched` only
(C-10).

### R-14 -- the audit
Opened: `src/world_engine/perspective_audit.py` (whole, 128 lines).
Finding: `WITHHELD_REASONS = ("creator_only", "not_public",
"entity_not_public", "secret_membership", "faction_not_public")` (:35-37).
`withheld(plan, world_id, db, bindings=None)` handles `world_laws`
(nothing), `public_factions`, `public_facts_mentioning`, and otherwise
takes `next(a for a, kind in zip(call.args, spec.arg_kinds) if kind ==
"entity_id")` (:122) -- a selector with no `entity_id` argument that
reached this line would raise `StopIteration`.
Consequence: D gives `public_skills` its own branch before :122 and a sixth
reason, `skill_not_visible` (C-07).

### R-15 -- the Lore renderer's section vocabulary
Opened: `src/world_engine/lore_render.py:100-176` (340 lines).
Finding: `_SECTION_FORMATTERS` (:131-145) maps 13 sections to formatters;
`_group_rows_by_section` raises `ValueError` on a section it does not hold
(:157-161). `_format_laws` returns `row["text"]`; `_format_public_mentions`
quotes the content and appends the participants.
Consequence: D adds a `skills` formatter, or an answered question about
skills would raise at render (C-07).

### R-16 -- the perspective isolation check
Opened: `tooling/verify/checks/perspective_isolation.py:1-200, 280-300`.
Finding: PI1 forbids `chat(`, `db.add(`, `.commit(`,
`include_creator_only`, `CREATOR`, `NameScope("creator"`,
`near_candidates`, `validate_binding` and four `lore_selectors` imports in
the four perspective modules (`FORBIDDEN`, :61-64); PI2 asserts
`len(PERSPECTIVE_SELECTORS) == 4` (:130-134) and that the three tables
share its keys in order, every `row_cap` non-zero, every context section a
`"section"` literal; PI4 builds its world in `_build_world(engine)` (:172), which `player_routes.py` imports.
Consequence: D edits PI2's count to 5 and adds a rule PI6 (C-07). The
`creation_rules` module D imports must keep PI1 true for the perspective
modules: it is imported, never inlined, and holds none of PI1's needles
itself only by choice -- PI1 scans the four perspective modules, not it.

### R-17 -- the plan validator and selector spec
Opened: `src/world_engine/lore_selectors.py:30-50`;
`src/world_engine/lore_query.py:66-110, 163-171`.
Finding: `SelectorSpec(fn, arity, row_cap, arg_kinds, context_sections=())`.
`validate_plan(plan, db, *, lookups=None)` rejects a selector outside
`lookups`, a wrong arity and an arg-kind mismatch (`"$world"` for
`world_id`). `_call_args` passes the world id for `$world`.
Consequence: `public_skills` is `SelectorSpec(fn=public_skills, arity=1,
row_cap=200, arg_kinds=("world_id",))`, like `public_factions`.

### R-18 -- the shared perspective flow
Opened: `src/world_engine/cockpit/perspective_flow.py` (whole, 113 lines).
Finding: `ask_flow` pings (`ollama_client.ping()`), drafts the plan with
`descriptions=PERSPECTIVE_DESCRIPTIONS` (:73-74), runs it, audits, renders,
and journals through `_usage.record(..., kind="perspective", ...)`; on
`OllamaError` it journals `unavailable` and raises 503 with
`lore_render.PLANNER_UNAVAILABLE_MESSAGE`; on `LlmParseError` it journals
`parse_error` and raises 502.
Consequence: the planner sees `public_skills` as soon as D adds it to
`PERSPECTIVE_DESCRIPTIONS` -- nothing to change here. The designer route
(G) follows this ping / journal / status shape.

### R-19 -- the Lore usage journal
Opened: `src/world_engine/models/pipeline.py:450-505`;
`src/world_engine/writes/lore_usage.py:1-90`; `src/world_engine/lore_usage.py`
(whole, 71 lines); `tooling/verify/checks/lore_usage.py:1-80, 225-250`;
`tooling/verify/checks/player_entry_schema.py:1-40, 70-92, 150-215`.
Finding: `LORE_USAGE_STEPS` (:467-471) maps `write`, `consult`,
`perspective` to their steps; `LoreUsageEvent` carries the CHECK
`ck_lore_usage_event_step` listing the same pairs as literal SQL (:479-485),
no `world_id`, kept out of the world cascade by construction.
`PAYLOAD_KEYS` (`writes/lore_usage.py:29-39`) gives each step's exact
payload keys; `write_usage_event` refuses a payload whose keys differ, an
`error` set when the outcome is `ok`, a step outside its kind.
`lore_usage.attempt_id(raw)` canonicalises or mints a UUID; `stage(db, *,
attempt, world_id, kind, step, outcome, payload, exchanges=None,
lore_entry_ref=None)` adds a row to the caller's transaction; `record`
stages and commits. `lore_usage.py` U1 reads the CHECK pairs from a fresh
`create_all` and compares them with `LORE_USAGE_STEPS`;
`player_entry_schema.py` PS2 reshapes the journal to its v2.13 DDL and runs
the v2.31 script, which rebuilds the table from the current model, then
asserts `'perspective_ask'` in the stored SQL.
Consequence: B adds the kind `creation` to `LORE_USAGE_STEPS` and the CHECK
text, two `PAYLOAD_KEYS` entries, and rebuilds the table in v2.32 when the
stored SQL lacks `'creation'` (C-02). U1 and PS1/PS2 stay true.

### R-20 -- the world premise
Opened: `src/world_engine/world_premise.py` (whole, 131 lines);
`tooling/verify/checks/world_premise.py:1-90, 180-190, 610-620`.
Finding: `world_premise(db, regime, *, entity_type=None)` reads the
`is_active` world (:80) -- a player route keyed by world cannot use it as
it is. The `player` regime gives name, description, tone, laws, never a
skill system nor a state. `fill(text, db, usage, *, entity_type=None)`
replaces `{world_premise}` and runs no query when the text holds none. The
check's WP1 compares each regime's usages with literal tuples `CREATOR`
(14), `PLAYER` (15, :79-84) and `NONE` (18); its PASS line names « 47
usages » and « 14/15/18 » (:616).
Consequence: F adds a keyword `world_id=None` to `world_premise` and
`fill` (None keeps the active world: every current caller is unchanged)
and adds the designer's two usages to WP1's `PLAYER` tuple, its docstring
count (17) and its PASS line (49 usages, 14/17/18) (C-09).

### R-21 -- one templated JSON call
Opened: `src/world_engine/prompt_call.py` (whole, 47 lines);
`src/world_engine/prompt_load.py:50-72`; `src/world_engine/llm_parse.py:44-60`;
`src/world_engine/ollama_client.py:39, 73`.
Finding: `call_json(db, usage, values, exchanges, chat)` loads the usage's
head (`prompt_load.load`: active template, current version, effective
model), fills both texts with `fill(..., db, usage)` (exactly two `fill(`
calls, WP3 of `world_premise.py` asserts it), replaces `{key}` in the user
message only, records the exchange, calls `chat(..., format="json")` and
returns `llm_parse.extract_object(raw)` (`LlmParseError` on no object).
`OllamaError` (a `RuntimeError`) and `ping()` live in `ollama_client`.
Consequence: F adds `world_id: Optional[str] = None` to `call_json`, passed
to both `fill` calls (still two). Every variable of the designer's prompts
lives in the user template.

### R-22 -- the prompt registry and its check
Opened: `src/world_engine/prompt_registry.py:1-75, 340-380`;
`tooling/verify/checks/prompt_registry.py:1-30, 78-80, 120-150`.
Finding: `PromptSpec(surface, world_scoped, dry_run_capable, call_sites,
default_model, premise, premise_reason="")`; the quest designer's entries
are `surface="authoring"`, `world_scoped=False`, `dry_run_capable=True`,
`call_sites=("src/world_engine/quest_designer.py:_subject",)`,
`default_model=_author_model`, `premise="creator"`. The check requires the
registry keys to equal the usages seeded in `scripts/seed_pilot.py` and
every call site `path:function` to name a file holding `^def function(`.
Consequence: F adds `creation_subject` and `creation_design` with
`premise="player"`, call sites in `creation_designer.py` on module-level
functions (C-11), and seeds both.

### R-23 -- seeding and delivering designer prompts
Opened: `scripts/seed_pilot.py:134-160, 2350-2420, 2490-2520, 3620-3630`;
`scripts/apply_ticket_0121_designer_prompts.py` (whole, 59 lines);
`tooling/verify/checks/prompt_lean.py:1-25`.
Finding: `premised_texts(usage, system_prompt, user_template, variables)`
prefixes `{world_premise}` for a `creator` or `player` usage and appends
the variable; `upsert_prompt_template(session, id, *, system_prompt,
user_template, **head_fields)` writes v1 on a virgin head only. Heads are
tuples of dicts (`QUEST_DESIGNER_PROMPT_HEADS`, keys `id, name, usage,
world_id=None, system_prompt, user_template, variables, destination
"local"`), seeded in a loop at :3624-3627. The 0121 delivery script embeds
no text: it refuses unless `WORLD_ENGINE_ENV` is `prod` or `test`, upserts
each head of the tuple and prints `created` / `updated` / `existing`.
`prompt_lean.py` rule 2: no `*_SYSTEM_PROMPT` / `*_USER_TEMPLATE` constant
holds a pilot identifier.
Consequence: F adds `CREATION_SUBJECT_*`, `CREATION_DESIGN_*` constants
(no proper name of any world in them), `CHARACTER_DESIGNER_PROMPT_HEADS`,
its seed loop line, and `scripts/apply_ticket_0126_designer_prompts.py`
on the 0121 model.

### R-24 -- the quest designer's call pattern
Opened: `src/world_engine/quest_designer.py:1-60, 84-105`.
Finding: the module imports `chat` from `.ollama_client` and calls
`prompt_call.call_json(db, USAGE, values, exchanges, chat)`; a check
swaps `<module>.chat`. `OllamaError` and `LlmParseError` propagate; the
caller rolls back.
Consequence: `creation_designer.py` imports `chat` the same way, so a check
swaps `creation_designer.chat`.

### R-25 -- zones and visitable places
Opened: `src/world_engine/zone_rules.py:32-84`.
Finding: `is_zone(db, location_id)` is true when the location has an active
child; `zone_ids(db, world_id)` returns every zone of the world;
`require_visitable` refuses a zone.
Consequence: a starting place is a location in `view.entity_ids` that is
not in `zone_ids(db, world_id)` (D1, C-10).

### R-26 -- knowledge levels
Opened: `src/world_engine/writes/knowledge.py:63-73`.
Finding: `KNOWLEDGE_LEVELS = {"unaware", "rumor", "suspicious", "partial",
"knows", "fully_understands"}`; `KNOWLEDGE_LEVEL_LADDER` orders them.
Consequence: a draft knowledge line takes one of `rumor`, `suspicious`,
`partial`, `knows` (a player-claimed knowledge is never `unaware` nor
`fully_understands`); 0129 writes it through `write_knowledge`.

### R-27 -- the world cascade
Opened: `src/world_engine/writes/worlds.py:1-25, 39-91`;
`tooling/verify/checks/world_cascade.py:1-40, 67-215, 310-345`.
Finding: `_DIRECT_WORLD_SCOPED_DELETES` (:65-85) lists tables deleted by
`world_id`, order free under the FK deferral, ending with
`"quest_request",`. W1 requires the world-reaching tables of the metadata
(a `world_id` column, or a foreign key to a world-reaching table) to equal
the tables the module names; W3 requires `_FIXTURE` (:67) to name exactly
the cascaded tables; W4 builds two worlds through `_build_world(engine,
world_id)` (:336-345), which inserts the `world` row then every
`_FIXTURE` row (`{w}` formatted) by raw INSERT, and requires every fixture
table to grow. No `user` row is inserted. `user` is not world-reaching.
Consequence: B adds `creation_rules` and the five `pc_draft*` tables to
`_DIRECT_WORLD_SCOPED_DELETES` (each carries `world_id`), adds their rows
to `_FIXTURE`, and makes `_build_world` insert a `user` row `u-{w}` before
the fixture so `pc_draft.user_id` resolves.

### R-28 -- the JSON boundary
Opened: `tooling/verify/checks/json_ui_boundary.py:1-60, 215-230`.
Finding: every JSON column of the metadata must be a named entry of
`JSON_COLUMN_ALLOWLIST`; an unlisted one fails volet c.
Consequence: no table of this lot has a JSON column (B1, INV-20); the
allowlist is untouched.

### R-29 -- the models package layout
Opened: `src/world_engine/models/__init__.py:1-58, 109-205`.
Finding: the docstring lists each stratum module with its tables; the
import order is canon, canon_faction, canon_knowledge, canon_attribute,
canon_event, config, ephemeral, pipeline, observation, quests; each module
imports `_created_ts, _uuid` from `.canon`.
Consequence: A adds `canon_skill.py` after `canon` in the docstring and the
imports; B adds `pc_drafts.py` (non-canon, pending player drafts) last.

### R-30 -- a relational pending request, the precedent
Opened: `src/world_engine/models/pipeline.py:578-640`.
Finding: `QuestRequest` is non-canon, world-scoped, deleted with its world,
its states a CHECK list, its skill named by a text `skill_key` (a base
domain or a skill definition id, TICKET-0116), written only by its own
`writes/` module, which never commits.
Consequence: `pc_draft_skill.skill_key` follows that shape (no FK: a
deleted definition leaves an `unknown_skill` the check reports) and the
draft writer never commits (C-12).

### R-31 -- the player shell
Opened: `frontend/src/joueur/` (`JoueurApp.svelte` 32, `ProfilePicker.svelte`
31, `WorldList.svelte` 45, `WorldPage.svelte` 83, `joueur.svelte.js` 168,
`main.js` 4 lines); `frontend/jouer.html`;
`tooling/verify/checks/player_shell.py:1-40, 90-160`.
Finding: `WorldPage.svelte:27-29` holds `<button disabled>Créer mon
personnage (bientôt)</button>` above the savoir section. `joueur.svelte.js`
keeps `joueurState` and the fetch helpers `call(url, options)` (throws an
`Error` with the server's string `detail`) and `postJson(url, payload)`
(:23-46); the profile is `joueurState.profile`, the world
`joueurState.world`. PSH2: every `fetch(` / `call(` URL literal under
`frontend/src/joueur/` starts with `/api/joueur/`; PSH3: no import leaves
the folder (`svelte` excepted); PSH4: `jouer.html` wired, `/jouer` out of
`_SHELL_ROUTES`. `jouer.html` loads `/static/shared.css`.
Consequence: H adds its components and state file in that folder, calls
only `/api/joueur/creation/...` through `call` / `postJson` (a PUT helper
of the same shape is added beside them), and replaces the disabled button.

### R-32 -- the Compétences tab
Opened: `frontend/src/creation/CompetencesList.svelte` (130 lines),
`CompetencesSheet.svelte` (253), `competences.svelte.js` (361),
`Sheet.svelte:108, 420-425, 505-525`;
`tooling/verify/checks/rank_trials.py:1040-1070`,
`skill_progression.py:738-752`, `npc_skills.py:600-610`.
Finding: the list's first section is « Rangs » with one record, `Rangs du
monde`, opened by `onSelect(ranksRecord())` (:50-56); the sheet branches on
`rec.kind` (`ranks`, `assistant`, `skill`, `system`) and renders the
`thresholds` snippet once per skill and once per system;
`competences.svelte.js` builds records (`skillRecord`, `systemRecord`,
`ranksRecord`, `draftRecord`, `blankRecord`), titles them
(`competenceSheetTitle`) and saves them (`saveCompetenceRecord`, :332-338)
through `saveSkill`, `saveSystem`, `saveRanks`; `Sheet.svelte` imports
`blankRecord, competenceSheetTitle, saveCompetenceRecord` (:108). Checks
pin: TF1 -- `...trialsBody(record)` and `...pointsBody(record)` each exactly
twice in `competences.svelte.js`; TF2 -- `{@render thresholds()}` exactly
twice in the sheet; C3 -- `Rangs du monde` and `ranksRecord()` in the list,
`rec.kind === 'ranks'` in the sheet, `'/api/skill-ranks', {` in the state;
C2 of `npc_skills.py` -- `bind:checked={creationState.sheetDetail.requires_master}`
in the sheet and `requires_master: !!record.requires_master` in the state.
Consequence: E adds a `creation` record kind, its own component and state
file, and new override fields sent through a new spread
(`...creationOverridesBody(record)`), never through `pointsBody` or
`trialsBody` and never through a third `{@render thresholds()}`; every
needle above survives.

### R-33 -- the Création right column and the germ precedent
Opened: `frontend/src/creation/Creation.svelte:175-210` (250 lines);
`tabs.js:100-115, 195-232, 505-521, 740-805` (890 lines);
`EntityList.svelte:295-360` (413); `registry.js:585-604` (604);
`mount.js:45-55` (171); `state.svelte.js:75-100` (114);
`sheetState.svelte.js:105-115`; `GermPanel.svelte:1-20`;
`frontend/public/creation.css:300-306`;
`tooling/verify/checks/creation_layout.py:1-110`;
`.claude/rules/frontend.md` (INV-49, INV-50, INV-54).
Finding: the right column holds `<div id="creation-germ-panel"
style:display={creationState.selectedGermId ? '' : 'none'}></div>`, the
sheet panel hidden by `style:display={(creationState.selectedGermId ||
creationState.sheetPane === 'competences') ? 'none' : ''}`, and
`#creation-pj-skill` shown by `(containerVisible('creation-pj-skill') &&
creationState.sheetPane === 'competences' && !creationState.selectedGermId)`.
The `pj` entry (`tabs.js:219-231`) declares islands `entityList`,
`entitySheet`, `pjSkillFiche` and no `showPendingCreations`.
`_creationActivateTab` (:507-521) resets `selectedGermId`, `sheetPane`,
`germLinkTarget`, then loads pending creations when the entry declares
`showPendingCreations`. `api(path, options)` (:105) throws the server's
detail. `selectGerm(id)` (:787-789) sets `selectedGermId`. `EntityList`
renders `germGroup()` (« En attente (n) », one `author-list-item` per germ)
at the top of `flat` mode. `registry.js` declares `germPanel` with
`containerId`, `component: 'GermPanel.svelte'`, `origin: 'new'`,
`createdBy`; `mount.js` imports `GermPanel` and keys `germPanel:
GermPanel` in `COMPONENTS`. `state.svelte.js` holds `selectedGermId: null`.
`selectEntity` sets `selectedGermId = null` first. `creation.css:304`:
`#creation-germ-panel { flex: 1; min-height: 0; overflow-y: auto; padding:
16px 20px; }`. CL1 pins the three display strings above verbatim; CL2 pins
the germ island on `npc`, `lieux`, `factions` and its absence on `pj`, and
the two resets; INV-49: no tab-specific branch outside the registry;
INV-50: a surface mounts as a `CREATION_ISLANDS` entry through `mount.js`,
`Creation.svelte` imports no component.
Consequence: I mirrors the germ panel for submitted drafts: a registry
entry `pcDraftPanel`, a container `creation-pc-draft-panel`, a flag
`showSubmittedDrafts: true` on the `pj` entry only, a `selectedPcDraftId`
reset beside every `selectedGermId` reset, the two display conditions
extended, and CL1 re-pinned to the new strings (C-15).

### R-34 -- route registration
Opened: `src/world_engine/cockpit/app.py:55-82, 130-160` (343 lines).
Finding: each route module is imported as `from .routes import <m> as
_routes_<m>` and included by `app.include_router(_routes_<m>.router)`;
`quest_designer.py` and `condition_interpreter.py` (checks) assert their
own include line.
Consequence: G includes `player_creation`, I includes `pc_drafts`, one
import and one include line each.

### R-35 -- the check fixture and the stubbed model
Opened: `tooling/verify/checks/world_sheet.py:48-62`;
`tooling/verify/checks/lore_usage.py:427-466, 655-665`;
`tooling/verify/checks/player_routes.py:88-130, 180-185`;
`.claude/rules/verify-checks.md`.
Finding: `_fresh_engine()` points `WORLD_ENGINE_DATABASE_URL` at a temp
file, sets `WORLD_ENGINE_ENV=test`, drops cached `world_engine` modules,
imports `world_engine.models` and runs `SQLModel.metadata.create_all`.
`_Stub(replies)` pops one reply per call (an `Exception` is raised, a dict
is JSON-dumped); `_swap(module, stub)` replaces `module.chat` and returns
the original; route tests use `TestClient(app,
base_url="http://127.0.0.1")`; `_seed_prompts` upserts heads through
`seed_pilot.upsert_prompt_template` after `sys.path.insert(0, scripts)`.
Rules: fail-closed, never Nia's DB, rows through sanctioned writers, every
rule proven by a named mutation.
Consequence: every DB check of this lot copies `_fresh_engine`'s body, and
the designer and route checks stub `chat` with `_Stub`/`_swap` and
`ollama_client.ping` by attribute.

### R-36 -- governance texts and budgets
Opened: `CLAUDE.md:234-254` (20 589 characters);
`.claude/rules/player-surface.md` (889), `skills.md` (2 896);
`tooling/verify/checks/claude_md_contract.py:1-76`;
`tooling/standards/ARCHITECTURE_DECISIONS.md` (last 15 lines).
Finding: budgets 22 000 characters for the root, 4 000 per rule file, 100
characters per line; every invariant bullet starts `- **INV-NN**` and ends
with `-- enforced by` and checks, or `[no check]`; ids run INV-01 to the
highest with none dropped; the highest is INV-66
(`player-surface.md:17`); a rule file opens with `paths:` globs that each
match a file; the root's « Path-scoped rules » list equals the files on
disk. ARCHITECTURE_DECISIONS ends with `---` then `*Co-built with Claude,
June 2026.*`; an entry is inserted above that footer.
Consequence: C creates `.claude/rules/character-creation.md` (INV-67) and
its list line in CLAUDE.md; D and F amend INV-66 in `player-surface.md`;
I inserts the ticket's entry above the footer.

### R-37 -- the corpus gate
Opened: `tooling/verify/checks/corpus_gate.py:1-60, 150-165`.
Finding: every `*.py` of `tooling/verify/checks/` is discovered and run as
a subprocess, 15 seconds each (`TIMEOUT_SECONDS`) unless listed in
`SLOW_CHECK_TIMEOUTS`.
Consequence: every new check of this lot must finish in 15 seconds; the
schema check's migration subprocess runs once per sub-rule, not per table.

### R-38 -- frontend files the checks read
Opened: the enumeration (c)-5.
Finding: `CompetencesSheet.svelte`, `CompetencesList.svelte` and
`competences.svelte.js` are read by `npc_skills.py`, `rank_trials.py`,
`skill_progression.py`, `page_contract.py` (a comment) and
`graph_primitive.py` (a comment); `Creation.svelte`, `tabs.js`,
`EntityList.svelte`, `registry.js`, `mount.js`, `state.svelte.js` are read
by `creation_layout.py`, `creation_island.py`, `creation_container_sizing.py`,
`page_contract.py`, `creation_tab_switch.py`, `npc_skills.py` and others
listed in (c)-5. No check reads a file under `frontend/src/joueur/` but
`player_shell.py`.
Consequence: no file is moved or renamed in this lot; E and I keep every
pinned needle (R-32, R-33) and re-pin CL1 deliberately (I).

### R-39 -- the existing PC creation route, untouched here
Opened: `src/world_engine/cockpit/routes/creator.py:786-940`.
Finding: `POST /api/characters/player` creates a PC in the active world,
bound to the lone `creator` user, base domains and every open definition at
the default rank, knowledge through `write_knowledge`.
Consequence: out of this lot (0129 writes a draft to canon); named so no
brief reaches into `creator.py` (968 lines, R-40).

### R-40 -- module budgets of the files this lot edits
Opened: `ast` count and `wc -l` at `fb8557a`;
`tooling/verify/checks/module_budget.py:1-60`.
Finding: caps 1000 physical lines and 40 top-level functions plus methods
for `src/**/*.py`, 1000 lines for `frontend/src/**/*.svelte|js`.
`models/canon.py` 964; `crud/skills.py` 667 lines / 23; `models/pipeline.py`
813; `perspective_selectors.py` 281; `perspective_audit.py` 128;
`lore_render.py` 340; `world_premise.py` 131; `prompt_call.py` 47;
`prompt_registry.py` 488; `writes/worlds.py` 168; `cockpit/app.py` 343 /
12; `routes/player.py` 129; `tabs.js` 890; `EntityList.svelte` 413;
`registry.js` 604; `Creation.svelte` 250; `CompetencesSheet.svelte` 253;
`competences.svelte.js` 361; `joueur.svelte.js` 168; `WorldPage.svelte` 83.
Consequence: `canon.py` cannot take B's columns before A; every other edit
stays far under its cap; `tabs.js` takes at most 15 lines; new logic goes
to new modules.

### R-41 -- the pure-move proof
Opened: `src/world_engine/schema_reconcile.py:30`.
Finding: `static_table_names() -> set[str]` returns the table names of the
static model metadata.
Consequence: A's Done means compares its output before and after the move.

### R-42 -- the schema document's layout
Opened: `world-engine-schema.md:1-20, 1209-1240, 1319-1390, 2048-2120,
2201-2230, 3451-3460`.
Finding: each table is a `### \`<table>\`` section: one or more prose
paragraphs (what it is, ticket and version), a ```sql``` block with the
`CREATE TABLE` (one column per line, a `--` comment for a column added
later, e.g. `trial_to_rank_1  BOOLEAN,  -- reaching rank n asks a trial
(v2.29); NULL = inherited`), its `CREATE ... INDEX` lines inside the same
block, then `-- NOTE:` lines and `-----`. The journal section names each
kind in prose (« Perspective questions (v2.31, TICKET-0125) are journaled
as kind `perspective` ... »). `## INDEXES` (:3451) repeats every index
grouped by purpose. `quest_request` (:1319) is the last pipeline table
section before `skill_resolution`; `skill_rank` (:2201) is the last of the
skill sections.
Consequence: B documents `creation_rules` after `skill_rank`, the five
draft tables after `quest_request`, the six override columns inside the two
existing `CREATE TABLE` blocks with a `-- ... (v2.32)` comment, the journal
kind in the journal section's prose and CHECK, and every new index in
`## INDEXES`.

### R-43 -- name bans across the source tree, and the arrow floor (AMENDMENT-0126-01)
Opened: `tooling/verify/checks/lore_as_facts.py:1-80`;
`tooling/verify/checks/knowledge_identity.py:842-863`;
`tooling/verify/checks/pipeline_state.py:54, 113-120`; every check under
`tooling/verify/checks/` holding `.attr in` / `.attr ==` with an `rglob` over
`src/` (enumerated in the amendment).
Finding: `lore_as_facts.py` R1 fails on any `ast.Attribute` whose `attr` is
one of `appearance, backstory, secrets, philosophy, internal_structure,
internal_tensions, aversion, goals` anywhere under `src/world_engine/`
outside `models/` -- by name, whatever the object. `knowledge_identity.py`
K3 counts, per file under `src/world_engine/`, every attribute, constant,
keyword and argument named `subject` and fails when a file's count differs
from its pinned census (a new file with one reference fails). The other
source-wide name bans -- `.tier` (`skill_progression.py` A4),
`.physical_tier` (`npc_skills.py`), `owner_id`/`location_id`/`equipped` on
item reads (`quest_rewards.py`), `event_contexts.py`'s `DROPPED` -- name
nothing of this lot. `pipeline_state.py` fails, for a ticket whose status
is `brief`, `exec`, `verify`, `live-gate` or `done`, on any
Machine-checkable arrow naming a check that does not exist.
Consequence: the draft's text is `pc_draft.story` (never `backstory`); the
designer's first call is `backstory_terms` (never `subject`). While
TICKET-0126 is in `exec`, `corpus_gate.py` is red on `pipeline_state.py`
for every check a later brief creates (`player_creation.py` until G's
commit 3, `submitted_drafts.py` until I), and only for those.

## Contract sheet

### C-01 -- the skill stratum module
Produced by: A   Consumed by: B, C
Module: `src/world_engine/models/canon_skill.py`. Holds, verbatim and in
this order, `canon.py` lines 580-719 at `fb8557a`: the comment and
`BASE_SKILL_DOMAINS`, the comment and `RANK_POINTS_CHECK`, `SkillSystem`,
`SkillDefinition`, `Skill`, with their section comments. Its own docstring
(the `canon_faction.py` shape: « extracted from ``canon.py`` (TICKET-0126,
BRIEF-0126-A) to keep each stratum module under the `module_budget.py`
line cap »). Imports exactly what those lines use: `datetime`, `Optional`,
`Column, CheckConstraint, ForeignKey, Index, JSON, text` from sqlalchemy,
`Field, SQLModel` from sqlmodel, `_created_ts, _uuid` from `.canon`.
`canon.py` no longer holds lines 580-719; its imports are unchanged.
`models/__init__.py` imports `BASE_SKILL_DOMAINS, Skill, SkillDefinition,
SkillSystem` from `.canon_skill`; `__all__` unchanged; the docstring lists
`canon_skill.py` after `canon.py`. Table set unchanged
(`static_table_names()` identical).

### C-02 -- schema v2.32
(Amended by AMENDMENT-0126-01: `pc_draft.story`; `backstory_terms`.)
Produced by: B   Consumed by: C, D, F, G, I
**`models/canon_skill.py` gains:**
```python
CREATION_COST_COLUMNS: tuple[str, ...] = tuple(f"cost_to_rank_{n}" for n in range(1, 6))
CREATION_CAP_RANKS: tuple[int, ...] = (0, 2, 3, 4, 5)
CREATION_CAP_COLUMNS: tuple[str, ...] = tuple(f"cap_at_rank_{r}" for r in CREATION_CAP_RANKS)
CREATION_RULES_CHECK = " AND ".join(
    ["pool >= 0", "max_rank BETWEEN 1 AND 5", "max_master_skills >= 0"]
    + [f"{c} >= 0" for c in CREATION_COST_COLUMNS]
    + [f"({c} IS NULL OR {c} >= 0)" for c in CREATION_CAP_COLUMNS]
)

class CreationRules(SQLModel, table=True):
    __tablename__ = "creation_rules"
    __table_args__ = (
        Index("idx_creation_rules_world", "world_id", unique=True),
        CheckConstraint(CREATION_RULES_CHECK, name="ck_creation_rules_values"),
    )
    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    pool: int = Field(default=6, sa_column_kwargs={"server_default": text("6")})
    cost_to_rank_1: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    cost_to_rank_2: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    cost_to_rank_3: int = Field(default=2, sa_column_kwargs={"server_default": text("2")})
    cost_to_rank_4: int = Field(default=3, sa_column_kwargs={"server_default": text("3")})
    cost_to_rank_5: int = Field(default=4, sa_column_kwargs={"server_default": text("4")})
    cap_at_rank_0: Optional[int] = Field(default=2, sa_column_kwargs={"server_default": text("2")})
    cap_at_rank_2: Optional[int] = None
    cap_at_rank_3: Optional[int] = None
    cap_at_rank_4: Optional[int] = None
    cap_at_rank_5: Optional[int] = None
    max_rank: int = Field(default=5, sa_column_kwargs={"server_default": text("5")})
    max_master_skills: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    skills_visible: bool = Field(default=True, sa_column_kwargs={"server_default": text("1")})
    updated_at: datetime = _created_ts()
```
A cap of NULL is « no cap »; a missing row is every default above.
`SkillSystem` gains, after `trial_to_rank_5`: `visible_at_creation:
Optional[bool] = None`, `max_rank_at_creation: Optional[int] = None`,
`cap_raised_at_creation: Optional[int] = None`, `cap_held_at_creation:
Optional[int] = None`. `SkillDefinition` gains, after `trial_to_rank_5`:
`visible_at_creation: Optional[bool] = None`, `max_rank_at_creation:
Optional[int] = None`. NULL inherits. No CHECK on them (R-04).

**`models/pc_drafts.py`** (non-canon; a player's character draft):
```python
PC_DRAFT_STATUSES: tuple[str, ...] = ("draft", "submitted", "returned", "approved")
PC_DRAFT_ORIGINS: tuple[str, ...] = ("player", "designer")
PC_SKETCH_KINDS: tuple[str, ...] = ("family", "master", "faction", "other")
PC_KNOWLEDGE_LEVELS: tuple[str, ...] = ("rumor", "suspicious", "partial", "knows")
PC_SKETCH_MAX = 8
```
- `PcDraft` (`pc_draft`): `id`; `world_id` FK world NOT NULL; `user_id` FK
  `user.id` NOT NULL; `status: str` default `'draft'` (server default);
  `name: str` default `''`; `story: str` default `''` (AMENDMENT-0126-01:
  not `backstory`, a name `lore_as_facts.py` R1 forbids as an attribute);
  `start_location_id: Optional[str]` FK entity; `start_location_set_by:
  Optional[str]`; `creator_note: Optional[str]`; `submitted_at:
  Optional[datetime]`; `created_at`, `updated_at` (`_created_ts()`).
  CHECKs `ck_pc_draft_status` (`status IN ('draft','submitted','returned',
  'approved')`), `ck_pc_draft_set_by` (`start_location_set_by IS NULL OR
  start_location_set_by IN ('player','designer')`). Indexes
  `idx_pc_draft_world` (`world_id`), `idx_pc_draft_open` unique on
  `(world_id, user_id)` where `status <> 'approved'`.
- `PcDraftSkill` (`pc_draft_skill`): `id`; `draft_id` FK `pc_draft.id` NOT
  NULL; `world_id` FK world NOT NULL; `skill_key: str`; `player_rank:
  Optional[int]`; `designer_rank: Optional[int]`; `justification:
  Optional[str]`; `designer_reason: Optional[str]`. CHECKs
  `ck_pc_draft_skill_ranks` (`(player_rank IS NULL OR player_rank BETWEEN 0
  AND 5) AND (designer_rank IS NULL OR designer_rank BETWEEN 0 AND 5)`),
  `ck_pc_draft_skill_some` (`player_rank IS NOT NULL OR designer_rank IS NOT
  NULL`). Unique index `idx_pc_draft_skill_key` (`draft_id, skill_key`).
- `PcDraftSketch` (`pc_draft_sketch`): `id`; `draft_id`; `world_id`;
  `position: int`; `name: str`; `role: str` default `''`; `sentence: str`
  default `''`; `group_label: str` default `''`; `kind: str`; `skill_key:
  Optional[str]`; `existing_entity_id: Optional[str]` FK entity; `origin:
  str`. CHECKs `ck_pc_draft_sketch_kind` (`kind IN ('family','master',
  'faction','other')`), `ck_pc_draft_sketch_master` (`(kind = 'master') =
  (skill_key IS NOT NULL)`), `ck_pc_draft_sketch_origin` (`origin IN
  ('player','designer')`). Index `idx_pc_draft_sketch_draft` (`draft_id`).
- `PcDraftMembership` (`pc_draft_membership`): `id`; `draft_id`;
  `world_id`; `faction_id` FK entity NOT NULL; `role: Optional[str]`;
  `origin: str`. CHECK `ck_pc_draft_membership_origin`; unique index
  `idx_pc_draft_membership_faction` (`draft_id, faction_id`).
- `PcDraftKnowledge` (`pc_draft_knowledge`): `id`; `draft_id`; `world_id`;
  `position: int`; `level: str`; `content: str`; `origin: str`. CHECKs
  `ck_pc_draft_knowledge_level` (`level IN ('rumor','suspicious','partial',
  'knows')`), `ck_pc_draft_knowledge_origin`. Index
  `idx_pc_draft_knowledge_draft` (`draft_id`).
Every string default carries `server_default text("''")`; `status` carries
`text("'draft'")`. No JSON column, no `change_history`.

**Journal.** `LORE_USAGE_STEPS["creation"] = ("creation_subject",
"creation_design")`, appended after `perspective`; the CHECK
`ck_lore_usage_event_step` gains `OR (kind = 'creation' AND step IN
('creation_subject','creation_design'))` at its end. `PAYLOAD_KEYS` gains:
- `"creation_subject": frozenset({"draft_id", "asked_by", "story",
  "names", "keywords", "error"})`
- `"creation_design": frozenset({"draft_id", "asked_by", "lore",
  "proposal", "violations", "notes", "error"})`

**Migration** `scripts/migrate_v2_32_character_creation.py`: R-01's
skeleton, `_PREVIOUS_VERSION = "v2.31"`, `_THIS_VERSION = "v2.32"`.
`_plan()` returns (a) `CreationRules` and the five draft models to create
when their table is absent (created by `_create_from_model`, parents before
children: `creation_rules`, `pc_draft`, `pc_draft_skill`, `pc_draft_sketch`,
`pc_draft_membership`, `pc_draft_knowledge`); (b) `ALTER TABLE skill_system
ADD COLUMN visible_at_creation BOOLEAN`, `... max_rank_at_creation INTEGER`,
`... cap_raised_at_creation INTEGER`, `... cap_held_at_creation INTEGER`,
`ALTER TABLE skill_definition ADD COLUMN visible_at_creation BOOLEAN`,
`... max_rank_at_creation INTEGER`, each only when the column is absent;
(c) a rebuild of `lore_usage_event` (`models.LoreUsageEvent`, the v2.31
script's `_JOURNAL_COLUMNS`) when its stored SQL lacks `'creation'`. Writes
no data. Post-checks: the six tables exist; the six columns exist;
`'creation_design'` is in the stored journal SQL; the journal row count is
unchanged. Then `schema_meta` -> v2.32. Output lines as v2.31's.

**Cascade.** `_DIRECT_WORLD_SCOPED_DELETES` gains, after `"quest_request",`:
`"creation_rules", "pc_draft", "pc_draft_skill", "pc_draft_sketch",
"pc_draft_membership", "pc_draft_knowledge",`.

### C-03 -- the creation rules reader
Produced by: C   Consumed by: C (C-04, C-06), D, F, G
Module: `src/world_engine/creation_rules.py`. Reads only: no write, no
flush, no commit, no model call.
```python
DEFAULT_POOL = 6
DEFAULT_COSTS: tuple[int, ...] = (0, 1, 1, 2, 3, 4)   # index = rank reached; index 0 unused
DEFAULT_CAPS: dict[int, Optional[int]] = {0: 2, 2: None, 3: None, 4: None, 5: None}
DEFAULT_MAX_RANK = 5
DEFAULT_MAX_MASTER_SKILLS = 1
DEFAULT_SKILLS_VISIBLE = True

@dataclass(frozen=True)
class CreationRuleSet:
    pool: int
    costs: tuple[int, ...]               # len 6, costs[0] == 0
    caps: tuple[tuple[int, Optional[int]], ...]   # (rank, cap) for CREATION_CAP_RANKS, in order
    max_rank: int
    max_master_skills: int
    skills_visible: bool
    def cap(self, rank: int) -> Optional[int]: ...   # None for a rank not in CREATION_CAP_RANKS

@dataclass(frozen=True)
class StartSkill:
    skill_key: str                 # a base domain literal, or a skill definition id
    name: str                      # the domain literal, or the definition's name
    base_domain: str
    system_id: Optional[str]
    system_name: Optional[str]
    description: Optional[str]     # the definition's; None for a base domain
    requires_master: bool
    start_rank: int                # 0 for requires_master, else DEFAULT_RANK
    max_rank: int                  # skill_max_rank
    visible: bool                  # skill_visible

def world_creation_rules(db, world_id: str) -> CreationRuleSet
def skill_visible(rules: CreationRuleSet, *, system, definition) -> bool
def skill_max_rank(rules: CreationRuleSet, *, system, definition) -> int
def visible_skill_ids(db, world_id: str) -> frozenset[str]
def start_sheet(db, world_id: str, rules: Optional[CreationRuleSet] = None) -> tuple[StartSkill, ...]
```
- `world_creation_rules`: the world's `creation_rules` row, else every
  `DEFAULT_*`; `costs = (0, cost_to_rank_1, ..., cost_to_rank_5)`.
- `skill_visible`: `definition.visible_at_creation` when `definition` is not
  None and that value is not None; else `system.visible_at_creation` under
  the same test; else `rules.skills_visible`. A base domain (`definition`
  None) is always True.
- `skill_max_rank`: the same cascade over `max_rank_at_creation`, ending at
  `rules.max_rank`; a base domain reads `rules.max_rank`.
- `visible_skill_ids`: the ids of the world's definitions for which
  `skill_visible` is True.
- `start_sheet`: the four base domains first, in `BASE_SKILL_DOMAINS` order
  (`skill_key = name = base_domain = domain`, start `DEFAULT_RANK`, system
  None, `requires_master` False, visible True), then every definition of
  the world, sorted by (system name, with no system last; definition name;
  id): `start_rank = 0` when `requires_master`, else `DEFAULT_RANK`.

### C-04 -- the one creation check
(AMENDMENT-0126-01: `story_missing`, `draft.story`; INV-67 reads « no other
module computes a sheet's cost or verdict ».)
Produced by: C (`check_creation`, `verdict_dict`), G (`check_draft`)   Consumed by: F, G, I
Module: `src/world_engine/creation_check.py`. Reads only.
```python
VIOLATION_CODES: tuple[str, ...] = (
    "unknown_skill", "rank_out_of_range", "not_visible", "above_max_rank",
    "over_master_count", "over_rank_cap", "over_system_raised", "over_system_held", "over_pool",
)
DRAFT_VIOLATION_CODES: tuple[str, ...] = (
    "name_missing", "story_missing", "start_place_missing", "start_place_invalid",
    "too_many_sketches", "master_without_sketch", "sketch_existing_invalid",
    "membership_invalid", "pc_exists",
)

@dataclass(frozen=True)
class Violation:
    code: str
    skill_key: Optional[str]
    message: str

@dataclass(frozen=True)
class SheetLine:
    skill_key: str
    start_rank: int
    rank: int
    cost: int          # positive spent, negative given back, 0 unchanged

@dataclass(frozen=True)
class CreationVerdict:
    pool: int
    spent: int         # sum of every line's cost (refunds subtract)
    remaining: int     # pool - spent
    lines: tuple[SheetLine, ...]   # every start_sheet line, in its order
    violations: tuple[Violation, ...]

def check_creation(db, world_id: str, choices: Mapping[str, int], *,
                   enforce_visibility: bool) -> CreationVerdict
def check_draft(db, draft: PcDraft) -> tuple[Violation, ...]
def verdict_dict(verdict: CreationVerdict, violations: tuple[Violation, ...]) -> dict
```
**`check_creation`.** `rules = world_creation_rules`, `sheet =
start_sheet(db, world_id, rules)`, ladder labels from
`skill_ranks.world_ladder`. `choices` maps a skill key to a wanted rank;
an absent key keeps its start rank.
1. For each key of `choices` not in the sheet: `unknown_skill`. For each
   choice whose value is not an int in 0..5 (a bool is not an int):
   `rank_out_of_range`; that key keeps its start rank for every later step.
2. Each line's `rank` = its valid choice, else `start_rank`. Cost: `rank >
   start_rank` -> `sum(costs[r] for r in start_rank+1..rank)`; `rank <
   start_rank` -> `-costs[1]` (only 1 -> 0 exists); else 0.
3. Per line whose `rank != start_rank`, in sheet order: when
   `enforce_visibility` and not `visible` -> `not_visible` (and nothing else
   for that line); else when `rank > max_rank` -> `above_max_rank`.
4. `over_master_count` when the number of `requires_master` lines at rank >=
   1 exceeds `rules.max_master_skills`.
5. For each rank `r` of `CREATION_CAP_RANKS` in order with a cap not None:
   the lines at rank `r` -- for `r == 0`, only lines that are not
   `requires_master` -- exceed the cap -> `over_rank_cap`.
6. For each system of the sheet, by system name: when its
   `cap_raised_at_creation` is not None and the count of its lines at rank
   > `DEFAULT_RANK` exceeds it -> `over_system_raised`; when its
   `cap_held_at_creation` is not None and the count of its lines at rank >=
   1 exceeds it -> `over_system_held`.
7. `spent > rules.pool` -> `over_pool`.
Order of `violations`: steps 1, 3, 4, 5, 6, 7 as listed. Messages
(verbatim; `{label}` is the world's ladder label of the rank, `{name}` the
line's name, `{default_label}` the label of `DEFAULT_RANK`):
- `unknown_skill`: `Compétence inconnue : {key}.`
- `rank_out_of_range`: `« {name} » : le rang doit être entre 0 et 5.`
  (`{name}` the key when unknown)
- `not_visible`: `« {name} » ne peut pas être choisie à la création.`
- `above_max_rank`: `« {name} » : au plus {label} à la création.`
- `over_master_count`: `Au plus {n} compétence(s) qui exigent un maître.`
- `over_rank_cap`: `Au plus {n} compétence(s) au rang {label}.`
- `over_system_raised`: `Système « {system} » : au plus {n} compétence(s) au-dessus de {default_label}.`
- `over_system_held`: `Système « {system} » : au plus {n} compétence(s) détenue(s).`
- `over_pool`: `Réserve dépassée : {spent} point(s) pour {pool}.`
`skill_key` is set for the per-line codes (steps 1-3), None for the rest.

**`check_draft`.** `view = public_view(db, draft.world_id)`; in this order:
1. `name_missing` when `draft.name.strip()` is empty: `Le personnage n'a pas de nom.`
2. `story_missing` when `draft.story.strip()` is empty: `L'histoire du personnage est vide.`
3. `start_place_missing` when `start_location_id` is None: `Choisis un lieu de départ.`;
   else `start_place_invalid` when it is not in `view.entity_ids`, not an
   active `location` of the world, or in `zone_ids(db, world_id)`:
   `Ce lieu de départ ne peut pas être choisi.`
4. every violation of `check_creation(db, world_id, {row.skill_key:
   row.player_rank for each draft skill row with player_rank not None},
   enforce_visibility=True)`.
5. `too_many_sketches` when the draft has more than `PC_SKETCH_MAX`
   sketches: `Au plus 8 personnes d'ancrage.`
6. `master_without_sketch`, per `requires_master` line at rank >= 1 of that
   verdict with no sketch of kind `master` and that `skill_key`: `« {name} »
   exige un maître : ajoute la personne qui te l'a enseignée.`
   (`skill_key` set).
7. `sketch_existing_invalid`, per sketch whose `existing_entity_id` is not
   None and not a `character` in `view.entity_ids`: `« {sketch} » : la
   personne choisie n'est pas connue de tous.`
8. `membership_invalid`, per membership whose faction is not a `faction` in
   `view.entity_ids`: `Cette faction ne peut pas être choisie.`
9. `pc_exists` when the draft's user already holds a character of
   `character_type` `player` in the world (R-09): `Ce joueur a déjà un
   personnage dans ce monde.`
**`verdict_dict`** returns `{"pool", "spent", "remaining", "lines": [{"skill_key",
"start_rank", "rank", "cost"}], "violations": [{"code", "skill_key",
"message"}]}` with `violations` the tuple passed in.

### C-05 -- the creation rules writer
Produced by: C   Consumed by: C (C-06)
`src/world_engine/writes/creation_rules.py::write_creation_rules(db, *,
world_id: str, pool: int, costs: Sequence[int], caps: Mapping[int,
Optional[int]], max_rank: int, max_master_skills: int, skills_visible:
bool) -> CreationRules`. `costs` lists ranks 1..5 in order (exactly 5);
`caps` has exactly the keys of `CREATION_CAP_RANKS`. Fetch-or-create the
world's row, set every field, `updated_at` now, add, flush; never deletes,
never commits. `ValueError`, before any write, with these messages:
- pool not an int >= 0: `La réserve est un nombre entier, au moins 0.`
- costs not 5 ints >= 0: `Chaque coût est un nombre entier, au moins 0.`
- caps keys not exactly `CREATION_CAP_RANKS`, or a value neither None nor
  an int >= 0: `Chaque plafond est vide ou un nombre entier, au moins 0.`
- max_rank not an int in 1..5: `Le rang maximal va d'Initié à Maître.`
- max_master_skills not an int >= 0: `Le nombre de compétences à maître est un nombre entier, au moins 0.`
- skills_visible not a bool: `La visibilité est oui ou non.`
(a bool is never accepted as an int).

### C-06 -- the creator's rules routes and the override fields
Produced by: C   Consumed by: E
In `cockpit/crud/skills.py`, on the shared `/api` router:
- `GET /api/creation-rules` -> `rules_dict(world_creation_rules(db,
  world_id))` for the active world (`_world_id`).
- `PUT /api/creation-rules`, body `CreationRulesBody{pool: int, costs:
  list[CreationCostBody{rank: int, cost: int}], caps:
  list[CreationCapBody{rank: int, cap: Optional[int]}], max_rank: int,
  max_master_skills: int, skills_visible: bool}`: costs must list ranks
  1..5 exactly once and caps ranks 0, 2, 3, 4, 5 exactly once (422 `Chaque
  rang est donné une fois.` otherwise), then `write_creation_rules`, commit,
  return the GET shape; `ValueError` -> rollback, 422 with its message.
- `rules_dict(rules) -> dict` lives in `creation_rules.py` (C-03's module):
  `{"pool": int, "costs": [{"rank": 1..5, "cost": int}], "caps": [{"rank":
  r, "cap": int | None} for r in CREATION_CAP_RANKS], "max_rank": int,
  "max_master_skills": int, "skills_visible": bool}`.
- `SkillSystemWriteBody` gains `visible_at_creation: Optional[bool] = None`,
  `max_rank_at_creation: Optional[int] = Field(default=None, ge=1, le=5)`,
  `cap_raised_at_creation: Optional[int] = Field(default=None, ge=0)`,
  `cap_held_at_creation: Optional[int] = Field(default=None, ge=0)`;
  `SkillDefinitionWriteBody` gains the first two. `create_skill_system`,
  `update_skill_system`, `create_skill_definition`,
  `update_skill_definition` set them (a PUT replaces them like every other
  field); `_skill_system_dict` and `_skill_definition_dict` return them.

### C-07 -- the visible skills in the public view
Produced by: D   Consumed by: F, G
In `perspective_selectors.py`:
- `PublicView` gains `skill_ids: frozenset[str]` (last field);
  `public_view` sets it to `creation_rules.visible_skill_ids(db, world_id)`.
- `public_skills(world_id, view, db) -> list[dict]`: one row per skill
  definition of the world in `view.skill_ids`: `{"section": "skills",
  "skill_id", "name", "base_domain", "system", "description",
  "requires_master"}`, `system` the system's name or None, `description` the
  definition's or None; sorted by (system name, with no system last; name;
  id).
- `PERSPECTIVE_SELECTORS` = `("public_dossier", "public_factions",
  "public_facts_mentioning", "world_laws", "public_skills")`;
  `_PERSPECTIVE_LOOKUPS["public_skills"] = SelectorSpec(fn=public_skills,
  arity=1, row_cap=200, arg_kinds=("world_id",))`;
  `PERSPECTIVE_DESCRIPTIONS["public_skills"] = "public_skills($world) -- les
  compétences de ce monde connues de tous : celles qu'un personnage peut
  choisir à sa création."`
In `perspective_audit.py`: `WITHHELD_REASONS` gains `"skill_not_visible"`
(last); in `withheld`, before the `entity_id` branch, a `public_skills`
call adds `("skill_not_visible", name, name)` for every skill definition of
the world not in `view.skill_ids`.
In `lore_render.py`: `_SECTION_FORMATTERS["skills"] = _format_skills`,
`_format_skills(row)` = `f"{name} ({system or 'sans système'},
{base_domain})"`, then ` ; exige un maître` when `requires_master`, then `
-- {description}` when `description`.

### C-08 -- the premise of a chosen world
Produced by: F   Consumed by: F (C-11)
`world_premise(db, regime, *, entity_type=None, world_id: Optional[str] =
None)`: when `world_id` is not None the world is `db.get(World, world_id)`
(`""` when None), else the `is_active` world as today. `fill(text, db,
usage, *, entity_type=None, world_id=None)` passes it through.
`prompt_call.call_json(db, usage, values, exchanges, chat, *, world_id:
Optional[str] = None)` passes it to both `fill(` calls. Every existing
caller passes nothing and is unchanged.

### C-09 -- the designer's prompts
Produced by: F   Consumed by: F (C-11)
Usages `creation_subject`, `creation_design` in `PROMPT_REGISTRY`:
`surface="authoring"`, `world_scoped=False`, `dry_run_capable=True`,
`default_model=_author_model`, `premise="player"`, call sites
`src/world_engine/creation_designer.py:_subject_call` and
`src/world_engine/creation_designer.py:_design_call`. Seeded in
`scripts/seed_pilot.py` as `CHARACTER_DESIGNER_PROMPT_HEADS`: ids
`pt-creation-subject` (variables `character_name, backstory`) and
`pt-creation-design` (variables `character_name, backstory, skills,
player_choices, rules, lore, people, places, factions, errors`), names
`Concepteur de personnage — le sujet de l'histoire` and `Concepteur de
personnage — la proposition`, `world_id=None`, `destination="local"`;
texts in BRIEF-0126-F verbatim. Delivered by
`scripts/apply_ticket_0126_designer_prompts.py` (the 0121 script's shape
over this tuple).

### C-10 -- the creation lore (public view only)
Produced by: F   Consumed by: F (C-11), G
Module: `src/world_engine/creation_lore.py`. Reads only.
```python
MAX_NAMES = 10
MAX_KEYWORDS = 6
MAX_LORE_LINES = 80
MAX_LISTED = 60

@dataclass(frozen=True)
class CreationLore:
    lines: tuple[str, ...]
    people: tuple[dict, ...]     # {"entity_id", "name"}
    places: tuple[dict, ...]     # {"entity_id", "name"}
    factions: tuple[dict, ...]   # {"entity_id", "name", "description"}

def public_places(db, world_id: str, view: PublicView) -> list[dict]
def gather_creation_lore(db, world_id: str, *, names: list[str], keywords: list[str]) -> CreationLore
```
- `public_places`: active `location` entities of the world in
  `view.entity_ids` and not in `zone_ids(db, world_id)`, `{"entity_id",
  "name"}`, sorted by (name, id).
- `gather_creation_lore`: `view = public_view(db, world_id)`; names
  stripped, empty dropped, de-duplicated under `normalize_surface`, first
  `MAX_NAMES`; for each, every category of `CATEGORIES` is tried with
  `resolve_named(name, category, world_id, db, scope=public_scope(view))`
  and every `matched` id is kept; for each kept entity, its
  `public_dossier` rows become lines; the kept `character` entities are
  `people`. Keywords likewise, first `MAX_KEYWORDS`, each through
  `public_facts_mentioning(keyword, world_id, view, db)`. Lines:
  `identity` -> `— {name} ({type})`; `facets` -> `  • {label} : {content}`;
  `memberships` -> `  • membre de {faction_name}` plus ` ({role})` when
  set; `members` -> `  • membre : {member_name}` plus ` ({role})`;
  `public_mentions` -> `• {content}`; de-duplicated in order, first
  `MAX_LORE_LINES`. `places` = first `MAX_LISTED` of `public_places`;
  `factions` = first `MAX_LISTED` of `public_factions`, keys `entity_id,
  name, description`.
`public_scope` comes from `perspective_query`; the module imports nothing
from `lore_selectors` and holds no `entity_dossier`, `who_knows_about`,
`facts_mentioning(` outside `public_facts_mentioning(`, `world_factions`,
`CREATOR`, `NameScope("creator"`, `World.is_active` or `_world_id(`.

### C-11 -- the character designer
(Amended by AMENDMENT-0126-01: `pc_draft.story`; `backstory_terms`.)
Produced by: F   Consumed by: G
Module: `src/world_engine/creation_designer.py`; imports `chat` from
`.ollama_client` (R-24).
```python
SUBJECT_USAGE = "creation_subject"
DESIGN_USAGE = "creation_design"
MAX_KNOWLEDGE = 10
DESIGNER_UNAVAILABLE_MESSAGE = (
    "Le modèle local (Ollama) est indisponible : le concepteur n'a rien proposé et rien n'a changé. "
    "Réessaie quand Ollama est démarré."
)

@dataclass(frozen=True)
class DesignedSkill:
    skill_key: str
    rank: int
    reason: Optional[str]

@dataclass(frozen=True)
class DesignedSketch:
    name: str
    role: str
    sentence: str
    group_label: str
    kind: str                          # one of PC_SKETCH_KINDS
    skill_key: Optional[str]           # set exactly when kind == "master"
    existing_entity_id: Optional[str]

@dataclass(frozen=True)
class DesignedMembership:
    faction_id: str
    role: Optional[str]

@dataclass(frozen=True)
class DesignedKnowledge:
    level: str                         # one of PC_KNOWLEDGE_LEVELS
    content: str

@dataclass(frozen=True)
class CreationDesign:
    names: tuple[str, ...]
    keywords: tuple[str, ...]
    lore: CreationLore
    skills: tuple[DesignedSkill, ...]
    sketches: tuple[DesignedSketch, ...]
    start_location_id: Optional[str]
    memberships: tuple[DesignedMembership, ...]
    knowledge: tuple[DesignedKnowledge, ...]
    notes: tuple[str, ...]
    violations: tuple[Violation, ...]  # check_creation of `skills`, after the retry

def _subject_call(db, draft, exchanges: list) -> dict
def _design_call(db, draft, values: dict[str, str], exchanges: list) -> dict
def backstory_terms(db, draft: PcDraft, exchanges: list) -> tuple[tuple[str, ...], tuple[str, ...]]
def design(db, draft: PcDraft, names: tuple[str, ...], keywords: tuple[str, ...],
           exchanges: list) -> CreationDesign
def design_record(design: CreationDesign) -> dict
```
`backstory_terms` (AMENDMENT-0126-01: never `subject`, a name
`knowledge_identity.py` K3 counts): `_subject_call` (`call_json(db,
SUBJECT_USAGE, {"character_name": draft name, "backstory": draft.story},
exchanges, chat, world_id=draft.world_id)` -- the prompt variable keeps its
name) -> `(names,
keywords)`: each a list of non-empty strings in the reply, anything else ->
`()`. `design`: (1) `gather_creation_lore`; (2) `_design_call` with the
values of BRIEF-0126-F and `errors=""`; (3) resolve (case table (b)-3);
(4) `check_creation(db, world_id, {s.skill_key: s.rank},
enforce_visibility=True)`; when it has violations, one more `_design_call`
with `errors` = `\nErreurs de ta réponse précédente :` then one `\n-
{message}` per violation, re-resolve, re-check; the second result is kept
whatever it holds. `OllamaError`, `LlmParseError` propagate from both
functions. Neither writes anything.
`design_record(design)` -> `{"skills": [{"skill_key", "rank", "reason"}],
"sketches": [{"name", "role", "sentence", "group_label", "kind",
"skill_key", "existing_entity_id"}], "start_location_id", "memberships":
[{"faction_id", "role"}], "knowledge": [{"level", "content"}]}` (the
journal's `proposal`).

### C-12 -- the draft writer
(Amended by AMENDMENT-0126-01: `pc_draft.story`; `backstory_terms`.)
Produced by: G   Consumed by: G
Module: `src/world_engine/writes/pc_drafts.py`; never commits.
```python
class PcExists(ValueError): ...
class DraftLocked(ValueError): ...
PC_EXISTS_MESSAGE = "Ce joueur a déjà un personnage dans ce monde."
DRAFT_LOCKED_MESSAGE = "Ce personnage est soumis : il ne peut plus être modifié."

def open_draft(db, *, world_id: str, user_id: str) -> PcDraft
def save_player_draft(db, draft: PcDraft, *, name: str, story: str,
                      start_location_id: Optional[str], skills: list[dict],
                      sketches: list[dict], memberships: list[dict], knowledge: list[dict]) -> None
def apply_design(db, draft: PcDraft, design: CreationDesign) -> None
def submit_draft(db, draft: PcDraft, violations: tuple[Violation, ...]) -> None
```
- `open_draft`: `PcExists(PC_EXISTS_MESSAGE)` when the user holds a player
  character of the world; else the world's non-`approved` draft of that
  user, or a new `PcDraft(world_id, user_id)` added and flushed.
- `save_player_draft`: `DraftLocked` unless `status == "draft"`. Sets `name`
  and `story` (stripped); `start_location_id` and
  `start_location_set_by = "player"` when given, both None when None.
  `skills`: items `{skill_key, rank: int | None, justification}`; each
  named key's row gets `player_rank = rank`, `justification`; every other
  row gets both None; a row with both ranks None is deleted; a key listed
  twice -> `ValueError("Une compétence est donnée deux fois.")`.
  `sketches`: items `{id?, name, role, sentence, group_label, kind,
  skill_key, existing_entity_id}`; more than `PC_SKETCH_MAX` ->
  `ValueError("Au plus 8 personnes d'ancrage.")`; an empty name ->
  `ValueError("Chaque personne a un nom.")`; a kind outside
  `PC_SKETCH_KINDS` -> `ValueError("Sorte de personne inconnue.")`;
  `skill_key` kept only for `master` (None otherwise), and a `master`
  without one -> `ValueError("Un maître enseigne une compétence.")`. Rows
  whose id is not listed are deleted; a listed id updates its row and, when
  any field differs, sets `origin = "player"`; an item without id is a new
  row, origin `player`; `position` = list order.
  `memberships`: items `{faction_id, role}`, keyed by faction; same
  delete/update/insert rule, origin flipping to `player` on a change; a
  faction listed twice -> `ValueError("Une faction est donnée deux fois.")`.
  `knowledge`: items `{id?, level, content}`; level outside
  `PC_KNOWLEDGE_LEVELS` -> `ValueError("Niveau de connaissance inconnu.")`;
  empty content dropped; same id rule. `updated_at` now.
- `apply_design`: `DraftLocked` unless `draft`. Skills: every row's
  `designer_rank` and `designer_reason` become None, then each designed
  skill sets them on its row (created when absent); rows with both ranks
  None are deleted. Sketches, memberships, knowledge: rows of origin
  `designer` are deleted, then the design's rows are inserted, origin
  `designer`, positions after the player's; a designed membership whose
  faction a player row already holds is skipped. Start place: when
  `start_location_set_by != "player"`, set to the design's
  (`start_location_set_by = "designer"` when not None, else both None).
- `submit_draft`: `DraftLocked` unless `draft`; `ValueError("Le personnage
  ne peut pas être soumis.")` when `violations` is not empty; else
  `status = "submitted"`, `submitted_at` and `updated_at` now.

### C-13 -- the draft's read shape
(Amended by AMENDMENT-0126-01: `pc_draft.story`; `backstory_terms`.)
Produced by: G   Consumed by: G, I
Module: `src/world_engine/pc_draft_reads.py`. Reads only.
`draft_view(db, draft: PcDraft, *, view: Optional[PublicView]) -> dict`:
`{"id", "world_id", "status", "name", "story", "start_location":
{"entity_id", "name"} | None, "start_location_set_by", "creator_note",
"submitted_at" (ISO or None), "skills": [{"skill_key", "player_rank",
"designer_rank", "justification", "designer_reason"}] (by skill_key),
"sketches": [{"id", "position", "name", "role", "sentence", "group_label",
"kind", "skill_key", "existing_entity": {"entity_id", "name"} | None,
"origin"}] (by position), "memberships": [{"id", "faction_id",
"faction_name", "role", "origin"}] (by faction name), "knowledge": [{"id",
"position", "level", "content", "origin"}] (by position)}`. With a `view`
(the player), an entity outside `view.entity_ids` is named None; without
(the creator), by its name.
`open_draft_of(db, *, world_id, user_id) -> Optional[PcDraft]`: the user's
non-approved draft of the world, or None.

### C-14 -- the player's creation routes
(Amended by AMENDMENT-0126-01: `pc_draft.story`; `backstory_terms`.)
Produced by: G   Consumed by: H
Module: `src/world_engine/cockpit/routes/player_creation.py`; every path
under `/api/joueur/creation/`; each first runs `_open_world` and
`_player_profile` (R-10).
- `GET /catalogue?profile_id=&world_id=` -> `{"rules": rules_dict,
  "ranks": [six labels], "skills": [{"skill_key", "name", "base_domain",
  "system", "description", "requires_master", "start_rank", "max_rank"}],
  "places": [{"entity_id", "name"}], "factions": [{"entity_id", "name",
  "description"}]}`. Skills: the `start_sheet` lines that are base domains
  or whose id is in `public_view(...).skill_ids`, in sheet order; their
  `system` and `description` read from that view's `public_skills` rows.
  Places: `public_places`; factions: `public_factions`.
- `GET /brouillon?profile_id=&world_id=` -> `{"draft": draft_view | None,
  "verdict": verdict_dict | None}` (`open_draft_of`; verdict of
  `check_creation` on the player ranks with `check_draft`'s violations).
- `POST /brouillon` body `{profile_id, world_id}` -> 201 `{"draft",
  "verdict"}`; `PcExists` -> 409 with its message.
- `PUT /brouillon` body `{profile_id, world_id, name, story,
  start_location_id, skills, sketches, memberships, knowledge}` -> `{"draft",
  "verdict"}`; no open draft -> 404 `Aucun brouillon de personnage.`;
  `DraftLocked` -> 409; other `ValueError` -> 422; each with its message.
- `POST /verifier` body `{profile_id, world_id, skills: [{skill_key,
  rank}]}` -> `verdict_dict(check_creation(..., enforce_visibility=True),
  its violations)`; writes nothing.
- `POST /concepteur` body `{profile_id, world_id, attempt_id?}` ->
  `{"draft", "verdict", "designer": {"notes": [...], "violations":
  [violation dicts]}}`. Order: `ollama_client.ping()`, then `backstory_terms`, then
  `design` (C-11), each with its own exchange list. An `OllamaError` at the
  ping or in `backstory_terms` -> one `creation_subject/unavailable` row, 503
  `DESIGNER_UNAVAILABLE_MESSAGE`; an `LlmParseError` in `backstory_terms` -> one
  `creation_subject/parse_error` row, 502 `Le concepteur a répondu dans un
  format illisible.`; the same two errors in `design` -> a
  `creation_subject/ok` row and a `creation_design/unavailable` (503) or
  `creation_design/parse_error` (502) row; `model_exchange.fail` records
  the error on the list that failed. Success -> `apply_design`, both `ok`
  rows staged (`lore_usage.stage`) in the same transaction, one commit.
  Payloads per C-02: `asked_by` `player:<profile_id>`; subject `names`,
  `keywords` (lists, `[]` when unknown); design `lore` the lore lines,
  `proposal` `design_record(...)`, `violations` the designer's violation
  dicts, `notes`; on an error the design keys not reached are `[]` or
  None and `error` the message returned. Refusal rows go through
  `lore_usage.record` after `db.rollback()`. No open draft -> 404;
  `DraftLocked` -> 409 (neither journaled: the model was not reached).
- `POST /soumettre` body `{profile_id, world_id}` -> `{"submitted": bool,
  "draft", "verdict"}`; `submitted` False (nothing written) when
  `check_draft` finds anything; no open draft -> 404; not `draft` -> 409.

### C-15 -- the creator's view of submitted drafts
Produced by: I   Consumed by: I
Route module `src/world_engine/cockpit/routes/pc_drafts.py`:
- `GET /api/pc-drafts` -> `[{"id", "name", "player_name", "submitted_at"}]`,
  the active world's drafts with status `submitted`, by `submitted_at`.
- `GET /api/pc-drafts/{draft_id}` -> `{"draft": draft_view(..., view=None),
  "player_name", "verdict": verdict_dict (check_creation of the player
  ranks, with check_draft's violations), "skill_names": {skill_key: name}
  for every `start_sheet` line, "ranks": [the six ladder labels]}`; 404
  `Brouillon introuvable.` for an unknown id or a draft of another world.
  Both routes read only; neither writes.
Frontend: `creationState.submittedDrafts` (`[]`) and
`creationState.selectedPcDraftId` (`null`); `pcDrafts.svelte.js` exports
`loadSubmittedDrafts()`, `selectPcDraft(id)`, `loadPcDraft(id)`; island
`pcDraftPanel` (`PcDraftPanel.svelte`, container
`creation-pc-draft-panel`, `origin: 'new'`, `createdBy: 'TICKET-0126'`).

## Gate output

### (a) Property trace

One line per property about existing code that a brief asserts: property
-- finding -- the declaring file it opened.

- Skill symbols occupy `canon.py` 580-719, nothing outside names them -- R-02 -- `models/canon.py`
- `__init__` imports the four skill names from `.canon` -- R-02 -- `models/__init__.py`
- `RANK_POINTS_CHECK` has no reader outside `canon.py` -- R-02, (c)-2 -- `models/canon.py` + grep
- Skill system / definition columns and CHECKs -- R-03 -- `models/canon.py`
- v2.29 added the skill columns by ADD COLUMN, no CHECK -- R-04 -- `scripts/migrate_v2_29_rank_trials.py`
- `upsert_skill_rank` is the one writer of `skill_rank` -- R-05 -- `writes/config.py`, `canon_write_policy.txt`
- `DEFAULT_RANK = 1`, `MAX_RANK = 5`, labels, cascade order definition > system > ladder -- R-06 -- `skill_ranks.py`
- The skills CRUD routes, bodies, dicts and setters -- R-07 -- `cockpit/crud/skills.py`
- `_world_id` reads the active world -- R-07 -- `cockpit/crud/_shared.py`
- `skill*` and `skill_rank` are canon tables; sites are listed per function -- R-08 -- `canon_write_policy.txt`, `single_canon_write.py` (implementation docstring + rule)
- One player character per (world, user) -- R-09 -- `models/canon.py` (`Character.__table_args__`)
- `User` columns; `_open_world`, `_player_profile` and their messages -- R-10 -- `models/pipeline.py`, `routes/player.py`
- PR8's rules on `routes/player.py` -- R-11 -- `player_routes.py` (implementation :320-345)
- `PublicView` built only by `public_view`; members, sections, tables -- R-12 -- `perspective_selectors.py`
- `public_scope`, `NameScope` public needs known facts, `resolve_named` verdicts, `CATEGORIES` -- R-13 -- `perspective_query.py`, `name_index.py`, `lore_resolve.py`
- The audit's branches and its `StopIteration` hazard -- R-14 -- `perspective_audit.py`
- An unknown render section raises -- R-15 -- `lore_render.py`
- PI1 needles, PI2 count 4, PI4 `_build_world` -- R-16 -- `perspective_isolation.py` (implementation)
- `SelectorSpec` shape, `validate_plan(lookups=)`, `_call_args` -- R-17 -- `lore_selectors.py`, `lore_query.py`
- The planner reads `PERSPECTIVE_DESCRIPTIONS`; ping / journal / 503 / 502 shape -- R-18 -- `cockpit/perspective_flow.py`
- Journal steps, its CHECK, `PAYLOAD_KEYS`, `stage`/`record`, `attempt_id`; U1, PS1, PS2 -- R-19 -- `models/pipeline.py`, `writes/lore_usage.py`, `lore_usage.py`, `lore_usage.py` (check), `player_entry_schema.py` (implementation)
- `world_premise` reads `is_active`; regimes; WP1 tuples and PASS line -- R-20 -- `world_premise.py`, `world_premise.py` (check implementation)
- `call_json` fills twice, replaces values in the user message only -- R-21 -- `prompt_call.py`
- `PromptSpec` fields; the check's bijection and call-site rule -- R-22 -- `prompt_registry.py`, `prompt_registry.py` (check implementation)
- `premised_texts`, `upsert_prompt_template`, the heads tuple, the seed loop, the 0121 delivery script, prompt_lean rule 2 -- R-23 -- `scripts/seed_pilot.py`, `scripts/apply_ticket_0121_designer_prompts.py`, `prompt_lean.py`
- The designer module imports `chat` from `ollama_client` -- R-24 -- `quest_designer.py`
- `is_zone`, `zone_ids` -- R-25 -- `zone_rules.py`
- `KNOWLEDGE_LEVELS` -- R-26 -- `writes/knowledge.py`
- `_DIRECT_WORLD_SCOPED_DELETES` ends with `quest_request`; W1/W3/W4; `_build_world` inserts no user -- R-27 -- `writes/worlds.py`, `world_cascade.py` (implementation)
- Every JSON column must be allow-listed -- R-28 -- `json_ui_boundary.py` (implementation)
- Package layout and import order -- R-29 -- `models/__init__.py`
- `QuestRequest`'s `skill_key` text, non-canon, own writer -- R-30 -- `models/pipeline.py`
- `WorldPage.svelte` button; `call`/`postJson`; PSH2-PSH4 -- R-31 -- `frontend/src/joueur/*`, `player_shell.py` (implementation)
- Compétences records, branches, save; TF1, TF2, C3, C2 needles -- R-32 -- the three Compétences files, `rank_trials.py`, `skill_progression.py`, `npc_skills.py` (implementations)
- The right column's display strings; `pj` entry; `_creationActivateTab`; germ group, registry, mount, state, CSS; CL1/CL2 -- R-33 -- `Creation.svelte`, `tabs.js`, `EntityList.svelte`, `registry.js`, `mount.js`, `state.svelte.js`, `sheetState.svelte.js`, `creation.css`, `creation_layout.py` (implementation), `.claude/rules/frontend.md`
- Router import and include lines -- R-34 -- `cockpit/app.py`
- `_fresh_engine`, `_Stub`, `_swap`, `_seed_prompts`, TestClient base URL -- R-35 -- `world_sheet.py`, `lore_usage.py`, `player_routes.py` (checks)
- Budgets, invariant bullet shape, id continuity, rule-file front matter, footer -- R-36 -- `claude_md_contract.py` (implementation), `CLAUDE.md`, `.claude/rules/player-surface.md`, `ARCHITECTURE_DECISIONS.md`
- 15-second per check -- R-37 -- `corpus_gate.py`
- File sizes and the caps -- R-40 -- `module_budget.py` + `wc`/`ast`
- `static_table_names()` -- R-41 -- `schema_reconcile.py`

No brief invokes a convention it does not name: each « as X does » names
the file and the finding (R-NN) it copies.

### (b) Case tables

**(b)-1 `check_creation` (C-04), on CB1's world.** Default rules (pool 6,
costs 1/1/2/3/4, Inexpérimenté cap 2, max rank 5, one master skill, visible).
Systems: `Martial` (`cap_raised_at_creation = 1`), `Magie`
(`visible_at_creation = False`, `cap_held_at_creation = 1`). Definitions:
`Escrime` (Martial, open), `Lutte` (Martial, open), `Pistage` (no system,
open, `max_rank_at_creation = 2`), `Sorts` (Magie, open: invisible by its
system), `Nécromancie` (Magie, requires a master, `visible_at_creation =
True`), `Alchimie` (no system, requires a master, visible).

| # | choices | enforce | spent | violations (codes, in order) |
|---|---|---|---|---|
| 1 | {} | yes | 0 | none |
| 2 | Escrime 2 | yes | 1 | none |
| 3 | Escrime 4 | yes | 6 | none |
| 4 | Escrime 5 | yes | 10 | over_pool |
| 5 | Pistage 3 | yes | 3 | above_max_rank |
| 6 | physical 0 | yes | -1 | none (remaining 7) |
| 7 | physical 0, agility 0, perception 0 | yes | -3 | over_rank_cap (rank 0) |
| 8 | Nécromancie 1 | yes | 1 | over_system_held (Magie: Sorts + Nécromancie) |
| 9 | Nécromancie 1, Alchimie 1 | yes | 2 | over_master_count, over_system_held |
| 10 | Sorts 2 | yes | 1 | not_visible |
| 11 | Sorts 2 | no | 1 | none |
| 12 | Escrime 2, Lutte 2 | yes | 2 | over_system_raised (Martial) |
| 13 | nope 2 | yes | 0 | unknown_skill |
| 14 | Escrime 7 | yes | 0 | rank_out_of_range |
| 15 | Escrime True | yes | 0 | rank_out_of_range |
| 16 | rules `cap_at_rank_2 = 1`; Escrime 2, Pistage 2 | yes | 2 | over_rank_cap (rank 2) |
| 17 | rules `pool = 0`; physical 0, Escrime 2 | yes | 0 | none |

Every outcome is reachable; case 8 is the R1 (held) interaction Nia was
warned about; case 17 shows a refund paying a raise.

**(b)-2 Cascades (C-03).** For `skill_visible` and `skill_max_rank`:

| definition | system | world | result |
|---|---|---|---|
| value | any | any | definition's |
| None | value | any | system's |
| None | None (or no system) | value | world's |
| base domain | -- | any | visible: True; max rank: world's |

**(b)-3 The designer's resolution (C-11), item by item.**

| input | outcome | note (verbatim, French) |
|---|---|---|
| skill code listed, rank int 0..5 | `DesignedSkill` | -- |
| skill code not listed (unknown, or an invisible skill: never listed) | dropped | `Compétence inconnue écartée : {code}.` |
| skill rank not an int 0..5 | dropped | `Rang invalide écarté pour « {name} ».` |
| sketch not an object, or empty name | dropped | `Une personne sans nom a été écartée.` |
| sketch kind outside `PC_SKETCH_KINDS` | kind `other` | -- |
| sketch kind `master`, skill code of a listed skill requiring a master | `skill_key` set | -- |
| sketch kind `master`, any other skill | kind `other`, no skill | `« {name} » : maître sans compétence connue, gardé comme « autre ».` |
| sketch `existing` resolves (person, public scope) to one character of the view | `existing_entity_id` set | -- |
| sketch `existing` otherwise | None | -- |
| sketches beyond `PC_SKETCH_MAX` minus the player's | dropped | `{n} personne(s) proposée(s) écartée(s) : 8 au plus.` |
| `start_place` equal (`normalize_surface`) to a listed place | its id | -- |
| `start_place` a non-empty unmatched name | None | `Lieu de départ inconnu écarté : {name}.` |
| `start_place` null or empty | None | -- |
| membership faction equal to a listed faction | kept | -- |
| membership faction unmatched | dropped | `Faction inconnue écartée : {name}.` |
| membership faction given twice | first kept | -- |
| knowledge level outside `PC_KNOWLEDGE_LEVELS` | level `rumor` | -- |
| knowledge empty content | dropped | -- |
| knowledge beyond `MAX_KNOWLEDGE` | dropped | -- |
| `notes` | the model's non-empty strings, then the code's notes | -- |
| (AMENDMENT-0126-01) skill code given twice | the first valid entry kept | -- |
| (AMENDMENT-0126-01) a membership or knowledge item that is not an object | dropped | -- (no note) |
| (AMENDMENT-0126-01) membership faction | matched under `normalize_surface`, as the place | -- |
| (AMENDMENT-0126-01) sketch `group` | stored as `group_label` | -- |

**(b)-4 The draft writer (C-12).**

| call | draft status | outcome |
|---|---|---|
| `open_draft`, user holds a player character of the world | -- | `PcExists` |
| `open_draft`, an open draft exists | any but approved | that draft |
| `open_draft`, none | -- | a new `draft` |
| `save_player_draft` / `apply_design` / `submit_draft` | not `draft` | `DraftLocked` |
| `save_player_draft`, a designer sketch listed unchanged | draft | origin stays `designer` |
| `save_player_draft`, a designer sketch listed with a field changed | draft | origin `player` |
| `save_player_draft`, a sketch not listed | draft | deleted |
| `apply_design`, sketches | draft | `designer` rows replaced, `player` rows kept |
| `apply_design`, start place set by the player | draft | kept |
| `apply_design`, start place set by the designer or none | draft | the design's |
| `submit_draft`, violations | draft | `ValueError`, nothing written |
| `submit_draft`, none | draft | `submitted`, `submitted_at` set |

**(b)-5 The player's creation routes (C-14).**

| request | status |
|---|---|
| any, world closed or unknown | 404 `Monde introuvable.` |
| any, profile unknown, inactive or not a player | 404 `Profil introuvable.` |
| POST brouillon, character exists | 409 |
| PUT / concepteur / soumettre, no open draft | 404 `Aucun brouillon de personnage.` |
| PUT / concepteur / soumettre, draft submitted | 409 `DRAFT_LOCKED_MESSAGE` |
| PUT, writer `ValueError` | 422 its message |
| concepteur, ping down | 503, one `creation_subject/unavailable` row |
| concepteur, unparsable subject | 502, one `creation_subject/parse_error` row |
| concepteur, unparsable design | 502, `creation_subject/ok` and `creation_design/parse_error` rows |
| concepteur, Ollama down during the design | 503, `creation_subject/ok` and `creation_design/unavailable` rows |
| concepteur, success | 200, both `ok` rows, the design applied |
| soumettre, violations | 200 `submitted: false`, nothing written |
| soumettre, clean | 200 `submitted: true` |

### (c) Enumerations

(c)-1 -- skill names in `canon.py` outside 580-719 (empty) and importers of
`models.canon`:
```
$ grep -n "BASE_SKILL_DOMAINS\|RANK_POINTS_CHECK\|SkillSystem\|SkillDefinition\|\bSkill\b" canon.py | awk -F: '$1<580 || $1>719'
(no output)
$ grep -rn "from \.canon import\|from \.\.models\.canon\|models\.canon\b\|world_engine\.models\.canon\b" src scripts tooling --include=*.py
src/world_engine/models/canon_knowledge.py:17:from .canon import _created_ts, _uuid
src/world_engine/models/config.py:26:from .canon import _created_ts, _uuid
src/world_engine/models/canon_attribute.py:40:from .canon import _created_ts, _uuid
src/world_engine/models/__init__.py:61:from .canon import (
src/world_engine/models/quests.py:29:from .canon import _created_ts, _uuid
src/world_engine/models/ephemeral.py:19:from .canon import _created_ts, _uuid
src/world_engine/models/schedule.py:18:from .canon import _created_ts, _uuid
src/world_engine/models/observation.py:22:from .canon import _created_ts, _uuid
src/world_engine/models/canon_event.py:46:from .canon import _created_ts, _uuid
src/world_engine/models/canon_faction.py:16:from .canon import _created_ts, _uuid
src/world_engine/models/pipeline.py:24:from .canon import _created_ts, _uuid
```
(c)-2 -- `RANK_POINTS_CHECK` readers:
```
src/world_engine/models/canon.py:588:RANK_POINTS_CHECK = " AND ".join(
src/world_engine/models/canon.py:600:        CheckConstraint(RANK_POINTS_CHECK, name="ck_skill_system_rank_points"),
src/world_engine/models/canon.py:636:        CheckConstraint(RANK_POINTS_CHECK, name="ck_skill_definition_rank_points"),
```
(c)-3 -- every check naming `canon.py` (step 4 of the protocol for A's
symbol move); none asserts a skill symbol in it:
```
tooling/verify/checks/prompt_version.py:60      (comment)
tooling/verify/checks/world_tick.py:143         (comment: AgendaStep)
tooling/verify/checks/npc_schedule.py:69        CANON_FILE: CheckConstraint scan of schedule/canon -- unchanged, it counts CHECKs of its own tables
tooling/verify/checks/standing_goal.py:12,33    NpcGoal's CHECKs -- unchanged
tooling/verify/checks/day_plan.py:186-438       Agenda's CHECKs -- unchanged
tooling/verify/checks/no_world_magic_status.py:14  World model -- unchanged
tooling/verify/checks/parked_plan_guard.py:5,37 Agenda status values -- unchanged
tooling/verify/checks/npc_goal_read.py:37-39    NpcGoal -- unchanged
tooling/verify/checks/schema_0025.py:4          (docstring)
$ for f in npc_schedule standing_goal day_plan parked_plan_guard npc_goal_read no_world_magic_status; do grep -n "Skill\|BASE_SKILL\|RANK_POINTS" $f.py; done
day_plan.py:205, 391, 394: the condition form names "skill_rank_gte" -- not a model symbol
```
(c)-4 -- `PublicView(` constructions:
```
src/world_engine/perspective_selectors.py:49:    return PublicView(world_id=world_id, fact_ids=frozenset(fact_ids), entity_ids=frozenset(entity_ids))
```
(c)-5 -- checks reading the frontend files E and I edit:
```
CompetencesSheet / CompetencesList / competences.svelte.js:
  graph_primitive.py (comment), npc_skills.py (C2), page_contract.py (comment),
  rank_trials.py (TF1, TF2), skill_progression.py (C3)
EntityList.svelte / Creation.svelte / tabs.js / registry.js / mount.js / state.svelte.js:
  creation_container_sizing.py creation_island.py creation_layout.py creation_return_nav.py
  creation_tab_switch.py dashboard_tab.py debts.py event_journal.py graph_primitive.py
  legacy_call.py legacy_mount.py npc_skills.py observation_surface.py page_contract.py
  quests.py review_component.py review_root_fallback.py stylesheet_partition.py
  world_sheet.py zone_graph.py
frontend/src/joueur/*: player_shell.py only
```
(c)-6 -- readers of the perspective tables:
```
src/world_engine/perspective_audit.py:25, 94, 114      _PERSPECTIVE_LOOKUPS
src/world_engine/perspective_query.py:23, 95, 111      _PERSPECTIVE_LOOKUPS
src/world_engine/cockpit/perspective_flow.py:29, 74    PERSPECTIVE_DESCRIPTIONS
tooling/verify/checks/perspective_isolation.py:10-11, 130-137   PI2 (count 4)
tooling/verify/checks/player_routes.py:12, 63, 65      a public_dossier plan only
```
(c)-7 -- checks naming the journal steps or payload keys:
```
tooling/verify/checks/lore_usage.py:231-247       U1: CHECK pairs == LORE_USAGE_STEPS
tooling/verify/checks/player_entry_schema.py:72-90  PS1: the perspective entries only
tooling/verify/checks/player_routes.py:159-160    perspective rows only
```
(c)-8 -- the highest invariant id: `INV-66`
(`.claude/rules/player-surface.md:17`); INV-67 is free.
(c)-9 -- callers of `_player_character_id(` (the G2 reason, 0129):
`cockpit/crud/entities.py`, `cockpit/routes/creator.py`,
`cockpit/routes/scene.py`, `cockpit/routes/play.py`,
`cockpit/routes/spatial.py`.

### (d) Contracts re-derived

- [x] The violation family (C-04): `VIOLATION_CODES` and
  `DRAFT_VIOLATION_CODES` written before the steps; each step re-read
  against the list after the last (9 + 9 codes, each with one message).
- [x] The public selector family (C-07) re-read against LOT-0125 C-04's
  family rule: `(world_id, view, db)` signature, every row a `"section"`,
  only ids in the view, no forbidden key (`skill_id`, `requires_master` are
  not in the forbidden set).
- [x] The route family (C-14): every route runs `_open_world` then
  `_player_profile`, answers French `detail` strings, and the status table
  (b)-5 covers each.
- [x] The draft child-table family (C-02): every child carries `draft_id`,
  `world_id`, an `origin` (but skills, which carry two ranks) and no JSON.

### (e) Gates and the modules that satisfy them

Proposed:
- `creation_schema.py` (B) -- satisfied by `models/canon_skill.py`,
  `models/pc_drafts.py`, `models/pipeline.py`, `writes/lore_usage.py`,
  `scripts/migrate_v2_32_character_creation.py`, `schema_version.py`. Needs
  nothing it forbids: it reads the models and runs the script as a
  subprocess on its own temp file.
- `creation_budget.py` (C) -- satisfied by `creation_rules.py`,
  `creation_check.py`, `writes/creation_rules.py`, `crud/skills.py`. Its
  static rule (no `cost_to_rank_` outside the named modules) is satisfied
  because the only readers of the columns are those modules, the models
  and the migration, all named in the rule.
- `perspective_isolation.py` PI2/PI6 (D) -- satisfied by
  `perspective_selectors.py`, `perspective_audit.py`, `lore_render.py`;
  PI1 stays true because `creation_rules.py` is imported, not inlined, and
  is not one of the four scanned modules.
- `creation_rules_ui.py` (E) -- satisfied by `CreationRulesFiche.svelte`,
  `creationRules.svelte.js`, the three Compétences files and the built
  bundle.
- `creation_designer.py` (F) -- satisfied by `world_premise.py`,
  `prompt_call.py`, `creation_lore.py`, `creation_designer.py`,
  `prompt_registry.py`, `scripts/seed_pilot.py`,
  `scripts/apply_ticket_0126_designer_prompts.py`.
- `player_creation.py` (G) -- satisfied by `writes/pc_drafts.py`,
  `pc_draft_reads.py`, `cockpit/routes/player_creation.py`, `cockpit/app.py`.
- `player_shell.py` PSH5 (H) -- satisfied by the new files under
  `frontend/src/joueur/` and the built bundle.
- `creation_layout.py` CL1 (re-pinned) and CL5 (I) -- satisfied by
  `Creation.svelte`, `tabs.js`, `EntityList.svelte`, `registry.js`,
  `mount.js`, `state.svelte.js`, `sheetState.svelte.js`,
  `PcDraftPanel.svelte`, `pcDrafts.svelte.js`, `creation.css`.
- `submitted_drafts.py` (I) -- satisfied by `cockpit/routes/pc_drafts.py`
  and `cockpit/app.py`.

Merely passed (each named in its brief's Scope IN):
- `module_budget.py` -- every edited file stays under its cap (R-40); A runs
  first so B fits `canon.py`.
- `single_canon_write.py` -- C lists `creation_rules` and its writer; the
  draft tables are non-canon; the CRUD routes C edits are listed already.
- `world_cascade.py` -- B adds the six tables, their fixture rows and the
  fixture user.
- `json_ui_boundary.py` -- no JSON column added.
- `lore_usage.py` U1, `player_entry_schema.py` PS1/PS2 -- B changes the CHECK
  and the steps together.
- `world_premise.py` WP1 -- F adds the two usages to `PLAYER`; WP2 and WP3
  stay true (no new caller of `premised_prompt(`/`current_prompt(`;
  `call_json` keeps two `fill(`).
- `prompt_registry.py` -- F seeds and registers both usages, call sites on
  module-level functions.
- `prompt_lean.py` rule 2 -- F's prompt constants hold no world's proper
  name.
- `player_routes.py` PR8 -- `routes/player.py` is not edited.
- `rank_trials.py` TF1/TF2, `skill_progression.py` C3, `npc_skills.py` C2 --
  E keeps every needle (R-32).
- `creation_island.py`, `creation_container_sizing.py`, `page_contract.py`,
  `creation_tab_switch.py` -- I mirrors the germ panel's registration,
  which passes them today; `pj` keeps one container.
- `claude_md_contract.py` -- C's new rule file and list line, D's and F's
  INV-66 edits, each line under 100 characters, budgets under their caps.
- `frontend_build_fresh.py` -- E, H, I rebuild and commit the bundle.
- `file_map.py` -- `/close-step` regenerates `FILE_MAP.md` for every new
  module.

## Drafting decisions flagged to Nia

Each was decided while drafting, without an explicit instruction; each is
reversible before execution.

1. TICKET-0129 is the number of the review ticket (L2 cut), run before 0127.
2. Defaults written into the schema: pool 6; costs 1/1/2/3/4; Inexpérimenté
   cap 2; no other cap; max rank Maître; one skill requiring a master;
   visible by default.
3. The draft keeps both ranks per skill (`player_rank`, `designer_rank`):
   the counter-proposal never overwrites the player's choice; « Accepter »
   copies it.
4. A sketch, membership or knowledge line edited by the player becomes
   `origin = player` and survives the next designer call.
5. Draft knowledge levels are limited to `rumor`, `suspicious`, `partial`,
   `knows`.
6. The designer's sketch room is 8 minus the player's own sketches.
7. Base domains may be lowered (P1) but are not in `public_skills`: they
   are no world lore; the catalogue adds them.
8. The designer route journals both steps in one transaction with the
   draft change; refusals before the model (404, 409) are not journaled.
9. The creator's panel shows only `submitted` drafts, never drafts in
   progress.
10. The skill system and definition overrides have no database CHECK (the
    v2.29 precedent); their bounds live in the request bodies.

## Amendments

- AMENDMENT-0126-01 (2026-10-23, during F): `pc_draft.story` and
  `backstory_terms` (R-a); R-43; C-02, C-04, C-11-C-14 and (b)-3 amended; G,
  H, I regenerated.
