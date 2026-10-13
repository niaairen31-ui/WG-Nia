"""What a step's own condition said when the creator reviewed its change (TICKET-0115, BRIEF-0115-B; decision C1 of the conditions series' dashboard, for M2).

`step_verdict(db, mutation_type, payload)` is read by the four review paths
of `cockpit/routes/mutations.py` BEFORE anything is applied, so the verdict
is the canon the creator was looking at:

- not an `agenda_step_change`: None (the column stays NULL);
- `complete` is judged on the step's `completion` condition, `fail` on its
  `failure` condition (M1 and H1: shown, never acting), with the bindings
  Journée uses (`day_plan.plan_bindings`, `conditions.for_step`): `met`,
  `unmet` or `unknown` (R1);
- `none`: the step has no such condition;
- `not_judged`: no step id, no such step, an action that is neither, an
  agenda whose owner is not a character (a faction's agenda has no one to
  bind as `doer`), or a stored condition that cannot be read.

Reads only.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session

from .conditions import evaluate, for_step, read_condition
from .day_plan import plan_bindings
from .models import Agenda, AgendaStep, Character

ROLE_BY_ACTION: dict[str, str] = {"complete": "completion", "fail": "failure"}
NOT_JUDGED = "not_judged"
NO_CONDITION = "none"


def step_verdict(db: Session, mutation_type: str, payload: Any) -> Optional[str]:
    """The verdict to record with a review (see the module docstring)."""
    if mutation_type != "agenda_step_change":
        return None
    payload = payload if isinstance(payload, dict) else {}
    role = ROLE_BY_ACTION.get(payload.get("action"))
    step = db.get(AgendaStep, payload["step_id"]) if isinstance(payload.get("step_id"), str) else None
    if role is None or step is None:
        return NOT_JUDGED
    agenda = db.get(Agenda, step.agenda_id)
    character = db.get(Character, agenda.owner_entity_id) if agenda is not None else None
    if character is None:
        return NOT_JUDGED
    try:
        tree = read_condition(db, role=role, agenda_step_id=step.id)
    except ValueError:
        return NOT_JUDGED
    if tree is None:
        return NO_CONDITION
    verdict = evaluate(tree, for_step(plan_bindings(agenda.id, character, db), step), db)
    return verdict.state if verdict is not None else NO_CONDITION
