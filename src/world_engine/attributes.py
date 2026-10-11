"""The state of the world, read (TICKET-0113, BRIEF-0113-A; decisions WA3,
WB2, WC1, WE1 and WH1 of the conditions series).

An attribute is either one of a world's definitions (`attribute_definition`,
keyed by its id) or a SYSTEM attribute -- a state the canon already keeps,
read where it lives and never copied (G3 of the series), keyed `sys:<name>`:
`character.vital_status`, `entity.status`, `location.magic_status`. Both
read the same way here:

- `attribute_view(db, world_id, key)` : one attribute as an `AttributeView`
  (its kind, its types, its choices, its default), or None.
- `world_attributes(db, world_id)`    : the system attributes, then the
  world's definitions by name.
- `current_value(db, view, entity)`   : an entity's `StateValue` -- its own
  value, or the default when it holds none (WC1: nothing is written on read).
- `world_entity_types(db, world_id)`  : the entity types a definition may
  name (WB2): the built-in four, then the world's active runtime types.

The vocabularies of the system attributes are the creator forms'
(`cockpit/crud/entities.py`: `ENTITY_STATUSES`, the character's
`vital_status` select, the location's `magic_status` select), kept equal to
them by `attributes.py` AA4. This module writes nothing; its writer is
`writes/attributes.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from sqlmodel import Session, select

from .models import (
    AttributeChoice,
    AttributeDefinition,
    AttributeDefinitionType,
    AttributeValue,
    Character,
    Entity,
    EntityType,
    Location,
)

# The condition form that reads an attribute (TICKET-0113, WG1); its
# evaluator lives in `condition_forms.py`.
ATTRIBUTE_FORM = "attribute"

# The built-in entity types -- `cockpit/crud/entities.py`'s
# `ENTITY_TYPE_REGISTRY` keys, kept equal by AA4. A runtime type is named by
# its `entity_type.slug`, which is its entities' `entity.type`.
BUILTIN_ENTITY_TYPES: tuple[str, ...] = ("character", "location", "faction", "item")

SYSTEM_PREFIX = "sys:"

RawValue = Union[str, int, None]


@dataclass(frozen=True)
class SystemAttribute:
    """A state the canon already keeps (WE1): a `choice` kind whose choices
    are the column's values, each with its French label."""
    key: str
    name: str
    entity_types: Optional[tuple[str, ...]]  # None: every entity
    values: tuple[tuple[str, str], ...]      # (stored value, French label)
    default: str


SYSTEM_ATTRIBUTES: tuple[SystemAttribute, ...] = (
    SystemAttribute("sys:vital_status", "État vital", ("character",),
                    (("alive", "en vie"), ("dead", "mort"), ("missing", "disparu"), ("unknown", "d'état inconnu")),
                    "alive"),
    SystemAttribute("sys:status", "Statut", None,
                    (("active", "actif"), ("inactive", "inactif"), ("destroyed", "détruit"),
                     ("missing", "disparu")),
                    "active"),
    SystemAttribute("sys:magic_status", "Magie", ("location",),
                    (("inert", "inerte"), ("sensitive", "sensible"), ("active", "active"), ("nexus", "nexus")),
                    "inert"),
)


@dataclass(frozen=True)
class AttributeView:
    """One attribute as every reader sees it. `choices` are (key, label)
    pairs in order -- a choice's id, or a system value; `default` is a
    choice key, an integer, or None (an `entity` kind's default is empty).
    `holder_types` None: every entity type."""
    key: str
    name: str
    kind: str
    system: bool
    hidden: bool
    status: str
    holder_types: Optional[tuple[str, ...]]
    value_types: tuple[str, ...]
    choices: tuple[tuple[str, str], ...]
    default: RawValue


@dataclass(frozen=True)
class StateValue:
    """An entity's state for one attribute: the raw value (a choice key, an
    integer, an entity id or None), its French label, and whether it is the
    default because the entity holds no value of its own."""
    raw: RawValue
    label: str
    is_default: bool


def system_attribute(key: Optional[str]) -> Optional[SystemAttribute]:
    return next((s for s in SYSTEM_ATTRIBUTES if s.key == key), None)


def world_entity_types(db: Session, world_id: str) -> tuple[str, ...]:
    """WB2: the built-in types, then the world's active runtime types by slug."""
    slugs = db.exec(select(EntityType.slug).where(
        EntityType.world_id == world_id, EntityType.status == "active",
    )).all()
    return BUILTIN_ENTITY_TYPES + tuple(sorted(s for s in slugs if s not in BUILTIN_ENTITY_TYPES))


