# BRIEF — Step "Dedicated JSON columns: secrets to TEXT, coordinates to columns, subculture and fundamental_laws to tables"

## Context

BRIEF-0025-a removed the `entity.metadata` blob. Four dedicated JSON
columns remain UI-visible as raw JSON textareas in the cockpit:
`character.secrets`, `location.subculture`, `location.coordinates`, and
`world.fundamental_laws` (creation form). Locked decisions: secrets becomes
plain TEXT (B1 — no reader, structure never used), coordinates becomes two
REAL columns (A1), subculture becomes a `location_subculture` table whose
`is_hidden` flag makes the secret slice structurally excluded instead of
cohabiting with public keys in one blob (C1), fundamental_laws becomes a
position-ordered `world_law` table, resolving the string-vs-array shape
inconsistency between the manual form and the AI draft (D1).

## Scope IN

1. `src/world_engine/models.py` — `Character.secrets` becomes
   `secrets: Optional[str] = None` (plain TEXT). Keep the existing
   creator-meta-narrative comment, append one line:
   `# Plain text since TICKET-0025 (B1): no reader ever consumed structure.`

2. `src/world_engine/models.py` — `Location`: remove `coordinates` JSON
   column; add `coord_x: Optional[float] = None` and
   `coord_y: Optional[float] = None` with comment:
   `# Map position (schema vX.YY, TICKET-0025) — was coordinates JSON {x,y}. NULL = unplaced.`

3. `src/world_engine/models.py` — new table `LocationSubculture`
   (`__tablename__ = "location_subculture"`):
   - `id` (uuid pk), `world_id` (FK world.id, not null), `location_id`
     (FK entity.id, not null), `key: str`, `value: str`,
     `is_hidden: bool` (server default 0).
   - Unique index `idx_location_subculture_key` on
     `(location_id, text("key COLLATE NOCASE"))`.
   - Header comment verbatim:
   ```
   # location_subculture  (ambient culture lines, schema vX.YY,
   # TICKET-0025, BRIEF-0025-b — replaces location.subculture JSON)
   #
   # One row per key. is_hidden = 1 rows are creator-only: every
   # non-creator read path filters is_hidden = 0 AT QUERY CONSTRUCTION —
   # exclusion is structural, never instructional. Curated config
   # (faction_role family): no change_history, full-replace writes via
   # writes.write_location_subculture only.
   ```
   Remove `Location.subculture`.

4. `src/world_engine/models.py` — new table `WorldLaw`
   (`__tablename__ = "world_law"`): `id` (uuid pk), `world_id` (FK
   world.id, not null), `position: int` (server default 0), `text_: str`
   mapped to column name `text` if the name collides with the SQLAlchemy
   import — executor picks the non-colliding mapping and documents it in
   the model comment. Unique index on `(world_id, position)`. Remove
   `World.fundamental_laws`. Header comment: curated config family, no
   change_history, written via `writes.write_world_laws` only.

5. `src/world_engine/writes.py` — two full-replace helpers, same shape as
   `write_npc_prices`:
   - `write_location_subculture(db, *, location_entity, rows: list[dict], changed_by)` —
     each item `{"key": str, "value": str, "is_hidden": bool}`; validates
     non-empty key/value, casefold-duplicate keys rejected before write.
   - `write_world_laws(db, *, world, laws: list[str], changed_by)` — strips
     empties, positions = list order.

6. `src/world_engine/context.py` — both subculture readers switch to
   queries with structural exclusion:
   - Setting line (~311): `select(LocationSubculture).where(location_id ==
     ..., key == "values", is_hidden == False)`.
   - Perception slice (~553): `where(key.in_(_SAFE_SUBCULTURE_KEYS),
     is_hidden == False)`. `_SAFE_SUBCULTURE_KEYS` stays as the allow-list
     constant; the `is_hidden` filter is added defense in depth.
   Rendered prompt text stays byte-identical for equivalent data.

7. `src/world_engine/region_author.py` (~391) and
   `src/world_engine/entity_author.py` (~587): read `world_law` rows
   ordered by `position` and join them exactly as today
   (numbered `"{i+1}. {law}"` in entity_author; plain join in
   region_author) — output strings unchanged for equivalent data.

8. `src/world_engine/cockpit/crud.py`:
   - Character registry: `secrets` field becomes
     `{"name": "secrets", "label": "Secrets (creator-only)", "kind": "textarea"}`.
   - Location registry: remove the `subculture` and `coordinates` JSON
     fields; add `{"name": "coord_x", "label": "Map X", "kind": "number", "float": True}`
     and the same for `coord_y`. Extend `_coerce_field`'s `"number"` branch:
     when `field.get("float")` is true, coerce with `float(raw)` (no
     min/max clamping change otherwise).

9. `src/world_engine/cockpit/app.py`:
   - Location entity detail response gains
     `"subculture_rows": [{key, value, is_hidden}, ...]`.
   - New endpoint `PUT /api/entities/{id}/subculture` accepting
     `{"rows": [...]}` -> `write_location_subculture`.
   - `create_world` (~2206): `WorldCreateBody.fundamental_laws: str` keeps
     its shape (one law per line, textarea); the endpoint splits on
     newlines, strips empties, and calls `write_world_laws`. World detail
     responses that carried `fundamental_laws` now assemble the joined
     string from rows (client shape preserved).
   - AI world-draft accept path: a list-shaped `fundamental_laws` draft maps
     one item per row (no join-then-split round trip).

