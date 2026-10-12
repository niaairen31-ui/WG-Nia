"""The writer of the state of the world (TICKET-0113, BRIEF-0113-A;
decisions WA3, WB2, WC1, WD1, WE1 and WJ2 of the conditions series): the
one writer of `attribute_definition`, `attribute_definition_type`,
`attribute_choice`, `attribute_value` and `attribute_change`.

- `clean_definition(db, world_id, spec, definition_id=None)` : a definition
  as it will be written, or `ValueError` -- the name is not a system
  attribute's nor another definition's of the world (compared through
  `lore_resolve.normalize_surface`), its types are the world's, a `choice`
  kind has two labels or more and one of them is the default, an `integer`
  kind has an integer default, an `entity` kind names the types its value
  may take. On an existing definition, nothing in use is taken away (WJ2): its
  kind, a holder type an entity holding a value has, a value type a value
  names, a choice a value, a condition or an event type's effect holds;
  its kind while an effect names it (TICKET-0119). Writes nothing -- the
  interpreter validates a proposed definition through it (BRIEF-0113-E).
- `write_attribute_definition(db, *, world_id, spec, definition_id=None)` :
  create or save one definition after cleaning it; its types are replaced
  whole (the full-replace shape of `write_offer_terms`), a choice dropped
  from the list is retired, never deleted, and a retired label named again
  comes back.
- `set_attribute_status(db, *, world_id, definition_id, status)` : retire
  or restore one definition; retiring is refused while a condition or an
  event type's effect names it (WJ2, TICKET-0119).
- `write_attribute_value(db, *, world_id, definition_id, entity_id, value,
  kind, changed_by, event_id=None)` : set one entity's value and append its
  `attribute_change` row -- the value before (the default when it held
  none) and after, `correction` or `changement` (WD1), and the event that
  made it, when one did (M-c, TICKET-0119). An unchanged value writes
  nothing and returns None.

A system attribute (`attributes.SYSTEM_ATTRIBUTES`) is never written here:
its column keeps its own writer. None of these functions commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from ..attributes import (
    ATTRIBUTE_FORM,
    SYSTEM_ATTRIBUTES,
    RawValue,
    raw_of,
    stored_value,
    world_entity_types,
)
from ..lore_resolve import normalize_surface
from ..models import (
    ATTRIBUTE_CHANGE_KINDS,
    ATTRIBUTE_KINDS,
    ATTRIBUTE_STATUSES,
    AttributeChange,
    AttributeChoice,
    AttributeDefinition,
    AttributeDefinitionType,
    AttributeValue,
    EventTypeEffect,
    ConditionNode,
    Entity,
)

MAX_NAME_CHARS = 80


@dataclass(frozen=True)
class ChoiceSpec:
    """One label of a `choice` kind; `id` names an existing choice."""
    label: str
    id: Optional[str] = None


@dataclass(frozen=True)
class DefinitionSpec:
    """A definition as the creator (or the interpreter) states it. `default`
    is a choice's label, an integer, or None for an `entity` kind."""
    name: str
    kind: str
    holder_types: tuple[str, ...]
    value_types: tuple[str, ...] = ()
    choices: tuple[ChoiceSpec, ...] = ()
    default: RawValue = None
    is_hidden: bool = False


# --- cleaning ------------------------------------------------------------------

def _clean_name(db: Session, world_id: str, name: object, definition_id: Optional[str]) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("an attribute needs a name")
    clean = " ".join(name.split())
    if len(clean) > MAX_NAME_CHARS:
        raise ValueError(f"an attribute's name has at most {MAX_NAME_CHARS} characters")
    key = normalize_surface(clean)
    for system in SYSTEM_ATTRIBUTES:
        if normalize_surface(system.name) == key:
            raise ValueError(f"« {clean} » is a system attribute's name")
    for other in db.exec(select(AttributeDefinition).where(AttributeDefinition.world_id == world_id)).all():
        if other.id != definition_id and normalize_surface(other.name) == key:
            raise ValueError(f"« {clean} » is already the name of « {other.name} »")
    return clean


