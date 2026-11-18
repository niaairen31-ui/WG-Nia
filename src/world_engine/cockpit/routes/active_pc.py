"""The creator's choice of the player character her cockpit acts for (TICKET-0128, BRIEF-0128-B, A1).

`GET /api/active-pc` reads the active world's player characters and which
one the cockpit acts for; `PUT /api/active-pc` sets or clears the choice
through `writes/active_pc.write_active_pc` (one commit; a refused id is a
422 and nothing is written).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ...active_pc import active_pc_id_or_none, world_player_characters
from ...db import get_session
from ...models import World
from ...writes.active_pc import write_active_pc
from .. import crud as _crud

router = APIRouter()


class ActivePcBody(BaseModel):
    character_id: Optional[str] = None


def _active_pc_dict(db: Session, world_id: str) -> dict:
    world = db.get(World, world_id)
    active_pc_id = active_pc_id_or_none(db, world_id)
    return {
        "world_id": world_id,
        "active_pc_id": active_pc_id,
        "chosen": world.active_pc_id is not None and world.active_pc_id == active_pc_id,
        "characters": [
            {"id": character.id, "name": name}
            for character, name in world_player_characters(db, world_id)
        ],
    }


@router.get("/api/active-pc")
def get_active_pc(db: Session = Depends(get_session)) -> dict:
    """The active world's player characters and the one the cockpit acts for."""
    return _active_pc_dict(db, _crud._world_id(db))


@router.put("/api/active-pc")
def put_active_pc(body: ActivePcBody, db: Session = Depends(get_session)) -> dict:
    """Choose (or clear, with null) the active world's active PC."""
    world_id = _crud._world_id(db)
    world: World = db.get(World, world_id)
    try:
        write_active_pc(db, world=world, character_id=body.character_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return _active_pc_dict(db, world_id)
