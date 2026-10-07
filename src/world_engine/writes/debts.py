"""Debts: the writers (TICKET-0110, BRIEF-0110-B, J2, C2, T1, F-a, F-b1, U1,
V1, X1, contract C-03).

- `prepare_debt(...)` validates a debt whole -- parties, contact, origin,
  terms -- and returns what `write_debt` writes; nothing is written before
  every check has passed. `create_debt` is the two in a row.
- `write_debt(...)`   : the debt's fact (a free `information` fact, aspect
  `dette`, whose participants are the debtor, the creditor and the
  contact), the parties' knowledge of it (the debtor, and the creditor --
  his contact for a faction -- at `knows`, secret when the debt is), a
  `faction` default at `knows` for a faction creditor's members when the
  debt is not secret (U1), the `debt` row and its terms.
- `debt_refusals(...)` / `settle_debt(...)`: repaying, all at once (D1).
  Money and items move from the debtor to the creditor; a fact is
  delivered, a skill taught, to the RECEIVER (the creditor, his contact for
  a faction). A receiver who already holds that fact or skill is not
  refused: his regard toward the debtor falls by the world's
  `debt_fact_relation` or `debt_skill_relation` instead.
- `forgive_debt(...)`: the creditor lets it go, with an optional note.

Settling and forgiving close the row once (`status`, `closed_at`, and the
note) -- a debt is never deleted -- and rewrite its fact with a
`changement` (TICKET-0105): whoever learned the debt earlier keeps the old
version until a later contact; the two parties' rows are refreshed, so they
know at once. None of these functions commits.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from ..fact_refs import find_held
from ..holdings import held_quantity
from ..ledger import get_balance
from ..models import (
    DEBT_CURRENCIES,
    DEBT_ORIGINS,
    Debt,
    DebtTerm,
    Entity,
    Fact,
    FactionMembership,
    Item,
    Knowledge,
    Quest,
    SkillDefinition,
)
from ..prose_render import entity_token
from ..quest_value import world_rates
from ..skill_access import held_rank, skill_label
from ..skill_ranks import MAX_RANK
from .characters import write_ledger_entry, write_skill_row
from .facts import attach_participants, create_fact, create_fact_default, update_fact_content
from .items import write_holding
from .knowledge import knowledge_level_rank, write_knowledge
from .quest_settlement import LEARNED_RANK, skill_row
from .relations import write_relation

# What a party learns of the debt, and from where (F-a).
DEBT_FACT_LEVEL = "knows"
DEBT_FACT_ASPECT = "dette"
DEBT_SOURCE = "dette"
# The ledger origin of a repayment.
DEBT_LEDGER_SOURCE = "debt"
# The settings of `quest_economy` a delivery no longer possible costs.
STALE_RELATION_SETTING = {"fact": "debt_fact_relation", "skill": "debt_skill_relation"}


@dataclass(frozen=True)
class DebtTermSpec:
    currency: str
    item_id: Optional[str] = None
    fact_id: Optional[str] = None
    skill_key: Optional[str] = None
    amount: Optional[int] = None


@dataclass(frozen=True)
class PreparedDebt:
    world_id: str
    debtor_id: str
    creditor_id: str
    contact_id: Optional[str]
    origin: str
    origin_quest_id: Optional[str]
    reason: Optional[str]
    is_secret: bool
    terms: tuple[dict, ...]


def _active(db: Session, world_id: str, entity_id: Optional[str], types: tuple[str, ...]) -> Optional[Entity]:
    entity = db.get(Entity, entity_id) if entity_id else None
    if entity is None or entity.world_id != world_id or entity.type not in types or entity.status != "active":
        return None
    return entity


def is_active_member(db: Session, character_id: Optional[str], faction_id: str) -> bool:
    """X1: `character_id` holds an active membership of `faction_id`."""
    return character_id is not None and db.exec(select(FactionMembership.id).where(
        FactionMembership.entity_id == character_id, FactionMembership.faction_id == faction_id,
        FactionMembership.left_at.is_(None))).first() is not None


def clean_debt_term(db: Session, world_id: str, index: int, spec: DebtTermSpec) -> dict:
    """One owed term validated (C-02); its columns, or `ValueError`."""
    where = f"owed term {index + 1}"
    if spec.currency not in DEBT_CURRENCIES:
        raise ValueError(f"{where}: currency must be one of {DEBT_CURRENCIES}")
    columns = {"currency": spec.currency, "item_id": None, "fact_id": None, "skill_key": None, "amount": None}
    if spec.currency in ("money", "item"):
        if not isinstance(spec.amount, int) or isinstance(spec.amount, bool) or spec.amount < 1:
            raise ValueError(f"{where}: a {spec.currency} term needs an amount of at least 1")
        columns["amount"] = spec.amount
    if spec.currency == "item":
        if _active(db, world_id, spec.item_id, ("item",)) is None or db.get(Item, spec.item_id) is None:
            raise ValueError(f"{where}: {spec.item_id!r} is not an item of this world")
        columns["item_id"] = spec.item_id
    elif spec.currency == "fact":
        fact = db.get(Fact, spec.fact_id) if spec.fact_id else None
        if fact is None or fact.world_id != world_id:
            raise ValueError(f"{where}: {spec.fact_id!r} is not a fact of this world")
        columns["fact_id"] = spec.fact_id
    elif spec.currency == "skill":
        definition = db.get(SkillDefinition, spec.skill_key) if spec.skill_key else None
        if definition is None or definition.world_id != world_id:
            raise ValueError(f"{where}: teaching needs a skill definition of this world")
        columns["skill_key"] = spec.skill_key
    return columns


def _check_contact(db: Session, world_id: str, creditor: Entity, contact_id: Optional[str]) -> None:
    if creditor.type == "character":
        if contact_id is not None:
            raise ValueError("prepare_debt: a character creditor has no contact")
        return
    if contact_id is None:
        raise ValueError("prepare_debt: a debt toward a faction names its contact, an active member (X1)")
    if _active(db, world_id, contact_id, ("character",)) is None or not is_active_member(db, contact_id, creditor.id):
        raise ValueError(f"prepare_debt: {contact_id!r} is not an active member of the creditor faction")


def prepare_debt(
    db: Session, *, world_id: str, debtor_id: str, creditor_id: str, contact_id: Optional[str], origin: str,
    origin_quest_id: Optional[str] = None, reason: Optional[str] = None, is_secret: bool = False,
    terms: list[DebtTermSpec],
) -> PreparedDebt:
    """Every check of C-03's case table (b-1), before any write."""
    if _active(db, world_id, debtor_id, ("character",)) is None:
        raise ValueError(f"prepare_debt: debtor {debtor_id!r} is not an active character of this world")
    creditor = _active(db, world_id, creditor_id, ("character", "faction"))
    if creditor is None:
        raise ValueError(f"prepare_debt: creditor {creditor_id!r} is not an active character or faction")
    if creditor_id == debtor_id:
        raise ValueError("prepare_debt: a character cannot owe himself")
    _check_contact(db, world_id, creditor, contact_id or None)
    if origin not in DEBT_ORIGINS:
        raise ValueError(f"prepare_debt: origin must be one of {DEBT_ORIGINS}")
    quest = db.get(Quest, origin_quest_id) if origin_quest_id else None
    if (origin == "quest") != (quest is not None and quest.world_id == world_id):
        raise ValueError("prepare_debt: a debt born of a quest names that quest, and only then")
    clean = tuple(clean_debt_term(db, world_id, i, spec) for i, spec in enumerate(terms))
    motive = (reason or "").strip() or None
    if not clean and motive is None:
        raise ValueError("prepare_debt: a debt that owes nothing counted needs a reason")
    return PreparedDebt(world_id, debtor_id, creditor_id, contact_id or None, origin, origin_quest_id, motive,
                        bool(is_secret), clean)


