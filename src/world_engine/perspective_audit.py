"""The perspective audit: every line an answer withheld, and why (TICKET-0125, BRIEF-0125-D, C-07; TICKET-0127, C-10).

For the creator and the journal only: a player-facing module never returns
it (`routes/player.py` journals it). It replays a valid plan's calls over
the same queries as `perspective_selectors` and names each line the view
dropped. Everybody's view: a creator-only note, a fact not public, a
non-public entity, a secret membership, a membership in a non-public
faction, a skill not visible at creation. A character's view: a fact he
does not know, one his own row keeps secret from the player's door
(`concealed`), one he believes wrongly, one he knows at an older version,
an entity, a membership or a skill he does not know. A mention that does
not resolve in the view is named under `names_only` -- never the creator
regime. Read-only: no write, no commit, no model call.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .facet_reads import creator_only_fact_ids
from .lore_query import LorePlan, _call_args, validate_plan
from .lore_resolve import resolve_named
from .models import Entity, Faction, FactionMembership, Knowledge, SkillDefinition
from .name_index import NAMES_ONLY
from .perspective_query import resolve_view_mentions
from .perspective_selectors import (
    PerspectiveView,
    _current_memberships,
    _facts_matching,
    _membership_shown,
    _participant_facts,
    _relation_facts,
    lookups_for,
    public_view,
)
from .prose_render import fact_is_stale, fact_texts

WITHHELD_REASONS: tuple[str, ...] = (
    "creator_only", "not_public", "entity_not_public", "secret_membership", "faction_not_public",
    "skill_not_visible", "not_known", "entity_unknown", "membership_unknown", "skill_unknown",
    "false_belief", "stale_version", "concealed",
)


def _membership_line(name: str, membership: FactionMembership) -> str:
    role = membership.cover_role if membership.cover_role is not None else membership.role
    return f"{name} ({role or '-'})"


def _concealed_ids(fact_ids: list[str], view: PerspectiveView, db: Session) -> set[str]:
    """At the player's door, the facts the holder's own stored row keeps
    secret (above `unaware`), in one query; empty at the creator's door."""
    if view.door != "player" or not fact_ids:
        return set()
    return set(db.exec(
        select(Knowledge.fact_id).where(
            Knowledge.entity_id == view.character_id,
            Knowledge.fact_id.in_(fact_ids),
            Knowledge.is_secret == True,  # noqa: E712
            Knowledge.level != "unaware",
        )
    ).all())


def _withheld_facts(facts: list, about: str, view: PerspectiveView, db: Session) -> list[tuple]:
    hidden = [f for f in facts if f.id not in view.fact_ids]
    creator_only = creator_only_fact_ids(db, [f.id for f in hidden])
    if view.kind != "character":
        return [
            ("creator_only" if fact.id in creator_only else "not_public", about, text)
            for fact, text in zip(hidden, fact_texts(db, hidden))
        ]
    concealed = _concealed_ids([f.id for f in hidden if f.id not in creator_only], view, db)
    lines = [
        ("creator_only" if fact.id in creator_only else "concealed" if fact.id in concealed else "not_known",
         about, text)
        for fact, text in zip(hidden, fact_texts(db, hidden))
    ]
    held = [f for f in facts if f.id in view.fact_ids]
    for fact, text in zip(held, fact_texts(db, held)):
        belief = view.beliefs[fact.id]
        if belief.incorrect:
            lines.append(("false_belief", about, text))
        if belief.text is None and fact_is_stale(fact, belief.as_of):
            lines.append(("stale_version", about, text))
    return lines


def _membership_withheld(
    member: Entity, faction: Entity, membership: FactionMembership, view: PerspectiveView, other: Entity,
    public_reason: str, name: str,
) -> Optional[tuple[str, str]]:
    """The reason and line of one membership the dossier drops, or None.
    Everybody's view keeps its test (the other end outside the view); a
    character's view, rule M."""
    if membership.is_secret:
        return ("secret_membership", _membership_line(name, membership))
    if view.kind != "character":
        if other.id not in view.entity_ids:
            return (public_reason, _membership_line(name, membership))
        return None
    if not _membership_shown(member, faction, view):
        return ("membership_unknown", _membership_line(name, membership))
    return None


