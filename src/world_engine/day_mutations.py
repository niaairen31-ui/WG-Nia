"""Mutation emission for the resolved day chain (TICKET-0075, BRIEF-0075-e,
as corrected by BRIEF-0075-e-amendment-1 and BRIEF-0075-d-amendment-1 / V1).

V1 (BRIEF-0075-d-amendment-1): the day chain PROPOSES canon changes; it
never writes them. `day_resolve.py` computes `StepOutcome` objects and
stops there — this module turns each resolved step into a
`ProposedMutation` row, always at `status='proposed'`,
`source_type='pass_play'`. Nothing here calls `_apply_mutation`, and
nothing here sets `status` to anything but `'proposed'` (R3/R4).

`EMITTED_MUTATION_TYPES` (BRIEF-0075-e-amendment-1's corrected vocabulary):
`knowledge_change`, `relation_change`, `agenda_step_change`,
`entity_creation`. `resource_change` and `agenda_creation` are OUT: under
V1, creating a plan has no world footprint and stays `write_day_plan`'s
direct write (BRIEF-0075-b); resources travel as `ledger_transfer` effects
on a step's own completion, never a parallel vocabulary. `npc_move` stays
absent (N1, R2).

The delta contract (BRIEF-0075-e-amendment-1): it travels on the
`agenda_step_change` payload's `effects` list
(`_apply_completion_effects`, `cockpit/mutations.py`, TICKET-0024/
BRIEF-0024-c) — `relation_delta`, `ledger_transfer`, `role_change`, at most
`_MAX_EFFECTS`. This module never invents an effect: there is no per-step
reward column anywhere on `AgendaStep`/`AgendaStepRequirement` to compute
one from (a `resource`-type requirement carries no counterparty entity at
all, so a `ledger_transfer` cannot even be well-formed from it; a
`relation_gte`-type requirement carries no `relation_type` and no delta
amount). Every emitted `agenda_step_change` therefore carries an EMPTY
`effects` list — Nia edits the proposed payload in the review queue
(`ApproveBody.payload`, cockpit/routes/mutations.py) to attach a concrete
effect when the day's narrative warrants one; nothing here fabricates a
number or a shape.

`relation_change` (standalone, belonging to no step) has no data source in
v1 either — kept in the vocabulary for a future source, never actually
emitted (`_emit_relation_change` always returns an empty list; the same
X1-style deferral as skill deltas). Skills have no carrier at all (X1,
`_EFFECT_TYPES` in `cockpit/mutations.py`) and are never emitted here.

`entity_creation` is NOT built by this module — it is already emitted by
`day_concordance.emit_germs` at PLAN time (BRIEF-0075-c, unchanged). It
stays a member of `EMITTED_MUTATION_TYPES` because it is part of the day
chain's mutation vocabulary as a whole; `_EMITTERS['entity_creation']` is a
documented no-op so the dispatch is a literal bijection with the constant
(R1), not a second germ-construction path (Scope OUT: persons only, still
`day_concordance.py`'s job).

The armed rendezvous (I1, corrected by BRIEF-0075-e-amendment-1): not
detected by inventing a marker. `AgendaStepRequirement` already has a
`knowledge` requirement type (`_eval_knowledge`, `day_plan.py`) gating a
step on the player ALREADY holding some `Knowledge` subject — meaning that
row must already exist for the step to have been attemptable at all. This
module treats successfully completing such a step as Nia's "a contact
found, an appointment made": deepening that SAME existing knowledge row to
`knows` is the `knowledge_change` half, emitted only for a step that
actually carried the precondition — a step with no `knowledge` requirement
produces no `knowledge_change` (an unanticipated meeting reports nothing
extra here, per the amendment). The `agenda_step_change` half needs no
special code: completing the step is the generic emission below, and
`_mutation_apply_agenda_step_change`'s existing cascade (cockpit/
mutations.py) activates the next `pending` step on approval — whose
`objective`, written at plan time by the model, IS the meeting. Nothing
here inserts a step or touches an objective.

Ordered approval (BRIEF-0075-e-amendment-1): a day resolving N steps emits
N `agenda_step_change` proposals; the applier's cascade means they must be
approved in `step_order`, or the stale guard rejects the out-of-order one.
Nothing here works around that — O1 stands.
"""

from __future__ import annotations

from typing import Callable

from sqlmodel import Session, select

from .day_resolve import StepOutcome, outcome_line
from .models import AgendaStepRequirement, Character, PassPlay, ProposedMutation

EMITTED_MUTATION_TYPES: tuple[str, ...] = (
    "knowledge_change", "relation_change", "agenda_step_change", "entity_creation",
)

