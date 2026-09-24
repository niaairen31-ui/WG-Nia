"""Reads for the name-resolution panel (TICKET-0091, BRIEF-0091-K, contract
C-16, decision Q17d).

The open `unresolved_mention` rows of the active world, each with a
rendered excerpt of its owner's text and its candidates recomputed by
`lore_resolve.resolve_named` (every category when `category` is NULL) and
its near names (`near_candidates`, BRIEF-0092-d) -- the resolver never
picks; two or more candidates are shown to the creator. Read-only: no
`db.add`, no commit, no model call.

Isolated from the consultation pipeline by construction: this module
imports none of `lore_selectors`, `lore_query`, `lore_plan`, `lore_render`,
`lore_prompt` (`lore_isolation.py` R17).
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .lore_resolve import CATEGORIES, near_candidates, resolve_named, validate_binding
from .models import Entity, Fact, Knowledge, UnresolvedMention, World
from .name_index import CREATOR
from .prose_render import fact_text, knowledge_text

EXCERPT_LENGTH = 80


def active_world_id(db: Session) -> Optional[str]:
    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    return world.id if world is not None else None


def open_mention(db: Session, mention_id: str, world_id: str) -> Optional[UnresolvedMention]:
    """The open mention `mention_id` of `world_id`, or None (unknown, other
    world, or already closed)."""
    return db.exec(select(UnresolvedMention).where(
        UnresolvedMention.id == mention_id,
        UnresolvedMention.world_id == world_id,
        UnresolvedMention.resolved_at.is_(None),
    )).first()


def binding_is_valid(db: Session, mention: UnresolvedMention, entity_id: str) -> bool:
    """`validate_binding` for the mention's category; any category when NULL."""
    categories = (mention.category,) if mention.category else CATEGORIES
    return any(validate_binding(entity_id, c, mention.world_id, db) for c in categories)


def entity_is_valid(db: Session, world_id: str, entity_id: str) -> bool:
    """True iff `entity_id` is an active entity of `world_id`, any category."""
    return any(validate_binding(entity_id, c, world_id, db) for c in CATEGORIES)


def excerpt(text: Optional[str], surface: str) -> str:
    """Up to `EXCERPT_LENGTH` characters of `text` around the first
    occurrence of `surface` (its start when absent)."""
    text = text or ""
    at = text.find(surface)
    if at == -1:
        at = text.casefold().find(surface.casefold())
    if len(text) <= EXCERPT_LENGTH:
        return text
    start = max(0, at - (EXCERPT_LENGTH - len(surface)) // 2) if at != -1 else 0
    start = min(start, len(text) - EXCERPT_LENGTH)
    return text[start:start + EXCERPT_LENGTH]


def _named_ids(db: Session, world_id: str, surface: str, categories: tuple[str, ...]) -> set[str]:
    ids: set[str] = set()
    for category in categories:
        ids.update(resolve_named(surface, category, world_id, db, scope=CREATOR).candidate_ids)
    return ids


def _described(db: Session, ids: set[str]) -> list[dict]:
    if not ids:
        return []
    entities = db.exec(select(Entity).where(Entity.id.in_(ids))).all()
    return sorted(({"id": e.id, "name": e.name, "type": e.type} for e in entities), key=lambda c: c["name"])


def _near(db: Session, world_id: str, surface: str, candidates: list[dict]) -> list[dict]:
    """C-11: near names of `surface`, the resolver's candidates excluded --
    display only, never a pick (N9b)."""
    exclude = frozenset(c["id"] for c in candidates)
    return [
        {"id": c.entity_id, "name": c.name, "type": c.entity_type, "score": c.score}
        for c in near_candidates(surface, world_id, db, scope=CREATOR, exclude_ids=exclude)
    ]


def _candidates(db: Session, mention: UnresolvedMention) -> list[dict]:
    categories = (mention.category,) if mention.category in CATEGORIES else CATEGORIES
    return _described(db, _named_ids(db, mention.world_id, mention.surface, categories))


def lookup_surface(db: Session, world_id: str, surface: str) -> dict:
    """C-11's lookup body: the resolver's candidates for `surface` over every
    category, sorted by name, and its near names excluding them."""
    candidates = _described(db, _named_ids(db, world_id, surface, CATEGORIES))
    return {"surface": surface, "candidates": candidates, "near": _near(db, world_id, surface, candidates)}


def _owner_text(db: Session, mention: UnresolvedMention) -> Optional[str]:
    if mention.fact_id:
        fact = db.get(Fact, mention.fact_id)
        return fact_text(db, fact) if fact is not None else None
    knowledge = db.get(Knowledge, mention.knowledge_id)
    return knowledge_text(db, knowledge) if knowledge is not None else None


def list_open_mentions(db: Session, world_id: str) -> list[dict]:
    """C-16's GET body rows: open mentions of `world_id`, oldest first."""
    rows = db.exec(select(UnresolvedMention).where(
        UnresolvedMention.world_id == world_id,
        UnresolvedMention.resolved_at.is_(None),
    ).order_by(UnresolvedMention.created_at, UnresolvedMention.id)).all()
    return [
        {
            "id": m.id,
            "surface": m.surface,
            "reason": m.reason,
            "category": m.category,
            "excerpt": excerpt(_owner_text(db, m), m.surface),
            "owner": {"kind": "fact", "id": m.fact_id} if m.fact_id else {"kind": "knowledge", "id": m.knowledge_id},
            "candidates": candidates,
            "near": _near(db, world_id, m.surface, candidates),
        }
        for m, candidates in ((m, _candidates(db, m)) for m in rows)
    ]
