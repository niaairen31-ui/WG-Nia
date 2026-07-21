"""NPC group agent — batch staging lifecycle, run driver, and commit routes
(TICKET-0037, BRIEF-0037-a/b/c).

Creator-surface only. Staging/run (BRIEF-0037-a/b) write no canon:
`npc_batch`/`npc_batch_row` stay ephemeral stratum (models/ephemeral.py
NOTE), never a `proposed_mutation`, never routed through `writes/`
(`npc_agent_strata.py` enforces). One open `npc_batch` per world — an open
`link_batch` does NOT block this route (each staging table enforces its own
singleton, per-agent rule). The commit route (BRIEF-0037-c) is this module's
one canon-write site — a route-module function mirroring
`routes/regions.py::_commit_region_npcs`, NOT placed in `npc_group_author.py`
(same layering as the region commit: canon writes live route-side, the
author module stays generate-only). It rides exclusively the sanctioned
`_crud._create_entity_core` / `_crud._create_knowledge_core` /
`write_npc_goal` helpers — never a direct `db.add(Entity(...)/...)` — so no
new `canon_write_policy.txt` ALLOWED_SITES entry is needed (mirrors why
`_commit_region_npcs` itself isn't listed there either)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ...db import get_session
from ...models import NpcBatch, NpcBatchRow
from ...npc_group_author import journal_append, patch_npc_row, resolve_vocabulary, run_next_npc
from ...writes import write_npc_goal
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


def _commit_npc_row_goals(db: Session, world_id: str, npc_id: str, goals: dict | None) -> None:
    """Writes the row's attached goals block (long + shorts) via
    `write_npc_goal` — commit-free, same transaction as its NPC (G1)."""
    if not isinstance(goals, dict):
        return
    long_desc = (goals.get("long") or "").strip()
    if long_desc:
        write_npc_goal(
            db, world_id=world_id, npc_id=npc_id,
            description=long_desc, horizon="long", changed_by="creator",
        )
    for short_desc in (goals.get("shorts") or []):
        short_desc = (short_desc or "").strip()
        if short_desc:
            write_npc_goal(
                db, world_id=world_id, npc_id=npc_id,
                description=short_desc, horizon="short", changed_by="creator",
            )


def _commit_npc_row(row: NpcBatchRow, batch: NpcBatch, db: Session) -> dict:
    """Writes one staged row's NPC + knowledge + goals into canon — the
    `_commit_region_npcs` recipe, byte-same posture, adapted to a staged row
    instead of an untrusted client draft entry. Commit-free (caller's
    transaction); returns `{row_id, entity_id, name}`."""
    draft = row.payload["draft"]
    pub, sec = draft["public"], draft["secret"]
    entity_data = {
        "type": "character",
        "name": pub.get("name"),
        "description": pub.get("description"),
    }
    ext_data: dict = {
        "character_type": "npc",
        "appearance": pub.get("appearance"),
        "backstory": pub.get("backstory"),
        "aversion": pub.get("aversion"),
        "current_location_id": row.payload["location_id"],
        "secrets": json.dumps(sec["creator_meta"]) if sec.get("creator_meta") is not None else None,
    }
    if pub.get("physical_tier") is not None:
        ext_data["physical_tier"] = pub["physical_tier"]
    faction_id = pub.get("faction_id")
    if faction_id is not None:
        ext_data["faction_id"] = faction_id

    npc_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data)
    npc_entity = _crud._create_entity_core(npc_body, db)

    for k in (sec.get("knowledge") or []):
        k_body = _crud.KnowledgeWriteBody(
            subject=k.get("subject"),
            level=k.get("level"),
            content=k.get("content"),
            source=None,
            is_incorrect=False,
            is_secret=True,
            share_threshold=50,
        )
        _crud._create_knowledge_core(npc_entity.id, k_body, db)

    _commit_npc_row_goals(db, batch.world_id, npc_entity.id, row.payload.get("goals"))

    return {"row_id": row.id, "entity_id": npc_entity.id, "name": npc_entity.name}


def _commit_npc_batch(batch: NpcBatch, db: Session) -> dict:
    """Atomic NPC batch commit (BRIEF-0037-c) — mirror of `regions.py::
    commit_region`'s transaction shape (try/rollback, exactly one
    `db.commit()`), NPC writes delegated to `_commit_npc_row`.

    Guards: batch must be `open` (409); the count contract must hold —
    `npcs_done == npcs_total` (409, "generation incomplete — run or
    abandon") — no partial commit (Scope OUT). No coherence gate (I1).

    Server-authoritative: rows are re-read from the DB by `row_status`,
    never trusted from client state. Rows `row_status in ("proposed",
    "edited")` commit; `rejected` rows (excluded by the query) and
    `kind == "failed"` rows write nothing. Any exception rolls back the
    whole batch — zero canon rows survive a mid-commit failure.
    """
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"NPC batch {batch.id!r} is not open")
    if batch.npcs_done != batch.npcs_total:
        raise HTTPException(status_code=409, detail="generation incomplete — run or abandon")

    rows = db.exec(
        select(NpcBatchRow)
        .where(NpcBatchRow.batch_id == batch.id)
        .where(NpcBatchRow.row_status.in_(("proposed", "edited")))
    ).all()

    committed: list[dict] = []
    skipped: list[dict] = []
    now = datetime.now(UTC)

    try:
        for row in rows:
            if row.kind == "failed":
                skipped.append({"row_id": row.id, "reason": "failed row"})
                continue
            committed.append(_commit_npc_row(row, batch, db))
            row.row_status = "committed"
            row.updated_at = now
            db.add(row)

        batch.status = "committed"
        batch.closed_at = now
        db.add(batch)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise

    journal_append(batch.id, {"event": "commit", "committed": committed, "skipped": skipped})
    return {"committed": committed, "skipped": skipped}


@router.post("/api/npc-batches/{batch_id}/commit")
def commit_npc_batch_route(batch_id: str, db: Session = Depends(get_session)) -> dict:
    batch = db.get(NpcBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"NPC batch {batch_id!r} not found")
    return _commit_npc_batch(batch, db)
