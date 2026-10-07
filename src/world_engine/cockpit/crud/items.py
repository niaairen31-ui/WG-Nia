"""Author CRUD — who holds how many of an item (TICKET-0109, BRIEF-0109-A,
A1). The creator's one write path into `item_holding`: an item is a kind
since v2.18, and giving it to someone, or laying it somewhere, is a holding.

    GET /api/items/{item_id}/holders   who holds the item
    PUT /api/item-holdings             set one holding's quantity

Every rule lives in `writes.write_holding`; a refusal is a 422.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DbSession

from ...db import get_session
from ...holdings import holders_of
from ...writes import write_holding
from ._router import router
from ._shared import _get_entity, _world_id


class HoldingBody(BaseModel):
    item_id: str
    holder_entity_id: str
    quantity: int


@router.get("/items/{item_id}/holders")
def list_item_holders(item_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    _get_entity(db, item_id)
    return [{"id": holder.id, "name": holder.name, "type": holder.type, "quantity": holding.quantity}
            for holding, holder in holders_of(db, item_id)]


@router.put("/item-holdings")
def set_holding(body: HoldingBody, db: DbSession = Depends(get_session)) -> dict:
    try:
        row = write_holding(db, world_id=_world_id(db), item_id=body.item_id,
                            holder_entity_id=body.holder_entity_id, quantity=body.quantity,
                            changed_by="creator_crud")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {"item_id": row.item_id, "holder_entity_id": row.holder_entity_id, "quantity": row.quantity}
