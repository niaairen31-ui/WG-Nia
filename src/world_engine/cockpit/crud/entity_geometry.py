"""Author CRUD — location spatial write surface: playable bounds, obstacle
polygons and door rows. Extracted from `entities.py` (TICKET-0089,
BRIEF-0089-b) — pure move, no logic change.

The readers (`_location_geometry_dict`, `_location_doors_rows`) stay in
`entities.py` because `entities.py`'s own composite reads consume them, and
importing them from here would close a module-level cycle.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DbSession

from ...db import get_session
from ...models import Location
from ...writes import write_location_doors, write_location_obstacles

from ._router import router
from ._shared import _get_entity, _list_knowledge, _list_relations
from .entities import (
    _entity_dict,
    _extension_dict,
    _location_doors_rows,
    _location_geometry_dict,
    _location_subculture_rows,
)


class ObstacleIn(BaseModel):
    # EITHER vertices (>= 3, polygon-ready) OR rect (v1 UI shorthand,
    # [x, y, width, height]) — the endpoint expands rect server-side.
    vertices: Optional[list[list[float]]] = None
    rect: Optional[list[float]] = None


class LocationGeometryBody(BaseModel):
    bounds_width: Optional[float] = None
    bounds_height: Optional[float] = None
    obstacles: list[ObstacleIn] = []


class DoorIn(BaseModel):
    target_location_id: str
    x: float
    y: float


class LocationDoorsBody(BaseModel):
    doors: list[DoorIn] = []


@router.put("/entities/{entity_id}/geometry")
def set_location_geometry(entity_id: str, body: LocationGeometryBody, db: DbSession = Depends(get_session)) -> dict:
    """Full-replace a location's spatial geometry — playable bounds +
    obstacle polygons (TICKET-0029, BRIEF-0029-a). `rect` items are
    expanded server-side into 4 vertices clockwise from top-left
    `(x,y), (x+w,y), (x+w,y+h), (x,y+h)`; `vertices` items are
    polygon-ready as-is. One transaction: bounds on `location` +
    full-replace `obstacle`/`obstacle_vertex` via `write_location_obstacles`."""
    entity = _get_entity(db, entity_id)
    if entity.type != "location":
        raise HTTPException(404, f"Entity {entity_id!r} is not a location")

    if body.bounds_width is not None and body.bounds_width <= 0:
        raise HTTPException(422, "bounds_width must be > 0")
    if body.bounds_height is not None and body.bounds_height <= 0:
        raise HTTPException(422, "bounds_height must be > 0")

    polygons: list[list[tuple[float, float]]] = []
    for item in body.obstacles:
        if item.rect is not None:
            if len(item.rect) != 4:
                raise HTTPException(422, "rect must be [x, y, width, height]")
            x, y, w, h = item.rect
            if w <= 0 or h <= 0:
                raise HTTPException(422, "rect width and height must be > 0")
            polygons.append([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
        elif item.vertices is not None:
            polygons.append([(v[0], v[1]) for v in item.vertices])
        else:
            raise HTTPException(422, "each obstacle needs either 'vertices' or 'rect'")

    try:
        write_location_obstacles(
            db, world_id=entity.world_id, location_id=entity_id,
            obstacles=polygons, changed_by="creator",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    location = db.get(Location, entity_id)
    fields_set = body.model_fields_set
    # F1, TICKET-0040: a key absent from the body preserves the stored
    # value; an explicit null clears it. Same posture as
    # writes.upsert_location_type, which never overwrites a decided value
    # with NULL. Full-replace still governs `obstacle` rows below - only
    # the two bounds columns gained this distinction.
    if "bounds_width" in fields_set:
        location.bounds_width = body.bounds_width
    if "bounds_height" in fields_set:
        location.bounds_height = body.bounds_height
    db.add(location)
    db.commit()

    result = _entity_dict(entity)
    db.refresh(location)
    result["extension"] = _extension_dict("location", location)
    result["relations"] = _list_relations(entity_id, db)
    result["knowledge"] = _list_knowledge(entity_id, db)
    result["subculture_rows"] = _location_subculture_rows(entity_id, db)
    result["geometry"] = _location_geometry_dict(entity_id, db)
    return result


@router.put("/entities/{entity_id}/doors")
def set_location_doors(entity_id: str, body: LocationDoorsBody, db: DbSession = Depends(get_session)) -> dict:
    """Full-replace a location's `door` rows (TICKET-0034, BRIEF-0034-a).
    One row per `connects_to` neighbour the creator points a door at — the
    B1 gate (write_location_doors) rejects any target without a live
    connects_to edge. Nothing here resolves, judges or moves; see
    BRIEF-0034-b/-c for that."""
    entity = _get_entity(db, entity_id)
    if entity.type != "location":
        raise HTTPException(404, f"Entity {entity_id!r} is not a location")

    try:
        write_location_doors(
            db, world_id=entity.world_id, location_id=entity_id,
            doors=[d.model_dump() for d in body.doors], changed_by="creator",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()

    result = _entity_dict(entity)
    location = db.get(Location, entity_id)
    result["extension"] = _extension_dict("location", location)
    result["relations"] = _list_relations(entity_id, db)
    result["knowledge"] = _list_knowledge(entity_id, db)
    result["subculture_rows"] = _location_subculture_rows(entity_id, db)
    result["geometry"] = _location_geometry_dict(entity_id, db)
    result["doors"] = _location_doors_rows(entity_id, db)
    return result
