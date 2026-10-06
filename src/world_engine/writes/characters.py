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
- `write_skill_row(...)`                : create one `skill` row for a
  character -- an NPC's skill, a carrure, a skill learned (TICKET-0107,
  BRIEF-0107-A). The sole creator of a row outside the PC seed and the
  catalogue backfill.
- `write_skill_progress(...)`           : add points to a `skill` row and
  move its rank when a threshold is crossed (TICKET-0106, BRIEF-0106-B).
  The sole write shape for points; called by the `skill_progress` applier
  and the day step's roll, both inside `_apply_mutation`.
- `write_ledger_entry(...)`             : pure INSERT into the append-only
  `ledger` table (BRIEF-18). No UPDATE, no DELETE, ever — a correction is a
  new compensating line. The single chokepoint for ledger writes, shared by
  the creator CRUD and `_apply_mutation`'s `resource_change` branch
  (BRIEF-19) so the two paths cannot diverge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from ..models import BASE_SKILL_DOMAINS, Character, Ledger, Skill, SkillDefinition
from ..skill_ranks import MAX_RANK, RANKS, skill_points_to_next


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


def write_skill_row(
    db: Session,
    *,
    character_id: str,
    rank: int,
    domain: Optional[str] = None,
    skill_definition_id: Optional[str] = None,
    taught_by_id: Optional[str] = None,
) -> Skill:
    """Create one `skill` row: a base domain (`domain`, no definition) or a
    skill definition (`skill_definition_id`; the row's `domain` is the
    definition's base domain, never the caller's). Caller adds nothing and
    commits. `ValueError` before any write on a rank outside `RANKS`, both
    or neither of `domain`/`skill_definition_id`, an unknown definition, a
    base domain outside `BASE_SKILL_DOMAINS`, or a row the character already
    holds for that skill (one row per character and skill)."""
    if rank not in RANKS:
        raise ValueError(f"write_skill_row: rank {rank!r} is not one of {RANKS}")
    if (domain is None) == (skill_definition_id is None):
        raise ValueError("write_skill_row: exactly one of domain and skill_definition_id")
    if skill_definition_id is not None:
        definition = db.get(SkillDefinition, skill_definition_id)
        if definition is None:
            raise ValueError(f"write_skill_row: skill definition {skill_definition_id!r} not found")
        domain = definition.base_domain
        clash = select(Skill).where(Skill.character_id == character_id,
                                    Skill.skill_definition_id == skill_definition_id)
    else:
        if domain not in BASE_SKILL_DOMAINS:
            raise ValueError(f"write_skill_row: {domain!r} is not a base domain")
        clash = select(Skill).where(Skill.character_id == character_id, Skill.domain == domain,
                                    Skill.skill_definition_id.is_(None))
    if db.exec(clash).first() is not None:
        raise ValueError("write_skill_row: the character already holds this skill")
    row = Skill(character_id=character_id, domain=domain, rank=rank,
                skill_definition_id=skill_definition_id, taught_by_id=taught_by_id)
    db.add(row)
    return row


@dataclass(frozen=True)
class SkillProgress:
    rank_before: int
    rank: int
    xp: int
    points_to_next: Optional[int]  # None at MAX_RANK


def write_skill_progress(
    db: Session,
    *,
    skill_id: str,
    world_id: str,
    points: int,
    changed_by: str,
) -> SkillProgress:
    """Add `points` (non-zero, may be negative) to a `skill` row's `xp`.
    Caller adds the row to the session.

    Gaining: when `xp` reaches the points needed to leave the current rank
    (`skill_ranks.skill_points_to_next`), the rank rises by one and `xp`
    restarts at 0 (U2) -- at most one rank per call. At MAX_RANK the points
    still accumulate. Losing (the inverse of a gain): below 0, the rank falls
    by one and `xp` becomes that lower rank's threshold minus the remainder,
    so -1 exactly undoes a +1 that ranked up; at rank 0 `xp` stops at 0.
    `change_history` gets the previous rank and points only when the rank
    moves -- a point alone is audited by the mutation that carried it.
    `ValueError` on zero points or an unknown row, before any write.
    """
    if not isinstance(points, int) or isinstance(points, bool) or points == 0:
        raise ValueError(f"write_skill_progress: points must be a non-zero integer, got {points!r}")
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise ValueError(f"write_skill_progress: skill {skill_id!r} not found")

    def threshold(rank: int) -> Optional[int]:
        return skill_points_to_next(db, world_id=world_id, rank=rank, skill_definition_id=skill.skill_definition_id)

    rank_before, xp_before = skill.rank, skill.xp
    rank, xp = rank_before, xp_before + points
    needed = threshold(rank)
    if points > 0 and needed is not None and xp >= needed:
        rank, xp = rank + 1, 0
    elif xp < 0 and rank > 0:
        rank -= 1
        xp = max(0, (threshold(rank) or 1) + xp)
    xp = max(0, xp)

    if rank != rank_before:
        history = list(skill.change_history or [])
        history.append({
            "rank": rank_before,
            "xp": xp_before,
            "changed_at": datetime.now(UTC).isoformat(),
            "by": changed_by,
        })
        skill.change_history = history
        sa_attrs.flag_modified(skill, "change_history")
    skill.rank = rank
    skill.xp = xp
    skill.updated_at = datetime.now(UTC)
    db.add(skill)
    return SkillProgress(
        rank_before=rank_before, rank=rank, xp=xp,
        points_to_next=None if rank >= MAX_RANK else threshold(rank),
    )


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
