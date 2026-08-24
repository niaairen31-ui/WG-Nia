"""Narration and the conditional rewrite (TICKET-0075, BRIEF-0075-d, Scope IN
items 3-4). One model call renders the frozen `FactSheet` (`day_resolve.py`)
into prose; `narrate`'s body never touches the DB directly (R3) — template
loading is delegated to `_load_day_prose_template`, so `narrate` itself
contains no `select(`.

Positive-form only (the gameplay model is abliterated — a negative
instruction like "do not invent names" is worthless). The `day_narration`
prompt asks for two things the judge (`day_narration_guard.py`) can then
verify structurally:
  1. Name ONLY people/places on the fact sheet's authorised list, and
     render every role hint as a function, never a name.
  2. Prefix each step's beat with the EXACT band marker
     (`[RÉUSSITE]`/`[PARTIEL]`/`[ÉCHEC]`) — `_BAND_MARKERS` below is the
     single source both this module's prompt-building and the judge's
     outcome-survival check key off.

The rewrite pass exists for a late-delta trigger — a role hint resolving to
a canon id AFTER narration was drafted — that CANNOT currently fire: no code
path ever turns an `entity_creation` germ into a real entity synchronously
(I2, `day_concordance.py` R5) or asynchronously (no applier exists yet for
that mutation_type). `detect_late_delta` is written against the day the
germ pathway eventually gets one; until then it is expected to always
return None in a correctly ordered run — see the execution notes for the
observed firing count.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .day_resolve import FactSheet
from .models import Entity, PassPlay, ProposedMutation, PromptTemplate
from .prompt_registry import effective_model
from .prompt_store import current_prompt

_log = logging.getLogger(__name__)

# A rewrite fires at most once per resolution — a judge failure after the
# rewrite is a stop, never a retry loop (Scope OUT).
MAX_REWRITE_ATTEMPTS = 1

# Shared with day_narration_guard.py's outcome-survival check — the single
# source of the band-to-marker mapping.
BAND_MARKERS: dict[str, str] = {"success": "[RÉUSSITE]", "partial": "[PARTIEL]", "failure": "[ÉCHEC]"}


@dataclass(frozen=True)
class LateDelta:
    role_hint: str
    resolved_name: str


def _load_day_prose_template(usage: str, world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    """`day_plan._load_day_plan_template`'s precedent, parametrized over
    `usage` so `narrate` and `rewrite` share one loader."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == usage,
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


def _render_fact_sheet(fact_sheet: FactSheet) -> str:
    lines = [f"Jour {fact_sheet.day_number}.", f"Personnage joueur : {fact_sheet.character_name}."]
    for step in fact_sheet.steps:
        marker = BAND_MARKERS[step.band]
        detail = f" (jet total {step.total})" if step.total is not None else " (aucun jet)"
        lines.append(f"- Étape « {step.objective} » — marqueur attendu {marker}{detail}.")
    if fact_sheet.npcs:
        lines.append("Personnes nommables : " + ", ".join(r.name for r in fact_sheet.npcs) + ".")
    if fact_sheet.locations:
        lines.append("Lieux nommables : " + ", ".join(r.name for r in fact_sheet.locations) + ".")
    if fact_sheet.role_hints:
        lines.append(
            "Personnes SANS nom résolu — désigne-les uniquement par leur fonction : "
            + ", ".join(fact_sheet.role_hints) + "."
        )
    return "\n".join(lines)


def narrate(fact_sheet: FactSheet, declaration: str, db: Session) -> str:
    """ONE model call (Scope IN item 3). Takes the fact sheet and the
    declaration and nothing else derived from the DB (R3): `db` is used
    only to load and read the prompt template."""
    template = _load_day_prose_template("day_narration", fact_sheet.world_id, db)
    if template is None:
        raise llm_parse.LlmParseError("day_narration: no active prompt_template for usage='day_narration'")
    version = current_prompt(db, template)

    user_msg = (
        version.user_template
        .replace("{declaration}", declaration)
        .replace("{fact_sheet}", _render_fact_sheet(fact_sheet))
        + "\n/no_think"
    )
    raw = ollama_client.chat(
        [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=effective_model(template, ollama_client.DEFAULT_MODEL),
        host=ollama_client.OLLAMA_HOST,
    )
    return raw.strip()


def rewrite(fact_sheet: FactSheet, prior_prose: str, delta: LateDelta, db: Session) -> str:
    """The conditional rewrite (Scope IN item 4). Receives the frozen fact
    sheet plus the single late delta, and nothing else — never the
    registry, never a fresh model call over the raw declaration."""
    template = _load_day_prose_template("day_rewrite", fact_sheet.world_id, db)
    if template is None:
        raise llm_parse.LlmParseError("day_narration: no active prompt_template for usage='day_rewrite'")
    version = current_prompt(db, template)

    user_msg = (
        version.user_template
        .replace("{fact_sheet}", _render_fact_sheet(fact_sheet))
        .replace("{role_hint}", delta.role_hint)
        .replace("{resolved_name}", delta.resolved_name)
        .replace("{prior_prose}", prior_prose)
        + "\n/no_think"
    )
    raw = ollama_client.chat(
        [
            {"role": "system", "content": version.system_prompt},
            {"role": "user", "content": user_msg},
        ],
        model=effective_model(template, ollama_client.DEFAULT_MODEL),
        host=ollama_client.OLLAMA_HOST,
    )
    _log.info("day_rewrite fired for role_hint=%r -> %r", delta.role_hint, delta.resolved_name)
    return raw.strip()


def detect_late_delta(fact_sheet: FactSheet, pass_play: PassPlay, db: Session) -> Optional[LateDelta]:
    """The rewrite's narrow, named trigger: a role hint on the fact sheet
    whose `entity_creation` germ has since been approved AND applied (a
    real `target_id` exists). See the module docstring — this currently
    never fires (no applier exists for `entity_creation` yet); the
    function is written against the day one does."""
    if not fact_sheet.role_hints:
        return None
    germs = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.pass_play_id == pass_play.id,
            ProposedMutation.mutation_type == "entity_creation",
            ProposedMutation.status == "applied",
        )
    ).all()
    for germ in germs:
        payload = germ.payload if isinstance(germ.payload, dict) else {}
        role_hint = str(payload.get("name") or "")
        if role_hint not in fact_sheet.role_hints or not germ.target_id:
            continue
        entity = db.get(Entity, germ.target_id)
        if entity is not None:
            return LateDelta(role_hint=role_hint, resolved_name=entity.name)
    return None
