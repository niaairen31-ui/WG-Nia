"""Day-plan emission and budget cut (TICKET-0075, BRIEF-0075-b — the
plan-emission-and-budget step; decisions F1, M1, P2, S1, H1).

One model call (`emit_plan`) turns a player's day declaration into a full,
ordered step list — the model PROPOSES. Everything downstream is Python: the
named requirement evaluators judge each step's preconditions, and
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
from .fact_refs import CodedFacts, code_facts
from .models import (
    BASE_SKILL_DOMAINS,
    SCHEDULE_PHASES,
    Agenda,
    AgendaStep,
    AgendaStepRequirement,
    Character,
    Entity,
    Fact,
    FactionMembership,
    Knowledge,
    Ledger,
    PromptTemplate,
    Quest,
    QuestOffer,
    Relation,
    Rencontre,
)
from .prompt_registry import effective_model
from .prompt_store import current_prompt
from .prose_render import fact_text, fact_texts
from .relation_orientation import is_social
from .skill_access import held_rank, skill_label

_log = logging.getLogger(__name__)

# P2: every day gets the full budget, regardless of the world's stored
# day-cycle phase — derived from the phase vocabulary (R4), never written
# as a literal.
DAY_BUDGET_SLOTS: int = len(SCHEDULE_PHASES)

# S1: the closed requirement vocabulary, each form with a named evaluator.
# Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A, C-01): the four the
# day-plan model may emit, then four only the creator authors (quest offers).
REQUIREMENT_TYPES: tuple[str, ...] = (
    "knowledge", "relation_gte", "resource", "location_reachable",
    "has_met", "faction_member", "skill_rank_gte", "quest_completed",
)

# What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
# forms it always could. A creator-only form in a model's plan is a parse
# failure, never a row.
MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")

# The shape of each form, the three groups of the `*_requirement_shape`
# CHECK (C-01): which column names its target, and which need a threshold.
ENTITY_TARGET_TYPES: tuple[str, ...] = ("relation_gte", "location_reachable", "has_met", "faction_member")
KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte")

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
    # TICKET-0097: the player-facing text of `required` when it is an id
    # (a `knowledge` gate's fact); None when `required` is already readable.
    required_label: Optional[str] = None


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
    """`target_key` is a fact id (TICKET-0097, D1'a): met iff the character
    holds a row on that fact."""
    del reachable_ids
    row = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == character.id, Knowledge.fact_id == req.target_key,
        )
    ).first()
    met = row is not None
    fact = db.get(Fact, req.target_key) if req.target_key else None
    label = fact_text(db, fact) if fact is not None else req.target_key
    reason = (
        f"knowledge {label!r} already held" if met
        else f"prerequisite not met — knowledge {label!r} not held"
    )
    return Verdict(
        type=req.type, met=met, current=("held" if met else "unheld"), required=req.target_key, reason=reason,
        required_label=label,
    )


def _eval_relation_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """What the TARGET feels toward the character (TICKET-0108, B-dir): the
    social row `entity_a = target`, `entity_b = character`, `is_social`;
    0 when there is none. A deliberate duplicate of
    `writes.relations._find_perceived_relation`'s query (perceiver = the
    target), not an import: writes/goals_agendas.py imports FROM this module,
    so importing FROM writes/ here would cycle the package. The reverse row
    (the character's own feeling) and the structural types are never read."""
    del reachable_ids
    rows = db.exec(
        select(Relation).where(
            Relation.entity_a_id == req.target_entity_id, Relation.entity_b_id == character.id,
        )
    ).all()
    rel = next((row for row in rows if is_social(row.type)), None)
    current = rel.intensity if rel else 0
    threshold = req.threshold or 0
    met = current >= threshold
    target = db.get(Entity, req.target_entity_id)
    target_name = target.name if target else req.target_entity_id
    reason = (
        f"relation of {target_name} toward the character is {current}, meets requires >= {threshold}" if met
        else f"prerequisite not met — relation of {target_name} toward the character is {current}, "
        f"requires >= {threshold}"
    )
    return Verdict(
        type=req.type, met=met, current=current, required=threshold, reason=reason,
        required_label=target_name,
    )


def _eval_resource(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """Money: the character's ledger balance. A world has one currency (the
    `ledger` has no currency column), so `target_key` is a label and is not
    read; an object is never a `resource` (TICKET-0108, E1: objects held in
    quantity come with `item_holding`)."""
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


def _entity_name(db: Session, entity_id: Optional[str]) -> str:
    entity = db.get(Entity, entity_id) if entity_id else None
    return entity.name if entity is not None else str(entity_id)


def _eval_has_met(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """The character and the target have an encounter row (`rencontre`, one
    row per unordered pair, `entity_lo_id < entity_hi_id`)."""
    del reachable_ids
    low, high = sorted((character.id, req.target_entity_id))
    row = db.exec(
        select(Rencontre).where(Rencontre.entity_lo_id == low, Rencontre.entity_hi_id == high)
    ).first()
    met = row is not None
    name = _entity_name(db, req.target_entity_id)
    reason = f"has met {name}" if met else f"prerequisite not met — has not met {name}"
    return Verdict(
        type=req.type, met=met, current=("met" if met else "not met"), required=req.target_entity_id,
        reason=reason, required_label=name,
    )


def _eval_faction_member(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """The character holds an ACTIVE membership (`left_at IS NULL`) of the
    target faction. A secret membership counts: it is the character's own
    (the `tick_context` self-briefing precedent); secrecy hides it from
    others, not from the gate."""
    del reachable_ids
    row = db.exec(
        select(FactionMembership).where(
            FactionMembership.entity_id == character.id,
            FactionMembership.faction_id == req.target_entity_id,
            FactionMembership.left_at.is_(None),
        )
    ).first()
    met = row is not None
    name = _entity_name(db, req.target_entity_id)
    reason = f"member of {name}" if met else f"prerequisite not met — not a member of {name}"
    return Verdict(
        type=req.type, met=met, current=("member" if met else "not a member"), required=req.target_entity_id,
        reason=reason, required_label=name,
    )


def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """`target_key` is a base domain or a skill definition id; the rank held
    is `skill_access.held_rank` (a missing base row is Initié, a missing
    definition row is not held)."""
    del reachable_ids
    rank = held_rank(db, character.id, req.target_key)
    threshold = req.threshold or 0
    met = rank is not None and rank >= threshold
    label = skill_label(db, req.target_key)
    current = rank if rank is not None else "not held"
    reason = (
        f"skill {label!r} at rank {rank}, meets requires >= {threshold}" if met
        else f"prerequisite not met — skill {label!r} is {current}, requires rank >= {threshold}"
    )
    return Verdict(
        type=req.type, met=met, current=current, required=threshold, reason=reason, required_label=label,
    )


def _eval_quest_completed(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
    """`target_key` is a quest offer id: met iff a quest the character took
    from that offer has its agenda `completed` (M1: a quest's state is its
    agenda's)."""
    del reachable_ids
    row = db.exec(
        select(Quest.id)
        .join(Agenda, Agenda.id == Quest.agenda_id)
        .where(
            Quest.character_id == character.id, Quest.offer_id == req.target_key,
            Agenda.status == "completed",
        )
    ).first()
    met = row is not None
    offer = db.get(QuestOffer, req.target_key) if req.target_key else None
    label = offer.title if offer is not None else str(req.target_key)
    reason = f"quest {label!r} completed" if met else f"prerequisite not met — quest {label!r} not completed"
    return Verdict(
        type=req.type, met=met, current=("completed" if met else "not completed"), required=req.target_key,
        reason=reason, required_label=label,
    )


_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
    "knowledge": _eval_knowledge,
    "relation_gte": _eval_relation_gte,
    "resource": _eval_resource,
    "location_reachable": _eval_location_reachable,
    "has_met": _eval_has_met,
    "faction_member": _eval_faction_member,
    "skill_rank_gte": _eval_skill_rank_gte,
    "quest_completed": _eval_quest_completed,
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


def evaluate_specs(
    requirements: tuple[RequirementSpec, ...], character: Character, db: Session,
) -> list[Verdict]:
    """Judge each requirement against `character`'s current state (C-02).
    Dispatches through `_EVALUATORS`; an unknown `type` raises fail-closed —
    it cannot happen through the DB (the CHECK forbids it), the branch exists
    so that widening `REQUIREMENT_TYPES` without adding an evaluator fails
    loudly. Shared by a step (`evaluate_requirements`) and a quest offer's
    eligibility (`quest_reads`), so both are one judgment.

    `_day_reachable_ids` is computed AT MOST ONCE per call, only if a
    `location_reachable` requirement is present — never per requirement."""
    needs_reachable = any(r.type == "location_reachable" for r in requirements)
    reachable_ids = _day_reachable_ids(character.current_location_id, db) if needs_reachable else None

    verdicts: list[Verdict] = []
    for req in requirements:
        evaluator = _EVALUATORS.get(req.type)
        if evaluator is None:
            raise ValueError(f"unknown requirement type {req.type!r}")
        verdicts.append(evaluator(req, character, db, reachable_ids))
    return verdicts


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
