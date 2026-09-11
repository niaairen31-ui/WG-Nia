"""Shared action-lexicon resolver (TICKET-0084, BRIEF-0084-c).

The clamp that used to live sealed inside `cockpit/play_physical.py::_arbitrate`
moves here so a non-Play caller can use it without importing the Play surface.
The split is the point: the model proposes a free-text domain (`_arbitrate`),
this module judges it against the world's two closed sets (`judge`), and the
verdict is kept as an append-only audit trail (`record`) — never merge the
three jobs back together.

`judge` is pure: no DB, no I/O, never raises. `lexicon_terms` and `record` are
the only DB-touching functions here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from sqlmodel import Session, select

from .models import SkillDefinition, SkillResolution


@dataclass(frozen=True)
class Verdict:
    """One arbiter classification, judged against the closed sets.

    `verdict` is one of 'base' | 'matched' | 'unmatched'. `surface_form` is
    the raw string handed to `judge`, verbatim, always. `effective_domain` is
    what the caller should roll against: the base domain, the matched
    skill's base domain, or 'physical' on 'unmatched'.
    """

    verdict: str
    base_domain: Optional[str]
    skill_definition_id: Optional[str]
    surface_form: str
    effective_domain: str


def lexicon_terms(db: Session, *, world_id: str) -> tuple[str, ...]:
    """The world's `skill_definition` names, ordered, for prompt injection."""
    names = db.exec(
        select(SkillDefinition.name)
        .where(SkillDefinition.world_id == world_id)
        .order_by(SkillDefinition.name)
    ).all()
    return tuple(names)


def judge(
    raw: str,
    *,
    base_domains: Iterable[str],
    catalogue: Mapping[str, tuple[str, str]],
) -> Verdict:
    """Classify `raw` against the base domains and this world's catalogue.

    Pure — no DB, no I/O. `catalogue` maps a skill_definition name to
    `(skill_definition_id, base_domain)`. Matching is exact after `.strip()`
    and a lowercase compare on base domains only; catalogue names compare
    exactly as stored. Never raises: any input, including empty string and
    None-ish, yields 'unmatched'.
    """
    surface_form = raw if isinstance(raw, str) else ("" if raw is None else str(raw))
    stripped = surface_form.strip()

    for domain in base_domains:
        if stripped.lower() == domain.lower():
            return Verdict(
                verdict="base",
                base_domain=domain,
                skill_definition_id=None,
                surface_form=surface_form,
                effective_domain=domain,
            )

    match = catalogue.get(stripped)
    if match is not None:
        skill_definition_id, matched_base_domain = match
        return Verdict(
            verdict="matched",
            base_domain=None,
            skill_definition_id=skill_definition_id,
            surface_form=surface_form,
            effective_domain=matched_base_domain,
        )

    return Verdict(
        verdict="unmatched",
        base_domain=None,
        skill_definition_id=None,
        surface_form=surface_form,
        effective_domain="physical",
    )


def record(db: Session, *, world_id: str, conversation_id: str, verdict: Verdict) -> None:
    """Insert one `SkillResolution` row. Insert only — caller commits."""
    db.add(SkillResolution(
        world_id=world_id,
        conversation_id=conversation_id,
        surface_form=verdict.surface_form,
        verdict=verdict.verdict,
        base_domain=verdict.base_domain,
        skill_definition_id=verdict.skill_definition_id,
    ))
