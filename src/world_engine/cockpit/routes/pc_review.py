"""The creator's review of a submitted character draft (TICKET-0129): her choices, the check of her final version, the return to the player, the approval. Keyed by the active world, as every Création surface.

`GET /api/pc-reviews/{id}` answers a submitted draft of the active world
whole (`pc_draft_reads.draft_view`, the creator's -- every entity named),
her choices beside it (`pc_review_reads.review_view`), her pick lists, the
verdict of her final version (`creation_check.check_review`, INV-67's
sibling) and the groups of people she creates. `PUT` writes her choices
(`writes/pc_drafts.save_review`); `POST .../renvoyer` sends the draft back
to its player with a note (`return_draft`), abandoning its review
batches. `POST .../lots` opens the review batch of one group of people to
create (`cockpit/pc_approval.prepare_group_lot`, BRIEF-0129-D). `POST
.../approuver` writes the draft to canon in one transaction
(`cockpit/pc_approval.approve_draft`, BRIEF-0129-E). Each write
commits once, then journals. A draft of another world, or not submitted,
answers 404.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ...creation_check import check_creation, check_review, verdict_dict
from ...creation_rules import start_sheet
from ...db import get_session
from ...models import PcDraft, PcDraftSkill, User
from ...npc_group_author import journal_append
from ...pc_draft_reads import draft_view
from ...pc_review_reads import review_choices, review_view
from ...relation_orientation import is_social
from ...skill_ranks import world_ladder
from ...writes.pc_drafts import DraftLocked, return_draft, save_review
from ..crud._shared import RELATION_TYPES, _world_id
from ..pc_approval import (
    APPROVAL_REFUSED, ApprovalRefused, abandon_review_lots, approve_draft, lot_view, open_review_lots,
    prepare_group_lot, review_blockers, review_groups,
)

router = APIRouter()

DRAFT_NOT_FOUND = "Brouillon introuvable."


class PcReviewSketchItem(BaseModel):
    id: str
    action: Optional[str] = None
    entity_id: Optional[str] = None
    relation_type: str = ""
    intensity: int = 60


class PcReviewMembershipItem(BaseModel):
    id: str
    dropped: bool = False


class PcReviewBody(BaseModel):
    review_location_id: Optional[str] = None
    sketches: list[PcReviewSketchItem] = []
    memberships: list[PcReviewMembershipItem] = []


class PcReturnBody(BaseModel):
    note: str = ""


class PcLotBody(BaseModel):
    group_label: str = ""


def _submitted(draft_id: str, db: Session) -> PcDraft:
    """The active world's submitted draft `draft_id`, else 404."""
    world_id = _world_id(db)
    draft = db.get(PcDraft, draft_id)
    if draft is None or draft.world_id != world_id or draft.status != "submitted":
        raise HTTPException(status_code=404, detail=DRAFT_NOT_FOUND)
    return draft


def _player_name(db: Session, draft: PcDraft) -> str | None:
    user = db.get(User, draft.user_id)
    return user.name if user is not None else None


def _groups(db: Session, draft: PcDraft) -> list[dict]:
    """The groups of people the creator creates, each with its open review batch, if any."""
    lots = {batch.pc_group_label: lot_view(batch) for batch in open_review_lots(db, draft)}
    return [dict(group, lot=lots.get(group["label"])) for group in review_groups(db, draft)]


def _review_body(db: Session, draft: PcDraft) -> dict:
    world_id = draft.world_id
    rows = db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all()
    choices = {row.skill_key: row.player_rank for row in rows if row.player_rank is not None}
    verdict = check_creation(db, world_id, choices, enforce_visibility=True)
    return {
        "draft": draft_view(db, draft, view=None),
        "player_name": _player_name(db, draft),
        "review": review_view(db, draft),
        "choices": {**review_choices(db, draft),
                    "relation_types": [t for t in RELATION_TYPES if is_social(t)]},
        "verdict": verdict_dict(verdict, check_review(db, draft)),
        "skill_names": {line.skill_key: line.name for line in start_sheet(db, world_id)},
        "ranks": [step.label for step in world_ladder(db, world_id)],
        "groups": _groups(db, draft),
        "blockers": review_blockers(db, draft),
    }


@router.get("/api/pc-reviews/{draft_id}")
def get_review(draft_id: str, db: Session = Depends(get_session)) -> dict:
    return _review_body(db, _submitted(draft_id, db))


@router.put("/api/pc-reviews/{draft_id}")
def put_review(draft_id: str, body: PcReviewBody, db: Session = Depends(get_session)) -> dict:
    draft = _submitted(draft_id, db)
    try:
        save_review(db, draft, review_location_id=body.review_location_id,
                    sketches=[item.model_dump() for item in body.sketches],
                    memberships=[item.model_dump() for item in body.memberships])
    except DraftLocked as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(draft)
    return _review_body(db, draft)


@router.post("/api/pc-reviews/{draft_id}/renvoyer")
def return_review(draft_id: str, body: PcReturnBody, db: Session = Depends(get_session)) -> dict:
    draft = _submitted(draft_id, db)
    try:
        abandoned = abandon_review_lots(db, draft)
        return_draft(db, draft, note=body.note)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    for batch_id in abandoned:
        journal_append(batch_id, {"event": "batch_abandoned", "pc_draft_id": draft.id})
    return {"ok": True, "status": "returned"}


@router.post("/api/pc-reviews/{draft_id}/lots")
def create_review_lot(draft_id: str, body: PcLotBody, db: Session = Depends(get_session)) -> dict:
    draft = _submitted(draft_id, db)
    try:
        batch = prepare_group_lot(db, draft, body.group_label)
    except DraftLocked as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=DRAFT_NOT_FOUND) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(batch)
    journal_append(batch.id, {"event": "batch_created", "scope": batch.scope, "pc_draft_id": draft.id})
    return {"batch_id": batch.id, "npcs_total": batch.npcs_total}


@router.post("/api/pc-reviews/{draft_id}/approuver")
def approve_review(draft_id: str, db: Session = Depends(get_session)) -> dict:
    draft = _submitted(draft_id, db)
    try:
        written = approve_draft(db, draft)
    except (ApprovalRefused, DraftLocked) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=APPROVAL_REFUSED) from exc
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HTTPException:
        db.rollback()
        raise
    db.commit()
    for lot_id in written["lot_ids"]:
        journal_append(lot_id, {"event": "commit_by_approval", "pc_draft_id": draft_id,
                                "character_id": written["character_id"]})
    return {"ok": True, "character_id": written["character_id"], "name": written["name"]}
