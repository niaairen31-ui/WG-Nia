"""Step resolution and the frozen fact sheet (TICKET-0075, BRIEF-0075-d —
decisions B4-as-amended and T1; dice are Python, never a model — as
corrected by BRIEF-0075-d-amendment-1, decision V1).

Scope IN item 1 (step resolution): `resolve_steps` re-evaluates the
character's active `Agenda` (the "plan" — every REMAINING `agenda_step`
row plus its `agenda_step_requirement` rows) EVERY call, through the SAME
`evaluate_requirements`/`budget_cut` pair `day_plan.py` uses at emission
time. This is deliberate: a REPLAY (Scope IN item 5) re-derives
requirement verdicts against current world state and may re-roll a step
that already resolved once.

**The remaining-work invariant** (BRIEF-0075-f, decision BB1):
`_load_evaluated_steps` walks only steps whose `status` is NOT `completed`
or `failed` — a step that has already reached a TERMINAL status is never
re-included in a later `budget_cut` walk, on this call or any future one.
This is safe for REPLAY: under V1 (below), this module writes no canon —
an `AgendaStep.status` only ever reaches `completed`/`failed` when Nia
APPROVES the corresponding `agenda_step_change` mutation
(`_mutation_apply_agenda_step_change`, `cockpit/mutations.py`), an action
structurally decoupled from `/resolve` itself. A REPLAY (calling `/resolve`
again before that approval) therefore never encounters a step that moved
out from under it — every step it re-rolls is still exactly as `pending`/
`active` as it was on the first call. Multi-day CONTINUATION (BRIEF-0075-f)
is the case this invariant actually protects: once a PRIOR day's step is
approved (now `completed`), a LATER day's walk must never re-include it —
without this filter, `budget_cut`'s greedy walk (always starting at the
lowest `step_order` in `ordered_steps`) would re-roll the same completed
step forever, and the day could never progress past it. (The resulting
mutation would still be REJECTED at approval time by the applier's stale
guard — `step.status != "active"` — so canon safety never depended on this
invariant; only the day's own narration and dice did.)

V1 (BRIEF-0075-d-amendment-1): this module writes NO canon. The original
brief had `persist_step_outcomes` transition `AgendaStep.status` directly —
that was wrong, because it made every `agenda_step_change` proposal
BRIEF-0075-e emits a dead one (the step is no longer `active` by the time
the proposal reaches the queue). The boundary is EMPTY FOOTPRINT vs. WORLD
FOOTPRINT: creating a plan (`write_day_plan`, BRIEF-0075-b) has no world
footprint and stays a direct write; completing a step carries `effects` and
advances the agenda, so it goes through the queue, always. `AgendaStep.
status`, `outcome` and `change_history` move only when Nia approves an
`agenda_step_change` (`day_mutations.py`, BRIEF-0075-e).

The dice roll is `resolve_physical` (M1, `resolution.py`); this module
contains no `randint` call of its own (R1). The truncation logic itself
(`_truncate_on_failure`) is pure — no `db`, `select(`, `chat(`, `datetime`
or `randint` in its body (R2) — everything it needs (the band, already
decided by `resolve_physical`) is precomputed by its impure caller.

There is no "opposed NPC" concept on an `agenda_step`/`agenda_step_requirement`
(unlike the live Play physical branch, `play_physical.py`) — a day-plan step
names no opposing character. D2 (NPC opposition tier) therefore resolves to
a constant: `npc_tier` is always 0 for a day step. This is not an
ambiguity between two derivations (the brief's STOP condition, S3); it is
the single derivation found (`play_physical.py`'s `character.physical_tier`
read, gated on an `opposed_npc_id` this schema never carries) reducing to
its `npc_tier is None -> 0` fallback because the gate is never true here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session, select

from .day_concordance import ConcordanceResult
from .day_plan import (
    DAY_BUDGET_SLOTS,
    BudgetResult,
    EvaluatedStep,
    Verdict as RequirementVerdict,
    budget_cut,
    evaluate_agenda_step,
)
from .models import (
    Agenda,
    AgendaStep,
    Batch,
    Character,
    Entity,
    Skill,
)
from .resolution import Verdict, resolve_physical

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class StepOutcome:
    agenda_step_id: str
    step_order: int
    objective: str
    domain: Optional[str]
    # None is the explicit "no roll" marker (the step's domain was NULL).
    verdict: Optional[Verdict]
    # "success" | "partial" | "failure" are resolve_physical's own three
    # (M1, rolled); "blocked" (BRIEF-0078-b, BLOCKED_BAND) is the fourth,
    # assigned by this module ONLY — never rolled, never produced by
    # resolution.py.
    band: str
    requirement_verdicts: tuple[RequirementVerdict, ...]
    canon_ids: tuple[str, ...]


@dataclass(frozen=True)
class NamedRef:
    entity_id: str
    name: str


@dataclass(frozen=True)
class StepFact:
    objective: str
    band: str
    dice: Optional[tuple[int, int]]
    modifier: Optional[int]
    total: Optional[int]
    # French, code-built (requirement_detail_fr) — set only for a `blocked`
    # step; None for every other band. Defaulted so every pre-existing
    # construction stays valid (BRIEF-0078-b Scope IN item 2).
    blocked_detail: Optional[str] = None


@dataclass(frozen=True)
class FactSheet:
    world_id: str
    day_number: int
    character_name: str
    steps: tuple[StepFact, ...]
    npcs: tuple[NamedRef, ...]
    locations: tuple[NamedRef, ...]
    # Role hints for persons AND places the concordance pass (BRIEF-0075-c)
    # never resolved to a canon id — the narration renders these as
    # functions, never as invented names (they are explicitly NOT in
    # authorised_names). Places widened in live-testing: an unresolved
    # place with no role hint at all (e.g. "le marché") was never told to
    # stay generic, so the model capitalized it into what read as an
    # invented proper noun — the judge was right to reject that; the fix
    # is telling the model, not loosening the judge.
    role_hints: tuple[str, ...]
    # Computed deltas the outcomes imply, NOT yet emitted as mutations
    # (Scope OUT — BRIEF-0075-e owns emission). Empty in this brief: no
    # delta-computation rule is specified here, and inventing one would be
    # a house-rule this brief was not asked to make. The fields exist so
    # -e populates them against a stable fact-sheet contract, not so it
    # invents the contract too.
    resource_deltas: tuple = field(default_factory=tuple)
    knowledge_deltas: tuple = field(default_factory=tuple)
    skill_deltas: tuple = field(default_factory=tuple)
    authorised_names: frozenset[str] = field(default_factory=frozenset)


@dataclass
class _RolledStep:
    agenda_step: AgendaStep
    evaluated: EvaluatedStep
    verdict: Optional[Verdict]
    band: str
    canon_ids: tuple[str, ...]


def _step_player_tier(character: Character, domain: str, db: Session) -> int:
    """`play_physical.py`'s base-domain derivation (D1), verbatim: a day
    step's `domain` is always a base domain (`day_plan._validate_step`
    rejects anything else) — the custom-skill branch that precedent also
    has never applies here, so it is not reproduced."""
    skill_row = db.exec(
        select(Skill).where(
            Skill.character_id == character.id,
            Skill.domain == domain,
            Skill.skill_definition_id.is_(None),
        )
    ).first()
    return skill_row.tier if skill_row else 0


_TERMINAL_AGENDA_STEP_STATUSES = ("completed", "failed")

# BRIEF-0078-b Scope IN item 1: the fourth StepOutcome.band, assigned by
# this module only (resolve_physical keeps its own three — resolution.py
# is not touched).
BLOCKED_BAND: str = "blocked"


def _load_evaluated_steps(
    agenda: Agenda, character: Character, db: Session,
) -> tuple[list[AgendaStep], list[EvaluatedStep]]:
    """The agenda's REMAINING work only (BB1, module docstring): steps
    already at a terminal status are excluded from the walk, on this call
    and every future one — see the module docstring for why this is safe
    under REPLAY and necessary for multi-day continuation."""
    ordered_steps = db.exec(
        select(AgendaStep)
        .where(AgendaStep.agenda_id == agenda.id, AgendaStep.status.not_in(_TERMINAL_AGENDA_STEP_STATUSES))
        .order_by(AgendaStep.step_order)
    ).all()
    evaluated_steps: list[EvaluatedStep] = []
    for agenda_step in ordered_steps:
        evaluated_steps.append(evaluate_agenda_step(agenda_step, character, db))
    return ordered_steps, evaluated_steps


def _roll_included_steps(
    ordered_steps: list[AgendaStep], included: tuple[EvaluatedStep, ...], character: Character, db: Session,
) -> list[_RolledStep]:
    """Impure: reads the player's tier and calls `resolve_physical` (the
    ONLY randint call in the day chain, R1) for every domain-bearing
    included step. `included` is always a prefix of `ordered_steps`
    (`budget_cut` only ever appends then breaks), so positional zip is
    safe."""
    rolled: list[_RolledStep] = []
    for agenda_step, evaluated in zip(ordered_steps, included):
        canon_ids = tuple(sorted({
            r.target_entity_id for r in evaluated.step.requirements if r.target_entity_id
        }))
        if evaluated.step.domain is None:
            verdict = None
            band = "success"
        else:
            player_tier = _step_player_tier(character, evaluated.step.domain, db)
            verdict = resolve_physical(evaluated.step.domain, player_tier, npc_tier=0)
            band = verdict.band
        rolled.append(_RolledStep(
            agenda_step=agenda_step, evaluated=evaluated, verdict=verdict, band=band, canon_ids=canon_ids,
        ))
    return rolled


def _truncate_on_failure(rolled: list[_RolledStep]) -> list[StepOutcome]:
    """Pure (R2): every input is already computed by the caller. A
    `failure` band stops the walk at that step — it and every later step
    stay unattempted (Scope IN item 1)."""
    outcomes: list[StepOutcome] = []
    for item in rolled:
        outcomes.append(StepOutcome(
            agenda_step_id=item.agenda_step.id,
            step_order=item.agenda_step.step_order,
            objective=item.evaluated.step.objective,
            domain=item.evaluated.step.domain,
            verdict=item.verdict,
            band=item.band,
            requirement_verdicts=item.evaluated.verdicts,
            canon_ids=item.canon_ids,
        ))
        if item.band == "failure":
            break
    return outcomes


# BRIEF-0078-b Scope IN item 3: player-facing French for a blocked step's
# requirement, keyed on `Verdict.type` (BRIEF-0078-a). No English machine
# text from `Verdict.reason` may reach a player — this dict is the ONLY
# source of a blocked step's rendered reason.
_BLOCKED_DETAIL_FR: dict[str, str] = {
    "knowledge": "il lui manque encore ce qu'il faut savoir sur « {required} »",
    "resource": "il ne dispose pas des moyens nécessaires",
    "relation_gte": "ses appuis ne sont pas encore assez solides pour cela",
    "location_reachable": "l'endroit n'est pas accessible depuis là où il se trouve",
}


def requirement_detail_fr(verdict: RequirementVerdict) -> str:
    """Pure: `verdict.type` -> player-facing French. Fail-closed on an
    unknown type — the same posture `evaluate_requirements` already takes
    (`day_plan.py`'s `_EVALUATORS.get(...) is None` branch)."""
    template = _BLOCKED_DETAIL_FR.get(verdict.type)
    if template is None:
        raise ValueError(f"day_resolve: unknown requirement type {verdict.type!r}")
    return template.format(required=verdict.required)


def _append_blocked_step(
    ordered_steps: list[AgendaStep],
    evaluated_steps: list[EvaluatedStep],
    budget_result: BudgetResult,
    rolled: list[_RolledStep],
    outcomes: list[StepOutcome],
) -> None:
    """Pure (no `db`, `select(`, `chat(`, `datetime`, `randint` — everything
    it needs is precomputed by `resolve_steps`). Appends AT MOST ONE
    `StepOutcome` to `outcomes`, in place, and only when all three
    conjuncts hold (Scope IN item 4):

    1. the budget cut actually excluded a step for being UNMET (a
       budget-only cut is not a block);
    2. the feasibility veto did not truncate further than that excluded
       step — when it did, the veto owns the day's reason;
    3. `_truncate_on_failure` did not already stop the walk on an earlier
       FAILURE — that failure is what stopped the day, not this step's gate.
    """
    first_excluded = budget_result.first_excluded_index
    if first_excluded is None or evaluated_steps[first_excluded].met:
        return
    if len(rolled) != first_excluded:
        return
    if len(outcomes) != len(rolled):
        return
    agenda_step = ordered_steps[first_excluded]
    evaluated = evaluated_steps[first_excluded]
    canon_ids = tuple(sorted({
        r.target_entity_id for r in evaluated.step.requirements if r.target_entity_id
    }))
    outcomes.append(StepOutcome(
        agenda_step_id=agenda_step.id,
        step_order=agenda_step.step_order,
        objective=evaluated.step.objective,
        domain=evaluated.step.domain,
        verdict=None,
        band=BLOCKED_BAND,
        requirement_verdicts=evaluated.verdicts,
        canon_ids=canon_ids,
    ))


def resolve_steps(
    agenda: Agenda, character: Character, db: Session, *, veto_retained: Optional[int] = None,
) -> list[StepOutcome]:
    """Resolve the budgeted portion of `agenda`'s plan (Scope IN item 1).
    `agenda` is the character's currently active `Agenda` — the "plan" of
    the brief's signature. A step whose own requirements are unmet no
    longer empties the result (BRIEF-0078-b): it becomes a single trailing
    `blocked` outcome (`_append_blocked_step`), an OUTCOME rather than an
    absence. The result is still an EMPTY list in one legitimate case: the
    feasibility veto retained zero steps (`veto_retained == 0`) while
    Python itself retained at least one — the veto owns that day's reason,
    and no blocked beat is invented for it (the caller keeps its own
    code-rendered prose for that case, unchanged from before this brief).

    `veto_retained` (BRIEF-0075-g, decision Y1) is the feasibility veto's
    OWN retained count, decided once at `/plan` time and read back by the
    caller from `pass_play.history` (`writes.read_latest_feasibility`) —
    never re-decided here. It is a FURTHER truncation applied on top of
    `budget_cut`'s own output, never a change to what `budget_cut` computes
    or to any requirement verdict (S4 stands: `budget_cut`'s result is
    still exactly what every prerequisite/budget judgment produces; the
    veto only ever narrows the PREFIX of it that actually gets rolled,
    identically to how it narrowed the plan at `/plan` time). `None` (no
    feasibility entry recorded — a plan predating this brief) leaves
    `budget_cut`'s output untouched, byte for byte."""
    ordered_steps, evaluated_steps = _load_evaluated_steps(agenda, character, db)
    budget_result = budget_cut(evaluated_steps, DAY_BUDGET_SLOTS)
    included = budget_result.included
    if veto_retained is not None:
        included = included[: max(0, veto_retained)]
    rolled = _roll_included_steps(ordered_steps, included, character, db)
    outcomes = _truncate_on_failure(rolled)
    _append_blocked_step(ordered_steps, evaluated_steps, budget_result, rolled, outcomes)
    return outcomes


def outcome_line(outcome: StepOutcome) -> str:
    """A short FACTUAL line (not prose — narration is `day_narration.py`).
    V1 (BRIEF-0075-d-amendment-1): no longer consumed by a direct write in
    this module — `day_mutations.emit_mutations` reads it for the
    `agenda_step_change` payload's `outcome` key, which
    `_mutation_apply_agenda_step_change` (cockpit/mutations.py) writes onto
    the `AgendaStep` row only once Nia approves."""
    if outcome.verdict is None:
        return f"{outcome.band}: no roll required"
    v = outcome.verdict
    return f"{outcome.band}: {v.domain} {v.dice[0]}+{v.dice[1]}{v.modifier:+d}={v.total}"


def freeze_facts(
    outcomes: list[StepOutcome], concordance: ConcordanceResult, batch: Batch, character: Character, db: Session,
) -> FactSheet:
    """Build the frozen fact sheet (Scope IN item 2). `concordance` is a
    FRESH `day_concordance.concord()` result over `pass_play.declared_
    action`, re-run by the caller the same way `_extract_and_concord` does
    at `/plan` time — `ConcordanceResult` is never persisted past the call
    that builds it (BRIEF-0075-c), and `agenda_step_requirement` almost
    never carries a `target_entity_id` in practice (the seeded `day_plan`
    prompt only ever asks the model for the two requirement forms that
    don't need one — knowledge/resource). Re-running the same
    deterministic, model-free lookup is the durable-enough substitute:
    concordance precedes narration here exactly as it did at plan time
    (AMENDMENT 1's ordering, restated), so a mention resolvable at all is
    already resolved before `narrate` ever runs."""
    npcs: list[NamedRef] = []
    locations: list[NamedRef] = []
    for mm in concordance.matched:
        entity = db.get(Entity, mm.entity_id)
        if entity is None:
            continue
        ref = NamedRef(entity_id=mm.entity_id, name=entity.name)
        if entity.type == "character" and ref not in npcs:
            npcs.append(ref)
        elif entity.type == "location" and ref not in locations:
            locations.append(ref)

    role_hints = tuple(sorted({
        um.mention.role_hint or um.mention.surface_form
        for um in concordance.unmatched
        if um.mention.category in ("person", "place")
    }))

    character_entity = db.get(Entity, character.id)
    character_name = character_entity.name if character_entity is not None else character.id

    steps = tuple(
        StepFact(
            objective=o.objective,
            band=o.band,
            dice=o.verdict.dice if o.verdict is not None else None,
            modifier=o.verdict.modifier if o.verdict is not None else None,
            total=o.verdict.total if o.verdict is not None else None,
            blocked_detail=(
                " ; ".join(requirement_detail_fr(v) for v in o.requirement_verdicts if not v.met)
                if o.band == BLOCKED_BAND else None
            ),
        )
        for o in outcomes
    )

    authorised_names = frozenset({r.name for r in npcs} | {r.name for r in locations} | {character_name})

    return FactSheet(
        world_id=character.world_id,
        day_number=batch.day_number,
        character_name=character_name,
        steps=steps,
        npcs=tuple(npcs),
        locations=tuple(locations),
        role_hints=role_hints,
        authorised_names=authorised_names,
    )


def fact_sheet_dict(fact_sheet: FactSheet) -> dict:
    """JSON-serializable projection (for the `pass_play.history` append —
    `writes.pipeline.write_pass_play_resolution`)."""
    return {
        "world_id": fact_sheet.world_id,
        "day_number": fact_sheet.day_number,
        "character_name": fact_sheet.character_name,
        "steps": [
            {
                "objective": s.objective, "band": s.band,
                "dice": list(s.dice) if s.dice is not None else None,
                "modifier": s.modifier, "total": s.total,
                "blocked_detail": s.blocked_detail,
            }
            for s in fact_sheet.steps
        ],
        "npcs": [{"id": r.entity_id, "name": r.name} for r in fact_sheet.npcs],
        "locations": [{"id": r.entity_id, "name": r.name} for r in fact_sheet.locations],
        "role_hints": list(fact_sheet.role_hints),
        "authorised_names": sorted(fact_sheet.authorised_names),
    }
