"""Prompt dry-run preview routes (BRIEF-0008-b, C3): zero model calls, zero
writes, reuse the real context assemblers and the real system-prompt
construction so the preview never drifts from the live path.

Split out of `cockpit/app.py` (TICKET-0027, BRIEF-0027-d) — pure move, no
logic change, no route path/method change. `_npc_dialogue_system_prompt`
now lives in `cockpit/play.py` (its live call site); imported here for the
preview.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ...prompt_registry import PROMPT_REGISTRY
from ...prompt_store import current_prompt
from ...context import assemble_mj_context, assemble_npc_context, format_mj_context
from ...db import get_session
from ...models import Character, Entity, PromptTemplate
from .. import crud as _crud
from ..play import _npc_dialogue_system_prompt

router = APIRouter()


@router.get("/api/prompts/preview/npc_dialogue")
def preview_prompt_npc_dialogue(
    npc_id: str = Query(...),
    pc_id: str = Query(...),
    db: Session = Depends(get_session),
) -> dict:
    """Assembled dry-run preview (BRIEF-0008-b, C3) — the exact system prompt
    the real conversation-start path would build. Zero model calls, zero
    writes: no `conversation` row, no `injected_context` snapshot, no
    `change_history`. Reuses the real `assemble_npc_context` (never a
    reimplementation) and the extracted `_npc_dialogue_system_prompt`
    construction, so structural secret exclusion traverses the preview
    intact. Deliberately NOT in crud.py — same no-canon-write reasoning as
    `POST /api/entities/generate`.
    """
    npc_entity = db.get(Entity, npc_id)
    if npc_entity is None:
        raise HTTPException(status_code=404, detail=f"NPC {npc_id!r} not found")
    pc_entity = db.get(Entity, pc_id)
    if pc_entity is None:
        raise HTTPException(status_code=404, detail=f"Interlocutor {pc_id!r} not found")
    npc_char = db.get(Character, npc_id)
    location_id = npc_char.current_location_id if npc_char else None
    if not location_id:
        raise HTTPException(status_code=400, detail=f"NPC {npc_id!r} has no current location")

    world_id = _crud._world_id(db)
    spec = PROMPT_REGISTRY["npc_dialogue"]
    rows = db.exec(select(PromptTemplate).where(PromptTemplate.usage == "npc_dialogue")).all()
    behaviour = _crud._effective_prompt_row(rows, spec.world_scoped, world_id)
    if behaviour is None:
        raise HTTPException(status_code=503, detail="No active 'npc_dialogue' prompt template found.")

    assembled_context = assemble_npc_context(npc_id, pc_id, location_id, db)
    behaviour_version = current_prompt(db, behaviour)
    system_prompt = _npc_dialogue_system_prompt(behaviour_version.system_prompt, assembled_context)
    return {
        "prompt_template_id": behaviour.id,
        "npc_id": npc_id,
        "pc_id": pc_id,
        "location_id": location_id,
        "system_prompt": system_prompt,
    }


@router.get("/api/prompts/preview/player_narration")
def preview_prompt_player_narration(
    pc_id: str = Query(...),
    db: Session = Depends(get_session),
) -> dict:
    """Assembled dry-run preview (BRIEF-0008-b, C3) — the MJ context a
    `player_narration` turn actually renders. Zero model calls, zero writes.
    Reuses the real `assemble_mj_context` + `format_mj_context` (never a
    reimplementation) — the player's own knowledge (including `is_secret`
    rows) is present (MJ perception boundary, not the NPC secret boundary);
    other entities' secrets are excluded by the same query construction as
    live play.
    """
    pc_char = db.get(Character, pc_id)
    if pc_char is None or pc_char.character_type != "player":
        raise HTTPException(status_code=400, detail=f"{pc_id!r} is not a player character")
    location_id = pc_char.current_location_id
    if not location_id:
        raise HTTPException(status_code=400, detail="Player has no current location")

    world_id = _crud._world_id(db)
    spec = PROMPT_REGISTRY["player_narration"]
    rows = db.exec(select(PromptTemplate).where(PromptTemplate.usage == "player_narration")).all()
    mj_template = _crud._effective_prompt_row(rows, spec.world_scoped, world_id)
    if mj_template is None:
        raise HTTPException(status_code=503, detail="No active 'player_narration' prompt template found.")

    mj_context = assemble_mj_context(db, pc_id, location_id)
    mj_version = current_prompt(db, mj_template)
    return {
        "prompt_template_id": mj_template.id,
        "pc_id": pc_id,
        "location_id": location_id,
        "system_prompt": mj_version.system_prompt,
        "mj_context_rendered": format_mj_context(mj_context),
    }
