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
- `ledger` rows: **append-only, no delete, no update, ever** (schema v1.31,
  BRIEF-18) — a deliberate divergence from the policy above. A mistake is
  corrected with a new compensating line (`source_type='correction'`), never
  by editing or deleting an existing row. `write_ledger_entry` (`..writes`)
  is the single chokepoint; this module's `POST /api/ledger` is one of only
  two sanctioned canon-write paths into `ledger` (the other is
  `_apply_mutation`'s `resource_change` branch, BRIEF-19, which reuses the
  same helper).
- `event` rows: **no delete, ever** (TICKET-0022, C3) — an event either
  happened or did not; `event` is history. Retraction is
  `knowledge_status = 'secret'`, which structurally excludes the row from
  all four readers (`context.py`, `tick.py` x2, `app.py`'s return-visit
  delta). Mirrors `ledger`'s append-only policy above.

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
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DbSession, select

from ..db import get_session
from ..entity_author import generate_npc_goals
from ..gathering import close_open_memberships
from ..ledger import get_balance, list_entries
from ..ollama_client import OllamaError, ping
from ..models import (
    Agenda,
    AgendaStep,
    BASE_SKILL_DOMAINS,
    Character,
    DiscoverableDetail,
    Entity,
    Event,
    Faction,
    FactionMembership,
    FactionRole,
    GoalAgendaLink,
    Item,
    Knowledge,
    Ledger,
    Location,
    NpcGoal,
    PromptTemplate,
    ProposedMutation,
    Relation,
    Skill,
    SkillDefinition,
    World,
)
from ..prompt_registry import PROMPT_REGISTRY, effective_model
from ..prompt_store import current_prompt, get_version, list_versions
from ..tick import _EVENT_TYPES
from ..writes import (
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
    write_membership,
    write_npc_goal,
    write_npc_goal_prerequisites,
    write_npc_goal_status,
    write_prompt_version,
    write_relation,
    write_skill_tier,
)

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
#
# controls: controller (faction OR any entity) -> controlled asset
# (location | item | artifact | character | other). direction='a_to_b'
# (controller is entity_a, asset is entity_b). intensity is a MEANINGLESS
# structural default (50) with no social significance — it MUST NEVER be
# read as an affective or relational signal. Structurally isolated like
# connects_to: every gameplay consumer of `relation` is keyed on a
# character/player id, so a controls row (controller + asset endpoints) is
# invisible to the initiative vote and to both context assemblers. Any
# future world-wide relation scan added to the codebase MUST explicitly
# exclude type='controls' (and type='connects_to'). Reading "who controls
# asset X" = the entity_a of controls rows whose entity_b = X; shared or
# contested control = several controls rows, no special handling.
RELATION_TYPES = (
    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
    "instrumentalizes", "interest", "indifference", "rejection",
    "passive_attention", "other", "connects_to", "controls",
)
RELATION_DIRECTIONS = ("mutual", "a_to_b", "b_to_a")

# Ordered for display (schema doc order); KNOWLEDGE_LEVELS itself is a set.
KNOWLEDGE_LEVELS_ORDERED = (
    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
)

# skill sheet — fixed display order (schema v1.22, BRIEF-10); the four
# literal domains are BASE_SKILL_DOMAINS (models.py, schema v1.63 — single
# source of truth, decision 3).
SKILL_DOMAINS = BASE_SKILL_DOMAINS
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
            {"name": "current_location_id", "label": "Current location", "kind": "entity_ref", "ref_type": "location"},
            {
                "name": "vital_status", "label": "Vital status", "kind": "select",
                "options": ["alive", "dead", "missing", "unknown"], "default": "alive",
            },
            {"name": "appearance", "label": "Appearance", "kind": "textarea"},
            {"name": "backstory", "label": "Backstory", "kind": "textarea"},
            {"name": "aversion", "label": "Aversion", "kind": "textarea"},
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
                "options": ["city", "district", "building", "room", "natural", "underground", "other"],
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


