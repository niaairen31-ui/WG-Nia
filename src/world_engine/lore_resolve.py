"""World-scoped named-mention resolver (TICKET-0085, BRIEF-0085-a; reads the
name index since TICKET-0092, BRIEF-0092-b).

Extracted from `day_concordance.py`'s named rungs (RECON-0085-a, F1/F2): the
lore consultation chantier gets its own resolver rather than reaching into
the day chain for one. No day-chain type is imported here.

The rungs are pure functions over name surfaces (`name_index.surfaces`):
entity names and appellations are candidates of equal rank (N11a). Which
appellations a caller sees is the `NameScope` it passes — every caller
states one, there is no default. The `named_partial` rung runs only under
the `creator` regime (N12a), and so do near candidates.

The resolver never authors and never casts. No model call happens here: a
lookup cannot hallucinate an id. Two or more candidates on a name is an
ambiguity reported to the creator, never resolved by picking — casting is
play semantics and does not exist on this path.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from sqlmodel import Session, select

from .models import Entity
from .name_index import NameScope, NameSurface, surfaces

_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
}

# `named_alias` is NOT here (RECON F1: a permanent no-op in day_concordance —
# `faction_membership.cover_role` is a faction ROLE label, never a person's
# name). A no-op does not get carried into a new module to look complete.
NAMED_RUNGS: tuple[str, ...] = ("named_exact", "named_token", "named_partial")

NEAR_RATIO = 0.8
NEAR_LIMIT = 5

_LEADING_TOKENS: frozenset[str] = frozenset({
    "chez", "le", "la", "les", "l", "du", "de", "des", "au", "aux", "a",
})

_SURFACE_TOKEN_SPLIT = re.compile(r"[\s'’]+")


def category_of_type(entity_type: str) -> Optional[str]:
    """The category whose type tuple claims `entity_type`, else None."""
    for category, types in _CATEGORY_ENTITY_TYPE.items():
        if entity_type in types:
            return category
    return None


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


def _rung(surface_form: str, category: str, name_surfaces: Sequence[NameSurface],
          match: Callable[[str, set[str], str, set[str]], bool]) -> Optional[list[str]]:
    """The sorted distinct ids of the `category` surfaces `match` accepts,
    given `F`, `TF` (the surface form) and `K`, `TK` (the surface), or None."""
    target = normalize_surface(surface_form)
    target_tokens = set(target.split())
    ids: set[str] = set()
    for s in name_surfaces:
        if category_of_type(s.entity_type) != category:
            continue
        key = normalize_surface(s.text)
        if match(target, target_tokens, key, set(key.split())):
            ids.add(s.entity_id)
    return sorted(ids) or None


def rung_named_exact(surface_form: str, category: str,
                     name_surfaces: Sequence[NameSurface]) -> Optional[list[str]]:
    return _rung(surface_form, category, name_surfaces,
                 lambda f, tf, k, tk: f != "" and k == f)


def rung_named_token(surface_form: str, category: str,
                     name_surfaces: Sequence[NameSurface]) -> Optional[list[str]]:
    return _rung(surface_form, category, name_surfaces,
                 lambda f, tf, k, tk: bool(tk) and tk <= tf and any(len(t) >= 3 for t in tk))


def rung_named_partial(surface_form: str, category: str,
                       name_surfaces: Sequence[NameSurface]) -> Optional[list[str]]:
    return _rung(surface_form, category, name_surfaces,
                 lambda f, tf, k, tk: bool(tf) and all(len(t) >= 3 for t in tf) and tf <= tk)


_NAMED_RUNG_LOOKUPS: dict[str, Callable[[str, str, Sequence[NameSurface]], Optional[list[str]]]] = {
    "named_exact": rung_named_exact,
    "named_token": rung_named_token,
    "named_partial": rung_named_partial,
}


@dataclass(frozen=True)
class NamedResolution:
    verdict: str
    entity_id: Optional[str]
    candidate_ids: tuple[str, ...]
    rung: Optional[str]
    rungs_tried: tuple[str, ...]


def resolve_named(surface_form: str, category: str, world_id: str, db: Session, *,
                  scope: NameScope) -> NamedResolution:
    """Walks `NAMED_RUNGS` in order over `name_index.surfaces(db, world_id,
    scope)` (built once), stopping at the first rung whose lookup returns
    non-`None`; `named_partial` is skipped unless the regime is `creator`
    (N12a). Exactly one candidate is `matched`; two or more is `ambiguous` —
    the creator disambiguates, this function never picks. Every rung tried
    without a hit is `unmatched`. There is no fourth verdict and no casting
    branch."""
    name_surfaces = surfaces(db, world_id, scope)
    rungs_tried: list[str] = []
    for rung_name in NAMED_RUNGS:
        if rung_name == "named_partial" and scope.regime != "creator":
            continue
        rungs_tried.append(rung_name)
        result = _NAMED_RUNG_LOOKUPS[rung_name](surface_form, category, name_surfaces)
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


@dataclass(frozen=True)
class NearCandidate:
    entity_id: str
    name: str          # entity.name
    entity_type: str
    surface: str       # the surface text that scored highest
    score: int         # 0-100, ratio * 100 rounded half up


def near_candidates(surface_form: str, world_id: str, db: Session, *,
                    scope: NameScope, exclude_ids: frozenset[str] = frozenset()
                    ) -> tuple[NearCandidate, ...]:
    """Names close to `surface_form`, for display only — never a pick (N5c,
    N9b). Creator regime only (N12a); every category counts. A surface
    qualifies on a `difflib` ratio >= `NEAR_RATIO` or a shared 3+ token; per
    entity the best-scoring qualifying surface is kept."""
    if scope.regime != "creator":
        raise ValueError(f"near_candidates takes the creator regime, not {scope.regime!r}")
    target = normalize_surface(surface_form)
    if not target:
        return ()
    long_target = {t for t in target.split() if len(t) >= 3}
    best: dict[str, tuple[float, NameSurface]] = {}
    for s in surfaces(db, world_id, scope):
        if s.entity_id in exclude_ids:
            continue
        key = normalize_surface(s.text)
        ratio = difflib.SequenceMatcher(None, target, key).ratio()
        shared = long_target & {t for t in key.split() if len(t) >= 3}
        if ratio < NEAR_RATIO and not shared:
            continue
        if s.entity_id not in best or ratio > best[s.entity_id][0]:
            best[s.entity_id] = (ratio, s)
    # Half-up, not `round()`: banker's rounding would score 0.625 as 62, and
    # the lot's Near table (La Reine Grise, 63) is the acceptance reference.
    found = [
        NearCandidate(s.entity_id, s.entity_name, s.entity_type, s.text, int(ratio * 100 + 0.5))
        for ratio, s in best.values()
    ]
    found.sort(key=lambda c: (-c.score, c.name.casefold(), c.entity_id))
    return tuple(found[:NEAR_LIMIT])


def pre_resolved(entity_id: str) -> NamedResolution:
    """A creator-chosen binding from `/api/lore/resolve` (BRIEF-0085-c),
    treated as already resolved -- never routed through a rung. Lives here,
    not as an inline `NamedResolution(...)` in `lore_query.py`, so that
    module's `verdict=` keyword stays exclusively `LoreResult`'s closed
    five-value set for `lore_selectors.py`'s R5 check."""
    return NamedResolution(
        verdict="matched", entity_id=entity_id, candidate_ids=(entity_id,),
        rung=None, rungs_tried=(),
    )


def validate_binding(entity_id: str, category: str, world_id: str, db: Session) -> bool:
    """True iff `entity_id` is an active entity in `world_id` whose `type`
    is in `_CATEGORY_ENTITY_TYPE[category]`; an unknown category is False.
    Used by `/api/lore/resolve` (TICKET-0085, BRIEF-0085-c) to re-check a
    client-echoed binding: the id was produced by this server a moment ago,
    but a client-supplied plan is untrusted input all the same, so it is
    looked up again, never trusted."""
    entity_types = _CATEGORY_ENTITY_TYPE.get(category)
    if entity_types is None:
        return False
    entity = db.exec(
        select(Entity).where(
            Entity.id == entity_id,
            Entity.world_id == world_id,
            Entity.type.in_(entity_types),
            Entity.status == "active",
        )
    ).first()
    return entity is not None
