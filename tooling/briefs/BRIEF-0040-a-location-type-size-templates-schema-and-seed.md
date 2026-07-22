# BRIEF - Step "location_type size templates: schema, write path, room seed"

## Context
TICKET-0040, step 1 of 5. Nothing in the engine can derive a location's playable
bounds today: `bounds_width`/`bounds_height` are absent from
`ENTITY_TYPE_REGISTRY["location"]` (crud/entities.py:135-158) and are written only
by `PUT /api/entities/{id}/geometry`, an editor reachable for existing locations
only (index.html:7475). Every location is therefore born with bounds NULL. This
step adds the two template columns to `location_type_catalog`, their write path,
and the `room` seed. It applies the template to NOTHING - that is BRIEF-0040-b.

## Scope IN

1. **Model.** `LocationTypeCatalog` (`src/world_engine/models/canon.py:247`) gains
   two nullable REAL columns, `default_width` and `default_height`, with this NOTE
   embedded verbatim above them:

   ```
   # Size template (schema v1.85, TICKET-0040, BRIEF-0040-a). The ONLY
   # source of a location's birth bounds: code reads these, a model never
   # produces a number (A1). Applied ONCE, at creation
   # (crud/entities.py::_create_entity_core, E1) - never a live link: a
   # template change is NEVER retroactive (F1). Both NULL or both set,
   # enforced by writes.upsert_location_type; a type with no template ->
   # bounds NULL -> no spatial mode. Same LOCAL coordinate space as
   # obstacle_vertex (1.0 = one world-meter), NEVER coord_x/coord_y.
   ```

2. **Schema doc.** `world-engine-schema.md`: bump the `Current schema version:`
   line (:3) to the next number after v1.84; extend the
   `location_type_catalog` DDL block (:201-209) with the two columns and a short
   prose note carrying the same three facts (birth-only, both-or-neither, local
   coordinate space). Append the changelog entry to
   `world-engine-schema-changelog.md`, newest first, in the exact shape of the
   existing v1.84 entry.

3. **Migration** `scripts/migrate_v1_85_location_type_templates.py`, modeled line
   for line on `scripts/migrate_v1_84_location_type_catalog.py`:
   - idempotent `ALTER TABLE location_type_catalog ADD COLUMN` for each of the two
     columns, only when the column is absent from the inspector's column list;
   - re-runnable: a second run prints "nothing to do" and exits 0;
   - prints the applied list, same output shape as v1.84.

