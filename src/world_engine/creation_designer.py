"""The player-side character designer (TICKET-0126, BRIEF-0126-F; S1, T1, F'a-1, F-c). Two calls -- the backstory's names and words, then the proposal -- over the public lore only; its skills pass `creation_check.check_creation`, with one retry. Writes nothing: `writes/pc_drafts.apply_design` (BRIEF-0126-G) applies a design. `OllamaError` and `LlmParseError` propagate.

The design call is told the world's listed skills under codes (`s1`,
`s2`, ...: the base domains and the skills visible at creation, in start
sheet order), the player's own choices, the creation rules, and the
creation lore (`creation_lore.gather_creation_lore`). Its reply is
resolved item by item in code (LOT-0126 case table (b)-3): an unknown
code, a place or a faction outside the lists is dropped with a note; a
person it names as existing is kept only when the public scope resolves
the name to one public character. Both prompts are in the `player`
premise regime, filled for the draft's own world (`world_id`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlmodel import Session, select

from . import prompt_call
from .creation_check import Violation, check_creation
from .creation_lore import CreationLore, gather_creation_lore
from .creation_rules import CreationRuleSet, StartSkill, start_sheet, world_creation_rules
from .lore_resolve import normalize_surface, resolve_named
from .models import (
    CREATION_CAP_RANKS, PC_KNOWLEDGE_LEVELS, PC_SKETCH_KINDS, PC_SKETCH_MAX, Entity, PcDraft, PcDraftSketch,
    PcDraftSkill, SkillSystem,
)
from .ollama_client import chat
from .perspective_query import public_scope
from .perspective_selectors import PublicView, public_view
from .skill_ranks import world_ladder

SUBJECT_USAGE = "creation_subject"
DESIGN_USAGE = "creation_design"
MAX_KNOWLEDGE = 10
DESIGNER_UNAVAILABLE_MESSAGE = (
    "Le modèle local (Ollama) est indisponible : le concepteur n'a rien proposé et rien n'a changé. "
    "Réessaie quand Ollama est démarré."
)


@dataclass(frozen=True)
class DesignedSkill:
    skill_key: str
    rank: int
    reason: Optional[str]


@dataclass(frozen=True)
class DesignedSketch:
    name: str
    role: str
    sentence: str
    group_label: str
    kind: str                          # one of PC_SKETCH_KINDS
    skill_key: Optional[str]           # set exactly when kind == "master"
    existing_entity_id: Optional[str]


@dataclass(frozen=True)
class DesignedMembership:
    faction_id: str
    role: Optional[str]


@dataclass(frozen=True)
class DesignedKnowledge:
    level: str                         # one of PC_KNOWLEDGE_LEVELS
    content: str


@dataclass(frozen=True)
class CreationDesign:
    names: tuple[str, ...]
    keywords: tuple[str, ...]
    lore: CreationLore
    skills: tuple[DesignedSkill, ...]
    sketches: tuple[DesignedSketch, ...]
    start_location_id: Optional[str]
    memberships: tuple[DesignedMembership, ...]
    knowledge: tuple[DesignedKnowledge, ...]
    notes: tuple[str, ...]
    violations: tuple[Violation, ...]  # check_creation of `skills`, after the retry


# ── the two calls (the registry's call sites) ─────────────────────────────


def _subject_call(db: Session, draft: PcDraft, exchanges: list) -> dict:
    values = {"character_name": draft.name, "backstory": draft.backstory}
    return prompt_call.call_json(db, SUBJECT_USAGE, values, exchanges, chat, world_id=draft.world_id)


def _design_call(db: Session, draft: PcDraft, values: dict[str, str], exchanges: list) -> dict:
    return prompt_call.call_json(db, DESIGN_USAGE, values, exchanges, chat, world_id=draft.world_id)


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def subject(db: Session, draft: PcDraft, exchanges: list) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The backstory's proper names and distinguishing words."""
    reply = _subject_call(db, draft, exchanges)
    return _strings(reply.get("names")), _strings(reply.get("keywords"))


# ── the design values ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Listing:
    lines: tuple[StartSkill, ...]       # the listed start sheet lines, in order
    codes: dict[str, StartSkill]        # "s1" -> line
    code_of: dict[str, str]             # skill_key -> "s1"


def _listing(db: Session, world_id: str, view: PublicView, rules: CreationRuleSet) -> _Listing:
    sheet = start_sheet(db, world_id, rules)
    # A base domain's key is its domain literal; a definition's is its id (INV-44).
    lines = tuple(line for line in sheet if line.skill_key == line.base_domain or line.skill_key in view.skill_ids)
    codes = {f"s{index}": line for index, line in enumerate(lines, start=1)}
    return _Listing(lines=lines, codes=codes, code_of={line.skill_key: code for code, line in codes.items()})


def _skills_text(listing: _Listing, labels: list[str]) -> str:
    return "\n".join(
        f"{code} -- {line.name} ; {line.system_name or 'sans système'} ; {labels[line.start_rank]} ; "
        f"{labels[line.max_rank]} ; {'exige un maître' if line.requires_master else 'ouverte'}"
        for code, line in listing.codes.items()
    )


