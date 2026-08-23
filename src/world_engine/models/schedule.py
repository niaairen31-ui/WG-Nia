"""NPC standing-schedule curated config (TICKET-0074, BRIEF-0074-a).

Split out of `canon.py` (993/1000 lines, no headroom for a new table —
`tooling/verify/checks/module_budget.py`), not because this table belongs to
a different stratum: it is canon curated-config, same family as
`location_type_catalog` / `world_law` (metadata-config category, no
`change_history`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Index
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

# The four named cycle phases (A1a, TICKET-0074). A DAY-CYCLE axis, with no
# calendrical component in v1. Deliberately NOT a reuse of
# `tick_context.INTERVAL_HOP_RADIUS`, which is a DURATION axis (a BFS hop
# bound on `connects_to` -- how much time passed off-screen) and whose key
# set is asserted by `tooling/verify/checks/world_tick.py`. Two axes, two
# constants, two checks. Adding a calendar later means a nullable
# `day_kind` column and a pair of PARTIAL unique indexes (see the
# `NpcSchedule` index comment) -- it never means adding a key here.
SCHEDULE_PHASES: tuple[str, ...] = ("matin", "apres-midi", "soir", "nuit")


# -----------------------------------------------------------------------------
# npc_schedule  (standing per-phase location default, schema v1.92,
# TICKET-0074, BRIEF-0074-a)
#
# One row per NPC per phase. Curated config (location_type_catalog family):
# no `change_history`, written ONLY via `writes.write_npc_schedule`
# (full-replace per NPC). Sparse by decision (B1) -- absence of a row is
# legal and handled by the `schedule_reads.py` accessor's fallback.
# -----------------------------------------------------------------------------
class NpcSchedule(SQLModel, table=True):
    __tablename__ = "npc_schedule"
    __table_args__ = (
        CheckConstraint("phase IN ('matin','apres-midi','soir','nuit')", name="ck_npc_schedule_phase"),
        # One row per NPC per phase. When a calendar lands (A2's reactivation),
        # this does NOT widen to (npc_id, phase, day_kind): SQLite treats NULLs as
        # DISTINCT inside a UNIQUE index, so the widened index would silently stop
        # guaranteeing uniqueness for every default row. The correct path is the
        # `faction_membership` partial-unique idiom (models/canon_faction.py):
        # one partial UNIQUE `WHERE day_kind IS NULL`, one `WHERE day_kind IS NOT
        # NULL`. Recorded now so the migration that adds the calendar does not
        # have to rediscover it.
        Index("idx_npc_schedule_npc_phase", "npc_id", "phase", unique=True),
        # Drives who_is_at -- the inverse read the resolution chain uses most.
        Index("idx_npc_schedule_location_phase", "location_id", "phase"),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    npc_id: str = Field(foreign_key="entity.id", nullable=False)
    phase: str
    location_id: str = Field(foreign_key="entity.id", nullable=False)
    standing_goal_id: Optional[str] = Field(default=None, foreign_key="npc_goal.id")
    created_at: datetime = _created_ts()
    updated_at: datetime = _created_ts()
