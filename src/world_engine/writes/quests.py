"""Quest offers and quests: the writers (TICKET-0108, BRIEF-0108-B,
contract C-03).

- `write_quest_offer(...)` : create or save one offer, all or nothing. Its
  steps and conditions are replaced whole (the `write_npc_prices`
  full-replace shape, `DELETE FROM` scoped to the offer, then the submitted
  set); the offer row snapshots its previous state into `change_history`.
- `accept_quest(...)`      : the player takes an offer (B1, A1): one agenda
  born `paused` through `write_agenda`, its steps (the first `active`, the
  creator-agenda precedent) and their conditions copied from the offer,
  the `quest` row, and its own copy of the offer's terms (TICKET-0109, B1). Eligibility and L1 are judged HERE, so no caller can
  skip them.
- `abandon_quest(...)`     : N1, the quest's agenda to `abandoned` through
  `write_agenda_status`; nothing is deleted.

Every condition goes through `conditions.clean_condition`, the same checks
as a day plan's (B1, then I1 of TICKET-0111: one language), and is written
by `conditions.write_condition`. None of these functions commits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from ..conditions import Bindings, ConditionTree, evaluate, leaves, read_condition
from ..day_plan import MAX_PLAN_STEPS, PlanStep
from ..models import (
    BASE_SKILL_DOMAINS,
    QUEST_OFFER_STATUSES,
    Agenda,
    AgendaStep,
    Character,
    Entity,
    PassPlay,
    ProposedMutation,
    Quest,
    QuestOffer,
    QuestOfferStep,
)
from .debts import is_active_member
from .conditions import clean_condition, delete_offer_conditions, write_condition
from .goals_agendas import write_agenda, write_agenda_status, write_agenda_step
from .quest_terms import TERM_COLUMNS, TermSpec, clean_terms, copy_terms_to_quest, offer_terms, write_offer_terms

# An offer is given by a character or a faction of the world (H1).
QUEST_GIVER_TYPES: tuple[str, ...] = ("character", "faction")

# The agenda statuses of a quest still open (M1): the others are over.
OPEN_QUEST_STATUSES: tuple[str, ...] = ("active", "paused")


def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, object]]:
    if not 1 <= len(steps) <= MAX_PLAN_STEPS:
        raise ValueError(f"write_quest_offer: an offer has 1 to {MAX_PLAN_STEPS} steps, got {len(steps)}")
    clean: list[tuple[PlanStep, object]] = []
    for index, step in enumerate(steps):
        if not isinstance(step.objective, str) or not step.objective.strip():
            raise ValueError(f"write_quest_offer: step {index} needs an objective")
        if not isinstance(step.cost, int) or isinstance(step.cost, bool) or not 1 <= step.cost <= 4:
            raise ValueError(f"write_quest_offer: step {index} has invalid cost {step.cost!r}")
        if step.domain is not None and step.domain not in BASE_SKILL_DOMAINS:
            raise ValueError(f"write_quest_offer: step {index} has invalid domain {step.domain!r}")
        clean.append((step, clean_condition(db, world_id, step.prerequisite, f"write_quest_offer: step {index}: ")))
    return clean


def _check_giver(db: Session, world_id: str, giver_entity_id: str) -> None:
    giver = db.get(Entity, giver_entity_id) if giver_entity_id else None
    if (giver is None or giver.world_id != world_id or giver.type not in QUEST_GIVER_TYPES
            or giver.status != "active"):
        raise ValueError(f"write_quest_offer: giver {giver_entity_id!r} is not an active character or faction")


def _check_contact(db: Session, world_id: str, giver_entity_id: str, contact_entity_id: Optional[str]) -> None:
    """X1 (TICKET-0110): an offer's contact is an active character member of
    its faction giver; a character giver has none."""
    if contact_entity_id is None:
        return
    giver, contact = db.get(Entity, giver_entity_id), db.get(Entity, contact_entity_id)
    if giver is None or giver.type != "faction":
        raise ValueError("write_quest_offer: only an offer given by a faction names a contact")
    if (contact is None or contact.world_id != world_id or contact.type != "character" or contact.status != "active"
            or not is_active_member(db, contact.id, giver.id)):
        raise ValueError(f"write_quest_offer: contact {contact_entity_id!r} is not an active member of the giver")


def _snapshot(offer: QuestOffer) -> None:
    history = list(offer.change_history or [])
    history.append({
        "giver_entity_id": offer.giver_entity_id, "contact_entity_id": offer.contact_entity_id,
        "title": offer.title, "summary": offer.summary,
        "repeatable": offer.repeatable, "status": offer.status,
        "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
    })
    offer.change_history = history
    sa_attrs.flag_modified(offer, "change_history")


def write_quest_offer(
    db: Session,
    *,
    world_id: str,
    offer: Optional[QuestOffer],
    giver_entity_id: str,
    title: str,
    summary: Optional[str],
    repeatable: bool,
    status: str,
    eligibility: Optional[ConditionTree],
    steps: list[PlanStep],
    terms: Optional[list[TermSpec]] = None,
    contact_entity_id: Optional[str] = None,
) -> QuestOffer:
    """Create (`offer` None) or save one offer (C-03). Everything is
    validated before the first write; a `quest_state` leaf naming the offer
    itself is refused (a quest cannot wait on its own state). `terms` (TICKET-0109,
    B1) replaces the offer's costs and rewards whole; None keeps them, each
    re-validated against the giver, who may have changed.
    `contact_entity_id` (TICKET-0110, X1) is written as given."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("write_quest_offer: title is required")
    if status not in QUEST_OFFER_STATUSES:
        raise ValueError(f"write_quest_offer: status must be one of {QUEST_OFFER_STATUSES}, got {status!r}")
    _check_giver(db, world_id, giver_entity_id)
    _check_contact(db, world_id, giver_entity_id, contact_entity_id or None)
    every = list(leaves(eligibility)) + [req for step in steps for req in leaves(step.prerequisite)]
    if offer is not None and any(r.type == "quest_state" and r.target_key == offer.id for r in every):
        raise ValueError("write_quest_offer: an offer cannot require its own state")
    clean_eligibility = clean_condition(db, world_id, eligibility, "write_quest_offer: eligibility: ")
    clean_steps = _clean_offer_steps(db, world_id, steps)
    if terms is None:
        terms = [TermSpec(**{c: getattr(t, c) for c in TERM_COLUMNS}) for t in offer_terms(db, offer.id)] if offer else []
    clean_term_rows = clean_terms(db, world_id, giver_entity_id, terms)

    if offer is None:
        offer = QuestOffer(world_id=world_id, giver_entity_id=giver_entity_id, title=title.strip(), change_history=[])
    else:
        _snapshot(offer)
        delete_offer_conditions(db, offer.id)
        db.execute(text("DELETE FROM quest_offer_step WHERE offer_id = :oid"), {"oid": offer.id})
    offer.giver_entity_id = giver_entity_id
    offer.contact_entity_id = contact_entity_id or None
    offer.title = title.strip()
    offer.summary = (summary or "").strip() or None
    offer.repeatable = bool(repeatable)
    offer.status = status
    offer.updated_at = datetime.now(UTC)
    db.add(offer)
    db.flush()

    write_condition(db, world_id=world_id, role="eligibility", tree=clean_eligibility, quest_offer_id=offer.id)
    for order, (step, prerequisite) in enumerate(clean_steps, start=1):
        row = QuestOfferStep(world_id=world_id, offer_id=offer.id, step_order=order,
                             objective=step.objective.strip(), cost=step.cost, domain=step.domain)
        db.add(row)
        db.flush()
        write_condition(db, world_id=world_id, role="prerequisite", tree=prerequisite, quest_offer_step_id=row.id)
    write_offer_terms(db, world_id=world_id, offer_id=offer.id, clean=clean_term_rows)
    return offer


