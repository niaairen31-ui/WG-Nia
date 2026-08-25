"""Reconciliation pass (TICKET-0075, BRIEF-0075-f — decision R1; Z4 and
AA2 correcting the original brief, per AMENDMENT 1).

A player who already owns an active `Agenda` (their standing day-plan) can
declare a new day without abandoning it. ONE model call classifies the new
declaration against the standing agenda as `continue`, `modify` or
`replace` — the model CLASSIFIES, it never edits (R1: `reconcile()` writes
nothing). The classification's EFFECT, when there is one, goes through the
ordinary mutation queue like every other day-chain proposal — never a
direct write.

The three verdicts, as corrected by AMENDMENT 1:

- **`continue` proposes NOTHING.** In the normal case there is nothing to
  activate: the applier's own cascade (BRIEF-0075-e) already promoted the
  agenda's next `pending` step to `active` when the prior step's mutation
  was approved. The only way an ACTIVE agenda can have no active step is
  the RECOVERY state (a manually-reactivated agenda), and Z4
  (`cockpit/crud/agendas.py`) repairs that at its source — by the time
  reconciliation runs, an active agenda either already has an active
  step, or has no pending steps left at all (inert — a `replace` case,
  not a `continue` one). `continue` on an inert agenda reports the plan
  exhausted and stops.
- **`modify`** re-runs `day_plan.emit_plan` with the standing agenda's
  remaining steps as context and compares the revised plan against them.
  `_apply_mutation`'s `agenda_step_change` applier accepts only
  `action in ("complete", "fail")` on the CURRENTLY ACTIVE step — it has
  no action to insert, reorder, or edit a PENDING step's objective. Any
  revised plan that differs from the standing remaining steps therefore
  needs an action the applier does not have: S2, a STOP. Only an
  IDENTICAL revised plan (no real diff — the reconciliation classification
  was a `modify` but nothing actually changed) is expressible, and it
  expresses as a no-op, same as `continue`.
- **`replace` (AA2) emits nothing and writes nothing.** The chain records
  the verdict, reports that the standing plan must be closed, names it,
  and stops the day. Nia closes it manually via the EXISTING
  `PATCH /agendas/{id}` with `status='abandoned'` — history-preserving,
  unlike `failed`, which additionally cascades every linked `npc_goal` to
  `abandoned` too (`_cascade_agenda_status_to_goals`,
  `writes/goals_agendas.py`) — the wrong side effect for a plan the player
  merely dropped rather than lost.

The pass sees the declaration, the standing agenda's title, and its
steps' `objective`/`step_order`/`status` only — no costs, no requirements,
no ids, no registry (R6): it classifies intent, nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .models import Agenda, AgendaStep, PromptTemplate
from .prompt_registry import effective_model
from .prompt_store import current_prompt

RECONCILE_VERDICTS: tuple[str, ...] = ("continue", "modify", "replace")

# Same mild repetition controls as the rest of the day chain's emission calls.
RECONCILE_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}


@dataclass(frozen=True)
class Reconciliation:
    verdict: str
    cited_step_order: int
    cited_objective: str
    rationale: str


def _load_reconcile_template(world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """`day_plan._load_day_plan_template`'s precedent, verbatim."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "day_reconcile",
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


def _render_steps(steps: list[AgendaStep]) -> str:
    return "\n".join(f"{s.step_order}. {s.objective} ({s.status})" for s in steps)


def reconcile(declaration: str, agenda: Agenda, steps: list[AgendaStep], db: Session) -> Reconciliation:
    """ONE model call (Scope IN item 1). Parsed through `llm_parse` (M6),
    then domain-validated here — strictly: a verdict outside
    `RECONCILE_VERDICTS`, or a `cited_step_order` naming no real
    `step_order` among `steps`, RAISES `LlmParseError`. NEVER a silent
    fallback to `continue` — the brief's own Invariants call that "the
    worst possible failure mode: it looks like inertia and is actually a
    swallowed error." `steps` should be every `AgendaStep` on `agenda`
    (any status) — the citation validator checks against every real
    `step_order`, not only the remaining ones, so the model can correctly
    cite an already-completed step if that is what its reasoning names."""
    template = _load_reconcile_template(agenda.world_id, db)
    if template is None:
        raise llm_parse.LlmParseError("day_reconcile: no active prompt_template for usage='day_reconcile'")
    version = current_prompt(db, template)

    user_msg = (
        version.user_template
        .replace("{agenda_title}", agenda.title)
        .replace("{declaration}", declaration)
        .replace("{steps}", _render_steps(steps))
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
        options=RECONCILE_OPTIONS,
    )
    obj = llm_parse.extract_object(raw)

    verdict = obj.get("verdict")
    if verdict not in RECONCILE_VERDICTS:
        raise llm_parse.LlmParseError(f"day_reconcile: verdict {verdict!r} not in {RECONCILE_VERDICTS}")

    cited_step_order = obj.get("cited_step_order")
    if not isinstance(cited_step_order, int) or isinstance(cited_step_order, bool):
        raise llm_parse.LlmParseError(
            f"day_reconcile: cited_step_order must be an int, got {cited_step_order!r}"
        )
    cited_step = next((s for s in steps if s.step_order == cited_step_order), None)
    if cited_step is None:
        raise llm_parse.LlmParseError(
            f"day_reconcile: cited_step_order {cited_step_order!r} names no real step on this agenda"
        )

    rationale = obj.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise llm_parse.LlmParseError("day_reconcile: missing non-empty rationale")

    return Reconciliation(
        verdict=verdict, cited_step_order=cited_step_order,
        cited_objective=cited_step.objective, rationale=rationale.strip(),
    )