def _owed_phrase(db: Session, terms: list) -> str:
    """What the fact says is owed: « 20 pièce(s), 2 × [Fourrure] … »."""
    phrases = []
    for term in terms:
        if term.currency == "money":
            phrases.append(f"{term.amount} pièce(s)")
        elif term.currency == "item":
            item = db.get(Entity, term.item_id)
            phrases.append(f"{term.amount} × {entity_token(term.item_id, item.name if item else '?')}")
        elif term.currency == "fact":
            fact = db.get(Fact, term.fact_id)
            phrases.append(f"le savoir « {fact.content_raw if fact else '?'} »")
        else:
            phrases.append(f"l'enseignement de « {skill_label(db, term.skill_key)} »")
    return ", ".join(phrases) if phrases else "une faveur"


def debt_fact_text(db: Session, *, debtor_id: str, creditor_id: str, contact_id: Optional[str], terms: list,
                   reason: Optional[str], state: str, note: Optional[str] = None) -> str:
    """The stored text of a debt's fact (C-04), identity tokens for the
    parties: `open`, `settled` or `forgiven`."""
    def token(entity_id: str) -> str:
        entity = db.get(Entity, entity_id)
        return entity_token(entity_id, entity.name if entity else "?")
    debtor, creditor = token(debtor_id), token(creditor_id)
    via = f" (par l'entremise de {token(contact_id)})" if contact_id else ""
    tail = f" : {_owed_phrase(db, terms)}" + (f" — {reason}" if reason else "")
    if state == "open":
        return f"{debtor} doit à {creditor}{via}{tail}."
    if state == "settled":
        return f"{debtor} a réglé sa dette envers {creditor}{via}{tail}."
    return f"{creditor} a fait grâce à {debtor} de sa dette{via}{tail}." + (f" ({note})" if note else "")


