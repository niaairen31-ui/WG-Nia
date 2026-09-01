"""Reconciliation finalizers, relocated from `cockpit/routes/day.py` for
module-budget headroom (TICKET-0077, BRIEF-0077-a) — the
`models/config.py::AgendaStep` relocation precedent. Byte-identical
otherwise: `_reconciliation_dict`, `_finalize_continue`,
`_revised_plan_matches_remaining`, `_finalize_modify`, `_finalize_replace`,
`_reconcile_and_finalize`, in that order.

`_reconcile_and_finalize` (BRIEF-0077-c) now takes the plan `day_plan_select`
chose rather than assuming the single active agenda, and dispatches on an
`action` — `continue`/`modify`/`replace`/`resume` — derived from the
model's three-value verdict plus the selected plan's MEASURED status
(`day_reconcile.plan_action`). `resume` swaps which plan is active before
dispatch and reuses `continue`'s handler unchanged.

`_refuse_unstarted_plan` (TICKET-0080, BRIEF-0080-b) is defined immediately
BEFORE `_finalize_continue`, which is now the only caller: the single
conflated 409 the guard used to raise directly is split into two verdicts
that name their own cause — EXHAUSTED (409) versus UNSTARTED (422, the
plan is intact).
"""

from __future__ import annotations

from typing import Callable, NoReturn

from fastapi import HTTPException
from sqlmodel import Session, select

from .. import day_plans
from ..day_concordance import ConcordanceResult, plan_context
from ..day_plan import emit_plan, evaluate_agenda_step
from ..day_reconcile import Reconciliation, plan_action, reconcile
from ..day_resolve import requirement_detail_fr
from ..llm_parse import LlmParseError
from ..models import Agenda, AgendaStep, Character, PassPlay
from ..writes import write_agenda_status


def _reconciliation_dict(recon: Reconciliation, mutation_ids: list[str]) -> dict:
    """No `agenda_id`, no `step_id` (ticket-wide Scope OUT) — the verdict,
    the cited step's OBJECTIVE, the rationale, and any mutation ids
    proposed (Wiring, Scope IN item 3)."""
    return {
        "verdict": recon.verdict,
        "cited_objective": recon.cited_objective,
        "rationale": recon.rationale,
        "mutation_ids": mutation_ids,
    }


def _refuse_unstarted_plan(character: Character, agenda: Agenda, db: Session) -> NoReturn:
    """The guard asserts, it does not write (BRIEF-0080-b): no `db.add`, no
    `write_*`, no `db.commit` here — any repair belongs at the transition
    (BRIEF-0080-a) or in G3, never here. Two failure modes, conflated into
    one message before this brief: EXHAUSTED (no pending step either — 409,
    closure is the right remedy) versus UNSTARTED (a pending step exists,
    lowest `step_order`, but was never activated — 422, the plan is intact
    and the first remaining step's unmet requirement is the true reason)."""
    pending_step = db.exec(
        select(AgendaStep)
        .where(AgendaStep.agenda_id == agenda.id, AgendaStep.status == "pending")
        .order_by(AgendaStep.step_order)
    ).first()
    if pending_step is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"the standing plan {agenda.title!r} has no step left at all - every step is "
                "completed or failed. Close it (PATCH its status to 'completed' or 'abandoned') "
                "before declaring again."
            ),
        )
    evaluated = evaluate_agenda_step(pending_step, character, db)
    unmet = [requirement_detail_fr(v) for v in evaluated.verdicts if not v.met]
    detail = "; ".join(unmet) if unmet else (
        "aucun prerequis non satisfait - le veto de faisabilite a juge l'action elle-meme irrealisable"
    )
    raise HTTPException(
        status_code=422,
        detail=(
            f"the standing plan {agenda.title!r} has not started: its first remaining step "
            f"({pending_step.objective!r}) was judged infeasible when the plan was created and no "
            f"step is active. Reason: {detail}. The plan is intact - do NOT abandon it."
        ),
    )


def _finalize_continue(
    character: Character, pass_play: PassPlay, agenda: Agenda, recon: Reconciliation, db: Session,
) -> dict:
    """AMENDMENT 1: `continue` proposes NOTHING — a classification with no
    structural effect. The day proceeds against the standing agenda's
    already-active step. BRIEF-0080-a bound the pending-step repair to the
    `-> active` transition itself, so an active agenda reaching here with
    no active step means that repair found nothing to promote —
    `_refuse_unstarted_plan` (BRIEF-0080-b) names which of the two distinct
    failure modes that actually is, rather than the single false message
    this function used to raise directly."""
    active_step = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda.id, AgendaStep.status == "active")
    ).first()
    if active_step is None:
        _refuse_unstarted_plan(character, agenda, db)
    pass_play.status = "resolving"
    pass_play.agenda_id = agenda.id  # BRIEF-0077-a: which plan this day advanced
    db.add(pass_play)
    db.commit()
    return {"reconciliation": _reconciliation_dict(recon, [])}


def _revised_plan_matches_remaining(revised: list, remaining: list[AgendaStep]) -> bool:
    """Pure comparison (Scope IN item 2, `modify`): the ONLY diff
    `_mutation_apply_agenda_step_change` can express is completing or
    failing the CURRENTLY ACTIVE step — it has no action to insert,
    reorder or edit a PENDING one. An identical revised plan (same count,
    same objectives in order) is therefore the only expressible outcome;
    anything else is S2."""
    if len(revised) != len(remaining):
        return False
    return all(r.objective.strip() == s.objective.strip() for r, s in zip(revised, remaining))


