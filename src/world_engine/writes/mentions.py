"""`unresolved_mention` writer (TICKET-0091, BRIEF-0091-J, contract C-15).

The single write site of the name-resolution worklist: a name in new canon
prose that `prose_tokens.tokenize` could not turn into an identity token
(`ambigu`: two or more candidates, `inconnu`: none). Non-canon — the table
records a question for the creator, never a statement about the world.
Each row points at exactly one of a `fact` or a `knowledge` row. Nothing
here commits; the caller owns the transaction.

`bind_mention` is the name-resolution panel's write (TICKET-0091,
BRIEF-0091-K, C-16): the owner's stored text is read here, in `writes/`,
never by the route (`identity_tokens.py` R1), and written back through
`update_fact_content` or `apply_knowledge_patch` (`write_knowledge`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from ..models import Fact, Knowledge, UnresolvedMention
from ..prose_render import TOKEN_RE, entity_token


def record_unresolved(
    db: Session, *, world_id: str, fact_id: Optional[str] = None,
    knowledge_id: Optional[str] = None, items: tuple = (),
) -> list[UnresolvedMention]:
    """One open row per `prose_tokens.Unresolved` in `items`. Raises
    `ValueError` unless exactly one of `fact_id` / `knowledge_id` is set.
    An item already open on the same owner (same surface, reason, category)
    is not asked twice: a rewrite of the owner's text re-reports the names
    still plain in it (TICKET-0091, BRIEF-0091-K)."""
    if (fact_id is None) == (knowledge_id is None):
        raise ValueError("record_unresolved: exactly one of fact_id, knowledge_id")
    open_rows = db.exec(select(UnresolvedMention).where(
        UnresolvedMention.fact_id == fact_id if fact_id is not None
        else UnresolvedMention.knowledge_id == knowledge_id,
        UnresolvedMention.resolved_at.is_(None),
    )).all()
    asked = {(r.surface, r.reason, r.category) for r in open_rows}
    rows = []
    for item in items:
        if (item.surface, item.reason, item.category) in asked:
            continue
        asked.add((item.surface, item.reason, item.category))
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


def _first_plain(text: str, surface: str) -> int:
    """Index of the first occurrence of `surface` in `text` outside every
    identity token, or -1."""
    cursor = 0
    bounds = [m.span() for m in TOKEN_RE.finditer(text)] + [(len(text), len(text))]
    for token_start, token_end in bounds:
        found = text.find(surface, cursor, token_start)
        if found != -1 and found + len(surface) <= token_start:
            return found
        cursor = token_end
    return -1


def bind_mention(db: Session, *, mention: UnresolvedMention, entity_id: str, changed_by: str) -> UnresolvedMention:
    """Replace the first plain occurrence of `mention.surface` in its owner's
    stored text with `entity_token(entity_id, surface)`, write the owner
    back (history appended by the chokepoint), then close `mention` as bound.
    Raises `ValueError` when the surface no longer occurs plain in the text.
    Validation of `entity_id` is the caller's responsibility."""
    # Local: `knowledge.py` imports this module (`record_unresolved`).
    from .facts import update_fact_content
    from .knowledge import apply_knowledge_patch

    owner = db.get(Fact, mention.fact_id) if mention.fact_id else db.get(Knowledge, mention.knowledge_id)
    if owner is None:
        raise ValueError(f"unresolved_mention {mention.id!r}: owner row not found")
    text = owner.content_raw if isinstance(owner.content_raw, str) else ""
    at = _first_plain(text, mention.surface)
    if at == -1:
        raise ValueError(f"unresolved_mention {mention.id!r}: {mention.surface!r} no longer occurs in the text")
    new_text = text[:at] + entity_token(entity_id, mention.surface) + text[at + len(mention.surface):]
    if isinstance(owner, Fact):
        update_fact_content(db, fact=owner, content=new_text, changed_by=changed_by)
    else:
        apply_knowledge_patch(db, knowledge=owner, patch={"content": new_text}, changed_by=changed_by)
    return resolve_mention(db, mention=mention, entity_id=entity_id)
