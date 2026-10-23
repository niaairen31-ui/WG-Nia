"""The public perspective's selectors: what everybody knows about a world (TICKET-0125, BRIEF-0125-D, C-04).

A sibling of `lore_selectors.py` for the player: the creator selectors
cannot serve a perspective, even filtered afterwards (they carry secrets,
creator-only notes, knowers and intensities). Every selector here takes a
`PublicView` -- the world's public facts (a public level above `unaware`,
creator-only notes subtracted) and its public entities (active, `is_public`)
-- and never returns a fact or an entity outside it, nor a key naming
secrecy, levels or knowers. Read-only: no write, no commit, no model call.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from .context import read_public_memberships
from .facet_reads import creator_only_fact_ids
from .facets import FACETS
from .knowledge_resolve import resolve_public_levels
from .lore_resolve import normalize_surface
from .lore_selectors import SelectorSpec
from .models import Entity, Fact, FactionMembership, FactParticipant, Faction, Relation, WorldLaw
from .prose_render import fact_texts
from .relation_orientation import MAP_TOPOLOGY_TYPES


@dataclass(frozen=True)
class PublicView:
    world_id: str
    fact_ids: frozenset[str]
    entity_ids: frozenset[str]


def public_view(db: Session, world_id: str) -> PublicView:
    """The facts whose public level is above `unaware`, minus the creator's
    notes (INV-01), and the active entities whose `is_public` is true."""
    levels = resolve_public_levels(db, world_id)
    fact_ids = {fact_id for fact_id, level in levels.items() if level != "unaware"}
    fact_ids -= creator_only_fact_ids(db, fact_ids)
    entity_ids = db.exec(
        select(Entity.id).where(
            Entity.world_id == world_id,
            Entity.status == "active",
            Entity.is_public == True,  # noqa: E712
        )
    ).all()
    return PublicView(world_id=world_id, fact_ids=frozenset(fact_ids), entity_ids=frozenset(entity_ids))


_FACET_ORDER = {name: index for index, name in enumerate(FACETS)}
_MIN_TOKEN_LENGTH = 3


def _label(fact: Fact) -> str:
    spec = FACETS.get(fact.facet) if fact.facet else None
    return spec.label if spec is not None else "Fait"


def _participant_facts(entity_id: str, world_id: str, db: Session) -> list[Fact]:
    """Every free fact of the world with `entity_id` as a participant, event
    facts aside, in registry facet order (unknown last), then age, then id.
    Unfiltered: the dossier keeps the public ones, the audit names the rest."""
    facts = db.exec(
        select(Fact)
        .join(FactParticipant, FactParticipant.fact_id == Fact.id)
        .where(
            Fact.world_id == world_id,
            FactParticipant.entity_id == entity_id,
            Fact.event_id.is_(None),
        )
    ).all()
    unique = list({fact.id: fact for fact in facts}.values())
    return sorted(unique, key=lambda f: (_FACET_ORDER.get(f.facet, len(_FACET_ORDER)), f.created_at, f.id))


def _relation_facts(entity_id: str, world_id: str, db: Session) -> list[tuple[Fact, Relation]]:
    """The `lien` facts of the entity's relations, map topology excluded
    (INV-06), each with its relation. Unfiltered, as `_participant_facts`."""
    pairs = db.exec(
        select(Fact, Relation)
        .join(Relation, Fact.relation_id == Relation.id)
        .where(
            Relation.world_id == world_id,
            (Relation.entity_a_id == entity_id) | (Relation.entity_b_id == entity_id),
            Relation.type.not_in(MAP_TOPOLOGY_TYPES),
        )
    ).all()
    return sorted(pairs, key=lambda pair: (pair[0].created_at, pair[0].id))


def _other_end(relation: Relation, entity_id: str) -> str:
    return relation.entity_b_id if relation.entity_a_id == entity_id else relation.entity_a_id


def _current_memberships(world_id: str, db: Session, *, entity_id=None, faction_id=None) -> list[FactionMembership]:
    """Every current membership of a member or of a faction, secret ones
    included -- read by the audit only, never rendered into a prompt."""
    query = select(FactionMembership).where(
        FactionMembership.world_id == world_id, FactionMembership.left_at.is_(None),
    )
    if entity_id is not None:
        query = query.where(FactionMembership.entity_id == entity_id)
    if faction_id is not None:
        query = query.where(FactionMembership.faction_id == faction_id)
    return list(db.exec(query).all())


def _public_members(faction_id: str, world_id: str, view: PublicView, db: Session) -> list[dict]:
    # Third sanctioned reader of `faction_membership` for a model prompt
    # (INV-03, INV-66): the same WHERE triplet as `read_public_memberships`,
    # keyed by faction.
    rows = db.exec(
        select(FactionMembership, Entity)
        .join(Entity, Entity.id == FactionMembership.entity_id)
        .where(
            Entity.world_id == world_id,
            FactionMembership.faction_id == faction_id,
            FactionMembership.left_at.is_(None),
            FactionMembership.is_secret == False,  # noqa: E712
        )
    ).all()
    kept = sorted(
        ((m, e) for m, e in rows if e.id in view.entity_ids), key=lambda pair: (pair[1].name, pair[1].id),
    )
    return [
        {"section": "members", "member_name": e.name, "role": m.cover_role if m.cover_role is not None else m.role}
        for m, e in kept
    ]


def _public_membership_rows(entity_id: str, world_id: str, view: PublicView, db: Session) -> list[dict]:
    """`read_public_memberships` rows whose faction is public. The accessor
    returns names only, so a name shared with a non-public faction of the
    entity's memberships is dropped too: never shown on a doubt."""
    names: dict[str, set[bool]] = {}
    for membership in _current_memberships(world_id, db, entity_id=entity_id):
        faction = db.get(Entity, membership.faction_id)
        if faction is not None:
            names.setdefault(faction.name, set()).add(faction.id in view.entity_ids)
    return [
        {"section": "memberships", "faction_name": name, "role": role}
        for name, role in read_public_memberships(entity_id, db)
        if names.get(name) == {True}
    ]


