"""The read shape of a character draft, for the player (through the public view) and for the creator (TICKET-0126, BRIEF-0126-G). Reads only.

`draft_view` answers one draft with its skills, people, factions and
knowledge (C-13). Given a `PublicView` -- the player's door -- an entity
the draft points at that is not in the view is answered with no name
(INV-66); without one -- the creator's -- it is named. `open_draft_of`
finds a user's not yet approved draft of a world. No write, no flush, no
commit, no model call.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Entity, PcDraft, PcDraftKnowledge, PcDraftMembership, PcDraftSketch, PcDraftSkill
from .perspective_selectors import PublicView


def _name(db: Session, entity_id: Optional[str], view: Optional[PublicView]) -> Optional[str]:
    if entity_id is None or (view is not None and entity_id not in view.entity_ids):
        return None
    entity = db.get(Entity, entity_id)
    return entity.name if entity is not None else None


def _entity(db: Session, entity_id: Optional[str], view: Optional[PublicView]) -> Optional[dict]:
    if entity_id is None:
        return None
    return {"entity_id": entity_id, "name": _name(db, entity_id, view)}


def draft_view(db: Session, draft: PcDraft, *, view: Optional[PublicView]) -> dict:
    """The draft as the screens read it (C-13)."""
    skills = db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)
                     .order_by(PcDraftSkill.skill_key)).all()
    sketches = db.exec(select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)
                       .order_by(PcDraftSketch.position, PcDraftSketch.id)).all()
    memberships = db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id)).all()
    knowledge = db.exec(select(PcDraftKnowledge).where(PcDraftKnowledge.draft_id == draft.id)
                        .order_by(PcDraftKnowledge.position, PcDraftKnowledge.id)).all()
    membership_rows = [
        {"id": m.id, "faction_id": m.faction_id, "faction_name": _name(db, m.faction_id, view),
         "role": m.role, "origin": m.origin}
        for m in memberships
    ]
    membership_rows.sort(key=lambda m: (m["faction_name"] is None, m["faction_name"] or "", m["id"]))
    return {
        "id": draft.id,
        "world_id": draft.world_id,
        "status": draft.status,
        "name": draft.name,
        "story": draft.story,
        "start_location": _entity(db, draft.start_location_id, view),
        "start_location_set_by": draft.start_location_set_by,
        "creator_note": draft.creator_note,
        "submitted_at": draft.submitted_at.isoformat() if draft.submitted_at is not None else None,
        "skills": [
            {"skill_key": s.skill_key, "player_rank": s.player_rank, "designer_rank": s.designer_rank,
             "justification": s.justification, "designer_reason": s.designer_reason}
            for s in skills
        ],
        "sketches": [
            {"id": s.id, "position": s.position, "name": s.name, "role": s.role, "sentence": s.sentence,
             "group_label": s.group_label, "kind": s.kind, "skill_key": s.skill_key,
             "existing_entity": _entity(db, s.existing_entity_id, view), "origin": s.origin}
            for s in sketches
        ],
        "memberships": membership_rows,
        "knowledge": [
            {"id": k.id, "position": k.position, "level": k.level, "content": k.content, "origin": k.origin}
            for k in knowledge
        ],
    }


def open_draft_of(db: Session, *, world_id: str, user_id: str) -> Optional[PcDraft]:
    """The user's not yet approved draft of the world, or None."""
    return db.exec(select(PcDraft).where(
        PcDraft.world_id == world_id, PcDraft.user_id == user_id, PcDraft.status != "approved",
    )).first()
