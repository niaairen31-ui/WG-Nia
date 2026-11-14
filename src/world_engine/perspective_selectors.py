"""The perspective selectors: what a view -- everybody, or one character -- knows about a world (TICKET-0125, BRIEF-0125-D, C-04; TICKET-0127, C-06).

Each selector reads the facts, the texts and the entities of its view, and
never returns a fact or an entity outside it, nor a key naming secrecy
levels or knowers.

A view is everybody's (`public_view`) or one character's
(`perspective_view.character_view`, TICKET-0127).

A sibling of `lore_selectors.py` for the player: the creator selectors
cannot serve a perspective, even filtered afterwards (they carry secrets,
creator-only notes, knowers and intensities). Every selector here takes a
`PerspectiveView` -- for everybody, the world's public facts (a public level
above `unaware`, creator-only notes subtracted), its public entities
(active, `is_public`) and the skills visible at creation.
Read-only: no write, no commit, no model call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Optional

from sqlmodel import Session, select

from .context import read_public_memberships
from .creation_rules import visible_skill_ids
from .encounters import acquaintances
from .facet_reads import creator_only_fact_ids
from .facets import FACETS
from .knowledge_resolve import resolve_public_levels
from .lore_resolve import normalize_surface
from .lore_selectors import SelectorSpec
from .models import (
    BASE_SKILL_DOMAINS, Entity, EventParticipant, Fact, FactionMembership, FactParticipant, Faction, Relation,
    Skill, SkillDefinition, SkillSystem, WorldLaw,
)
from .prose_render import fact_texts, fact_texts_at
from .relation_orientation import MAP_TOPOLOGY_TYPES
from .skill_ranks import world_ladder


PERSPECTIVE_KINDS: tuple[str, ...] = ("public", "character")
PERSPECTIVE_DOORS: tuple[str, ...] = ("creator", "player")


@dataclass(frozen=True)
class Belief:
    text: Optional[str]        # the holder's own wording (knowledge content); None: the fact's text at as_of
    as_of: Optional[datetime]  # Known.as_of
    certainty: Optional[str]   # "rumeur" | "soupçon" | "partiel" | None
    secret: bool               # the holder's knowledge row is is_secret
    incorrect: bool            # the holder's knowledge row is is_incorrect -- never a row key


@dataclass(frozen=True)
class PerspectiveView:
    world_id: str
    fact_ids: frozenset[str]
    entity_ids: frozenset[str]
    skill_ids: frozenset[str]
    kind: str = "public"
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    door: str = "creator"
    member_of: frozenset[str] = frozenset()
    beliefs: Mapping[str, Belief] = field(default_factory=dict, hash=False)


def public_view(db: Session, world_id: str) -> PerspectiveView:
    """The facts whose public level is above `unaware`, minus the creator's
    notes (INV-01), the active entities whose `is_public` is true, and the
    skill definitions visible at creation (`creation_rules.visible_skill_ids`)."""
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
    return PerspectiveView(
        world_id=world_id, fact_ids=frozenset(fact_ids), entity_ids=frozenset(entity_ids),
        skill_ids=visible_skill_ids(db, world_id),
    )


_FACET_ORDER = {name: index for index, name in enumerate(FACETS)}
_MIN_TOKEN_LENGTH = 3


def _label(fact: Fact) -> str:
    spec = FACETS.get(fact.facet) if fact.facet else None
    return spec.label if spec is not None else "Fait"


def view_texts(db: Session, view: PerspectiveView, facts: list) -> list[str]:
    """The text `view` gives each fact, in input order (C-05): the current
    text for everybody; for a character, his own wording when he has one,
    else the fact as it was when he last saw it."""
    if not facts:
        return []
    if view.kind != "character":
        return fact_texts(db, facts)
    beliefs = []
    for fact in facts:
        belief = view.beliefs.get(fact.id)
        if belief is None:
            raise ValueError(f"fact {fact.id!r} is not in the character's view")
        beliefs.append(belief)
    unworded = [(fact, belief.as_of) for fact, belief in zip(facts, beliefs) if belief.text is None]
    rendered = iter(fact_texts_at(db, unworded))
    return [belief.text if belief.text is not None else next(rendered) for belief in beliefs]


def _marks(view: PerspectiveView, fact: Fact) -> dict:
    """The `secret` and `certainty` of a fact row (C-06): a character's
    belief; nothing on a public view."""
    if view.kind != "character":
        return {"secret": False, "certainty": None}
    belief = view.beliefs[fact.id]
    return {"secret": belief.secret, "certainty": belief.certainty}


def _participant_facts(entity_id: str, world_id: str, db: Session) -> list[Fact]:
    """Every free fact of the world with `entity_id` as a participant, and
    every event fact of an event it takes part in (TICKET-0127, F1), in
    registry facet order (unknown last), then age, then id. Unfiltered: the
    dossier keeps the ones of its view, the audit names the rest."""
    facts = list(db.exec(
        select(Fact)
        .join(FactParticipant, FactParticipant.fact_id == Fact.id)
        .where(
            Fact.world_id == world_id,
            FactParticipant.entity_id == entity_id,
            Fact.event_id.is_(None),
        )
    ).all())
    facts += db.exec(
        select(Fact)
        .join(EventParticipant, EventParticipant.event_id == Fact.event_id)
        .where(Fact.world_id == world_id, EventParticipant.entity_id == entity_id)
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


def _membership_shown(member: Entity, faction: Entity, view: PerspectiveView) -> bool:
    """Rule M (C-06): may `view` show a current non-secret membership of
    `member` in `faction`? Both must be in the view, and either both are
    public, or the member is the view's character, or he openly belongs to
    the faction. On a public view: today's rule."""
    if faction.id not in view.entity_ids or member.id not in view.entity_ids:
        return False
    return (
        (member.is_public and faction.is_public)
        or member.id == view.character_id
        or faction.id in view.member_of
    )


