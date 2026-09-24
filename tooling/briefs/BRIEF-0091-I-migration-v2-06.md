# BRIEF 0091-I — "migration v2.06 — relocation and drop"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: C, E, F, G, H

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- The AST enumeration of gate (c) (moving attribute names) returns only
  `models/` and nothing else.
- The subculture enumeration of gate (c) (AMENDMENT-0091-02), minus what G
  and H switched: the remaining references are exactly the writer
  (`writes/config.py`, `writes/__init__.py:50`), the seed
  (`scripts/seed_pilot.py`), the allow-list sites, the import-only lines and
  the policy/doc lines listed there.
- `canon_write_policy.txt:30` `write_location_subculture`.
- `prompt_lean.py` rule 3 on `_SAFE_SUBCULTURE_KEYS`.
- `schema_version.py:15` reads `"v2.05"`.

## Facts carried

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

### R-28 — prod measurements carried
[C] 2026-09-14: 615 `knowledge` rows over 312 facts; 0087 backfill bound
98 rows / 69 subjects to participants. 2026-09-21: 0 groups of identical
free facts per world. 2026-09-22: see R-18. `entity` and `character` have no
`change_history`.

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

### C-08 — `fact_default` scope `rencontre`
Produced by: A (schema), D (meaning)   Consumed by: C-05, I
`scope_type = 'rencontre'`, `scope_id` = the entity whose acquaintances
know the fact at `level`. Allowed by the rebuilt
`ck_fact_default_scope_type IN ('world','faction','location','rencontre')`.

### C-18 — migration v2.06 (`scripts/migrate_v2_06_lore_as_facts.py`)
Produced by: I
One transaction. For each filled column (trimmed non-empty), one fact,
text unchanged (L2), `created_by = 'migrate_v2_06'`, one participant:

| source | facet | aspect | default |
|---|---|---|---|
| `entity.description` | description | — | `world`/`knows` if `entity.is_public` |
| `character.appearance` | physique | — | `rencontre`/`knows`, scope_id = the character |
| `character.backstory` | histoire | — | none |
| `character.aversion` | aversion | — | none |
| `character.secrets` | histoire | — | none, plus one `knowledge` row: entity = the character, `level='unaware'`, `is_secret=1`, `subject='creator_meta'` |
| `faction.philosophy` | doctrine | — | `world`/`knows` |
| `faction.internal_structure` | organisation | — | none |
| `faction.internal_tensions` | tension | — | none |
| `faction.goals` | visee | — | none |
| `faction.aversion` | aversion | — | none |
| `location_subculture` row | coutume | `lower(trim(key))` | `location`/`knows` at `location_id` if `is_hidden = 0`, else none |

Then `ALTER TABLE ... DROP COLUMN` for the twelve columns, `DROP TABLE
location_subculture`, the D3b' control query (groups of free facts with
identical `(world_id, facet, content)` among facts created by this
migration; printed; the script does not merge), report, post-checks (one
fact per filled source cell), `_converge_schema_meta()` to `v2.06`.
Idempotent: a source cell whose fact already exists (`created_by =
'migrate_v2_06'`, same participant, facet, aspect, content) is skipped;
the DROPs are guarded by `PRAGMA table_info` / `sqlite_master`.

## Context

Readers and writers no longer touch the columns. This brief moves the
existing text into facts, unchanged (L2), and drops the columns and the
subculture table.

## Scope IN

1. `scripts/migrate_v2_06_lore_as_facts.py` per C-18: steps S1 (one
   fact per source cell, the table of C-18, text trimmed of outer
   whitespace only), S2 defaults, S3 the `creator_meta` knowledge row for
   `character.secrets`, S4 DROP COLUMN x12 and DROP TABLE
   `location_subculture`, S5 the D3b' control query printed, S6 report,
   S7 post-checks, S8 `_converge_schema_meta()` -> `v2.06`. Idempotency per
   C-18. The script writes SQL; it does not import `writes/facets.py`.
2. Models: remove the twelve fields from `Entity`, `Character`, `Faction`
   and the `LocationSubculture` class and export.
3. `writes/config.py`: remove `write_location_subculture` and its docstring
   line; `writes/__init__.py`: remove its export (`:50`) and the
   `location_subculture` mention in the docstring (`:24`); remove the
   import-only references of gate (c) (`LocationSubculture` and
   `write_location_subculture` in the eleven `cockpit/crud/*.py` modules,
   `LocationSubculture` in `cockpit/routes/mutations.py:74`);
   `scripts/seed_pilot.py`: `ensure_location_subculture` becomes
   `ensure_location_customs`, writing each key/value as a `coutume` fact
   through `write_entity_facets` (aspect = key; `hidden` = the entry's own
   `is_hidden` flag, so a hidden entry gets no default, exactly as C-18 —
   AMENDMENT-0091-03), idempotent by
   skipping when the location already has a `coutume` fact with that
   aspect and content; the call at `:3064` follows; `canon_write_policy.txt`: remove line `:30` and `location_subculture`
   from `[CANON_TABLES]`; the `single_canon_write.py` docstring list at
   `:71-76` drops the two names.
4. `context.py`: remove `_SAFE_SUBCULTURE_KEYS`; `_mj_context_location`
   filters on `FACETS["coutume"].aspects`; so do
   `cockpit/play_physical.py` (import at `:20`, docstring `:598`) and
   `cockpit/routes/mutations.py` (import at `:45`); `entity_author.py`
   already reads `FACETS["coutume"].aspects` (E). `traits.py:160` keeps
   `"description"` in `_ENTITY_BASE_FIELD_NAMES` (a runtime trait of that
   name would shadow the facet) and its comment gains one line citing
   TICKET-0091. `prompt_lean.py` rule 3 becomes
   `FACETS["coutume"].aspects == ("values",)` (import `facets`).
5. New `tooling/verify/checks/lore_as_facts.py`, R1-R4 of gate (e).
6. Schema doc (sections of the three tables, `location_subculture`
   removed), changelog `v2.06`, constant `v2.06`.

## Scope OUT

- Splitting migrated text into several facts (L2).
- Tokens on migrated text (L2).
- Merging duplicates (D3b').

## Invariants to defend

- destructive_data: the drop runs only after S7's post-checks pass inside the
  same transaction; a failed post-check rolls everything back.
- Secrets: `character.secrets` lands with its secret `unaware` row.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- S7 finds a filled source cell with no matching fact.
- The anchors' enumerations return anything outside `models/`.

ADAPT:
- SQLite refuses a DROP COLUMN because an index names the column: drop the
  index first, report it.

REPORT-ONLY:
- Counts per source column; the control query output.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] On a copy of prod: report counts equal the number of filled cells;
      second run prints zeros.
- [ ] `PRAGMA table_info(character)` has no `appearance`, `backstory`,
      `aversion`, `secrets`.
- [ ] Green: `lore_as_facts.py`, `prompt_lean.py`, `single_canon_write.py`,
      `schema_version_agreement.py`, `fact_facets.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

Schema doc + changelog `v2.06` (this step).
