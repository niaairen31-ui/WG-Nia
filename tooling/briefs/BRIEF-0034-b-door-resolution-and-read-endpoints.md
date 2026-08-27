# BRIEF — Step "Door resolution module and read endpoints" (TICKET-0034, BRIEF-0034-b)

## Context

BRIEF-0034-a stored doors and let the creator author them. Nothing reads them
in play. This step builds the resolution layer: which doors of a location are
live, which are within reach of a transient position, and where the player
appears on arrival — the ticket's stated request, *"J'apparais toujours à la
porte"*.

Locked decisions carried here: K1 — `cockpit/spatial_doors.py` orchestrates
(touches the DB, calls `placement` and `geometry`, implements NO math), on the
`cockpit/spatial_presence.py:39` precedent; `DOOR_RANGE` and the spawn offset
live in `placement.py`, the sole placement/distance authority — two thresholds
are two values to calibrate, not two authorities. D1 — doors ride the existing
proximity call. F1 — spawn is resolved server-side. B1's read-time filter lands
here.

Everything in this step is read-only. Both endpoints belong in
`routes/spatial.py` and its zero-write register (`routes/spatial.py:4-10`)
holds. The writing endpoint is BRIEF-0034-c and lives elsewhere.

## Scope IN

1. **Constants — `src/world_engine/placement.py`**, beside
   `INTERACTION_RANGE` (`placement.py:29`):

   ```python
   DOOR_RANGE = 1.5           # world-meters; door reach (intake I/K1, calibrate at live gate)
   DOOR_SPAWN_OFFSET = 0.6    # world-meters; arrival stands this far off the door point
   ```

   Comment above `DOOR_RANGE`, verbatim:

   ```
   # Distinct from INTERACTION_RANGE by decision (TICKET-0034): reaching a
   # handle and being heard across a room are calibrated separately. They
   # are two THRESHOLDS on the same comparison, not two authorities — both
   # are compared by `distance` below, and no other module may compare
   # them.
   ```

2. **Spawn offset — same file**, a new function after
   `_derive_member_position` (`placement.py:89`), reusing the module's
   existing idiom (`_unit_floats`, `_in_bounds`, `MAX_ATTEMPTS`) rather than
   inventing a second one:

   ```python
   def spawn_point(
       door_id: str,
       anchor: Point,
       bounds: tuple[float, float],
       obstacles: list[geometry.Polygon],
   ) -> Point:
       """A standing point DOOR_SPAWN_OFFSET off `anchor`, in bounds and
       outside every obstacle. Deterministic rejection sampling on a ring
       around the anchor, seeded by `door_id` — the same shape as
       `_derive_member_position`'s ring around a centroid, and for the same
       reason: a door is a point with no orientation column (none exists —
       TICKET-0034 Scope OUT), so "inward" is not computable. It is
       DERIVED: candidates outside bounds or inside a wall are rejected, so
       the survivor is inside the room by construction.

       Total: never raises. Saturation returns `anchor` itself — the caller
       (cockpit/spatial_doors.py::resolve_spawn) is what decides a
       degenerate anchor falls back to center."""
   ```

   Candidate k: angle from `_unit_floats(door_id, k, 2)[0] * 2π`, radius
   `DOOR_SPAWN_OFFSET` (no jitter — unlike `_member_candidate`, the offset is
   a fixed clearance, not a scatter). Reject if not `_in_bounds` or if
   `geometry.point_in_polygon` hits any obstacle. Return the first survivor.

