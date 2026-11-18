"""The player character a creator surface acts for: one resolver for every surface of the cockpit (TICKET-0128, A1; INV-70).

A world may hold several player characters. The creator picks the one her
cockpit acts for (`world.active_pc_id`, written only by
`writes/active_pc.py`); a world with a single active PC needs no choice.
Several and none chosen is a refusal, never a pick. Reads only; no HTTP
here -- `cockpit/crud/_shared.py` gives the cockpit its 400 / 409 face.
"""
from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Character, Entity, World

NO_PC_MESSAGE = "Aucun personnage joueur dans ce monde."
CHOOSE_PC_MESSAGE = "Choisissez le PJ actif."


class NoPlayerCharacter(LookupError):
    """The world holds no active player character."""


class ActivePcUnchosen(LookupError):
    """The world holds several active player characters and none is chosen."""


def world_player_characters(db: Session, world_id: str) -> list[tuple[Character, str]]:
    """Every active player character of the world with its name, by name then id."""
    return list(db.exec(
        select(Character, Entity.name)
        .join(Entity, Entity.id == Character.id)
        .where(
            Character.world_id == world_id,
            Character.character_type == "player",
            Entity.status == "active",
        )
        .order_by(Entity.name, Entity.id)
    ).all())


def resolve_active_pc(db: Session, world_id: str) -> Character:
    """The chosen active PC when it is one of the world's, else the only one."""
    pcs = [character for character, _ in world_player_characters(db, world_id)]
    world = db.get(World, world_id)
    if world is not None and world.active_pc_id is not None:
        for character in pcs:
            if character.id == world.active_pc_id:
                return character
    if len(pcs) == 1:
        return pcs[0]
    if not pcs:
        raise NoPlayerCharacter(NO_PC_MESSAGE)
    raise ActivePcUnchosen(CHOOSE_PC_MESSAGE)


def active_pc_id_or_none(db: Session, world_id: str) -> Optional[str]:
    """The resolved active PC's id, or None when there is none to resolve."""
    try:
        return resolve_active_pc(db, world_id).id
    except (NoPlayerCharacter, ActivePcUnchosen):
        return None
