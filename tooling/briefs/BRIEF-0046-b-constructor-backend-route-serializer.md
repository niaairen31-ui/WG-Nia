# BRIEF -- Step "Constructor backend: create-type route + registry serializer"

## Context

BRIEF-0046-a landed on `ticket/0046`: `traits.ext_columns_for` /
`form_fields_for` now derive DDL columns and form field-specs from checked
traits. This step wires the governed writer to a creator route and teaches the
existing `GET /api/entity-types` serializer to expose runtime types + the trait
palette. After this, a type can be born from an API call and the frontend
registry sees it; the UI (c), the live tab (d), and instance CRUD (e) build on
top.

## RECON verified (ticket/0046)

- `ext_columns_for` / `form_fields_for` (`src/world_engine/traits.py:200,207`),
  `checkable_traits()` (`:143`), `trait_keys()` (`:139`).
- `create_entity_type(session, *, world_id, name, slug, columns, changed_by)
  -> id`, A1-atomic, writes `entity_type` + `entity_type_history` only
  (`src/world_engine/writes/schema.py:104-148`); slug/column validation +
  collision are internal (`:50-101`).
- `GET /api/entity-types` serializer, static-only today
  (`src/world_engine/cockpit/crud/entities.py:464-482`); shared `router`, world
  scoping via `_world_id(db)` + `get_session` (used throughout, e.g. `:490`).
- Create gate rejects non-registry types (`entities.py:549-550`).
- Models `EntityType` (`slug`, `physical_table`, `status`, world-scoped) and
  `EntityTrait` (`entity_type_id`, `trait_key`) importable from `...models`
  (`src/world_engine/models/canon.py:882,960`); active status is `'active'`.
- Creator POST pattern + `db.commit()` (`routes/creator.py:404-...`).

## Scope IN

1. Add `POST /api/entity-types` (creator authority) on the shared `router` in
   `crud/entities.py`. Body model
   `EntityTypeCreateBody { name: str, slug: str, trait_keys: list[str] = [] }`.
   Steps, all in ONE transaction, commit once:
   a. Reject any `trait_keys` entry not in `{t.key for t in checkable_traits()}`
      -> 422 (rejects unknown keys AND socle keys like `describable`, which are
      implicit, never checked).
   b. Reject `slug` equal (case-insensitive) to any `ENTITY_TYPE_REGISTRY` key
      -> 422 ("slug collides with a built-in type"). (`create_entity_type`
      already guards runtime-vs-runtime collisions; this guards runtime-vs-
      static.)
   c. `columns = ext_columns_for(trait_keys)` (socle auto-unioned by the
      derivation).
   d. `etype_id = create_entity_type(db, world_id=_world_id(db), name=name,
      slug=slug, columns=columns, changed_by=<creator id>)`.
   e. For each `k` in `trait_keys`: `db.add(EntityTrait(entity_type_id=etype_id,
      trait_key=k))`. Never write a row for `describable`/socle.
   f. `db.commit()`. On any raised error before commit, the session rolls back
      -> no `ext_*` table, no rows (A1 + the entity_trait inserts share the txn).
   Return `{ok: True, entity_type_id, slug, physical_table: "ext_"+slug}`.

2. For `changed_by`, use the same creator-identity source existing author-CRUD
   writes use. RECON it (`grep changed_by src/world_engine/cockpit/crud`); if
   author CRUD has no established creator id, pass the constant `"creator"` and
   note it. REPORT the value chosen.

3. Extend the `GET /api/entity-types` serializer (`entities.py:464-482`) to be
   the single source the frontend reads. Keep all existing keys; add / extend:
   - `types`: after the static entries, append one per ACTIVE, world-scoped
     `EntityType` row: `types[row.slug] = {"label": row.name, "fields":
     form_fields_for([et.trait_key for et in <its entity_trait rows>])}`.
     `entity_base_fields` already carries the base form; the client appends
     `fields`.
   - `entity_types`: append each runtime slug.
   - `runtime_types`: NEW key -- the list of runtime slugs (lets the frontend
     distinguish runtime from static without shipping the static set).
   - `checkable_traits`: NEW key -- `[{"key": t.key, "label": t.label} for t in
     checkable_traits()]`, the palette source for the UI (0046-c).
   Guard: a runtime slug can never collide a static key (enforced at create,
   item 1b), so no overwrite risk.

## Scope OUT

- No UI (0046-c), no live tab injection (0046-d), no instance CRUD
  generalization (0046-e).
- No AI / `write_authorities` / `ai_proposable` handling -- reserved columns
  stay untouched, reader is 0047.
- No type retire / quarantine / delete route -- create + list only this brief.
  (Retiring a type is an `entity_type` status flag; its route/UI is a later
  concern. Logged deferral: "runtime type retire route".)
- No `_create_entity_core` / `get_entity` change -- instance writes to `ext_*`
  are 0046-e.
- No schema version bump, no `models/` change.

## Invariants to defend

- Single canon-write authority: `create_entity_type` is the governed DDL/registry
  writer (0044); the `entity_trait` inserts are creator-direct rows in the SAME
  transaction -- do not open a second write path or bypass `create_entity_type`.
- History is sacred: `entity_type_history 'type_created'` is written by
  `create_entity_type`; add no update/rewrite path here.
- S-norme: columns come from `ext_columns_for`, fields from `form_fields_for` --
  never recompute either inline.
- Structural exclusion is not this brief's concern (no gameplay read here), but
  do not leak `is_secret` handling logic into the route.

## Done means

- [ ] `POST /api/entity-types {name:"Vehicule", slug:"vehicule",
      trait_keys:["spatial","secretable"]}` returns `ok` and, in the DB: `ext_
      vehicule` with `location_id` + `is_secret`; one `entity_type` row
      (status `active`); one `entity_type_history 'type_created'`; exactly two
      `entity_trait` rows (`spatial`, `secretable`); NO `describable` row.
- [ ] `trait_keys:["describable"]` or `["bogus"]` -> 422; `slug:"character"`
      -> 422 (built-in collision); a duplicate slug -> error, and NO partial
      write remains (A1 rollback verified).
- [ ] `GET /api/entity-types` now includes `"vehicule"` in `entity_types` and
      `runtime_types`, `types["vehicule"].fields` carries the `location_id`
      (entity_ref/location) and `is_secret` (bool) specs, and `checkable_traits`
      lists the four checkable traits with labels.
- [ ] Existing static types and the four static form flows are unchanged in the
      serializer output (regression: diff the static portion).
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: append -- `POST /api/entity-types` is the
  creator-direct type-creation path; it composes `create_entity_type` +
  `entity_trait` inserts in one txn; the serializer is the single source of
  runtime types + the checkable-trait palette for the frontend.
- `CLAUDE.md`: note the new route + serializer keys (`runtime_types`,
  `checkable_traits`) if it carries a route inventory.
- No schema changelog (no schema change; runtime DDL is data-plane, governed).

---

### Drafting decisions flagged (reversible)

1. **Route lives on the `crud/entities.py` router** (next to the entity-type
   serializer), not `routes/creator.py`. Move it if you prefer all "generate/
   create authoring" verbs under `creator.py`.
2. **Client supplies `slug`** (UI auto-suggests, `create_entity_type`
   validates); no server-side slugify. If you want the server to derive slug
   from name, we add a slugify helper (and reconcile with `_IDENTIFIER_RE`).
3. **`changed_by`** value pending RECON of the author-CRUD creator id; falls
   back to `"creator"` with a REPORT if none exists.
4. **Retire/delete deferred** -- create + list only. If you want at least a
   status-flip retire in this ticket, say so and I fold it into a later brief.
