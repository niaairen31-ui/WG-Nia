"""Read helpers for observation_* tables (TICKET-0051, BRIEF-0051-f).

Parallel to `observation_writes.py`: writes go through that module, reads go
through this one — `cockpit/routes/observation.py` never references an
`Observation*` model class directly, so the model-identifier allowlist in
`observation_socle.py` stays meaningful for reads as well as writes (this
module is the one addition to that allowlist this brief makes).
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import (
    Character,
    Entity,
    ObservationBeat,
    ObservationIntent,
    ObservationMutationLink,
    ObservationRun,
    ObservationRunTemplate,
    ProposedMutation,
)


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def _entity_name(entity_id: Optional[str], db: Session) -> Optional[str]:
    if entity_id is None:
        return None
    entity = db.get(Entity, entity_id)
    return entity.name if entity is not None else entity_id


def derive_not_selected_reason(intent: ObservationIntent) -> Optional[str]:
    """The precedence documented in `world-engine-schema.md`'s
    `observation_intent` NOTE — derived at read time, never stored (M1)."""
    if intent.selected:
        return None
    if not intent.act:
        return "no_intent"
    if intent.cooldown_active:
        return "cooldown"
    if intent.debt_score < 0:
        return "debt"
    return "lost_arbitration"


def list_present_npcs(location_id: str, db: Session) -> list[dict]:
    """Mirrors `observation_runner._present_npc_ids`'s physical-co-location
    query (never gathering membership), with names for the launch picker."""
    rows = db.exec(
        select(Character.id, Entity.name)
        .join(Entity, Entity.id == Character.id)
        .where(
            Character.current_location_id == location_id,
            Character.character_type == "npc",
            Character.vital_status == "alive",
            Entity.status == "active",
        )
    ).all()
    return [{"id": r[0], "name": r[1]} for r in rows]


def _intent_dict(intent: ObservationIntent, db: Session) -> dict:
    return {
        "id": intent.id,
        "npc_id": intent.npc_id,
        "npc_name": _entity_name(intent.npc_id, db),
        "act": intent.act,
        "urgency": intent.urgency,
        "target_id": intent.target_id,
        "target_name": _entity_name(intent.target_id, db),
        "why": intent.why,
        "propensity": intent.propensity,
        "cooldown_active": intent.cooldown_active,
        "debt_score": intent.debt_score,
        "final_score": intent.final_score,
        "selected": intent.selected,
        "call_status": intent.call_status,
        "latency_ms": intent.latency_ms,
        "not_selected_reason": derive_not_selected_reason(intent),
    }


def _beat_dict(beat: ObservationBeat, intents: list[ObservationIntent], db: Session) -> dict:
    return {
        "id": beat.id,
        "beat_index": beat.beat_index,
        "outcome": beat.outcome,
        "actor_id": beat.actor_id,
        "actor_name": _entity_name(beat.actor_id, db),
        "line": beat.line,
        "mj_narration": beat.mj_narration,
        "created_at": _iso(beat.created_at),
        "intents": [_intent_dict(i, db) for i in intents],
    }


def list_runs(world_id: str, db: Session) -> list[dict]:
    runs = db.exec(
        select(ObservationRun)
        .where(ObservationRun.world_id == world_id)
        .order_by(ObservationRun.started_at.desc())
    ).all()
    result = []
    for run in runs:
        beat_count = len(
            db.exec(select(ObservationBeat.id).where(ObservationBeat.run_id == run.id)).all()
        )
        result.append({
            "id": run.id,
            "location_id": run.location_id,
            "location_name": _entity_name(run.location_id, db),
            "status": run.status,
            "stop_reason": run.stop_reason,
            "started_at": _iso(run.started_at),
            "ended_at": _iso(run.ended_at),
            "beat_count": beat_count,
        })
    return result


def get_run_detail(run_id: str, db: Session) -> Optional[dict]:
    run = db.get(ObservationRun, run_id)
    if run is None:
        return None
    templates = db.exec(
        select(ObservationRunTemplate).where(ObservationRunTemplate.run_id == run_id)
    ).all()
    beats = db.exec(
        select(ObservationBeat).where(ObservationBeat.run_id == run_id).order_by(ObservationBeat.beat_index)
    ).all()
    intents_by_beat: dict[str, list[ObservationIntent]] = {}
    all_intents = db.exec(select(ObservationIntent).where(ObservationIntent.run_id == run_id)).all()
    for intent in all_intents:
        intents_by_beat.setdefault(intent.beat_id, []).append(intent)

    return {
        "id": run.id,
        "world_id": run.world_id,
        "location_id": run.location_id,
        "location_name": _entity_name(run.location_id, db),
        "status": run.status,
        "stop_reason": run.stop_reason,
        "max_beats": run.max_beats,
        "quiescence_limit": run.quiescence_limit,
        "mj_narration": run.mj_narration,
        "cooldown_beats": run.cooldown_beats,
        "debt_weight": run.debt_weight,
        "propensity_mode": run.propensity_mode,
        "model": run.model,
        "player_presence": run.player_presence,
        "started_at": _iso(run.started_at),
        "ended_at": _iso(run.ended_at),
        "templates": [
            {"usage": t.usage, "template_id": t.template_id, "version": t.version} for t in templates
        ],
        "beats": [_beat_dict(b, intents_by_beat.get(b.id, []), db) for b in beats],
    }


def get_run_proposals(run_id: str, db: Session) -> list[dict]:
    """Reached ONLY via `observation_mutation_link` (F3 isolation) — never
    `list_mutations`, which structurally excludes these rows."""
    links = db.exec(
        select(ObservationMutationLink).where(ObservationMutationLink.run_id == run_id)
    ).all()
    result = []
    for link in links:
        mutation = db.get(ProposedMutation, link.mutation_id)
        if mutation is None:
            continue
        result.append({
            "id": mutation.id,
            "mutation_type": mutation.mutation_type,
            "target_table": mutation.target_table,
            "target_id": mutation.target_id,
            "payload": mutation.payload,
            "rationale": mutation.rationale,
            "status": mutation.status,
            "beat_id": link.beat_id,
            "proposed_at": _iso(mutation.proposed_at),
        })
    return result
