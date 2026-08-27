"""Day declaration, plan-emission and resolution routes (TICKET-0075,
BRIEF-0075-a — the declaration socle: plumbing only; BRIEF-0075-b — plan
emission and budget; BRIEF-0075-c — extraction and concordance;
BRIEF-0075-d — resolution, the fact sheet and narration; BRIEF-0075-g —
the feasibility veto, decision Y1). A player declares a day; the
declaration is stored, listed and read back, a plan can be emitted against
it: extraction + concordance resolve its mentions to canon ids or roles
(C1: the resolver never authors — any unmatched PERSON mention only ever
reaches canon as a PARKED `entity_creation` germ, never authored here),
then one model call (`day_plan.emit_plan`), Python-judged requirements and
a Python budget cut (F1: model proposes, code judges), then ONE MORE model
call (`day_feasibility.veto`) that can only shorten what Python retained,
never extend it (Y1). Finally the budgeted, vetoed plan is resolved
(`resolve_day`): Python dice (`resolve_steps`, capped at the veto's own
retained count), a frozen fact sheet, one narration call constrained by it,
and a fail-closed Python judge before anything is stored final.

`_get_or_open_session` deliberately duplicates the M5 idiom from
`cockpit/play.py` (`_get_or_open_session`) rather than importing it: Play is
a sealed module (TICKET-0069 is its own migration), and this surface must
not couple to it.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ... import day_plan_select, day_plans
from ...day_concordance import ConcordanceResult, concord, emit_germs, plan_context
from ...day_extract import extract_factions, extract_persons, extract_places
from ...day_feasibility import VetoVerdict, veto as feasibility_veto
from ...day_mutations import emit_mutations
from ...day_narration import detect_late_delta, narrate, rewrite as day_rewrite
from ...day_narration_guard import JudgeVerdict, judge_narration
from ...day_plan import (
    DAY_BUDGET_SLOTS,
    EvaluatedStep,
    anchor_requirements,
    budget_cut,
    emit_plan,
    evaluate_requirements,
    held_subjects_summary,
)
from ...day_resolve import (
    FactSheet,
    StepOutcome,
    fact_sheet_dict,
    freeze_facts,
    resolve_steps,
)
from ...db import get_session
from ...llm_parse import LlmParseError
from ...prompt_coverage import DAY_CHAIN_USAGES, missing_usages
from ...models import (
    Agenda,
    AgendaStep,
    AgendaStepRequirement,
    Batch,
    Character,
    Entity,
    PassPlay,
    ProposedMutation,
)
from ...models import Session as GameSession
from ...writes import (
    BATCH_RESOLVED_STATUS,
    MAX_DECLARATION_CHARS,
    read_latest_feasibility,
    read_latest_resolution,
    resolution_count,
    write_batch,
    write_day_feasibility,
    write_day_plan,
    write_pass_play,
    write_pass_play_resolution,
)
from .. import crud as _crud
from ..day_reconcile_apply import _reconcile_and_finalize

router = APIRouter()


def _get_or_open_session(world_id: str, db: Session) -> GameSession:
    """Return the world's open session, creating one if none exists (same
    idiom as `cockpit/play.py::_get_or_open_session`, duplicated on
    purpose — see module docstring)."""
    existing = db.exec(
        select(GameSession)
        .where(GameSession.world_id == world_id, GameSession.status == "open")
        .order_by(GameSession.number.desc())
    ).first()
    if existing is not None:
        return existing
    numbers = db.exec(
        select(GameSession.number).where(GameSession.world_id == world_id)
    ).all()
    number = (max(numbers) if numbers else 0) + 1
    sess = GameSession(
        world_id=world_id,
        number=number,
        title="Live play session",
        status="open",
        started_at=datetime.now(UTC),
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _resolve_player_character(world_id: str, db: Session) -> Character:
    rows = db.exec(
        select(Character).where(
            Character.world_id == world_id, Character.character_type == "player",
        )
    ).all()
    if len(rows) != 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"expected exactly one player character for this world, found {len(rows)}"
            ),
        )
    return rows[0]


def _day_dict(batch: Batch, pass_play: PassPlay) -> dict:
    # `status` is the pass_play lifecycle (PASS_PLAY_STATUSES) -- the
    # player's own declaration, not `batch.status` (a separate, larger
    # vocabulary belonging to the legacy Claude-checkpoint pipeline).
    return {
        "id": batch.id,
        "pass_play_id": pass_play.id,
        "day_number": batch.day_number,
        "status": pass_play.status,
        "declared_action": pass_play.declared_action,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


def _feasibility_dict(
    python_retained: int, veto_retained: int, reason: str, cited_objective: Optional[str], outcome: str,
) -> dict:
    """Player-facing shape (BRIEF-0075-g, Wiring): counts, the reason, the
    cited step's OBJECTIVE (never its order/id -- ticket-wide Scope OUT),
    and the honoured/clamped/unavailable flag. Shared by the `/plan`
    response (built from the fresh `VetoVerdict`) and `GET /api/day/{id}`
    (built from the persisted `pass_play.history` entry via `read_latest_
    feasibility` -- never `.history` itself, `pipeline_wiring.py`'s R5)."""
    return {
        "python_retained": python_retained,
        "veto_retained": veto_retained,
        "reason": reason,
        "cited_objective": cited_objective,
        "outcome": outcome,
    }


class DayDeclareBody(BaseModel):
    # Bound read from writes/pipeline.py rather than restated as a literal
    # (R4) -- this is a fast client-facing 422, write_pass_play's own check
    # is the structural guarantee.
    declared_action: str = Field(max_length=MAX_DECLARATION_CHARS)


@router.post("/api/day/declare")
def declare_day(body: DayDeclareBody, db: Session = Depends(get_session)) -> dict:
    missing = missing_usages(DAY_CHAIN_USAGES, db)
    if missing:
        raise HTTPException(
            status_code=503,
            detail=(
                "day chain unavailable: no active prompt_template with a version for "
                f"{', '.join(missing)} -- run "
                "python scripts/apply_ticket_0077_plan_select_seed.py"
            ),
        )

    world_id = _crud._world_id(db)
    game_session = _get_or_open_session(world_id, db)
    character = _resolve_player_character(world_id, db)

    batch = write_batch(db, session_id=game_session.id, changed_by="player")
    try:
        pass_play = write_pass_play(
            db,
            batch_id=batch.id,
            session_id=game_session.id,
            character_id=character.id,
            declared_action=body.declared_action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.add(batch)
    db.add(pass_play)
    db.commit()
    db.refresh(batch)
    db.refresh(pass_play)
    return _day_dict(batch, pass_play)


@router.get("/api/days")
def list_days(db: Session = Depends(get_session)) -> list[dict]:
    world_id = _crud._world_id(db)
    rows = db.exec(
        select(Batch, PassPlay)
        .join(GameSession, GameSession.id == Batch.session_id)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .where(GameSession.world_id == world_id)
        .order_by(Batch.day_number.desc())
    ).all()
    return [_day_dict(batch, pass_play) for batch, pass_play in rows]


def _account_gains(mutations: list[ProposedMutation]) -> dict:
    """Gains block (Scope IN item 4): resource/relation gains are read from
    the `effects` embedded in `agenda_step_change` payloads (the delta
    contract, BRIEF-0075-e-amendment-1) plus any standalone
    `relation_change` row; knowledge gains are the rendezvous
    `knowledge_change` rows. Skill deltas have no carrier in v1 (X1) —
    reported positively, never silently omitted."""
    resource: list[dict] = []
    relation: list[dict] = []
    knowledge: list[dict] = []
    for m in mutations:
        payload = m.payload if isinstance(m.payload, dict) else {}
        if m.mutation_type == "agenda_step_change":
            for eff in payload.get("effects") or []:
                if not isinstance(eff, dict):
                    continue
                if eff.get("type") == "ledger_transfer":
                    resource.append({"mutation_id": m.id, "status": m.status, "detail": eff})
                elif eff.get("type") == "relation_delta":
                    relation.append({"mutation_id": m.id, "status": m.status, "detail": eff})
        elif m.mutation_type == "relation_change":
            relation.append({"mutation_id": m.id, "status": m.status, "detail": payload})
        elif m.mutation_type == "knowledge_change":
            knowledge.append({
                "mutation_id": m.id, "status": m.status,
                "subject": payload.get("subject"), "to_level": payload.get("to_level"),
            })
    return {
        "resource": resource,
        "relation": relation,
        "knowledge": knowledge,
        "skill": {
            "produced": [],
            "note": "La résolution de journée ne produit pas encore de gain de compétence.",
        },
    }


def _account_rendezvous(mutations: list[ProposedMutation], db: Session) -> Optional[dict]:
    """The armed rendezvous (I1, corrected by BRIEF-0075-e-amendment-1):
    surfaced only once the step that established it has actually been
    APPLIED — `_mutation_apply_agenda_step_change`'s own cascade
    (cockpit/mutations.py) is what puts the next step `active` on
    approval, so reading the agenda's current active step at that point
    is correct, never a guess. No `agenda_id`/`step_id` key anywhere in
    the returned dict (R7)."""
    agenda_id = None
    for m in mutations:
        if m.mutation_type != "agenda_step_change" or m.status != "applied":
            continue
        payload = m.payload if isinstance(m.payload, dict) else {}
        step = db.get(AgendaStep, payload.get("step_id"))
        if step is not None:
            agenda_id = step.agenda_id
    if agenda_id is None:
        return None

    active_step = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda_id, AgendaStep.status == "active")
    ).first()
    if active_step is None:
        return None

    npc_id, npc_name = None, None
    for req in db.exec(
        select(AgendaStepRequirement).where(
            AgendaStepRequirement.step_id == active_step.id,
            AgendaStepRequirement.type == "relation_gte",
        )
    ).all():
        target = db.get(Entity, req.target_entity_id) if req.target_entity_id else None
        if target is not None:
            npc_id, npc_name = target.id, target.name
            break

    return {"objective": active_step.objective, "npc_id": npc_id, "npc_name": npc_name, "armed": True}


