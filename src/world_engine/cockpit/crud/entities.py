"""Author CRUD — entity core: field-spec vocabularies, the entity type
registry, field coercion/validation, entity serialization, and composite
create/update/soft-delete for character/faction/location/artifact.

Split out of `cockpit/crud.py` (TICKET-0027, BRIEF-0027-d) — pure move,
no logic change. `router` is the single shared APIRouter (`crud/_router.py`),
imported by every domain module in this package so every route keeps its
original path/method.
"""

from __future__ import annotations

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
    Door,
    Entity,
    EntityTrait,
    EntityType,
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
    Obstacle,
    ObstacleVertex,
    PromptTemplate,
    PromptVariable,
    ProposedMutation,
    Relation,
    Skill,
    SkillDefinition,
)
from ...prompt_registry import PROMPT_REGISTRY, effective_model
from ...prompt_store import current_prompt, get_version, list_versions
from ...spatial_author import location_type_template
from ...tick_normalize import _EVENT_TYPES
from ...traits import checkable_traits, ext_columns_for, form_fields_for
from ...writes.schema import create_entity_type
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
    write_location_doors,
    write_location_obstacles,
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
    EVENT_FIELDS,
    KNOWLEDGE_FIELDS,
    RELATION_FIELDS,
    _coerce_field,
    _get_entity,
    _iso,
    _list_knowledge,
    _list_relations,
    _validate_entity_ref,
    _world_id,
)
from .entity_runtime import (
    _build_runtime_ext_kwargs,
    _insert_runtime_ext_row,
    _read_runtime_ext_row,
    _runtime_type_spec,
    _update_runtime_ext_row,
)


ENTITY_STATUSES = ("active", "inactive", "destroyed", "missing")


ENTITY_BASE_FIELDS: list[dict[str, Any]] = [
    {"name": "name", "label": "Name", "kind": "text", "required": True},
    {"name": "internal_name", "label": "Internal name (creator-only)", "kind": "text"},
    {"name": "description", "label": "Description", "kind": "textarea"},
    {"name": "is_public", "label": "Public", "kind": "bool", "default": True},
    {"name": "status", "label": "Status", "kind": "select", "options": list(ENTITY_STATUSES), "default": "active"},
]


ENTITY_TYPE_REGISTRY: dict[str, dict[str, Any]] = {
    "character": {
        "label": "Character",
        "model": Character,
        "fields": [
            {
                "name": "character_type", "label": "Character type", "kind": "select",
                "options": ["player", "npc"], "default": "npc", "required": True,
            },
            {"name": "current_location_id", "label": "Current location", "kind": "entity_ref", "ref_type": "location"},
            {
                "name": "vital_status", "label": "Vital status", "kind": "select",
                "options": ["alive", "dead", "missing", "unknown"], "default": "alive",
            },
            {"name": "appearance", "label": "Appearance", "kind": "textarea"},
            {"name": "backstory", "label": "Backstory", "kind": "textarea"},
            {"name": "aversion", "label": "Aversion", "kind": "textarea"},
            {"name": "secrets", "label": "Secrets (creator-only)", "kind": "textarea"},
            {"name": "physical_tier", "label": "Physical tier (Carrure)", "kind": "number", "min": -1, "max": 2, "default": 0},
        ],
    },
    "location": {
        "label": "Location",
        "model": Location,
        "fields": [
            {"name": "parent_location_id", "label": "Parent location", "kind": "entity_ref", "ref_type": "location"},
            {
                # TICKET-0039, BRIEF-0039-b: no "options" here — the picker
                # sources its datalist from GET /api/location-types (the
                # classified registry), not a hardcoded vocab. See
                # authorRenderField's 'datalist' case (index.html).
                "name": "location_type", "label": "Location type", "kind": "datalist",
            },
            {
                "name": "magic_status", "label": "Magic status", "kind": "select",
                "options": ["inert", "sensitive", "active", "nexus"], "default": "inert",
            },
            {"name": "coord_x", "label": "Map X", "kind": "number", "float": True},
            {"name": "coord_y", "label": "Map Y", "kind": "number", "float": True},
            {
                "name": "access_level", "label": "Access level", "kind": "select",
                "options": ["", "public", "restricted", "secret"],
            },
        ],
    },
    "faction": {
        "label": "Faction",
        "model": Faction,
        "fields": [
            {
                "name": "faction_type", "label": "Faction type", "kind": "datalist",
                "options": ["government", "criminal", "military", "esoteric", "other"],
            },
            {"name": "internal_structure", "label": "Internal structure", "kind": "textarea"},
            {"name": "philosophy", "label": "Philosophy", "kind": "textarea"},
            {"name": "aversion", "label": "Aversion", "kind": "textarea"},
            {
                "name": "magic_knowledge_level", "label": "Magic knowledge level", "kind": "select",
                "options": ["unaware", "suspicious", "partial", "knows", "understands"], "default": "unaware",
            },
            {"name": "internal_tensions", "label": "Internal tensions", "kind": "textarea"},
            # DORMANT trio (BRIEF-26, schema v1.38): stored and creator-editable,
            # read by no assembler or guard. See RELATION_TYPES's `controls`
            # comment and models.Faction for the same dormancy doctrine.
            {
                "name": "parent_faction_id", "label": "Parent faction", "kind": "entity_ref",
                "ref_type": "faction", "exclude_self": True,
            },
            {
                "name": "scope", "label": "Scope", "kind": "select",
                "options": ["", "global", "national", "regional", "local", "other"],
            },
            {"name": "goals", "label": "Goals", "kind": "textarea"},
        ],
    },
    "item": {
        "label": "Item",
        "model": Item,
        "fields": [
            {"name": "owner_id", "label": "Owner", "kind": "entity_ref", "ref_type": "character"},
            {"name": "location_id", "label": "Location", "kind": "entity_ref", "ref_type": "location"},
            {"name": "equipped", "label": "Equipped", "kind": "bool", "default": False},
            {"name": "condition", "label": "Condition", "kind": "text", "default": "intact"},
        ],
    },
}