def public_dossier(entity_id: str, world_id: str, view: PublicView, db: Session) -> list[dict]:
    """What everybody knows about one public entity: identity, public facts,
    public relations (`Lien`), memberships in public factions and, for a
    faction, its public members. Empty when the entity is not public."""
    if entity_id not in view.entity_ids:
        return []
    entity = db.exec(select(Entity).where(Entity.id == entity_id, Entity.world_id == world_id)).first()
    if entity is None:
        return []
    rows: list[dict] = [{"section": "identity", "entity_id": entity.id, "name": entity.name, "type": entity.type}]
    facts = [f for f in _participant_facts(entity_id, world_id, db) if f.id in view.fact_ids]
    rows += [
        {"section": "facets", "label": _label(fact), "aspect": fact.aspect, "content": text, "secret": False}
        for fact, text in zip(facts, fact_texts(db, facts))
    ]
    links = [
        fact for fact, relation in _relation_facts(entity_id, world_id, db)
        if fact.id in view.fact_ids and _other_end(relation, entity_id) in view.entity_ids
    ]
    rows += [
        {"section": "facets", "label": "Lien", "aspect": None, "content": text, "secret": False}
        for text in fact_texts(db, links)
    ]
    rows += _public_membership_rows(entity_id, world_id, view, db)
    if entity.type == "faction":
        rows += _public_members(entity_id, world_id, view, db)
    return rows


def public_factions(world_id: str, view: PublicView, db: Session) -> list[dict]:
    """One row per public active faction, its public `description` facts joined."""
    pairs = db.exec(
        select(Entity, Faction).join(Faction, Faction.id == Entity.id).where(
            Entity.world_id == world_id,
            Entity.status == "active",
            Entity.is_public == True,  # noqa: E712
        )
    ).all()
    rows = []
    for entity, faction in sorted(pairs, key=lambda pair: (pair[0].name, pair[0].id)):
        if entity.id not in view.entity_ids:
            continue
        descriptions = [
            f for f in _participant_facts(entity.id, world_id, db)
            if f.facet == "description" and f.id in view.fact_ids
        ]
        rows.append({
            "section": "factions",
            "entity_id": entity.id,
            "name": entity.name,
            "faction_type": faction.faction_type,
            "description": "\n".join(fact_texts(db, descriptions)) if descriptions else None,
        })
    return rows


