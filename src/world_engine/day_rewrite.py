"""The declaration rewrite (TICKET-0081, BRIEF-0081-b — decisions A2'/B2/J2).

Pure: no model call, no write, no canon-model construction. `render` turns a
player's raw declaration plus a `day_concordance.concord()` result into the
ONE string `day_plan_select.select_plan` and `day_plan.emit_plan` are handed
in place of `pass_play.declared_action` — the declaration's own words,
followed by a line per resolved mention naming the entity the model should
use. `resolutions` turns the same result into the row payloads
`writes.write_day_rewrite` persists. `load_latest` is the resolve-path
reader (item 7): it reads the LATEST `day_rewrite` for a `pass_play` back
into a `ConcordanceResult`, so `/resolve` never re-runs extraction.

`render` must NOT emit any `entity_id`, any `cast_basis`, or any discarded
candidate — the model sees names, never ids. It raises on an unresolved
`ambiguous` mention (the plan route's 409 must fire before this function is
ever reached), and is deterministic: the same declaration and the same
`ConcordanceResult` always render byte-identical text — no `set` iteration
anywhere in its body.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .day_concordance import (
    CastMention,
    ConcordanceResult,
    MatchedMention,
    UnmatchedMention,
)
from .day_extract import Mention
from .models import DayMentionResolution, DayRewrite, Entity


def render(declaration: str, result: ConcordanceResult, db: Session) -> str:
    """Deterministic assembly (Scope IN item 2): the declaration's own words,
    then a line per resolved mention naming the entity — matched and cast
    mentions render identically (no basis, no candidates); an unmatched
    person renders as its role. Iteration order is `result`'s own bucket
    order (matched, then cast, then unmatched) — never a set iteration, so
    two calls over the same inputs are byte-identical."""
    if result.ambiguous:
        raise ValueError(
            "day_rewrite.render called with unresolved ambiguity — the plan route's "
            "409 must fire before this function is ever reached"
        )

    def _name(entity_id: str) -> str:
        entity = db.get(Entity, entity_id)
        return entity.name if entity is not None else entity_id

    lines: list[str] = []
    for mm in result.matched:
        lines.append(f'- "{mm.mention.surface_form}" désigne {_name(mm.entity_id)} (déjà identifié).')
    for cm in result.cast:
        lines.append(f'- "{cm.mention.surface_form}" désigne {_name(cm.entity_id)} (déjà identifié).')
    for um in result.unmatched:
        if um.mention.category != "person":
            continue
        lines.append(
            f'- "{um.mention.surface_form}" : aucun personnage connu ne correspond — '
            f"désigne-le par sa fonction : {um.mention.role_hint or um.mention.surface_form}."
        )

    if not lines:
        return declaration
    return declaration + "\n\nRepères déjà résolus pour cette déclaration :\n" + "\n".join(lines)


def resolutions(result: ConcordanceResult) -> list[dict]:
    """The row payloads `writes.write_day_rewrite` persists, in mention
    order, `ordinal` assigned by position. Every mention gets a row
    regardless of category (unlike `render`, which only narrates persons for
    an unmatched mention) — this is the full fact sheet behind the rewrite,
    not just what the model was shown. `ambiguous` is never represented
    here: a non-empty `result.ambiguous` already made `render` raise before
    this function would ever be reached with the same result."""
    rows: list[dict] = []
    ordinal = 0
    for mm in result.matched:
        ordinal += 1
        rows.append({
            "ordinal": ordinal, "category": mm.mention.category, "surface_form": mm.mention.surface_form,
            "kind": mm.mention.kind, "role_hint": mm.mention.role_hint, "verdict": "matched",
            "entity_id": mm.entity_id, "rung": mm.rung, "cast_basis": None,
        })
    for cm in result.cast:
        ordinal += 1
        rows.append({
            "ordinal": ordinal, "category": cm.mention.category, "surface_form": cm.mention.surface_form,
            "kind": cm.mention.kind, "role_hint": cm.mention.role_hint, "verdict": "cast",
            "entity_id": cm.entity_id, "rung": cm.rung, "cast_basis": cm.basis,
        })
    for um in result.unmatched:
        ordinal += 1
        rows.append({
            "ordinal": ordinal, "category": um.mention.category, "surface_form": um.mention.surface_form,
            "kind": um.mention.kind, "role_hint": um.mention.role_hint, "verdict": "unmatched",
            "entity_id": None, "rung": None, "cast_basis": None,
        })
    return rows


def _reconstruct(rows: list[DayMentionResolution]) -> ConcordanceResult:
    matched: list[MatchedMention] = []
    cast: list[CastMention] = []
    unmatched: list[UnmatchedMention] = []
    for row in rows:
        mention = Mention(
            category=row.category, surface_form=row.surface_form, kind=row.kind, role_hint=row.role_hint,
        )
        if row.verdict == "matched":
            matched.append(MatchedMention(mention=mention, entity_id=row.entity_id, rung=row.rung))
        elif row.verdict == "cast":
            cast.append(CastMention(
                mention=mention, entity_id=row.entity_id, rung=row.rung, basis=row.cast_basis,
                candidate_ids=(),
            ))
        else:
            unmatched.append(UnmatchedMention(mention=mention, rungs_tried=()))
    return ConcordanceResult(
        matched=tuple(matched), cast=tuple(cast), ambiguous=(), unmatched=tuple(unmatched), skipped_rungs=(),
    )


def load_latest(pass_play_id: str, world_id: str, db: Session) -> Optional[ConcordanceResult]:
    """Resolve-path reader (Scope IN item 7): the LATEST `day_rewrite`
    generation for `pass_play_id`, reconstructed into a `ConcordanceResult`
    from its `day_mention_resolution` rows — no extraction call, no re-
    derivation. Returns `None` when no `day_rewrite` row exists at all; the
    caller (`routes/day.py`) turns that into a fail-closed 409 naming the
    missing trace."""
    rewrite = db.exec(
        select(DayRewrite)
        .where(DayRewrite.pass_play_id == pass_play_id, DayRewrite.world_id == world_id)
        .order_by(DayRewrite.generation.desc())
    ).first()
    if rewrite is None:
        return None
    rows = db.exec(
        select(DayMentionResolution)
        .where(DayMentionResolution.rewrite_id == rewrite.id, DayMentionResolution.world_id == world_id)
        .order_by(DayMentionResolution.ordinal)
    ).all()
    return _reconstruct(rows)
