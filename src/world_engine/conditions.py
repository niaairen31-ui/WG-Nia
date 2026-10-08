"""The condition language (TICKET-0111, BRIEF-0111-B, decisions A1, I1, P1,
R1 and S1 of the series).

A condition is a tree. Its leaves are the requirement forms of
`condition_forms.py` (a `RequirementSpec` each); its inner nodes are four
connectors: `all`, `any`, `not` (exactly one child) and `at_least` (`n` of
its children). The vocabulary grows by adding forms, never by adding
connectors.

Every leaf names its SUBJECT (P1): a role bound when the condition is
evaluated -- `doer`, the character who acts (the player for a quest or a day
plan), `giver`, the offer's giver, `contact`, a faction giver's contact --
or one fixed entity (`subject_entity_id`). A form judges a character; a
subject that is not one, or a role nothing binds, makes the leaf
`unknown`, never `met`.

A verdict has three states (R1): `met`, `unmet`, `unknown`. The connectors
follow Kleene's three-valued logic, so an `unknown` leaf can still be
outweighed (`any` with a met sibling is met). A gate passes only on `met`.

This module writes nothing: it reads the canon through the evaluators and
reads a stored tree back (`read_condition`). Its writer is
`writes/conditions.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .condition_forms import _EVALUATORS, RequirementSpec, Verdict, _day_reachable_ids
from .models import Character, Condition, ConditionNode, Entity

# The four connectors, then the leaf.
CONNECTORS: tuple[str, ...] = ("all", "any", "not", "at_least")
NODE_OPS: tuple[str, ...] = CONNECTORS + ("leaf",)

# P1: the roles a leaf's subject may name, bound at evaluation.
SUBJECT_ROLES: tuple[str, ...] = ("doer", "giver", "contact")

# R1: a verdict's three states.
VERDICT_STATES: tuple[str, ...] = ("met", "unmet", "unknown")

# Bounds on a tree, so a condition stays readable and cheap to judge.
MAX_DEPTH = 6
MAX_NODES = 60


class ConditionShapeError(ValueError):
    """A tree that breaks the language's shape (an unknown connector, a
    `not` with two children, an `at_least` asking for more than it has...).
    Its message is the reason, in English, for the creator's 422."""


@dataclass(frozen=True)
class ConditionTree:
    """A condition, or any of its subtrees: a connector with its children,
    or a leaf carrying one form. (The stored rows are `models.ConditionNode`.)"""
    op: str
    children: tuple["ConditionTree", ...] = ()
    n: Optional[int] = None
    leaf: Optional[RequirementSpec] = None


@dataclass(frozen=True)
class Bindings:
    """What the roles name when a condition is judged (P1)."""
    doer: Character
    giver_id: Optional[str] = None
    contact_id: Optional[str] = None


@dataclass(frozen=True)
class VerdictNode:
    state: str
    op: str
    children: tuple["VerdictNode", ...] = ()
    n: Optional[int] = None
    spec: Optional[RequirementSpec] = None
    verdict: Optional[Verdict] = None
    reason: Optional[str] = None  # why a leaf is `unknown`, in French

    @property
    def met(self) -> bool:
        return self.state == "met"

    def leaf_nodes(self) -> tuple["VerdictNode", ...]:
        if self.op == "leaf":
            return (self,)
        return tuple(leaf for child in self.children for leaf in child.leaf_nodes())

    def leaf_verdicts(self) -> tuple[Verdict, ...]:
        """The verdicts of the leaves that were judged, in order; an
        `unknown` leaf has none."""
        return tuple(node.verdict for node in self.leaf_nodes() if node.verdict is not None)


# --- building ------------------------------------------------------------------

def leaf(spec: RequirementSpec) -> ConditionTree:
    return ConditionTree(op="leaf", leaf=spec)


def all_of(specs) -> Optional[ConditionTree]:
    """A flat list as a tree: `all` of its leaves, or None when it is empty
    (no condition)."""
    specs = tuple(specs)
    if not specs:
        return None
    return ConditionTree(op="all", children=tuple(leaf(s) for s in specs))


