"""The one writer of `world.active_pc_id`, the creator's choice of the player character her cockpit acts for (TICKET-0128, A1).

Commit-free: the caller owns the transaction. `write_active_pc` sets or
clears the choice and refuses any id that is not an active player character
of that world; `clear_active_pc_of` drops a deleted character from every
world that had chosen it.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from ..active_pc import world_player_characters
from ..models import World

ACTIVE_PC_REFUSED = "Ce personnage ne peut pas être le PJ actif."


def write_active_pc(db: Session, *, world: World, character_id: Optional[str]) -> World:
    """Set (or clear, with None) the world's active PC; ValueError on a foreign id."""
    if character_id is not None:
        allowed = {character.id for character, _ in world_player_characters(db, world.id)}
        if character_id not in allowed:
            raise ValueError(ACTIVE_PC_REFUSED)
    world.active_pc_id = character_id
    world.updated_at = datetime.now(UTC)
    db.add(world)
    return world


def clear_active_pc_of(db: Session, *, character_id: str) -> int:
    """Clear the choice of every world whose active PC is this character."""
    world_ids = list(db.exec(select(World.id).where(World.active_pc_id == character_id)).all())
    for world_id in world_ids:
        row: World = db.get(World, world_id)
        row.active_pc_id = None
        row.updated_at = datetime.now(UTC)
        db.add(row)
    return len(world_ids)
