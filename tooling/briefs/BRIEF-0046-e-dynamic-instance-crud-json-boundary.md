# BRIEF -- Step "Dynamic instance CRUD for custom ext_* + json_ui_boundary volet"

## Context

The constructor (b), UI (c), and live tabs (d) exist; a runtime type's tab
renders its generated form, but instances cannot yet be persisted or read --
the entity CRUD is bound to the static `ENTITY_TYPE_REGISTRY` + SQLModel model
classes, which a runtime type has not. This step generalizes create/read/update/
delete for governed runtime types via a reflected `ext_*` path (creator-direct
authority only), closing the A1 vertical slice, and adds the F1
`json_ui_boundary` volet so the dynamic form surface can never reintroduce a
JSON-UI field. AI-proposal dispatch and the fail-closed runtime completeness
check are 0047 -- OUT here.

## RECON verified (ticket/0046)

- Create gate rejects non-registry types (`entities.py:549-550`); ext write uses
  the SQLModel class `ENTITY_TYPE_REGISTRY[entity_type]["model"]`
  (`:576,582`); base fields via `_apply_base_fields` (`:409`); ext kwargs via
  `_build_extension_kwargs` reading `spec["fields"]` (`:416-421`); field
  coercion `_coerce_field` handles `entity_ref`/`bool`/etc. (`:212`).
- `get_entity`: `if entity.type in ENTITY_TYPE_REGISTRY` resolves the ext model;
  ELSE returns empty extension/relations/knowledge (`:498-516`) -- the branch a
  runtime type currently falls into.
- `update_entity` (`:677`), `delete_entity` (`:736`).
- `EntityType` carries `physical_table` (validated `ext_*` identifier) and
  `status` (`models/canon.py:882`); `EntityTrait` gives the checked traits
  (`:960`). `form_fields_for` derives the field-specs (`traits.py:207`).
- `create_entity_type` births the table; `physical_table` is a validated
  identifier (`writes/schema.py:50-58,124`).
- `json_ui_boundary.py`: three static volets, no DB (`:25,117-197`);
  `ExtColumnSpec.__post_init__` already rejects `kind:"json"` at construction
  (`traits.py:42-46`).

## Scope IN

1. Add a resolver `_runtime_type_spec(db, type_slug) -> dict | None` in
   `crud/entities.py`: for a slug NOT in `ENTITY_TYPE_REGISTRY`, look up the
   ACTIVE, world-scoped `EntityType` by slug; if found, return
   `{"physical_table": row.physical_table, "fields":
   form_fields_for([et.trait_key for et in <its entity_trait rows>])}`; else
   `None`. This is the single "is this a governed runtime type" gate.
2. Ext-table access via SQLAlchemy Core reflection (NO string interpolation of
   values): `Table(physical_table, MetaData(), autoload_with=db.get_bind())`;
   build parameterized `insert()` / `select()` / `update()` / `delete()`
   statements. `physical_table` comes only from the registry (validated
   identifier), never from user input.
3. Generalize the four CRUD paths for governed runtime types:
   - `_create_entity_core` (`:534`): replace the hard gate so a governed runtime
     type is accepted; build the `Entity` + base fields as today; for the ext
     row, coerce `body.extension` through the runtime `fields`
     (reuse `_coerce_field` per field, same as `_build_extension_kwargs`) and
     INSERT `{id: entity.id, **coerced}` into the reflected table after the
     entity flush. Ungoverned slug (neither static nor active `entity_type`)
     -> 422 (fail-closed: never touch an arbitrary table).
   - `get_entity` ELSE branch (`:512-515`): if `_runtime_type_spec` matches,
     SELECT the ext row and populate `result["extension"]`; keep
     `relations`/`knowledge` as `[]` for runtime types this brief (see OUT).
   - `update_entity` (`:677`): UPDATE the reflected ext row with coerced fields.
   - `delete_entity` (`:736`): delete the ext row then the entity row (or rely
     on the FK/cascade already used for static types -- match the existing
     pattern; REPORT which).
   Factor the static-vs-runtime branch so the static paths are byte-for-byte
   unchanged in behavior (regression-critical).
4. Add a `json_ui_boundary.py` volet (F1), static, no DB: import `traits`,
   iterate every `ExtColumnSpec` across `TRAITS`, FAIL if any
   `.field.get("kind") == "json"`; assert non-vacuous (>= 1 ext field parsed --
   there are 2 today). This mirrors the construction-time guard at the verify
   plane (defense in depth: survives a future removal of the `__post_init__`
   check). Keep the three existing volets intact.
