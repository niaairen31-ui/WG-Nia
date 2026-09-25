"""Free-text `knowledge.subject` reconciled against entity names (TICKET-0087,
BRIEF-0087-a).

This module is the single place a free-text `knowledge.subject` is
reconciled against entity names; it reuses `lore_resolve`'s rungs and never
re-implements one; it never calls a model; it never picks between
candidates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .lore_resolve import resolve_named
from .models import Entity, FactParticipant, Knowledge
from .name_index import NAMES_ONLY

# Frozen here (N10a): a knowledge subject resolves on names only, among these
# three categories, whatever the Lore resolver's categories become.
_SUBJECT_CATEGORIES: tuple[str, ...] = ("faction", "person", "place")


@dataclass(frozen=True)
class SubjectResolution:
    verdict: str
    entity_id: Optional[str]
    candidate_ids: tuple[str, ...]
    category: Optional[str]


def resolve_subject(subject: str, world_id: str, db: Session) -> SubjectResolution:
    """Walk `_SUBJECT_CATEGORIES` in order, calling
    `resolve_named(subject, category, world_id, db, scope=NAMES_ONLY)` for
    each: entity names only, never an appellation (N10a).

    Exactly one distinct `entity_id` across all `matched` categories, and no
    category `ambiguous` -> `matched`. Two or more distinct matched ids, or
    any category `ambiguous` -> `ambiguous`, `candidate_ids` the sorted union
    of every candidate seen. No category matched -> `unmatched`. An empty or
    whitespace-only `subject` -> `unmatched`, with no rung call made.
    """
    if not subject or not subject.strip():
        return SubjectResolution(verdict="unmatched", entity_id=None, candidate_ids=(), category=None)

    matched_ids: set[str] = set()
    matched_category: Optional[str] = None
    any_ambiguous = False
    seen_candidates: set[str] = set()

    for category in _SUBJECT_CATEGORIES:
        result = resolve_named(subject, category, world_id, db, scope=NAMES_ONLY)
        if result.verdict == "ambiguous":
            any_ambiguous = True
            seen_candidates.update(result.candidate_ids)
        elif result.verdict == "matched":
            matched_ids.add(result.entity_id)
            matched_category = category
            seen_candidates.update(result.candidate_ids)

    if any_ambiguous or len(matched_ids) > 1:
        return SubjectResolution(
            verdict="ambiguous", entity_id=None,
            candidate_ids=tuple(sorted(seen_candidates)), category=None,
        )
    if len(matched_ids) == 1:
        entity_id = next(iter(matched_ids))
        return SubjectResolution(
            verdict="matched", entity_id=entity_id,
            candidate_ids=(entity_id,), category=matched_category,
        )
    return SubjectResolution(verdict="unmatched", entity_id=None, candidate_ids=(), category=None)


def unresolved_subjects(world_id: str, db: Session) -> list[dict]:
    """One row per distinct `knowledge.subject` in `world_id` whose fact
    carries no `fact_participant` at all (TICKET-0087, BRIEF-0087-c, C-06).

    `resolve_subject` runs once per distinct subject, never once per row.
    World scoping and the "no participant at all" filter are both applied
    in the single `select(...).where(...)` below — an outer join to
    `fact_participant` so a row with a match (participant_id IS NOT NULL)
    is excluded in Python, never fetched via a second, unscoped `select(`.
    Ordered by `row_count` descending, then `subject` ascending.
    """
    rows = db.exec(
        select(Knowledge.subject, Knowledge.fact_id, FactParticipant.id)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .outerjoin(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
        .where(Entity.world_id == world_id)
    ).all()

    grouped: dict[str, dict] = {}
    for subject, fact_id, participant_id in rows:
        if participant_id is not None:
            continue
        group = grouped.setdefault(subject, {"fact_ids": set(), "row_count": 0})
        group["fact_ids"].add(fact_id)
        group["row_count"] += 1

    result = [
        {
            "subject": subject,
            "fact_ids": tuple(sorted(group["fact_ids"])),
            "row_count": group["row_count"],
            "resolution": resolve_subject(subject, world_id, db),
        }
        for subject, group in grouped.items()
    ]
    result.sort(key=lambda entry: (-entry["row_count"], entry["subject"]))
    return result