4. **K2 seed, inside the same migration.** For EVERY world:
   - find the `room` row case-insensitively (same fold as
     `upsert_location_type:362-369`);
   - if it exists AND both `default_width` and `default_height` are NULL, set
     them to `6.0` and `5.0`;
   - if it does not exist, create it through `upsert_location_type` with
     `classification="interior"` (matching `migrate_v1_84`'s `_DEFAULTS`) and the
     same two values;
   - **never overwrite a non-NULL value**, in either direction, for any reason.
   No other type is seeded. `city`, `district`, `natural`, `building`,
   `underground`, `other` keep NULL templates.

   Seed constants at module top, named `_ROOM_DEFAULT_WIDTH = 6.0` /
   `_ROOM_DEFAULT_HEIGHT = 5.0`, with the comment: `# K2, TICKET-0040: the one
   seeded template, in world-meters. Creator-editable from the type picker; the
   migration never revisits it.`

5. **Write path.** `writes/config.py::upsert_location_type` (:339) gains two
   keyword-only optional parameters `default_width: Optional[float] = None` and
   `default_height: Optional[float] = None`. Posture identical to
   `classification` (:371-375): on an existing row, assign ONLY when the incoming
   value is non-NULL - a decided template is never overwritten with NULL.
   Validation, before any lookup, raising `ValueError` with these exact messages:
   - both-or-neither: `upsert_location_type: default_width and default_height must be both set or both NULL`
   - positive+finite: `upsert_location_type: default_width must be a finite number > 0`
     (and the `default_height` twin)
   Extend the function's docstring with one sentence naming the both-or-neither
   rule and the never-overwrite-with-NULL posture.

6. **Route pass-through.** `cockpit/crud/locations.py`: `_location_type_dict`
   (:287) returns the two new keys; `LocationTypeBody` (:304) gains the two
   optional fields; `create_or_classify_location_type` (:309) passes them to
   `upsert_location_type` and keeps mapping `ValueError -> HTTPException(422)`.

## Scope OUT
- Do NOT apply the template to any location. No touch to `_create_entity_core`,
  `_build_extension_kwargs`, or any `Location` row (BRIEF-0040-b).
- Do NOT touch `set_location_geometry`, `create_entity`'s response, or any
  frontend file (BRIEF-0040-c).
- Do NOT touch `placement.py`, `spatial_author.py`, or any `door` row
  (BRIEF-0040-d / -e).
- Do NOT implement B4 (median-of-siblings override). Named deferral, triggered by
  worlds populated enough for a median to mean something.
- Do NOT seed any type other than `room`, and do NOT backfill bounds onto
  existing locations.
- Do NOT add a SQL CHECK constraint for the positivity or the both-or-neither
  rule - validation lives in the write path, matching `set_location_geometry`'s
  422 idiom.
- Do NOT add `default_width`/`default_height` to
  `ENTITY_TYPE_REGISTRY["location"]["fields"]`. They are catalog columns, not
  location columns; the location's own bounds keep their single writer.
- Do NOT add a "classify/size all types" admin screen.

## Invariants to defend
- **Never overwrite a decided value with NULL** (config.py:371-375). The template
  follows the classification's posture exactly; the migration's seed is guarded by
  the same rule.
- **Upsert-ONE, never full-replace.** No `DELETE FROM location_type_catalog`
  anywhere, migration included.
- **Metadata-config category: no `change_history`.** `location_type_catalog`
  carries none today and must not gain one.
- **Single canon-write authority.** `upsert_location_type` stays the only writer
  of this table; the migration calls it rather than issuing raw UPDATEs where a
  row must be created.
- **module_budget**: `writes/config.py` is at 379 lines, `crud/locations.py` at
  325 - both far under the 1000-line cap; no extraction needed, do not start one.

## RECON needed at exec time (verify before writing)
- Read `scripts/migrate_v1_84_location_type_catalog.py` in full and reuse its
  idempotence idiom verbatim (`inspect(engine)`, table/index presence, the
  `applied` list, the print block). Confirm how it enumerates worlds - the seed
  must iterate the same way, not invent a world lookup.
- Confirm the exact format of the `Current schema version:` line
  (`world-engine-schema.md:3`) and the newest-first ordering rule stated at
  `world-engine-schema-changelog.md:1-8`.
- Grep `scripts/` for a prior `ADD COLUMN` migration and match its column-presence
  detection; SQLite `ALTER TABLE ADD COLUMN` cannot be re-run safely.
- Confirm `changed_by` is currently a signature-only parameter of
  `upsert_location_type` (it appears unused in the body). Do NOT start threading
  history through it; report the finding only.
- Confirm whether any verify check parses the schema version or the catalog's
  column set (`schema_partition.py`, `schema_0024.py`, `claude_md_contract.py`)
  and would need the new columns declared. If one does, update it in THIS commit.
- Confirm the SQLModel field style used elsewhere for nullable REAL columns
  (e.g. `Location.bounds_width`, `canon.py`) and match it exactly.

## Done means
- [ ] `world-engine-schema.md` shows the new version on line 3; the
      `location_type_catalog` DDL block lists both columns with the note.
- [ ] `world-engine-schema-changelog.md` has the new entry at the top.
- [ ] Deployment sequence, run in this order and recorded in the commit message:
      1. `python scripts/backup.py` (confirm a new file in
         `~/.world_engine/backups/`)
      2. `python scripts/migrate_v1_85_location_type_templates.py`
      3. re-run the migration: it reports nothing to do and exits 0
      4. `python tooling/verify/run.py --ticket TICKET-0040` (the checks touching
         this step: `location_type_classified`, `single_canon_write`,
         `function_length`, `module_budget`)
- [ ] `GET /api/location-types` returns `room` with
      `default_width: 6.0, default_height: 5.0`, and every other seeded type with
      both keys `null`.
- [ ] `POST /api/location-types` with `{name: "room", default_width: 10, default_height: 8}`
      updates the template; posting the same name again with both fields omitted
      leaves 10 x 8 intact (never-overwrite-with-NULL).
- [ ] `POST /api/location-types` with only `default_width` returns 422 carrying
      the both-or-neither message; with `default_width: 0` returns 422 carrying
      the positivity message.
- [ ] No `Location` row's `bounds_width`/`bounds_height` changed value during this
      step (spot-check one location before/after).
- [ ] `/review-step` clean.

## Docs to update
- `world-engine-schema.md` + `world-engine-schema-changelog.md` (step 2 above).
- `ARCHITECTURE_DECISIONS.md`: new append-only section
  `## LOCATION TYPE SIZE TEMPLATES (BRIEF-0040-a, schema v1.85)` recording A1
  (the model produces no number), B1 (templates on the per-world catalog, not
  Python constants; no template -> NULL bounds -> no spatial mode, fail-closed),
  K2 (room-only seed at 6.0 x 5.0, never overwriting a decided value), the
  both-or-neither rule, and B4 as a NAMED DEFERRAL with its trigger condition
  (worlds populated enough for a median of >= 3 siblings to mean something).
- `CLAUDE.md`: extend the existing `location_type_catalog` sentence with the two
  template columns and the "birth-only, never retroactive" rule. Pointer-fresh,
  line-budgeted - one clause, not a paragraph.