def _day_account_dict(pass_play: PassPlay, batch: Batch, db: Session) -> dict:
    """The day account (Scope IN item 4): prose, NPCs, locations, gains and
    a pending-review block. Reads the LATEST resolution through
    `read_latest_resolution` (`writes/pipeline.py`), never `pass_play.
    history` directly — this file must never reference `.history`
    (`pipeline_wiring.py`'s R5) — and that helper also spares a second,
    non-deterministic extraction+concordance model-call pass just to
    rebuild what `resolve_day` already computed once. `is_replay` comes
    from `resolution_count`, the same `.history`-free boundary."""
    latest = read_latest_resolution(pass_play)
    if latest is None:
        return {}
    fact_sheet = latest.get("fact_sheet") or {}

    mutations = db.exec(
        select(ProposedMutation).where(ProposedMutation.pass_play_id == pass_play.id)
    ).all()

    germs = [
        {
            "name": (m.payload or {}).get("name") if isinstance(m.payload, dict) else None,
            "role_hint": (m.payload or {}).get("role_hint") if isinstance(m.payload, dict) else None,
            "status": m.status,
        }
        for m in mutations if m.mutation_type == "entity_creation"
    ]
    pending_review = [
        {"mutation_id": m.id, "mutation_type": m.mutation_type, "rationale": m.rationale}
        for m in mutations if m.status == "proposed"
    ]

    return {
        "prose": latest.get("prose") or batch.final_result,
        "npcs": fact_sheet.get("npcs", []),
        "locations": fact_sheet.get("locations", []),
        "role_hints": fact_sheet.get("role_hints", []),
        "gains": _account_gains(mutations),
        "pending_review": pending_review,
        "germs": germs,
        "rendezvous": _account_rendezvous(mutations, db),
        "is_replay": resolution_count(pass_play) > 1,
    }


