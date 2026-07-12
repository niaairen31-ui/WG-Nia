"""SQLModel table classes for the World Engine.

These mirror `world-engine-schema.md` (v1.2) exactly: same tables, columns,
types, defaults, foreign keys, indexes, and the one CHECK constraint.

Conventions used throughout:
- Primary keys are TEXT (UUID strings), matching the Supabase migration note.
- JSON columns use SQLAlchemy's ``JSON`` type (becomes ``JSONB`` on PostgreSQL).
- DB-level ``DEFAULT`` clauses are preserved via ``server_default`` so the
  generated DDL matches the schema, while Python-side defaults keep the ORM
  ergonomic.
- ``DEFAULT CURRENT_TIMESTAMP`` columns carry ``server_default=func.now()``.
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
    fundamental_laws: Optional[Any] = Field(default=None, sa_column=Column(JSON))
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
    secrets: Optional[Any] = Field(default=None, sa_column=Column(JSON))
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
    subculture: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    magic_status: str = Field(
        default="inert", sa_column_kwargs={"server_default": text("'inert'")}
    )
    coordinates: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    access_level: Optional[str] = None


# -----------------------------------------------------------------------------
# faction  (extension of entity)
# -----------------------------------------------------------------------------
class Faction(SQLModel, table=True):
    __tablename__ = "faction"
    __table_args__ = (Index("idx_faction_parent", "parent_faction_id"),)

    id: str = Field(primary_key=True, foreign_key="entity.id")
    faction_type: Optional[str] = None
    internal_structure: Optional[str] = None
    philosophy: Optional[str] = None
    magic_knowledge_level: str = Field(
        default="unaware",
        sa_column_kwargs={"server_default": text("'unaware'")},
    )
    internal_tensions: Optional[str] = None
    # DORMANT (BRIEF-26, schema v1.38): containment tree, mirror of
    # location.parent_location_id. No assembler or guard traverses it yet —
    # creator-CRUD only, metadata-config category, no change_history (same
    # as location_type / coordinates).
    parent_faction_id: Optional[str] = Field(
        default=None, foreign_key="entity.id"
    )
    # DORMANT: descriptive scale label, NOT derived from tree depth. No code
    # reads it yet. global | national | regional | local | other.
    scope: Optional[str] = None
    # DORMANT: prose, what the faction is trying to do. No mechanic, no
    # structured consumer.
    goals: Optional[str] = None
    # DORMANT (BRIEF-33, schema v1.44): prose dual of `philosophy` — what the
    # faction rejects/opposes. Public-tagged, authored + proposed, but read
    # by no assembler yet. Future reader MUST route through
    # `read_public_memberships` (see ARCHITECTURE_DECISIONS.md).
    aversion: Optional[str] = None


# -----------------------------------------------------------------------------
# faction_role  (declared role vocabulary of a faction, schema v1.76,
# TICKET-0024, BRIEF-0024-d — corrective: replaces the disconnected
# `faction.role_capacities` JSON map and `entity.metadata['roles']` list with
# one relational table)
#
# Declared role vocabulary of a faction. Public by construction (BRIEF-31
# lineage) — safe to expose to prompts and player-facing reads. Closed
# vocabulary for the AI path (K1). Case-duplicate names are schema-impossible
# via the unique index below (structural, not a code-side casefold check).
# Curated config, same family as `faction_type` / `philosophy` — no
# `change_history` column.
# -----------------------------------------------------------------------------
class FactionRole(SQLModel, table=True):
    __tablename__ = "faction_role"
    __table_args__ = (
        Index(
            "idx_faction_role_name", "faction_id", text("name COLLATE NOCASE"),
            unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    faction_id: str = Field(foreign_key="faction.id", nullable=False)
    name: str
    description: Optional[str] = None
    max_holders: Optional[int] = None  # NULL = unlimited
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    created_at: datetime = _created_ts()
    created_by: str


# -----------------------------------------------------------------------------
# faction_membership  (durable member <-> faction roster, schema v1.39)
#
# Durable counterpart to `gathering_member` (which is session-ephemeral).
# Roster predicate, single source: a membership is ACTIVE iff
# `left_at IS NULL`. Rows are append/close only — never updated in place or
# deleted; a role/primary change is close + reopen (a new row), so the closed
# rows ARE the history (no `change_history` column here, by construction).
# `role` and `is_secret` are DORMANT this step: stored, creator-editable, but
# read by no assembler — the first reader is the next brief, which must also
# add the structural `is_secret = FALSE` exclusion for non-creator contexts.
# -----------------------------------------------------------------------------
class FactionMembership(SQLModel, table=True):
    __tablename__ = "faction_membership"
    __table_args__ = (
        Index("idx_faction_membership_entity", "entity_id"),
        Index("idx_faction_membership_faction", "faction_id"),
        # At most one ACTIVE primary membership per member.
        Index(
            "idx_membership_one_primary", "entity_id",
            unique=True, sqlite_where=text("is_primary = 1 AND left_at IS NULL"),
        ),
        # No duplicate ACTIVE membership of the same member in the same faction.
        Index(
            "idx_membership_unique_active", "entity_id", "faction_id",
            unique=True, sqlite_where=text("left_at IS NULL"),
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)  # the member (a character, by intent)
    faction_id: str = Field(foreign_key="entity.id", nullable=False)
    role: Optional[str] = None  # creator-authored label. DORMANT: no assembler reads it yet.
    # Prompt-facing façade role (schema v1.41, BRIEF-30). NULL by default —
    # `read_public_memberships` resolves `cover_role ?? role`. The true
    # `role` stays creator-only when a cover is set; never read directly by
    # any prompt assembler.
    cover_role: Optional[str] = None
    is_primary: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    # DORMANT: the mole. Present but its exclusion is NOT enforced this step
    # (no reader exists). The first reader MUST filter is_secret=FALSE for
    # every non-creator context, by query construction.
    is_secret: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    joined_at: datetime = _created_ts()
    left_at: Optional[datetime] = None  # NULL = active, never erased


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
    # Schema v1.74, TICKET-0024: optional completion gate. Shape:
    # [{"type": "relation_gte", "target_entity_id": "<entity id>",
    # "threshold": <int 1-100>}] — v1 accepts ONLY `relation_gte`.
    # Creator-CRUD authored only (`writes.write_npc_goal_prerequisites`,
    # BRIEF-0024-a's editor). Read by `_apply_mutation`'s `goal_change
    # complete` judge and the per-NPC tick briefing (BRIEF-0024-b).
    prerequisites: Optional[list] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )


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
# session  (a period of play)
# -----------------------------------------------------------------------------
class Session(SQLModel, table=True):
    __tablename__ = "session"

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    number: int
    title: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str = Field(
        default="open", sa_column_kwargs={"server_default": text("'open'")}
    )
    summary: Optional[str] = None
    creator_notes: Optional[str] = None


# -----------------------------------------------------------------------------
# batch  (grouping of pass-plays)
# -----------------------------------------------------------------------------
class Batch(SQLModel, table=True):
    __tablename__ = "batch"

    id: str = Field(default_factory=_uuid, primary_key=True)
    session_id: str = Field(foreign_key="session.id", nullable=False)
    status: str = Field(
        default="pending",
        sa_column_kwargs={"server_default": text("'pending'")},
    )
    local_summary: Optional[str] = None
    message_to_claude: Optional[str] = None
    claude_raw_response: Optional[str] = None
    final_result: Optional[str] = None
    creator_notes: Optional[str] = None
    created_at: datetime = _created_ts()
    processed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None


# -----------------------------------------------------------------------------
# pass_play  (an action declared between sessions)
# -----------------------------------------------------------------------------
class PassPlay(SQLModel, table=True):
    __tablename__ = "pass_play"
    __table_args__ = (Index("idx_passplay_batch", "batch_id"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    batch_id: str = Field(foreign_key="batch.id", nullable=False)
    session_id: str = Field(foreign_key="session.id", nullable=False)
    character_id: str = Field(foreign_key="entity.id", nullable=False)
    declared_action: str
    injected_context: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    creator_notes: Optional[str] = None
    status: str = Field(
        default="submitted",
        sa_column_kwargs={"server_default": text("'submitted'")},
    )
    batch_order: Optional[int] = None
    history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )
    submitted_at: datetime = _created_ts()
    applied_at: Optional[datetime] = None


# -----------------------------------------------------------------------------
# gathering  (ephemeral social cluster, attached to a session)
# -----------------------------------------------------------------------------
class Gathering(SQLModel, table=True):
    __tablename__ = "gathering"
    __table_args__ = (
        Index("idx_gathering_location", "location_id"),
        Index("idx_gathering_session", "session_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    session_id: str = Field(foreign_key="session.id", nullable=False)
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    label: Optional[str] = None
    status: str = Field(
        default="open", sa_column_kwargs={"server_default": text("'open'")}
    )
    created_at: datetime = _created_ts()
    dissolved_at: Optional[datetime] = None


# -----------------------------------------------------------------------------
# gathering_member  (roster — also the conversation's participant list)
# -----------------------------------------------------------------------------
class GatheringMember(SQLModel, table=True):
    __tablename__ = "gathering_member"
    __table_args__ = (
        Index("idx_gathering_member_group", "gathering_id"),
        Index("idx_gathering_member_entity", "entity_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    gathering_id: str = Field(foreign_key="gathering.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)
    joined_at: datetime = _created_ts()
    left_at: Optional[datetime] = None  # NULL = still present, never erased


# -----------------------------------------------------------------------------
# conversation  (live player <-> NPC exchange)
# -----------------------------------------------------------------------------
class Conversation(SQLModel, table=True):
    __tablename__ = "conversation"
    __table_args__ = (
        Index("idx_conversation_world", "world_id"),
        Index("idx_conversation_gathering", "gathering_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    session_id: str = Field(foreign_key="session.id", nullable=False)
    location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    player_id: str = Field(foreign_key="entity.id", nullable=False)
    npc_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    gathering_id: Optional[str] = Field(default=None, foreign_key="gathering.id")
    status: str = Field(
        default="open", sa_column_kwargs={"server_default": text("'open'")}
    )
    injected_context: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    # scene_state is EPHEMERAL combat/constraint state, scoped to the conversation.
    # It is cleared when the conversation closes. It is NOT canon: a durable
    # consequence (lasting injury, capture, death) must go through
    # proposed_mutation. Same philosophy as gathering: free play inside the
    # scene, controlled consequences outside it.
    scene_state: Any = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default=text("'{}'")),
    )
    started_at: datetime = _created_ts()
    ended_at: Optional[datetime] = None
    last_analyzed_turn: int = Field(
        default=0, sa_column_kwargs={"server_default": text("0")}
    )


# -----------------------------------------------------------------------------
# conversation_message  (each line, in order)
# -----------------------------------------------------------------------------
class ConversationMessage(SQLModel, table=True):
    __tablename__ = "conversation_message"
    __table_args__ = (Index("idx_message_conversation", "conversation_id"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    conversation_id: str = Field(
        foreign_key="conversation.id", nullable=False
    )
    turn_order: int
    speaker: str  # player | npc | mj
    speaker_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    content: str
    created_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# proposed_mutation  (unified validation pipeline)
# -----------------------------------------------------------------------------
class ProposedMutation(SQLModel, table=True):
    __tablename__ = "proposed_mutation"
    __table_args__ = (
        Index("idx_mutation_status", "status"),
        Index("idx_mutation_passplay", "pass_play_id"),
        Index("idx_mutation_conversation", "conversation_id"),
        Index("idx_mutation_tick", "tick_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)

    # source: exactly one of these is set
    source_type: str  # pass_play | conversation | world_tick
    pass_play_id: Optional[str] = Field(
        default=None, foreign_key="pass_play.id"
    )
    conversation_id: Optional[str] = Field(
        default=None, foreign_key="conversation.id"
    )
    # world_tick sets NEITHER FK above; tick_id is its anchor — one UUID per
    # run_world_tick invocation, shared by every row it writes (schema v1.70,
    # TICKET-0014/BRIEF-0014-b). Read by the duplicate-guard's tick branch
    # and the queue's TICK badge.
    tick_id: Optional[str] = Field(default=None)

    # what kind of change
    mutation_type: str
    target_table: Optional[str] = None
    target_id: Optional[str] = None
    payload: Any = Field(sa_column=Column(JSON, nullable=False))

    # control
    status: str = Field(
        default="proposed",
        sa_column_kwargs={"server_default": text("'proposed'")},
    )
    rationale: Optional[str] = None
    creator_notes: Optional[str] = None
    proposed_by: str = Field(
        default="local_ai",
        sa_column_kwargs={"server_default": text("'local_ai'")},
    )
    proposed_at: datetime = _created_ts()
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None


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
    involved_entities: Optional[Any] = Field(
        default=None, sa_column=Column(JSON)
    )
    location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    has_magic_impact: bool = Field(
        default=False, sa_column_kwargs={"server_default": text("0")}
    )
    consequences: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    occurred_at: Optional[datetime] = None
    recorded_at: datetime = _created_ts()


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
# user  (system accounts)
# -----------------------------------------------------------------------------
class User(SQLModel, table=True):
    __tablename__ = "user"

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    email: Optional[str] = Field(default=None, unique=True)
    role: str = Field(
        default="player",
        nullable=False,
        sa_column_kwargs={"server_default": text("'player'")},
    )
    created_at: datetime = _created_ts()
    is_active: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("1")}
    )


# -----------------------------------------------------------------------------
# prompt_template  (creator-editable master prompts — head/identity row only;
# text lives exclusively in `prompt_version`, schema vX.YY / TICKET-0011)
# -----------------------------------------------------------------------------
class PromptTemplate(SQLModel, table=True):
    __tablename__ = "prompt_template"

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: Optional[str] = Field(default=None, foreign_key="world.id")
    name: str
    usage: str
    variables: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    destination: str = Field(
        default="local",
        sa_column_kwargs={"server_default": text("'local'")},
    )
    model: Optional[str] = Field(default=None)
    # NULL = code decides (default_model); non-NULL = creator override,
    # consumed by prompt_registry.effective_model (BRIEF-0008-a, schema v1.67).
    is_active: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("1")}
    )
    notes: Optional[str] = None
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# prompt_version  (append-only prompt text history, schema vX.YY / TICKET-0011)
#
# "Current" = MAX(version_number) per prompt_template_id — no pointer column
# anywhere (A2). No UPDATE, no DELETE, ever (append-only by construction). The
# ONLY read path is `prompt_store.current_prompt`/`get_version`/`list_versions`;
# the ONLY write path is `writes.write_prompt_version`.
# -----------------------------------------------------------------------------
class PromptVersion(SQLModel, table=True):
    __tablename__ = "prompt_version"
    __table_args__ = (
        Index(
            "idx_prompt_version_head_number", "prompt_template_id", "version_number",
            unique=True,
        ),
        Index("idx_prompt_version_head", "prompt_template_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    prompt_template_id: str = Field(foreign_key="prompt_template.id", nullable=False)
    version_number: int
    system_prompt: str
    user_template: str
    note: Optional[str] = None
    created_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# visit  (player location entries, append-only — schema v1.71, TICKET-0016/
# BRIEF-0016-a). Anchors the player's last entry per location so enter_scene
# can compute a return-visit delta. NOT in canon_write_policy.txt's
# CANON_TABLES — written directly from enter_scene, same non-canon,
# bookkeeping status as gathering/gathering_member. No UPDATE/DELETE path
# exists (enforced by tooling/verify/checks/visit_delta.py rule 1).
# -----------------------------------------------------------------------------
class Visit(SQLModel, table=True):
    __tablename__ = "visit"
    __table_args__ = (
        Index("idx_visit_player_location", "player_id", "location_id", "entered_at"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    player_id: str = Field(foreign_key="entity.id", nullable=False)
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    entered_at: datetime = _created_ts()
    present_npc_ids: Optional[Any] = Field(default=None, sa_column=Column(JSON))


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


__all__ = [
    "World",
    "Entity",
    "Character",
    "Location",
    "Faction",
    "Relation",
    "Knowledge",
    "Session",
    "Batch",
    "PassPlay",
    "Gathering",
    "GatheringMember",
    "Conversation",
    "ConversationMessage",
    "ProposedMutation",
    "Event",
    "Artifact",
    "Item",
    "Skill",
    "DiscoverableDetail",
    "User",
    "PromptTemplate",
    "PromptVersion",
    "Visit",
    "Agenda",
    "AgendaStep",
    "GoalAgendaLink",
]
