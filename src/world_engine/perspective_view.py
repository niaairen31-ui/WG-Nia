"""A character's perspective view: what one character knows of his world, and the player's own character (TICKET-0127, BRIEF-0127-B, C-03).

His facts are every fact `resolve_known_for_entity` resolves above
`unaware` for him, minus the creator's notes, and, at the player's door,
minus the facts his own knowledge row keeps secret. His entities are the
world's active entities that are public, himself, met, a faction he
openly belongs to, or a participant of one of his facts or of the event
behind one of them.
Read-only: no write, no commit, no model call.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .context import read_public_membership_faction_ids
from .creation_rules import visible_skill_ids
from .encounters import acquaintances
from .facet_reads import creator_only_fact_ids
from .knowledge_resolve import resolve_known_for_entity
from .models import Character, Entity, EventParticipant, Fact, FactParticipant, Knowledge, Skill
from .perspective_selectors import PERSPECTIVE_DOORS, Belief, PerspectiveView
from .prose_render import knowledge_texts

CERTAINTY_LABELS: dict[str, str] = {"rumor": "rumeur", "suspicious": "soupçon", "partial": "partiel"}


class UnknownCharacter(ValueError):
    """No active character of that id in that world."""


def _character_name(db: Session, world_id: str, character_id: str) -> str:
    row = db.exec(
        select(Entity.name)
        .join(Character, Character.id == Entity.id)
        .where(
            Character.id == character_id,
            Entity.id == character_id,
            Entity.world_id == world_id,
            Entity.status == "active",
        )
    ).first()
    if row is None:
        raise UnknownCharacter(character_id)
    return row


def _beliefs(db: Session, fact_ids: set[str], known: dict, stored: dict) -> dict:
    """Step 4: one `Belief` per id of `fact_ids`; a stored row without
    content renders `None` (`prose_render.knowledge_texts`)."""
    held = [stored[fid] for fid in sorted(fact_ids) if fid in stored]
    texts = dict(zip((row.fact_id for row in held), knowledge_texts(db, held)))
    beliefs = {}
    for fid in fact_ids:
        row = stored.get(fid)
        beliefs[fid] = Belief(
            text=texts.get(fid),
            as_of=known[fid].as_of,
            certainty=CERTAINTY_LABELS.get(known[fid].level),
            secret=bool(row.is_secret) if row is not None else False,
            incorrect=bool(row.is_incorrect) if row is not None else False,
        )
    return beliefs


def _entity_ids(db: Session, world_id: str, character_id: str, fact_ids: set[str],
                member_of: frozenset[str]) -> frozenset[str]:
    """Step 6: the world's active entities the character may name."""
    candidates = {character_id} | acquaintances(db, character_id) | set(member_of)
    if fact_ids:
        candidates |= set(db.exec(
            select(FactParticipant.entity_id).where(FactParticipant.fact_id.in_(fact_ids))
        ).all())
        candidates |= {eid for eid in db.exec(
            select(EventParticipant.entity_id)
            .join(Fact, Fact.event_id == EventParticipant.event_id)
            .where(Fact.id.in_(fact_ids))
        ).all() if eid is not None}
    rows = db.exec(
        select(Entity.id, Entity.is_public).where(Entity.world_id == world_id, Entity.status == "active")
    ).all()
    return frozenset(eid for eid, is_public in rows if is_public or eid in candidates)


def character_view(db: Session, world_id: str, character_id: str, *, door: str) -> PerspectiveView:
    """What `character_id` knows of `world_id`, seen through `door` (C-03)."""
    if door not in PERSPECTIVE_DOORS:
        raise ValueError(f"unknown perspective door {door!r}")
    name = _character_name(db, world_id, character_id)
    known = resolve_known_for_entity(db, character_id)
    stored = {row.fact_id: row for row in db.exec(
        select(Knowledge).where(Knowledge.entity_id == character_id)
    ).all()}
    fact_ids = set(known) - creator_only_fact_ids(db, known)
    if door == "player":
        fact_ids = {fid for fid in fact_ids if not (fid in stored and stored[fid].is_secret)}
    beliefs = _beliefs(db, fact_ids, known, stored)
    member_of = frozenset(read_public_membership_faction_ids(character_id, db))
    entity_ids = _entity_ids(db, world_id, character_id, fact_ids, member_of)
    held = {sid for sid in db.exec(
        select(Skill.skill_definition_id).where(Skill.character_id == character_id)
    ).all() if sid is not None}
    return PerspectiveView(
        world_id, frozenset(fact_ids), entity_ids, frozenset(visible_skill_ids(db, world_id) | held),
        kind="character", character_id=character_id, character_name=name, door=door,
        member_of=member_of, beliefs=beliefs,
    )


def player_character_of(db: Session, world_id: str, profile_id: str) -> Optional[tuple[str, str]]:
    """The `(id, name)` of the profile's active player character in the world, or None."""
    row = db.exec(
        select(Character.id, Entity.name)
        .join(Entity, Entity.id == Character.id)
        .where(
            Character.world_id == world_id,
            Character.user_id == profile_id,
            Character.character_type == "player",
            Entity.status == "active",
        )
    ).first()
    return (row[0], row[1]) if row is not None else None


def world_characters(db: Session, world_id: str) -> list[dict]:
    """Every active character of the world: players first, then by name, then id."""
    rows = db.exec(
        select(Character.id, Entity.name, Character.character_type)
        .join(Entity, Entity.id == Character.id)
        .where(Character.world_id == world_id, Entity.status == "active")
    ).all()
    ordered = sorted(rows, key=lambda r: (r[2] != "player", r[1], r[0]))
    return [{"id": cid, "name": name, "character_type": ctype} for cid, name, ctype in ordered]
