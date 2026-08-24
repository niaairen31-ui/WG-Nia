"""Step resolution and the frozen fact sheet (TICKET-0075, BRIEF-0075-d —
decisions B4-as-amended and T1; dice are Python, never a model).

Scope IN item 1 (step resolution): `resolve_steps` re-evaluates the
character's active `Agenda` (the "plan" — every `agenda_step` row plus its
`agenda_step_requirement` rows) from `step_order` 1 EVERY call, through the
SAME `evaluate_requirements`/`budget_cut` pair `day_plan.py` uses at
emission time. This is deliberate: a REPLAY (Scope IN item 5) re-derives
requirement verdicts against current world state and may re-roll a step
that already resolved once — `write_agenda_step_status` appends the
previous `{status, outcome, updated_at}` before overwriting, so history
grows rather than being replaced (history is sacred). Persistence
(`persist_step_outcomes`) is the ONLY place this module writes canon, and it
writes through `write_agenda_step_status` — the existing, already-allow-
listed `agenda_step` chokepoint (`canon_write_policy.txt`) — never a
`db.add(` of its own.

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
    EvaluatedStep,
    PlanStep,
    RequirementSpec,
    Verdict as RequirementVerdict,
    budget_cut,
    evaluate_requirements,
)
from .models import (
    Agenda,
    AgendaStep,
    AgendaStepRequirement,
    Batch,
    Character,
    Entity,
    Skill,
)
from .resolution import Verdict, resolve_physical
from .writes import write_agenda_step_status

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class StepOutcome:
    agenda_step_id: str
    step_order: int
    objective: str
    domain: Optional[str]
    # None is the explicit "no roll" marker (the step's domain was NULL).
    verdict: Optional[Verdict]
    band: str  # "success" | "partial" | "failure"
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


@dataclass(frozen=True)
class FactSheet:
    world_id: str
    day_number: int
    character_name: str
    steps: tuple[StepFact, ...]
    npcs: tuple[NamedRef, ...]
    locations: tuple[NamedRef, ...]
    # Role hints for persons the concordance pass (BRIEF-0075-c) never
    # resolved to a canon id — the narration renders these as functions,
    # never as invented names (they are explicitly NOT in authorised_names).
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


def _load_evaluated_steps(
    agenda: Agenda, character: Character, db: Session,
) -> tuple[list[AgendaStep], list[EvaluatedStep]]:
    ordered_steps = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda.id).order_by(AgendaStep.step_order)
    ).all()
    evaluated_steps: list[EvaluatedStep] = []
    for agenda_step in ordered_steps:
        requirement_rows = db.exec(
            select(AgendaStepRequirement).where(AgendaStepRequirement.step_id == agenda_step.id)
        ).all()
        plan_step = PlanStep(
            objective=agenda_step.objective,
            cost=agenda_step.cost,
            domain=agenda_step.domain,
            requirements=tuple(
                RequirementSpec(
                    type=r.type, target_entity_id=r.target_entity_id,
                    target_key=r.target_key, threshold=r.threshold,
                )
                for r in requirement_rows
            ),
        )
        verdicts = tuple(evaluate_requirements(plan_step, character, db))
        evaluated_steps.append(EvaluatedStep(step=plan_step, verdicts=verdicts))
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


def resolve_steps(agenda: Agenda, character: Character, db: Session) -> list[StepOutcome]:
    """Resolve the budgeted portion of `agenda`'s plan (Scope IN item 1).
    `agenda` is the character's currently active `Agenda` — the "plan" of
    the brief's signature."""
    ordered_steps, evaluated_steps = _load_evaluated_steps(agenda, character, db)
    budget_result = budget_cut(evaluated_steps, DAY_BUDGET_SLOTS)
    rolled = _roll_included_steps(ordered_steps, budget_result.included, character, db)
    return _truncate_on_failure(rolled)


def _outcome_line(outcome: StepOutcome) -> str:
    """A short FACTUAL line (not prose — narration is `day_narration.py`)."""
    if outcome.verdict is None:
        return f"{outcome.band}: no roll required"
    v = outcome.verdict
    return f"{outcome.band}: {v.domain} {v.dice[0]}+{v.dice[1]}{v.modifier:+d}={v.total}"


def persist_step_outcomes(agenda: Agenda, outcomes: list[StepOutcome], db: Session) -> None:
    """Persist item 1's outcomes: every attempted step transitions to
    `completed`/`failed` through `write_agenda_step_status` (the existing
    allow-listed `agenda_step` chokepoint — this function itself never
    calls `db.add(` on an `AgendaStep`). The next unattempted step (by
    `step_order`, across the FULL agenda, not just the attempted prefix)
    becomes `active` — the partial unique index (M7) guarantees at most
    one ever is. Caller commits."""
    ordered_steps = db.exec(
        select(AgendaStep).where(AgendaStep.agenda_id == agenda.id).order_by(AgendaStep.step_order)
    ).all()

    for outcome in outcomes:
        step = db.get(AgendaStep, outcome.agenda_step_id)
        if step is None:
            continue
        new_status = "failed" if outcome.band == "failure" else "completed"
        write_agenda_step_status(db, step=step, status=new_status, outcome=_outcome_line(outcome))
    db.flush()

    last_attempted_order = outcomes[-1].step_order if outcomes else 0
    next_step = next((s for s in ordered_steps if s.step_order > last_attempted_order), None)
    if next_step is not None and next_step.status != "active":
        write_agenda_step_status(db, step=next_step, status="active")


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
        if um.mention.category == "person"
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
            }
            for s in fact_sheet.steps
        ],
        "npcs": [{"id": r.entity_id, "name": r.name} for r in fact_sheet.npcs],
        "locations": [{"id": r.entity_id, "name": r.name} for r in fact_sheet.locations],
        "role_hints": list(fact_sheet.role_hints),
        "authorised_names": sorted(fact_sheet.authorised_names),
    }
