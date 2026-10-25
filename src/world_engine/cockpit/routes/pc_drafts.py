"""The creator's read of submitted character drafts (TICKET-0126, BRIEF-0126-I; W1'). Reads only; the review is TICKET-0129. Keyed by the active world, as every Création surface.

`GET /api/pc-drafts` lists the active world's `submitted` drafts, by
submission date; `GET /api/pc-drafts/{id}` answers one with its whole
read shape (`pc_draft_reads.draft_view`, the creator's -- every entity
named), the verdict of its sheet (`creation_check`, INV-67), the names of
the start sheet's skills and the world's rank labels. A draft still being
written by its player is not shown. Nothing here writes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ...creation_check import check_creation, check_draft, verdict_dict
from ...creation_rules import start_sheet
from ...db import get_session
from ...models import PcDraft, PcDraftSkill, User
from ...pc_draft_reads import draft_view
from ...skill_ranks import world_ladder
from ..crud._shared import _world_id

router = APIRouter()

DRAFT_NOT_FOUND = "Brouillon introuvable."


def _player_name(db: Session, draft: PcDraft) -> str | None:
    user = db.get(User, draft.user_id)
    return user.name if user is not None else None


@router.get("/api/pc-drafts")
def list_submitted_drafts(db: Session = Depends(get_session)) -> list[dict]:
    world_id = _world_id(db)
    drafts = db.exec(
        select(PcDraft).where(PcDraft.world_id == world_id, PcDraft.status == "submitted")
        .order_by(PcDraft.submitted_at, PcDraft.id)
    ).all()
    return [
        {"id": d.id, "name": d.name, "player_name": _player_name(db, d),
         "submitted_at": d.submitted_at.isoformat() if d.submitted_at is not None else None}
        for d in drafts
    ]


@router.get("/api/pc-drafts/{draft_id}")
def get_submitted_draft(draft_id: str, db: Session = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    draft = db.get(PcDraft, draft_id)
    if draft is None or draft.world_id != world_id or draft.status != "submitted":
        raise HTTPException(status_code=404, detail=DRAFT_NOT_FOUND)
    rows = db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all()
    choices = {row.skill_key: row.player_rank for row in rows if row.player_rank is not None}
    verdict = check_creation(db, world_id, choices, enforce_visibility=True)
    return {
        "draft": draft_view(db, draft, view=None),
        "player_name": _player_name(db, draft),
        "verdict": verdict_dict(verdict, check_draft(db, draft)),
        "skill_names": {line.skill_key: line.name for line in start_sheet(db, world_id)},
        "ranks": [step.label for step in world_ladder(db, world_id)],
    }
