"""Facts nobody is attached to (TICKET-0097, decisions I1 and J1) — the read
behind Creation's « Sujets » panel.

One row per free fact (no `relation_id` / `event_id` / `world_law_id`: a
typed fact takes no participant) that a `knowledge` row of the world knows
and that carries no `fact_participant` at all. Each row shows the fact's
text, the version of its first knower by name (J1), how many entities know
it, and the Lore resolver's reading of the fact's text
(`lore_mentions_read.lookup_surface`: names and appellations of every
category, the partial rung, near names) — the creator binds, the resolver
never picks. Read-only: no `db.add`, no commit, no model call.

Replaces `subject_resolve.py` (N10a fired with Q1b): there is no subject
left to resolve, and one name resolver serves the whole tool.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .lore_mentions_read import lookup_surface
from .models import Entity, Fact, FactParticipant, Knowledge
from .prose_render import fact_texts, knowledge_texts

EXCERPT_CHARS = 120


def _clip(text: str) -> str:
    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rstrip() + "…"


def _unbound_rows(world_id: str, db: Session) -> dict[str, list[tuple[Knowledge, Entity]]]:
    """fact id -> its (knowledge row, knower) pairs, for every free fact of
    `world_id` known by someone and bound to no participant."""
    rows = db.exec(
        select(Knowledge, Entity, FactParticipant.id)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .join(Fact, Fact.id == Knowledge.fact_id)
        .outerjoin(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
        .where(
            Entity.world_id == world_id,
            Fact.relation_id.is_(None), Fact.event_id.is_(None), Fact.world_law_id.is_(None),
        )
    ).all()
    grouped: dict[str, list[tuple[Knowledge, Entity]]] = {}
    for knowledge, knower, participant_id in rows:
        if participant_id is None:
            grouped.setdefault(knowledge.fact_id, []).append((knowledge, knower))
    return grouped


def unbound_facts(world_id: str, db: Session) -> list[dict]:
    """C-08. Ordered by knower count descending, then fact text."""
    grouped = _unbound_rows(world_id, db)
    facts = [db.get(Fact, fact_id) for fact_id in grouped]
    result = []
    for fact, text in zip(facts, fact_texts(db, facts)):
        knowers = sorted(grouped[fact.id], key=lambda pair: (pair[1].name.casefold(), pair[1].id))
        first_row, first_knower = knowers[0]
        first_text = knowledge_texts(db, [first_row])[0]
        lookup = lookup_surface(db, world_id, text)
        result.append({
            "fact_id": fact.id,
            "fact": text,
            "knower_count": len(knowers),
            "excerpt": (
                {"entity_name": first_knower.name, "text": _clip(first_text)} if first_text else None
            ),
            "candidates": lookup["candidates"],
            "near": lookup["near"],
        })
    result.sort(key=lambda row: (-row["knower_count"], row["fact"].casefold(), row["fact_id"]))
    return result
