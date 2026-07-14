"""Author CRUD — knowledge editor (in-context), shared write rules with
`_apply_mutation` via `..writes.write_knowledge`.

Split out of `cockpit/crud.py` (TICKET-0027, BRIEF-0027-d) — pure move,
no logic change.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DbSession, select

from ...db import get_session
from ...entity_author import generate_npc_goals
from ...gathering import close_open_memberships
from ...ledger import get_balance, list_entries
from ...ollama_client import OllamaError, ping
from ...models import (
    Agenda,
    AgendaStep,
    BASE_SKILL_DOMAINS,
    Character,
    DiscoverableDetail,
    Entity,
    Event,
    EventEntity,
    Faction,
    FactionMembership,
    FactionRole,
    GoalAgendaLink,
    GoalPrerequisite,
    Item,
    Knowledge,
    Ledger,
    Location,
    LocationSubculture,
    NpcPrice,
    PromptTemplate,
    PromptVariable,
    ProposedMutation,
    Relation,
    Skill,
    SkillDefinition,
    World,
)
from ...prompt_registry import PROMPT_REGISTRY, effective_model
from ...prompt_store import current_prompt, get_version, list_versions
from ...tick import _EVENT_TYPES
from ...writes import (
    KNOWLEDGE_LEVELS,
    NPC_GOAL_HORIZONS,
    NPC_GOAL_PREREQUISITE_TYPES,
    PromptValidationError,
    detach_goal_agenda_link,
    write_agenda,
    write_agenda_status,
    write_agenda_step,
    write_agenda_step_status,
    write_event,
    write_event_update,
    write_faction_role,
    write_goal_agenda_link,
    write_knowledge,
    write_ledger_entry,
    write_location_subculture,
    write_membership,
    write_npc_goal,
    write_npc_goal_prerequisites,
    write_npc_goal_status,
    write_npc_prices,
    write_prompt_version,
    write_relation,
    write_skill_tier,
)

from ._router import router
from ._shared import (
    KNOWLEDGE_FIELDS,
    KNOWLEDGE_LEVELS_ORDERED,
    _get_entity,
    _iso,
    _knowledge_dict,
    _list_knowledge,
)


class KnowledgeWriteBody(BaseModel):
    subject: Optional[str] = None
    level: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    is_incorrect: bool = False
    is_secret: bool = False
    share_threshold: Optional[int] = None


@router.get("/entities/{entity_id}/knowledge")
def list_entity_knowledge(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    _get_entity(db, entity_id)
    return _list_knowledge(entity_id, db)


def _create_knowledge_core(entity_id: str, body: KnowledgeWriteBody, db: DbSession) -> Knowledge:
    """Commit-free core of `create_knowledge` — adds, never commits (BRIEF-35)."""
    _get_entity(db, entity_id)
    if not body.subject:
        raise HTTPException(422, "subject is required")
    if body.level not in KNOWLEDGE_LEVELS:
        raise HTTPException(422, f"level must be one of {sorted(KNOWLEDGE_LEVELS)}")

    return write_knowledge(
        db,
        entity_id=entity_id,
        subject=body.subject,
        level=body.level,
        content=body.content,
        source=body.source,
        is_incorrect=body.is_incorrect,
        is_secret=body.is_secret,
        share_threshold=body.share_threshold if body.share_threshold is not None else 50,
        session_id=None,  # author-created knowledge is foundational, not session-acquired
    )


@router.post("/entities/{entity_id}/knowledge", status_code=201)
def create_knowledge(entity_id: str, body: KnowledgeWriteBody, db: DbSession = Depends(get_session)) -> dict:
    k = _create_knowledge_core(entity_id, body, db)
    db.commit()
    db.refresh(k)
    return _knowledge_dict(k)


@router.put("/knowledge/{knowledge_id}")
def update_knowledge(knowledge_id: str, body: KnowledgeWriteBody, db: DbSession = Depends(get_session)) -> dict:
    existing = db.get(Knowledge, knowledge_id)
    if existing is None:
        raise HTTPException(404, f"Knowledge {knowledge_id!r} not found")
    if body.level is not None and body.level not in KNOWLEDGE_LEVELS:
        raise HTTPException(422, f"level must be one of {sorted(KNOWLEDGE_LEVELS)}")
    if not body.subject:
        raise HTTPException(422, "subject is required")

    k = write_knowledge(
        db,
        knowledge_id=knowledge_id,
        subject=body.subject,
        level=body.level or existing.level,
        content=body.content,
        source=body.source,
        is_incorrect=body.is_incorrect,
        is_secret=body.is_secret,
        share_threshold=body.share_threshold if body.share_threshold is not None else existing.share_threshold,
    )
    db.commit()
    db.refresh(k)
    return _knowledge_dict(k)


@router.delete("/knowledge/{knowledge_id}")
def delete_knowledge(knowledge_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Hard delete — knowledge rows are facts the author poses and removes cleanly."""
    k = db.get(Knowledge, knowledge_id)
    if k is None:
        raise HTTPException(404, f"Knowledge {knowledge_id!r} not found")
    db.delete(k)
    db.commit()
    return {"deleted": True, "id": knowledge_id}
