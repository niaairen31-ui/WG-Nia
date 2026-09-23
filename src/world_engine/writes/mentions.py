"""`unresolved_mention` writer (TICKET-0091, BRIEF-0091-J, contract C-15).

The single write site of the name-resolution worklist: a name in new canon
prose that `prose_tokens.tokenize` could not turn into an identity token
(`ambigu`: two or more candidates, `inconnu`: none). Non-canon — the table
records a question for the creator, never a statement about the world.
Each row points at exactly one of a `fact` or a `knowledge` row. Nothing
here commits; the caller owns the transaction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session

from ..models import UnresolvedMention


def record_unresolved(
    db: Session, *, world_id: str, fact_id: Optional[str] = None,
    knowledge_id: Optional[str] = None, items: tuple = (),
) -> list[UnresolvedMention]:
    """One open row per `prose_tokens.Unresolved` in `items`. Raises
    `ValueError` unless exactly one of `fact_id` / `knowledge_id` is set."""
    if (fact_id is None) == (knowledge_id is None):
        raise ValueError("record_unresolved: exactly one of fact_id, knowledge_id")
    rows = []
    for item in items:
        row = UnresolvedMention(
            world_id=world_id, fact_id=fact_id, knowledge_id=knowledge_id,
            surface=item.surface, reason=item.reason, category=item.category,
        )
        db.add(row)
        rows.append(row)
    return rows


def _close(db: Session, mention: UnresolvedMention, entity_id: Optional[str]) -> UnresolvedMention:
    if mention.resolved_at is not None:
        raise ValueError(f"unresolved_mention {mention.id!r} is already closed")
    mention.resolved_at = datetime.now(UTC)
    mention.resolved_entity_id = entity_id
    db.add(mention)
    return mention


def resolve_mention(db: Session, *, mention: UnresolvedMention, entity_id: str) -> UnresolvedMention:
    """Close `mention` as bound to `entity_id`."""
    return _close(db, mention, entity_id)


def dismiss_mention(db: Session, *, mention: UnresolvedMention) -> UnresolvedMention:
    """Close `mention` with no entity (dismissed: `resolved_at` set,
    `resolved_entity_id` NULL)."""
    return _close(db, mention, None)
