---
id: TICKET-0029
title: Obstacle geometry schema
type: feature
status: live-gate
created: 2026-07-16
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: small
brief_ids: [BRIEF-0029-a]
schema_version_touched: v1.80
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Give locations a spatial wall geometry the server can read to judge
movement, and the client can read to draw walls. No structure ships without
these two concrete readers (collision endpoint + canvas renderer), both in
this workstream."

First of four tickets in the spatial / Play mode workstream:
0029 obstacle geometry schema → 0030 collision authority →
0031 NPC spatial presence + proximity gate → 0032 canvas/WASD surface.

## Clarifications resolved (intake)

- **A1** — Two relational tables `obstacle` + `obstacle_vertex`
  (`vertex_order` int, unique `(obstacle_id, vertex_order)`), on the
  `agenda`/`agenda_step` precedent. Single-table-with-implicit-obstacle
  rejected (identity by convention = anti-pattern). No `kind`/`label`
  column: no reader exists.
- **B1** — Curated-config governance family (`faction_role` /
  `location_subculture` precedent): full-replace per location via new
  sanctioned site `writes/config.py::write_location_obstacles`, no
  `change_history`, tables added to `[CANON_TABLES]`.
- **C1** — Per-location local coordinate space, origin top-left, y DOWN
  (canvas-native), floats, nominal unit 1.0 = one world-meter. DISTINCT
  from `location.coord_x/coord_y` (world-map placement, v1.78).
- **C-b1** — Playable bounds as two nullable REAL columns on `location`
  (`bounds_width`, `bounds_height`); NULL = no spatial mode. Rejected:
  bounds-as-special-obstacle.
- **D'1** — Creator authoring surface = rectangle form rows (x, y, width,
  height) in the location sheet, one Save → `PUT /entities/{id}/geometry`;
  server expands `rect` shorthand into 4 clockwise vertices; endpoint
  contract is polygon-ready (generic `vertices` lists, ≥3, also accepted).
  Nia never writes raw JSON. Graphical editor deferred (0032 territory).
- **E** — Migration purely additive (two tables + two nullable columns),
  danger class `migration` sequence stands: backup → migration
  (column-existence guards) → verify → live smoke through the new form.
  No demo-data seed in the migration.
- Locked upstream (workstream doc): movement transient, never persisted
  (Q1); geometry IS persistent canon; vertex storage never (x,y,w,h) in
  schema (B2); polygon migration must be additive, never a rewrite.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Migration `migrate_v1_80_obstacle_geometry.py` idempotent: second
      run reports already-applied, zero writes  -> live-gate script run
- [ ] `obstacle`, `obstacle_vertex` exist; `idx_obstacle_vertex_order`
      UNIQUE on (obstacle_id, vertex_order); `location.bounds_width` /
      `bounds_height` REAL nullable  -> verify/checks/schema-level
- [ ] `single_canon_write.py` green with both tables in `[CANON_TABLES]`
      and the 23rd sanctioned site  -> verify/checks/single_canon_write.py
- [ ] `json_ui_boundary.py` green (vertices relational, no JSON column)
      -> verify/checks/json_ui_boundary.py
- [ ] `schema_partition.py` green with v1.80 newest-first changelog entry
      -> verify/checks/schema_partition.py
- [ ] Full verify suite green

### Live  ->  human gate (Nia)
- [ ] Location sheet: set bounds 40 × 30, add block (5, 5, 10, 2), Save,
      reload → panel shows same bounds and rect row
- [ ] GET location detail returns
      `geometry.obstacles[0].vertices == [[5,5],[15,5],[15,7],[5,7]]`
- [ ] PUT with a 2-vertex obstacle → 422, nothing written; rect width 0
      → 422; bounds_width -1 → 422; non-location entity → 404
- [ ] Full-replace: save with the block row removed → 0 obstacle /
      obstacle_vertex rows for that location