def leaves(node: Optional[ConditionTree]) -> tuple[RequirementSpec, ...]:
    """Every leaf, in order (depth first)."""
    if node is None:
        return ()
    if node.op == "leaf":
        return (node.leaf,)
    return tuple(spec for child in node.children for spec in leaves(child))


def and_path_leaves(node: Optional[ConditionTree]) -> tuple[RequirementSpec, ...]:
    """The leaves the condition cannot be met without: those reached from
    the root through `all` nodes only (Q1). A leaf under `any`, `not` or
    `at_least` is not guaranteed and is left out."""
    if node is None:
        return ()
    if node.op == "leaf":
        return (node.leaf,)
    if node.op != "all":
        return ()
    return tuple(spec for child in node.children for spec in and_path_leaves(child))


def flat_leaves(node: Optional[ConditionTree]) -> Optional[tuple[RequirementSpec, ...]]:
    """The leaves of a FLAT condition -- none, one leaf, or `all` of leaves --
    or None when the tree is not flat (T1: only a flat condition is edited
    as a list)."""
    if node is None:
        return ()
    if node.op == "leaf":
        return (node.leaf,)
    if node.op == "all" and all(child.op == "leaf" for child in node.children):
        return tuple(child.leaf for child in node.children)
    return None


def map_leaves(tree: Optional[ConditionTree], fn) -> Optional[ConditionTree]:
    """The same tree with `fn(spec) -> spec` applied to every leaf."""
    if tree is None:
        return None
    if tree.op == "leaf":
        return ConditionTree(op="leaf", leaf=fn(tree.leaf))
    return ConditionTree(op=tree.op, n=tree.n, children=tuple(map_leaves(c, fn) for c in tree.children))


def drop_leaves(tree: Optional[ConditionTree], drop) -> Optional[ConditionTree]:
    """The tree without the leaves `drop(spec)` is true for. A connector left
    with no child goes too; an `at_least` keeps `n` at most its remaining
    children; no tree is left when the root goes."""
    if tree is None:
        return None
    if tree.op == "leaf":
        return None if drop(tree.leaf) else tree
    children = tuple(kept for kept in (drop_leaves(c, drop) for c in tree.children) if kept is not None)
    if not children:
        return None
    n = min(tree.n, len(children)) if tree.op == "at_least" else None
    return ConditionTree(op=tree.op, n=n, children=children)

# --- the dict form (what the API carries) --------------------------------------

_LEAF_KEYS = ("type", "subject_role", "subject_entity_id", "target_entity_id", "target_key", "threshold", "value")


def node_to_dict(node: Optional[ConditionTree]) -> Optional[dict]:
    if node is None:
        return None
    if node.op == "leaf":
        spec = node.leaf
        return {"op": "leaf", **{key: getattr(spec, key) for key in _LEAF_KEYS}}
    out: dict = {"op": node.op, "children": [node_to_dict(child) for child in node.children]}
    if node.op == "at_least":
        out["n"] = node.n
    return out


def _blank(value):
    return None if value == "" else value


def node_from_dict(raw: object) -> Optional[ConditionTree]:
    """A request's tree, shape-checked (`check_shape`). None (or no body)
    is no condition. Raises `ConditionShapeError`."""
    if raw is None:
        return None
    node = _from_dict(raw)
    check_shape(node)
    return node


