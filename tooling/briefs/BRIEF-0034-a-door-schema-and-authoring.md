# BRIEF — Step "Door schema, write path and creator authoring" (TICKET-0034, BRIEF-0034-a)

## Context

The spatial workstream can draw a location, judge movement against its walls
(`geometry.clip_segment`), place NPCs in it (`placement.derive_positions`) and
let the player walk with WASD — but it cannot leave the room. Spawn is a
transitional center point, flagged verbatim in the code:
`cockpit/index.html:3311` — *"TRANSITIONAL SPAWN (TICKET-0032): fixed center
until the door chantier introduces spawn-at-door"*. TICKET-0034 is that
chantier.

This step ships storage, the sanctioned write path, the creator read helper
and the authoring panel — nothing that resolves, judges or moves. It is the
exact analogue of BRIEF-0029-a for a second geometry table.

Locked decisions carried here: A1 one row per side, unique index
`(location_id, target_location_id)`, pairing derived not defended; A1
escalation guard — `door` is terminal, no FK may point at `door.id`; B1 the
door is the spatial manifestation of a `connects_to` edge, rejected at write,
filtered at read.

## Scope IN

1. **Model — `src/world_engine/models/canon.py`**: one new table, placed
   directly after `ObstacleVertex` (`models/canon.py:288`).

   ```python
   class Door(SQLModel, table=True):
       __tablename__ = "door"
       __table_args__ = (
           Index(
               "idx_door_target", "location_id", "target_location_id",
               unique=True,
           ),
       )

       id: str = Field(default_factory=_uuid, primary_key=True)
       world_id: str = Field(foreign_key="world.id", nullable=False)
       location_id: str = Field(foreign_key="entity.id", nullable=False)
       target_location_id: str = Field(foreign_key="entity.id", nullable=False)
       x: float
       y: float
       created_at: datetime = _created_ts()
   ```

   One index only: `idx_door_target` leads on `location_id`, so a separate
   `idx_door_location` would be dead weight (`Obstacle` carries one only
   because it has no other index).

   Doctrine comment above `Door`, verbatim:

   ```
   # -----------------------------------------------------------------------------
   # door  (inter-location passage, spatial side, schema v1.81, TICKET-0034,
   # BRIEF-0034-a)
   #
   # ONE ROW PER SIDE (A1). A passage between A and B is two rows: (A -> B)
   # and (B -> A), each carrying the point in ITS OWN location's local
   # space. Pairing is DERIVED at arrival — "the door of B that points back
   # at A" — and made unambiguous BY idx_door_target, not by a defended
   # invariant. The consequence is deliberate: at most one door per ordered
   # pair of locations.
   #
   # TERMINAL BY CONTRACT: no table may take a foreign key on door.id. The
   # A1 -> A2 escalation (one `passage` row carrying both endpoints, needed
   # the day two passages must join the same pair of locations) is a
   # mechanical self-join ONLY while nothing references a door by id. This
   # is enforced by tooling/verify/checks/door_terminal.py, not by memory.
   #
   # A door is the SPATIAL MANIFESTATION of a connects_to edge, never its
   # source (B1): write_location_doors rejects a target with no active
   # connects_to edge, and the play-side reader (cockpit/spatial_doors.py)
   # filters doors whose edge later disappeared. The map stays the world's
   # traversability truth. Neither side cascades or deletes.
   #
   # Curated config (faction_role family): no change_history, full-replace
   # writes via writes.write_location_doors only.
   #
   # COORDINATE SPACE: per-location local coordinates — the obstacle_vertex
   # space (origin top-left, x rightward, y DOWNWARD, 1.0 = one
   # world-meter), NOT location.coord_x / coord_y (world map). x, y is the
   # door's point in `location_id`'s space; the counterpart row carries its
   # own point in the counterpart's space. NOTHING here judges whether that
   # point is inside a wall — see write_location_doors' NOTE.
   # -----------------------------------------------------------------------------
   ```

