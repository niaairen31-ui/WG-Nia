"""Day declaration and plan-emission routes (TICKET-0075, BRIEF-0075-a — the
declaration socle: plumbing only; BRIEF-0075-b — plan emission and budget;
BRIEF-0075-c — extraction and concordance). A player declares a day; the
declaration is stored, listed and read back, and a plan can be emitted
against it: extraction + concordance resolve its mentions to canon ids or
roles (C1: the resolver never authors — any unmatched PERSON mention only
ever reaches canon as a PARKED `entity_creation` germ, never authored here),
then one model call (`day_plan.emit_plan`), Python-judged requirements and a
Python budget cut (F1: model proposes, code judges). No `resolve_physical`
call appears anywhere in this module (still Scope OUT of BRIEF-0075-b).

`_get_or_open_session` deliberately duplicates the M5 idiom from
`cockpit/play.py` (`_get_or_open_session`) rather than importing it: Play is
a sealed module (TICKET-0069 is its own migration), and this surface must
not couple to it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ...day_concordance import ConcordanceResult, concord, emit_germs, plan_context
from ...day_extract import extract_factions, extract_persons, extract_places
from ...day_plan import DAY_BUDGET_SLOTS, EvaluatedStep, budget_cut, emit_plan, evaluate_requirements
from ...db import get_session
from ...llm_parse import LlmParseError
from ...models import Agenda, Batch, Character, Entity, PassPlay
from ...models import Session as GameSession
from ...writes import MAX_DECLARATION_CHARS, write_batch, write_day_plan, write_pass_play
from .. import crud as _crud

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
        "day_number": batch.day_number,
        "status": pass_play.status,
        "declared_action": pass_play.declared_action,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


class DayDeclareBody(BaseModel):
    # Bound read from writes/pipeline.py rather than restated as a literal
    # (R4) -- this is a fast client-facing 422, write_pass_play's own check
    # is the structural guarantee.
    declared_action: str = Field(max_length=MAX_DECLARATION_CHARS)


@router.post("/api/day/declare")
def declare_day(body: DayDeclareBody, db: Session = Depends(get_session)) -> dict:
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
    return _day_dict(batch, pass_play)


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


def _guard_no_active_agenda(character: Character, db: Session) -> None:
    existing_agenda = db.exec(
        select(Agenda).where(Agenda.owner_entity_id == character.id, Agenda.status == "active")
    ).first()
    if existing_agenda is not None:
        raise HTTPException(
            status_code=409,
            detail=f"character {character.id!r} already holds an active agenda",
        )


def _finalize_plan(
    world_id: str, character: Character, pass_play: PassPlay, raw_steps: list, db: Session,
) -> dict:
    evaluated_steps = [
        EvaluatedStep(step=step, verdicts=tuple(evaluate_requirements(step, character, db)))
        for step in raw_steps
    ]
    budget_result = budget_cut(evaluated_steps, DAY_BUDGET_SLOTS)
    active_step_index = 0 if budget_result.included else None

    title = pass_play.declared_action.strip().splitlines()[0][:200]
    try:
        write_day_plan(
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
    # added inside day_concordance.py itself (R1).
    pass_play.status = "resolving"
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
    }


@router.post("/api/day/{batch_id}/plan")
def plan_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
    """Emit and persist a day plan (TICKET-0075, BRIEF-0075-b; extraction and
    concordance, BRIEF-0075-c). ONE model call for the plan (F1), preceded by
    the extraction/concordance stage (C1: the resolver never authors — an
    unmatched person only ever reaches canon as a parked germ). Fail-closed:
    the batch must belong to the active world, its `pass_play.status` must
    be `submitted` (a second call on the same batch fails here — `status`
    is now `resolving`), and the player must not already hold an active
    agenda (S3 — reconciliation is BRIEF-0075-f). `agenda_id`/`step_id`
    never appear in the response — the player never sees the agenda (ticket
    Scope OUT)."""
    world_id = _crud._world_id(db)
    pass_play = _load_plannable_day(batch_id, world_id, db)
    character = _resolve_player_character(world_id, db)
    _guard_no_active_agenda(character, db)

    # Extraction and concordance run BEFORE plan emission (BRIEF-0075-c, C1):
    # the resolver never authors, and its result only ever reaches the plan
    # as a resolved name or a role, never a canon id the model could misuse.
    # A failure here reports and stops — no plan row, no germ row, nothing
    # committed (Scope IN item 4).
    try:
        concordance_result, germ_ids = _extract_and_concord(pass_play, character, db)
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"day extraction failed: {exc}") from exc

    try:
        raw_steps = emit_plan(
            pass_play.declared_action, character, db,
            concordance_summary=plan_context(concordance_result, db),
        )
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"plan emission failed: {exc}") from exc

    result = _finalize_plan(world_id, character, pass_play, raw_steps, db)
    result["concordance"] = _concordance_dict(concordance_result, germ_ids, db)
    return result
