<!-- slug: character-selectors -->
# BRIEF 0127-C — "Every selector answers through the view; the self sheet; the renderer's suffixes"

Lot: LOT-0127-character-perspective.md (authoritative on conflict)
Depends on: BRIEF-0127-B (C-02, C-03, the CP fixture)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/perspective_selectors.py`: `_participant_facts`
  holds `Fact.event_id.is_(None),`; `def known_dossier(` exists;
  `known_factions` filters `Entity.is_public == True,  # noqa: E712`;
  `def _public_membership_rows(` and `def _public_members(` exist;
  `class Belief:` and `class PerspectiveView:` hold C-02's fields.
- `src/world_engine/perspective_view.py` defines `character_view`,
  `player_character_of`, `world_characters`, `UnknownCharacter`,
  `CERTAINTY_LABELS`.
- `src/world_engine/lore_render.py:41` is `def _format_facets(row: dict) ->
  str:`; `:124` `def _format_public_mentions(row: dict) -> str:`; `:140`
  opens `_SECTION_FORMATTERS`, whose last entry is `"skills": _format_skills,`.
- `src/world_engine/skill_ranks.py:77` is `def world_ladder(db: Session,
  world_id: str) -> tuple[RankStep, ...]:`.
- `tooling/verify/checks/character_perspective.py` passes CP1-CP3.

Halt if any anchor has moved.

## Facts carried

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

B built a character's view; nothing reads it yet. This brief makes every
selector read through the view -- facts, texts, entities, memberships --
so the same code answers for everybody and for one character (H1-b), adds
the character's self sheet (E1), puts known events into the dossier for
both perspectives (F1), and teaches the Lore renderer the two new marks
and sections.

## Scope IN

1. `perspective_selectors.py`, `view_texts` per C-05 (imports
   `fact_texts_at`).
2. `_participant_facts(entity_id, world_id, db)`: also returns the facts of
   the world whose `event_id` is the `event_id` of an `EventParticipant` row
   with that `entity_id` (F1), deduplicated, in the existing sort (registry
   facet order, `created_at`, id). Docstring: « Every free fact of the world
   with `entity_id` as a participant, and every event fact of an event it
   takes part in (TICKET-0127, F1), ... ». Its other callers (the factions'
   description facts, the audit) keep their filters.
3. Rule M (C-06) as one private function `_membership_shown(member, faction,
   view) -> bool` taking two `Entity` rows. `_public_membership_rows` is
   renamed `_membership_rows` and `_public_members` `_view_members`; both
   apply rule M as C-06 member 1 states (a secret membership is never shown;
   the names of `read_public_memberships` are kept only when every current
   membership of that name is shown). `public_member_ids` is unchanged.
4. `known_dossier` per C-06 member 1: facts kept in `view.fact_ids`, content
   by `view_texts`, label `"Événement"` for a fact with an `event_id`, rows
   with `secret` and `certainty` as the family rule states; liens likewise.
5. `known_factions` per C-06 member 2 (the SQL `is_public` filter goes; the
   view decides). `known_facts_mentioning` per member 3, through a private
   `_view_facts_matching(text, world_id, view, db)` over `view.fact_ids` and
   `view_texts`; `_facts_matching` stays as is for the audit; rows gain
   `secret` and `certainty`.
6. `self_sheet` per member 6 (imports `acquaintances`, `world_ladder`,
   `BASE_SKILL_DOMAINS`, `Skill`, `SkillSystem`).
7. The tables of C-07 after the public ones: `CHARACTER_SELECTORS`,
   `_CHARACTER_LOOKUPS`, `CHARACTER_DESCRIPTIONS` (verbatim), `lookups_for`,
   `descriptions_for`.
8. The module docstring's first sentence becomes « The perspective
   selectors: what a view -- everybody, or one character -- knows about a
   world (TICKET-0125, BRIEF-0125-D, C-04; TICKET-0127, C-06). »; the
   paragraph after it says each selector reads the facts, texts and entities
   of its view, never a fact or an entity outside it, nor a key naming
   secrecy levels or knowers.
9. `src/world_engine/lore_render.py` per C-08.
10. `character_perspective.py`: rules CP4 and CP5 of C-15; the docstring
    lists them and the « added by » line reads « CP6-CP7 are added by
    BRIEF-0127-D. »
11. Regenerate `FILE_MAP.md` (first sentence of `perspective_selectors.py`
    changed).
12. Commits: (a) « TICKET-0127 C: the selectors read through the view;
    events in the dossier (C-05, C-06, F1) »; (b) « TICKET-0127 C: the self
    sheet and the character's table (C-07) »; (c) « TICKET-0127 C: the
    renderer's certainty, secret mark and new sections (C-08) »; (d)
    « TICKET-0127 C: character_perspective CP4-CP5; FILE_MAP regenerated ».

## Scope OUT

- The executor, the audit, the renderer's verdict messages, the flow, the
  routes, the journal (D).
- Events' participants named in `public_mentions` rows (only
  `FactParticipant`, as today).
- A label from `FACETS["evenement"]` (« Événements »): the dossier says
  « Événement », as it says « Lien ».
- Any change to `public_member_ids` or to TICKET-0129's approval.
- Screens (E).

## Invariants to defend

- INV-03: memberships still reach rows only through `read_public_memberships`
  (an entity's) and the faction-keyed WHERE triplet (a faction's); rule M only
  removes rows. No secret membership, no true `role` behind a `cover_role`.
- INV-66: every selector returns nothing outside its view; a public view's
  answers are today's but for the events of F1 (PI4 and PI6 stay green).
- INV-58 (`.claude/rules/authoring-lore.md`): the renderer receives rows, never
  a `Session` -- the new formatters read the row only.
- INV-01: a `secret` mark appears only on a character view at the creator's
  door (the player's view holds no secret belief, B).

## Decision rights

STOP:
- An anchor does not hold.
- A set of CP4/CP5 differs from C-15 on the fixture: report the printed rows.
- PI4 or PI6 of `perspective_isolation.py` turns red.

ADAPT:
- A creation-side caller (`creation_lore.py`, `player_creation.py`) breaks on
  the extra `certainty` / `secret` keys: read only the keys it already reads,
  report.
- `_participant_facts` needs a join `Fact` -> `EventParticipant` that the
  ORM writes differently from C-06's wording: keep the semantics (same rows,
  same sort), report.

REPORT-ONLY:
- A public dossier of the live database that now lists events (expected, F1).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python -c "import sys; sys.path.insert(0,'src'); from world_engine.schema_reconcile import static_table_names; print(sorted(static_table_names()))"`
      prints the same list before and after (paste both).
- [ ] PASS: `character_perspective.py` (CP1-CP5), `perspective_isolation.py`,
      `player_routes.py`, `creation_designer.py`, `player_creation.py`,
      `draft_approval.py`, `lore_isolation.py`, `lore_usage.py`,
      `knowledge_identity.py`, `lore_as_facts.py`, `file_map.py`,
      `module_budget.py`.
- [ ] Named mutations, each red then reverted: drop rule M's `member_of`
      branch -> CP4 red; drop the event facts from `_participant_facts` ->
      CP4 red; render the current text instead of `view_texts` in
      `known_dossier` -> CP4 red; drop the certainty suffix of
      `_format_public_mentions` -> CP5 red.
- [ ] `corpus_gate.py`: green, or red only on rules D adds -- name them.
- [ ] /review-step and /close-step run.

## Docs to update

FILE_MAP regenerated (Scope IN 11). No schema entry, no CLAUDE.md change,
no decision entry (E).
