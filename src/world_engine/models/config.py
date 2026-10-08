"""Conversation-window curated config (TICKET-0050, BRIEF-0050-a); `AgendaStep`
(TICKET-0075, BRIEF-0075-b); `condition` and `condition_node` (TICKET-0111,
BRIEF-0111-C), which replaced `agenda_step_requirement`.

Split out of `canon.py` (974/1000 lines at TICKET-0050, again at exactly
1000/1000 by TICKET-0075 — no headroom for a new table,
`tooling/verify/checks/module_budget.py`), not because these tables belong
to a different stratum: `AgendaStep` is the same `agenda`/`agenda_step`
family as `Agenda` (still in `canon.py`) — only its FILE moved, not its
identity, and every existing `from ..models import AgendaStep` import is
unaffected (resolved through `models/__init__.py`). `condition` / `condition_node`
are canon curated-config, same family as `location_type_catalog` / `world_law`
(metadata-config category, no `change_history`). `skill_rank` (TICKET-0106,
BRIEF-0106-A) is the same curated-config family, placed here for the same
module budget.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Column, Index, Integer, JSON, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

# -----------------------------------------------------------------------------
# conversation_window_config  (creator-tunable NPC dialogue context window,
# schema v1.89, TICKET-0050, BRIEF-0050-a)
#
# One row per world. Curated config (location_type_catalog family): no
# change_history, written ONLY via writes.upsert_conversation_window_config.
# Absence of a row is legal — the reader (context_window.py) applies
# in-memory defaults and never writes on read.
# -----------------------------------------------------------------------------
class ConversationWindowConfig(SQLModel, table=True):
    __tablename__ = "conversation_window_config"
    __table_args__ = (
        Index("idx_conversation_window_config_world", "world_id", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    word_budget: int = Field(
        default=1200,
        sa_column=Column(Integer, nullable=False, server_default=text("1200")),
    )
    # Counted in player/npc MESSAGE rows, NOT exchanges (6 rows = 3 exchanges).
    verbatim_turns: int = Field(
        default=6,
        sa_column=Column(Integer, nullable=False, server_default=text("6")),
    )
    summary_enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("1")),
    )
    updated_at: datetime = _created_ts()


# -----------------------------------------------------------------------------
# agenda_step  (structured faction intrigues — schema v1.72, TICKET-0018/
# BRIEF-0018-a; relocated from canon.py to here at TICKET-0075/BRIEF-0075-b
# for module_budget headroom, byte-identical otherwise). The model never
# addresses a step directly — it names the agenda by TITLE; the active step
# is always derived in code (the partial unique index below guarantees at
# most one). `cost`/`domain` (v1.94, BRIEF-0075-b): NULL for every
# pre-existing (NPC) step, populated only by `day_plan.py`. Still no location
# column — the positional wall (BRIEF-0074-a-amendment-1) holds.
# -----------------------------------------------------------------------------
class AgendaStep(SQLModel, table=True):
    __tablename__ = "agenda_step"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','active','completed','failed')",
            name="ck_agenda_step_status",
        ),
        CheckConstraint(
            "cost IS NULL OR cost BETWEEN 1 AND 4", name="ck_agenda_step_cost",
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
    cost: Optional[int] = None
    domain: Optional[str] = None
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


# -----------------------------------------------------------------------------
# condition / condition_node  (the condition language, schema v2.20,
# TICKET-0111, BRIEF-0111-C -- decisions A1, I1, O-a, M1 and P1). They replace
# `agenda_step_requirement` and `quest_offer_requirement` (v1.94 / v2.17).
#
# A `condition` is ONE tree, owned by exactly one of an offer (its
# eligibility), an offer step or an agenda step (its prerequisite or, M1, its
# completion -- shown, never acting). At most one condition per owner and
# role. Its nodes are rows (O-a: never JSON, the UI reads them): a connector
# (`all`, `any`, `not`, `at_least` with `n`) or a leaf carrying one form of
# `condition_forms.REQUIREMENT_TYPES` and its arguments; `parent_id` and
# `position` give the tree its shape, the root has no parent.
#
# The form vocabulary is a code-plane property (the `entity_trait.trait_key`
# precedent): no CHECK lists the forms -- a new form is code, never a table
# rebuild. `writes.conditions.write_condition` is the one writer and refuses
# an unknown form, an ill-shaped tree or a target outside the world, before
# any row; `conditions.py` (CC) holds it to that. What a CHECK can say without
# naming a form, it says: a node is a connector or a leaf; a leaf names
# exactly one subject; a connector carries no argument; `at_least` has n >= 1.
# Curated plan metadata, the requirement rows' family: no `change_history`
# (an offer snapshots itself; a save replaces its conditions whole).
# -----------------------------------------------------------------------------
CONDITION_ROLES: tuple[str, ...] = ("eligibility", "prerequisite", "completion")
CONDITION_OPS: tuple[str, ...] = ("all", "any", "not", "at_least", "leaf")


class Condition(SQLModel, table=True):
    __tablename__ = "condition"
    __table_args__ = (
        CheckConstraint("role IN ('eligibility','prerequisite','completion')", name="ck_condition_role"),
        CheckConstraint(
            "(quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) + (agenda_step_id IS NOT NULL) = 1",
            name="ck_condition_owner",
        ),
        CheckConstraint("(quest_offer_id IS NOT NULL) = (role = 'eligibility')", name="ck_condition_owner_role"),
        Index("idx_condition_offer", "quest_offer_id", "role", unique=True),
        Index("idx_condition_offer_step", "quest_offer_step_id", "role", unique=True),
        Index("idx_condition_agenda_step", "agenda_step_id", "role", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    role: str
    quest_offer_id: Optional[str] = Field(default=None, foreign_key="quest_offer.id")
    quest_offer_step_id: Optional[str] = Field(default=None, foreign_key="quest_offer_step.id")
    agenda_step_id: Optional[str] = Field(default=None, foreign_key="agenda_step.id")
    created_at: datetime = _created_ts()


class ConditionNode(SQLModel, table=True):
    __tablename__ = "condition_node"
    __table_args__ = (
        CheckConstraint("op IN ('all','any','not','at_least','leaf')", name="ck_condition_node_op"),
        CheckConstraint("(op = 'leaf') = (form IS NOT NULL)", name="ck_condition_node_leaf"),
        CheckConstraint(
            "op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND target_entity_id IS NULL "
            "AND target_key IS NULL AND threshold IS NULL AND value IS NULL)",
            name="ck_condition_node_connector",
        ),
        CheckConstraint(
            "op <> 'leaf' OR ((subject_role IS NULL) <> (subject_entity_id IS NULL))",
            name="ck_condition_node_subject",
        ),
        CheckConstraint(
            "subject_role IS NULL OR subject_role IN ('doer','giver','contact')", name="ck_condition_node_role",
        ),
        CheckConstraint("(op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)", name="ck_condition_node_n"),
        Index("idx_condition_node_condition", "condition_id", "parent_id", "position"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    condition_id: str = Field(foreign_key="condition.id", nullable=False)
    parent_id: Optional[str] = Field(default=None, foreign_key="condition_node.id")
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    op: str
    n: Optional[int] = None
    form: Optional[str] = None
    subject_role: Optional[str] = None
    subject_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    target_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    target_key: Optional[str] = None
    threshold: Optional[int] = None
    value: Optional[str] = None


# -----------------------------------------------------------------------------
# skill_rank  (a world's rank ladder — schema v2.15, TICKET-0106, BRIEF-0106-A)
#
# At most one row per (world, rank): the name the world gives that rank and
# the points a skill needs to leave it (`points_to_next`, NULL only for the
# top rank). Absence of a row is legal: the reader (`skill_ranks.world_ladder`)
# applies `skill_ranks.DEFAULT_RANK_LABELS` / `DEFAULT_POINTS_TO_NEXT` and
# never writes on read (`conversation_window_config` precedent). Curated
# config, no `change_history`; written only by `writes.upsert_skill_rank`.
# -----------------------------------------------------------------------------
class SkillRank(SQLModel, table=True):
    __tablename__ = "skill_rank"
    __table_args__ = (
        CheckConstraint("rank BETWEEN 0 AND 5", name="ck_skill_rank_rank"),
        CheckConstraint(
            "(rank = 5 AND points_to_next IS NULL) OR (rank < 5 AND points_to_next >= 1)",
            name="ck_skill_rank_points",
        ),
        Index("idx_skill_rank_world_rank", "world_id", "rank", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    rank: int
    label: str
    points_to_next: Optional[int] = None
    updated_at: datetime = _created_ts()
