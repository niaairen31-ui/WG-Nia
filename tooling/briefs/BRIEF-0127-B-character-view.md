<!-- slug: character-view -->
# BRIEF 0127-B — "A character's view and the character name regime"

Lot: LOT-0127-character-perspective.md (authoritative on conflict)
Depends on: BRIEF-0127-A (the class is `PerspectiveView`, C-01)

## Anchors to confirm (Mini-RECON)

- `src/world_engine/perspective_selectors.py`: `class PerspectiveView:`
  (A's rename) declares exactly `world_id, fact_ids, entity_ids, skill_ids`;
  `def public_view(db: Session, world_id: str) -> PerspectiveView:` builds it.
- `src/world_engine/name_index.py:35` is `REGIMES: tuple[str, ...] =
  ("names_only", "creator", "prose", "perceiver", "public")`; `:123` is
  `and (scope.regime != "public" or e.is_public)`.
- `src/world_engine/knowledge_resolve.py:253` is `def
  resolve_known_for_entity(db: Session, entity_id: str) -> dict[str, Known]:`.
- `src/world_engine/context.py:200` is `def
  read_public_membership_faction_ids(entity_id: str, session: Session) ->
  set[str]:`.
- `src/world_engine/encounters.py:140` is `def acquaintances(db: Session,
  entity_id: str) -> set[str]:`.
- `src/world_engine/facet_reads.py:58` is `def creator_only_fact_ids(db:
  Session, fact_ids: Iterable[str]) -> set[str]:`.
- `src/world_engine/creation_rules.py:111` is `def visible_skill_ids(db:
  Session, world_id: str) -> frozenset[str]:`.
- `src/world_engine/prose_render.py:76` is `def knowledge_texts(db: Session,
  rows: list) -> list[Optional[str]]:`.
- `tooling/verify/checks/perspective_isolation.py:182` is `def
  _build_world(engine) -> dict:`; `:71-73` hold `FORBIDDEN` and
  `CREATOR_SELECTORS`; `player_routes.py:74` is `def _fresh_engine():`.
- `src/world_engine/perspective_view.py` and
  `tooling/verify/checks/character_perspective.py` do not exist.

Halt if any anchor has moved.

## Facts carried

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

## Contracts

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

A1 made the public view one case of a perspective view. This brief adds
the other case: what one character knows, built on the engine's single
knowledge authority (R-10), and the name regime that lets a question name
only what he knows (D1). Nothing reads either yet; C gives them to the
selectors, D to the executor and the doors.

## Scope IN

1. `src/world_engine/perspective_selectors.py`: replace the class with
   C-02 verbatim (`PERSPECTIVE_KINDS`, `PERSPECTIVE_DOORS`, `Belief`,
   `PerspectiveView`), adding the imports it needs (`field` from
   `dataclasses`, `datetime`, `Mapping`, `Optional`). `public_view` is
   unchanged. Append to the module docstring, after its first paragraph, the
   sentence « A view is everybody's (`public_view`) or one character's
   (`perspective_view.character_view`, TICKET-0127). » The first sentence is
   unchanged.
2. Create `src/world_engine/perspective_view.py` per C-03, verbatim names and
   steps, first docstring sentence as C-03 gives it; the rest of the
   docstring states steps 3 and 6 in one sentence each and « Read-only: no
   write, no commit, no model call. »
3. `src/world_engine/name_index.py`: C-04 -- `REGIMES`, `_APPELLATION_RULES`,
   the `NameScope` field and its `__post_init__` messages, the `surfaces`
   condition, the docstring line.
4. Create `tooling/verify/checks/character_perspective.py` per C-15: the
   docstring (first sentence verbatim; CP1-CP3 stated as C-15 states them;
   one line « CP4-CP7 are added by BRIEF-0127-C and BRIEF-0127-D. »), the
   fresh engine (as `player_routes._fresh_engine`, R-22), the fixture
   `_extend` (all eight steps of C-15, through the writers C-15 names), and
   rules CP1, CP2, CP3 with exact set equality. `main()` returns 1 on any
   failure and prints `PASS: character_perspective -- ...` otherwise.
5. Regenerate `tooling/standards/FILE_MAP.md` (`python
   tooling/glue/gen_file_map.py`): it gains `perspective_view.py` and
   `character_perspective.py`.
6. Commits: (a) « TICKET-0127 B: PerspectiveView carries a character's
   beliefs; perspective_view builds it (C-02, C-03) »; (b) « TICKET-0127 B:
   the character name regime (C-04) »; (c) « TICKET-0127 B:
   character_perspective CP1-CP3; FILE_MAP regenerated ».

## Scope OUT

- Any selector, executor, audit, renderer, flow or route change (C, D).
- `public_scope`, `resolve_public_mentions` and their callers (D).
- A `__post_init__` on `PerspectiveView`: none (C-02).
- Reading a membership any other way than
  `read_public_membership_faction_ids` (INV-03).
- INV-01 / INV-66 wording (E).
- The PC/NPC distinction inside `character_view`: none; the door decides
  (C1).

## Invariants to defend

- INV-01: `character_view` reads its holder's own `is_secret` rows; at the
  player's door it must drop them by query construction (C-03 step 3). Never
  read another entity's knowledge rows.
- INV-03: the holder's factions come only through
  `read_public_membership_faction_ids` (no secret membership, no role).
- INV-07: a PC's knowledge is never secret -- the check's PC row is a
  deliberate breach to prove the door; nothing in `src/` writes one.
- INV-66: `perspective_view.py` is under `src/world_engine/perspective_*.py`;
  it imports no creator selector and holds none of PI1's tokens (CP1).

## Decision rights

STOP:
- An anchor does not hold.
- A measured set of C-15 (CP2, CP3) differs on the fixture as specified: the
  lot's R-27 is wrong; report the printed sets.
- An import cycle that a function-local import cannot break.

ADAPT:
- `perspective_view.py` closes an import cycle at module level: move the
  offending import inside the function that uses it (as `name_index.surfaces`
  does for `facet_reads`), report.
- A writer of the fixture needs an argument C-15 does not state (a role, a
  `created_by`, a `changed_by`): pass the value the writer's own docstring or
  an existing check uses, report.
- `name_index.py` F1 or R3 asserts a message text the new messages change:
  keep the old text for the old cases, report.

REPORT-ONLY:
- Any existing caller of `NameScope` that would need `entity_ids`: none
  should; list any found.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python -c "import sys; sys.path.insert(0,'src'); from world_engine.schema_reconcile import static_table_names; print(sorted(static_table_names()))"`
      prints the same list before and after (paste both).
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/character_perspective.py`
      PASS (CP1-CP3).
- [ ] PASS: `perspective_isolation.py`, `player_routes.py`, `name_index.py`,
      `name_resolution.py`, `day_choice.py`, `creation_designer.py`,
      `player_creation.py`, `draft_approval.py`, `knowledge_identity.py`,
      `lore_as_facts.py`, `file_map.py`, `module_budget.py`.
- [ ] Named mutations, each red then reverted: drop the
      `creator_only_fact_ids` subtraction in `character_view` -> CP2 red;
      drop the player-door `is_secret` filter -> CP2 red; drop the
      `character` condition in `surfaces` -> CP3 red.
- [ ] `corpus_gate.py`: green except the arrows whose rules C and D add
      (`character_perspective.py` is green with CP1-CP3; nothing else red is
      expected) -- name any red.
- [ ] /review-step and /close-step run.

## Docs to update

FILE_MAP regenerated (Scope IN 5). No schema entry (no table changes), no
CLAUDE.md change (E), no decision entry (E).
