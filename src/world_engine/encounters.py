"""Encounter registry writer and reads (TICKET-0091, BRIEF-0091-C, C-07).

`rencontre` records that two entities have met: one row per unordered pair
(`entity_lo_id < entity_hi_id`, compared as strings), the earliest known
encounter winning. It is non-canon bookkeeping, like `visit` and
`gathering` — derived from play traces (visit, gathering membership,
conversation) and authored state (NPC schedules, social relations), never
edited by hand, never updated, never deleted.

This module is the ONLY site that adds a `Rencontre` row
(`tooling/verify/checks/encounter_registry.py`). No function here commits;
the caller owns the transaction.
"""
from __future__ import annotations

from datetime import UTC, datetime
from itertools import combinations
from typing import Iterable, Optional

from sqlmodel import Session, or_, select

from .models import ENCOUNTER_SOURCES, Gathering, GatheringMember, Rencontre


def _ordered(a_id: str, b_id: str) -> tuple[str, str]:
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def _find_pair(db: Session, lo_id: str, hi_id: str) -> Optional[Rencontre]:
    return db.exec(
        select(Rencontre).where(
            Rencontre.entity_lo_id == lo_id,
            Rencontre.entity_hi_id == hi_id,
        )
    ).first()


def record_encounter(
    db: Session,
    *,
    world_id: str,
    a_id: str,
    b_id: str,
    source: str,
    at: Optional[datetime] = None,
    source_ref: Optional[str] = None,
) -> Optional[Rencontre]:
    """Record that `a_id` and `b_id` have met. Returns the new row, or
    `None` for a self pair or a pair already recorded (idempotent: read
    guard before add). `source` outside `ENCOUNTER_SOURCES` raises
    `ValueError`. `at` defaults to now (UTC)."""
    if source not in ENCOUNTER_SOURCES:
        raise ValueError(f"record_encounter: invalid source {source!r}")
    if a_id == b_id:
        return None
    lo_id, hi_id = _ordered(a_id, b_id)
    if _find_pair(db, lo_id, hi_id) is not None:
        return None
    row = Rencontre(
        world_id=world_id,
        entity_lo_id=lo_id,
        entity_hi_id=hi_id,
        first_at=at or datetime.now(UTC),
        source=source,
        source_ref=source_ref,
    )
    db.add(row)
    db.flush()
    return row


def record_encounters_among(
    db: Session,
    *,
    world_id: str,
    entity_ids: Iterable[str],
    source: str,
    at: Optional[datetime] = None,
    source_ref: Optional[str] = None,
) -> int:
    """Record every unordered pair of the distinct `entity_ids`; returns
    the number of new rows."""
    distinct = sorted(set(entity_ids))
    created = 0
    for a_id, b_id in combinations(distinct, 2):
        if record_encounter(
            db, world_id=world_id, a_id=a_id, b_id=b_id, source=source,
            at=at, source_ref=source_ref,
        ) is not None:
            created += 1
    return created


def record_gathering_join(db: Session, *, gathering_id: str, joiner_id: str) -> int:
    """Pair `joiner_id` with every other open member (`left_at IS NULL`) of
    the gathering, source `gathering`, `source_ref` = the gathering id;
    returns the number of new rows."""
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        return 0
    member_ids = db.exec(
        select(GatheringMember.entity_id).where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.left_at.is_(None),
            GatheringMember.entity_id != joiner_id,
        )
    ).all()
    created = 0
    for member_id in set(member_ids):
        if record_encounter(
            db, world_id=gathering.world_id, a_id=joiner_id, b_id=member_id,
            source="gathering", source_ref=gathering_id,
        ) is not None:
            created += 1
    return created


def acquaintances(db: Session, entity_id: str) -> set[str]:
    """Every entity id paired with `entity_id` in `rencontre`."""
    rows = db.exec(
        select(Rencontre).where(
            or_(Rencontre.entity_lo_id == entity_id, Rencontre.entity_hi_id == entity_id)
        )
    ).all()
    return {r.entity_hi_id if r.entity_lo_id == entity_id else r.entity_lo_id for r in rows}


def have_met(db: Session, a_id: str, b_id: str) -> bool:
    """True when the unordered pair `{a_id, b_id}` has a `rencontre` row."""
    if a_id == b_id:
        return False
    return _find_pair(db, *_ordered(a_id, b_id)) is not None
