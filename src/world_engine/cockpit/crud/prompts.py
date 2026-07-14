"""Author CRUD — prompt template read + version history (Création ->
Prompts, read-only besides `PATCH .../text` and the restore route).

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


def _effective_prompt_row(
    rows: list[PromptTemplate], world_scoped: bool, world_id: str
) -> Optional[PromptTemplate]:
    """Replicate the REAL loader semantics (R1) over an already-fetched row
    list for one usage — never idealized. `world_scoped=True` usages use the
    world-preferred-else-global chain every cockpit/gathering loader shares
    (app.py:1307-1311); `world_scoped=False` (the 6 authoring usages) take
    the first active row in whatever order the DB returns them, mirroring
    their loaders' bare `.first()` — the latent nondeterminism with 2+ active
    rows is an accepted observation, not fixed here."""
    active = [r for r in rows if r.is_active]
    if not active:
        return None
    if world_scoped:
        for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
            match = next((t for t in active if prefer(t)), None)
            if match is not None:
                return match
        return active[0]
    return active[0]


def _prompt_row_summary(r: PromptTemplate, db: DbSession) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "world_id": r.world_id,
        "version": current_prompt(db, r).version_number,
        "is_active": r.is_active,
        "model": r.model,
    }


@router.get("/prompts")
def list_prompts(db: DbSession = Depends(get_session)) -> dict:
    """Master list grouped by usage — registry facts + DB rows, no
    system_prompt/user_template bodies (lazy: only the selected prompt is
    ever rendered, per the creator's stated requirement)."""
    world_id = _world_id(db)
    usages = []
    for usage, spec in PROMPT_REGISTRY.items():
        rows = db.exec(
            select(PromptTemplate).where(PromptTemplate.usage == usage)
        ).all()
        default_model = spec.default_model()
        effective_row = _effective_prompt_row(rows, spec.world_scoped, world_id)
        usages.append({
            "usage": usage,
            "surface": spec.surface,
            "world_scoped": spec.world_scoped,
            "dry_run_capable": spec.dry_run_capable,
            "call_sites": list(spec.call_sites),
            "default_model": default_model,
            "rows": [_prompt_row_summary(r, db) for r in rows],
            "effective_id": effective_row.id if effective_row else None,
            "effective_model": (
                effective_model(effective_row, default_model) if effective_row else None
            ),
        })
    return {"usages": usages}


@router.get("/prompts/{prompt_id}")
def get_prompt_detail(prompt_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Full detail for one row, including body text — fetched on demand only
    (D1: lazy master list + one detail at a time)."""
    row = db.get(PromptTemplate, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt template {prompt_id!r} not found")
    spec = PROMPT_REGISTRY.get(row.usage)
    if spec is None:
        raise HTTPException(
            status_code=500, detail=f"Usage {row.usage!r} has no PROMPT_REGISTRY entry"
        )
    world_id = _world_id(db)
    sibling_rows = db.exec(
        select(PromptTemplate).where(PromptTemplate.usage == row.usage)
    ).all()
    default_model = spec.default_model()
    effective_row = _effective_prompt_row(sibling_rows, spec.world_scoped, world_id)
    is_effective = effective_row is not None and effective_row.id == row.id
    version = current_prompt(db, row)
    variable_rows = db.exec(
        select(PromptVariable).where(PromptVariable.prompt_template_id == row.id)
    ).all()
    return {
        "id": row.id,
        "name": row.name,
        "usage": row.usage,
        "world_id": row.world_id,
        "version": version.version_number,
        "is_active": row.is_active,
        "model": row.model,
        "effective_model": effective_model(row, default_model),
        "system_prompt": version.system_prompt,
        "user_template": version.user_template,
        "variables": [v.name for v in variable_rows],
        "notes": row.notes,
        "surface": spec.surface,
        "world_scoped": spec.world_scoped,
        "dry_run_capable": spec.dry_run_capable,
        "call_sites": list(spec.call_sites),
        "default_model": default_model,
        "is_effective": is_effective,
        "shadowed_by": (effective_row.id if not is_effective and effective_row else None),
    }


def _version_summary(v) -> dict:
    return {
        "version_number": v.version_number,
        "created_at": v.created_at,
        "note": v.note,
    }


@router.get("/prompts/{prompt_id}/versions")
def list_prompt_versions(prompt_id: str, db: DbSession = Depends(get_session)) -> dict:
    """History list, newest first — no bodies (D1, same rationale as the
    lazy master list: only the selected version is ever rendered)."""
    row = db.get(PromptTemplate, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt template {prompt_id!r} not found")
    versions = list_versions(db, prompt_id)
    current_number = versions[0].version_number if versions else None
    return {
        "versions": [
            {**_version_summary(v), "is_current": v.version_number == current_number}
            for v in versions
        ]
    }


@router.get("/prompts/{prompt_id}/versions/{version_number}")
def get_prompt_version(
    prompt_id: str, version_number: int, db: DbSession = Depends(get_session)
) -> dict:
    """One specific version, with bodies."""
    row = db.get(PromptTemplate, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt template {prompt_id!r} not found")
    version = get_version(db, prompt_id, version_number)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} of prompt template {prompt_id!r} not found",
        )
    return {
        **_version_summary(version),
        "system_prompt": version.system_prompt,
        "user_template": version.user_template,
    }


class PromptTextBody(BaseModel):
    system_prompt: str
    user_template: str
    note: Optional[str] = None


@router.patch("/prompts/{prompt_id}/text")
def update_prompt_text(
    prompt_id: str, body: PromptTextBody, db: DbSession = Depends(get_session)
) -> dict:
    """Write path for prompt text (TICKET-0011) — appends a new `prompt_version`
    row via the single write shape (`write_prompt_version`). 404 unknown head;
    422 with the offending placeholder names on a C1 validation failure
    (nothing written); 200 -> the new version's summary."""
    row = db.get(PromptTemplate, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt template {prompt_id!r} not found")
    try:
        version = write_prompt_version(
            db,
            template_id=prompt_id,
            system_prompt=body.system_prompt,
            user_template=body.user_template,
            note=body.note,
        )
    except PromptValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Undeclared placeholder(s): {', '.join(exc.offending)}",
        ) from exc
    db.commit()
    return _version_summary(version)


@router.post("/prompts/{prompt_id}/versions/{version_number}/restore")
def restore_prompt_version(
    prompt_id: str, version_number: int, db: DbSession = Depends(get_session)
) -> dict:
    """D1: restore = append a NEW version copying the restored one's text —
    history stays strictly monotone. C1 re-validates (fail-closed even on
    restore: if the head's `variables` changed since, the restore is refused,
    not silently admitted)."""
    row = db.get(PromptTemplate, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt template {prompt_id!r} not found")
    source = get_version(db, prompt_id, version_number)
    if source is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_number} of prompt template {prompt_id!r} not found",
        )
    try:
        version = write_prompt_version(
            db,
            template_id=prompt_id,
            system_prompt=source.system_prompt,
            user_template=source.user_template,
            note=f"restored from v{version_number}",
        )
    except PromptValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Undeclared placeholder(s): {', '.join(exc.offending)}",
        ) from exc
    db.commit()
    return _version_summary(version)


