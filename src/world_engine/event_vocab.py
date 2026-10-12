"""The event journal's vocabulary, read (TICKET-0114, BRIEF-0114-A;
decisions B1, C1, D1, N1 and W1 of the conditions series).

A world's event types -- each with its roles in order, the entity types a
role accepts and whether a sorte may fill it, who learns an event of it --
and its sortes. Every surface that names an event type or a sorte reads
them here: the Création « Vocabulaire du monde » tab, the journal's sheet,
the `event` condition form, the interpreter, the play analyzer.

`near_event_types` / `near_sortes` find the names near a new one, so a
creator never makes « Tuer » twice as « tuer » (the WK2 rule of
TICKET-0113, `lore_resolve.near_ratio`).

`DOMAIN_LABELS_FR` names each domain in French; `DOMAIN_ROLE_FR` is the one
role of a type made from a domain (`writes.event_types.ensure_domain_type`,
and the v2.24 migration for the events written before it).

This module writes nothing; `writes/event_types.py` is its writer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .lore_resolve import near_ratio, near_score, normalize_surface
from .models import (
    EventSorte,
    EventType,
    EventTypeRole,
    EventTypeRoleType,
    EventTypeScope,
)

DOMAIN_LABELS_FR: dict[str, str] = {
    "political": "Politique", "magical": "Magique", "criminal": "Criminel", "military": "Militaire",
    "social": "Social", "mystery": "Mystère", "other": "Autre",
}
DOMAIN_ROLE_FR = "Impliqué"
# The condition form that counts events (BRIEF-0114-D); named here so the
# vocabulary's writer can tell which leaves name a type (`event_journal.py`
# keeps it in `condition_forms.REQUIREMENT_TYPES`).
EVENT_FORM = "event"


@dataclass(frozen=True)
class RoleView:
    id: str
    name: str
    position: int
    entity_types: tuple[str, ...]
    accepts_sorte: bool
    status: str


@dataclass(frozen=True)
class ScopeView:
    kind: str
    role_id: Optional[str]
    level: str


@dataclass(frozen=True)
class EventTypeView:
    id: str
    world_id: str
    name: str
    domain: str
    counts_quantity: bool
    in_chronicle: bool
    participants_secret: bool
    status: str
    roles: tuple[RoleView, ...]
    scopes: tuple[ScopeView, ...]

    def role(self, role_id: Optional[str]) -> Optional[RoleView]:
        return next((r for r in self.roles if r.id == role_id), None)

    def active_roles(self) -> tuple[RoleView, ...]:
        return tuple(r for r in self.roles if r.status == "active")


def role_accepts(role: RoleView, entity_type: Optional[str]) -> bool:
    """A role accepts an entity of `entity_type` when it names that type."""
    return entity_type is not None and entity_type in role.entity_types


def _roles(db: Session, type_id: str) -> tuple[RoleView, ...]:
    rows = db.exec(select(EventTypeRole).where(EventTypeRole.type_id == type_id)
                   .order_by(EventTypeRole.position, EventTypeRole.id)).all()
    views = []
    for row in rows:
        types = tuple(db.exec(select(EventTypeRoleType.entity_type).where(
            EventTypeRoleType.role_id == row.id).order_by(EventTypeRoleType.entity_type)).all())
        views.append(RoleView(row.id, row.name, row.position, types, row.accepts_sorte, row.status))
    return tuple(views)


def _scopes(db: Session, type_id: str) -> tuple[ScopeView, ...]:
    rows = db.exec(select(EventTypeScope).where(EventTypeScope.type_id == type_id)
                   .order_by(EventTypeScope.scope_kind, EventTypeScope.id)).all()
    return tuple(ScopeView(row.scope_kind, row.role_id, row.level) for row in rows)


def _view(db: Session, row: EventType) -> EventTypeView:
    return EventTypeView(
        id=row.id, world_id=row.world_id, name=row.name, domain=row.domain,
        counts_quantity=row.counts_quantity, in_chronicle=row.in_chronicle,
        participants_secret=row.participants_secret, status=row.status,
        roles=_roles(db, row.id), scopes=_scopes(db, row.id),
    )


def type_view(db: Session, type_id: Optional[str]) -> Optional[EventTypeView]:
    """One event type, its roles and scopes; None when there is none."""
    row = db.get(EventType, type_id) if type_id else None
    return _view(db, row) if row is not None else None


def world_event_types(db: Session, world_id: str, include_retired: bool = False) -> list[EventTypeView]:
    """A world's event types, by name; the retired ones only when asked."""
    query = select(EventType).where(EventType.world_id == world_id)
    if not include_retired:
        query = query.where(EventType.status == "active")
    rows = db.exec(query).all()
    return [_view(db, row) for row in sorted(rows, key=lambda r: (r.name.casefold(), r.id))]


def world_sortes(db: Session, world_id: str, include_retired: bool = False) -> list[EventSorte]:
    """A world's sortes, by name; the retired ones only when asked."""
    query = select(EventSorte).where(EventSorte.world_id == world_id)
    if not include_retired:
        query = query.where(EventSorte.status == "active")
    return sorted(db.exec(query).all(), key=lambda r: (r.name.casefold(), r.id))


@dataclass(frozen=True)
class NearName:
    id: str
    name: str
    score: int


def _near(rows, name: str, exclude_id: Optional[str]) -> tuple[NearName, ...]:
    target = normalize_surface(name or "")
    if not target:
        return ()
    found = []
    for row_id, row_name in rows:
        if row_id == exclude_id:
            continue
        ratio = near_ratio(target, row_name)
        if ratio is not None:
            found.append(NearName(row_id, row_name, near_score(ratio)))
    return tuple(sorted(found, key=lambda n: (-n.score, n.name.casefold(), n.id)))


def near_event_types(db: Session, world_id: str, name: str, exclude_id: Optional[str] = None) -> tuple[NearName, ...]:
    """The world's event types (retired included) whose name is near
    `name`, best first. For display: the creator picks, the tool never does."""
    return _near(((v.id, v.name) for v in world_event_types(db, world_id, include_retired=True)), name, exclude_id)


def near_sortes(db: Session, world_id: str, name: str, exclude_id: Optional[str] = None) -> tuple[NearName, ...]:
    """The world's sortes (retired included) whose name is near `name`."""
    return _near(((s.id, s.name) for s in world_sortes(db, world_id, include_retired=True)), name, exclude_id)
