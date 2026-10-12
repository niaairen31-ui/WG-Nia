"""A condition in French, for the creator and the player (TICKET-0111,
BRIEF-0111-B, decision T1).

`describe` reads a tree back as indented lines (a connector heads its
children); `verdict_lines` does the same for a judged tree, each line with
its state and, for a form that counts, its progress (« 3/15 »). Both are
read by the surfaces; neither decides anything. Every phrase comes from
`FORM_PHRASES_FR`, one per form, kept equal to `REQUIREMENT_TYPES` by
`conditions.py` CB4.

A player surface passes its character as `viewer_id` (AMENDMENT-0111-01):
a fact he does not know is never written out (A1, `HIDDEN_FACT_FR`), nor a
hidden attribute (WH1 of TICKET-0113, `HIDDEN_STATE_FR`), a leaf about
someone else shows `?` (V2, `VerdictNode.seen_by`), and no line counts
another's regard toward him. The creator reads every line whole.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from .attributes import ATTRIBUTE_FORM, value_label, view_of
from .condition_forms import RequirementSpec
from .conditions import ConditionTree, VerdictNode, known_event_facts
from .knowledge_resolve import resolve_knowledge_level
from .models import Entity, EventSorte, EventType, EventTypeRole, Fact, QuestOffer
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
    "attribute": "{who} — {target} : {value}",
    # TICKET-0114 (G1): what happened, counted; `_event_text` adds its
    # filters, its place and its window.
    "event": "{who} a vécu « {target} » {value}, au moins {threshold} fois",
}

# F1 (TICKET-0114): an `event` leaf's window, in French.
SINCE_LABELS_FR: dict[str, str] = {
    "always": "", "quest": "depuis l'acceptation de la quête", "step": "depuis le début de l'étape",
}

# The French of a form's value (`condition_forms.FORM_VALUES`), one label per
# value, kept equal to it by `conditions.py` CC.
VALUE_LABELS_FR: dict[str, dict[str, str]] = {
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

# A1 (AMENDMENT-0111-01): what a player reads in place of a fact his
# character does not know -- a secret, the creator's note, or simply a fact
# still to learn.
HIDDEN_FACT_FR = "{who} connaît un fait encore caché"

# WH1 (TICKET-0113): what a player reads in place of a leaf on a hidden
# attribute -- its name and its value are never written out.
HIDDEN_STATE_FR = "{who} est dans un état encore caché"

# Forms whose progress a player never sees: the count is another's regard.
HIDDEN_PROGRESS_FORMS: tuple[str, ...] = ("relation_gte",)


def known_to(db: Session, viewer_id: str, fact_id: Optional[str]) -> bool:
    """A1: the viewer resolves the fact above `unaware` (stored row, scope
    defaults and contacts, `knowledge_resolve`)."""
    return bool(fact_id) and resolve_knowledge_level(db, viewer_id, fact_id) != "unaware"


def _entity_name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else str(entity_id)


def _view(db: Session, key: Optional[str], unsaved: Optional[dict]):
    """The attribute `key` names -- an unsaved one the interpreter proposed
    (TICKET-0113, BRIEF-0113-E), else a stored one."""
    return (unsaved or {}).get(key) or view_of(db, key)


def _target(db: Session, spec: RequirementSpec, unsaved: Optional[dict] = None) -> str:
    if spec.target_entity_id and spec.type != ATTRIBUTE_FORM:
        return _entity_name(db, spec.target_entity_id)
    if spec.type == "knowledge":
        fact = db.get(Fact, spec.target_key) if spec.target_key else None
        return fact_text(db, fact) if fact is not None else str(spec.target_key)
    if spec.type == "skill_rank_gte":
        return skill_label(db, spec.target_key)
    if spec.type == "quest_state":
        offer = db.get(QuestOffer, spec.target_key) if spec.target_key else None
        return offer.title if offer is not None else str(spec.target_key)
    if spec.type == ATTRIBUTE_FORM:
        view = _view(db, spec.target_key, unsaved)
        return view.name if view is not None else str(spec.target_key)
    if spec.type == "event":
        event_type = db.get(EventType, spec.target_key) if spec.target_key else None
        return event_type.name if event_type is not None else str(spec.target_key)
    return str(spec.target_key or "")


def _subject(db: Session, spec: RequirementSpec) -> str:
    if spec.subject_role is not None:
        return SUBJECT_LABELS_FR.get(spec.subject_role, spec.subject_role)
    return _entity_name(db, spec.subject_entity_id)


def leaf_text(db: Session, spec: RequirementSpec, viewer_id: Optional[str] = None,
              unsaved: Optional[dict] = None) -> str:
    """One leaf in French. With `viewer_id` (a player surface), a fact the
    viewer does not know is not written out (A1)."""
    phrase = FORM_PHRASES_FR.get(spec.type)
    if phrase is None:
        raise ValueError(f"condition_text: unknown requirement type {spec.type!r}")
    if spec.type == "knowledge" and viewer_id is not None and not known_to(db, viewer_id, spec.target_key):
        phrase = HIDDEN_FACT_FR
    if spec.type == ATTRIBUTE_FORM and viewer_id is not None and _hidden(db, spec):
        phrase = HIDDEN_STATE_FR
    value = _value(db, spec, unsaved)
    text = phrase.format(who=_subject(db, spec), target=_target(db, spec, unsaved), threshold=spec.threshold,
                         value=value)
    if spec.type == "event":
        text += _event_details(db, spec)
    return text[0].upper() + text[1:]


def _role_name(db: Session, role_id: Optional[str]) -> str:
    role = db.get(EventTypeRole, role_id) if role_id else None
    return role.name if role is not None else str(role_id)


def _event_details(db: Session, spec: RequirementSpec) -> str:
    """An `event` leaf's filters (« victime : loup »), place and window."""
    parts = []
    for f in spec.filters:
        sorte = db.get(EventSorte, f.sorte_id) if f.sorte_id else None
        parts.append(f"{_role_name(db, f.role_id)} : {sorte.name if sorte else _entity_name(db, f.entity_id)}")
    if spec.target_entity_id:
        parts.append(f"à {_entity_name(db, spec.target_entity_id)} ou dedans")
    since = SINCE_LABELS_FR.get(spec.since or "always", "")
    if since:
        parts.append(since)
    return (" (" + ", ".join(parts) + ")") if parts else ""


