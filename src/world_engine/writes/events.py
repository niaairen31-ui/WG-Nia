"""`event` canon-write chokepoint -- the event journal (TICKET-0114,
BRIEF-0114-C; decisions F1, D1, E1, K-a, V1, W1 and X1 of the conditions
series). The one writer of `event` and `event_participant`.

- `clean_event(db, world_id, spec, event=None)` : an event as it will be
  written, or `ValueError`. Its type is the world's (active, for a new
  event); its title is not empty; its place an active location of the
  world; a quantity only when its type counts, at least 1; each participant
  fills an active role of its type with an entity of a type the role
  accepts, or a sorte when the role accepts one, never twice the same; a
  participant's `secret` is its own (X1), the type's default when unsaid,
  and always False for a player character (INV-07). Its scopes are the
  type's when unsaid (W1): `location` its place, `world`, `rencontre` each
  entity in the role, `faction` each faction in the role -- the highest
  level kept per scope. On an existing event (a correction), the type
  stays, and no participant is taken away. Writes nothing.
- `write_event(db, *, world_id, spec, created_by)` : the event, its
  participants, its fact (`fact.event_id`, facet `evenement`, its title then
  its description -- `event_fact_text`), the fact's scopes
  (`fact_default`) and one `knowledge` row at `knows` for each character
  taking part (K-a), secret as said -- then its CHANGES to the state of the
  world (M-c, TICKET-0119). Returns the event, flushed. `record_event` does
  the same and returns every row it wrote (`WrittenEvent`), for a caller
  that records them (Lore) or keeps a system change's before and after
  (the applier).
- `write_event_update(db, *, event, spec, changed_by)` : a correction from
  the journal -- title, description, place, quantity; a participant added;
  a participant's secret changed (his knowledge row); the scopes replaced
  whole. The fact's text is rewritten as a `correction` when it changed. A
  correction changes no state (L1: the event already did, or never did).

An event's changes (`StateChangeSpec`, TICKET-0119, F1) are what the
creator kept of its type's effects, edited or added: each names an entity
of the world, a state that applies to it -- one of the world's active
definitions, or `État vital` / `Statut` (E1) --, and a value of the state's
kind (`add` for an integer, D3; an entity of a type the state may name, or
none). One refused and the whole event is refused: nothing is written. A
definition's change is a `changement` naming the event
(`writes.attributes.write_attribute_value`); a system state is written by
`writes.entity_states.write_system_state`, which keeps no history -- the
event and its fact are the reason.

The two producers -- the creator's journal (`cockpit/crud/events.py`) and
`_apply_mutation`'s `event_creation` (a model's proposal, reviewed by the
creator, D1) -- both call `write_event`; `event_payloads.py` turns a
proposal's payload into an `EventSpec`. None of these functions commits.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from ..attributes import applies_to, attribute_view, current_value, stored_value
from ..event_vocab import EventTypeView, role_accepts, type_view
from ..models import (
    EVENT_EFFECT_MODES,
    Character,
    Entity,
    Event,
    EventParticipant,
    EventSorte,
    Fact,
    Knowledge,
)
from .attributes import write_attribute_value
from .entity_states import write_system_state
from .event_types import EFFECT_SYSTEM_KEYS
from .facts import create_fact, create_fact_default, update_typed_fact_content
from .knowledge import knowledge_level_rank, write_knowledge

# K-a: what a participant holds of the event, and from where.
PARTICIPANT_LEVEL = "knows"
EVENT_SOURCE = "evenement"
MAX_TITLE_CHARS = 200
# The fact_default scope types an event's scope may name (`fact_default`'s CHECK).
SCOPE_TYPES: tuple[str, ...] = ("world", "location", "rencontre", "faction")
SCOPE_LEVELS: tuple[str, ...] = ("rumor", "suspicious", "partial", "knows", "fully_understands")


@dataclass(frozen=True)
class ParticipantSpec:
    """One participant: a role of the type, an entity or a sorte, and for an
    entity whether he keeps the event secret (None: the type's default)."""
    role_id: str
    entity_id: Optional[str] = None
    sorte_id: Optional[str] = None
    secret: Optional[bool] = None


@dataclass(frozen=True)
class EventScopeSpec:
    """One concrete scope of an event's fact: a `fact_default` row."""
    scope_type: str
    scope_id: Optional[str]
    level: str


@dataclass(frozen=True)
class StateChangeSpec:
    """One change an event makes to the state of the world (M-c): `entity_id`'s
    `attribute` (a definition id or a system key) takes `value` -- a choice
    key, an integer (set, or added when `mode` is `add`), an entity id, or
    None (an entity state left empty)."""
    entity_id: str
    attribute: str
    value: object
    mode: str = "set"


@dataclass(frozen=True)
class EventSpec:
    type_id: str
    title: str
    description: Optional[str] = None
    location_id: Optional[str] = None
    quantity: Optional[int] = None
    participants: tuple[ParticipantSpec, ...] = ()
    scopes: Optional[tuple[EventScopeSpec, ...]] = None  # None: the type's (W1)
    session_id: Optional[str] = None
    batch_id: Optional[str] = None
    changes: tuple[StateChangeSpec, ...] = ()


@dataclass
class WrittenEvent:
    """Every row one `record_event` wrote: (id, `created` | `updated`) per
    table, and the system states it changed (`entity_id`, `attribute`,
    `before`, `after`), which keep no history of their own."""
    event: Event
    fact: Fact
    rows: list[tuple[str, str, str]] = field(default_factory=list)  # (table, id, action)
    system_changes: list[dict] = field(default_factory=list)


def event_fact_text(title: str, description: Optional[str]) -> str:
    """The text of an event's fact: its title, then its description."""
    description = (description or "").strip()
    return f"{title} — {description}" if description else title


# --- cleaning ------------------------------------------------------------------

def _clean_type(db: Session, world_id: str, type_id: str, event: Optional[Event]) -> EventTypeView:
    view = type_view(db, type_id)
    if view is None or view.world_id != world_id:
        raise ValueError(f"unknown event type {type_id!r}")
    if event is not None and event.type_id != type_id:
        raise ValueError("an event's type does not change; write another event")
    if event is None and view.status != "active":
        raise ValueError(f"« {view.name} » is retired")
    return view


def _clean_location(db: Session, world_id: str, location_id: Optional[str]) -> Optional[str]:
    if not location_id:
        return None
    place = db.get(Entity, location_id)
    if place is None or place.type != "location" or place.status != "active" or place.world_id != world_id:
        raise ValueError(f"{location_id!r} is not an active location of this world")
    return location_id


def _clean_quantity(view: EventTypeView, quantity: object) -> Optional[int]:
    if quantity is None:
        return None
    if not view.counts_quantity:
        raise ValueError(f"« {view.name} » counts no quantity")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        raise ValueError("a quantity is an integer of 1 or more")
    return quantity


def _is_player(db: Session, entity_id: str) -> bool:
    character = db.get(Character, entity_id)
    return character is not None and character.character_type == "player"


def _clean_participant(db: Session, world_id: str, view: EventTypeView, p: ParticipantSpec) -> ParticipantSpec:
    role = view.role(p.role_id)
    if role is None or role.status != "active":
        raise ValueError(f"{p.role_id!r} is no role of « {view.name} »")
    if (p.entity_id is None) == (p.sorte_id is None):
        raise ValueError(f"the role « {role.name} » is filled by an entity or a sorte, exactly one")
    if p.sorte_id is not None:
        sorte = db.get(EventSorte, p.sorte_id)
        if sorte is None or sorte.world_id != world_id or sorte.status != "active":
            raise ValueError(f"unknown sorte {p.sorte_id!r}")
        if not role.accepts_sorte:
            raise ValueError(f"the role « {role.name} » takes no sorte")
        return ParticipantSpec(role_id=role.id, sorte_id=sorte.id)
    entity = db.get(Entity, p.entity_id)
    if entity is None or entity.world_id != world_id:
        raise ValueError(f"unknown entity {p.entity_id!r}")
    if not role_accepts(role, entity.type):
        raise ValueError(f"the role « {role.name} » takes no {entity.type}")
    secret = view.participants_secret if p.secret is None else bool(p.secret)
    return ParticipantSpec(role_id=role.id, entity_id=entity.id, secret=False if _is_player(db, entity.id) else secret)


def _key(p: ParticipantSpec) -> tuple:
    return (p.role_id, p.entity_id, p.sorte_id)


def _clean_participants(db: Session, world_id: str, view: EventTypeView, participants) -> tuple[ParticipantSpec, ...]:
    cleaned = tuple(_clean_participant(db, world_id, view, p) for p in participants)
    keys = [_key(p) for p in cleaned]
    if len(set(keys)) != len(keys):
        raise ValueError("a participant is named twice in one role")
    return cleaned


def _type_scopes(db: Session, view: EventTypeView, location_id: Optional[str],
                 participants: tuple[ParticipantSpec, ...]) -> tuple[EventScopeSpec, ...]:
    """The type's scopes made concrete for one event (W1)."""
    found: list[EventScopeSpec] = []
    for scope in view.scopes:
        if scope.kind == "world":
            found.append(EventScopeSpec("world", None, scope.level))
        elif scope.kind == "location" and location_id:
            found.append(EventScopeSpec("location", location_id, scope.level))
        elif scope.kind in ("rencontre", "faction"):
            for p in participants:
                entity = db.get(Entity, p.entity_id) if p.entity_id else None
                if p.role_id == scope.role_id and entity is not None and (
                        scope.kind == "rencontre" or entity.type == "faction"):
                    found.append(EventScopeSpec(scope.kind, entity.id, scope.level))
    return _merged(found)


def _merged(scopes) -> tuple[EventScopeSpec, ...]:
    """One scope per (type, id), the highest level kept."""
    best: dict[tuple, EventScopeSpec] = {}
    for scope in scopes:
        key = (scope.scope_type, scope.scope_id)
        if key not in best or knowledge_level_rank(scope.level) > knowledge_level_rank(best[key].level):
            best[key] = scope
    return tuple(best.values())


_SCOPE_ENTITY_TYPE = {"location": "location", "faction": "faction"}


def _clean_scope(db: Session, world_id: str, scope: EventScopeSpec) -> EventScopeSpec:
    if scope.scope_type not in SCOPE_TYPES:
        raise ValueError(f"unknown scope {scope.scope_type!r}")
    if scope.level not in SCOPE_LEVELS:
        raise ValueError(f"a scope's level is one the knower holds, not {scope.level!r}")
    if scope.scope_type == "world":
        if scope.scope_id is not None:
            raise ValueError("a world scope names nothing")
        return scope
    entity = db.get(Entity, scope.scope_id) if scope.scope_id else None
    wanted = _SCOPE_ENTITY_TYPE.get(scope.scope_type)
    if entity is None or entity.world_id != world_id or (wanted and entity.type != wanted):
        raise ValueError(f"a {scope.scope_type} scope names {scope.scope_id!r}, not one of this world")
    return scope


def _clean_change_value(db: Session, world_id: str, view, change: StateChangeSpec) -> object:
    if change.mode not in EVENT_EFFECT_MODES:
        raise ValueError(f"unknown change mode {change.mode!r}")
    if change.mode == "add" and view.kind != "integer":
        raise ValueError(f"« {view.name} » is not a number: a change sets it")
    if view.kind == "integer":
        if not isinstance(change.value, int) or isinstance(change.value, bool):
            raise ValueError(f"« {view.name} » takes an integer")
        return change.value
    if view.kind == "choice":
        if change.value not in dict(view.choices):
            raise ValueError(f"{change.value!r} is no value of « {view.name} »")
        return change.value
    if change.value is None:
        return None
    named = db.get(Entity, change.value) if isinstance(change.value, str) else None
    if named is None or named.world_id != world_id or named.type not in view.value_types:
        raise ValueError(f"« {view.name} » names no {change.value!r}")
    return named.id


def _clean_change(db: Session, world_id: str, change: StateChangeSpec) -> StateChangeSpec:
    view = attribute_view(db, world_id, change.attribute) if isinstance(change.attribute, str) else None
    if view is None or view.status != "active" or (view.system and view.key not in EFFECT_SYSTEM_KEYS):
        raise ValueError(f"{change.attribute!r} is no state an event changes")
    entity = db.get(Entity, change.entity_id) if isinstance(change.entity_id, str) else None
    if entity is None or entity.world_id != world_id:
        raise ValueError(f"unknown entity {change.entity_id!r}")
    if not applies_to(view, entity.type):
        raise ValueError(f"« {view.name} » does not apply to « {entity.name} »")
    if view.key == "sys:vital_status" and db.get(Character, entity.id) is None:
        raise ValueError(f"« {entity.name} » has no vital state")
    value = _clean_change_value(db, world_id, view, change)
    if view.key == "sys:status" and entity.type == "location" and value == "active" and entity.status != "active":
        raise ValueError(f"« {entity.name} » is made active again from its fiche, never by an event")
    return StateChangeSpec(entity_id=entity.id, attribute=view.key, value=value, mode=change.mode)


def _clean_changes(db: Session, world_id: str, changes) -> tuple[StateChangeSpec, ...]:
    cleaned = tuple(_clean_change(db, world_id, c) for c in changes)
    keys = [(c.entity_id, c.attribute) for c in cleaned]
    if len(set(keys)) != len(keys):
        raise ValueError("one state of one entity is changed twice")
    return cleaned


def clean_event(db: Session, world_id: str, spec: EventSpec, event: Optional[Event] = None) -> EventSpec:
    """`spec` as it will be written, its scopes made concrete; raises
    `ValueError` on any violation. Writes nothing."""
    view = _clean_type(db, world_id, spec.type_id, event)
    title = " ".join(str(spec.title or "").split())
    if not title:
        raise ValueError("an event needs a title")
    if len(title) > MAX_TITLE_CHARS:
        raise ValueError(f"an event's title has at most {MAX_TITLE_CHARS} characters")
    location_id = _clean_location(db, world_id, spec.location_id)
    participants = _clean_participants(db, world_id, view, spec.participants)
    if event is not None:
        kept = {(p.role_id, p.entity_id, p.sorte_id) for p in participants}
        for row in _participant_rows(db, event.id):
            if (row.role_id, row.entity_id, row.sorte_id) not in kept:
                raise ValueError("a participant stays: an event's participants are never taken away")
    if spec.scopes is None:
        scopes = _type_scopes(db, view, location_id, participants)
    else:
        scopes = _merged(_clean_scope(db, world_id, s) for s in spec.scopes)
    if event is not None and spec.changes:
        raise ValueError("a correction of an event changes no state")
    description = (spec.description or "").strip() or None
    return replace(spec, title=title, description=description, location_id=location_id,
                   quantity=_clean_quantity(view, spec.quantity), participants=participants, scopes=scopes,
                   changes=_clean_changes(db, world_id, spec.changes))


# --- writing -------------------------------------------------------------------

def _participant_rows(db: Session, event_id: str) -> list[EventParticipant]:
    return list(db.exec(select(EventParticipant).where(EventParticipant.event_id == event_id)
                        .order_by(EventParticipant.position, EventParticipant.id)).all())


def _knows(db: Session, entity_id: str, fact_id: str, secret: bool, changed_by: str) -> Optional[tuple]:
    """K-a: a character taking part knows the event -- his row written at
    `knows`, or raised to it, his `is_secret` set as said (X1). Returns
    (`knowledge`, its id, `created` | `updated`), or None for a non-character."""
    if db.get(Character, entity_id) is None:
        return None
    row = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
    if row is None:
        made = write_knowledge(db, entity_id=entity_id, fact_id=fact_id, level=PARTICIPANT_LEVEL, is_secret=secret,
                               source=EVENT_SOURCE, changed_by=changed_by)
        db.flush()
        return "knowledge", made.id, "created"
    level = row.level if knowledge_level_rank(row.level) >= knowledge_level_rank(PARTICIPANT_LEVEL) \
        else PARTICIPANT_LEVEL
    write_knowledge(db, knowledge_id=row.id, level=level, content=row.content_raw, source=row.source,
                    is_incorrect=row.is_incorrect, is_secret=secret, share_threshold=row.share_threshold,
                    session_id=row.session_id, changed_by=changed_by)
    return "knowledge", row.id, "updated"


def _add_participants(db: Session, event: Event, participants, fact_id: str, changed_by: str) -> list[tuple]:
    rows = _participant_rows(db, event.id)
    have = {(r.role_id, r.entity_id, r.sorte_id) for r in rows}
    position = len(rows)
    written: list[tuple] = []
    for p in participants:
        if _key(p) not in have:
            row = EventParticipant(world_id=event.world_id, event_id=event.id, role_id=p.role_id,
                                   entity_id=p.entity_id, sorte_id=p.sorte_id, position=position)
            db.add(row)
            db.flush()
            written.append(("event_participant", row.id, "created"))
            position += 1
        if p.entity_id is not None:
            known = _knows(db, p.entity_id, fact_id, bool(p.secret), changed_by)
            if known is not None:
                written.append(known)
    return written


def _write_scopes(db: Session, world_id: str, fact_id: str, scopes, created_by: str) -> list[tuple]:
    """The fact's scopes replaced whole (the full-replace shape)."""
    db.execute(text("DELETE FROM fact_default WHERE fact_id = :fid"), {"fid": fact_id})
    written: list[tuple] = []
    for scope in scopes:
        row = create_fact_default(db, world_id=world_id, fact_id=fact_id, scope_type=scope.scope_type,
                                  scope_id=scope.scope_id, level=scope.level, created_by=created_by)
        db.flush()
        written.append(("fact_default", row.id, "created"))
    return written


def _apply_changes(db: Session, world_id: str, event: Event, changes, changed_by: str, out: WrittenEvent) -> None:
    """The event's changes to the state of the world (M-c)."""
    for change in changes:
        view = attribute_view(db, world_id, change.attribute)
        entity = db.get(Entity, change.entity_id)
        if view.system:
            done = write_system_state(db, world_id=world_id, entity_id=entity.id, key=view.key, value=change.value)
            if done is not None:
                out.system_changes.append({"entity_id": entity.id, "attribute": view.key,
                                           "before": done[0], "after": done[1]})
            continue
        value = change.value
        if change.mode == "add":
            value = (current_value(db, view, entity).raw or 0) + change.value
        held = stored_value(db, view.key, entity.id) is not None
        made = write_attribute_value(db, world_id=world_id, definition_id=view.key, entity_id=entity.id,
                                     value=value, kind="changement", changed_by=changed_by, event_id=event.id)
        if made is not None:
            out.rows.append(("attribute_value", made.value_id, "updated" if held else "created"))
            out.rows.append(("attribute_change", made.id, "created"))


def record_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> WrittenEvent:
    """C-01: the event, its participants, its fact, the fact's scopes, the
    participants' knowledge and its changes, from a cleaned spec; every row
    written, returned."""
    clean = clean_event(db, world_id, spec)
    event = Event(world_id=world_id, type_id=clean.type_id, title=clean.title, description=clean.description,
                  location_id=clean.location_id, quantity=clean.quantity, session_id=clean.session_id,
                  batch_id=clean.batch_id)
    db.add(event)
    db.flush()
    fact = create_fact(db, world_id=world_id, content=event_fact_text(clean.title, clean.description),
                       created_by=created_by, facet="evenement", event_id=event.id)
    db.flush()
    out = WrittenEvent(event=event, fact=fact, rows=[("event", event.id, "created"), ("fact", fact.id, "created")])
    out.rows += _add_participants(db, event, clean.participants, fact.id, created_by)
    out.rows += _write_scopes(db, world_id, fact.id, clean.scopes, created_by)
    _apply_changes(db, world_id, event, clean.changes, created_by, out)
    db.flush()
    return out


def write_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> Event:
    """`record_event`, for a caller that needs only the event."""
    return record_event(db, world_id=world_id, spec=spec, created_by=created_by).event


def event_fact(db: Session, event_id: str) -> Optional[Fact]:
    return db.exec(select(Fact).where(Fact.event_id == event_id)).first()


def write_event_update(db: Session, *, event: Event, spec: EventSpec, changed_by: str) -> Event:
    """C-02: a creator's correction of one event, from the journal."""
    clean = clean_event(db, event.world_id, spec, event)
    event.title, event.description = clean.title, clean.description
    event.location_id, event.quantity = clean.location_id, clean.quantity
    db.add(event)
    fact = event_fact(db, event.id)
    if fact is None:
        raise ValueError(f"event {event.id!r} has no fact")
    content = event_fact_text(clean.title, clean.description)
    if fact.content_raw != content:
        update_typed_fact_content(db, fact=fact, content=content, changed_by=changed_by, kind="correction")
    _add_participants(db, event, clean.participants, fact.id, changed_by)
    _write_scopes(db, event.world_id, fact.id, clean.scopes, changed_by)
    db.flush()
    return event
