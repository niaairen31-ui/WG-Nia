"""Link-agent NPC sheet rendering (TICKET-0091 BRIEF-B, pure move).

`_location_chain_names` and `_npc_sheet` moved verbatim out of
`link_author.py` for its module budget; `link_author.py` imports
`_npc_sheet` back. Code-owned, no model call, no write.
"""

from __future__ import annotations

from sqlmodel import Session

from .context import read_public_memberships
from .models import Character, Entity, Location


def _location_chain_names(db: Session, location_id: str | None) -> list[str]:
    """Immediate location name, then each ancestor's name up the
    `parent_location_id` chain. Cycle-guarded (visited set)."""
    names: list[str] = []
    visited: set[str] = set()
    current_id = location_id
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        entity = db.get(Entity, current_id)
        location = db.get(Location, current_id)
        if entity is None or location is None:
            break
        names.append(entity.name)
        current_id = location.parent_location_id
    return names


def _npc_sheet(db: Session, entity_id: str) -> str:
    entity = db.get(Entity, entity_id)
    character = db.get(Character, entity_id)
    memberships = read_public_memberships(entity_id, db)
    factions = "; ".join(
        f"{name} ({role})" if role else name for name, role in memberships
    ) or "none"
    location_ids = character.current_location_id if character else None
    location_chain = _location_chain_names(db, location_ids)
    location_text = " -> ".join(location_chain) if location_chain else "unknown"

    return "\n".join([
        f"Name: {entity.name if entity else 'unknown'}",
        f"Description: {(entity.description if entity else None) or ''}",
        f"Appearance: {(character.appearance if character else None) or ''}",
        f"Backstory: {(character.backstory if character else None) or ''}",
        f"Aversion: {(character.aversion if character else None) or ''}",
        f"Vital status: {character.vital_status if character else 'unknown'}",
        f"Factions: {factions}",
        f"Location: {location_text}",
    ])
