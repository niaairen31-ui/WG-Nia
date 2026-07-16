"""NPC spatial presence assembler (TICKET-0031, BRIEF-0031-a). The SOLE
site that turns a location into named NPC positions; every reader
(presence endpoint, proximity endpoint, future earshot) calls
`npc_positions`.

TRANSIENT ADJUDICATION register: reads persistent geometry and open
gatherings, derives transient positions via `placement.derive_positions`,
persists nothing.
"""
from __future__ import annotations

from sqlmodel import Session

from .. import geometry, placement
from ..models import Character
from . import crud as _crud
from . import play as _play


def npc_positions(location_id: str, world_id: str, db: Session) -> list[dict]:
    """[{id, name, x, y}] for every present NPC, gathering-clustered,
    deterministic. Read-only; persists nothing."""
    session = _play._get_or_open_session(world_id, db)
    gatherings = _play._open_gatherings(location_id, session.id, db)

    rosters: list[tuple[str, list[str]]] = []
    names: dict[str, str] = {}
    for gathering in gatherings:
        entity_ids: list[str] = []
        for _gm, entity in _play._active_members(gathering.id, db):
            character = db.get(Character, entity.id)
            if character is not None and character.character_type == "player":
                continue
            entity_ids.append(entity.id)
            names[entity.id] = entity.name
        if entity_ids:
            rosters.append((gathering.id, entity_ids))

    geometry_dict = _crud._location_geometry_dict(location_id, db)
    bounds = (geometry_dict["bounds_width"], geometry_dict["bounds_height"])
    obstacles: list[geometry.Polygon] = [
        [(v[0], v[1]) for v in obstacle["vertices"]]
        for obstacle in geometry_dict["obstacles"]
    ]

    positions = placement.derive_positions(rosters, bounds, obstacles)

    result: list[dict] = []
    for _gathering_id, entity_ids in rosters:
        for entity_id in entity_ids:
            x, y = positions[entity_id]
            result.append({"id": entity_id, "name": names[entity_id], "x": x, "y": y})
    return result
