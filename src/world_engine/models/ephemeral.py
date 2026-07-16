"""Ephemeral SQLModel table classes — session/scene-lifetime tables
(TICKET-0028, BRIEF-0028-c — package split of the former flat
``models.py``, by schema stratum).

None of these tables appear in ``canon_write_policy.txt``'s
``[CANON_TABLES]``; they are session/scene bookkeeping, not durable world
canon. Same schema-fidelity conventions as `canon.py` (see that module's
docstring).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column, Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid


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
