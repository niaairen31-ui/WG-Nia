"""Pipeline-internal SQLModel table classes — prompt/pipeline/approval
machinery (TICKET-0028, BRIEF-0028-c — package split of the former flat
``models.py``, by schema stratum).

None of these tables appear in ``canon_write_policy.txt``'s
``[CANON_TABLES]``. `PromptTemplate`/`PromptVariable`/`PromptVersion` carry
an explicit "(non-canon)" annotation at their sole writer
(`writes/prompts.py`, see `writes/__init__.py`'s layout docstring).
`User` is placed here per Nia's stratum escalation answer (TICKET-0028/
BRIEF-0028-c, 2026-07-15): app/account infrastructure, not world canon, not
scene-lifetime either — zero readers outside `models.py` as of schema v1.79
(logged as a no-reader review candidate in the BRIEF-0028-c execution
notes, out of this brief's scope).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, CheckConstraint, Column, Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid


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
# schema_meta  (static-plane schema version, C2 two-plane governance,
# schema v1.86 / TICKET-0044, BRIEF-0044-a)
#
# Singleton row (`CHECK (id = 1)`) recording the DB's applied static schema
# version. Migration-only infra, never canon: the ONLY writer is
# `scripts/migrate_v1_86_schema_meta.py` (plus `scripts/init_db.py`'s
# virgin-head seed). Read by the cockpit's fail-closed boot guard
# (`cockpit/app.py`) against `schema_version.EXPECTED_STATIC_SCHEMA_VERSION`.
# This is the STATIC plane only — the per-world runtime-type manifest
# (`entity_type`, BRIEF-0044-b) is a separate plane and never writes here.
# -----------------------------------------------------------------------------
class SchemaMeta(SQLModel, table=True):
    __tablename__ = "schema_meta"
    __table_args__ = (CheckConstraint("id = 1", name="ck_schema_meta_singleton"),)

    id: int = Field(default=1, primary_key=True)
    static_version: str
    updated_at: datetime = _created_ts()


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
# prompt_variable  (declared template variables, schema v1.79, TICKET-0025,
# BRIEF-0025-c — replaces prompt_template.variables JSON)
#
# One row per declared variable name. No change_history (curated config,
# not event canon).
# -----------------------------------------------------------------------------
class PromptVariable(SQLModel, table=True):
    __tablename__ = "prompt_variable"
    __table_args__ = (
        Index("idx_prompt_variable_unique", "prompt_template_id", "name", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    prompt_template_id: str = Field(foreign_key="prompt_template.id", nullable=False)
    name: str


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
