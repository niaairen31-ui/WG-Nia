# BRIEF 0091-A — "schema v2.05 — facets, encounters table, fact chokepoint"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `models/canon_knowledge.py:86-117` — `Fact` has no `facet`, no `aspect`.
- `models/canon_knowledge.py` `FactDefault` — `ck_fact_default_scope_type`
  reads `scope_type IN ('world','faction','location')`.
- `writes/facts.py:39-61` — `create_fact(db, *, world_id, content,
  created_by, default_level="unaware", relation_id=None, event_id=None,
  world_law_id=None)`.
- `grep -rn "create_fact(" src scripts tooling/verify/checks` — exactly the
  five callers of R-05 (plus the definition).
- `schema_version.py:15` — `EXPECTED_STATIC_SCHEMA_VERSION = "v2.04"`;
  `world-engine-schema.md:3` — `Current schema version: v2.04`.
- `canon_write_policy.txt:137,138,146,150` — the four `writes/facts.py`
  sites.

## Facts carried

### R-01 — `fact` declares no facet and no aspect
Opened: `src/world_engine/models/canon_knowledge.py:86-117` [M].
Finding: columns `id, world_id, relation_id, event_id, world_law_id,
content, default_level, created_at, created_by, change_history`. CHECKs
`ck_fact_spine_exclusive` (at most one typed FK) and `ck_fact_default_level`.
Indexes `idx_fact_world`, `idx_fact_relation`, `idx_fact_event`,
`idx_fact_world_law`. No facet, no aspect.
Consequence: v2.05 adds `facet TEXT NULL` and `aspect TEXT NULL` with
`ALTER TABLE ... ADD COLUMN` (no CHECK — Q2a). NULL facet means "predates
TICKET-0091" and is never written again.

### R-02 — `fact_default` closes its scope set with a CHECK
Opened: `src/world_engine/models/canon_knowledge.py:140-180` [M].
Finding: `ck_fact_default_scope_type`: `scope_type IN
('world','faction','location')`; `ck_fact_default_scope_shape`: world has
NULL `scope_id`, the others NOT NULL; `ck_fact_default_level` (six levels);
`idx_fact_default_unique (fact_id, scope_type, scope_id)` unique;
`idx_fact_default_fact`. Columns `id, world_id, fact_id, scope_type,
scope_id, level, created_by` (+ `created_at` per the model tail).
Consequence: adding `rencontre` requires a table rebuild (Q3a). The shape
CHECK already accepts it (`scope_type <> 'world' AND scope_id IS NOT NULL`).

### R-03 — migration precedents, and no rebuild precedent
Opened: `scripts/migrate_v2_00_connects_to_facts.py` …
`migrate_v2_04_oriented_relations.py`; `grep -n "_rebuild\|RENAME"
scripts/migrate_v2_0*.py` [M].
Finding: the grep returns zero lines (pasted in gate (c)). Precedents:
`ALTER TABLE ... ADD COLUMN` (v2.01 `:79`), `ALTER TABLE ... DROP COLUMN`
(v2.03 `:90`), `CREATE INDEX` in one transaction with idempotent guards,
S-numbered steps, report, post-checks and `_converge_schema_meta()` (v2.04
docstring `:1-40`). Version constant `src/world_engine/schema_version.py:15`
`EXPECTED_STATIC_SCHEMA_VERSION = "v2.04"`; doc line
`world-engine-schema.md:3`; changelog newest-first
(`world-engine-schema-changelog.md:16`); agreement enforced by
`checks/schema_version_agreement.py` (changelog `:12-16`).
Consequence: the `fact_default` rebuild in v2.05 is the first of the series.
It follows SQLite's documented 12-step shape (new table, copy, drop, rename,
re-create indexes) inside the script's single transaction, with FKs on
(R-26).

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

### R-05 — every `create_fact` caller
Opened: `grep -rn "create_fact(" src scripts tooling/verify/checks` [M]
(pasted in gate (c)).
Finding: `src/world_engine/writes/knowledge.py:193` (create path of
`_build_knowledge_update`; content = subject label),
`src/world_engine/writes/relations.py:144` (`_birth_typed_fact`),
`scripts/seed_pilot.py:117`, `tooling/verify/checks/fact_spine.py:138`,
`tooling/verify/checks/knowledge_resolution.py:120`. No producer of an
`event_id` or `world_law_id` fact exists.
Consequence: making `facet` required (C-02) forces all five to pass one:
`information` (knowledge path, seed), `lien` (relations), check fixtures
updated in A.

### R-06 — `fact_participant` is unique per (fact, entity)
Opened: `src/world_engine/models/canon_knowledge.py:124-138` [M].
Finding: `idx_fact_participant_unique (fact_id, entity_id)` unique;
`idx_fact_participant_entity (entity_id)`; `role` free text, `position` int.
Consequence: "the entity's facts of facet X" is a join
`fact_participant.entity_id = X` — indexed. `role` never filters
(AMENDMENT-0087-1).