def _player_character_id(db: DbSession, world_id: str) -> str:
    char = db.exec(
        select(Character)
        .join(Entity, Entity.id == Character.id)
        .where(
            Entity.world_id == world_id,
            Character.character_type == "player",
        )
    ).first()
    if char is None:
        raise HTTPException(status_code=400, detail="No player character in the active world.")
    return char.id


def _entity_summary(e: Entity) -> dict:
    return {
        "id": e.id,
        "world_id": e.world_id,
        "type": e.type,
        "name": e.name,
        "internal_name": e.internal_name,
        "status": e.status,
        "is_public": e.is_public,
    }


def _entity_dict(e: Entity) -> dict:
    return {
        "id": e.id,
        "world_id": e.world_id,
        "type": e.type,
        "name": e.name,
        "internal_name": e.internal_name,
        "description": e.description,
        "is_public": e.is_public,
        "status": e.status,
        "created_at": _iso(e.created_at),
        "updated_at": _iso(e.updated_at),
    }


def _extension_dict(entity_type: str, ext: Any) -> dict:
    spec = ENTITY_TYPE_REGISTRY[entity_type]
    return {f["name"]: getattr(ext, f["name"]) for f in spec["fields"]}


def _npc_prices_dict(entity_id: str, db: DbSession) -> dict[str, int]:
    """`npc_price` rows for one character, as `{tag: amount}` — the client
    shape the Tarifs editor expects (TICKET-0025, BRIEF-0025-a)."""
    rows = db.exec(select(NpcPrice).where(NpcPrice.entity_id == entity_id)).all()
    return {row.tag: row.amount for row in rows}


def _location_subculture_rows(location_id: str, db: DbSession) -> list[dict]:
    """`location_subculture` rows for one location, as
    `[{key, value, is_hidden}, ...]` (TICKET-0025, BRIEF-0025-b). Includes
    `is_hidden` rows — this is the creator-facing editor; structural
    exclusion for non-creator reads lives in context.py's query
    construction, not here."""
    rows = db.exec(select(LocationSubculture).where(LocationSubculture.location_id == location_id)).all()
    return [{"key": row.key, "value": row.value, "is_hidden": row.is_hidden} for row in rows]


def _location_geometry_dict(location_id: str, db: DbSession) -> dict:
    """Intra-location wall geometry for one location, as
    `{bounds_width, bounds_height, obstacles: [{id, vertices}, ...]}`
    (TICKET-0029, BRIEF-0029-a). Vertices ordered by `vertex_order`."""
    location = db.get(Location, location_id)
    obstacles = db.exec(
        select(Obstacle).where(Obstacle.location_id == location_id).order_by(Obstacle.created_at)
    ).all()
    obstacle_dicts = []
    for obstacle in obstacles:
        vertices = db.exec(
            select(ObstacleVertex)
            .where(ObstacleVertex.obstacle_id == obstacle.id)
            .order_by(ObstacleVertex.vertex_order)
        ).all()
        obstacle_dicts.append({
            "id": obstacle.id,
            "vertices": [[v.x, v.y] for v in vertices],
        })
    return {
        "bounds_width": location.bounds_width if location is not None else None,
        "bounds_height": location.bounds_height if location is not None else None,
        "obstacles": obstacle_dicts,
    }


