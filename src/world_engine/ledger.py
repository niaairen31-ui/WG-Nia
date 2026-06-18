"""Read helpers for the `ledger` table (BRIEF-18).

Pure reads — no balance is stored anywhere; it is computed on demand from
the append-only `ledger` rows. Writes go exclusively through
`writes.write_ledger_entry`.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select
from sqlalchemy import func

from .models import Ledger


def get_balance(db: Session, entity_id: str) -> int:
    """Sum of all `ledger.amount` rows for `entity_id`; 0 if none exist."""
    total = db.exec(
        select(func.coalesce(func.sum(Ledger.amount), 0)).where(Ledger.entity_id == entity_id)
    ).one()
    return int(total)


def list_entries(
    db: Session,
    *,
    entity_id: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 200,
) -> list[Ledger]:
    """List `ledger` rows, newest first. `entity_id`/`session_id` are optional, ANDed."""
    stmt = select(Ledger)
    if entity_id is not None:
        stmt = stmt.where(Ledger.entity_id == entity_id)
    if session_id is not None:
        stmt = stmt.where(Ledger.session_id == session_id)
    stmt = stmt.order_by(Ledger.created_at.desc()).limit(limit)
    return list(db.exec(stmt).all())


__all__ = ["get_balance", "list_entries"]