# The rendezvous deepens a pre-existing knowledge row to this level on a
# successfully completed step whose own `knowledge` requirement it
# satisfied — never higher, never invented per-case; `_mutation_apply_
# knowledge_change`'s own monotone guard (cockpit/mutations.py) is the
# backstop if the row is already at or past this level.
_KNOWLEDGE_DEEPEN_LEVEL = "knows"


def _step_action(outcome: StepOutcome) -> str:
    return "fail" if outcome.band == "failure" else "complete"


def _emit_agenda_step_change(
    outcome: StepOutcome, pass_play: PassPlay, character: Character, world_id: str, db: Session,
) -> list[ProposedMutation]:
    """One `agenda_step_change` per resolved step. `effects` is always an
    empty list (see module docstring) — a construction site for R10, never
    an invented value. No subject key in the payload (R11):
    `_mutation_apply_agenda_step_change` forces the subject to the
    agenda's owner."""
    del character, db
    action = _step_action(outcome)
    payload: dict = {"step_id": outcome.agenda_step_id, "action": action, "outcome": outcome_line(outcome)}
    if action == "complete":
        payload["effects"] = []
    return [ProposedMutation(
        world_id=world_id,
        source_type="pass_play",
        pass_play_id=pass_play.id,
        mutation_type="agenda_step_change",
        payload=payload,
        status="proposed",
        proposed_by="local_ai",
        rationale=f"step {outcome.step_order} ({outcome.objective}): {outcome.band}",
    )]


def _emit_knowledge_change(
    outcome: StepOutcome, pass_play: PassPlay, character: Character, world_id: str, db: Session,
) -> list[ProposedMutation]:
    """The rendezvous half (see module docstring): deepen every `knowledge`
    -type precondition this COMPLETED step already carried. Emits nothing
    on `fail`, and nothing for a step with no `knowledge` requirement."""
    if _step_action(outcome) != "complete":
        return []
    requirements = db.exec(
        select(AgendaStepRequirement).where(
            AgendaStepRequirement.step_id == outcome.agenda_step_id,
            AgendaStepRequirement.type == "knowledge",
        )
    ).all()
    mutations: list[ProposedMutation] = []
    for req in requirements:
        mutations.append(ProposedMutation(
            world_id=world_id,
            source_type="pass_play",
            pass_play_id=pass_play.id,
            mutation_type="knowledge_change",
            payload={
                "entity_id": character.id,
                "subject": req.target_key,
                "to_level": _KNOWLEDGE_DEEPEN_LEVEL,
                "source": "day resolution",
            },
            status="proposed",
            proposed_by="local_ai",
            rationale=(
                f"step {outcome.step_order} ({outcome.objective}) resolved — "
                f"deepens knowledge of {req.target_key!r}"
            ),
        ))
    return mutations


def _emit_relation_change(
    outcome: StepOutcome, pass_play: PassPlay, character: Character, world_id: str, db: Session,
) -> list[ProposedMutation]:
    """No step-independent relation-movement source exists in v1 (see
    module docstring) — kept in the vocabulary, never emitted."""
    del outcome, pass_play, character, world_id, db
    return []


def _emit_entity_creation(
    outcome: StepOutcome, pass_play: PassPlay, character: Character, world_id: str, db: Session,
) -> list[ProposedMutation]:
    """Not this module's job — `day_concordance.emit_germs` already builds
    these at PLAN time (BRIEF-0075-c). Present only so `_EMITTERS`'s key
    set is a literal bijection with `EMITTED_MUTATION_TYPES` (R1)."""
    del outcome, pass_play, character, world_id, db
    return []


_EMITTERS: dict[str, Callable[[StepOutcome, PassPlay, Character, str, Session], list[ProposedMutation]]] = {
    "agenda_step_change": _emit_agenda_step_change,
    "knowledge_change": _emit_knowledge_change,
    "relation_change": _emit_relation_change,
    "entity_creation": _emit_entity_creation,
}


def emit_mutations(
    outcomes: list[StepOutcome], pass_play: PassPlay, character: Character, db: Session,
) -> list[ProposedMutation]:
    """Turn resolved steps into proposals (Scope IN item 1). Writes rows,
    applies nothing: no `_apply_mutation` call anywhere in this module, no
    status other than `'proposed'` (R4). Takes `outcomes`
    (`day_resolve.resolve_steps`'s return value) directly rather than the
    frozen `FactSheet` — `StepFact` deliberately carries no
    `agenda_step_id` (narration must never see one), but this function
    runs server-side and needs the real step id for the payload."""
    world_id = character.world_id
    mutations: list[ProposedMutation] = []
    for outcome in outcomes:
        for emitter in _EMITTERS.values():
            mutations.extend(emitter(outcome, pass_play, character, world_id, db))
    return mutations
