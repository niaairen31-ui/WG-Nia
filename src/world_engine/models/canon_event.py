"""Canon SQLModel table classes -- the event journal's vocabulary and its
participants (TICKET-0114, BRIEF-0114-A, schema v2.24; decisions F1, B1, C1,
D1, K-a, N1, V1 and W1 of the conditions series).

A world names what can happen in it -- « Tuer », « Repérer », « Pacte » --
and every `event` row is one happening of one of those types:

- `event_type`            : one type of one world -- its name, its domain
  (one of the seven former categories, F1), whether an event of it carries
  a quantity (« 3 loups »), whether it enters the chronicle the models read
  (Q1), whether its participants keep it secret by default (X1), active or
  retired.
- `event_type_role`       : the roles of a type (C1) -- « tueur »,
  « victime » -- in order; a role is retired, never deleted.
- `event_type_role_type`  : the entity types a role accepts (C1, the
  `attribute_definition_type` shape). A role may also accept a sorte
  (`accepts_sorte`, D1).
- `event_type_scope`      : who learns an event of the type (K-a, W1): its
  place, everyone, the acquaintances of a role, the faction a role names --
  each at a knowledge level. No row: the participants only.
- `event_sorte`           : the anonymous kinds of a world (D1) -- « loup »,
  « bandit » -- a role may be filled by one, with the event's quantity.
- `event_participant`     : who took part in one event, in which role: an
  entity or a sorte, exactly one (V1; it replaces `event_entity`).

`writes/event_types.py` is the one writer of the vocabulary tables,
`writes/events.py` the one writer of `event_participant`. Same
schema-fidelity conventions as `canon.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

# F1: the seven former `event.type` categories, now a type's domain. Quoted
# by the CHECK below; `tick_normalize._EVENT_TYPES` is the same set
# (`event_journal.py` EA1 keeps them equal).
EVENT_DOMAINS: tuple[str, ...] = (
    "political", "magical", "criminal", "military", "social", "mystery", "other",
)
# W1: who learns an event, besides its participants. `rencontre` and
# `faction` name a role of the type; `location` is the event's place.
EVENT_SCOPE_KINDS: tuple[str, ...] = ("location", "world", "rencontre", "faction")
EVENT_VOCAB_STATUSES: tuple[str, ...] = ("active", "retired")
# The knowledge ladder -- `writes.knowledge.KNOWLEDGE_LEVEL_LADDER`, quoted by
# the CHECK below (models never import `writes`; EA1 keeps them equal).
EVENT_SCOPE_LEVELS: tuple[str, ...] = (
    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
)


def _in(values: tuple[str, ...]) -> str:
    return ",".join(f"'{v}'" for v in values)


class EventType(SQLModel, table=True):
    __tablename__ = "event_type"
    __table_args__ = (
        CheckConstraint(f"domain IN ({_in(EVENT_DOMAINS)})", name="ck_event_type_domain"),
        CheckConstraint(f"status IN ({_in(EVENT_VOCAB_STATUSES)})", name="ck_event_type_status"),
        Index("idx_event_type_name", "world_id", text("name COLLATE NOCASE"), unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    name: str
    domain: str = Field(default="other", sa_column_kwargs={"server_default": text("'other'")})
    counts_quantity: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    in_chronicle: bool = Field(default=True, sa_column_kwargs={"server_default": text("1")})
    participants_secret: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


class EventTypeRole(SQLModel, table=True):
    __tablename__ = "event_type_role"
    __table_args__ = (
        CheckConstraint(f"status IN ({_in(EVENT_VOCAB_STATUSES)})", name="ck_event_type_role_status"),
        Index("idx_event_type_role_name", "type_id", text("name COLLATE NOCASE"), unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    type_id: str = Field(foreign_key="event_type.id", nullable=False)
    name: str
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    accepts_sorte: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})


class EventTypeRoleType(SQLModel, table=True):
    __tablename__ = "event_type_role_type"
    __table_args__ = (
        Index("idx_event_type_role_type_unique", "role_id", "entity_type", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    role_id: str = Field(foreign_key="event_type_role.id", nullable=False)
    entity_type: str


class EventTypeScope(SQLModel, table=True):
    __tablename__ = "event_type_scope"
    __table_args__ = (
        CheckConstraint(f"scope_kind IN ({_in(EVENT_SCOPE_KINDS)})", name="ck_event_type_scope_kind"),
        CheckConstraint(
            "(scope_kind IN ('rencontre','faction')) = (role_id IS NOT NULL)", name="ck_event_type_scope_role",
        ),
        CheckConstraint(f"level IN ({_in(EVENT_SCOPE_LEVELS)})", name="ck_event_type_scope_level"),
        Index("idx_event_type_scope_type", "type_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    type_id: str = Field(foreign_key="event_type.id", nullable=False)
    scope_kind: str
    role_id: Optional[str] = Field(default=None, foreign_key="event_type_role.id")
    level: str = Field(default="knows", sa_column_kwargs={"server_default": text("'knows'")})


class EventSorte(SQLModel, table=True):
    __tablename__ = "event_sorte"
    __table_args__ = (
        CheckConstraint(f"status IN ({_in(EVENT_VOCAB_STATUSES)})", name="ck_event_sorte_status"),
        Index("idx_event_sorte_name", "world_id", text("name COLLATE NOCASE"), unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    name: str
    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
    created_at: datetime = _created_ts()


class EventParticipant(SQLModel, table=True):
    __tablename__ = "event_participant"
    __table_args__ = (
        CheckConstraint(
            "(entity_id IS NOT NULL) + (sorte_id IS NOT NULL) = 1", name="ck_event_participant_one",
        ),
        Index("idx_event_participant_event", "event_id", "position"),
        Index("idx_event_participant_entity", "entity_id"),
        Index("idx_event_participant_unique_entity", "event_id", "role_id", "entity_id", unique=True,
              sqlite_where=text("entity_id IS NOT NULL")),
        Index("idx_event_participant_unique_sorte", "event_id", "role_id", "sorte_id", unique=True,
              sqlite_where=text("sorte_id IS NOT NULL")),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    event_id: str = Field(foreign_key="event.id", nullable=False)
    role_id: str = Field(foreign_key="event_type_role.id", nullable=False)
    entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    sorte_id: Optional[str] = Field(default=None, foreign_key="event_sorte.id")
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
