"""The attributes the interpreter proposes (TICKET-0113, BRIEF-0113-E;
decisions WK2 and WN2 of the conditions series).

When the creator's sentence names a state her world does not define yet,
the model proposes its definition in its answer's `define` block and the
condition names it there. Until her « Enregistrer », such a definition is
UNSAVED: it lives in the offer's draft, keyed `new:<ref>` (`n1`, `n2`, …),
and every condition naming it is validated against it by the writer's own
rules (`writes.conditions.clean_leaf(..., unsaved=...)`, the definition by
`writes.attributes.clean_definition`). On the save (WN2), `materialize`
writes each definition a condition still names -- through
`write_attribute_definition`, in the offer's transaction -- and rewrites
the conditions to its id, a label to its choice's id. A definition no
condition names any more is not written.

- `unsaved_view(p)`         : an `UnsavedAttribute` as an `AttributeView`
  (its choices keyed by their label).
- `clean_unsaved(...)`      : the draft's definitions as the client sends
  them, cleaned.
- `read_definitions(...)`   : the model's `define` block -> new unsaved
  definitions with fresh refs, the model's refs mapped, and the errors.
- `near_existing(...)`      : for each new definition, the attributes whose
  name is near (`attributes.near_attributes`, and the other unsaved ones) --
  the creator picks one or creates (WK2); the tool never picks.
- `adopt(...)`              : a pick of an existing attribute -- the leaves
  naming `new:<ref>` rewritten to it, a label to its choice's key.
- `materialize(...)`        : the save's half (WN2).

Writes nothing except through `materialize`, which calls the writer and
never commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlmodel import Session

from .attributes import (
    ATTRIBUTE_FORM,
    AttributeView,
    attribute_view,
    near_attributes,
    world_entity_type_labels,
)
from .lore_resolve import near_ratio, near_score, normalize_surface
from .writes.attributes import ChoiceSpec, DefinitionSpec, clean_definition, write_attribute_definition

UNSAVED_PREFIX = "new:"


@dataclass(frozen=True)
class UnsavedAttribute:
    ref: str
    spec: DefinitionSpec


def unsaved_key(ref: str) -> str:
    return UNSAVED_PREFIX + ref


def is_unsaved(key: Optional[str]) -> bool:
    return bool(key) and key.startswith(UNSAVED_PREFIX)


def unsaved_view(item: UnsavedAttribute) -> AttributeView:
    spec = item.spec
    return AttributeView(
        key=unsaved_key(item.ref), name=spec.name, kind=spec.kind, system=False, hidden=spec.is_hidden,
        status="active", holder_types=tuple(spec.holder_types), value_types=tuple(spec.value_types),
        choices=tuple((c.label, c.label) for c in spec.choices), default=spec.default,
    )


def unsaved_views(items) -> dict[str, AttributeView]:
    return {unsaved_key(item.ref): unsaved_view(item) for item in items}


def spec_dict(spec: DefinitionSpec) -> dict:
    """A definition in the request body's shape (`routes.attributes.DefinitionBody`)."""
    return {"name": spec.name, "kind": spec.kind, "holder_types": list(spec.holder_types),
            "value_types": list(spec.value_types), "choices": [{"label": c.label} for c in spec.choices],
            "default": spec.default, "is_hidden": spec.is_hidden}


def spec_from_dict(raw: Any) -> DefinitionSpec:
    if not isinstance(raw, dict):
        raise ValueError(f"a definition is an object, got {raw!r}")
    return DefinitionSpec(
        name=raw.get("name") or "", kind=raw.get("kind") or "",
        holder_types=tuple(raw.get("holder_types") or ()), value_types=tuple(raw.get("value_types") or ()),
        choices=tuple(ChoiceSpec(str(c.get("label") if isinstance(c, dict) else c)) for c in raw.get("choices") or ()),
        default=raw.get("default"), is_hidden=bool(raw.get("is_hidden")),
    )


