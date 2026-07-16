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
from __future__ import annotations

import hashlib
import math

from . import geometry

Point = geometry.Point

INTERACTION_RANGE = 2.0    # world-meters; proximity threshold (intake, calibrate at live gate)
MEMBER_RING_RADIUS = 0.8   # world-meters; member offset around the gathering centroid
EDGE_MARGIN = 1.0          # world-meters; centroid candidates keep this off bounds edges
MAX_ATTEMPTS = 32          # deterministic rejection-sampling budget per point


def distance(a: Point, b: Point) -> float:
    """Plain Euclidean distance. Trivial on purpose: it exists so the
    single-site rule has a name to point at (the earshot rail), not
    because the math is hard."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _unit_floats(seed: str, counter: int, n: int) -> tuple[float, ...]:
    """n deterministic floats in [0, 1), derived from
    sha256(f"{seed}:{counter}"). The single source of pseudo-randomness
    in this module."""
    digest = hashlib.sha256(f"{seed}:{counter}".encode()).digest()
    out = []
    for i in range(n):
        chunk = digest[i * 8:(i + 1) * 8]
        value = int.from_bytes(chunk, "big") / float(1 << 64)
        out.append(value)
    return tuple(out)


def _centroid_candidate(gathering_id: str, k: int, bounds: tuple[float, float]) -> Point:
    width, height = bounds
    margin_x = EDGE_MARGIN if width > 2 * EDGE_MARGIN else 0.0
    margin_y = EDGE_MARGIN if height > 2 * EDGE_MARGIN else 0.0
    u, v = _unit_floats(gathering_id, k, 2)
    x = margin_x + u * (width - 2 * margin_x)
    y = margin_y + v * (height - 2 * margin_y)
    return (x, y)


def _derive_centroid(
    gathering_id: str,
    bounds: tuple[float, float],
    obstacles: list[geometry.Polygon],
) -> Point:
    candidate = (0.0, 0.0)
    for k in range(MAX_ATTEMPTS):
        candidate = _centroid_candidate(gathering_id, k, bounds)
        if not any(geometry.point_in_polygon(candidate, polygon) for polygon in obstacles):
            return candidate
    return candidate


def _member_candidate(entity_id: str, k: int, centroid: Point) -> Point:
    angle_u, jitter_u = _unit_floats(entity_id, k, 2)
    angle = angle_u * 2.0 * math.pi
    radius = MEMBER_RING_RADIUS * (0.6 + 0.4 * jitter_u)
    return (centroid[0] + radius * math.cos(angle), centroid[1] + radius * math.sin(angle))


def _in_bounds(point: Point, bounds: tuple[float, float]) -> bool:
    width, height = bounds
    x, y = point
    return 0.0 <= x <= width and 0.0 <= y <= height


def _derive_member_position(
    entity_id: str,
    centroid: Point,
    bounds: tuple[float, float],
    obstacles: list[geometry.Polygon],
) -> Point:
    candidate = centroid
    for k in range(MAX_ATTEMPTS):
        candidate = _member_candidate(entity_id, k, centroid)
        if not _in_bounds(candidate, bounds):
            continue
        if any(geometry.point_in_polygon(candidate, polygon) for polygon in obstacles):
            continue
        return candidate
    return centroid


def derive_positions(
    rosters: list[tuple[str, list[str]]],
    bounds: tuple[float, float],
    obstacles: list[geometry.Polygon],
) -> dict[str, Point]:
    """{entity_id: (x, y)} for every entity in every roster, clustered by
    gathering. Total: never raises, even against a degenerate all-wall
    location (saturation fallback)."""
    positions: dict[str, Point] = {}
    for gathering_id, entity_ids in rosters:
        centroid = _derive_centroid(gathering_id, bounds, obstacles)
        if len(entity_ids) == 1:
            positions[entity_ids[0]] = centroid
            continue
        for entity_id in entity_ids:
            positions[entity_id] = _derive_member_position(entity_id, centroid, bounds, obstacles)
    return positions
