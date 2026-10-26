"""The one check of a character-creation skill sheet (TICKET-0126, BRIEF-0126-C; INV-67): the player's, the designer's and the one submitted are judged here and nowhere else. Reads only.

`check_creation` reads the world's rules (`creation_rules`) and its rank
labels (`skill_ranks.world_ladder`), prices every line of the start sheet
against the wanted ranks and lists the violations in a fixed order (C-04):
the per-line codes, the master count, the rank caps, the system caps, the
pool. A cost is per step reached; lowering a held skill to Inexpérimenté
gives back the Initié cost.

`check_draft` judges a whole draft before its submission (BRIEF-0126-G):
the sheet through `check_creation`, then what only a draft carries -- a
name, a story, a public starting place that is not a zone, a master for
every skill that requires one, people and factions everybody knows, and
no character of the player already in the world.

`check_review` judges the creator's final version (TICKET-0129,
BRIEF-0129-C): the player's sheet and story, the creator's place, people,
masters, relations and memberships, with all the lore -- never through the
public view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from sqlmodel import Session, select

from .creation_rules import start_sheet, world_creation_rules
from .models import (
    BASE_SKILL_DOMAINS, CREATION_CAP_RANKS, PC_SKETCH_MAX, Character, Entity, PcDraft, PcDraftMembership,
    PcDraftSketch, PcDraftSkill, SkillSystem,
)
from .perspective_selectors import public_view
from .relation_orientation import RETIRED_RELATION_TYPES, is_social
from .skill_access import skill_masters
from .skill_ranks import DEFAULT_RANK, world_ladder
from .zone_rules import zone_ids

VIOLATION_CODES: tuple[str, ...] = (
    "unknown_skill", "rank_out_of_range", "not_visible", "above_max_rank",
    "over_master_count", "over_rank_cap", "over_system_raised", "over_system_held", "over_pool",
)
DRAFT_VIOLATION_CODES: tuple[str, ...] = (
    "name_missing", "story_missing", "start_place_missing", "start_place_invalid",
    "too_many_sketches", "master_without_sketch", "sketch_existing_invalid",
    "membership_invalid", "pc_exists",
)
REVIEW_VIOLATION_CODES: tuple[str, ...] = (
    "review_place_invalid", "sketch_undecided", "attach_invalid",
    "attach_duplicate", "master_not_master", "relation_type_invalid",
    "world_has_pc",
)


@dataclass(frozen=True)
class Violation:
    code: str
    skill_key: Optional[str]
    message: str


@dataclass(frozen=True)
class SheetLine:
    skill_key: str
    start_rank: int
    rank: int
    cost: int          # positive spent, negative given back, 0 unchanged


@dataclass(frozen=True)
class CreationVerdict:
    pool: int
    spent: int         # sum of every line's cost (refunds subtract)
    remaining: int     # pool - spent
    lines: tuple[SheetLine, ...]   # every start_sheet line, in its order
    violations: tuple[Violation, ...]


def _valid_rank(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 5


def _cost(costs: tuple[int, ...], start_rank: int, rank: int) -> int:
    if rank > start_rank:
        return sum(costs[r] for r in range(start_rank + 1, rank + 1))
    if rank < start_rank:
        return -costs[1]
    return 0


def _choice_violations(choices: Mapping[str, Any], by_key: Mapping[str, Any]) -> list[Violation]:
    """Step 1: every key not on the sheet, then every rank not an int in 0..5."""
    found = [Violation("unknown_skill", key, f"Compétence inconnue : {key}.")
             for key in choices if key not in by_key]
    for key, value in choices.items():
        if not _valid_rank(value):
            name = by_key[key].name if key in by_key else key
            found.append(Violation("rank_out_of_range", key, f"« {name} » : le rang doit être entre 0 et 5."))
    return found


def _system_violations(db: Session, sheet: tuple, ranks: Mapping[str, int], labels: list[str]) -> list[Violation]:
    """Step 6: each system of the sheet, by name -- its raised, then its held skills."""
    found: list[Violation] = []
    system_ids = {line.system_id for line in sheet if line.system_id is not None}
    systems = sorted((s for s in (db.get(SkillSystem, i) for i in system_ids) if s is not None),
                     key=lambda s: (s.name, s.id))
    for system in systems:
        members = [line for line in sheet if line.system_id == system.id]
        raised = sum(1 for line in members if ranks[line.skill_key] > DEFAULT_RANK)
        held = sum(1 for line in members if ranks[line.skill_key] >= 1)
        if system.cap_raised_at_creation is not None and raised > system.cap_raised_at_creation:
            found.append(Violation(
                "over_system_raised", None,
                f"Système « {system.name} » : au plus {system.cap_raised_at_creation} compétence(s) "
                f"au-dessus de {labels[DEFAULT_RANK]}."))
        if system.cap_held_at_creation is not None and held > system.cap_held_at_creation:
            found.append(Violation(
                "over_system_held", None,
                f"Système « {system.name} » : au plus {system.cap_held_at_creation} compétence(s) détenue(s)."))
    return found


def check_creation(db: Session, world_id: str, choices: Mapping[str, Any], *,
                   enforce_visibility: bool) -> CreationVerdict:
    """Judge a sheet: `choices` maps a skill key to a wanted rank; an absent
    key keeps its start rank. Reads only."""
    rules = world_creation_rules(db, world_id)
    sheet = start_sheet(db, world_id, rules)
    labels = [step.label for step in world_ladder(db, world_id)]
    by_key = {line.skill_key: line for line in sheet}
    violations: list[Violation] = []

    # 1. Unknown keys, then ranks out of range (those keep their start rank).
    violations.extend(_choice_violations(choices, by_key))

    # 2. Each line's rank and cost.
    ranks = {
        line.skill_key: (choices[line.skill_key]
                         if line.skill_key in choices and _valid_rank(choices[line.skill_key])
                         else line.start_rank)
        for line in sheet
    }
    lines = tuple(
        SheetLine(skill_key=line.skill_key, start_rank=line.start_rank, rank=ranks[line.skill_key],
                  cost=_cost(rules.costs, line.start_rank, ranks[line.skill_key]))
        for line in sheet
    )

    # 3. Per changed line: visibility, else the maximum rank.
    for line in sheet:
        rank = ranks[line.skill_key]
        if rank == line.start_rank:
            continue
        if enforce_visibility and not line.visible:
            violations.append(Violation("not_visible", line.skill_key,
                                        f"« {line.name} » ne peut pas être choisie à la création."))
        elif rank > line.max_rank:
            violations.append(Violation("above_max_rank", line.skill_key,
                                        f"« {line.name} » : au plus {labels[line.max_rank]} à la création."))

    # 4. Skills that require a master.
    masters = sum(1 for line in sheet if line.requires_master and ranks[line.skill_key] >= 1)
    if masters > rules.max_master_skills:
        violations.append(Violation("over_master_count", None,
                                    f"Au plus {rules.max_master_skills} compétence(s) qui exigent un maître."))

    # 5. The caps per rank.
    for rank in CREATION_CAP_RANKS:
        cap = rules.cap(rank)
        if cap is None:
            continue
        count = sum(1 for line in sheet
                    if ranks[line.skill_key] == rank and not (rank == 0 and line.requires_master))
        if count > cap:
            violations.append(Violation("over_rank_cap", None,
                                        f"Au plus {cap} compétence(s) au rang {labels[rank]}."))

    # 6. The caps per system, by system name.
    violations.extend(_system_violations(db, sheet, ranks, labels))

    # 7. The pool.
    spent = sum(line.cost for line in lines)
    if spent > rules.pool:
        violations.append(Violation("over_pool", None, f"Réserve dépassée : {spent} point(s) pour {rules.pool}."))

    return CreationVerdict(pool=rules.pool, spent=spent, remaining=rules.pool - spent,
                           lines=lines, violations=tuple(violations))


def verdict_dict(verdict: CreationVerdict, violations: tuple[Violation, ...]) -> dict:
    """The verdict as the routes return it, with `violations` the tuple passed in."""
    return {
        "pool": verdict.pool,
        "spent": verdict.spent,
        "remaining": verdict.remaining,
        "lines": [{"skill_key": line.skill_key, "start_rank": line.start_rank, "rank": line.rank,
                   "cost": line.cost} for line in verdict.lines],
        "violations": [{"code": v.code, "skill_key": v.skill_key, "message": v.message}
                       for v in violations],
    }


def _public_of_type(db: Session, entity_id: Optional[str], world_id: str, entity_type: str,
                    public_ids: frozenset[str]) -> bool:
    """True when `entity_id` is an active entity of `world_id`, of `entity_type`, in the public view."""
    if entity_id is None or entity_id not in public_ids:
        return False
    entity = db.get(Entity, entity_id)
    return (entity is not None and entity.world_id == world_id and entity.type == entity_type
            and entity.status == "active")


def check_draft(db: Session, draft: PcDraft) -> tuple[Violation, ...]:
    """Every reason `draft` cannot be submitted, in C-04's order: its name,
    story and starting place, its sheet (`check_creation`, visibility
    enforced), its people, factions, and the user's existing character.
    Reads only; the world is read through its public view (INV-66)."""
    world_id = draft.world_id
    view = public_view(db, world_id)
    found: list[Violation] = []
    if not draft.name.strip():
        found.append(Violation("name_missing", None, "Le personnage n'a pas de nom."))
    if not draft.story.strip():
        found.append(Violation("story_missing", None, "L'histoire du personnage est vide."))
    if draft.start_location_id is None:
        found.append(Violation("start_place_missing", None, "Choisis un lieu de départ."))
    elif (not _public_of_type(db, draft.start_location_id, world_id, "location", view.entity_ids)
          or draft.start_location_id in zone_ids(db, world_id)):
        found.append(Violation("start_place_invalid", None, "Ce lieu de départ ne peut pas être choisi."))

    skills = db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all()
    choices = {row.skill_key: row.player_rank for row in skills if row.player_rank is not None}
    verdict = check_creation(db, world_id, choices, enforce_visibility=True)
    found.extend(verdict.violations)

    sketches = db.exec(
        select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)
        .order_by(PcDraftSketch.position, PcDraftSketch.id)
    ).all()
    if len(sketches) > PC_SKETCH_MAX:
        found.append(Violation("too_many_sketches", None, f"Au plus {PC_SKETCH_MAX} personnes d'ancrage."))
    taught = {s.skill_key for s in sketches if s.kind == "master"}
    names = {line.skill_key: line for line in start_sheet(db, world_id)}
    for line in verdict.lines:
        start = names.get(line.skill_key)
        if start is not None and start.requires_master and line.rank >= 1 and line.skill_key not in taught:
            found.append(Violation(
                "master_without_sketch", line.skill_key,
                f"« {start.name} » exige un maître : ajoute la personne qui te l'a enseignée."))
    for sketch in sketches:
        if sketch.existing_entity_id is not None and not _public_of_type(
                db, sketch.existing_entity_id, world_id, "character", view.entity_ids):
            found.append(Violation("sketch_existing_invalid", None,
                                   f"« {sketch.name} » : la personne choisie n'est pas connue de tous."))

    memberships = db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id)).all()
    for membership in memberships:
        if not _public_of_type(db, membership.faction_id, world_id, "faction", view.entity_ids):
            found.append(Violation("membership_invalid", None, "Cette faction ne peut pas être choisie."))

    pc = db.exec(select(Character.id).where(
        Character.world_id == world_id, Character.user_id == draft.user_id,
        Character.character_type == "player",
    )).first()
    if pc is not None:
        found.append(Violation("pc_exists", None, "Ce joueur a déjà un personnage dans ce monde."))
    return tuple(found)


def review_place_id(draft: PcDraft) -> Optional[str]:
    """The character's starting place: the creator's when she set one, else the player's."""
    return draft.review_location_id if draft.review_location_id is not None else draft.start_location_id