@router.get("/api/day/{batch_id}")
def get_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
    world_id = _crud._world_id(db)
    row = db.exec(
        select(Batch, PassPlay)
        .join(GameSession, GameSession.id == Batch.session_id)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .where(Batch.id == batch_id, GameSession.world_id == world_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"day {batch_id!r} not found")
    batch, pass_play = row
    result = _day_dict(batch, pass_play)
    feasibility_entry = read_latest_feasibility(pass_play)
    if feasibility_entry is not None:
        result["feasibility"] = _feasibility_dict(
            feasibility_entry["python_retained"], feasibility_entry["veto_retained"],
            feasibility_entry["reason"], feasibility_entry["cited_objective"], feasibility_entry["outcome"],
        )
    if pass_play.status == "resolved":
        result["account"] = _day_account_dict(pass_play, batch, db)
    return result


def _plan_step_dict(evaluated: EvaluatedStep, status: str) -> dict:
    return {
        "objective": evaluated.step.objective,
        "cost": evaluated.step.cost,
        "domain": evaluated.step.domain,
        "status": status,
        "requirements": [
            {"met": v.met, "current": v.current, "required": v.required, "reason": v.reason}
            for v in evaluated.verdicts
        ],
    }


def _concordance_dict(result: ConcordanceResult, germ_ids: dict[int, str], db: Session) -> dict:
    """Response shape for BRIEF-0075-c's `concordance` block. Entity ids for
    MATCHED mentions may appear; germ ids may appear; no `agenda_id` and no
    `step_id` anywhere (Scope OUT)."""
    def _name(entity_id: str) -> str:
        entity = db.get(Entity, entity_id)
        return entity.name if entity is not None else entity_id

    return {
        "matched": [
            {
                "surface_form": mm.mention.surface_form,
                "category": mm.mention.category,
                "entity_id": mm.entity_id,
                "entity_name": _name(mm.entity_id),
                "rung": mm.rung,
            }
            for mm in result.matched
        ],
        "ambiguous": [
            {
                "surface_form": am.mention.surface_form,
                "category": am.mention.category,
                "candidate_ids": list(am.candidate_ids),
                "candidate_count": len(am.candidate_ids),
            }
            for am in result.ambiguous
        ],
        "unmatched": [
            {
                "surface_form": um.mention.surface_form,
                "category": um.mention.category,
                "kind": um.mention.kind,
                "role_hint": um.mention.role_hint,
                "germ_id": germ_ids.get(id(um)),
            }
            for um in result.unmatched
        ],
        "skipped_rungs": list(result.skipped_rungs),
    }


def _extract_and_concord(
    pass_play: PassPlay, character: Character, db: Session,
) -> tuple[ConcordanceResult, dict[int, str]]:
    """Extraction + concordance + germ construction (BRIEF-0075-c), split
    out of `plan_day` for the function-length ceiling. Germs are returned
    already `db.add`-ed (staged, not committed) so the caller's single
    commit covers the plan and the germs together (Scope IN item 4,
    all-or-nothing)."""
    mentions = [
        *extract_places(pass_play.declared_action, db),
        *extract_persons(pass_play.declared_action, db),
        *extract_factions(pass_play.declared_action, db),
    ]
    concordance_result = concord(mentions, character, db)
    germs = emit_germs(concordance_result.unmatched, pass_play, db)
    person_unmatched = [um for um in concordance_result.unmatched if um.mention.category == "person"]
    germ_ids = {id(um): germ.id for um, germ in zip(person_unmatched, germs)}
    for germ in germs:
        db.add(germ)
    return concordance_result, germ_ids


def _load_plannable_day(batch_id: str, world_id: str, db: Session) -> PassPlay:
    row = db.exec(
        select(Batch, PassPlay)
        .join(GameSession, GameSession.id == Batch.session_id)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .where(Batch.id == batch_id, GameSession.world_id == world_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"day {batch_id!r} not found")
    # Annotated single-name assignment, not a tuple-unpack (single_canon_write.py's
    # static resolver tracks an ast.AnnAssign target's type but not a Tuple
    # target — `_, pass_play = row` would leave pass_play unattributable at
    # its later db.add() below).
    pass_play: PassPlay = row[1]
    if pass_play.status != "submitted":
        raise HTTPException(
            status_code=409,
            detail=f"day {batch_id!r} is not awaiting a plan (status={pass_play.status!r})",
        )
    return pass_play


def _finalize_plan(
    world_id: str, character: Character, pass_play: PassPlay, raw_steps: list, db: Session,
) -> dict:
    # BRIEF-0078-a, Scope IN item 7: anchoring runs BEFORE evaluate_requirements
    # so a dropped requirement never reaches evaluate_requirements or
    # agenda_step_requirement (E2 — reporting, never refusing: /plan still
    # returns 200 and writes the plan exactly as it does today).
    anchored_steps, dropped_report = anchor_requirements(raw_steps, character, db)
    evaluated_steps = [
        EvaluatedStep(step=step, verdicts=tuple(evaluate_requirements(step, character, db)))
        for step in anchored_steps
    ]
    budget_result = budget_cut(evaluated_steps, DAY_BUDGET_SLOTS)
    # BRIEF-0075-g, Y1: the veto runs AFTER budget_cut, on an already-legal
    # plan (R4) — its own output can only narrow `budget_result.included`
    # further, never widen it (day_feasibility.clamp_verdict, R1/R2).
    verdict = feasibility_veto(budget_result, character, pass_play.declared_action, db)
    active_step_index = 0 if verdict.veto_retained > 0 else None

    # E2: reporting, never refusing — a budget-only cut is not a block.
    blocked_index: Optional[int] = None
    blocked_text: Optional[str] = None
    if budget_result.first_excluded_index is not None:
        excluded = evaluated_steps[budget_result.first_excluded_index]
        if not excluded.met:
            blocked_index = budget_result.first_excluded_index
            blocked_text = "; ".join(v.reason for v in excluded.verdicts if not v.met)

    title = pass_play.declared_action.strip().splitlines()[0][:200]
    try:
        agenda = write_day_plan(
            db,
            world_id=world_id,
            owner_entity_id=character.id,
            title=title,
            steps=[evaluated.step for evaluated in evaluated_steps],
            active_step_index=active_step_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Germs (already staged by `_extract_and_concord`) commit in the same
    # transaction as the plan (Scope IN item 4, all-or-nothing) — never
    # added inside day_concordance.py itself (R1). The feasibility verdict
    # (item 4, observability) is recorded in the SAME transaction, exactly
    # once per pass_play, BEFORE the status move to 'resolving'.
    write_day_feasibility(db, pass_play=pass_play, verdict=verdict)
    pass_play.status = "resolving"
    pass_play.agenda_id = agenda.id  # BRIEF-0077-a: which plan this day advanced
    db.add(pass_play)
    db.commit()

    return {
        "steps": [
            _plan_step_dict(evaluated, "active" if idx == active_step_index else "pending")
            for idx, evaluated in enumerate(evaluated_steps)
        ],
        "slots_consumed": budget_result.slots_consumed,
        "slots_budget": budget_result.slots_budget,
        "first_excluded_index": budget_result.first_excluded_index,
        "feasibility": _feasibility_dict(
            verdict.python_retained, verdict.veto_retained, verdict.reason,
            verdict.cited_objective, verdict.outcome,
        ),
        "anchoring": {"dropped": dropped_report},
        "blocked_at_index": blocked_index,
        "blocked_reason": blocked_text,
    }


@router.post("/api/day/{batch_id}/plan")
def plan_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
    """Emit and persist a day plan (TICKET-0075, BRIEF-0075-b; extraction and
    concordance, BRIEF-0075-c; reconciliation, BRIEF-0075-f as corrected by
    AMENDMENT 1; dedicated plan selection, TICKET-0077/BRIEF-0077-c). ONE
    model call for the plan (F1), preceded by the extraction/concordance
    stage (C1: the resolver never authors — an unmatched person only ever
    reaches canon as a parked germ). Fail-closed: the batch must belong to
    the active world and its `pass_play.status` must be `submitted` (a
    second call on the same batch fails here — `status` is now
    `resolving`). A dedicated model call (`day_plan_select.select_plan`)
    picks which of the player's open plans, if any, the declaration
    targets — ONE OF among ALL open (active or paused) plans, never only
    the active one; `None` means the declaration opens something new, and
    the standing active plan (if any) is parked before a fresh one is
    emitted. `agenda_id`/`step_id` never appear in the response — the
    player never sees the agenda (ticket Scope OUT)."""
    world_id = _crud._world_id(db)
    pass_play = _load_plannable_day(batch_id, world_id, db)
    character = _resolve_player_character(world_id, db)

    # Extraction and concordance run BEFORE plan emission, selection or
    # reconciliation (BRIEF-0075-c, C1; ordering re-asserted by
    # BRIEF-0075-f's Wiring): the resolver never authors, and its result
    # only ever reaches either path as a resolved name or a role, never a
    # canon id the model could misuse. A failure here reports and stops —
    # no plan row, no germ row, nothing committed (Scope IN item 4).
    try:
        concordance_result, germ_ids = _extract_and_concord(pass_play, character, db)
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"day extraction failed: {exc}") from exc

    plans = day_plans.open_plans(character, db)
    try:
        selected = day_plan_select.select_plan(pass_play.declared_action, plans, db)
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"plan selection failed: {exc}") from exc
    if selected is not None:
        result = _reconcile_and_finalize(character, pass_play, selected, concordance_result, db)
    else:
        day_plans.park_active_plan(character, db)
        try:
            raw_steps = emit_plan(
                pass_play.declared_action, character, db,
                concordance_summary=plan_context(concordance_result, db),
                held_subjects_summary=held_subjects_summary(character, db),
            )
        except LlmParseError as exc:
            raise HTTPException(status_code=502, detail=f"plan emission failed: {exc}") from exc
        result = _finalize_plan(world_id, character, pass_play, raw_steps, db)

    result["concordance"] = _concordance_dict(concordance_result, germ_ids, db)
    return result


def _load_resolvable_day(batch_id: str, world_id: str, db: Session) -> tuple[Batch, PassPlay]:
    row = db.exec(
        select(Batch, PassPlay)
        .join(GameSession, GameSession.id == Batch.session_id)
        .join(PassPlay, PassPlay.batch_id == Batch.id)
        .where(Batch.id == batch_id, GameSession.world_id == world_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"day {batch_id!r} not found")
    batch: Batch = row[0]
    pass_play: PassPlay = row[1]
    # 'resolving' is the first resolve; 'resolved' is a replay (Scope IN
    # item 5) — the route says so in the response.
    if pass_play.status not in ("resolving", "resolved"):
        raise HTTPException(
            status_code=409,
            detail=f"day {batch_id!r} is not awaiting resolution (status={pass_play.status!r})",
        )
    return batch, pass_play


def _load_active_agenda(character: Character, pass_play: PassPlay, db: Session) -> Agenda:
    """The agenda this day resolves against (BRIEF-0077-a, B2). When
    `pass_play.agenda_id` is set (every day planned since this brief), it
    binds to THAT plan specifically — not required to be `active` here
    (BRIEF-0077-c may resolve a plan the same request just resumed). When it
    is NULL (every pre-BRIEF-0077-a row, and a day that never reached plan
    emission), this is the pre-BRIEF-0077-a fallback: the player's single
    `status == 'active'` agenda, 409 when absent — unchanged."""
    if pass_play.agenda_id is not None:
        agenda = db.get(Agenda, pass_play.agenda_id)
        if agenda is None or agenda.owner_entity_id != character.id:
            raise HTTPException(
                status_code=409,
                detail=f"pass_play {pass_play.id!r}'s bound agenda {pass_play.agenda_id!r} is missing or not owned by {character.id!r}",
            )
        return agenda
    agenda = db.exec(
        select(Agenda).where(Agenda.owner_entity_id == character.id, Agenda.status == "active")
    ).first()
    if agenda is None:
        raise HTTPException(
            status_code=409, detail=f"character {character.id!r} has no active agenda to resolve",
        )
    return agenda


def _guard_no_pending_agenda_step_change(agenda: Agenda, db: Session) -> None:
    """BB1 (locked with Nia): `/resolve` refuses, fail-closed, while ANY
    `agenda_step_change` proposal for this agenda is still `status=
    'proposed'` — no distinction between a mutation this SAME batch just
    emitted and one a PRIOR day emitted. This is the structural expression
    of A1's rhythm (the world does not advance while proposals about it
    are unreviewed), extended from "no direct write" to "no further
    resolution either": a REPLAY of THIS day is blocked exactly the same
    way a NEXT day's continuation is, until Nia approves or rejects what
    is already in the queue — one rule, not an exception for same-batch
    proposals. `day_resolve.py` has no business knowing the queue exists
    (`writes/pipeline.py`'s discipline, unchanged) — this precondition
    lives here, one query, never coupled into the walk itself."""
    step_ids = set(
        db.exec(select(AgendaStep.id).where(AgendaStep.agenda_id == agenda.id)).all()
    )
    if not step_ids:
        return
    pending = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.mutation_type == "agenda_step_change",
            ProposedMutation.status == "proposed",
        )
    ).all()
    pending_count = sum(
        1 for m in pending if isinstance(m.payload, dict) and m.payload.get("step_id") in step_ids
    )
    if pending_count:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{pending_count} agenda_step_change proposal(s) for {agenda.title!r} are still "
                "awaiting review — approve or reject them before resolving again"
            ),
        )


