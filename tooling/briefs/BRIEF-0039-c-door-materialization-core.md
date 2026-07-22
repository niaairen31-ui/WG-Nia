# BRIEF - Step "door materialization core (spatial_author.py + placement placeholder)"

## Context
Adjacency (`connects_to`) is written today with no matching door; doors are created
by hand, one per neighbour (crud/entities.py:830). This step builds the pure core
that turns a location's live `connects_to` neighbours into `door` rows via the
existing `write_location_doors` writer - preserving any hand-placed coordinates and
using the H1 placeholder for edges that have no door yet. NO call-sites are wired in
this brief (that is BRIEF-0039-d); the core is exercised by a script/unit so it is
testable in isolation.

## Scope IN
1. NEW placement helper in `src/world_engine/placement.py` (the sole
   placement/distance authority - door_terminal.py forbids this math living in
   spatial_doors.py):
   `door_placeholder_point(location) -> tuple[float, float]`
   - Returns `(bounds_width / 2.0, bounds_height / 2.0)` when BOTH `bounds_width`
     and `bounds_height` are non-null and finite (center of the playable area, the
     obstacle_vertex local space).
   - Otherwise returns `(0.0, 0.0)`.
   This is H1 verbatim: center of bounds if present, else origin.
2. NEW Creation orchestrator `src/world_engine/spatial_author.py` (naming matches
   region_author.py / entity_author.py / link_author.py - Creation-side generation).
   Core function:
   `materialize_doors(db, *, world_id: str, location_ids: Iterable[str], changed_by: str) -> dict`
   For EACH location id in the input set (dedup first):
   a. Gather its LIVE `connects_to` neighbours that are ACTIVE locations of this
      world, reading BOTH column orders exactly as play.py:848 / config.py:258-270
      do (do NOT refactor the four connects_to readers into one - decision D1 of
      BRIEF-19 stands; this becomes the fifth reader, and that is accepted).
      Filter out any neighbour that is not an active `location` entity (defensive:
      a connects_to to a non-location must NOT abort the commit).
   b. Read the location's CURRENT `door` rows into a map
      `{target_location_id: (x, y)}`.
   c. Build the new door payload: one item per neighbour from (a):
      `{"target_location_id": neighbour_id, "x": X, "y": Y}` where (X, Y) is the
      EXISTING (x, y) from (b) if a door for that neighbour already exists, ELSE
      `door_placeholder_point(location)`.
   d. Call `write_location_doors(db, world_id=world_id, location_id=<this loc>,
      doors=<payload>, changed_by=changed_by)` and add the returned rows to the
      session. This full-replace naturally DROPS doors whose edge died and KEEPS
      hand-placed coordinates for surviving edges.
   Return a small summary dict, e.g.
   `{"locations": n, "doors_written": m, "placeholders": k}` for logging/notes.
   Do NOT commit inside `materialize_doors` - the caller owns the commit (match the
   region commit's single-`db.commit()` contract, regions.py).
3. VERBATIM module docstring for spatial_author.py (copy exactly):
   ```
   """Creation-side spatial materialization (TICKET-0039).

   materialize_doors turns a location's live connects_to neighbours into door
   rows via writes.config.write_location_doors - the SOLE door-write path. It
   NEVER creates, judges or removes connects_to edges (a door is the spatial
   manifestation of an edge, never its source - B1). It preserves hand-placed
   door coordinates and only invents a placeholder point (placement.
   door_placeholder_point, H1) for an edge that has no door yet. Idempotent:
   re-running on the same locations reproduces the same door set. This module
   is NOT reachable from _apply_mutation - world creation is creator direct
   authority, never an AI proposal.
   """
   ```

## Scope OUT
- NO call-site wiring. `_commit_region_links`, the relation-CRUD path, and
  `connect_locations` are BRIEF-0039-d. This brief must not import spatial_author
  anywhere in the request/commit flow yet.
- NO geometry validation. Do NOT check that the placeholder point is inside bounds
  or outside an obstacle - write_location_doors' NOTE (config.py:311-325) forbids
  write-time geometry checks; read-time is the only sound place (spatial_doors.py).
- NO second door per pair. Exactly one door per neighbour per direction; do NOT
  attempt front/back doors; do NOT touch the idx_door_target unique index.
- NO classification reading here. Door KIND derivation (D1) is not needed for
  materialization (the placeholder point does not depend on interior/exterior).
  D1 derivation, if a reader needs it, lands in BRIEF-0039-e - not here.
- NO new distance/threshold math beyond the center-of-bounds midpoint.

## Invariants to defend
- door_terminal.py part (b): spatial_doors.py implements no math. This brief keeps
  the ONLY new math (midpoint) inside placement.py; spatial_author.py just calls it.
  Keep spatial_author.py free of arithmetic on coordinates.
- single_canon_write.py: doors are still written ONLY by write_location_doors.
  materialize_doors must not INSERT Door rows directly - it builds payloads and
  delegates. Keep the check green.
- Module budget (R5) + R6 (no catch-all): spatial_author.py is a single-purpose
  module. Do not let it accrete unrelated helpers.
- "history is sacred": full-replace on `door` is the sanctioned curated-config
  exception (already documented on write_location_doors). The coordinate-preserving
  merge is what protects creator intent within that exception.

## RECON needed at exec time (verify before writing)
- Confirm `write_location_doors` signature and its all-or-nothing validation
  (config.py:281-328): it REJECTS a target with no live connects_to edge and a
  target that is not an active location. Since materialize builds the payload FROM
  live active-location neighbours, it will pass - verify this assumption against the
  current validator before relying on it.
- Confirm the door-read shape (Door rows for one location: which columns) and the
  connects_to read used by play.py:848 - copy that read verbatim as the fifth reader.
- Confirm `bounds_width` / `bounds_height` nullability on Location (canon.py:227-228)
  and that they are the obstacle-space bounds, not the world-map coords.

## Done means
- [ ] A script that creates two active locations, writes a `connects_to` between
      them, then calls `materialize_doors` for both -> exactly two door rows appear
      (A->B, B->A), each at (0,0) when bounds are null, or at center when bounds set.
- [ ] Hand-place a door coordinate on one side, add a second neighbour, re-run
      `materialize_doors` -> the hand-placed coordinate is UNCHANGED and the new
      neighbour's door appears at the placeholder point.
- [ ] Delete the `connects_to` edge, re-run `materialize_doors` -> the corresponding
      door row is gone (full-replace drop), the other edges' doors remain.
- [ ] door_terminal.py and single_canon_write.py green.
- [ ] `/review-step` clean.

## Docs to update
- ARCHITECTURE_DECISIONS.md: append the materialization contract (derived from
  connects_to, coordinate-preserving, placeholder H1, idempotent, delegates to
  write_location_doors, not reachable from _apply_mutation).
- CLAUDE.md: add spatial_author.py to the module map with a one-line purpose.
