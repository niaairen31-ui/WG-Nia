"""Canon SQLModel table classes — perception domain (what an entity holds
about the world, and the typed links between entities), extracted from
``canon.py`` (TICKET-0082, BRIEF-0082-a) to keep each stratum module under
the `module_budget.py` line cap. Same schema-fidelity conventions as
`canon.py` — see that module's docstring for the full convention list
(primary keys, JSON columns, ``server_default`` usage, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Column, Index, JSON, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid


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
        Index("idx_knowledge_subject", "subject"),
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