def _resolve_response(fact_sheet: FactSheet, prose: str, is_replay: bool) -> dict:
    """No `agenda_id`, no `step_id`, no fact-sheet internals beyond what the
    player should see (Scope IN item 5)."""
    return {
        "day_number": fact_sheet.day_number,
        "prose": prose,
        "npcs": [{"id": r.entity_id, "name": r.name} for r in fact_sheet.npcs],
        "locations": [{"id": r.entity_id, "name": r.name} for r in fact_sheet.locations],
        "resource_deltas": list(fact_sheet.resource_deltas),
        "knowledge_deltas": list(fact_sheet.knowledge_deltas),
        "skill_deltas": list(fact_sheet.skill_deltas),
        "is_replay": is_replay,
    }


def _concord_declaration(pass_play: PassPlay, character: Character, db: Session) -> ConcordanceResult:
    """Extraction + concordance ONLY (BRIEF-0075-d) — the `_extract_and_
    concord` precedent above minus `emit_germs`: re-emitting germs at
    resolve time would duplicate the `entity_creation` proposals `/plan`
    already staged, including on every replay. `ConcordanceResult` is
    never persisted past the call that builds it (BRIEF-0075-c), so
    `freeze_facts` needs a fresh one — same deterministic, model-free
    lookup, re-run."""
    mentions = [
        *extract_places(pass_play.declared_action, db),
        *extract_persons(pass_play.declared_action, db),
        *extract_factions(pass_play.declared_action, db),
    ]
    return concord(mentions, character, db)


