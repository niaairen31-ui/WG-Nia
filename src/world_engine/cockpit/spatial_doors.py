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
from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .. import geometry, placement
from ..models import Door, Entity, Relation
from . import crud as _crud

Point = geometry.Point


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
    rows = db.exec(select(Door).where(Door.location_id == location_id)).all()
    result: list[dict] = []
    for row in rows:
        target = db.get(Entity, row.target_location_id)
        if (
            target is None
            or target.type != "location"
            or target.status != "active"
            or target.world_id != world_id
        ):
            continue

        # Read the connects_to rows in both column orders, exactly as
        # play.py:847 _location_neighbours does. This is the fifth
        # connects_to reader; decision D1 (BRIEF-19) stands — do NOT
        # refactor them together.
        rel_a = db.exec(
            select(Relation).where(
                Relation.type == "connects_to",
                Relation.entity_a_id == location_id,
                Relation.entity_b_id == row.target_location_id,
            )
        ).first()
        rel_b = db.exec(
            select(Relation).where(
                Relation.type == "connects_to",
                Relation.entity_a_id == row.target_location_id,
                Relation.entity_b_id == location_id,
            )
        ).first()
        if rel_a is None and rel_b is None:
            continue

        result.append({
            "id": row.id,
            "target_location_id": row.target_location_id,
            "target_name": target.name,
            "x": row.x,
            "y": row.y,
        })
    result.sort(key=lambda d: d["target_name"])
    return result


def doors_in_range(location_id: str, world_id: str, position: Point, db: Session) -> list[dict]:
    """[{door_id, target_location_id, target_name, distance}] for the
    live doors within placement.DOOR_RANGE of a transient position,
    nearest first, distance rounded to 3. Advisory (G-A): it enables
    the client's affordance; the door-travel endpoint re-judges the
    same predicate itself and is what actually gates."""
    result: list[dict] = []
    for door in location_doors(location_id, world_id, db):
        d = placement.distance(position, (door["x"], door["y"]))
        if d <= placement.DOOR_RANGE:
            result.append({
                "door_id": door["id"],
                "target_location_id": door["target_location_id"],
                "target_name": door["target_name"],
                "distance": round(d, 3),
            })
    result.sort(key=lambda entry: entry["distance"])
    return result


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
    geometry_dict = _crud._location_geometry_dict(location_id, db)
    bounds_width = geometry_dict["bounds_width"]
    bounds_height = geometry_dict["bounds_height"]
    if bounds_width is None or bounds_height is None:
        return {"x": 0.0, "y": 0.0, "anchor": "center"}

    bounds = (bounds_width, bounds_height)
    obstacles: list[geometry.Polygon] = [
        [(v[0], v[1]) for v in obstacle["vertices"]]
        for obstacle in geometry_dict["obstacles"]
    ]

    if from_location_id:
        # The return door is location_doors(location_id, ...) filtered on
        # target_location_id == from_location_id — at most one by
        # idx_door_target, so no tie-break exists to write.
        return_door = next(
            (
                door for door in location_doors(location_id, world_id, db)
                if door["target_location_id"] == from_location_id
            ),
            None,
        )
        if return_door is not None:
            anchor: Point = (return_door["x"], return_door["y"])
            degenerate = not placement._in_bounds(anchor, bounds) or any(
                geometry.point_in_polygon(anchor, obstacle) for obstacle in obstacles
            )
            if not degenerate:
                x, y = placement.spawn_point(return_door["id"], anchor, bounds, obstacles)
                return {"x": x, "y": y, "anchor": "door"}

    center = (bounds[0] / 2.0, bounds[1] / 2.0)
    return {"x": center[0], "y": center[1], "anchor": "center"}
