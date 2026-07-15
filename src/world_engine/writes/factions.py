"""`faction_membership`/`faction_role` canon-write chokepoints (TICKET-0028,
BRIEF-0028-b — decomposed from `writes.py`).

- `write_membership(mode="open"/"close", ...)` : the only chokepoint for
  `faction_membership` writes (BRIEF-27). Creator CRUD only — no
  `_apply_mutation` branch exists for this table this step. INSERT-only /
  close-only: never updates `role` / `is_secret` / `faction_id` /
  `is_primary` of an existing row. A role or primary change is close + open
  a fresh row — the closed-row sequence IS the history, by construction
  (no `change_history` column on `faction_membership`).

  Modes are no longer "creator CRUD only" (schema v1.74, TICKET-0024):
  `_apply_mutation`'s `role_change` completion effect (BRIEF-0024-c) is
  the second sanctioned caller — it closes the subject's current
  membership and opens a fresh one with the new role, same close+reopen
  discipline, no third path.

  `cover_role` (schema v1.41, BRIEF-30): the prompt-facing façade role,
  set at open time only. Like `role`, changing it on an existing
  membership is close + reopen — no in-place update.

- `write_faction_role(...)`             : the only chokepoint for
  `faction_role` writes (TICKET-0024, BRIEF-0024-d — corrective, replaces
  `write_faction_role_capacities`). `mode="create"` / `"update"` / `"rename"`
  / `"delete"`; case-duplicate names are the unique index's job (caught as
  `IntegrityError`, re-raised as `ValueError`); `mode="rename"` realigns
  every ACTIVE membership whose true `role` casefold-matches the old name
  (close + reopen, T1); `mode="delete"` (S1) is a hard delete, blocked while
  any active membership still holds the role. No `change_history` (curated
  config, same family as `faction_type` / `philosophy`).

`_build_faction_role_create`, `_get_faction_role_or_raise`,
`_apply_faction_role_update`, `_realign_faction_role_holders` and
`_count_active_faction_role_holders` are pure-computation extractions
carved out of `write_faction_role` at this brief (R7) so the function fits
the 80-line cap. `write_faction_role` itself owns every `db.add`/
`db.delete` call on `FactionRole`, so `canon_write_policy.txt`'s
`faction_role` site count doesn't change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..models import FactionMembership, FactionRole


def write_membership(
    db: Session,
    *,
    mode: str,
    membership_id: Optional[str] = None,
    world_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    faction_id: Optional[str] = None,
    role: Optional[str] = None,
    cover_role: Optional[str] = None,
    is_primary: bool = False,
    is_secret: bool = False,
) -> FactionMembership:
    """Write a `faction_membership` row. Caller adds the row to the session.

    mode="open":
        Inserts a new row (`world_id`, `entity_id`, `faction_id` required).
        Setting `is_primary=True` while another active primary exists for
        this `entity_id`, or opening a second active membership in the same
        faction, violates a partial unique index
        (`idx_membership_one_primary` / `idx_membership_unique_active`) —
        the resulting `IntegrityError` propagates to the caller, which must
        surface it as an error, never silently demote the existing row.

    mode="close":
        Sets `left_at` on `membership_id`. Never touches `role` /
        `cover_role` / `is_secret` / `faction_id` / `is_primary`. Closing an
        already-closed row is a no-op (idempotent), not an error.
    """
    if mode not in ("open", "close"):
        raise ValueError(f"write_membership: invalid mode {mode!r}")

    if mode == "open":
        if not world_id or not entity_id or not faction_id:
            raise ValueError(
                "write_membership(mode='open'): world_id, entity_id and "
                "faction_id are required"
            )
        membership = FactionMembership(
            world_id=world_id,
            entity_id=entity_id,
            faction_id=faction_id,
            role=role,
            cover_role=cover_role,
            is_primary=is_primary,
            is_secret=is_secret,
        )
        db.add(membership)
        return membership

    # mode == "close"
    if not membership_id:
        raise ValueError("write_membership(mode='close'): membership_id is required")
    membership = db.get(FactionMembership, membership_id)
    if membership is None:
        raise ValueError(f"write_membership(mode='close'): membership {membership_id!r} not found")
    if membership.left_at is None:
        membership.left_at = datetime.now(UTC)
        db.add(membership)
    return membership


def _validate_max_holders(max_holders: Optional[int]) -> None:
    if max_holders is not None and (
        not isinstance(max_holders, int) or isinstance(max_holders, bool) or max_holders < 1
    ):
        raise ValueError("write_faction_role: max_holders must be null or an int >= 1")


def _faction_role_next_position(db: Session, faction_id: str) -> int:
    current_max = db.exec(
        select(func.max(FactionRole.position)).where(FactionRole.faction_id == faction_id)
    ).first()
    return (current_max or 0) + 1


def _build_faction_role_create(
    db: Session, *, world_id: Optional[str], faction_id: Optional[str],
    name: Optional[str], description: Optional[str], max_holders: Optional[int],
    position: Optional[int], changed_by: str,
) -> FactionRole:
    """Pure build (+ a default-position read query) for mode="create" — no
    `db.add`."""
    if not world_id or not faction_id:
        raise ValueError("write_faction_role(mode='create'): world_id and faction_id are required")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("write_faction_role(mode='create'): name must be a non-empty string")
    _validate_max_holders(max_holders)
    if position is None:
        position = _faction_role_next_position(db, faction_id)
    return FactionRole(
        world_id=world_id, faction_id=faction_id, name=name.strip(),
        description=description, max_holders=max_holders, position=position,
        created_by=changed_by,
    )


def _get_faction_role_or_raise(db: Session, mode: str, role_id: Optional[str]) -> FactionRole:
    if not role_id:
        raise ValueError(f"write_faction_role(mode={mode!r}): role_id is required")
    role = db.get(FactionRole, role_id)
    if role is None:
        raise ValueError(f"write_faction_role(mode={mode!r}): role {role_id!r} not found")
    return role


def _apply_faction_role_update(
    role: FactionRole, *, description: Optional[str], max_holders: Optional[int],
    position: Optional[int],
) -> None:
    """Mutates `role` in place for mode="update" — caller owns `db.add`.
    Always sets description/max_holders to whatever the caller sends (the
    editor row carries full state, so None is meaningful); position is set
    only when given (the dedicated reorder route is the only caller that
    passes it)."""
    _validate_max_holders(max_holders)
    role.description = description
    role.max_holders = max_holders
    if position is not None:
        role.position = position


def _realign_faction_role_holders(db: Session, role: FactionRole, old_name: str) -> None:
    """T1 realignment for mode="rename": close + reopen every ACTIVE
    membership whose true `role` casefold-matches the OLD name, preserving
    `cover_role`/`is_primary`/`is_secret`. Closed membership rows keep the
    old string untouched — history is never rewritten. Calls
    `write_membership` (its own sanctioned `db.add` sites)."""
    holders = db.exec(
        select(FactionMembership).where(
            FactionMembership.faction_id == role.faction_id,
            FactionMembership.left_at.is_(None),
        )
    ).all()
    for m in holders:
        if (m.role or "").casefold() != old_name.casefold():
            continue
        write_membership(db, mode="close", membership_id=m.id)
        write_membership(
            db, mode="open", world_id=m.world_id, entity_id=m.entity_id,
            faction_id=m.faction_id, role=role.name, cover_role=m.cover_role,
            is_primary=m.is_primary, is_secret=m.is_secret,
        )


def _count_active_faction_role_holders(db: Session, role: FactionRole) -> int:
    holders = db.exec(
        select(FactionMembership).where(
            FactionMembership.faction_id == role.faction_id,
            FactionMembership.left_at.is_(None),
        )
    ).all()
    return sum(1 for m in holders if (m.role or "").casefold() == role.name.casefold())


def write_faction_role(
    db: Session,
    *,
    mode: str,
    role_id: Optional[str] = None,
    world_id: Optional[str] = None,
    faction_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    max_holders: Optional[int] = None,
    position: Optional[int] = None,
    changed_by: str = "creator",
) -> Optional[FactionRole]:
    """Write a `faction_role` row. Caller adds the row (or, for
    `mode="delete"`, owns the commit of the deletion) — this function is
    the sole `faction_role` write site: create/update/rename add; delete
    hard-deletes. See module docstring for the per-mode contract.
    """
    if mode not in ("create", "update", "rename", "delete"):
        raise ValueError(f"write_faction_role: invalid mode {mode!r}")

    if mode == "create":
        role = _build_faction_role_create(
            db, world_id=world_id, faction_id=faction_id, name=name,
            description=description, max_holders=max_holders, position=position,
            changed_by=changed_by,
        )
        db.add(role)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                f"faction_role: a role named {name.strip()!r} already exists for this faction"
            ) from exc
        return role

    # mode in ("update", "rename", "delete") — role_id is required, row must exist.
    role = _get_faction_role_or_raise(db, mode, role_id)

    if mode == "update":
        _apply_faction_role_update(role, description=description, max_holders=max_holders, position=position)
        db.add(role)
        return role

    if mode == "rename":
        if not isinstance(name, str) or not name.strip():
            raise ValueError("write_faction_role(mode='rename'): name must be a non-empty string")
        old_name = role.name
        role.name = name.strip()
        db.add(role)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(
                f"faction_role: a role named {name.strip()!r} already exists for this faction"
            ) from exc
        _realign_faction_role_holders(db, role, old_name)
        return role

    # mode == "delete"
    count = _count_active_faction_role_holders(db, role)
    if count > 0:
        raise ValueError(f"faction_role: {count} active member(s) still hold {role.name!r}")
    db.delete(role)
    return None
