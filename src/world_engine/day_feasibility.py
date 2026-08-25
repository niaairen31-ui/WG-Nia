"""The feasibility veto (TICKET-0075, BRIEF-0075-g — decision Y1).

The four `requires` forms (BRIEF-0075-b) and the budget cut are mechanical:
they judge preconditions and slot arithmetic, never whether a plan is
PLAUSIBLE for THIS character. This module adds the one place in the day
chain where fuzzy judgment is allowed, shaped so it structurally cannot do
damage: **the veto can only SHORTEN the day, never extend it.** `veto()`
calls the model exactly once; `clamp_verdict()` — pure, no `db`, no
`chat(`, no `datetime`, no `randint` — is what actually enforces that,
never the prompt. A model that can only subtract cannot break F1.

Input discipline (mini-RECON D1, resolved): the extraction passes
(`day_extract.py`) build no character-specific frame at all — only a
secret-free `world_frame(world)` (name + description; `World` carries no
secret column). `day_plan.emit_plan` adds exactly one more thing, a
character NAME, via `db.get(Entity, character.id)`. That pair — world
frame plus character name — is the entirety of "context" assembled
anywhere in the day chain; this module reuses BOTH builders verbatim
rather than assembling a deeper NPC-style frame (goals, secrets-excluded
knowledge, etc.) that nothing else in the chain has, and that would be
exactly the ad-hoc frame the mini-RECON warned against.

`veto()` never raises. Every failure mode — Ollama unreachable, unparseable
JSON, a missing/malformed field, a citation naming a step outside the
input — collapses to `outcome="unavailable"` with `veto_retained ==
python_retained`: **a veto that cannot be understood never shortens the day
either.** Only `day_plan.emit_plan` and the extraction passes are allowed to
abort the whole `/plan` call on a model failure (F1's "propose or stop"
posture); the veto is an ADD-ON judgment, and its own failure must never
block the plan Python already legally computed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .day_extract import world_frame
from .day_plan import BudgetResult
from .models import Character, Entity, PromptTemplate, World
from .prompt_registry import effective_model
from .prompt_store import current_prompt

_log = logging.getLogger(__name__)

VETO_OUTCOMES: tuple[str, ...] = ("honoured", "clamped", "unavailable")

# Same mild repetition controls as the other day-chain emission calls.
DAY_FEASIBILITY_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}


@dataclass(frozen=True)
class VetoVerdict:
    python_retained: int
    veto_retained: int
    reason: str
    cited_step_order: Optional[int]
    cited_objective: Optional[str]
    outcome: str  # one of VETO_OUTCOMES


def clamp_verdict(
    python_retained: int,
    raw_retained: object,
    raw_reason: object,
    raw_cited_step_order: object,
    step_objectives: tuple[str, ...],
) -> VetoVerdict:
    """Pure (R1): no `db`, `select(`, `chat(`, `datetime` or `randint`.
    Applied to every model response before it can affect anything (Scope IN
    item 2) — the ONLY place `veto_retained` is decided.

    `python_retained` is `len(step_objectives)`, the count of steps Python
    already retained (`budget_cut`'s output) — the input this function
    operates on, never re-derived here.

    A missing/wrongly-typed `retained` or `reason`, or a `cited_step_order`
    that is inconsistent with `retained` (must equal `retained + 1` — "the
    FIRST step the veto drops" — required exactly when `retained <
    python_retained`, forbidden otherwise, and must name a real position)
    makes the WHOLE verdict `unavailable`: Python's cut stands, untouched
    (R6). Otherwise the upper bound is enforced with an explicit `min(...)`
    (R2) — a verdict claiming MORE than `python_retained` is clamped down
    and reported `clamped`, never honoured, never an error."""
    def _unavailable(reason: str) -> VetoVerdict:
        return VetoVerdict(
            python_retained=python_retained, veto_retained=python_retained, reason=reason,
            cited_step_order=None, cited_objective=None, outcome="unavailable",
        )

    if not isinstance(raw_retained, int) or isinstance(raw_retained, bool):
        return _unavailable(f"veto response missing a valid 'retained' integer, got {raw_retained!r}")
    if not isinstance(raw_reason, str) or not raw_reason.strip():
        return _unavailable("veto response missing a non-empty 'reason'")
    reason = raw_reason.strip()

    drops = raw_retained < python_retained
    if drops:
        if raw_cited_step_order != raw_retained + 1 or not (1 <= raw_retained + 1 <= python_retained):
            return _unavailable(
                f"veto response cites step order {raw_cited_step_order!r}, inconsistent with "
                f"retained={raw_retained!r} over {python_retained} step(s)"
            )
    elif raw_cited_step_order is not None:
        return _unavailable(
            f"veto response cites step order {raw_cited_step_order!r} despite not dropping any step"
        )

    # THE CLAMP (R2): retained can never exceed what Python retained — a
    # verdict trying to raise the count is clamped DOWN, never honoured.
    veto_retained = max(0, min(raw_retained, python_retained))
    outcome = "honoured" if veto_retained == raw_retained else "clamped"

    if veto_retained < python_retained:
        cited_step_order = veto_retained + 1
        cited_objective = step_objectives[veto_retained]
    else:
        cited_step_order = None
        cited_objective = None

    return VetoVerdict(
        python_retained=python_retained, veto_retained=veto_retained, reason=reason,
        cited_step_order=cited_step_order, cited_objective=cited_objective, outcome=outcome,
    )


def _load_feasibility_template(world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """`day_plan._load_day_plan_template`'s precedent, verbatim."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "day_feasibility",
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


def _render_steps(included: tuple) -> str:
    """1-indexed so `cited_step_order` in the model's response and in
    `clamp_verdict` mean the same position."""
    return "\n".join(
        f"{idx}. {evaluated.step.objective} (coût {evaluated.step.cost})"
        for idx, evaluated in enumerate(included, start=1)
    )


def veto(budget_result: BudgetResult, character: Character, declaration: str, db: Session) -> VetoVerdict:
    """ONE model call (Scope IN item 1), parsed through `llm_parse` (M3),
    then domain-validated by `clamp_verdict`. NEVER raises: any failure —
    no template seeded, Ollama unreachable, unparseable JSON, a malformed
    field — becomes `outcome='unavailable'` with Python's cut unchanged (see
    module docstring). `evaluate_requirements`/`REQUIREMENT_TYPES` are never
    referenced here (R5) — the veto judges plausibility, never a
    precondition already judged by Python."""
    included = budget_result.included
    python_retained = len(included)
    step_objectives = tuple(evaluated.step.objective for evaluated in included)

    if python_retained == 0:
        # Nothing for the model to judge — no call, no citation possible.
        return VetoVerdict(
            python_retained=0, veto_retained=0, reason="aucune étape retenue à juger",
            cited_step_order=None, cited_objective=None, outcome="honoured",
        )

    def _unavailable(reason: str) -> VetoVerdict:
        _log.info("day_feasibility: veto unavailable — %s", reason)
        return VetoVerdict(
            python_retained=python_retained, veto_retained=python_retained, reason=reason,
            cited_step_order=None, cited_objective=None, outcome="unavailable",
        )

    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    world_id = world.id if world is not None else None

    template = _load_feasibility_template(world_id, db)
    if template is None:
        return _unavailable("no active prompt_template for usage='day_feasibility'")
    version = current_prompt(db, template)

    character_entity = db.get(Entity, character.id)
    character_name = character_entity.name if character_entity is not None else character.id

    user_msg = (
        version.user_template
        .replace("{character_name}", character_name)
        .replace("{world_frame}", world_frame(world))
        .replace("{declaration}", declaration)
        .replace("{steps}", _render_steps(included))
        + "\n/no_think"
    )

    try:
        raw = ollama_client.chat(
            [
                {"role": "system", "content": version.system_prompt},
                {"role": "user", "content": user_msg},
            ],
            model=effective_model(template, ollama_client.DEFAULT_MODEL),
            host=ollama_client.OLLAMA_HOST,
            format="json",
            options=DAY_FEASIBILITY_OPTIONS,
        )
    except ollama_client.OllamaError as exc:
        return _unavailable(f"model call failed: {exc}")

    try:
        obj = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError as exc:
        return _unavailable(f"unparseable veto response: {exc}")

    return clamp_verdict(
        python_retained=python_retained,
        raw_retained=obj.get("retained"),
        raw_reason=obj.get("reason"),
        raw_cited_step_order=obj.get("cited_step_order"),
        step_objectives=step_objectives,
    )