def receiver_of(debt: Debt) -> str:
    """Who receives a fact or a skill: the creditor, his contact for a faction."""
    return debt.contact_entity_id or debt.creditor_entity_id


def _knows(db: Session, entity_id: str, fact_id: str, is_secret: bool, changed_by: str) -> None:
    """The entity knows the debt's fact now: a new row at `knows`, or its row
    refreshed (the same values, `updated_at` now -- a level never falls)."""
    row = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
    if row is None:
        write_knowledge(db, entity_id=entity_id, fact_id=fact_id, level=DEBT_FACT_LEVEL, is_secret=is_secret,
                        source=DEBT_SOURCE, changed_by=changed_by)
        return
    level = row.level if knowledge_level_rank(row.level) >= knowledge_level_rank(DEBT_FACT_LEVEL) else DEBT_FACT_LEVEL
    write_knowledge(db, knowledge_id=row.id, level=level, content=row.content_raw, source=row.source,
                    is_incorrect=row.is_incorrect, is_secret=row.is_secret, share_threshold=row.share_threshold,
                    session_id=row.session_id, changed_by=changed_by)


def write_debt(db: Session, prepared: PreparedDebt, *, changed_by: str) -> Debt:
    """C-03: the fact, the parties' knowledge, the faction default (U1), the
    row and its terms, from a `PreparedDebt`."""
    p = prepared
    terms = [DebtTerm(**columns) for columns in p.terms]  # for the text only, never added
    fact = create_fact(db, world_id=p.world_id, created_by=changed_by, facet="information", aspect=DEBT_FACT_ASPECT,
                       content=debt_fact_text(db, debtor_id=p.debtor_id, creditor_id=p.creditor_id,
                                              contact_id=p.contact_id, terms=terms, reason=p.reason, state="open"))
    db.flush()
    attach_participants(db, fact=fact, entity_ids=[p.debtor_id, p.creditor_id] + ([p.contact_id] if p.contact_id else []))
    debt = Debt(world_id=p.world_id, debtor_entity_id=p.debtor_id, creditor_entity_id=p.creditor_id,
                contact_entity_id=p.contact_id, origin=p.origin, origin_quest_id=p.origin_quest_id, reason=p.reason,
                is_secret=p.is_secret, fact_id=fact.id, status="open")
    db.add(debt)
    db.flush()
    for order, columns in enumerate(p.terms, start=1):
        db.add(DebtTerm(world_id=p.world_id, debt_id=debt.id, term_order=order, **columns))
    for party in (p.debtor_id, receiver_of(debt)):
        _knows(db, party, fact.id, p.is_secret, changed_by)
    if p.contact_id and not p.is_secret:
        create_fact_default(db, world_id=p.world_id, fact_id=fact.id, scope_type="faction",
                            scope_id=p.creditor_id, level=DEBT_FACT_LEVEL, created_by=changed_by)
    db.flush()
    return debt


def create_debt(db: Session, *, changed_by: str, **fields) -> Debt:
    """`prepare_debt(**fields)` then `write_debt` -- the creator's hand."""
    return write_debt(db, prepare_debt(db, **fields), changed_by=changed_by)


def debt_terms(db: Session, debt_id: str) -> list[DebtTerm]:
    return list(db.exec(select(DebtTerm).where(DebtTerm.debt_id == debt_id).order_by(DebtTerm.term_order)).all())


def _name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else "?"


def _already_held(db: Session, debt: Debt, term) -> bool:
    """The receiver already holds what this fact or skill term delivers."""
    receiver = receiver_of(debt)
    if term.currency == "fact":
        return find_held(db, receiver, {"fact_id": term.fact_id}) is not None
    return term.currency == "skill" and skill_row(db, receiver, term.skill_key) is not None


