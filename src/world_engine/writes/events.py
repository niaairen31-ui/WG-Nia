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
  taking part (K-a), secret as said. Returns the event, flushed.
- `write_event_update(db, *, event, spec, changed_by)` : a correction from
  the journal -- title, description, place, quantity; a participant added;
  a participant's secret changed (his knowledge row); the scopes replaced
  whole. The fact's text is rewritten as a `correction` when it changed.

The two producers -- the creator's journal (`cockpit/crud/events.py`) and
`_apply_mutation`'s `event_creation` (a model's proposal, reviewed by the
creator, D1) -- both call `write_event`; `event_payloads.py` turns a
proposal's payload into an `EventSpec`. None of these functions commits.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from ..event_vocab import EventTypeView, role_accepts, type_view
from ..models import (
    Character,
    Entity,
    Event,
    EventParticipant,
    EventSorte,
    Fact,
    Knowledge,
)
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
    description = (spec.description or "").strip() or None
    return replace(spec, title=title, description=description, location_id=location_id,
                   quantity=_clean_quantity(view, spec.quantity), participants=participants, scopes=scopes)


# --- writing -------------------------------------------------------------------

def _participant_rows(db: Session, event_id: str) -> list[EventParticipant]:
    return list(db.exec(select(EventParticipant).where(EventParticipant.event_id == event_id)
                        .order_by(EventParticipant.position, EventParticipant.id)).all())


def _knows(db: Session, entity_id: str, fact_id: str, secret: bool, changed_by: str) -> None:
    """K-a: a character taking part knows the event -- his row written at
    `knows`, or raised to it, his `is_secret` set as said (X1)."""
    if db.get(Character, entity_id) is None:
        return
    row = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
    if row is None:
        write_knowledge(db, entity_id=entity_id, fact_id=fact_id, level=PARTICIPANT_LEVEL, is_secret=secret,
                        source=EVENT_SOURCE, changed_by=changed_by)
        return
    level = row.level if knowledge_level_rank(row.level) >= knowledge_level_rank(PARTICIPANT_LEVEL) \
        else PARTICIPANT_LEVEL
    write_knowledge(db, knowledge_id=row.id, level=level, content=row.content_raw, source=row.source,
                    is_incorrect=row.is_incorrect, is_secret=secret, share_threshold=row.share_threshold,
                    session_id=row.session_id, changed_by=changed_by)


def _add_participants(db: Session, event: Event, participants, fact_id: str, changed_by: str) -> None:
    rows = _participant_rows(db, event.id)
    have = {(r.role_id, r.entity_id, r.sorte_id) for r in rows}
    position = len(rows)
    for p in participants:
        if _key(p) not in have:
            db.add(EventParticipant(world_id=event.world_id, event_id=event.id, role_id=p.role_id,
                                    entity_id=p.entity_id, sorte_id=p.sorte_id, position=position))
            position += 1
        if p.entity_id is not None:
            _knows(db, p.entity_id, fact_id, bool(p.secret), changed_by)


def _write_scopes(db: Session, world_id: str, fact_id: str, scopes, created_by: str) -> None:
    """The fact's scopes replaced whole (the full-replace shape)."""
    db.execute(text("DELETE FROM fact_default WHERE fact_id = :fid"), {"fid": fact_id})
    for scope in scopes:
        create_fact_default(db, world_id=world_id, fact_id=fact_id, scope_type=scope.scope_type,
                            scope_id=scope.scope_id, level=scope.level, created_by=created_by)


def write_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> Event:
    """C-01: the event, its participants, its fact, the fact's scopes and
    the participants' knowledge, from a cleaned spec."""
    clean = clean_event(db, world_id, spec)
    event = Event(world_id=world_id, type_id=clean.type_id, title=clean.title, description=clean.description,
                  location_id=clean.location_id, quantity=clean.quantity, session_id=clean.session_id,
                  batch_id=clean.batch_id)
    db.add(event)
    db.flush()
    fact = create_fact(db, world_id=world_id, content=event_fact_text(clean.title, clean.description),
                       created_by=created_by, facet="evenement", event_id=event.id)
    db.flush()
    _add_participants(db, event, clean.participants, fact.id, created_by)
    _write_scopes(db, world_id, fact.id, clean.scopes, created_by)
    db.flush()
    return event


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
