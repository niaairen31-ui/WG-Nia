# BRIEF — Step "Obstacle geometry schema" (TICKET-0029, BRIEF-0029-a)

## Context

Play mode is node-logical today: locations are transition targets via
`enter_location` (`src/world_engine/gathering.py:359`) with no internal
geometry. The spatial workstream (tickets 0029→0032) needs persistent wall
geometry the server can judge movement against (collision endpoint, ticket
0030) and the client can draw (canvas renderer, ticket 0032). This step
ships the storage, the sanctioned write path, and a minimal creator
authoring surface — nothing that moves.

Locked decisions: dedicated `obstacle` table (A2 of the workstream doc);
ordered vertex storage, never (x,y,w,h) in the schema (B2); two relational
tables `obstacle` + `obstacle_vertex` on the `agenda`/`agenda_step`
precedent (A1); curated-config governance family, full-replace, no
`change_history` (B1); per-location local coordinates, origin top-left,
y-down, floats, nominal unit 1.0 = one world-meter (C1); playable bounds as
two nullable columns on `location` (C-b1); creator authors rectangles
through a form, never raw JSON (D'1).

## Scope IN

1. **Models — `src/world_engine/models/canon.py`**: two new tables,
   placed directly after `LocationSubculture`.

   ```python
   class Obstacle(SQLModel, table=True):
       __tablename__ = "obstacle"
       __table_args__ = (Index("idx_obstacle_location", "location_id"),)

       id: str = Field(default_factory=_uuid, primary_key=True)
       world_id: str = Field(foreign_key="world.id", nullable=False)
       location_id: str = Field(foreign_key="entity.id", nullable=False)
       created_at: datetime = _created_ts()

   class ObstacleVertex(SQLModel, table=True):
       __tablename__ = "obstacle_vertex"
       __table_args__ = (
           Index(
               "idx_obstacle_vertex_order", "obstacle_id", "vertex_order",
               unique=True,
           ),
       )

       id: str = Field(default_factory=_uuid, primary_key=True)
       obstacle_id: str = Field(foreign_key="obstacle.id", nullable=False)
       vertex_order: int
       x: float
       y: float
   ```

   Doctrine comment above `Obstacle`, verbatim:

   ```
   # -----------------------------------------------------------------------------
   # obstacle / obstacle_vertex  (intra-location wall geometry, schema v1.80,
   # TICKET-0029, BRIEF-0029-a)
   #
   # Curated config (faction_role family): no change_history, full-replace
   # writes via writes.write_location_obstacles only. One obstacle = one
   # closed polygon, stored as ordered vertex rows (agenda_step.step_order
   # precedent) — NEVER a JSON list. v1 obstacles are 4-vertex rectangles;
   # real polygons later add vertex rows only, never a schema rewrite.
   #
   # COORDINATE SPACE: per-location local coordinates. Origin at the
   # top-left of the playable area, x rightward, y DOWNWARD (canvas-native).
   # Nominal unit: 1.0 = one world-meter. This space is DISTINCT from
   # location.coord_x / coord_y (v1.78), which place the location on the
   # WORLD map — never mix the two. Rectangle→vertex expansion emits the 4
   # corners CLOCKWISE from the top-left corner (declared convention, not
   # structurally enforced).
   # -----------------------------------------------------------------------------
   ```

2. **`location` bounds columns — same file**, on the `Location` model
   (`models/canon.py:209`), after `coord_x`/`coord_y`:

   ```python
   # Playable-area bounds for the intra-location obstacle space (schema
   # v1.80, TICKET-0029). NULL = this location has no spatial mode.
   # Same local space as obstacle_vertex, NOT the world-map coords above.
   bounds_width: Optional[float] = None
   bounds_height: Optional[float] = None
   ```

3. **Migration — `scripts/migrate_v1_80_obstacle_geometry.py`**, modeled
   on `migrate_v1_76_faction_role_table.py` (docstring, `SRC` path bootstrap,
   single transaction). Purely additive:
   a. Create `obstacle`, `obstacle_vertex`, and both indexes.
   b. `ALTER TABLE location ADD COLUMN bounds_width REAL` and
      `bounds_height REAL` (nullable, no default).
   c. Guards check **column existence** on `location` and table existence
      for the two new tables independently (a partially applied prior run
      must complete the missing parts, not skip). Idempotent: a fully
      applied run exits reporting "already applied", zero writes.
   d. No data copy, no seed rows, no validation pass needed (nothing to
      transform).

4. **Write path — `src/world_engine/writes/config.py::write_location_obstacles`**,
   mirroring `write_location_subculture` (`writes/config.py:59`):
   full-replace all `obstacle` + `obstacle_vertex` rows for one location.
   Signature: `(db, *, world_id, location_id, obstacles: list[list[tuple[float, float]]], changed_by)`.
   Validation before any write (all-or-nothing):
   - each obstacle has **≥ 3 vertices**;
   - every coordinate is a finite float (reject NaN/inf);
   - vertex order is emitted by enumeration (0..n-1), so contiguity is
     by construction.
   Delete-then-insert inside the caller's transaction, `location_subculture`
   pattern: `DELETE FROM obstacle_vertex WHERE obstacle_id IN (SELECT id
   FROM obstacle WHERE location_id = :location_id)` then `DELETE FROM
   obstacle WHERE location_id = :location_id`, then fresh rows.
   NO bounds-containment validation in v1 (the collision endpoint, ticket
   0030, is the sole judge of space) — REPORT ONLY if this feels wrong
   during execution, do not add it.

5. **Canon-write policy — `tooling/verify/canon_write_policy.txt`**: add
   `obstacle obstacle_vertex` to `[CANON_TABLES]` and one site to
   `[ALLOWED_SITES]`:
   `src/world_engine/writes/config.py::write_location_obstacles   obstacle obstacle_vertex`
   (23rd and only new sanctioned site; `location.bounds_*` writes flow
   through the existing creator CRUD location-update path, already
   sanctioned as creator CRUD).

6. **API — `src/world_engine/cockpit/crud/entities.py`**, mirroring the
   subculture pair (`_location_subculture_rows` at `:316`, PUT at `:639`):
   a. **Read**: extend the location detail payload with
      `geometry: {"bounds_width": float|null, "bounds_height": float|null,
      "obstacles": [{"id": str, "vertices": [[x, y], ...]}]}` — vertices
      ordered by `vertex_order`, everywhere the detail payload already
      includes `subculture_rows` (all three sites: `:403`, `:540`, `:595`
      region — locate by the `subculture_rows` keys, line numbers will
      have drifted).
   b. **Write**: `PUT /entities/{entity_id}/geometry` with body model
      `LocationGeometryBody`:
      ```
      bounds_width: Optional[float]
      bounds_height: Optional[float]
      obstacles: list[ObstacleIn]
      # ObstacleIn: EITHER {"vertices": [[x, y], ...]}  (≥3, polygon-ready)
      #             OR     {"rect": [x, y, width, height]}  (v1 UI shorthand)
      ```
      The endpoint normalizes every `rect` item server-side into 4 vertices
      clockwise from top-left — `(x,y), (x+w,y), (x+w,y+h), (x,y+h)` —
      rejects `rect` with `width <= 0` or `height <= 0` (422), then calls
      `write_location_obstacles` with vertex lists only, writes
      `bounds_width`/`bounds_height` onto the `location` row (both nullable;
      if present each must be `> 0`, else 422), one transaction, 404 if the
      entity is not a location (subculture-endpoint precedent).

7. **Creator frontend — `src/world_engine/cockpit/index.html`** (advisory
   tier, H1): in the location sheet, a "Spatial geometry" panel below the
   subculture editor, same visual pattern:
   - two numeric inputs for bounds (width, height), blank = null;
   - a row list of obstacles, each row four numeric inputs
     (`x`, `y`, `width`, `height`) + a remove button; an "Add block" button
     appends a blank row;
   - one Save button sending the whole panel to
     `PUT /entities/{id}/geometry`, obstacles as `rect` shorthand items;
   - on load, incoming vertex lists that are exactly 4 corners of an
     axis-aligned rectangle are displayed back as rect rows; any other
     polygon renders as a read-only row "polygon (N vertices)" that is
     preserved verbatim on save (round-trip its vertices unchanged).

8. **Docs** (see Docs to update).

## Scope OUT

- **Collision endpoint / movement judging** — ticket 0030. Nothing in this
  step evaluates a position against geometry.
- **NPC positions and the proximity endpoint** — ticket 0031.
- **Canvas renderer, WASD input, player circle** — ticket 0032. No canvas
  element ships here; the creator form is plain inputs.
- **Graphical obstacle editor** (click-to-draw, drag handles) — explicitly
  deferred at D'2; the v1 authoring surface is numeric rect rows only.
- **Polygon-editing UI** — the API accepts generic vertex lists; the UI
  does not expose them beyond the read-only round-trip in Scope IN 7.
- **Obstacle metadata** (`kind`, `label`, passable flags, materials) — no
  reader exists; do not add columns.
- **Bounds enforcement** (clamping movement inside bounds) — 0030's job.
- **`change_history` on obstacle tables** — B1 locked: curated config, none.
- **Building entry/exit, doors, multi-level/z** — deferred workstream-wide.
- **Seeding demo geometry in the migration** — the live smoke authors its
  rectangle through the new form instead; migrations stay data-free.
- **Any refactor of `crud/entities.py` or the subculture editor** while in
  there — REPORT ONLY.

## Invariants to defend

- **Single canon-write path**: `obstacle`/`obstacle_vertex` writes exist
  ONLY in `write_location_obstacles`; the endpoint is a caller, never a
  writer. `single_canon_write.py` must be green with the updated closed
  list — the risk is a "convenient" direct insert in the endpoint.
- **JSON UI boundary**: vertices are relational rows; the temptation is a
  `vertices` JSON column on `obstacle`. Forbidden — `json_ui_boundary.py`
  guards it, and the vertex table is the point of decision B2.
- **History is sacred, curated-config carve-out**: full-replace is the
  sanctioned exception for this family; do NOT add ad-hoc UPDATE paths to
  individual vertex rows.
- **Coordinate-space confusion**: `location.coord_x/coord_y` (world map)
  vs the new intra-location space. The doctrine comment in Scope IN 1 is
  the defense; keep it verbatim.
- **Migration guards by column existence, not table existence**
  (CLAUDE.md, v1.77 lesson).

## Done means

- [ ] `python scripts/migrate_v1_80_obstacle_geometry.py` on a backup-fresh
      DB: creates both tables + both indexes + both `location` columns;
      second run reports already-applied, zero writes.
- [ ] `sqlite3` inspection: `idx_obstacle_vertex_order` is UNIQUE on
      `(obstacle_id, vertex_order)`; `location` has `bounds_width`,
      `bounds_height` REAL nullable.
- [ ] Full verify suite green, including `single_canon_write.py` with the
      two new tables in `[CANON_TABLES]` and the 23rd site, and
      `schema_partition.py` with the v1.80 changelog entry.
- [ ] Live smoke (backup → migration → verify → smoke, danger class
      `migration`): open a location sheet in the creator cockpit → set
      bounds 40 × 30 → add block `(5, 5, 10, 2)` → Save → reload → the
      panel shows the same bounds and rect row.
- [ ] `GET` location detail returns
      `geometry.obstacles[0].vertices == [[5,5],[15,5],[15,7],[5,7]]`
      (clockwise from top-left) and the bounds.
- [ ] `PUT /entities/{id}/geometry` with a 2-vertex obstacle → 422, nothing
      written; with `rect` width `0` → 422; with `bounds_width: -1` → 422.
- [ ] Full-replace semantics: save the panel with the block row removed →
      `obstacle` and `obstacle_vertex` row counts for that location are 0.
- [ ] PUT against a non-location entity → 404.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md`: `obstacle` + `obstacle_vertex` table entries,
  the two `location` columns, the coordinate-space NOTE (verbatim from the
  doctrine comment), version bump to v1.80.
- `world-engine-schema-changelog.md`: newest-first v1.80 entry
  (TICKET-0029, BRIEF-0029-a) — Claude Code owns the final version number;
  v1.80 is the expected next.
- `ARCHITECTURE_DECISIONS.md`: append the 0029 decision block — A1 two
  relational tables on the agenda_step precedent; B1 curated-config
  governance; C1 coordinate space + C-b1 bounds columns; D'1 rect-form
  authoring over a polygon-ready vertex contract.
- `tooling/verify/canon_write_policy.txt` (Scope IN 5 — the policy file IS
  a doc).
- `CLAUDE.md`: no new standing rule expected; REPORT if execution reveals
  one.
