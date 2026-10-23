"""Canon SQLModel table classes — skill domain, extracted from
``canon.py`` (TICKET-0126, BRIEF-0126-A) to keep each stratum module under
the `module_budget.py` line cap. Same schema-fidelity conventions as
`canon.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, CheckConstraint, Column, ForeignKey, Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

# The four structural skill domains — single source of truth (decision 3,
# BRIEF-55, schema v1.63). Previously declared independently in three places
# (cockpit/app.py `_PHYSICAL_DOMAINS`, cockpit/crud.py and seed_pilot.py
# `SKILL_DOMAINS`); all three now import this constant instead.
BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")

# A rank threshold is a positive count of points, or NULL to inherit (v2.15,
# TICKET-0106). One literal for the two tables that carry the five columns.
RANK_POINTS_CHECK = " AND ".join(
    f"(points_to_rank_{n} IS NULL OR points_to_rank_{n} >= 1)" for n in range(1, 6)
)


# -----------------------------------------------------------------------------
# skill_system  (world-authored body of skill rules — magic, technology,
# ritual, ... ; schema v2.01, TICKET-0084)
# -----------------------------------------------------------------------------
class SkillSystem(SQLModel, table=True):
    __tablename__ = "skill_system"
    __table_args__ = (
        CheckConstraint(RANK_POINTS_CHECK, name="ck_skill_system_rank_points"),
        Index("idx_skill_system_world_name", "world_id", "name", unique=True),
        Index("idx_skill_system_world", "world_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    name: str
    description: Optional[str] = None  # rendered as the group subtitle (F2)
    # Points to reach each rank, for every skill of this system (v2.15,
    # TICKET-0106). NULL = the world's default (`skill_ranks.points_to_next`).
    points_to_rank_1: Optional[int] = None
    points_to_rank_2: Optional[int] = None
    points_to_rank_3: Optional[int] = None
    points_to_rank_4: Optional[int] = None
    points_to_rank_5: Optional[int] = None
    # Whether reaching rank n asks a trial (v2.29, TICKET-0116, B1); NULL inherits.
    trial_to_rank_1: Optional[bool] = None
    trial_to_rank_2: Optional[bool] = None
    trial_to_rank_3: Optional[bool] = None
    trial_to_rank_4: Optional[bool] = None
    trial_to_rank_5: Optional[bool] = None
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


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
        CheckConstraint(RANK_POINTS_CHECK, name="ck_skill_definition_rank_points"),
        Index("idx_skill_definition_world_name", "world_id", "name", unique=True),
        Index("idx_skill_definition_world", "world_id"),
        Index("idx_skill_definition_system", "system_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    name: str
    base_domain: str  # specialises exactly one of BASE_SKILL_DOMAINS
    # The body of rules this skill belongs to; NULL = unaffiliated (v2.01).
    # `sa_column=Column(ForeignKey(..., ondelete=...), nullable=True)`
    # mirrors `Skill.skill_definition_id` below — SQLModel's
    # `Field(foreign_key=..., sa_column_kwargs={"ondelete": ...})` shape
    # raises (`ondelete` is a `ForeignKey` kwarg, not a `Column` kwarg).
    system_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skill_system.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    description: Optional[str] = None  # authored in chantier 2, not read this round
    # Points to reach each rank for this skill (v2.15, TICKET-0106). NULL =
    # its system's value, then the world's (`skill_ranks.points_to_next`).
    points_to_rank_1: Optional[int] = None
    points_to_rank_2: Optional[int] = None
    points_to_rank_3: Optional[int] = None
    points_to_rank_4: Optional[int] = None
    points_to_rank_5: Optional[int] = None
    # Whether reaching rank n asks a trial (v2.29, TICKET-0116, B1); NULL inherits.
    trial_to_rank_1: Optional[bool] = None
    trial_to_rank_2: Optional[bool] = None
    trial_to_rank_3: Optional[bool] = None
    trial_to_rank_4: Optional[bool] = None
    trial_to_rank_5: Optional[bool] = None
    # Learned only from a master (v2.16, TICKET-0107, A2): a player
    # character holds no row for it until taught, and cannot roll it.
    requires_master: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# skill  (a character's skill sheet — physical/sensory domains, schema v1.22;
# NPC rows too since v2.16, TICKET-0107;
# skill_definition_id added schema v1.63; `rank` and `xp` replace `tier` at
# v2.15, TICKET-0106 — the dice modifier is `skill_ranks.rank_modifier(rank)`)
# -----------------------------------------------------------------------------
class Skill(SQLModel, table=True):
    __tablename__ = "skill"
    __table_args__ = (
        CheckConstraint("rank BETWEEN 0 AND 5", name="ck_skill_rank"),
        CheckConstraint("xp >= 0", name="ck_skill_xp"),
        Index("idx_skill_character", "character_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    character_id: str = Field(foreign_key="entity.id", nullable=False)
    domain: str  # physical | agility | perception | composure
    rank: int = Field(default=1, sa_column_kwargs={"server_default": text("1")})
    xp: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
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
    # Who taught this skill (v2.16, TICKET-0107, C1): a character at Maître in
    # it when the row was learned; NULL for a row seeded or granted without
    # a master.
    taught_by_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