def _location_doors_rows(location_id: str, db: DbSession) -> list[dict]:
    """`door` rows for one location, as [{id, target_location_id,
    target_name, x, y, edge_live}, ...] (TICKET-0034, BRIEF-0034-a).
    Ordered by target_name (stable panel order).

    CREATOR-FACING: returns EVERY row, including doors whose
    connects_to edge or target has since died — `edge_live: false` is
    exactly what lets the creator see and fix an orphan. Structural
    exclusion for play-side reads lives in cockpit/spatial_doors.py's
    query construction, not here (the location_subculture `is_hidden`
    precedent at :316)."""
    rows = db.exec(select(Door).where(Door.location_id == location_id)).all()

    def _edge_live(row: Door) -> bool:
        target = db.get(Entity, row.target_location_id)
        if target is None or target.type != "location" or target.status != "active":
            return False
        rel_a = db.exec(
            select(Relation).where(
                Relation.type == "connects_to",
                Relation.entity_a_id == location_id,
                Relation.entity_b_id == row.target_location_id,
            )
        ).first()
        rel_b = db.exec(
            select(Relation).where(
                Relation.type == "connects_to",
                Relation.entity_a_id == row.target_location_id,
                Relation.entity_b_id == location_id,
            )
        ).first()
        return rel_a is not None or rel_b is not None

    result = []
    for row in rows:
        target = db.get(Entity, row.target_location_id)
        result.append({
            "id": row.id,
            "target_location_id": row.target_location_id,
            "target_name": target.name if target is not None else row.target_location_id,
            "x": row.x,
            "y": row.y,
            "edge_live": _edge_live(row),
        })
    result.sort(key=lambda d: d["target_name"])
    return result


def _apply_base_fields(db: DbSession, entity: Entity, data: dict) -> None:
    for field in ENTITY_BASE_FIELDS:
        name = field["name"]
        value = _coerce_field(db, field, data.get(name))
        setattr(entity, name, value)


def _build_extension_kwargs(db: DbSession, entity_type: str, data: dict) -> dict:
    spec = ENTITY_TYPE_REGISTRY[entity_type]
    ext_kwargs = {f["name"]: _coerce_field(db, f, data.get(f["name"])) for f in spec["fields"]}
    if entity_type == "item" and ext_kwargs.get("equipped") and not ext_kwargs.get("owner_id"):
        raise HTTPException(422, "Equipping an item requires an owner")
    return ext_kwargs


class EntityWriteBody(BaseModel):
    entity: dict[str, Any]
    extension: dict[str, Any] = {}
    # Two-stage entity creation (TICKET-0019, BRIEF-0019-a): set only when
    # this create realizes an approved entity_creation germ from the
    # Création tab's pending-creations strip.
    mutation_id: Optional[str] = None


class NpcPricesBody(BaseModel):
    prices: dict[str, int] = {}


class LocationSubcultureBody(BaseModel):
    rows: list[dict[str, Any]] = []


class ObstacleIn(BaseModel):
    # EITHER vertices (>= 3, polygon-ready) OR rect (v1 UI shorthand,
    # [x, y, width, height]) — the endpoint expands rect server-side.
    vertices: Optional[list[list[float]]] = None
    rect: Optional[list[float]] = None


class LocationGeometryBody(BaseModel):
    bounds_width: Optional[float] = None
    bounds_height: Optional[float] = None
    obstacles: list[ObstacleIn] = []


class DoorIn(BaseModel):
    target_location_id: str
    x: float
    y: float


class LocationDoorsBody(BaseModel):
    doors: list[DoorIn] = []


class EntityTypeCreateBody(BaseModel):
    name: str
    slug: str
    trait_keys: list[str] = []


