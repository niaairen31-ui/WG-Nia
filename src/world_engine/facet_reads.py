"""Facet reads (TICKET-0091, BRIEF-0091-D, C-10): one call to read what is
said of an entity, facet by facet.

`facts_of` returns the facts an entity takes part in (`fact_participant`,
R-06 — `role` never filters) whose facet is one of `facets`, in the order of
`facets`, then `created_at`, then `fact_id`. `known_facts_of` narrows that
list to the facts a perceiver resolves above `'unaware'`
(`knowledge_resolve.resolve_levels_for_entity`, one batch call).

Creator-only facts (AMENDMENT-0091-01) are excluded by query construction:
a fact is creator-only when a stored `knowledge` row on it belongs to one of
its own participants with `level = 'unaware'` and `is_secret = 1` (the shape
the creator's note takes). Only `lore_selectors.py` — the creator's dossier
— may pass `include_creator_only=True`; `known_facts_of` has no override.

Resolution is a read: no function here ever calls `db.add`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from sqlmodel import Session, select

from .facets import normalize_aspect
from .knowledge_resolve import resolve_levels_for_entity
from .models import Fact, FactDefault, FactParticipant, Knowledge


@dataclass(frozen=True)
class FactRow:
    fact_id: str
    facet: str
    aspect: Optional[str]
    content: str
    created_at: datetime


def _creator_only_select():
    """`fact_id`s carrying a stored `unaware`, `is_secret` knowledge row that
    belongs to one of the fact's own participants."""
    return (
        select(Knowledge.fact_id)
        .join(
            FactParticipant,
            (FactParticipant.fact_id == Knowledge.fact_id)
            & (FactParticipant.entity_id == Knowledge.entity_id),
        )
        .where(Knowledge.level == "unaware", Knowledge.is_secret == True)  # noqa: E712
    )


def creator_only_fact_ids(db: Session, fact_ids: Iterable[str]) -> set[str]:
    """The creator-only subset of `fact_ids`, in one query."""
    ids = list(fact_ids)
    if not ids:
        return set()
    return set(db.exec(_creator_only_select().where(Knowledge.fact_id.in_(ids))).all())


def facts_of(
    db: Session,
    *,
    entity_id: str,
    facets: tuple[str, ...],
    aspect: Optional[str] = None,
    notorious_at_location: Optional[str] = None,
    include_creator_only: bool = False,
) -> list[FactRow]:
    """Facts with `entity_id` as a participant and `facet in facets`
    (and `aspect == normalize_aspect(aspect)` when given). With
    `notorious_at_location`, only facts carrying a `location` default whose
    `scope_id` equals it. Creator-only facts are dropped in the query unless
    `include_creator_only` (legal only in `lore_selectors.py`). Empty list
    when none."""
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
    if not include_creator_only:
        query = query.where(Fact.id.not_in(_creator_only_select()))
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
    """`facts_of` (creator-only facts always excluded, no override), filtered
    to the facts `perceiver_id` resolves above `'unaware'` — one
    `resolve_levels_for_entity` call, never one per fact."""
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
