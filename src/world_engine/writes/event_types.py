"""The writer of the event journal's vocabulary (TICKET-0114, BRIEF-0114-A;
decisions B1, C1, D1, N1 and W1 of the conditions series): the one writer of
`event_type`, `event_type_role`, `event_type_role_type`, `event_type_scope`,
`event_type_effect` (TICKET-0119) and `event_sorte`.

- `clean_event_type(db, world_id, spec, type_id=None)` : a type as it will
  be written, or `ValueError` -- its name is no other type's of the world
  (compared through `lore_resolve.normalize_surface`), its domain one of
  `EVENT_DOMAINS`, one role or more with distinct names, each accepting one
  of the world's entity types or a sorte; a scope on `rencontre` names a
  role that accepts an entity, on `faction` a role that accepts a faction.
  An effect (M-c, TICKET-0119, `EFFECT_SYSTEM_KEYS` for E1) names one of
  its roles that holds an entity, a state of the world -- one of the world's
  active definitions, or `État vital` / `Statut` -- that applies to an
  entity type the role accepts, and a value of that state's kind: one of its
  choices, an integer (`add` only for an integer, D3), or another role whose
  entity the state may name; never the same role and state twice. On an
  existing type, nothing in use is taken away: a role an event or a
  condition names, an entity type a participant has, a sorte a participant
  is, a quantity an event carries. Writes nothing -- the interpreter and the
  analyzer validate a proposed type through it.
- `write_event_type(db, *, world_id, spec, type_id=None)` : create or save
  one type after cleaning it. Roles are matched by id, else by name; a role
  dropped from the list is retired, never deleted, and comes back when named
  again. A role's entity types, the type's scopes and its effects are
  replaced whole (an effect only pre-fills a proposal: nothing holds it).
- `set_event_type_status(db, *, world_id, type_id, status)` : retire or
  restore a type; retiring is refused while a condition names it.
- `clean_sorte_name` / `write_sorte(db, *, world_id, name, sorte_id=None)` /
  `set_sorte_status(...)` : the same for a sorte; retiring is refused while
  a condition names it.
- `ensure_domain_type(db, *, world_id, domain)` : the type made from a
  domain (N1) -- « Social », one role « Impliqué » accepting every entity
  type of the world -- found by its name, created when the world has none.
  It types what still arrives untyped (the world tick until TICKET-0119).

None of these functions commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import text
from sqlmodel import Session, select

from ..attributes import AttributeView, attribute_view, world_entity_types
from ..event_vocab import DOMAIN_LABELS_FR, DOMAIN_ROLE_FR, EVENT_FORM
from ..lore_resolve import normalize_surface
from ..models import (
    EVENT_DOMAINS,
    EVENT_EFFECT_MODES,
    EVENT_SCOPE_KINDS,
    EVENT_SCOPE_LEVELS,
    EVENT_VOCAB_STATUSES,
    ConditionNode,
    ConditionNodeFilter,
    Entity,
    Event,
    EventParticipant,
    EventSorte,
    EventType,
    EventTypeEffect,
    EventTypeRole,
    EventTypeRoleType,
    EventTypeScope,
)

MAX_NAME_CHARS = 80
MAX_ROLES = 8
MAX_EFFECTS = 8
# E1 (TICKET-0119): the system states an effect may change. `Magie` stays
# the creator's alone.
EFFECT_SYSTEM_KEYS: tuple[str, ...] = ("sys:vital_status", "sys:status")


@dataclass(frozen=True)
class RoleSpec:
    """One role as the creator states it; `id` names an existing role."""
    name: str
    entity_types: tuple[str, ...] = ()
    accepts_sorte: bool = False
    id: Optional[str] = None


@dataclass(frozen=True)
class ScopeSpec:
    """Who learns an event of the type (W1); `role` is a role's NAME, for a
    `rencontre` or `faction` scope."""
    kind: str
    role: Optional[str] = None
    level: str = "knows"


@dataclass(frozen=True)
class EffectSpec:
    """One effect as the creator states it (M-c): `role` and, for an
    `entity` state, `value` are role NAMES of the type; `attribute` is a
    definition id or a system key; `value` is otherwise a choice key or an
    integer. `mode` is `set` or, for an integer, `add` (D3)."""
    role: str
    attribute: str
    value: object
    mode: str = "set"


@dataclass(frozen=True)
class EventTypeSpec:
    name: str
    domain: str = "other"
    roles: tuple[RoleSpec, ...] = ()
    counts_quantity: bool = False
    in_chronicle: bool = True
    participants_secret: bool = False
    scopes: tuple[ScopeSpec, ...] = ()
    effects: tuple[EffectSpec, ...] = ()


# --- cleaning ------------------------------------------------------------------

def _clean_label(raw: object, what: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{what} needs a name")
    clean = " ".join(raw.split())
    if len(clean) > MAX_NAME_CHARS:
        raise ValueError(f"{what}'s name has at most {MAX_NAME_CHARS} characters")
    return clean


def _clean_type_name(db: Session, world_id: str, name: object, type_id: Optional[str]) -> str:
    clean = _clean_label(name, "an event type")
    key = normalize_surface(clean)
    for other in db.exec(select(EventType).where(EventType.world_id == world_id)).all():
        if other.id != type_id and normalize_surface(other.name) == key:
            raise ValueError(f"« {clean} » is already the name of « {other.name} »")
    return clean


def _clean_role(world_types: tuple[str, ...], role: RoleSpec) -> RoleSpec:
    name = _clean_label(role.name, "a role")
    if isinstance(role.entity_types, str) or not isinstance(role.entity_types, (list, tuple)):
        raise ValueError(f"the role « {name} »'s entity types are a list")
    types: list[str] = []
    for entity_type in role.entity_types:
        if entity_type not in world_types:
            raise ValueError(f"unknown entity type {entity_type!r}")
        if entity_type not in types:
            types.append(entity_type)
    if not types and not role.accepts_sorte:
        raise ValueError(f"the role « {name} » accepts an entity type or a sorte")
    return RoleSpec(name=name, entity_types=tuple(types), accepts_sorte=bool(role.accepts_sorte), id=role.id)


def _clean_roles(world_types: tuple[str, ...], roles: tuple[RoleSpec, ...]) -> tuple[RoleSpec, ...]:
    cleaned = tuple(_clean_role(world_types, role) for role in roles)
    if not cleaned:
        raise ValueError("an event type has one role or more")
    if len(cleaned) > MAX_ROLES:
        raise ValueError(f"an event type has at most {MAX_ROLES} roles")
    keys = [normalize_surface(role.name) for role in cleaned]
    for key, role in zip(keys, cleaned):
        if keys.count(key) > 1:
            raise ValueError(f"the role « {role.name} » is given twice")
    return cleaned


def _clean_scopes(roles: tuple[RoleSpec, ...], scopes: tuple[ScopeSpec, ...]) -> tuple[ScopeSpec, ...]:
    by_key = {normalize_surface(role.name): role for role in roles}
    seen: list[ScopeSpec] = []
    for scope in scopes:
        if scope.kind not in EVENT_SCOPE_KINDS:
            raise ValueError(f"unknown scope {scope.kind!r}")
        if scope.level not in EVENT_SCOPE_LEVELS or scope.level == "unaware":
            raise ValueError(f"a scope's level is one the knower holds, not {scope.level!r}")
        role = None
        if scope.kind in ("rencontre", "faction"):
            role = by_key.get(normalize_surface(scope.role or ""))
            if role is None:
                raise ValueError(f"a {scope.kind} scope names one of the type's roles")
            if scope.kind == "rencontre" and not role.entity_types:
                raise ValueError(f"the role « {role.name} » holds no entity: no one has met it")
            if scope.kind == "faction" and "faction" not in role.entity_types:
                raise ValueError(f"the role « {role.name} » accepts no faction")
        elif scope.role is not None:
            raise ValueError(f"a {scope.kind} scope names no role")
        clean = ScopeSpec(kind=scope.kind, role=role.name if role else None, level=scope.level)
        if any(s.kind == clean.kind and s.role == clean.role for s in seen):
            raise ValueError(f"the scope {scope.kind!r} is given twice")
        seen.append(clean)
    return tuple(seen)


def _effect_state(db: Session, world_id: str, key: object) -> AttributeView:
    view = attribute_view(db, world_id, key) if isinstance(key, str) else None
    if view is None or view.status != "active":
        raise ValueError(f"unknown state {key!r}")
    if view.system and view.key not in EFFECT_SYSTEM_KEYS:
        raise ValueError(f"« {view.name} » is the creator's alone: no event changes it")
    return view


def _effect_value(view: AttributeView, effect: EffectSpec, by_key: dict, role: RoleSpec) -> object:
    if effect.mode not in EVENT_EFFECT_MODES:
        raise ValueError(f"unknown effect mode {effect.mode!r}")
    if effect.mode == "add" and view.kind != "integer":
        raise ValueError(f"« {view.name} » is not a number: an effect sets it")
    if view.kind == "integer":
        if not isinstance(effect.value, int) or isinstance(effect.value, bool):
            raise ValueError(f"« {view.name} » takes an integer")
        return effect.value
    if view.kind == "choice":
        if effect.value not in dict(view.choices):
            raise ValueError(f"{effect.value!r} is no value of « {view.name} »")
        return effect.value
    other = by_key.get(normalize_surface(str(effect.value or "")))
    if other is None or other is role:
        raise ValueError(f"« {view.name} » names the entity of another role of the type")
    if not set(other.entity_types) & set(view.value_types):
        raise ValueError(f"the role « {other.name} » holds no entity « {view.name} » may name")
    return other.name


def _clean_effects(db: Session, world_id: str, roles: tuple[RoleSpec, ...],
                   effects: tuple[EffectSpec, ...]) -> tuple[EffectSpec, ...]:
    by_key = {normalize_surface(role.name): role for role in roles}
    if len(effects) > MAX_EFFECTS:
        raise ValueError(f"an event type has at most {MAX_EFFECTS} effects")
    seen: list[EffectSpec] = []
    for effect in effects:
        role = by_key.get(normalize_surface(str(effect.role or "")))
        if role is None:
            raise ValueError("an effect names one of the type's roles")
        if not role.entity_types:
            raise ValueError(f"the role « {role.name} » holds no entity: no state to change")
        view = _effect_state(db, world_id, effect.attribute)
        if view.holder_types is not None and not set(role.entity_types) & set(view.holder_types):
            raise ValueError(f"« {view.name} » applies to no entity the role « {role.name} » holds")
        clean = EffectSpec(role=role.name, attribute=view.key, value=_effect_value(view, effect, by_key, role),
                           mode=effect.mode)
        if any(s.role == clean.role and s.attribute == clean.attribute for s in seen):
            raise ValueError(f"the role « {role.name} » changes « {view.name} » twice")
        seen.append(clean)
    return tuple(seen)


def clean_event_type(db: Session, world_id: str, spec: EventTypeSpec, type_id: Optional[str] = None) -> EventTypeSpec:
    """`spec` as it will be written; raises `ValueError` on any violation.
    Writes nothing."""
    if spec.domain not in EVENT_DOMAINS:
        raise ValueError(f"unknown event domain {spec.domain!r}")
    roles = _clean_roles(world_entity_types(db, world_id), tuple(spec.roles))
    clean = EventTypeSpec(
        name=_clean_type_name(db, world_id, spec.name, type_id), domain=spec.domain, roles=roles,
        counts_quantity=bool(spec.counts_quantity), in_chronicle=bool(spec.in_chronicle),
        participants_secret=bool(spec.participants_secret), scopes=_clean_scopes(roles, tuple(spec.scopes)),
        effects=_clean_effects(db, world_id, roles, tuple(spec.effects)),
    )
    if type_id is not None:
        _clean_update(db, world_id, type_id, clean)
    elif any(role.id for role in clean.roles):
        raise ValueError("a new event type's roles carry no id")
    return clean


# --- what an existing type holds -------------------------------------------------

def _role_rows(db: Session, type_id: str) -> list[EventTypeRole]:
    return list(db.exec(select(EventTypeRole).where(EventTypeRole.type_id == type_id)
                        .order_by(EventTypeRole.position, EventTypeRole.id)).all())


def _type_leaves(db: Session, type_id: str) -> list[ConditionNode]:
    return list(db.exec(select(ConditionNode).where(
        ConditionNode.form == EVENT_FORM, ConditionNode.target_key == type_id)).all())


def _role_in_condition(db: Session, role_id: str) -> bool:
    leaf = db.exec(select(ConditionNode.id).where(
        ConditionNode.form == EVENT_FORM, ConditionNode.value == role_id)).first()
    found = db.exec(select(ConditionNodeFilter.id).where(ConditionNodeFilter.role_id == role_id)).first()
    return leaf is not None or found is not None


def _participants(db: Session, role_id: str) -> list[EventParticipant]:
    return list(db.exec(select(EventParticipant).where(EventParticipant.role_id == role_id)).all())


def _matched(rows: list[EventTypeRole], role: RoleSpec) -> Optional[EventTypeRole]:
    if role.id:
        return next((r for r in rows if r.id == role.id), None)
    return next((r for r in rows if normalize_surface(r.name) == normalize_surface(role.name)), None)


def _clean_kept_role(db: Session, row: EventTypeRole, role: RoleSpec) -> None:
    for participant in _participants(db, row.id):
        if participant.sorte_id and not role.accepts_sorte:
            raise ValueError(f"the role « {row.name} » is held by a sorte: it keeps accepting one")
        entity = db.get(Entity, participant.entity_id) if participant.entity_id else None
        if entity is not None and entity.type not in role.entity_types:
            raise ValueError(f"the role « {row.name} » is held by a {entity.type}: that type stays")


def _clean_update(db: Session, world_id: str, type_id: str, clean: EventTypeSpec) -> None:
    row = db.get(EventType, type_id)
    if row is None or row.world_id != world_id:
        raise ValueError(f"unknown event type {type_id!r}")
    rows = _role_rows(db, type_id)
    for role in clean.roles:
        if role.id and _matched(rows, role) is None:
            raise ValueError(f"unknown role {role.id!r}")
    kept = {matched.id for role in clean.roles if (matched := _matched(rows, role)) is not None}
    for row_role in rows:
        if row_role.id in kept:
            _clean_kept_role(db, row_role, next(r for r in clean.roles if _matched(rows, r) is row_role))
        elif row_role.status == "active" and (_participants(db, row_role.id) or _role_in_condition(db, row_role.id)):
            raise ValueError(f"the role « {row_role.name} » is in use: it stays")
    if not clean.counts_quantity and db.exec(select(Event.id).where(
            Event.type_id == type_id, Event.quantity.is_not(None))).first() is not None:
        raise ValueError(f"« {row.name} » has events with a quantity: it keeps counting")


# --- writing a type ---------------------------------------------------------------

def _write_roles(db: Session, world_id: str, type_id: str, clean: EventTypeSpec) -> dict[str, str]:
    """The roles, matched by id then name; returns name key -> role id."""
    rows = _role_rows(db, type_id)
    ids: dict[str, str] = {}
    kept: set[str] = set()
    for position, role in enumerate(clean.roles):
        row = _matched(rows, role)
        if row is None:
            row = EventTypeRole(world_id=world_id, type_id=type_id, name=role.name)
        row.name, row.position, row.accepts_sorte, row.status = role.name, position, role.accepts_sorte, "active"
        db.add(row)
        db.flush()
        kept.add(row.id)
        ids[normalize_surface(role.name)] = row.id
        db.execute(text("DELETE FROM event_type_role_type WHERE role_id = :rid"), {"rid": row.id})
        for entity_type in role.entity_types:
            db.add(EventTypeRoleType(world_id=world_id, role_id=row.id, entity_type=entity_type))
    for row in rows:
        if row.id not in kept and row.status != "retired":
            row.status = "retired"
            db.add(row)
    return ids


def _write_scopes(db: Session, world_id: str, type_id: str, clean: EventTypeSpec, ids: dict[str, str]) -> None:
    db.execute(text("DELETE FROM event_type_scope WHERE type_id = :tid"), {"tid": type_id})
    for scope in clean.scopes:
        role_id = ids[normalize_surface(scope.role)] if scope.role else None
        db.add(EventTypeScope(world_id=world_id, type_id=type_id, scope_kind=scope.kind, role_id=role_id,
                              level=scope.level))


def _write_effects(db: Session, world_id: str, type_id: str, clean: EventTypeSpec, ids: dict[str, str]) -> None:
    """The type's effects replaced whole: an effect pre-fills a proposal,
    nothing holds it."""
    db.execute(text("DELETE FROM event_type_effect WHERE type_id = :tid"), {"tid": type_id})
    for position, effect in enumerate(clean.effects):
        row = EventTypeEffect(world_id=world_id, type_id=type_id, role_id=ids[normalize_surface(effect.role)],
                              mode=effect.mode, position=position)
        if effect.attribute.startswith("sys:"):
            row.system_key = effect.attribute
        else:
            row.definition_id = effect.attribute
        kind = attribute_view(db, world_id, effect.attribute).kind
        if kind == "integer":
            row.integer_value = effect.value
        elif kind == "entity":
            row.value_role_id = ids[normalize_surface(effect.value)]
        elif row.system_key is not None:
            row.system_value = effect.value
        else:
            row.choice_id = effect.value
        db.add(row)


def write_event_type(
    db: Session, *, world_id: str, spec: EventTypeSpec, type_id: Optional[str] = None,
) -> EventType:
    """Create (`type_id` None) or save one event type after
    `clean_event_type`. Returns its row, flushed."""
    clean = clean_event_type(db, world_id, spec, type_id)
    if type_id is None:
        row = EventType(world_id=world_id, name=clean.name)
    else:
        row = db.get(EventType, type_id)
    row.name, row.domain = clean.name, clean.domain
    row.counts_quantity, row.in_chronicle = clean.counts_quantity, clean.in_chronicle
    row.participants_secret = clean.participants_secret
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    ids = _write_roles(db, world_id, row.id, clean)
    _write_scopes(db, world_id, row.id, clean, ids)
    _write_effects(db, world_id, row.id, clean, ids)
    db.flush()
    return row


def set_event_type_status(db: Session, *, world_id: str, type_id: str, status: str) -> EventType:
    """Retire or restore one type. Retiring is refused while a condition
    names it. Its events keep it: history is sacred."""
    if status not in EVENT_VOCAB_STATUSES:
        raise ValueError(f"unknown status {status!r}")
    row = db.get(EventType, type_id)
    if row is None or row.world_id != world_id:
        raise ValueError(f"unknown event type {type_id!r}")
    if status == "retired" and _type_leaves(db, type_id):
        raise ValueError(f"« {row.name} » is named by a condition: it cannot be retired")
    row.status = status
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    return row


# --- sortes ---------------------------------------------------------------------

def clean_sorte_name(db: Session, world_id: str, name: object, sorte_id: Optional[str] = None) -> str:
    """A sorte's name as it will be written; `ValueError` when it is empty,
    too long, or another sorte's of the world."""
    clean = _clean_label(name, "a sorte")
    key = normalize_surface(clean)
    for other in db.exec(select(EventSorte).where(EventSorte.world_id == world_id)).all():
        if other.id != sorte_id and normalize_surface(other.name) == key:
            raise ValueError(f"« {clean} » is already the name of « {other.name} »")
    return clean


