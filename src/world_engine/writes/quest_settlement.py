"""« Déclarer accomplie »: settling a quest (TICKET-0109, BRIEF-0109-C, D1,
contract C-05).

`settlement_refusals` says why a quest cannot be settled now; `settle_quest`
applies, in one transaction the caller commits, every cost then every
reward of the quest's own terms (B1), writes its agenda `completed` when it
is not already, and sets `quest.settled_at`. The code checks what it can:
a cost the character cannot pay refuses the whole settlement (D1); a
reward is always given, even when the counterparty lacks it (C-src1: its
purse may go below 0; it gives the items it holds, the rest is new).

Per currency (the series' D table):
- money: two ledger lines (the payer -n, the payee +n), `source_type`
  `quest`.
- item: the giver's holding -n, the receiver's +n (`write_holding`).
- relation: what the counterparty feels toward the character, -n (cost) or
  +n (reward) -- `write_relation(mode="delta")`, type `other` on a new row.
- fact: the receiver learns it (`knows`, or the reward's level); a holder
  who already knows it is left as is -- a level never falls.
- skill, cost: the character, at Maître (C-teach1), teaches the
  counterparty, who gains the row at Inexpérimenté, `taught_by` him.
- skill, reward (C-skill1): held -> 10 % of the points its rank needs to
  rise, at least 1 (a rise resets the points to 0: the surplus is not
  carried, `write_skill_progress`); at Maître, nothing; not held -> the row
  at Inexpérimenté, taught by the counterparty when he is at Maître in it.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from ..fact_refs import find_held
from ..holdings import held_quantity
from ..ledger import get_balance
from ..models import BASE_SKILL_DOMAINS, Agenda, Entity, Quest, QuestOffer, Skill
from ..skill_access import held_rank, skill_label
from ..skill_ranks import MAX_RANK, skill_points_to_next
from .characters import write_ledger_entry, write_skill_progress, write_skill_row
from .goals_agendas import write_agenda_status
from .items import write_holding
from .knowledge import write_knowledge
from .quest_terms import quest_terms
from .relations import write_relation

# The share of the points a rank needs that a skill reward gives (C-skill1).
SKILL_REWARD_SHARE = 0.10
# The rank a skill learned or taught starts at (Inexpérimenté, 0107 C1).
LEARNED_RANK = 0
# The knowledge level a fact gives when the term names none.
DEFAULT_FACT_LEVEL = "knows"
CHANGED_BY = "quest_settlement"


def _name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else "?"


def skill_row(db: Session, character_id: str, skill_key: str) -> Optional[Skill]:
    if skill_key in BASE_SKILL_DOMAINS:
        return db.exec(select(Skill).where(Skill.character_id == character_id, Skill.domain == skill_key,
                                           Skill.skill_definition_id.is_(None))).first()
    return db.exec(select(Skill).where(Skill.character_id == character_id,
                                       Skill.skill_definition_id == skill_key)).first()


def skill_reward_points(db: Session, world_id: str, row: Skill) -> Optional[int]:
    """C-skill1: the points a skill reward gives this row, or None at Maître."""
    needed = skill_points_to_next(db, world_id=world_id, rank=row.rank, skill_definition_id=row.skill_definition_id)
    if row.rank >= MAX_RANK or needed is None:
        return None
    return max(1, math.ceil(needed * SKILL_REWARD_SHARE))


def _cost_refusals(db: Session, quest: Quest, giver_id: str) -> list[str]:
    character = quest.character_id
    money = 0
    items: dict[str, int] = defaultdict(int)
    refusals: list[str] = []
    for term in quest_terms(db, quest.id):
        if term.direction != "cost":
            continue
        other = term.counterparty_entity_id or giver_id
        if term.currency == "money":
            money += term.amount
        elif term.currency == "item":
            items[term.item_id] += term.amount
        elif term.currency == "fact" and find_held(db, character, {"fact_id": term.fact_id}) is None:
            refusals.append("il faut connaître le fait à transmettre")
        elif term.currency == "skill":
            label = skill_label(db, term.skill_key)
            if held_rank(db, character, term.skill_key) != MAX_RANK:
                refusals.append(f"il faut être Maître en « {label} » pour l'enseigner")
            elif skill_row(db, other, term.skill_key) is not None:
                refusals.append(f"{_name(db, other)} connaît déjà « {label} »")
    balance = get_balance(db, character)
    if money > balance:
        refusals.append(f"il faut {money} pièce(s), vous en avez {balance}")
    for item_id, needed in items.items():
        held = held_quantity(db, character, item_id)
        if needed > held:
            refusals.append(f"il faut {needed} × {_name(db, item_id)}, vous en avez {held}")
    return refusals


def settlement_refusals(db: Session, quest: Quest) -> list[str]:
    """Why `quest` cannot be settled now (French); empty when it can."""
    if quest.settled_at is not None:
        return ["cette quête est déjà réglée"]
    agenda = db.get(Agenda, quest.agenda_id)
    if agenda is None or agenda.status in ("failed", "abandoned"):
        return ["cette quête est terminée sans succès"]
    offer = db.get(QuestOffer, quest.offer_id)
    return _cost_refusals(db, quest, offer.giver_entity_id)


def _money(db: Session, quest: Quest, payer: str, payee: str, amount: int, reason: str) -> None:
    write_ledger_entry(db, world_id=quest.world_id, entity_id=payer, amount=-amount, counterparty_id=payee,
                       reason=reason, source_type="quest")
    write_ledger_entry(db, world_id=quest.world_id, entity_id=payee, amount=amount, counterparty_id=payer,
                       reason=reason, source_type="quest")


def _items(db: Session, quest: Quest, giver: str, receiver: str, item_id: str, amount: int, cost: bool) -> None:
    taken = amount if cost else min(amount, held_quantity(db, giver, item_id))
    if taken:
        write_holding(db, world_id=quest.world_id, item_id=item_id, holder_entity_id=giver, delta=-taken,
                      changed_by=CHANGED_BY)
    write_holding(db, world_id=quest.world_id, item_id=item_id, holder_entity_id=receiver, delta=amount,
                  changed_by=CHANGED_BY)


def _fact(db: Session, receiver: str, fact_id: str, level: Optional[str]) -> None:
    if find_held(db, receiver, {"fact_id": fact_id}) is not None:
        return
    write_knowledge(db, entity_id=receiver, fact_id=fact_id, level=level or DEFAULT_FACT_LEVEL,
                    source="quête", changed_by=CHANGED_BY)


def _skill_reward(db: Session, quest: Quest, teacher: str, skill_key: str) -> None:
    row = skill_row(db, quest.character_id, skill_key)
    if row is None and skill_key not in BASE_SKILL_DOMAINS:
        master = teacher if held_rank(db, teacher, skill_key) == MAX_RANK else None
        write_skill_row(db, character_id=quest.character_id, rank=LEARNED_RANK, skill_definition_id=skill_key,
                        taught_by_id=master)
        return
    if row is None:
        row = write_skill_row(db, character_id=quest.character_id, rank=held_rank(db, quest.character_id, skill_key),
                              domain=skill_key)
        db.flush()
    points = skill_reward_points(db, quest.world_id, row)
    if points is not None:
        write_skill_progress(db, skill_id=row.id, world_id=quest.world_id, points=points, changed_by=CHANGED_BY)


def _apply_term(db: Session, quest: Quest, term, giver_id: str, reason: str) -> None:
    character, other = quest.character_id, term.counterparty_entity_id or giver_id
    cost = term.direction == "cost"
    if term.currency == "money":
        _money(db, quest, character if cost else other, other if cost else character, term.amount, reason)
    elif term.currency == "item":
        _items(db, quest, character if cost else other, other if cost else character, term.item_id, term.amount, cost)
    elif term.currency == "relation":
        write_relation(db, mode="delta", world_id=quest.world_id, entity_a_id=other, entity_b_id=character,
                       type="other", value=-term.amount if cost else term.amount, changed_by=CHANGED_BY)
    elif term.currency == "fact":
        _fact(db, other if cost else character, term.fact_id, None if cost else term.level)
    elif cost:
        write_skill_row(db, character_id=other, rank=LEARNED_RANK, skill_definition_id=term.skill_key,
                        taught_by_id=character)
    else:
        _skill_reward(db, quest, other, term.skill_key)
    db.flush()


def settle_quest(db: Session, *, quest: Quest) -> Quest:
    """D1 (C-05): `ValueError` with the refusals joined, before any write;
    otherwise every cost, then every reward, the agenda `completed`, and
    `settled_at`. Never commits."""
    refusals = settlement_refusals(db, quest)
    if refusals:
        raise ValueError("; ".join(refusals))
    offer = db.get(QuestOffer, quest.offer_id)
    agenda = db.get(Agenda, quest.agenda_id)
    reason = f"Quête « {agenda.title} »"
    terms = quest_terms(db, quest.id)
    for term in [t for t in terms if t.direction == "cost"] + [t for t in terms if t.direction == "reward"]:
        _apply_term(db, quest, term, offer.giver_entity_id, reason)
    if agenda.status != "completed":
        write_agenda_status(db, agenda=agenda, status="completed")
    quest.settled_at = datetime.now(UTC)
    db.add(quest)
    return quest
