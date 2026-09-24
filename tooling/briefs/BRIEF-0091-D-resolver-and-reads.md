# BRIEF 0091-D — "resolver tiers and facet reads"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: A, C

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `knowledge_resolve.py:93-120` `_resolve_tiers` has the five-tier signature
  of R-07.
- `knowledge_resolve.py:278-304` `resolve_default_rows` builds a row for
  every fact above `unaware`.
- `encounters.py` exports `acquaintances` (C).
- `facets.py` exports `DESCRIPTIVE_FACETS` (A).

## Facts carried

### R-06 — `fact_participant` is unique per (fact, entity)
Opened: `src/world_engine/models/canon_knowledge.py:124-138` [M].
Finding: `idx_fact_participant_unique (fact_id, entity_id)` unique;
`idx_fact_participant_entity (entity_id)`; `role` free text, `position` int.
Consequence: "the entity's facts of facet X" is a join
`fact_participant.entity_id = X` — indexed. `role` never filters
(AMENDMENT-0087-1).

### R-07 — the resolver
Opened: `src/world_engine/knowledge_resolve.py:1-304` [M].
Finding: docstring `:1-33` states the five tiers (stored row; nearest
location default up the parent chain; highest faction default across active
memberships; world default; `fact.default_level`). `_resolve_tiers` (`:93-120`)
is the pure precedence shared by `resolve_knowledge_level` (`:123-175`) and
`resolve_levels_for_entity` (`:178-225`, one pass over every fact of the
world, returns only levels above `unaware`). `resolve_public_level(s)`
(`:228-275`) enter at the world tier. `resolve_default_rows` (`:278-304`)
builds transient `Knowledge` rows for **every** fact resolving above
`unaware`, copying `fact.content` into `subject` and `content`
(`:299-300`), `is_secret=False`.
Consequence: once descriptive facts carry defaults, every reader of
`resolve_default_rows` would receive them as speakable knowledge. D filters
by facet (C-09).

### R-08 — who consumes `resolve_default_rows`
Opened: `grep -rn "resolve_default_rows" src` [M] (pasted in gate (c)).
Finding: `context.py:384` (`_npc_context_speak`), `context.py:732`
(`_mj_context_player_knowledge`), `tick_context.py:252`
(`_tick_knowledge_block`).
Consequence: C-09's facet filter keeps all three unchanged in behaviour.

### R-26 — check fixtures that build facts
Opened: `tooling/verify/checks/fact_spine.py:1-140`,
`knowledge_resolution.py:78-146`, `known_reachability.py:178-240`,
`relation_orientation.py:150-160` [M]. FK enforcement: `db.py:126` [C].
Finding: `fact_spine.py` asserts (1) no participant on a typed fact, (2) no
knowledge with NULL `fact_id`, (3) level vocabulary, (4) AST: no
`db.add(Fact(...))` / `FactParticipant(...)` outside `writes/facts.py`;
fixture calls `create_fact` at `:138`. `knowledge_resolution.py:120`
calls `create_fact` and `:126-146` `create_fact_default` for the tier
fixture. `known_reachability.py:233` calls `create_fact_default`.
Consequence: A updates the two `create_fact` fixtures with a facet; D
extends `knowledge_resolution.py` with the new tiers; J updates
`relation_orientation.py:156`.

## Contracts

