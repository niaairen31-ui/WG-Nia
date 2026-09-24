# BRIEF 0091-E — "fact writers, facts routes, generators"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: A, B

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `cockpit/crud/entities.py:116-122` `ENTITY_BASE_FIELDS` includes
  `description`; `:139-142` character `appearance, backstory, aversion,
  secrets`; `:178-185` faction `internal_structure, philosophy, aversion,
  internal_tensions`.
- `cockpit/crud/entities.py:545-560` `_create_entity_core`; `:739-816`
  `update_entity` (78 lines); `:857-878` `set_location_subculture`.
- `cockpit/routes/creator.py:655-670` builds `Entity(description=…)` and
  `Character(appearance=…, backstory=…)`.
- `entity_author.py:45-93` `_TYPE_FIELDS`; `:432-505` the three drafts.
- `cockpit/routes/npc_agent.py:213-217`; `cockpit/routes/regions.py:160-170`,
  `:205-223`; `npc_group_author.py:389`.
- `cockpit/crud/_router.py:12` `APIRouter(prefix="/api", tags=["author-crud"])`.

## Facts carried

### R-04 — the fact chokepoint
Opened: `src/world_engine/writes/facts.py:1-126` [M].
Finding: `create_fact(db, *, world_id, content, created_by,
default_level="unaware", relation_id=None, event_id=None,
world_law_id=None) -> Fact` (`:39-61`) adds the row. `update_typed_fact_content(db,
*, fact, content, changed_by)` (`:64-77`) appends `{"content",
"changed_by", "at"}` to `change_history` then overwrites. `attach_participants(db,
*, fact, entity_ids, role=None)` (`:80-106`) raises `ValueError` on a typed
fact; `position` from list order. `create_fact_default(db, *, world_id,
fact_id, scope_type, scope_id, level, created_by)` (`:109-126`), no
duplicate check. There is no content-update path for a free fact and no
delete path for a free fact.
Policy: `canon_write_policy.txt:137` `create_fact fact`, `:138`
`attach_participants fact_participant`, `:146` `create_fact_default
fact_default`, `:150` `update_typed_fact_content fact`.
Consequence: A amends `create_fact` (C-02) and adds `update_fact_content`
and `delete_free_fact` (C-03, C-04), each declared in the policy.

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

### R-13 — the prose columns, where declared
Opened: `models/canon.py:117-142` (`Entity`), `:143-190` (`Character`),
`models/canon_faction.py:22-60` (`Faction`) [M].
Finding: `entity.description` (nullable) and `entity.is_public`;
`character.appearance`, `.backstory`, `.aversion`, `.secrets` (nullable);
`faction.internal_structure`, `.philosophy`, `.internal_tensions`,
`.scope`, `.goals`, `.aversion` (nullable). `faction.goals` carries a
`DORMANT` comment while `tick_context.py:303,637`, `creator.py:78`,
`crud/goals.py:260` and `npc_group_author.py:313` read it (trap: a
docstring is not the code).
Consequence: `faction.scope` stays (mechanic). The other twelve move.

### R-14 — creator write paths into those columns
Opened: `tooling/verify/canon_write_policy.txt`; `cockpit/crud/entities.py`;
`cockpit/routes/creator.py:640-690` [M].
Finding: policy `:89` `creator.py::create_player_character entity character
skill`; `:102` `crud/entities.py::_create_static_entity_core entity
character location faction item`; `:104` `crud/entities.py::update_entity
entity character location faction item`. `ENTITY_BASE_FIELDS`
(`crud/entities.py:116-122`) includes `description`; `_apply_base_fields`
(`:350-355`) `setattr`s each base field. Type field specs
(`:125-210`): character `appearance`, `backstory`, `aversion`, `secrets`
(`:139-142`); faction `internal_structure`, `philosophy`, `aversion`,
`internal_tensions` (`:178-185`). `_build_extension_kwargs` (`:357-375`)
keeps only spec fields and silently drops any other key.
`create_player_character` builds `Entity(description=…)` and
`Character(appearance=…, backstory=…)` directly (`creator.py:655-670`).
Consequence: E moves these fields out of the specs and into a `facets`
payload handled by C-05.

