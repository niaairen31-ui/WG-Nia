# BRIEF - Step "bounds preservation + template authoring in the type picker"

## Context
BRIEF-0040-b stamps birth bounds from the type template, which exposes two
pre-existing weaknesses that would silently erase them. `create_entity`
(crud/entities.py:648) hardcodes `{"bounds_width": None, "bounds_height": None,
"obstacles": []}` in its response, so the client renders an EMPTY geometry editor
right after creating a templated room; the next save then posts `null` and wipes
the 6 x 5. And `set_location_geometry` (:815-816) assigns unconditionally, `None`
included. This step closes both, and gives the creator a surface to author a
template for a type other than `room`.

## Scope IN

1. **Truthful create response.** `create_entity` (crud/entities.py:620-651): in
   the `elif entity.type == "location":` branch, replace the hardcoded geometry
   stub at :648 with `result["geometry"] = _location_geometry_dict(entity.id, db)`
   - the accessor already used at :354 and in `set_location_geometry`. Keep
   `subculture_rows` and `doors` as they are (both are genuinely empty on a fresh
   location). One-line comment: `# TICKET-0040: read the real geometry - birth
   bounds come from the type template (E1), so a hardcoded null stub would make
   the client render an empty editor whose next save wipes them.`

2. **F1 - absent means preserve.** `set_location_geometry`
   (crud/entities.py:775-827) must distinguish a bounds key that was OMITTED from
   one explicitly sent as `null`:
   - omitted -> leave `location.bounds_width` / `bounds_height` untouched;
   - explicitly `null` -> clear it (explicit creator intent, the emptied field in
     the editor);
   - a number -> assign it, after the existing `> 0` validation.
   Use Pydantic's set-fields introspection on `LocationGeometryBody` (see RECON
   below for the exact attribute name in the installed version); do NOT invent a
   sentinel default value, and do NOT change the field declarations at :447-450.
   Both-or-neither is NOT enforced here - `bounds_width` alone was already
   assignable and that is out of scope. Comment at the assignment site, verbatim:

   ```
   # F1, TICKET-0040: a key absent from the body preserves the stored
   # value; an explicit null clears it. Same posture as
   # writes.upsert_location_type, which never overwrites a decided value
   # with NULL. Full-replace still governs `obstacle` rows below - only
   # the two bounds columns gained this distinction.
   ```

   The obstacle full-replace is UNCHANGED: `write_location_obstacles` still
   receives the submitted set and still replaces it wholesale.

3. **Frontend, geometry editor.** `authorSaveGeometry` (index.html:7450-7469)
   keeps sending both keys, including explicit `null` for an emptied field - that
   is now a meaningful clear, and the field is reliably pre-filled thanks to item
   1. No change to the send shape. Verify only; if a change turns out to be
   needed, it must be reported, not improvised.

4. **Template authoring in the type modal.** The classification prompt shipped by
   BRIEF-0039-b (index.html around :8319-8348) gains two OPTIONAL numeric inputs
   below the Interieur/Exterieur control, labeled exactly `Largeur par defaut (m)`
   and `Hauteur par defaut (m)`, pre-filled from the catalog entry when present.
   They are posted to `POST /api/location-types` alongside `classification`
   (the route already accepts them since BRIEF-0040-a). Client-side guard before
   POST: if exactly one of the two is filled, block with the message
   `Renseigne les deux dimensions, ou aucune.` - the server's 422 stays the
   authority, this is only an early message.
   - Trigger for the modal is UNCHANGED: uncatalogued type, or catalogued with
     `classification == null`. A missing template NEVER triggers it.
   - Plus one new affordance: a small `Gabarit...` button beside the
     `location_type` field in the author form, always visible, which opens the
     SAME modal for whatever string the field currently holds. This is how a
     creator sets a template on an already-classified type (`building`, `city`)
     without any bulk screen.

5. **Picker display.** In the type datalist rendering fed by
   `authorLocationTypeCatalog` (index.html:3133), show the template beside a type
   that has one, as a plain suffix - e.g. `room (interieur, 6 x 5 m)`. Types
   without a template render exactly as today.

## Scope OUT
- Do NOT make the modal fire because a template is missing. Classification is
  required, sizing is optional; a modal that reappears on every `city` save would
  be a nuisance and is explicitly rejected.
- Do NOT build a "classify/size all types" admin screen, and do NOT bulk-backfill
  templates. Lazy, on next use, plus the on-demand button - same doctrine as
  BRIEF-0039-b's Scope OUT.
- Do NOT apply a template retroactively to existing locations, and do NOT add a
  "re-apply template" action anywhere in the UI (F1).
- Do NOT add `bounds_width`/`bounds_height` to the location author form or to
  `ENTITY_TYPE_REGISTRY`. The geometry editor remains their only editing surface.
