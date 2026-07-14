"""Author CRUD — agendas (TICKET-0018).

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
    NpcGoal,
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
from ._shared import _iso, _world_id


class AgendaStepCreateBody(BaseModel):
    objective: Optional[str] = None
    visibility_trace: Optional[str] = None


class AgendaCreateBody(BaseModel):
    owner_entity_id: Optional[str] = None
    title: Optional[str] = None
    steps: list[AgendaStepCreateBody] = []


class AgendaStatusBody(BaseModel):
    status: Optional[str] = None


class AgendaStepPatchBody(BaseModel):
    objective: Optional[str] = None
    visibility_trace: Optional[str] = None
    status: Optional[str] = None


def _agenda_step_dict(s: AgendaStep) -> dict:
    return {
        "id": s.id,
        "agenda_id": s.agenda_id,
        "step_order": s.step_order,
        "objective": s.objective,
        "status": s.status,
        "outcome": s.outcome,
        "visibility_trace": s.visibility_trace,
        "created_at": _iso(s.created_at),
        "updated_at": _iso(s.updated_at),
    }


def _agenda_linked_goals(agenda_id: str, db: DbSession) -> list[dict]:
    """ACTIVE links into this agenda (TICKET-0020, BRIEF-0020-c) — link id +
    the linked goal's id/description/status/owning NPC name, for the
    Intrigues card's linked-goals list and its per-link detach control."""
    links = db.exec(
        select(GoalAgendaLink).where(
            GoalAgendaLink.agenda_id == agenda_id, GoalAgendaLink.detached_at.is_(None)
        )
    ).all()
    out = []
    for link in links:
        goal = db.get(NpcGoal, link.goal_id)
        if goal is None:
            continue
        npc = db.get(Entity, goal.npc_id)
        out.append({
            "link_id": link.id,
            "goal_id": goal.id,
            "goal_description": goal.description,
            "goal_status": goal.status,
            "npc_id": goal.npc_id,
            "npc_name": npc.name if npc is not None else goal.npc_id,
        })
    return out


def _agenda_dict(a: Agenda, db: DbSession) -> dict:
    owner = db.get(Entity, a.owner_entity_id)
    steps = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == a.id).order_by(AgendaStep.step_order)
    ).all()
    return {
        "id": a.id,
        "world_id": a.world_id,
        "owner_entity_id": a.owner_entity_id,
        "owner_name": owner.name if owner is not None else a.owner_entity_id,
        "owner_type": owner.type if owner is not None else None,
        "title": a.title,
        "status": a.status,
        "created_at": _iso(a.created_at),
        "updated_at": _iso(a.updated_at),
        "steps": [_agenda_step_dict(s) for s in steps],
        "linked_goals": _agenda_linked_goals(a.id, db),
    }


@router.get("/agendas")
def list_agendas(db: DbSession = Depends(get_session)) -> list[dict]:
    world_id = _world_id(db)
    agendas = db.exec(select(Agenda).where(Agenda.world_id == world_id)).all()
    ordered = sorted(agendas, key=lambda a: (a.status != "active", -a.created_at.timestamp()))
    return [_agenda_dict(a, db) for a in ordered]


@router.post("/agendas", status_code=201)
def create_agenda(body: AgendaCreateBody, db: DbSession = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    if not body.owner_entity_id:
        raise HTTPException(422, "owner_entity_id is required")
    if not body.title or not body.title.strip():
        raise HTTPException(422, "title is required")
    if not (2 <= len(body.steps) <= 5):
        raise HTTPException(422, "steps must contain 2 to 5 entries")
    for step in body.steps:
        if not step.objective or not step.objective.strip():
            raise HTTPException(422, "every step requires a non-empty objective")

    try:
        agenda = write_agenda(
            db, world_id=world_id, owner_entity_id=body.owner_entity_id, title=body.title.strip(),
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    # Step 1 is born active — creator-authored agendas are symmetric with the
    # tick-proposed creation (the authoring act IS the activation, flagged
    # drafting decision #2).
    for order, step in enumerate(body.steps, start=1):
        write_agenda_step(
            db,
            agenda_id=agenda.id,
            step_order=order,
            objective=step.objective.strip(),
            visibility_trace=(step.visibility_trace.strip() if step.visibility_trace else None) or None,
            status="active" if order == 1 else "pending",
        )
    db.commit()
    db.refresh(agenda)
    return _agenda_dict(agenda, db)


@router.patch("/agendas/{agenda_id}")
def update_agenda_status(agenda_id: str, body: AgendaStatusBody, db: DbSession = Depends(get_session)) -> dict:
    agenda = db.get(Agenda, agenda_id)
    if agenda is None or agenda.world_id != _world_id(db):
        raise HTTPException(404, f"Agenda {agenda_id!r} not found")
    if body.status not in ("active", "abandoned"):
        raise HTTPException(422, "status must be 'active' (reactivate) or 'abandoned'")

    agenda = write_agenda_status(db, agenda=agenda, status=body.status)
    db.commit()
    db.refresh(agenda)
    return _agenda_dict(agenda, db)


@router.patch("/agenda-steps/{step_id}")
def update_agenda_step(step_id: str, body: AgendaStepPatchBody, db: DbSession = Depends(get_session)) -> dict:
    step = db.get(AgendaStep, step_id)
    if step is None:
        raise HTTPException(404, f"AgendaStep {step_id!r} not found")
    agenda = db.get(Agenda, step.agenda_id)
    if agenda is None or agenda.world_id != _world_id(db):
        raise HTTPException(404, f"AgendaStep {step_id!r} not found")

    if body.objective is not None or body.visibility_trace is not None:
        if step.status != "pending":
            raise HTTPException(422, "objective/visibility_trace may only be edited while pending")
        if body.objective is not None:
            if not body.objective.strip():
                raise HTTPException(422, "objective cannot be blank")
            step.objective = body.objective.strip()
        if body.visibility_trace is not None:
            step.visibility_trace = body.visibility_trace.strip() or None
        step.updated_at = datetime.now(UTC)
        db.add(step)

    if body.status is not None:
        if body.status not in ("completed", "failed", "active"):
            raise HTTPException(422, "status must be one of 'completed', 'failed', 'active'")
        if body.status in ("completed", "failed"):
            step = write_agenda_step_status(db, step=step, status=body.status)
        else:
            # Manual reactivation must respect the partial unique index — the
            # creator completes or fails the current active step first;
            # deactivate is not a thing. The IntegrityError surfaces as a 409.
            step.status = "active"
            step.updated_at = datetime.now(UTC)
            db.add(step)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                raise HTTPException(409, "another step of this agenda is already active")

    db.commit()
    db.refresh(step)
    return _agenda_step_dict(step)
