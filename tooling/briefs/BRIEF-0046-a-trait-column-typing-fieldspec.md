# BRIEF -- Step "Trait column typing + field-spec (0045-gap back-fill)"

## Context

TICKET-0046 (A1,B1,C1,D2,E1,F1) builds the type constructor. Everything
downstream (the create route, the generated form) needs one thing that does not
exist yet: a mapping from a trait to (a) the typed `ext_*` columns it
contributes and (b) the form field-specs those columns render as. The socle
already anticipates this -- `writes/schema.py:15` says "deriving it from traits
is 0045" -- but no derivation landed. This step adds it on `TraitDef` (D2:
single source for both the DDL `columns` and the form `fields`), completing the
0045 plane. Code only: no route, no DB write, no schema change.

## Scope IN

1. In `src/world_engine/traits.py`, introduce a frozen dataclass
   `ExtColumnSpec` with fields:
   - `name: str`
   - `col_type: str` -- must be a member of the closed DDL enum (see item 2).
   - `field: dict` -- the form field-spec, same shape as an `ENTITY_BASE_FIELDS`
     entry in `crud/entities.py` (at minimum `name`, `label`, `kind`; plus
     `ref_type`, `options`, etc. as needed).
   `__post_init__` raises `ValueError` unless ALL hold: `field["name"] == name`
   (the name appears once, never duplicated as free text -> S-norme); `col_type`
   is in the closed enum; `field["kind"] != "json"` (no JSON-UI field may be
   born here). No other reader form logic here.

2. In `src/world_engine/writes/schema.py`, add ONE public read-only accessor
   exposing the closed col_type set that already lives there (Dcol1: this module
   is "the ONLY source of SQL type fragments"):
   `def valid_col_types() -> frozenset[str]: return frozenset(_COLUMN_TYPES)`
   `traits.py` imports and validates against it -- the enum is referenced, never
   redefined (S-norme). No behavior change to `create_entity_type`.

3. In `TraitDef` (same file), REPLACE the current `columns: tuple[str, ...]` and
   `fk: str | None` fields with:
   `ext_columns: tuple[ExtColumnSpec, ...]`
   The `fk` string was documentary and had no reader (RECON: no `.fk`/`.columns`
   consumer exists in `src/`); the FK target is now encoded by `col_type`
   (`FK_ENTITY_NULLABLE` = `REFERENCES entity(id)`) and the UI target by the
   field-spec's `ref_type`. Keep `key`, `label`, `checkable`, and the three
   reader fields and their `__post_init__` invariant exactly as-is.

4. Populate `ext_columns` per trait:
   - `describable` (socle): `ext_columns=()`. Its name/description are `entity`
     base columns, already served by `ENTITY_BASE_FIELDS`; the trait re-emits
     nothing.
   - `knowable`: `ext_columns=()`.
   - `mutable_by_ai`: `ext_columns=()`.
   - `spatial`:
     `ExtColumnSpec(name="location_id", col_type="FK_ENTITY_NULLABLE",
       field={"name":"location_id","label":"Location","kind":"entity_ref",
              "ref_type":"location"})`
   - `secretable`:
     `ExtColumnSpec(name="is_secret", col_type="BOOLEAN",
       field={"name":"is_secret","label":"Secret (creator-only)","kind":"bool",
              "default":False})`

5. Add two derivation functions in `traits.py`, the single readers of
   `ext_columns` (E2: structure ships with its reader):
   - `def ext_columns_for(trait_keys: Iterable[str]) -> list[tuple[str, str]]`
     Returns the `(name, col_type)` list to pass to `create_entity_type`,
     unioning `socle_traits()` ext columns (none today) with the ext columns of
     each key in `trait_keys` that names a checkable trait. Order: socle first,
     then checked keys in `TRAITS` declaration order. Raise `ValueError` on a
     name collision across traits (same `name`, any type). Unknown / non-
     checkable keys in the input are ignored for column emission (they may be
     valid trait keys with no columns, e.g. `knowable`).
   - `def form_fields_for(trait_keys: Iterable[str]) -> list[dict]`
     Same effective set, same order/dedupe, returns each `ExtColumnSpec.field`
     dict (for 0046-b to append to `ENTITY_BASE_FIELDS` in the
     `GET /api/entity-types` serializer).

6. Add a structural, fail-closed guard (module-import time in `traits.py`, so a
   violation crashes at import): assert no `socle_traits()` trait declares an
   `ext_columns` entry whose `name` collides with any `ENTITY_BASE_FIELDS` name.
   To reference base-field names without a circular import, hardcode the base
   name set in the assertion with an inline comment pointing at
   `crud/entities.py:ENTITY_BASE_FIELDS` as the authority, OR (preferred) expose
   the base names via a tiny read-only accessor and import it. Executor picks
   the non-circular option; REPORT if a circular import forces the hardcode.
   Keep the existing partition invariant
   (`set(socle_traits()) | set(checkable_traits()) == set(TRAITS)`, disjoint).

7. Add `verify/checks/trait_ext_columns.py` (fail-closed, vacuous-proof):
   - Imports `traits`; asserts
     `ext_columns_for(("spatial","secretable")) == [("location_id",
     "FK_ENTITY_NULLABLE"), ("is_secret","BOOLEAN")]`.
   - Asserts `ext_columns_for(("knowable","mutable_by_ai")) == []` and that
     `describable` is absent from any emitted set.
   - Asserts every `ExtColumnSpec.col_type` is in `valid_col_types()` and every
     `.field["kind"]` != `"json"`.
   - Asserts the socle/base-name guard holds.
   - Counts parsed ext columns; ZERO parsed is a FAIL (a parse that finds
     nothing is a broken parse, not a clean repo). Exit 0 on pass, 1 on any
     failure, one line per failure.
   Register it in the verify runner alongside the existing checks.

