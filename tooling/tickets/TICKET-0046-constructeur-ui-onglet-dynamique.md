---
id: TICKET-0046
title: Constructeur UI + onglet dynamique
type: feature
status: live-gate
created: 2026-07-24
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]      # 0046-b writes entity_trait rows AND runs governed runtime DDL via create_entity_type
blast_radius: medium
brief_ids: [BRIEF-0046-a, BRIEF-0046-b, BRIEF-0046-c, BRIEF-0046-d, BRIEF-0046-e]
schema_version_touched:       # none: entity_type (v1.87) / entity_trait (v1.88) already landed; 0046 births ext_* via runtime DDL only, no schema-version bump
retry_count: 0
---

## Request (verbatim, as Nia stated it)

TICKET 0046 -- Constructeur UI et onglet dynamique

Contexte : Verkhaal (repo `niaairen31-ui/WG-Nia`). Suite des tickets 1 et 2
(socle `entity_type` + registry de traits, supposes landes). Frontend :
vanilla JS / HTMX, `cockpit/index.html` unique, tabs gouvernes par
`page_contract.py`.

Ce ticket construit l'interface du constructeur de types en mode Creation :
une palette de traits cochables, la creation du type, et l'apparition d'un
nouvel onglet Creation pour ce type avec son formulaire CRUD genere.

Le probleme dur : `page_contract.py` verifie aujourd'hui un registry de tabs
statique. Des onglets nes a chaud le rendent non verifiable en l'etat. Il faut
decider si le contrat devient dynamique (verification runtime que tout tab
rendu correspond a un `entity_type` gouverne) ou si les tabs custom vivent dans
un conteneur unique declare statiquement, avec selection interne.

Second point : le check `json_ui_boundary` et sa liste d'autorisations nommees
-- les formulaires generes doivent-ils passer par une frontiere JSON, et si oui
l'allow-list devient-elle dynamique ?

Scope OUT : DDL runtime, definition des traits, dispatch IA.

## Clarifications resolved (intake)

RECON landed on `main` (live tarball). Key anchors:
- `create_entity_type` writes `entity_type` + `entity_type_history` only, never
  an `ext_*` row (`src/world_engine/writes/schema.py:10-16,104-148`); `columns`
  is `[(name, col_type)]`, `col_type` in the closed enum
  (`schema.py:32-41`). No call site exists in `src/` yet -- wiring it is this
  ticket.
- Trait registry landed: `checkable_traits()` = spatial/knowable/secretable/
  mutable_by_ai; `describable` is socle (implicit, never an `entity_trait` row)
  (`src/world_engine/traits.py:38-108`). `mutable_by_ai.reader_deferred =
  "TICKET-0047"` -- AI stays out.
- No trait -> `(name, col_type)` derivation exists anywhere in `src/`.
- Forms are ALREADY client-generated from `GET /api/entity-types` ->
  `authorRegistry`; `authorRenderSheet(detail, isNew, type)` builds the form
  from `entity_base_fields` + `types[type].fields`
  (`index.html:3132,6954,7225-7274`; `crud/entities.py:464-482`). No server
  HTMX form rendering exists.
- Instance CRUD is bound to the static `ENTITY_TYPE_REGISTRY` + SQLModel model
  classes: create gates on it (`entities.py:549-550`), read/write resolve the
  ext model class (`:501-502,576,692`). Custom runtime types have no SQLModel
  class -> need a dynamic ext path.
- `CREATION_TABS` dispatcher is already data-driven with no tab-id literals
  (`index.html:4283-4349`); the sub-tab BAR is static markup, 13 hand-written
  `#ctab-<slug>` buttons (`:1200-1213`). `page_contract.py` iterates a frozen
  `TAB_KEYS` and asserts each has a registry entry + `primaryAction`, and that
  the dispatcher/activate bodies carry no tab-id literal
  (`tooling/verify/checks/page_contract.py:11-14,88-127`); pure static scan, no
  DB.
- `json_ui_boundary.py`: three volets, static text scan, no DB
  (`:25`); `EntityType.write_authorities` already allow-listed with note "first
  reader = 0047 must relationalize" (`:91-96`).

Locked decisions (Nia):

- A1 -- 0046 ships a usable vertical slice: type creation + dynamic tab +
  generated form + creator-direct read/write of custom-type INSTANCES via a
  dynamic `ext_*` path. 0047 adds governance only (dispatch registry,
  fail-closed runtime check, write authorities, AI proposal path).
