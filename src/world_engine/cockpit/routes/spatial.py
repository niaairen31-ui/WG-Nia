"""Spatial adjudication routes (TICKET-0030, BRIEF-0030-b).

TRANSIENT ADJUDICATION register: these endpoints read persistent
geometry, judge transient positions, and persist NOTHING — neither
_apply_mutation nor creator CRUD. Player position lives client-side
for the duration of a scene (workstream decision Q1); the server is
judge, never registrar. All intersection math lives in
world_engine.geometry (sole collision authority) — this module is a
caller only. Ticket 0031's proximity endpoint joins this module.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from ... import geometry
from ...db import get_session
from ...models import Character, Location
from .. import crud as _crud

router = APIRouter()


class PointBody(BaseModel):
    x: float
    y: float


class MoveCheckBody(BaseModel):
    location_id: str
    origin: PointBody
    destination: PointBody


@router.post("/api/spatial/move-check")
def move_check(
    body: MoveCheckBody,
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    """Judge a transient player movement segment against the persistent
    obstacle geometry of the player's current location. Read-only:
    the handler performs zero writes of any kind."""
    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
    char = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player character {player_id!r} not found")

    if body.location_id != char.current_location_id:
        raise HTTPException(
            status_code=409,
            detail="location_id is not the player's current location",
        )

    location = db.get(Location, body.location_id)
    if location is None:
        raise HTTPException(status_code=404, detail=f"Location {body.location_id!r} not found")

    if location.bounds_width is None or location.bounds_height is None:
        raise HTTPException(status_code=409, detail="location has no spatial mode")

    coords = (body.origin.x, body.origin.y, body.destination.x, body.destination.y)
    if not all(math.isfinite(c) for c in coords):
        raise HTTPException(status_code=422, detail="coordinates must be finite")

    geometry_dict = _crud._location_geometry_dict(body.location_id, db)
    polygons: list[geometry.Polygon] = [
        [(v[0], v[1]) for v in obstacle["vertices"]]
        for obstacle in geometry_dict["obstacles"]
    ]
    bounds = (geometry_dict["bounds_width"], geometry_dict["bounds_height"])

    point, blocked = geometry.clip_segment(
        (body.origin.x, body.origin.y),
        (body.destination.x, body.destination.y),
        polygons,
        bounds,
    )
    return {"x": point[0], "y": point[1], "blocked": blocked}