def _finalize_modify(
    world_id: str, character: Character, pass_play: PassPlay, agenda: Agenda,
    steps: list[AgendaStep], recon: Reconciliation, concordance_result: ConcordanceResult, db: Session,
) -> dict:
    """AMENDMENT 1: re-run `emit_plan` with the standing agenda's remaining
    steps as context; only an IDENTICAL revised plan is expressible (no
    action exists to insert/reorder/edit a pending step) — anything else
    is S2, a STOP, per the brief's own Scope OUT ("if the diff needs an
    action the applier does not have, STOP")."""
    del world_id  # unused: modify emits nothing, so no owner_entity_id write happens here
    remaining = [s for s in steps if s.status in ("active", "pending")]
    remaining_summary = "Étapes restantes du plan en cours :\n" + "\n".join(
        f"{s.step_order}. {s.objective}" for s in remaining
    )
    try:
        revised_steps = emit_plan(
            pass_play.declared_action, character, db,
            concordance_summary=plan_context(concordance_result, db),
            standing_steps_summary=remaining_summary,
        )
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"plan revision failed: {exc}") from exc

    if not _revised_plan_matches_remaining(revised_steps, remaining):
        raise HTTPException(
            status_code=422,
            detail=(
                "reconciliation verdict is 'modify' but the revised plan cannot be expressed as "
                "agenda_step_change mutations — no action exists to insert, reorder or edit a "
                "pending step"
            ),
        )

    pass_play.status = "resolving"
    pass_play.agenda_id = agenda.id  # BRIEF-0077-a: which plan this day advanced
    db.add(pass_play)
    db.commit()
    return {"reconciliation": _reconciliation_dict(recon, [])}


def _finalize_replace(
    world_id: str, character: Character, pass_play: PassPlay, agenda: Agenda,
    recon: Reconciliation, concordance_result: ConcordanceResult, db: Session,
) -> dict:
    """AA2, superseded by TICKET-0077/BRIEF-0077-a (A1): `replace` no longer
    refuses — it PARKS the standing plan and opens a fresh one in its place,
    one transaction: `day_plans.park_active_plan` -> `emit_plan` (same
    `concordance_summary` the fresh-plan path uses) -> `_finalize_plan`
    unchanged. `_finalize_plan` stays in `routes/day.py` (not moved here by
    BRIEF-0077-a item 5) — reached via a lazy import to avoid a module
    cycle (`play_stream`/`play.py` precedent, `import_cycle.py`'s sanctioned
    idiom). A failed emission (`LlmParseError`) rolls back the park with the
    rest of the transaction, leaving the standing plan `active`, never
    orphaned mid-park."""
    from .routes import day as _day

    day_plans.park_active_plan(character, db)
    try:
        raw_steps = emit_plan(
            pass_play.declared_action, character, db,
            concordance_summary=plan_context(concordance_result, db),
        )
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"plan emission failed: {exc}") from exc

    result = _day._finalize_plan(world_id, character, pass_play, raw_steps, db)
    result["reconciliation"] = _reconciliation_dict(recon, [])
    return result


def _reconcile_and_finalize(
    character: Character, pass_play: PassPlay, agenda: Agenda,
    concordance_result: ConcordanceResult, db: Session,
) -> dict:
    steps = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda.id).order_by(AgendaStep.step_order)
    ).all()
    try:
        recon = reconcile(pass_play.declared_action, agenda, steps, db)
    except LlmParseError as exc:
        raise HTTPException(status_code=502, detail=f"reconciliation failed: {exc}") from exc

    # BRIEF-0077-c: `selected_status` is read BEFORE any write, and
    # `plan_action` maps the model's verdict plus that MEASURED status onto
    # the dispatch action — `resume` is derived, never reported by the model.
    selected_status = agenda.status
    action = plan_action(recon.verdict, selected_status)
    if action != "replace" and selected_status == "paused":
        # Swap: park whichever plan is currently active, then activate the
        # selected (paused) one. The park runs first so `write_agenda_status`'s
        # one-active-per-character guard cannot normally fire here; if it
        # somehow does, its own message becomes the 409 detail.
        day_plans.park_active_plan(character, db)
        try:
            write_agenda_status(db, agenda=agenda, status="active")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        db.flush()

    # R2 (verify): the dispatch's key set equals EXPECTED_PLAN_ACTIONS, both
    # directions — a real dict, not an if/elif chain, so the bijection is
    # a static, checkable fact.
    handlers: dict[str, Callable[[], dict]] = {
        "continue": lambda: _finalize_continue(character, pass_play, agenda, recon, db),
        "modify": lambda: _finalize_modify(
            agenda.world_id, character, pass_play, agenda, steps, recon, concordance_result, db,
        ),
        "replace": lambda: _finalize_replace(
            agenda.world_id, character, pass_play, agenda, recon, concordance_result, db,
        ),
    }
    # `resume` reuses `continue`'s handler UNCHANGED (Scope IN item 5e): a
    # resumed plan's content doesn't change, only which plan is active does
    # — the distinct key is what makes the action visible to dispatch and
    # to R12, not a different code path.
    handlers["resume"] = handlers["continue"]
    result = handlers[action]()
    result["reconciliation"]["action"] = action
    return result
