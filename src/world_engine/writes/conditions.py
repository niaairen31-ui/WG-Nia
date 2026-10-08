"""The condition writer and reader (TICKET-0111, BRIEF-0111-C, decisions O-a
and I1): one `condition` row per owner and role, its tree as
`condition_node` rows.

- `clean_leaf(...)`        : one leaf against its form -- the form is known,
  its subject is a role or a character of the world, its target exists in
  the world and is of the right kind, its threshold and value are in
  range. Moved here from `goals_agendas._clean_requirement` (TICKET-0108,
  C-01) and widened to subjects and values.
- `clean_condition(...)`   : a whole tree, shape (`conditions.check_shape`)
  then every leaf; returns the tree as it will be stored.
- `write_condition(...)`   : replace one owner's condition for one role
  whole (no tree: none is kept), after cleaning it. Its reader is
  `conditions.read_condition`.
- `delete_offer_conditions(...)` : every condition of an offer and of its
  steps, before `write_quest_offer` replaces them.

The form vocabulary is a code-plane property (no CHECK names a form): this
module is the one writer of both tables (`single_canon_write.py`), and it
refuses before any row. None of these functions commits.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlmodel import Session

from ..condition_forms import (
    ENTITY_TARGET_TYPES,
    FORM_VALUES,
    NO_TARGET_TYPES,
    REQUIREMENT_TYPES,
    THRESHOLD_TYPES,
    RequirementSpec,
)
from ..conditions import SUBJECT_ROLES, ConditionTree, check_shape, owner_of, stored_condition
from ..models import (
    BASE_SKILL_DOMAINS,
    CONDITION_ROLES,
    Condition,
    ConditionNode,
    Entity,
    Fact,
    QuestOffer,
    SkillDefinition,
)

# The entity type each entity-targeted form must name (TICKET-0108, C-01);
# `None` accepts any entity of the world -- the two model-emitted forms keep
# the check they always had, so a day plan is refused for nothing new.
_TARGET_ENTITY_TYPE: dict[str, Optional[tuple[str, ...]]] = {
    "relation_gte": None, "location_reachable": None, "has_met": None, "faction_member": ("faction",),
    # TICKET-0110 (G1): a debt's creditor, a character or a faction (J1).
    "has_debt_to": ("character", "faction"), "no_debt_to": ("character", "faction"),
    # TICKET-0111 (S1): an item held in quantity (`item_holding`).
    "item_held": ("item",),
}


def _clean_target_key(db: Session, world_id: str, req: RequirementSpec) -> Optional[str]:
    """The error for a key-targeted form whose key names nothing in
    `world_id`, or None. `resource`'s key is a label (one currency per
    world), never resolved."""
    if req.type == "knowledge":
        fact = db.get(Fact, req.target_key)
        return None if fact is not None and fact.world_id == world_id else f"unknown fact {req.target_key!r}"
    if req.type == "skill_rank_gte":
        if req.target_key in BASE_SKILL_DOMAINS:
            return None
        definition = db.get(SkillDefinition, req.target_key)
        ok = definition is not None and definition.world_id == world_id
        return None if ok else f"unknown skill {req.target_key!r}"
    if req.type == "quest_state":
        offer = db.get(QuestOffer, req.target_key)
        return None if offer is not None and offer.world_id == world_id else f"unknown quest offer {req.target_key!r}"
    return None


def _clean_subject(db: Session, world_id: str, where: str, req: RequirementSpec) -> None:
    if (req.subject_role is None) == (req.subject_entity_id is None):
        raise ValueError(f"{where}requirement type {req.type!r} names exactly one subject: a role or an entity")
    if req.subject_role is not None:
        if req.subject_role not in SUBJECT_ROLES:
            raise ValueError(f"{where}unknown subject role {req.subject_role!r}")
        return
    subject = db.get(Entity, req.subject_entity_id)
    if subject is None or subject.world_id != world_id or subject.type != "character":
        raise ValueError(f"{where}subject {req.subject_entity_id!r} is not a character of this world")


def _clean_target(db: Session, world_id: str, where: str, req: RequirementSpec) -> tuple[Optional[str], Optional[str]]:
    if req.type in NO_TARGET_TYPES:
        if req.target_entity_id or req.target_key:
            raise ValueError(f"{where}requirement type {req.type!r} judges its subject alone and takes no target")
        return None, None
    if req.type in ENTITY_TARGET_TYPES:
        if not req.target_entity_id:
            raise ValueError(f"{where}requirement type {req.type!r} needs a target_entity_id")
        target = db.get(Entity, req.target_entity_id)
        wanted = _TARGET_ENTITY_TYPE[req.type]
        if target is None or target.world_id != world_id or (wanted is not None and target.type not in wanted):
            raise ValueError(f"{where}unknown target entity {req.target_entity_id!r}")
        return req.target_entity_id, None
    if not req.target_key:
        raise ValueError(f"{where}requirement type {req.type!r} needs a target_key")
    error = _clean_target_key(db, world_id, req)
    if error is not None:
        raise ValueError(f"{where}requirement type {req.type!r}: {error}")
    return None, req.target_key


def _clean_threshold(where: str, req: RequirementSpec) -> Optional[int]:
    if req.type not in THRESHOLD_TYPES:
        return None
    threshold, top = req.threshold, (5 if req.type == "skill_rank_gte" else None)
    if (not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1
            or (top is not None and threshold > top)):
        raise ValueError(
            f"{where}requirement type {req.type!r} needs a positive integer threshold"
            + (f" of at most {top}" if top is not None else "")
        )
    return threshold


def _clean_value(where: str, req: RequirementSpec) -> Optional[str]:
    allowed = FORM_VALUES.get(req.type)
    if allowed is None:
        return None
    if req.value not in allowed:
        raise ValueError(f"{where}requirement type {req.type!r} needs a value among {allowed}, got {req.value!r}")
    return req.value


def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "") -> RequirementSpec:
    """One leaf as it will be stored: the arguments its form uses, nothing
    else. `where` prefixes every error (« write_day_plan: step 2 »).
    Raises `ValueError` on any violation."""
    if req.type not in REQUIREMENT_TYPES:
        raise ValueError(f"{where}unknown requirement type {req.type!r}")
    _clean_subject(db, world_id, where, req)
    target_entity_id, target_key = _clean_target(db, world_id, where, req)
    return RequirementSpec(
        type=req.type, subject_role=req.subject_role, subject_entity_id=req.subject_entity_id,
        target_entity_id=target_entity_id, target_key=target_key,
        threshold=_clean_threshold(where, req), value=_clean_value(where, req),
    )


def clean_condition(
    db: Session, world_id: str, tree: Optional[ConditionTree], where: str = "",
) -> Optional[ConditionTree]:
    """A whole tree, shape first then every leaf, before any write. None is
    no condition. Raises `ValueError` (a `ConditionShapeError` is one)."""
    if tree is None:
        return None
    try:
        check_shape(tree)
    except ValueError as exc:
        raise ValueError(f"{where}{exc}") from exc
    return _clean_tree(db, world_id, tree, where)


def _clean_tree(db: Session, world_id: str, tree: ConditionTree, where: str) -> ConditionTree:
    if tree.op == "leaf":
        return ConditionTree(op="leaf", leaf=clean_leaf(db, world_id, tree.leaf, where))
    return ConditionTree(op=tree.op, n=tree.n, children=tuple(_clean_tree(db, world_id, c, where) for c in tree.children))


def write_condition(db: Session, *, world_id: str, role: str, tree: Optional[ConditionTree], **owner) -> Optional[Condition]:
    """Replace the condition `role` of one owner (`quest_offer_id=`,
    `quest_offer_step_id=` or `agenda_step_id=`) whole: the tree is cleaned,
    the previous condition and its nodes removed, the new one written. No
    tree: none is kept. Returns the new `condition` row, or None."""
    column, owner_id = owner_of(owner)
    if role not in CONDITION_ROLES or (column == "quest_offer_id") != (role == "eligibility"):
        raise ValueError(f"a {column} owner cannot hold a {role!r} condition")
    clean = clean_condition(db, world_id, tree)
    previous = stored_condition(db, role, column, owner_id)
    if previous is not None:
        db.execute(text("DELETE FROM condition_node WHERE condition_id = :cid"), {"cid": previous.id})
        db.execute(text("DELETE FROM condition WHERE id = :cid"), {"cid": previous.id})
        db.expunge(previous)
    if clean is None:
        return None
    condition = Condition(world_id=world_id, role=role, **{column: owner_id})
    db.add(condition)
    db.flush()
    _write_node(db, world_id, condition.id, clean, None, 0)
    return condition


def _write_node(db: Session, world_id: str, condition_id: str, tree: ConditionTree,
                parent_id: Optional[str], position: int) -> None:
    spec = tree.leaf
    row = ConditionNode(
        world_id=world_id, condition_id=condition_id, parent_id=parent_id, position=position, op=tree.op,
        n=tree.n if tree.op == "at_least" else None,
        form=spec.type if spec else None,
        subject_role=spec.subject_role if spec else None,
        subject_entity_id=spec.subject_entity_id if spec else None,
        target_entity_id=spec.target_entity_id if spec else None,
        target_key=spec.target_key if spec else None,
        threshold=spec.threshold if spec else None,
        value=spec.value if spec else None,
    )
    db.add(row)
    db.flush()
    for index, child in enumerate(tree.children):
        _write_node(db, world_id, condition_id, child, row.id, index)


def delete_offer_conditions(db: Session, offer_id: str) -> None:
    """Every condition of an offer -- its eligibility and its steps' -- with
    their nodes: `write_quest_offer` replaces them whole (its full-replace
    shape, TICKET-0108)."""
    owned = ("SELECT id FROM condition WHERE quest_offer_id = :oid OR quest_offer_step_id IN "
             "(SELECT id FROM quest_offer_step WHERE offer_id = :oid)")
    db.execute(text(f"DELETE FROM condition_node WHERE condition_id IN ({owned})"), {"oid": offer_id})
    db.execute(text(f"DELETE FROM condition WHERE id IN ({owned})"), {"oid": offer_id})
