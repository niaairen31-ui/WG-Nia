"""`fact`/`fact_participant`/`fact_default` canon-write chokepoint
(TICKET-0082, BRIEF-0082-b; `fact_default` added at BRIEF-0082-c).

The single sanctioned write site for all three tables — every
`db.add(Fact(...))`, `db.add(FactParticipant(...))` and
`db.add(FactDefault(...))` in `src/` goes through `create_fact`,
`attach_participants` and `create_fact_default` respectively (enforced by
`tooling/verify/checks/fact_spine.py`'s AST scan for the first two;
`single_canon_write.py`'s policy-file allowlist for the third).

`attach_participants` enforces in code the one rule SQLite cannot express as
a CHECK because it spans two tables: a participant may be attached only to a
fact whose typed FKs (`relation_id`, `event_id`, `world_law_id`) are ALL
NULL. A typed fact already IS the row it points to; `fact_participant`
exists only to carry arity for a free-standing fact.

`create_fact_default` performs no duplicate check of its own — the creator
route (`cockpit/crud/knowledge.py`) queries for an existing
`(fact_id, scope_type, scope_id)` row and returns 409 before ever calling
this function, so a duplicate never reaches the write site.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from ..models import Fact, FactDefault, FactParticipant


def create_fact(
    db: Session,
    *,
    world_id: str,
    content: str,
    created_by: str,
    default_level: str = "unaware",
    relation_id: Optional[str] = None,
    event_id: Optional[str] = None,
    world_law_id: Optional[str] = None,
) -> Fact:
    """Insert a new `fact` row — the single sanctioned `fact` write site."""
    fact = Fact(
        world_id=world_id,
        content=content,
        created_by=created_by,
        default_level=default_level,
        relation_id=relation_id,
        event_id=event_id,
        world_law_id=world_law_id,
    )
    db.add(fact)
    return fact


def attach_participants(
    db: Session,
    *,
    fact: Fact,
    entity_ids: list[str],
    role: Optional[str] = None,
) -> list[FactParticipant]:
    """Attach one or more entities as participants on a free-standing fact.

    Raises `ValueError` if `fact` carries any typed FK (`relation_id`/
    `event_id`/`world_law_id`) — never silently drops. `position` is
    assigned in `entity_ids` order, starting at 0.
    """
    if fact.relation_id is not None or fact.event_id is not None or fact.world_law_id is not None:
        raise ValueError(
            f"attach_participants: fact {fact.id!r} is typed (relation_id/event_id/"
            "world_law_id set) — a participant may attach only to a free-standing fact"
        )
    rows = []
    for position, entity_id in enumerate(entity_ids):
        row = FactParticipant(
            world_id=fact.world_id, fact_id=fact.id, entity_id=entity_id,
            role=role, position=position,
        )
        db.add(row)
        rows.append(row)
    return rows


def create_fact_default(
    db: Session,
    *,
    world_id: str,
    fact_id: str,
    scope_type: str,
    scope_id: Optional[str],
    level: str,
    created_by: str,
) -> FactDefault:
    """Insert a new `fact_default` row — the single sanctioned `fact_default`
    write site (TICKET-0082, BRIEF-0082-c)."""
    row = FactDefault(
        world_id=world_id, fact_id=fact_id, scope_type=scope_type,
        scope_id=scope_id, level=level, created_by=created_by,
    )
    db.add(row)
    return row