def clean_unsaved(db: Session, world_id: str, raw: Any) -> list[UnsavedAttribute]:
    """The draft's unsaved definitions, as the client sends them
    (`[{ref, definition}]`), each cleaned by `clean_definition`; two with
    one name, or a ref used twice, are refused. `ValueError` names the
    first problem."""
    items: list[UnsavedAttribute] = []
    names: set[str] = set()
    for entry in raw or []:
        ref = str((entry or {}).get("ref") or "")
        if not ref or any(i.ref == ref for i in items):
            raise ValueError(f"an unsaved attribute needs a ref of its own, got {ref!r}")
        try:
            spec = clean_definition(db, world_id, spec_from_dict(entry.get("definition")))
        except ValueError as exc:
            raise ValueError(f"« {(entry.get('definition') or {}).get('name')} » : {exc}") from exc
        if normalize_surface(spec.name) in names:
            raise ValueError(f"« {spec.name} » is proposed twice")
        names.add(normalize_surface(spec.name))
        items.append(UnsavedAttribute(ref=ref, spec=spec))
    return items


# --- the model's `define` block (C-12) --------------------------------------------

def _types(raw: Any, labels: dict[str, str]) -> tuple[str, ...]:
    """Entity types the model named, by key or by French name."""
    by_name = {normalize_surface(label): key for key, label in labels.items()}
    out = []
    for item in raw if isinstance(raw, list) else []:
        text = str(item or "")
        key = text if text in labels else by_name.get(normalize_surface(text))
        if key is None:
            raise ValueError(f"unknown entity type {text!r}")
        out.append(key)
    return tuple(out)


def _model_spec(raw: dict, labels: dict[str, str]) -> DefinitionSpec:
    choices = raw.get("choices") if isinstance(raw.get("choices"), list) else []
    return DefinitionSpec(
        name=str(raw.get("name") or ""), kind=str(raw.get("kind") or ""),
        holder_types=_types(raw.get("for"), labels), value_types=_types(raw.get("value_types"), labels),
        choices=tuple(ChoiceSpec(str(c)) for c in choices), default=raw.get("default"),
        is_hidden=bool(raw.get("hidden")),
    )


def read_definitions(db: Session, world_id: str, raw: Any, taken: set[str],
                     others: list[UnsavedAttribute]) -> tuple[list[UnsavedAttribute], dict[str, str], list[str]]:
    """The model's `define` block: each definition cleaned by
    `clean_definition` and given a fresh ref (`n<k>`, past every ref of
    `taken`); returns the new definitions, the model's ref -> `new:<ref>`,
    and the errors in French (a definition refused, one already in the
    draft's)."""
    labels = {t["type"]: t["label"] for t in world_entity_type_labels(db, world_id)}
    new: list[UnsavedAttribute] = []
    refs: dict[str, str] = {}
    errors: list[str] = []
    names = {normalize_surface(o.spec.name) for o in others}
    for raw_def in raw if isinstance(raw, list) else []:
        if not isinstance(raw_def, dict):
            errors.append(f"état proposé : un objet attendu, reçu {raw_def!r}")
            continue
        name = str(raw_def.get("name") or "").strip()
        try:
            spec = clean_definition(db, world_id, _model_spec(raw_def, labels))
        except ValueError as exc:
            errors.append(f"état proposé « {name} » : {exc}")
            continue
        if normalize_surface(spec.name) in names:
            errors.append(f"état proposé « {name} » : il est déjà proposé, utilise son code")
            continue
        names.add(normalize_surface(spec.name))
        k = 1
        while f"n{k}" in taken:
            k += 1
        taken.add(f"n{k}")
        new.append(UnsavedAttribute(ref=f"n{k}", spec=spec))
        refs[str(raw_def.get("ref") or name)] = unsaved_key(f"n{k}")
    return new, refs, errors