def _system_view(spec: SystemAttribute) -> AttributeView:
    return AttributeView(
        key=spec.key, name=spec.name, kind="choice", system=True, hidden=False, status="active",
        holder_types=spec.entity_types, value_types=(), choices=spec.values, default=spec.default,
    )


def _types(db: Session, definition_id: str, side: str) -> tuple[str, ...]:
    return tuple(db.exec(select(AttributeDefinitionType.entity_type).where(
        AttributeDefinitionType.definition_id == definition_id, AttributeDefinitionType.side == side,
    ).order_by(AttributeDefinitionType.entity_type)).all())


def _definition_view(db: Session, definition: AttributeDefinition) -> AttributeView:
    choices = db.exec(select(AttributeChoice).where(
        AttributeChoice.definition_id == definition.id, AttributeChoice.status == "active",
    ).order_by(AttributeChoice.position)).all()
    default: RawValue = None
    if definition.kind == "choice":
        default = next((c.id for c in choices if c.is_default), None)
    elif definition.kind == "integer":
        default = definition.default_integer
    return AttributeView(
        key=definition.id, name=definition.name, kind=definition.kind, system=False,
        hidden=definition.is_hidden, status=definition.status,
        holder_types=_types(db, definition.id, "holder"), value_types=_types(db, definition.id, "value"),
        choices=tuple((c.id, c.label) for c in choices), default=default,
    )


def attribute_view(db: Session, world_id: str, key: Optional[str]) -> Optional[AttributeView]:
    """The attribute `key` names in `world_id` -- a system key or one of its
    definitions, active or retired -- or None."""
    spec = system_attribute(key)
    if spec is not None:
        return _system_view(spec)
    definition = db.get(AttributeDefinition, key) if key else None
    if definition is None or definition.world_id != world_id:
        return None
    return _definition_view(db, definition)


def world_attributes(db: Session, world_id: str, include_retired: bool = False) -> tuple[AttributeView, ...]:
    """Every attribute of the world: the system ones, then its definitions
    by name (the retired ones only on request)."""
    query = select(AttributeDefinition).where(AttributeDefinition.world_id == world_id)
    if not include_retired:
        query = query.where(AttributeDefinition.status == "active")
    definitions = sorted(db.exec(query).all(), key=lambda d: d.name.casefold())
    return tuple(_system_view(s) for s in SYSTEM_ATTRIBUTES) + tuple(_definition_view(db, d) for d in definitions)


def applies_to(view: AttributeView, entity_type: str) -> bool:
    return view.holder_types is None or entity_type in view.holder_types


def value_label(db: Session, view: AttributeView, raw: RawValue) -> str:
    """The French of one raw value of `view`: a choice's label (a retired one
    included, for the history), an integer, an entity's name, or « (aucun) »."""
    if raw is None:
        return "(aucun)"
    if view.kind == "integer":
        return str(raw)
    if view.kind == "entity":
        entity = db.get(Entity, raw)
        return entity.name if entity is not None else str(raw)
    label = dict(view.choices).get(raw)
    if label is None and not view.system:
        choice = db.get(AttributeChoice, raw)
        label = choice.label if choice is not None else None
    return label if label is not None else str(raw)


def _system_raw(db: Session, key: str, entity: Entity) -> RawValue:
    if key == "sys:status":
        return entity.status
    if key == "sys:vital_status":
        character = db.get(Character, entity.id)
        return character.vital_status if character is not None else None
    location = db.get(Location, entity.id)
    return location.magic_status if location is not None else None


def stored_value(db: Session, definition_id: str, entity_id: str) -> Optional[AttributeValue]:
    return db.exec(select(AttributeValue).where(
        AttributeValue.definition_id == definition_id, AttributeValue.entity_id == entity_id,
    )).first()


def raw_of(row: AttributeValue) -> RawValue:
    if row.choice_id is not None:
        return row.choice_id
    if row.integer_value is not None:
        return row.integer_value
    return row.entity_value_id


def current_value(db: Session, view: AttributeView, entity: Entity) -> StateValue:
    """The entity's state for `view`: a system column read where it lives,
    else its own value, else the default (WC1). The caller checks
    `applies_to` first."""
    if view.system:
        raw = _system_raw(db, view.key, entity)
        return StateValue(raw=raw, label=value_label(db, view, raw), is_default=False)
    row = stored_value(db, view.key, entity.id)
    if row is None:
        return StateValue(raw=view.default, label=value_label(db, view, view.default), is_default=True)
    raw = raw_of(row)
    return StateValue(raw=raw, label=value_label(db, view, raw), is_default=False)