- B1 -- real dynamic tabs: one boot-time factory reads active `entity_type`
  rows and injects a `#ctab-<slug>` button + a `CREATION_TABS[<slug>]` entry
  (archetype `entity`, `type=<slug>`, shared container `creation-editor-area`).
  No new container, no per-type hand authoring.
- C1 -- reuse the existing seam: `GET /api/entity-types` also returns runtime
  types (label + fields), `authorRenderSheet` renders them unchanged. No server
  HTMX, no per-trait template.
- D2 -- typed columns + field-specs live on the trait (`TraitDef`), single
  source for both the DDL `columns` and the form `fields`. This is the
  completion of the 0045 derivation gap (`writes/schema.py:15`); trait
  SEMANTICS / readers stay OUT, only column-typing + field-spec is added.
- E1 -- `page_contract` asserts the MECHANISM (single factory is the sole
  producer of runtime tabs; no hand-authored custom `#ctab-`; dispatcher stays
  literal-free), never enumerates live types (no-DB doctrine holds).
- F1 -- the rule stays true; `json_ui_boundary` gains one volet asserting the
  trait field-spec derivation emits no `kind:"json"` / blob field. Extend the
  check only where the dynamic surface could reintroduce a JSON-UI field.

Concrete D2 shape (no buried choice):
- `describable` (socle), `knowable`, `mutable_by_ai` contribute ZERO ext
  columns. `describable`'s name/description live on `entity` and are already
  served by `ENTITY_BASE_FIELDS` -- authority unchanged.
- `spatial` -> `location_id` `FK_ENTITY_NULLABLE`, form `kind:'entity_ref'
  ref_type:'location'`. `secretable` -> `is_secret` `BOOLEAN`, form
  `kind:'bool'`.

Brief plan (authored in sequence; fresh RECON before each subsequent brief):
- a -- trait column typing + field-spec (D2), the 0045-plane back-fill: extend
  `TraitDef`, add `ext_columns_for()` / `form_fields_for()` derivations. Code
  only, no DB, no schema. DEPENDENCY of b..e.
- b -- constructor backend: `POST /api/entity-types` (creator) -> derive
  columns (a) -> `create_entity_type` + `entity_trait` inserts in one txn;
  extend `GET /api/entity-types` to include runtime types. danger: db_write.
- c -- constructor UI in Creation: palette of `checkable_traits()` + name/slug
  inputs -> posts to (b); renders the created type.
- d -- dynamic tab factory (B1) + `page_contract` mechanism assertion (E1).
- e -- dynamic instance read/write path for custom `ext_*` (A1, creator-direct
  only) + `json_ui_boundary` no-json-field volet (F1).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `ext_columns_for(("spatial","secretable"))` == `[("location_id",
      "FK_ENTITY_NULLABLE"), ("is_secret","BOOLEAN")]`; socle/knowable/
      mutable_by_ai contribute none  -> verify/checks/trait_ext_columns.py (0046-a)
- [ ] socle traits declare no ext column duplicating an `ENTITY_BASE_FIELDS`
      name (structural, fail-closed)  -> same check
- [ ] `page_contract` passes with dynamic tabs present AND fails if a custom
      `#ctab-<slug>` is hand-authored in static markup or a tab-id literal
      leaks into the dispatcher  -> verify/checks/page_contract.py (0046-d)
- [ ] `json_ui_boundary` gains a volet that FAILS when the trait field-spec
      derivation emits any `kind:"json"` field (red-teamed by planting one)
      -> verify/checks/json_ui_boundary.py (0046-e)
- [ ] no `ENTITY_TYPE_REGISTRY`-gated 422 blocks a governed runtime type on
      create/read/update  -> verify/checks/dynamic_ext_crud.py (0046-e)

### Live  ->  human gate (Nia)
- [ ] In Creation, check `spatial` + `secretable`, name a type, submit ->
      `ext_<slug>` table exists with `location_id` + `is_secret`, one
      `entity_type` row, one `entity_type_history 'type_created'`, and one
      `entity_trait` row per checked trait; `describable` has no row.
- [ ] A new sub-tab for the type appears without reload; its generated form
      shows the base fields + `location_id` picker + `is_secret` toggle.
- [ ] Create an instance of the custom type via the form; it persists to
      `ext_<slug>` and reappears in the list on tab re-entry.
- [ ] Retiring the type (status flag) removes its tab on next boot; existing
      rows and history are untouched (history is sacred).
