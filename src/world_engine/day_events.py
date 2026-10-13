"""Journée proposes the event a completed step's objective names (TICKET-0119,
BRIEF-0119-F; decisions Bt1, M-c and V1 of the conditions series).

A quest step's objective may be an event: « Chasse : Brakk, en chasseur, 3
loups ». When the day resolves such a step as completed (the dice band
`success` or `partial`, `day_mutations._step_action`), the step's
completion condition already says what has to have happened -- so Journée
proposes that very event, beside the step's `agenda_step_change`, both
reviewed by the creator (V1: proposing, never applying). Nothing is
invented and no model is asked: every key comes from the leaf, and the row
says so -- `proposed_by='engine'` (INV-14, TICKET-0115).

For each `event` leaf of the step's completion reached through `all` only
(Q1: a leaf under `any`, `not` or `at_least` is not guaranteed) whose
subject is the one who acts (`doer`), and which is not met yet:

- its type is the leaf's (active; a retired one proposes nothing);
- the character fills the leaf's role, or the type's first active role
  accepting a character when the leaf says « any role » (none: nothing);
- each filter of the leaf fills its role (an entity, or a sorte);
- its place is the leaf's place, when it is an active location;
- its quantity, when the type counts one, is what the leaf still lacks
  (its threshold minus what is already counted in its window, at least 1);
- its changes are pre-filled from the type's effects (M-c), its title is
  the step's objective and the day's number (« Chasser trois loups — jour
  4 »: the approval's duplicate guard compares titles and places, and a
  step may need several days), its description the step's outcome line.

`emit_objective_events(outcome, pass_play, character, world_id, db)` is
`day_mutations._EMITTERS["event_creation"]`. Reads only; the rows it
returns are added by the caller (`routes/day._finalize_resolution`).
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from .condition_forms import counted_events
from .conditions import and_path_leaves, for_step, leaf_since, read_condition
from .day_plan import plan_bindings
from .day_resolve import StepOutcome, outcome_line
from .event_changes import type_changes
from .event_vocab import EVENT_FORM, EventTypeView, role_accepts, type_view
from .models import AgendaStep, Batch, Character, Entity, PassPlay, ProposedMutation


def _role_id(view: EventTypeView, role_id: Optional[str]) -> Optional[str]:
    if role_id:
        role = view.role(role_id)
        return role.id if role is not None and role.status == "active" else None
    first = next((r for r in view.active_roles() if role_accepts(r, "character")), None)
    return first.id if first is not None else None


def _place(db: Session, world_id: str, entity_id: Optional[str]) -> Optional[str]:
    place = db.get(Entity, entity_id) if entity_id else None
    if place is None or place.world_id != world_id or place.type != "location" or place.status != "active":
        return None
    return place.id


def _payload(db: Session, world_id: str, view: EventTypeView, req, character: Character, step: AgendaStep,
             outcome: StepOutcome, quantity: Optional[int], title: str) -> Optional[dict]:
    role_id = _role_id(view, req.value)
    if role_id is None:
        return None
    participants = [{"role_id": role_id, "role": view.role(role_id).name, "entity_id": character.id,
                     "sorte_id": None, "sorte_name": None, "secret": None}]
    for f in req.filters:
        role = view.role(f.role_id)
        if role is None or role.status != "active":
            continue
        participants.append({"role_id": role.id, "role": role.name, "entity_id": f.entity_id,
                             "sorte_id": f.sorte_id, "sorte_name": None, "secret": None})
    return {
        "title": title, "description": outcome_line(outcome), "type_id": view.id,
        "type_name": view.name, "participants": participants, "quantity": quantity,
        "location_id": _place(db, world_id, req.target_entity_id),
        "state_changes": type_changes(db, world_id, view, [(p["role_id"], p["entity_id"]) for p in participants]),
    }


def emit_objective_events(
    outcome: StepOutcome, pass_play: PassPlay, character: Character, world_id: str, db: Session,
) -> list[ProposedMutation]:
    """The events a completed step's objective names (see the module
    docstring), each one `event_creation` at `status='proposed'`."""
    from .day_mutations import _step_action

    if _step_action(outcome) != "complete":
        return []
    step = db.get(AgendaStep, outcome.agenda_step_id)
    completion = read_condition(db, role="completion", agenda_step_id=outcome.agenda_step_id)
    if step is None or completion is None:
        return []
    bindings = for_step(plan_bindings(step.agenda_id, character, db), step)
    batch = db.get(Batch, pass_play.batch_id)
    title = f"{step.objective} — jour {batch.day_number}" if batch is not None else step.objective
    mutations: list[ProposedMutation] = []
    for req in and_path_leaves(completion):
        if req.type != EVENT_FORM or req.subject_role != "doer":
            continue
        view = type_view(db, req.target_key)
        if view is None or view.world_id != world_id or view.status != "active":
            continue
        since_at, unbound = leaf_since(req, bindings)
        counted = 0 if unbound else sum(q or 1 for _e, _f, q in counted_events(db, req, character.id, since_at))
        lacking = (req.threshold or 1) - counted
        if lacking <= 0:
            continue
        payload = _payload(db, world_id, view, req, character, step, outcome,
                           lacking if view.counts_quantity else None, title)
        if payload is None:
            continue
        mutations.append(ProposedMutation(
            world_id=world_id,
            source_type="pass_play",
            pass_play_id=pass_play.id,
            mutation_type="event_creation",
            target_table="event",
            payload=payload,
            status="proposed",
            # TICKET-0115 (B2): code proposed it, no model -- INV-14.
            proposed_by="engine",
            rationale=(f"step {outcome.step_order} ({outcome.objective}) completed -- its objective is the event "
                       f"« {view.name} »"),
        ))
    return mutations