# ── Event field specs (TICKET-0022, BRIEF-0022-a) ─────────────────────────────
# Single source of the event-type vocabulary is tick.py:_EVENT_TYPES — the
# tick CLAMPS model proposals onto it (tick.py:877). The creator must write
# into the SAME vocabulary or the column carries two disjoint namespaces.
# Imported, never re-typed (drafting decision 1). The assert below fails
# loudly at import if the two vocabularies ever diverge.
EVENT_TYPE_LABELS_FR: dict[str, str] = {
    "political": "politique",
    "military":  "militaire",
    "criminal":  "criminel",
    "social":    "social",
    "mystery":   "mystère",
    "magical":   "magique",
    "other":     "autre",
}
assert set(EVENT_TYPE_LABELS_FR) == set(_EVENT_TYPES), (
    "EVENT_TYPE_LABELS_FR's key set has diverged from tick._EVENT_TYPES"
)

# Mirrors app.py:1572's clamp exactly. Note: tick.py:880 accepts only
# ("secret", "public") — a narrower, pre-existing clamp on the
# model-proposal path, deliberately left alone by this brief.
EVENT_KNOWLEDGE_STATUSES = ("secret", "public", "confirmed")

# `involved_entities` is deliberately ABSENT — not a scalar field, handled by
# the chip editor. `occurred_at` is absent (E3, dormant column).
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
    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    if world is None:
        raise HTTPException(status_code=400, detail="No active world. Activate a world before proceeding.")
    return world.id


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


def _get_entity(db: DbSession, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id!r} not found")
    return entity


