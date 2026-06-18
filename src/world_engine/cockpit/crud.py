"""Author CRUD — direct canonical writes for creator-mode world editing.

This is the **author's** master tool: a second canonical write path,
alongside the approval pipeline (`_apply_mutation` in `app.py`). It is
deliberately a *direct* write with no `proposed_mutation` checkpoint — that
checkpoint exists to contain the local model's drift during play, not to
gate the creator, who is the authority over world state.

Scope (see Claude Code Brief — Author CRUD):
- Composite editors for `character`, `faction`, `location` (entity + its
  extension row, written transactionally).
- In-context `relation` / `knowledge` row editors, reached from an entity's
  sheet.
- `relation_change`/`new_knowledge` write rules are shared with
  `_apply_mutation` via `..writes.write_relation` / `..writes.write_knowledge`
  so the two paths cannot diverge.

Deletion policy:
- Entities: **soft delete** (`entity.status = 'inactive'`) — reversible,
  relations/knowledge pointing at it survive.
- `relation` / `knowledge` rows: **hard delete** — they are edges/facts the
  author poses and must be able to remove cleanly.

Author edits to `relation` are state-setting, not delta accumulation —
but still append the previous state to `change_history` first (history is
sacred on both write paths; see `writes.write_relation(mode="set")`).
Author edits pass through **no** `proposed_mutation` (decision 1).

Creator-mode-only: this router is mounted on the cockpit app, which is the
creator's tool (bound to 127.0.0.1, no auth, "creator review dashboard" —
see app.py). The player-facing app is a separate, not-yet-built surface;
nothing here is linked or routed from it.

Type → extension registry (`ENTITY_TYPE_REGISTRY`): adding a future type
(e.g. `artifact`) is one registry entry — the composite form, validation and
serialization are all driven from here.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session as DbSession, select

from ..db import get_session
from ..models import Character, DiscoverableDetail, Entity, Faction, Item, Knowledge, Location, Relation, Skill, World
from ..writes import KNOWLEDGE_LEVELS, write_knowledge, write_relation

router = APIRouter(prefix="/api", tags=["author-crud"])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# ── Field-spec vocabularies (world-engine-schema.md) ──────────────────────────

ENTITY_STATUSES = ("active", "inactive", "destroyed", "missing")

# connects_to is location<->location map topology, NOT a social signal.
# Stored as a relation row (direction='mutual', intensity=50 — the intensity
# is a structural default with NO meaning). No gameplay consumer reads it
# (initiative vote and context assemblers are keyed on character/player ids;
# a connects_to row has two location endpoints, so it is structurally
# isolated). Any future world-wide relation scan MUST exclude
# type='connects_to'.
RELATION_TYPES = (
    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
    "instrumentalizes", "interest", "indifference", "rejection",
    "passive_attention", "other", "connects_to",
)
RELATION_DIRECTIONS = ("mutual", "a_to_b", "b_to_a")

# Ordered for display (schema doc order); KNOWLEDGE_LEVELS itself is a set.
KNOWLEDGE_LEVELS_ORDERED = (
    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
)

# skill sheet — fixed display order (schema v1.22, BRIEF-10)
SKILL_DOMAINS = ("physical", "agility", "perception", "composure")
SKILL_TIERS = (-1, 0, 1, 2)


# ── Entity base fields (the `entity` table) ───────────────────────────────────
# `type` is intentionally absent here — it is set at creation and locked
# afterward (handled directly by the create/update endpoints).

ENTITY_BASE_FIELDS: list[dict[str, Any]] = [
    {"name": "name", "label": "Name", "kind": "text", "required": True},
    {"name": "internal_name", "label": "Internal name (creator-only)", "kind": "text"},
    {"name": "description", "label": "Description", "kind": "textarea"},
    {"name": "is_public", "label": "Public", "kind": "bool", "default": True},
    {"name": "status", "label": "Status", "kind": "select", "options": list(ENTITY_STATUSES), "default": "active"},
    {"name": "metadata", "label": "Metadata (JSON)", "kind": "json"},
]


# ── Type → extension registry ─────────────────────────────────────────────────

ENTITY_TYPE_REGISTRY: dict[str, dict[str, Any]] = {
    "character": {
        "label": "Character",
        "model": Character,
        "fields": [
            {
                "name": "character_type", "label": "Character type", "kind": "select",
                "options": ["player", "npc"], "default": "npc", "required": True,
            },
            {"name": "faction_id", "label": "Faction", "kind": "entity_ref", "ref_type": "faction"},
            {"name": "current_location_id", "label": "Current location", "kind": "entity_ref", "ref_type": "location"},
            {
                "name": "vital_status", "label": "Vital status", "kind": "select",
                "options": ["alive", "dead", "missing", "unknown"], "default": "alive",
            },
            {"name": "appearance", "label": "Appearance", "kind": "textarea"},
            {"name": "backstory", "label": "Backstory", "kind": "textarea"},
            {"name": "secrets", "label": "Secrets (JSON, creator-only)", "kind": "json"},
        ],
    },
    "location": {
        "label": "Location",
        "model": Location,
        "fields": [
            {"name": "parent_location_id", "label": "Parent location", "kind": "entity_ref", "ref_type": "location"},
            {
                "name": "location_type", "label": "Location type", "kind": "datalist",
                "options": ["city", "district", "building", "natural", "underground", "other"],
            },
            {"name": "subculture", "label": "Subculture (JSON)", "kind": "json"},
            {
                "name": "magic_status", "label": "Magic status", "kind": "select",
                "options": ["inert", "sensitive", "active", "nexus"], "default": "inert",
            },
            {"name": "coordinates", "label": "Coordinates (JSON)", "kind": "json"},
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
            {
                "name": "magic_knowledge_level", "label": "Magic knowledge level", "kind": "select",
                "options": ["unaware", "suspicious", "partial", "knows", "understands"], "default": "unaware",
            },
            {"name": "internal_tensions", "label": "Internal tensions", "kind": "textarea"},
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


# ── Relation / knowledge field specs (in-context panels) ──────────────────────

RELATION_FIELDS: list[dict[str, Any]] = [
    {"name": "type", "label": "Type", "kind": "datalist", "options": list(RELATION_TYPES), "required": True},
    {"name": "intensity", "label": "Intensity (1-100)", "kind": "number", "min": 1, "max": 100, "default": 50},
    {"name": "direction", "label": "Direction", "kind": "select", "options": list(RELATION_DIRECTIONS), "default": "mutual"},
    {"name": "visible_to_b", "label": "Visible to B", "kind": "bool", "default": True},
    {"name": "notes", "label": "Notes", "kind": "textarea"},
]

KNOWLEDGE_FIELDS: list[dict[str, Any]] = [
    {"name": "subject", "label": "Subject", "kind": "text", "required": True},
    {
        "name": "level", "label": "Level", "kind": "select",
        "options": list(KNOWLEDGE_LEVELS_ORDERED), "default": "rumor", "required": True,
    },
    {"name": "content", "label": "Content", "kind": "textarea"},
    {"name": "source", "label": "Source", "kind": "text"},
    {"name": "is_incorrect", "label": "Incorrect", "kind": "bool", "default": False},
    {"name": "is_secret", "label": "Secret", "kind": "bool", "default": False},
    {"name": "share_threshold", "label": "Share threshold (1-100)", "kind": "number", "min": 1, "max": 100, "default": 50},
]


# ── Field coercion / validation (shared by entity base, extension, relation,
#    and knowledge field specs — all are the same {name, kind, ...} shape) ────

def _validate_entity_ref(db: DbSession, value: Any, ref_type: str, label: str) -> Optional[str]:
    if not value:
        return None
    target = db.get(Entity, value)
    if target is None or target.type != ref_type:
        raise HTTPException(422, f"{label}: {value!r} is not a valid {ref_type} entity id")
    return value


def _coerce_field(db: DbSession, field: dict, raw: Any) -> Any:
    kind = field["kind"]
    label = field.get("label", field["name"])
    required = field.get("required", False)

    if kind == "entity_ref":
        val = _validate_entity_ref(db, raw, field["ref_type"], label)
        if required and val is None:
            raise HTTPException(422, f"{label} is required")
        return val

    if kind == "bool":
        if raw is None:
            return bool(field.get("default", False))
        return bool(raw)

    if kind == "number":
        if raw is None or raw == "":
            if required:
                raise HTTPException(422, f"{label} is required")
            return field.get("default")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            raise HTTPException(422, f"{label} must be a number")
        lo, hi = field.get("min"), field.get("max")
        if lo is not None:
            n = max(lo, n)
        if hi is not None:
            n = min(hi, n)
        return n

    if kind == "json":
        if raw in (None, ""):
            return None
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise HTTPException(422, f"{label}: invalid JSON ({exc})")
        return raw

    if kind == "select":
        if raw in (None, ""):
            if required and "default" not in field:
                raise HTTPException(422, f"{label} is required")
            return field.get("default")
        options = field.get("options")
        if options and raw not in options:
            raise HTTPException(422, f"{label}: {raw!r} is not one of {options}")
        return raw

    # text / textarea / datalist
    if raw in (None, ""):
        if required:
            raise HTTPException(422, f"{label} is required")
        return field.get("default")
    return str(raw)


def _world_id(db: DbSession) -> str:
    world = db.exec(select(World)).first()
    if world is None:
        raise HTTPException(status_code=500, detail="No world row found — run scripts/seed_pilot.py")
    return world.id


def _get_entity(db: DbSession, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id!r} not found")
    return entity


# ── Serialization ──────────────────────────────────────────────────────────────

def _entity_summary(e: Entity) -> dict:
    return {
        "id": e.id,
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
        "metadata": e.metadata_,
        "created_at": _iso(e.created_at),
        "updated_at": _iso(e.updated_at),
    }


def _extension_dict(entity_type: str, ext: Any) -> dict:
    spec = ENTITY_TYPE_REGISTRY[entity_type]
    return {f["name"]: getattr(ext, f["name"]) for f in spec["fields"]}


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


def _knowledge_dict(k: Knowledge) -> dict:
    return {
        "id": k.id,
        "entity_id": k.entity_id,
        "subject": k.subject,
        "level": k.level,
        "content": k.content,
        "source": k.source,
        "is_incorrect": k.is_incorrect,
        "is_secret": k.is_secret,
        "share_threshold": k.share_threshold,
        "session_id": k.session_id,
        "acquired_at": _iso(k.acquired_at),
        "updated_at": _iso(k.updated_at),
    }


def _list_knowledge(entity_id: str, db: DbSession) -> list[dict]:
    rows = db.exec(
        select(Knowledge)
        .where(Knowledge.entity_id == entity_id)
        .order_by(Knowledge.acquired_at)
    ).all()
    return [_knowledge_dict(k) for k in rows]


# ── Field application ──────────────────────────────────────────────────────────

def _apply_base_fields(db: DbSession, entity: Entity, data: dict) -> None:
    for field in ENTITY_BASE_FIELDS:
        name = field["name"]
        attr = "metadata_" if name == "metadata" else name
        value = _coerce_field(db, field, data.get(name))
        setattr(entity, attr, value)


def _build_extension_kwargs(db: DbSession, entity_type: str, data: dict) -> dict:
    spec = ENTITY_TYPE_REGISTRY[entity_type]
    ext_kwargs = {f["name"]: _coerce_field(db, f, data.get(f["name"])) for f in spec["fields"]}
    if entity_type == "item" and ext_kwargs.get("equipped") and not ext_kwargs.get("owner_id"):
        raise HTTPException(422, "Equipping an item requires an owner")
    return ext_kwargs


# ── Request bodies ──────────────────────────────────────────────────────────────

class EntityWriteBody(BaseModel):
    entity: dict[str, Any]
    extension: dict[str, Any] = {}


class RelationWriteBody(BaseModel):
    other_entity_id: Optional[str] = None  # required on create; ignored on update
    type: Optional[str] = None
    intensity: Optional[int] = None
    direction: Optional[str] = None
    visible_to_b: Optional[bool] = None
    notes: Optional[str] = None


class KnowledgeWriteBody(BaseModel):
    subject: Optional[str] = None
    level: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    is_incorrect: bool = False
    is_secret: bool = False
    share_threshold: Optional[int] = None


# ── Registry / metadata ───────────────────────────────────────────────────────

@router.get("/entity-types")
def get_entity_types() -> dict:
    """Registry metadata driving the composite form (decision 5).

    Adding a future type means one entry in ENTITY_TYPE_REGISTRY — the
    frontend renders the base form plus whatever `fields` the type declares.
    """
    return {
        "entity_types": list(ENTITY_TYPE_REGISTRY.keys()),
        "entity_base_fields": ENTITY_BASE_FIELDS,
        "entity_statuses": list(ENTITY_STATUSES),
        "types": {
            t: {"label": spec["label"], "fields": spec["fields"]}
            for t, spec in ENTITY_TYPE_REGISTRY.items()
        },
        "relation_fields": RELATION_FIELDS,
        "knowledge_fields": KNOWLEDGE_FIELDS,
    }


# ── Entity list / detail ─────────────────────────────────────────────────────

@router.get("/entities")
def list_entities(
    type: Optional[str] = Query(default=None),
    db: DbSession = Depends(get_session),
) -> list[dict]:
    stmt = select(Entity)
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
    else:
        result["extension"] = {}
        result["relations"] = []
        result["knowledge"] = []
    return result


# ── Composite create / update / soft delete ──────────────────────────────────

@router.post("/entities", status_code=201)
def create_entity(body: EntityWriteBody, db: DbSession = Depends(get_session)) -> dict:
    """Composite create — entity + extension row in one transaction.

    If extension validation fails, nothing is written: the entity row is
    constructed in Python (its id is assigned at construction, not by the
    DB) but never added to the session, so no orphan `entity` row results.
    """
    data = body.entity
    entity_type = data.get("type")
    if entity_type not in ENTITY_TYPE_REGISTRY:
        raise HTTPException(422, f"type must be one of {list(ENTITY_TYPE_REGISTRY)}")

    name = data.get("name")
    if not name:
        raise HTTPException(422, "Name is required")

    entity = Entity(world_id=_world_id(db), type=entity_type, name=str(name))
    _apply_base_fields(db, entity, data)

    # Validate the extension payload BEFORE adding anything to the session —
    # a 422 here leaves no orphan `entity` row.
    ext_kwargs = _build_extension_kwargs(db, entity_type, body.extension)
    ext_model = ENTITY_TYPE_REGISTRY[entity_type]["model"]
    ext_row = ext_model(id=entity.id, **ext_kwargs)

    db.add(entity)
    # Flush the entity row first: SQLModel's auto insert-order detection gets
    # confused for extension tables with multiple FK columns to entity.id
    # (e.g. character.faction_id, character.current_location_id) and may try
    # to insert the extension row before its own entity row.
    db.flush()
    db.add(ext_row)
    db.commit()
    db.refresh(entity)
    db.refresh(ext_row)

    result = _entity_dict(entity)
    result["extension"] = _extension_dict(entity_type, ext_row)
    result["relations"] = []
    result["knowledge"] = []
    return result


@router.put("/entities/{entity_id}")
def update_entity(entity_id: str, body: EntityWriteBody, db: DbSession = Depends(get_session)) -> dict:
    entity = _get_entity(db, entity_id)
    data = body.entity

    new_type = data.get("type")
    if new_type is not None and new_type != entity.type:
        raise HTTPException(422, "type cannot be changed after creation")

    _apply_base_fields(db, entity, data)
    entity.updated_at = datetime.now(UTC)
    db.add(entity)

    ext: Any = None
    if entity.type in ENTITY_TYPE_REGISTRY:
        ext_model = ENTITY_TYPE_REGISTRY[entity.type]["model"]
        ext = db.get(ext_model, entity_id)
        if ext is None:
            raise HTTPException(500, f"Missing {entity.type} extension row for entity {entity_id!r}")
        ext_kwargs = _build_extension_kwargs(db, entity.type, body.extension)
        for key, value in ext_kwargs.items():
            setattr(ext, key, value)
        db.add(ext)

    db.commit()
    db.refresh(entity)

    result = _entity_dict(entity)
    if ext is not None:
        db.refresh(ext)
        result["extension"] = _extension_dict(entity.type, ext)
        result["relations"] = _list_relations(entity_id, db)
        result["knowledge"] = _list_knowledge(entity_id, db)
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
    db.commit()
    db.refresh(entity)
    return _entity_dict(entity)


# ── In-context relation editor ────────────────────────────────────────────────

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


# ── In-context knowledge editor ───────────────────────────────────────────────

@router.get("/entities/{entity_id}/knowledge")
def list_entity_knowledge(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    _get_entity(db, entity_id)
    return _list_knowledge(entity_id, db)


@router.post("/entities/{entity_id}/knowledge", status_code=201)
def create_knowledge(entity_id: str, body: KnowledgeWriteBody, db: DbSession = Depends(get_session)) -> dict:
    _get_entity(db, entity_id)
    if not body.subject:
        raise HTTPException(422, "subject is required")
    if body.level not in KNOWLEDGE_LEVELS:
        raise HTTPException(422, f"level must be one of {sorted(KNOWLEDGE_LEVELS)}")

    k = write_knowledge(
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


# ── In-context items (read-only, for the character sheet) ────────────────────

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


# ── Skill sheet (BRIEF-10, schema v1.22) ──────────────────────────────────────
# Creator-mode direct write — no `proposed_mutation`, same rule as the rest of
# this module. Player-mode read-only rendering is a frontend-only distinction
# (the cockpit is the creator's tool; the player-facing app is separate).

def _skill_dict(s: Skill) -> dict:
    return {
        "id": s.id,
        "character_id": s.character_id,
        "domain": s.domain,
        "tier": s.tier,
        "change_history": s.change_history,
        "updated_at": _iso(s.updated_at),
    }


@router.get("/skills/player-characters")
def list_skill_player_characters(db: DbSession = Depends(get_session)) -> list[dict]:
    """Player characters (`character_type = 'player'`), for the Fiche selector."""
    rows = db.exec(
        select(Entity, Character)
        .join(Character, Character.id == Entity.id)
        .where(Character.character_type == "player")
        .order_by(Entity.name)
    ).all()
    return [{"id": e.id, "name": e.name} for e, _ in rows]


@router.get("/skills")
def list_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
    """A player character's skill sheet, in fixed domain order."""
    _get_entity(db, character_id)
    rows = db.exec(select(Skill).where(Skill.character_id == character_id)).all()
    order = {domain: i for i, domain in enumerate(SKILL_DOMAINS)}
    rows.sort(key=lambda s: order.get(s.domain, len(SKILL_DOMAINS)))
    return [_skill_dict(s) for s in rows]


