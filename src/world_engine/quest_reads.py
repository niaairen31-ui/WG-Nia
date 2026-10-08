"""Quest offers and quests: what the two surfaces read (TICKET-0108,
BRIEF-0108-B, contract C-04). Reads only: this module never writes.

Two audiences. The creator's offer editor (`offer_dict`, `editor_choices`)
sees the offers whole. The player's Journée panel (`journee_payload`) sees
the open offers he is eligible for (I1) and his quests: titles, giver,
objectives and states -- never an agenda or step id (the agenda stays
invisible, TICKET-0075's Scope OUT, kept for quests by Nia), so its dicts
carry a `quest_id`, an `offer_id`, and nothing else that names a row.

A quest's state is its agenda's (M1), worded by `QUEST_STATE_LABELS`.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .condition_forms import FORM_VALUES
from .condition_text import VALUE_LABELS_FR, describe, verdict_lines
from .conditions import evaluate, flat_leaves, node_to_dict, read_condition
from .day_resolve import blocked_details_fr
from .day_plan import evaluate_agenda_step, plan_bindings
from .models import (
    BASE_SKILL_DOMAINS,
    Agenda,
    AgendaStep,
    Character,
    Entity,
    Fact,
    FactionMembership,
    Item,
    Quest,
    QuestOffer,
    QuestOfferStep,
    SkillDefinition,
)
from .prose_render import fact_texts
from .quest_value import offer_value, value_dict, world_rates
from .quest_wording import term_dict, term_line
from .writes.quest_terms import FACT_REWARD_LEVELS, offer_terms, quest_terms
from .writes.quests import QUEST_GIVER_TYPES, acceptance_refusal

# M1: the agenda's status, as the player reads it.
QUEST_STATE_LABELS: dict[str, str] = {
    "active": "en cours",
    "paused": "en cours",
    "completed": "accomplie",
    "failed": "échouée",
    "abandoned": "abandonnée",
}


def _requirement_dict(req) -> dict:
    return {"type": req.type, "target_entity_id": req.target_entity_id, "target_key": req.target_key,
            "threshold": req.threshold, "subject_role": req.subject_role,
            "subject_entity_id": req.subject_entity_id, "value": req.value}


def condition_view(db: Session, tree) -> dict:
    """One condition as the editor reads it (TICKET-0111, T1): the tree
    itself, its leaves when it is flat (the list the editor edits; None when
    it is not -- shown, sent back unchanged), and its French lines."""
    flat = flat_leaves(tree)
    return {"tree": node_to_dict(tree), "flat": None if flat is None else [_requirement_dict(r) for r in flat],
            "lines": describe(db, tree)}


def _name(db: Session, entity_id: Optional[str]) -> Optional[str]:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else None


def offer_dict(offer: QuestOffer, db: Session) -> dict:
    """The creator's view of one offer: every field, its eligibility and its
    steps with their requirements, in order."""
    steps = db.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)
                    .order_by(QuestOfferStep.step_order)).all()
    terms = offer_terms(db, offer.id)
    return {
        "id": offer.id, "giver_entity_id": offer.giver_entity_id, "giver_name": _name(db, offer.giver_entity_id),
        # TICKET-0110 (X1): a faction giver's contact.
        "contact_entity_id": offer.contact_entity_id, "contact_name": _name(db, offer.contact_entity_id),
        "title": offer.title, "summary": offer.summary, "repeatable": offer.repeatable, "status": offer.status,
        "eligibility": condition_view(db, read_condition(db, role="eligibility", quest_offer_id=offer.id)),
        "steps": [{
            "objective": step.objective, "cost": step.cost, "domain": step.domain,
            "prerequisite": condition_view(db, read_condition(db, role="prerequisite", quest_offer_step_id=step.id)),
            "completion": condition_view(db, read_condition(db, role="completion", quest_offer_step_id=step.id)),
        } for step in steps],
        # TICKET-0109 (B1, C1): the costs and rewards, and their indicative value.
        "terms": [term_dict(db, t, offer.giver_entity_id) for t in terms],
        "value": value_dict(offer_value(db, offer.world_id, terms)),
    }


def world_offers(world_id: str, db: Session) -> list[QuestOffer]:
    """Every offer of the world, open first, then by title."""
    offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).all()
    return sorted(offers, key=lambda o: (o.status != "open", o.title.lower(), o.id))


def _named(db: Session, world_id: str, entity_type: str) -> list[dict]:
    rows = db.exec(select(Entity).where(Entity.world_id == world_id, Entity.type == entity_type,
                                        Entity.status == "active")).all()
    return sorted(({"id": e.id, "name": e.name} for e in rows), key=lambda d: (d["name"].lower(), d["id"]))


def faction_members(world_id: str, db: Session) -> dict[str, list[dict]]:
    """TICKET-0110 (X1): each faction's active character members, by name --
    who may be a contact."""
    rows = db.exec(select(FactionMembership.faction_id, Entity).join(Entity, Entity.id == FactionMembership.entity_id)
                   .where(Entity.world_id == world_id, Entity.type == "character", Entity.status == "active",
                          FactionMembership.left_at.is_(None))).all()
    members: dict[str, list[dict]] = {}
    for faction_id, entity in rows:
        members.setdefault(faction_id, []).append({"id": entity.id, "name": entity.name})
    return {fid: sorted(people, key=lambda d: (d["name"].lower(), d["id"])) for fid, people in members.items()}


def editor_choices(world_id: str, db: Session) -> dict:
    """What the offer editor's pickers list: givers, characters, locations,
    factions, facts (their text), skills (base domains, then definitions),
    offers; items with their value, the fact reward levels and the world's
    rates (TICKET-0109); each faction's members (TICKET-0110, X1); the
    values a form compares to (TICKET-0111)."""
    facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
    definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
    characters = _named(db, world_id, "character")
    factions = _named(db, world_id, "faction")
    return {
        "givers": characters + factions,
        "characters": characters,
        "locations": _named(db, world_id, "location"),
        "factions": factions,
        "facts": sorted(({"id": f.id, "text": t} for f, t in zip(facts, fact_texts(db, facts))),
                        key=lambda d: (d["text"].lower(), d["id"])),
        "skills": [{"key": d, "label": d} for d in BASE_SKILL_DOMAINS]
        + sorted(({"key": d.id, "label": d.name} for d in definitions), key=lambda d: d["label"].lower()),
        "offers": [{"id": o.id, "title": o.title} for o in world_offers(world_id, db)],
        "giver_types": list(QUEST_GIVER_TYPES),
        "items": [{**i, "value": db.get(Item, i["id"]).value} for i in _named(db, world_id, "item")],
        "fact_levels": list(FACT_REWARD_LEVELS),
        "rates": world_rates(db, world_id),
        "members": faction_members(world_id, db),
        # TICKET-0111 (S1): the values a form compares to, in French.
        "form_values": {form: [{"value": value, "label": VALUE_LABELS_FR[form][value]} for value in values]
                        for form, values in FORM_VALUES.items()},
    }


def available_offers(character: Character, db: Session) -> list[QuestOffer]:
    """I1: the open offers of the world `character` may accept now."""
    offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == character.world_id,
                                              QuestOffer.status == "open")).all()
    return sorted((o for o in offers if acceptance_refusal(db, o, character) is None),
                  key=lambda o: (o.title.lower(), o.id))


def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]:
    """Each step: what the active one still needs, and -- M1 (TICKET-0111) --
    where its objective stands, every line of its completion condition
    judged (« 3/15 »); [] when it has none. Shown, never acted on. A player
    surface: every line is as the character may read it (AMENDMENT-0111-01,
    A1 and V2), `completion_met` included."""
    steps = db.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda.id)
                    .order_by(AgendaStep.step_order)).all()
    bindings = plan_bindings(agenda.id, character, db)
    view = []
    for step in steps:
        blocked: list[str] = []
        if step.status == "active":
            evaluated = evaluate_agenda_step(step, character, db)
            blocked = blocked_details_fr(evaluated.verdict, db, character.id)
        completion = evaluate(read_condition(db, role="completion", agenda_step_id=step.id), bindings, db)
        seen = completion.seen_by(character.id) if completion is not None else None
        view.append({"order": step.step_order, "objective": step.objective, "status": step.status,
                     "outcome": step.outcome, "blocked": blocked,
                     "completion": verdict_lines(db, completion, character.id),
                     "completion_met": seen.met if seen is not None else None})
    return view


def player_quests(character: Character, db: Session) -> list[dict]:
    """The character's quests, open first then most recent: title, giver,
    state, steps (the active one with what it still needs)."""
    rows = db.exec(select(Quest, Agenda).join(Agenda, Agenda.id == Quest.agenda_id)
                   .where(Quest.character_id == character.id)).all()
    ordered = sorted(rows, key=lambda r: (QUEST_STATE_LABELS[r[1].status] != "en cours",
                                          -r[0].accepted_at.timestamp(), r[0].id))
    view = []
    for quest, agenda in ordered:
        offer = db.get(QuestOffer, quest.offer_id)
        view.append({
            "quest_id": quest.id, "offer_id": quest.offer_id, "title": agenda.title,
            "giver_name": _name(db, offer.giver_entity_id) if offer is not None else None,
            "summary": offer.summary if offer is not None else None,
            "state": QUEST_STATE_LABELS[agenda.status], "open": agenda.status in ("active", "paused"),
            "steps": _steps_view(agenda, character, db),
            # TICKET-0109 (D1): its terms, and whether « déclarer accomplie » applies.
            "terms": [term_line(db, t, offer.giver_entity_id) for t in quest_terms(db, quest.id)] if offer else [],
            "settled": quest.settled_at is not None,
            "settleable": quest.settled_at is None and agenda.status in ("active", "paused", "completed"),
        })
    return view


def journee_payload(character: Character, db: Session) -> dict:
    """GET /api/quests (C-04): the offers the player may accept and his
    quests. No agenda or step id (checked by `quests.py`)."""
    offers = [{"offer_id": o.id, "title": o.title, "summary": o.summary,
               "giver_name": _name(db, o.giver_entity_id),
               "terms": [term_line(db, t, o.giver_entity_id) for t in offer_terms(db, o.id)],
               "steps": [s.objective for s in db.exec(select(QuestOfferStep).where(
                   QuestOfferStep.offer_id == o.id).order_by(QuestOfferStep.step_order)).all()]}
              for o in available_offers(character, db)]
    return {"offers": offers, "quests": player_quests(character, db)}


def pinned_plan(quest_id: str, character: Character, db: Session) -> Agenda:
    """O1 (C-05): the agenda of the character's OPEN quest `quest_id`, for a
    day the player pinned to it. `LookupError` when no such quest is his,
    `ValueError` when it is over."""
    quest = db.get(Quest, quest_id) if quest_id else None
    if quest is None or quest.character_id != character.id:
        raise LookupError(f"quest {quest_id!r} not found for this character")
    agenda = db.get(Agenda, quest.agenda_id)
    if agenda is None or agenda.status not in ("active", "paused"):
        raise ValueError("cette quête est terminée : elle ne peut plus être avancée")
    return agenda