def _from_dict(raw: object) -> ConditionTree:
    if not isinstance(raw, dict):
        raise ConditionShapeError(f"a condition node must be an object, got {raw!r}")
    op = raw.get("op")
    if op == "leaf":
        threshold = raw.get("threshold")
        if threshold is not None and (not isinstance(threshold, int) or isinstance(threshold, bool)):
            raise ConditionShapeError(f"a leaf's threshold must be an integer, got {threshold!r}")
        subject_entity_id = _blank(raw.get("subject_entity_id"))
        subject_role = _blank(raw.get("subject_role"))
        if subject_role is None and subject_entity_id is None:
            subject_role = "doer"  # a leaf that names no subject judges the one who acts
        spec = RequirementSpec(
            type=raw.get("type"),
            subject_role=subject_role,
            subject_entity_id=subject_entity_id,
            target_entity_id=_blank(raw.get("target_entity_id")),
            target_key=_blank(raw.get("target_key")),
            threshold=threshold,
            value=_blank(raw.get("value")),
        )
        return ConditionTree(op="leaf", leaf=spec)
    if op not in CONNECTORS:
        raise ConditionShapeError(f"unknown condition connector {op!r}")
    children = raw.get("children")
    if not isinstance(children, list):
        raise ConditionShapeError(f"a {op!r} node needs a list of children")
    n = raw.get("n") if op == "at_least" else None
    return ConditionTree(op=op, children=tuple(_from_dict(child) for child in children), n=n)


# --- shape ---------------------------------------------------------------------

def check_shape(node: ConditionTree) -> None:
    """The language's shape, form-blind: connectors and their arity, a
    leaf's subject (one role or one entity, never both), depth and size.
    Whether a FORM is known and its target exists is the writer's check
    (`writes.conditions.clean_condition`). Raises `ConditionShapeError`."""
    count = _check_node(node, depth=1)
    if count > MAX_NODES:
        raise ConditionShapeError(f"a condition has at most {MAX_NODES} nodes, got {count}")


def _check_node(node: ConditionTree, depth: int) -> int:
    if depth > MAX_DEPTH:
        raise ConditionShapeError(f"a condition is at most {MAX_DEPTH} levels deep")
    if node.op == "leaf":
        if node.leaf is None or node.children:
            raise ConditionShapeError("a leaf carries a form and no children")
        spec = node.leaf
        if (spec.subject_role is None) == (spec.subject_entity_id is None):
            raise ConditionShapeError("a leaf names exactly one subject: a role or an entity")
        if spec.subject_role is not None and spec.subject_role not in SUBJECT_ROLES:
            raise ConditionShapeError(f"unknown subject role {spec.subject_role!r}")
        return 1
    if node.op not in CONNECTORS or node.leaf is not None:
        raise ConditionShapeError(f"unknown condition connector {node.op!r}")
    if not node.children:
        raise ConditionShapeError(f"a {node.op!r} node needs at least one child")
    if node.op == "not" and len(node.children) != 1:
        raise ConditionShapeError("a 'not' node has exactly one child")
    if node.op == "at_least":
        n = node.n
        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= len(node.children):
            raise ConditionShapeError(f"'at_least' needs n between 1 and its {len(node.children)} children, got {n!r}")
    elif node.n is not None:
        raise ConditionShapeError(f"only 'at_least' carries n, not {node.op!r}")
    return 1 + sum(_check_node(child, depth + 1) for child in node.children)


# --- evaluation ----------------------------------------------------------------

def evaluate(node: Optional[ConditionTree], bindings: Bindings, db: Session) -> Optional[VerdictNode]:
    """Judge `node` against the canon (R1). None for no condition -- the
    caller treats it as met. Each subject's reachable set is computed at
    most once, and only for a `location_reachable` leaf."""
    if node is None:
        return None
    return _evaluate(node, bindings, db, {})


def _evaluate(node: ConditionTree, bindings: Bindings, db: Session, reachable: dict) -> VerdictNode:
    if node.op == "leaf":
        return _evaluate_leaf(node.leaf, bindings, db, reachable)
    children = tuple(_evaluate(child, bindings, db, reachable) for child in node.children)
    return VerdictNode(state=_combine(node, children), op=node.op, children=children, n=node.n)


def _combine(node: ConditionTree, children: tuple[VerdictNode, ...]) -> str:
    met = sum(1 for c in children if c.state == "met")
    unknown = sum(1 for c in children if c.state == "unknown")
    total = len(children)
    if node.op == "not":
        return {"met": "unmet", "unmet": "met"}.get(children[0].state, "unknown")
    need = {"all": total, "any": 1, "at_least": node.n}[node.op]
    if met >= need:
        return "met"
    if met + unknown < need:
        return "unmet"
    return "unknown"


