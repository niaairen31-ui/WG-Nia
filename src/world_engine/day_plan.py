"""Day-plan emission and budget cut (TICKET-0075, BRIEF-0075-b — the
plan-emission-and-budget step; decisions F1, M1, P2, S1, H1).

One model call (`emit_plan`) turns a player's day declaration into a full,
ordered step list — the model PROPOSES. Everything downstream is Python: the
named requirement evaluators (`condition_forms.py` since TICKET-0111,
BRIEF-0111-A) judge each step's preconditions, and `budget_cut` (pure,
sequential, not a knapsack) decides how much of the plan happens today
against `DAY_BUDGET_SLOTS`. This module authors no prose and emits no
`proposed_mutation` — persistence is `writes.write_day_plan`.

THE POSITIONAL WALL (BRIEF-0074-a-amendment-1) holds here too: no function in
this module reads the world's stored day-cycle phase (P2 — every day gets
the full budget), and `location_reachable`'s target is a precondition on the
PLAYER, never a position of an NPC.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .condition_forms import MODEL_REQUIREMENT_TYPES, RequirementSpec, Verdict, evaluate_specs
from .fact_refs import CodedFacts, code_facts
from .models import (
    BASE_SKILL_DOMAINS,
    SCHEDULE_PHASES,
    AgendaStep,
    AgendaStepRequirement,
    Character,
    Entity,
    Fact,
    Knowledge,
    PromptTemplate,
)
from .prompt_registry import effective_model
from .prompt_store import current_prompt
from .prose_render import fact_texts

_log = logging.getLogger(__name__)

# P2: every day gets the full budget, regardless of the world's stored
# day-cycle phase — derived from the phase vocabulary (R4), never written
# as a literal.
DAY_BUDGET_SLOTS: int = len(SCHEDULE_PHASES)


# Emission bound (Scope IN item 4). Anything beyond is truncated with a
# reported count (logged), not silently dropped.
MAX_PLAN_STEPS = 12

# BRIEF-0078-a Scope IN item 6, re-aimed by TICKET-0097 (D1'a): bound on how
# many learnable facts `learnable_facts` codes for the model. Anything beyond
# is truncated with a reported count (logged), not silently dropped.
MAX_LEARNABLE_FACTS_SHOWN: int = 40

# Same mild repetition controls as MJ gathering — short, low-drift JSON output.
DAY_PLAN_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}


@dataclass(frozen=True)
class PlanStep:
    objective: str
    cost: Optional[int]
    domain: Optional[str]
    requirements: tuple[RequirementSpec, ...] = field(default_factory=tuple)


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


def evaluate_requirements(step: PlanStep, character: Character, db: Session) -> list[Verdict]:
    """Judge every requirement on `step` (`evaluate_specs` on its
    requirements)."""
    return evaluate_specs(step.requirements, character, db)


def evaluate_agenda_step(agenda_step: AgendaStep, character: Character, db: Session) -> EvaluatedStep:
    """One `agenda_step` row plus its requirement rows, judged against
    `character`'s current state (TICKET-0080, BRIEF-0080-b). Carved out of
    `day_resolve._load_evaluated_steps` unchanged so that the day chain's
    resolve walk and `_finalize_continue`'s refusal path share ONE
    evaluation, rather than growing a second copy that can drift."""
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
    return EvaluatedStep(step=plan_step, verdicts=verdicts)


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
# B3: a gate is legitimate only on a fact that exists to be learned --
# held in this world by an entity OTHER than the player, on a non-secret
# row. `is_secret` is excluded because a gate on a secret is both
# unsatisfiable and a disclosure: the reject message would reveal that the
# secret exists.

def _held_facts(character: Character, db: Session) -> frozenset[str]:
    """The fact ids the player already holds (A1b) — left out of the coded
    list the emission model sees, so it cannot propose a dead gate."""
    rows = db.exec(
        select(Knowledge.fact_id).where(Knowledge.entity_id == character.id).distinct()
    ).all()
    return frozenset(rows)


def _anchorable_facts(character: Character, db: Session) -> frozenset[str]:
    """The B3 predicate, and nowhere else: fact ids that legitimately anchor
    a `knowledge` requirement — held in this world (`Entity.world_id`), by an
    entity OTHER than the player (`Knowledge.entity_id != character.id`), on
    a non-secret row (`Knowledge.is_secret == False`)."""
    rows = db.exec(
        select(Knowledge.fact_id)
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
    """Drop every `knowledge` requirement whose `target_key` is not an
    anchored fact id (B3) — REQUIREMENTS are dropped, never steps: the
    returned step count always equals the input count. A step whose only
    requirement was dropped becomes an ungated step, the intended outcome,
    not a degradation. `_anchorable_facts` is called ONCE for the whole plan
    (F3)."""
    anchorable = _anchorable_facts(character, db)
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
    if req_type not in MODEL_REQUIREMENT_TYPES:
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


def learnable_facts(character: Character, db: Session) -> CodedFacts:
    """D1'a (TICKET-0097): the coded list of facts a `knowledge` gate may
    name — anchorable (B3) and not already held (A1b), ordered by their
    rendered text, at most `MAX_LEARNABLE_FACTS_SHOWN` (the rest is counted
    in a log line, never silently dropped)."""
    fact_ids = _anchorable_facts(character, db) - _held_facts(character, db)
    facts = [fact for fact in (db.get(Fact, fid) for fid in fact_ids) if fact is not None]
    ordered = [fact for _text, fact in sorted(zip(fact_texts(db, facts), facts), key=lambda p: (p[0], p[1].id))]
    if len(ordered) > MAX_LEARNABLE_FACTS_SHOWN:
        _log.info(
            "day_plan: learnable_facts truncated %d fact(s) beyond MAX_LEARNABLE_FACTS_SHOWN=%d",
            len(ordered) - MAX_LEARNABLE_FACTS_SHOWN, MAX_LEARNABLE_FACTS_SHOWN,
        )
    return code_facts(db, [fact.id for fact in ordered[:MAX_LEARNABLE_FACTS_SHOWN]])


def learnable_facts_summary(character_name: str, learnable: CodedFacts) -> str:
    """The French text `emit_plan` appends for `learnable` (BRIEF-0078-a's
    appended-text shape, never a template placeholder). Positive form only —
    the gameplay model is abliterated. "" when the list is empty."""
    if not learnable.lines:
        return ""
    liste = "\n".join(learnable.lines)
    return (
        f"Faits que {character_name} peut apprendre (code — fait) :\n{liste}\n"
        "Une condition « knowledge » donne comme target_key le code d'un de ces faits."
    )


def _resolve_knowledge_codes(steps: list[PlanStep], learnable: CodedFacts) -> list[PlanStep]:
    """Each `knowledge` requirement's code becomes its fact id; a code the
    list did not show is kept as emitted, for `anchor_requirements` to drop
    and report."""
    resolved_steps = []
    for step in steps:
        requirements = tuple(
            replace(req, target_key=learnable.resolve(req.target_key) or req.target_key)
            if req.type == "knowledge" else req
            for req in step.requirements
        )
        resolved_steps.append(replace(step, requirements=requirements))
    return resolved_steps


def emit_plan(
    declaration: str, character: Character, db: Session, standing_steps_summary: str = "",
) -> list[PlanStep]:
    """ONE model call (F1). Parses through `llm_parse.extract_object`;
    domain/shape validation stays here per M9's contract. A parse failure or
    a shape violation RAISES — this never falls back to a partial plan
    (unlike `gathering.py`'s solo-partition fallback: a day plan gates real
    play consequences, a silent partial plan would be worse than none).

    `declaration` is the RENDERED text (TICKET-0081, BRIEF-0081-b —
    `day_rewrite.render`'s output, participants already named), never the
    raw `pass_play.declared_action` — every call site passes the rewrite.
    `standing_steps_summary` (BRIEF-0075-f, `modify`'s reconciliation path)
    and the learnable-facts summary (TICKET-0097, D1'a — built here, on every
    call site) are appended verbatim to the user message, never woven into
    the seeded template text. Every `knowledge` requirement comes back with
    its code resolved to a fact id (`_resolve_knowledge_codes`)."""
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
    learnable = learnable_facts(character, db)
    learnable_summary = learnable_facts_summary(character_name, learnable)
    if standing_steps_summary:
        user_msg += f"\n\n{standing_steps_summary}"
    if learnable_summary:
        user_msg += f"\n\n{learnable_summary}"
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

    steps = _resolve_knowledge_codes([_validate_step(item) for item in raw_steps], learnable)
    if truncated:
        _log.info("day_plan: emitted plan truncated by %d step(s) beyond MAX_PLAN_STEPS=%d", truncated, MAX_PLAN_STEPS)
    return steps