def write_sorte(db: Session, *, world_id: str, name: str, sorte_id: Optional[str] = None) -> EventSorte:
    """Create or rename one sorte. Returns its row, flushed."""
    clean = clean_sorte_name(db, world_id, name, sorte_id)
    if sorte_id is None:
        row = EventSorte(world_id=world_id, name=clean)
    else:
        row = db.get(EventSorte, sorte_id)
        if row is None or row.world_id != world_id:
            raise ValueError(f"unknown sorte {sorte_id!r}")
        row.name = clean
    db.add(row)
    db.flush()
    return row


def set_sorte_status(db: Session, *, world_id: str, sorte_id: str, status: str) -> EventSorte:
    """Retire or restore one sorte; retiring is refused while a condition
    names it."""
    if status not in EVENT_VOCAB_STATUSES:
        raise ValueError(f"unknown status {status!r}")
    row = db.get(EventSorte, sorte_id)
    if row is None or row.world_id != world_id:
        raise ValueError(f"unknown sorte {sorte_id!r}")
    named = db.exec(select(ConditionNodeFilter.id).where(ConditionNodeFilter.sorte_id == sorte_id)).first()
    if status == "retired" and named is not None:
        raise ValueError(f"« {row.name} » is named by a condition: it cannot be retired")
    row.status = status
    db.add(row)
    db.flush()
    return row


# --- the type made from a domain (N1) -------------------------------------------

def ensure_domain_type(db: Session, *, world_id: str, domain: Optional[str]) -> EventType:
    """The world's type named after `domain` (an unknown or empty domain is
    `other`), created with one role « Impliqué » accepting every entity type
    of the world when the world has none of that name."""
    domain = domain if domain in EVENT_DOMAINS else "other"
    name = DOMAIN_LABELS_FR[domain]
    key = normalize_surface(name)
    for found in db.exec(select(EventType).where(EventType.world_id == world_id)).all():
        if normalize_surface(found.name) == key:
            return found
    role = RoleSpec(name=DOMAIN_ROLE_FR, entity_types=world_entity_types(db, world_id))
    return write_event_type(db, world_id=world_id, spec=EventTypeSpec(name=name, domain=domain, roles=(role,)))