def _withheld_dossier(entity: Entity, world_id: str, view: PerspectiveView, db: Session) -> list[tuple]:
    if entity.id not in view.entity_ids:
        reason = "entity_unknown" if view.kind == "character" else "entity_not_public"
        return [(reason, entity.name, entity.name)]
    facts = _participant_facts(entity.id, world_id, db)
    facts += [fact for fact, _ in _relation_facts(entity.id, world_id, db)]
    lines = _withheld_facts(facts, entity.name, view, db)
    for membership in _current_memberships(world_id, db, entity_id=entity.id):
        faction = db.get(Entity, membership.faction_id)
        if faction is None:
            continue
        line = _membership_withheld(entity, faction, membership, view, faction, "faction_not_public", faction.name)
        if line is not None:
            lines.append((line[0], entity.name, line[1]))
    if entity.type == "faction":
        for membership in _current_memberships(world_id, db, faction_id=entity.id):
            member = db.get(Entity, membership.entity_id)
            if member is None:
                continue
            line = _membership_withheld(member, entity, membership, view, member, "entity_not_public", member.name)
            if line is not None:
                lines.append((line[0], entity.name, line[1]))
    return lines


def _withheld_factions(world_id: str, view: PerspectiveView, db: Session) -> list[tuple]:
    factions = db.exec(
        select(Entity).join(Faction, Faction.id == Entity.id).where(
            Entity.world_id == world_id, Entity.status == "active",
        )
    ).all()
    reason = "entity_unknown" if view.kind == "character" else "entity_not_public"
    return [(reason, e.name, e.name) for e in factions if e.id not in view.entity_ids]


def _withheld_skills(world_id: str, view: PerspectiveView, db: Session) -> list[tuple]:
    definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
    reason = "skill_unknown" if view.kind == "character" else "skill_not_visible"
    return [(reason, d.name, d.name) for d in definitions if d.id not in view.skill_ids]


def withheld(
    plan: LorePlan, world_id: str, db: Session, bindings: Optional[dict[str, str]] = None,
) -> list[dict]:
    """The audit of everybody's view (`public_view`)."""
    return withheld_for(plan, public_view(db, world_id), db, bindings)


def withheld_for(
    plan: LorePlan, view: PerspectiveView, db: Session, bindings: Optional[dict[str, str]] = None,
) -> list[dict]:
    """`{reason, subject, content}` rows, sorted by subject, reason, content.
    `[]` for an invalid plan or an ambiguous mention."""
    lookups = lookups_for(view)
    world_id = view.world_id
    if not validate_plan(plan, db, lookups=lookups).ok:
        return []
    resolutions = resolve_view_mentions(plan, world_id, db, view, bindings)
    if any(r.verdict == "ambiguous" for r in resolutions.values()):
        return []
    entity_ids: dict[str, Optional[str]] = {}
    for mention in plan.mentions:
        resolution = resolutions[mention.ref]
        if resolution.verdict == "unmatched":
            resolution = resolve_named(mention.surface_form, mention.category, world_id, db, scope=NAMES_ONLY)
        entity_ids[mention.ref] = resolution.entity_id if resolution.verdict == "matched" else None

    lines: set[tuple] = set()
    for call in plan.calls:
        if call.selector in ("world_laws", "self_sheet"):
            continue
        if call.selector == "known_factions":
            lines.update(_withheld_factions(world_id, view, db))
            continue
        if call.selector == "known_skills":
            lines.update(_withheld_skills(world_id, view, db))
            continue
        spec = lookups[call.selector]
        if call.selector == "known_facts_mentioning":
            (text, _) = _call_args(call.args, spec.arg_kinds, world_id, {})
            facts = [fact for fact, _ in _facts_matching(text, world_id, db)]
            lines.update(_withheld_facts(facts, text, view, db))
            continue
        ref = next(a for a, kind in zip(call.args, spec.arg_kinds) if kind == "entity_id")
        entity_id = entity_ids.get(ref)
        entity = db.get(Entity, entity_id) if entity_id else None
        if entity is not None and entity.world_id == world_id:
            lines.update(_withheld_dossier(entity, world_id, view, db))
    return [
        {"reason": reason, "subject": subject, "content": content}
        for reason, subject, content in sorted(lines)
    ]