3. **New module — `src/world_engine/cockpit/spatial_doors.py`**, on the
   `cockpit/spatial_presence.py` shape (imports `geometry`, `placement`,
   `crud as _crud`, the models; never `math`).

   Module docstring, verbatim:

   ```
   """Door resolution for the spatial workstream (TICKET-0034,
   BRIEF-0034-b). The SOLE site that turns a location into live, drawable,
   reachable doors; every reader (proximity endpoint, spawn endpoint,
   door-travel endpoint) calls into it.

   TRANSIENT ADJUDICATION register: reads persistent door rows and
   geometry, judges a transient position, persists nothing.

   ORCHESTRATION ONLY — this module implements no math. Distances come from
   placement.distance, thresholds from placement.DOOR_RANGE, spawn offsets
   from placement.spawn_point, containment from geometry.point_in_polygon.
   A `math.hypot` appearing here is a bug: it forks the sole
   distance authority (K1, and the reason this module exists rather than a
   self-contained `door.py`).

   It exists because three readers span two route modules —
   routes/spatial.py (proximity, spawn) and routes/play.py (door-travel,
   which writes and so cannot live in routes/spatial.py's zero-write
   register). Without this seam those two route modules import each other
   for the same resolution.
   """
   ```

   Three public functions:

   a. ```python
      def location_doors(location_id: str, world_id: str, db: Session) -> list[dict]:
          """[{id, target_location_id, target_name, x, y}] for every LIVE
          door of a location: target is an active location of this world AND
          an active connects_to relation touches both endpoints. Ordered by
          target_name.

          This filter is B1's read half — the structural counterpart to
          write_location_doors' reject-at-write. A creator may delete a
          connects_to relation long after authoring a door; the row is never
          cascaded or swept, it simply stops resolving. PLAY-SIDE: unlike
          crud/entities.py::_location_doors_rows (creator-facing, returns
          orphans with edge_live:false so they can be fixed), nothing that
          fails the filter is returned here, at query construction."""
      ```
      Read the `connects_to` rows in both column orders, exactly as
      `play.py:847 _location_neighbours` does. This is the fifth
      `connects_to` reader; decision D1 (BRIEF-19) stands — do NOT refactor
      them together.

   b. ```python
      def doors_in_range(location_id: str, world_id: str, position: Point, db: Session) -> list[dict]:
          """[{door_id, target_location_id, target_name, distance}] for the
          live doors within placement.DOOR_RANGE of a transient position,
          nearest first, distance rounded to 3. Advisory (G-A): it enables
          the client's affordance; the door-travel endpoint re-judges the
          same predicate itself and is what actually gates."""
      ```
      Distance via `placement.distance` only.

   c. ```python
      def resolve_spawn(location_id: str, world_id: str, from_location_id: Optional[str], db: Session) -> dict:
          """{"x": float, "y": float, "anchor": "door"|"center"} — where the
          player stands on arriving in a location.

          anchor="door" when `from_location_id` is given AND a live door of
          `location_id` points back at it AND that door's point is neither
          out of bounds nor inside an obstacle: the point is
          placement.spawn_point(door.id, (door.x, door.y), bounds,
          obstacles).

          anchor="center" otherwise — no origin (narrative travel, creator
          god-mode, page reload), no return door (the counterpart side was
          never authored), or a degenerate anchor (the creator edited the
          geometry and the door now sits in a wall). This is the READ-TIME
          fallback that BRIEF-0034-a's write path deliberately does not
          duplicate: a write-time geometry check could not stay true.

          The center is returned RAW, unchecked, preserving TICKET-0032's
          documented behavior verbatim (cockpit/index.html:3311): if the
          center itself lies inside an obstacle the judge blocks all
          movement by design — geometry.clip_segment's degenerate-origin
          rule, the judge never rescues. Fix the location's geometry, not
          this code."""
      ```
      The return door is `location_doors(location_id, ...)` filtered on
      `target_location_id == from_location_id` — at most one by
      `idx_door_target`, so no tie-break exists to write. Containment
      checked with `geometry.point_in_polygon` and the bounds rectangle;
      when the location has no bounds, `anchor="center"` with `x=y=0.0`
      (the caller's guard chain already rejects non-spatial locations, so
      this is a total-function tail, not a reachable path).

4. **Proximity endpoint — `src/world_engine/cockpit/routes/spatial.py`**,
   in `spatial_proximity` (`routes/spatial.py:147`): additively extend the
   response with two keys. Existing keys and shapes are untouched.

   ```python
   return {
       "in_range": in_range,
       "threshold": placement.INTERACTION_RANGE,
       "doors_in_range": spatial_doors.doors_in_range(location.id, world_id, position, db),
       "door_threshold": placement.DOOR_RANGE,
   }
   ```

5. **Spawn endpoint — same file**, after `spatial_proximity`:

   ```python
   @router.get("/api/spatial/spawn")
   def spatial_spawn(
       location_id: str = Query(...),
       from_location_id: Optional[str] = Query(None),
       player_id: Optional[str] = Query(None),
       db: Session = Depends(get_session),
   ) -> dict:
       """Where the player appears on arriving in a spatial location
       (TICKET-0034, F1). Read-only: the handler performs zero writes of any
       kind. `from_location_id` is a transient client-carried hint (G1) —
       the server persists no position and no last-location; an absent,
       stale or wrong origin costs a center spawn, never an error."""
   ```
   Guard chain: `_resolve_spatial_location(location_id, player_id, db)`
   (`routes/spatial.py:106`) — same player/current-location/spatial-mode
   parity as `presence` and `proximity`. Returns
   `spatial_doors.resolve_spawn(...)` directly.

