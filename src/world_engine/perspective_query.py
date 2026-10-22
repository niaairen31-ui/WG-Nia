"""The public perspective's executor: a plan run over what everybody knows (TICKET-0125, BRIEF-0125-D, C-05, C-06).

The plan comes from the same planner as the creator's Lore question, but it
is validated against `perspective_selectors._PERSPECTIVE_LOOKUPS`, its
mentions resolve under the `public` name regime, and a player's binding is
accepted only among that mention's public candidates (never the creator's
binding test, which knows nothing of `is_public`). An unknown,
non-public or unnamed entity is one verdict, `nothing_known`: an absence is
never told apart from a secret. Read-only: no write, no commit, no model call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .lore_query import LorePlan, _call_args, validate_plan
from .lore_resolve import NamedResolution, pre_resolved, resolve_named
from .models import Entity
from .name_index import NameScope
from .perspective_selectors import _PERSPECTIVE_LOOKUPS, PublicView, public_view

PERSPECTIVE_VERDICTS: tuple[str, ...] = ("answered", "ambiguous_mention", "nothing_known", "unsupported_selector")


class BindingRefused(ValueError):
    """A binding names an unknown mention ref, or an entity outside that
    mention's public candidates."""


@dataclass(frozen=True)
class PerspectiveResult:
    verdict: str
    rows: tuple[dict, ...]
    ambiguous: tuple[dict, ...]
    rejection_reason: Optional[str]


def public_scope(view: PublicView) -> NameScope:
    return NameScope("public", known_fact_ids=view.fact_ids)


def resolve_public_mentions(
    plan: LorePlan, world_id: str, db: Session, view: PublicView,
    bindings: Optional[dict[str, str]] = None,
) -> dict[str, NamedResolution]:
    """Every mention resolved under the public scope (C-06): a bound mention
    keeps its binding only when the bound id is one of its public
    candidates. `BindingRefused` otherwise, before any selector runs."""
    bindings = bindings or {}
    refs = {m.ref for m in plan.mentions}
    unknown = sorted(set(bindings) - refs)
    if unknown:
        raise BindingRefused(f"binding for unknown mention ref(s) {unknown!r}")
    scope = public_scope(view)
    resolutions: dict[str, NamedResolution] = {}
    for mention in plan.mentions:
        resolution = resolve_named(mention.surface_form, mention.category, world_id, db, scope=scope)
        if mention.ref in bindings:
            bound = bindings[mention.ref]
            if bound not in resolution.candidate_ids:
                raise BindingRefused(f"binding {mention.ref!r} is not one of the mention's public candidates")
            resolution = pre_resolved(bound)
        resolutions[mention.ref] = resolution
    return resolutions


def _ambiguous_items(resolutions: dict[str, NamedResolution], view: PublicView, db: Session) -> tuple[dict, ...]:
    items = []
    for ref, resolution in resolutions.items():
        if resolution.verdict != "ambiguous":
            continue
        ids = [cid for cid in resolution.candidate_ids if cid in view.entity_ids]
        entities = db.exec(
            select(Entity).where(Entity.world_id == view.world_id, Entity.id.in_(ids))
        ).all() if ids else []
        items.append({
            "ref": ref,
            "candidates": [
                {"entity_id": e.id, "name": e.name, "type": e.type}
                for e in sorted(entities, key=lambda e: (e.name, e.id))
            ],
        })
    return tuple(items)


def execute_public_plan(
    plan: LorePlan, world_id: str, db: Session, bindings: Optional[dict[str, str]] = None,
) -> PerspectiveResult:
    """Validate, resolve under the public scope, then run each call through
    `_PERSPECTIVE_LOOKUPS`, truncated at its `row_cap`. `answered` iff a row
    lies outside the spec's `context_sections`."""
    validation = validate_plan(plan, db, lookups=_PERSPECTIVE_LOOKUPS)
    if not validation.ok:
        return PerspectiveResult(
            verdict="unsupported_selector", rows=(), ambiguous=(), rejection_reason=validation.reason,
        )
    view = public_view(db, world_id)
    resolutions = resolve_public_mentions(plan, world_id, db, view, bindings)
    ambiguous = _ambiguous_items(resolutions, view, db)
    if ambiguous:
        return PerspectiveResult(verdict="ambiguous_mention", rows=(), ambiguous=ambiguous, rejection_reason=None)
    if any(resolution.verdict == "unmatched" for resolution in resolutions.values()):
        return PerspectiveResult(verdict="nothing_known", rows=(), ambiguous=(), rejection_reason=None)

    rows: list[dict] = []
    content_row_count = 0
    for call in plan.calls:
        spec = _PERSPECTIVE_LOOKUPS[call.selector]
        args = _call_args(call.args, spec.arg_kinds, world_id, resolutions)
        result_rows = spec.fn(*args, view, db)
        for row in result_rows:
            if "section" not in row:
                raise ValueError(f"perspective_query: selector {call.selector!r} returned a row with no \"section\"")
        result_rows = result_rows[: spec.row_cap]
        rows.extend(result_rows)
        content_row_count += sum(1 for r in result_rows if r["section"] not in spec.context_sections)
    if not content_row_count:
        return PerspectiveResult(verdict="nothing_known", rows=(), ambiguous=(), rejection_reason=None)
    return PerspectiveResult(verdict="answered", rows=tuple(rows), ambiguous=(), rejection_reason=None)
