# BRIEF 0091-G — "play readers switch to facts"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: B, D

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `context.py` `_npc_context_identity` reads appearance, backstory,
  aversion, description; `_mj_context_location` reads subculture and
  description; `context_describe.py` holds setting, company, MJ co-presents
  (B).
- `tick_context.py` lines of R-10.
- `gathering.py:96`; `link_sheet.py` `_npc_sheet` (B).
- `facet_reads.py` exports `facts_of`, `known_facts_of`, `joined` (D).

## Facts carried

### R-09 — `context.py` readers of moving columns
Opened: `src/world_engine/context.py` [M].
Finding: `_npc_context_identity` (`:231-243`) appends
`npc_char.appearance`, `.backstory`, `.aversion`, `npc_entity.description`
(`:234-241`). `_npc_context_setting` (`:327`) appends
`loc_entity.description` (`:333-334`). `_npc_context_company` (`:449`)
uses `co_char.appearance or co_entity.description` (`:471`).
`_mj_context_location` (`:698`) reads `location_subculture` rows with
`key in _SAFE_SUBCULTURE_KEYS` and `is_hidden == False` (`:704-713`) and
`loc_entity.description` (`:718`). `_mj_context_co_presents` (`:770-798`)
emits `co_entity.description` for public co-presents, `None` when
blindfolded (`:795`). `_SAFE_SUBCULTURE_KEYS = ("values",)` (`:102`).
`context.py:762` is `Event.description`, not an entity — out of scope.
Module: 956 lines, 30 top-level functions.
Consequence: G replaces each read by C-10; the file has 44 lines of
headroom, so B moves the identity/company/setting/MJ-location/MJ-co-presents
helpers out first.

### R-10 — `tick_context.py` readers
Opened: `src/world_engine/tick_context.py` [M].
Finding: `_tick_identity_block` (`:177`) appends appearance, backstory,
aversion (`:179-184`) and `npc_entity.description` (`:185-186`).
`_tick_affiliations_block` (`:280`) prints faction philosophy,
internal_tensions, aversion, goals (`:302-305`). `_tick_setting_block`
(`:313`) reads `loc_entity.description` (`:322-323`) and the `values`
subculture row, not hidden (`:326-330`). `_tick_destinations_block`
(`:337`) reads `dest_entity.description` (`:343-344`). `_tick_company_block`
(`:350`) uses `other_char.appearance or other_entity.description`
(`:364-365`). `assemble_location_event_context` (`:544`) reads the location
description (`:558-559`) and the `values` row (`:562-566`).
`_tick_faction_identity_block` (`:619`) reads faction description and
philosophy (`:623-629`); `_tick_faction_posture_block` (`:633`) reads goals,
internal_tensions, aversion (`:637-639`). Module: 736 lines, 28 functions.
Consequence: G switches every one; there is headroom.

### R-11 — the remaining readers
Opened: each file below [M].
Finding:
- `gathering.py:96` (`_request_partition`, `:84`): `char.appearance or
  entity.description` in the MJ partition prompt.
- `link_author.py:176-180` (`_npc_sheet`, `:164`): description, appearance,
  backstory, aversion. Module 959 lines, 36 functions.
- `cockpit/routes/creator.py:78` (`_generate_draft_with_l1`, `:57`):
  `faction.goals`; `:309-315` (`generate_agenda`, `:281`): owner
  description + philosophy / backstory; `:669-670`
  (`create_player_character`): `body.appearance`, `body.backstory` (PC
  creation payload).
- `cockpit/crud/goals.py:260` (`_npc_faction_goals`, `:246`):
  `faction.goals`; `:305-306` (`_backfill_one_npc`, `:289`): description,
  backstory.
- `npc_group_author.py:216` (`_resolve_faction_context`, `:210`): faction
  description; `:313` (`_generate_row_goals`, `:304`): `faction.goals`;
  `:389` `_NPC_PLAIN_STR_FIELDS = ("description", "appearance",
  "backstory", "aversion")`.