# ── Serialization ──────────────────────────────────────────────────────────────

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
    stores the id")."""
    items = g.prerequisites or []
    out = []
    for item in items:
        target = db.get(Entity, item.get("target_entity_id"))
        out.append({
            "type": item.get("type"),
            "target_entity_id": item.get("target_entity_id"),
            "target_entity_name": target.name if target else item.get("target_entity_id"),
            "threshold": item.get("threshold"),
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
    # Two-stage entity creation (TICKET-0019, BRIEF-0019-a): set only when
    # this create realizes an approved entity_creation germ from the
    # Création tab's pending-creations strip.
    mutation_id: Optional[str] = None


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


class GoalWriteBody(BaseModel):
    description: Optional[str] = None
    horizon: Optional[str] = None


class GoalStatusBody(BaseModel):
    status: Optional[str] = None


class GoalPrerequisitesBody(BaseModel):
    prerequisites: Optional[list[dict[str, Any]]] = None


class FactionRoleCreateBody(BaseModel):
    name: str
    description: Optional[str] = None
    max_holders: Optional[int] = None


class FactionRoleUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_holders: Optional[int] = None


class FactionRoleReorderBody(BaseModel):
    role_ids: list[str] = []


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
        "event_fields": EVENT_FIELDS,
    }


# ── Entity list / detail ─────────────────────────────────────────────────────

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
    else:
        result["extension"] = {}
        result["relations"] = []
        result["knowledge"] = []
    return result


# ── Composite create / update / soft delete ──────────────────────────────────

def _create_entity_core(body: EntityWriteBody, db: DbSession) -> Entity:
    """Commit-free core of `create_entity`.

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
    entity_type = data.get("type")
    if entity_type not in ENTITY_TYPE_REGISTRY:
        raise HTTPException(422, f"type must be one of {list(ENTITY_TYPE_REGISTRY)}")

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
    ext_row = db.get(ENTITY_TYPE_REGISTRY[entity.type]["model"], entity.id)
    db.refresh(ext_row)

    result = _entity_dict(entity)
    result["extension"] = _extension_dict(entity.type, ext_row)
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


# ── NPC goals — in-scene volition (schema v1.69, BRIEF-0013-a) ───────────────
# Creator CRUD only this step (writes.write_npc_goal / write_npc_goal_status).
# No edit/reopen endpoints — description immutability and the closed-is-closed
# rule are design, not omissions (see CLAUDE.md invariants).

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


# ── Agendas (TICKET-0018, BRIEF-0018-a) ───────────────────────────────────────
# First dedicated non-entity CRUD surface (RECON-0018 F7). All writes route
# through writes.write_agenda / write_agenda_step / write_agenda_step_status /
# write_agenda_status — the ONLY constructors of Agenda/AgendaStep, shared
# with `_apply_mutation`'s agenda_step_change/agenda_creation branches so the
# two canon-write paths cannot diverge.

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


# ── Goal <-> agenda links (schema v1.73, TICKET-0020, BRIEF-0020-c) ──────────
# Thin wrappers over the 0020-a helpers only — no business rule lives here;
# a ValueError from either helper (inactive goal/agenda, duplicate active
# pair, already detached) surfaces as a 422, never a 500. No delete route
# exists: detach is the only exit (history is sacred).

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


# ── Events (TICKET-0022, BRIEF-0022-a) ────────────────────────────────────────
# Second concrete non-entity reader of the sheetRenderer seam after `agenda`
# (TICKET-0021). Two writers, both in `writes.py`: `write_event` (creation —
# shared with `_apply_mutation`'s `event_creation` branch) and
# `write_event_update` (creator edit only, this module). No DELETE route: an
# event either happened or did not (C3) — see the "Deletion policy" docstring
# block above. The creator-authored duplicate-title guard used by
# `_apply_mutation` (app.py:886-906) is deliberately NOT applied here: the
# creator may author two same-titled events at one location on purpose.

def _event_dict(event: Event, db: DbSession) -> dict:
    location = db.get(Entity, event.location_id) if event.location_id else None
    involved = []
    for entity_id in (event.involved_entities or []):
        target = db.get(Entity, entity_id)
        involved.append({"id": entity_id, "name": target.name if target is not None else None})
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "type": event.type,
        "type_label": EVENT_TYPE_LABELS_FR.get(event.type, event.type),
        "knowledge_status": event.knowledge_status,
        "location_id": event.location_id,
        "location_name": location.name if location is not None else None,
        "involved_entities": involved,
        "recorded_at": _iso(event.recorded_at),
    }


def _validate_event_location(db: DbSession, world_id: str, location_id: Optional[str]) -> Optional[str]:
    """Reuses the exact predicate at app.py:1575-1583 (event_creation branch)
    — active `location` entity in the active world. 422 on anything else:
    the creator's picker cannot produce a bad id, so a bad id is a bug, not
    a typo."""
    if not location_id:
        return None
    target = db.get(Entity, location_id)
    if (
        target is None
        or target.type != "location"
        or target.status != "active"
        or target.world_id != world_id
    ):
        raise HTTPException(422, f"location_id {location_id!r} is not an active location in this world")
    return location_id


def _validate_event_involved(db: DbSession, world_id: str, ids: Optional[list]) -> Optional[list]:
    if not ids:
        return None
    out = []
    for entity_id in ids:
        target = db.get(Entity, entity_id)
        if target is None or target.world_id != world_id:
            raise HTTPException(422, f"involved_entities: {entity_id!r} is not a valid entity id in this world")
        out.append(entity_id)
    return out


class EventCreateBody(BaseModel):
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    knowledge_status: str = "secret"
    location_id: Optional[str] = None
    involved_entities: Optional[list[str]] = None


class EventUpdateBody(BaseModel):
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    knowledge_status: str
    location_id: Optional[str] = None
    involved_entities: Optional[list[str]] = None


@router.get("/events")
def list_events(db: DbSession = Depends(get_session)) -> list[dict]:
    world_id = _world_id(db)
    events = db.exec(
        select(Event).where(Event.world_id == world_id).order_by(Event.recorded_at.desc())
    ).all()
    return [_event_dict(e, db) for e in events]


@router.get("/events/{event_id}")
def get_event(event_id: str, db: DbSession = Depends(get_session)) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.world_id != _world_id(db):
        raise HTTPException(404, f"Event {event_id!r} not found")
    return _event_dict(event, db)


@router.post("/events", status_code=201)
def create_event(body: EventCreateBody, db: DbSession = Depends(get_session)) -> dict:
    world_id = _world_id(db)
    if not body.title or not body.title.strip():
        raise HTTPException(422, "title is required")
    if body.knowledge_status not in EVENT_KNOWLEDGE_STATUSES:
        raise HTTPException(422, f"knowledge_status must be one of {EVENT_KNOWLEDGE_STATUSES}")
    location_id = _validate_event_location(db, world_id, body.location_id)
    involved = _validate_event_involved(db, world_id, body.involved_entities)

    event = write_event(
        db,
        world_id=world_id,
        title=body.title.strip(),
        description=body.description,
        type=body.type,
        knowledge_status=body.knowledge_status,
        involved_entities=involved,
        location_id=location_id,
    )
    db.commit()
    db.refresh(event)
    return _event_dict(event, db)


@router.put("/events/{event_id}")
def update_event(event_id: str, body: EventUpdateBody, db: DbSession = Depends(get_session)) -> dict:
    event = db.get(Event, event_id)
    if event is None or event.world_id != _world_id(db):
        raise HTTPException(404, f"Event {event_id!r} not found")
    world_id = _world_id(db)
    if not body.title or not body.title.strip():
        raise HTTPException(422, "title is required")
    if body.knowledge_status not in EVENT_KNOWLEDGE_STATUSES:
        raise HTTPException(422, f"knowledge_status must be one of {EVENT_KNOWLEDGE_STATUSES}")
    location_id = _validate_event_location(db, world_id, body.location_id)
    involved = _validate_event_involved(db, world_id, body.involved_entities)

    event = write_event_update(
        db,
        event=event,
        title=body.title.strip(),
        description=body.description,
        type=body.type,
        knowledge_status=body.knowledge_status,
        involved_entities=involved,
        location_id=location_id,
    )
    db.commit()
    db.refresh(event)
    return _event_dict(event, db)


# ── Faction membership (schema v1.39, BRIEF-27) ───────────────────────────────
# Creator-CRUD only, INSERT-only / close-only (see writes.write_membership).
# No PUT route exists for an existing row, by construction — a role/primary
# change is close + reopen (close_membership_route + create_membership), so
# the closed-row sequence IS the history (no `change_history` column here).

class MembershipOpenBody(BaseModel):
    faction_id: str
    role: Optional[str] = None
    cover_role: Optional[str] = None
    is_primary: bool = False
    is_secret: bool = False


def _membership_dict(m: FactionMembership, db: DbSession) -> dict:
    member = db.get(Entity, m.entity_id)
    faction = db.get(Entity, m.faction_id)
    return {
        "id": m.id,
        "entity_id": m.entity_id,
        "entity_name": member.name if member else m.entity_id,
        "faction_id": m.faction_id,
        "faction_name": faction.name if faction else m.faction_id,
        "role": m.role,
        "cover_role": m.cover_role,
        "is_primary": m.is_primary,
        "is_secret": m.is_secret,
        "joined_at": _iso(m.joined_at),
        "left_at": _iso(m.left_at),
    }


@router.get("/entities/{faction_id}/roles")
def list_faction_roles(faction_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    """Curated, ordered role vocabulary for a faction — membership role
    select contract (names-only, order = rank). Reads the `faction_role`
    table (TICKET-0024, BRIEF-0024-d — corrective, replaces
    `entity.metadata['roles']`). Public org vocabulary — no secret
    filtering applies.
    """
    faction = _get_entity(db, faction_id)
    if faction.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    roles = db.exec(
        select(FactionRole)
        .where(FactionRole.faction_id == faction_id)
        .order_by(FactionRole.position)
    ).all()
    return [{"name": r.name, "description": r.description} for r in roles]


def _active_role_counts(db: DbSession, faction_id: str) -> dict[str, int]:
    """Casefold -> count of ACTIVE memberships bearing that true `role`."""
    holder_roles = db.exec(
        select(FactionMembership.role)
        .where(FactionMembership.faction_id == faction_id, FactionMembership.left_at.is_(None))
    ).all()
    counts: dict[str, int] = {}
    for role_name in holder_roles:
        if role_name:
            folded = role_name.casefold()
            counts[folded] = counts.get(folded, 0) + 1
    return counts


def _faction_role_dict(role: FactionRole, active_holder_count: int) -> dict:
    return {
        "id": role.id,
        "faction_id": role.faction_id,
        "name": role.name,
        "description": role.description,
        "max_holders": role.max_holders,
        "position": role.position,
        "active_holder_count": active_holder_count,
    }


@router.get("/factions/{faction_id}/roles")
def list_faction_role_rows(faction_id: str, db: DbSession = Depends(get_session)) -> dict:
    """Faction sheet's ROLES editor: full `faction_role` rows ordered by
    `position`, plus the DISTINCT true `role` values on ACTIVE memberships
    that match NO declared row (casefold) — the undeclared-borne-roles
    adoption hint source (TICKET-0024, BRIEF-0024-d)."""
    entity = _get_entity(db, faction_id)
    if entity.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    roles = db.exec(
        select(FactionRole)
        .where(FactionRole.faction_id == faction_id)
        .order_by(FactionRole.position)
    ).all()
    counts = _active_role_counts(db, faction_id)
    declared_casefold = {r.name.casefold() for r in roles}
    active_role_names = db.exec(
        select(FactionMembership.role)
        .where(FactionMembership.faction_id == faction_id, FactionMembership.left_at.is_(None))
        .distinct()
    ).all()
    undeclared = sorted({
        name for name in active_role_names
        if name and name.casefold() not in declared_casefold
    })
    return {
        "roles": [_faction_role_dict(r, counts.get(r.name.casefold(), 0)) for r in roles],
        "undeclared_active_roles": undeclared,
    }


@router.post("/factions/{faction_id}/roles", status_code=201)
def create_faction_role(
    faction_id: str, body: FactionRoleCreateBody, db: DbSession = Depends(get_session)
) -> dict:
    entity = _get_entity(db, faction_id)
    if entity.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    try:
        role = write_faction_role(
            db, mode="create", world_id=entity.world_id, faction_id=faction_id,
            name=body.name, description=body.description, max_holders=body.max_holders,
            changed_by="creator",
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    db.refresh(role)
    return _faction_role_dict(role, _active_role_counts(db, faction_id).get(role.name.casefold(), 0))


@router.patch("/factions/{faction_id}/roles/reorder")
def reorder_faction_roles(
    faction_id: str, body: FactionRoleReorderBody, db: DbSession = Depends(get_session)
) -> dict:
    """Full ordered id list — `position` is rewritten 0..n-1 to match."""
    entity = _get_entity(db, faction_id)
    if entity.type != "faction":
        raise HTTPException(422, f"{faction_id!r} is not a faction entity")
    roles = {
        r.id: r for r in db.exec(
            select(FactionRole).where(FactionRole.faction_id == faction_id)
        ).all()
    }
    if set(body.role_ids) != set(roles.keys()):
        raise HTTPException(422, "reorder: role_ids must be exactly this faction's role ids, no more, no less")
    for position, role_id in enumerate(body.role_ids):
        write_faction_role(
            db, mode="update", role_id=role_id,
            description=roles[role_id].description, max_holders=roles[role_id].max_holders,
            position=position,
        )
    db.commit()
    return list_faction_role_rows(faction_id, db)


@router.patch("/factions/{faction_id}/roles/{role_id}")
def update_faction_role(
    faction_id: str, role_id: str, body: FactionRoleUpdateBody, db: DbSession = Depends(get_session)
) -> dict:
    """Field edit and/or rename in one call — a `name` differing from the
    stored value triggers `mode="rename"` (T1: realigns active memberships
    holding the old name) before `description`/`max_holders` are applied."""
    role = db.get(FactionRole, role_id)
    if role is None or role.faction_id != faction_id:
        raise HTTPException(404, f"faction_role {role_id!r} not found")
    try:
        if body.name is not None and body.name.strip() and body.name.strip() != role.name:
            role = write_faction_role(db, mode="rename", role_id=role_id, name=body.name)
        role = write_faction_role(
            db, mode="update", role_id=role_id,
            description=body.description, max_holders=body.max_holders,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    db.refresh(role)
    return _faction_role_dict(role, _active_role_counts(db, faction_id).get(role.name.casefold(), 0))


@router.delete("/factions/{faction_id}/roles/{role_id}")
def delete_faction_role(faction_id: str, role_id: str, db: DbSession = Depends(get_session)) -> dict:
    role = db.get(FactionRole, role_id)
    if role is None or role.faction_id != faction_id:
        raise HTTPException(404, f"faction_role {role_id!r} not found")
    try:
        write_faction_role(db, mode="delete", role_id=role_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc))
    return {"deleted": True}


@router.get("/entities/{entity_id}/memberships")
def list_entity_memberships(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    """Active memberships for a member (character sheet "Appartenances" list)."""
    _get_entity(db, entity_id)
    rows = db.exec(
        select(FactionMembership)
        .where(FactionMembership.entity_id == entity_id, FactionMembership.left_at.is_(None))
    ).all()
    return [_membership_dict(m, db) for m in rows]


def _open_membership_core(
    entity_id: str, body: MembershipOpenBody, db: DbSession
) -> FactionMembership:
    """Commit-free core of `open_entity_membership` (BRIEF-35).

    Flushes (not commits) so the partial-unique-index `IntegrityError`
    surfaces deterministically at the core call site, catchable by either
    caller (this route's wrapper or a future batch caller).
    """
    entity = _get_entity(db, entity_id)
    faction = db.get(Entity, body.faction_id)
    if faction is None or faction.type != "faction":
        raise HTTPException(422, f"{body.faction_id!r} is not a valid faction entity id")

    membership = write_membership(
        db,
        mode="open",
        world_id=entity.world_id,
        entity_id=entity_id,
        faction_id=body.faction_id,
        role=body.role,
        cover_role=body.cover_role,
        is_primary=body.is_primary,
        is_secret=body.is_secret,
    )
    db.flush()
    return membership


@router.post("/entities/{entity_id}/memberships", status_code=201)
def open_entity_membership(
    entity_id: str, body: MembershipOpenBody, db: DbSession = Depends(get_session)
) -> dict:
    try:
        membership = _open_membership_core(entity_id, body, db)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Membership conflicts with an existing active row — at most one "
            "active primary per member, and no duplicate active membership "
            "in the same faction. Close the existing membership first.",
        )
    db.refresh(membership)
    return _membership_dict(membership, db)


@router.post("/memberships/{membership_id}/close")
def close_entity_membership(membership_id: str, db: DbSession = Depends(get_session)) -> dict:
    try:
        membership = write_membership(db, mode="close", membership_id=membership_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    db.commit()
    db.refresh(membership)
    return _membership_dict(membership, db)


@router.get("/entities/{entity_id}/faction-roster")
def get_faction_roster(entity_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
    """Active members of a faction (faction sheet read-only roster).

    Secret members ARE included, with their `is_secret` badge — the creator
    sees everything; the structural exclusion belongs to the future
    player-facing reader, which does not exist yet (Scope OUT, BRIEF-27).
    """
    _get_entity(db, entity_id)
    rows = db.exec(
        select(FactionMembership)
        .where(FactionMembership.faction_id == entity_id, FactionMembership.left_at.is_(None))
    ).all()
    return [_membership_dict(m, db) for m in rows]


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

def _skill_dict(s: Skill, definition_name: str | None = None) -> dict:
    return {
        "id": s.id,
        "character_id": s.character_id,
        "domain": s.domain,
        "skill_definition_id": s.skill_definition_id,
        "definition_name": definition_name,
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
        .where(Character.world_id == _world_id(db))
        .order_by(Entity.name)
    ).all()
    return [{"id": e.id, "name": e.name} for e, _ in rows]


@router.get("/skills")
def list_skills(character_id: str = Query(...), db: DbSession = Depends(get_session)) -> list[dict]:
    """A player character's skill sheet, in fixed domain order."""
    _get_entity(db, character_id)
    pairs = db.exec(
        select(Skill, SkillDefinition)
        .outerjoin(SkillDefinition, Skill.skill_definition_id == SkillDefinition.id)
        .where(Skill.character_id == character_id)
    ).all()
    order = {domain: i for i, domain in enumerate(SKILL_DOMAINS)}
    pairs.sort(key=lambda p: order.get(p[0].domain, len(SKILL_DOMAINS)))
    return [_skill_dict(s, d.name if d else None) for s, d in pairs]


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
        write_skill_tier(db, skill_id=skill_id, tier=body.tier, changed_by="creator")
        db.commit()
        db.refresh(skill)

    return _skill_dict(skill)


# ── Skill catalogue — world-scoped custom skill definitions (BRIEF-56) ───────
# Creator-direct writes, same doctrine as the rest of this module: no
# proposed_mutation checkpoint. `skill_definition` has no `entity_id` — this
# is a dedicated-router CRUD surface (the `skill`/`discoverable_detail`/
# `ledger` shape), NOT the generic composite entity editor.

def _skill_definition_dict(d: SkillDefinition) -> dict:
    return {
        "id": d.id,
        "world_id": d.world_id,
        "name": d.name,
        "base_domain": d.base_domain,
        "description": d.description,
        "updated_at": _iso(d.updated_at),
    }


@router.get("/skill-definitions")
def list_skill_definitions(db: DbSession = Depends(get_session)) -> list[dict]:
    """The active world's custom skill catalogue."""
    rows = db.exec(
        select(SkillDefinition)
        .where(SkillDefinition.world_id == _world_id(db))
        .order_by(SkillDefinition.name)
    ).all()
    return [_skill_definition_dict(d) for d in rows]


class SkillDefinitionWriteBody(BaseModel):
    name: str
    base_domain: str
    description: Optional[str] = None


@router.post("/skill-definitions", status_code=201)
def create_skill_definition(
    body: SkillDefinitionWriteBody, db: DbSession = Depends(get_session)
) -> dict:
    """Add a custom skill to the active world's catalogue (D2-backfill-yes).

    Backfills: inserts a tier-0 `skill` row for this definition onto every
    existing player character of the world, in the SAME transaction, so the
    catalogue<->PC alignment that makes the arbiter lookup total never
    lapses (BRIEF-55's invariant — every PC always has every world skill).
    """
    world_id = _world_id(db)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "name is required")
    if name.lower() in BASE_SKILL_DOMAINS:
        raise HTTPException(422, "name must not be a base domain literal")
    if body.base_domain not in BASE_SKILL_DOMAINS:
        raise HTTPException(422, f"base_domain must be one of {BASE_SKILL_DOMAINS}")

    definition = SkillDefinition(
        world_id=world_id,
        name=name,
        base_domain=body.base_domain,
        description=body.description,
    )
    db.add(definition)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A skill named {name!r} already exists in this world")

    pc_ids = db.exec(
        select(Character.id)
        .where(Character.world_id == world_id)
        .where(Character.character_type == "player")
    ).all()
    for character_id in pc_ids:
        db.add(Skill(
            character_id=character_id,
            domain=definition.base_domain,
            tier=0,
            skill_definition_id=definition.id,
        ))

    db.commit()
    db.refresh(definition)
    return _skill_definition_dict(definition)


@router.put("/skill-definitions/{definition_id}")
def update_skill_definition(
    definition_id: str,
    body: SkillDefinitionWriteBody,
    db: DbSession = Depends(get_session),
) -> dict:
    """Rename / re-base / re-word a custom skill.

    Rename is safe by construction (every reader joins by id, never copies
    the name onto a `skill` row). Changing `base_domain` re-points
    resolution for every existing PC `skill` row referencing this
    definition — also updates their `domain` column so the 2d6 bands and
    the base-domain CHECK stay consistent (mirrors the create-time seed).
    """
    definition = db.get(SkillDefinition, definition_id)
    if definition is None or definition.world_id != _world_id(db):
        raise HTTPException(404, f"SkillDefinition {definition_id!r} not found")
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "name is required")
    if name.lower() in BASE_SKILL_DOMAINS:
        raise HTTPException(422, "name must not be a base domain literal")
    if body.base_domain not in BASE_SKILL_DOMAINS:
        raise HTTPException(422, f"base_domain must be one of {BASE_SKILL_DOMAINS}")

    domain_changed = body.base_domain != definition.base_domain
    definition.name = name
    definition.base_domain = body.base_domain
    definition.description = body.description
    definition.updated_at = datetime.now(UTC)
    db.add(definition)

    if domain_changed:
        dependent = db.exec(
            select(Skill).where(Skill.skill_definition_id == definition.id)
        ).all()
        for skill in dependent:
            skill.domain = body.base_domain
            skill.updated_at = datetime.now(UTC)
            db.add(skill)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"A skill named {name!r} already exists in this world")
    db.refresh(definition)
    return _skill_definition_dict(definition)