## Scope OUT

- Do NOT add or call any route; do NOT call `create_entity_type`; do NOT write
  `entity_trait` rows. That is BRIEF-0046-b.
- Do NOT modify `GET /api/entity-types` or its serializer. 0046-b consumes
  `form_fields_for`; this brief only provides it.
- Do NOT add, remove, or re-key any trait; do NOT touch `reader_callable`,
  `reader_guard`, `reader_deferred`, or any reader logic. Trait SEMANTICS stay
  OUT (0045).
- Do NOT introduce a `JSON` col_type usage or a `kind:"json"` field anywhere.
  The `json_ui_boundary` volet is BRIEF-0046-e; here, simply never create one.
- Do NOT emit ext columns for `describable`, `knowable`, or `mutable_by_ai`.
- Do NOT build the dynamic instance CRUD path (0046-e), the tab factory
  (0046-d), or any UI (0046-c).
- Do NOT bump a schema version or touch any `models/` file -- no table changes.
- Do NOT change `create_entity_type` behavior; item 2 adds a read-only accessor
  only.

## Invariants to defend

- S-norme (no duplication): the closed col_type set is referenced from
  `writes/schema.py` via `valid_col_types()`, never redefined in `traits.py`;
  each ext-column name appears once (`ExtColumnSpec.name`, with
  `field["name"] == name` asserted).
- E2 "no structure without a reader": `ext_columns_for` / `form_fields_for` are
  the concrete readers of the new `ext_columns` structure, delivered in THIS
  brief -- the structure never ships reader-less.
- "Socle traits are implicit, never projected" (BRIEF-0045-d): unchanged;
  `describable` still writes no `entity_trait` row and now also emits no ext
  column. The partition invariant stays asserted.
- Module budget R5 (1000 lines / 40 fns) and R1 (80-line function ceiling):
  `traits.py` is small; keep both derivations and the guard well under caps.
- R8 (pyflakes F821): no undefined names introduced by the field replacement.

## Done means

- [ ] `python -c "from world_engine.traits import ext_columns_for;
      print(ext_columns_for(('spatial','secretable')))"` prints
      `[('location_id', 'FK_ENTITY_NULLABLE'), ('is_secret', 'BOOLEAN')]`.
- [ ] `form_fields_for(('spatial','secretable'))` returns two dicts: one
      `{name:'location_id', kind:'entity_ref', ref_type:'location', ...}` and one
      `{name:'is_secret', kind:'bool', ...}`.
- [ ] `ext_columns_for(('knowable','mutable_by_ai'))` returns `[]`.
- [ ] `from world_engine.writes.schema import valid_col_types;
      'FK_ENTITY_NULLABLE' in valid_col_types()` is `True`; `create_entity_type`
      is unchanged (existing 0044 smoke behavior identical).
- [ ] `python tooling/verify/checks/trait_ext_columns.py` exits 0 and prints a
      PASS line; temporarily planting an ext column named `name` on a socle
      trait (or a `kind:"json"` field) makes it exit 1, then removing it returns
      green (red-team both guards live).
- [ ] The full verify suite (including `trait_registry_projection.py`) is green;
      pyflakes reports no F821.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: append one entry recording D2 -- typed
  `ext_columns` on `TraitDef` as the completion of the 0045 derivation gap
  (`writes/schema.py:15`), the `describable`/`knowable`/`mutable_by_ai` = zero-
  ext-column rule, and that `ext_columns_for` / `form_fields_for` are the single
  source for both DDL columns and form fields.
- `CLAUDE.md`: if it carries a `traits.py` contract line, update it to name
  `ext_columns` + the two derivations; note `valid_col_types()` as the pointer-
  fresh accessor for the closed DDL type enum.
- No schema changelog entry (no schema change).

---

### Drafting decisions flagged (reversible before sending)

1. **Replaced `columns`/`fk` rather than adding a parallel typed field.** Kills
   duplication and matches "single source on the trait", but it is a visible
   edit to the trait plane the ticket scoped OUT for semantics. If you'd rather
   leave `columns` untouched, we make `ext_columns` purely additive and accept a
   dormant `columns` field -- less clean, smaller trait-plane footprint.
2. **`location_id` typed `FK_ENTITY_NULLABLE`** (placement optional at
   creation). Flip to `FK_ENTITY` if a spatial entity must be placed at birth.
3. **Added `valid_col_types()` to `writes/schema.py`** -- a read-only touch to
   the 0044 module so `traits.py` validates without redefining the enum. If you
   want 0044 frozen, we instead duplicate the key set in `traits.py` with a
   pointer comment (violates S-norme; not recommended).
4. **`describable` keeps `ext_columns=()`**, base identity authority stays
   `ENTITY_BASE_FIELDS`. If you want `describable` to remain the documented owner
   of name/description, we'd model base-plane columns explicitly -- a larger
   change deferred here.
5. **Base-name guard import** (item 6): executor chooses accessor vs hardcode to
   avoid a circular import; flagged so you know a hardcode-with-pointer is the
   fallback if the import direction bites.
