"""Zones and visitable locations (TICKET-0101) — pure reads, no write.

A location is a **zone** when at least one ACTIVE location names it as
`parent_location_id`; every other location is **visitable** (A1). The
property is derived from the tree on every call and never stored: there is
no zone flag, no per-type setting, no cache.

- `active_child_ids(db, location_id, exclude_id=None)` : the active children,
  oldest first (`entity.created_at`, then id).
- `is_zone(db, location_id)` : at least one active child.
- `zone_ids(db, world_id)` : every zone of a world, in one query.
- `geographic_link_type(db, a, b)` : `"borde"` when either endpoint is a zone,
  else `"connects_to"` (L1). The only place the type of a geographic link is
  decided.
- `require_visitable(db, location_id, what=...)` : raises `ZoneRefusal` when
  `location_id` is a zone (B1/Q1). `what` names the refused thing in the
  message shown to the creator.

Reads see the session's pending rows (autoflush), so a child added earlier in
the same transaction already makes its parent a zone.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Entity, Location


class ZoneRefusal(ValueError):
    """A being, an item or a discoverable detail was placed in a zone."""


def active_child_ids(db: Session, location_id: str, *, exclude_id: Optional[str] = None) -> list[str]:
    """Ids of the ACTIVE locations whose parent is `location_id`, oldest first;
    `exclude_id` is left out (the child being created or moved)."""
    rows = db.exec(
        select(Entity.id)
        .join(Location, Location.id == Entity.id)
        .where(Location.parent_location_id == location_id, Entity.status == "active")
        .order_by(Entity.created_at, Entity.id)
    ).all()
    return [row for row in rows if row != exclude_id]


def is_zone(db: Session, location_id: Optional[str]) -> bool:
    """True when `location_id` has at least one active child (A1)."""
    if not location_id:
        return False
    return bool(active_child_ids(db, location_id))


def zone_ids(db: Session, world_id: str) -> set[str]:
    """Every zone of `world_id`: the distinct parents of its active locations."""
    rows = db.exec(
        select(Location.parent_location_id)
        .join(Entity, Entity.id == Location.id)
        .where(
            Entity.world_id == world_id,
            Entity.status == "active",
            Location.parent_location_id.is_not(None),
        )
    ).all()
    return {row for row in rows if row}


def geographic_link_type(db: Session, entity_a_id: str, entity_b_id: str) -> str:
    """The type a geographic link between two locations must have (L1)."""
    if is_zone(db, entity_a_id) or is_zone(db, entity_b_id):
        return "borde"
    return "connects_to"


def require_visitable(db: Session, location_id: Optional[str], *, what: str) -> None:
    """Refuse a zone as the place of `what` (B1/Q1). A null id passes."""
    if not is_zone(db, location_id):
        return
    entity = db.get(Entity, location_id)
    name = entity.name if entity is not None else location_id
    raise ZoneRefusal(
        f"{what} : « {name} » est une zone, on ne peut s'y trouver que dans l'un de ses lieux"
    )
