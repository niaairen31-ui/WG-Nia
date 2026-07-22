# BRIEF - Step "perimeter door point (N1): replace the center placeholder"

## Context
`placement.door_placeholder_point(location)` (placement.py:49-64) returns the
CENTER of the location's bounds, so every door of a room sits at exactly the same
coordinates - three neighbours, three doors, one point. TICKET-0034's proximity
affordance and TICKET-0032's spawn both read those points, so the defect is
visible in Play. This step replaces the center with a deterministic placement on
the PERIMETER. Pure function change: `placement.py` imports no DB and persists
nothing. No door row is rewritten here - that is BRIEF-0040-e.

## Scope IN

1. **Signature change, declared not silent.** `door_placeholder_point` takes a
   second required parameter:

   ```
   def door_placeholder_point(location, target_location_id: str) -> Point
   ```

   The target id is what makes two doors of the same room differ; there is no way
   to derive it from `location` alone. Update the single call site
   (`spatial_author.py:89`) to pass `neighbour_id`. This is an assumed contract
   evolution of a function delivered by TICKET-0039, BRIEF-0039-c - see Docs.

2. **H1 - arc-length parametrization.** One deterministic float from the existing
   pseudo-random source, then a clockwise walk of the perimeter starting at the
   top-left corner `(0, 0)`, matching the rect -> vertices convention already
   declared for obstacles (`crud/entities.py:800`, `world-engine-schema.md:250-254`):

   ```
   u = _unit_floats(f"{location.id}:{target_location_id}", 0, 1)[0]
   t = u * 2.0 * (width + height)
   t < width               -> (t, 0.0)                 # top edge,    left  -> right
   t < width + height      -> (width, t - width)       # right edge,  top   -> bottom
   t < 2*width + height    -> (2*width + height - t, height)   # bottom, right -> left
   otherwise               -> (0.0, 2*(width+height) - t)      # left,   bottom -> top
   ```

   Counter `0` and `n=1` on `_unit_floats` - the same call shape
   `spawn_point:153` uses. No second draw, no rejection sampling: every point on
   the perimeter is valid by construction, and an obstacle overlapping a wall is
   the creator's geometry problem, resolved at read time by
   `spatial_doors.resolve_spawn`'s existing degenerate-anchor fallback, never
   here.

3. **I1 - the NULL-bounds fallback is preserved verbatim.** When `bounds_width` or
   `bounds_height` is None, non-finite, or `<= 0`, return `(0.0, 0.0)` exactly as
   today. `write_location_doors` requires NOT NULL `x`,`y`, so the function stays
   total and never raises. Note the `<= 0` guard is an ADDITION (today only
   None/non-finite are guarded); a zero-width location would otherwise produce a
   degenerate perimeter.

4. **Asymmetry comment, verbatim in the docstring:**

   ```
   The seed is f"{location.id}:{target_location_id}" and is deliberately
   ASYMMETRIC: the door A->B and the door B->A get different positions
   because each lives in its OWN location's local coordinate space, with
   different bounds and a different origin. A symmetric (sorted-pair)
   seed would be a bug, not a simplification.
   ```

   Plus a line stating that the whole function is replaceable wholesale the day a
   geometric floor plan lands, since `placement.py` is the single placement
   authority.

5. **`placement_unit.py` extension** (tooling/verify/checks/placement_unit.py) -
   hard asserts, in the file's existing idiom:
   - **on-perimeter**: for a fixed bounds and 20 distinct target ids, every
     returned point satisfies `x == 0 or x == width or y == 0 or y == height`
     within `1e-9`, and lies within `[0, width] x [0, height]`;
   - **distinctness**: those 20 points contain no exact duplicate pair;
   - **spread**: the 20 points touch at least 3 of the 4 edges (a regression that
     collapsed the walk onto one edge would pass on-perimeter but fail here);
   - **determinism**: pinned literal expectations for at least 3 fixed
     `(location_id, target_id, bounds)` triples, in the style of the existing
     `EXPECTED` dict - a salted-hash regression flips them on the next process;
   - **asymmetry**: `door_placeholder_point` for `(A, B)` under A's bounds differs
     from `(B, A)` under B's bounds;
   - **I1**: bounds `(None, None)`, `(10.0, None)`, `(0.0, 5.0)` and a non-finite
     width each return exactly `(0.0, 0.0)`;
   - **elongation** (this is the H1 assertion): with bounds `(100.0, 2.0)`, the
     fraction of the 20 points landing on the two SHORT edges is under 0.2 - a
     uniform-angle ray-cast implementation would cluster there and fail.

   Use a lightweight stand-in object for `location` (the function reads only
   `.id`, `.bounds_width`, `.bounds_height`); do not import the DB into this check.

## Scope OUT
- Do NOT re-derive, move, or rewrite any existing `door` row. `materialize_doors`
  still reuses `existing_points` for every surviving edge, so this brief changes
  the position of NEW doors only. The re-derivation is BRIEF-0040-e and must not
  be anticipated.
- Do NOT add a `door.orientation` or `door.edge` column, and do NOT compute an
  "inward" direction. A door is a point with no orientation - TICKET-0034 Scope
  OUT, unchanged.
