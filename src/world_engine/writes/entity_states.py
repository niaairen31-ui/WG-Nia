"""The writer of the system states an event may change (TICKET-0119,
BRIEF-0119-C; decision E1 of the conditions series): `character.vital_status`
(`sys:vital_status`) and `entity.status` (`sys:status`), the two columns
`writes.event_types.EFFECT_SYSTEM_KEYS` names.

- `write_system_state(db, *, world_id, entity_id, key, value)` : set one
  entity's system state, or `ValueError` -- the key is one of the two, the
  value one of its stored values (`attributes.SYSTEM_ATTRIBUTES`), the
  entity one of the world's (a character for the vital state). An
  unchanged value writes nothing and returns None; otherwise
  `(before, after)`. An entity leaving `active`, or a character leaving
  `alive`, leaves the gatherings it sat in (`gathering.close_open_memberships`
  -- INV-25's repair, the creator CRUD's own; a gathering it empties is
  ignored by the entry guard until it dissolves, INV-26). A location is never
  made `active` again here: that may promote its parent into a zone, which
  only its fiche confirms (TICKET-0101) -- refused.

These columns keep no history table: the reason of a change is the event
that made it, and its fact. Called only by `writes.events` (an event's
changes). Never commits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session

from ..attributes import system_attribute
from ..models import Character, Entity

SYSTEM_STATE_KEYS: tuple[str, ...] = ("sys:vital_status", "sys:status")


def write_system_state(
    db: Session, *, world_id: str, entity_id: str, key: str, value: str,
) -> Optional[tuple[str, str]]:
    """Set `key` of `entity_id` to `value` (see the module docstring)."""
    spec = system_attribute(key)
    if spec is None or key not in SYSTEM_STATE_KEYS:
        raise ValueError(f"{key!r} is not a state an event changes")
    if value not in dict(spec.values):
        raise ValueError(f"{value!r} is no value of « {spec.name} »")
    entity = db.get(Entity, entity_id)
    if entity is None or entity.world_id != world_id:
        raise ValueError(f"unknown entity {entity_id!r}")
    if key == "sys:vital_status":
        character = db.get(Character, entity_id)
        if character is None:
            raise ValueError(f"« {entity.name} » has no vital state")
        before = character.vital_status
        if before == value:
            return None
        character.vital_status = value
        db.add(character)
        leaves = before == "alive"
    else:
        before = entity.status
        if before == value:
            return None
        if entity.type == "location" and value == "active":
            raise ValueError(f"« {entity.name} » is made active again from its fiche, never by an event")
        entity.status = value
        leaves = before == "active"
    entity.updated_at = datetime.now(UTC)
    db.add(entity)
    db.flush()
    if leaves:
        # Imported here: `gathering` reaches the analyzers, which import `writes`.
        from ..gathering import close_open_memberships

        close_open_memberships(entity_id, db)
    return before, value