def _facts_matching(text: str, world_id: str, db: Session) -> list[tuple[Fact, str]]:
    """Facts of the world whose rendered text holds every word of three
    letters or more of `text` (as `lore_selectors.facts_mentioning`), by
    text then id. Unfiltered, as `_participant_facts`."""
    wanted = {t for t in normalize_surface(text).split() if len(t) >= _MIN_TOKEN_LENGTH}
    if not wanted:
        return []
    facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
    matched = [
        (fact, rendered) for fact, rendered in zip(facts, fact_texts(db, facts))
        if wanted <= set(normalize_surface(rendered).split())
    ]
    return sorted(matched, key=lambda pair: (pair[1], pair[0].id))


def public_facts_mentioning(text: str, world_id: str, view: PublicView, db: Session) -> list[dict]:
    """The public facts holding every word of `text`, each with its public
    participants' names."""
    matched = [(fact, rendered) for fact, rendered in _facts_matching(text, world_id, db) if fact.id in view.fact_ids]
    participants: dict[str, list[str]] = {}
    if matched:
        for fact_id, entity_id, name in db.exec(
            select(FactParticipant.fact_id, Entity.id, Entity.name)
            .join(Entity, Entity.id == FactParticipant.entity_id)
            .where(Entity.world_id == world_id, FactParticipant.fact_id.in_([f.id for f, _ in matched]))
            .order_by(FactParticipant.position, Entity.name)
        ).all():
            if entity_id in view.entity_ids:
                participants.setdefault(fact_id, []).append(name)
    return [
        {"section": "public_mentions", "content": rendered, "participants": participants.get(fact.id, [])}
        for fact, rendered in matched
    ]


def world_laws(world_id: str, view: PublicView, db: Session) -> list[dict]:
    """The world's fundamental laws, by position: known to everybody."""
    laws = db.exec(select(WorldLaw).where(WorldLaw.world_id == world_id).order_by(WorldLaw.position)).all()
    return [{"section": "laws", "position": law.position, "text": law.text_} for law in laws]


PERSPECTIVE_SELECTORS: tuple[str, ...] = (
    "public_dossier", "public_factions", "public_facts_mentioning", "world_laws",
)

_PERSPECTIVE_LOOKUPS: dict[str, SelectorSpec] = {
    "public_dossier": SelectorSpec(
        fn=public_dossier, arity=2, row_cap=400, arg_kinds=("entity_id", "world_id"),
        context_sections=("identity",),
    ),
    "public_factions": SelectorSpec(
        fn=public_factions, arity=1, row_cap=200, arg_kinds=("world_id",),
    ),
    "public_facts_mentioning": SelectorSpec(
        fn=public_facts_mentioning, arity=2, row_cap=200, arg_kinds=("text", "world_id"),
    ),
    "world_laws": SelectorSpec(
        fn=world_laws, arity=1, row_cap=100, arg_kinds=("world_id",),
    ),
}

PERSPECTIVE_DESCRIPTIONS: dict[str, str] = {
    "public_dossier": (
        "public_dossier(entity_id, $world) -- ce que tout le monde sait sur UNE "
        "entite nommee : son nom, ses faits publics, ses liens et appartenances publics."
    ),
    "public_factions": (
        "public_factions($world) -- une ligne par faction connue de tous."
    ),
    "public_facts_mentioning": (
        'public_facts_mentioning("text:<mots>", $world) -- les faits connus de tous '
        "dont le texte contient ces mots (un sujet qui n'est pas une entite nommee)."
    ),
    "world_laws": (
        "world_laws($world) -- les lois fondamentales du monde, connues de tous."
    ),
}
