"""Conversation-window curated config (TICKET-0050, BRIEF-0050-a); `AgendaStep`
and `agenda_step_requirement` (TICKET-0075, BRIEF-0075-b).

Split out of `canon.py` (974/1000 lines at TICKET-0050, again at exactly
1000/1000 by TICKET-0075 — no headroom for a new table,
`tooling/verify/checks/module_budget.py`), not because these tables belong
to a different stratum: `AgendaStep` is the same `agenda`/`agenda_step`
family as `Agenda` (still in `canon.py`) — only its FILE moved, not its
identity, and every existing `from ..models import AgendaStep` import is
unaffected (resolved through `models/__init__.py`). `agenda_step_requirement`
is canon curated-config, same family as `location_type_catalog` / `world_law`
(metadata-config category, no `change_history`).
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
# agenda_step_requirement  (day-plan precondition gate, schema v1.94,
# TICKET-0075, BRIEF-0075-b). `goal_prerequisite` shape precedent (same
# id/world_id/type/target_entity_id/threshold spine), widened to a closed
# four-form vocabulary and a `target_key` column for the two forms that gate
# on a string (knowledge subject, resource tag) rather than an entity.
#
# The per-type shape CHECK is the structural guarantee that an ill-formed row
# cannot exist: `relation_gte`/`location_reachable` require target_entity_id
# NOT NULL; `knowledge`/`resource` require target_key NOT NULL;
# `relation_gte`/`resource` require threshold NOT NULL. Curated plan
# metadata, same family as `npc_schedule` — no `change_history`.
#
# THE POSITIONAL WALL: `location_reachable`'s target lives HERE, on the
# requirement row, never on `agenda_step` — a requirement states "the player
# must be able to reach L", a precondition on the player, never a position of
# an NPC. See BRIEF-0074-a-amendment-1.
# -----------------------------------------------------------------------------
class AgendaStepRequirement(SQLModel, table=True):
    __tablename__ = "agenda_step_requirement"
    __table_args__ = (
        CheckConstraint(
            "type IN ('knowledge','relation_gte','resource','location_reachable')",
            name="ck_agenda_step_requirement_type",
        ),
        CheckConstraint(
            "(type NOT IN ('relation_gte','location_reachable') OR target_entity_id IS NOT NULL) "
            "AND (type NOT IN ('knowledge','resource') OR target_key IS NOT NULL) "
            "AND (type NOT IN ('relation_gte','resource') OR threshold IS NOT NULL)",
            name="ck_agenda_step_requirement_shape",
        ),
        Index(
            "idx_agenda_step_requirement_unique", "step_id", "type",
            "target_entity_id", "target_key", unique=True,
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    step_id: str = Field(foreign_key="agenda_step.id", nullable=False)
    type: str
    target_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    target_key: Optional[str] = None
    threshold: Optional[int] = None
