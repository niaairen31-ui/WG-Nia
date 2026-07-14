"""Author CRUD — NPC goals (in-scene volition) and goal<->agenda links.

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


def _goal_links(goal_id: str, db: DbSession) -> list[dict]:
    """ACTIVE goal_agenda_link rows for one goal (TICKET-0020, BRIEF-0020-c) —
    link id + agenda id/title, so the creator can render `(sert : « … »)`
    and offer a detach control. Detached rows never surface here — a
    detached link is not "less active", it is gone from every reader
    (history is sacred: the row itself is preserved, just not shown as
    current)."""
    links = db.exec(
        select(GoalAgendaLink).where(
            GoalAgendaLink.goal_id == goal_id, GoalAgendaLink.detached_at.is_(None)
        )
    ).all()
    out = []
    for link in links:
        agenda = db.get(Agenda, link.agenda_id)
        out.append({
            "link_id": link.id,
            "agenda_id": link.agenda_id,
            "agenda_title": agenda.title if agenda is not None else link.agenda_id,
        })
    return out


def _goal_prerequisites_dict(g: NpcGoal, db: DbSession) -> list[dict]:
    """Resolved prerequisites for display — entity NAME, id kept underneath
    (TICKET-0024, BRIEF-0024-a: "display shows the resolved entity NAME,
    stores the id"; relationalized TICKET-0025, BRIEF-0025-c)."""
    rows = db.exec(select(GoalPrerequisite).where(GoalPrerequisite.goal_id == g.id)).all()
    out = []
    for row in rows:
        target = db.get(Entity, row.target_entity_id)
        out.append({
            "type": row.type,
            "target_entity_id": row.target_entity_id,
            "target_entity_name": target.name if target else row.target_entity_id,
            "threshold": row.threshold,
        })
    return out


def _goal_dict(g: NpcGoal, db: DbSession) -> dict:
    return {
        "id": g.id,
        "npc_id": g.npc_id,
        "description": g.description,
        "horizon": g.horizon,
        "status": g.status,
        "created_at": _iso(g.created_at),
        "updated_at": _iso(g.updated_at),
        "links": _goal_links(g.id, db),
        "prerequisites": _goal_prerequisites_dict(g, db),
    }


def _list_goals(entity_id: str, db: DbSession) -> list[dict]:
    """Active first, then newest first within each status group (BRIEF-0013-a)."""
    rows = db.exec(
        select(NpcGoal).where(NpcGoal.npc_id == entity_id)
    ).all()
    ordered = sorted(rows, key=lambda g: (g.status != "active", -g.created_at.timestamp()))
    return [_goal_dict(g, db) for g in ordered]


class GoalWriteBody(BaseModel):
    description: Optional[str] = None
    horizon: Optional[str] = None


class GoalStatusBody(BaseModel):
    status: Optional[str] = None


class GoalPrerequisitesBody(BaseModel):
    prerequisites: Optional[list[dict[str, Any]]] = None


@router.get("/entities/{entity_id}/goals")
def list_entity_goals(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    entity = _get_entity(db, entity_id)
    if entity.world_id != _world_id(db):
        raise HTTPException(404, f"Entity {entity_id!r} not found")
    return _list_goals(entity_id, db)


@router.post("/entities/{entity_id}/goals", status_code=201)
def create_goal(entity_id: str, body: GoalWriteBody, db: DbSession = Depends(get_session)) -> dict:
    entity = _get_entity(db, entity_id)
    if entity.world_id != _world_id(db):
        raise HTTPException(404, f"Entity {entity_id!r} not found")
    if body.horizon not in NPC_GOAL_HORIZONS:
        raise HTTPException(422, f"horizon must be one of {sorted(NPC_GOAL_HORIZONS)}")
    if not body.description or not body.description.strip():
        raise HTTPException(422, "description is required")
    char = db.get(Character, entity_id)
    if char is None or char.character_type != "npc":
        raise HTTPException(422, "goals may only be created on an NPC character")

    goal = write_npc_goal(
        db,
        world_id=entity.world_id,
        npc_id=entity_id,
        description=body.description.strip(),
        horizon=body.horizon,
        changed_by="creator",
    )
    db.commit()
    db.refresh(goal)
    return _goal_dict(goal, db)


@router.post("/goals/{goal_id}/status")
def set_goal_status(goal_id: str, body: GoalStatusBody, db: DbSession = Depends(get_session)) -> dict:
    goal = db.get(NpcGoal, goal_id)
    if goal is None or goal.world_id != _world_id(db):
        raise HTTPException(404, f"NpcGoal {goal_id!r} not found")
    if body.status not in ("completed", "abandoned"):
        raise HTTPException(422, "status must be 'completed' or 'abandoned'")

    try:
        goal = write_npc_goal_status(db, goal=goal, new_status=body.status, changed_by="creator")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    db.refresh(goal)
    return _goal_dict(goal, db)


@router.patch("/goals/{goal_id}/prerequisites")
def set_goal_prerequisites(
    goal_id: str, body: GoalPrerequisitesBody, db: DbSession = Depends(get_session)
) -> dict:
    """Creator-CRUD-only write of `npc_goal.prerequisites` (TICKET-0024,
    BRIEF-0024-a). v1 vocabulary: `relation_gte` only."""
    goal = db.get(NpcGoal, goal_id)
    if goal is None or goal.world_id != _world_id(db):
        raise HTTPException(404, f"NpcGoal {goal_id!r} not found")

    try:
        goal = write_npc_goal_prerequisites(
            db, goal=goal, prerequisites=body.prerequisites, changed_by="creator"
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    db.refresh(goal)
    return _goal_dict(goal, db)


def _npc_faction_goals(entity_id: str, db: DbSession) -> Optional[str]:
    """This NPC's first PUBLIC active faction membership's `Faction.goals`
    (read-only, generator input only — BRIEF-0013-b)."""
    membership = db.exec(
        select(FactionMembership)
        .where(
            FactionMembership.entity_id == entity_id,
            FactionMembership.left_at.is_(None),
            FactionMembership.is_secret == False,  # noqa: E712
        )
    ).first()
    if membership is None:
        return None
    faction = db.get(Faction, membership.faction_id)
    return faction.goals if faction else None


class GoalBackfillBody(BaseModel):
    entity_id: Optional[str] = None


@router.post("/npc-goals/backfill")
def backfill_npc_goals(body: GoalBackfillBody, db: DbSession = Depends(get_session)) -> dict:
    """Fill per-horizon goal deficits (G2/P2, BRIEF-0013-b) — never rewrites
    a satisfied NPC. Scoped to `body.entity_id`, or every NPC of the active
    world (`character_type == 'npc'`, `vital_status == 'alive'`) when absent.
    Idempotent by construction: a second run on an unchanged world writes
    zero rows. A per-NPC generator failure is recorded in `failures` and
    never aborts the batch.
    """
    world_id = _world_id(db)

    if body.entity_id:
        entity = _get_entity(db, body.entity_id)
        if entity.world_id != world_id:
            raise HTTPException(404, f"Entity {body.entity_id!r} not found")
        char = db.get(Character, body.entity_id)
        if char is None or char.character_type != "npc":
            raise HTTPException(422, "backfill targets NPC characters only")
        targets = [char]
    else:
        targets = db.exec(
            select(Character)
            .join(Entity, Entity.id == Character.id)
            .where(
                Entity.world_id == world_id,
                Character.character_type == "npc",
                Character.vital_status == "alive",
            )
        ).all()

    processed = 0
    skipped_complete = 0
    written = {"long": 0, "short": 0}
    failures: list[dict] = []

    for char in targets:
        processed += 1
        active_goals = db.exec(
            select(NpcGoal).where(NpcGoal.npc_id == char.id, NpcGoal.status == "active")
        ).all()
        needs_long = not any(g.horizon == "long" for g in active_goals)
        n_shorts = sum(1 for g in active_goals if g.horizon == "short")
        needs_shorts = max(0, 2 - n_shorts)
        if not needs_long and needs_shorts == 0:
            skipped_complete += 1
            continue

        entity = db.get(Entity, char.id)
        result = generate_npc_goals(
            entity.name if entity else "",
            entity.description if entity else "",
            char.backstory,
            _npc_faction_goals(char.id, db),
            db,
        )
        if not result.get("ok"):
            failures.append({"npc": entity.name if entity else char.id, "reason": result.get("error")})
            continue

        if needs_long:
            long_desc = (result.get("long") or "").strip()
            if long_desc:
                write_npc_goal(
                    db, world_id=world_id, npc_id=char.id,
                    description=long_desc, horizon="long", changed_by="creator-backfill",
                )
                written["long"] += 1
        if needs_shorts:
            for short_desc in (result.get("shorts") or [])[:needs_shorts]:
                short_desc = (short_desc or "").strip()
                if short_desc:
                    write_npc_goal(
                        db, world_id=world_id, npc_id=char.id,
                        description=short_desc, horizon="short", changed_by="creator-backfill",
                    )
                    written["short"] += 1

    db.commit()
    return {
        "ok": True,
        "processed": processed,
        "skipped_complete": skipped_complete,
        "written": written,
        "failures": failures,
    }


class GoalAgendaLinkCreateBody(BaseModel):
    goal_id: Optional[str] = None
    agenda_id: Optional[str] = None


@router.post("/goal-agenda-links", status_code=201)
def create_goal_agenda_link(body: GoalAgendaLinkCreateBody, db: DbSession = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    if not body.goal_id or not body.agenda_id:
        raise HTTPException(422, "goal_id and agenda_id are required")
    try:
        link = write_goal_agenda_link(
            db, world_id=world_id, goal_id=body.goal_id, agenda_id=body.agenda_id, created_by="creator",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    db.refresh(link)
    return {
        "id": link.id,
        "goal_id": link.goal_id,
        "agenda_id": link.agenda_id,
        "created_at": _iso(link.created_at),
        "created_by": link.created_by,
    }


@router.post("/goal-agenda-links/{link_id}/detach")
def detach_goal_agenda_link_route(link_id: str, db: DbSession = Depends(get_session)) -> dict:
    link = db.get(GoalAgendaLink, link_id)
    if link is None or link.world_id != _world_id(db):
        raise HTTPException(404, f"GoalAgendaLink {link_id!r} not found")
    try:
        link = detach_goal_agenda_link(db, link=link, detached_by="creator")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    db.refresh(link)
    return {
        "id": link.id,
        "goal_id": link.goal_id,
        "agenda_id": link.agenda_id,
        "detached_at": _iso(link.detached_at),
        "detached_by": link.detached_by,
    }