10. `src/world_engine/cockpit/index.html`:
    - Location form: subculture textarea replaced by a rows editor (key
      input, value input, hidden checkbox, add/remove line) modeled on the
      Tarifs editor; saves via the new PUT endpoint.
    - AI location authoring accept (~6132): public keys map to visible
      rows; `draft.secret.subculture_hidden` maps to ONE row
      `{key: "hidden", value: <text>, is_hidden: true}` — the read-only
      notes rendering of the full subculture stays as is.
    - Map (~7936, ~8082): nodes read `coord_x` / `coord_y`; the null filter
      uses `coord_x == null`; drag-save PUTs the two fields through the
      normal entity update (the read-merge-write comment block is deleted —
      two scalar columns need no merge discipline).
    - Character form: secrets renders as a plain textarea.

11. Migration script `scripts/migrate_vX_YY_dedicated_json_columns.py`,
    ONE transaction, idempotent (skips once `location_subculture` exists),
    modeled on 0024-d:
    a. Read-only validation pass first, fail-closed: any
       `location.subculture` that is non-NULL and not a flat dict of
       string/number values aborts, listing location ids; any
       `location.coordinates` that is not NULL or `{x: num, y: num}`
       aborts likewise.
    b. `character.secrets`: values that are JSON dicts/lists are rewritten
       as `json.dumps(value, ensure_ascii=False, indent=2)` text; JSON
       strings are unquoted to their inner text; NULL stays NULL. (SQLite
       stores both in the same column type — this is a data rewrite, not a
       DDL change.)
    c. `location_subculture` rows from each subculture dict: key `hidden`
       -> `is_hidden = 1`; every other key -> `is_hidden = 0`; values
       coerced to str. Then drop `location.subculture`.
    d. `coord_x` / `coord_y` from `coordinates.x` / `.y`; drop
       `location.coordinates`.
    e. `world_law` rows: existing `fundamental_laws` string split on
       newlines (JSON-array values: one row per item), positions in order;
       drop `world.fundamental_laws`.
    f. SQLite >= 3.35 guard for the three DROP COLUMNs.

12. `scripts/seed_pilot.py`: seed subculture/coordinates/fundamental_laws
    through the new helpers and columns.

## Scope OUT

- `goal_prerequisite`, `event_entity`, `prompt_variable`, the
  `json_ui_boundary` check, the ARCHITECTURE_DECISIONS exception registry —
  BRIEF-0025-c.
- No expansion of `_SAFE_SUBCULTURE_KEYS` — the allow-list stays
  `("values",)`; do not surface other public keys to prompts "while at it".
- No structured modeling of secrets (B2 was rejected: no reader).
- No renaming of the `hidden` subculture key during migration — it becomes
  a row with `is_hidden = 1`, key preserved.
- No coordinates beyond x/y (no z, no map-id) — the map is single-plane.
- No world_law editing UI beyond the create form (editing laws of an
  existing world is a future ticket; the table makes it cheap later).
- No change_history on the three new tables (curated config family).
- Do not touch `magic_status` exclusion or any other perception rule in
  context.py beyond the two named readers.

## Invariants to defend

- Exclusion is structural, never instructional: the `is_hidden = 0` filter
  MUST live in query construction in context.py — never as a post-filter in
  Python on fully-fetched rows, and never as prompt instruction. This is
  the doctrinal payoff of C1; getting it wrong reproduces the disease in a
  new shape.
- Secrets doctrine: `character.secrets` remains read by NO assembler — the
  type change must not tempt a "it's just text now" prompt injection.
- Two sanctioned canon-write paths: all three new surfaces write through
  the new writes.py helpers only.
- Fail-closed migration (11a): unexpected shapes abort everything.
- Prompt byte-stability: subculture and fundamental_laws prompt fragments
  are identical pre/post for equivalent data (guards against silent prompt
  drift — prompt_lean check must stay green).

## Done means

- [ ] Migration on a live-DB copy completes; re-run is a no-op.
- [ ] `PRAGMA table_info(location)` shows `coord_x`/`coord_y`, no
  `subculture`, no `coordinates`; `PRAGMA table_info(world)` shows no
  `fundamental_laws`; `location_subculture` and `world_law` populated to
  match pre-migration data (spot-check the pilot tavern's `values` key and
  Verkhaal's law list, order preserved).
- [ ] A fixture location with a non-dict subculture aborts the migration
  fail-closed, nothing written.
- [ ] Character secrets edited as plain text persists; a pre-existing JSON
  secret reads back as legible indented text.
- [ ] Location form: subculture rows editor add/edit/remove/hidden-toggle
  persists; no JSON textarea anywhere in the location form.
- [ ] Map: dragging a node persists `coord_x`/`coord_y`; unplaced nodes
  (NULL) still land in the fallback layout.
- [ ] Prompt preview at a location with a hidden subculture row: the hidden
  value appears in NO preview (player context, NPC context, tick briefing);
  the `values` line renders identically to pre-migration.
- [ ] World creation with three laws on three lines yields three `world_law`
  rows, positions 0..2; region-author prompt renders them in order.
- [ ] `python tooling/verify/run.py` green.
- [ ] Live deployment sequence: `python scripts/backup.py` -> migration ->
  verify run -> live smoke (subculture edit + map drag + world create).
- [ ] /review-step and /close-step runs.

## Docs to update

- `world-engine-schema-changelog.md`: entry for the version bump —
  `secrets` type change, `coord_x`/`coord_y` added, `location_subculture`
  and `world_law` created, three columns DROPPED.
- `world-engine-schema.md`: bump `Current schema version:` header only.
- `ARCHITECTURE_DECISIONS.md`: short entry "subculture hidden slice is now
  structurally excluded (is_hidden filter at query construction)".
- `CLAUDE.md`: no change (invariant line lands in -c).