@router.delete("/skill-definitions/{definition_id}")
def delete_skill_definition(
    definition_id: str, db: DbSession = Depends(get_session)
) -> dict:
    """Delete a custom skill definition (D2-delete-cascade).

    Always possible — never blocked by the structural `ON DELETE RESTRICT`
    floor. Deletes every dependent PC `skill` row first, then the
    definition, in one transaction. Per the locked decision, this cascade
    carries no separate history snapshot — the creator-side confirmation
    (type "Oui") is the safeguard, the same idiom as world block deletion.
    """
    definition = db.get(SkillDefinition, definition_id)
    if definition is None or definition.world_id != _world_id(db):
        raise HTTPException(404, f"SkillDefinition {definition_id!r} not found")

    dependent = db.exec(
        select(Skill).where(Skill.skill_definition_id == definition.id)
    ).all()
    for skill in dependent:
        db.delete(skill)
    db.delete(definition)
    db.commit()
    return {"deleted": definition_id, "skills_removed": len(dependent)}


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


# ── NPC relation ego-graph (BRIEF-0023-b, no schema change) ─────────────────

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


# ── Location hierarchy browse (BRIEF-51, no schema change) ──────────────────

@router.get("/locations")
def list_locations(db: DbSession = Depends(get_session)) -> list[dict]:
    """All locations (every status) with hierarchy fields — read-only, creator browse."""
    world_id = _world_id(db)
    rows = db.exec(
        select(Entity, Location)
        .join(Location, Location.id == Entity.id)
        .where(Entity.type == "location")
        .where(Entity.world_id == world_id)
        .order_by(Entity.name)
    ).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "parent_location_id": loc.parent_location_id,
            "location_type": loc.location_type,
            "status": e.status,
        }
        for e, loc in rows
    ]


# ── Ledger (schema v1.31, BRIEF-18) ──────────────────────────────────────────
# Append-only conserved currency. Creator-direct writes — same doctrine as
# the rest of this module: no proposed_mutation checkpoint. UNLIKE the
# relation/knowledge editors above, this surface is INSERT-ONLY: no PUT, no
# DELETE, ever. A mistake is corrected with a new compensating line
# (source_type='correction'), never by editing or deleting an existing row.
# God-mode: no non-negative balance guard here (that rule lives in
# _apply_mutation's resource_change branch, BRIEF-19, on the AI path only).

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


# ── Prompts (Création → Prompts, read-only) — BRIEF-0008-a/-b ──────────────────

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
        "variables": row.variables,
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


__all__ = ["router", "ENTITY_TYPE_REGISTRY"]