def offer_bindings(offer: QuestOffer, character: Character) -> Bindings:
    """What an offer's roles name for `character` (P1): he acts; the giver
    and the contact are the offer's."""
    return Bindings(doer=character, giver_id=offer.giver_entity_id, contact_id=offer.contact_entity_id)


def acceptance_refusal(db: Session, offer: QuestOffer, character: Character) -> Optional[str]:
    """Why `character` cannot take `offer` now, or None (C-04): a closed
    offer, an unmet eligibility requirement, or L1 -- a non-repeatable offer
    already taken, a repeatable one still open."""
    if offer.status != "open":
        return "cette quête n'est plus proposée"
    taken = db.exec(
        select(Agenda.status).join(Quest, Quest.agenda_id == Agenda.id)
        .where(Quest.offer_id == offer.id, Quest.character_id == character.id)
    ).all()
    if taken and not offer.repeatable:
        return "quête déjà acceptée"
    if any(status in OPEN_QUEST_STATUSES for status in taken):
        return "quête déjà en cours"
    eligibility = evaluate(read_condition(db, role="eligibility", quest_offer_id=offer.id),
                           offer_bindings(offer, character), db)
    if eligibility is not None and not eligibility.met:
        unmet = [node.verdict.reason if node.verdict else (node.reason or "") for node in eligibility.leaf_nodes()
                 if not node.met]
        return "; ".join(unmet) or "conditions non remplies"
    return None


