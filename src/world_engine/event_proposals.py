"""The event types and sortes a model proposes (TICKET-0114, BRIEF-0114-G;
decisions R1 and I2 of the conditions series).

When a sentence -- the creator's, to the condition interpreter; or a
scene's, to Play's analyzer (BRIEF-0114-H) -- speaks of an event no type of
the world says, or of a sorte the world lacks, the model proposes it in its
answer's `define_events` / `define_sortes` blocks and names it by its ref.
Code reads each proposal here, cleaned by the writer's own rules
(`writes.event_types.clean_event_type`, `clean_sorte_name`), refs renamed
`v1`, `v2`, … (types) and `o1`, … (sortes), each with the world's near names
(the creator picks one or creates; the tool never picks). A proposal whose
name IS one the world has is no proposal: it names that type or sorte.

Nothing is written here. The creator creates a proposal from its card
through the vocabulary's own routes (`routes/event_types.py`), or picks a
near one; her pick binds the ref to that id (`bind_vocabulary`), and only
then are the leaf's role names read against the type she chose.

- `read_vocabulary(...)`  : the two blocks -> proposals, the model's refs
  mapped, the errors.
- `bind_vocabulary(...)`  : a pending tree with each ref replaced by the
  id the creator picked, its role names resolved.
- `vocab_waiting(leaf)`   : a leaf still names a proposal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlmodel import Session

from .event_vocab import (
    EventTypeView,
    near_event_types,
    near_sortes,
    type_view,
    world_event_types,
    world_sortes,
)
from .lore_resolve import normalize_surface
from .models import EVENT_DOMAINS, EventSorte
from .writes.event_types import EventTypeSpec, RoleSpec, clean_event_type, clean_sorte_name

TYPE_PREFIX, SORTE_PREFIX = "v", "o"


@dataclass
class Vocabulary:
    """What `read_vocabulary` read: `proposals` (`{ref, kind, definition,
    near}`, kind `type` or `sorte`), `refs` the model's ref -> `("id", id)`
    for a name the world has, or `("ref", our ref)`; `errors`."""

    proposals: list[dict] = field(default_factory=list)
    refs: dict[str, tuple[str, str]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def target(self, model_ref: Any) -> Optional[tuple[str, str]]:
        return self.refs.get(str(model_ref))


def type_spec(raw: dict) -> EventTypeSpec:
    """A type in the model's form -> the writer's spec. An unknown domain
    reads as `other`: the creator retouches it in the card."""
    roles = tuple(RoleSpec(name=str(r.get("name") or ""), entity_types=tuple(r.get("for") or ()),
                           accepts_sorte=bool(r.get("sorte"))) for r in raw.get("roles") or [] if isinstance(r, dict))
    domain = raw.get("domain") if raw.get("domain") in EVENT_DOMAINS else "other"
    return EventTypeSpec(name=str(raw.get("name") or ""), domain=domain, roles=roles,
                         counts_quantity=bool(raw.get("quantity")), in_chronicle=raw.get("chronicle") is not False,
                         participants_secret=bool(raw.get("secret")))


def type_definition(spec: EventTypeSpec) -> dict:
    """A clean spec as the card's form reads it (`eventVocab.typeDraft`)."""
    return {"name": spec.name, "domain": spec.domain, "counts_quantity": spec.counts_quantity,
            "in_chronicle": spec.in_chronicle, "participants_secret": spec.participants_secret,
            "roles": [{"name": r.name, "entity_types": list(r.entity_types), "accepts_sorte": r.accepts_sorte}
                      for r in spec.roles], "scopes": []}


def _near(found) -> list[dict]:
    return [{"id": n.id, "name": n.name, "score": n.score} for n in found]


def _existing(rows, name: str) -> Optional[str]:
    key = normalize_surface(name)
    return next((row_id for row_id, row_name in rows if key and normalize_surface(row_name) == key), None)