### C-01 — the facet registry (`src/world_engine/facets.py`, new)
Produced by: A   Consumed by: C, D, E, F (through C-12), G, H, I, J
```python
FAMILIES = ("identite", "interiorite", "collectif", "monde")
GRANULARITIES = ("bloc", "affirmation", "typed")
PRESETS = ("none", "world", "public_world", "location", "rencontre", "typed")

@dataclass(frozen=True)
class FacetSpec:
    name: str
    family: str          # in FAMILIES
    granularity: str     # in GRANULARITIES
    preset: str          # in PRESETS — default knowledge for NEW writing
    label: str           # French UI label
    description: str     # one French sentence: what belongs here
    aspects: tuple[str, ...] = ()   # known aspects, suggestion only

FACETS: dict[str, FacetSpec]        # insertion order = display order
DESCRIPTIVE_FACETS: frozenset[str]  # family in identite|interiorite|collectif
KNOWLEDGE_SECTION_FACETS: frozenset[str] = frozenset(
    {"information", "lien", "evenement", "loi"})
TYPED_FACET_BY_FK = {"relation_id": "lien", "event_id": "evenement",
                     "world_law_id": "loi"}

def facet_spec(name: str) -> FacetSpec        # ValueError if unknown
def normalize_aspect(raw: str | None) -> str | None  # strip+casefold; "" -> None
```
Verbatim table (name, family, granularity, preset, aspects):
| name | family | granularity | preset | aspects |
|---|---|---|---|---|
| appellation | identite | affirmation | location | () |
| statut | identite | affirmation | location | () |
| physique | identite | bloc | rencontre | () |
| tenue | identite | bloc | none | () |
| description | identite | bloc | public_world | () |
| reputation | identite | affirmation | location | () |
| histoire | interiorite | affirmation | none | () |
| personnalite | interiorite | affirmation | none | () |
| preference | interiorite | affirmation | none | () |
| aversion | interiorite | affirmation | none | () |
| doctrine | collectif | bloc | world | () |
| organisation | collectif | bloc | none | () |
| tension | collectif | affirmation | none | () |
| visee | collectif | affirmation | none | () |
| coutume | collectif | affirmation | location | ("values",) |
| information | monde | affirmation | none | () |
| lien | monde | typed | typed | () |
| evenement | monde | typed | typed | () |
| loi | monde | typed | typed | () |

Labels (verbatim): appellation "Appellations", statut "Statuts", physique
"Physique", tenue "Tenue", description "Description", reputation
"Réputation", histoire "Histoire", personnalite "Personnalité", preference
"Préférences", aversion "Aversions", doctrine "Doctrine", organisation
"Organisation", tension "Tensions", visee "Visées", coutume "Coutumes",
information "Informations", lien "Liens", evenement "Événements", loi "Lois".
Descriptions (verbatim): appellation "Un nom, surnom ou titre sous lequel
on désigne l'entité." ; statut "Une position sociale, une charge ou un rang
que l'entité occupe." ; physique "Ce que l'on voit durablement de l'entité :
corps, visage, allure." ; tenue "Ce que l'entité porte en ce moment et qui
peut changer." ; description "La présentation générale de l'entité." ;
reputation "Ce qui se dit de l'entité, vrai ou non." ; histoire "Un fait du
passé de l'entité." ; personnalite "Un trait de caractère de l'entité." ;
preference "Une chose que l'entité aime ou recherche." ; aversion "Une chose
que l'entité rejette, craint ou fuit." ; doctrine "Le credo affiché et les
valeurs revendiquées publiquement." ; organisation "La forme d'organisation
du groupe telle qu'on peut la connaître." ; tension "Une fracture, une
rivalité ou une faiblesse interne du groupe." ; visee "Un but que le groupe
poursuit réellement." ; coutume "Un usage, une valeur ou une règle de vie
propre au lieu." ; information "Une information détenue par quelqu'un." ;
lien "Un lien entre deux entités, porté par une relation." ; evenement "Un
événement du monde." ; loi "Une loi du monde." They are UI help and future
extractor vocabulary; no check reads them.
Preset semantics (C-05 applies them): `none` no default; `world` a `world`
default at `knows`; `public_world` a `world` default at `knows` only when
the subject entity `is_public`; `location` a `location` default at `knows`
on the subject itself when the subject is a location, otherwise none unless
the creator picks a location; `rencontre` a `rencontre` default at `knows`
with `scope_id` = the subject; `typed` never used by C-05.
Error cases: `facet_spec` of an unknown name raises `ValueError`.

### C-07 — the encounter writer (`src/world_engine/encounters.py`, new)
Produced by: C   Consumed by: D, the live sites
```python
def record_encounter(db, *, world_id, a_id, b_id, source, at=None,
                     source_ref=None) -> Rencontre | None
def record_encounters_among(db, *, world_id, entity_ids, source, at=None,
                            source_ref=None) -> int
def record_gathering_join(db, *, gathering_id, joiner_id) -> int
def acquaintances(db, entity_id) -> set[str]
def have_met(db, a_id, b_id) -> bool
```
`record_encounter`: `a_id == b_id` returns `None`; `source` outside
`ENCOUNTER_SOURCES` raises `ValueError`; an existing pair returns `None`
(idempotent, read guard before add); else adds and returns the row. `at`
defaults to now (UTC). `record_encounters_among`: every unordered pair of
the distinct ids, returns the number of new rows. `record_gathering_join`:
reads the gathering's `world_id`, pairs `joiner_id` with every other member
whose `left_at IS NULL`, source `gathering`, `source_ref` = the gathering
id; returns the number of new rows. `acquaintances`: every entity id paired
with `entity_id` in `rencontre`. The only module that adds a `Rencontre`.

