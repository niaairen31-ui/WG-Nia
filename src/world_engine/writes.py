"""Shared canon-write primitives for `relation` and `knowledge`.

Both canon-write paths — the approval pipeline (`_apply_mutation` in
`cockpit/app.py`) and the author CRUD (`cockpit/crud.py`) — call these
functions so that clamping and field validation live in exactly one place.

- `write_relation(mode="delta", ...)`  : gameplay consequence. Find/create the
  relation by (a, b) pair, apply a clamped intensity delta, append the
  previous state to `change_history`. Used by `_apply_mutation`.
- `write_relation(mode="set", ...)`    : author CRUD. Set intensity to an
  absolute value on a specific row (or create a new edge). Updating an
  existing row appends its previous state to `change_history` first
  (history is sacred on both write paths); creating a new edge starts with
  an empty `change_history`, same as `mode="delta"`.
- `write_knowledge(...)`               : insert or update a `knowledge` row.
  `knowledge_id=None` creates; otherwise updates that row in place, appending
  the previous state to `change_history` first (history is sacred on this
  path too — see `_append_knowledge_history`).
- `write_ledger_entry(...)`             : pure INSERT into the append-only
  `ledger` table (BRIEF-18). No UPDATE, no DELETE, ever — a correction is a
  new compensating line. The single chokepoint for ledger writes, shared by
  the creator CRUD and `_apply_mutation`'s `resource_change` branch
  (BRIEF-19) so the two paths cannot diverge.

Callers add the returned row to the session; neither function commits.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from .models import Knowledge, Ledger, Relation

# knowledge.level enum (world-engine-schema.md): unaware | rumor | suspicious |
# partial | knows | fully_understands.
KNOWLEDGE_LEVELS = frozenset(
    {"unaware", "rumor", "suspicious", "partial", "knows", "fully_understands"}
)

# Ordered ladder, lowest to highest. Shared by the analyzer (overhearing /
# direct-affirmation upgrade detection) and `_apply_mutation`'s monotone
# guard for `knowledge_change` — one source of truth for level ordering.
KNOWLEDGE_LEVEL_LADDER: tuple[str, ...] = (
    "unaware", "rumor", "suspicious", "partial", "knows", "fully_understands",
)


def knowledge_level_rank(level: Optional[str]) -> int:
    """Return `level`'s position on `KNOWLEDGE_LEVEL_LADDER`, or -1 if unrecognised.

    An unrecognised level ranks below 'unaware' so it can never satisfy a
    monotone "target > existing" check — invalid levels fail safe.
    """
    try:
        return KNOWLEDGE_LEVEL_LADDER.index(level)
    except ValueError:
        return -1


def cap_knowledge_level(level: str, cap: str = "knows") -> str:
    """Clamp `level` to at most `cap` on the ladder.

    Direct-affirmation rule: a target level is never granted above `cap`
    (default `knows`) by hearsay — `fully_understands` is creator CRUD only.
    """
    if knowledge_level_rank(level) > knowledge_level_rank(cap):
        return cap
    return level


def _clamp(value: int, lo: int = 1, hi: int = 100) -> int:
    return max(lo, min(hi, int(value)))


def _append_history_snapshot(rel: Relation, mutation_id: Optional[str] = None) -> None:
    """Append a snapshot of `rel`'s current state to its `change_history`.

    Shared by both `write_relation` modes — history is sacred on either
    write path (delta or set). `mutation_id` is None for author-CRUD edits
    (no `proposed_mutation` row is involved).
    """
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


def _append_knowledge_history(row: Knowledge, changed_by: str) -> None:
    """Append a snapshot of `row`'s PREVIOUS state to its `change_history`.

    Called before any overwrite of an existing `knowledge` row — history is
    sacred on every write path that updates `knowledge` (creator CRUD via
    `write_knowledge`; `knowledge_change` apply in `_apply_mutation`).
    `changed_by` is `"creator_crud"` or `"apply_mutation"`.
    """
    history = list(row.change_history or [])
    history.append({
        "level": row.level,
        "content": row.content,
        "source": row.source,
        "is_incorrect": row.is_incorrect,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "changed_by": changed_by,
        "changed_at": datetime.now(UTC).isoformat(),
    })
    row.change_history = history
    # flag_modified ensures SQLAlchemy detects the JSON list change
    # even though we replaced the object (not mutated it in place).
    sa_attrs.flag_modified(row, "change_history")


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
            _append_history_snapshot(rel, mutation_id=mutation_id)
            rel.intensity = _clamp(rel.intensity + value)
            rel.last_evolved_at = now

        db.add(rel)
        return rel

    # mode == "set"
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
    changed_by: str = "creator_crud",
) -> Knowledge:
    """Insert or update a `knowledge` row. Caller adds the row to the session.

    `knowledge_id=None` inserts a new row (`entity_id`, `subject` and `level`
    required); `change_history` starts empty. Otherwise updates that row in
    place and bumps `updated_at` — the previous state is appended to
    `change_history` first (history is sacred), tagged with `changed_by`
    (`"creator_crud"` or `"apply_mutation"`).

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
        _append_knowledge_history(k, changed_by=changed_by)
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


def write_ledger_entry(
    db: Session,
    *,
    world_id: str,
    entity_id: str,
    amount: int,
    counterparty_id: Optional[str] = None,
    reason: Optional[str] = None,
    source_type: str = "creator",
    conversation_id: Optional[str] = None,
    pass_play_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Ledger:
    """Insert one `ledger` row. Caller adds the row to the session.

    Pure INSERT: no balance read, no non-negative guard (that rule belongs to
    `_apply_mutation`'s `resource_change` branch, on the AI path — BRIEF-19),
    no UPDATE, no DELETE. This is the ONLY function that writes a `ledger`
    row — both sanctioned canon-write paths (creator CRUD, `_apply_mutation`)
    call it so they cannot diverge. `amount == 0` is rejected: a zero line is
    meaningless.
    """
    if amount == 0:
        raise ValueError("write_ledger_entry: amount must be nonzero")

    entry = Ledger(
        world_id=world_id,
        entity_id=entity_id,
        amount=amount,
        counterparty_id=counterparty_id,
        reason=reason,
        source_type=source_type,
        conversation_id=conversation_id,
        pass_play_id=pass_play_id,
        session_id=session_id,
    )
    db.add(entry)
    return entry


__all__ = [
    "write_relation",
    "write_knowledge",
    "write_ledger_entry",
    "KNOWLEDGE_LEVELS",
    "KNOWLEDGE_LEVEL_LADDER",
    "knowledge_level_rank",
    "cap_knowledge_level",
    "_append_knowledge_history",
]