def _active_of_type(db: Session, entity_id: Optional[str], world_id: str, entity_type: str) -> Optional[Entity]:
    """The active entity `entity_id` of `world_id` and `entity_type`, public or not, else None."""
    entity = db.get(Entity, entity_id) if entity_id is not None else None
    if entity is None or entity.world_id != world_id or entity.type != entity_type or entity.status != "active":
        return None
    return entity


def _master_ids(db: Session, world_id: str, skill_key: Optional[str]) -> set[str]:
    """The ids of the world's Maîtres in `skill_key` (a base domain, else a definition id)."""
    if skill_key in BASE_SKILL_DOMAINS:
        masters = skill_masters(db, world_id, definition_id=None, domain=skill_key)
    else:
        masters = skill_masters(db, world_id, definition_id=skill_key, domain=None)
    return {m["id"] for m in masters}


def _review_sketch_violations(db: Session, world_id: str, sketches: list[PcDraftSketch],
                              names: Mapping[str, Any]) -> list[Violation]:
    """Step 6: each sketch's decision, its attached character, its master, its relation type."""
    found: list[Violation] = []
    attached: set[str] = set()
    for sketch in sketches:
        if sketch.review_action is None:
            found.append(Violation("sketch_undecided", None,
                                   f"« {sketch.name} » : choisis de créer cette personne, de la rattacher "
                                   f"ou de l'écarter."))
            continue
        if sketch.review_action == "attach":
            entity = _active_of_type(db, sketch.review_entity_id, world_id, "character")
            character = db.get(Character, entity.id) if entity is not None else None
            if character is None or character.character_type == "player":
                found.append(Violation("attach_invalid", None,
                                       f"« {sketch.name} » : le personnage choisi n'existe pas dans ce monde."))
            elif entity.id in attached:
                found.append(Violation("attach_duplicate", None,
                                       f"« {sketch.name} » : ce personnage est déjà choisi pour une autre "
                                       f"personne."))
            elif sketch.kind == "master" and entity.id not in _master_ids(db, world_id, sketch.skill_key):
                start = names.get(sketch.skill_key)
                skill = start.name if start is not None else sketch.skill_key
                found.append(Violation("master_not_master", sketch.skill_key,
                                       f"« {sketch.name} » n'est pas Maître en « {skill} »."))
            if entity is not None:
                attached.add(entity.id)
        if sketch.review_action in ("create", "attach"):
            relation_type = (sketch.review_relation_type or "").strip()
            if not relation_type or not is_social(relation_type) or relation_type in RETIRED_RELATION_TYPES:
                found.append(Violation("relation_type_invalid", None,
                                       f"« {sketch.name} » : le lien « {relation_type} » ne peut pas être "
                                       f"choisi."))
    return found


