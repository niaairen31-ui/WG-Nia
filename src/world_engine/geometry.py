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
from __future__ import annotations

import math
from typing import Optional

Point = tuple[float, float]
Polygon = list[Point]   # closed polygon, >= 3 vertices; edge i runs
                        # vertex[i] -> vertex[(i+1) % n]. Winding
                        # direction irrelevant to every function here.

EPS_METERS = 1e-3


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """Standard ray-casting (even-odd rule). A point exactly on an edge
    may resolve either way — the epsilon pull-back in clip_segment keeps
    judged positions off edges in practice, so this ambiguity never
    surfaces to a caller."""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_intersect:
                inside = not inside
    return inside


def segment_intersection(p1: Point, p2: Point, q1: Point, q2: Point) -> Optional[float]:
    """Returns the parameter t in [0, 1] along p1 -> p2 at which the
    segment crosses q1 -> q2, or None. Collinear-overlap resolves to the
    smallest valid t within both segments' overlap (clamped to [0, 1]),
    or None if the segments don't overlap at all or p1 == p2; this is a
    deliberately simple resolution, not exact general-position collinear
    handling."""
    r = (p2[0] - p1[0], p2[1] - p1[1])
    s = (q2[0] - q1[0], q2[1] - q1[1])
    rxs = r[0] * s[1] - r[1] * s[0]
    qp = (q1[0] - p1[0], q1[1] - p1[1])
    qpxr = qp[0] * r[1] - qp[1] * r[0]

    if rxs == 0:
        rr = r[0] * r[0] + r[1] * r[1]
        if qpxr != 0 or rr == 0:
            return None  # parallel, non-collinear (or p1 == p2)
        t0 = (qp[0] * r[0] + qp[1] * r[1]) / rr
        t1 = t0 + (s[0] * r[0] + s[1] * r[1]) / rr
        lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)
        lo, hi = max(lo, 0.0), min(hi, 1.0)
        if lo > hi:
            return None
        return lo

    t = (qp[0] * s[1] - qp[1] * s[0]) / rxs
    u = qpxr / rxs
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return t
    return None


def _polygon_edges(polygon: Polygon) -> list[tuple[Point, Point]]:
    n = len(polygon)
    return [(polygon[i], polygon[(i + 1) % n]) for i in range(n)]


def _bounds_edges(bounds: tuple[float, float]) -> list[tuple[Point, Point]]:
    width, height = bounds
    corners: Polygon = [(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)]
    return _polygon_edges(corners)


def clip_segment(
    origin: Point,
    destination: Point,
    polygons: list[Polygon],
    bounds: Optional[tuple[float, float]],
) -> tuple[Point, bool]:
    """The single public judgment: origin -> destination against obstacle
    polygons and (optionally) location bounds, both in per-location local
    coordinates. Returns (stop_point, blocked).

    Semantics, in order:
    a. Degenerate origin — if bounds is present and origin lies outside
       [0, width] x [0, height], OR origin is inside any polygon: returns
       (origin, True). The judge never rescues the player (creator
       teleport, geometry edited underfoot); unblocking is a creator act,
       not adjudicator behavior.
    b. Zero-length segment — origin == destination (after the degenerate
       check): returns (destination, False).
    c. Edge set — all edges of all polygons, plus the four bounds edges
       when bounds is present (bounds are walls seen from inside). No
       containment assumption between obstacles and bounds; every edge
       the geometry hands over is judged.
    d. Judgment — the minimum t_hit across all edges. No hit: (destination,
       False). Hit: the stop point is pulled back along the segment by
       EPS_METERS (1 mm) so it lands strictly off the wall, clamped so it
       never backs past origin; returns (stop_point, True).
    """
    if bounds is not None:
        width, height = bounds
        ox, oy = origin
        if not (0.0 <= ox <= width and 0.0 <= oy <= height):
            return (origin, True)

    for polygon in polygons:
        if point_in_polygon(origin, polygon):
            return (origin, True)

    if origin == destination:
        return (destination, False)

    edges: list[tuple[Point, Point]] = []
    for polygon in polygons:
        edges.extend(_polygon_edges(polygon))
    if bounds is not None:
        edges.extend(_bounds_edges(bounds))

    best_t: Optional[float] = None
    for q1, q2 in edges:
        t = segment_intersection(origin, destination, q1, q2)
        if t is not None and (best_t is None or t < best_t):
            best_t = t

    if best_t is None:
        return (destination, False)

    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    seg_len = math.hypot(dx, dy)
    stop_t = best_t
    if seg_len > 0:
        stop_t = max(0.0, best_t - (EPS_METERS / seg_len))
    stop_point = (origin[0] + dx * stop_t, origin[1] + dy * stop_t)
    return (stop_point, True)
