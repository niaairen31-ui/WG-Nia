"""Single write chokepoint for `observation_*` tables (TICKET-0051,
BRIEF-0051-a).

Observed-scene instrumentation is telemetry, not canon — this module is the
ONLY place in the codebase allowed to write an `observation_*` row, exactly
as `single_canon_write.py` gates the two canon-write paths. There is no
runner yet (BRIEF-0051-d) and no model call yet (BRIEF-0051-c); this brief
ships the write surface only, each function a complete, self-contained
transaction (there is no established caller to own a shared commit boundary
until the runner exists).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session

from .models import (
    ObservationBeat,
    ObservationIntent,
    ObservationMutationLink,
    ObservationRun,
    ObservationRunTemplate,
)

# The proposed_mutation.proposed_by value marking an observed-run proposal —
# defined ONCE here, imported everywhere else (the queue filter, the future
# proposal producer).
OBSERVED_PROPOSED_BY = "observed_scene"

_TERMINAL_STATUSES = ("completed", "stopped", "failed")


def write_observation_run(
    session: Session,
    *,
    world_id: str,
    location_id: str,
    gathering_id: Optional[str],
    player_presence: str,
    max_beats: int,
    quiescence_limit: int,
    mj_narration: bool,
    cooldown_beats: int,
    debt_weight: float,
    propensity_mode: str,
    model: str,
    templates: list[dict],
) -> ObservationRun:
    """Insert the run plus its `observation_run_template` rows in one
    transaction. Refuses `player_presence != 'absent'` outright (H2 —
    'silent'/'active' are named deferrals, never silently downgraded).

    Each item of `templates` is `{"usage": str, "template_id": str,
    "version": int}`.
    """
    if player_presence != "absent":
        raise ValueError(
            f"write_observation_run: player_presence {player_presence!r} is not "
            "implemented — only 'absent' is supported (TICKET-0051, H2)"
        )

    run = ObservationRun(
        world_id=world_id,
        location_id=location_id,
        gathering_id=gathering_id,
        player_presence=player_presence,
        max_beats=max_beats,
        quiescence_limit=quiescence_limit,
        mj_narration=mj_narration,
        cooldown_beats=cooldown_beats,
        debt_weight=debt_weight,
        propensity_mode=propensity_mode,
        model=model,
    )
    session.add(run)
    for template in templates:
        session.add(
            ObservationRunTemplate(
                run_id=run.id,
                usage=template["usage"],
                template_id=template["template_id"],
                version=template["version"],
            )
        )
    session.commit()
    session.refresh(run)
    return run


def close_observation_run(
    run_id: str,
    status: str,
    stop_reason: Optional[str],
    session: Session,
) -> ObservationRun:
    """The ONLY path that sets a terminal `status`/`stop_reason`/`ended_at`.
    Allows exactly `running -> completed | stopped | failed`; any other
    transition, including reopening a terminal run, raises `ValueError`."""
    run = session.get(ObservationRun, run_id)
    if run is None:
        raise ValueError(f"close_observation_run: no observation_run {run_id!r}")
    if run.status != "running":
        raise ValueError(
            f"close_observation_run: run {run_id!r} is already {run.status!r} "
            "— a terminal run cannot be re-closed or reopened"
        )
    if status not in _TERMINAL_STATUSES:
        raise ValueError(f"close_observation_run: invalid terminal status {status!r}")

    run.status = status
    run.stop_reason = stop_reason
    run.ended_at = datetime.now(UTC)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def write_observation_beat(
    session: Session,
    *,
    run_id: str,
    beat_index: int,
    outcome: str,
    actor_id: Optional[str] = None,
    line: Optional[str] = None,
    mj_narration: Optional[str] = None,
) -> ObservationBeat:
    """Insert-only. `outcome == 'acted'` requires `actor_id`; every other
    outcome requires its absence — never inferred, always asserted (M2)."""
    if outcome == "acted" and actor_id is None:
        raise ValueError("write_observation_beat: outcome 'acted' requires actor_id")
    if outcome != "acted" and actor_id is not None:
        raise ValueError(
            f"write_observation_beat: outcome {outcome!r} must not carry an actor_id"
        )

    beat = ObservationBeat(
        run_id=run_id,
        beat_index=beat_index,
        outcome=outcome,
        actor_id=actor_id,
        line=line,
        mj_narration=mj_narration,
    )
    session.add(beat)
    session.commit()
    session.refresh(beat)
    return beat


def write_observation_intent(
    session: Session,
    *,
    run_id: str,
    beat_id: str,
    npc_id: str,
    act: bool,
    urgency: Optional[int],
    target_id: Optional[str],
    why: Optional[str],
    propensity: float,
    cooldown_active: bool,
    debt_score: float,
    final_score: float,
    selected: bool,
    call_status: str,
    latency_ms: Optional[int] = None,
    raw_response: Optional[str] = None,
) -> ObservationIntent:
    """Insert-only. Written for EVERY candidate on EVERY beat, including a
    failed model call (`call_status != 'ok'`) — a missing row is a bug, never
    a silent decline."""
    intent = ObservationIntent(
        run_id=run_id,
        beat_id=beat_id,
        npc_id=npc_id,
        act=act,
        urgency=urgency,
        target_id=target_id,
        why=why,
        propensity=propensity,
        cooldown_active=cooldown_active,
        debt_score=debt_score,
        final_score=final_score,
        selected=selected,
        call_status=call_status,
        latency_ms=latency_ms,
        raw_response=raw_response,
    )
    session.add(intent)
    session.commit()
    session.refresh(intent)
    return intent


def link_observation_mutation(
    session: Session,
    *,
    run_id: str,
    beat_id: Optional[str],
    mutation_id: str,
) -> ObservationMutationLink:
    """Insert-only provenance row joining a `proposed_mutation` back to the
    run/beat that produced it, without altering the canon `proposed_mutation`
    row itself."""
    link = ObservationMutationLink(run_id=run_id, beat_id=beat_id, mutation_id=mutation_id)
    session.add(link)
    session.commit()
    session.refresh(link)
    return link
