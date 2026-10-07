"""What « déclarer accomplie » shows before Nia decides (TICKET-0109,
BRIEF-0109-C, G1, contract C-06). Reads only.

Measured context, never a verdict: the quest's steps (status and recorded
outcome, what the active one still needs), its terms with what each will do,
their indicative value, the days that advanced it (the declared action, the
text the day chain read, each step's band), how many of its step changes
still await review, and why it cannot be settled now, if it cannot. No
model is called (G1). No agenda or step id appears: the quest is named by
its `quest_id`.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .models import Agenda, AgendaStep, Batch, Character, DayRewrite, PassPlay, ProposedMutation, Quest, QuestOffer
from .quest_reads import QUEST_STATE_LABELS, _steps_view
from .quest_value import offer_value, value_dict
from .quest_wording import term_line
from .skill_access import skill_label
from .writes.pipeline import read_latest_resolution
from .writes.quest_settlement import skill_row, settlement_refusals, skill_reward_points
from .writes.quest_terms import quest_terms


def _skill_note(db: Session, quest: Quest, term) -> str:
    label = skill_label(db, term.skill_key)
    row = skill_row(db, quest.character_id, term.skill_key)
    if row is None:
        return f"apprend « {label} » (Inexpérimenté)"
    points = skill_reward_points(db, quest.world_id, row)
    return f"+{points} point(s) en « {label} »" if points is not None else f"déjà Maître en « {label} » : rien"


def _terms(db: Session, quest: Quest, giver_id: str, terms: list) -> list[dict]:
    view = []
    for term in terms:
        note = _skill_note(db, quest, term) if term.currency == "skill" and term.direction == "reward" else None
        view.append({"direction": term.direction, "line": term_line(db, term, giver_id), "note": note})
    return view


def _days(db: Session, agenda: Agenda) -> list[dict]:
    rows = db.exec(select(PassPlay, Batch).join(Batch, Batch.id == PassPlay.batch_id)
                   .where(PassPlay.agenda_id == agenda.id).order_by(Batch.day_number)).all()
    days = []
    for pass_play, batch in rows:
        rewrite = db.exec(select(DayRewrite).where(DayRewrite.pass_play_id == pass_play.id)
                          .order_by(DayRewrite.generation.desc())).first()
        resolution = read_latest_resolution(pass_play) or {}
        steps = (resolution.get("fact_sheet") or {}).get("steps") or []
        days.append({"day_number": batch.day_number, "declared_action": pass_play.declared_action,
                     "rewritten": rewrite.rendered_text if rewrite is not None else None,
                     "steps": [{"objective": s.get("objective"), "band": s.get("band")} for s in steps]})
    return days


def _pending_reviews(db: Session, agenda: Agenda) -> int:
    step_ids = set(db.exec(select(AgendaStep.id).where(AgendaStep.agenda_id == agenda.id)).all())
    pending = db.exec(select(ProposedMutation).where(
        ProposedMutation.mutation_type == "agenda_step_change", ProposedMutation.status == "proposed")).all()
    return sum(1 for m in pending if isinstance(m.payload, dict) and m.payload.get("step_id") in step_ids)


def settlement_context(db: Session, quest: Quest) -> dict:
    """GET /api/quests/{quest_id}/settlement (C-06)."""
    agenda = db.get(Agenda, quest.agenda_id)
    offer = db.get(QuestOffer, quest.offer_id)
    character = db.get(Character, quest.character_id)
    terms = quest_terms(db, quest.id)
    refusals = settlement_refusals(db, quest)
    return {
        "quest_id": quest.id, "title": agenda.title, "state": QUEST_STATE_LABELS[agenda.status],
        "settled": quest.settled_at is not None,
        "steps": _steps_view(agenda, character, db),
        "terms": _terms(db, quest, offer.giver_entity_id, terms),
        "value": value_dict(offer_value(db, quest.world_id, terms)),
        "days": _days(db, agenda),
        "pending_reviews": _pending_reviews(db, agenda),
        "refusals": refusals, "can_settle": not refusals,
    }
