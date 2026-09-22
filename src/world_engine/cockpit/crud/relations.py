"""Author CRUD — relation editor (in-context) and the NPC relation ego-graph.

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

from ...context import RELATION_GRAPH_EXCLUDED_TYPES as _RELATION_GRAPH_EXCLUDED_TYPES
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
    Fact,
    FactDefault,
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
from ...relation_orientation import is_social
from ...spatial_author import connect_locations
from ...tick_normalize import _EVENT_TYPES
from ...writes import (
    KNOWLEDGE_LEVELS,
    NPC_GOAL_HORIZONS,
    NPC_GOAL_PREREQUISITE_TYPES,
    PromptValidationError,
    _find_perceived_relation,
    _find_relation_pair,
    detach_goal_agenda_link,
    set_target_knows,
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
    write_oriented_relations,
    write_prompt_version,
    write_relation,
    write_skill_tier,
)

from ._router import router
from ._shared import (
    RELATION_DIRECTIONS,
    RELATION_FIELDS,
    RELATION_TYPES,
    _get_entity,
    _iso,
    _list_relations,
    _relation_dict,
    _world_id,
)


class RelationWriteBody(BaseModel):
    """Create/update body. Orientation rule (TICKET-0090): a social relation
    is the sheet entity's feeling toward `other_entity_id`; `reciprocal`
    (create only) also writes the reverse row. `direction` and
    `visible_to_b` are still ACCEPTED so a stale client does not 422, but
    are IGNORED for a social relation (the target's knowledge is set through
    `PUT /relations/{id}/target-knows`)."""
    other_entity_id: Optional[str] = None  # required on create; ignored on update
    type: Optional[str] = None
    intensity: Optional[int] = None
    direction: Optional[str] = None  # ignored for social relations (TICKET-0090)
    visible_to_b: Optional[bool] = None  # ignored for social relations (TICKET-0090)
    notes: Optional[str] = None
    reciprocal: Optional[bool] = None  # create only: also write other -> sheet entity


class TargetKnowsBody(BaseModel):
    knows: bool


@router.get("/entities/{entity_id}/relations")
def list_entity_relations(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    _get_entity(db, entity_id)
    return _list_relations(entity_id, db)


def _create_social_relation(db: DbSession, world_id: str, entity_id: str, body: RelationWriteBody) -> dict:
    """Social create: 409 if the sheet entity already feels something toward
    the other (or, with `reciprocal`, the other toward it); else one call to
    `write_oriented_relations` -- one oriented row, or two when reciprocal.
    Returns the sheet entity's own row (the first)."""
    other_id = body.other_entity_id
    pairs = [(entity_id, other_id)] + ([(other_id, entity_id)] if body.reciprocal else [])
    for perceiver_id, target_id in pairs:
        existing = _find_perceived_relation(db, perceiver_id, target_id)
        if existing is not None:
            raise HTTPException(
                409,
                f"Relation {existing.id!r} ({existing.type}) already exists "
                f"from {perceiver_id!r} toward {target_id!r}",
            )
    try:
        rows = write_oriented_relations(
            db, world_id=world_id, entity_a_id=entity_id, entity_b_id=other_id,
            type=body.type, value=body.intensity if body.intensity is not None else 50,
            direction="mutual" if body.reciprocal else "a_to_b", visible_to_b=False,
            notes=body.notes, changed_by="creator_crud",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A {body.type} relation between these entities already exists")
    db.refresh(rows[0])
    return _relation_dict(rows[0], entity_id, db)


@router.post("/entities/{entity_id}/relations", status_code=201)
def create_relation(entity_id: str, body: RelationWriteBody, db: DbSession = Depends(get_session)) -> dict:
    """Create a relation from the sheet entity. Orientation rule
    (TICKET-0090): a social type makes the sheet entity the perceiver
    (`entity_a`) -- `reciprocal` adds the reverse row, `direction` and
    `visible_to_b` are ignored; `connects_to` delegates to
    `connect_locations`; `controls` makes the sheet entity the controller."""
    entity = _get_entity(db, entity_id)
    if not body.other_entity_id:
        raise HTTPException(422, "other_entity_id is required")
    other = db.get(Entity, body.other_entity_id)
    if other is None:
        raise HTTPException(422, f"Entity {body.other_entity_id!r} not found")
    if not body.type:
        raise HTTPException(422, "type is required")

    if body.type == "connects_to":
        connect_locations(
            db, world_id=entity.world_id, entity_a_id=entity_id,
            entity_b_id=body.other_entity_id, changed_by="creator",
        )
        db.commit()
        rel = _find_relation_pair(db, entity_id, body.other_entity_id)
        return _relation_dict(rel, entity_id, db)

    if is_social(body.type):
        return _create_social_relation(db, entity.world_id, entity_id, body)

    rel = write_relation(
        db,
        mode="set",
        world_id=entity.world_id,
        entity_a_id=entity_id,
        entity_b_id=body.other_entity_id,
        type=body.type,
        value=body.intensity if body.intensity is not None else 50,
        direction="a_to_b",
        visible_to_b=body.visible_to_b if body.visible_to_b is not None else True,
        notes=body.notes,
    )
    db.commit()
    db.refresh(rel)
    return _relation_dict(rel, entity_id, db)


@router.put("/relations/{relation_id}")
def update_relation(relation_id: str, body: RelationWriteBody, db: DbSession = Depends(get_session)) -> dict:
    """Edit type, intensity and notes of one row. Orientation rule
    (TICKET-0090): the endpoints never move; a social row stays `a_to_b`, a
    structural row keeps its own direction; `body.direction` and
    `body.visible_to_b` are never read (`visible_to_b` passes through from
    the row)."""
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
        direction="a_to_b" if is_social(body.type) else rel.direction,
        visible_to_b=rel.visible_to_b,
        notes=body.notes,
    )
    db.commit()
    db.refresh(rel)
    return _relation_dict(rel, rel.entity_a_id, db)


