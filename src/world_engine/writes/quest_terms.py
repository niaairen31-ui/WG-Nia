"""Quest terms: validation and writing (TICKET-0109, BRIEF-0109-B, B1,
contract C-02).

A term is a cost (what the character gives to settle the quest) or a reward
(what he receives), in one of five currencies. `clean_term` validates one
and returns the exact columns a term row takes; `write_offer_terms` replaces
an offer's terms whole (with its steps, `write_quest_offer`);
`copy_terms_to_quest` gives an accepted quest its own copy (B1);
`upsert_quest_economy` writes a world's rates (E1).

The counterparty is the term's own entity, else the offer's giver; for a
relation, a fact or a skill it must be a character (a faction feels
nothing, knows nothing, learns nothing). A skill COST is teaching it
(C-teach1), so it must be a skill definition: every character already holds
the four base domains. None of these functions commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from ..models import (
    BASE_SKILL_DOMAINS,
    QUEST_TERM_CURRENCIES,
    QUEST_TERM_DIRECTIONS,
    Entity,
    Fact,
    Item,
    QuestEconomy,
    QuestOfferTerm,
    QuestTerm,
    SkillDefinition,
)
from ..quest_value import DEFAULT_RATES
from .knowledge import KNOWLEDGE_LEVELS

# The currencies whose counterparty must be a character.
PERSONAL_CURRENCIES: tuple[str, ...] = ("relation", "fact", "skill")
# The currencies counted by `amount`.
COUNTED_CURRENCIES: tuple[str, ...] = ("money", "item", "relation")
# The largest relation term: an intensity moves within 1-100.
MAX_RELATION_AMOUNT = 99
# The knowledge levels a fact reward may give (never `unaware`).
FACT_REWARD_LEVELS: tuple[str, ...] = tuple(sorted(KNOWLEDGE_LEVELS - {"unaware"}))
# The columns of a term row, beyond its owner and order.
TERM_COLUMNS: tuple[str, ...] = (
    "direction", "currency", "counterparty_entity_id", "item_id", "fact_id", "skill_key", "amount", "level",
)
# The economy columns a world may set (E1); the two debt settings since
# v2.19 (TICKET-0110).
ECONOMY_COLUMNS: tuple[str, ...] = (
    "rate_money", "rate_relation", "rate_fact", "rate_skill", "band_low_pct", "band_high_pct",
    "debt_fact_relation", "debt_skill_relation",
)


@dataclass(frozen=True)
class TermSpec:
    direction: str
    currency: str
    counterparty_entity_id: Optional[str] = None
    item_id: Optional[str] = None
    fact_id: Optional[str] = None
    skill_key: Optional[str] = None
    amount: Optional[int] = None
    level: Optional[str] = None


def _entity_of(db: Session, world_id: str, entity_id: Optional[str], types: tuple[str, ...]) -> Optional[Entity]:
    entity = db.get(Entity, entity_id) if entity_id else None
    if entity is None or entity.world_id != world_id or entity.type not in types or entity.status != "active":
        return None
    return entity


def _clean_target(db: Session, world_id: str, where: str, term: TermSpec) -> dict:
    """The target columns of `term`'s currency, the others None."""
    target = {"item_id": None, "fact_id": None, "skill_key": None, "level": None}
    if term.currency == "item":
        if _entity_of(db, world_id, term.item_id, ("item",)) is None or db.get(Item, term.item_id) is None:
            raise ValueError(f"{where}: {term.item_id!r} is not an item of this world")
        target["item_id"] = term.item_id
    elif term.currency == "fact":
        fact = db.get(Fact, term.fact_id) if term.fact_id else None
        if fact is None or fact.world_id != world_id:
            raise ValueError(f"{where}: {term.fact_id!r} is not a fact of this world")
        target["fact_id"] = term.fact_id
        if term.direction == "reward" and term.level not in (None, *FACT_REWARD_LEVELS):
            raise ValueError(f"{where}: a fact reward's level is one of {FACT_REWARD_LEVELS}")
        target["level"] = term.level if term.direction == "reward" else None
    elif term.currency == "skill":
        definition = db.get(SkillDefinition, term.skill_key) if term.skill_key else None
        is_definition = definition is not None and definition.world_id == world_id
        if term.direction == "cost" and not is_definition:
            raise ValueError(f"{where}: teaching (a skill cost) needs a skill definition of this world")
        if not is_definition and term.skill_key not in BASE_SKILL_DOMAINS:
            raise ValueError(f"{where}: {term.skill_key!r} is not a skill of this world")
        target["skill_key"] = term.skill_key
    return target