@router.get("/ollama/models")
def list_ollama_models() -> dict:
    """Live installed-model list (Création → Prompts selector) — thin wrapper
    over `ollama_client.ping()`. No cache, no table, no sync."""
    try:
        models = ping()
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"models": models}


class PromptModelBody(BaseModel):
    model: Optional[str] = None


@router.patch("/prompts/{prompt_id}/model")
def update_prompt_model(
    prompt_id: str, body: PromptModelBody, db: DbSession = Depends(get_session)
) -> dict:
    """Write path for `prompt_template.model` (W1) — writes `model` and
    `updated_at` only; full template editing is Scope OUT. Fail-closed
    validation (V1): a non-null value must be in the live Ollama tag list;
    clearing the override (null) is always accepted, no `ping()` call."""
    row = db.get(PromptTemplate, prompt_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prompt template {prompt_id!r} not found")

    value = (body.model or "").strip() or None
    if value is not None:
        try:
            models = ping()
        except OllamaError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if value not in models:
            raise HTTPException(
                status_code=422,
                detail=f"Model {value!r} is not installed in Ollama.",
            )

    row.model = value
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    db.refresh(row)

    spec = PROMPT_REGISTRY.get(row.usage)
    default_model = spec.default_model() if spec else None
    summary = _prompt_row_summary(row, db)
    summary["effective_model"] = effective_model(row, default_model)
    return summary
