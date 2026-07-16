# BRIEF — Step "Placement core + presence assembler" (TICKET-0031, BRIEF-0031-a)

## Context

Tickets 0029 (schema v1.80) and 0030 (both merged) shipped persistent
wall geometry and the pure collision authority (`geometry.py::clip_segment`,
`point_in_polygon`), plus the transient-adjudication route module
`routes/spatial.py`. Ticket 0031 gives NPCs a drawable, measurable
position WITHOUT persistent NPC coordinates. This first brief ships the
pure placement math and the single DB-reading assembler — no endpoint,
no HTTP (BRIEF-0031-b's job).

Locked decisions (intake, TICKET-0031):
- **A** — NPC position is a deterministic pure derivation, stored
  nowhere: `f(location geometry, open gatherings + rosters, stable ids)`.
  Recomputed on every request; stability comes from determinism, not
  storage. Q1 holds workstream-wide: nothing transient is ever persisted.
- **A-i** — pure math in a NEW module `src/world_engine/placement.py`
  (geometry.py's sibling: zero DB, zero FastAPI, zero `cockpit/`
  imports); the assembler in a NEW module
  `src/world_engine/cockpit/spatial_presence.py` (it must read
  gatherings and geometry — neither `geometry.py` (pure, locked) nor
  `routes/spatial.py` (caller only, locked D1-0030) may host it).
- **Determinism doctrine** — all randomness derives from
  `hashlib.sha256` over stable ids. NEVER Python's built-in `hash()`
  (per-process salt: a server restart mid-scene would silently reshuffle
  every circle, violating the live-gate stability criterion).
- **Earshot rail** — `placement.distance` + the assembler are the SOLE
  spatial-distance site in the engine. Future audibility imports them,
  never recomputes.

## Scope IN

1. **New module `src/world_engine/placement.py`** — pure functions,
   stdlib + `from . import geometry` only. Module docstring states the
   register doctrine:

   ```
   """Pure NPC placement for the spatial workstream (TICKET-0031,
   BRIEF-0031-a). The SOLE spatial-distance and placement authority:
   every NPC position and every spatial distance in the engine flows
   through derive_positions / distance — no other module may implement
   either. Future audibility (earshot) imports this site.

   TRANSIENT ADJUDICATION register: functions here read persistent
   geometry handed to them as plain values, derive transient positions,
   and persist nothing. This module never imports the DB, the models,
   or FastAPI.

   Determinism: all placement randomness derives from sha256 over
   stable ids — identical inputs yield identical positions across
   requests, refreshes, and server restarts. Python's salted hash()
   is forbidden here.

   Coordinate space: per-location local coordinates (schema v1.80) —
   origin top-left, x rightward, y DOWNWARD, 1.0 = one world-meter.
   """
   ```

2. **Constants**:

   ```python
   INTERACTION_RANGE = 2.0    # world-meters; proximity threshold (intake, calibrate at live gate)
   MEMBER_RING_RADIUS = 0.8   # world-meters; member offset around the gathering centroid
   EDGE_MARGIN = 1.0          # world-meters; centroid candidates keep this off bounds edges
   MAX_ATTEMPTS = 32          # deterministic rejection-sampling budget per point
   ```

3. **`distance(a: Point, b: Point) -> float`** — plain Euclidean.
   Trivial on purpose: it exists so the single-site rule has a name to
   point at (the earshot rail), not because the math is hard. Reuses
   `geometry.Point`.

4. **`_unit_floats(seed: str, counter: int, n: int) -> tuple[float, ...]`**
   (private) — `sha256(f"{seed}:{counter}".encode())`, digest bytes
   consumed 8 at a time as big-endian ints scaled into `[0, 1)`. The
   single source of pseudo-randomness in the module.

5. **`derive_positions(rosters, bounds, obstacles) -> dict[str, Point]`**
   — the placement function.
   - `rosters: list[tuple[str, list[str]]]` — `(gathering_id,
     [entity_id, ...])`, already player-free (the assembler's job);
     `bounds: tuple[float, float]`; `obstacles: list[geometry.Polygon]`.
   - **Centroid per gathering**: candidates from
     `_unit_floats(gathering_id, k, 2)` scaled into
     `[EDGE_MARGIN, bounds - EDGE_MARGIN]`, k = 0..MAX_ATTEMPTS-1;
     reject a candidate inside any obstacle
     (`geometry.point_in_polygon`); first accepted wins. Saturation
     fallback: the last candidate is used as-is — the function is
     TOTAL and never raises; a degenerate all-wall location yields a
     degenerate-but-stable layout, never a broken scene (resilience
     doctrine). If `bounds` is too small for the margin
     (`bounds_* <= 2 * EDGE_MARGIN`), the margin collapses to 0 for
     that axis rather than producing an inverted interval.
   - **Member position**: for each entity, angle and radial jitter from
     `_unit_floats(entity_id, k, 2)` → point on a ring of radius
     `MEMBER_RING_RADIUS * (0.6 + 0.4 * jitter)` around the centroid;
     reject if inside an obstacle or outside bounds; on saturation,
     fall back to the centroid itself. A solo gathering places its
     single member ON the centroid (no ring).
   - Returns `{entity_id: (x, y)}` over every entity in every roster.
     No de-duplication logic: the per-NPC-uniqueness invariant already
     guarantees each NPC appears in exactly one roster.

6. **New module `src/world_engine/cockpit/spatial_presence.py`** — the
   single assembler. Docstring names it verbatim as "the SOLE site that
   turns a location into named NPC positions; every reader (presence
   endpoint, proximity endpoint, future earshot) calls this function".

   ```python
   def npc_positions(location_id: str, world_id: str, db: Session) -> list[dict]:
       """[{id, name, x, y}] for every present NPC, gathering-clustered,
       deterministic. Read-only; persists nothing."""
   ```
   - Reuses `_get_or_open_session`, `_open_gatherings`,
     `_active_members` (cockpit/play.py — the sanctioned roster source)
     and `_location_geometry_dict` (crud/entities.py — 0029's sole
     geometry assembler).
   - **Excludes the player**: filter `character_type == "player"` on
     the `Character` row of each member (RECON finding: rosters include
     the player; the H_COMPANY exclusion lives in context assembly, not
     in `_active_members`). Do NOT widen `_active_members` itself —
     other consumers (initiative vote, speaker selection) legitimately
     see the player.
   - Builds `rosters` and calls `placement.derive_positions`; zips
     names back on. Order: gatherings in `_open_gatherings` order,
     members in roster order — stable output ordering for free.

7. **Permanent regression check
   `tooling/verify/checks/placement_unit.py`** (no DB, geometry_unit.py
   precedent), covering at minimum:
   - determinism: two calls, identical inputs → identical dict;
   - restart-determinism proxy: expected coordinates for one fixed
     input pinned as literals in the check (a salted-hash regression
     would flip them);
   - obstacle avoidance: no returned point inside the test block;
   - bounds containment: all points within bounds;
   - clustering: members of one gathering all within
     `MEMBER_RING_RADIUS + eps` of their centroid, two gatherings'
     centroids distinct;
   - saturation totality: an all-wall location still returns a
     position per entity, no exception;
   - `distance`: exactness on a 3-4-5 triangle.

## Scope OUT (this brief)

- The two endpoints and their guards — BRIEF-0031-b.
- Any frontend, canvas, WASD — ticket 0032.
- Earshot/audibility logic — dormant rail, named only.
- Authored spawn zones (intake option D), per-location threshold
  column, persistent NPC coordinates — rejected/deferred at intake.
- The ARCHITECTURE_DECISIONS block — BRIEF-0031-b writes the single
  block covering both briefs (0030 precedent).

## Verify

- `placement_unit.py` green; full suite green.
- `module_budget.py`: two new small modules; `routes/play.py` and
  `cockpit/play.py` untouched.
- `single_canon_write.py`: policy file unchanged — this brief adds
  zero write sites of any kind.
