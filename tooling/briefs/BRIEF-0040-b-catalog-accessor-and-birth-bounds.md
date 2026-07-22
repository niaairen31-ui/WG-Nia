# BRIEF - Step "single catalog accessor + template applied at location birth"

## Context
BRIEF-0040-a shipped the size template with no reader. This step gives it exactly
one reader and exactly one application site: a location is stamped with its type's
template at creation, once, and never again. It also collapses the two existing
case-fold catalog scans into one accessor (J1) rather than adding a third.

## Scope IN

1. **J1 - one catalog read accessor.** In `src/world_engine/spatial_author.py`,
   extract from `location_classification` (:126-145) a module-private helper:

   ```
   def _catalog_row(db: Session, *, world_id: str, type_name: str) -> Optional[LocationTypeCatalog]
   ```

   Case-insensitive `casefold()` match over the world's rows, identical semantics
   to the current inline scan. `location_classification` becomes a caller of it and
   keeps its signature, its return type and its docstring contract byte-identical.
   Docstring for `_catalog_row`: `The single catalog read path (J1, TICKET-0040).
   Both the interior/exterior classification and the size template resolve a
   location_type through here; writes.upsert_location_type keeps its own lookup -
   the write layer never climbs into the read layer.`

2. **Template reader**, next to it, second caller of `_catalog_row`:

   ```
   def location_type_template(db: Session, *, world_id: str, type_name: Optional[str]) -> Optional[tuple[float, float]]
   ```

   Returns `(default_width, default_height)` when the type is catalogued AND both
   columns are non-NULL AND both are finite and > 0; returns `None` in every other
   case (NULL type, uncatalogued type, one column NULL, non-finite, <= 0). Total:
   never raises. Docstring must state: `Fail-closed (B1): no template -> None ->
   the location is born with NULL bounds and has no spatial mode. Nothing is ever
   invented.`

3. **E1 - application at birth, one site.** In
   `src/world_engine/cockpit/crud/entities.py`, add a module-level helper:

   ```
   def _stamp_type_template(db: DbSession, world_id: str, ext_row: Location) -> None
   ```

   which reads `spatial_author.location_type_template(db, world_id=world_id,
   type_name=ext_row.location_type)` and, when it returns a pair, assigns
   `ext_row.bounds_width` / `ext_row.bounds_height`. It assigns NOTHING when the
   template is `None`, and NOTHING when either bound is already non-NULL on the
   row. Docstring: `E1, TICKET-0040: birth bounds from the location_type size
   template. Called from _create_entity_core ONLY - never from the update path
   (_build_extension_kwargs is shared with PUT /entities/{id} and would re-stamp
   on every edit, breaking F1: a template change is never retroactive).`

   Call site in `_create_entity_core`, immediately after
   `ext_row = ext_model(id=entity.id, **ext_kwargs)` (:566), **exactly two
   lines**:

   ```
   if entity_type == "location":
       _stamp_type_template(db, entity.world_id, ext_row)
   ```

   `_create_entity_core` is 73 physical lines against an 80-line ceiling; two
   lines is the budget. Do not inline the logic, do not add comments inside the
   function body, do not add an entry to the `function_length` baseline.

4. **Import direction.** `crud/entities.py` imports `spatial_author`, not the
   reverse. Confirm this introduces no cycle (see RECON below); if it does, the
   accessor moves to a leaf module and BOTH callers import it from there - report
   before choosing.

## Scope OUT
- Do NOT put the stamping in `_build_extension_kwargs` (entities.py:415). It is
  called from the UPDATE path at :678; putting it there re-stamps bounds on every
  location edit and silently overwrites creator-set geometry. This is the single
  most likely wrong move in this brief.
- Do NOT add a second application site (batch commit, region commit, add-location).
  `routes/regions.py:223` already calls `_create_entity_core`; one site covers all.
- Do NOT make the template a live link: no re-read on edit, no propagation when a
  template changes, no "re-apply template" button (F1).
- Do NOT touch `create_entity`'s response shape or `set_location_geometry`
  (BRIEF-0040-c) - even though the create response now under-reports the stamped
  bounds. That is the next brief's job; leave it visibly broken rather than
  half-fixing it here.
