"""Canon SQLModel table classes — every table listed in
``canon_write_policy.txt``'s ``[CANON_TABLES]`` (TICKET-0028, BRIEF-0028-c —
package split of the former flat ``models.py``, by schema stratum).

These mirror `world-engine-schema.md` exactly: same tables, columns,
types, defaults, foreign keys, indexes, and the one CHECK constraint.

Conventions used throughout:
- Primary keys are TEXT (UUID strings), matching the Supabase migration note.
- JSON columns use SQLAlchemy's ``JSON`` type (becomes ``JSONB`` on PostgreSQL).
- DB-level ``DEFAULT`` clauses are preserved via ``server_default`` so the
  generated DDL matches the schema, while Python-side defaults keep the ORM
  ergonomic.
- ``DEFAULT CURRENT_TIMESTAMP`` columns carry ``server_default=func.now()``.

``GoalPrerequisite`` (table ``goal_prerequisite``) and ``EventEntity``
(table ``event_entity``) are placed here despite being absent from
``canon_write_policy.txt``'s ``[CANON_TABLES]`` list — both are written by a
sanctioned site alongside canon tables in their `writes/` domain module with
no "(non-canon)" annotation (unlike `prompt_version`/`prompt_variable`,
which carry one). Nia confirmed (TICKET-0028/BRIEF-0028-c stratum
escalation, 2026-07-15): the `[CANON_TABLES]` omission is a known governance
gap, not a signal about the tables' nature. `[CANON_TABLES]` itself is
untouched by this brief (Scope OUT) — see the candidate follow-up ticket
logged in the BRIEF-0028-c execution notes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid4())


# Reusable column factories ---------------------------------------------------

def _created_ts() -> Any:
    """A NOT NULL timestamp column defaulting to CURRENT_TIMESTAMP."""
    return Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime, nullable=False, server_default=func.now()),
    )


# -----------------------------------------------------------------------------
# world
# -----------------------------------------------------------------------------
class World(SQLModel, table=True):
    __tablename__ = "world"
    __table_args__ = (
        # At most one ACTIVE world across the whole database.
        Index(
            "idx_world_one_active", "is_active",
            unique=True, sqlite_where=text("is_active = 1"),
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    description: Optional[str] = None
    magic_status: str = Field(
        default="dormant",
        sa_column_kwargs={"server_default": text("'dormant'")},
    )
    is_active: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# world_law  (position-ordered fundamental laws, schema v1.78,
# TICKET-0025, BRIEF-0025-b — replaces world.fundamental_laws JSON)
#
# One row per law, in creation-form order. Curated config (faction_role
# family): no change_history, written via writes.write_world_laws only.
# Python attribute `text_` maps to DB column `text` (`text` is reserved by
# the sqlalchemy.text import used throughout this module — same pattern as
# entity.metadata_/`metadata`).
# -----------------------------------------------------------------------------
class WorldLaw(SQLModel, table=True):
    __tablename__ = "world_law"
    __table_args__ = (
        Index("idx_world_law_position", "world_id", "position", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    text_: str = Field(sa_column=Column("text", String, nullable=False))


# -----------------------------------------------------------------------------
# entity  (central table — everything is an entity)
# -----------------------------------------------------------------------------
class Entity(SQLModel, table=True):
    __tablename__ = "entity"
    __table_args__ = (
        Index("idx_entity_world", "world_id"),
        Index("idx_entity_type", "type"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    type: str
    name: str
    internal_name: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("1")}
    )
    status: str = Field(
        default="active", sa_column_kwargs={"server_default": text("'active'")}
    )
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# character  (extension of entity)
# -----------------------------------------------------------------------------
class Character(SQLModel, table=True):
    __tablename__ = "character"
    __table_args__ = (
        Index("idx_character_location", "current_location_id"),
        Index("idx_character_user", "user_id"),
        Index("idx_character_world", "world_id"),
        # One player character per user per world (v1 invariant, BRIEF-46).
        # Multiplayer-safe: scoped to (world_id, user_id), not world-wide —
        # many users may each hold one PC per world.
        Index(
            "idx_character_one_pc_per_user_world", "world_id", "user_id",
            unique=True, sqlite_where=text("character_type = 'player'"),
        ),
    )

    id: str = Field(primary_key=True, foreign_key="entity.id")
    # Denormalized from entity.world_id (same pattern as relation.world_id) —
    # needed because the one-PC-per-user-per-world index lives on this table,
    # and SQLite indexes can't reach across a join to entity.
    world_id: str = Field(foreign_key="world.id", nullable=False)
    character_type: str  # player | npc
    user_id: Optional[str] = None  # NULL for NPCs (no FK in schema)
    current_location_id: Optional[str] = Field(
        default=None, foreign_key="entity.id"
    )
    vital_status: str = Field(
        default="alive", sa_column_kwargs={"server_default": text("'alive'")}
    )
    appearance: Optional[str] = None
    backstory: Optional[str] = None
    aversion: Optional[str] = None
    # Plain text since TICKET-0025 (B1): no reader ever consumed structure.
    secrets: Optional[str] = None
    # Schema v1.77, TICKET-0025, BRIEF-0025-a: physical resistance tier for
    # opposed rolls (resolution.py). Migrated from entity.metadata
    # ['physical_tier'] — UI-visible data is never stored in JSON
    # (json_ui_boundary). 0 = untrained default.
    physical_tier: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})


# -----------------------------------------------------------------------------
# npc_price  (seller tariff lines, schema v1.77, TICKET-0025,
# BRIEF-0025-a — replaces entity.metadata['price_list'], BRIEF-20)
#
# Curated config, same family as faction_role: no change_history column,
# full-replace writes, hard delete of a line is the sanctioned edit
# (named doctrine exception — logged in ARCHITECTURE_DECISIONS). Read by
# the seller-tariff block of assemble_npc_context; written ONLY via
# writes.write_npc_prices (creator Tarifs editor).
# -----------------------------------------------------------------------------
class NpcPrice(SQLModel, table=True):
    __tablename__ = "npc_price"
    __table_args__ = (
        Index(
            "idx_npc_price_tag", "entity_id", text("tag COLLATE NOCASE"),
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)
    tag: str
    amount: int


# -----------------------------------------------------------------------------
# location  (extension of entity, hierarchical)
# -----------------------------------------------------------------------------
class Location(SQLModel, table=True):
    __tablename__ = "location"
    __table_args__ = (Index("idx_location_parent", "parent_location_id"),)

    id: str = Field(primary_key=True, foreign_key="entity.id")
    parent_location_id: Optional[str] = Field(
        default=None, foreign_key="entity.id"
    )
    location_type: Optional[str] = None
    magic_status: str = Field(
        default="inert", sa_column_kwargs={"server_default": text("'inert'")}
    )
    # Map position (schema v1.78, TICKET-0025) — was coordinates JSON {x,y}.
    # NULL = unplaced.
    coord_x: Optional[float] = None
    coord_y: Optional[float] = None
    # Playable-area bounds for the intra-location obstacle space (schema
    # v1.80, TICKET-0029). NULL = this location has no spatial mode.
    # Same local space as obstacle_vertex, NOT the world-map coords above.
    bounds_width: Optional[float] = None
    bounds_height: Optional[float] = None
    access_level: Optional[str] = None


# -----------------------------------------------------------------------------
# location_type_catalog  (classified type registry, schema v1.84, TICKET-0039,
# BRIEF-0039-a)
#
# One row per location_type string, per world. classification is the ONLY
# interior/exterior signal in the engine (A1/B1): doors derive their kind from
# the two endpoints' classification (D1), and street-access (E1) reads it.
# NULL classification = not yet decided; a NULL-classified type is inert for
# door derivation and E1 until the creator classifies it (BRIEF-0039-b prompts
# on next use). This is a per-row upsert catalog, NOT a full-replace config
# table: types are added one at a time from the picker. exterior-public ==
# exterior for v1; the public/private split on exterior is a named deferral.
# -----------------------------------------------------------------------------
class LocationTypeCatalog(SQLModel, table=True):
    __tablename__ = "location_type_catalog"
    __table_args__ = (
        Index(
            "idx_location_type_catalog_name", "world_id", text("name COLLATE NOCASE"),
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    name: str
    classification: Optional[str] = None
    created_at: datetime = _created_ts()

    # Size template (schema v1.85, TICKET-0040, BRIEF-0040-a). The ONLY
    # source of a location's birth bounds: code reads these, a model never
    # produces a number (A1). Applied ONCE, at creation
    # (crud/entities.py::_create_entity_core, E1) - never a live link: a
    # template change is NEVER retroactive (F1). Both NULL or both set,
    # enforced by writes.upsert_location_type; a type with no template ->
    # bounds NULL -> no spatial mode. Same LOCAL coordinate space as
    # obstacle_vertex (1.0 = one world-meter), NEVER coord_x/coord_y.
    default_width: Optional[float] = None
    default_height: Optional[float] = None


# -----------------------------------------------------------------------------
# location_subculture  (ambient culture lines, schema v1.78,
# TICKET-0025, BRIEF-0025-b — replaces location.subculture JSON)
#
# One row per key. is_hidden = 1 rows are creator-only: every
# non-creator read path filters is_hidden = 0 AT QUERY CONSTRUCTION —
# exclusion is structural, never instructional. Curated config
# (faction_role family): no change_history, full-replace writes via
# writes.write_location_subculture only.
# -----------------------------------------------------------------------------
class LocationSubculture(SQLModel, table=True):
    __tablename__ = "location_subculture"
    __table_args__ = (
        Index(
            "idx_location_subculture_key", "location_id", text("key COLLATE NOCASE"),
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    key: str
    value: str
    is_hidden: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})


# -----------------------------------------------------------------------------
# obstacle / obstacle_vertex  (intra-location wall geometry, schema v1.80,
# TICKET-0029, BRIEF-0029-a)
#
# Curated config (faction_role family): no change_history, full-replace
# writes via writes.write_location_obstacles only. One obstacle = one
# closed polygon, stored as ordered vertex rows (agenda_step.step_order
# precedent) — NEVER a JSON list. v1 obstacles are 4-vertex rectangles;
# real polygons later add vertex rows only, never a schema rewrite.
#
# COORDINATE SPACE: per-location local coordinates. Origin at the
# top-left of the playable area, x rightward, y DOWNWARD (canvas-native).
# Nominal unit: 1.0 = one world-meter. This space is DISTINCT from
# location.coord_x / coord_y (v1.78), which place the location on the
# WORLD map — never mix the two. Rectangle→vertex expansion emits the 4
# corners CLOCKWISE from the top-left corner (declared convention, not
# structurally enforced).
# -----------------------------------------------------------------------------
class Obstacle(SQLModel, table=True):
    __tablename__ = "obstacle"
    __table_args__ = (Index("idx_obstacle_location", "location_id"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    created_at: datetime = _created_ts()


class ObstacleVertex(SQLModel, table=True):
    __tablename__ = "obstacle_vertex"
    __table_args__ = (
        Index(
            "idx_obstacle_vertex_order", "obstacle_id", "vertex_order",
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    obstacle_id: str = Field(foreign_key="obstacle.id", nullable=False)
    vertex_order: int
    x: float
    y: float


# -----------------------------------------------------------------------------
# door  (inter-location passage, spatial side, schema v1.81, TICKET-0034,
# BRIEF-0034-a)
#
# ONE ROW PER SIDE (A1). A passage between A and B is two rows: (A -> B)
# and (B -> A), each carrying the point in ITS OWN location's local
# space. Pairing is DERIVED at arrival — "the door of B that points back
# at A" — and made unambiguous BY idx_door_target, not by a defended
# invariant. The consequence is deliberate: at most one door per ordered
# pair of locations.
#
# TERMINAL BY CONTRACT: no table may take a foreign key on door.id. The
# A1 -> A2 escalation (one `passage` row carrying both endpoints, needed
# the day two passages must join the same pair of locations) is a
# mechanical self-join ONLY while nothing references a door by id. This
# is enforced by tooling/verify/checks/door_terminal.py, not by memory.
#
# A door is the SPATIAL MANIFESTATION of a connects_to edge, never its
# source (B1): write_location_doors rejects a target with no active
# connects_to edge, and the play-side reader (cockpit/spatial_doors.py)
# filters doors whose edge later disappeared. The map stays the world's
# traversability truth. Neither side cascades or deletes.
#
# Curated config (faction_role family): no change_history, full-replace
# writes via writes.write_location_doors only.
#
# COORDINATE SPACE: per-location local coordinates — the obstacle_vertex
# space (origin top-left, x rightward, y DOWNWARD, 1.0 = one
# world-meter), NOT location.coord_x / coord_y (world map). x, y is the
# door's point in `location_id`'s space; the counterpart row carries its
# own point in the counterpart's space. NOTHING here judges whether that
# point is inside a wall — see write_location_doors' NOTE.
# -----------------------------------------------------------------------------
class Door(SQLModel, table=True):
    __tablename__ = "door"
    __table_args__ = (
        Index(
            "idx_door_target", "location_id", "target_location_id",
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    target_location_id: str = Field(foreign_key="entity.id", nullable=False)
    x: float
    y: float
    created_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# relation  (universal relation graph)
# -----------------------------------------------------------------------------
class Relation(SQLModel, table=True):
    __tablename__ = "relation"
    __table_args__ = (
        CheckConstraint(
            "intensity BETWEEN 1 AND 100", name="ck_relation_intensity"
        ),
        Index("idx_relation_a", "entity_a_id"),
        Index("idx_relation_b", "entity_b_id"),
        Index("idx_relation_world", "world_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    entity_a_id: str = Field(foreign_key="entity.id", nullable=False)
    entity_b_id: str = Field(foreign_key="entity.id", nullable=False)
    type: str
    direction: str = Field(
        default="mutual", sa_column_kwargs={"server_default": text("'mutual'")}
    )
    intensity: int = Field(
        default=50, sa_column_kwargs={"server_default": text("50")}
    )
    visible_to_b: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("1")}
    )
    notes: Optional[str] = None
    created_at: datetime = _created_ts()
    last_evolved_at: datetime = _created_ts()
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


# -----------------------------------------------------------------------------
# knowledge  (what each entity knows)
# -----------------------------------------------------------------------------
class Knowledge(SQLModel, table=True):
    __tablename__ = "knowledge"
    __table_args__ = (
        CheckConstraint(
            "share_threshold BETWEEN 1 AND 100",
            name="ck_knowledge_share_threshold",
        ),
        Index("idx_knowledge_entity", "entity_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)
    subject: str
    level: str
    content: Optional[str] = None
    source: Optional[str] = None
    is_incorrect: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    is_secret: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    # Minimum NPC->interlocutor relation intensity (1-100) to share this row;
    # ignored when is_secret = TRUE (see world-engine-schema.md v1.3).
    share_threshold: int = Field(
        default=50, sa_column_kwargs={"server_default": text("50")}
    )
    acquired_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
    session_id: Optional[str] = None  # no FK in schema
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


# -----------------------------------------------------------------------------
# npc_goal  (NPC interiority — in-scene volition, schema v1.69, BRIEF-0013-a)
#
# Flat table (F1, no parent_goal_id — see ARCHITECTURE_DECISIONS "Deferred
# decisions" for the F2 reactivation trigger). description is immutable after
# insert: a "changed" goal is a closed goal plus a new row. status transitions
# are one-way (active -> completed|abandoned), never reopened. Read ONLY by
# assemble_npc_context and the initiative vote (N1) — assemble_mj_context must
# never gain a query against this table.
# -----------------------------------------------------------------------------
class NpcGoal(SQLModel, table=True):
    __tablename__ = "npc_goal"
    __table_args__ = (
        CheckConstraint("horizon IN ('short','long')", name="ck_npc_goal_horizon"),
        CheckConstraint(
            "status IN ('active','completed','abandoned')", name="ck_npc_goal_status"
        ),
        Index("idx_npc_goal_npc_status", "npc_id", "status"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    npc_id: str = Field(foreign_key="entity.id", nullable=False)
    description: str
    horizon: str
    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


# -----------------------------------------------------------------------------
# goal_prerequisite  (npc_goal completion gate, schema v1.79, TICKET-0025,
# BRIEF-0025-c — replaces npc_goal.prerequisites JSON)
#
# Closed vocabulary (K1) enforced by CHECK: v1 accepts ONLY `relation_gte`.
# Extension = a new enum value in a migration, never a free string.
# Creator-CRUD authored only (`writes.write_npc_goal_prerequisites`,
# BRIEF-0024-a's editor). Read by `_apply_mutation`'s `goal_change complete`
# judge and the per-NPC tick briefing (BRIEF-0024-b).
# -----------------------------------------------------------------------------
class GoalPrerequisite(SQLModel, table=True):
    __tablename__ = "goal_prerequisite"
    __table_args__ = (
        CheckConstraint("type IN ('relation_gte')", name="ck_goal_prerequisite_type"),
        CheckConstraint("threshold BETWEEN 1 AND 100", name="ck_goal_prerequisite_threshold"),
        Index(
            "idx_goal_prerequisite_unique", "goal_id", "type", "target_entity_id",
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    goal_id: str = Field(foreign_key="npc_goal.id", nullable=False)
    type: str
    target_entity_id: str = Field(foreign_key="entity.id", nullable=False)
    threshold: int


# -----------------------------------------------------------------------------
# ledger  (conserved currency, append-only — schema v1.31, BRIEF-18)
#
# NOTE: this table is INSERT-only. No code path may UPDATE or DELETE an
# existing row — a correction is a new compensating line
# (writes.write_ledger_entry is the single chokepoint that inserts).
# -----------------------------------------------------------------------------
class Ledger(SQLModel, table=True):
    __tablename__ = "ledger"
    __table_args__ = (
        Index("idx_ledger_entity", "entity_id"),
        Index("idx_ledger_session", "session_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)
    amount: int  # signed: + credit, - debit; world base unit
    counterparty_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    reason: Optional[str] = None
    source_type: Optional[str] = None
    # creator | correction | conversation | pass_play ('conversation' written by
    # _apply_mutation's resource_change branch, BRIEF-19; 'pass_play' still unused)
    conversation_id: Optional[str] = Field(default=None, foreign_key="conversation.id")
    pass_play_id: Optional[str] = Field(default=None, foreign_key="pass_play.id")
    session_id: Optional[str] = Field(default=None, foreign_key="session.id")
    created_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# event  (facts that occur in the world)
# -----------------------------------------------------------------------------
class Event(SQLModel, table=True):
    __tablename__ = "event"
    __table_args__ = (Index("idx_event_world", "world_id"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    session_id: Optional[str] = Field(default=None, foreign_key="session.id")
    batch_id: Optional[str] = Field(default=None, foreign_key="batch.id")
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    knowledge_status: str = Field(
        default="secret",
        sa_column_kwargs={"server_default": text("'secret'")},
    )
    location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    has_magic_impact: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    consequences: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    occurred_at: Optional[datetime] = None
    recorded_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# event_entity  (event <-> entity link, schema v1.79, TICKET-0025,
# BRIEF-0025-c — replaces the FK-less event.involved_entities JSON id array)
#
# Membership queries become joins/EXISTS instead of a Python `in` over a
# JSON list of ids. No change_history (link table, not a fact-bearing row).
# -----------------------------------------------------------------------------
class EventEntity(SQLModel, table=True):
    __tablename__ = "event_entity"
    __table_args__ = (
        Index("idx_event_entity_unique", "event_id", "entity_id", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    event_id: str = Field(foreign_key="event.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)


# -----------------------------------------------------------------------------
# artifact  (extension of entity)
# -----------------------------------------------------------------------------
class Artifact(SQLModel, table=True):
    __tablename__ = "artifact"

    id: str = Field(primary_key=True, foreign_key="entity.id")
    owner_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    origin: Optional[str] = None
    known_properties: Optional[Any] = Field(
        default=None, sa_column=Column(JSON)
    )
    actual_behavior: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    status: str = Field(
        default="unknown",
        sa_column_kwargs={"server_default": text("'unknown'")},
    )
    magic_link: Optional[str] = None


# -----------------------------------------------------------------------------
# item  (mundane tracked objects — static possession, schema v1.18)
# -----------------------------------------------------------------------------
class Item(SQLModel, table=True):
    __tablename__ = "item"
    __table_args__ = (
        CheckConstraint(
            "NOT equipped OR owner_id IS NOT NULL", name="ck_item_equipped_owner"
        ),
        Index("idx_item_owner", "owner_id"),
        Index("idx_item_location", "location_id"),
    )

    id: str = Field(primary_key=True, foreign_key="entity.id")
    owner_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    equipped: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    condition: str = Field(
        default="intact",
        sa_column_kwargs={"server_default": text("'intact'")},
    )


# The four structural skill domains — single source of truth (decision 3,
# BRIEF-55, schema v1.63). Previously declared independently in three places
# (cockpit/app.py `_PHYSICAL_DOMAINS`, cockpit/crud.py and seed_pilot.py
# `SKILL_DOMAINS`); all three now import this constant instead.
BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")


# -----------------------------------------------------------------------------
# skill_definition  (world-scoped custom skill catalogue, schema v1.63)
# -----------------------------------------------------------------------------
class SkillDefinition(SQLModel, table=True):
    __tablename__ = "skill_definition"
    __table_args__ = (
        CheckConstraint(
            "base_domain IN ('physical','agility','perception','composure')",
            name="ck_skill_definition_base_domain",
        ),  # canonical list: BASE_SKILL_DOMAINS above
        Index("idx_skill_definition_world_name", "world_id", "name", unique=True),
        Index("idx_skill_definition_world", "world_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    name: str
    base_domain: str  # specialises exactly one of BASE_SKILL_DOMAINS
    description: Optional[str] = None  # authored in chantier 2, not read this round
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# skill  (player character skill sheet — physical/sensory domains, schema v1.22;
# skill_definition_id added schema v1.63)
# -----------------------------------------------------------------------------
class Skill(SQLModel, table=True):
    __tablename__ = "skill"
    __table_args__ = (
        CheckConstraint("tier BETWEEN -1 AND 2", name="ck_skill_tier"),
        Index("idx_skill_character", "character_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    character_id: str = Field(foreign_key="entity.id", nullable=False)
    domain: str  # physical | agility | perception | composure
    tier: int = Field(
        default=0, sa_column_kwargs={"server_default": text("0")}
    )
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )
    # NULL for the four base-domain rows; set for custom-skill rows. A custom
    # skill's identity is this id, never a copied name — rename-safe by
    # construction (display name is always read by join to
    # skill_definition.name). ON DELETE RESTRICT is a structural floor only
    # (chantier 2 owns the real delete/cascade UX).
    skill_definition_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skill_definition.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# discoverable_detail  (pre-seeded hidden content per location, schema v1.26)
#
# NOTE: this table is NEVER read by any context assembler (assemble_mj_context,
# assemble_npc_context, or any prompt-building path). Undiscovered content is
# absent from every prompt by data exclusion, not by instruction. Content
# reaches a model only via the explicit post-selection injection in _stream()
# on a partial/success perception search.
# -----------------------------------------------------------------------------
class DiscoverableDetail(SQLModel, table=True):
    __tablename__ = "discoverable_detail"
    __table_args__ = (
        CheckConstraint(
            "discovery_threshold BETWEEN 0 AND 12",
            name="ck_discoverable_threshold",
        ),
        Index("idx_discoverable_location", "location_id"),
        Index("idx_discoverable_world", "world_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    subject: str  # short tag, e.g. "lettre_innommee"
    content: str  # what the player learns on discovery
    access_level: str = Field(
        default="hidden",
        sa_column_kwargs={"server_default": text("'hidden'")},
    )
    # ACTIVE (N1, BRIEF-23): minimum 2d6+modifier roll total required to
    # reveal, filtered at selection in _stream(). Same philosophy as
    # knowledge.share_threshold.
    discovery_threshold: int = Field(
        default=0, sa_column_kwargs={"server_default": text("0")}
    )
    # Flips TRUE when the discovery new_knowledge mutation is APPLIED
    # (creator-approved), not at propose time — ensures the creator can reject
    # the proposal and the detail remains available for re-selection.
    discovered: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    # Clusters an `ambient` panel row with the `hidden` content rows it
    # signposts (schema v1.30, BRIEF-17): both the panel and its grouped
    # contents carry the SAME signpost_group value. NULL = no cluster (a
    # standalone ambient note, or a hidden row with no signpost).
    signpost_group: str | None = Field(default=None, index=True)
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# agenda / agenda_step  (structured faction intrigues — schema v1.72,
# TICKET-0018/BRIEF-0018-a). NpcGoal shape precedent (change_history on both).
# A1 (this step): owner_entity_id is FK entity.id (A2-ready — location/NPC
# owners deferred) but write_agenda enforces a faction-type, active owner.
# F2: at most one ACTIVE step per agenda is a structural partial unique index,
# not discipline. The model references an agenda by TITLE and never a
# step/agenda id directly; the active step is always code-derived.
# -----------------------------------------------------------------------------
class Agenda(SQLModel, table=True):
    __tablename__ = "agenda"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','completed','failed','abandoned')",
            name="ck_agenda_status",
        ),
        Index("idx_agenda_owner_status", "owner_entity_id", "status"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    owner_entity_id: str = Field(foreign_key="entity.id", nullable=False)
    title: str
    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


class AgendaStep(SQLModel, table=True):
    __tablename__ = "agenda_step"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','completed','failed')",
            name="ck_agenda_step_status",
        ),
        Index("idx_agenda_step_agenda", "agenda_id", "step_order"),
        # At most one ACTIVE step per agenda (RECON-0018 F2 — the
        # idx_membership_one_primary precedent).
        Index(
            "idx_agenda_step_one_active", "agenda_id",
            unique=True, sqlite_where=text("status = 'active'"),
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    agenda_id: str = Field(foreign_key="agenda.id", nullable=False)
    step_order: int
    objective: str
    status: str = Field(default="pending", sa_column_kwargs={"server_default": text("'pending'")})
    outcome: Optional[str] = None
    visibility_trace: Optional[str] = None
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


# -----------------------------------------------------------------------------
# goal_agenda_link  (npc_goal <-> agenda many-to-many, schema v1.73,
# TICKET-0020/BRIEF-0020-a). Ties a goal to the intrigue(s) it serves — B3
# grain is the AGENDA, never the step. No `change_history`: link rows are
# immutable facts whose only transition is the soft detach (the two detach
# columns ARE the audit trail, `faction_membership.left_at` precedent);
# goal-side status transitions live in `npc_goal.change_history` as always.
# `idx_goal_agenda_link_active` (partial unique on `goal_id, agenda_id` WHERE
# `detached_at IS NULL`) forbids a duplicate ACTIVE link for the same pair
# while allowing re-attach after detach (`idx_membership_unique_active`
# precedent, models.py:222-226).
# -----------------------------------------------------------------------------
class GoalAgendaLink(SQLModel, table=True):
    __tablename__ = "goal_agenda_link"
    __table_args__ = (
        Index("idx_goal_agenda_link_goal", "goal_id"),
        Index("idx_goal_agenda_link_agenda", "agenda_id"),
        Index(
            "idx_goal_agenda_link_active", "goal_id", "agenda_id",
            unique=True, sqlite_where=text("detached_at IS NULL"),
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    goal_id: str = Field(foreign_key="npc_goal.id", nullable=False)
    agenda_id: str = Field(foreign_key="agenda.id", nullable=False)
    created_at: datetime = _created_ts()
    created_by: str
    detached_at: Optional[datetime] = None
    detached_by: Optional[str] = None
