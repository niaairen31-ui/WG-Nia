"""Spatial adjudication routes (TICKET-0030, BRIEF-0030-b; TICKET-0031,
BRIEF-0031-b).

TRANSIENT ADJUDICATION register: these endpoints read persistent
geometry, judge transient positions, and persist NOTHING — neither
_apply_mutation nor creator CRUD. Player position lives client-side
for the duration of a scene (workstream decision Q1); the server is
judge, never registrar. All intersection math lives in
world_engine.geometry (sole collision authority); all NPC placement and
distance math lives in world_engine.placement (sole spatial-distance
authority) — this module is a caller only.

Client handoff contract (TICKET-0032, BRIEF-0032-a; AMENDS the 0031
paragraph this replaces, decision G2-b): the client maps
`/api/spatial/proximity`'s returned `npc_id`s onto the rosters already
present in `_scene_response`, enables the "Parler" affordance for
in-range NPCs, and fires `POST /api/scene/join` with `target_gathering_id`
set to that roster's gathering id — a deterministic targeted join, zero
model calls. The previously-cited `POST /api/conversations/start` created
gathering-less conversations, invisible to `_active_conv_for_gathering`;
it remains for 1:1 pilot flows only. Zero server coupling — this is an
advisory gate (G-A), not a structural one.

Door flow (TICKET-0034, BRIEF-0034-b): `doors_in_range` (folded into this
module's proximity response) feeds `GET /api/spatial/spawn`, which feeds
`POST /api/spatial/travel` (BRIEF-0034-c). `/api/spatial/travel` lives in
`routes/play.py`, not here, precisely BECAUSE it writes and this module's
zero-write register forbids it.
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from ... import geometry, placement
from ...db import get_session
from ...models import Character, Location
from .. import crud as _crud
from .. import spatial_doors, spatial_presence

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


class ProximityBody(BaseModel):
    location_id: str
    position: PointBody


def _resolve_spatial_location(location_id: str, player_id: Optional[str], db: Session) -> tuple[str, Location]:
    """Shared guard chain (move-check parity): resolve the player, verify
    `location_id` is their current location, resolve the location, and
    verify it is in spatial mode. Returns (world_id, location)."""
    world_id = _crud._world_id(db)
    player_id = player_id or _crud._player_character_id(db, world_id)
    char = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player character {player_id!r} not found")

    if location_id != char.current_location_id:
        raise HTTPException(
            status_code=409,
            detail="location_id is not the player's current location",
        )

    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail=f"Location {location_id!r} not found")

    if location.bounds_width is None or location.bounds_height is None:
        raise HTTPException(status_code=409, detail="location has no spatial mode")

    return world_id, location


@router.get("/api/spatial/presence")
def spatial_presence_endpoint(
    location_id: str = Query(...),
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    """Drawable NPC circles for a spatial-mode location: gathering-clustered,
    deterministic, recomputed from scratch on every call. Read-only: the
    handler performs zero writes of any kind."""
    world_id, location = _resolve_spatial_location(location_id, player_id, db)
    npcs = spatial_presence.npc_positions(location.id, world_id, db)
    return {"npcs": npcs}


@router.post("/api/spatial/proximity")
def spatial_proximity(
    body: ProximityBody,
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    """Judge a transient player position against the same recomputed NPC
    positions `presence` draws. Advisory only (G-A): enables the client's
    talk affordance, never gates `/api/conversations/start` itself.
    Read-only: the handler performs zero writes of any kind."""
    world_id, location = _resolve_spatial_location(body.location_id, player_id, db)

    if not math.isfinite(body.position.x) or not math.isfinite(body.position.y):
        raise HTTPException(status_code=422, detail="position must be finite")

    npcs = spatial_presence.npc_positions(location.id, world_id, db)
    position = (body.position.x, body.position.y)
    in_range = []
    for npc in npcs:
        d = placement.distance(position, (npc["x"], npc["y"]))
        if d <= placement.INTERACTION_RANGE:
            in_range.append({"npc_id": npc["id"], "name": npc["name"], "distance": round(d, 3)})
    in_range.sort(key=lambda entry: entry["distance"])
    return {
        "in_range": in_range,
        "threshold": placement.INTERACTION_RANGE,
        "doors_in_range": spatial_doors.doors_in_range(location.id, world_id, position, db),
        "door_threshold": placement.DOOR_RANGE,
    }


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
    world_id, location = _resolve_spatial_location(location_id, player_id, db)
    return spatial_doors.resolve_spawn(location.id, world_id, from_location_id, db)