### R-15 — generator paths
Opened: `entity_author.py:45-93`, `:432-505`; `cockpit/routes/npc_agent.py:199-230`;
`cockpit/routes/regions.py:135-225`; `npc_group_author.py:389`;
`frontend/src/creation/generatePanel.svelte.js:44-110` [M].
Finding: `_TYPE_FIELDS` (`entity_author.py:45-93`) is the per-type JSON
guidance injected into the `entity_generation` prompt as `{type_fields}`;
drafts split `public` / `secret` (`:432-505`). Every server-side commit
calls `_crud._create_entity_core(EntityWriteBody(...))`: `npc_agent.py:226`
(maps `creator_meta` to `secrets` as JSON text, `:217`), `regions.py:170`
(factions), `regions.py:223` (locations). `regions.py:207-219` passes a
`subculture` key (with a `hidden` entry from `secret.subculture_hidden`)
into `ext_data`; the location field spec has no `subculture` field, so
`_build_extension_kwargs` drops it — **region-generated subculture is never
persisted today**. The frontend applies drafts into legacy DOM ids
(`generatePanel.svelte.js:44-72`, `setVal(legacyDoc, 'author-x-appearance', …)`)
and subculture rows into `subcultureDraftState` (`:84-110`, the hidden text
as key `hidden`, `is_hidden: true`).
Consequence: E carries generator output as `facets` (C-11); the region
subculture defect is fixed as a side effect and reported.

### R-29 — files and functions pinned by existing gates
Opened: `src/world_engine/traits.py:74`; `tooling/verify/checks/prompt_lean.py:8,28,77`;
`stream_session_readonly.py:12-14`; `json_ui_boundary.py:33`;
`known_reachability.py:315-330`; AST spans of the four budget files [M].
Finding: `traits.py:74` names `reader_callable="world_engine.context:_npc_context_identity"`.
`prompt_lean.py` rule 3 requires `_SAFE_SUBCULTURE_KEYS == ("values",)` in
`context.py`. `stream_session_readonly.py` documents `_join_gathering`
(`cockpit/play.py:901-926`) keeping its signature and its call sites
(`play.py:400`, `routes/scene.py:316`, `routes/play.py:239`).
`json_ui_boundary.py:33` reads the field registry from
`cockpit/crud/entities.py`. `known_reachability.py` lists
`cockpit/crud/entities.py` among modules spelling `"connects_to"`
(`_location_doors_rows`, `:302-347`). Spans: `context.py`
`_npc_context_setting` 327-356, `_npc_context_company` 449-475,
`_mj_context_co_presents` 770-797 (none uses a `context.py` top-level name);
`link_author.py` `_location_chain_names` 147-161 (sole caller `_npc_sheet`),
`_npc_sheet` 164-184 (sole callers `:235-236`); `cockpit/play.py`
`_propose_engine_discovery` 964-997 (uses only `ProposedMutation` among
module names; imported by `play_physical.py:53`); `cockpit/crud/entities.py`
`_create_entity_core` 545-560, `_create_static_entity_core` 563-634 (72
lines), `update_entity` 739-816 (78 lines).
`src/world_engine/schema_reconcile.py:30` defines `static_table_names()`.
Consequence: B moves only the unpinned spans above; `crud/entities.py`
moves nothing and its two long functions gain one-line calls only.

### R-30 — generator review surfaces
Opened: `frontend/src/creation/Region.svelte:119,591-645`;
`frontend/src/creation/npcAgent.svelte.js:303`;
`src/world_engine/npc_group_author.py:389-405`;
`frontend/src/creation/PjCreatePanel.svelte:50-51,96-97,120-121,129,180,184`;
`src/world_engine/cockpit/routes/npc_agent.py:213-217` [M].
Finding: `Region.svelte` binds `pub.subculture` (`:591`),
`sec.subculture_hidden` (`:603`), `pub.philosophy` (`:618`),
`pub.internal_structure` (`:620`), `pub.aversion` (`:641`),
`sec.internal_tensions` (`:645`). The NPC batch review patches one field at
a time (`npcAgent.svelte.js:303`, `{payload_patch: {[field]: value}}`),
validated by `_coerce_npc_patch_value` against `_NPC_PLAIN_STR_FIELDS =
("description", "appearance", "backstory", "aversion")`.
`PjCreatePanel.svelte` holds and posts `appearance` / `backstory`.
`npc_agent.py:217` stores `creator_meta` as JSON text in `secrets`.
Consequence (Q20b): the generator emits facet keys; these three review
surfaces keep one text field per facet, one line per affirmation; the
server splits by line (C-05). Only the sheet's generate panel edits facets
as lists (F).

### R-31 — the crud router and write timestamps
Opened: `src/world_engine/cockpit/crud/_router.py:12`;
`cockpit/crud/__init__.py:8-16,62-97`; `models/ephemeral.py:84-160` [M].
Finding: every `crud/<domain>.py` decorates the single
`router = APIRouter(prefix="/api", tags=["author-crud"])`; `crud/__init__.py`
imports each domain module (a re-export surface, no logic).
`conversation.started_at`, `visit.entered_at`, `gathering_member.joined_at`
/ `left_at`, `relation.created_at`, `npc_schedule.created_at` are the
timestamps available to the backfill.
Consequence: C-12 lives in a new `crud/facets.py` imported by
`crud/__init__.py`; C's backfill orders candidate pairs by those columns.

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

