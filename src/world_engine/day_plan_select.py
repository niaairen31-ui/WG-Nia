"""Plan-selection pass (TICKET-0077, BRIEF-0077-c).

The model PROPOSES a selection; code judges it. The proposal is an ORDINAL
into a list Python built and Python owns — the model never sees or emits an
agenda id, so a hallucinated identifier cannot reach canon, and an
out-of-range ordinal is a parse failure rather than a silent fallback to
the first plan. Whether the selected plan is parked or active is a fact
this module never asks about and never reports: `day_plans.active_plan`
measures it, and `_reconcile_and_finalize` derives the transition from the
measurement.

Selection and reconciliation are deliberately TWO model calls, not one
(Nia's decision C3): this module answers "which open plan, if any, does the
declaration target" and nothing else; `day_reconcile.reconcile` then
classifies the declaration against that ONE plan's remaining steps.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .models import Agenda, AgendaStep, PromptTemplate
from .prompt_registry import effective_model
from .prompt_store import current_prompt

# Same mild repetition controls as the rest of the day chain's emission calls.
SELECT_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}


def _load_day_plan_select_template(world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """`day_reconcile._load_reconcile_template`'s precedent, verbatim."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "day_plan_select",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _first_open_objective(agenda: Agenda, db: Session) -> str:
    """The first non-terminal (`pending` or `active`) step's objective, in
    `step_order`. An open agenda with none left (all completed/failed) is
    Z4's recovery corner case, not this module's problem — it renders with
    no objective clause rather than raising."""
    step = db.exec(
        select(AgendaStep)
        .where(AgendaStep.agenda_id == agenda.id, AgendaStep.status.in_(("pending", "active")))
        .order_by(AgendaStep.step_order)
    ).first()
    return step.objective if step is not None else ""


def _render_plans(plans: list[Agenda], db: Session) -> str:
    """One line per plan, numbered from 1 in the order `plans` arrives —
    never an id (Scope IN item 1c): the model answers with the ordinal,
    exactly as `day_reconcile` cites a `step_order` rather than a `step_id`."""
    lines = []
    for idx, agenda in enumerate(plans, start=1):
        objective = _first_open_objective(agenda, db)
        suffix = f" — {objective}" if objective else ""
        lines.append(f"{idx}. {agenda.title} ({agenda.status}){suffix}")
    return "\n".join(lines)


def select_plan(declaration: str, plans: list[Agenda], db: Session) -> Optional[Agenda]:
    """ONE model call (Scope IN item 1). `plans` is Python-owned and
    Python-ordered; the model answers with an ORDINAL into it, never an id.
    Raises `llm_parse.LlmParseError` on a missing template or a malformed or
    out-of-range answer — never a silent fallback to `None` or to plan 1,
    the same discipline `day_reconcile.reconcile` applies."""
    if not plans:
        return None

    template = _load_day_plan_select_template(plans[0].world_id, db)
    if template is None:
        raise llm_parse.LlmParseError(
            "day_plan_select: no active prompt_template for usage='day_plan_select'"
        )
    version = current_prompt(db, template)

    user_msg = (
        version.user_template
        .replace("{plans}", _render_plans(plans, db))
        .replace("{declaration}", declaration)
        + "\n/no_think"
    )
    raw = ollama_client.chat(
        [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=effective_model(template, ollama_client.DEFAULT_MODEL),
        host=ollama_client.OLLAMA_HOST,
        format="json",
        options=SELECT_OPTIONS,
    )
    obj = llm_parse.extract_object(raw)

    selected = obj.get("selected")
    if selected is None or selected == 0:
        return None
    if not isinstance(selected, int) or isinstance(selected, bool):
        raise llm_parse.LlmParseError(f"day_plan_select: selected must be an int, got {selected!r}")
    if not (1 <= selected <= len(plans)):
        raise llm_parse.LlmParseError(
            f"day_plan_select: selected {selected!r} outside range 1..{len(plans)}"
        )
    return plans[selected - 1]
