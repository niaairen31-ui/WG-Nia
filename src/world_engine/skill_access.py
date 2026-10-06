"""Which skill row a roll reads, for the player and for the NPC opposing him
(TICKET-0107, BRIEF-0107-A, decision D1).

Reads only: this module never writes.

The player's row: the arbiter named a base domain or a skill definition of
the world. A base domain reads the player's base row for it
(`skill_definition_id IS NULL`, CLAUDE.md « Custom skill lookups »). A
definition reads the player's row for it; when the player has none, the
roll falls back to his base row for the definition's domain.

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

from .models import Skill, SkillDefinition
from .skill_ranks import DEFAULT_RANK, rank_modifier


@dataclass(frozen=True)
class RolledSkill:
    base_domain: str  # what bands, discovery and the dice key off
    row: Optional[Skill]  # the player's row rolled; None when he has none at all
    definition: Optional[SkillDefinition]  # set when the arbiter named a definition


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
    row = _definition_row(db, player_id, definition.id) or _base_row(db, player_id, definition.base_domain)
    return RolledSkill(base_domain=definition.base_domain, row=row, definition=definition)


def opposition_modifier(db: Session, npc_id: str, base_domain: str, definition: Optional[SkillDefinition]) -> int:
    """D1: the opposing NPC's modifier for this roll."""
    row = _definition_row(db, npc_id, definition.id) if definition is not None else None
    if row is None:
        row = _base_row(db, npc_id, base_domain)
    return rank_modifier(row.rank if row is not None else DEFAULT_RANK)