class SkillTierBody(BaseModel):
    tier: int


@router.patch("/skills/{skill_id}")
def update_skill_tier(skill_id: str, body: SkillTierBody, db: DbSession = Depends(get_session)) -> dict:
    """Creator edit: set a skill's tier directly (canon write, no checkpoint).

    Archives the previous tier into `change_history` and bumps `updated_at`
    — but only on an actual change, so resubmitting the same tier is a no-op.
    """
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(404, f"Skill {skill_id!r} not found")
    if body.tier not in SKILL_TIERS:
        raise HTTPException(422, f"tier must be one of {SKILL_TIERS}")

    if body.tier != skill.tier:
        history = list(skill.change_history or [])
        history.append({
            "tier": skill.tier,
            "changed_at": datetime.now(UTC).isoformat(),
            "by": "creator",
        })
        skill.change_history = history
        skill.tier = body.tier
        skill.updated_at = datetime.now(UTC)
        db.add(skill)
        db.commit()
        db.refresh(skill)

    return _skill_dict(skill)


# ── Discoverable details (schema v1.26, BRIEF-13) ────────────────────────────
# Creator-direct writes — same doctrine as the rest of this module: no
# proposed_mutation checkpoint, because the creator is the authority.
# In player mode this entire surface is hidden (index.html conditionally
# renders it only in creator mode).
# This table is NEVER read by any context assembler — structural exclusion,
# not instruction. See models.py DiscoverableDetail NOTE.