def near_existing(db: Session, world_id: str, new: list[UnsavedAttribute],
                  others: list[UnsavedAttribute]) -> dict[str, list[dict]]:
    """For each new definition whose name is near another attribute's -- a
    saved one, or one already in the draft -- the near ones, best first
    (`{key, name, system, score}`). WK2: never a duplicate « Maudit » /
    « maudite » unseen."""
    out: dict[str, list[dict]] = {}
    for item in new:
        near = [{"key": n.key, "name": n.name, "system": n.system, "score": n.score}
                for n in near_attributes(db, world_id, item.spec.name)]
        target = normalize_surface(item.spec.name)
        for other in others:
            ratio = near_ratio(target, other.spec.name)
            if ratio is not None:
                near.append({"key": unsaved_key(other.ref), "name": other.spec.name, "system": False,
                             "score": near_score(ratio)})
        if near:
            out[item.ref] = sorted(near, key=lambda n: (-n["score"], n["name"].casefold()))
    return out


def adopt(db: Session, world_id: str, tree: Optional[dict], ref: str, key: str,
          views: dict[str, AttributeView]) -> Optional[dict]:
    """`tree` (dict form) with every leaf on `new:<ref>` moved to the
    existing attribute `key` -- a label read back to its choice's key
    (case- and accent-blind). `ValueError` when a label is not one of its."""
    view = views.get(key) or attribute_view(db, world_id, key)
    if view is None:
        raise ValueError(f"unknown attribute {key!r}")
    by_label = {normalize_surface(label): choice for choice, label in view.choices}

    def move(node: dict) -> dict:
        if node.get("op") != "leaf":
            return {**node, "children": [move(c) for c in node.get("children", [])]}
        if node.get("target_key") != unsaved_key(ref):
            return node
        out = {**node, "target_key": key}
        if view.kind == "choice" and node.get("value") is not None:
            choice = by_label.get(normalize_surface(str(node["value"])))
            if choice is None:
                labels = ", ".join(label for _c, label in view.choices)
                raise ValueError(f"« {node['value']} » n'est pas un libellé de « {view.name} » (libellés : {labels})")
            out["value"] = choice
        return out

    return move(tree) if tree is not None else None


# --- the save (WN2) ----------------------------------------------------------------

def _named(tree: Optional[dict], found: set[str]) -> None:
    if not tree:
        return
    if tree.get("op") == "leaf":
        if tree.get("type") == ATTRIBUTE_FORM and is_unsaved(tree.get("target_key")):
            found.add(tree["target_key"])
        return
    for child in tree.get("children", []):
        _named(child, found)


def rewrite(tree: Optional[dict], keys: dict[str, str], labels: dict[tuple[str, str], str]) -> Optional[dict]:
    """`tree` with each `new:` key replaced by its written id and each of
    its labels by its choice's id."""
    if tree is None:
        return None
    if tree.get("op") != "leaf":
        return {**tree, "children": [rewrite(c, keys, labels) for c in tree.get("children", [])]}
    key = tree.get("target_key")
    if tree.get("type") != ATTRIBUTE_FORM or key not in keys:
        return tree
    out = {**tree, "target_key": keys[key]}
    if tree.get("value") is not None:
        out["value"] = labels.get((key, tree["value"]), tree["value"])
    return out


def materialize(db: Session, world_id: str, raw: Any, trees: list[Optional[dict]]
                ) -> tuple[list[Optional[dict]], dict[str, str], dict[tuple[str, str], str]]:
    """WN2: write every unsaved definition one of `trees` names, in the
    caller's transaction, and return the trees rewritten to the written ids,
    with the key and label maps. A definition no tree names is not written.
    `ValueError` for a tree naming a definition the body does not carry."""
    items = {unsaved_key(i.ref): i for i in clean_unsaved(db, world_id, raw)}
    named: set[str] = set()
    for tree in trees:
        _named(tree, named)
    missing = sorted(named - set(items))
    if missing:
        raise ValueError(f"a condition names an unsaved attribute the offer does not carry: {missing}")
    keys: dict[str, str] = {}
    labels: dict[tuple[str, str], str] = {}
    for key in sorted(named):
        definition = write_attribute_definition(db, world_id=world_id, spec=items[key].spec)
        keys[key] = definition.id
        for choice, label in attribute_view(db, world_id, definition.id).choices:
            labels[(key, label)] = choice
    return [rewrite(tree, keys, labels) for tree in trees], keys, labels
