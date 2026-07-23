"""Room batch generation + commit routes (TICKET-0042).

Read routes (BRIEF-0042-d) are thin wrappers over room_batch_author's three
phases -- same no-canon-write neighbourhood as /api/regions/manifest and
/api/regions/generate (regions.py). The commit route (BRIEF-0042-e) is the
SOLE canon-write path for a batch, posture identical to commit_region: the
client is untrusted, the parent cascade is re-derived server-side, doors
materialize through spatial_author.connect_locations, and the whole batch
commits in one transaction with full rollback on any exception.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from ...db import get_session
from ...room_batch_author import generate_room_batch_draft as _generate_room_batch_draft
from ...room_batch_author import generate_room_batch_manifest as _generate_room_batch_manifest
from ...room_batch_author import propose_batch_coherence as _propose_batch_coherence

router = APIRouter()


class RoomBatchManifestBody(BaseModel):
    anchor_id: str
    count: int


@router.post("/api/room-batch/manifest")
def generate_room_batch_manifest_route(
    body: RoomBatchManifestBody,
    db: Session = Depends(get_session),
) -> dict:
    """Phase A (BRIEF-0042-a) -- writes no canon."""
    return _generate_room_batch_manifest(body.anchor_id, body.count, db)


class RoomBatchDraftBody(BaseModel):
    manifest: dict[str, Any]
    anchor: dict[str, Any]


@router.post("/api/room-batch/draft")
def generate_room_batch_draft_route(
    body: RoomBatchDraftBody,
    db: Session = Depends(get_session),
) -> dict:
    """Phase B (BRIEF-0042-b) -- writes no canon."""
    return _generate_room_batch_draft(body.manifest, body.anchor, db)


class RoomBatchCoherenceBody(BaseModel):
    manifest: dict[str, Any]
    drafts: dict[str, Any]
    anchor: dict[str, Any]


@router.post("/api/room-batch/coherence")
def propose_batch_coherence_route(
    body: RoomBatchCoherenceBody,
    db: Session = Depends(get_session),
) -> dict:
    """Phase C (BRIEF-0042-c) -- writes no canon."""
    return _propose_batch_coherence(body.manifest, body.drafts, body.anchor, db)