ACCESS_LEVELS = ("hidden", "ambient")


def _detail_dict(d: DiscoverableDetail) -> dict:
    return {
        "id": d.id,
        "world_id": d.world_id,
        "location_id": d.location_id,
        "subject": d.subject,
        "content": d.content,
        "access_level": d.access_level,
        "discovery_threshold": d.discovery_threshold,
        "discovered": d.discovered,
        "signpost_group": d.signpost_group,
        "created_at": _iso(d.created_at),
        "updated_at": _iso(d.updated_at),
    }


@router.get("/locations/{location_id}/discoverable-details")
def list_discoverable_details(
    location_id: str, db: DbSession = Depends(get_session)
) -> list[dict]:
    """List all discoverable details for a location (creator view)."""
    _get_entity(db, location_id)
    rows = db.exec(
        select(DiscoverableDetail)
        .where(DiscoverableDetail.location_id == location_id)
        .order_by(DiscoverableDetail.created_at, DiscoverableDetail.id)
    ).all()
    return [_detail_dict(d) for d in rows]


class DiscoverableDetailBody(BaseModel):
    world_id: str
    subject: str
    content: str
    access_level: str = "hidden"
    discovery_threshold: int = 0
    signpost_group: Optional[str] = None


@router.post("/locations/{location_id}/discoverable-details")
def create_discoverable_detail(
    location_id: str,
    body: DiscoverableDetailBody,
    db: DbSession = Depends(get_session),
) -> dict:
    """Seed a new discoverable detail on a location (creator direct write)."""
    _get_entity(db, location_id)
    if body.access_level not in ACCESS_LEVELS:
        raise HTTPException(422, f"access_level must be one of {ACCESS_LEVELS}")
    if not (0 <= body.discovery_threshold <= 12):
        raise HTTPException(422, "discovery_threshold must be between 0 and 12")
    detail = DiscoverableDetail(
        world_id=body.world_id,
        location_id=location_id,
        subject=body.subject,
        content=body.content,
        access_level=body.access_level,
        discovery_threshold=body.discovery_threshold,
        signpost_group=body.signpost_group,
    )
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return _detail_dict(detail)


