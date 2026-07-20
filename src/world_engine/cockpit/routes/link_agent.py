"""NPC link agent — batch staging lifecycle, pair-pass, coherence pass and
commit routes (TICKET-0036, BRIEF-0036-a/b/c).

Creator-surface only. This module is a thin HTTP wrapper: every canon write
happens inside `link_author.apply_finding`/`commit_batch`, which route
exclusively through `write_relation`/`write_knowledge` — nothing here calls
those helpers, or touches `Relation`/`Knowledge` model classes, directly
(`link_agent_strata.py` enforces via AST scan). `link_batch`/`link_batch_row`
stay ephemeral stratum (models/ephemeral.py NOTE), never a
`proposed_mutation`, never routed through `writes/`. The frontend loop
(0036-d) drives pair-pass repetition; no server-side loop here either.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ...db import get_session
from ...link_author import (
    apply_finding,
    commit_batch,
    journal_append,
    pending_pairs,
    resolve_roster,
    run_coherence,
    run_pair,
)
from ...models import LinkBatch, LinkBatchRow
from .. import crud as _crud

router = APIRouter()


class LinkBatchRosterBody(BaseModel):
    root_location_ids: list[str]


def _open_batch(world_id: str, db: Session) -> LinkBatch | None:
    return db.exec(
        select(LinkBatch)
        .where(LinkBatch.world_id == world_id)
        .where(LinkBatch.status == "open")
    ).first()


@router.post("/api/link-batches/preview")
def preview_link_batch(
    body: LinkBatchRosterBody,
    db: Session = Depends(get_session),
) -> dict:
    """Roster preview for a candidate root-location set — read-only, no
    batch created (S1: pair count surfaced for confirmation before
    launch)."""
    return resolve_roster(db, body.root_location_ids)


@router.post("/api/link-batches")
def create_link_batch(
    body: LinkBatchRosterBody,
    db: Session = Depends(get_session),
) -> dict:
    """Open a new batch from the resolved roster. Refuses (409) if another
    batch of this world is already open — one open batch at a time. Pair
    enumeration and F1 filtering happen at run time in 0036-b, not here."""
    world_id = _crud._world_id(db)
    if _open_batch(world_id, db) is not None:
        raise HTTPException(status_code=409, detail="a link batch is already open for this world")

    roster = resolve_roster(db, body.root_location_ids)
    batch = LinkBatch(
        world_id=world_id,
        scope={
            "root_location_ids": body.root_location_ids,
            "expanded_location_ids": roster["expanded_location_ids"],
            "npc_ids": [npc["id"] for npc in roster["npcs"]],
            "pair_count": roster["pair_count"],
        },
        pairs_total=roster["pair_count"],
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    journal_append(batch.id, {"event": "batch_created", "scope": batch.scope})
    return batch.model_dump()


@router.get("/api/link-batches")
def list_link_batches(db: Session = Depends(get_session)) -> dict:
    """The open batch (if any) plus every closed batch still retained
    (last-2 purge runs at startup, not here)."""
    world_id = _crud._world_id(db)
    batches = db.exec(
        select(LinkBatch)
        .where(LinkBatch.world_id == world_id)
        .order_by(LinkBatch.created_at.desc())
    ).all()
    return {"batches": [b.model_dump() for b in batches]}


@router.get("/api/link-batches/{batch_id}")
def get_link_batch(batch_id: str, db: Session = Depends(get_session)) -> dict:
    batch = db.get(LinkBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"link batch {batch_id!r} not found")
    rows = db.exec(
        select(LinkBatchRow).where(LinkBatchRow.batch_id == batch_id)
    ).all()
    return {"batch": batch.model_dump(), "rows": [r.model_dump() for r in rows]}


@router.post("/api/link-batches/{batch_id}/abandon")
def abandon_link_batch(batch_id: str, db: Session = Depends(get_session)) -> dict:
    batch = db.get(LinkBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"link batch {batch_id!r} not found")
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"link batch {batch_id!r} is not open")

    batch.status = "abandoned"
    batch.closed_at = datetime.now(UTC)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    journal_append(batch.id, {"event": "batch_abandoned"})
    return batch.model_dump()


@router.post("/api/link-batches/{batch_id}/run-next")
def run_next_pair(batch_id: str, db: Session = Depends(get_session)) -> dict:
    """Process exactly ONE pending pair (BRIEF-0036-b) and return progress.
    Pending is recomputed from scratch every call (F1 exclusion + rows
    already staged in this batch) — resume-after-restart is free. Returns
    {done: true} once nothing is pending; refuses on a non-open batch."""
    batch = db.get(LinkBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"link batch {batch_id!r} not found")
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"link batch {batch_id!r} is not open")

    pending = pending_pairs(db, batch)
    if not pending:
        return {"done": True}

    a_id, b_id = pending[0]
    result = run_pair(db, batch, a_id, b_id)
    return {
        "pairs_done": batch.pairs_done,
        "pairs_total": batch.pairs_total,
        "last_pair": {"a": a_id, "b": b_id, "verdict": result["verdict"], "row_count": result["row_count"]},
    }


def _get_batch_or_404(batch_id: str, db: Session) -> LinkBatch:
    batch = db.get(LinkBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"link batch {batch_id!r} not found")
    return batch


@router.post("/api/link-batches/{batch_id}/coherence")
def run_batch_coherence(batch_id: str, db: Session = Depends(get_session)) -> dict:
    """Mechanical (phase 1) + model (phase 2) coherence pass over the
    staged batch and the full canon character graph (BRIEF-0036-c)."""
    batch = _get_batch_or_404(batch_id, db)
    return run_coherence(db, batch)


@router.post("/api/link-batches/{batch_id}/findings/{index}/apply")
def apply_batch_finding(batch_id: str, index: int, db: Session = Depends(get_session)) -> dict:
    """Applies one pre-validated (validation='valid') coherence finding's
    patch — one click, one finding. Re-validates at time-of-use."""
    batch = _get_batch_or_404(batch_id, db)
    return apply_finding(db, batch, index)


@router.post("/api/link-batches/{batch_id}/commit")
def commit_batch_route(batch_id: str, db: Session = Depends(get_session)) -> dict:
    """Commits every non-rejected staged row to canon (write_relation /
    write_knowledge). Refuses if coherence never ran on this batch."""
    batch = _get_batch_or_404(batch_id, db)
    return commit_batch(db, batch)