@router.get("/entity-types")
def get_entity_types(db: DbSession = Depends(get_session)) -> dict:
    """Registry metadata driving the composite form (decision 5).

    Adding a future type means one entry in ENTITY_TYPE_REGISTRY — the
    frontend renders the base form plus whatever `fields` the type declares.
    Runtime types (TICKET-0046, BRIEF-0046-b) are appended after the static
    ones: one `types[slug]` entry per ACTIVE, world-scoped `entity_type` row,
    its `fields` derived from `form_fields_for` over that row's checked
    `entity_trait` rows — never recomputed inline.
    """
    types: dict[str, Any] = {
        t: {"label": spec["label"], "fields": spec["fields"]}
        for t, spec in ENTITY_TYPE_REGISTRY.items()
    }
    runtime_types: list[str] = []
    world_id = _world_id(db)
    runtime_rows = db.exec(
        select(EntityType).where(
            EntityType.world_id == world_id, EntityType.status == "active"
        )
    ).all()
    for row in runtime_rows:
        trait_keys = [
            et.trait_key
            for et in db.exec(
                select(EntityTrait).where(EntityTrait.entity_type_id == row.id)
            ).all()
        ]
        types[row.slug] = {"label": row.name, "fields": form_fields_for(trait_keys)}
        runtime_types.append(row.slug)

    return {
        "entity_types": list(ENTITY_TYPE_REGISTRY.keys()) + runtime_types,
        "entity_base_fields": ENTITY_BASE_FIELDS,
        "entity_statuses": list(ENTITY_STATUSES),
        "types": types,
        "runtime_types": runtime_types,
        "checkable_traits": [
            {"key": t.key, "label": t.label} for t in checkable_traits()
        ],
        "relation_fields": RELATION_FIELDS,
        "knowledge_fields": KNOWLEDGE_FIELDS,
        "event_fields": EVENT_FIELDS,
    }


@router.post("/entity-types", status_code=201)
def create_entity_type_route(
    body: EntityTypeCreateBody, db: DbSession = Depends(get_session)
) -> dict:
    """Creator-direct type creation (TICKET-0046, BRIEF-0046-b). Composes
    the governed DDL/registry writer (`create_entity_type`, TICKET-0044)
    with the `entity_trait` projection inserts in the SAME transaction —
    never a second write path, never a bypass. Columns/fields derive
    exclusively from `ext_columns_for`/`form_fields_for` (S-norme)."""
    checkable_keys = {t.key for t in checkable_traits()}
    unknown = [k for k in body.trait_keys if k not in checkable_keys]
    if unknown:
        raise HTTPException(422, f"unknown or non-checkable trait_keys: {unknown}")

    if body.slug.casefold() in {k.casefold() for k in ENTITY_TYPE_REGISTRY}:
        raise HTTPException(422, "slug collides with a built-in type")

    columns = ext_columns_for(body.trait_keys)
    try:
        etype_id = create_entity_type(
            db,
            world_id=_world_id(db),
            name=body.name,
            slug=body.slug,
            columns=columns,
            changed_by="creator",
        )
        db.flush()
        for trait_key in body.trait_keys:
            db.add(EntityTrait(entity_type_id=etype_id, trait_key=trait_key))
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))

    return {
        "ok": True,
        "entity_type_id": etype_id,
        "slug": body.slug,
        "physical_table": "ext_" + body.slug,
    }


@router.get("/entities")
def list_entities(
    type: Optional[str] = Query(default=None),
    db: DbSession = Depends(get_session),
) -> list[dict]:
    stmt = select(Entity).where(Entity.world_id == _world_id(db))
    if type is not None:
        stmt = stmt.where(Entity.type == type)
    stmt = stmt.order_by(Entity.type, Entity.name)
    return [_entity_summary(e) for e in db.exec(stmt).all()]


@router.get("/entities/{entity_id}")
def get_entity(entity_id: str, db: DbSession = Depends(get_session)) -> dict:
    entity = _get_entity(db, entity_id)
    result = _entity_dict(entity)
    if entity.type in ENTITY_TYPE_REGISTRY:
        ext = db.get(ENTITY_TYPE_REGISTRY[entity.type]["model"], entity_id)
        result["extension"] = _extension_dict(entity.type, ext) if ext is not None else {}
        result["relations"] = _list_relations(entity_id, db)
        result["knowledge"] = _list_knowledge(entity_id, db)
        if entity.type == "character":
            result["prices"] = _npc_prices_dict(entity_id, db)
        elif entity.type == "location":
            result["subculture_rows"] = _location_subculture_rows(entity_id, db)
            result["geometry"] = _location_geometry_dict(entity_id, db)
            result["doors"] = _location_doors_rows(entity_id, db)
    else:
        # Governed runtime type or unknown slug: relations/knowledge stay []
        # this brief (deferral: runtime-type relations/knowledge UI, 0047+).
        runtime_spec = _runtime_type_spec(db, entity.type)
        result["extension"] = _read_runtime_ext_row(db, runtime_spec, entity_id) if runtime_spec else {}
        result["relations"] = []
        result["knowledge"] = []
    return result


def _stamp_type_template(db: DbSession, world_id: str, ext_row: Location) -> None:
    """E1, TICKET-0040: birth bounds from the location_type size template.
    Called from _create_entity_core ONLY - never from the update path
    (_build_extension_kwargs is shared with PUT /entities/{id} and would
    re-stamp on every edit, breaking F1: a template change is never
    retroactive).
    """
    if ext_row.bounds_width is not None or ext_row.bounds_height is not None:
        return
    template = location_type_template(db, world_id=world_id, type_name=ext_row.location_type)
    if template is None:
        return
    ext_row.bounds_width, ext_row.bounds_height = template


