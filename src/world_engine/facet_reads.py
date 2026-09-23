"""Facet reads (TICKET-0091, BRIEF-0091-D, C-10): one call to read what is
said of an entity, facet by facet.

`facts_of` returns the facts an entity takes part in (`fact_participant`,
R-06 — `role` never filters) whose facet is one of `facets`, in the order of
`facets`, then `created_at`, then `fact_id`. `known_facts_of` narrows that
list to the facts a perceiver resolves above `'unaware'`
(`knowledge_resolve.resolve_levels_for_entity`, one batch call).

Resolution is a read: no function here ever calls `db.add`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from .facets import normalize_aspect
from .knowledge_resolve import resolve_levels_for_entity
from .models import Fact, FactDefault, FactParticipant


@dataclass(frozen=True)
class FactRow:
    fact_id: str
    facet: str
    aspect: Optional[str]
    content: str
    created_at: datetime


def facts_of(
    db: Session,
    *,
    entity_id: str,
    facets: tuple[str, ...],
    aspect: Optional[str] = None,
    notorious_at_location: Optional[str] = None,
) -> list[FactRow]:
    """Facts with `entity_id` as a participant and `facet in facets`
    (and `aspect == normalize_aspect(aspect)` when given). With
    `notorious_at_location`, only facts carrying a `location` default whose
    `scope_id` equals it. Empty list when none."""
    if not facets:
        return []
    query = (
        select(Fact)
        .join(FactParticipant, FactParticipant.fact_id == Fact.id)
        .where(FactParticipant.entity_id == entity_id, Fact.facet.in_(facets))
    )
    if aspect is not None:
        query = query.where(Fact.aspect == normalize_aspect(aspect))
    if notorious_at_location is not None:
        notorious_ids = select(FactDefault.fact_id).where(
            FactDefault.scope_type == "location",
            FactDefault.scope_id == notorious_at_location,
        )
        query = query.where(Fact.id.in_(notorious_ids))
    facts = db.exec(query).all()
    order = {facet: index for index, facet in enumerate(facets)}
    facts = sorted(facts, key=lambda f: (order[f.facet], f.created_at, f.id))
    return [
        FactRow(
            fact_id=f.id, facet=f.facet, aspect=f.aspect, content=f.content,
            created_at=f.created_at,
        )
        for f in facts
    ]


def known_facts_of(
    db: Session,
    *,
    perceiver_id: str,
    entity_id: str,
    facets: tuple[str, ...],
    aspect: Optional[str] = None,
) -> list[FactRow]:
    """`facts_of`, filtered to the facts `perceiver_id` resolves above
    `'unaware'` — one `resolve_levels_for_entity` call, never one per fact."""
    rows = facts_of(db, entity_id=entity_id, facets=facets, aspect=aspect)
    if not rows:
        return []
    known = resolve_levels_for_entity(db, perceiver_id)
    return [row for row in rows if row.fact_id in known]


def joined(rows: list[FactRow], sep: str = "\n") -> Optional[str]:
    """Contents joined by `sep`; `None` for an empty list."""
    if not rows:
        return None
    return sep.join(row.content for row in rows)
