"""The public perspective's audit: every line a public answer withheld, and why (TICKET-0125, BRIEF-0125-D, C-07).

For the creator and the journal only: a player-facing module never returns
it (`routes/player.py` journals it). It replays a valid plan's calls over
the same queries as `perspective_selectors` and names each line the public
view dropped: a creator-only note, a fact not public, a non-public entity,
a secret membership, a membership in a non-public faction. A mention that
does not resolve publicly is named under `names_only` -- never the creator
regime. Read-only: no write, no commit, no model call.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .facet_reads import creator_only_fact_ids
from .lore_query import LorePlan, _call_args, validate_plan
from .lore_resolve import resolve_named
from .models import Entity, Faction, FactionMembership
from .name_index import NAMES_ONLY
from .perspective_query import resolve_public_mentions
from .perspective_selectors import (
    _PERSPECTIVE_LOOKUPS,
    PublicView,
    _current_memberships,
    _facts_matching,
    _participant_facts,
    _relation_facts,
    public_view,
)
from .prose_render import fact_texts

WITHHELD_REASONS: tuple[str, ...] = (
    "creator_only", "not_public", "entity_not_public", "secret_membership", "faction_not_public",
)


def _membership_line(name: str, membership: FactionMembership) -> str:
    role = membership.cover_role if membership.cover_role is not None else membership.role
    return f"{name} ({role or '-'})"


def _withheld_facts(facts: list, about: str, view: PublicView, db: Session) -> list[tuple]:
    hidden = [f for f in facts if f.id not in view.fact_ids]
    creator_only = creator_only_fact_ids(db, [f.id for f in hidden])
    return [
        ("creator_only" if fact.id in creator_only else "not_public", about, text)
        for fact, text in zip(hidden, fact_texts(db, hidden))
    ]


def _withheld_dossier(entity: Entity, world_id: str, view: PublicView, db: Session) -> list[tuple]:
    if entity.id not in view.entity_ids:
        return [("entity_not_public", entity.name, entity.name)]
    facts = _participant_facts(entity.id, world_id, db)
    facts += [fact for fact, _ in _relation_facts(entity.id, world_id, db)]
    lines = _withheld_facts(facts, entity.name, view, db)
    for membership in _current_memberships(world_id, db, entity_id=entity.id):
        faction = db.get(Entity, membership.faction_id)
        if faction is None:
            continue
        if membership.is_secret:
            lines.append(("secret_membership", entity.name, _membership_line(faction.name, membership)))
        elif faction.id not in view.entity_ids:
            lines.append(("faction_not_public", entity.name, _membership_line(faction.name, membership)))
    if entity.type == "faction":
        for membership in _current_memberships(world_id, db, faction_id=entity.id):
            member = db.get(Entity, membership.entity_id)
            if member is None:
                continue
            if membership.is_secret:
                lines.append(("secret_membership", entity.name, _membership_line(member.name, membership)))
            elif member.id not in view.entity_ids:
                lines.append(("entity_not_public", entity.name, _membership_line(member.name, membership)))
    return lines


def _withheld_factions(world_id: str, view: PublicView, db: Session) -> list[tuple]:
    factions = db.exec(
        select(Entity).join(Faction, Faction.id == Entity.id).where(
            Entity.world_id == world_id, Entity.status == "active",
        )
    ).all()
    return [("entity_not_public", e.name, e.name) for e in factions if e.id not in view.entity_ids]


def withheld(
    plan: LorePlan, world_id: str, db: Session, bindings: Optional[dict[str, str]] = None,
) -> list[dict]:
    """`{reason, subject, content}` rows, sorted by subject, reason, content.
    `[]` for an invalid plan or an ambiguous mention."""
    if not validate_plan(plan, db, lookups=_PERSPECTIVE_LOOKUPS).ok:
        return []
    view = public_view(db, world_id)
    resolutions = resolve_public_mentions(plan, world_id, db, view, bindings)
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
        if call.selector == "world_laws":
            continue
        if call.selector == "public_factions":
            lines.update(_withheld_factions(world_id, view, db))
            continue
        spec = _PERSPECTIVE_LOOKUPS[call.selector]
        if call.selector == "public_facts_mentioning":
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
