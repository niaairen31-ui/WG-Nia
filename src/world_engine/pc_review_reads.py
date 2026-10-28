"""The creator's review of a character draft, as the screens read it (TICKET-0129, BRIEF-0129-C). Reads only.

`review_view` answers the creator's choices on a draft (C-07) -- her
starting place, each sketch's action, character, relation type and
intensity, each membership's drop -- apart from `pc_draft_reads.draft_view`,
the shape the player shares: the player never reads a review column (C1).
`review_choices` answers her pick lists: the world's places that are not a
zone, its non-player characters, the Maîtres of each master sketch's skill.
Every entity is named: the review reads all the lore. No write, no flush,
no commit, no model call.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .creation_check import review_place_id
from .models import BASE_SKILL_DOMAINS, Character, Entity, PcDraft, PcDraftMembership, PcDraftSketch
from .skill_access import skill_masters
from .zone_rules import zone_ids


def _entity(db: Session, entity_id: Optional[str]) -> Optional[dict]:
    if entity_id is None:
        return None
    entity = db.get(Entity, entity_id)
    return {"entity_id": entity_id, "name": entity.name if entity is not None else None}


def _sketches(db: Session, draft: PcDraft) -> list[PcDraftSketch]:
    return list(db.exec(select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)
                        .order_by(PcDraftSketch.position, PcDraftSketch.id)).all())


def review_view(db: Session, draft: PcDraft) -> dict:
    """The creator's choices on `draft` (C-07)."""
    memberships = db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id)
                          .order_by(PcDraftMembership.id)).all()
    return {
        "review_location": _entity(db, draft.review_location_id),
        "place": _entity(db, review_place_id(draft)),
        "character_id": draft.character_id,
        "sketches": [
            {"id": s.id, "action": s.review_action, "entity": _entity(db, s.review_entity_id),
             "relation_type": s.review_relation_type, "intensity": s.review_intensity}
            for s in _sketches(db, draft)
        ],
        "memberships": [{"id": m.id, "dropped": m.review_dropped} for m in memberships],
    }


def _named(rows) -> list[dict]:
    return [{"entity_id": e.id, "name": e.name} for e in sorted(rows, key=lambda e: (e.name, e.id))]


def review_choices(db: Session, draft: PcDraft) -> dict:
    """The creator's pick lists for `draft` (C-07)."""
    world_id = draft.world_id
    zones = zone_ids(db, world_id)
    places = db.exec(select(Entity).where(
        Entity.world_id == world_id, Entity.type == "location", Entity.status == "active",
    )).all()
    characters = db.exec(
        select(Entity).join(Character, Character.id == Entity.id).where(
            Entity.world_id == world_id, Entity.type == "character", Entity.status == "active",
            Character.character_type != "player",
        )
    ).all()
    masters: dict[str, list[dict]] = {}
    for sketch in _sketches(db, draft):
        if sketch.kind != "master" or sketch.skill_key is None or sketch.skill_key in masters:
            continue
        if sketch.skill_key in BASE_SKILL_DOMAINS:
            masters[sketch.skill_key] = skill_masters(db, world_id, definition_id=None, domain=sketch.skill_key)
        else:
            masters[sketch.skill_key] = skill_masters(db, world_id, definition_id=sketch.skill_key, domain=None)
    return {
        "places": _named(e for e in places if e.id not in zones),
        "characters": _named(characters),
        "masters": masters,
    }
