"""A skill's rank ladder (TICKET-0106, BRIEF-0106-A, decisions G1, L1, O1, P2,
U2, V).

Six ranks, fixed in the engine and read as numbers by the code (G1):
0 Inexpérimenté, 1 Initié, 2 Apprenti, 3 Confirmé, 4 Expert, 5 Maître. A
world renames them (P2) and sets the default points needed to leave each
rank (O1) in `skill_rank`; a skill system and a skill definition may each
override any of those points in their five `points_to_rank_<n>` columns.
The most specific value wins: the skill definition, then its system, then
the world, then the engine default below.

The dice modifier is NOT the rank (L1): `RANK_MODIFIERS` maps it, so the
four former tiers keep their exact modifier (tier -1/0/1/2 became rank
0/1/2/3 at v2.15) and a Maître rolls +3 at most.

Reads only: this module never writes. `world_ladder` applies the engine
defaults to a world with no `skill_rank` row, without writing them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlmodel import Session, select

from .models import SkillDefinition, SkillRank, SkillSystem

RANKS: tuple[int, ...] = (0, 1, 2, 3, 4, 5)
MAX_RANK: int = 5
# A new skill row starts here: Initié, modifier 0 -- the former tier 0.
DEFAULT_RANK: int = 1
# Index = rank (L1).
RANK_MODIFIERS: tuple[int, ...] = (-1, 0, 1, 2, 2, 3)
DEFAULT_RANK_LABELS: tuple[str, ...] = (
    "Inexpérimenté", "Initié", "Apprenti", "Confirmé", "Expert", "Maître",
)
# Index = rank left; the top rank has no next (V).
DEFAULT_POINTS_TO_NEXT: tuple[int, ...] = (5, 10, 20, 40, 80)
# Migration v2.15 only: the former `skill.tier` value -> its rank.
TIER_TO_RANK: dict[int, int] = {-1: 0, 0: 1, 1: 2, 2: 3}
# Index = rank left: `points_to_rank_<rank + 1>` holds the points to leave it.
RANK_POINTS_COLUMNS: tuple[str, ...] = tuple(f"points_to_rank_{n}" for n in range(1, 6))


@dataclass(frozen=True)
class RankStep:
    rank: int
    label: str
    points_to_next: Optional[int]  # None for MAX_RANK only


def rank_modifier(rank: int) -> int:
    """The dice modifier of a rank (L1). `ValueError` outside 0-5."""
    if rank not in RANKS:
        raise ValueError(f"rank_modifier: rank {rank!r} is not one of {RANKS}")
    return RANK_MODIFIERS[rank]


def default_ladder() -> tuple[RankStep, ...]:
    return tuple(
        RankStep(rank=r, label=DEFAULT_RANK_LABELS[r],
                 points_to_next=DEFAULT_POINTS_TO_NEXT[r] if r < MAX_RANK else None)
        for r in RANKS
    )


def world_ladder(db: Session, world_id: str) -> tuple[RankStep, ...]:
    """The world's six ranks, index = rank: its `skill_rank` rows over the
    engine defaults. Never writes."""
    stored = {row.rank: row for row in db.exec(select(SkillRank).where(SkillRank.world_id == world_id)).all()}
    steps: list[RankStep] = []
    for step in default_ladder():
        row = stored.get(step.rank)
        steps.append(step if row is None else RankStep(
            rank=step.rank, label=row.label,
            points_to_next=row.points_to_next if step.rank < MAX_RANK else None,
        ))
    return tuple(steps)


def points_to_next(
    rank: int, ladder: tuple[RankStep, ...], *, system: Any = None, definition: Any = None,
) -> Optional[int]:
    """Points needed to leave `rank`: `definition`'s column, else `system`'s,
    else the ladder's (O1). None at MAX_RANK. `system`/`definition` are any
    objects carrying the five `points_to_rank_<n>` attributes, or None."""
    if rank >= MAX_RANK:
        return None
    column = RANK_POINTS_COLUMNS[rank]
    for owner in (definition, system):
        value = getattr(owner, column, None) if owner is not None else None
        if value is not None:
            return value
    return ladder[rank].points_to_next


def skill_owners(db: Session, skill_definition_id: Optional[str]) -> tuple[Optional[SkillSystem], Optional[SkillDefinition]]:
    """(system, definition) of a skill row; (None, None) for a base domain."""
    if skill_definition_id is None:
        return None, None
    definition = db.get(SkillDefinition, skill_definition_id)
    if definition is None or definition.system_id is None:
        return None, definition
    return db.get(SkillSystem, definition.system_id), definition


def skill_points_to_next(db: Session, *, world_id: str, rank: int, skill_definition_id: Optional[str]) -> Optional[int]:
    """`points_to_next` for one skill row, its owners and ladder read here."""
    system, definition = skill_owners(db, skill_definition_id)
    return points_to_next(rank, world_ladder(db, world_id), system=system, definition=definition)
