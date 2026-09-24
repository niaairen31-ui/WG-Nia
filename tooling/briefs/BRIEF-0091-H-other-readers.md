# BRIEF 0091-H — "remaining readers and the Lore dossier"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: D

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- R-11's non-play lines, as they stand after E (AMENDMENT-0091-02 accepts
  the drift): `creator.py:80` (`faction.goals`), `generate_agenda` at `:284`
  with the owner block at `:312-318`; `crud/goals.py:260`, `:305-306`;
  `npc_group_author.py:216`, `:313`; `room_batch_author.py:100-113`, `:133`;
  `play_physical.py:724` (description) and `:725-734` (subculture);
  `observation_runner.py:123`; `crud/relations.py:293`;
  `lore_candidates.py:57`; `crud/entities.py:237` (`"description"` in
  `_entity_dict`), `:257-264` (`_location_subculture_rows`), `:507`, `:719`,
  `:812` (`subculture_rows`); `crud/entity_geometry.py:28`, `:113`, `:143`;
  `crud/__init__.py` re-export of `_location_subculture_rows`.
- A shift of a few lines with identical content is drift, not a moved
  anchor; a different content at the anchor is still a STOP.
- `lore_selectors.py:43-68` `world_factions`; `:71-99` `_identity_rows`;
  `:187-199` `entity_dossier`; `lore_render.py:87-96` `_SECTION_FORMATTERS`;
  `Lore.svelte:22-29` `SECTION_LABEL`.

## Facts carried

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
**Corrected by AMENDMENT-0091-02**: the reader list below was a negative
claim with no pasted enumeration; it missed `cockpit/play_physical.py:725-734`,
`cockpit/crud/entity_geometry.py:28,113,143`, the import-only references and
`scripts/seed_pilot.py:246-269,3064`. The complete enumeration is in the
amendment and in gate (c).
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

### R-22 — the Lore surface and its gates
Opened: `tooling/verify/checks/lore_isolation.py:1-60`;
`src/world_engine/lore_render.py:27-113`; `lore_selectors.py:187-265`;
`tooling/verify/checks/lore_selectors.py:5-26`;
`frontend/src/lore/Lore.svelte:1-30`; `cockpit/app.py:130` [M].
Finding: `lore_isolation.py` R1-R16 name only `lore_selectors.py`,
`lore_query.py`, `lore_render.py`, `lore_plan.py`, `lore_prompt.py` and
`cockpit/routes/lore.py` (R6: no `chat(`, no `select(`). `lore_render`'s
`_SECTION_FORMATTERS` (`:87-96`) is the closed section vocabulary; an
unknown section raises (`:99-113`). `entity_dossier` (`:187-199`) returns
identity, relations, knowledge, memberships, goals. `SELECTORS` (`:251`),
`_SELECTOR_LOOKUPS` (`:253-265`); `checks/lore_selectors.py` R6 requires
every `context_sections` string to be an emitted `"section"` literal.
`Lore.svelte` declares itself read-only (`:1-8`) and labels sections in
`SECTION_LABEL` (`:22-29`); 179 lines; `lore.svelte.js` 88 lines.
The Lore router is mounted at `cockpit/app.py:130`.
Consequence: H adds a `facets` section (formatter + label). K adds a
separate route module and panel; R1-R16 stay untouched; a new rule forbids
imports between the panel's modules and the consultation pipeline.

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

Every reader outside play moves to facts, and the Lore dossier gains a
`facets` section so the creator sees an entity's lore by facet — the gap
6.3 of the handover named.

## Scope IN

1. Each R-11 non-play reader reads through `facts_of` with the same text it
   printed before: faction goals -> `visee`; philosophy -> `doctrine`;
   backstory -> `histoire`; description -> `description`; room batch
   subculture -> `coutume` notorious at the anchor, keyed by aspect.
   `observation_runner.check_run_readiness` requires at least one
   `description` fact.
2. `crud/entities.py`: `_entity_dict` drops `"description"`; remove
   `_location_subculture_rows` and its three `subculture_rows` payload
   lines; `crud/entity_geometry.py`: remove the import (`:28`) and the two
   `subculture_rows` lines (`:113`, `:143`); `crud/__init__.py`: remove the
   `_location_subculture_rows` re-export (AMENDMENT-0091-02).
2b. `cockpit/play_physical.py::_build_establishment_narration` (`:725-734`):
   the subculture dict = `{row.aspect: row.content for row in
   facts_of(db, entity_id=location_id, facets=("coutume",),
   notorious_at_location=location_id) if row.aspect in
   _SAFE_SUBCULTURE_KEYS and row.content}` — the same read as G's item 4
   for `_mj_context_location`. A hidden custom has no `location` default and
   is therefore never returned (the hidden-subculture trap holds by query
   construction). Remove the `LocationSubculture` import from this file.
3. `lore_selectors.py`: `_identity_rows` keeps name, type, status,
   is_public, internal_name and the character mechanics
   (`character_type`, `current_location_id`, `vital_status`,
   `physical_tier`) and drops the prose keys; new `_facet_rows(entity_id,
   world_id, db)` returns one row per `facts_of(entity_id=…,
   facets=tuple(DESCRIPTIVE_FACETS in registry order))` with keys
   `{"section": "facets", "facet", "label", "aspect", "content",
   "secret"}`, read with `include_creator_only=True` (the only legal call
   site, AMENDMENT-0091-01), where `secret` is `fact_id in
   creator_only_fact_ids(db, <ids>)`; `entity_dossier` appends it
   after identity. `world_factions` keeps its keys but fills `description`,
   `philosophy`, `internal_structure`, `internal_tensions` from
   `description`, `doctrine`, `organisation`, `tension` facts (joined).
4. `lore_render.py`: `_format_facets(row)` = `"{label}{ (aspect)} :
   {content}{ [secret]}"`, registered in `_SECTION_FORMATTERS`; update the
   vocabulary comment. `_format_identity` prints name and type only.
5. `Lore.svelte` `SECTION_LABEL`: `facets: 'Faits'`. Rebuild the bundle.

## Scope OUT

- Knowledge-filtered views in Lore (creator surface, sees all).
- The names panel (K). Render (J).

## Invariants to defend

- Secrets excluded at query construction: every reader of item 1 uses
  `facts_of` without `include_creator_only`, so the creator's note never
  reaches the agenda or goal-backfill prompts (AMENDMENT-0091-01).
- `lore_isolation.py` R1: no write in `lore_selectors.py`.
- Secrets: the dossier marks the `creator_meta` fact secret; nothing reaches
  Play.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- A reader of a moving column or of `location_subculture` exists outside
  R-09, R-10, R-11 and the subculture enumeration of gate (c) as amended by
  AMENDMENT-0091-02.

ADAPT:
- A route's JSON consumer in the frontend reads `description` from
  `_entity_dict`: point it at `GET /api/entities/{id}/facts`; report the
  file.

REPORT-ONLY:
- Any frontend consumer of `subculture_rows` found.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] The dossier of a fixture NPC lists its facts under "Faits", the
      creator note tagged secret.
- [ ] A fixture location with a visible `values` custom and a hidden one:
      the establishment narration context carries the first, never the
      second.
- [ ] `generate_agenda` and `_backfill_one_npc` prompts for that NPC do not
      contain the creator note.
- [ ] `fact_facets.py` R7 passes (`include_creator_only=True` only in
      `lore_selectors.py`).
- [ ] Green: `lore_isolation.py`, `lore_selectors.py`, `observation_runner.py`,
      `json_ui_boundary.py`, `frontend_build_fresh.py`,
      `static_asset_freshness.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: Lore dossier sections now include `facets`.