def _create_entity_core(body: EntityWriteBody, db: DbSession) -> Entity:
    """Commit-free core of `create_entity` — dispatches to the static
    (`ENTITY_TYPE_REGISTRY`) or governed-runtime (reflected `ext_*`,
    TICKET-0046 BRIEF-0046-e) path by `type`. An ungoverned slug (neither)
    is a 422 before any table is touched (A1 fail-closed)."""
    entity_type = body.entity.get("type")
    if entity_type in ENTITY_TYPE_REGISTRY:
        return _create_static_entity_core(body, db, entity_type)

    runtime_spec = _runtime_type_spec(db, entity_type) if entity_type else None
    if runtime_spec is None:
        raise HTTPException(
            422,
            f"type must be one of {list(ENTITY_TYPE_REGISTRY)} or an active governed entity type",
        )
    return _create_runtime_entity_core(body, db, entity_type, runtime_spec)


def _create_static_entity_core(body: EntityWriteBody, db: DbSession, entity_type: str) -> Entity:
    """Static-registry create core — moved verbatim out of
    `_create_entity_core` (BRIEF-0046-e), behavior byte-for-byte unchanged.

    Does everything up to and including `db.add` / `db.flush()` — never
    `db.commit()` / `db.refresh()`. Returns the `Entity` row (with its
    extension and, where applicable, primary faction membership already
    added to the session, uncommitted). Callable directly by a batch caller
    sharing the same session (BRIEF-35).

    If extension validation fails, nothing is written: the entity row is
    constructed in Python (its id is assigned at construction, not by the
    DB) but never added to the session, so no orphan `entity` row results.
    """
    data = body.entity
    name = data.get("name")
    if not name:
        raise HTTPException(422, "Name is required")

    entity = Entity(world_id=_world_id(db), type=entity_type, name=str(name))
    _apply_base_fields(db, entity, data)

    # `faction_id` on a character payload is no longer a `character` column
    # (BRIEF-28, schema v1.40): it is not in the registry's `fields`, so
    # `_build_extension_kwargs` never sees it. Pull it separately and recable
    # it onto a `faction_membership` row AFTER the entity's id is usable (the
    # membership write needs the new entity's id) — mirrors the post-accept
    # flush pattern used for BRIEF-24's `pendingDraftKnowledge`.
    pending_faction_id: Optional[str] = None
    if entity_type == "character":
        pending_faction_id = body.extension.get("faction_id") or None
        if pending_faction_id:
            faction = db.get(Entity, pending_faction_id)
            if faction is None or faction.type != "faction":
                raise HTTPException(422, f"{pending_faction_id!r} is not a valid faction entity id")

    # Validate the extension payload BEFORE adding anything to the session —
    # a 422 here leaves no orphan `entity` row.
    ext_kwargs = _build_extension_kwargs(db, entity_type, body.extension)
    ext_model = ENTITY_TYPE_REGISTRY[entity_type]["model"]
    if entity_type == "character":
        # `character.world_id` is denormalized from `entity.world_id`
        # (BRIEF-46, same pattern as `relation.world_id`) — system-managed,
        # never a user-editable registry field.
        ext_kwargs["world_id"] = entity.world_id
    ext_row = ext_model(id=entity.id, **ext_kwargs)
    if entity_type == "location":
        _stamp_type_template(db, entity.world_id, ext_row)

    db.add(entity)
    # Flush the entity row first: SQLModel's auto insert-order detection gets
    # confused for extension tables with multiple FK columns to entity.id
    # (e.g. character.current_location_id) and may try to insert the
    # extension row before its own entity row.
    db.flush()
    db.add(ext_row)

    if pending_faction_id:
        # Creator authority (this create/accept IS the creator action) — not
        # an AI proposal path. mode="open" only; history is sacred.
        write_membership(
            db,
            mode="open",
            world_id=entity.world_id,
            entity_id=entity.id,
            faction_id=pending_faction_id,
            role=None,
            is_primary=True,
            is_secret=False,
        )

    return entity