6. **Module docstring — same file**: extend the client-handoff contract
   paragraph (`routes/spatial.py:13-18`) with one sentence naming
   `doors_in_range` -> `GET /api/spatial/spawn` -> `POST /api/spatial/travel`
   (BRIEF-0034-c) as the door flow, and stating that `/api/spatial/travel`
   lives in `routes/play.py` precisely BECAUSE it writes and this module's
   register forbids it.

7. **Verify — `tooling/verify/checks/placement_unit.py`**: extend with
   `spawn_point` cases, in the file's existing hard-assert idiom.
   - Determinism: pin the literal output for a fixed
     `(door_id, anchor, BOUNDS, [BLOCK])` — the same restart-determinism
     proxy `EXPECTED` already uses. Compute the literals from the
     implementation and paste them; a salted-hash regression must flip them.
   - The returned point is `DOOR_SPAWN_OFFSET` from the anchor (within tol)
     when a free candidate exists.
   - Anchor beside a wall block: the returned point is not inside `BLOCK`.
   - Anchor in a corner of `BOUNDS`: the returned point is in bounds.
   - Saturation (anchor boxed in by an obstacle covering the whole ring):
     returns the anchor itself, does not raise.

8. **Verify — new check `tooling/verify/checks/door_terminal.py`**, AST-based,
   no DB, on the `module_budget.py` / `llm_parse_chokepoint.py` idiom. Two
   assertions, both fail-closed (zero parsed criteria = FAILURE, never a
   vacuous pass):
   a. **A1 escalation guard**: no `Field(foreign_key="door.id")` anywhere
      under `src/` — scan every `models/*.py` for a `foreign_key` keyword
      whose value is `"door.id"`. The check must find at least one
      `foreign_key=` in the scanned tree (proof the scan works) or FAIL.
   b. **K1 orchestration guard**: `src/world_engine/cockpit/spatial_doors.py`
      imports neither `math` nor `numpy`, and its AST contains no call to
      `math.hypot` / `math.sqrt` / `**0.5`. Failure message must name the
      reason: *"spatial_doors.py orchestrates; distance and offsets belong
      to placement.py (K1)."*

## Scope OUT

- **`POST /api/spatial/travel`, `_perform_travel`'s `origin_location_id`,
  `spatial_door_travel.py`** — BRIEF-0034-c. Nothing in this step writes, and
  nothing calls `_perform_travel`.
- **Canvas rendering, spawn-at-door on the client, the "Aller à X" button** —
  BRIEF-0034-d. The client still spawns at the raw center after this step;
  `index.html:3311` is untouched here. `GET /api/spatial/spawn` ships with no
  caller — this is the one place where "no structure without a reader" is
  satisfied by the next brief in the same ticket, not by this one.
- **Widening `_resolve_spatial_location`** or moving it out of
  `routes/spatial.py` — BRIEF-0034-c deliberately does not import it.
- **A `door.py` module carrying threshold + distance + offset** — decision K3,
  rejected: it forks the sole distance authority and pulls placement out of
  the placement authority.
- **Refactoring `_location_neighbours`, `GET /api/locations/graph`, or
  `write_location_doors`'s reader into a shared `connects_to` accessor** —
  decision D1 (BRIEF-19) stands, now at five readers. REPORT ONLY; a dedup
  opportunity is reported, never acted on.
- **Recomputing NPC positions or touching `spatial_presence.py`** — untouched.
- **Caching door resolution** across requests — `spatial_presence.npc_positions`
  recomputes from scratch on every call; match it.
- **Orientation / `width` on doors**, needed by the future walk-through (C3) —
  `spawn_point`'s ring exists precisely so this step needs no such column.
- **Punching openings in the edge set of `clip_segment`** — C1 keeps the wall
  solid.
- **Proximity call cadence changes** — D1 rides the existing on-stop 200 ms
  debounce; no new client-side polling.

## Invariants to defend

- **`routes/spatial.py`'s zero-write register** (`routes/spatial.py:4-10`).
  The temptation is real and near: the spawn endpoint is "obviously" where
  you would record where the player appeared. It records nothing. Player
  position is transient by decision Q1; the server is judge, never registrar.