@router.delete("/relations/{relation_id}")
def delete_relation(relation_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Hard delete -- a creator correction: the relation never existed, so the
    knowledge of it goes with it. Same family as the `skill_definition`
    delete (dependents then the row, one transaction, no history snapshot).

    Orientation rule (TICKET-0090): deleting one oriented row never touches
    the reverse row. In one transaction, layer by layer with a flush
    between: the `knowledge` rows on the relation's typed fact, its
    `fact_default` rows, the fact, then the relation. A relation with no
    typed fact deletes as before; a `connects_to` edge's fact goes the same
    way."""
    rel = db.get(Relation, relation_id)
    if rel is None:
        raise HTTPException(404, f"Relation {relation_id!r} not found")
    facts = db.exec(select(Fact).where(Fact.relation_id == rel.id)).all()
    fact_ids = [f.id for f in facts]
    if fact_ids:
        for knowledge in db.exec(select(Knowledge).where(Knowledge.fact_id.in_(fact_ids))).all():
            db.delete(knowledge)
        db.flush()
        for default in db.exec(select(FactDefault).where(FactDefault.fact_id.in_(fact_ids))).all():
            db.delete(default)
        db.flush()
        for fact in facts:
            db.delete(fact)
        db.flush()
    db.delete(rel)
    db.commit()
    return {"deleted": True, "id": relation_id}


@router.put("/relations/{relation_id}/target-knows")
def set_relation_target_knows(
    relation_id: str, body: TargetKnowsBody, db: DbSession = Depends(get_session),
) -> dict:
    """C-13: make the target (`entity_b`) of a social relation know, or stop
    knowing, that relation -- its knowledge row on the lien fact, idempotent
    both ways (`set_target_knows`). 404 unknown relation; 409 structural
    relation or no lien fact."""
    rel = db.get(Relation, relation_id)
    if rel is None:
        raise HTTPException(404, f"Relation {relation_id!r} not found")
    if not is_social(rel.type):
        raise HTTPException(409, f"Relation {relation_id!r} is structural ({rel.type})")
    try:
        set_target_knows(db, rel=rel, knows=body.knows, changed_by="creator_crud")
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    db.commit()
    db.refresh(rel)
    return _relation_dict(rel, rel.entity_a_id, db)


def _relation_graph_nodes(rows) -> list[dict]:
    """Node shape shared by the ego and global relation-graph endpoints."""
    return [
        {
            "id": e.id,
            "name": e.name,
            "character_type": c.character_type,
            "description": (e.description or "")[:200],
        }
        for e, c in rows
    ]


def _relation_graph_edges(rels) -> list[dict]:
    """Edge shape shared by the ego and global relation-graph endpoints."""
    return [
        {
            "id": r.id,
            "source": r.entity_a_id,
            "target": r.entity_b_id,
            "type": r.type,
            "intensity": r.intensity,
            "direction": r.direction,
        }
        for r in rels
    ]


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

    nodes = _relation_graph_nodes(active_chars.values())

    edge_rels = db.exec(
        select(Relation)
        .where(Relation.world_id == world_id)
        .where(Relation.type.not_in(_RELATION_GRAPH_EXCLUDED_TYPES))
        .where(Relation.entity_a_id.in_(node_ids))
        .where(Relation.entity_b_id.in_(node_ids))
    ).all()
    edges = _relation_graph_edges(edge_rels)

    return {"center": entity_id, "nodes": nodes, "edges": edges}


@router.get("/relation-graph")
def get_global_relation_graph(db: DbSession = Depends(get_session)) -> dict:
    """Global relation graph — every active character of the world, read-only.

    Same node/edge shapes as the ego endpoint (`_relation_graph_nodes`/
    `_relation_graph_edges`), no `center` key. Isolated characters (zero
    edges) are included so links can be created toward them. Structural
    exclusion of `_RELATION_GRAPH_EXCLUDED_TYPES` in the WHERE clause,
    same as the ego route (G1 of BRIEF-0023-b) — never post-filtered.
    Path deliberately outside `/characters/{entity_id}/...` so the
    ego route's `{entity_id}` segment never swallows this literal path.
    """
    world_id = _world_id(db)

    active_char_rows = db.exec(
        select(Entity, Character)
        .join(Character, Character.id == Entity.id)
        .where(Entity.world_id == world_id)
        .where(Entity.type == "character")
        .where(Entity.status == "active")
    ).all()
    node_ids = {e.id for e, _c in active_char_rows}
    nodes = _relation_graph_nodes(active_char_rows)

    edge_rels = db.exec(
        select(Relation)
        .where(Relation.world_id == world_id)
        .where(Relation.type.not_in(_RELATION_GRAPH_EXCLUDED_TYPES))
        .where(Relation.entity_a_id.in_(node_ids))
        .where(Relation.entity_b_id.in_(node_ids))
    ).all()
    edges = _relation_graph_edges(edge_rels)

    return {"nodes": nodes, "edges": edges}