def _create_runtime_entity_core(
    body: EntityWriteBody, db: DbSession, entity_type: str, runtime_spec: dict
) -> Entity:
    """Governed-runtime-type create core (A1, TICKET-0046 BRIEF-0046-e): no
    SQLModel class exists for a runtime type, so the ext row goes in via
    `entity_runtime._insert_runtime_ext_row` instead of `db.add()`. No
    faction-membership leg (character-only, static types only)."""
    data = body.entity
    name = data.get("name")
    if not name:
        raise HTTPException(422, "Name is required")

    entity = Entity(world_id=_world_id(db), type=entity_type, name=str(name))
    _apply_base_fields(db, entity, data)

    # Validate the extension payload BEFORE adding anything to the session —
    # a 422 here leaves no orphan `entity` row (same posture as the static path).
    ext_kwargs = _build_runtime_ext_kwargs(db, runtime_spec["fields"], body.extension)

    db.add(entity)
    db.flush()
    _insert_runtime_ext_row(db, runtime_spec, entity.id, ext_kwargs)

    return entity


def _link_entity_creation(mutation_id: str, entity_id: str, db: DbSession) -> dict:
    """Guarded flip: entity_creation germ -> applied + created_entity_id
    (BRIEF-0019-a item 5, RECON F4). Guards — must exist, be
    entity_creation, be approved, and its payload must LACK
    created_entity_id (double-commit protection). REASSIGNMENT (not
    in-place update — SQLModel JSON columns don't detect in-place mutation).
    A guard failure NEVER rolls back the entity commit already made by the
    caller; it is returned as a visibility note only."""
    mut = db.get(ProposedMutation, mutation_id)
    if mut is None:
        return {"ok": False, "error": "mutation not found"}
    if mut.mutation_type != "entity_creation":
        return {"ok": False, "error": "mutation is not an entity_creation germ"}
    if mut.status != "approved":
        return {"ok": False, "error": f"mutation status is {mut.status!r}, not 'approved'"}
    payload = mut.payload if isinstance(mut.payload, dict) else {}
    if "created_entity_id" in payload:
        return {"ok": False, "error": "mutation already carries a created_entity_id"}

    mut.payload = {**payload, "created_entity_id": entity_id}
    mut.status = "applied"
    mut.applied_at = datetime.now(UTC)
    db.add(mut)
    db.commit()
    return {"ok": True}


@router.post("/entities", status_code=201)
def create_entity(body: EntityWriteBody, db: DbSession = Depends(get_session)) -> dict:
    """Composite create — entity + extension row (+ optional primary
    membership) in one transaction (single commit — BRIEF-35; previously two:
    entity+extension, then the membership leg)."""
    try:
        entity = _create_entity_core(body, db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Membership conflicts with an existing active row — at most one "
            "active primary per member, and no duplicate active membership "
            "in the same faction.",
        )
    db.refresh(entity)

    if entity.type in ENTITY_TYPE_REGISTRY:
        ext_row = db.get(ENTITY_TYPE_REGISTRY[entity.type]["model"], entity.id)
        db.refresh(ext_row)

        result = _entity_dict(entity)
        result["extension"] = _extension_dict(entity.type, ext_row)
        result["relations"] = []
        result["knowledge"] = []
        if entity.type == "character":
            result["prices"] = {}
        elif entity.type == "location":
            result["subculture_rows"] = []
            # TICKET-0040: read the real geometry - birth bounds come from the
            # type template (E1), so a hardcoded null stub would make the
            # client render an empty editor whose next save wipes them.
            result["geometry"] = _location_geometry_dict(entity.id, db)
            result["doors"] = []
    else:
        # Governed runtime type (TICKET-0046, BRIEF-0046-e).
        runtime_spec = _runtime_type_spec(db, entity.type)
        result = _entity_dict(entity)
        result["extension"] = _read_runtime_ext_row(db, runtime_spec, entity.id) if runtime_spec else {}
        result["relations"] = []
        result["knowledge"] = []

    if body.mutation_id:
        result["creation_linkage"] = _link_entity_creation(body.mutation_id, entity.id, db)
    return result


