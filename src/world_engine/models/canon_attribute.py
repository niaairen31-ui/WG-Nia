"""Canon SQLModel table classes -- the state of the world (TICKET-0113,
BRIEF-0113-A, schema v2.22; decisions WA3, WB2, WC1, WD1 and WH1 of the
conditions series).

A world defines its own attributes -- « Maudit », « Ouvert », « Niveau
d'alerte », « Occupé par » -- and every entity of a type the definition
names holds one value of it, its history kept row by row:

- `attribute_definition`      : one attribute of one world -- its name, its
  kind (a choice among labels, an integer, or another entity), its default
  (WC1: an entity with no value reads the default, nothing is written on
  read), whether it is hidden from the player (WH1), active or retired.
- `attribute_definition_type` : the entity types it applies to
  (`side = 'holder'`, WB2), and for an `entity` kind the types its value may
  name (`side = 'value'`).
- `attribute_choice`          : the labels of a `choice` kind, in order, one
  of them the default; a label is retired, never deleted.
- `attribute_value`           : one entity's current value -- a choice, an
  integer, or an entity (none of the three: an `entity` kind left empty).
- `attribute_change`          : the history (WD1), append-only: the value
  before and after each write, `correction` or `changement`, by whom --
  and, for a change an event made (M-c, TICKET-0119, v2.26), that event
  (`event_id`).

The states the canon already keeps (`character.vital_status`,
`entity.status`, `location.magic_status`) are read as SYSTEM attributes by
`attributes.py`, never copied here (G3 of the series). `writes/attributes.py`
is the one writer of all five tables. Same schema-fidelity conventions as
`canon.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

ATTRIBUTE_KINDS: tuple[str, ...] = ("choice", "integer", "entity")
ATTRIBUTE_TYPE_SIDES: tuple[str, ...] = ("holder", "value")
ATTRIBUTE_STATUSES: tuple[str, ...] = ("active", "retired")
# The kind of a change -- `writes.facts.FACT_CHANGE_KINDS`, quoted by the
# CHECK below (models never import `writes`; `attributes.py` AA1 keeps them
# equal).
ATTRIBUTE_CHANGE_KINDS: tuple[str, ...] = ("correction", "changement")


class AttributeDefinition(SQLModel, table=True):
    __tablename__ = "attribute_definition"
    __table_args__ = (
        CheckConstraint("kind IN ('choice','integer','entity')", name="ck_attribute_definition_kind"),
        CheckConstraint("status IN ('active','retired')", name="ck_attribute_definition_status"),
        CheckConstraint("kind = 'integer' OR default_integer IS NULL", name="ck_attribute_definition_default"),
        Index("idx_attribute_definition_name", "world_id", text("name COLLATE NOCASE"), unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    name: str
    kind: str
    default_integer: Optional[int] = None
    is_hidden: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()


class AttributeDefinitionType(SQLModel, table=True):
    __tablename__ = "attribute_definition_type"
    __table_args__ = (
        CheckConstraint("side IN ('holder','value')", name="ck_attribute_definition_type_side"),
        Index("idx_attribute_definition_type_unique", "definition_id", "side", "entity_type", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    definition_id: str = Field(foreign_key="attribute_definition.id", nullable=False)
    side: str
    entity_type: str


class AttributeChoice(SQLModel, table=True):
    __tablename__ = "attribute_choice"
    __table_args__ = (
        CheckConstraint("status IN ('active','retired')", name="ck_attribute_choice_status"),
        CheckConstraint("is_default = 0 OR status = 'active'", name="ck_attribute_choice_default"),
        Index("idx_attribute_choice_label", "definition_id", text("label COLLATE NOCASE"), unique=True),
        Index("idx_attribute_choice_one_default", "definition_id", unique=True,
              sqlite_where=text("is_default = 1")),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    definition_id: str = Field(foreign_key="attribute_definition.id", nullable=False)
    label: str
    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    is_default: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
    status: str = Field(default="active", sa_column_kwargs={"server_default": text("'active'")})


class AttributeValue(SQLModel, table=True):
    __tablename__ = "attribute_value"
    __table_args__ = (
        CheckConstraint(
            "(choice_id IS NOT NULL) + (integer_value IS NOT NULL) + (entity_value_id IS NOT NULL) <= 1",
            name="ck_attribute_value_one",
        ),
        Index("idx_attribute_value_pair", "definition_id", "entity_id", unique=True),
        Index("idx_attribute_value_entity", "entity_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    definition_id: str = Field(foreign_key="attribute_definition.id", nullable=False)
    entity_id: str = Field(foreign_key="entity.id", nullable=False)
    choice_id: Optional[str] = Field(default=None, foreign_key="attribute_choice.id")
    integer_value: Optional[int] = None
    entity_value_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    updated_at: datetime = _created_ts()


class AttributeChange(SQLModel, table=True):
    __tablename__ = "attribute_change"
    __table_args__ = (
        CheckConstraint("kind IN ('correction','changement')", name="ck_attribute_change_kind"),
        Index("idx_attribute_change_value", "value_id", "changed_at"),
        Index("idx_attribute_change_event", "event_id"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    value_id: str = Field(foreign_key="attribute_value.id", nullable=False)
    kind: str
    changed_by: str
    before_choice_id: Optional[str] = Field(default=None, foreign_key="attribute_choice.id")
    before_integer: Optional[int] = None
    before_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    after_choice_id: Optional[str] = Field(default=None, foreign_key="attribute_choice.id")
    after_integer: Optional[int] = None
    after_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
    changed_at: datetime = _created_ts()
    # v2.26 (TICKET-0119, M-c): the event that made this change, when one
    # did; a creator's own edit has none.
    event_id: Optional[str] = Field(default=None, foreign_key="event.id")