_ROLE_LABELS_FR = {"giver": "le donneur", "contact": "le contact"}


def _subject(spec: RequirementSpec, bindings: Bindings, db: Session) -> tuple[Optional[Character], Optional[str]]:
    """The character a leaf judges, or None and why (in French)."""
    if spec.subject_role == "doer":
        return bindings.doer, None
    if spec.subject_role is not None:
        entity_id = bindings.giver_id if spec.subject_role == "giver" else bindings.contact_id
        label = _ROLE_LABELS_FR[spec.subject_role]
        if entity_id is None:
            return None, f"{label} n'est pas défini ici"
    else:
        entity_id = spec.subject_entity_id
        entity = db.get(Entity, entity_id)
        label = entity.name if entity is not None else "le sujet"
    character = db.get(Character, entity_id)
    if character is None:
        return None, f"{label} n'est pas un personnage"
    return character, None


def _evaluate_leaf(spec: RequirementSpec, bindings: Bindings, db: Session, reachable: dict) -> VerdictNode:
    evaluator = _EVALUATORS.get(spec.type)
    if evaluator is None:
        raise ValueError(f"unknown requirement type {spec.type!r}")
    character, why = _subject(spec, bindings, db)
    if character is None:
        return VerdictNode(state="unknown", op="leaf", spec=spec, reason=why)
    ids = None
    if spec.type == "location_reachable":
        if character.id not in reachable:
            reachable[character.id] = _day_reachable_ids(character.current_location_id, db)
        ids = reachable[character.id]
    verdict = evaluator(spec, character, db, ids)
    return VerdictNode(state="met" if verdict.met else "unmet", op="leaf", spec=spec, verdict=verdict)


# --- reading a stored tree -----------------------------------------------------

# The three owners a `condition` row may have (TICKET-0111, BRIEF-0111-C).
OWNER_COLUMNS: tuple[str, ...] = ("quest_offer_id", "quest_offer_step_id", "agenda_step_id")


def owner_of(owner: dict) -> tuple[str, str]:
    given = [(column, value) for column, value in owner.items() if column in OWNER_COLUMNS and value]
    if len(given) != 1 or set(owner) - set(OWNER_COLUMNS):
        raise ValueError(f"a condition has exactly one owner among {OWNER_COLUMNS}, got {owner}")
    return given[0]


def stored_condition(db: Session, role: str, column: str, owner_id: str) -> Optional[Condition]:
    return db.exec(select(Condition).where(getattr(Condition, column) == owner_id, Condition.role == role)).first()


def read_condition(db: Session, *, role: str, **owner) -> Optional[ConditionTree]:
    """The stored tree of one owner for one role, or None."""
    column, owner_id = owner_of(owner)
    condition = stored_condition(db, role, column, owner_id)
    if condition is None:
        return None
    nodes = db.exec(select(ConditionNode).where(ConditionNode.condition_id == condition.id)).all()
    children: dict[Optional[str], list[ConditionNode]] = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node)
    roots = children.get(None, [])
    if len(roots) != 1:
        raise ValueError(f"condition {condition.id!r} has {len(roots)} roots")
    return _build(roots[0], children)


def _build(node: ConditionNode, children: dict) -> ConditionTree:
    if node.op == "leaf":
        return ConditionTree(op="leaf", leaf=RequirementSpec(
            type=node.form, subject_role=node.subject_role, subject_entity_id=node.subject_entity_id,
            target_entity_id=node.target_entity_id, target_key=node.target_key, threshold=node.threshold,
            value=node.value,
        ))
    kids = sorted(children.get(node.id, []), key=lambda n: n.position)
    return ConditionTree(op=node.op, n=node.n, children=tuple(_build(k, children) for k in kids))
