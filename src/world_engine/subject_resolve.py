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

from sqlmodel import Session

from .lore_resolve import _CATEGORY_ENTITY_TYPE, resolve_named


@dataclass(frozen=True)
class SubjectResolution:
    verdict: str
    entity_id: Optional[str]
    candidate_ids: tuple[str, ...]
    category: Optional[str]


def resolve_subject(subject: str, world_id: str, db: Session) -> SubjectResolution:
    """Walk `_CATEGORY_ENTITY_TYPE` in sorted key order, calling
    `resolve_named(subject, category, world_id, db)` for each.

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

    for category in sorted(_CATEGORY_ENTITY_TYPE):
        result = resolve_named(subject, category, world_id, db)
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
