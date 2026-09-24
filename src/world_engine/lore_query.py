"""Plan validation, execution and verdict classification for the lore
consultation surface (TICKET-0085, BRIEF-0085-b).

A plan is a Python object, never a query: mentions are resolved to
`entity.id` through `lore_resolve.resolve_named` (a lookup, never a model),
and calls are dispatched only through `lore_selectors._SELECTOR_LOOKUPS` (a
whitelist, never a name looked up ad hoc). Validation runs before a single
selector executes, so a plan naming anything outside the whitelist is
rejected before any row is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session

from .lore_resolve import near_candidates, pre_resolved, resolve_named
from .lore_selectors import SELECTORS, _SELECTOR_LOOKUPS
from .name_index import CREATOR


@dataclass(frozen=True)
class PlanMention:
    ref: str
    surface_form: str
    category: str


@dataclass(frozen=True)
class PlanCall:
    selector: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class LorePlan:
    mentions: tuple[PlanMention, ...]
    calls: tuple[PlanCall, ...]


@dataclass(frozen=True)
class PlanValidation:
    ok: bool
    reason: Optional[str]


@dataclass(frozen=True)
class LoreResult:
    verdict: str
    rows: tuple[dict, ...]
    trace: list[dict]
    ambiguous_mentions: tuple[dict, ...]
    unmatched_surface_forms: tuple[str, ...]
    rejection_reason: Optional[str]
    # One block per unmatched surface form, set only on `unknown_entity`
    # (BRIEF-0092-d, C-10): near names are computed here, never in the
    # renderer, which receives rows and never a `Session`.
    near: tuple[dict, ...] = ()


def validate_plan(plan: LorePlan, db: Session) -> PlanValidation:
    """Rejects, before any selector runs: a selector outside `SELECTORS`,
    an arg count not matching the spec's arity, an arg referencing an
    unknown mention ref, or an `arg_kinds` mismatch (a mention ref where
    `"world_id"` was expected, or `"$world"` where `"entity_id"` was
    expected)."""
    mention_refs = {m.ref for m in plan.mentions}
    for call in plan.calls:
        if call.selector not in SELECTORS:
            return PlanValidation(False, f"selector {call.selector!r} is not in the whitelist")
        spec = _SELECTOR_LOOKUPS[call.selector]
        if len(call.args) != spec.arity:
            return PlanValidation(
                False,
                f"selector {call.selector!r} expects {spec.arity} argument(s), got {len(call.args)}",
            )
        for arg, kind in zip(call.args, spec.arg_kinds):
            if arg == "$world":
                if kind != "world_id":
                    return PlanValidation(
                        False,
                        f"selector {call.selector!r} argument {arg!r} is $world but expects {kind!r}",
                    )
            elif arg not in mention_refs:
                return PlanValidation(
                    False,
                    f"selector {call.selector!r} argument {arg!r} references an unknown mention",
                )
            elif kind != "entity_id":
                return PlanValidation(
                    False,
                    f"selector {call.selector!r} argument {arg!r} is a mention but expects {kind!r}",
                )
    return PlanValidation(True, None)


def _resolve_mentions(
    plan: LorePlan, world_id: str, db: Session, bindings: Optional[dict[str, str]] = None
) -> tuple[dict, list[dict]]:
    bindings = bindings or {}
    resolutions = {}
    trace: list[dict] = []
    for mention in plan.mentions:
        if mention.ref in bindings:
            # A creator-chosen binding from /api/lore/resolve: pre-resolved,
            # never re-run through resolve_named (BRIEF-0085-c item 6) --
            # re-resolving an already-disambiguated mention would just hit
            # the same ambiguity again.
            resolution = pre_resolved(bindings[mention.ref])
        else:
            resolution = resolve_named(mention.surface_form, mention.category, world_id, db, scope=CREATOR)
        resolutions[mention.ref] = resolution
        trace.append(
            {
                "surface_form": mention.surface_form,
                "verdict": resolution.verdict,
                "rung": resolution.rung,
                "entity_id": resolution.entity_id,
            }
        )
    return resolutions, trace


def _near_blocks(surface_forms: tuple[str, ...], world_id: str, db: Session) -> tuple[dict, ...]:
    """C-10: the near names of each unmatched surface form, in plan order --
    display only, never a pick (N9b)."""
    return tuple(
        {
            "surface_form": surface_form,
            "candidates": [
                {"entity_id": c.entity_id, "name": c.name, "type": c.entity_type, "score": c.score}
                for c in near_candidates(surface_form, world_id, db, scope=CREATOR)
            ],
        }
        for surface_form in surface_forms
    )


def execute_plan(
    plan: LorePlan, world_id: str, db: Session, bindings: Optional[dict[str, str]] = None
) -> LoreResult:
    """Resolves every mention through `resolve_named`, then dispatches each
    call through `_SELECTOR_LOOKUPS`, truncating at each spec's `row_cap`
    and recording the truncation in the trace rather than dropping it
    silently. Validation gates every path to a selector call: an invalid
    plan returns `unsupported_selector` before a single mention is even
    resolved.

    `bindings` (BRIEF-0085-c) maps a mention `ref` to a creator-chosen
    `entity_id`, from `/api/lore/resolve`'s disambiguation round-trip: a
    bound mention is treated as pre-resolved and never reaches
    `resolve_named`. `None`/empty reproduces BRIEF-0085-b's original
    behavior exactly -- the `/api/lore/ask` path never passes bindings."""
    validation = validate_plan(plan, db)
    if not validation.ok:
        return LoreResult(
            verdict="unsupported_selector", rows=(), trace=[],
            ambiguous_mentions=(), unmatched_surface_forms=(),
            rejection_reason=validation.reason,
        )

    resolutions, trace = _resolve_mentions(plan, world_id, db, bindings)

    ambiguous = [
        {"ref": ref, "candidate_ids": resolution.candidate_ids}
        for ref, resolution in resolutions.items() if resolution.verdict == "ambiguous"
    ]
    if ambiguous:
        return LoreResult(
            verdict="ambiguous_mention", rows=(), trace=trace,
            ambiguous_mentions=tuple(ambiguous), unmatched_surface_forms=(),
            rejection_reason=None,
        )

    unmatched = tuple(
        m.surface_form for m in plan.mentions if resolutions[m.ref].verdict == "unmatched"
    )
    if unmatched:
        return LoreResult(
            verdict="unknown_entity", rows=(), trace=trace,
            ambiguous_mentions=(), unmatched_surface_forms=unmatched,
            rejection_reason=None, near=_near_blocks(unmatched, world_id, db),
        )

    rows: list[dict] = []
    content_row_count = 0
    for call in plan.calls:
        spec = _SELECTOR_LOOKUPS[call.selector]
        args = [world_id if a == "$world" else resolutions[a].entity_id for a in call.args]
        result_rows = spec.fn(*args, db)
        for row in result_rows:
            if "section" not in row:
                raise ValueError(
                    f"lore_query: selector {call.selector!r} returned a row with no "
                    "\"section\" key -- every selector row must carry one (BRIEF-0085-d "
                    "item 2: section is the grouping key the renderer and the trace both need)"
                )
        truncated = len(result_rows) > spec.row_cap
        result_rows = result_rows[: spec.row_cap]
        rows.extend(result_rows)
        content_row_count += sum(1 for r in result_rows if r.get("section") not in spec.context_sections)
        trace.append(
            {"selector": call.selector, "args": call.args, "row_count": len(result_rows), "truncated": truncated}
        )

    # A `context_sections` row (e.g. `entity_dossier`'s `identity`) proves
    # only that the entity exists, never that canon holds something on the
    # point asked — it counts toward `rows` (the renderer needs the name
    # even when canon is silent) but never toward `answered`.
    verdict = "answered" if content_row_count else "silent_canon"
    return LoreResult(
        verdict=verdict, rows=tuple(rows), trace=trace,
        ambiguous_mentions=(), unmatched_surface_forms=(),
        rejection_reason=None,
    )