- `room_batch_author.py:100-113`, `:133` (`_compose_batch_context`, `:93`):
  non-hidden subculture of the anchor (all keys), anchor and sibling
  descriptions.
- `cockpit/play_physical.py:724` (`_build_establishment_narration`,
  `:704`): location description. `:693` is `Event.description` — out.
- `observation_runner.py:123` (`check_run_readiness`, `:84`): requires a
  non-empty `entity.description` for each NPC.
- `cockpit/crud/relations.py:293`: description truncated to 200 chars.
- `lore_candidates.py:57` (`describe_candidates`, `:18`): description.
- `cockpit/crud/entities.py:246` (`_entity_dict`, `:239`): description in
  the sheet payload.
- `lore_selectors.py:60-64` (`world_factions`, `:43`): description,
  philosophy, internal_structure, internal_tensions; `:82`, `:94-96`
  (`_identity_rows`, `:71`): description, appearance, backstory, aversion.
Consequence: H switches each through C-10. `observation_runner`'s
readiness rule becomes "has a `description` fact".

### R-12 — `location_subculture` is keyed prose with a hidden flag
Opened: `src/world_engine/models/canon.py:286-300`; `writes/config.py:104-150`;
`grep -rn "write_location_subculture(" src` [M].
Finding: columns `location_id, key, value, is_hidden`;
`idx_location_subculture_key (location_id, key COLLATE NOCASE)` unique.
One writer, `writes/config.py::write_location_subculture` (full-replace,
policy `:30`), one caller `cockpit/crud/entities.py:864`
(`set_location_subculture`, `:857`, `PUT /entities/{id}/subculture`).
`cockpit/crud/agendas.py:71` and `cockpit/crud/entities.py:80` import it
without calling it. Readers: R-09, R-10, R-11 (room batch). Key vocabulary
is free text on the creator side (`frontend/src/creation/SubcultureEditor.svelte:80`,
placeholder "clé (ex : values)").
Consequence: Q12d — each row becomes a `coutume` fact with `aspect` = key
(casefolded), content = value unchanged, participant = the location; a
visible row gets a `location` default at that location, a hidden row gets
none. The table is dropped in v2.06.

## Contracts

### C-05 — the entity-fact writer (`src/world_engine/writes/facets.py`, new)
Produced by: E (module), with `add_entity_fact` used by I's migration
logic only as a reference (I writes SQL)   Consumed by: C-12, E's cores, J
```python
@dataclass(frozen=True)
class ScopeChoice:
    scope_type: str            # "none"|"world"|"location"|"faction"|"rencontre"
    scope_id: str | None = None

def add_entity_fact(db, *, entity_id, facet, content, created_by,
                    aspect=None, scope: ScopeChoice | None = None) -> Fact
def write_entity_facets(db, *, entity_id, facets: dict, created_by) -> list[Fact]
def edit_entity_fact(db, *, fact_id, content, changed_by) -> Fact
def remove_entity_fact(db, *, fact_id) -> None
def facts_payload_keys() -> frozenset[str]   # descriptive facet names
```
`add_entity_fact`: facet must be in `DESCRIPTIVE_FACETS` (else
`ValueError`); empty/whitespace content raises; for a `bloc` facet, an
existing fact with this entity as participant, the same facet and the same
aspect raises `ValueError("bloc facet already has a fact")`;
`create_fact(facet=…, aspect=…)`, `attach_participants([entity_id])`, then
the default: `scope` when given (`none` writes nothing; `world` scope_id
None; others require scope_id), else the facet's preset (C-01). Default
level is always `knows`.
`write_entity_facets`: keys must be descriptive facet names or the
special key `creator_meta`; a `bloc` value is a `str`; an `affirmation`
value is a `list[str]` **or a `str`, split into one fact per non-empty
stripped line** (Q20b); `coutume` is a `list[{"aspect": str | None,
"content": str, "hidden": bool}]` where `hidden` means scope `none` and not
hidden means the preset. `creator_meta` (a `str`) becomes one `histoire`
fact with scope `none` plus one `knowledge` row written through
`write_knowledge(entity_id=<the entity>, fact_id=<that fact>,
subject="creator_meta", level="unaware", is_secret=True)` — the entity never
knows the creator's note (same shape as C-18's `character.secrets` row).
Empty strings are skipped. Returns the created facts in input order.
`edit_entity_fact`: refuses a fact whose facet is not descriptive;
delegates to C-03. `remove_entity_fact`: same refusal; delegates to C-04.
All four add rows and never commit.