def _player_choices_text(db: Session, draft: PcDraft, listing: _Listing, labels: list[str]) -> str:
    rows = {
        row.skill_key: row
        for row in db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all()
        if row.player_rank is not None
    }
    lines = []
    for code, line in listing.codes.items():
        row = rows.get(line.skill_key)
        if row is None:
            continue
        text = f"{code} -- {line.name} : {labels[row.player_rank]}"
        if row.justification:
            text += f" -- {row.justification}"
        lines.append(text)
    return "\n".join(lines) or "(aucune)"


def _rules_text(db: Session, listing: _Listing, rules: CreationRuleSet, labels: list[str]) -> str:
    costs = rules.costs
    lines = [
        f"Réserve : {rules.pool} point(s).",
        "Coût pour atteindre : " + ", ".join(f"{labels[n]} {costs[n]}" for n in range(1, 6)) + ".",
        f"Descendre une compétence détenue à {labels[0]} rend {costs[1]} point(s).",
        f"Au plus {rules.max_master_skills} compétence(s) qui exigent un maître.",
    ]
    for rank in CREATION_CAP_RANKS:
        cap = rules.cap(rank)
        if cap is not None:
            lines.append(f"Au plus {cap} compétence(s) au rang {labels[rank]}.")
    system_ids = {line.system_id for line in listing.lines if line.system_id is not None}
    systems = [db.get(SkillSystem, system_id) for system_id in system_ids]
    for system in sorted((s for s in systems if s is not None), key=lambda s: (s.name, s.id)):
        if system.cap_raised_at_creation is not None:
            lines.append(f"Système « {system.name} » : au plus {system.cap_raised_at_creation} "
                         f"compétence(s) au-dessus de {labels[1]}.")
        if system.cap_held_at_creation is not None:
            lines.append(f"Système « {system.name} » : au plus {system.cap_held_at_creation} "
                         "compétence(s) détenue(s).")
    return "\n".join(lines)


def _names_text(items: tuple[dict, ...], *, with_description: bool = False) -> str:
    lines = []
    for item in items:
        line = f"- {item['name']}"
        if with_description and item.get("description"):
            line += f" : {item['description']}"
        lines.append(line)
    return "\n".join(lines) or "(aucun)"


def _errors_text(violations: tuple[Violation, ...]) -> str:
    if not violations:
        return ""
    return "\nErreurs de ta réponse précédente :" + "".join(f"\n- {v.message}" for v in violations)