def _narrate_and_judge(
    fact_sheet: FactSheet, pass_play: PassPlay, db: Session,
) -> tuple[FactSheet, str, JudgeVerdict]:
    """Narration + the T1 judge + the ONE conditional rewrite attempt
    (Scope IN items 3-4), carved out of `resolve_day` for the function-
    length ceiling (`_finalize_plan`/`write_day_plan`'s precedent). Raises
    `HTTPException` (502) on an LLM failure; returns the (possibly
    rewritten) fact sheet, the prose and the judge's final verdict —
    NEVER raises on a judge rejection, that is the caller's job (it must
    still record the rejected attempt before reporting)."""
    try:
        prose = narrate(fact_sheet, pass_play.declared_action, db)
    except LlmParseError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"day narration failed: {exc}") from exc
    verdict = judge_narration(prose, fact_sheet)
    if verdict.passed:
        return fact_sheet, prose, verdict

    delta = detect_late_delta(fact_sheet, pass_play, db)
    if delta is None:
        return fact_sheet, prose, verdict

    fact_sheet = dataclasses.replace(
        fact_sheet, authorised_names=fact_sheet.authorised_names | {delta.resolved_name},
    )
    try:
        prose = day_rewrite(fact_sheet, prose, delta, db)
    except LlmParseError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"day rewrite failed: {exc}") from exc
    verdict = judge_narration(prose, fact_sheet)
    return fact_sheet, prose, verdict