def _hidden(db: Session, spec: RequirementSpec) -> bool:
    view = view_of(db, spec.target_key)
    return view is None or view.hidden


def _value(db: Session, spec: RequirementSpec, unsaved: Optional[dict] = None) -> object:
    """The French of what a leaf compares to: a form's value label, or an
    attribute's label, « N ou plus », an entity or « quelqu'un »."""
    if spec.type == "event":
        return f"comme {_role_name(db, spec.value)}" if spec.value else "à un titre ou un autre"
    if spec.type != ATTRIBUTE_FORM:
        return VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
    view = _view(db, spec.target_key, unsaved)
    if view is None:
        return spec.value or spec.threshold or ""
    if view.kind == "choice":
        return value_label(db, view, spec.value)
    if view.kind == "integer":
        return f"{spec.threshold} ou plus"
    return value_label(db, view, spec.target_entity_id) if spec.target_entity_id else "quelqu'un"


def _head(op: str, n: Optional[int]) -> str:
    return CONNECTOR_HEADS_FR[op].format(n=n)


def describe(db: Session, node: Optional[ConditionTree], unsaved: Optional[dict] = None) -> list[dict]:
    """The tree as lines: `{"depth", "text"}`, a connector before its
    children. [] for no condition. `unsaved`: the attributes the
    interpreter proposed, by their `new:` key (BRIEF-0113-E)."""
    lines: list[dict] = []
    if node is not None:
        _describe(db, node, 0, lines, unsaved)
    return lines


def _describe(db: Session, node: ConditionTree, depth: int, lines: list[dict], unsaved: Optional[dict]) -> None:
    if node.op == "leaf":
        lines.append({"depth": depth, "text": leaf_text(db, node.leaf, unsaved=unsaved)})
        return
    lines.append({"depth": depth, "text": _head(node.op, node.n)})
    for child in node.children:
        _describe(db, child, depth + 1, lines, unsaved)


def _progress(verdict_node: VerdictNode, viewer_id: Optional[str] = None) -> Optional[str]:
    verdict = verdict_node.verdict
    if verdict is None or (viewer_id is not None and verdict.type in HIDDEN_PROGRESS_FORMS):
        return None
    current, required = verdict.current, verdict.required
    if isinstance(current, int) and isinstance(required, int) and not isinstance(current, bool):
        return f"{current}/{required}"
    return None


def verdict_lines(db: Session, verdict: Optional[VerdictNode], viewer_id: Optional[str] = None) -> list[dict]:
    """A judged tree as lines: `{"depth", "text", "state", "mark",
    "progress"}`; an `unknown` leaf's text ends with why. With `viewer_id`
    (a player surface), the verdict is first `seen_by` him (V2) and every
    leaf is written as he may read it (A1)."""
    lines: list[dict] = []
    if verdict is not None:
        seen = verdict.seen_by(viewer_id, known_event_facts(db, verdict, viewer_id)) \
            if viewer_id is not None else verdict
        _verdict_lines(db, seen, 0, lines, viewer_id)
    return lines


def _verdict_lines(db: Session, node: VerdictNode, depth: int, lines: list[dict], viewer_id: Optional[str]) -> None:
    if node.op == "leaf":
        text = leaf_text(db, node.spec, viewer_id)
        if node.state == "unknown" and node.reason:
            text = f"{text} ({node.reason})"
        lines.append({"depth": depth, "text": text, "state": node.state, "mark": STATE_MARKS[node.state],
                      "progress": _progress(node, viewer_id)})
        return
    lines.append({"depth": depth, "text": _head(node.op, node.n), "state": node.state,
                  "mark": STATE_MARKS[node.state], "progress": None})
    for child in node.children:
        _verdict_lines(db, child, depth + 1, lines, viewer_id)