- Do NOT inset the point off the wall. The door sits ON the border;
  `spawn_point` (placement.py:133-163) already rejects out-of-bounds ring
  candidates, so arrival lands inside the room by construction.
- Do NOT touch `spawn_point`, `derive_positions`, `distance`,
  `DOOR_RANGE`, `DOOR_SPAWN_OFFSET`, `INTERACTION_RANGE`, or `_unit_floats`.
- Do NOT add obstacle-avoidance to the door point. Read-time filtering is the
  correct enforcement point; a write-time geometry check could not stay true after
  a later edit.
- Do NOT implement the geometric floor plan, wall segments, or door-on-shared-wall
  alignment between two neighbours. Named future chantier.
- Do NOT add the new `door_distinct_points.py` check here (BRIEF-0040-e).

## Invariants to defend
- **placement.py is the sole placement/distance authority.** All the new math
  lands here; `spatial_author.py` gains zero coordinate arithmetic and stays
  dict-building plus dispatch. `door_terminal.py` enforces the twin rule for
  `spatial_doors.py`.
- **Determinism.** `hashlib.sha256` via `_unit_floats` only. Python's salted
  `hash()`, `random`, and `uuid` are forbidden in this module.
- **Transient adjudication register.** No DB import, no model import, no FastAPI
  import in `placement.py`. The function receives a location object and reads
  three attributes off it.
- **Local coordinate space.** `bounds_*` and the returned point are in the
  per-location space of `obstacle_vertex`, y DOWNWARD, never
  `location.coord_x/coord_y`.
- **80-line ceiling**: the new function should land near 25 lines. If it exceeds
  80 the walk has been overbuilt.

## RECON needed at exec time (verify before writing)
- Confirm `door_placeholder_point` has exactly ONE production call site
  (`spatial_author.py:89`) before changing the signature:
  `grep -rn "door_placeholder_point" src/ tooling/ scripts/`. Any additional
  caller found is a STOP-and-report, not a silent update.
- Confirm the `location` object passed at `spatial_author.py:74-89` is the
  `Location` extension row (it is `db.get(Location, location_id)`) and therefore
  carries `.id` - the seed depends on it. If `.id` is not populated at that point,
  report before falling back to anything else.
- Read `placement_unit.py` in full and match its `EXPECTED`/`close()`/`FAILURES`
  idiom exactly; generate the pinned literals by RUNNING the new implementation,
  then paste them - never hand-compute them.
- Confirm no verify check or test pins the current center-returning behaviour
  (`grep -rn "door_placeholder\|bounds_width / 2\|width / 2.0" tooling/`).
  `spatial_door_travel.py` and `door_coverage.py` are the likely ones; if either
  asserts a center coordinate, it must be updated in THIS commit and the change
  called out.
- Confirm `index.html:3370` (`_spatialConfirmed = { x: geo.bounds_width / 2, ... }`)
  is the SPAWN fallback for a location with no return door, unrelated to door
  points - report if it turns out to read door coordinates.

## Done means
- [ ] `door_placeholder_point(loc, "target-a")` and
      `door_placeholder_point(loc, "target-b")` return different points for the
      same 12 x 8 location, both on the perimeter.
- [ ] Two identical calls in two SEPARATE python processes return identical
      points (run it twice from the shell and compare).
- [ ] A location with NULL bounds returns `(0.0, 0.0)`.
- [ ] `python tooling/verify/checks/placement_unit.py` exits 0 and its summary
      line names the new perimeter cases.
- [ ] Deliberately breaking the walk (e.g. returning the top edge always) makes
      `placement_unit.py` FAIL on the spread assertion - demonstrate this once,
      then revert (proves the check is not vacuous).
- [ ] `door_coverage.py`, `door_terminal.py`, `spatial_door_travel.py`,
      `single_canon_write.py`, `function_length.py` green.
- [ ] Live: wire a new adjacency onto a room that already had two doors. The new
      door appears on a wall, away from the two existing (still centered) ones -
      the two old ones are expected to still overlap at this stage.
- [ ] `/review-step` clean.

## Docs to update
- `ARCHITECTURE_DECISIONS.md`: AMEND the existing
  `## DOOR MATERIALIZATION CORE (BRIEF-0039-c, no schema change)` section, whose
  text graves H1 verbatim ("`door_placeholder_point(location)` returns the center
  of `(bounds_width, bounds_height)`"). Append - do not rewrite history - a
  clearly labeled evolution paragraph: **N1 supersedes H1 (TICKET-0040,
  BRIEF-0040-d)**, stating that the center placeholder stacked every door of a
  room at one point, that the replacement is an arc-length perimeter walk seeded
  by the asymmetric `location_id:target_location_id` pair, that the signature
  gained `target_location_id`, that `(0.0, 0.0)` survives as the NULL-bounds
  fallback, and that the placement stays in `placement.py` for the same reason H1
  did. This is an assumed evolution, not a silent bugfix.
- `CLAUDE.md`: update any clause describing the placeholder as "the center of
  bounds" to the perimeter rule. Pointer-fresh.