### R-20 — non-canon bookkeeping posture
Opened: `tooling/verify/canon_write_policy.txt:152-159`;
`models/ephemeral.py:136-141`;
`tooling/verify/checks/single_canon_write.py:1-30` [M].
Finding: `single_canon_write.py` gates only tables in `[CANON_TABLES]`;
`visit`, `gathering`, `conversation` and the observation telemetry tables
are deliberately outside it, each with its own chokepoint and, for
observation, its own check (`observation_socle.py`).
Consequence: `rencontre` (derived from play traces and authored state,
never edited by hand) and `unresolved_mention` (a worklist) are non-canon.
Each gets one writer module and a dedicated check (C-06, C-15).

### R-25 — no JSON column without an allow-list entry
Opened: `tooling/verify/checks/json_ui_boundary.py:1-25` [M].
Finding: volet c fails any `Column(JSON` not named in
`JSON_COLUMN_ALLOWLIST`.
Consequence: `rencontre` and `unresolved_mention` declare no JSON column;
candidates are recomputed at read time (C-16).

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

### C-06 — the `rencontre` table (`models/ephemeral.py`)
Produced by: A   Consumed by: C, D
```python
class Rencontre(SQLModel, table=True):
    __tablename__ = "rencontre"
    # idx_rencontre_pair UNIQUE (entity_lo_id, entity_hi_id)
    # idx_rencontre_hi (entity_hi_id)
    id: str (uuid pk); world_id: str FK world NOT NULL
    entity_lo_id: str FK entity NOT NULL   # min(a, b) as strings
    entity_hi_id: str FK entity NOT NULL   # max(a, b)
    first_at: datetime NOT NULL
    source: str NOT NULL     # in ENCOUNTER_SOURCES
    source_ref: str | None   # id of the visit/gathering/conversation/relation row
ENCOUNTER_SOURCES = ("visit", "gathering", "conversation", "schedule", "relation")
```
One row per unordered pair; the earliest known encounter wins; never
updated, never deleted. No JSON column.

### C-08 — `fact_default` scope `rencontre`
Produced by: A (schema), D (meaning)   Consumed by: C-05, I
`scope_type = 'rencontre'`, `scope_id` = the entity whose acquaintances
know the fact at `level`. Allowed by the rebuilt
`ck_fact_default_scope_type IN ('world','faction','location','rencontre')`.

### C-15 — `unresolved_mention` (`models/pipeline.py`) and its writer
Produced by: A (table), J (writer `writes/mentions.py`)   Consumed by: K
```python
class UnresolvedMention(SQLModel, table=True):
    __tablename__ = "unresolved_mention"
    # idx_unresolved_mention_world_open (world_id, resolved_at)
    id: str (uuid pk); world_id: str FK world NOT NULL
    fact_id: str | None FK fact
    knowledge_id: str | None FK knowledge
    surface: str NOT NULL
    reason: str NOT NULL          # "ambigu" | "inconnu"
    category: str | None
    created_at: datetime NOT NULL
    resolved_at: datetime | None
    resolved_entity_id: str | None FK entity   # NULL + resolved_at = dismissed
```
Exactly one of `fact_id`, `knowledge_id` is set (guarded in the writer).
No JSON column. Writer functions: `record_unresolved(db, *, world_id,
fact_id=None, knowledge_id=None, items: tuple[Unresolved, ...])`,
`resolve_mention(db, *, mention, entity_id)`, `dismiss_mention(db, *,
mention)`.

### C-17 — migration v2.05 (`scripts/migrate_v2_05_facets_encounters.py`)
Produced by: A   Consumed by: every later brief
One transaction. S1 `ALTER TABLE fact ADD COLUMN facet TEXT`; `ADD COLUMN
aspect TEXT`. S2 facet of typed facts: `lien` where `relation_id` NOT NULL,
`evenement` where `event_id`, `loi` where `world_law_id`; free facts stay
NULL. S3 rebuild `fact_default` with the widened CHECK, rows copied
identically, indexes re-created. S4 `CREATE TABLE rencontre` + indexes.
S5 `CREATE TABLE unresolved_mention` + index. S6 report (counts per
facet, rows copied). S7 post-checks (row count of `fact_default` equal
before/after; no typed fact with NULL facet). S8 `_converge_schema_meta()`
to `v2.05`. Idempotent; a second run prints zeros.

## Context

TICKET-0090 landed the relation spine. This brief lays the structure the
rest of the lot writes into: the facet registry, the facet/aspect columns,
the widened `fact_default` scope set, and two new non-canon tables. Nothing
reads facets yet; no prose moves.

## Scope IN

1. Create `src/world_engine/facets.py` exactly per C-01: the constants,
   `FacetSpec`, the nineteen entries in table order with the verbatim labels
   and descriptions, `DESCRIPTIVE_FACETS` (the fifteen facets whose family is
   `identite`, `interiorite` or `collectif`), `KNOWLEDGE_SECTION_FACETS`,
   `TYPED_FACET_BY_FK`, `facet_spec`, `normalize_aspect`. No import from
   `models` or `writes`.