# ── resolution (LOT-0126 case table (b)-3) ─────────────────────────────────


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _valid_rank(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 5


def _resolve_skills(items: Any, listing: _Listing, notes: list[str]) -> tuple[DesignedSkill, ...]:
    kept: dict[str, DesignedSkill] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        code = item.get("skill")
        line = listing.codes.get(code) if isinstance(code, str) else None
        if line is None:
            notes.append(f"Compétence inconnue écartée : {code}.")
            continue
        if not _valid_rank(item.get("rank")):
            notes.append(f"Rang invalide écarté pour « {line.name} ».")
            continue
        if line.skill_key not in kept:
            kept[line.skill_key] = DesignedSkill(line.skill_key, item["rank"], _text(item.get("reason")) or None)
    return tuple(kept.values())


def _existing_character(name: str, world_id: str, view: PublicView, db: Session) -> Optional[str]:
    if not name:
        return None
    resolution = resolve_named(name, "person", world_id, db, scope=public_scope(view))
    if resolution.verdict != "matched" or resolution.entity_id not in view.entity_ids:
        return None
    entity = db.get(Entity, resolution.entity_id)
    return entity.id if entity is not None and entity.type == "character" else None


def _resolve_sketches(items: Any, room: int, listing: _Listing, world_id: str, view: PublicView,
                      db: Session, notes: list[str]) -> tuple[DesignedSketch, ...]:
    sketches: list[DesignedSketch] = []
    for item in items if isinstance(items, list) else []:
        name = _text(item.get("name")) if isinstance(item, dict) else ""
        if not name:
            notes.append("Une personne sans nom a été écartée.")
            continue
        kind = item.get("kind") if item.get("kind") in PC_SKETCH_KINDS else "other"
        skill_key = None
        if kind == "master":
            code = item.get("skill")
            line = listing.codes.get(code) if isinstance(code, str) else None
            if line is not None and line.requires_master:
                skill_key = line.skill_key
            else:
                kind = "other"
                notes.append(f"« {name} » : maître sans compétence connue, gardé comme « autre ».")
        sketches.append(DesignedSketch(
            name=name, role=_text(item.get("role")), sentence=_text(item.get("sentence")),
            group_label=_text(item.get("group")), kind=kind, skill_key=skill_key,
            existing_entity_id=_existing_character(_text(item.get("existing")), world_id, view, db),
        ))
    room = max(room, 0)
    if len(sketches) > room:
        notes.append(f"{len(sketches) - room} personne(s) proposée(s) écartée(s) : {PC_SKETCH_MAX} au plus.")
    return tuple(sketches[:room])


def _by_surface(items: tuple[dict, ...]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for item in items:
        found.setdefault(normalize_surface(item["name"]), item)
    return found


def _resolve_start_place(value: Any, lore: CreationLore, notes: list[str]) -> Optional[str]:
    name = _text(value)
    if not name:
        return None
    place = _by_surface(lore.places).get(normalize_surface(name))
    if place is None:
        notes.append(f"Lieu de départ inconnu écarté : {name}.")
        return None
    return place["entity_id"]


def _resolve_memberships(items: Any, lore: CreationLore, notes: list[str]) -> tuple[DesignedMembership, ...]:
    factions = _by_surface(lore.factions)
    kept: dict[str, DesignedMembership] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("faction"))
        faction = factions.get(normalize_surface(name))
        if faction is None:
            notes.append(f"Faction inconnue écartée : {name}.")
            continue
        if faction["entity_id"] not in kept:
            kept[faction["entity_id"]] = DesignedMembership(faction["entity_id"], _text(item.get("role")) or None)
    return tuple(kept.values())


def _resolve_knowledge(items: Any) -> tuple[DesignedKnowledge, ...]:
    kept: list[DesignedKnowledge] = []
    for item in items if isinstance(items, list) else []:
        content = _text(item.get("content")) if isinstance(item, dict) else ""
        if not content:
            continue
        level = item.get("level") if item.get("level") in PC_KNOWLEDGE_LEVELS else "rumor"
        kept.append(DesignedKnowledge(level, content))
    return tuple(kept[:MAX_KNOWLEDGE])


def _resolve(reply: dict, *, listing: _Listing, lore: CreationLore, room: int, world_id: str,
             view: PublicView, db: Session) -> dict:
    notes: list[str] = []
    resolved = {
        "skills": _resolve_skills(reply.get("skills"), listing, notes),
        "sketches": _resolve_sketches(reply.get("sketches"), room, listing, world_id, view, db, notes),
        "start_location_id": _resolve_start_place(reply.get("start_place"), lore, notes),
        "memberships": _resolve_memberships(reply.get("memberships"), lore, notes),
        "knowledge": _resolve_knowledge(reply.get("knowledge")),
    }
    resolved["notes"] = _strings(reply.get("notes")) + tuple(notes)
    return resolved


# ── the design ─────────────────────────────────────────────────────────────


def design(db: Session, draft: PcDraft, names: tuple[str, ...], keywords: tuple[str, ...],
           exchanges: list) -> CreationDesign:
    """The proposal for `draft`, over the public lore of its backstory; one
    retry when its skills break the creation rules."""
    world_id = draft.world_id
    lore = gather_creation_lore(db, world_id, names=list(names), keywords=list(keywords))
    view = public_view(db, world_id)
    rules = world_creation_rules(db, world_id)
    labels = [step.label for step in world_ladder(db, world_id)]
    listing = _listing(db, world_id, view, rules)
    player_sketches = db.exec(
        select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id, PcDraftSketch.origin == "player")
    ).all()
    room = PC_SKETCH_MAX - len(player_sketches)
    values = {
        "character_name": draft.name,
        "backstory": draft.backstory,
        "skills": _skills_text(listing, labels),
        "player_choices": _player_choices_text(db, draft, listing, labels),
        "rules": _rules_text(db, listing, rules, labels),
        "lore": "\n".join(lore.lines) or "(rien)",
        "people": _names_text(lore.people),
        "places": _names_text(lore.places),
        "factions": _names_text(lore.factions, with_description=True),
        "errors": "",
    }

    def attempt(errors: str) -> tuple[dict, tuple[Violation, ...]]:
        reply = _design_call(db, draft, {**values, "errors": errors}, exchanges)
        resolved = _resolve(reply, listing=listing, lore=lore, room=room, world_id=world_id, view=view, db=db)
        verdict = check_creation(db, world_id, {s.skill_key: s.rank for s in resolved["skills"]},
                                 enforce_visibility=True)
        return resolved, verdict.violations

    resolved, violations = attempt("")
    if violations:
        resolved, violations = attempt(_errors_text(violations))
    return CreationDesign(
        names=names, keywords=keywords, lore=lore, skills=resolved["skills"], sketches=resolved["sketches"],
        start_location_id=resolved["start_location_id"], memberships=resolved["memberships"],
        knowledge=resolved["knowledge"], notes=resolved["notes"], violations=violations,
    )


def design_record(design: CreationDesign) -> dict:
    """The design as the journal's `proposal`."""
    return {
        "skills": [{"skill_key": s.skill_key, "rank": s.rank, "reason": s.reason} for s in design.skills],
        "sketches": [
            {"name": s.name, "role": s.role, "sentence": s.sentence, "group_label": s.group_label,
             "kind": s.kind, "skill_key": s.skill_key, "existing_entity_id": s.existing_entity_id}
            for s in design.sketches
        ],
        "start_location_id": design.start_location_id,
        "memberships": [{"faction_id": m.faction_id, "role": m.role} for m in design.memberships],
        "knowledge": [{"level": k.level, "content": k.content} for k in design.knowledge],
    }
