"""Author CRUD — shared cross-domain accessors (TICKET-0027, BRIEF-0027-i).

BRIEF-0027-d's split left these helpers defined in one domain module while
sibling modules called them without importing — 80 pyflakes F821 sites
(undefined names resolved only because Python binds names at call time, so
every handler touching one 500s at request time; see BRIEF-0027-i).

This module is a **closed, package-private set** of the accessors actually
shared across `crud/*` domain modules, re-homed here so every caller
imports explicitly. It is not a catch-all (R6): adding a new entry requires
a brief. The set, and why each entry is here:

- `_iso`, `_world_id`, `_get_entity` — used across nearly every domain
  module (date serialization, active-world resolution, entity lookup).
- `RELATION_TYPES`, `RELATION_DIRECTIONS`, `RELATION_FIELDS`,
  `_relation_dict`, `_list_relations` — the relation field-spec and its
  dict-serializer/lister moved together to avoid a circular import between
  `relations.py` and this module (`_list_relations` calls `_relation_dict`).
- `KNOWLEDGE_LEVELS_ORDERED`, `KNOWLEDGE_FIELDS`, `_knowledge_dict`,
  `_list_knowledge` — same reasoning, for `knowledge.py`.
- `EVENT_TYPE_LABELS_FR`, `EVENT_KNOWLEDGE_STATUSES`, `EVENT_FIELDS` —
  `EVENT_FIELDS` is built from the other two, which `events.py` also uses
  for its own validation; kept together as one source of truth.

Every helper body below is byte-identical to its original definition; only
its module (and the callers' import lines) changed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from ...models import Entity, Knowledge, Relation, World


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _world_id(db: DbSession) -> str:
    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    if world is None:
        raise HTTPException(status_code=400, detail="No active world. Activate a world before proceeding.")
    return world.id


def _get_entity(db: DbSession, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id!r} not found")
    return entity


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


KNOWLEDGE_LEVELS_ORDERED = (
    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
)


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


EVENT_TYPE_LABELS_FR: dict[str, str] = {
    "political": "politique",
    "military":  "militaire",
    "criminal":  "criminel",
    "social":    "social",
    "mystery":   "mystère",
    "magical":   "magique",
    "other":     "autre",
}


EVENT_KNOWLEDGE_STATUSES = ("secret", "public", "confirmed")


EVENT_FIELDS: list[dict[str, Any]] = [
    {"name": "title", "label": "Titre", "kind": "text", "required": True},
    {"name": "description", "label": "Description", "kind": "textarea"},
    {"name": "type", "label": "Type", "kind": "datalist",
     "options": list(EVENT_TYPE_LABELS_FR.keys())},
    {"name": "knowledge_status", "label": "Statut de connaissance",
     "kind": "select", "options": list(EVENT_KNOWLEDGE_STATUSES),
     "default": "secret", "required": True},
    {"name": "location_id", "label": "Lieu", "kind": "entity_ref",
     "ref_type": "location"},
]
