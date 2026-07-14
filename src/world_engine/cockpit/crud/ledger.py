"""Author CRUD — the append-only ledger. `write_ledger_entry` (`..writes`)
is the single chokepoint; `POST /api/ledger` is one of only two sanctioned
canon-write paths into `ledger` (the other is `_apply_mutation`'s
`resource_change` branch).

Split out of `cockpit/crud.py` (TICKET-0027, BRIEF-0027-d) — pure move,
no logic change.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Optional

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


LEDGER_SOURCE_TYPES_CREATOR = ("creator", "correction")


def _ledger_dict(entry: Ledger) -> dict:
    return {
        "id": entry.id,
        "world_id": entry.world_id,
        "entity_id": entry.entity_id,
        "amount": entry.amount,
        "counterparty_id": entry.counterparty_id,
        "reason": entry.reason,
        "source_type": entry.source_type,
        "conversation_id": entry.conversation_id,
        "pass_play_id": entry.pass_play_id,
        "session_id": entry.session_id,
        "created_at": _iso(entry.created_at),
    }


class LedgerWriteBody(BaseModel):
    entity_id: str
    amount: int
    counterparty_id: Optional[str] = None
    reason: Optional[str] = None
    source_type: str = "creator"
    session_id: Optional[str] = None


@router.post("/ledger", status_code=201)
def create_ledger_entry(body: LedgerWriteBody, db: DbSession = Depends(get_session)) -> dict:
    """Creator-direct ledger write — the starting-money / correction path.

    `world_id` is always derived from the target entity, never trusted from
    the client. `conversation_id`/`pass_play_id` are always NULL on this
    path — those legs belong to `_apply_mutation`'s AI-detected
    `resource_change` branch (BRIEF-19).
    """
    entity = db.get(Entity, body.entity_id)
    if entity is None:
        raise HTTPException(422, f"Entity {body.entity_id!r} not found")
    if not isinstance(body.amount, int) or body.amount == 0:
        raise HTTPException(422, "amount must be a nonzero integer")
    if body.source_type not in LEDGER_SOURCE_TYPES_CREATOR:
        raise HTTPException(422, f"source_type must be one of {LEDGER_SOURCE_TYPES_CREATOR}")
    if body.counterparty_id is not None:
        counterparty = db.get(Entity, body.counterparty_id)
        if counterparty is None or counterparty.world_id != entity.world_id:
            raise HTTPException(422, f"counterparty_id {body.counterparty_id!r} is not an entity of the same world")

    entry = write_ledger_entry(
        db,
        world_id=entity.world_id,
        entity_id=body.entity_id,
        amount=body.amount,
        counterparty_id=body.counterparty_id,
        reason=body.reason,
        source_type=body.source_type,
        conversation_id=None,
        pass_play_id=None,
        session_id=body.session_id,
    )
    db.commit()
    db.refresh(entry)
    return _ledger_dict(entry)


@router.get("/entities/{entity_id}/ledger")
def get_entity_ledger(entity_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Per-entity balance + recent lines — for the character sheet "Solde" block."""
    _get_entity(db, entity_id)
    return {
        "balance": get_balance(db, entity_id),
        "entries": [_ledger_dict(e) for e in list_entries(db, entity_id=entity_id)],
    }


@router.get("/ledger")
def get_ledger_journal(
    entity_id: Optional[str] = Query(default=None),
    session_id: Optional[str] = Query(default=None),
    db: DbSession = Depends(get_session),
) -> list[dict]:
    """Global journal (Création → Registre), read-only."""
    return [
        _ledger_dict(e)
        for e in list_entries(db, entity_id=entity_id, session_id=session_id, world_id=_world_id(db))
    ]