### C-09 — resolver, amended (`knowledge_resolve.py`)
Produced by: D   Consumed by: C-10, G, H, K
Precedence, most specific first:
1. stored `knowledge` row — wins outright;
2. **self**: the entity is a `fact_participant` of the fact AND
   `fact.facet in DESCRIPTIVE_FACETS` → `knows` (Q6a, Q18a);
3. **rencontre**: a `rencontre` default whose `scope_id` is in
   `acquaintances(entity)` → that level (highest if several);
4. nearest `location` default up the parent chain;
5. highest `faction` default across active memberships;
6. `world` default;
7. `fact.default_level`.
`resolve_knowledge_level` and `resolve_levels_for_entity` apply the same
order; `resolve_public_level(s)` unchanged (they enter at tier 6).
`resolve_default_rows` skips every fact whose `facet in
DESCRIPTIVE_FACETS` (NULL and `KNOWLEDGE_SECTION_FACETS` pass).

### C-10 — facet reads (`src/world_engine/facet_reads.py`, new)
Produced by: D   Consumed by: G, H, K
```python
@dataclass(frozen=True)
class FactRow:
    fact_id: str
    facet: str
    aspect: str | None
    content: str
    created_at: datetime

def facts_of(db, *, entity_id, facets: tuple[str, ...], aspect=None,
             notorious_at_location: str | None = None,
             include_creator_only: bool = False) -> list[FactRow]
def creator_only_fact_ids(db, fact_ids) -> set[str]
def known_facts_of(db, *, perceiver_id, entity_id, facets: tuple[str, ...],
                   aspect=None) -> list[FactRow]
def joined(rows: list[FactRow], sep: str = "\n") -> str | None
```
`facts_of`: facts with `entity_id` as participant and `facet in facets`
(and `aspect == normalize_aspect(aspect)` when given); with
`notorious_at_location`, only facts carrying a `location` default whose
`scope_id` equals it. **Creator-only facts are excluded by query
construction** unless `include_creator_only=True` (AMENDMENT-0091-01): a
fact is creator-only when a stored `knowledge` row on it belongs to one of
its own participants with `level = 'unaware'` and `is_secret = 1` — the
shape C-05 gives `creator_meta` and C-18 gives `character.secrets`.
`include_creator_only=True` is legal only in `lore_selectors.py` (the
creator's dossier). `creator_only_fact_ids`: the subset of `fact_ids` that
are creator-only, one query. Ordered by the order of `facets`, then `created_at`,
then `fact_id`. Empty list when none. `known_facts_of`: `facts_of`
(creator-only facts always excluded, no override) filtered to facts that `resolve_levels_for_entity(perceiver_id)` holds above
`unaware` (one batch call). `joined`: contents joined by `sep`, `None`
for an empty list. After J, `content` is rendered (C-13); before J it is
the raw text.

## Context

Play readers switch from columns to facts with constant behaviour (Q13a):
the same audience sees the same content. The one intended change is the
MJ's view of a co-present NPC's physique once the player has met them
(R-c).

## Scope IN

0. AMENDMENT-0091-01, **its own commit, before the reader commit**: in
   `src/world_engine/facet_reads.py`, implement C-10 as amended —
   `include_creator_only` on `facts_of` (default `False`, the creator-only
   exclusion built into the query), `creator_only_fact_ids`, and
   `known_facts_of` always excluding. Add R7 and R8 to
   `tooling/verify/checks/fact_facets.py` exactly as gate (e) states them.
1. `context.py::_npc_context_identity`: lines from
   `known_facts_of(perceiver_id=npc, entity_id=npc, facets=("physique",
   "histoire", "aversion", "description"))`, in that order, one line per
   fact. The signature gains `session`; update its single caller and the
   `traits.py:74` reader stays valid (same module, same name).
2. `context_describe.py::_npc_context_setting`: location text =
   `joined(facts_of(entity_id=location_id, facets=("description",)))`;
   `values` line = `joined(facts_of(entity_id=location_id,
   facets=("coutume",), aspect="values",
   notorious_at_location=location_id))`.
3. `context_describe.py::_npc_context_company`: each co-present's line =
   `joined(known_facts_of(perceiver_id=npc_id, entity_id=co_id,
   facets=("physique",)))` or else the `description` facts, else
   `"(pas de description)"`.
4. `context.py::_mj_context_location`: subculture dict from
   `facts_of(entity_id=location_id, facets=("coutume",),
   notorious_at_location=location_id)` filtered to aspects in
   `_SAFE_SUBCULTURE_KEYS`, keyed by aspect; description from facts.
5. `context_describe.py::_mj_context_co_presents`: `description` from facts;
   add `"physique"`: `joined(known_facts_of(perceiver_id=player_character_id,
   entity_id=co_id, facets=("physique",)))`, `None` when blindfolded;
   `format_mj_context` prints it after the description when present.
6. `tick_context.py`: every read of R-10 through `facts_of` (the tick is
   omniscient: no perceiver filter) — identity (physique, histoire,
   aversion, description), affiliations (doctrine, visee, tension,
   aversion of the faction), setting and location event (description,
   `coutume`/`values` notorious at the location), destinations
   (description), company (physique else description), faction identity
   (description, doctrine), faction posture (visee, tension, aversion).
   Labels and order unchanged.
7. `gathering.py::_request_partition`: physique facts else description
   facts, via `facts_of`.
8. `link_sheet.py::_npc_sheet`: the four lines from `facts_of`, labels
   unchanged.

## Scope OUT

- Knowledge filtering of any other facet (Q13a; injection ticket).
- Physique for entities cited in a scene (deferred, needs H2).
- Non-play readers (H). Render (J).

## Invariants to defend

- MJ perception boundary: only public co-presents; blindfold still removes
  visual data (physique included).
- Secrets excluded at query construction: `facts_of` itself drops
  creator-only facts (AMENDMENT-0091-01), so no reader of this brief —
  the omniscient tick included — can see the creator's note; NPC identity
  also reads through `known_facts_of`.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- Any reader in R-09/R-10/R-11 (play subset) not found where anchored.

ADAPT:
- A label string would change: keep the old label; report.

REPORT-ONLY:
- Line counts of `context.py`, `context_describe.py`, `tick_context.py`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] On a fixture NPC with a physique, histoire and a `creator_meta`
      fact, `assemble_npc_context` contains the first two and not the third.
- [ ] The same fixture: the creator note is absent from the tick identity
      block and from the link-agent sheet (the review's scratch fixture,
      `TICK_LEAK False SHEET_LEAK False`).
- [ ] `fact_facets.py` R7 and R8 pass.
- [ ] `assemble_mj_context` shows a co-present's physique only after a
      `rencontre` row exists for the player and that NPC.
- [ ] Green: `context_disclosure_floor.py`, `prompt_lean.py`,
      `world_tick.py`, `gathering_lifecycle.py`, `link_agent_strata.py`,
      `module_budget.py`, `function_length.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: note under the MJ perception entry that the
co-present physique follows the encounter registry (R-c).