def _clean_amount(where: str, term: TermSpec) -> Optional[int]:
    if term.currency not in COUNTED_CURRENCIES:
        return None
    amount = term.amount
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
        raise ValueError(f"{where}: a {term.currency} term needs an amount of at least 1")
    if term.currency == "relation" and amount > MAX_RELATION_AMOUNT:
        raise ValueError(f"{where}: a relation term moves at most {MAX_RELATION_AMOUNT} points")
    return amount


def clean_term(db: Session, world_id: str, giver_entity_id: str, index: int, term: TermSpec) -> dict:
    """Validate one term against the offer's giver; the row's columns, or
    `ValueError` (C-02's refusals)."""
    where = f"term {index + 1}"
    if term.direction not in QUEST_TERM_DIRECTIONS:
        raise ValueError(f"{where}: direction must be one of {QUEST_TERM_DIRECTIONS}")
    if term.currency not in QUEST_TERM_CURRENCIES:
        raise ValueError(f"{where}: currency must be one of {QUEST_TERM_CURRENCIES}")
    counterparty = term.counterparty_entity_id or None
    if counterparty is not None and _entity_of(db, world_id, counterparty, ("character", "faction")) is None:
        raise ValueError(f"{where}: the counterparty is not an active character or faction of this world")
    effective = counterparty or giver_entity_id
    if term.currency in PERSONAL_CURRENCIES and _entity_of(db, world_id, effective, ("character",)) is None:
        raise ValueError(f"{where}: a {term.currency} term needs a character as counterparty -- name one")
    return {"direction": term.direction, "currency": term.currency, "counterparty_entity_id": counterparty,
            **_clean_target(db, world_id, where, term), "amount": _clean_amount(where, term)}


def clean_terms(db: Session, world_id: str, giver_entity_id: str, terms: list[TermSpec]) -> list[dict]:
    """Every term validated before any write (all or nothing)."""
    return [clean_term(db, world_id, giver_entity_id, i, term) for i, term in enumerate(terms)]


def write_offer_terms(db: Session, *, world_id: str, offer_id: str, clean: list[dict]) -> None:
    """Replace an offer's terms whole (full-replace, the offer's steps' shape)."""
    db.execute(text("DELETE FROM quest_offer_term WHERE offer_id = :oid"), {"oid": offer_id})
    for order, columns in enumerate(clean, start=1):
        db.add(QuestOfferTerm(world_id=world_id, offer_id=offer_id, term_order=order, **columns))


def offer_terms(db: Session, offer_id: str) -> list[QuestOfferTerm]:
    return list(db.exec(select(QuestOfferTerm).where(QuestOfferTerm.offer_id == offer_id)
                        .order_by(QuestOfferTerm.term_order)).all())


def quest_terms(db: Session, quest_id: str) -> list[QuestTerm]:
    return list(db.exec(select(QuestTerm).where(QuestTerm.quest_id == quest_id)
                        .order_by(QuestTerm.term_order)).all())


def copy_terms_to_quest(db: Session, *, world_id: str, offer_id: str, quest_id: str) -> None:
    """B1: the accepted quest's own copy, never touched again."""
    for term in offer_terms(db, offer_id):
        db.add(QuestTerm(world_id=world_id, quest_id=quest_id, term_order=term.term_order,
                         **{c: getattr(term, c) for c in TERM_COLUMNS}))


def upsert_quest_economy(db: Session, *, world_id: str, values: dict) -> QuestEconomy:
    """E1: set a world's rates; a None value returns that rate to the code's
    default. Refuses an unknown column, a negative value, or a band whose low
    end is above its high end, before any write."""
    unknown = set(values) - set(ECONOMY_COLUMNS)
    if unknown:
        raise ValueError(f"upsert_quest_economy: unknown {sorted(unknown)}")
    for name, value in values.items():
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise ValueError(f"upsert_quest_economy: {name} must be a whole number >= 0 or empty")
    row = db.exec(select(QuestEconomy).where(QuestEconomy.world_id == world_id)).first()
    merged = {name: (values[name] if name in values else getattr(row, name, None)) for name in ECONOMY_COLUMNS}
    low = merged["band_low_pct"] if merged["band_low_pct"] is not None else DEFAULT_RATES["band_low_pct"]
    high = merged["band_high_pct"] if merged["band_high_pct"] is not None else DEFAULT_RATES["band_high_pct"]
    if low > high:
        raise ValueError(f"upsert_quest_economy: the band's low end {low} % is above its high end {high} %")
    if row is None:
        row = QuestEconomy(world_id=world_id)
    for name, value in values.items():
        setattr(row, name, value)
    row.updated_at = datetime.now(UTC)
    db.add(row)
    return row
