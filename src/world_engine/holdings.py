"""Who holds how many of an item (TICKET-0109, BRIEF-0109-A, A1). Reads
only: the one writer is `writes.write_holding`.

A holding at 0 reads as absent; every reader here filters `quantity > 0`.
The holder may be a character, a faction or a location (an object lying
somewhere is held by that place).
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import Entity, Item, ItemHolding


def held_quantity(db: Session, holder_entity_id: str, item_id: str) -> int:
    """How many of `item_id` `holder_entity_id` holds (0 when none)."""
    row = db.exec(select(ItemHolding).where(
        ItemHolding.holder_entity_id == holder_entity_id, ItemHolding.item_id == item_id)).first()
    return row.quantity if row is not None else 0


def items_held(db: Session, holder_entity_id: str) -> list[tuple[ItemHolding, Item, Entity]]:
    """What `holder_entity_id` holds, by item name."""
    return list(db.exec(
        select(ItemHolding, Item, Entity)
        .join(Item, Item.id == ItemHolding.item_id)
        .join(Entity, Entity.id == Item.id)
        .where(ItemHolding.holder_entity_id == holder_entity_id, ItemHolding.quantity > 0)
        .order_by(Entity.name, Entity.id)
    ).all())


def holders_of(db: Session, item_id: str) -> list[tuple[ItemHolding, Entity]]:
    """Who holds `item_id`, by holder name."""
    return list(db.exec(
        select(ItemHolding, Entity)
        .join(Entity, Entity.id == ItemHolding.holder_entity_id)
        .where(ItemHolding.item_id == item_id, ItemHolding.quantity > 0)
        .order_by(Entity.name, Entity.id)
    ).all())


def held_label(name: str, quantity: int) -> str:
    """« Dague », or « Fourrure de loup ×10 » -- one line of an inventory."""
    return name if quantity == 1 else f"{name} ×{quantity}"