5. Add `verify/checks/dynamic_ext_crud.py` (fail-closed, temp-fixture pattern
   like `trait_registry_projection.py`): in a temp DB, `create_entity_type` a
   throwaway spatial+secretable type, create an instance through the generalized
   path, read it back and assert `location_id`/`is_secret` round-trip; assert an
   ungoverned slug is rejected. Zero assertions exercised = FAIL.

## Scope OUT

- AI-proposal dynamic dispatch, the fail-closed runtime dispatch-registry
  completeness check, `write_authorities` / `ai_proposable` enforcement, and the
  `mutable_by_ai` reader -- ALL 0047. This brief is creator-direct authority
  only.
- Relations / knowledge editing for custom-type instances -- runtime types get
  `[]` here. (Logged deferral: "runtime-type relations/knowledge UI".)
- Type retire/quarantine effects on instances, and any destructive DDL -- none;
  retiring is an `entity_type` status flag (0046-b deferral), not handled here.
- No change to static-type CRUD behavior (only refactor to branch cleanly).
- No `models/` change, no schema bump, no new JSON column.

## Invariants to defend

- Single canon-write authority: runtime-type instance writes are the creator-
  direct path (the analog of the static author CRUD); they do NOT go through
  `proposed_mutation` / `_apply_mutation` (that is the AI path, 0047). Do not
  create a second write authority.
- Structural exclusion stays structural: `is_secret` (secretable) is filtered
  for gameplay by its `reader_guard` at query construction (context plane,
  unchanged). The creator CRUD legitimately shows `is_secret` to the creator --
  do NOT add prompt-level or ad-hoc exclusion here.
- Fail-closed: an ungoverned slug is rejected before any table is touched; the
  `json_ui_boundary` and `dynamic_ext_crud` checks fail loudly, never vacuously.
- No JSON-UI field: the F1 volet keeps the dynamic form surface relational-only
  (the DDL enum already maps a `JSON` col_type to physical `TEXT`, but no trait
  emits one and no `kind:"json"` field may exist).
- History is sacred: delete is the only destructive path and it mirrors the
  existing static delete; no other mutation of past rows.

## Done means

- [ ] For a runtime `vehicule` (spatial+secretable): submitting the generated
      form creates an `entity` row (type `vehicule`) AND an `ext_vehicule` row
      with the chosen `location_id` + `is_secret`; the instance appears in the
      type's list on tab re-entry.
- [ ] Opening the instance repopulates the form (extension round-trips);
      editing `location_id`/`is_secret` and saving updates `ext_vehicule`;
      deleting removes both rows.
- [ ] A create/read/update against a slug that is neither static nor an active
      `entity_type` returns 422 and touches no table.
- [ ] Static-type CRUD (character/location/faction/item) is behaviorally
      unchanged (regression pass).
- [ ] `python tooling/verify/checks/json_ui_boundary.py` passes with the new
      volet; planting a `kind:"json"` field on an `ExtColumnSpec` (bypassing the
      `__post_init__` guard) makes it FAIL; removing it returns green.
- [ ] `python tooling/verify/checks/dynamic_ext_crud.py` exits 0; the full
      verify suite is green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: append -- custom `ext_*` instance CRUD is a
  reflected-table, parameterized, creator-direct path; ungoverned slugs are
  fail-closed; the AI-proposal path + fail-closed dispatch check are 0047; the
  `json_ui_boundary` F1 volet makes the dynamic form surface relational-only at
  the verify plane. Record the runtime-type relations/knowledge deferral.
- `CLAUDE.md`: note the reflected-table CRUD helper + the new checks.
- No schema changelog (no schema change).

---

### Drafting decisions flagged (reversible)

1. **Reflected `Table` + Core statements** (not raw `text()` string SQL) for
   ext access -- safest against injection and reuses `_coerce_field`. If you
   prefer explicit parameterized `text()`, say so.
2. **Relations/knowledge = `[]` for runtime types** this brief (deferred). If a
   runtime type should support the generic relation/knowledge editors now, that
   is a larger add I can fold into a follow-up.
3. **`json_ui_boundary` F1 volet imports `traits`** (pure, no DB) rather than
   text-scanning `traits.py`. Mirrors the runtime guard; switch to a text scan
   if you want the check import-free.
4. **Delete mirrors the static pattern** (cascade vs explicit ext delete) --
   executor RECONs which the static path uses and matches it; flagged so the
   choice is visible.
