"""The lore a quest designer is shown before it designs: what canon already holds on the request's subject.

Gathers, read-only, the facts reachable by the request's words (`facts_mentioning`), by the entities it
names, and by a Lore entry it was written from, with who knows each one. It runs on the creator regime
of INV-01: creator-only facts are included and marked, never withheld -- the designer is a creator
surface. Its only caller is the quest designer (BRIEF-0121-E); no play assembler reaches it.

(TICKET-0121, BRIEF-0121-C, C-05.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .facet_reads import creator_only_fact_ids
from .lore_resolve import CATEGORIES, resolve_named
from .lore_selectors import facts_mentioning
from .models import Entity, Fact, FactParticipant, Knowledge, LoreEntry, LoreEntryRow
from .name_index import CREATOR
from .prose_render import fact_texts
from .writes.knowledge import knowledge_level_rank

CREATOR_ONLY_SUFFIX = " (réservé à la créatrice)"


@dataclass(frozen=True)
class LoreGathering:
    fact_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    lines: tuple[str, ...]
    empty: bool


def _resolved_entity_ids(
    db: Session, world_id: str, entity_ids: tuple[str, ...], names: list[str],
) -> tuple[str, ...]:
    """`entity_ids` given, then each name that resolves to exactly one entity;
    an ambiguous or unmatched name is skipped -- the designer sees what is
    certain. A name is tried in every category (`other` alone claims no
    character, place, faction or item): it is certain only when one entity
    matches across all of them."""
    resolved: list[str] = list(entity_ids)
    for name in names:
        candidates: set[str] = set()
        ambiguous = False
        for category in CATEGORIES:
            resolution = resolve_named(name, category, world_id, db, scope=CREATOR)
            if resolution.verdict == "matched":
                candidates.add(resolution.entity_id)
            elif resolution.verdict == "ambiguous":
                ambiguous = True
        if len(candidates) == 1 and not ambiguous:
            resolved.append(next(iter(candidates)))
    return tuple(dict.fromkeys(resolved))


def _mentioned_fact_ids(db: Session, world_id: str, keywords: list[str]) -> list[str]:
    """The facts holding all the keywords; each keyword on its own when the
    joined call finds nothing."""
    words = [k for k in keywords if k and k.strip()]
    if not words:
        return []

    def ids_of(text: str) -> list[str]:
        return [
            row["fact_id"] for row in facts_mentioning(text, world_id, db)
            if row.get("section") == "mentions"
        ]

    found = ids_of(" ".join(words))
    if found:
        return found
    return [fact_id for word in words for fact_id in ids_of(word)]


def _entity_fact_ids(db: Session, world_id: str, entity_ids: tuple[str, ...]) -> list[str]:
    if not entity_ids:
        return []
    rows = db.exec(
        select(Fact.id)
        .join(FactParticipant, FactParticipant.fact_id == Fact.id)
        .where(Fact.world_id == world_id, FactParticipant.entity_id.in_(entity_ids))
        .order_by(Fact.created_at, Fact.id)
    ).all()
    return list(rows)


def _entry_fact_ids(db: Session, world_id: str, lore_entry_id: Optional[str]) -> list[str]:
    if lore_entry_id is None:
        return []
    entry = db.get(LoreEntry, lore_entry_id)
    if entry is None or entry.world_id != world_id:
        return []
    rows = db.exec(
        select(Fact.id)
        .join(LoreEntryRow, LoreEntryRow.row_id == Fact.id)
        .where(
            LoreEntryRow.entry_id == lore_entry_id,
            LoreEntryRow.row_table == "fact",
            Fact.world_id == world_id,
        )
        .order_by(Fact.created_at, Fact.id)
    ).all()
    return list(rows)


def _lines(db: Session, world_id: str, fact_ids: tuple[str, ...]) -> tuple[str, ...]:
    facts = [db.get(Fact, fact_id) for fact_id in fact_ids]
    texts = fact_texts(db, facts)
    secret_ids = creator_only_fact_ids(db, fact_ids)
    knowers: dict[str, list[tuple[Knowledge, Entity]]] = {}
    for k, knower in db.exec(
        select(Knowledge, Entity)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .where(Entity.world_id == world_id, Knowledge.fact_id.in_(list(fact_ids)))
    ).all():
        knowers.setdefault(k.fact_id, []).append((k, knower))
    lines: list[str] = []
    for fact_id, text in zip(fact_ids, texts):
        holders = sorted(
            knowers.get(fact_id, []),
            key=lambda pair: (-knowledge_level_rank(pair[0].level), pair[1].name or ""),
        )
        if holders:
            who = "su par " + ", ".join(
                f"{knower.name} ({k.level}{', secret' if k.is_secret else ''})"
                for k, knower in holders
            )
        else:
            who = "su de personne"
        line = f"« {text} » -- {who}"
        if fact_id in secret_ids:
            line += CREATOR_ONLY_SUFFIX
        lines.append(line)
    return tuple(lines)


def gather_lore(
    db: Session, world_id: str, *, keywords: list[str], names: list[str],
    entity_ids: tuple[str, ...] = (), lore_entry_id: Optional[str] = None,
) -> LoreGathering:
    """What canon holds on the request, in a stable order: the facts mentioning
    the keywords, then the facts on each resolved entity, then the facts a Lore
    entry wrote; de-duplicated, one line each, who knows it named."""
    resolved = _resolved_entity_ids(db, world_id, entity_ids, names)
    ordered = (
        _mentioned_fact_ids(db, world_id, keywords)
        + _entity_fact_ids(db, world_id, resolved)
        + _entry_fact_ids(db, world_id, lore_entry_id)
    )
    fact_ids = tuple(dict.fromkeys(ordered))
    return LoreGathering(
        fact_ids=fact_ids, entity_ids=resolved,
        lines=_lines(db, world_id, fact_ids) if fact_ids else (),
        empty=not fact_ids,
    )
