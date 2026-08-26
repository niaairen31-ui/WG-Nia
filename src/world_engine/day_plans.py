"""Open-plan reads and the park/activate transition (TICKET-0077,
BRIEF-0077-a).

Parking and activating a player plan is a DIRECT WRITE, not a proposal.
`day_mutations.py` records the governing precedent: under V1 creating a
plan has no world footprint and stays `write_day_plan`'s direct write.
A status swap between two plans of the SAME player has the same property —
no NPC sees it, no relation, knowledge or ledger row moves — so there is
nothing for Nia to approve, and therefore nothing that can leave the day
blocked behind an unreviewed queue row. The audit trail is
`agenda.change_history`, appended by `write_agenda_status` on every
transition, exactly as for every other agenda status change.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Agenda, Character
from .writes import write_agenda_status

OPEN_PLAN_STATUSES: tuple[str, ...] = ("active", "paused")


def open_plans(character: Character, db: Session) -> list[Agenda]:
    """The player's open (not-yet-terminal) day plans, active-first then most
    recently created. Explicitly filtered — never a bare `select(Agenda)`
    (enumeration scope discipline)."""
    return db.exec(
        select(Agenda)
        .where(Agenda.owner_entity_id == character.id, Agenda.status.in_(OPEN_PLAN_STATUSES))
        .order_by((Agenda.status != "active"), Agenda.created_at.desc())
    ).all()


def active_plan(character: Character, db: Session) -> Optional[Agenda]:
    """The player's single `active` plan, or `None`."""
    return db.exec(
        select(Agenda).where(Agenda.owner_entity_id == character.id, Agenda.status == "active")
    ).first()


def park_active_plan(character: Character, db: Session) -> Optional[Agenda]:
    """Park the player's active plan, if any; return it (still the same row,
    now `paused`), or `None` when there is nothing to park.

    The `db.flush()` is REQUIRED: `write_agenda`'s one-active guard is a
    SELECT, so a plan created later in the SAME transaction would otherwise
    still see the old `active` row.
    """
    agenda = active_plan(character, db)
    if agenda is None:
        return None
    write_agenda_status(db, agenda=agenda, status="paused")
    db.flush()
    return agenda
