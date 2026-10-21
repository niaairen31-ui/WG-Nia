"""The quest request's reads (TICKET-0121, BRIEF-0121-B, L1): which steps of an agenda are inquiry steps, by the requests that opened them, and the request as the creator's panel lists it (BRIEF-0121-E), and a rank trial's reads: the open offer that already gives the rank, the request's subject and declaration (TICKET-0116).

Writes live in `writes/quest_requests.py`; nothing here mutates.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import AgendaStep, Batch, Entity, PassPlay, ProposedMutation, QuestOffer, QuestOfferTerm, QuestRequest
from .skill_access import skill_label
from .skill_ranks import world_ladder

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


def request_dict(request: QuestRequest, db: Session) -> dict:
    """C-12: one request as the creator's panel lists it -- its proposal's id and status, its offer's
    id and title; no agenda or step id."""
    character = db.get(Entity, request.character_id)
    play = db.get(PassPlay, request.pass_play_id) if request.pass_play_id else None
    batch = db.get(Batch, play.batch_id) if play is not None else None
    proposal = db.get(ProposedMutation, request.mutation_id) if request.mutation_id else None
    offer = db.get(QuestOffer, request.offer_id) if request.offer_id else None
    return {
        "id": request.id, "trigger": request.trigger, "status": request.status,
        "declaration": request.declaration, "subject": request.subject,
        "character_name": character.name if character is not None else None,
        "day_number": batch.day_number if batch is not None else None,
        "existence_answer": request.existence_answer, "creator_text": request.creator_text,
        "note": request.note, "created_at": request.created_at.isoformat() if request.created_at else None,
        "proposal": {"id": proposal.id, "status": proposal.status} if proposal is not None else None,
        "offer": {"id": offer.id, "title": offer.title} if offer is not None else None,
    }


def world_requests(db: Session, world_id: str) -> list[QuestRequest]:
    """The active world's requests, newest first, the set-aside ones left out."""
    return list(db.exec(
        select(QuestRequest).where(QuestRequest.world_id == world_id, QuestRequest.status != "dropped")
        .order_by(QuestRequest.created_at.desc(), QuestRequest.id)).all())


def covering_trial_offer(db: Session, world_id: str, skill_key: str, target_rank: int) -> Optional[QuestOffer]:
    """C-07: the world's first `open` offer, by title then id, whose reward gives `target_rank` in
    `skill_key` -- while one exists, a ready skill asks no new trial."""
    return db.exec(
        select(QuestOffer).join(QuestOfferTerm, QuestOfferTerm.offer_id == QuestOffer.id)
        .where(QuestOffer.world_id == world_id, QuestOffer.status == "open",
               QuestOfferTerm.direction == "reward", QuestOfferTerm.currency == "rank",
               QuestOfferTerm.skill_key == skill_key, QuestOfferTerm.amount == target_rank)
        .order_by(QuestOffer.title, QuestOffer.id)
    ).first()


def trial_subject(db: Session, world_id: str, skill_key: str, target_rank: int) -> str:
    """C-07: a trial request's subject, the rank named by the world's label."""
    to = world_ladder(db, world_id)[target_rank].label
    return f"Épreuve de rang : « {skill_label(db, skill_key)} » vers {to}"


def trial_declaration(db: Session, world_id: str, character_id: str, skill_key: str, target_rank: int) -> str:
    """C-07: a trial request's declaration -- who is ready, in which skill, from which rank to which."""
    ladder = world_ladder(db, world_id)
    character = db.get(Entity, character_id)
    name = character.name if character is not None else character_id
    frm, to = ladder[target_rank - 1].label, ladder[target_rank].label
    return (f"{name} a assez pratiqué « {skill_label(db, skill_key)} » pour passer de {frm} à {to} : "
            "ce rang demande une épreuve.")
