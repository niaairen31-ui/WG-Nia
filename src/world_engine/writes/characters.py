"""`character`/`skill`/`ledger` canon-write chokepoints (TICKET-0028,
BRIEF-0028-b — decomposed from `writes.py`). Pure moves, no logic change —
none of these three functions were baselined.

- `write_character_location(...)`      : write a character's
  `current_location_id` (TICKET-0015, BRIEF-0015-a).
- `write_skill_rank(...)`               : set a `skill` row's rank,
  appending the previous rank and points to `change_history` first
  (history is sacred on this path too) and restarting its points at 0
  (U2). The sole write shape for a creator's rank edit (TICKET-0106,
  BRIEF-0106-A; formerly `write_skill_tier`).
- `write_ledger_entry(...)`             : pure INSERT into the append-only
  `ledger` table (BRIEF-18). No UPDATE, no DELETE, ever — a correction is a
  new compensating line. The single chokepoint for ledger writes, shared by
  the creator CRUD and `_apply_mutation`'s `resource_change` branch
  (BRIEF-19) so the two paths cannot diverge.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session

from ..models import Character, Ledger, Skill
from ..skill_ranks import RANKS


def write_character_location(
    db: Session,
    *,
    entity_id: str,
    to_location_id: str,
    mutation_id: Optional[str] = None,
) -> Character:
    """Write a character's `current_location_id` (TICKET-0015, BRIEF-0015-a).

    Caller adds no row itself but owns the transaction/commit — same
    convention as `write_relation`. `character` has no `change_history`
    column and the creator-CRUD location edit snapshots nothing; the
    `proposed_mutation` row (from/to payload, `tick_id`, `applied_at`) is the
    durable audit trail for this write (RECON-0015 F7), so `mutation_id` is
    accepted only for call-site symmetry and is not otherwise used here.
    """
    del mutation_id
    character = db.get(Character, entity_id)
    if character is None:
        raise ValueError(f"write_character_location: character {entity_id!r} not found")
    character.current_location_id = to_location_id
    db.add(character)
    return character


def write_skill_rank(
    db: Session,
    *,
    skill_id: str,
    rank: int,
    changed_by: str = "creator",
) -> Skill:
    """Set a `skill` row's rank. Caller adds the row to the session.

    The sole write shape for a creator's rank edit (`cockpit/crud/skills.py`'s
    `update_skill_rank` is its only caller). Appends the previous rank and
    points to `change_history` first (history is sacred), then sets `rank`,
    restarts `xp` at 0 (U2: points count within a rank) and bumps
    `updated_at`. The caller decides whether to call this at all — a
    resubmission of the same rank should be a no-op, not an empty history
    entry. `ValueError` outside `skill_ranks.RANKS`, before any write.
    """
    if rank not in RANKS:
        raise ValueError(f"write_skill_rank: rank {rank!r} is not one of {RANKS}")
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise ValueError(f"write_skill_rank: skill {skill_id!r} not found")

    history = list(skill.change_history or [])
    history.append({
        "rank": skill.rank,
        "xp": skill.xp,
        "changed_at": datetime.now(UTC).isoformat(),
        "by": changed_by,
    })
    skill.change_history = history
    sa_attrs.flag_modified(skill, "change_history")
    skill.rank = rank
    skill.xp = 0
    skill.updated_at = datetime.now(UTC)

    db.add(skill)
    return skill


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
