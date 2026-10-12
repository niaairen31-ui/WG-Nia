"""What an event's type proposes it changes in the world (TICKET-0119,
BRIEF-0119-C; decisions M-c, D3 and E1 of the conditions series).

An event type declares its effects (`event_type_effect`, « Ouvrir : Cible
-> Ouvert = oui »). When an event of it is proposed -- by Play's analyzer,
the world tick, Journée, Lore or the creator's own journal -- its effects
are made concrete on the event's participants and PRE-FILL the event's
changes, which the creator keeps, edits or drops before the event is
written (`writes.events`, F1: one refused and nothing is written).

- `type_changes(db, world_id, view, participants)` : the changes a type's
  effects make on `participants` -- (role id, entity id or None) pairs --
  as payload dicts `{entity_id, attribute, mode, value}`: one per entity in
  the effect's role (a sorte changes nothing: there is no one to change);
  an entity state takes the first entity in its value role, and is left
  out when that role has none.
- `change_line(db, world_id, change)` : one change in French, for a card --
  « Porte : Ouvert -> oui », « Garnison : Alerte + 1 », « Ivo : État vital
  -> mort »; None when the change names nothing the world has.
- `payload_changes(raw)` : a payload's `state_changes` read into the
  writer's `StateChangeSpec`s (the writer cleans them).

Reads only; writes nothing.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from sqlmodel import Session

from .attributes import applies_to, attribute_view, value_label
from .event_vocab import EventTypeView
from .models import Entity
from .writes.events import StateChangeSpec


def type_changes(db: Session, world_id: str, view: Optional[EventTypeView],
                 participants: Iterable[tuple[Optional[str], Optional[str]]]) -> list[dict]:
    """The changes `view`'s effects make on `participants` (see the module
    docstring), in the order of its effects."""
    if view is None:
        return []
    held: dict[str, list[str]] = {}
    for role_id, entity_id in participants:
        if role_id and entity_id and entity_id not in held.setdefault(role_id, []):
            held[role_id].append(entity_id)
    out: list[dict] = []
    for effect in view.effects:
        state = attribute_view(db, world_id, effect.attribute)
        if state is None or state.status != "active":
            continue
        value = effect.value
        if effect.value_kind == "role":
            named = held.get(effect.value) or []
            if not named:
                continue
            value = named[0]
        for entity_id in held.get(effect.role_id, []):
            entity = db.get(Entity, entity_id)
            if entity is None or not applies_to(state, entity.type):
                continue
            if any(c["entity_id"] == entity_id and c["attribute"] == state.key for c in out):
                continue
            out.append({"entity_id": entity_id, "attribute": state.key, "mode": effect.mode, "value": value})
    return out


def change_line(db: Session, world_id: str, change: dict) -> Optional[str]:
    """One change, in French (see the module docstring)."""
    state = attribute_view(db, world_id, change.get("attribute"))
    entity = db.get(Entity, change.get("entity_id")) if isinstance(change.get("entity_id"), str) else None
    if state is None or entity is None or entity.world_id != world_id:
        return None
    if change.get("mode") == "add":
        value = change.get("value")
        sign = "+" if isinstance(value, int) and value >= 0 else ""
        return f"{entity.name} : {state.name} {sign}{value}"
    return f"{entity.name} : {state.name} -> {value_label(db, state, change.get('value'))}"


def payload_changes(raw: Any) -> tuple[StateChangeSpec, ...]:
    """A payload's `state_changes`, as the writer reads them; a malformed
    item is kept as it is for the writer to refuse, never dropped."""
    out = []
    for item in raw if isinstance(raw, list) else []:
        item = item if isinstance(item, dict) else {}
        out.append(StateChangeSpec(entity_id=item.get("entity_id"), attribute=item.get("attribute"),
                                   value=item.get("value"), mode=item.get("mode") or "set"))
    return tuple(out)