### C-08 — `fact_default` scope `rencontre`
Produced by: A (schema), D (meaning)   Consumed by: C-05, I
`scope_type = 'rencontre'`, `scope_id` = the entity whose acquaintances
know the fact at `level`. Allowed by the rebuilt
`ck_fact_default_scope_type IN ('world','faction','location','rencontre')`.

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
             notorious_at_location: str | None = None) -> list[FactRow]
def known_facts_of(db, *, perceiver_id, entity_id, facets: tuple[str, ...],
                   aspect=None) -> list[FactRow]
def joined(rows: list[FactRow], sep: str = "\n") -> str | None
```
`facts_of`: facts with `entity_id` as participant and `facet in facets`
(and `aspect == normalize_aspect(aspect)` when given); with
`notorious_at_location`, only facts carrying a `location` default whose
`scope_id` equals it. Ordered by the order of `facets`, then `created_at`,
then `fact_id`. Empty list when none. `known_facts_of`: `facts_of`
filtered to facts that `resolve_levels_for_entity(perceiver_id)` holds above
`unaware` (one batch call). `joined`: contents joined by `sep`, `None`
for an empty list. After J, `content` is rendered (C-13); before J it is
the raw text.

## Context

Facts now carry facets and encounters are recorded. This brief teaches
the resolver the two new tiers and gives every later reader one call to read
an entity's facts.

## Scope IN

1. `knowledge_resolve.py`: `_resolve_tiers` gains keyword params
   `self_level: Optional[str]` and `rencontre_levels: list[str]` and applies
   C-09's order. `resolve_knowledge_level`: `self_level = "knows"` when a
   `FactParticipant(fact_id, entity_id)` exists and the fact's facet is in
   `DESCRIPTIVE_FACETS`; `rencontre_levels` from `FactDefault` rows of scope
   `rencontre` whose `scope_id` is in `acquaintances(db, entity_id)`.
   `resolve_levels_for_entity`: the same, from one query of the entity's
   participant fact ids, one `acquaintances` call and the defaults already
   fetched. Public resolvers pass `self_level=None, rencontre_levels=[]`.
   Rewrite the module docstring's tier list to C-09's seven tiers.
2. `resolve_default_rows`: skip facts whose facet is in
   `DESCRIPTIVE_FACETS`; add one docstring sentence citing Q13a.
3. New `src/world_engine/facet_reads.py` per C-10.
4. `tooling/verify/checks/knowledge_resolution.py`: extend the fixture with
   C-09's case table rows 1-9, each built through the real writers
   (`create_fact`, `attach_participants`, `create_fact_default`,
   `write_knowledge`, `record_encounter`) and asserted on both the single and
   the batch entry point.
5. `tooling/verify/checks/fact_facets.py`: add R6 (a descriptive fact with a
   `world` default is absent from `resolve_default_rows`; an `information`
   fact with the same default is present).

## Scope OUT

- Switching any reader to `facet_reads` (G, H).
- `content_raw` / render (J): `FactRow.content` is the raw text here.
- Writing any default (E, I).

## Invariants to defend

- A resolved default never carries `is_secret` (module docstring): unchanged.
- Resolution is a read: no `db.add` in `knowledge_resolve.py` or
  `facet_reads.py`.
- Secrets excluded at query construction: the speakable section's content is
  unchanged (Q13a).

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- A caller of `_resolve_tiers` exists outside `knowledge_resolve.py`.

ADAPT:
- `resolve_levels_for_entity` exceeds 80 lines: extract the default
  bucketing into a local helper; report.

REPORT-ONLY:
- The resolver's query count for one `resolve_levels_for_entity` call
  before and after.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `knowledge_resolution.py` passes with the nine C-09 rows.
- [ ] `fact_facets.py` R6 passes.
- [ ] `facts_of` on an entity with no facts returns `[]`; `joined([])`
      returns `None`.
- [ ] Green: `known_reachability.py`, `context_disclosure_floor.py`,
      `module_budget.py`, `function_length.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: amend the scoped-default entry with the
seven tiers (C-09) and Q18a.
