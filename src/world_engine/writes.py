"""Shared canon-write primitives for `relation` and `knowledge`.

Both canon-write paths — the approval pipeline (`_apply_mutation` in
`cockpit/app.py`) and the author CRUD (`cockpit/crud.py`) — call these
functions so that clamping and field validation live in exactly one place.

- `write_relation(mode="delta", ...)`  : gameplay consequence. Find/create the
  relation by (a, b) pair, apply a clamped intensity delta, append the
  previous state to `change_history`. Used by `_apply_mutation`.
- `write_relation(mode="set", ...)`    : author CRUD. Set intensity to an
  absolute value on a specific row (or create a new edge). Writes no
  `change_history`.
- `write_knowledge(...)`               : insert or update a `knowledge` row.
  `knowledge_id=None` creates; otherwise updates that row in place.

Callers add the returned row to the session; neither function commits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from .models import Knowledge, Relation

# knowledge.level enum (world-engine-schema.md): unaware | rumor | suspicious |
# partial | knows | fully_understands.
KNOWLEDGE_LEVELS = frozenset(
    {"unaware", "rumor", "suspicious", "partial", "knows", "fully_understands"}
)


def _clamp(value: int, lo: int = 1, hi: int = 100) -> int:
    return max(lo, min(hi, int(value)))


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
    """Write a `relation` row. Caller adds the row to the session.

    mode="delta" (gameplay consequence, `_apply_mutation`):
        Search both directions for an existing (entity_a_id, entity_b_id)
        pair; create one if none exists. `value` is an intensity delta,
        applied on top of the existing intensity (or 50 for a new relation),
        clamped to 1-100. The previous state is appended to
        `change_history` (history is sacred). `entity_a_id`, `entity_b_id`,
        `world_id` and `type` are required.

    mode="set" (author CRUD):
        `relation_id=None` creates a new edge with intensity = clamp(value)
        (`entity_a_id`, `entity_b_id`, `world_id`, `type` required).
        `relation_id=<id>` updates that row in place: intensity is set to
        clamp(value); `type`, `direction`, `visible_to_b`, `notes` are
        overwritten. No `change_history` entry is written either way.

    Clamp 1-100 is a backstop in both modes; CRUD callers should also
    validate the input range before calling this.
    """
    if mode not in ("delta", "set"):
        raise ValueError(f"write_relation: invalid mode {mode!r}")

    now = datetime.now(UTC)

    if mode == "delta":
        if not entity_a_id or not entity_b_id or not world_id or not type:
            raise ValueError(
                "write_relation(mode='delta'): entity_a_id, entity_b_id, "
                "world_id and type are required"
            )

        # Search in both directions; take first match if several types exist.
        # Design choice: no UNIQUE constraint in schema on (a, b) pair, so we
        # take the first match. A future version could match by type too.
        rel = db.exec(
            select(Relation).where(
                ((Relation.entity_a_id == entity_a_id) & (Relation.entity_b_id == entity_b_id))
                | ((Relation.entity_a_id == entity_b_id) & (Relation.entity_b_id == entity_a_id))
            )
        ).first()

        if rel is None:
            rel = Relation(
                world_id=world_id,
                entity_a_id=entity_a_id,
                entity_b_id=entity_b_id,
                type=type,
                direction=direction,
                intensity=_clamp(50 + value),
                visible_to_b=visible_to_b,
                notes=notes,
                change_history=[],
                created_at=now,
                last_evolved_at=now,
            )
        else:
            # Append a snapshot of the previous state (history is sacred).
            history = list(rel.change_history or [])
            history.append({
                "intensity": rel.intensity,
                "last_evolved_at": rel.last_evolved_at.isoformat() if rel.last_evolved_at else None,
                "mutation_id": mutation_id,
            })
            rel.change_history = history
            # flag_modified ensures SQLAlchemy detects the JSON list change
            # even though we replaced the object (not mutated it in place).
            sa_attrs.flag_modified(rel, "change_history")
            rel.intensity = _clamp(rel.intensity + value)
            rel.last_evolved_at = now

        db.add(rel)
        return rel

    # mode == "set"
    if relation_id is not None:
        rel = db.get(Relation, relation_id)
        if rel is None:
            raise ValueError(f"write_relation(mode='set'): relation {relation_id!r} not found")
        if type is not None:
            rel.type = type
        rel.direction = direction
        rel.visible_to_b = visible_to_b
        rel.notes = notes
        rel.intensity = _clamp(value)
        rel.last_evolved_at = now
    else:
        if not entity_a_id or not entity_b_id or not world_id or not type:
            raise ValueError(
                "write_relation(mode='set'): entity_a_id, entity_b_id, "
                "world_id and type are required to create a relation"
            )
        rel = Relation(
            world_id=world_id,
            entity_a_id=entity_a_id,
            entity_b_id=entity_b_id,
            type=type,
            direction=direction,
            intensity=_clamp(value),
            visible_to_b=visible_to_b,
            notes=notes,
            change_history=[],
            created_at=now,
            last_evolved_at=now,
        )

    db.add(rel)
    return rel


def write_knowledge(
    db: Session,
    *,
    knowledge_id: Optional[str] = None,
    entity_id: Optional[str] = None,
    subject: Optional[str] = None,
    level: Optional[str] = None,
    content: Optional[Any] = None,
    source: Optional[Any] = None,
    is_incorrect: bool = False,
    is_secret: bool = False,
    share_threshold: int = 50,
    session_id: Optional[str] = None,
) -> Knowledge:
    """Insert or update a `knowledge` row. Caller adds the row to the session.

    `knowledge_id=None` inserts a new row (`entity_id`, `subject` and `level`
    required). Otherwise updates that row in place and bumps `updated_at`.

    `level` falls back to "rumor" if missing or outside `KNOWLEDGE_LEVELS` —
    matching the analyzer's existing default for model output that doesn't
    name a recognised level (the local model is not always reliable here;
    see CLAUDE.md "Local model notes"). `share_threshold` is clamped to
    1-100 (the DB CHECK constraint requires this regardless of `is_secret` —
    share_threshold is simply ignored at read time when `is_secret` is true).
    """
    norm_level = level if level in KNOWLEDGE_LEVELS else "rumor"
    threshold = _clamp(share_threshold)

    if knowledge_id is not None:
        k = db.get(Knowledge, knowledge_id)
        if k is None:
            raise ValueError(f"write_knowledge: knowledge {knowledge_id!r} not found")
        if subject is not None:
            k.subject = subject
        k.level = norm_level
        k.content = content
        k.source = source
        k.is_incorrect = bool(is_incorrect)
        k.is_secret = bool(is_secret)
        k.share_threshold = threshold
        k.updated_at = datetime.now(UTC)
    else:
        if not entity_id:
            raise ValueError("write_knowledge: entity_id is required to create")
        k = Knowledge(
            entity_id=entity_id,
            subject=subject or "unknown",
            level=norm_level,
            content=content,
            source=source,
            is_incorrect=bool(is_incorrect),
            is_secret=bool(is_secret),
            share_threshold=threshold,
            session_id=session_id,
        )

    db.add(k)
    return k


__all__ = ["write_relation", "write_knowledge", "KNOWLEDGE_LEVELS"]
