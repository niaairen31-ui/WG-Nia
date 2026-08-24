"""Concordance and germ emission (TICKET-0075, BRIEF-0075-c — decision C1:
**the resolver never authors**).

This module is "another AI with the full registry" resolved to code — which
is strictly better, per the design conversation: a lookup cannot hallucinate
an id. No model call happens here (R1); every candidate comes from a real
`select(` against canon rows, scoped to the active world at query
construction (never post-fetch).

Matching order, tried in sequence per mention and stopping at the first hit
(`MATCHING_RUNGS`, dispatched through `_RUNG_LOOKUPS` — the same
one-tuple/one-dict idiom as `schedule_reads.PRESENT_PRECEDENCE`/
`_SOURCE_LOOKUPS`):

1. `named_exact` — surface_form against entity names, case-folded.
2. `named_alias` — an alias/cover-role surface. None exists in this schema
   (D1: `faction_membership.cover_role` is a faction ROLE label, never a
   person's name) — this rung is a structural no-op, reported once as
   skipped rather than backed by a table built for the occasion.
3. `occupation` — persons only, inferred only: `role_hint` keywords against
   standing goals reached through `npc_schedule.standing_goal_id`.
4. `presence` — persons only, inferred only: `who_is_at` on a place mention
   already matched within the same call, swept across all four phases.

Two or more equally good candidates is `ambiguous`, never resolved by
picking. `emit_germs` writes NOTHING (no `db.add(`, no `.commit(`) — it
constructs `ProposedMutation` objects and returns them; the caller (the
`/api/day/{id}/plan` route) adds and commits them in the same transaction as
the plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from sqlmodel import Session, select

from .day_extract import Mention
from .models import SCHEDULE_PHASES, Character, Entity, NpcGoal, NpcSchedule, PassPlay, ProposedMutation
from .schedule_reads import who_is_at

_CATEGORY_ENTITY_TYPE: dict[str, str] = {"place": "location", "person": "character", "faction": "faction"}

MATCHING_RUNGS: tuple[str, ...] = ("named_exact", "named_alias", "occupation", "presence")

_ALIAS_SKIP_NOTE = "rung 2 (named_alias) skipped — no alias/cover-role surface exists for entity names"

_STOPWORDS = frozenset({
    "who", "that", "someone", "something", "with", "near", "from", "have",
    "knows", "sells", "deals", "quelqu", "connait", "connaît", "vend", "près",
})


@dataclass(frozen=True)
class MatchedMention:
    mention: Mention
    entity_id: str
    rung: str


@dataclass(frozen=True)
class AmbiguousMention:
    mention: Mention
    candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class UnmatchedMention:
    mention: Mention
    rungs_tried: tuple[str, ...]
    candidate_location_id: Optional[str] = None


@dataclass(frozen=True)
class ConcordanceResult:
    matched: tuple[MatchedMention, ...]
    ambiguous: tuple[AmbiguousMention, ...]
    unmatched: tuple[UnmatchedMention, ...]
    skipped_rungs: tuple[str, ...]


@dataclass(frozen=True)
class _ConcordContext:
    world_id: str
    place_candidate_ids: tuple[str, ...]


def _role_keywords(role_hint: str) -> list[str]:
    words = re.findall(r"[a-zA-Zàâäéèêëïîôöùûüçñ]+", role_hint.casefold())
    return [w for w in words if len(w) >= 4 and w not in _STOPWORDS]


def _rung_named_exact(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    if mention.kind != "named":
        return None
    entity_type = _CATEGORY_ENTITY_TYPE[mention.category]
    target = mention.surface_form.casefold()
    rows = db.exec(
        select(Entity).where(
            Entity.world_id == ctx.world_id,
            Entity.type == entity_type,
            Entity.status == "active",
        )
    ).all()
    matches = [e.id for e in rows if e.name.casefold() == target]
    return matches or None


def _rung_named_alias(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    del mention, ctx, db
    # D1: no alias/cover-role surface exists for entity names. Per Scope OUT
    # ("Alias infrastructure"), this rung never builds one — it stays a
    # structural no-op forever, not a stub awaiting data.
    return None


def _rung_occupation(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    if mention.category != "person" or mention.kind != "inferred" or not mention.role_hint:
        return None
    keywords = _role_keywords(mention.role_hint)
    if not keywords:
        return None
    rows = db.exec(
        select(NpcSchedule.npc_id, NpcGoal.description)
        .join(NpcGoal, NpcGoal.id == NpcSchedule.standing_goal_id)
        .where(
            NpcSchedule.world_id == ctx.world_id,
            NpcGoal.kind == "standing",
            NpcGoal.status == "active",
        )
    ).all()
    matched_npc_ids = {
        npc_id
        for npc_id, description in rows
        if any(kw in (description or "").casefold() for kw in keywords)
    }
    return list(matched_npc_ids) or None


def _rung_presence(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    if mention.category != "person" or mention.kind != "inferred" or not ctx.place_candidate_ids:
        return None
    found: set[str] = set()
    for location_id in ctx.place_candidate_ids:
        for phase in SCHEDULE_PHASES:
            found.update(who_is_at(location_id, phase, db, is_present=True))
    return list(found) or None


_RUNG_LOOKUPS: dict[str, Callable[[Mention, _ConcordContext, Session], Optional[list[str]]]] = {
    "named_exact": _rung_named_exact,
    "named_alias": _rung_named_alias,
    "occupation": _rung_occupation,
    "presence": _rung_presence,
}


def _resolve_place_candidates(mentions: list[Mention], world_id: str, db: Session) -> tuple[str, ...]:
    ctx = _ConcordContext(world_id=world_id, place_candidate_ids=())
    place_ids: set[str] = set()
    for mention in mentions:
        if mention.category != "place":
            continue
        result = _rung_named_exact(mention, ctx, db)
        if result and len(result) == 1:
            place_ids.add(result[0])
    return tuple(sorted(place_ids))


def concord(mentions: list[Mention], character: Character, db: Session) -> ConcordanceResult:
    """Resolve every mention to a canon id, an ambiguity, or nothing — never
    by authoring (C1). World scoping happens in every rung's query
    construction (`ctx.world_id`), never as a post-fetch filter."""
    ctx = _ConcordContext(
        world_id=character.world_id,
        place_candidate_ids=_resolve_place_candidates(mentions, character.world_id, db),
    )

    matched: list[MatchedMention] = []
    ambiguous: list[AmbiguousMention] = []
    unmatched: list[UnmatchedMention] = []
    skipped_rungs: set[str] = set()

    for mention in mentions:
        rungs_tried: list[str] = []
        resolved = False
        for rung_name in MATCHING_RUNGS:
            rungs_tried.append(rung_name)
            result = _RUNG_LOOKUPS[rung_name](mention, ctx, db)
            if rung_name == "named_alias":
                skipped_rungs.add(_ALIAS_SKIP_NOTE)
            if result is None:
                continue
            if len(result) == 1:
                matched.append(MatchedMention(mention=mention, entity_id=result[0], rung=rung_name))
            else:
                ambiguous.append(AmbiguousMention(mention=mention, candidate_ids=tuple(sorted(result))))
            resolved = True
            break
        if not resolved:
            unmatched.append(UnmatchedMention(
                mention=mention,
                rungs_tried=tuple(rungs_tried),
                candidate_location_id=(
                    ctx.place_candidate_ids[0]
                    if mention.category == "person" and ctx.place_candidate_ids
                    else None
                ),
            ))

    return ConcordanceResult(
        matched=tuple(matched), ambiguous=tuple(ambiguous), unmatched=tuple(unmatched),
        skipped_rungs=tuple(sorted(skipped_rungs)),
    )


def emit_germs(unmatched: tuple[UnmatchedMention, ...], pass_play: PassPlay, db: Session) -> list[ProposedMutation]:
    """Persons only (Scope IN item 3 / Scope OUT: places and factions are
    reported, never germinated). Constructs `ProposedMutation` rows and
    returns them — writes NOTHING itself (R1): no `db.add(`, no `.commit(`.
    The caller adds and commits them in the same transaction as the plan."""
    character = db.get(Character, pass_play.character_id)
    world_id = character.world_id if character is not None else None

    germs: list[ProposedMutation] = []
    for item in unmatched:
        mention = item.mention
        if mention.category != "person":
            continue
        name = mention.role_hint or mention.surface_form
        rationale = f"matching rungs tried and missed: {', '.join(item.rungs_tried)}"
        if item.candidate_location_id:
            rationale += f"; anchored near location {item.candidate_location_id}"
        payload = {
            "entity_type": "character",
            "name": name,
            "concept": f"Rôle à pourvoir : {name}.",
            "anchor": item.candidate_location_id,
            "role_hint": mention.role_hint,
            "surface_form": mention.surface_form,
            "kind": mention.kind,
            "candidate_location_id": item.candidate_location_id,
        }
        germs.append(ProposedMutation(
            world_id=world_id,
            source_type="pass_play",
            pass_play_id=pass_play.id,
            mutation_type="entity_creation",
            payload=payload,
            status="proposed",
            proposed_by="local_ai",
            rationale=rationale,
        ))
    return germs


def plan_context(result: ConcordanceResult, db: Session) -> str:
    """A short French summary handed to `day_plan.emit_plan` (Scope IN item
    4) so a matched mention reaches the plan as a resolved name and an
    unmatched person reaches it as a role, never a canon id the model could
    misuse. Pure text; the model never sees this module's queries."""
    lines: list[str] = []
    for mm in result.matched:
        entity = db.get(Entity, mm.entity_id)
        display = entity.name if entity is not None else mm.entity_id
        lines.append(f'- "{mm.mention.surface_form}" désigne {display} (déjà identifié).')
    for um in result.unmatched:
        if um.mention.category != "person":
            continue
        lines.append(
            f'- "{um.mention.surface_form}" : aucun personnage connu ne correspond — '
            f"désigne-le par sa fonction : {um.mention.role_hint or um.mention.surface_form}."
        )
    if not lines:
        return ""
    return "Repères déjà résolus pour cette déclaration :\n" + "\n".join(lines)
