"""Day-plan emission and budget cut (TICKET-0075, BRIEF-0075-b — the
plan-emission-and-budget step; decisions F1, M1, P2, S1, H1).

One model call (`emit_plan`) turns a player's day declaration into a full,
ordered step list — the model PROPOSES. Everything downstream is Python: the
four named requirement evaluators judge each step's preconditions, and
`budget_cut` (pure, sequential, not a knapsack) decides how much of the plan
happens today against `DAY_BUDGET_SLOTS`. This module authors no prose and
emits no `proposed_mutation` — persistence is `writes.write_day_plan`.

THE POSITIONAL WALL (BRIEF-0074-a-amendment-1) holds here too: no function in
this module reads the world's stored day-cycle phase (P2 — every day gets
the full budget), and `location_reachable`'s target is a precondition on the
PLAYER, never a position of an NPC.

`_day_reachable_ids` is a NEW, day-local `connects_to` BFS reader, not a
reuse of an existing one. The original brief instructed "reuse the existing
traversal; do not write a second one" — that instruction was wrong: it
contradicted decision D1 (BRIEF-19), standing project doctrine that each new
`connects_to` consumer gets its OWN reader (a real dedup opportunity is
REPORTED, never acted on). Claude Code escalated under the brief's own STOP
condition rather than guess; Nia's correction is
`tooling/briefs/BRIEF-0075-b-amendment-1-location-reachable-reader.md`. Per
that amendment's count, this is roughly the SEVENTH independent
`connects_to` reader in the tree — `_location_neighbours`
(`cockpit/play.py:854`, direct neighbours only) and `_reachable_locations`
(`tick_context.py:405`, interval-hop-bounded, origin EXCLUDED) are the two
closest siblings, and `_day_reachable_ids` is deliberately NOT shared with
either: unbounded (a day has no meaningful hop radius) and origin-INCLUSIVE
(the player is already there, which satisfies reachability) — a concrete
shape difference, not only a doctrinal one.

`_day_reachable_ids` proves a path exists in the `connects_to` graph; it does
NOT prove the Play surface's door/travel gate would let the player walk it
today. Harmless now (the day chain resolves travel abstractly — Play is
sealed, TICKET-0061), and worth a fresh look only if a future ticket ever
routes a day step through Play.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Callable, Optional

from sqlmodel import Session, func, select

from . import llm_parse, ollama_client
from .models import (
    BASE_SKILL_DOMAINS,
    SCHEDULE_PHASES,
    Character,
    Entity,
    Knowledge,
    Ledger,
    PromptTemplate,
    Relation,
)
from .prompt_registry import effective_model
from .prompt_store import current_prompt

_log = logging.getLogger(__name__)

# P2: every day gets the full budget, regardless of the world's stored
# day-cycle phase — derived from the phase vocabulary (R4), never written
# as a literal.
DAY_BUDGET_SLOTS: int = len(SCHEDULE_PHASES)

# S1: four requirement forms, each with a named evaluator.
REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")

# Emission bound (Scope IN item 4). Anything beyond is truncated with a
# reported count (logged), not silently dropped.
MAX_PLAN_STEPS = 12

# BRIEF-0078-a Scope IN item 6: bound on how many held subjects are listed
# in held_subjects_summary(). Anything beyond is truncated with a reported
# count (logged), not silently dropped.
MAX_HELD_SUBJECTS_SHOWN: int = 40

# Same mild repetition controls as MJ gathering — short, low-drift JSON output.
DAY_PLAN_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}


@dataclass(frozen=True)
class RequirementSpec:
    type: str
    target_entity_id: Optional[str] = None
    target_key: Optional[str] = None
    threshold: Optional[int] = None


@dataclass(frozen=True)
class PlanStep:
    objective: str
    cost: Optional[int]
    domain: Optional[str]
    requirements: tuple[RequirementSpec, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Verdict:
    # `type` FIRST (BRIEF-0078-a, Scope IN item 3): a positional
    # `Verdict(...)` construction anywhere in the tree now fails loudly
    # (wrong type in the wrong slot) rather than silently shifting fields.
    type: str
    met: bool
    current: object
    required: object
    reason: str


@dataclass(frozen=True)
class EvaluatedStep:
    step: PlanStep
    verdicts: tuple[Verdict, ...]

    @property
    def met(self) -> bool:
        return all(v.met for v in self.verdicts)


@dataclass(frozen=True)
class BudgetResult:
    included: tuple[EvaluatedStep, ...]
    slots_consumed: int
    slots_budget: int
    first_excluded_index: Optional[int]


# ── requirement evaluators (S1) ──────────────────────────────────────────────
# Uniform 4-arg signature (`_SOURCE_LOOKUPS` precedent, schedule_reads.py):
# every evaluator accepts `reachable_ids`, even the three that ignore it —
# keeps `_EVALUATORS` directly callable without a special case.

def _eval_knowledge(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    del reachable_ids
    row = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == character.id, Knowledge.subject == req.target_key,
        )
    ).first()
    met = row is not None
    reason = (
        f"knowledge {req.target_key!r} already held" if met
        else f"prerequisite not met — knowledge {req.target_key!r} not held"
    )
    return Verdict(
        type=req.type, met=met, current=("held" if met else "unheld"), required=req.target_key, reason=reason,
    )


def _eval_relation_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    del reachable_ids
    # Deliberate duplicate of writes.relations._find_relation_pair's
    # both-directions first-match query, not an import: writes/goals_agendas.py
    # (which constructs agenda_step_requirement rows) imports FROM this
    # module, so importing FROM writes/ here would cycle the package.
    # Same posture as the connects_to readers above — reported, not acted on.
    rel = db.exec(
        select(Relation).where(
            ((Relation.entity_a_id == character.id) & (Relation.entity_b_id == req.target_entity_id))
            | ((Relation.entity_a_id == req.target_entity_id) & (Relation.entity_b_id == character.id))
        )
    ).first()
    current = rel.intensity if rel else 0
    threshold = req.threshold or 0
    met = current >= threshold
    target = db.get(Entity, req.target_entity_id)
    target_name = target.name if target else req.target_entity_id
    reason = (
        f"relation with {target_name} is {current}, meets requires >= {threshold}" if met
        else f"prerequisite not met — relation with {target_name} is {current}, requires >= {threshold}"
    )
    return Verdict(type=req.type, met=met, current=current, required=threshold, reason=reason)


def _eval_resource(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    del reachable_ids
    total = db.exec(select(func.sum(Ledger.amount)).where(Ledger.entity_id == character.id)).first() or 0
    threshold = req.threshold or 0
    met = total >= threshold
    reason = (
        f"resource {req.target_key!r} balance is {total}, meets requires >= {threshold}" if met
        else f"prerequisite not met — resource {req.target_key!r} balance is {total}, requires >= {threshold}"
    )
    return Verdict(type=req.type, met=met, current=total, required=threshold, reason=reason)


def _eval_location_reachable(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    ids = reachable_ids or frozenset()
    met = req.target_entity_id in ids
    target = db.get(Entity, req.target_entity_id)
    target_name = target.name if target else req.target_entity_id
    reason = (
        f"{target_name} is reachable" if met
        else f"prerequisite not met — {target_name} is not reachable from the current location"
    )
    return Verdict(
        type=req.type, met=met, current=character.current_location_id,
        required=req.target_entity_id, reason=reason,
    )


_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
    "knowledge": _eval_knowledge,
    "relation_gte": _eval_relation_gte,
    "resource": _eval_resource,
    "location_reachable": _eval_location_reachable,
}


def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:
    """A NEW, day-local `connects_to` BFS reader (decision D1, BRIEF-19) —
    see the module docstring for the escalation this corrects. Unbounded
    (the origin's whole connected component of ACTIVE locations), origin
    INCLUDED, both `connects_to` column orders. Returns bare ids —
    `evaluate_requirements` needs membership only, nothing else."""
    visited: set[str] = {origin_location_id}
    frontier = [origin_location_id]
    while frontier:
        next_frontier: list[str] = []
        for loc_id in frontier:
            rows = db.exec(
                select(Relation).where(
                    Relation.type == "connects_to",
                    (Relation.entity_a_id == loc_id) | (Relation.entity_b_id == loc_id),
                )
            ).all()
            for rel in rows:
                other_id = rel.entity_b_id if rel.entity_a_id == loc_id else rel.entity_a_id
                if other_id in visited:
                    continue
                other = db.get(Entity, other_id)
                if other is None or other.type != "location" or other.status != "active":
                    continue
                visited.add(other_id)
                next_frontier.append(other_id)
        frontier = next_frontier
    return frozenset(visited)


def evaluate_requirements(step: PlanStep, character: Character, db: Session) -> list[Verdict]:
    """Judge every requirement on `step` against `character`'s current
    state. Dispatches through `_EVALUATORS`; an unknown `type` raises
    fail-closed — it cannot happen through the DB (the CHECK forbids it),
    the branch exists so that widening `REQUIREMENT_TYPES` without adding an
    evaluator fails loudly.

    `_day_reachable_ids` is computed AT MOST ONCE per call, only if `step`
    actually carries a `location_reachable` requirement — never per
    requirement item."""
    needs_reachable = any(r.type == "location_reachable" for r in step.requirements)
    reachable_ids = _day_reachable_ids(character.current_location_id, db) if needs_reachable else None

    verdicts: list[Verdict] = []
    for req in step.requirements:
        evaluator = _EVALUATORS.get(req.type)
        if evaluator is None:
            raise ValueError(f"unknown requirement type {req.type!r}")
        verdicts.append(evaluator(req, character, db, reachable_ids))
    return verdicts


def budget_cut(steps: list[EvaluatedStep], budget: int) -> BudgetResult:
    """Sequential greedy cut — NOT a knapsack: a plan is sequential, step N
    cannot happen before step N-1. Steps are taken in order until the next
    step's cost would exceed the remaining budget, OR a step's requirements
    are unmet (that step and everything after it are excluded). Pure: no db,
    no select(, no chat(, no datetime, no randint — every input is already
    computed."""
    included: list[EvaluatedStep] = []
    consumed = 0
    first_excluded: Optional[int] = None
    for idx, evaluated in enumerate(steps):
        if evaluated.step.cost is None:
            raise ValueError(f"budget_cut: step {idx} has NULL cost — plan emission failure")
        if not evaluated.met:
            first_excluded = idx
            break
        if consumed + evaluated.step.cost > budget:
            first_excluded = idx
            break
        included.append(evaluated)
        consumed += evaluated.step.cost
    return BudgetResult(
        included=tuple(included), slots_consumed=consumed, slots_budget=budget,
        first_excluded_index=first_excluded,
    )


# ── requirement anchoring (BRIEF-0078-a, decisions A5(A1b)/B3) ──────────────
#
# B3: a gate is legitimate only on a subject that exists to be learned --
# held in this world by an entity OTHER than the player, on a non-secret
# row. `is_secret` is excluded because a gate on a secret is both
# unsatisfiable and a disclosure: the reject message would reveal that the
# secret exists.

def _held_subjects(character: Character, db: Session) -> frozenset[str]:
    """The player's own held subjects (A1b) — handed to the emission model
    via `held_subjects_summary` so it stops proposing a dead gate on
    something already held. Called at most once per emission (F3)."""
    rows = db.exec(
        select(Knowledge.subject).where(Knowledge.entity_id == character.id).distinct()
    ).all()
    return frozenset(rows)


def _anchorable_subjects(character: Character, db: Session) -> frozenset[str]:
    """The B3 predicate, and nowhere else: subjects that legitimately anchor
    a `knowledge` requirement — held in this world (`Entity.world_id`), by an
    entity OTHER than the player (`Knowledge.entity_id != character.id`), on
    a non-secret row (`Knowledge.is_secret == False`). Called at most once
    per emission (F3)."""
    rows = db.exec(
        select(Knowledge.subject)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .where(
            Entity.world_id == character.world_id,
            Knowledge.entity_id != character.id,
            Knowledge.is_secret == False,  # noqa: E712
        )
        .distinct()
    ).all()
    return frozenset(rows)


def anchor_requirements(
    steps: list[PlanStep], character: Character, db: Session,
) -> tuple[list[PlanStep], list[dict]]:
    """Drop every `knowledge` requirement whose `target_key` is not anchored
    (B3) — REQUIREMENTS are dropped, never steps: the returned step count
    always equals the input count. A step whose only requirement was dropped
    becomes an ungated step, the intended outcome, not a degradation.
    `_anchorable_subjects` is called ONCE for the whole plan (F3)."""
    anchorable = _anchorable_subjects(character, db)
    dropped: list[dict] = []
    anchored_steps: list[PlanStep] = []
    for step_index, step in enumerate(steps):
        kept_requirements = []
        for req in step.requirements:
            if req.type == "knowledge" and req.target_key not in anchorable:
                dropped.append({
                    "step_index": step_index, "objective": step.objective, "target_key": req.target_key,
                })
                _log.info(
                    "day_plan: dropped unanchored knowledge requirement %r on step %d",
                    req.target_key, step_index,
                )
                continue
            kept_requirements.append(req)
        anchored_steps.append(replace(step, requirements=tuple(kept_requirements)))
    return anchored_steps, dropped


# ── plan emission (model call) ───────────────────────────────────────────────

def _load_day_plan_template(world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """Return the active day_plan template (world-specific preferred), or
    None. `mj_gathering`'s `_load_gathering_template` precedent."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "day_plan",
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


def _validate_requirement(raw: object) -> RequirementSpec:
    if not isinstance(raw, dict):
        raise llm_parse.LlmParseError(f"day_plan: requirement entry must be an object, got {raw!r}")
    req_type = raw.get("type")
    if req_type not in REQUIREMENT_TYPES:
        raise llm_parse.LlmParseError(f"day_plan: unknown requirement type {req_type!r}")
    threshold = raw.get("threshold")
    if not isinstance(threshold, int) or isinstance(threshold, bool):
        threshold = None
    target_key = raw.get("target_key")
    target_entity_id = raw.get("target_entity_id")
    return RequirementSpec(
        type=req_type,
        target_key=str(target_key) if target_key is not None else None,
        target_entity_id=str(target_entity_id) if target_entity_id is not None else None,
        threshold=threshold,
    )


def _validate_step(raw: object) -> PlanStep:
    if not isinstance(raw, dict):
        raise llm_parse.LlmParseError(f"day_plan: step must be an object, got {raw!r}")
    objective = raw.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise llm_parse.LlmParseError("day_plan: step missing non-empty 'objective'")
    cost = raw.get("cost")
    if not isinstance(cost, int) or isinstance(cost, bool) or not (1 <= cost <= DAY_BUDGET_SLOTS):
        raise llm_parse.LlmParseError(
            f"day_plan: step 'cost' must be an int 1..{DAY_BUDGET_SLOTS}, got {cost!r}"
        )
    domain = raw.get("domain")
    if domain is not None and domain not in BASE_SKILL_DOMAINS:
        raise llm_parse.LlmParseError(
            f"day_plan: step 'domain' must be null or one of {BASE_SKILL_DOMAINS}, got {domain!r}"
        )
    raw_requires = raw.get("requires") or []
    if not isinstance(raw_requires, list):
        raise llm_parse.LlmParseError("day_plan: step 'requires' must be a list")
    requirements = tuple(_validate_requirement(item) for item in raw_requires)
    return PlanStep(objective=objective.strip(), cost=cost, domain=domain, requirements=requirements)


def held_subjects_summary(character: Character, db: Session) -> str:
    """A short French summary of the subjects `character` already holds
    (BRIEF-0078-a Scope IN item 6, decision A1b) — appended to `emit_plan`'s
    user message so the model stops proposing a `knowledge` gate on a
    subject already held (a dead gate). Positive form only — the gameplay
    model is abliterated. Returns "" when the player holds no subject at
    all. Calls `_held_subjects` once."""
    subjects = sorted(_held_subjects(character, db))
    if not subjects:
        return ""
    truncated = 0
    if len(subjects) > MAX_HELD_SUBJECTS_SHOWN:
        truncated = len(subjects) - MAX_HELD_SUBJECTS_SHOWN
        subjects = subjects[:MAX_HELD_SUBJECTS_SHOWN]
        _log.info(
            "day_plan: held_subjects_summary truncated %d subject(s) beyond MAX_HELD_SUBJECTS_SHOWN=%d",
            truncated, MAX_HELD_SUBJECTS_SHOWN,
        )
    character_entity = db.get(Entity, character.id)
    character_name = character_entity.name if character_entity is not None else character.id
    liste = ", ".join(subjects)
    return (
        f"Sujets que {character_name} connaît déjà : {liste}.\n"
        "Une condition « knowledge » porte sur un sujet absent de cette liste."
    )


def emit_plan(
    declaration: str, character: Character, db: Session, concordance_summary: str = "",
    standing_steps_summary: str = "", held_subjects_summary: str = "",
) -> list[PlanStep]:
    """ONE model call (F1). Parses through `llm_parse.extract_object`;
    domain/shape validation stays here per M9's contract. A parse failure or
    a shape violation RAISES — this never falls back to a partial plan
    (unlike `gathering.py`'s solo-partition fallback: a day plan gates real
    play consequences, a silent partial plan would be worse than none).

    `concordance_summary` (BRIEF-0075-c), `standing_steps_summary`
    (BRIEF-0075-f, `modify`'s reconciliation path) and `held_subjects_summary`
    (BRIEF-0078-a, item 6) are ALL appended verbatim to the user message,
    never woven into the seeded template text — the same discipline for the
    same reason: text a Python pass already built, not a new prompt-template
    placeholder that a virgin-head-only seed (S2) could never retrofit onto
    an already-provisioned world. Each defaults to "" (a no-op) so every
    pre-existing call site is byte-identical."""
    template = _load_day_plan_template(character.world_id, db)
    if template is None:
        raise llm_parse.LlmParseError("day_plan: no active prompt_template for usage='day_plan'")
    version = current_prompt(db, template)

    character_entity = db.get(Entity, character.id)
    character_name = character_entity.name if character_entity is not None else character.id
    user_msg = (
        version.user_template
        .replace("{character_name}", character_name)
        .replace("{declaration}", declaration)
    )
    if concordance_summary:
        user_msg += f"\n\n{concordance_summary}"
    if standing_steps_summary:
        user_msg += f"\n\n{standing_steps_summary}"
    if held_subjects_summary:
        user_msg += f"\n\n{held_subjects_summary}"
    user_msg += "\n/no_think"
    raw = ollama_client.chat(
        [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=effective_model(template, ollama_client.DEFAULT_MODEL),
        host=ollama_client.OLLAMA_HOST,
        format="json",
        options=DAY_PLAN_OPTIONS,
    )
    obj = llm_parse.extract_object(raw)
    raw_steps = obj.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise llm_parse.LlmParseError("day_plan: model returned no steps")

    truncated = 0
    if len(raw_steps) > MAX_PLAN_STEPS:
        truncated = len(raw_steps) - MAX_PLAN_STEPS
        raw_steps = raw_steps[:MAX_PLAN_STEPS]

    steps = [_validate_step(item) for item in raw_steps]
    if truncated:
        _log.info("day_plan: emitted plan truncated by %d step(s) beyond MAX_PLAN_STEPS=%d", truncated, MAX_PLAN_STEPS)
    return steps
