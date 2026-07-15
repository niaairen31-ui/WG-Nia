"""`relation` canon-write chokepoint (TICKET-0028, BRIEF-0028-b — decomposed
from `writes.py`).

- `_find_relation_pair(db, a, b)`      : both-directions first-match search
  for a `relation` row (TICKET-0024, BRIEF-0024-b) — the single source of
  pair semantics, shared by `write_relation(mode="delta")` and, outside
  this module, `_apply_mutation`'s `goal_change complete` prerequisite
  judge and the per-NPC tick briefing's prerequisite resolution.
- `write_relation(mode="delta", ...)`  : gameplay consequence. Find/create the
  relation by (a, b) pair, apply a clamped intensity delta, append the
  previous state to `change_history`. Used by `_apply_mutation`.
- `write_relation(mode="set", ...)`    : author CRUD. Set intensity to an
  absolute value on a specific row (or create a new edge). Updating an
  existing row appends its previous state to `change_history` first
  (history is sacred on both write paths); creating a new edge starts with
  an empty `change_history`, same as `mode="delta"`.

`_build_relation_delta`/`_build_relation_set` are pure builds (find-or-new,
in-memory mutation, no `db.add`) carved out of `write_relation` at this
brief so the function fits the 80-line cap (R7: new extractions, new
names). `write_relation` itself owns the single `db.add` call, so
`canon_write_policy.txt`'s `relation` site count doesn't change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from ..models import Relation
from ._shared import _append_history_snapshot, _clamp


def _find_relation_pair(db: Session, entity_a_id: str, entity_b_id: str) -> Optional[Relation]:
    """Both-directions first-match search for a `relation` row between two
    entities — the single source of pair semantics (TICKET-0024,
    BRIEF-0024-b). Shared by `write_relation(mode="delta")` and
    `_apply_mutation`'s `goal_change complete` prerequisite judge / the
    per-NPC tick briefing, so the judge and the briefing can never
    disagree with the write path about which row is "the" relation for a
    pair. No UNIQUE constraint enforces a single row per pair in schema,
    so this takes the first match if several exist (same design choice as
    the write path)."""
    return db.exec(
        select(Relation).where(
            ((Relation.entity_a_id == entity_a_id) & (Relation.entity_b_id == entity_b_id))
            | ((Relation.entity_a_id == entity_b_id) & (Relation.entity_b_id == entity_a_id))
        )
    ).first()


def _require_relation_fields(mode_label: str, *, entity_a_id, entity_b_id, world_id, type) -> None:
    if not entity_a_id or not entity_b_id or not world_id or not type:
        raise ValueError(
            f"write_relation(mode={mode_label!r}): entity_a_id, entity_b_id, "
            "world_id and type are required"
        )


def _build_relation_delta(
    db: Session, *, world_id, entity_a_id, entity_b_id, type, value, direction,
    visible_to_b, notes, mutation_id, now,
) -> Relation:
    """Pure build for `write_relation(mode="delta")` — find/create-or-update
    in memory. No `db.add`: the caller owns the single write site."""
    rel = _find_relation_pair(db, entity_a_id, entity_b_id)
    if rel is None:
        return Relation(
            world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
            type=type, direction=direction, intensity=_clamp(50 + value),
            visible_to_b=visible_to_b, notes=notes, change_history=[],
            created_at=now, last_evolved_at=now,
        )
    _append_history_snapshot(rel, mutation_id=mutation_id)
    rel.intensity = _clamp(rel.intensity + value)
    rel.last_evolved_at = now
    return rel


def _build_relation_set(
    db: Session, *, relation_id, world_id, entity_a_id, entity_b_id, type,
    value, direction, visible_to_b, notes, now,
) -> Relation:
    """Pure build for `write_relation(mode="set")` — same no-`db.add`
    discipline as `_build_relation_delta`."""
    if relation_id is not None:
        rel = db.get(Relation, relation_id)
        if rel is None:
            raise ValueError(f"write_relation(mode='set'): relation {relation_id!r} not found")
        _append_history_snapshot(rel, mutation_id=None)
        if type is not None:
            rel.type = type
        rel.direction = direction
        rel.visible_to_b = visible_to_b
        rel.notes = notes
        rel.intensity = _clamp(value)
        rel.last_evolved_at = now
        return rel

    _require_relation_fields(
        "set", entity_a_id=entity_a_id, entity_b_id=entity_b_id, world_id=world_id, type=type
    )
    return Relation(
        world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
        type=type, direction=direction, intensity=_clamp(value),
        visible_to_b=visible_to_b, notes=notes, change_history=[],
        created_at=now, last_evolved_at=now,
    )


def write_relation(
    db: Session,
    *,
    mode: str,
    relation_id: Optional[str] = None,
    world_id: Optional[str] = None,
    entity_a_id: Optional[str] = None,
    entity_b_id: Optional[str] = None,
    type: Optional[str] = None,
    value: int = 0,
    direction: str = "mutual",
    visible_to_b: bool = True,
    notes: Optional[str] = None,
    mutation_id: Optional[str] = None,
) -> Relation:
    """Write a `relation` row. Caller adds the row to the session — no,
    THIS function adds the row (the single sanctioned `relation` write
    site); the caller only commits.

    mode="delta" (gameplay consequence, `_apply_mutation`):
        Search both directions for an existing (entity_a_id, entity_b_id)
        pair; create one if none exists. `value` is an intensity delta,
        applied on top of the existing intensity (or 50 for a new relation),
        clamped to 1-100. The previous state is appended to
        `change_history` (history is sacred). `entity_a_id`, `entity_b_id`,
        `world_id` and `type` are required.

    mode="set" (author CRUD):
        `relation_id=None` creates a new edge with intensity = clamp(value)
        (`entity_a_id`, `entity_b_id`, `world_id`, `type` required); starts
        with an empty `change_history`, same as a new `mode="delta"` edge.
        `relation_id=<id>` updates that row in place: the previous state is
        appended to `change_history` first (history is sacred), then
        intensity is set to clamp(value); `type`, `direction`,
        `visible_to_b`, `notes` are overwritten.

    Clamp 1-100 is a backstop in both modes; CRUD callers should also
    validate the input range before calling this.
    """
    if mode not in ("delta", "set"):
        raise ValueError(f"write_relation: invalid mode {mode!r}")

    now = datetime.now(UTC)

    if mode == "delta":
        _require_relation_fields(
            "delta", entity_a_id=entity_a_id, entity_b_id=entity_b_id, world_id=world_id, type=type
        )
        rel = _build_relation_delta(
            db, world_id=world_id, entity_a_id=entity_a_id, entity_b_id=entity_b_id,
            type=type, value=value, direction=direction, visible_to_b=visible_to_b,
            notes=notes, mutation_id=mutation_id, now=now,
        )
    else:
        rel = _build_relation_set(
            db, relation_id=relation_id, world_id=world_id, entity_a_id=entity_a_id,
            entity_b_id=entity_b_id, type=type, value=value, direction=direction,
            visible_to_b=visible_to_b, notes=notes, now=now,
        )

    db.add(rel)
    return rel
