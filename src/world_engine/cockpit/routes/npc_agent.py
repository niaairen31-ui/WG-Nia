"""NPC group agent — batch staging lifecycle routes (TICKET-0037,
BRIEF-0037-a).

Creator-surface only, staging-only this step: no generation call, no canon
write. `npc_batch`/`npc_batch_row` stay ephemeral stratum (models/ephemeral.py
NOTE), never a `proposed_mutation`, never routed through `writes/`
(`npc_agent_strata.py` enforces). One open `npc_batch` per world — an open
`link_batch` does NOT block this route (each staging table enforces its own
singleton, per-agent rule)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ...db import get_session
from ...models import NpcBatch, NpcBatchRow
from ...npc_group_author import journal_append, patch_npc_row, resolve_vocabulary, run_next_npc
from .. import crud as _crud

router = APIRouter()

_MAX_BATCH_SIZE = 30


class NpcBatchBody(BaseModel):
    root_location_id: str
    group_brief: str
    lines: list[dict]


class NpcRowPatchBody(BaseModel):
    payload_patch: dict | None = None
    row_status: str | None = None


def _open_batch(world_id: str, db: Session) -> NpcBatch | None:
    return db.exec(
        select(NpcBatch)
        .where(NpcBatch.world_id == world_id)
        .where(NpcBatch.status == "open")
    ).first()


@router.get("/api/npc-batches/preview")
def preview_npc_batch(root_location_id: str, db: Session = Depends(get_session)) -> dict:
    """Placement vocabulary for a candidate region root — read-only, no
    batch created (S1-preview posture, mirror of link_agent.py)."""
    return resolve_vocabulary(db, root_location_id)


@router.post("/api/npc-batches")
def create_npc_batch(body: NpcBatchBody, db: Session = Depends(get_session)) -> dict:
    """Open a new batch from the submitted spec lines. Refuses (409) if
    another `npc_batch` of this world is already open. Validates each line
    against the resolved placement vocabulary; generation happens at run
    time in BRIEF-0037-b, not here."""
    world_id = _crud._world_id(db)
    if _open_batch(world_id, db) is not None:
        raise HTTPException(status_code=409, detail="a NPC batch is already open for this world")

    vocabulary = resolve_vocabulary(db, body.root_location_id)
    valid_faction_ids = {f["id"] for f in vocabulary["factions"]}
    valid_location_ids = set(vocabulary["expanded_location_ids"])

    total = 0
    for line in body.lines:
        count = line.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise HTTPException(status_code=422, detail="chaque ligne doit avoir un count >= 1")
        description = line.get("description")
        if not isinstance(description, str) or not description.strip():
            raise HTTPException(status_code=422, detail="chaque ligne doit avoir une description non vide")
        faction_id = line.get("faction_id")
        if faction_id is not None and faction_id not in valid_faction_ids:
            raise HTTPException(status_code=422, detail=f"faction_id {faction_id!r} inconnue ou inactive")
        location_id = line.get("location_id")
        if location_id is not None and location_id not in valid_location_ids:
            raise HTTPException(status_code=422, detail=f"location_id {location_id!r} hors de la zone étendue")
        total += count

    if total > _MAX_BATCH_SIZE:
        raise HTTPException(status_code=422, detail="batch trop grand — 30 PNJ max")

    batch = NpcBatch(
        world_id=world_id,
        scope={
            "root_location_id": body.root_location_id,
            "expanded_location_ids": vocabulary["expanded_location_ids"],
            "lines": body.lines,
            "group_brief": body.group_brief,
        },
        npcs_total=total,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    journal_append(batch.id, {"event": "batch_created", "scope": batch.scope})
    return batch.model_dump()


@router.get("/api/npc-batches")
def list_npc_batches(db: Session = Depends(get_session)) -> dict:
    """The open batch (if any) plus every closed batch still retained
    (last-2 purge runs at startup, not here)."""
    world_id = _crud._world_id(db)
    batches = db.exec(
        select(NpcBatch)
        .where(NpcBatch.world_id == world_id)
        .order_by(NpcBatch.created_at.desc())
    ).all()
    return {"batches": [b.model_dump() for b in batches]}


@router.get("/api/npc-batches/{batch_id}")
def get_npc_batch(batch_id: str, db: Session = Depends(get_session)) -> dict:
    batch = db.get(NpcBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"NPC batch {batch_id!r} not found")
    rows = db.exec(
        select(NpcBatchRow).where(NpcBatchRow.batch_id == batch_id)
    ).all()
    return {"batch": batch.model_dump(), "rows": [r.model_dump() for r in rows]}


@router.post("/api/npc-batches/{batch_id}/abandon")
def abandon_npc_batch(batch_id: str, db: Session = Depends(get_session)) -> dict:
    batch = db.get(NpcBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"NPC batch {batch_id!r} not found")
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"NPC batch {batch_id!r} is not open")

    batch.status = "abandoned"
    batch.closed_at = datetime.now(UTC)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    journal_append(batch.id, {"event": "batch_abandoned"})
    return batch.model_dump()


@router.post("/api/npc-batches/{batch_id}/run-next")
def run_next_npc_batch(batch_id: str, db: Session = Depends(get_session)) -> dict:
    """Generate exactly one more NPC for this batch (H1 — exact count by
    construction). Backend only; the cockpit panel arrives in BRIEF-0037-c."""
    batch = db.get(NpcBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"NPC batch {batch_id!r} not found")
    return run_next_npc(db, batch)


@router.patch("/api/npc-batches/{batch_id}/rows/{row_id}")
def patch_npc_batch_row(
    batch_id: str, row_id: str, body: NpcRowPatchBody, db: Session = Depends(get_session)
) -> dict:
    """Inline creator review edit on one staged row — mirror of the link
    agent's row PATCH."""
    batch = db.get(NpcBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"NPC batch {batch_id!r} not found")
    return patch_npc_row(db, batch, row_id, body.payload_patch, body.row_status)