### C-02 — `create_fact`, amended
Produced by: A   Consumed by: C-05, `writes/knowledge.py`, `writes/relations.py`
```python
def create_fact(db, *, world_id, content, created_by, facet, aspect=None,
                default_level="unaware", relation_id=None, event_id=None,
                world_law_id=None) -> Fact
```
`facet` is keyword-only with **no default**. Raises `ValueError` when:
`facet` is `None` ("NULL facet is reserved for facts predating
TICKET-0091"); `facet` not in `FACETS`; a typed FK is set and `facet` is not
`TYPED_FACET_BY_FK[that FK]`; no typed FK is set and `facet` has granularity
`typed`. `aspect` is stored through `normalize_aspect`. Everything else as
R-04.

### C-03 — `update_fact_content` (new, `writes/facts.py`)
Produced by: A   Consumed by: C-05, C-16
```python
def update_fact_content(db, *, fact, content, changed_by) -> Fact
```
Appends `{"content": <previous>, "changed_by": changed_by, "at": <iso UTC>}`
to `change_history` (same shape as `update_typed_fact_content`), flags it
modified, overwrites the content. Works on free and typed facts.
Declared in the policy (`fact`).

### C-04 — `delete_free_fact` (new, `writes/facts.py`)
Produced by: A   Consumed by: C-05
```python
def delete_free_fact(db, *, fact) -> None
```
Raises `ValueError` if any typed FK is set. Deletes, in this order, the
fact's `knowledge` rows, `fact_default` rows, `fact_participant` rows,
then the fact (FKs on; children before parent). Declared in the policy
(`fact fact_participant fact_default knowledge`), creator-CRUD only.

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

### C-11 — the entity write payload, amended (`cockpit/crud`)
Produced by: E   Consumed by: F, generators
`EntityWriteBody` gains `facets: dict | None = None` (shape of C-05's
`write_entity_facets`) and, from J, `mentions: list[dict] | None = None`
(`[{"name": str, "category": "place"|"person"|"faction"}]`). The
descriptive fields leave `ENTITY_BASE_FIELDS` (`description`) and the
type specs (`appearance`, `backstory`, `aversion`, `secrets`,
`internal_structure`, `philosophy`, `internal_tensions`). Create cores call
`write_entity_facets` after the entity row is flushed, in the same
transaction. `update_entity` with a non-empty `facets` returns 422 with
detail `"descriptive lore is edited through /api/entities/{id}/facts"`.
The PC-creation body of `create_player_character` loses `description`,
`appearance` and `backstory` and gains the same `facets` field.

### C-12 — facts CRUD routes (`src/world_engine/cockpit/crud/facets.py`, new)
Produced by: E   Consumed by: F
- `GET /api/facets` -> `{"facets": [{"name", "label", "family",
  "granularity", "preset", "aspects"}]}` (descriptive facets only, registry
  order).
- `GET /api/entities/{entity_id}/facts` -> `{"entity_id", "facts":
  [{"fact_id", "facet", "aspect", "content", "scopes": [{"scope_type",
  "scope_id", "level"}], "created_at"}]}`; 404 on unknown entity.
- `POST /api/entities/{entity_id}/facts` body `{"facet", "content",
  "aspect"?: str, "scope"?: {"scope_type", "scope_id"?}}` -> the created
  fact as one element of the GET list; 422 on `ValueError`.
- `PUT /api/facts/{fact_id}/content` body `{"content"}` -> the updated fact;
  404 unknown; 422 non-descriptive.
- `DELETE /api/facts/{fact_id}` -> `{"ok": true}`; 404; 422
  non-descriptive.
Each route commits once. Declared in the policy.

## Context

Every descriptive write now becomes facts. Creation cores, the PC route and
every generator commit go through one writer module; the sheet gets routes
to list, add, edit and remove facts. Readers are untouched (G, H).

## Scope IN

1. New `src/world_engine/writes/facets.py` per C-05 (all five functions and
   `ScopeChoice`); re-export from `writes/__init__.py` next to the fact
   writers.
2. New `src/world_engine/cockpit/crud/facets.py` per C-12, decorating the
   shared `router` from `._router`; import it in `cockpit/crud/__init__.py`.
3. `cockpit/crud/entities.py`: remove `description` from
   `ENTITY_BASE_FIELDS`; remove the seven fields of the anchors from the
   character and faction specs; `EntityWriteBody` gains `facets: dict |
   None = None`; `_create_entity_core` flushes, then calls
   `write_entity_facets(db, entity_id=entity.id, facets=body.facets or {},
   created_by="creator_crud")`; `update_entity` calls a one-line
   `_refuse_facets(body)` first (422 per C-11); remove
   `set_location_subculture`, `LocationSubcultureBody` and the unused
   `write_location_subculture` import (`:80`).
4. `cockpit/crud/agendas.py:71`: remove the unused `write_location_subculture`
   import.
5. `cockpit/routes/creator.py::create_player_character`: PC body per C-11;
   the entity is created without description; after flush,
   `write_entity_facets(db, entity_id=entity.id, facets=body.facets or {},
   created_by="creator_crud")`.
6. `entity_author.py` `_TYPE_FIELDS`, verbatim:
   - character: `'public.name (string) ; public.description (string) ; '
     'public.physique (string) ; public.histoire (tableau de chaînes — un
     fait du passé par entrée) ; public.aversion (tableau de chaînes — ce que
     ce personnage rejette ou fuit : un concept, une catégorie ou un
     phénomène, PAS une entité nommée) ; '` followed by the existing
     `physical_tier`, `faction_name` and `secret.*` text unchanged.
   - location: `public.subculture` becomes `'public.coutume (tableau
     d\'objets {"aspect","content"} — aspect parmi ' + ', '.join(
     FACETS["coutume"].aspects) + ' ; n\'invente pas d\'autre aspect)'`;
     the rest unchanged.
   - faction: `public.philosophy` -> `public.doctrine`,
     `public.internal_structure` -> `public.organisation`, `public.aversion`
     -> `(tableau de chaînes)`, `secret.internal_tensions` ->
     `secret.tension (tableau de chaînes)`, `secret.goals` -> `secret.visee
     (tableau de chaînes)`; every explanatory clause kept.
   The three draft builders put these values under `draft["facets"]` (C-05
   shape; `creator_meta` goes there too for characters; a location's
   `subculture_hidden` becomes one `coutume` entry with `aspect: None,
   hidden: True`). The `_SAFE_SUBCULTURE_KEYS` import from `.context` is
   replaced by `FACETS["coutume"].aspects`.
7. Server commits pass `facets=draft["facets"]` in `EntityWriteBody`:
   `npc_agent.py::_commit_npc_row` (drop `appearance/backstory/aversion/
   secrets` from `ext_data`), `regions.py::_commit_region_factions`,
   `regions.py::_commit_region_locations` (drop the `subculture` key).
8. `npc_group_author.py:389`: `_NPC_PLAIN_STR_FIELDS = ("description",
   "physique", "histoire", "aversion")` — Q20b: one string per facet, one
   line per affirmation; the patch writes into `draft["facets"]`.
9. `tooling/verify/checks/fact_facets.py`: add R5 (bloc guard) and a
   fixture for `write_entity_facets` (line split, `coutume` hidden,
   `creator_meta` secret row).

## Scope OUT

- Any reader change (G, H); `_entity_dict`'s `description` (H).
- The frontend (F); the prompt template text stored in the DB.
- Tokens and `mentions` (J).
- Dropping `write_location_subculture` or its policy line (I).

## Invariants to defend

- Canon writes only through the chokepoints: `writes/facets.py` and
  `crud/facets.py` never `db.add` a canon row themselves.
- Secrets excluded structurally: `creator_meta` never becomes knowable by
  its own entity (`unaware`, `is_secret`).
- History is sacred: edits go through C-03.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- A generator commit path exists that does not call `_create_entity_core`.
- `update_entity` or `_create_static_entity_core` would exceed 80 lines.

ADAPT:
- The seeded `entity_generation` template (search `src/` and `scripts/` for
  its seed) names the old keys: do not edit it; report the file and line.

REPORT-ONLY:
- Any other `_create_entity_core` caller found that passes descriptive
  keys in `extension`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `POST /api/entities` with `facets={"aversion": "le soleil\nla
      mer"}` creates two `aversion` facts with the entity as participant.
- [ ] A second `physique` via `POST /api/entities/{id}/facts` returns 422.
- [ ] `PUT /api/facts/{id}/content` appends history.
- [ ] A generated character committed through the NPC batch has its
      `creator_meta` as a `histoire` fact plus an `unaware`, secret
      knowledge row for itself.
- [ ] A region commit writes its locations' customs as `coutume` facts.
- [ ] Green: `fact_facets.py`, `single_canon_write.py`,
      `json_ui_boundary.py`, `function_length.py`, `module_budget.py`,
      `link_agent_strata.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: amend "Author CRUD" — descriptive lore is
written through `writes/facets.py` and the facts routes.
