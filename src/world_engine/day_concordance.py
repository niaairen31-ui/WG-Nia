"""Concordance and germ emission (TICKET-0075, BRIEF-0075-c — decision C1:
**the resolver never authors**; robustness and casting, TICKET-0081,
BRIEF-0081-a — decisions G2, C2-partition, F1, E2c).

This module is "another AI with the full registry" resolved to code — which
is strictly better, per the design conversation: a lookup cannot hallucinate
an id. No model call happens here (R1); every candidate comes from a real
`select(` against canon rows, scoped to the active world at query
construction (never post-fetch).

Matching order, tried in sequence per mention and stopping at the first hit
(`MATCHING_RUNGS`, dispatched through `_RUNG_LOOKUPS` — the same
one-tuple/one-dict idiom as `schedule_reads.PRESENT_PRECEDENCE`/
`_SOURCE_LOOKUPS`):

1. `named_exact` — surface_form against entity names, compared through
   `_normalize_surface` on both sides (casefold, accent-stripping, a bounded
   leading-article strip) so a qualified or article-prefixed name still
   matches.
2. `named_token` — surface_form against entity names as normalized token
   sets: an entity name whose tokens are a non-empty subset of the surface
   form's tokens matches, catching a trailing qualifier the exact rung
   misses.
3. `named_alias` — an alias/cover-role surface. None exists in this schema
   (D1: `faction_membership.cover_role` is a faction ROLE label, never a
   person's name) — this rung is a structural no-op, reported once as
   skipped rather than backed by a table built for the occasion.
4. `occupation` — persons only, inferred only: `role_hint` keywords against
   standing goals reached through `npc_schedule.standing_goal_id`, scoped to
   NPCs reachable from the character's current location (E2c — a `WHERE`
   clause, never an instruction).
5. `presence` — persons only, inferred only: `who_is_at` on a place mention
   already matched within the same call, swept across all four phases.

C2-partition (`Mention.kind` is already disjoint on this): two or more
equally good candidates on a NAMED mention is `ambiguous`, never resolved by
picking. Two or more equally good candidates on an INFERRED mention is
casting, not resolving — F1's `_cast_one` narrows the set through
`CAST_PRECEDENCE` and the winner lands in `cast`, never `ambiguous`.

`emit_germs` writes NOTHING (no `db.add(`, no `.commit(`) — it constructs
`ProposedMutation` objects and returns them; the caller (the
`/api/day/{id}/plan` route) adds and commits them in the same transaction as
the plan. TICKET-0081, BRIEF-0081-c gave it the two emission-side guards
TICKET-0019 already gave the tick path (name collision against an active
entity, dedup against a pending germ) plus a per-declaration quota — reads
only, deliberately redundant with the approval-side guard.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional

from sqlmodel import Session, select

from .day_extract import Mention
from .models import (
    SCHEDULE_PHASES,
    Character,
    Entity,
    NpcGoal,
    NpcSchedule,
    PassPlay,
    ProposedMutation,
    Relation,
)
from .schedule_reads import who_is_at

_log = logging.getLogger(__name__)

_CATEGORY_ENTITY_TYPE: dict[str, str] = {"place": "location", "person": "character", "faction": "faction"}

MATCHING_RUNGS: tuple[str, ...] = (
    "named_exact", "named_token", "named_alias", "occupation", "presence",
)

CAST_PRECEDENCE: tuple[str, ...] = ("presence", "relation", "stable")

# Bound on germs emitted per declaration (BRIEF-0081-c). Over the bound,
# truncate and report the count — never silently drop the excess without a
# log line.
MAX_GERMS_PER_DECLARATION = 3

_ALIAS_SKIP_NOTE = "rung 2 (named_alias) skipped — no alias/cover-role surface exists for entity names"

_LEADING_TOKENS: frozenset[str] = frozenset({
    "chez", "le", "la", "les", "l", "du", "de", "des", "au", "aux", "a",
})

_SURFACE_TOKEN_SPLIT = re.compile(r"[\s'’]+")

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
class CastMention:
    mention: Mention
    entity_id: str
    rung: str
    basis: str
    candidate_ids: tuple[str, ...]


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
    cast: tuple[CastMention, ...]
    ambiguous: tuple[AmbiguousMention, ...]
    unmatched: tuple[UnmatchedMention, ...]
    skipped_rungs: tuple[str, ...]


@dataclass(frozen=True)
class _ConcordContext:
    world_id: str
    place_candidate_ids: tuple[str, ...]
    reachable_location_ids: frozenset[str]


def _normalize_surface(text: str) -> str:
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


def _role_keywords(role_hint: str) -> list[str]:
    words = re.findall(r"[a-zA-Zàâäéèêëïîôöùûüçñ]+", role_hint.casefold())
    return [w for w in words if len(w) >= 4 and w not in _STOPWORDS]


def _rung_named_exact(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    if mention.kind != "named":
        return None
    entity_type = _CATEGORY_ENTITY_TYPE[mention.category]
    target = _normalize_surface(mention.surface_form)
    rows = db.exec(
        select(Entity).where(
            Entity.world_id == ctx.world_id,
            Entity.type == entity_type,
            Entity.status == "active",
        )
    ).all()
    matches = [e.id for e in rows if _normalize_surface(e.name) == target]
    return matches or None


def _rung_named_token(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    if mention.kind != "named":
        return None
    entity_type = _CATEGORY_ENTITY_TYPE[mention.category]
    surface_tokens = set(_normalize_surface(mention.surface_form).split())
    rows = db.exec(
        select(Entity).where(
            Entity.world_id == ctx.world_id,
            Entity.type == entity_type,
            Entity.status == "active",
        )
    ).all()
    matches: list[str] = []
    for entity in rows:
        name_tokens = set(_normalize_surface(entity.name).split())
        if not name_tokens or not name_tokens.issubset(surface_tokens):
            continue
        if not any(len(token) >= 3 for token in name_tokens):
            continue
        matches.append(entity.id)
    return matches or None


def _rung_named_alias(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    del mention, ctx, db
    # D1: no alias/cover-role surface exists for entity names. Per Scope OUT
    # ("Alias infrastructure"), this rung never builds one — it stays a
    # structural no-op forever, not a stub awaiting data.
    return None


def _concord_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:
    """A NEW, day-local `connects_to` BFS reader (D1, BRIEF-19; restated in
    `day_plan.py`'s module docstring and BRIEF-0075-b-amendment-1) — written
    fresh in this module rather than importing `day_plan._day_reachable_ids`
    or extracting a shared one. Unbounded, origin INCLUDED, both `connects_to`
    column orders, filtered to `Entity.type == "location"` and
    `Entity.status == "active"`. World-scoped at query construction via the
    origin's OWN `world_id` (never a post-fetch filter and never a caller-
    supplied context, so this reader cannot be handed the wrong world)."""
    origin_world_id = db.exec(select(Entity.world_id).where(Entity.id == origin_location_id)).first()
    if origin_world_id is None:
        return frozenset()
    visited: set[str] = {origin_location_id}
    frontier = [origin_location_id]
    while frontier:
        next_frontier: list[str] = []
        for loc_id in frontier:
            rows = db.exec(
                select(Relation).where(
                    Relation.world_id == origin_world_id,
                    Relation.type == "connects_to",
                    (Relation.entity_a_id == loc_id) | (Relation.entity_b_id == loc_id),
                )
            ).all()
            for rel in rows:
                other_id = rel.entity_b_id if rel.entity_a_id == loc_id else rel.entity_a_id
                if other_id in visited:
                    continue
                other = db.exec(
                    select(Entity).where(
                        Entity.id == other_id,
                        Entity.world_id == origin_world_id,
                        Entity.type == "location",
                        Entity.status == "active",
                    )
                ).first()
                if other is None:
                    continue
                visited.add(other_id)
                next_frontier.append(other_id)
        frontier = next_frontier
    return frozenset(visited)


def _rung_occupation(mention: Mention, ctx: _ConcordContext, db: Session) -> Optional[list[str]]:
    if mention.category != "person" or mention.kind != "inferred" or not mention.role_hint:
        return None
    # E2c, fail-closed: no known origin or no reachable location at all means
    # no world-wide fallback — the mention stays unmatched, not resolved.
    if not ctx.reachable_location_ids:
        return None
    keywords = _role_keywords(mention.role_hint)
    if not keywords:
        return None
    rows = db.exec(
        select(NpcSchedule.npc_id, NpcGoal.description)
        .join(NpcGoal, NpcGoal.id == NpcSchedule.standing_goal_id)
        .where(
            NpcSchedule.world_id == ctx.world_id,
            NpcSchedule.location_id.in_(tuple(ctx.reachable_location_ids)),
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
    "named_token": _rung_named_token,
    "named_alias": _rung_named_alias,
    "occupation": _rung_occupation,
    "presence": _rung_presence,
}


def _resolve_place_candidates(mentions: list[Mention], world_id: str, db: Session) -> tuple[str, ...]:
    # `_rung_named_exact` ONLY — an inferred place mention never reaches this
    # set (Scope OUT). Consequence for F1: `_cast_presence` is inert whenever
    # the place a cast candidate would need to be "present at" was inferred
    # rather than named, since `place_candidate_ids` has nothing to offer it.
    ctx = _ConcordContext(world_id=world_id, place_candidate_ids=(), reachable_location_ids=frozenset())
    place_ids: set[str] = set()
    for mention in mentions:
        if mention.category != "place":
            continue
        result = _rung_named_exact(mention, ctx, db)
        if result and len(result) == 1:
            place_ids.add(result[0])
    return tuple(sorted(place_ids))


def _cast_presence(candidates: list[str], ctx: _ConcordContext, character: Character, db: Session) -> list[str]:
    if not ctx.place_candidate_ids:
        return []
    present: set[str] = set()
    for location_id in ctx.place_candidate_ids:
        for phase in SCHEDULE_PHASES:
            present.update(who_is_at(location_id, phase, db, is_present=True))
    return [cid for cid in candidates if cid in present]


def _cast_relation(candidates: list[str], ctx: _ConcordContext, character: Character, db: Session) -> list[str]:
    # A NEW relation scan keyed on `character.id` (a player id): structurally
    # blind to `connects_to` — that type is location map topology, never a
    # social signal, and its `intensity=50` is meaningless here.
    rows = db.exec(
        select(Relation).where(
            Relation.world_id == ctx.world_id,
            Relation.type != "connects_to",
            (
                (Relation.entity_a_id == character.id) & Relation.entity_b_id.in_(tuple(candidates))
            ) | (
                (Relation.entity_b_id == character.id) & Relation.entity_a_id.in_(tuple(candidates))
            ),
        )
    ).all()
    best: dict[str, int] = {}
    for rel in rows:
        other_id = rel.entity_b_id if rel.entity_a_id == character.id else rel.entity_a_id
        best[other_id] = max(best.get(other_id, 0), rel.intensity)
    if not best:
        return []
    top = max(best.values())
    return [cid for cid, intensity in best.items() if intensity == top]


def _cast_stable(candidates: list[str], ctx: _ConcordContext, character: Character, db: Session) -> list[str]:
    del ctx, character, db
    return [min(candidates)]


_CAST_LOOKUPS: dict[str, Callable[[list[str], _ConcordContext, Character, Session], list[str]]] = {
    "presence": _cast_presence,
    "relation": _cast_relation,
    "stable": _cast_stable,
}


def _cast_one(candidate_ids: list[str], ctx: _ConcordContext, character: Character, db: Session) -> tuple[str, str]:
    """F1: each `CAST_PRECEDENCE` criterion narrows the candidate list; the
    first that narrows it to exactly one wins and names the basis. A
    criterion that narrows to zero is discarded (the prior, wider set
    survives to the next criterion) rather than emptying the pool. `stable`
    is TOTAL — the lexicographically lowest id always narrows a >=2-element
    list to exactly one — so this can never fall through."""
    candidates = list(candidate_ids)
    for basis in CAST_PRECEDENCE:
        narrowed = _CAST_LOOKUPS[basis](candidates, ctx, character, db)
        if len(narrowed) == 1:
            return narrowed[0], basis
        if narrowed:
            candidates = narrowed
    raise AssertionError("cast precedence exhausted without a winner — 'stable' is TOTAL")


def _classify(
    mention: Mention, result: list[str], rung_name: str, ctx: _ConcordContext, character: Character, db: Session,
) -> "MatchedMention | CastMention | AmbiguousMention":
    """Extracted out of `concord` for the function-length ceiling. C2-
    partition: a multi-candidate NAMED mention is a genuine identity
    collision (`ambiguous`, unchanged); a multi-candidate INFERRED mention is
    a role reference — any member satisfies it, so casting (F1) picks one."""
    if len(result) == 1:
        return MatchedMention(mention=mention, entity_id=result[0], rung=rung_name)
    if mention.kind == "named":
        return AmbiguousMention(mention=mention, candidate_ids=tuple(sorted(result)))
    entity_id, basis = _cast_one(result, ctx, character, db)
    return CastMention(
        mention=mention, entity_id=entity_id, rung=rung_name, basis=basis,
        candidate_ids=tuple(sorted(result)),
    )


def concord(mentions: list[Mention], character: Character, db: Session) -> ConcordanceResult:
    """Resolve every mention to a canon id, a cast, an ambiguity, or nothing
    — never by authoring (C1). World scoping happens in every rung's query
    construction (`ctx.world_id`), never as a post-fetch filter."""
    reachable_location_ids = (
        _concord_reachable_ids(character.current_location_id, db)
        if character.current_location_id is not None else frozenset()
    )
    ctx = _ConcordContext(
        world_id=character.world_id,
        place_candidate_ids=_resolve_place_candidates(mentions, character.world_id, db),
        reachable_location_ids=reachable_location_ids,
    )

    matched: list[MatchedMention] = []
    cast: list[CastMention] = []
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
            classified = _classify(mention, result, rung_name, ctx, character, db)
            if isinstance(classified, MatchedMention):
                matched.append(classified)
            elif isinstance(classified, CastMention):
                cast.append(classified)
            else:
                ambiguous.append(classified)
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
        matched=tuple(matched), cast=tuple(cast), ambiguous=tuple(ambiguous), unmatched=tuple(unmatched),
        skipped_rungs=tuple(sorted(skipped_rungs)),
    )


def _germ_blocked(name: str, world_id: Optional[str], db: Session) -> Optional[str]:
    """Two emission-side guards (BRIEF-0081-c), deliberately redundant with
    the approval-side ones TICKET-0019 already enforces
    (`_approve_entity_creation_shortcircuit`): a name colliding with an
    ACTIVE entity, or a still-open pending germ already proposing the same
    name. Reads only — returns a reason string (for the INFO log at the
    call site) or None."""
    folded = name.casefold()

    for entity in db.exec(
        select(Entity).where(Entity.world_id == world_id, Entity.status == "active")
    ).all():
        if entity.name.casefold() == folded:
            return f"collides with active entity {entity.name!r} ({entity.id})"

    for mut in db.exec(
        select(ProposedMutation).where(
            ProposedMutation.world_id == world_id,
            ProposedMutation.mutation_type == "entity_creation",
            ProposedMutation.status.in_(("proposed", "approved")),
        )
    ).all():
        payload = mut.payload if isinstance(mut.payload, dict) else {}
        if payload.get("created_entity_id"):
            # Already realized — a second, different NPC may legitimately
            # be needed, so this pending row no longer blocks a new germ.
            continue
        if str(payload.get("name") or "").casefold() == folded:
            return f"duplicates pending mutation {mut.id}"

    return None


def emit_germs(unmatched: tuple[UnmatchedMention, ...], pass_play: PassPlay, db: Session) -> list[ProposedMutation]:
    """Persons only (Scope IN item 3 / Scope OUT: places and factions are
    reported, never germinated). Constructs `ProposedMutation` rows and
    returns them — writes NOTHING itself (R1): no `db.add(`, no `.commit(`.
    The caller adds and commits them in the same transaction as the plan.
    Guards and quota per BRIEF-0081-c: `_germ_blocked` runs before the
    quota, so a blocked candidate never occupies a quota slot; the quota
    then keeps the first `MAX_GERMS_PER_DECLARATION` survivors in mention
    order and logs the truncated count."""
    character = db.get(Character, pass_play.character_id)
    world_id = character.world_id if character is not None else None

    survivors: list[UnmatchedMention] = []
    for item in unmatched:
        mention = item.mention
        if mention.category != "person":
            continue
        name = mention.role_hint or mention.surface_form
        reason = _germ_blocked(name, world_id, db)
        if reason is not None:
            _log.info("day_concordance.emit_germs: skipped germ for %r — %s", name, reason)
            continue
        survivors.append(item)

    if len(survivors) > MAX_GERMS_PER_DECLARATION:
        dropped = len(survivors) - MAX_GERMS_PER_DECLARATION
        _log.info(
            "day_concordance.emit_germs: truncated %d germ candidate(s) over MAX_GERMS_PER_DECLARATION=%d",
            dropped, MAX_GERMS_PER_DECLARATION,
        )
        survivors = survivors[:MAX_GERMS_PER_DECLARATION]

    germs: list[ProposedMutation] = []
    for item in survivors:
        mention = item.mention
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
