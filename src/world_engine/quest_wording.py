"""How a quest term reads, in French (TICKET-0109, BRIEF-0109-B, C-04).
Reads only.

One line per term, from the character's side: « Donner 10 × Fourrure de
loup à Garde », « Recevoir 30 pièces de Garde », « La relation de Garde
envers vous monte de 5 », « Apprendre « Le passage secret » de Garde »,
« Enseigner « Herboristerie » à Garde », « Passer au rang « Expert » en
« Forge » (épreuve) ». The counterparty is the term's own entity, else the
offer's giver.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from .models import Entity, Fact
from .prose_render import fact_text
from .skill_access import skill_label
from .skill_ranks import world_ladder


def counterparty_id(term, giver_entity_id: str) -> str:
    return term.counterparty_entity_id or giver_entity_id


def _name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else "?"


def _rank_line(db: Session, term) -> str:
    """A rank reward (TICKET-0116, C-05): the skill and the rank it gives."""
    world_id, rank = getattr(term, "world_id", None), term.amount
    ranked = world_id and isinstance(rank, int) and not isinstance(rank, bool) and 1 <= rank <= 5
    label = world_ladder(db, world_id)[rank].label if ranked else str(rank)
    return f"Passer au rang « {label} » en « {skill_label(db, term.skill_key)} » (épreuve)"


def term_line(db: Session, term, giver_entity_id: str) -> str:
    """The French line of one term (an offer's or a quest's)."""
    who = _name(db, counterparty_id(term, giver_entity_id))
    cost = term.direction == "cost"
    if term.currency == "money":
        return f"Verser {term.amount} pièce(s) à {who}" if cost else f"Recevoir {term.amount} pièce(s) de {who}"
    if term.currency == "item":
        item = _name(db, term.item_id)
        return f"Donner {term.amount} × {item} à {who}" if cost else f"Recevoir {term.amount} × {item} de {who}"
    if term.currency == "relation":
        way = "baisse" if cost else "monte"
        return f"La relation de {who} envers vous {way} de {term.amount}"
    if term.currency == "fact":
        fact = db.get(Fact, term.fact_id) if term.fact_id else None
        text = fact_text(db, fact) if fact is not None else "?"
        return f"Transmettre « {text} » à {who}" if cost else f"Apprendre « {text} » de {who}"
    if term.currency == "rank":
        return _rank_line(db, term)
    label = skill_label(db, term.skill_key)
    return f"Enseigner « {label} » à {who}" if cost else f"Progresser en « {label} » (enseigné par {who})"


def term_dict(db: Session, term, giver_entity_id: str) -> dict:
    """The editor's view of one term: its columns and its line."""
    return {
        "direction": term.direction, "currency": term.currency,
        "counterparty_entity_id": term.counterparty_entity_id, "item_id": term.item_id,
        "fact_id": term.fact_id, "skill_key": term.skill_key, "amount": term.amount, "level": term.level,
        "line": term_line(db, term, giver_entity_id),
    }
