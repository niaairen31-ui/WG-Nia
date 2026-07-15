"""`event` canon-write chokepoints (TICKET-0028, BRIEF-0028-b — decomposed
from `writes.py`). Pure moves, no logic change — neither function was
baselined.

- `write_event(...)`        : insert one `event` row. The ONLY place
  `Event(` is constructed in gameplay code (TICKET-0017, BRIEF-0017-a).
- `write_event_update(...)`  : creator-CRUD-only writer for an existing
  `event` row (TICKET-0022, BRIEF-0022-a). `_apply_mutation` never calls
  this. Together `write_event` and `write_event_update` are the complete
  set of `event` writers.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlmodel import Session

from ..models import Event, EventEntity


def write_event(
    db: Session,
    *,
    world_id: str,
    title: str,
    description: Optional[str] = None,
    type: Optional[str] = None,
    knowledge_status: Optional[str] = None,
    involved_entities: Optional[list] = None,
    location_id: Optional[str] = None,
    mutation_id: Optional[str] = None,
) -> Event:
    """Insert one `event` row. Caller adds nothing else — this function
    calls `db.add`. Both producers — the scope-level tick call and the
    analyzer's dormant conversation-sourced channel — route through
    `_apply_mutation`'s `event_creation` branch, which calls this.

    `knowledge_status=None` lets the column's `server_default` 'secret'
    apply — the analyzer's minimal payload shape carries no status.
    `occurred_at` stays None (in-fiction time unknown); `recorded_at` is the
    row's own `_created_ts` default. `session_id`/`batch_id` stay None:
    neither a play-session artifact nor a pass-play batch — the mutation
    row's `tick_id`/`conversation_id` is the provenance anchor.
    `mutation_id` is accepted only for call-site symmetry with the other
    `_apply_mutation` writers (no `change_history` column on this table) and
    is not otherwise used here. `involved_entities` (TICKET-0025,
    BRIEF-0025-c: relationalized) inserts `event_entity` rows after the
    event row — a fresh event has no prior rows to replace.
    """
    del mutation_id
    event = Event(
        world_id=world_id,
        title=title,
        description=description,
        type=type,
        location_id=location_id,
    )
    if knowledge_status is not None:
        event.knowledge_status = knowledge_status
    db.add(event)
    for entity_id in (involved_entities or []):
        db.add(EventEntity(event_id=event.id, entity_id=entity_id))
    return event


def write_event_update(
    db: Session,
    *,
    event: Event,
    title: str,
    description: Optional[str] = None,
    type: Optional[str] = None,
    knowledge_status: str,
    involved_entities: Optional[list] = None,
    location_id: Optional[str] = None,
) -> Event:
    """Creator-CRUD-only writer for an existing `event` row (TICKET-0022,
    BRIEF-0022-a). Sets exactly the six fields listed above and calls
    `db.add`. Does NOT touch `recorded_at`, `occurred_at`,
    `has_magic_impact`, `consequences`, `session_id`, `batch_id` — those
    keep whatever they had. No `change_history` append: the table has no
    such column — a known, accepted gap, not an oversight.
    `involved_entities` (TICKET-0025, BRIEF-0025-c: relationalized)
    full-replaces this event's `event_entity` rows — the chips editor's
    replace contract.
    """
    event.title = title
    event.description = description
    event.type = type
    event.knowledge_status = knowledge_status
    event.location_id = location_id
    db.add(event)
    db.execute(text("DELETE FROM event_entity WHERE event_id = :event_id"), {"event_id": event.id})
    for entity_id in (involved_entities or []):
        db.add(EventEntity(event_id=event.id, entity_id=entity_id))
    return event