2. `models/canon_knowledge.py` `Fact`: add `facet: Optional[str] = None` and
   `aspect: Optional[str] = None` after `content`, with a comment block:
   "facet: FACETS key (facets.py); NULL only on facts created before
   TICKET-0091. aspect: normalized qualifier within the facet (Q12d)."
3. Same file `FactDefault`: the scope CHECK becomes
   `"scope_type IN ('world','faction','location','rencontre')"`; extend the
   class comment's precedence note with one line: "`rencontre`: scope_id is
   an entity; the fact is known to that entity's acquaintances (C-08)."
4. `models/ephemeral.py`: add `Rencontre` per C-06 after `Visit`, and
   `ENCOUNTER_SOURCES`. `models/pipeline.py`: add `UnresolvedMention` per
   C-15 (table only). Export both classes (and `ENCOUNTER_SOURCES`) from
   `models/__init__.py` the way `Visit` and the pipeline models are
   exported there (open `models/__init__.py` and add them to the same
   import and `__all__` lists).
5. `writes/facts.py`: amend `create_fact` per C-02 (import `FACETS`,
   `TYPED_FACET_BY_FK`, `normalize_aspect` from `..facets`); add
   `update_fact_content` (C-03) and `delete_free_fact` (C-04). Extend the
   module docstring with one paragraph naming the two new functions.
6. Callers: `writes/knowledge.py:193` passes `facet="information"`;
   `writes/relations.py:144` passes `facet="lien"` (both the social and the
   `connects_to` branch); `scripts/seed_pilot.py:117` passes
   `facet="information"`.
7. `tooling/verify/canon_write_policy.txt`: add, under a comment
   `# TICKET-0091, BRIEF-0091-A`,
   `src/world_engine/writes/facts.py::update_fact_content     fact` and
   `src/world_engine/writes/facts.py::delete_free_fact        fact fact_participant fact_default knowledge`.
8. `scripts/migrate_v2_05_facets_encounters.py` per C-17, following the
   v2.04 script's shape (R-03): docstring with steps, one transaction, S
   steps, report, post-checks, `_converge_schema_meta()`. The `fact_default`
   rebuild derives its column list from `PRAGMA table_info(fact_default)`
   and copies every column; it re-creates `idx_fact_default_unique` and
   `idx_fact_default_fact` exactly as the model declares them.
9. Schema: `world-engine-schema.md` line 3 -> `v2.05`, and the sections for
   `fact`, `fact_default`, plus new sections `rencontre` and
   `unresolved_mention`; newest-first changelog entry `v2.05` in
   `world-engine-schema-changelog.md`; `schema_version.py:15` -> `"v2.05"`.
10. Checks: new `tooling/verify/checks/fact_facets.py` with R1-R4 of gate
    (e) (R3 is a negative-existence rule over a possibly-empty space, the
    `lore_isolation.py` R5-R7 precedent); `fact_spine.py:138` and
    `knowledge_resolution.py:120` pass `facet="information"`.

## Scope OUT

- `writes/facets.py`, the facts routes, any sheet change (E, F).
- Resolver tiers and `resolve_default_rows` filter (D).
- `encounters.py` and any write into `rencontre` (C).
- Any write into `unresolved_mention` (J).
- Moving any prose column (I). Tokens (J).
- `knowledge.subject` (Q1b, later ticket). `relation.notes`.

## Invariants to defend

- Schema is authoritative: model, doc, changelog and constant move together.
- History is sacred: `update_fact_content` appends before it overwrites.
- FK enforcement is on: `delete_free_fact` deletes children before the fact;
  the rebuild keeps every FK.
- Secrets are excluded at query construction: nothing here reads knowledge.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- A column exists on `fact_default` that the model does not declare.
- A `create_fact` caller exists beyond R-05.
- The rebuild's post-check row count differs.

ADAPT:
- `models/__init__.py` exports by a mechanism other than an import list and
  `__all__`: add the new classes the same way the file exports `Visit`;
  report the mechanism.
- `seed_pilot.py:117` calls `create_fact` positionally: convert that call
  to keywords; report.

REPORT-ONLY:
- The number of free facts left with NULL facet after S2 (expected: all of
  them).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python scripts/migrate_v2_05_facets_encounters.py` on a copy of the
      DB prints the report; a second run prints zeros.
- [ ] `PRAGMA table_info(fact)` lists `facet` and `aspect`; every fact with
      a `relation_id` has facet `lien`.
- [ ] Inserting a `fact_default` with `scope_type='rencontre'` and a
      `scope_id` succeeds; with `'other'` fails.
- [ ] `create_fact(..., facet=None)` raises `ValueError`.
- [ ] Green: `fact_facets.py`, `fact_spine.py`, `knowledge_resolution.py`,
      `relation_orientation.py`, `single_canon_write.py`,
      `json_ui_boundary.py`, `schema_version_agreement.py`,
      `module_budget.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

Schema doc + changelog `v2.05` (this step); `ARCHITECTURE_DECISIONS.md`:
one entry "Facet registry (TICKET-0091)" stating Q2a and Q12d.
