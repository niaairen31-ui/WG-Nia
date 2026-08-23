"""Read helpers for `npc_schedule` and the C1 time-relative position
resolution (TICKET-0074, BRIEF-0074-a).

Parallel to `observation_reads.py`: `writes/config.py::write_npc_schedule` is
the one write site, this module is the one read site. Nothing outside this
module reads `npc_schedule` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from sqlmodel import Session, select

from .models import Character, Entity, Gathering, GatheringMember, NpcSchedule, World

# C1 -- time-relative precedence. TWO branches, ONE accessor. The present
# is a set of FACTS (a roster, a stored location); a future phase is a set
# of PREDICTIONS, where a stored `current_location_id` is only a last
# known position and must NOT beat the schedule. A single total order
# (rejected C2) lets a stale fact win a phase three days out -- the exact
# failure this table exists to fix.
#
# C1 also named an `agenda_step` term in both branches. It is ABSENT here
# BY DESIGN, not deferred. An agenda states an OBJECTIVE, never a place --
# measured 2026-08-23: no location column on `AgendaStep`
# (models/canon.py:822), `Agenda` (:799) or `NpcGoal` (:495). That is the
# J1 taxonomy holding, not an omission. The schedule is the positional
# expression of a STANDING disposition; a volition has no positional
# expression, and giving it one would create a second positional
# authority competing with this table.
#
# An agenda's positional consequence already reaches this accessor: the
# tick moves the NPC, `_mutation_apply_npc_move` (cockpit/mutations.py)
# writes `current_location_id` through `write_character_location`, and
# the present branch reads that one term ABOVE the schedule. Predicting a
# FUTURE position from an agenda is the day-resolution chain's job (plan
# emission), explicitly Scope OUT of TICKET-0074 -- an agenda term in the
# future branch would be that chain leaking into a pure read.
#
# There is no reactivation condition on `agenda_step`. If positional
# prediction is ever needed, it comes from whatever the resolution chain
# emits, as a NEW named term -- never from an agenda.
#
# These tuples are the ONLY place a source may be named. `where_is`
# iterates them and dispatches through `_SOURCE_LOOKUPS`; it performs no
# lookup of its own. verify/checks/npc_schedule.py asserts the bijection
# between these names and that table's keys, and that `where_is`'s body
# contains no `select(` call.
PRESENT_PRECEDENCE: tuple[str, ...] = (
    "gathering", "current_location", "schedule", "unknown",
)
FUTURE_PRECEDENCE: tuple[str, ...] = (
    "schedule", "last_known", "unknown",
)


@dataclass(frozen=True)
class Resolution:
    npc_id: str
    phase: str
    location_id: Optional[str]
    source: str
    standing_goal_id: Optional[str] = None


# Each lookup takes (npc_id, phase, session) and returns None (no answer
# from this source) or a `(location_id, standing_goal_id)` pair.
# `standing_goal_id` is always None except for `_lookup_schedule`.
_LookupResult = Optional[tuple[str, Optional[str]]]


def _lookup_gathering(npc_id: str, phase: str, db: Session) -> _LookupResult:
    row = db.exec(
        select(Gathering)
        .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
        .where(
            GatheringMember.entity_id == npc_id,
            GatheringMember.left_at.is_(None),
            Gathering.status == "open",
            Gathering.dissolved_at.is_(None),
        )
    ).first()
    return (row.location_id, None) if row is not None else None


def _lookup_current_location(npc_id: str, phase: str, db: Session) -> _LookupResult:
    character = db.get(Character, npc_id)
    if character is None or character.current_location_id is None:
        return None
    return (character.current_location_id, None)


def _lookup_schedule(npc_id: str, phase: str, db: Session) -> _LookupResult:
    row = db.exec(
        select(NpcSchedule).where(NpcSchedule.npc_id == npc_id, NpcSchedule.phase == phase)
    ).first()
    return (row.location_id, row.standing_goal_id) if row is not None else None


def _lookup_unknown(npc_id: str, phase: str, db: Session) -> _LookupResult:
    return None


# T-D2 -- the TERMINAL TERM of both precedence orders, not an error branch.
_SOURCE_LOOKUPS: dict[str, Callable[[str, str, Session], _LookupResult]] = {
    "gathering": _lookup_gathering,
    "current_location": _lookup_current_location,
    "last_known": _lookup_current_location,
    "schedule": _lookup_schedule,
    "unknown": _lookup_unknown,
}


def where_is(npc_id: str, phase: str, db: Session, *, is_present: bool) -> Resolution:
    """C1's single accessor. Iterates the branch's precedence tuple and
    dispatches through `_SOURCE_LOOKUPS`; performs no lookup of its own.
    Never raises on the unresolved path (T-D2) -- `is_present` is an
    explicit argument, not derived here: the caller knows whether it is
    asking about now or about later, and this module has no clock."""
    order = PRESENT_PRECEDENCE if is_present else FUTURE_PRECEDENCE
    for name in order:
        if name == "unknown":
            return Resolution(npc_id=npc_id, phase=phase, location_id=None, source="unknown")
        result = _SOURCE_LOOKUPS[name](npc_id, phase, db)
        if result is not None:
            location_id, standing_goal_id = result
            return Resolution(
                npc_id=npc_id, phase=phase, location_id=location_id,
                source=name, standing_goal_id=standing_goal_id,
            )
    return Resolution(npc_id=npc_id, phase=phase, location_id=None, source="unknown")


def _active_npc_ids(db: Session) -> list[str]:
    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    if world is None:
        return []
    rows = db.exec(
        select(Character.id)
        .join(Entity, Entity.id == Character.id)
        .where(
            Character.world_id == world.id,
            Character.character_type == "npc",
            Character.vital_status == "alive",
            Entity.status == "active",
        )
    ).all()
    return list(rows)


def who_is_at(location_id: str, phase: str, db: Session, *, is_present: bool) -> list[str]:
    """NPCs `where_is` resolves to `location_id` at `phase`. Scoped to the
    ACTIVE world's alive, active NPCs. One resolution rule, two readers
    (this and `unresolved_npcs`); neither reimplements precedence."""
    return [
        npc_id
        for npc_id in _active_npc_ids(db)
        if where_is(npc_id, phase, db, is_present=is_present).location_id == location_id
    ]


def unresolved_npcs(phase: str, db: Session, *, is_present: bool) -> list[str]:
    """NPCs `where_is` resolves to `source == "unknown"` at `phase` — the
    F1 panel's compensating control for B1 (a sparse schedule table)."""
    return [
        npc_id
        for npc_id in _active_npc_ids(db)
        if where_is(npc_id, phase, db, is_present=is_present).source == "unknown"
    ]
