"""Where a debt comes from besides the creator's hand (TICKET-0110,
BRIEF-0110-B, S2 and A2, contract C-05).

- `request_service(...)` (S2): a character helps the player now. What he
  does is a list of quest terms -- rewards the player receives, costs he
  pays at once (a fall of regard, typically: E stays available) -- applied
  exactly as a quest's settlement applies them (`apply_term`), the ledger
  lines marked `service`. What the player will owe is a debt toward that
  character, or toward his faction when he acts for it (X1: he is then its
  contact). Every check -- the terms, the costs he must pay now, the debt
  -- passes before the first write.
- `credit_plan(...)` / `settle_quest_on_credit(...)` (A2): « régler à
  crédit ». When the only reasons a quest cannot be settled are coins or
  items the player lacks, he pays what he has -- money in term order from
  a balance above 0, each item from what he holds -- and the rest becomes
  one debt per creditor (the term's counterparty, else the giver), origin
  `quest`, its motive the quest's title. A faction creditor's contact is
  the offer's contact when the faction is the giver, else the one Nia
  names (`contacts`). Everything else is the settlement: every reward
  given, the agenda completed, `settled_at` set. A refusal of another kind
  (a fact, a skill) still refuses.

None of these functions commits.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session

from ..holdings import held_quantity
from ..ledger import get_balance
from ..models import Agenda, Character, Debt, Entity, Quest, QuestOffer
from .debts import DebtTermSpec, PreparedDebt, is_active_member, prepare_debt, write_debt
from .quest_settlement import apply_term, closed_refusal, cost_checks, finish_settlement, in_order
from .quest_terms import TermSpec, clean_terms, quest_terms

SERVICE_LEDGER_SOURCE = "service"
CHANGED_BY_SERVICE = "service"
CHANGED_BY_CREDIT = "quest_credit"


def request_service(
    db: Session, *, character: Character, provider_id: str, on_behalf_of_id: Optional[str],
    terms: list[TermSpec], owed: list[DebtTermSpec], reason: Optional[str], is_secret: bool,
) -> Debt:
    """S2 (C-05): `ValueError` before any write; else the service's terms
    applied (costs, then rewards) and the debt written. Returns the debt."""
    world_id = character.world_id
    provider = db.get(Entity, provider_id) if provider_id else None
    if (provider is None or provider.world_id != world_id or provider.type != "character"
            or provider.status != "active" or provider.id == character.id):
        raise ValueError("request_service: the provider is another active character of this world")
    creditor, contact = provider.id, None
    if on_behalf_of_id:
        if not is_active_member(db, provider.id, on_behalf_of_id):
            raise ValueError("request_service: the provider is not an active member of that faction")
        creditor, contact = on_behalf_of_id, provider.id
    rows = [TermSpec(**columns) for columns in clean_terms(db, world_id, provider.id, terms)]
    unpaid = [reason_ for _kind, reason_ in cost_checks(db, character.id, rows, provider.id)]
    if unpaid:
        raise ValueError("; ".join(unpaid))
    prepared = prepare_debt(db, world_id=world_id, debtor_id=character.id, creditor_id=creditor, contact_id=contact,
                            origin="service", reason=reason, is_secret=is_secret, terms=owed)
    label = f"Service de {provider.name}"
    for term in in_order(rows):
        apply_term(db, world_id=world_id, character_id=character.id, term=term, giver_id=provider.id, reason=label,
                   source_type=SERVICE_LEDGER_SOURCE)
    return write_debt(db, prepared, changed_by=CHANGED_BY_SERVICE)


@dataclass
class CreditPlan:
    refusals: list[str] = field(default_factory=list)
    paid: dict[str, int] = field(default_factory=dict)             # quest_term.id -> paid now
    owed: dict[str, list[DebtTermSpec]] = field(default_factory=dict)  # creditor id -> shortfall


def credit_plan(db: Session, quest: Quest) -> CreditPlan:
    """What « régler à crédit » would pay and owe (case table b-4)."""
    plan = CreditPlan()
    closed = closed_refusal(db, quest)
    if closed is not None:
        plan.refusals.append(closed)
        return plan
    offer = db.get(QuestOffer, quest.offer_id)
    terms = quest_terms(db, quest.id)
    checks = cost_checks(db, quest.character_id, terms, offer.giver_entity_id)
    plan.refusals = [reason for kind, reason in checks if kind == "other"]
    if plan.refusals:
        return plan
    money = max(0, get_balance(db, quest.character_id))
    stock: dict[str, int] = defaultdict(int)
    owed: dict[str, list[DebtTermSpec]] = defaultdict(list)
    for term in terms:
        if term.direction != "cost" or term.currency not in ("money", "item"):
            continue
        if term.currency == "money":
            pay = min(term.amount, money)
            money -= pay
        else:
            if term.item_id not in stock:
                stock[term.item_id] = held_quantity(db, quest.character_id, term.item_id)
            pay = min(term.amount, stock[term.item_id])
            stock[term.item_id] -= pay
        plan.paid[term.id] = pay
        if pay < term.amount:
            owed[term.counterparty_entity_id or offer.giver_entity_id].append(
                DebtTermSpec(currency=term.currency, item_id=term.item_id, amount=term.amount - pay))
    plan.owed = dict(owed)
    if not plan.owed:
        plan.refusals.append("rien à régler à crédit : la quête peut être déclarée accomplie")
    return plan


def credit_contact(db: Session, quest: Quest, creditor_id: str, contacts: dict[str, str]) -> Optional[str]:
    """X1: who a faction creditor's debt is linked to -- the one Nia named,
    else the offer's contact when the faction is the giver; None for a
    character creditor."""
    creditor = db.get(Entity, creditor_id)
    if creditor is None or creditor.type != "faction":
        return None
    offer = db.get(QuestOffer, quest.offer_id)
    if contacts.get(creditor_id):
        return contacts[creditor_id]
    return offer.contact_entity_id if offer.giver_entity_id == creditor_id else None


def settle_quest_on_credit(db: Session, *, quest: Quest, contacts: dict[str, str], is_secret: bool) -> Quest:
    """A2 (C-05): `ValueError` before any write; else the costs paid in part,
    every reward, one debt per creditor, the quest settled."""
    plan = credit_plan(db, quest)
    if plan.refusals:
        raise ValueError("; ".join(plan.refusals))
    title = db.get(Agenda, quest.agenda_id).title
    prepared: list[PreparedDebt] = []
    for creditor_id, owed in plan.owed.items():
        contact = credit_contact(db, quest, creditor_id, contacts)
        if contact is None and db.get(Entity, creditor_id).type == "faction":
            raise ValueError(f"il faut choisir le membre de « {db.get(Entity, creditor_id).name} » qui porte la dette")
        prepared.append(prepare_debt(db, world_id=quest.world_id, debtor_id=quest.character_id,
                                     creditor_id=creditor_id, contact_id=contact, origin="quest",
                                     origin_quest_id=quest.id, reason=f"Quête « {title} »", is_secret=is_secret,
                                     terms=owed))
    offer = db.get(QuestOffer, quest.offer_id)
    for term in in_order(quest_terms(db, quest.id)):
        pay = plan.paid.get(term.id)
        if pay == 0:
            continue
        apply_term(db, world_id=quest.world_id, character_id=quest.character_id, term=term,
                   giver_id=offer.giver_entity_id, reason=f"Quête « {title} »", amount=pay)
    finish_settlement(db, quest)
    for debt in prepared:
        write_debt(db, debt, changed_by=CHANGED_BY_CREDIT)
    return quest