class DiscoverableDetailPatchBody(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    access_level: Optional[str] = None
    discovery_threshold: Optional[int] = None
    discovered: Optional[bool] = None
    signpost_group: Optional[str] = None
    clear_signpost_group: bool = False  # explicit flag — signpost_group=None alone means "no change"


@router.put("/discoverable-details/{detail_id}")
def update_discoverable_detail(
    detail_id: str,
    body: DiscoverableDetailPatchBody,
    db: DbSession = Depends(get_session),
) -> dict:
    """Edit a discoverable detail (creator direct write).

    `discovered` is normally read-only (flipped by _apply_mutation on approve),
    but the creator can reset it to False to re-enable re-discovery.
    """
    detail = db.get(DiscoverableDetail, detail_id)
    if detail is None:
        raise HTTPException(404, f"DiscoverableDetail {detail_id!r} not found")
    if body.access_level is not None and body.access_level not in ACCESS_LEVELS:
        raise HTTPException(422, f"access_level must be one of {ACCESS_LEVELS}")
    if body.discovery_threshold is not None and not (0 <= body.discovery_threshold <= 12):
        raise HTTPException(422, "discovery_threshold must be between 0 and 12")
    if body.subject is not None:
        detail.subject = body.subject
    if body.content is not None:
        detail.content = body.content
    if body.access_level is not None:
        detail.access_level = body.access_level
    if body.discovery_threshold is not None:
        detail.discovery_threshold = body.discovery_threshold
    if body.discovered is not None:
        detail.discovered = body.discovered
    if body.clear_signpost_group:
        detail.signpost_group = None
    elif body.signpost_group is not None:
        detail.signpost_group = body.signpost_group
    detail.updated_at = datetime.now(UTC)
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return _detail_dict(detail)


@router.delete("/discoverable-details/{detail_id}")
def delete_discoverable_detail(
    detail_id: str, db: DbSession = Depends(get_session)
) -> dict:
    """Delete a discoverable detail (creator direct write — hard delete)."""
    detail = db.get(DiscoverableDetail, detail_id)
    if detail is None:
        raise HTTPException(404, f"DiscoverableDetail {detail_id!r} not found")
    db.delete(detail)
    db.commit()
    return {"deleted": detail_id}


# ── Location map graph (BRIEF-15, schema v1.28) ──────────────────────────────

@router.get("/locations/graph")
def get_locations_graph(db: DbSession = Depends(get_session)) -> dict:
    """Active location nodes + connects_to edges — read-only, creator surface.

    nodes: all active location entities joined to their extension (for coordinates).
    edges: connects_to relations whose both endpoints are in nodes (dangling
           edges from soft-deleted locations are filtered out server-side).
    """
    world_id = _world_id(db)

    rows = db.exec(
        select(Entity, Location)
        .join(Location, Location.id == Entity.id)
        .where(Entity.type == "location")
        .where(Entity.world_id == world_id)
        .where(Entity.status == "active")
        .order_by(Entity.name)
    ).all()

    active_ids = {e.id for e, _ in rows}
    nodes = [
        {"id": e.id, "name": e.name, "coordinates": loc.coordinates}
        for e, loc in rows
    ]

    rels = db.exec(
        select(Relation)
        .where(Relation.world_id == world_id)
        .where(Relation.type == "connects_to")
    ).all()
    edges = [
        {
            "id": r.id,
            "entity_a_id": r.entity_a_id,
            "entity_b_id": r.entity_b_id,
            "direction": r.direction,
        }
        for r in rels
        if r.entity_a_id in active_ids and r.entity_b_id in active_ids
    ]

    return {"nodes": nodes, "edges": edges}


__all__ = ["router", "ENTITY_TYPE_REGISTRY"]
