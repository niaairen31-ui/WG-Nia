"""Debts: what the two surfaces read (TICKET-0110, BRIEF-0110-B, contract
C-06). Reads only: this module never writes.

`debt_dict` is one debt as both surfaces show it: the parties by name, its
origin (a quest by its title, never an agenda id), its motive, its terms
each with a French line, its indicative value in the world's unit -- a
display, never converted (C1 of the series) -- and its state.
`world_debts` is every debt of a world, for Création › Dettes;
`player_debts` is what the player owes and what is owed to him, for
Journée › Dettes, each open one with the reasons it cannot be repaid now.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Agenda, Character, Debt, Entity, Fact, Quest
from .prose_render import fact_text
from .quest_value import term_value, world_rates
from .skill_access import skill_label
from .writes.debts import debt_refusals, debt_terms

DEBT_STATUS_LABELS: dict[str, str] = {"open": "due", "settled": "réglée", "forgiven": "remise"}
DEBT_ORIGIN_LABELS: dict[str, str] = {"service": "service", "quest": "quête", "creator": "création"}


def _name(db: Session, entity_id: Optional[str]) -> Optional[str]:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else None


def debt_term_line(db: Session, term) -> str:
    """One owed term in French: « 20 pièce(s) », « 2 × Fourrure », « le savoir
    « … » », « l'enseignement de « Herboristerie » »."""
    if term.currency == "money":
        return f"{term.amount} pièce(s)"
    if term.currency == "item":
        return f"{term.amount} × {_name(db, term.item_id) or '?'}"
    if term.currency == "fact":
        fact = db.get(Fact, term.fact_id) if term.fact_id else None
        return f"le savoir « {fact_text(db, fact) if fact is not None else '?'} »"
    return f"l'enseignement de « {skill_label(db, term.skill_key)} »"


def _origin_label(db: Session, debt: Debt) -> str:
    if debt.origin != "quest":
        return DEBT_ORIGIN_LABELS[debt.origin]
    quest = db.get(Quest, debt.origin_quest_id)
    agenda = db.get(Agenda, quest.agenda_id) if quest is not None else None
    return f"quête « {agenda.title} »" if agenda is not None else "quête"


def debt_dict(debt: Debt, db: Session) -> dict:
    """C-06: one debt, every key always present."""
    terms = debt_terms(db, debt.id)
    rates = world_rates(db, debt.world_id)
    return {
        "id": debt.id,
        "debtor_id": debt.debtor_entity_id, "debtor_name": _name(db, debt.debtor_entity_id),
        "creditor_id": debt.creditor_entity_id, "creditor_name": _name(db, debt.creditor_entity_id),
        "contact_id": debt.contact_entity_id, "contact_name": _name(db, debt.contact_entity_id),
        "origin": debt.origin, "origin_label": _origin_label(db, debt),
        "reason": debt.reason, "is_secret": debt.is_secret,
        "status": debt.status, "status_label": DEBT_STATUS_LABELS[debt.status],
        "created_at": debt.created_at.isoformat() if debt.created_at else None,
        "closed_at": debt.closed_at.isoformat() if debt.closed_at else None,
        "closed_note": debt.closed_note,
        "terms": [{"currency": t.currency, "item_id": t.item_id, "fact_id": t.fact_id, "skill_key": t.skill_key,
                   "amount": t.amount, "line": debt_term_line(db, t)} for t in terms],
        "value": sum(term_value(db, t, rates) for t in terms),
    }


def _ordered(debts: list[Debt]) -> list[Debt]:
    """Open first, then the most recent."""
    return sorted(debts, key=lambda d: (d.status != "open", -(d.created_at.timestamp() if d.created_at else 0), d.id))


def world_debts(world_id: str, db: Session) -> list[dict]:
    """GET /api/debts: every debt of the world."""
    return [debt_dict(d, db) for d in _ordered(list(db.exec(select(Debt).where(Debt.world_id == world_id)).all()))]


def _with_refusals(debt: Debt, db: Session) -> dict:
    view = debt_dict(debt, db)
    view["refusals"] = debt_refusals(db, debt) if debt.status == "open" else []
    view["repayable"] = debt.status == "open" and not view["refusals"]
    return view


def player_debts(character: Character, db: Session) -> dict:
    """GET /api/journee/debts: `owes` (he is the debtor) and `owed` (he is
    the creditor), each open one with why it cannot be repaid now."""
    owes = db.exec(select(Debt).where(Debt.debtor_entity_id == character.id)).all()
    owed = db.exec(select(Debt).where(Debt.creditor_entity_id == character.id)).all()
    return {"owes": [_with_refusals(d, db) for d in _ordered(list(owes))],
            "owed": [_with_refusals(d, db) for d in _ordered(list(owed))]}
