# BRIEF — Step "Collision geometry core" (TICKET-0030, BRIEF-0030-a)

## Context

Ticket 0029 (schema v1.80, merged) shipped persistent intra-location wall
geometry: `obstacle` + `obstacle_vertex` rows in a per-location local space
(origin top-left, x rightward, y DOWNWARD, floats, 1.0 = one world-meter),
plus nullable `location.bounds_width` / `bounds_height` (NULL = no spatial
mode). Ticket 0030 adds the single server authority that judges a transient
movement segment against that geometry. This first brief ships the pure
algorithm and its permanent regression guard — no endpoint, no DB, no HTTP.

Locked decisions (intake, TICKET-0030):
- **Q2 (workstream)** — collisions are judged server-side only; no parallel
  client collision (C3 rejected as premature optimization). This module is
  exactly the piece a future C3 would reuse.
- **C2 (workstream)** — segment-based judging: origin → destination in,
  stop point out.
- **D1** — the algorithm lives in a pure module, `src/world_engine/geometry.py`:
  zero DB, zero FastAPI, zero imports from `cockpit/`. The route (BRIEF-0030-b)
  is a caller, never a co-implementer. "Sole collision authority" holds by
  construction: one importable module contains the math.
- **D3** — hard-stop semantics. The server returns the clipped stop point;
  slide-along-wall EMERGES client-side in 0032 by re-submitting axis
  components. Server-computed slide (option B) is a recorded compatible
  evolution — same signature, same response shape — NOT built now.
- **D4** — the player is a point. No radius parameter, no polygon inflation.
  The 0032 circle is purely visual.
- **B2 payoff (0029)** — the segment↔polygon intersection is generic from
  day one: the same code judges 4-vertex rectangles and future real
  polygons. Nothing in this module may assume rectangles or axis-alignment.

## Scope IN

1. **New module `src/world_engine/geometry.py`** — pure functions,
   `from __future__ import annotations`, stdlib only (`math`). Module
   docstring states the register doctrine verbatim:

   ```
   """Pure collision geometry for the spatial workstream (TICKET-0030,
   BRIEF-0030-a). The SOLE collision authority: every movement judgment in
   the engine flows through clip_segment — no other module may implement
   segment-vs-geometry intersection.

   TRANSIENT ADJUDICATION register: functions here read persistent
   geometry handed to them as plain values, judge a transient position,
   and persist nothing. This module never imports the DB, the models, or
   FastAPI — it is the piece a future client-side predictor (rejected C3)
   would reuse verbatim.

   Coordinate space: per-location local coordinates (schema v1.80) —
   origin top-left, x rightward, y DOWNWARD, 1.0 = one world-meter.
   """
   ```

2. **Types** (plain aliases, no dataclasses):

   ```python
   Point = tuple[float, float]
   Polygon = list[Point]   # closed polygon, >= 3 vertices; edge i runs
                           # vertex[i] -> vertex[(i+1) % n]. Winding
                           # direction irrelevant to every function here.
   ```

3. **`point_in_polygon(point: Point, polygon: Polygon) -> bool`** —
   standard ray-casting (even-odd rule). A point exactly on an edge may
   resolve either way (documented; the epsilon pull-back in `clip_segment`
   keeps judged positions off edges in practice).

4. **`segment_intersection(p1, p2, q1, q2) -> Optional[float]`** — returns
   the parameter `t` in `[0, 1]` along `p1 -> p2` at which the segment
   crosses `q1 -> q2`, or `None`. Collinear-overlap resolves to the
   smallest valid `t` or `None` if degenerate; do not over-engineer exact
   collinear handling — document the choice.

5. **`clip_segment(origin, destination, polygons, bounds) -> tuple[Point, bool]`**
   — the single public judgment. `bounds: Optional[tuple[float, float]]`
   as `(width, height)`; `polygons: list[Polygon]`.

   Semantics, in order:
   a. **Degenerate origin** — if `bounds` is present and origin lies
      outside `[0, width] x [0, height]`, OR origin is inside any polygon:
      return `(origin, True)`. The judge never rescues the player (creator
      teleport, geometry edited underfoot); unblocking is a creator act,
      not adjudicator behavior. Document this in the docstring.
   b. **Zero-length segment** — `origin == destination`: return
      `(destination, False)` (after the degenerate check).
   c. **Edge set** — all edges of all polygons, PLUS the four bounds edges
      when `bounds` is present (bounds are walls seen from inside; 0029
      explicitly deferred bounds enforcement to this ticket). No
      containment assumption between obstacles and bounds — judge every
      edge the geometry hands over.
   d. **Judgment** — find the minimum `t_hit` across all edges. No hit:
      `(destination, False)`. Hit: pull the stop point back along the
      segment by `EPS_METERS = 1e-3` (module constant, 1 mm) so the
      returned point is strictly off the wall — clamped so it never
      backs past origin — and return `(stop_point, True)`.