def _clean_types(world_types: tuple[str, ...], raw: object, what: str) -> tuple[str, ...]:
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise ValueError(f"an attribute's {what} types are a list")
    seen: list[str] = []
    for entity_type in raw:
        if entity_type not in world_types:
            raise ValueError(f"unknown entity type {entity_type!r}")
        if entity_type not in seen:
            seen.append(entity_type)
    return tuple(seen)


def _clean_choices(kind: str, choices: tuple[ChoiceSpec, ...], default: RawValue) -> tuple[tuple[ChoiceSpec, ...], RawValue]:
    if kind != "choice":
        if choices:
            raise ValueError(f"a {kind} attribute has no choices")
        return (), default
    labels: list[ChoiceSpec] = []
    keys: set[str] = set()
    for choice in choices:
        label = " ".join(str(choice.label or "").split())
        if not label:
            raise ValueError("a choice needs a label")
        if normalize_surface(label) in keys:
            raise ValueError(f"the label « {label} » is given twice")
        keys.add(normalize_surface(label))
        labels.append(ChoiceSpec(label=label, id=choice.id))
    if len(labels) < 2:
        raise ValueError("a choice attribute has at least two labels")
    if not isinstance(default, str) or normalize_surface(default) not in keys:
        raise ValueError("a choice attribute's default is one of its labels")
    chosen = next(c.label for c in labels if normalize_surface(c.label) == normalize_surface(default))
    return tuple(labels), chosen


def _clean_default(kind: str, default: RawValue) -> RawValue:
    if kind == "integer":
        if not isinstance(default, int) or isinstance(default, bool):
            raise ValueError("an integer attribute's default is an integer")
        return default
    if kind == "entity" and default is not None:
        raise ValueError("an entity attribute's default is empty")
    return default


def clean_definition(
    db: Session, world_id: str, spec: DefinitionSpec, definition_id: Optional[str] = None,
) -> DefinitionSpec:
    """`spec` as it will be written; raises `ValueError` on any violation.
    Writes nothing."""
    if spec.kind not in ATTRIBUTE_KINDS:
        raise ValueError(f"unknown attribute kind {spec.kind!r}")
    world_types = world_entity_types(db, world_id)
    holder_types = _clean_types(world_types, spec.holder_types, "holder")
    if not holder_types:
        raise ValueError("an attribute applies to one entity type or more")
    value_types = _clean_types(world_types, spec.value_types, "value")
    if (spec.kind == "entity") != bool(value_types):
        raise ValueError("an entity attribute, and only it, names the types its value may take")
    choices, default = _clean_choices(spec.kind, tuple(spec.choices), spec.default)
    clean = DefinitionSpec(
        name=_clean_name(db, world_id, spec.name, definition_id), kind=spec.kind,
        holder_types=holder_types, value_types=value_types, choices=choices,
        default=_clean_default(spec.kind, default), is_hidden=bool(spec.is_hidden),
    )
    if definition_id is not None:
        _clean_update(db, world_id, definition_id, clean)
    elif any(c.id for c in clean.choices):
        raise ValueError("a new attribute's choices carry no id")
    return clean


# --- what an existing definition holds (WJ2) -----------------------------------

def _leaves(db: Session, definition_id: str) -> list[ConditionNode]:
    return list(db.exec(select(ConditionNode).where(
        ConditionNode.form == ATTRIBUTE_FORM, ConditionNode.target_key == definition_id,
    )).all())


def _effects(db: Session, definition_id: str) -> list[EventTypeEffect]:
    return list(db.exec(select(EventTypeEffect).where(EventTypeEffect.definition_id == definition_id)).all())


def _values(db: Session, definition_id: str) -> list[AttributeValue]:
    return list(db.exec(select(AttributeValue).where(AttributeValue.definition_id == definition_id)).all())


def _entity_type(db: Session, entity_id: Optional[str]) -> Optional[str]:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.type if entity is not None else None


