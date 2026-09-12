"""World-scoped named-mention resolver (TICKET-0085, BRIEF-0085-a).

Extracted from `day_concordance.py`'s named rungs (RECON-0085-a, F1/F2): the
two named rungs depended on their concordance context only through
`world_id`, so they lift cleanly into a module with no day-chain coupling and
no `Mention`/`Character` import — the lore consultation chantier gets its own
resolver rather than reaching into the day chain for one.

The resolver never authors and never casts. No model call happens here: a
lookup cannot hallucinate an id. Every candidate comes from a real `select(`
against canon rows, scoped to the active world at query construction, never
post-fetch. Two or more candidates on a name is an ambiguity reported to the
creator, never resolved by picking — casting is play semantics and does not
exist on this path.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional

from sqlmodel import Session, select

from .models import Entity

_CATEGORY_ENTITY_TYPE: dict[str, str] = {"place": "location", "person": "character", "faction": "faction"}

# `named_alias` is NOT here (RECON F1: a permanent no-op in day_concordance —
# `faction_membership.cover_role` is a faction ROLE label, never a person's
# name). A no-op does not get carried into a new module to look complete.
NAMED_RUNGS: tuple[str, ...] = ("named_exact", "named_token")

_LEADING_TOKENS: frozenset[str] = frozenset({
    "chez", "le", "la", "les", "l", "du", "de", "des", "au", "aux", "a",
})

_SURFACE_TOKEN_SPLIT = re.compile(r"[\s'’]+")


def normalize_surface(text: str) -> str:
    """Casefold; NFKD-decompose and drop combining marks; strip a leading
    token drawn from `_LEADING_TOKENS` (bounded at three iterations, so a
    pathological run of articles cannot loop); collapse to single-space-
    joined tokens. Applied to BOTH sides of every named comparison — never
    to one side only, or a real name would drift out of reach of its own
    surface form. Splitting on apostrophes too (not just whitespace) is what
    makes the bare `"l"` entry usable: French elision ("l'aubergiste") never
    appears as a separate word otherwise."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    tokens = [t for t in _SURFACE_TOKEN_SPLIT.split(without_marks) if t]
    for _ in range(3):
        if tokens and tokens[0] in _LEADING_TOKENS:
            tokens.pop(0)
        else:
            break
    return " ".join(tokens)


def rung_named_exact(surface_form: str, category: str, world_id: str, db: Session) -> Optional[list[str]]:
    entity_type = _CATEGORY_ENTITY_TYPE[category]
    target = normalize_surface(surface_form)
    rows = db.exec(
        select(Entity).where(
            Entity.world_id == world_id,
            Entity.type == entity_type,
            Entity.status == "active",
        )
    ).all()
    matches = [e.id for e in rows if normalize_surface(e.name) == target]
    return matches or None


def rung_named_token(surface_form: str, category: str, world_id: str, db: Session) -> Optional[list[str]]:
    entity_type = _CATEGORY_ENTITY_TYPE[category]
    surface_tokens = set(normalize_surface(surface_form).split())
    rows = db.exec(
        select(Entity).where(
            Entity.world_id == world_id,
            Entity.type == entity_type,
            Entity.status == "active",
        )
    ).all()
    matches: list[str] = []
    for entity in rows:
        name_tokens = set(normalize_surface(entity.name).split())
        if not name_tokens or not name_tokens.issubset(surface_tokens):
            continue
        if not any(len(token) >= 3 for token in name_tokens):
            continue
        matches.append(entity.id)
    return matches or None


_NAMED_RUNG_LOOKUPS: dict[str, Callable[[str, str, str, Session], Optional[list[str]]]] = {
    "named_exact": rung_named_exact,
    "named_token": rung_named_token,
}


@dataclass(frozen=True)
class NamedResolution:
    verdict: str
    entity_id: Optional[str]
    candidate_ids: tuple[str, ...]
    rung: Optional[str]
    rungs_tried: tuple[str, ...]


def resolve_named(surface_form: str, category: str, world_id: str, db: Session) -> NamedResolution:
    """Walks `NAMED_RUNGS` in order, stopping at the first rung whose lookup
    returns non-`None`. Exactly one candidate is `matched`; two or more is
    `ambiguous` — the creator disambiguates, this function never picks.
    Every rung tried without a hit is `unmatched`. There is no fourth verdict
    and no casting branch."""
    rungs_tried: list[str] = []
    for rung_name in NAMED_RUNGS:
        rungs_tried.append(rung_name)
        result = _NAMED_RUNG_LOOKUPS[rung_name](surface_form, category, world_id, db)
        if result is None:
            continue
        candidate_ids = tuple(sorted(result))
        if len(candidate_ids) == 1:
            return NamedResolution(
                verdict="matched", entity_id=candidate_ids[0], candidate_ids=candidate_ids,
                rung=rung_name, rungs_tried=tuple(rungs_tried),
            )
        return NamedResolution(
            verdict="ambiguous", entity_id=None, candidate_ids=candidate_ids,
            rung=rung_name, rungs_tried=tuple(rungs_tried),
        )
    return NamedResolution(
        verdict="unmatched", entity_id=None, candidate_ids=(), rung=None,
        rungs_tried=tuple(rungs_tried),
    )