6. **Permanent regression guard —
   `tooling/verify/checks/geometry_unit.py`** — deterministic, no DB,
   imports `world_engine.geometry` via the same `ROOT`/`src` path
   bootstrap the other checks use. REPORT ONLY if the check-runner
   conventions resist importing from `src/` (module_budget.py already
   walks `src/`, so pathing exists); fallback is `scripts/test_geometry.py`
   on the `test_context.py` model — but the check placement is preferred:
   it makes the sole-authority module gate-guarded on every future ticket.
   Cases (each a hard assert, one summary PASS line on success):
   - free move in open space → destination unchanged, `blocked=False`;
   - segment crossing one rectangle edge → stop point on the entry edge
     (within `EPS_METERS` tolerance), `blocked=True`;
   - segment crossing a NON-rectangular polygon (e.g. a triangle) →
     blocked (the B2 genericity proof);
   - segment leaving bounds → clipped at the bounds edge, `blocked=True`;
   - `bounds=None`, no polygons → any segment passes;
   - origin inside a polygon → `(origin, True)`, destination ignored;
   - origin outside bounds → `(origin, True)`;
   - zero-length segment in open space → `(point, False)`;
   - destination exactly on an edge → blocked, stop pulled back;
   - grazing move parallel to and just off a wall → NOT blocked (no
     false positives from the epsilon).

## Scope OUT

- **The HTTP endpoint, player resolution, DB reads** — BRIEF-0030-b.
- **Server-computed slide (D3 option B)** — recorded evolution, not built.
  Do NOT add a `slide=` parameter "while in there".
- **Player radius / polygon inflation (D4 option B)** — rejected for the
  pilot; the algorithm judges a point.
- **Obstacle containment validation** (obstacles poking outside bounds) —
  the write path deliberately does not validate this (0029) and the judge
  just judges edges; do not add validation on either side.
- **Spatial indexing / broad-phase** (quadtrees, AABB pre-filter) —
  premature at pilot obstacle counts; brute-force every edge.
- **NPC proximity / distance functions** — ticket 0031 (it will import
  this module; do not pre-build its helpers).
- **Any change to `writes/config.py`, models, or schema** — this brief
  touches zero persistent state. No migration, no changelog entry,
  schema version untouched.

## Invariants to defend

- **Purity** — `geometry.py` imports nothing from `world_engine` beyond
  stdlib. The temptation is importing `models` for a typed Obstacle;
  forbidden — values in, values out.
- **Genericity (B2)** — no code path may branch on "is this a rectangle".
  The triangle test case is the tripwire.
- **Module budget (G1)** — new module, trivially within 40 functions /
  1000 lines; keep it that way (no speculative helpers).
- **Transient adjudication** — nothing in this module (or its test)
  writes anywhere. `single_canon_write.py` stays green with an unchanged
  policy file.

## Done means

- [ ] `python tooling/verify/checks/geometry_unit.py` → PASS, all cases
      above asserted (or the documented `scripts/` fallback, REPORT why).
- [ ] Full verify suite green — no policy, schema, or budget change.
- [ ] `geometry.py` contains no import of `sqlmodel`, `fastapi`,
      `world_engine.models`, or `world_engine.db` (eyeball + the purity
      note in the module docstring).
- [ ] The doctrine docstring (Scope IN 1) is present verbatim.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: deferred to BRIEF-0030-b, which appends the
  single TICKET-0030 decision block covering both briefs (D1–D5 and the
  transient-adjudication register) — do not write a partial entry here.
- No schema docs, no changelog: zero schema surface.
- `CLAUDE.md`: no new standing rule expected; REPORT if execution reveals
  one.