def check_review(db: Session, draft: PcDraft) -> tuple[Violation, ...]:
    """Every reason the creator's final version of `draft` cannot be
    approved, in C-05's order. Reads only, with all the lore -- never
    through the public view; the sheet is judged by `check_creation`."""
    world_id = draft.world_id
    found: list[Violation] = []
    if not draft.name.strip():
        found.append(Violation("name_missing", None, "Le personnage n'a pas de nom."))
    if not draft.story.strip():
        found.append(Violation("story_missing", None, "L'histoire du personnage est vide."))
    place_id = review_place_id(draft)
    if place_id is None:
        found.append(Violation("start_place_missing", None, "Choisis un lieu de départ."))
    elif (_active_of_type(db, place_id, world_id, "location") is None
          or place_id in zone_ids(db, world_id)):
        found.append(Violation("review_place_invalid", None, "Ce lieu de départ ne peut pas être choisi."))

    skills = db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all()
    choices = {row.skill_key: row.player_rank for row in skills if row.player_rank is not None}
    verdict = check_creation(db, world_id, choices, enforce_visibility=True)
    found.extend(verdict.violations)

    sketches = list(db.exec(
        select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)
        .order_by(PcDraftSketch.position, PcDraftSketch.id)
    ).all())
    if len(sketches) > PC_SKETCH_MAX:
        found.append(Violation("too_many_sketches", None, f"Au plus {PC_SKETCH_MAX} personnes d'ancrage."))
    taught = {s.skill_key for s in sketches if s.kind == "master" and s.review_action != "drop"}
    names = {line.skill_key: line for line in start_sheet(db, world_id)}
    for line in verdict.lines:
        start = names.get(line.skill_key)
        if start is not None and start.requires_master and line.rank >= 1 and line.skill_key not in taught:
            found.append(Violation(
                "master_without_sketch", line.skill_key,
                f"« {start.name} » exige un maître : ajoute la personne qui te l'a enseignée."))
    found.extend(_review_sketch_violations(db, world_id, sketches, names))

    memberships = db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id)).all()
    for membership in memberships:
        if not membership.review_dropped and _active_of_type(
                db, membership.faction_id, world_id, "faction") is None:
            found.append(Violation("membership_invalid", None, "Cette faction ne peut pas être choisie."))

    pc = db.exec(select(Character.id).where(
        Character.world_id == world_id, Character.user_id == draft.user_id,
        Character.character_type == "player",
    )).first()
    if pc is not None:
        found.append(Violation("pc_exists", None, "Ce joueur a déjà un personnage dans ce monde."))
    any_pc = db.exec(select(Character.id).where(
        Character.world_id == world_id, Character.character_type == "player",
    )).first()
    if any_pc is not None:
        found.append(Violation("world_has_pc", None, "Ce monde a déjà un personnage joueur : l'approbation "
                                                     "attend le sélecteur « PJ actif »."))
    return tuple(found)