2. **Migration — `scripts/migrate_v1_81_door_geometry.py`**, modeled on
   `scripts/migrate_v1_80_obstacle_geometry.py` (docstring, `SRC` path
   bootstrap, single transaction). Purely additive:
   a. Create table `door` and index `idx_door_target`.
   b. Guards check **table existence and index existence independently** — a
      partially applied prior run completes the missing part, never skips
      wholesale (CLAUDE.md, v1.77 lesson; v1.80's own guard shape).
   c. Idempotent: a fully applied run reports "already applied", zero writes.
   d. No data copy, no seed rows, no backfill — there is nothing to
      transform.

3. **Write path — `src/world_engine/writes/config.py::write_location_doors`**,
   placed after `write_location_obstacles` (`writes/config.py:135`),
   mirroring its full-replace shape.

   Signature:
   `(db, *, world_id, location_id, doors: list[dict], changed_by) -> list[Door]`
   where each item is `{"target_location_id": str, "x": float, "y": float}`.

   Validation before any write (all-or-nothing, `ValueError` on every
   failure, message prefixed `write_location_doors:`):
   - `target_location_id` non-empty after strip;
   - `target_location_id != location_id` (no door to self);
   - `x` and `y` are finite floats (reject NaN/inf);
   - no duplicate `target_location_id` within one payload (defense in depth
     — `idx_door_target` is the structural guard);
   - the target `entity` exists, has `type == "location"`, `status == "active"`,
     and `world_id == world_id`;
   - **B1 gate**: an active `connects_to` `relation` row exists touching both
     `location_id` and `target_location_id`, in either column order (the
     relation is `direction='mutual'`; read both orders exactly as
     `play.py:847 _location_neighbours` does — do NOT refactor the two to
     share code, decision D1 of BRIEF-19 stands, this is the fourth
     `connects_to` reader).

   Then delete-then-insert inside the caller's transaction, the
   `write_location_obstacles` pattern:
   `DELETE FROM door WHERE location_id = :location_id`, then fresh rows.
   Caller adds the returned rows to the session and commits.

   NOTE comment above the function, verbatim:

   ```
   # NO GEOMETRY VALIDATION HERE, BY DESIGN. This site does not check that
   # the door's point is inside bounds or outside an obstacle — not as an
   # oversight, and not merely because "the collision endpoint is the sole
   # judge of space" (write_location_obstacles' rule). A write-time
   # geometry check could not stay true: the creator may edit bounds or
   # obstacles afterwards and strand a door inside a wall without touching
   # this table. Only a READ-TIME fallback is sound, and it lives in
   # cockpit/spatial_doors.py::resolve_spawn (BRIEF-0034-b). The relational
   # gates above (target active, connects_to live) can go stale the same
   # way, which is why B1 pairs them with a read-time filter at the same
   # site. REPORT ONLY if this feels wrong during execution; do not add a
   # geometry check.
   ```

4. **Canon-write policy — `tooling/verify/canon_write_policy.txt`**:
   a. add `door` to `[CANON_TABLES]`;
   b. add one site to `[ALLOWED_SITES]`:
      `src/world_engine/writes/config.py::write_location_doors        door`
      — the 24th sanctioned site, curated-config full-replace family. Add a
      comment above it in the existing idiom:
      `# TICKET-0034, BRIEF-0034-a: write_location_doors is the 24th site — door geometry full-replace, curated-config family (obstacle precedent).`

5. **Read helper — `src/world_engine/cockpit/crud/entities.py`**, placed
   directly after `_location_geometry_dict` (`crud/entities.py:329`):

   ```python
   def _location_doors_rows(location_id: str, db: DbSession) -> list[dict]:
       """`door` rows for one location, as [{id, target_location_id,
       target_name, x, y, edge_live}, ...] (TICKET-0034, BRIEF-0034-a).
       Ordered by target_name (stable panel order).

       CREATOR-FACING: returns EVERY row, including doors whose
       connects_to edge or target has since died — `edge_live: false` is
       exactly what lets the creator see and fix an orphan. Structural
       exclusion for play-side reads lives in cockpit/spatial_doors.py's
       query construction, not here (the location_subculture `is_hidden`
       precedent at :316)."""
   ```

   `edge_live` is `True` when the target entity is an active location of the
   same world AND an active `connects_to` relation touches both — the same
   predicate `write_location_doors` gates on. `target_name` falls back to the
   raw id when the entity is gone.

6. **Read payload — same file**: extend the location detail payload with
   `doors: [...]` from `_location_doors_rows`, at every site that already
   includes `subculture_rows` / `geometry` (three sites; locate them by the
   `subculture_rows` key — the BRIEF-0029-a line numbers have drifted).

7. **Write endpoint — same file**, `PUT /entities/{entity_id}/doors`,
   mirroring `set_location_geometry` (`crud/entities.py:710`) — a SEPARATE
   endpoint, not a widening of `/geometry` (the subculture/geometry
   precedent: one concern, one full-replace endpoint, one Save button).

   ```python
   class DoorIn(BaseModel):
       target_location_id: str
       x: float
       y: float

   class LocationDoorsBody(BaseModel):
       doors: list[DoorIn] = []
   ```

   Handler: 404 if the entity is not a location; call `write_location_doors`
   inside a try/except `ValueError` -> `HTTPException(422, str(exc))`; one
   `db.commit()`; return the same result shape `set_location_geometry`
   returns, with `doors` from `_location_doors_rows` included.

8. **Creator frontend — `src/world_engine/cockpit/index.html`** (advisory
   tier, H1): in the location sheet, a "Portes" panel below the "Spatial
   geometry" panel, same visual pattern:
   - the panel's row set is driven by the location's **`connects_to`
     neighbours**, not by free text: one row per neighbour, each with the
     neighbour's name as a static label and two numeric inputs (`x`, `y`).
     Blank x or y = no door toward that neighbour (the row is simply not
     sent). This is why the panel cannot author a door toward a
     non-neighbour: the choice surface has no such row.
   - neighbours come from the `relations` array already in the location
     detail payload (`_list_relations`) — filter `type === 'connects_to'`
     and take the other endpoint. No new endpoint.
   - a door row whose payload entry has `edge_live: false` (an orphan: its
     edge died after authoring) renders ABOVE the neighbour rows, read-only,
     with the destination id and the text `⚠ lien connects_to absent — cette
     porte est ignorée en jeu. Supprimez-la ou recréez le lien.` and a remove
     button. Removing it = not sending it on the next save (full-replace does
     the rest).
   - one Save button sending the whole panel to `PUT /entities/{id}/doors`.
   - if the location has no `connects_to` neighbour, the panel shows
     `Aucun lieu adjacent — créez une relation connects_to d'abord.` and no
     Save button.

9. **Docs** (see Docs to update).

## Scope OUT

- **Door resolution, `DOOR_RANGE`, spawn offset, `cockpit/spatial_doors.py`,
  `placement.spawn_point`** — BRIEF-0034-b. Nothing in this step computes a
  distance or resolves an arrival anchor.
- **`GET /api/spatial/spawn`, `doors_in_range` on the proximity endpoint** —
  BRIEF-0034-b.
- **`POST /api/spatial/travel`, `_perform_travel`'s `origin_location_id`** —
  BRIEF-0034-c. This step's endpoint writes `door` rows only; it moves nobody.
- **Canvas door rendering, spawn-at-door, the "Aller à X" button** —
  BRIEF-0034-d. `index.html:3311`'s transitional center spawn stays exactly
  as it is in this step.
- **A `label` column on `door`** ("porte nord"). No reader: the canvas will
  label doors with the destination entity's name (BRIEF-0034-d). Same rule
  that kept `kind`/`label` off `obstacle` at BRIEF-0029-a — no column without
  a concrete consumer.
- **`width` / orientation columns** — the walk-through chantier (C3) needs
  them to punch an opening in the edge set. Additive then; no reader now.
- **Locked doors, `access_level` gating, one-way doors** — no reader, named
  deferrals of TICKET-0034.
- **Two passages between the same pair of locations** — structurally excluded
  by `idx_door_target`; that index IS the A1 -> A2 trigger. Do not relax it.
- **Punching a hole in bounds or obstacle edges** — C1 is a proximity
  affordance; the wall stays solid, the door is a marker.
- **Any FK onto `door.id`** — the A1 escalation guard. `door_terminal.py`
  (BRIEF-0034-b) enforces it; do not pre-empt it here.
- **Cascading door deletion when a `connects_to` relation is deleted** — B1
  is reject-at-write + filter-at-read. No cascade, no orphan sweep.
- **Refactoring `_location_neighbours` / `GET /api/locations/graph` to share
  the fourth `connects_to` reader** — decision D1 (BRIEF-19) stands. REPORT
  ONLY.
- **Any refactor of `crud/entities.py`, `writes/config.py` or the geometry
  panel while in there** — REPORT ONLY.

## Invariants to defend

- **Single canon-write path.** `door` writes exist ONLY in
  `write_location_doors`; the endpoint is a caller, never a writer. The
  temptation is a "convenient" direct `db.add(Door(...))` in the endpoint,
  or a single-row PATCH for one door. `single_canon_write.py` must be green
  with the updated closed list.
- **Full-replace IS the write shape for this family** (CLAUDE.md:282). Do NOT
  add an ad-hoc UPDATE or per-row DELETE path. The CLAUDE.md hard-delete list
  must gain `write_location_doors` / `set_location_doors` alongside the other
  four full-replace config deletes — an unlisted hard-delete path fails
  `single_canon_write.py` by design.
- **JSON UI boundary.** Doors are relational rows. The temptation is a
  `doors` JSON column on `location` (it is "just a few points"). Forbidden —
  `json_ui_boundary.py` guards it, and it is the point of decision A1.
- **Coordinate-space confusion.** `location.coord_x/coord_y` (world map) vs
  the intra-location space `door.x/y` lives in. The doctrine comment in
  Scope IN 1 is the defense; keep it verbatim.
- **`connects_to` is location map topology, never a social signal**
  (CLAUDE.md:210). The new reader in `write_location_doors` reads it as
  topology only — never `intensity`, which is a meaningless structural
  default.
- **Migration guards by column/index existence, not table existence**
  (CLAUDE.md, v1.77 lesson).
- **Commit before touching any canon-writing path** (CLAUDE.md:166).

## Done means

- [ ] `python scripts/migrate_v1_81_door_geometry.py` on a backup-fresh DB:
      creates `door` + `idx_door_target`; second run reports already-applied,
      zero writes.
- [ ] `sqlite3` inspection: `idx_door_target` is UNIQUE on
      `(location_id, target_location_id)`; no other index on `door`.
- [ ] Full verify suite green, including `single_canon_write.py` with `door`
      in `[CANON_TABLES]` and the 24th site, and `schema_partition.py` with
      the v1.81 changelog entry.
- [ ] Live smoke (danger class `migration`: backup -> migration -> verify ->
      smoke): two locations A and B linked by `connects_to`, both with bounds
      set. Open A's sheet -> "Portes" panel lists B -> set `x=2, y=15` ->
      Save -> reload -> the panel shows `2, 15` on B's row.
- [ ] `GET /entities/{A}` returns
      `doors == [{id, target_location_id: B, target_name: "<B's name>", x: 2.0, y: 15.0, edge_live: true}]`.
- [ ] Same round-trip on B's sheet toward A (the two sides are authored
      independently; neither write touches the other's row).
- [ ] Full-replace semantics: clear A's x/y and Save -> `door` row count for
      A is 0; B's row is untouched.
- [ ] `PUT /entities/{A}/doors` with a `target_location_id` that has no
      `connects_to` edge -> 422, nothing written.
- [ ] Same endpoint with `target_location_id == A` -> 422; with a
      soft-deleted target -> 422; with the same target twice in one payload
      -> 422; with `x: "NaN"` -> 422.
- [ ] PUT against a non-location entity -> 404.
- [ ] Orphan display: with A's door toward B saved, delete the `connects_to`
      relation -> reload A's sheet -> the door renders in the orphan strip
      with the `⚠ lien connects_to absent` text; the row still exists in the
      DB (nothing cascaded).
- [ ] A location with no `connects_to` neighbour shows the empty-state text
      and no Save button.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md`: `door` table entry + `idx_door_target`, the
  coordinate-space NOTE and the TERMINAL BY CONTRACT note (verbatim from the
  doctrine comment), version bump to v1.81.
- `world-engine-schema-changelog.md`: newest-first v1.81 entry (TICKET-0034,
  BRIEF-0034-a) — Claude Code owns the final version number; v1.81 is the
  expected next.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: append the 0034 decision
  block for this step — A1 one row per side with derived pairing made
  unambiguous by the unique index; the A1 -> A2 named deferred escalation,
  its trigger (a second passage between the same pair) and its precondition
  (`door` stays terminal); B1 reject-at-write + filter-at-read with the
  staleness argument for why no geometry check exists at the write site.
- `tooling/verify/canon_write_policy.txt` (Scope IN 4 — the policy file IS a
  doc).
- `CLAUDE.md`: extend the full-replace config-delete sentence (`CLAUDE.md:282`)
  with `write_location_doors` / `set_location_doors`. Add one standing line:
  *"No table may take a foreign key on `door.id` (A1 escalation guard,
  TICKET-0034) — enforced by `door_terminal.py`."*
