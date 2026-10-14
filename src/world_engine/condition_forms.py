"""The requirement forms: the leaves of the condition language, each with
its evaluator (TICKET-0111, BRIEF-0111-A -- a pure move out of `day_plan.py`,
which keeps the plan emission and the budget cut; decisions S1 of TICKET-0075,
C-01 of TICKET-0108, G1 of TICKET-0110 unchanged).

Every form judges ONE character against the canon and returns a `Verdict`;
`_EVALUATORS` maps each form of `REQUIREMENT_TYPES` to its evaluator, and
`evaluate_specs` judges a flat list of them. This module writes nothing.

`_day_reachable_ids` is a NEW, day-local `connects_to` BFS reader, not a
reuse of an existing one. The original brief instructed "reuse the existing
traversal; do not write a second one" — that instruction was wrong: it
contradicted decision D1 (BRIEF-19), standing project doctrine that each new
`connects_to` consumer gets its OWN reader (a real dedup opportunity is
REPORTED, never acted on). Claude Code escalated under the brief's own STOP
condition rather than guess; Nia's correction is
`tooling/briefs/BRIEF-0075-b-amendment-1-location-reachable-reader.md`. Per
that amendment's count, this is roughly the SEVENTH independent
`connects_to` reader in the tree — `_location_neighbours`
(`cockpit/play.py:854`, direct neighbours only) and `_reachable_locations`
(`tick_context.py:405`, interval-hop-bounded, origin EXCLUDED) are the two
closest siblings, and `_day_reachable_ids` is deliberately NOT shared with
either: unbounded (a day has no meaningful hop radius) and origin-INCLUSIVE
(the player is already there, which satisfies reachability) — a concrete
shape difference, not only a doctrinal one.

`_day_reachable_ids` proves a path exists in the `connects_to` graph; it does
NOT prove the Play surface's door/travel gate would let the player walk it
today. Harmless now (the day chain resolves travel abstractly — Play is
sealed, TICKET-0061), and worth a fresh look only if a future ticket ever
routes a day step through Play.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from sqlmodel import Session, func, select

from .attributes import AttributeView, applies_to, current_value, value_label, view_of
from .models import (
    Agenda,
    Character,
    Debt,
    Entity,
    Event,
    EventParticipant,
    EventType,
    Fact,
    FactionMembership,
    ItemHolding,
    Knowledge,
    Ledger,
    Location,
    Quest,
    QuestOffer,
    Relation,
    Rencontre,
)
from .prose_render import fact_text
from .relation_orientation import is_social
from .skill_access import held_rank, skill_label

# S1: the closed requirement vocabulary, each form with a named evaluator.
# Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A, C-01): the four the
# day-plan model may emit, then four only the creator authors (quest offers).
# Ten since v2.19 (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and
# `no_debt_to`, creator only as well. Twelve since v2.20 (TICKET-0111,
# BRIEF-0111-C, S1): `quest_state` replaces `quest_completed` (a quest in
# any of its four states, `completed` among them), `item_held` and
# `vital_status` read data the canon already keeps. Since v2.23
# (TICKET-0113, BRIEF-0113-B, WE1, WG1): `attribute` reads one attribute of
# its subject -- a world's definition or a system attribute, `vital_status`
# among them -- and replaces the `vital_status` form (`attributes.ATTRIBUTE_FORM`
# names it there, `attribute_conditions.py` AB1 keeps the two equal). Since
# v2.24 (TICKET-0114, BRIEF-0114-E, G1): `event` counts what happened --
# the events of one type its subject took part in, in one role or any, with
# filters on the other roles and a place, since a window (F1);
# `event_vocab.EVENT_FORM` names it there.
# TICKET-0121 (BRIEF-0121-A, E3a): `is_character` -- the one who acts is this character.
REQUIREMENT_TYPES: tuple[str, ...] = (
    "knowledge", "relation_gte", "resource", "location_reachable",
    "has_met", "faction_member", "skill_rank_gte", "quest_state",
    "has_debt_to", "no_debt_to", "item_held", "attribute", "event",
    "is_character",
)

# What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
# forms it always could. A creator-only form in a model's plan is a parse
# failure, never a row.
MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")

# The shape of each form, the three groups of the `*_requirement_shape`
# CHECK (C-01): which column names its target, and which need a threshold.
ENTITY_TARGET_TYPES: tuple[str, ...] = (
    "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to", "item_held",
    "is_character",
)
KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_state", "attribute", "event")
THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte", "item_held", "event")
# v2.23 (TICKET-0113, WG1): the forms whose subject may be any entity of
# the world -- an attribute applies to the types its definition names; every
# other form judges a character.
ANY_SUBJECT_TYPES: tuple[str, ...] = ("attribute", "event")
# A quest's state is its agenda's (M1 of TICKET-0108); `open` is `active` or
# `paused`, the player's « en cours ».
QUEST_STATES: tuple[str, ...] = ("open", "completed", "failed", "abandoned")
QUEST_STATE_AGENDA_STATUSES: dict[str, tuple[str, ...]] = {
    "open": ("active", "paused"), "completed": ("completed",), "failed": ("failed",),
    "abandoned": ("abandoned",),
}
# A form whose `value` is one of a closed set. An `attribute` leaf's value is
# one of its definition's choices: its writer checks it against the
# definition, never a set here.
FORM_VALUES: dict[str, tuple[str, ...]] = {"quest_state": QUEST_STATES}


@dataclass(frozen=True)
class EventFilter:
    """An `event` leaf's filter on one other role of its type (TICKET-0114):
    an entity or a sorte fills it (`condition_node_filter`)."""
    role_id: str
    entity_id: Optional[str] = None
    sorte_id: Optional[str] = None


@dataclass(frozen=True)
class RequirementSpec:
    """One form with its arguments: a leaf of the condition language. Its
    SUBJECT (TICKET-0111, P1) is a role bound when the condition is judged
    (`conditions.SUBJECT_ROLES`, `doer` by default: the character who acts)
    or one fixed entity; `value` is the state a form compares to, for the
    forms that take one."""
    type: str
    target_entity_id: Optional[str] = None
    target_key: Optional[str] = None
    threshold: Optional[int] = None
    subject_role: Optional[str] = "doer"
    subject_entity_id: Optional[str] = None
    value: Optional[str] = None
    # `event` (TICKET-0114): since when it counts (`models.CONDITION_WINDOWS`)
    # and its filters on the other roles; `value` is the subject's role id
    # (None: any role), `target_key` the type, `target_entity_id` a place,
    # `threshold` how many.
    since: Optional[str] = None
    filters: tuple[EventFilter, ...] = ()



@dataclass(frozen=True)
class Verdict:
    # `type` FIRST (BRIEF-0078-a, Scope IN item 3): a positional
    # `Verdict(...)` construction anywhere in the tree now fails loudly
    # (wrong type in the wrong slot) rather than silently shifting fields.
    type: str
    met: bool
    current: object
    required: object
    reason: str
    # TICKET-0097: the player-facing text of `required` when it is an id
    # (a `knowledge` gate's fact); None when `required` is already readable.
    required_label: Optional[str] = None
    # TICKET-0113 (BRIEF-0113-B, WH1): the leaf reads a hidden attribute --
    # never written out, nor its state shown, on a player surface.
    hidden: bool = False
    # TICKET-0114 (BRIEF-0114-E): an `event` leaf's counted events, as
    # (fact id, quantity) -- a player surface recounts the ones its viewer
    # knows (`conditions.VerdictNode.seen_by`).
    events: tuple = ()



# ── requirement evaluators (S1) ──────────────────────────────────────────────
# Uniform 4-arg signature (`_SOURCE_LOOKUPS` precedent, schedule_reads.py):
# every evaluator accepts `reachable_ids`, even the three that ignore it —
# keeps `_EVALUATORS` directly callable without a special case.

def _eval_knowledge(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """`target_key` is a fact id (TICKET-0097, D1'a): met iff the character
    holds a row on that fact."""
    del reachable_ids
    row = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == character.id, Knowledge.fact_id == req.target_key,
        )
    ).first()
    met = row is not None
    fact = db.get(Fact, req.target_key) if req.target_key else None
    label = fact_text(db, fact) if fact is not None else req.target_key
    reason = (
        f"knowledge {label!r} already held" if met
        else f"prerequisite not met — knowledge {label!r} not held"
    )
    return Verdict(
        type=req.type, met=met, current=("held" if met else "unheld"), required=req.target_key, reason=reason,
        required_label=label,
    )


def _eval_relation_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """What the TARGET feels toward the character (TICKET-0108, B-dir): the
    social row `entity_a = target`, `entity_b = character`, `is_social`;
    0 when there is none. A deliberate duplicate of
    `writes.relations._find_perceived_relation`'s query (perceiver = the
    target), not an import: writes/goals_agendas.py imports FROM this module,
    so importing FROM writes/ here would cycle the package. The reverse row
    (the character's own feeling) and the structural types are never read."""
    del reachable_ids
    rows = db.exec(
        select(Relation).where(
            Relation.entity_a_id == req.target_entity_id, Relation.entity_b_id == character.id,
        )
    ).all()
    rel = next((row for row in rows if is_social(row.type)), None)
    current = rel.intensity if rel else 0
    threshold = req.threshold or 0
    met = current >= threshold
    target = db.get(Entity, req.target_entity_id)
    target_name = target.name if target else req.target_entity_id
    reason = (
        f"relation of {target_name} toward the character is {current}, meets requires >= {threshold}" if met
        else f"prerequisite not met — relation of {target_name} toward the character is {current}, "
        f"requires >= {threshold}"
    )
    return Verdict(
        type=req.type, met=met, current=current, required=threshold, reason=reason,
        required_label=target_name,
    )


def _eval_resource(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """Money: the character's ledger balance. A world has one currency (the
    `ledger` has no currency column), so `target_key` is a label and is not
    read; an object is never a `resource` (TICKET-0108, E1: objects held in
    quantity come with `item_holding`)."""
    del reachable_ids
    total = db.exec(select(func.sum(Ledger.amount)).where(Ledger.entity_id == character.id)).first() or 0
    threshold = req.threshold or 0
    met = total >= threshold
    reason = (
        f"resource {req.target_key!r} balance is {total}, meets requires >= {threshold}" if met
        else f"prerequisite not met — resource {req.target_key!r} balance is {total}, requires >= {threshold}"
    )
    return Verdict(type=req.type, met=met, current=total, required=threshold, reason=reason)


def _eval_location_reachable(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    ids = reachable_ids or frozenset()
    met = req.target_entity_id in ids
    target = db.get(Entity, req.target_entity_id)
    target_name = target.name if target else req.target_entity_id
    reason = (
        f"{target_name} is reachable" if met
        else f"prerequisite not met — {target_name} is not reachable from the current location"
    )
    return Verdict(
        type=req.type, met=met, current=character.current_location_id,
        required=req.target_entity_id, reason=reason,
    )


def _entity_name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else str(entity_id)


def _eval_has_met(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """The character and the target have an encounter row (`rencontre`, one
    row per unordered pair, `entity_lo_id < entity_hi_id`)."""
    del reachable_ids
    low, high = sorted((character.id, req.target_entity_id))
    row = db.exec(
        select(Rencontre).where(Rencontre.entity_lo_id == low, Rencontre.entity_hi_id == high)
    ).first()
    met = row is not None
    name = _entity_name(db, req.target_entity_id)
    reason = f"has met {name}" if met else f"prerequisite not met — has not met {name}"
    return Verdict(
        type=req.type, met=met, current=("met" if met else "not met"), required=req.target_entity_id,
        reason=reason, required_label=name,
    )


def _eval_faction_member(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """The character holds an ACTIVE membership (`left_at IS NULL`) of the
    target faction. A secret membership counts: it is the character's own
    (the `tick_context` self-briefing precedent); secrecy hides it from
    others, not from the gate."""
    del reachable_ids
    row = db.exec(
        select(FactionMembership).where(
            FactionMembership.entity_id == character.id,
            FactionMembership.faction_id == req.target_entity_id,
            FactionMembership.left_at.is_(None),
        )
    ).first()
    met = row is not None
    name = _entity_name(db, req.target_entity_id)
    reason = f"member of {name}" if met else f"prerequisite not met — not a member of {name}"
    return Verdict(
        type=req.type, met=met, current=("member" if met else "not a member"), required=req.target_entity_id,
        reason=reason, required_label=name,
    )


def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """`target_key` is a base domain or a skill definition id; the rank held
    is `skill_access.held_rank` (a missing base row is Initié, a missing
    definition row is not held)."""
    del reachable_ids
    rank = held_rank(db, character.id, req.target_key)
    threshold = req.threshold or 0
    met = rank is not None and rank >= threshold
    label = skill_label(db, req.target_key)
    current = rank if rank is not None else "not held"
    reason = (
        f"skill {label!r} at rank {rank}, meets requires >= {threshold}" if met
        else f"prerequisite not met — skill {label!r} is {current}, requires rank >= {threshold}"
    )
    return Verdict(
        type=req.type, met=met, current=current, required=threshold, reason=reason, required_label=label,
    )


def _eval_quest_state(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """`target_key` is a quest offer id, `value` one of `QUEST_STATES`: met
    iff a quest the character took from that offer is in that state (M1: a
    quest's state is its agenda's). A repeatable offer may have several:
    one is enough."""
    del reachable_ids
    statuses = QUEST_STATE_AGENDA_STATUSES.get(req.value or "", ())
    row = db.exec(
        select(Quest.id)
        .join(Agenda, Agenda.id == Quest.agenda_id)
        .where(
            Quest.character_id == character.id, Quest.offer_id == req.target_key,
            Agenda.status.in_(statuses),
        )
    ).first()
    met = row is not None
    offer = db.get(QuestOffer, req.target_key) if req.target_key else None
    label = offer.title if offer is not None else str(req.target_key)
    reason = (f"quest {label!r} is {req.value}" if met
              else f"prerequisite not met — quest {label!r} is not {req.value}")
    return Verdict(
        type=req.type, met=met, current=(req.value if met else f"not {req.value}"), required=req.target_key,
        reason=reason, required_label=label,
    )


def _eval_item_held(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """`target_entity_id` is an item: met iff the character holds at least
    `threshold` of it (`item_holding`, one row per item and holder; no row
    reads 0)."""
    del reachable_ids
    held = db.exec(select(ItemHolding.quantity).where(
        ItemHolding.item_id == req.target_entity_id, ItemHolding.holder_entity_id == character.id,
    )).first() or 0
    threshold = req.threshold or 0
    met = held >= threshold
    name = _entity_name(db, req.target_entity_id)
    reason = (f"holds {held} {name}, meets requires >= {threshold}" if met
              else f"prerequisite not met — holds {held} {name}, requires >= {threshold}")
    return Verdict(type=req.type, met=met, current=held, required=threshold, reason=reason, required_label=name)


def _attribute_required(db: Session, req: RequirementSpec, view: AttributeView) -> object:
    if view.kind == "choice":
        return req.value
    if view.kind == "integer":
        return req.threshold
    return req.target_entity_id


def _attribute_wanted(db: Session, req: RequirementSpec, view: AttributeView) -> str:
    """What the leaf asks, in French: a label, « N ou plus », an entity's
    name, or « quelqu'un » for an `entity` kind that must only be set."""
    if view.kind == "choice":
        return value_label(db, view, req.value)
    if view.kind == "integer":
        return f"{req.threshold} ou plus"
    return value_label(db, view, req.target_entity_id) if req.target_entity_id else "quelqu'un"


# WH1 (TICKET-0113): why a leaf on a hidden attribute shows `?` to a player,
# even about himself (`conditions.VerdictNode.seen_by`) -- and why it is
# `unknown` when its subject cannot hold it (`attribute_unjudged`): never
# its name, which a player surface would write out (INV-62,
# AMENDMENT-0113-01).
HIDDEN_STATE_REASON_FR = "c'est un état encore caché"


def attribute_unjudged(req: RequirementSpec, holder, db: Session) -> Optional[str]:
    """Why an `attribute` leaf cannot be judged on `holder` (its subject) --
    the attribute is gone, or does not apply to its type -- in French; None
    when it can. `conditions._evaluate_leaf` makes such a leaf `unknown`,
    and every surface writes this reason out: a hidden attribute's is
    `HIDDEN_STATE_REASON_FR`, which names nothing (INV-62)."""
    view = view_of(db, req.target_key)
    entity = db.get(Entity, holder.id)
    if view is None or entity is None:
        return "cet état n'existe plus"
    if not applies_to(view, entity.type):
        if view.hidden:
            return HIDDEN_STATE_REASON_FR
        return f"{entity.name} n'a pas l'état « {view.name} »"
    return None


def _eval_attribute(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """`target_key` names an attribute (a definition id or `sys:<name>`);
    its subject is any entity it applies to (`ANY_SUBJECT_TYPES`). A
    `choice` is met when the state is the leaf's `value`, an `integer` when
    it is at least `threshold`, an `entity` when it is `target_entity_id` --
    or, with no target, when it names anyone. An entity with no value reads
    the default (WC1). The caller checks `attribute_unjudged` first."""
    del reachable_ids
    view = view_of(db, req.target_key)
    entity = db.get(Entity, character.id)
    state = current_value(db, view, entity)
    if view.kind == "choice":
        met = state.raw == req.value
    elif view.kind == "integer":
        met = isinstance(state.raw, int) and state.raw >= (req.threshold or 0)
    else:
        met = state.raw is not None if req.target_entity_id is None else state.raw == req.target_entity_id
    wanted = _attribute_wanted(db, req, view)
    current = state.raw if view.kind == "integer" else state.label
    reason = (f"{entity.name}: {view.name} is {state.label}" if met
              else f"prerequisite not met — {entity.name}: {view.name} is {state.label}, not {wanted}")
    return Verdict(type=req.type, met=met, current=current, required=_attribute_required(db, req, view),
                   reason=reason, required_label=f"{entity.name} — {view.name} : {wanted}", hidden=view.hidden)


def _open_debt(db: Session, debtor_id: str, creditor_id: Optional[str]) -> bool:
    return db.exec(select(Debt.id).where(
        Debt.debtor_entity_id == debtor_id, Debt.creditor_entity_id == creditor_id, Debt.status == "open",
    )).first() is not None


def _eval_has_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """TICKET-0110 (G1): the character owes the target (a character or a
    faction) at least one OPEN debt -- one he is the debtor of; existence
    only, no amount. A settled or forgiven debt is not owed."""
    del reachable_ids
    met = _open_debt(db, character.id, req.target_entity_id)
    name = _entity_name(db, req.target_entity_id)
    reason = f"owes {name}" if met else f"prerequisite not met — owes {name} nothing"
    return Verdict(
        type=req.type, met=met, current=("owes" if met else "owes nothing"), required=req.target_entity_id,
        reason=reason, required_label=name,
    )


def _eval_no_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """TICKET-0110 (G1): the exact negation of `has_debt_to`."""
    del reachable_ids
    owes = _open_debt(db, character.id, req.target_entity_id)
    name = _entity_name(db, req.target_entity_id)
    reason = f"prerequisite not met — still owes {name}" if owes else f"owes {name} nothing"
    return Verdict(
        type=req.type, met=not owes, current=("owes" if owes else "owes nothing"), required=req.target_entity_id,
        reason=reason, required_label=name,
    )


def _places_within(db: Session, place_id: str) -> set[str]:
    """`place_id` and every location under it (`parent_location_id`), its own
    cycle-safe reader: « à Ombreval » counts an event in a house of it."""
    found, frontier = {place_id}, [place_id]
    while frontier:
        children = db.exec(select(Location.id).where(Location.parent_location_id.in_(frontier))).all()
        frontier = [c for c in children if c not in found]
        found.update(frontier)
    return found


def counted_events(db: Session, req: RequirementSpec, subject_id: str, since_at) -> list[tuple]:
    """The (event id, fact id, quantity) an `event` leaf counts for its
    subject: events of the type `target_key` the subject took part in -- in
    the role `value`, or any --, each filter's role filled as it says, at the
    place `target_entity_id` or under it, recorded at or after `since_at`."""
    query = (select(Event.id, Fact.id, Event.quantity).join(Fact, Fact.event_id == Event.id)
             .where(Event.type_id == req.target_key))
    taking_part = select(EventParticipant.event_id).where(EventParticipant.entity_id == subject_id)
    if req.value:
        taking_part = taking_part.where(EventParticipant.role_id == req.value)
    query = query.where(Event.id.in_(taking_part))
    for f in req.filters:
        filled = select(EventParticipant.event_id).where(EventParticipant.role_id == f.role_id)
        filled = filled.where(EventParticipant.entity_id == f.entity_id) if f.entity_id else filled.where(
            EventParticipant.sorte_id == f.sorte_id)
        query = query.where(Event.id.in_(filled))
    if req.target_entity_id:
        query = query.where(Event.location_id.in_(_places_within(db, req.target_entity_id)))
    if since_at is not None:
        query = query.where(Event.recorded_at >= since_at)
    return list(db.exec(query).all())


def evaluate_event(req: RequirementSpec, taker, db: Session, since_at) -> Verdict:
    """TICKET-0114 (G1, F1): met when the counted events add up to
    `threshold` (an event's quantity, 1 when it has none). Its subject
    (`taker`) is any entity -- a faction takes part too. The caller resolves `since_at`
    from the leaf's window (`conditions._evaluate_leaf`)."""
    rows = counted_events(db, req, taker.id, since_at)
    total = sum(quantity or 1 for _event, _fact, quantity in rows)
    need = req.threshold or 1
    event_type = db.get(EventType, req.target_key)
    name = event_type.name if event_type is not None else str(req.target_key)
    entity = db.get(Entity, taker.id)
    who = entity.name if entity is not None else taker.id
    met = total >= need
    reason = (f"{who}: {total} « {name} », meets requires >= {need}" if met
              else f"prerequisite not met — {who}: {total} « {name} », requires >= {need}")
    return Verdict(type=req.type, met=met, current=total, required=need, reason=reason,
                   required_label=f"{name} ({need})", events=tuple((fact, quantity or 1) for _e, fact, quantity in rows))


def _eval_event(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """The table's entry for `event` (no window: every event counts);
    `conditions._evaluate_leaf` calls `evaluate_event` with its window."""
    del reachable_ids
    return evaluate_event(req, character, db, None)


def _eval_is_character(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """The one who acts is the target character (TICKET-0121, E3a): a quest
    offered to one character only."""
    del reachable_ids
    met = character.id == req.target_entity_id
    name = _entity_name(db, req.target_entity_id)
    reason = f"is {name}" if met else f"prerequisite not met — is not {name}"
    return Verdict(
        type=req.type, met=met, current=character.id, required=req.target_entity_id,
        reason=reason, required_label=name,
    )


_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
    "knowledge": _eval_knowledge,
    "relation_gte": _eval_relation_gte,
    "resource": _eval_resource,
    "location_reachable": _eval_location_reachable,
    "has_met": _eval_has_met,
    "faction_member": _eval_faction_member,
    "skill_rank_gte": _eval_skill_rank_gte,
    "quest_state": _eval_quest_state,
    "has_debt_to": _eval_has_debt_to,
    "no_debt_to": _eval_no_debt_to,
    "item_held": _eval_item_held,
    "attribute": _eval_attribute,
    "event": _eval_event,
    "is_character": _eval_is_character,
}


def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:
    """A NEW, day-local `connects_to` BFS reader (decision D1, BRIEF-19) —
    see the module docstring for the escalation this corrects. Unbounded
    (the origin's whole connected component of ACTIVE locations), origin
    INCLUDED, both `connects_to` column orders. Returns bare ids —
    `evaluate_requirements` needs membership only, nothing else."""
    visited: set[str] = {origin_location_id}
    frontier = [origin_location_id]
    while frontier:
        next_frontier: list[str] = []
        for loc_id in frontier:
            rows = db.exec(
                select(Relation).where(
                    Relation.type == "connects_to",
                    (Relation.entity_a_id == loc_id) | (Relation.entity_b_id == loc_id),
                )
            ).all()
            for rel in rows:
                other_id = rel.entity_b_id if rel.entity_a_id == loc_id else rel.entity_a_id
                if other_id in visited:
                    continue
                other = db.get(Entity, other_id)
                if other is None or other.type != "location" or other.status != "active":
                    continue
                visited.add(other_id)
                next_frontier.append(other_id)
        frontier = next_frontier
    return frozenset(visited)


def evaluate_specs(
    requirements: tuple[RequirementSpec, ...], character: Character, db: Session,
) -> list[Verdict]:
    """Judge each requirement against `character`'s current state (C-02).
    Dispatches through `_EVALUATORS`; an unknown `type` raises fail-closed —
    it cannot happen through the DB (the CHECK forbids it), the branch exists
    so that widening `REQUIREMENT_TYPES` without adding an evaluator fails
    loudly. Shared by a step (`evaluate_requirements`) and a quest offer's
    eligibility (`quest_reads`), so both are one judgment.

    `_day_reachable_ids` is computed AT MOST ONCE per call, only if a
    `location_reachable` requirement is present — never per requirement."""
    needs_reachable = any(r.type == "location_reachable" for r in requirements)
    reachable_ids = _day_reachable_ids(character.current_location_id, db) if needs_reachable else None

    verdicts: list[Verdict] = []
    for req in requirements:
        evaluator = _EVALUATORS.get(req.type)
        if evaluator is None:
            raise ValueError(f"unknown requirement type {req.type!r}")
        verdicts.append(evaluator(req, character, db, reachable_ids))
    return verdicts
