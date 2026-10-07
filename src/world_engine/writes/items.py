"""`item_holding`: the one writer (TICKET-0109, BRIEF-0109-A, A1).

`write_holding` sets (`quantity=`) or moves (`delta=`) how many of an item
an entity holds. It refuses, before any write: an item that is not of the
world, a holder that is not an active entity of the world, a location holder
that is a zone when the quantity grows (`require_visitable`, CLAUDE.md « no
being, item or discoverable detail is placed in a zone »; taking items out of
a place that became a zone is how a promotion moves them), a result below 0,
and both or neither of `quantity`/`delta`. The previous quantity goes to the
row's `change_history`; a row at 0 is kept, never deleted.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from ..models import Entity, Item, ItemHolding
from ..zone_rules import ZoneRefusal, require_visitable


def _check_parties(db: Session, world_id: str, item_id: str, holder_entity_id: str, adds: bool) -> None:
    item = db.get(Entity, item_id) if item_id else None
    if item is None or item.world_id != world_id or item.type != "item" or db.get(Item, item_id) is None:
        raise ValueError(f"write_holding: {item_id!r} is not an item of this world")
    holder = db.get(Entity, holder_entity_id) if holder_entity_id else None
    if holder is None or holder.world_id != world_id or holder.status != "active":
        raise ValueError(f"write_holding: holder {holder_entity_id!r} is not an active entity of this world")
    if holder.type == "location" and adds:
        try:
            require_visitable(db, holder.id, what="Lieu de l'objet")
        except ZoneRefusal as exc:
            raise ValueError(str(exc)) from exc


def write_holding(
    db: Session,
    *,
    world_id: str,
    item_id: str,
    holder_entity_id: str,
    quantity: Optional[int] = None,
    delta: Optional[int] = None,
    changed_by: str,
) -> ItemHolding:
    """Set or move one holding; returns the row (added to the session)."""
    if (quantity is None) == (delta is None):
        raise ValueError("write_holding: give exactly one of quantity and delta")
    value = quantity if quantity is not None else delta
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"write_holding: {value!r} is not an integer")
    row = db.exec(select(ItemHolding).where(
        ItemHolding.item_id == item_id, ItemHolding.holder_entity_id == holder_entity_id)).first()
    before = row.quantity if row is not None else 0
    after = quantity if quantity is not None else before + delta
    _check_parties(db, world_id, item_id, holder_entity_id, adds=after > before)
    if after < 0:
        raise ValueError(f"write_holding: {before} held, cannot remove {-delta}")
    if row is None:
        row = ItemHolding(world_id=world_id, item_id=item_id, holder_entity_id=holder_entity_id,
                          quantity=0, change_history=[])
    else:
        history = list(row.change_history or [])
        history.append({"quantity": before, "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                        "by": changed_by})
        row.change_history = history
        sa_attrs.flag_modified(row, "change_history")
    row.quantity = after
    row.updated_at = datetime.now(UTC)
    db.add(row)
    return row
