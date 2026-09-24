# BRIEF 0091-F — "sheet Facts editor and review surfaces"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: E

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `frontend/src/creation/Sheet.svelte` 774 lines; `:89-90` subculture
  imports; `:95` `PendingKnowledgeEditor`, `:104` `KnowledgeEditor`;
  `:482`, `:527-529` subculture draft PUT; `:671-672` `SubcultureEditor`.
- `generatePanel.svelte.js:44-72` `applyCharacterDraft`, `:84-110`
  `applyLocationDraft`, `:116-119` faction `setVal` lines.
- `Region.svelte:591-645`; `PjCreatePanel.svelte:50-51,96-97,120-121,180,184`.

## Facts carried

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

### R-16 — the sheet frontend
Opened: `frontend/src/creation/Sheet.svelte` (774 lines),
`SubcultureEditor.svelte` (93), `subcultureDraft.svelte.js` (14),
`generatePanel.svelte.js` (140), `sheetState.svelte.js` (141) [M].
Finding: base and type fields are read generically
(`Sheet.svelte:402-406`, `readFieldValue`); knowledge follows the
pending/existing pair `PendingKnowledgeEditor` (`:95`) / `KnowledgeEditor`
(`:104`); `SubcultureEditor` is imported at `:90`. `module_budget.py` R5
applies the 1000-line ceiling to `frontend/src/**/*.svelte|js`.
Consequence: F adds `FactsEditor.svelte` + `factsDraft.svelte.js` on the
same pending/existing pattern; `Sheet.svelte` gains only the mount.

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

The server writes facts; the sheet must now show and edit them, and the
generate panel must fill them instead of the retired fields.

## Scope IN

1. New `frontend/src/creation/factsDraft.svelte.js`: state
   `factsDraftState = $state({ facets: {} })` (C-05 payload shape),
   `resetFactsDraft()`, `factsDraftForCreate()`.
2. New `frontend/src/creation/FactsEditor.svelte`, props `{ isNew,
   entityId, entityType }`: loads `GET /api/facets` once; for an existing
   entity loads `GET /api/entities/{id}/facts`. One block per facet whose
   family fits the type (character: identite + interiorite; faction:
   identite + collectif; location: identite + `coutume`; other types:
   `description` only). A `bloc` facet: one textarea, saved with `POST` if
   empty else `PUT …/content`. An `affirmation` facet: one line per fact,
   edit (`PUT`), delete (`DELETE`), add (`POST`); `coutume` lines carry an
   aspect input with the registry aspects as datalist and a "caché" toggle
   (maps to `scope: {"scope_type": "none"}`). In create mode the same UI
   writes into `factsDraftState`. Labels come from the registry. Errors show
   the route's detail.
3. `Sheet.svelte`: mount `FactsEditor` where `SubcultureEditor` was
   (`:671-672`), for every type; send `facets: factsDraftForCreate()` in the
   create body; remove the subculture draft collection and PUT
   (`:482`, `:527-529`) and the two subculture imports; reset the facts draft
   where the subculture draft was reset.
4. Delete `SubcultureEditor.svelte` and `subcultureDraft.svelte.js`; update
   the comment in `registry.js:139-141` to name `FactsEditor`.
5. `generatePanel.svelte.js`: `applyCharacterDraft`, `applyLocationDraft`
   and the faction apply write `result.draft.facets` into `factsDraftState`
   instead of `setVal(... 'author-x-appearance' …)` and siblings; the notes
   for `subculture_hidden` read the hidden `coutume` entry.
6. Q20b surfaces keep one textarea per facet: `Region.svelte` binds
   `draft.facets.doctrine`, `.organisation`, `.aversion`, `.tension`,
   `.visee`, `.coutume` (rendered as "aspect : texte" lines, parsed back on
   commit) instead of the old keys; `PjCreatePanel.svelte` sends
   `facets: {description, physique, histoire}` (histoire one line per fact).
7. Rebuild and commit the bundle (`frontend_build_fresh.py`,
   `static_asset_freshness.py`).

## Scope OUT

- A mention picker (Q15b, deferred). Tokens (J).
- The NPC batch review screen beyond its field names (Q20b).
- Any server change (E).

## Invariants to defend

- Creator-only surface: nothing here renders in Play.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- `Sheet.svelte` would exceed 1000 lines.

ADAPT:
- A type whose family mapping is ambiguous (a runtime type): show
  `description` only; report the type.

REPORT-ONLY:
- New line counts of `Sheet.svelte` and `generatePanel.svelte.js`.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Creating an NPC with two aversions from the sheet yields two facts.
- [ ] Editing a physique on an existing NPC saves in place; adding a second
      is refused with the route's message.
- [ ] Generating a location fills the Coutumes block; accepting creates the
      facts.
- [ ] Green: `frontend_build_fresh.py`, `static_asset_freshness.py`,
      `module_budget.py`, `page_contract.py`, `creation_island.py`,
      `corpus_gate.py`.

## Docs to update

This step needs no doc update beyond the component header comments.