- **Sole collision authority** (`geometry.py:1-5`) and **sole
  placement/distance authority** (`placement.py:1-6`). The temptation is a
  one-line `math.hypot` in `spatial_doors.py` "to avoid the import".
  `door_terminal.py` (Scope IN 8b) is the guard.
- **Structural exclusion at query construction, never after the fact.**
  `location_doors`' B1 filter is built into the read, not applied to a
  full list by the caller.
- **Determinism of `placement.py`** — `spawn_point` derives its randomness
  from `sha256` over `door_id` via `_unit_floats`. Python's salted `hash()`
  is forbidden here (`placement.py:15-18`).
- **Total functions in `placement.py`** — `derive_positions` "never raises,
  even against a degenerate all-wall location". `spawn_point` matches:
  saturation returns the anchor, the caller decides the fallback.
- **Module budget** — `routes/spatial.py` (169 lines) and `placement.py`
  (124 lines) have room; `spatial_doors.py` should land near
  `spatial_presence.py`'s 53 lines. If any approaches the cap, that is the
  tripwire, not a nuisance: REPORT, do not baseline.

## Done means

- [ ] Full verify suite green, including the extended `placement_unit.py` and
      the new `door_terminal.py`.
- [ ] `door_terminal.py` red-tested both ways: temporarily add
      `Field(foreign_key="door.id")` to a model -> check FAILS; temporarily
      add `import math` + a `math.hypot` call in `spatial_doors.py` -> check
      FAILS. Both reverted.
- [ ] `placement_unit.py` red-tested: swap `_unit_floats`' `sha256` for
      `hash()` -> the pinned `spawn_point` literals flip and the check FAILS.
      Reverted.
- [ ] `python -c "from world_engine.cockpit import spatial_doors"` imports
      clean; `grep -n "math\." src/world_engine/cockpit/spatial_doors.py`
      returns nothing.
- [ ] Live smoke, fixture from BRIEF-0034-a (A and B linked, both spatial,
      doors authored on both sides — A's door at `(2, 15)`, B's at `(38, 15)`):
      - `POST /api/spatial/proximity` with the player at `(2.5, 15)` in A
        returns `doors_in_range == [{door_id, target_location_id: B,
        target_name: "<B>", distance: 0.5}]` and `door_threshold == 1.5`;
        `in_range` and `threshold` unchanged from before this step.
      - Same call at `(10, 15)` returns `doors_in_range == []`.
      - `GET /api/spatial/spawn?location_id=<B>&from_location_id=<A>` returns
        `anchor == "door"` and a point `0.6 m` from `(38, 15)`, in bounds,
        outside every obstacle.
      - Same call twice returns the identical point; same after a server
        restart.
      - `GET /api/spatial/spawn?location_id=<B>` (no origin) returns
        `anchor == "center"` and B's bounds center.
      - `GET /api/spatial/spawn?location_id=<B>&from_location_id=<A>` after
        deleting B's door toward A -> `anchor == "center"`.
      - Same, after moving B's door inside an obstacle via the creator panel
        -> `anchor == "center"`, no error.
      - `GET /api/spatial/spawn` on a non-spatial location -> 409; on a
        location that is not the player's current -> 409.
- [ ] B1 read filter live: delete the `connects_to` relation between A and B
      -> `doors_in_range` at `(2.5, 15)` in A returns `[]`; the `door` row
      still exists in the DB (nothing cascaded); re-create the relation ->
      the door resolves again.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `world-engine-schema.md` / changelog: **no schema change this step** — no
  entry, no version bump. Say so explicitly in the close note.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: append the 0034 decision
  block for this step — K1 and why (three readers, two route modules, the
  cross-import it avoids); the threshold-vs-authority distinction that kept
  `DOOR_RANGE` in `placement.py`; `spawn_point`'s ring derivation and why no
  orientation column exists; `resolve_spawn`'s three fallback conditions and
  the staleness argument that makes read-time the ONLY sound place for the
  geometry check; the raw-center carry-over from TICKET-0032.
- `CLAUDE.md`: one standing line — *"`cockpit/spatial_doors.py` orchestrates
  door resolution and implements no math: distances, thresholds and spawn
  offsets belong to `placement.py`, the sole placement/distance authority
  (K1, TICKET-0034) — enforced by `door_terminal.py`."*
