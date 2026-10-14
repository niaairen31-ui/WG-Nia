"""The quest request's writer (TICKET-0121, BRIEF-0121-B, L1).

`quest_request` is non-canon: one row per agenda step the creator is asked
to design a quest for, moving along `QUEST_REQUEST_STATUSES`. This module
is its one writer; nothing here deletes a row (the world cascade does) and
nothing commits -- the caller owns the transaction (INV-18's posture).

- `open_request(...)` : open the request of a step, once per step; a step
  that already has one returns it unchanged.
- `move_request(...)` : move a request to a status, with the fields that
  change, appending the former state to `change_history`.

Every shape the schema CHECKs is asserted here first, so a malformed call
fails as a `ValueError` naming the field rather than as an `IntegrityError`.
A proposal's fate is its `proposed_mutation.status`, never a status here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from ..models import AgendaStep, QuestRequest

QUEST_REQUEST_TRIGGERS: tuple[str, ...] = ("route", "blocked", "dropped")
QUEST_REQUEST_STATUSES: tuple[str, ...] = (
    "new", "asking", "writing_lore", "proposed", "covered", "dropped",
)
EXISTENCE_ANSWERS: tuple[str, ...] = ("exists", "absent", "already")
QUEST_OFFER_CREATION = "quest_offer_creation"
DESIGNER_PRODUCER = "local_ai_quest_designer"

# The fields `move_request` may set besides the status (C-02).
_MOVABLE_FIELDS: tuple[str, ...] = (
    "subject", "existence_answer", "creator_text", "existing_entity_id",
    "lore_entry_id", "mutation_id", "offer_id", "note",
)


def open_request(
    db: Session, *, world_id: str, character_id: str, pass_play_id: str,
    trigger: str, declaration: str, agenda_step_id: str,
) -> QuestRequest:
    """Open the request of `agenda_step_id`, status `new`; the existing one
    when the step already has a request (idempotent per step)."""
    if trigger not in QUEST_REQUEST_TRIGGERS:
        raise ValueError(f"quest_request: unknown trigger {trigger!r}; one of {QUEST_REQUEST_TRIGGERS}")
    if not isinstance(declaration, str) or not declaration.strip():
        raise ValueError("quest_request: a declaration is not empty")
    if db.get(AgendaStep, agenda_step_id) is None:
        raise ValueError(f"quest_request: agenda step {agenda_step_id!r} does not exist")
    existing = db.exec(select(QuestRequest).where(QuestRequest.agenda_step_id == agenda_step_id)).first()
    if existing is not None:
        return existing
    request = QuestRequest(
        world_id=world_id, character_id=character_id, pass_play_id=pass_play_id,
        agenda_step_id=agenda_step_id, trigger=trigger, declaration=declaration,
    )
    db.add(request)
    db.flush()
    return request


def _snapshot(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def move_request(db: Session, request: QuestRequest, status: str, **fields: Any) -> QuestRequest:
    """Move `request` to `status`, setting `fields`; the former status, the
    former `updated_at` and each field changed are appended to
    `change_history` first. Never commits."""
    if status not in QUEST_REQUEST_STATUSES:
        raise ValueError(f"quest_request: unknown status {status!r}; one of {QUEST_REQUEST_STATUSES}")
    unknown = sorted(set(fields) - set(_MOVABLE_FIELDS))
    if unknown:
        raise ValueError(f"quest_request: unknown field(s) {unknown}; one of {_MOVABLE_FIELDS}")
    answer = fields.get("existence_answer")
    if answer is not None and answer not in EXISTENCE_ANSWERS:
        raise ValueError(f"quest_request: unknown existence answer {answer!r}; one of {EXISTENCE_ANSWERS}")
    former: dict[str, Any] = {"status": request.status, "updated_at": _snapshot(request.updated_at)}
    for name in fields:
        former[name] = getattr(request, name)
    request.change_history = [*(request.change_history or []), former]
    request.status = status
    request.updated_at = datetime.now(UTC)
    for name, value in fields.items():
        setattr(request, name, value)
    db.add(request)
    db.flush()
    return request
