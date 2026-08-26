"""Reconciliation finalizers, relocated from `cockpit/routes/day.py` for
module-budget headroom (TICKET-0077, BRIEF-0077-a) — the
`models/config.py::AgendaStep` relocation precedent. Byte-identical
otherwise: `_reconciliation_dict`, `_finalize_continue`,
`_revised_plan_matches_remaining`, `_finalize_modify`, `_finalize_replace`,
`_reconcile_and_finalize`, in that order.
"""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException
from sqlmodel import Session, select

from ..day_concordance import ConcordanceResult, plan_context
from ..day_plan import emit_plan
from ..day_reconcile import Reconciliation, reconcile
from ..llm_parse import LlmParseError
from ..models import Agenda, AgendaStep, Character, PassPlay


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


def _finalize_continue(pass_play: PassPlay, agenda: Agenda, recon: Reconciliation, db: Session) -> dict:
    """AMENDMENT 1: `continue` proposes NOTHING — a classification with no
    structural effect. The day proceeds against the standing agenda's
    already-active step. Z4 (`cockpit/crud/agendas.py`) guarantees that an
    ACTIVE agenda either already has an active step, or has no pending
    step left at all (inert) — so `active_step is None` here can only mean
    the latter: the plan is exhausted, and the verdict should have been
    `replace`."""
    active_step = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda.id, AgendaStep.status == "active")
    ).first()
    if active_step is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"the standing plan {agenda.title!r} has no active or pending step left — close it "
                "(PATCH its status to 'abandoned') before declaring again"
            ),
        )
    pass_play.status = "resolving"
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
    db.add(pass_play)
    db.commit()
    return {"reconciliation": _reconciliation_dict(recon, [])}


def _finalize_replace(agenda: Agenda, recon: Reconciliation) -> dict:
    """AA2: `replace` emits nothing and writes nothing — always raises.
    Nia closes the standing plan manually (`PATCH /agendas/{id}` ->
    `'abandoned'`, history-preserving); the NEXT declaration then finds no
    active agenda and takes the fresh-plan path unchanged."""
    del recon  # the verdict is already known to the caller; nothing more to record
    raise HTTPException(
        status_code=409,
        detail=(
            f"reconciliation verdict is 'replace': the standing plan {agenda.title!r} must be "
            "closed (PATCH its status to 'abandoned') before a new plan can start"
        ),
    )


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

    # R2 (verify): the dispatch's key set equals RECONCILE_VERDICTS, both
    # directions — a real dict, not an if/elif chain, so the bijection is
    # a static, checkable fact.
    handlers: dict[str, Callable[[], dict]] = {
        "continue": lambda: _finalize_continue(pass_play, agenda, recon, db),
        "modify": lambda: _finalize_modify(
            agenda.world_id, character, pass_play, agenda, steps, recon, concordance_result, db,
        ),
        "replace": lambda: _finalize_replace(agenda, recon),
    }
    return handlers[recon.verdict]()
