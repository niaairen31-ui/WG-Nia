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

TICKET-0110 (BRIEF-0110-B): the checks and the application of one term are
public and take the world and the character rather than a quest --
`cost_checks` and `apply_term` -- so a service applies its terms exactly as
a settlement does (`writes/debt_sources.py`), and a settlement on credit
pays a cost in part (`amount`). `finish_settlement` is what closes a quest
either way. Nothing here changes what « déclarer accomplie » does.
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


def cost_checks(db: Session, character_id: str, terms: list, giver_id: str) -> list[tuple[str, str]]:
    """Every cost of `terms` the character cannot pay now, as `(kind, French
    reason)`: `money` and `item` for a stock too small (summed per item), and
    `other` for a fact he does not know, a skill he is not Maître in, or one
    the counterparty already holds. Rewards are never checked (C-src1)."""
    money = 0
    items: dict[str, int] = defaultdict(int)
    checks: list[tuple[str, str]] = []
    for term in terms:
        if term.direction != "cost":
            continue
        other = term.counterparty_entity_id or giver_id
        if term.currency == "money":
            money += term.amount
        elif term.currency == "item":
            items[term.item_id] += term.amount
        elif term.currency == "fact" and find_held(db, character_id, {"fact_id": term.fact_id}) is None:
            checks.append(("other", "il faut connaître le fait à transmettre"))
        elif term.currency == "skill":
            label = skill_label(db, term.skill_key)
            if held_rank(db, character_id, term.skill_key) != MAX_RANK:
                checks.append(("other", f"il faut être Maître en « {label} » pour l'enseigner"))
            elif skill_row(db, other, term.skill_key) is not None:
                checks.append(("other", f"{_name(db, other)} connaît déjà « {label} »"))
    balance = get_balance(db, character_id)
    if money > balance:
        checks.append(("money", f"il faut {money} pièce(s), vous en avez {balance}"))
    for item_id, needed in items.items():
        held = held_quantity(db, character_id, item_id)
        if needed > held:
            checks.append(("item", f"il faut {needed} × {_name(db, item_id)}, vous en avez {held}"))
    return checks


def closed_refusal(db: Session, quest: Quest) -> Optional[str]:
    """The reason a quest can no longer be settled at all, or None."""
    if quest.settled_at is not None:
        return "cette quête est déjà réglée"
    agenda = db.get(Agenda, quest.agenda_id)
    if agenda is None or agenda.status in ("failed", "abandoned"):
        return "cette quête est terminée sans succès"
    return None


def settlement_refusals(db: Session, quest: Quest) -> list[str]:
    """Why `quest` cannot be settled now (French); empty when it can."""
    closed = closed_refusal(db, quest)
    if closed is not None:
        return [closed]
    offer = db.get(QuestOffer, quest.offer_id)
    return [reason for _kind, reason in cost_checks(db, quest.character_id, quest_terms(db, quest.id),
                                                    offer.giver_entity_id)]


def _money(db: Session, world_id: str, payer: str, payee: str, amount: int, reason: str, source_type: str) -> None:
    write_ledger_entry(db, world_id=world_id, entity_id=payer, amount=-amount, counterparty_id=payee,
                       reason=reason, source_type=source_type)
    write_ledger_entry(db, world_id=world_id, entity_id=payee, amount=amount, counterparty_id=payer,
                       reason=reason, source_type=source_type)


def _items(db: Session, world_id: str, giver: str, receiver: str, item_id: str, amount: int, cost: bool) -> None:
    taken = amount if cost else min(amount, held_quantity(db, giver, item_id))
    if taken:
        write_holding(db, world_id=world_id, item_id=item_id, holder_entity_id=giver, delta=-taken,
                      changed_by=CHANGED_BY)
    write_holding(db, world_id=world_id, item_id=item_id, holder_entity_id=receiver, delta=amount,
                  changed_by=CHANGED_BY)


def _fact(db: Session, receiver: str, fact_id: str, level: Optional[str]) -> None:
    if find_held(db, receiver, {"fact_id": fact_id}) is not None:
        return
    write_knowledge(db, entity_id=receiver, fact_id=fact_id, level=level or DEFAULT_FACT_LEVEL,
                    source="quête", changed_by=CHANGED_BY)


def _skill_reward(db: Session, world_id: str, character_id: str, teacher: str, skill_key: str) -> None:
    row = skill_row(db, character_id, skill_key)
    if row is None and skill_key not in BASE_SKILL_DOMAINS:
        master = teacher if held_rank(db, teacher, skill_key) == MAX_RANK else None
        write_skill_row(db, character_id=character_id, rank=LEARNED_RANK, skill_definition_id=skill_key,
                        taught_by_id=master)
        return
    if row is None:
        row = write_skill_row(db, character_id=character_id, rank=held_rank(db, character_id, skill_key),
                              domain=skill_key)
        db.flush()
    points = skill_reward_points(db, world_id, row)
    if points is not None:
        write_skill_progress(db, skill_id=row.id, world_id=world_id, points=points, changed_by=CHANGED_BY)


def apply_term(db: Session, *, world_id: str, character_id: str, term, giver_id: str, reason: str,
               source_type: str = "quest", amount: Optional[int] = None) -> None:
    """Apply one term between the character and its counterparty (else the
    giver), as the D table says. `amount` replaces a money or item term's
    own amount (a cost paid in part, on credit); `source_type` names the
    ledger lines' origin."""
    character, other = character_id, term.counterparty_entity_id or giver_id
    cost = term.direction == "cost"
    count = term.amount if amount is None else amount
    if term.currency == "money":
        _money(db, world_id, character if cost else other, other if cost else character, count, reason, source_type)
    elif term.currency == "item":
        _items(db, world_id, character if cost else other, other if cost else character, term.item_id, count, cost)
    elif term.currency == "relation":
        write_relation(db, mode="delta", world_id=world_id, entity_a_id=other, entity_b_id=character,
                       type="other", value=-term.amount if cost else term.amount, changed_by=CHANGED_BY)
    elif term.currency == "fact":
        _fact(db, other if cost else character, term.fact_id, None if cost else term.level)
    elif cost:
        write_skill_row(db, character_id=other, rank=LEARNED_RANK, skill_definition_id=term.skill_key,
                        taught_by_id=character)
    else:
        _skill_reward(db, world_id, character_id, other, term.skill_key)
    db.flush()


def in_order(terms: list) -> list:
    """Every cost, then every reward, each in term order."""
    return [t for t in terms if t.direction == "cost"] + [t for t in terms if t.direction == "reward"]


def finish_settlement(db: Session, quest: Quest) -> Quest:
    """The agenda `completed` when it is not, and `settled_at`, once."""
    agenda = db.get(Agenda, quest.agenda_id)
    if agenda.status != "completed":
        write_agenda_status(db, agenda=agenda, status="completed")
    quest.settled_at = datetime.now(UTC)
    db.add(quest)
    return quest


def settle_quest(db: Session, *, quest: Quest) -> Quest:
    """D1 (C-05): `ValueError` with the refusals joined, before any write;
    otherwise every cost, then every reward, the agenda `completed`, and
    `settled_at`. Never commits."""
    refusals = settlement_refusals(db, quest)
    if refusals:
        raise ValueError("; ".join(refusals))
    offer = db.get(QuestOffer, quest.offer_id)
    reason = f"Quête « {db.get(Agenda, quest.agenda_id).title} »"
    for term in in_order(quest_terms(db, quest.id)):
        apply_term(db, world_id=quest.world_id, character_id=quest.character_id, term=term,
                   giver_id=offer.giver_entity_id, reason=reason)
    return finish_settlement(db, quest)
