"""The prose guard of a quest offer proposal (TICKET-0121, BRIEF-0121-E, V1, INV-63).

A player-visible field of a designer's offer (title, summary, objectives) must not repeat a secret
fact the designer read. `flags` finds, for each text and each fact, the first run of four or more
consecutive tokens they share; `secret_ids` names which of the facts read are secret. A paraphrase
passes: the creator's review stays the last barrier for prose. Pure reads, no model.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .facet_reads import creator_only_fact_ids
from .lore_resolve import normalize_surface
from .models import Entity, Fact, Knowledge
from .prose_render import fact_texts

MIN_RUN = 4


def _longest_first_run(text_tokens: list[str], fact_tokens: list[str]) -> list[str]:
    """The first run (in the text's order) of at least `MIN_RUN` tokens that
    is also a run of the fact; the whole maximal run from where it starts."""
    if len(text_tokens) < MIN_RUN or len(fact_tokens) < MIN_RUN:
        return []
    windows = {tuple(fact_tokens[i:i + MIN_RUN]) for i in range(len(fact_tokens) - MIN_RUN + 1)}
    for start in range(len(text_tokens) - MIN_RUN + 1):
        if tuple(text_tokens[start:start + MIN_RUN]) in windows:
            end = start + MIN_RUN
            while end < len(text_tokens) and any(
                fact_tokens[i:i + end - start + 1] == text_tokens[start:end + 1]
                for i in range(len(fact_tokens) - (end - start))
            ):
                end += 1
            return text_tokens[start:end]
    return []


def flags(db: Session, texts: dict[str, str], fact_ids: list[str]) -> list[dict]:
    """`[{path, fact_id, words}]`: for each `texts` path and each fact id, the
    first shared run of >= 4 tokens of their `normalize_surface` forms."""
    facts = [f for f in (db.get(Fact, fid) for fid in dict.fromkeys(fact_ids)) if f is not None]
    if not facts or not texts:
        return []
    fact_tokens = {f.id: normalize_surface(t).split() for f, t in zip(facts, fact_texts(db, facts))}
    found: list[dict] = []
    for path, text in texts.items():
        tokens = normalize_surface(text or "").split()
        for fact_id, shared in fact_tokens.items():
            words = _longest_first_run(tokens, shared)
            if words:
                found.append({"path": path, "fact_id": fact_id, "words": " ".join(words)})
    return found


def secret_ids(db: Session, world_id: str, fact_ids: list[str]) -> list[str]:
    """R-22: a fact is secret when it is creator-only, or when no entity of the
    world holds it on a non-secret row (a fact nobody knows is not public)."""
    ids = list(dict.fromkeys(fact_ids))
    if not ids:
        return []
    creator_only = creator_only_fact_ids(db, ids)
    public = set(db.exec(
        select(Knowledge.fact_id).join(Entity, Entity.id == Knowledge.entity_id)
        .where(Entity.world_id == world_id, Knowledge.fact_id.in_(ids), Knowledge.is_secret == False)  # noqa: E712
    ).all())
    return [fid for fid in ids if fid in creator_only or fid not in public]
