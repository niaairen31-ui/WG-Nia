"""A player's character draft (schema v2.32, TICKET-0126, BRIEF-0126-B, B1) --
non-canon, pending: nothing here reaches canon before the creator approves it
(TICKET-0129). Relational by INV-20: the player sees and edits every row.
Written only by `writes/pc_drafts.py`, which never commits. World tables,
deleted with their world.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

PC_DRAFT_STATUSES: tuple[str, ...] = ("draft", "submitted", "returned", "approved")
PC_DRAFT_ORIGINS: tuple[str, ...] = ("player", "designer")
PC_SKETCH_KINDS: tuple[str, ...] = ("family", "master", "faction", "other")
PC_KNOWLEDGE_LEVELS: tuple[str, ...] = ("rumor", "suspicious", "partial", "knows")
PC_SKETCH_MAX = 8


# -----------------------------------------------------------------------------
# pc_draft  (one player's character draft in one world; at most one open --
# not yet approved -- per world and player)
# -----------------------------------------------------------------------------
class PcDraft(SQLModel, table=True):
    __tablename__ = "pc_draft"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','submitted','returned','approved')", name="ck_pc_draft_status",
        ),
        CheckConstraint(
            "start_location_set_by IS NULL OR start_location_set_by IN ('player','designer')",
            name="ck_pc_draft_set_by",
        ),
        Index("idx_pc_draft_world", "world_id"),
        Index(
            "idx_pc_draft_open", "world_id", "user_id",
            unique=True, sqlite_where=text("status <> 'approved'"),
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    user_id: str = Field(foreign_key="user.id", nullable=False)
    status: str = Field(default="draft", sa_column_kwargs={"server_default": text("'draft'")})
    name: str = Field(default="", sa_column_kwargs={"server_default": text("''")})
    backstory: str = Field(default="", sa_column_kwargs={"server_default": text("''")})
    start_location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    start_location_set_by: Optional[str] = None
    creator_note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# pc_draft_skill  (a rank asked by the player and/or set by the designer;
# `skill_key` is a base domain or a skill_definition id, no FK -- the
# quest_request precedent)
# -----------------------------------------------------------------------------
class PcDraftSkill(SQLModel, table=True):
    __tablename__ = "pc_draft_skill"
    __table_args__ = (
        CheckConstraint(
            "(player_rank IS NULL OR player_rank BETWEEN 0 AND 5) "
            "AND (designer_rank IS NULL OR designer_rank BETWEEN 0 AND 5)",
            name="ck_pc_draft_skill_ranks",
        ),
        CheckConstraint(
            "player_rank IS NOT NULL OR designer_rank IS NOT NULL",
            name="ck_pc_draft_skill_some",
        ),
        Index("idx_pc_draft_skill_key", "draft_id", "skill_key", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    draft_id: str = Field(foreign_key="pc_draft.id", nullable=False)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    skill_key: str
    player_rank: Optional[int] = None
    designer_rank: Optional[int] = None
    justification: Optional[str] = None
    designer_reason: Optional[str] = None


# -----------------------------------------------------------------------------
# pc_draft_sketch  (a person of the backstory: family, a master who taught a
# skill, a faction contact, another)
# -----------------------------------------------------------------------------
class PcDraftSketch(SQLModel, table=True):
    __tablename__ = "pc_draft_sketch"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('family','master','faction','other')", name="ck_pc_draft_sketch_kind",
        ),
        CheckConstraint(
            "(kind = 'master') = (skill_key IS NOT NULL)", name="ck_pc_draft_sketch_master",
        ),
        CheckConstraint("origin IN ('player','designer')", name="ck_pc_draft_sketch_origin"),
        Index("idx_pc_draft_sketch_draft", "draft_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    draft_id: str = Field(foreign_key="pc_draft.id", nullable=False)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    position: int
    name: str
    role: str = Field(default="", sa_column_kwargs={"server_default": text("''")})
    sentence: str = Field(default="", sa_column_kwargs={"server_default": text("''")})
    group_label: str = Field(default="", sa_column_kwargs={"server_default": text("''")})
    kind: str
    skill_key: Optional[str] = None
    existing_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    origin: str


# -----------------------------------------------------------------------------
# pc_draft_membership  (a faction the character would belong to)
# -----------------------------------------------------------------------------
class PcDraftMembership(SQLModel, table=True):
    __tablename__ = "pc_draft_membership"
    __table_args__ = (
        CheckConstraint(
            "origin IN ('player','designer')", name="ck_pc_draft_membership_origin",
        ),
        Index("idx_pc_draft_membership_faction", "draft_id", "faction_id", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    draft_id: str = Field(foreign_key="pc_draft.id", nullable=False)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    faction_id: str = Field(foreign_key="entity.id", nullable=False)
    role: Optional[str] = None
    origin: str


# -----------------------------------------------------------------------------
# pc_draft_knowledge  (a line the character would know, at a level)
# -----------------------------------------------------------------------------
class PcDraftKnowledge(SQLModel, table=True):
    __tablename__ = "pc_draft_knowledge"
    __table_args__ = (
        CheckConstraint(
            "level IN ('rumor','suspicious','partial','knows')",
            name="ck_pc_draft_knowledge_level",
        ),
        CheckConstraint(
            "origin IN ('player','designer')", name="ck_pc_draft_knowledge_origin",
        ),
        Index("idx_pc_draft_knowledge_draft", "draft_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    draft_id: str = Field(foreign_key="pc_draft.id", nullable=False)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    position: int
    level: str
    content: str
    origin: str
