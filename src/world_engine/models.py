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

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    description: Optional[str] = None
    fundamental_laws: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    magic_status: str = Field(
        default="dormant",
        sa_column_kwargs={"server_default": text("'dormant'")},
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
    # ``metadata`` is reserved by SQLAlchemy's declarative base, so the Python
    # attribute is ``metadata_`` while the DB column stays ``metadata``.
    metadata_: Optional[Any] = Field(
        default=None, sa_column=Column("metadata", JSON)
    )
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# character  (extension of entity)
# -----------------------------------------------------------------------------
class Character(SQLModel, table=True):
    __tablename__ = "character"
    __table_args__ = (
        Index("idx_character_faction", "faction_id"),
        Index("idx_character_location", "current_location_id"),
        Index("idx_character_user", "user_id"),
    )

    id: str = Field(primary_key=True, foreign_key="entity.id")
    faction_id: Optional[str] = Field(default=None, foreign_key="entity.id")
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
    secrets: Optional[Any] = Field(default=None, sa_column=Column(JSON))


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

    id: str = Field(primary_key=True, foreign_key="entity.id")
    faction_type: Optional[str] = None
    internal_structure: Optional[str] = None
    philosophy: Optional[str] = None
    magic_knowledge_level: str = Field(
        default="unaware",
        sa_column_kwargs={"server_default": text("'unaware'")},
    )
    internal_tensions: Optional[str] = None


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
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)

    # source: exactly one of these is set
    source_type: str  # pass_play | conversation
    pass_play_id: Optional[str] = Field(
        default=None, foreign_key="pass_play.id"
    )
    conversation_id: Optional[str] = Field(
        default=None, foreign_key="conversation.id"
    )

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


# -----------------------------------------------------------------------------
# skill  (player character skill sheet — physical/sensory domains, schema v1.22)
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
    # DORMANT: minimum 2d6 total required to reveal (not compared this brief).
    # Reserved so "some info is better hidden than other" can be activated later
    # without a migration — same philosophy as knowledge.share_threshold.
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
# prompt_template  (creator-editable master prompts)
# -----------------------------------------------------------------------------
class PromptTemplate(SQLModel, table=True):
    __tablename__ = "prompt_template"

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: Optional[str] = Field(default=None, foreign_key="world.id")
    name: str
    usage: str
    system_prompt: str
    user_template: str
    variables: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    destination: str = Field(
        default="local",
        sa_column_kwargs={"server_default": text("'local'")},
    )
    version: int = Field(
        default=1, sa_column_kwargs={"server_default": text("1")}
    )
    is_active: bool = Field(
        default=True, sa_column_kwargs={"server_default": text("1")}
    )
    notes: Optional[str] = None
    updated_at: datetime = _created_ts()


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
]