def _finalize_resolution(
    batch: Batch, pass_play: PassPlay, fact_sheet: FactSheet, prose: str, verdict: JudgeVerdict,
    is_replay: bool, outcomes: list[StepOutcome], character: Character, db: Session,
) -> dict:
    """Persist item 5's outcome and build the response — carved out of
    `resolve_day` for the function-length ceiling. A judge failure stores
    nothing final: `pass_play.status`/`batch` are left untouched (still
    `resolving`, so a retry re-enters the SAME `resolve_steps`/`narrate`
    chain), but the rejected attempt still gets ONE `history` entry (Nia
    sees the rejected prose and the reason) before the 422 — and no
    mutation is emitted for a narration the judge rejected (V1: only a
    resolution that actually stands proposes anything).

    On success (BRIEF-0075-e, V1): `emit_mutations` turns `outcomes` into
    `ProposedMutation` rows, added and committed in this SAME transaction
    as the narration/status writes — proposing, never applying (no
    `_apply_mutation` call anywhere in this chain)."""
    judge_dict = {"passed": verdict.passed, "reason": verdict.reason}
    if not verdict.passed:
        write_pass_play_resolution(
            db, pass_play=pass_play, fact_sheet=fact_sheet_dict(fact_sheet), prose=prose, judge_verdict=judge_dict,
        )
        db.add(pass_play)
        db.commit()
        raise HTTPException(status_code=422, detail=f"day narration rejected by judge: {verdict.reason}")

    batch.local_summary = prose
    batch.final_result = prose
    batch.processed_at = datetime.now(UTC)
    batch.status = BATCH_RESOLVED_STATUS
    db.add(batch)

    pass_play.status = "resolved"
    write_pass_play_resolution(
        db, pass_play=pass_play, fact_sheet=fact_sheet_dict(fact_sheet), prose=prose, judge_verdict=judge_dict,
    )
    db.add(pass_play)

    for mutation in emit_mutations(outcomes, pass_play, character, db):
        db.add(mutation)

    db.commit()

    return _resolve_response(fact_sheet, prose, is_replay)


