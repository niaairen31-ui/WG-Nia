"""The condition interpreter's `event` leaves (TICKET-0114, BRIEF-0114-F;
decision R1 of the conditions series).

The model reads the world's event types as a coded list (`t`), each with
its roles, and its sortes by name; it writes an `event` leaf with the
type's code as `target`, the subject's role by name as `value` (null: any),
a `place` named like any entity, a window `since` and, in `with`, the other
roles each filled by a sorte (by name) or an entity (by name). Code reads
it back here: a role or a sorte by its normalized name, an unknown one an
error listing the right ones; an entity through the interpreter's own
resolver (`resolve_entity`), so an ambiguous name waits for the creator's
pick like any other -- a filter's pick is kept as `entity_mention` until
`bind_filters`.

- `event_type_line(view, types)` : one type as the `t` list shows it.
- `encode_event(spec, out, ...)` : a clean event leaf in the model's form.
- `read_event(raw, out, ...)`    : the model's event leaf read back.
- `filters_waiting(leaf)`        : a filter still waits for a pick.
- `bind_filters(leaf, ...)`      : the creator's picks applied.

Writes nothing.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from .event_vocab import EventTypeView
from .lore_resolve import normalize_surface
from .models import CONDITION_WINDOWS

# The model's `since`, by the value the language stores (F1).
EVENT_WINDOW_DEFAULT = "always"


def event_type_line(view: EventTypeView, types: dict[str, str]) -> str:
    """« Tuer (rôles : tueur — personnage ; victime — personnage ou une
    sorte ; compte une quantité) »: what the model needs to write a leaf."""
    roles = []
    for role in view.active_roles():
        takes = [types.get(t, t).lower() for t in role.entity_types]
        if role.accepts_sorte:
            takes.append("une sorte")
        roles.append(f"{role.name} — {' ou '.join(takes) or 'rien'}")
    quantity = " ; compte une quantité" if view.counts_quantity else ""
    return f"{view.name} (rôles : {' ; '.join(roles) or 'aucun'}{quantity})"


def _role_by_name(view: EventTypeView, name: Any):
    wanted = normalize_surface(str(name or ""))
    return next((r for r in view.active_roles() if wanted and normalize_surface(r.name) == wanted), None)


def _role_names(view: EventTypeView) -> str:
    return ", ".join(r.name for r in view.active_roles()) or "aucun"


def encode_event(spec, out: dict, view: Optional[EventTypeView], sortes: dict[str, str],
                 encode_ref: Callable[[Optional[str]], Optional[dict]]) -> dict:
    """`out` (the generic leaf, its `target` the type's code) completed: the
    role by name, the place, the window and the filters by role name."""
    names = {r.id: r.name for r in view.roles} if view is not None else {}
    out["value"] = names.get(spec.value, spec.value) if spec.value else None
    out["place"] = encode_ref(spec.target_entity_id)
    out["since"] = spec.since or EVENT_WINDOW_DEFAULT
    out["with"] = [{"role": names.get(f.role_id, f.role_id),
                    **({"sorte": sortes.get(f.sorte_id, f.sorte_id)} if f.sorte_id else encode_ref(f.entity_id) or {})}
                   for f in spec.filters]
    return out


ResolveEntity = Callable[[Any, str], tuple[Optional[str], Optional[str]]]


def read_event(raw: dict, out: dict, view: Optional[EventTypeView], sortes: dict[str, str],
               resolve_entity: ResolveEntity, errors: list[str], where: str) -> None:
    """The rest of an `event` leaf, read into `out` (the generic leaf, its
    `target_key` the type's id or None): `value` a role's id, the place
    (`target_entity_id`, or `target_mention` while a pick waits), `since`
    and `filters`. Every problem is appended to `errors`."""
    out["since"] = raw.get("since") or EVENT_WINDOW_DEFAULT
    if out["since"] not in CONDITION_WINDOWS:
        errors.append(f"{where}fenêtre inconnue {out['since']!r} (attendu : {', '.join(CONDITION_WINDOWS)})")
    out["value"], out["filters"] = None, []
    place = raw.get("place")
    if isinstance(place, str):
        place = {"name": place, "kind": "place"}
    if place:
        out["target_entity_id"], out["target_mention"] = resolve_entity(place, where)
    if view is None:
        return
    if raw.get("value") not in (None, ""):
        role = _role_by_name(view, raw["value"])
        if role is None:
            errors.append(f"{where}« {raw['value']} » n'est pas un rôle de « {view.name} » "
                          f"(rôles : {_role_names(view)})")
        else:
            out["value"] = role.id
    by_name = {normalize_surface(name): sid for sid, name in sortes.items()}
    for item in raw.get("with") if isinstance(raw.get("with"), list) else []:
        role = _role_by_name(view, item.get("role")) if isinstance(item, dict) else None
        if role is None:
            errors.append(f"{where}« {item.get('role') if isinstance(item, dict) else item} » n'est pas un rôle "
                          f"de « {view.name} » (rôles : {_role_names(view)})")
            continue
        entry: dict[str, Any] = {"role_id": role.id, "entity_id": None, "sorte_id": None}
        if item.get("sorte") is not None:
            entry["sorte_id"] = by_name.get(normalize_surface(str(item["sorte"])))
            if entry["sorte_id"] is None:
                known = ", ".join(sortes.values()) or "aucune"
                errors.append(f"{where}« {item['sorte']} » n'est pas une sorte de ce monde (sortes : {known})")
                continue
        else:
            entity = {k: item[k] for k in ("name", "kind", "code") if k in item}
            entry["entity_id"], mention = resolve_entity(entity, where)
            if mention is not None:
                entry["entity_mention"] = mention
        out["filters"].append(entry)


def filters_waiting(leaf: dict) -> bool:
    return any("entity_mention" in f for f in leaf.get("filters") or [])


def bind_filters(leaf: dict, pick: Callable[[str], str]) -> dict:
    """`leaf` with each filter's waiting name replaced by `pick(ref)`."""
    if not leaf.get("filters"):
        return leaf
    filters = []
    for f in leaf["filters"]:
        f = dict(f)
        ref = f.pop("entity_mention", None)
        if ref is not None:
            f["entity_id"] = pick(ref)
        filters.append(f)
    return {**leaf, "filters": filters}
