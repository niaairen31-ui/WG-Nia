"""Author CRUD — relation editor (in-context) and the NPC relation ego-graph.

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


RELATION_TYPES = (
    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
    "instrumentalizes", "interest", "indifference", "rejection",
    "passive_attention", "other", "connects_to", "controls",
)


RELATION_DIRECTIONS = ("mutual", "a_to_b", "b_to_a")


RELATION_FIELDS: list[dict[str, Any]] = [
    {"name": "type", "label": "Type", "kind": "datalist", "options": list(RELATION_TYPES), "required": True},
    {"name": "intensity", "label": "Intensity (1-100)", "kind": "number", "min": 1, "max": 100, "default": 50},
    {"name": "direction", "label": "Direction", "kind": "select", "options": list(RELATION_DIRECTIONS), "default": "mutual"},
    {"name": "visible_to_b", "label": "Visible to B", "kind": "bool", "default": True},
    {"name": "notes", "label": "Notes", "kind": "textarea"},
]


def _relation_dict(rel: Relation, perspective_id: str, db: DbSession) -> dict:
    other_id = rel.entity_b_id if rel.entity_a_id == perspective_id else rel.entity_a_id
    other = db.get(Entity, other_id)
    return {
        "id": rel.id,
        "role": "a" if rel.entity_a_id == perspective_id else "b",
        "other_entity_id": other_id,
        "other_entity_name": other.name if other else other_id,
        "other_entity_type": other.type if other else None,
        "type": rel.type,
        "direction": rel.direction,
        "intensity": rel.intensity,
        "visible_to_b": rel.visible_to_b,
        "notes": rel.notes,
        "last_evolved_at": _iso(rel.last_evolved_at),
    }


def _list_relations(entity_id: str, db: DbSession) -> list[dict]:
    rels = db.exec(
        select(Relation).where(
            (Relation.entity_a_id == entity_id) | (Relation.entity_b_id == entity_id)
        )
    ).all()
    return [_relation_dict(r, entity_id, db) for r in rels]


class RelationWriteBody(BaseModel):
    other_entity_id: Optional[str] = None  # required on create; ignored on update
    type: Optional[str] = None
    intensity: Optional[int] = None
    direction: Optional[str] = None
    visible_to_b: Optional[bool] = None
    notes: Optional[str] = None


@router.get("/entities/{entity_id}/relations")
def list_entity_relations(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    _get_entity(db, entity_id)
    return _list_relations(entity_id, db)


@router.post("/entities/{entity_id}/relations", status_code=201)
def create_relation(entity_id: str, body: RelationWriteBody, db: DbSession = Depends(get_session)) -> dict:
    entity = _get_entity(db, entity_id)
    if not body.other_entity_id:
        raise HTTPException(422, "other_entity_id is required")
    other = db.get(Entity, body.other_entity_id)
    if other is None:
        raise HTTPException(422, f"Entity {body.other_entity_id!r} not found")
    if not body.type:
        raise HTTPException(422, "type is required")

    rel = write_relation(
        db,
        mode="set",
        world_id=entity.world_id,
        entity_a_id=entity_id,
        entity_b_id=body.other_entity_id,
        type=body.type,
        value=body.intensity if body.intensity is not None else 50,
        direction=body.direction or "mutual",
        visible_to_b=body.visible_to_b if body.visible_to_b is not None else True,
        notes=body.notes,
    )
    db.commit()
    db.refresh(rel)
    return _relation_dict(rel, entity_id, db)


@router.put("/relations/{relation_id}")
def update_relation(relation_id: str, body: RelationWriteBody, db: DbSession = Depends(get_session)) -> dict:
    rel = db.get(Relation, relation_id)
    if rel is None:
        raise HTTPException(404, f"Relation {relation_id!r} not found")
    if not body.type:
        raise HTTPException(422, "type is required")

    write_relation(
        db,
        mode="set",
        relation_id=relation_id,
        type=body.type,
        value=body.intensity if body.intensity is not None else rel.intensity,
        direction=body.direction or rel.direction,
        visible_to_b=body.visible_to_b if body.visible_to_b is not None else rel.visible_to_b,
        notes=body.notes,
    )
    db.commit()
    db.refresh(rel)
    return _relation_dict(rel, rel.entity_a_id, db)


@router.delete("/relations/{relation_id}")
def delete_relation(relation_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Hard delete — relation rows are edges the author poses and removes cleanly."""
    rel = db.get(Relation, relation_id)
    if rel is None:
        raise HTTPException(404, f"Relation {relation_id!r} not found")
    db.delete(rel)
    db.commit()
    return {"deleted": True, "id": relation_id}


_RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to", "controls")


@router.get("/characters/{entity_id}/relation-graph")
def get_character_relation_graph(entity_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Depth-1 ego-graph of a character's relations — display-only, read-only.

    Neighbors: every ACTIVE character entity linked to `entity_id` by at
    least one qualifying relation row (either endpoint). Edges: every
    qualifying relation row whose both endpoints are in {center} ∪
    neighbors (inter-neighbor edges included) — one edge object per row,
    no aggregation (B1). Qualifying = world_id match AND type NOT IN
    ('connects_to', 'controls') in the WHERE clause (structural exclusion,
    never post-filtered, G1) AND both endpoints resolve to active
    type='character' entities.
    """
    world_id = _world_id(db)

    center = db.get(Entity, entity_id)
    if (
        center is None
        or center.world_id != world_id
        or center.type != "character"
        or center.status != "active"
    ):
        raise HTTPException(status_code=404, detail=f"Character {entity_id!r} not found in the active world")

    neighbor_rels = db.exec(
        select(Relation)
        .where(Relation.world_id == world_id)
        .where(Relation.type.not_in(_RELATION_GRAPH_EXCLUDED_TYPES))
        .where((Relation.entity_a_id == entity_id) | (Relation.entity_b_id == entity_id))
    ).all()
    neighbor_ids = {
        (r.entity_b_id if r.entity_a_id == entity_id else r.entity_a_id)
        for r in neighbor_rels
    }

    active_char_rows = db.exec(
        select(Entity, Character)
        .join(Character, Character.id == Entity.id)
        .where(Entity.world_id == world_id)
        .where(Entity.type == "character")
        .where(Entity.status == "active")
        .where(Entity.id.in_(neighbor_ids | {entity_id}))
    ).all()
    active_chars = {e.id: (e, c) for e, c in active_char_rows}
    node_ids = set(active_chars.keys())

    nodes = [
        {
            "id": e.id,
            "name": e.name,
            "character_type": c.character_type,
            "description": (e.description or "")[:200],
        }
        for e, c in active_chars.values()
    ]

    edge_rels = db.exec(
        select(Relation)
        .where(Relation.world_id == world_id)
        .where(Relation.type.not_in(_RELATION_GRAPH_EXCLUDED_TYPES))
        .where(Relation.entity_a_id.in_(node_ids))
        .where(Relation.entity_b_id.in_(node_ids))
    ).all()
    edges = [
        {
            "id": r.id,
            "source": r.entity_a_id,
            "target": r.entity_b_id,
            "type": r.type,
            "intensity": r.intensity,
            "direction": r.direction,
        }
        for r in edge_rels
    ]

    return {"center": entity_id, "nodes": nodes, "edges": edges}
