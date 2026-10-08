"""A condition in French, for the creator and the player (TICKET-0111,
BRIEF-0111-B, decision T1).

`describe` reads a tree back as indented lines (a connector heads its
children); `verdict_lines` does the same for a judged tree, each line with
its state and, for a form that counts, its progress (« 3/15 »). Both are
read by the surfaces; neither decides anything. Every phrase comes from
`FORM_PHRASES_FR`, one per form, kept equal to `REQUIREMENT_TYPES` by
`conditions.py` CB4.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from .condition_forms import RequirementSpec
from .conditions import ConditionTree, VerdictNode
from .models import Entity, Fact, QuestOffer
from .prose_render import fact_text
from .skill_access import skill_label

# One phrase per form: {who} (the leaf's subject), {target}, {threshold} and
# {value} are filled in; a phrase names only what its form uses.
FORM_PHRASES_FR: dict[str, str] = {
    "knowledge": "{who} connaît « {target} »",
    "relation_gte": "{target} apprécie {who} à {threshold} ou plus",
    "resource": "{who} possède au moins {threshold} en monnaie",
    "location_reachable": "{who} peut atteindre {target}",
    "has_met": "{who} a rencontré {target}",
    "faction_member": "{who} est membre de {target}",
    "skill_rank_gte": "{who} a « {target} » au rang {threshold} ou plus",
    "quest_state": "la quête « {target} » de {who} est {value}",
    "has_debt_to": "{who} a une dette envers {target}",
    "no_debt_to": "{who} n'a aucune dette envers {target}",
    "item_held": "{who} possède au moins {threshold} × « {target} »",
    "vital_status": "{who} est {value}",
}

# The French of a form's value (`condition_forms.FORM_VALUES`), one label per
# value, kept equal to it by `conditions.py` CC.
VALUE_LABELS_FR: dict[str, dict[str, str]] = {
    "vital_status": {"alive": "en vie", "dead": "mort", "missing": "disparu", "unknown": "d'état inconnu"},
    "quest_state": {"open": "en cours", "completed": "accomplie", "failed": "échouée", "abandoned": "abandonnée"},
}

CONNECTOR_HEADS_FR: dict[str, str] = {
    "all": "Toutes ces conditions :",
    "any": "Au moins une de ces conditions :",
    "not": "Pas ceci :",
    "at_least": "Au moins {n} de ces conditions :",
}

SUBJECT_LABELS_FR: dict[str, str] = {"doer": "le personnage", "giver": "le donneur", "contact": "le contact"}

STATE_MARKS: dict[str, str] = {"met": "✓", "unmet": "✗", "unknown": "?"}


def _entity_name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else str(entity_id)


def _target(db: Session, spec: RequirementSpec) -> str:
    if spec.target_entity_id:
        return _entity_name(db, spec.target_entity_id)
    if spec.type == "knowledge":
        fact = db.get(Fact, spec.target_key) if spec.target_key else None
        return fact_text(db, fact) if fact is not None else str(spec.target_key)
    if spec.type == "skill_rank_gte":
        return skill_label(db, spec.target_key)
    if spec.type == "quest_state":
        offer = db.get(QuestOffer, spec.target_key) if spec.target_key else None
        return offer.title if offer is not None else str(spec.target_key)
    return str(spec.target_key or "")


def _subject(db: Session, spec: RequirementSpec) -> str:
    if spec.subject_role is not None:
        return SUBJECT_LABELS_FR.get(spec.subject_role, spec.subject_role)
    return _entity_name(db, spec.subject_entity_id)


def leaf_text(db: Session, spec: RequirementSpec) -> str:
    phrase = FORM_PHRASES_FR.get(spec.type)
    if phrase is None:
        raise ValueError(f"condition_text: unknown requirement type {spec.type!r}")
    value = VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
    text = phrase.format(who=_subject(db, spec), target=_target(db, spec), threshold=spec.threshold, value=value)
    return text[0].upper() + text[1:]


def _head(op: str, n: Optional[int]) -> str:
    return CONNECTOR_HEADS_FR[op].format(n=n)


def describe(db: Session, node: Optional[ConditionTree]) -> list[dict]:
    """The tree as lines: `{"depth", "text"}`, a connector before its
    children. [] for no condition."""
    lines: list[dict] = []
    if node is not None:
        _describe(db, node, 0, lines)
    return lines


def _describe(db: Session, node: ConditionTree, depth: int, lines: list[dict]) -> None:
    if node.op == "leaf":
        lines.append({"depth": depth, "text": leaf_text(db, node.leaf)})
        return
    lines.append({"depth": depth, "text": _head(node.op, node.n)})
    for child in node.children:
        _describe(db, child, depth + 1, lines)


def _progress(verdict_node: VerdictNode) -> Optional[str]:
    verdict = verdict_node.verdict
    if verdict is None:
        return None
    current, required = verdict.current, verdict.required
    if isinstance(current, int) and isinstance(required, int) and not isinstance(current, bool):
        return f"{current}/{required}"
    return None


def verdict_lines(db: Session, verdict: Optional[VerdictNode]) -> list[dict]:
    """A judged tree as lines: `{"depth", "text", "state", "mark",
    "progress"}`; an `unknown` leaf's text ends with why."""
    lines: list[dict] = []
    if verdict is not None:
        _verdict_lines(db, verdict, 0, lines)
    return lines


def _verdict_lines(db: Session, node: VerdictNode, depth: int, lines: list[dict]) -> None:
    if node.op == "leaf":
        text = leaf_text(db, node.spec)
        if node.state == "unknown" and node.reason:
            text = f"{text} ({node.reason})"
        lines.append({"depth": depth, "text": text, "state": node.state, "mark": STATE_MARKS[node.state],
                      "progress": _progress(node)})
        return
    lines.append({"depth": depth, "text": _head(node.op, node.n), "state": node.state,
                  "mark": STATE_MARKS[node.state], "progress": None})
    for child in node.children:
        _verdict_lines(db, child, depth + 1, lines)