- Do NOT change the obstacle full-replace semantics of
  `PUT /api/entities/{id}/geometry`.
- Do NOT convert the type datalist into a closed select. Free entry stays.
- Do NOT touch `placement.py`, `spatial_author.py`, or any `door` row.
- Do NOT extend the absent-vs-null distinction to any other route in the codebase,
  however tempting the consistency argument. Two columns, one route.

## Invariants to defend
- **json_ui_boundary**: `PUT /api/entities/{id}/geometry` and
  `POST /api/location-types` keep their plain JSON shapes. If the check maintains
  a named allow-list, the routes are already on it - do not loosen the check.
- **Full-replace config writes stay full-replace.** `write_location_obstacles` is
  untouched; only the two bounds columns gained absent-vs-null.
- **F1**: nothing in this brief writes a bounds value onto a location the creator
  did not explicitly submit.
- **page_contract**: no new tab, no new route. Both surfaces ride existing ones.
- **module_budget**: `crud/entities.py` at ~899 lines after BRIEF-0040-b, cap
  1000. This brief adds under 15 lines. Report headroom; do not extract.
  `index.html` is exempt from the module cap and is being decomposed by
  TICKET-0041 - do NOT start that decomposition here.

## RECON needed at exec time (verify before writing)
- Determine the installed Pydantic major version (`pip show pydantic`) and the
  correct set-fields attribute: `model_fields_set` (v2) vs `__fields_set__` (v1).
  `requirements.txt` pins neither; `fastapi>=0.110` implies v2 but CONFIRM against
  the live venv before writing, and use the attribute that actually exists.
- Confirm `_location_geometry_dict` (crud/entities.py:336-356) is importable at
  `create_entity`'s scope and returns the exact shape the client expects
  (`bounds_width`, `bounds_height`, `obstacles`), including for a location with
  zero obstacles.
- Read `index.html` around the classification modal (:8319-8348) and around
  `authorLocationTypeCatalog` (:3133) and the `location_type` field render
  (`authorRenderField`'s `datalist` case) to find EXACTLY where the modal is
  opened, where its result is POSTed, and where the datalist options are built.
  The `Gabarit...` button must hook the same open path, not a copy of it.
- Confirm whether any other caller of `PUT /api/entities/{id}/geometry` exists
  (grep for `/geometry` in `index.html` and in `scripts/`). A caller that omits
  the bounds keys today expecting them to be cleared would change behaviour -
  report before proceeding.
- Confirm the exact French label casing/accents used by neighbouring controls so
  the two new labels match the surrounding UI.

## Done means
- [ ] Create a `room` from the Creation surface: the sheet opens with the geometry
      editor pre-filled at 6 and 5 (not empty), immediately, with no reload.
- [ ] On that same location, add an obstacle and save WITHOUT touching the bounds
      inputs: bounds still 6 x 5, obstacle written.
- [ ] Clear the width input and save: `bounds_width` becomes NULL in the DB
      (explicit clear honoured), and Play mode reports no spatial mode for that
      location.
- [ ] `curl -X PUT .../geometry -d '{"obstacles": []}'` (both bounds keys omitted)
      on a location with 6 x 5: bounds unchanged, obstacles emptied.
- [ ] `curl -X PUT .../geometry -d '{"bounds_width": null, "bounds_height": null, "obstacles": []}'`:
      bounds cleared.
- [ ] Saving a location with a never-seen type still prompts Interieur/Exterieur
      exactly once (BRIEF-0039-b behaviour intact); filling the two optional size
      inputs persists the template; leaving them empty persists a NULL template
      and does NOT re-prompt on the next save of that type.
- [ ] Filling only one of the two size inputs shows the client message and does
      not POST.
- [ ] The `Gabarit...` button next to the type field opens the modal for
      `building` (already classified), lets a template be set, and the next
      `building` created is born with those bounds.
- [ ] The type datalist shows `room (interieur, 6 x 5 m)` and shows untemplated
      types unchanged.
- [ ] `json_ui_boundary.py`, `page_contract.py`, `module_budget.py`,
      `function_length.py` green.
- [ ] `/review-step` clean.

## Docs to update
- `ARCHITECTURE_DECISIONS.md`: extend the TICKET-0040 section with an F1
  paragraph - a template change is never retroactive; the create response now
  reads real geometry instead of a hardcoded null stub (naming the wipe path it
  closed); the two bounds columns distinguish an absent key from an explicit
  null, while the obstacle set stays full-replace; and the authoring surface is
  lazy-on-use plus one on-demand button, never a bulk screen.
- `CLAUDE.md`: one clause on the absent-vs-null rule for the two bounds columns of
  `PUT /api/entities/{id}/geometry`, since it is now the one route in the codebase
  where full-replace does not govern every field.