@router.put("/entities/{entity_id}")
def update_entity(entity_id: str, body: EntityWriteBody, db: DbSession = Depends(get_session)) -> dict:
    entity = _get_entity(db, entity_id)
    data = body.entity

    new_type = data.get("type")
    if new_type is not None and new_type != entity.type:
        raise HTTPException(422, "type cannot be changed after creation")

    prior_status = entity.status
    _apply_base_fields(db, entity, data)
    entity.updated_at = datetime.now(UTC)
    db.add(entity)

    ext: Any = None
    prior_location_id: Optional[str] = None
    runtime_spec: Optional[dict] = None
    if entity.type in ENTITY_TYPE_REGISTRY:
        ext_model = ENTITY_TYPE_REGISTRY[entity.type]["model"]
        ext = db.get(ext_model, entity_id)
        if ext is None:
            raise HTTPException(500, f"Missing {entity.type} extension row for entity {entity_id!r}")
        if entity.type == "character":
            prior_location_id = ext.current_location_id
        ext_kwargs = _build_extension_kwargs(db, entity.type, body.extension)
        for key, value in ext_kwargs.items():
            setattr(ext, key, value)
        db.add(ext)
    else:
        # Governed runtime type (TICKET-0046, BRIEF-0046-e): no SQLModel
        # class exists, so the ext row is a parameterized Core update()
        # against the reflected table instead of ORM attribute assignment.
        # Fail-closed: an ungoverned slug touches no table.
        runtime_spec = _runtime_type_spec(db, entity.type)
        if runtime_spec is None:
            raise HTTPException(422, f"{entity.type!r} is not a governed entity type")
        runtime_ext_kwargs = _build_runtime_ext_kwargs(db, runtime_spec["fields"], body.extension)
        _update_runtime_ext_row(db, runtime_spec, entity_id, runtime_ext_kwargs)

    # BRIEF-53 A1: a character's location change, or any transition to a
    # non-active entity.status, closes its open gathering_member rows
    # (gatherings are not canon — no proposed_mutation, no change_history).
    # Re-saving with the same current_location_id must not close anything.
    if entity.type == "character" and ext is not None and ext.current_location_id != prior_location_id:
        close_open_memberships(entity_id, db)
    if prior_status == "active" and entity.status != "active":
        close_open_memberships(entity_id, db)

    db.commit()
    db.refresh(entity)

    result = _entity_dict(entity)
    if ext is not None:
        db.refresh(ext)
        result["extension"] = _extension_dict(entity.type, ext)
        result["relations"] = _list_relations(entity_id, db)
        result["knowledge"] = _list_knowledge(entity_id, db)
        if entity.type == "character":
            result["prices"] = _npc_prices_dict(entity_id, db)
        elif entity.type == "location":
            result["subculture_rows"] = _location_subculture_rows(entity_id, db)
            result["geometry"] = _location_geometry_dict(entity_id, db)
            result["doors"] = _location_doors_rows(entity_id, db)
    elif runtime_spec is not None:
        result["extension"] = _read_runtime_ext_row(db, runtime_spec, entity_id)
        result["relations"] = []
        result["knowledge"] = []
    else:
        result["extension"] = {}
        result["relations"] = []
        result["knowledge"] = []
    return result