- Do NOT touch `placement.py`, `spatial_author.materialize_doors`,
  `connect_locations`, or any `door` row.
- Do NOT refactor `upsert_location_type`'s own lookup into `_catalog_row`. The
  writes layer stays isolated.
- Do NOT add obstacle generation. A room born with bounds has zero obstacles, by
  design.

## Invariants to defend
- **F1, no retroactivity.** The only write to `bounds_*` in this brief happens on
  a row that has just been constructed in memory and never existed in the DB.
- **Single canon-write authority.** `_create_entity_core` is already a creator
  direct-authority path; nothing here is reachable from `_apply_mutation`. The
  helper must not be importable into any mutation dispatch.
- **Structural exclusion / world scoping.** `_catalog_row` filters
  `world_id == <active>` at query construction, as `location_classification` does
  today. Never post-filter.
- **80-line function ceiling** (`function_length.py:29`) on `_create_entity_core`.
- **module_budget**: `crud/entities.py` is at 884 lines against a 1000-line cap.
  This brief adds roughly 15. Report the remaining headroom in the step summary;
  do NOT start an extraction.
- **import_cycle** check must stay green.

## RECON needed at exec time (verify before writing)
- Run `tooling/verify/checks/import_cycle.py` BEFORE writing, then confirm that
  `cockpit/crud/entities.py -> world_engine.spatial_author` creates no cycle
  (`spatial_author` imports `placement`, `models`, `writes` - none of which import
  `cockpit`). If a cycle appears, STOP and report rather than restructuring.
- Confirm the exact physical line count of `_create_entity_core` before and after
  (`ast`, `end_lineno - lineno + 1`) and state both numbers in the step summary.
- Confirm `entity.world_id` is populated at line 566 (it is set at :540 via
  `_world_id(db)`) - the helper must not call `_world_id(db)` a second time.
- Confirm BRIEF-0039-b's classification prompt persists the type BEFORE the
  location save completes, so that at `_create_entity_core` time the catalog row
  for the chosen type already exists. If that ordering does not hold, the stamp
  silently no-ops for brand-new types - report it, do not work around it.
- Confirm `Location` is already imported in `crud/entities.py` for the helper's
  type hint.
- Check whether `routes/regions.py` or `routes/npc_agent.py` construct location
  extension rows WITHOUT going through `_create_entity_core`; if any does, report
  it (it would be a second birth path the template misses) - do not patch it here.

## Done means
- [ ] `GET /api/location-types` still returns what BRIEF-0040-a shipped
      (no regression).
- [ ] Creating a location of type `room` via the Creation surface produces a
      `location` row with `bounds_width = 6.0`, `bounds_height = 5.0` (verified in
      the DB, since the create RESPONSE still reports null - expected, fixed in
      BRIEF-0040-c).
- [ ] Creating a location of type `city` (no template) produces NULL bounds, no
      error, no log noise.
- [ ] Creating a location with a brand-new type: the classification prompt fires,
      the type is persisted with a NULL template, the location is born with NULL
      bounds.
- [ ] Editing that `room` location (rename, change access_level, save) leaves
      `bounds_width`/`bounds_height` unchanged. Changing its `location_type` to
      another templated type ALSO leaves them unchanged (F1).
- [ ] Committing a region containing a `room` location produces a location with
      6.0 x 5.0 bounds through the same code path.
- [ ] `location_classification` returns the same value it returned before the
      refactor for: an interior type, an exterior type, an unclassified type, an
      uncatalogued type, a NULL type (five spot-checks).
- [ ] `function_length.py`, `module_budget.py`, `import_cycle.py`,
      `single_canon_write.py` green.
- [ ] `/review-step` clean.

## Docs to update
- `ARCHITECTURE_DECISIONS.md`: extend the
  `## LOCATION TYPE SIZE TEMPLATES (BRIEF-0040-a, schema v1.85)` section with an
  E1/J1 paragraph - one application site at birth, the explicit rejection of
  `_build_extension_kwargs` and why (shared with the update path), and the single
  catalog read accessor with the write layer deliberately left out of it.
- `CLAUDE.md`: one clause noting that `spatial_author._catalog_row` is the single
  catalog read path and that location birth bounds come from the type template at
  `_create_entity_core` only.
