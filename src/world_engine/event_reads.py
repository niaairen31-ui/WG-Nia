"""The journal as the models read it (TICKET-0114, BRIEF-0114-D; decisions
K-a and Q1 of the conditions series). It replaces the former
`event.knowledge_status IN ('public', 'confirmed')` filter of every reader.

Only an event whose type enters the chronicle (`event_type.in_chronicle`)
is ever told to a model: an event that only counts -- « un loup tué » --
serves the conditions and is known as a fact, never as news.

- `known_chronicle_events(db, knower_id, ...)` : what one character knows
  of the chronicle -- the events whose fact he resolves above `unaware`
  (`knowledge_resolve.resolve_known_for_entity`: his own knowledge rows,
  then the scopes he is in contact with, 0105). The MJ of Play reads the
  player's (`context.py`, `cockpit/play_physical.py`). His own rows are
  never secret (INV-07); an NPC's secret row is never read here, nor
  anywhere a model is briefed (INV-01).
- `public_chronicle_events(db, world_id, ...)` : what everyone knows -- the
  events whose fact has a `world` scope; the world tick reads these
  (`tick_context.py`), its briefing governed by no one character.

Both answer the newest first. This module writes nothing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from .knowledge_resolve import resolve_known_for_entity
from .models import Event, EventParticipant, EventType, Fact, FactDefault


def _chronicle(db: Session, world_id: str, location_id: Optional[str], since: Optional[datetime]):
    query = (select(Event, Fact.id)
             .join(EventType, EventType.id == Event.type_id)
             .join(Fact, Fact.event_id == Event.id)
             .where(Event.world_id == world_id, EventType.in_chronicle == True))  # noqa: E712
    if location_id is not None:
        query = query.where(Event.location_id == location_id)
    if since is not None:
        query = query.where(Event.recorded_at > since)
    return query.order_by(Event.recorded_at.desc(), Event.id)


def known_chronicle_events(db: Session, knower_id: str, world_id: str, *, location_id: Optional[str] = None,
                           since: Optional[datetime] = None) -> list[Event]:
    """The chronicle events `knower_id` knows, newest first."""
    known = resolve_known_for_entity(db, knower_id)
    if not known:
        return []
    rows = db.exec(_chronicle(db, world_id, location_id, since)).all()
    return [event for event, fact_id in rows if fact_id in known]


def public_chronicle_events(db: Session, world_id: str, *, location_id: Optional[str] = None,
                            participant_id: Optional[str] = None, limit: Optional[int] = None) -> list[Event]:
    """The chronicle events everyone knows (a `world` scope on their fact),
    newest first; at one place, or with one participant, when asked."""
    query = _chronicle(db, world_id, location_id, None).where(
        Fact.id.in_(select(FactDefault.fact_id).where(FactDefault.scope_type == "world")))
    if participant_id is not None:
        query = query.where(Event.id.in_(select(EventParticipant.event_id).where(
            EventParticipant.entity_id == participant_id)))
    if limit is not None:
        query = query.limit(limit)
    return [event for event, _fact_id in db.exec(query).all()]
