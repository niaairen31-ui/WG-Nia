"""Which skill row a roll reads, for the player and for the NPC opposing him
(TICKET-0107, BRIEF-0107-A, decision D1).

Reads only: this module never writes.

The player's row: the arbiter named a base domain or a skill definition of
the world. A base domain reads the player's base row for it
(`skill_definition_id IS NULL`, CLAUDE.md « Custom skill lookups »). A
definition reads the player's row for it; when the player has none, the
roll falls back to his base row for the definition's domain -- unless the
definition `requires_master` (TICKET-0107, BRIEF-0107-B, A2/B1): then the
skill is LOCKED, no row is rolled, and Play rolls no dice (`LOCKED_BAND`).

The opposing NPC's modifier (D1): its row for the same definition, else its
base row for the roll's base domain, else the rank every character holds in
a base domain by default -- `skill_ranks.DEFAULT_RANK` (Initié, +0): every
character has the four base domains, an NPC just has no row for one it was
never given. The modifier is always `skill_ranks.rank_modifier(rank)`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from .models import BASE_SKILL_DOMAINS, Skill, SkillDefinition
from .resolution import Verdict
from .skill_ranks import DEFAULT_RANK, rank_modifier


# The verdict band of a locked skill: no dice, no point (B1).
LOCKED_BAND = "locked"


@dataclass(frozen=True)
class RolledSkill:
    base_domain: str  # what bands, discovery and the dice key off
    row: Optional[Skill]  # the player's row rolled; None when he has none at all, or locked
    definition: Optional[SkillDefinition]  # set when the arbiter named a definition
    locked: bool = False  # a requires_master definition the player was never taught


def _base_row(db: Session, character_id: str, domain: str) -> Optional[Skill]:
    return db.exec(
        select(Skill).where(
            Skill.character_id == character_id,
            Skill.domain == domain,
            Skill.skill_definition_id.is_(None),
        )
    ).first()


def _definition_row(db: Session, character_id: str, definition_id: str) -> Optional[Skill]:
    return db.exec(
        select(Skill).where(Skill.character_id == character_id, Skill.skill_definition_id == definition_id)
    ).first()


def player_skill(db: Session, player_id: str, token: str, definitions_by_name: dict) -> RolledSkill:
    """The row the player rolls for `token` (a base domain, or a definition
    name of `definitions_by_name`)."""
    definition = definitions_by_name.get(token)
    if definition is None:
        return RolledSkill(base_domain=token, row=_base_row(db, player_id, token), definition=None)
    row = _definition_row(db, player_id, definition.id)
    if row is None and definition.requires_master:
        return RolledSkill(base_domain=definition.base_domain, row=None, definition=definition, locked=True)
    row = row or _base_row(db, player_id, definition.base_domain)
    return RolledSkill(base_domain=definition.base_domain, row=row, definition=definition)


def opposition_modifier(db: Session, npc_id: str, base_domain: str, definition: Optional[SkillDefinition]) -> int:
    """D1: the opposing NPC's modifier for this roll."""
    row = _definition_row(db, npc_id, definition.id) if definition is not None else None
    if row is None:
        row = _base_row(db, npc_id, base_domain)
    return rank_modifier(row.rank if row is not None else DEFAULT_RANK)


def held_rank(db: Session, character_id: str, skill_key: Optional[str]) -> Optional[int]:
    """The rank a character holds in `skill_key` (TICKET-0108, BRIEF-0108-A,
    the `skill_rank_gte` requirement): a base domain reads its base row, else
    `DEFAULT_RANK` (every character has the four base domains, D1); a skill
    definition id reads the character's row for it, else None -- not held."""
    if skill_key in BASE_SKILL_DOMAINS:
        row = _base_row(db, character_id, skill_key)
        return row.rank if row is not None else DEFAULT_RANK
    row = _definition_row(db, character_id, skill_key) if skill_key else None
    return row.rank if row is not None else None


def skill_label(db: Session, skill_key: Optional[str]) -> str:
    """A base domain as is, a skill definition id as its name (TICKET-0108,
    moved here from `day_plan` at TICKET-0109 for a second reader)."""
    if skill_key in BASE_SKILL_DOMAINS:
        return str(skill_key)
    definition = db.get(SkillDefinition, skill_key) if skill_key else None
    return definition.name if definition is not None else str(skill_key)


def locked_verdict(skill_name: str) -> Verdict:
    """The verdict of a locked skill (B1): no dice were rolled. `domain`
    carries the skill's name, for the verdict event and the MJ rubric."""
    return Verdict(domain=skill_name, dice=(0, 0), modifier=0, total=0, band=LOCKED_BAND)


def locked_rubric(skill_name: str) -> str:
    """The MJ's instruction for a locked skill: the attempt cannot be made."""
    return (
        "[COMPÉTENCE NON MAÎTRISÉE]\n"
        f"Le personnage n'a jamais appris « {skill_name} » : personne ne la lui a enseignée.\n"
        "Il ne peut pas tenter cette action. Narre qu'il en est incapable (il hésite, ne sait\n"
        "par où commencer, renonce) ; l'action n'a ni réussite ni échec, et rien ne change autour de lui."
    )
