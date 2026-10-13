"""The quest request's reads (TICKET-0121, BRIEF-0121-B, L1): which steps of an agenda are inquiry steps, by the requests that opened them.

Writes live in `writes/quest_requests.py`; nothing here mutates.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import AgendaStep, QuestRequest

INQUIRY_TRIGGERS: tuple[str, ...] = ("route", "dropped")


def inquiry_step_ids(db: Session, agenda_id: str) -> frozenset[str]:
    """The `agenda_step_id`s of the requests on `agenda_id`'s steps whose
    trigger is `route` or `dropped`."""
    rows = db.exec(
        select(QuestRequest.agenda_step_id)
        .join(AgendaStep, AgendaStep.id == QuestRequest.agenda_step_id)
        .where(AgendaStep.agenda_id == agenda_id, QuestRequest.trigger.in_(INQUIRY_TRIGGERS))
    ).all()
    return frozenset(rows)