def read_vocabulary(db: Session, world_id: str, types_raw: Any, sortes_raw: Any, where: str = "") -> Vocabulary:
    """The model's `define_events` and `define_sortes` blocks read."""
    vocab = Vocabulary()
    known_types = [(v.id, v.name) for v in world_event_types(db, world_id)]
    known_sortes = [(s.id, s.name) for s in world_sortes(db, world_id)]
    for kind, raws, prefix in (("type", types_raw, TYPE_PREFIX), ("sorte", sortes_raw, SORTE_PREFIX)):
        for raw in raws if isinstance(raws, list) else []:
            if not isinstance(raw, dict) or raw.get("ref") is None:
                vocab.errors.append(f"{where}une proposition sans « ref » : {raw!r}")
                continue
            name = str(raw.get("name") or "")
            same = _existing(known_types if kind == "type" else known_sortes, name)
            if same is not None:
                vocab.refs[str(raw["ref"])] = ("id", same)
                continue
            try:
                if kind == "type":
                    definition = type_definition(clean_event_type(db, world_id, type_spec(raw)))
                    near = _near(near_event_types(db, world_id, definition["name"]))
                else:
                    definition = {"name": clean_sorte_name(db, world_id, name)}
                    near = _near(near_sortes(db, world_id, definition["name"]))
            except ValueError as exc:
                vocab.errors.append(f"{where}{'type' if kind == 'type' else 'sorte'} proposé « {name} » : {exc}")
                continue
            ref = f"{prefix}{sum(p['kind'] == kind for p in vocab.proposals) + 1}"
            vocab.proposals.append({"ref": ref, "kind": kind, "definition": definition, "near": near})
            vocab.refs[str(raw["ref"])] = ("ref", ref)
    return vocab


def vocab_waiting(leaf: dict) -> bool:
    return "type_define" in leaf or any("sorte_define" in f for f in leaf.get("filters") or [])


def _role_id(view: EventTypeView, name: Any) -> Optional[str]:
    key = normalize_surface(str(name or ""))
    return next((r.id for r in view.active_roles() if key and normalize_surface(r.name) == key), None)


def _bound(db: Session, world_id: str, kind: str, ref: str, bindings: dict[str, str]) -> str:
    pick = bindings.get(ref)
    if kind == "type":
        view = type_view(db, pick) if pick else None
        if view is None or view.world_id != world_id or view.status != "active":
            raise ValueError(f"« {ref} » : crée le type proposé, ou choisis un type existant")
        return view.id
    sorte = db.get(EventSorte, pick) if pick else None
    if sorte is None or sorte.world_id != world_id or sorte.status != "active":
        raise ValueError(f"« {ref} » : crée la sorte proposée, ou choisis une sorte existante")
    return sorte.id


def _bind_leaf(db: Session, world_id: str, leaf: dict, bindings: dict[str, str], errors: list[str]) -> dict:
    out = dict(leaf)
    if "type_define" in out:
        out["target_key"] = _bound(db, world_id, "type", out.pop("type_define"), bindings)
    view = type_view(db, out["target_key"]) if out.get("target_key") else None
    names = ", ".join(r.name for r in view.active_roles()) if view else ""
    if "role_name" in out:
        name = out.pop("role_name")
        out["value"] = _role_id(view, name) if view and name not in (None, "") else None
        if name not in (None, "") and out["value"] is None:
            errors.append(f"« {name} » n'est pas un rôle de « {view.name if view else '?'} » (rôles : {names})")
    filters = []
    for f in out.get("filters") or []:
        f = dict(f)
        if "sorte_define" in f:
            f["sorte_id"] = _bound(db, world_id, "sorte", f.pop("sorte_define"), bindings)
        if "role_name" in f:
            name = f.pop("role_name")
            f["role_id"] = _role_id(view, name) if view else None
            if f["role_id"] is None:
                errors.append(f"« {name} » n'est pas un rôle de « {view.name if view else '?'} » (rôles : {names})")
        filters.append(f)
    out["filters"] = filters
    return out


def bind_vocabulary(db: Session, world_id: str, pending: dict, bindings: dict[str, str]) -> tuple[dict, list[str]]:
    """`pending` with every proposal ref replaced by the creator's pick and
    the role names of the type it names resolved. `ValueError` when a ref
    has no pick, or a pick that is no active type or sorte of the world;
    an unknown role name is an error of the list returned."""
    errors: list[str] = []

    def walk(node: dict) -> dict:
        if node.get("op") != "leaf":
            return {**node, "children": [walk(c) for c in node.get("children", [])]}
        if "type_define" not in node and "role_name" not in node and not any(
                "sorte_define" in f or "role_name" in f for f in node.get("filters") or []):
            return node
        return _bind_leaf(db, world_id, node, bindings, errors)

    return walk(pending), errors
