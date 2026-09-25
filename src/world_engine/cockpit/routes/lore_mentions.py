"""Name-resolution panel routes (TICKET-0091, BRIEF-0091-K, contract C-16,
decision Q17d).

The bounded reopening of the Lore shell's read-only lock: the creator binds
a name left plain in canon prose to an entity, or dismisses it, and may
record a missed name as an appellation (BRIEF-0092-d). Every read lives in
`lore_mentions_read.py`; every write goes through
`writes/mentions.py::bind_mention` (`update_fact_content` /
`write_knowledge`), `dismiss_mention` or
`writes/facets.py::record_appellation`, one commit per request. The
consultation pipeline is untouched: this module imports none of
`lore_selectors`, `lore_query`, `lore_plan`, `lore_render`, `lore_prompt`
(`lore_isolation.py` R17). Guarded exactly as Creation is (no route
authentication, R-27).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import lore_mentions_read as _read
from ...db import get_session
from ...writes.facets import record_appellation
from ...writes.mentions import bind_mention, dismiss_mention

router = APIRouter()

_CHANGED_BY = "creator_crud"


class MentionResolveBody(BaseModel):
    entity_id: str
    record_appellation: bool = False
    scope_type: str = "rencontre"


class AppellationBody(BaseModel):
    entity_id: str
    surface: str
    scope_type: str = "rencontre"


def _world_id(db: Session) -> str:
    world_id = _read.active_world_id(db)
    if world_id is None:
        raise HTTPException(status_code=400, detail="No active world. Activate a world before proceeding.")
    return world_id


def _open_or_404(db: Session, mention_id: str):
    mention = _read.open_mention(db, mention_id, _world_id(db))
    if mention is None:
        raise HTTPException(status_code=404, detail=f"open mention {mention_id!r} not found")
    return mention


@router.get("/api/lore/mentions")
def list_mentions(db: Session = Depends(get_session)) -> dict:
    return {"mentions": _read.list_open_mentions(db, _world_id(db))}


@router.post("/api/lore/mentions/{mention_id}/resolve")
def resolve_mention_route(mention_id: str, body: MentionResolveBody, db: Session = Depends(get_session)) -> dict:
    mention = _open_or_404(db, mention_id)
    if not _read.binding_is_valid(db, mention, body.entity_id):
        raise HTTPException(status_code=422, detail="entity_id is not an active entity of this category in the world")
    surface = mention.surface
    written = None
    try:
        bind_mention(db, mention=mention, entity_id=body.entity_id, changed_by=_CHANGED_BY)
        if body.record_appellation:
            written = record_appellation(db, entity_id=body.entity_id, surface=surface,
                                         scope_type=body.scope_type, created_by=_CHANGED_BY)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"ok": True, "id": mention_id, "appellation_written": written is not None}


@router.get("/api/lore/names/lookup")
def lookup_name(surface: str, db: Session = Depends(get_session)) -> dict:
    surface = surface.strip()
    if not surface:
        raise HTTPException(status_code=422, detail="surface is empty")
    return _read.lookup_surface(db, _world_id(db), surface)


@router.post("/api/lore/appellations")
def record_appellation_route(body: AppellationBody, db: Session = Depends(get_session)) -> dict:
    if not _read.entity_is_valid(db, _world_id(db), body.entity_id):
        raise HTTPException(status_code=422, detail="entity_id is not an active entity of the world")
    try:
        fact = record_appellation(db, entity_id=body.entity_id, surface=body.surface,
                                  scope_type=body.scope_type, created_by=_CHANGED_BY)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"ok": True, "written": fact is not None, "fact_id": fact.id if fact is not None else None}


@router.post("/api/lore/mentions/{mention_id}/dismiss")
def dismiss_mention_route(mention_id: str, db: Session = Depends(get_session)) -> dict:
    mention = _open_or_404(db, mention_id)
    dismiss_mention(db, mention=mention)
    db.commit()
    return {"ok": True, "id": mention_id}
