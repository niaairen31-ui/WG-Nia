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
# fact  (the spine: anything that can be known, schema vNEXT, TICKET-0082,
# BRIEF-0082-b)
#
# A fact is one proposition. It is EITHER a typed row that already exists
# (relation | event | world_law — at most one FK set, ck_fact_spine_exclusive)
# OR free-standing (every typed FK NULL), in which case `fact_participant`
# carries its arity: zero participants for a world-level statement, one for
# a statement about a single entity, three for a secret shared by three
# conspirators.
#
# There is NO `entity_id` column here on purpose. An arity-1 fact is a nu
# spine plus one participant row — exactly one way to say each thing.
#
# `content` is the TRUTH. A degraded or false belief lives on the knowledge
# row that points here (`knowledge.is_incorrect`), never on the fact.
#
# `situation_id` is deliberately absent: the `situation` table does not
# exist yet. Adding the FK before the table would be structure with no
# reader.
# -----------------------------------------------------------------------------
class Fact(SQLModel, table=True):
    __tablename__ = "fact"
    __table_args__ = (
        CheckConstraint(
            "(relation_id IS NOT NULL) + (event_id IS NOT NULL) + (world_law_id IS NOT NULL) <= 1",
            name="ck_fact_spine_exclusive",
        ),
        CheckConstraint(
            "default_level IN ('unaware','rumor','suspicious','partial','knows','fully_understands')",
            name="ck_fact_default_level",
        ),
        Index("idx_fact_world", "world_id"),
        Index("idx_fact_relation", "relation_id"),
        Index("idx_fact_event", "event_id"),
        Index("idx_fact_world_law", "world_law_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    relation_id: Optional[str] = Field(default=None, foreign_key="relation.id")
    event_id: Optional[str] = Field(default=None, foreign_key="event.id")
    world_law_id: Optional[str] = Field(default=None, foreign_key="world_law.id")
    content: str
    default_level: str = Field(
        default="unaware", sa_column_kwargs={"server_default": text("'unaware'")}
    )
    created_at: datetime = _created_ts()
    created_by: str
    change_history: list = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'")),
    )


# -----------------------------------------------------------------------------
# fact_participant  (arity for a free-standing fact — never for a typed one;
# enforced in code by writes/facts.py, spans two tables so SQLite cannot
# express it as a CHECK)
# -----------------------------------------------------------------------------
class FactParticipant(SQLModel, table=True):
    __tablename__ = "fact_participant"
    __table_args__ = (
        Index("idx_fact_participant_unique", "fact_id", "entity_id", unique=True),
        Index("idx_fact_participant_entity", "entity_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    fact_id: str = Field(foreign_key="fact.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)
    role: Optional[str] = None
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})


# -----------------------------------------------------------------------------
# fact_default  (scoped default knowledge level, schema vNEXT, TICKET-0082,
# BRIEF-0082-c — G2a: a secret known by an entire faction, or by everyone in
# a location, without one stored `knowledge` row per knower)
#
# Precedence (most specific first, `knowledge_resolve.py::resolve_knowledge_
# level`): a stored `knowledge` row beats every default outright; then the
# nearest `location`-scoped default up the entity's `parent_location_id`
# chain; then, across every ACTIVE faction membership, the HIGHEST
# `world`-scoped default; then `fact.default_level`.
#
# A faction scope uses the faction's `entity.id` directly — `Faction.id` is
# already a FK to `entity.id`, so `scope_id` needs no second column and no
# polymorphic type tag.
# -----------------------------------------------------------------------------
class FactDefault(SQLModel, table=True):
    __tablename__ = "fact_default"
    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('world','faction','location')",
            name="ck_fact_default_scope_type",
        ),
        CheckConstraint(
            "(scope_type = 'world' AND scope_id IS NULL) OR "
            "(scope_type <> 'world' AND scope_id IS NOT NULL)",
            name="ck_fact_default_scope_shape",
        ),
        CheckConstraint(
            "level IN ('unaware','rumor','suspicious','partial','knows','fully_understands')",
            name="ck_fact_default_level",
        ),
        Index(
            "idx_fact_default_unique", "fact_id", "scope_type", "scope_id", unique=True,
        ),
        Index("idx_fact_default_fact", "fact_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    fact_id: str = Field(foreign_key="fact.id", nullable=False)
    scope_type: str
    scope_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    level: str
    created_at: datetime = _created_ts()
    created_by: str


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
        Index("idx_knowledge_fact", "fact_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)
    fact_id: str = Field(foreign_key="fact.id", nullable=False)
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
