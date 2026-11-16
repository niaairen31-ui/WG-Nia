<!-- slug: character-flow-and-doors -->
# BRIEF 0127-D — "The executor, audit, renderer and flow over a view; the two doors; the journal"

Lot: LOT-0127-character-perspective.md (authoritative on conflict)
Depends on: BRIEF-0127-C (C-05 to C-08)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/perspective_query.py:45` is `def resolve_public_mentions(`
  and `:89` `def execute_public_plan(`; `perspective_audit.py:23` is `from
  .perspective_query import resolve_public_mentions` and `:95` `def withheld(`.
- `src/world_engine/perspective_render.py:30` is `def render_public(`.
- `src/world_engine/cockpit/perspective_flow.py:32` is `PERSPECTIVE =
  "public"`; `:59` `def ask_flow(db: Session, *, question: str, world_id:
  str, asked_by: str, attempt: str) -> dict:`.
- `src/world_engine/cockpit/routes/lore_perspective.py:45` is `def
  _check_perspective(perspective: str) -> None:`.
- `src/world_engine/cockpit/routes/player.py:32` is `PLAYER_ANSWER_KEYS:
  tuple[str, ...] = ("verdict", "answer", "renderer", "candidates", "plan")`;
  the module is 129 lines.
- `src/world_engine/writes/lore_usage.py:35` is `"perspective_ask":
  frozenset({"question", "perspective", "asked_by", "response", "withheld",
  "error"}),`.
- `tooling/verify/checks/player_entry_schema.py:38` is `"perspective_ask":
  {"question", "perspective", "asked_by", "response", "withheld", "error"},`.
- `perspective_selectors.py` defines `lookups_for`, `descriptions_for`,
  `CHARACTER_SELECTORS`; `character_perspective.py` passes CP1-CP5.

Halt if any anchor has moved.

## Facts carried

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
### R-18 -- the character row
Opened: `src/world_engine/models/canon.py:123-175`.
Finding: `Character(id -> entity.id, world_id, character_type ("player" |
"npc"), user_id, current_location_id, ...)`; unique
`idx_character_one_pc_per_user_world` on `(world_id, user_id)` where
`character_type = 'player'`. `Entity(world_id, type, name, status,
is_public, ...)`.
Consequence: `player_character_of` reads at most one row (C-03).
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

## Contracts

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

## Context

The selectors answer for any view (C). This brief carries the view
through the executor, the audit and the renderer, the shared flow and its
journal, and opens the two doors: the creator asks as any character (H1-b),
the player as his own (G1). It adds the check's routes and the rules that
prove the secret never leaves the creator's door (H1-d).

## Scope IN

1. `perspective_query.py` per C-09 (imports `PerspectiveView`,
   `lookups_for`, `public_view`). First docstring sentence: « The
   perspective executor: a plan run over what a view knows (TICKET-0125,
   BRIEF-0125-D, C-05, C-06; TICKET-0127, C-09). »
2. `perspective_audit.py` per C-10: `WITHHELD_REASONS`, `withheld_for`,
   `withheld` as a one-line delegate, the character branches of the case
   table (the holder's stored secret rows read in one query when `view.door
   == "player"`; `fact_is_stale` from `prose_render`); the import follows
   the rename to `resolve_view_mentions`. No new `subject` reference (R-25).
   First docstring sentence: « The perspective audit: every line an answer
   withheld, and why (TICKET-0125, BRIEF-0125-D, C-07; TICKET-0127, C-10). »
3. `perspective_render.py` per C-11. First docstring sentence: « The
   perspective renderer: the answer to a question asked as everybody or as
   one character, in prose or by code (TICKET-0125, BRIEF-0125-D, C-08;
   TICKET-0127, C-11). »
4. `cockpit/perspective_flow.py` per C-12. First docstring sentence: « The
   shared perspective flow behind two doors, as everybody or as one
   character (TICKET-0125, BRIEF-0125-E, C-15; TICKET-0127, C-12). » It
   keeps no `select(` and no `chat(`.
5. `writes/lore_usage.py`: `PAYLOAD_KEYS` and the comment per C-12.
   `tooling/verify/checks/player_entry_schema.py:38-40`: `C09_KEYS` gains
   `"character_id"` in both sets; PS2d's payload (`:200-201`) follows from
   them unchanged.
6. `cockpit/routes/lore_perspective.py` per C-13 (imports
   `world_characters` from `...perspective_view`). First docstring sentence:
   « The creator's perspective routes: Lore as everybody or as any character
   (TICKET-0125, BRIEF-0125-E, C-10; TICKET-0127, C-13). »
7. `cockpit/routes/player.py` per C-13 (imports `player_character_of` from
   `...perspective_view`); the docstring's sentence on the savoir routes adds
   « the personnage routes run it as the profile's own character at the
   player's door (TICKET-0127, G1) ». No `select(` added.
8. `character_perspective.py`: rules CP6 and CP7 of C-15 (CP7 imports
   `_seed_prompts`, `_Stub`, `_swap`, `_events`, `_all_events`, `_attempt`
   from `player_routes`); the docstring lists them and drops the « added by »
   line.
9. Regenerate `FILE_MAP.md`.
10. Commits: (a) « TICKET-0127 D: executor, audit and renderer over a view
    (C-09, C-10, C-11) »; (b) « TICKET-0127 D: the flow and its journal carry
    the character (C-12) »; (c) « TICKET-0127 D: the creator asks as any
    character, the player as his own (C-13) »; (d) « TICKET-0127 D:
    character_perspective CP6-CP7; FILE_MAP regenerated ».

## Scope OUT

- Screens (E), INV-01 / INV-66 wording (E), the decision entry (E).
- A `character_name` or any other key in the creator's or the player's
  answer (PR5 pins the keys).
- A migration: the journal's CHECK names kinds and steps only (R-21).
- Renaming `execute_public_plan`, `withheld`, `render_public`,
  `public_scope`: they stay as delegates for their callers (R-04).
- Several characters per profile in a world (TICKET-0128).

## Invariants to defend

- INV-01: the player's door builds its view with `door="player"`; the
  render prompt of a player's question never holds a secret row (CP7e).
- INV-66: the player's routes reach the world only through
  `perspective_flow` and `perspective_view`; they answer only
  `PLAYER_ANSWER_KEYS`; rows and audit are journaled, never returned.
- INV-58: an empty verdict never reaches a model (`render_perspective` keeps
  `render_public`'s order).
- INV-59 (`.claude/rules/authoring-lore.md`): the journal is written only
  through `lore_usage` and read back by no prompt, play or creator path --
  the flow writes `character_id`, nothing reads it. A refused perspective,
  an unknown character and a foreign character are refused before any row
  (C-12, C-13), as today's unknown perspective.

## Decision rights

STOP:
- An anchor does not hold.
- PR5 or PR8 of `player_routes.py` turns red.
- A CP6/CP7 set differs from C-15: report what printed.

ADAPT:
- `lore_perspective.py` needs `Optional` or `Query` imports for the GET:
  add exactly them, report.
- `perspective_flow.py` needs the character's view before the ping to
  refuse an unknown character: build it first (C-12 says so), report if a
  check expected another order.

REPORT-ONLY:
- Journal rows of the live database written before this brief lack
  `character_id`: history, never rewritten.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python -c "import sys; sys.path.insert(0,'src'); from world_engine.schema_reconcile import static_table_names; print(sorted(static_table_names()))"`
      prints the same list before and after (paste both).
- [ ] PASS: `character_perspective.py` (CP1-CP7), `perspective_isolation.py`,
      `player_routes.py`, `player_entry_schema.py`, `player_shell.py`,
      `creation_designer.py`, `player_creation.py`, `lore_isolation.py`,
      `lore_usage.py`, `knowledge_identity.py`, `json_ui_boundary.py`,
      `file_map.py`, `module_budget.py`.
- [ ] Named mutations, each red then reverted: build the player's view with
      `door="creator"` in the flow -> CP7e red; return `public_view` for a
      character in the flow -> CP7c red; drop `_own_character` from the
      player's ask -> CP7f red; add `"rows"` to `PLAYER_ANSWER_KEYS` -> PR4
      red.
- [ ] `corpus_gate.py`: green, or red only on `player_shell.py` rules E adds
      -- name them.
- [ ] /review-step and /close-step run.

## Docs to update

FILE_MAP regenerated (Scope IN 9). No schema entry (no table or CHECK
change; the journal payload is not a schema object). CLAUDE.md and the
decision entry: E.
