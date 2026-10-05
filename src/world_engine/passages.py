"""Place registry writer (TICKET-0105, BRIEF-0105-B, C-02).

`passage` records the last moment a character was at a location: one row
per (character, location) pair, `last_at` moving forward only. It is
non-canon bookkeeping, like `rencontre` and `visit`.

Every placement write is captured in ONE place (P1): a `before_flush`
listener on the SQLAlchemy `Session` class, registered when `db.py` is
imported. Whatever path creates a character with a location or changes its
`current_location_id` -- travel, the tick's NPC move, zone promotion, the
fiche, PC creation, a batch -- the listener sees the old and the new value at
flush time and records both: leaving a place is a contact with it as much as
entering it. A schedule names places without moving anyone, so
`write_npc_schedule` records its old and new places itself, through
`record_passages`.

This module is the ONLY site that adds a `Passage` row
(`tooling/verify/checks/fact_learning.py`, B1), the v2.14 migration's
backfill aside. No function here commits; the caller owns the transaction.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, Optional

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session as OrmSession
from sqlmodel import select

from .models import Character, Passage


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)


def _find(db: OrmSession, entity_id: str, location_id: str) -> Optional[Passage]:
    for obj in db.new:
        if isinstance(obj, Passage) and obj.entity_id == entity_id and obj.location_id == location_id:
            return obj
    with db.no_autoflush:
        return db.execute(
            select(Passage).where(Passage.entity_id == entity_id, Passage.location_id == location_id)
        ).scalars().first()


def record_passage(
    db: OrmSession,
    *,
    world_id: str,
    entity_id: str,
    location_id: str,
    at: Optional[datetime] = None,
) -> Passage:
    """Record that `entity_id` was at `location_id` at `at` (default: now,
    UTC). Creates the pair's row, or moves its `last_at` forward -- never
    back. Returns the row."""
    when = _utc(at or datetime.now(UTC))
    row = _find(db, entity_id, location_id)
    if row is None:
        row = Passage(world_id=world_id, entity_id=entity_id, location_id=location_id, last_at=when)
        db.add(row)
    elif _utc(row.last_at) < when:
        row.last_at = when
        db.add(row)
    return row


def record_passages(
    db: OrmSession,
    *,
    world_id: str,
    entity_id: str,
    location_ids: Iterable[str],
    at: Optional[datetime] = None,
) -> None:
    """`record_passage` for each distinct location of `location_ids`."""
    when = at or datetime.now(UTC)
    for location_id in sorted(set(location_ids)):
        record_passage(db, world_id=world_id, entity_id=entity_id, location_id=location_id, at=when)


def _moves(db: OrmSession) -> list[tuple[Character, list[str]]]:
    """Each character of the pending flush whose location is set or changed,
    with the places to record: the new one, and the one it left."""
    out = []
    for obj in db.new:
        if isinstance(obj, Character) and obj.current_location_id:
            out.append((obj, [obj.current_location_id]))
    for obj in db.dirty:
        if not isinstance(obj, Character):
            continue
        history = inspect(obj).attrs.current_location_id.history
        if history.has_changes():
            places = [p for p in list(history.added) + list(history.deleted) if p]
            if places:
                out.append((obj, places))
    return out


def _capture_placements(db: OrmSession, _flush_context, _instances) -> None:
    """`before_flush`: one passage per place a character enters or leaves."""
    moves = _moves(db)
    if not moves:
        return
    now = datetime.now(UTC)
    for character, places in moves:
        record_passages(db, world_id=character.world_id, entity_id=character.id,
                        location_ids=places, at=now)


def listener_registered() -> bool:
    """True when the placement listener is attached (read by the check)."""
    return event.contains(OrmSession, "before_flush", _capture_placements)


event.listen(OrmSession, "before_flush", _capture_placements)