def _clean_update(db: Session, world_id: str, definition_id: str, clean: DefinitionSpec) -> None:
    definition = db.get(AttributeDefinition, definition_id)
    if definition is None or definition.world_id != world_id:
        raise ValueError(f"unknown attribute {definition_id!r}")
    values, leaves = _values(db, definition_id), _leaves(db, definition_id)
    effects = _effects(db, definition_id)
    if clean.kind != definition.kind and (values or leaves or effects):
        raise ValueError(f"« {definition.name} » is in use: its kind cannot change")
    held = {_entity_type(db, v.entity_id) for v in values} | {
        _entity_type(db, n.subject_entity_id) for n in leaves if n.subject_entity_id}
    for entity_type in sorted(t for t in held if t and t not in clean.holder_types):
        raise ValueError(f"« {definition.name} » is in use on a {entity_type}: that type stays")
    named = {_entity_type(db, v.entity_value_id) for v in values if v.entity_value_id} | {
        _entity_type(db, n.target_entity_id) for n in leaves if n.target_entity_id}
    for entity_type in sorted(t for t in named if t and t not in clean.value_types):
        raise ValueError(f"« {definition.name} » names a {entity_type}: that value type stays")
    kept = {c.id for c in clean.choices if c.id}
    used = {v.choice_id for v in values if v.choice_id} | {n.value for n in leaves if n.value} | {
        e.choice_id for e in effects if e.choice_id}
    for choice in _choice_rows(db, definition_id):
        if choice.status == "active" and choice.id not in kept and choice.id in used:
            raise ValueError(f"the label « {choice.label} » is in use: it stays")
    for choice in clean.choices:
        if choice.id and choice.id not in {c.id for c in _choice_rows(db, definition_id)}:
            raise ValueError(f"unknown choice {choice.id!r}")


def _choice_rows(db: Session, definition_id: str) -> list[AttributeChoice]:
    return list(db.exec(select(AttributeChoice).where(
        AttributeChoice.definition_id == definition_id).order_by(AttributeChoice.position)).all())


# --- writing a definition --------------------------------------------------------

def _write_types(db: Session, world_id: str, definition_id: str, clean: DefinitionSpec) -> None:
    db.execute(text("DELETE FROM attribute_definition_type WHERE definition_id = :did"), {"did": definition_id})
    for side, types in (("holder", clean.holder_types), ("value", clean.value_types)):
        for entity_type in types:
            db.add(AttributeDefinitionType(world_id=world_id, definition_id=definition_id, side=side,
                                           entity_type=entity_type))


def _write_choices(db: Session, world_id: str, definition_id: str, clean: DefinitionSpec) -> None:
    rows = _choice_rows(db, definition_id)
    by_id = {c.id: c for c in rows}
    by_label = {normalize_surface(c.label): c for c in rows}
    kept: set[str] = set()
    for row in rows:
        row.is_default = False
        db.add(row)
    db.flush()
    for position, spec in enumerate(clean.choices):
        row = by_id.get(spec.id) if spec.id else by_label.get(normalize_surface(spec.label))
        if row is None:
            row = AttributeChoice(world_id=world_id, definition_id=definition_id, label=spec.label)
        row.label, row.position, row.status = spec.label, position, "active"
        row.is_default = normalize_surface(spec.label) == normalize_surface(str(clean.default))
        db.add(row)
        db.flush()
        kept.add(row.id)
    for row in rows:
        if row.id not in kept:
            row.status = "retired"
            db.add(row)


def write_attribute_definition(
    db: Session, *, world_id: str, spec: DefinitionSpec, definition_id: Optional[str] = None,
) -> AttributeDefinition:
    """Create (`definition_id` None) or save one definition after
    `clean_definition`. Returns its row, flushed."""
    clean = clean_definition(db, world_id, spec, definition_id)
    if definition_id is None:
        definition = AttributeDefinition(world_id=world_id, name=clean.name, kind=clean.kind)
    else:
        definition = db.get(AttributeDefinition, definition_id)
    definition.name, definition.kind, definition.is_hidden = clean.name, clean.kind, clean.is_hidden
    definition.default_integer = clean.default if clean.kind == "integer" else None
    definition.updated_at = datetime.now(UTC)
    db.add(definition)
    db.flush()
    _write_types(db, world_id, definition.id, clean)
    _write_choices(db, world_id, definition.id, clean)
    db.flush()
    return definition