def _view_members(faction_id: str, world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
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
    faction = db.get(Entity, faction_id)
    if faction is None:
        return []
    kept = sorted(
        ((m, e) for m, e in rows if _membership_shown(e, faction, view)),
        key=lambda pair: (pair[1].name, pair[1].id),
    )
    return [
        {"section": "members", "member_name": e.name, "role": m.cover_role if m.cover_role is not None else m.role}
        for m, e in kept
    ]


def public_member_ids(faction_id: str, world_id: str, view: PerspectiveView, db: Session) -> tuple[str, ...]:
    # Same WHERE triplet as `_view_members` (INV-03): ids for the approval's
    # encounters (TICKET-0129, F-b); never rendered into a prompt.
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
    kept = sorted((e for _m, e in rows if e.id in view.entity_ids), key=lambda e: (e.name, e.id))
    return tuple(e.id for e in kept)


def _membership_rows(entity_id: str, world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
    """`read_public_memberships` rows whose membership rule M shows. The
    accessor returns names only, so a name shared with a membership of the
    entity that is not shown -- a secret one never is -- is dropped too:
    never shown on a doubt."""
    member = db.get(Entity, entity_id)
    if member is None:
        return []
    names: dict[str, set[bool]] = {}
    for membership in _current_memberships(world_id, db, entity_id=entity_id):
        faction = db.get(Entity, membership.faction_id)
        if faction is not None:
            shown = not membership.is_secret and _membership_shown(member, faction, view)
            names.setdefault(faction.name, set()).add(shown)
    return [
        {"section": "memberships", "faction_name": name, "role": role}
        for name, role in read_public_memberships(entity_id, db)
        if names.get(name) == {True}
    ]


def known_dossier(entity_id: str, world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
    """What the view knows about one entity: identity, its facts and the
    events it took part in (`Événement`), its relations (`Lien`), the
    memberships rule M shows and, for a faction, the members it shows. Empty
    when the entity is not in the view."""
    if entity_id not in view.entity_ids:
        return []
    entity = db.exec(select(Entity).where(Entity.id == entity_id, Entity.world_id == world_id)).first()
    if entity is None:
        return []
    rows: list[dict] = [{"section": "identity", "entity_id": entity.id, "name": entity.name, "type": entity.type}]
    facts = [f for f in _participant_facts(entity_id, world_id, db) if f.id in view.fact_ids]
    rows += [
        {"section": "facets", "label": "Événement" if fact.event_id else _label(fact), "aspect": fact.aspect,
         "content": text, **_marks(view, fact)}
        for fact, text in zip(facts, view_texts(db, view, facts))
    ]
    links = [
        fact for fact, relation in _relation_facts(entity_id, world_id, db)
        if fact.id in view.fact_ids and _other_end(relation, entity_id) in view.entity_ids
    ]
    rows += [
        {"section": "facets", "label": "Lien", "aspect": None, "content": text, **_marks(view, fact)}
        for fact, text in zip(links, view_texts(db, view, links))
    ]
    rows += _membership_rows(entity_id, world_id, view, db)
    if entity.type == "faction":
        rows += _view_members(entity_id, world_id, view, db)
    return rows


def known_factions(world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
    """One row per active faction of the view, its `description` facts of the view joined."""
    pairs = db.exec(
        select(Entity, Faction).join(Faction, Faction.id == Entity.id).where(
            Entity.world_id == world_id,
            Entity.status == "active",
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
            "description": "\n".join(view_texts(db, view, descriptions)) if descriptions else None,
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


def _view_facts_matching(text: str, world_id: str, view: PerspectiveView, db: Session) -> list[tuple[Fact, str]]:
    """The facts of the view whose text in the view (`view_texts`) holds
    every word of three letters or more of `text`, by that text then id."""
    wanted = {t for t in normalize_surface(text).split() if len(t) >= _MIN_TOKEN_LENGTH}
    if not wanted or not view.fact_ids:
        return []
    facts = db.exec(select(Fact).where(Fact.world_id == world_id, Fact.id.in_(view.fact_ids))).all()
    matched = [
        (fact, rendered) for fact, rendered in zip(facts, view_texts(db, view, facts))
        if wanted <= set(normalize_surface(rendered).split())
    ]
    return sorted(matched, key=lambda pair: (pair[1], pair[0].id))


def known_facts_mentioning(text: str, world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
    """The facts of the view holding every word of `text`, each with the
    names of its participants in the view."""
    matched = _view_facts_matching(text, world_id, view, db)
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
        {"section": "public_mentions", "content": rendered, "participants": participants.get(fact.id, []),
         **_marks(view, fact)}
        for fact, rendered in matched
    ]


def world_laws(world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
    """The world's fundamental laws, by position: known to everybody."""
    laws = db.exec(select(WorldLaw).where(WorldLaw.world_id == world_id).order_by(WorldLaw.position)).all()
    return [{"section": "laws", "position": law.position, "text": law.text_} for law in laws]


def known_skills(world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
    """The skills everybody knows: the definitions visible at creation, one row each."""
    definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
    systems = {s.id: s.name for s in db.exec(select(SkillSystem).where(SkillSystem.world_id == world_id)).all()}
    kept = [d for d in definitions if d.id in view.skill_ids]

    def order(d: SkillDefinition) -> tuple:
        system = systems.get(d.system_id)
        return (system is None, system or "", d.name, d.id)

    return [
        {
            "section": "skills",
            "skill_id": d.id,
            "name": d.name,
            "base_domain": d.base_domain,
            "system": systems.get(d.system_id),
            "description": d.description,
            "requires_master": d.requires_master,
        }
        for d in sorted(kept, key=order)
    ]


def self_sheet(world_id: str, view: PerspectiveView, db: Session) -> list[dict]:
    """The view's character himself (E1): the people he has met, in the
    view, by name; then his skills, base domains first, then definitions by
    name, each with its rank's label. Empty on a public view."""
    if view.kind != "character":
        return []
    met = db.exec(
        select(Entity).where(
            Entity.id.in_(acquaintances(db, view.character_id) & set(view.entity_ids)),
            Entity.world_id == world_id,
        )
    ).all()
    rows: list[dict] = [
        {"section": "acquaintances", "name": e.name, "type": e.type}
        for e in sorted(met, key=lambda e: (e.name, e.id))
    ]
    skills = db.exec(select(Skill).where(Skill.character_id == view.character_id)).all()
    definitions = {
        d.id: d for d in db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
    }
    systems = {s.id: s.name for s in db.exec(select(SkillSystem).where(SkillSystem.world_id == world_id)).all()}
    ladder = world_ladder(db, world_id)

    def order(skill: Skill) -> tuple:
        definition = definitions.get(skill.skill_definition_id)
        if definition is None:
            domains = BASE_SKILL_DOMAINS
            domain = domains.index(skill.domain) if skill.domain in domains else len(domains)
            return (0, domain, skill.domain, skill.id)
        return (1, 0, definition.name, skill.id)

    for skill in sorted(skills, key=order):
        definition = definitions.get(skill.skill_definition_id)
        rows.append({
            "section": "own_skills",
            "name": definition.name if definition is not None else skill.domain,
            "base_domain": definition.base_domain if definition is not None else skill.domain,
            "system": systems.get(definition.system_id) if definition is not None else None,
            "rank_label": ladder[skill.rank].label,
        })
    return rows


PERSPECTIVE_SELECTORS: tuple[str, ...] = (
    "known_dossier", "known_factions", "known_facts_mentioning", "world_laws", "known_skills",
)

_PERSPECTIVE_LOOKUPS: dict[str, SelectorSpec] = {
    "known_dossier": SelectorSpec(
        fn=known_dossier, arity=2, row_cap=400, arg_kinds=("entity_id", "world_id"),
        context_sections=("identity",),
    ),
    "known_factions": SelectorSpec(
        fn=known_factions, arity=1, row_cap=200, arg_kinds=("world_id",),
    ),
    "known_facts_mentioning": SelectorSpec(
        fn=known_facts_mentioning, arity=2, row_cap=200, arg_kinds=("text", "world_id"),
    ),
    "world_laws": SelectorSpec(
        fn=world_laws, arity=1, row_cap=100, arg_kinds=("world_id",),
    ),
    "known_skills": SelectorSpec(
        fn=known_skills, arity=1, row_cap=200, arg_kinds=("world_id",),
    ),
}

PERSPECTIVE_DESCRIPTIONS: dict[str, str] = {
    "known_dossier": (
        "known_dossier(entity_id, $world) -- ce que tout le monde sait sur UNE "
        "entite nommee : son nom, ses faits publics, ses liens et appartenances publics."
    ),
    "known_factions": (
        "known_factions($world) -- une ligne par faction connue de tous."
    ),
    "known_facts_mentioning": (
        'known_facts_mentioning("text:<mots>", $world) -- les faits connus de tous '
        "dont le texte contient ces mots (un sujet qui n'est pas une entite nommee)."
    ),
    "world_laws": (
        "world_laws($world) -- les lois fondamentales du monde, connues de tous."
    ),
    "known_skills": (
        "known_skills($world) -- les compétences de ce monde connues de tous : "
        "celles qu'un personnage peut choisir à sa création."
    ),
}

CHARACTER_SELECTORS: tuple[str, ...] = PERSPECTIVE_SELECTORS + ("self_sheet",)

_CHARACTER_LOOKUPS: dict[str, SelectorSpec] = {
    **_PERSPECTIVE_LOOKUPS,
    "self_sheet": SelectorSpec(fn=self_sheet, arity=1, row_cap=200, arg_kinds=("world_id",)),
}

CHARACTER_DESCRIPTIONS: dict[str, str] = {
    "known_dossier": (
        "known_dossier(entity_id, $world) -- ce que ce personnage sait sur UNE entite nommee : "
        "son nom, les faits qu'il connait, ses liens et appartenances connus."
    ),
    "known_factions": (
        "known_factions($world) -- une ligne par faction que ce personnage connait."
    ),
    "known_facts_mentioning": (
        'known_facts_mentioning("text:<mots>", $world) -- les faits que ce personnage connait '
        "dont le texte contient ces mots (un sujet qui n'est pas une entite nommee)."
    ),
    "world_laws": (
        "world_laws($world) -- les lois fondamentales du monde, connues de tous."
    ),
    "known_skills": (
        "known_skills($world) -- les compétences de ce monde que ce personnage connait."
    ),
    "self_sheet": (
        "self_sheet($world) -- ce personnage lui-même : les personnes qu'il a rencontrées et ses "
        "compétences avec leur rang (« qui ai-je rencontré ? », « que sais-je faire ? »)."
    ),
}


def lookups_for(view: PerspectiveView) -> dict[str, SelectorSpec]:
    """The selector table a view answers through: the character's for a character, else the public one."""
    return _CHARACTER_LOOKUPS if view.kind == "character" else _PERSPECTIVE_LOOKUPS


def descriptions_for(view: PerspectiveView) -> dict[str, str]:
    """The planner's descriptions of `lookups_for(view)`, in the same order."""
    return CHARACTER_DESCRIPTIONS if view.kind == "character" else PERSPECTIVE_DESCRIPTIONS