def debt_refusals(db: Session, debt: Debt) -> list[str]:
    """Why the debtor cannot repay `debt` now (French, case table b-2);
    empty when he can."""
    if debt.status == "settled":
        return ["cette dette est déjà réglée"]
    if debt.status == "forgiven":
        return ["cette dette a été remise"]
    debtor, who = debt.debtor_entity_id, _name(db, debt.debtor_entity_id)
    money, items, refusals = 0, defaultdict(int), []
    for term in debt_terms(db, debt.id):
        if term.currency == "money":
            money += term.amount
        elif term.currency == "item":
            items[term.item_id] += term.amount
        elif _already_held(db, debt, term):
            continue
        elif term.currency == "fact" and find_held(db, debtor, {"fact_id": term.fact_id}) is None:
            refusals.append(f"{who} doit connaître le fait à transmettre")
        elif term.currency == "skill" and held_rank(db, debtor, term.skill_key) != MAX_RANK:
            refusals.append(f"{who} doit être Maître en « {skill_label(db, term.skill_key)} » pour l'enseigner")
    balance = get_balance(db, debtor)
    if money > balance:
        refusals.append(f"il faut {money} pièce(s), {who} en a {balance}")
    for item_id, needed in items.items():
        held = held_quantity(db, debtor, item_id)
        if needed > held:
            refusals.append(f"il faut {needed} × {_name(db, item_id)}, {who} en a {held}")
    return refusals


def _deliver(db: Session, debt: Debt, term, rates: dict[str, int], reason: str, changed_by: str) -> None:
    """One owed term, from the debtor to the creditor (b-3)."""
    debtor, creditor, receiver = debt.debtor_entity_id, debt.creditor_entity_id, receiver_of(debt)
    if term.currency == "money":
        write_ledger_entry(db, world_id=debt.world_id, entity_id=debtor, amount=-term.amount, counterparty_id=creditor,
                           reason=reason, source_type=DEBT_LEDGER_SOURCE)
        write_ledger_entry(db, world_id=debt.world_id, entity_id=creditor, amount=term.amount, counterparty_id=debtor,
                           reason=reason, source_type=DEBT_LEDGER_SOURCE)
    elif term.currency == "item":
        write_holding(db, world_id=debt.world_id, item_id=term.item_id, holder_entity_id=debtor, delta=-term.amount,
                      changed_by=changed_by)
        write_holding(db, world_id=debt.world_id, item_id=term.item_id, holder_entity_id=creditor, delta=term.amount,
                      changed_by=changed_by)
    elif _already_held(db, debt, term):
        fall = rates[STALE_RELATION_SETTING[term.currency]]
        if fall > 0:
            write_relation(db, mode="delta", world_id=debt.world_id, entity_a_id=receiver, entity_b_id=debtor,
                           type="other", value=-fall, changed_by=changed_by)
    elif term.currency == "fact":
        write_knowledge(db, entity_id=receiver, fact_id=term.fact_id, level=DEBT_FACT_LEVEL, source=DEBT_SOURCE,
                        changed_by=changed_by)
    else:
        write_skill_row(db, character_id=receiver, rank=LEARNED_RANK, skill_definition_id=term.skill_key,
                        taught_by_id=debtor)
    db.flush()


def _close(db: Session, debt: Debt, status: str, note: Optional[str], changed_by: str) -> Debt:
    """The row closed once, the fact's `changement`, both parties refreshed."""
    debt.status, debt.closed_at, debt.closed_note = status, datetime.now(UTC), note
    db.add(debt)
    fact = db.get(Fact, debt.fact_id)
    update_fact_content(db, fact=fact, changed_by=changed_by, kind="changement", content=debt_fact_text(
        db, debtor_id=debt.debtor_entity_id, creditor_id=debt.creditor_entity_id, contact_id=debt.contact_entity_id,
        terms=debt_terms(db, debt.id), reason=debt.reason, state=status, note=note))
    db.flush()
    for party in (debt.debtor_entity_id, receiver_of(debt)):
        _knows(db, party, fact.id, debt.is_secret, changed_by)
    return debt


def settle_debt(db: Session, *, debt: Debt, changed_by: str) -> Debt:
    """D1: `ValueError` with the refusals joined, before any write; else
    every term delivered in order, then the debt `settled`."""
    refusals = debt_refusals(db, debt)
    if refusals:
        raise ValueError("; ".join(refusals))
    rates = world_rates(db, debt.world_id)
    reason = f"Dette envers {_name(db, debt.creditor_entity_id)}"
    for term in debt_terms(db, debt.id):
        _deliver(db, debt, term, rates, reason, changed_by)
    return _close(db, debt, "settled", None, changed_by)


def forgive_debt(db: Session, *, debt: Debt, note: Optional[str], changed_by: str) -> Debt:
    """The creditor lets an open debt go; `ValueError` when it is closed."""
    if debt.status != "open":
        raise ValueError("cette dette n'est plus due")
    return _close(db, debt, "forgiven", (note or "").strip() or None, changed_by)
