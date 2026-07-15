"""`npc_goal`/`goal_prerequisite`/`agenda`/`agenda_step`/`goal_agenda_link`
canon-write chokepoints (TICKET-0028, BRIEF-0028-b — decomposed from
`writes.py`). Pure moves, no logic change — none of these functions were
baselined.

- `write_npc_goal_prerequisites(...)`   : the only chokepoint for
  `goal_prerequisite` writes (TICKET-0024, BRIEF-0024-a; relationalized
  TICKET-0025, BRIEF-0025-c — replaces `npc_goal.prerequisites` JSON).
  Full-replace; validates the v1 `relation_gte` shape; snapshots the
  previous `goal_prerequisite` rows into `npc_goal.change_history` first —
  the audit trail location does not move.
- `write_npc_goal(...)`                 : insert an `active` `npc_goal` row
  (BRIEF-0013-a). `description` is immutable after insert — a "changed" goal
  is a closed goal plus a new row, never an edit.
- `write_npc_goal_status(...)`          : the only chokepoint for `npc_goal`
  status transitions (BRIEF-0013-a). Allowed transitions are exactly
  `active -> completed` and `active -> abandoned` — anything else (including
  reopening a closed goal) raises `ValueError`. Appends the previous state to
  `change_history` first (history is sacred).
- `write_agenda(...)`                   : insert an `active` `agenda` row
  (BRIEF-0018-a). A1 structural: `owner_entity_id` must resolve to an ACTIVE
  faction entity, else `ValueError`. The only constructor of `Agenda`.
- `write_agenda_step(...)`              : insert one `agenda_step` row
  (BRIEF-0018-a). The only constructor of `AgendaStep`.
- `write_agenda_step_status(...)`       : transition an `agenda_step`'s
  status (BRIEF-0018-a), appending the previous `{status, outcome,
  updated_at}` to `change_history` first — history is sacred.
- `write_agenda_status(...)`            : transition an `agenda`'s status
  (BRIEF-0018-a), same snapshot discipline; cascades onto linked goals
  (TICKET-0020, BRIEF-0020-a).
- `write_goal_agenda_link(...)`         : insert an ACTIVE `goal_agenda_link`
  row (TICKET-0020, BRIEF-0020-a). The only constructor of `GoalAgendaLink`.
- `detach_goal_agenda_link(...)`        : soft-detach a `goal_agenda_link`
  row (TICKET-0020, BRIEF-0020-a).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from ..models import Agenda, AgendaStep, Entity, GoalAgendaLink, GoalPrerequisite, NpcGoal

# npc_goal.horizon enum (world-engine-schema.md v1.69): short | long.
NPC_GOAL_HORIZONS = frozenset({"short", "long"})

# npc_goal.prerequisites[].type enum (schema v1.74, TICKET-0024, G1). v1 is a
# single type; expand only at a second concrete case.
NPC_GOAL_PREREQUISITE_TYPES = frozenset({"relation_gte"})


def write_npc_goal_prerequisites(
    db: Session,
    *,
    goal: NpcGoal,
    prerequisites: Optional[list],
    changed_by: str,
) -> NpcGoal:
    """Full-replace `goal_prerequisite` rows for one goal. Caller adds the
    goal row.

    v1 accepts ONLY `relation_gte` items: `{"type": "relation_gte",
    "target_entity_id": <entity id in the goal's own world>, "threshold":
    int 1-100}`. `None` or `[]` clears the gate — a completion with zero
    prerequisites is legitimate (A1). History is sacred: the previous
    `goal_prerequisite` rows are snapshotted into `npc_goal.change_history`
    first — the audit trail location does not move even though the live
    data does.
    """
    clean: list[dict] = []
    if prerequisites:
        for item in prerequisites:
            item_type = item.get("type") if isinstance(item, dict) else None
            if item_type not in NPC_GOAL_PREREQUISITE_TYPES:
                raise ValueError(
                    f"write_npc_goal_prerequisites: unknown prerequisite type {item_type!r}"
                )
            target_entity_id = item.get("target_entity_id")
            target = db.get(Entity, target_entity_id) if target_entity_id else None
            if target is None or target.world_id != goal.world_id:
                raise ValueError(
                    f"write_npc_goal_prerequisites: unknown target entity {target_entity_id!r}"
                )
            threshold = item.get("threshold")
            if (
                not isinstance(threshold, int)
                or isinstance(threshold, bool)
                or not (1 <= threshold <= 100)
            ):
                raise ValueError(
                    f"write_npc_goal_prerequisites: threshold must be an int 1-100, got {threshold!r}"
                )
            clean.append({
                "type": "relation_gte",
                "target_entity_id": target_entity_id,
                "threshold": threshold,
            })

    existing_rows = db.exec(
        select(GoalPrerequisite).where(GoalPrerequisite.goal_id == goal.id)
    ).all()
    history = list(goal.change_history or [])
    history.append({
        "prerequisites": [
            {"type": row.type, "target_entity_id": row.target_entity_id, "threshold": row.threshold}
            for row in existing_rows
        ] or None,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        "changed_by": changed_by,
    })
    goal.change_history = history
    sa_attrs.flag_modified(goal, "change_history")
    goal.updated_at = datetime.now(UTC)
    db.add(goal)

    db.execute(text("DELETE FROM goal_prerequisite WHERE goal_id = :goal_id"), {"goal_id": goal.id})
    for item in clean:
        row = GoalPrerequisite(
            world_id=goal.world_id, goal_id=goal.id, type=item["type"],
            target_entity_id=item["target_entity_id"], threshold=item["threshold"],
        )
        db.add(row)

    return goal


def write_npc_goal(
    db: Session,
    *,
    world_id: str,
    npc_id: str,
    description: str,
    horizon: str,
    changed_by: str = "creator",
) -> NpcGoal:
    """Insert an `active` `npc_goal` row. Caller adds the row to the session.

    `description` is immutable after insert — a "changed" goal is a closed
    goal (`write_npc_goal_status`) plus a new row via this function, never an
    in-place edit. `change_history` starts empty on insert, matching
    `write_knowledge`'s idiom; `changed_by` is accepted for call-site
    symmetry with `write_npc_goal_status` but has nothing to attribute on a
    fresh row.
    """
    if horizon not in NPC_GOAL_HORIZONS:
        raise ValueError(f"write_npc_goal: invalid horizon {horizon!r}")

    goal = NpcGoal(
        world_id=world_id,
        npc_id=npc_id,
        description=description,
        horizon=horizon,
        status="active",
        change_history=[],
    )
    db.add(goal)
    return goal


def write_npc_goal_status(
    db: Session,
    *,
    goal: NpcGoal,
    new_status: str,
    changed_by: str,
    extra: Optional[dict] = None,
) -> NpcGoal:
    """Transition `goal.status`. Caller adds the row to the session.

    The ONLY chokepoint for `npc_goal` status transitions. Allowed
    transitions are exactly `active -> completed` and `active -> abandoned` —
    any other transition (including reopening a closed goal) raises
    `ValueError`: a revived goal is a NEW row via `write_npc_goal`, never a
    reopened one. Appends the previous state to `change_history` first
    (history is sacred), then sets `status` and bumps `updated_at`.

    `extra` (TICKET-0024, BRIEF-0024-c) merges additional keys into that
    SAME snapshot entry — e.g. `no_footprint: True` or `stripped: [...]`
    on a `complete` — rather than opening a second write path for
    completion-event metadata.
    """
    if goal.status != "active" or new_status not in ("completed", "abandoned"):
        raise ValueError(
            f"write_npc_goal_status: invalid transition {goal.status!r} -> {new_status!r}"
        )

    entry = {
        "status": goal.status,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
        "changed_by": changed_by,
    }
    if extra:
        entry.update(extra)
    history = list(goal.change_history or [])
    history.append(entry)
    goal.change_history = history
    sa_attrs.flag_modified(goal, "change_history")
    goal.status = new_status
    goal.updated_at = datetime.now(UTC)

    db.add(goal)
    return goal


def write_agenda(
    db: Session,
    *,
    world_id: str,
    owner_entity_id: str,
    title: str,
    mutation_id: Optional[str] = None,
) -> Agenda:
    """Insert an `active` `agenda` row (TICKET-0018, BRIEF-0018-a; owner
    unlock TICKET-0020, BRIEF-0020-a).

    The ONLY constructor of `Agenda` in gameplay code — both sanctioned
    canon-write paths (`_apply_mutation`'s `agenda_creation` branch and the
    creator CRUD) call this. `owner_entity_id` must resolve to an ACTIVE
    `entity` of `type` in `{"faction", "character"}` in `world_id` —
    anything else (including a missing owner) raises `ValueError`. Faction
    owners keep their multi-agenda freedom, unchanged. A `character` owner
    may hold AT MOST ONE active agenda — the one-active-personal-agenda
    invariant, enforced here (the sole canon-write path) by an explicit
    existence check. Location owners stay rejected (A2/A3 deferred).
    `mutation_id` is accepted only for call-site symmetry with the other
    `_apply_mutation` writers and is not otherwise used here.
    """
    del mutation_id
    owner = db.get(Entity, owner_entity_id)
    if owner is None or owner.world_id != world_id:
        raise ValueError(f"write_agenda: owner {owner_entity_id!r} not found in world {world_id!r}")
    if owner.type not in ("faction", "character") or owner.status != "active":
        raise ValueError(f"write_agenda: owner {owner_entity_id!r} is not an active faction or character")
    if owner.type == "character":
        existing = db.exec(
            select(Agenda).where(
                Agenda.owner_entity_id == owner_entity_id,
                Agenda.status == "active",
            )
        ).first()
        if existing is not None:
            raise ValueError("write_agenda: character owner already holds an active agenda")

    agenda = Agenda(
        world_id=world_id,
        owner_entity_id=owner_entity_id,
        title=title,
        status="active",
        change_history=[],
    )
    db.add(agenda)
    return agenda


def write_agenda_step(
    db: Session,
    *,
    agenda_id: str,
    step_order: int,
    objective: str,
    visibility_trace: Optional[str] = None,
    status: str = "pending",
) -> AgendaStep:
    """Insert one `agenda_step` row (TICKET-0018, BRIEF-0018-a).

    The ONLY constructor of `AgendaStep` in gameplay code. `status="active"`
    is passed by the caller for exactly one step per agenda (the first, at
    creation time — the partial unique index enforces this structurally);
    every other step is created `pending`.
    """
    step = AgendaStep(
        agenda_id=agenda_id,
        step_order=step_order,
        objective=objective,
        visibility_trace=visibility_trace,
        status=status,
        change_history=[],
    )
    db.add(step)
    return step


def write_agenda_step_status(
    db: Session,
    *,
    step: AgendaStep,
    status: str,
    outcome: Optional[str] = None,
    mutation_id: Optional[str] = None,
    extra: Optional[dict] = None,
) -> AgendaStep:
    """Transition `step.status` (TICKET-0018, BRIEF-0018-a).

    Appends the previous `{status, outcome, updated_at}` to `change_history`
    BEFORE overwriting (`write_npc_goal_status` discipline) — history is
    sacred. Sets `outcome` only when provided, leaving any existing outcome
    untouched otherwise. `mutation_id` is accepted only for call-site
    symmetry with the other `_apply_mutation` writers and is not otherwise
    used here.

    `extra` (TICKET-0024, BRIEF-0024-c) merges additional keys into that
    SAME snapshot entry — e.g. `no_footprint: True` on a `complete` — same
    idiom as `write_npc_goal_status`.
    """
    del mutation_id
    entry = {
        "status": step.status,
        "outcome": step.outcome,
        "updated_at": step.updated_at.isoformat() if step.updated_at else None,
    }
    if extra:
        entry.update(extra)
    history = list(step.change_history or [])
    history.append(entry)
    step.change_history = history
    sa_attrs.flag_modified(step, "change_history")
    step.status = status
    if outcome is not None:
        step.outcome = outcome
    step.updated_at = datetime.now(UTC)

    db.add(step)
    return step


def write_goal_agenda_link(
    db: Session,
    *,
    world_id: str,
    goal_id: str,
    agenda_id: str,
    created_by: str,
    mutation_id: Optional[str] = None,
) -> GoalAgendaLink:
    """Insert an ACTIVE `goal_agenda_link` row (TICKET-0020, BRIEF-0020-a).

    The ONLY constructor of `GoalAgendaLink` in gameplay code. Validates:
    the goal exists, belongs to `world_id`, and is `active`; the agenda
    exists, belongs to `world_id`, and is `active`; no ACTIVE link already
    exists for this exact pair (explicit query — a clearer error than the
    partial-unique-index violation). `mutation_id` is accepted only for
    call-site symmetry with the other `_apply_mutation` writers and is not
    otherwise used here.
    """
    del mutation_id
    goal = db.get(NpcGoal, goal_id)
    if goal is None or goal.world_id != world_id:
        raise ValueError(f"write_goal_agenda_link: goal {goal_id!r} not found in world {world_id!r}")
    if goal.status != "active":
        raise ValueError(f"write_goal_agenda_link: goal {goal_id!r} is not active")

    agenda = db.get(Agenda, agenda_id)
    if agenda is None or agenda.world_id != world_id:
        raise ValueError(f"write_goal_agenda_link: agenda {agenda_id!r} not found in world {world_id!r}")
    if agenda.status != "active":
        raise ValueError(f"write_goal_agenda_link: agenda {agenda_id!r} is not active")

    existing = db.exec(
        select(GoalAgendaLink).where(
            GoalAgendaLink.goal_id == goal_id,
            GoalAgendaLink.agenda_id == agenda_id,
            GoalAgendaLink.detached_at.is_(None),
        )
    ).first()
    if existing is not None:
        raise ValueError("write_goal_agenda_link: an active link already exists for this goal/agenda pair")

    link = GoalAgendaLink(
        world_id=world_id,
        goal_id=goal_id,
        agenda_id=agenda_id,
        created_by=created_by,
    )
    db.add(link)
    return link


def detach_goal_agenda_link(
    db: Session,
    *,
    link: GoalAgendaLink,
    detached_by: str,
) -> GoalAgendaLink:
    """Soft-detach a `goal_agenda_link` row (TICKET-0020, BRIEF-0020-a).

    Sets `detached_at`/`detached_by`. Raises `ValueError` if already
    detached. There is NO delete helper — soft detach is the only exit; a
    detached pair may be re-attached via `write_goal_agenda_link` (the
    partial unique index allows it).
    """
    if link.detached_at is not None:
        raise ValueError("detach_goal_agenda_link: link is already detached")

    link.detached_at = datetime.now(UTC)
    link.detached_by = detached_by

    db.add(link)
    return link


# agenda status -> npc_goal status, cascade mapping (E2+M1, TICKET-0020,
# BRIEF-0020-a). The goal vocabulary has no 'failed' — both non-completed
# exits collapse to 'abandoned'.
_AGENDA_GOAL_CASCADE_MAP = {
    "completed": "completed",
    "failed": "abandoned",
    "abandoned": "abandoned",
}


def _cascade_agenda_status_to_goals(
    db: Session, agenda: Agenda, goal_status: str, agenda_status: str,
) -> None:
    """Cascade an agenda status transition onto every goal linked to it
    (ACTIVE link, i.e. `detached_at IS NULL`): an `active` goal whose link
    to THIS agenda is its last still-active parent transitions via
    `write_npc_goal_status`; a goal with another active link to a
    still-active agenda survives (last-parent rule). Links are never
    detached by the cascade — the historical tie stays readable."""
    active_links = db.exec(
        select(GoalAgendaLink).where(
            GoalAgendaLink.agenda_id == agenda.id,
            GoalAgendaLink.detached_at.is_(None),
        )
    ).all()
    for link in active_links:
        goal = db.get(NpcGoal, link.goal_id)
        if goal is None or goal.status != "active":
            continue
        other_active_links = db.exec(
            select(GoalAgendaLink).where(
                GoalAgendaLink.goal_id == goal.id,
                GoalAgendaLink.agenda_id != agenda.id,
                GoalAgendaLink.detached_at.is_(None),
            )
        ).all()
        has_other_active_parent = any(
            (other_agenda := db.get(Agenda, other.agenda_id)) is not None
            and other_agenda.status == "active"
            for other in other_active_links
        )
        if has_other_active_parent:
            continue
        write_npc_goal_status(
            db,
            goal=goal,
            new_status=goal_status,
            changed_by=f"cascade:agenda:{agenda.id}:{agenda_status}",
        )


def write_agenda_status(
    db: Session,
    *,
    agenda: Agenda,
    status: str,
    mutation_id: Optional[str] = None,
) -> Agenda:
    """Transition `agenda.status` (TICKET-0018, BRIEF-0018-a; cascade
    TICKET-0020, BRIEF-0020-a).

    Same snapshot discipline as `write_agenda_step_status`: appends the
    previous `{status, updated_at}` to `change_history` before overwriting.
    `mutation_id` is accepted only for call-site symmetry and is not
    otherwise used here. Runs identically for tick-approved transitions and
    creator CRUD overrides (both route through this helper). See
    `_cascade_agenda_status_to_goals` for the goal-cascade rule.
    """
    del mutation_id
    was_active = agenda.status == "active"
    history = list(agenda.change_history or [])
    history.append({
        "status": agenda.status,
        "updated_at": agenda.updated_at.isoformat() if agenda.updated_at else None,
    })
    agenda.change_history = history
    sa_attrs.flag_modified(agenda, "change_history")
    agenda.status = status
    agenda.updated_at = datetime.now(UTC)

    db.add(agenda)

    goal_status = _AGENDA_GOAL_CASCADE_MAP.get(status)
    if was_active and goal_status is not None:
        _cascade_agenda_status_to_goals(db, agenda, goal_status, status)

    return agenda