def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Quest:
    """B1/A1 (C-03): the agenda is born `paused`, never displacing the
    player's active plan; its first step is `active`. Raises `ValueError`
    with `acceptance_refusal`'s reason before any write."""
    refusal = acceptance_refusal(db, offer, character)
    if refusal is not None:
        raise ValueError(refusal)
    steps = db.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)
                    .order_by(QuestOfferStep.step_order)).all()
    if not steps:
        raise ValueError("accept_quest: the offer has no step")
    copied = [(step, read_condition(db, role="prerequisite", quest_offer_step_id=step.id)) for step in steps]

    agenda = write_agenda(db, world_id=offer.world_id, owner_entity_id=character.id, title=offer.title,
                          status="paused")
    db.flush()
    for step, prerequisite in copied:
        row = write_agenda_step(db, agenda_id=agenda.id, step_order=step.step_order, objective=step.objective,
                                status="active" if step.step_order == 1 else "pending",
                                cost=step.cost, domain=step.domain)
        db.flush()
        write_condition(db, world_id=offer.world_id, role="prerequisite", tree=prerequisite, agenda_step_id=row.id)
    quest = Quest(world_id=offer.world_id, offer_id=offer.id, character_id=character.id, agenda_id=agenda.id)
    db.add(quest)
    db.flush()
    copy_terms_to_quest(db, world_id=offer.world_id, offer_id=offer.id, quest_id=quest.id)
    return quest


def abandon_refusal(db: Session, quest: Quest) -> Optional[str]:
    """Why the quest cannot be abandoned now, or None: it is over, a day is
    resolving against it, or a step change of it awaits review (applying it
    after the abandon would move an abandoned plan)."""
    agenda = db.get(Agenda, quest.agenda_id)
    if agenda is None or agenda.status not in OPEN_QUEST_STATUSES:
        return "cette quête est terminée"
    resolving = db.exec(select(PassPlay.id).where(
        PassPlay.agenda_id == agenda.id, PassPlay.status == "resolving")).first()
    if resolving is not None:
        return "une journée est en cours de résolution sur cette quête"
    # The `routes/day.py::_guard_no_pending_agenda_step_change` query (a
    # proposal awaiting review is `status='proposed'`), restated here: that
    # guard raises an HTTP error and lives in a route module.
    step_ids = set(db.exec(select(AgendaStep.id).where(AgendaStep.agenda_id == agenda.id)).all())
    pending = db.exec(select(ProposedMutation).where(
        ProposedMutation.mutation_type == "agenda_step_change", ProposedMutation.status == "proposed",
    )).all()
    if any(isinstance(m.payload, dict) and m.payload.get("step_id") in step_ids for m in pending):
        return "une étape de cette quête attend la revue"
    return None


def abandon_quest(db: Session, *, quest: Quest) -> Agenda:
    """N1 (C-03): the agenda to `abandoned`; `ValueError` with
    `abandon_refusal`'s reason before any write."""
    refusal = abandon_refusal(db, quest)
    if refusal is not None:
        raise ValueError(refusal)
    agenda = db.get(Agenda, quest.agenda_id)
    return write_agenda_status(db, agenda=agenda, status="abandoned")
