"""A roll earns a skill point (TICKET-0106, BRIEF-0106-B, decisions H1, K1, M2,
N2, Q1, S1, Y1b).

Every roll of the player earns one point (M2: success, partial or failure
alike -- one learns from failing too), with no cap (N2). Reaching the
threshold of the current rank moves the skill up one rank, automatically
(K1: the threshold half; trials with extra requirements come with quests).

Two carriers, both inside `_apply_mutation` (Q1):

- Play. `record_roll` runs right after the dice, on a session of its own
  (the stream's request session is read-only, `stream_session_readonly.py`):
  it writes one `skill_progress` mutation, `proposed_by='engine_roll'`, and
  applies it at once through `routes/mutations._approve_apply_and_commit`
  -- an AUTO-APPLIED mutation (ARCHITECTURE_DECISIONS.md, "Auto-applied
  mutations": reversible by a `skill_progress` of -1 point, creates and
  destroys nothing, touches no relation or knowledge, recorded `applied`
  and visible in the review cockpit). The point goes to the row that was
  rolled (S1): the custom skill when the arbiter named one. A skill at
  Maître earns nothing more: no mutation is written. A failure here is
  logged and swallowed -- a point must never break a turn. The result rides
  on the verdict event as `progress` (Y1b: Play is sealed, its client does
  not show it yet).
- A day. A day's dice are replayable and write no canon (`day_resolve.py`);
  the point is given when Nia APPROVES the step's `agenda_step_change`,
  complete or fail alike, by `grant_step_roll`, called from that applier:
  the step's `domain` names the base skill rolled, read from the step,
  never from the payload.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from ..db import engine
from ..models import AgendaStep, ProposedMutation, Skill, SkillDefinition, World
from ..skill_ranks import MAX_RANK, skill_points_to_next, world_ladder
from ..writes import write_skill_progress

_log = logging.getLogger(__name__)

SKILL_PROGRESS_PROPOSED_BY = "engine_roll"
ROLL_POINTS = 1


def apply_skill_progress(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
    """`_apply_mutation`'s applier for `skill_progress`: payload
    `{"skill_id": str, "points": non-zero int, "band": str | None}`. Returns
    an error string, never raises."""
    skill_id = payload.get("skill_id")
    points = payload.get("points")
    if not skill_id or not isinstance(points, int) or isinstance(points, bool) or points == 0:
        return "skill_progress: payload must contain skill_id and a non-zero integer points"
    if db.get(Skill, skill_id) is None:
        return f"skill_progress: skill {skill_id!r} not found"
    write_skill_progress(db, skill_id=skill_id, world_id=mut.world_id, points=points,
                         changed_by=f"mutation:{mut.id}")
    return None


def _progress_payload(db: Session, skill: Skill, world_id: str, rank_before: int) -> dict:
    definition = db.get(SkillDefinition, skill.skill_definition_id) if skill.skill_definition_id else None
    ladder = world_ladder(db, world_id)
    return {
        "skill": definition.name if definition else skill.domain,
        "rank": skill.rank,
        "rank_label": ladder[skill.rank].label,
        "ranked_up": skill.rank > rank_before,
        "xp": skill.xp,
        "points_to_next": skill_points_to_next(db, world_id=world_id, rank=skill.rank,
                                               skill_definition_id=skill.skill_definition_id),
    }


def record_roll(*, world_id: str, conversation_id: str, skill_id: Optional[str], band: str) -> Optional[dict]:
    """One auto-applied `skill_progress` for a Play roll. Returns the skill's
    new state (`skill`, `rank`, `rank_label`, `ranked_up`, `xp`,
    `points_to_next`), or None when nothing was earned: no row rolled, a
    Maître, an apply refused, or any error (logged)."""
    if skill_id is None:
        return None
    try:
        with Session(engine) as db:
            skill = db.get(Skill, skill_id)
            if skill is None or skill.rank >= MAX_RANK or db.get(World, world_id) is None:
                return None
            rank_before = skill.rank
            mut = ProposedMutation(
                world_id=world_id, source_type="conversation", conversation_id=conversation_id,
                mutation_type="skill_progress", target_table="skill", target_id=skill_id,
                payload={"skill_id": skill_id, "points": ROLL_POINTS, "band": band},
                rationale=f"jet ({band}) : +{ROLL_POINTS} point", proposed_by=SKILL_PROGRESS_PROPOSED_BY,
            )
            db.add(mut)
            db.flush()
            from .routes.mutations import _approve_apply_and_commit
            result = _approve_apply_and_commit(mut, db, datetime.now(UTC))
            if result.get("status") != "applied":
                _log.warning("skill_progress %s not applied: %s", mut.id, result.get("error"))
                return None
            db.refresh(skill)
            return _progress_payload(db, skill, world_id, rank_before)
    except Exception:  # a point must never break a turn
        _log.exception("skill_progress: recording the roll on skill %s failed", skill_id)
        return None


def grant_step_roll(db: Session, *, step: AgendaStep, owner_id: str, world_id: str, mutation_id: str) -> None:
    """The point of an approved day step's roll: the owner's base skill row
    for `step.domain` (`skill_definition_id IS NULL`). Nothing when the step
    had no roll (no domain), the owner has no such row (a faction, an NPC),
    or the skill is at Maître."""
    if step.domain is None:
        return
    skill = db.exec(
        select(Skill).where(
            Skill.character_id == owner_id,
            Skill.domain == step.domain,
            Skill.skill_definition_id.is_(None),
        )
    ).first()
    if skill is None or skill.rank >= MAX_RANK:
        return
    write_skill_progress(db, skill_id=skill.id, world_id=world_id, points=ROLL_POINTS,
                         changed_by=f"mutation:{mutation_id}")
