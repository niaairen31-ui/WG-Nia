# BRIEF - Step "type picker reads the registry + prompts classification on new types"

## Context
BRIEF-0039-a shipped the classified registry with no consumer. This step makes the
Creation-mode location type picker read it and keep it extensible: choosing a type
whose classification is NULL (or a brand-new type) prompts interior/exterior once
and persists the choice. This is the human side of G; nothing about doors yet.

## Scope IN
1. NEW READ ROUTE `GET /api/location-types` (creator surface; place beside the
   locations graph reader in `src/world_engine/cockpit/crud/locations.py`).
   Returns the catalog for the active world:
   `[{ "name": str, "classification": "interior"|"exterior"|null }, ...]`,
   ordered by name. Read-only; structural world scoping (WHERE world_id = active).
2. Picker source of truth (frontend, index.html): the location_type datalist must
   be populated from `/api/location-types` instead of the hardcoded
   `LOCATION_TYPE_ORDER` / the inline `options` list in crud/entities.py:141-143.
   - Keep `LOCATION_TYPE_ORDER` ONLY as the display bucket order for the browse
     tree (index.html:6536, 6540) - do NOT delete it; it is a presentation order,
     not a vocabulary. Any type absent from it still buckets under `other` as today.
3. Classification prompt on save. When the creator saves a location whose chosen
   `location_type`:
   - is not present in the catalog, OR
   - is present with `classification == null`,
   then BEFORE the save completes, the UI must require an interior/exterior choice
   (a two-option control - radio or two buttons - labeled exactly "Interieur" /
   "Exterieur"), and on confirm POST it (step 4). Only after the type is classified
   does the location save proceed. A type already classified saves with no prompt.
4. NEW WRITE ROUTE `POST /api/location-types` -> calls `upsert_location_type`
   (BRIEF-0039-a) with `{name, classification}` for the active world, commits,
   returns the stored row. `changed_by` = the creator identity used elsewhere in
   crud writes (match the existing pattern; do not invent one).
5. The datalist stays FREE-ENTRY (kind="datalist"): the creator may still type a
   new string. A new string simply falls into the "not in catalog" branch of
   step 3 and gets classified then persisted.

## Scope OUT
- NO door logic, NO materialization, NO E1 note. This brief only classifies types.
- Do NOT convert the datalist to a closed select. Free entry is the whole point of G.
- Do NOT retro-classify existing NULL types in bulk or build a "classify all types"
  admin screen - classification is lazy, on next use (named future nicety, not now).
- Do NOT add a public/private option to the prompt - two options only
  (interior/exterior). Public/private is deferred (see BRIEF-0039-e).
- Do NOT block editing a location whose CURRENT type is already classified just
  because other NULL types exist - the prompt is triggered by the CHOSEN value only.
- Do NOT remove `LOCATION_TYPE_ORDER`.

## Invariants to defend
- json_ui_boundary check: the two new routes return plain JSON shapes; keep them
  inside the named allow-list boundary that json_ui_boundary.py enforces. If the
  check has an allow-list of UI-shape routes, add these two explicitly rather than
  loosening the check.
- Structural exclusion: `/api/location-types` filters `world_id = active world` at
  query construction, never post-filter.
- page_contract / tab registry: no new tab; this rides existing Creation surfaces.
  If page_contract.py enumerates routes, register the two new ones.

## RECON needed at exec time (verify before writing)
- Read index.html around the location author form (the `author-x-location_type`
  field, index.html:6957, and the sheet input at 10820) to find EXACTLY where the
  datalist options are rendered and where the location save is dispatched - the
  prompt must gate that specific save path.
- Confirm how `changed_by` / creator identity is passed in an existing crud write
  route (e.g. the relation or subculture write) and reuse it verbatim.
- Confirm whether json_ui_boundary.py and page_contract.py maintain explicit
  route allow-lists; if so, the two new routes must be added there in THIS commit.

## Done means
- [ ] `GET /api/location-types` returns the seeded catalog for the active world.
- [ ] Opening the location type picker shows the catalog types (not a stale hardcoded
      list); typing a new type is still allowed.
- [ ] Saving a location with a never-seen type shows the Interieur/Exterieur prompt;
      confirming persists the type with that classification; re-opening the picker
      shows it; saving another location with that type does NOT prompt again.
- [ ] Saving a location whose type is a seeded-but-NULL type (`other`) prompts once,
      then `other` is classified going forward.
- [ ] json_ui_boundary.py and page_contract.py green.
- [ ] `/review-step` clean.

## Docs to update
- CLAUDE.md: note the two new routes under the Creation/locations surface (pointer-fresh).
- This step needs no ARCHITECTURE_DECISIONS entry beyond the G entry from BRIEF-0039-a.
