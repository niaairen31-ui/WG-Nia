"""The quest request's writer (TICKET-0121, BRIEF-0121-B, L1).

`quest_request` is non-canon: one row per agenda step the creator is asked
to design a quest for, moving along `QUEST_REQUEST_STATUSES`. This module
is its one writer; nothing here deletes a row (the world cascade does) and
nothing commits -- the caller owns the transaction (INV-18's posture).

- `open_request(...)` : open the request of a step, once per step; a step
  that already has one returns it unchanged.
- `move_request(...)` : move a request to a status, with the fields that
  change, appending the former state to `change_history`.
- `open_trial_request(...)` : open the request of a skill ready for a rank trial (TICKET-0116, F1-a): one live request per skill and rank in the world, none for a non-player character or while an open offer gives that rank.

Every shape the schema CHECKs is asserted here first, so a malformed call
fails as a `ValueError` naming the field rather than as an `IntegrityError`.
A proposal's fate is its `proposed_mutation.status`, never a status here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from sqlmodel import Session, select

from ..models import AgendaStep, Character, ProposedMutation, QuestRequest
from ..quest_requests import covering_trial_offer, trial_declaration, trial_subject

TRIAL_TRIGGER = "trial"
STEP_TRIGGERS: tuple[str, ...] = ("route", "blocked", "dropped")
QUEST_REQUEST_TRIGGERS: tuple[str, ...] = STEP_TRIGGERS + (TRIAL_TRIGGER,)
LIVE_PROPOSAL_STATUSES: tuple[str, ...] = ("proposed", "approved")
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
    if trigger == TRIAL_TRIGGER:
        raise ValueError("quest_request: a trial request opens through open_trial_request")
    if trigger not in STEP_TRIGGERS:
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


def _live(db: Session, request: QuestRequest) -> bool:
    """A request still in hand: `new`, or `proposed` while its proposal awaits or was approved."""
    if request.status == "new":
        return True
    if request.status != "proposed" or not request.mutation_id:
        return False
    proposal = db.get(ProposedMutation, request.mutation_id)
    return proposal is not None and proposal.status in LIVE_PROPOSAL_STATUSES


def open_trial_request(
    db: Session, *, world_id: str, character_id: str, skill_key: str, target_rank: int,
) -> Optional[QuestRequest]:
    """C-07: open the `trial` request of `skill_key` towards `target_rank`, once per skill and rank
    in the world -- the live one when it exists; None for a non-player character or while an open
    offer already gives that rank. No day, no step. Adds and flushes, never commits."""
    if not isinstance(skill_key, str) or not skill_key.strip():
        raise ValueError("quest_request: a trial request names its skill")
    if isinstance(target_rank, bool) or not isinstance(target_rank, int) or not 1 <= target_rank <= 5:
        raise ValueError(f"quest_request: a trial's target rank is 1 to 5, got {target_rank!r}")
    character = db.get(Character, character_id)
    if character is None or character.character_type != "player":
        return None
    if covering_trial_offer(db, world_id, skill_key, target_rank) is not None:
        return None
    existing = db.exec(select(QuestRequest).where(
        QuestRequest.world_id == world_id, QuestRequest.trigger == TRIAL_TRIGGER,
        QuestRequest.skill_key == skill_key, QuestRequest.target_rank == target_rank,
    ).order_by(QuestRequest.created_at, QuestRequest.id)).all()
    for request in existing:
        if _live(db, request):
            return request
    request = QuestRequest(
        world_id=world_id, character_id=character_id, trigger=TRIAL_TRIGGER,
        declaration=trial_declaration(db, world_id, character_id, skill_key, target_rank),
        subject=trial_subject(db, world_id, skill_key, target_rank),
        skill_key=skill_key, target_rank=target_rank,
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
