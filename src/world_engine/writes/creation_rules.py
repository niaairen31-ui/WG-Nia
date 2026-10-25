"""The creation rules' writer (TICKET-0126, BRIEF-0126-C, C-05).

`write_creation_rules` is the one writer of `creation_rules`, a world's
character creation rules (curated config, the `skill_rank` family): it
fetches or creates the world's one row and sets every field. It never
deletes, never commits -- the caller owns the transaction (INV-18's
posture). Every bound is checked first, as a French `ValueError` the
creator reads, before any write; a bool is never accepted as an int.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Optional, Sequence

from sqlalchemy import null
from sqlmodel import Session, select

from ..models import CREATION_CAP_RANKS, CreationRules


def _count(value: Any) -> bool:
    """An int >= 0, never a bool."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def write_creation_rules(
    db: Session,
    *,
    world_id: str,
    pool: int,
    costs: Sequence[int],
    caps: Mapping[int, Optional[int]],
    max_rank: int,
    max_master_skills: int,
    skills_visible: bool,
) -> CreationRules:
    """Set the world's creation rules (C-05). `costs` lists ranks 1..5 in
    order; `caps` has exactly the keys of CREATION_CAP_RANKS, a None cap
    meaning no cap. Adds and flushes; never deletes, never commits."""
    if not _count(pool):
        raise ValueError("La réserve est un nombre entier, au moins 0.")
    if isinstance(costs, (str, bytes)) or len(costs) != 5 or not all(_count(c) for c in costs):
        raise ValueError("Chaque coût est un nombre entier, au moins 0.")
    if set(caps) != set(CREATION_CAP_RANKS) or not all(c is None or _count(c) for c in caps.values()):
        raise ValueError("Chaque plafond est vide ou un nombre entier, au moins 0.")
    if not (isinstance(max_rank, int) and not isinstance(max_rank, bool) and 1 <= max_rank <= 5):
        raise ValueError("Le rang maximal va d'Initié à Maître.")
    if not _count(max_master_skills):
        raise ValueError("Le nombre de compétences à maître est un nombre entier, au moins 0.")
    if not isinstance(skills_visible, bool):
        raise ValueError("La visibilité est oui ou non.")
    row = db.exec(select(CreationRules).where(CreationRules.world_id == world_id)).first()
    if row is None:
        row = CreationRules(world_id=world_id)
    row.pool = pool
    for rank, cost in enumerate(costs, start=1):
        setattr(row, f"cost_to_rank_{rank}", cost)
    for rank in CREATION_CAP_RANKS:
        # null(): a None cap is written NULL (no cap) -- `cap_at_rank_0`'s
        # column default would otherwise fill a None on the row's INSERT.
        setattr(row, f"cap_at_rank_{rank}", caps[rank] if caps[rank] is not None else null())
    row.max_rank = max_rank
    row.max_master_skills = max_master_skills
    row.skills_visible = skills_visible
    row.updated_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    return row