@router.post("/entities/{entity_id}/delete")
def delete_entity(entity_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Soft delete — `status = 'inactive'`. Relations/knowledge survive untouched."""
    entity = _get_entity(db, entity_id)
    entity.status = "inactive"
    entity.updated_at = datetime.now(UTC)
    db.add(entity)
    close_open_memberships(entity_id, db)
    db.commit()
    db.refresh(entity)
    return _entity_dict(entity)


@router.put("/entities/{entity_id}/prices")
def set_npc_prices(entity_id: str, body: NpcPricesBody, db: DbSession = Depends(get_session)) -> dict:
    """Full-replace an NPC's `npc_price` rows (Tarifs editor, TICKET-0025,
    BRIEF-0025-a — replaces the metadata.price_list read-merge-write)."""
    entity = _get_entity(db, entity_id)
    if entity.type != "character":
        raise HTTPException(422, "Prices are a character-only field")
    character = db.get(Character, entity_id)
    try:
        write_npc_prices(db, entity=character, prices=body.prices, changed_by="creator")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()

    result = _entity_dict(entity)
    ext = db.get(Character, entity_id)
    result["extension"] = _extension_dict("character", ext)
    result["relations"] = _list_relations(entity_id, db)
    result["knowledge"] = _list_knowledge(entity_id, db)
    result["prices"] = _npc_prices_dict(entity_id, db)
    return result


@router.put("/entities/{entity_id}/subculture")
def set_location_subculture(entity_id: str, body: LocationSubcultureBody, db: DbSession = Depends(get_session)) -> dict:
    """Full-replace a location's `location_subculture` rows (TICKET-0025,
    BRIEF-0025-b — replaces the `location.subculture` JSON textarea)."""
    entity = _get_entity(db, entity_id)
    if entity.type != "location":
        raise HTTPException(422, "Subculture is a location-only field")
    try:
        write_location_subculture(
            db, world_id=entity.world_id, location_id=entity_id,
            rows=body.rows, changed_by="creator",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()

    result = _entity_dict(entity)
    ext = db.get(Location, entity_id)
    result["extension"] = _extension_dict("location", ext)
    result["relations"] = _list_relations(entity_id, db)
    result["knowledge"] = _list_knowledge(entity_id, db)
    result["subculture_rows"] = _location_subculture_rows(entity_id, db)
    return result


@router.put("/entities/{entity_id}/geometry")
def set_location_geometry(entity_id: str, body: LocationGeometryBody, db: DbSession = Depends(get_session)) -> dict:
    """Full-replace a location's spatial geometry — playable bounds +
    obstacle polygons (TICKET-0029, BRIEF-0029-a). `rect` items are
    expanded server-side into 4 vertices clockwise from top-left
    `(x,y), (x+w,y), (x+w,y+h), (x,y+h)`; `vertices` items are
    polygon-ready as-is. One transaction: bounds on `location` +
    full-replace `obstacle`/`obstacle_vertex` via `write_location_obstacles`."""
    entity = _get_entity(db, entity_id)
    if entity.type != "location":
        raise HTTPException(404, f"Entity {entity_id!r} is not a location")

    if body.bounds_width is not None and body.bounds_width <= 0:
        raise HTTPException(422, "bounds_width must be > 0")
    if body.bounds_height is not None and body.bounds_height <= 0:
        raise HTTPException(422, "bounds_height must be > 0")

    polygons: list[list[tuple[float, float]]] = []
    for item in body.obstacles:
        if item.rect is not None:
            if len(item.rect) != 4:
                raise HTTPException(422, "rect must be [x, y, width, height]")
            x, y, w, h = item.rect
            if w <= 0 or h <= 0:
                raise HTTPException(422, "rect width and height must be > 0")
            polygons.append([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
        elif item.vertices is not None:
            polygons.append([(v[0], v[1]) for v in item.vertices])
        else:
            raise HTTPException(422, "each obstacle needs either 'vertices' or 'rect'")

    try:
        write_location_obstacles(
            db, world_id=entity.world_id, location_id=entity_id,
            obstacles=polygons, changed_by="creator",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    location = db.get(Location, entity_id)
    fields_set = body.model_fields_set
    # F1, TICKET-0040: a key absent from the body preserves the stored
    # value; an explicit null clears it. Same posture as
    # writes.upsert_location_type, which never overwrites a decided value
    # with NULL. Full-replace still governs `obstacle` rows below - only
    # the two bounds columns gained this distinction.
    if "bounds_width" in fields_set:
        location.bounds_width = body.bounds_width
    if "bounds_height" in fields_set:
        location.bounds_height = body.bounds_height
    db.add(location)
    db.commit()

    result = _entity_dict(entity)
    db.refresh(location)
    result["extension"] = _extension_dict("location", location)
    result["relations"] = _list_relations(entity_id, db)
    result["knowledge"] = _list_knowledge(entity_id, db)
    result["subculture_rows"] = _location_subculture_rows(entity_id, db)
    result["geometry"] = _location_geometry_dict(entity_id, db)
    return result


@router.put("/entities/{entity_id}/doors")
def set_location_doors(entity_id: str, body: LocationDoorsBody, db: DbSession = Depends(get_session)) -> dict:
    """Full-replace a location's `door` rows (TICKET-0034, BRIEF-0034-a).
    One row per `connects_to` neighbour the creator points a door at — the
    B1 gate (write_location_doors) rejects any target without a live
    connects_to edge. Nothing here resolves, judges or moves; see
    BRIEF-0034-b/-c for that."""
    entity = _get_entity(db, entity_id)
    if entity.type != "location":
        raise HTTPException(404, f"Entity {entity_id!r} is not a location")

    try:
        write_location_doors(
            db, world_id=entity.world_id, location_id=entity_id,
            doors=[d.model_dump() for d in body.doors], changed_by="creator",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    db.commit()

    result = _entity_dict(entity)
    location = db.get(Location, entity_id)
    result["extension"] = _extension_dict("location", location)
    result["relations"] = _list_relations(entity_id, db)
    result["knowledge"] = _list_knowledge(entity_id, db)
    result["subculture_rows"] = _location_subculture_rows(entity_id, db)
    result["geometry"] = _location_geometry_dict(entity_id, db)
    result["doors"] = _location_doors_rows(entity_id, db)
    return result


@router.get("/entities/{entity_id}/items")
def list_entity_items(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    """Items owned by `entity_id` — read-only listing for the character sheet.

    Single write path: item edition lives only in the entity author flow
    (ENTITY_TYPE_REGISTRY["item"]).
    """
    _get_entity(db, entity_id)
    rows = db.exec(
        select(Item, Entity)
        .join(Entity, Entity.id == Item.id)
        .where(Item.owner_id == entity_id)
        .order_by(Entity.name)
    ).all()
    return [
        {
            "id": item.id,
            "name": entity.name,
            "equipped": item.equipped,
            "condition": item.condition,
            "location_id": item.location_id,
        }
        for item, entity in rows
    ]