def set_attribute_status(db: Session, *, world_id: str, definition_id: str, status: str) -> AttributeDefinition:
    """Retire or restore one definition. Retiring is refused while a
    condition names it (WJ2)."""
    if status not in ATTRIBUTE_STATUSES:
        raise ValueError(f"unknown attribute status {status!r}")
    definition = db.get(AttributeDefinition, definition_id)
    if definition is None or definition.world_id != world_id:
        raise ValueError(f"unknown attribute {definition_id!r}")
    if status == "retired" and _leaves(db, definition_id):
        raise ValueError(f"« {definition.name} » is named by a condition: it cannot be retired")
    if status == "retired" and _effects(db, definition_id):
        raise ValueError(f"« {definition.name} » is changed by an event type: it cannot be retired")
    definition.status = status
    definition.updated_at = datetime.now(UTC)
    db.add(definition)
    db.flush()
    return definition


# --- writing a value --------------------------------------------------------------

def _clean_value(db: Session, world_id: str, definition: AttributeDefinition, value: RawValue) -> RawValue:
    if definition.kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"« {definition.name} » takes an integer")
        return value
    if definition.kind == "choice":
        choice = db.get(AttributeChoice, value) if isinstance(value, str) else None
        if choice is None or choice.definition_id != definition.id or choice.status != "active":
            raise ValueError(f"« {definition.name} » takes one of its labels")
        return value
    if value is None:
        return None
    entity = db.get(Entity, value) if isinstance(value, str) else None
    value_types = set(db.exec(select(AttributeDefinitionType.entity_type).where(
        AttributeDefinitionType.definition_id == definition.id, AttributeDefinitionType.side == "value",
    )).all())
    if entity is None or entity.world_id != world_id or entity.type not in value_types:
        raise ValueError(f"« {definition.name} » cannot name {value!r}")
    return value


def _default_raw(db: Session, definition: AttributeDefinition) -> RawValue:
    if definition.kind == "integer":
        return definition.default_integer
    if definition.kind == "choice":
        return db.exec(select(AttributeChoice.id).where(
            AttributeChoice.definition_id == definition.id, AttributeChoice.is_default == True,  # noqa: E712
        )).first()
    return None


def _columns(kind: str, raw: RawValue, prefix: str) -> dict:
    return {
        f"{prefix}choice_id": raw if kind == "choice" else None,
        f"{prefix}integer": raw if kind == "integer" else None,
        f"{prefix}entity_id": raw if kind == "entity" else None,
    }


def write_attribute_value(
    db: Session, *, world_id: str, definition_id: str, entity_id: str, value: RawValue, kind: str,
    changed_by: str, event_id: Optional[str] = None,
) -> Optional[AttributeChange]:
    """Set one entity's value of one active definition (WD1): `kind` is
    `correction` or `changement`; `event_id` the event that made it (M-c),
    a `changement` only. Returns the appended `attribute_change`, or None
    when the value is unchanged (nothing written)."""
    if kind not in ATTRIBUTE_CHANGE_KINDS:
        raise ValueError(f"unknown change kind {kind!r}")
    if not changed_by:
        raise ValueError("a change names who made it")
    if event_id is not None and kind != "changement":
        raise ValueError("an event changes the world: its change is a `changement`")
    definition = db.get(AttributeDefinition, definition_id)
    if definition is None or definition.world_id != world_id or definition.status != "active":
        raise ValueError(f"unknown attribute {definition_id!r}")
    entity = db.get(Entity, entity_id)
    holder_types = set(db.exec(select(AttributeDefinitionType.entity_type).where(
        AttributeDefinitionType.definition_id == definition_id, AttributeDefinitionType.side == "holder",
    )).all())
    if entity is None or entity.world_id != world_id or entity.type not in holder_types:
        raise ValueError(f"« {definition.name} » does not apply to {entity_id!r}")
    after = _clean_value(db, world_id, definition, value)
    row = stored_value(db, definition_id, entity_id)
    before = raw_of(row) if row is not None else _default_raw(db, definition)
    if before == after:
        return None
    if row is None:
        row = AttributeValue(world_id=world_id, definition_id=definition_id, entity_id=entity_id)
    row.choice_id, row.integer_value, row.entity_value_id = _columns(definition.kind, after, "").values()
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    change = AttributeChange(
        world_id=world_id, value_id=row.id, kind=kind, changed_by=changed_by, event_id=event_id,
        **_columns(definition.kind, before, "before_"), **_columns(definition.kind, after, "after_"),
    )
    db.add(change)
    db.flush()
    return change
