"""One offer save, shared by Création › Quêtes and the review queue (TICKET-0121).

`save_offer_body` is the creator CRUD's own save of a quest offer -- the proposed
attributes materialized, the steps built, `write_quest_offer`, the interpreter
drafts marked `saved` -- without the commit and without the HTTP mapping: a
refusal is a `ValueError`. Two callers: `routes/quests.py` (the editor's save,
which maps the refusal to 422 and commits) and `apply_offer_proposal` (the
`quest_offer_creation` applier, BRIEF-0121-E, C-09 / C-10).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from sqlmodel import Session

from ..attribute_proposals import materialize, rewrite
from ..conditions import node_from_dict, node_to_dict
from ..day_plan import PlanStep
from ..models import QuestOffer
from ..writes import TermSpec, write_quest_offer
from ..writes.condition_drafts import mark_draft_saved
from ..writes.conditions import clean_condition
from .routes.attributes import UnsavedBody


class OfferStepBody(BaseModel):
    objective: str
    cost: int
    domain: Optional[str] = None
    # TICKET-0111 (I1, M1): a step's conditions are trees in the dict form of
    # `conditions.node_to_dict`; null is none.
    prerequisite: Optional[dict] = None
    completion: Optional[dict] = None
    # TICKET-0114 (H1): when the step has failed -- shown, never acting.
    failure: Optional[dict] = None
    # TICKET-0112 (IH1): the interpreter's proposal the creator inserted into
    # each condition, if any; saving marks it `saved` (`mark_draft_saved`).
    prerequisite_draft_id: Optional[str] = None
    completion_draft_id: Optional[str] = None
    failure_draft_id: Optional[str] = None


class TermBody(BaseModel):
    direction: str
    currency: str
    counterparty_entity_id: Optional[str] = None
    item_id: Optional[str] = None
    fact_id: Optional[str] = None
    skill_key: Optional[str] = None
    amount: Optional[int] = None
    level: Optional[str] = None


class OfferBody(BaseModel):
    giver_entity_id: str
    # TICKET-0110 (X1): a faction giver's contact; null clears it.
    contact_entity_id: Optional[str] = None
    title: str
    summary: Optional[str] = None
    repeatable: bool = False
    status: str = "open"
    eligibility: Optional[dict] = None
    steps: list[OfferStepBody] = Field(default_factory=list)
    # TICKET-0109 (B1): the offer's costs and rewards, replaced whole; absent
    # (None) keeps the stored ones.
    terms: Optional[list[TermBody]] = None
    # TICKET-0112 (IH1): the interpreter's proposal inserted into the eligibility.
    eligibility_draft_id: Optional[str] = None
    # TICKET-0113 (BRIEF-0113-E, WN2): the attributes the interpreter proposed
    # and the creator confirmed; the save writes those a condition names.
    unsaved_attributes: list[UnsavedBody] = Field(default_factory=list)


def term_spec(term: TermBody) -> TermSpec:
    return TermSpec(**{name: (value if value != "" else None) for name, value in term.model_dump().items()})


def _mark_drafts(body: OfferBody, trees: list, offer_id: str, world_id: str, db: Session, as_saved) -> None:
    """IH1: each inserted proposal is `saved` with the offer, in its
    transaction, compared with the condition as written (its clean dict
    form) -- the proposal's unsaved attributes rewritten to the ids the save
    wrote (`as_saved`, TICKET-0113). A draft that cannot be marked is
    skipped: the journal never fails the creator's save."""
    ids = [body.eligibility_draft_id] + [
        d for step in body.steps for d in (step.prerequisite_draft_id, step.completion_draft_id,
                                           step.failure_draft_id)]
    for draft_id, raw in zip(ids, trees):
        if draft_id:
            tree = node_to_dict(clean_condition(db, world_id, node_from_dict(raw)))
            mark_draft_saved(db, world_id=world_id, draft_id=draft_id, offer_id=offer_id, tree=tree,
                             proposed_as_saved=as_saved)


def save_offer_body(db: Session, world_id: str, body: OfferBody, offer: Optional[QuestOffer]) -> QuestOffer:
    """Write `body` as `offer` (None: a new one) in the caller's transaction.
    `ValueError` propagates; the caller rolls back and commits."""
    # WN2 (TICKET-0113): the proposed attributes a condition names are
    # written first, in this transaction, and the conditions rewritten
    # to their ids.
    trees, keys, labels = materialize(
        db, world_id, [u.model_dump() for u in body.unsaved_attributes],
        [body.eligibility] + [t for s in body.steps for t in (s.prerequisite, s.completion, s.failure)])
    steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
                      prerequisite=node_from_dict(trees[1 + 3 * i]), completion=node_from_dict(trees[2 + 3 * i]),
                      failure=node_from_dict(trees[3 + 3 * i]))
             for i, s in enumerate(body.steps)]
    offer = write_quest_offer(
        db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
        summary=body.summary, repeatable=body.repeatable, status=body.status,
        eligibility=node_from_dict(trees[0]), steps=steps,
        terms=None if body.terms is None else [term_spec(t) for t in body.terms],
        contact_entity_id=body.contact_entity_id or None,
    )
    _mark_drafts(body, trees, offer.id, world_id, db, lambda proposed: rewrite(proposed, keys, labels))
    return offer