@router.post("/api/day/{batch_id}/resolve")
def resolve_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
    """Resolve the budgeted portion of a declared day (TICKET-0075,
    BRIEF-0075-d, resolution+narration; BRIEF-0075-e, mutation emission —
    V1; BRIEF-0075-g, the feasibility veto — Y1): Python dice (`resolve_
    steps`, capped at the retained count the veto decided once at `/plan`
    time), a frozen fact sheet (`freeze_facts`), one narration call
    (`narrate`) constrained by that fact sheet, and a fail-closed Python
    judge (`judge_narration`) before anything is stored. A judge failure
    stores nothing final and reports — it never silently degrades (Scope IN
    item 4). One transaction: narration, the resolution-history append,
    both status moves, and the emitted `ProposedMutation` rows — never an
    agenda step transition (V1, BRIEF-0075-d-amendment-1): those move only
    when Nia approves.

    Fail-closed: the batch must belong to the active world, and
    `pass_play.status` must be `resolving` (first resolve) or `resolved`
    (a replay — the SAME immutable `declared_action` re-run, appending a
    SECOND `history` entry; the first stays intact). The character must
    hold an active agenda — the plan `/plan` wrote. BB1 (BRIEF-0075-f):
    the agenda must also carry NO `agenda_step_change` proposal still
    `status='proposed'` — a replay of THIS day is refused exactly like a
    NEXT day's continuation would be, until Nia clears the queue.
    """
    world_id = _crud._world_id(db)
    # Annotated single-name assignments, not a tuple-unpack
    # (single_canon_write.py's static resolver tracks an ast.AnnAssign
    # target's type but not a Tuple target — `_load_plannable_day`'s
    # precedent, same reason).
    row = _load_resolvable_day(batch_id, world_id, db)
    batch: Batch = row[0]
    pass_play: PassPlay = row[1]
    character = _resolve_player_character(world_id, db)
    agenda = _load_active_agenda(character, pass_play, db)
    _guard_no_pending_agenda_step_change(agenda, db)
    is_replay = pass_play.status == "resolved"

    # BRIEF-0075-g, Y1: the veto's retained count was decided once at
    # `/plan` time and recorded in `pass_play.history` (never re-decided
    # here, and never re-invoked on a replay — Scope OUT). `None` (no
    # feasibility entry — a plan predating this brief) leaves `resolve_
    # steps`'s own `budget_cut` untouched.
    feasibility_entry = read_latest_feasibility(pass_play)
    veto_retained = feasibility_entry.get("veto_retained") if feasibility_entry else None
    outcomes = resolve_steps(agenda, character, db, veto_retained=veto_retained)

    try:
        concordance_result = _concord_declaration(pass_play, character, db)
    except LlmParseError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"day narration concordance failed: {exc}") from exc
    fact_sheet = freeze_facts(outcomes, concordance_result, batch, character, db)

    if not outcomes:
        # BRIEF-0078-b: a step whose own requirements are unmet no longer
        # empties `outcomes` — resolve_steps appends a trailing `blocked`
        # StepOutcome for it instead. The ONE remaining legitimate empty
        # case is the feasibility veto retaining zero of Python's own
        # retained steps (`veto_retained == 0`, BRIEF-0075-g Scope IN item
        # 2) — the veto owns that day's reason, and no blocked beat is
        # invented for it; code renders it directly, exactly as before this
        # ticket.
        if veto_retained == 0 and feasibility_entry and feasibility_entry.get("python_retained", 0) > 0:
            reason = feasibility_entry.get("reason") or "jugé peu plausible en une seule journée"
            prose = f"La journée n'a pas pu commencer : {reason}"
            verdict = JudgeVerdict(
                passed=True, reason="blocked before any step — code-rendered, judge not invoked",
            )
            return _finalize_resolution(
                batch, pass_play, fact_sheet, prose, verdict, is_replay, outcomes, character, db,
            )
        # Fail-closed: the blocked band (BRIEF-0078-b) makes a step-level
        # empty result unreachable, and the veto-zero case above is already
        # handled — neither a step nor the veto explains this emptiness.
        raise HTTPException(
            status_code=500,
            detail="day resolution produced zero outcomes -- the blocked band should make this unreachable",
        )

    fact_sheet, prose, verdict = _narrate_and_judge(fact_sheet, pass_play, db)
    return _finalize_resolution(batch, pass_play, fact_sheet, prose, verdict, is_replay, outcomes, character, db)
