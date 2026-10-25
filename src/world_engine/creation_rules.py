"""The character creation rules of a world and the start sheet a new character holds (TICKET-0126, BRIEF-0126-C; decisions J1', L2, Q, Q-limits, A1, P1).

Reads only: no write, no flush, no commit, no model call. The cascade is
`skill_ranks`' (R-06): the definition, then its system, then the world's
`creation_rules` row, then the engine default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlmodel import Session, select

from .models import (
    BASE_SKILL_DOMAINS,
    CREATION_CAP_RANKS,
    CreationRules,
    SkillDefinition,
    SkillSystem,
)
from .skill_ranks import DEFAULT_RANK

DEFAULT_POOL = 6
DEFAULT_COSTS: tuple[int, ...] = (0, 1, 1, 2, 3, 4)   # index = rank reached; index 0 unused
DEFAULT_CAPS: dict[int, Optional[int]] = {0: 2, 2: None, 3: None, 4: None, 5: None}
DEFAULT_MAX_RANK = 5
DEFAULT_MAX_MASTER_SKILLS = 1
DEFAULT_SKILLS_VISIBLE = True


@dataclass(frozen=True)
class CreationRuleSet:
    pool: int
    costs: tuple[int, ...]               # len 6, costs[0] == 0
    caps: tuple[tuple[int, Optional[int]], ...]   # (rank, cap) for CREATION_CAP_RANKS, in order
    max_rank: int
    max_master_skills: int
    skills_visible: bool

    def cap(self, rank: int) -> Optional[int]:
        """The cap of `rank`; None (no cap) for a rank not in CREATION_CAP_RANKS."""
        return dict(self.caps).get(rank)


@dataclass(frozen=True)
class StartSkill:
    skill_key: str                 # a base domain literal, or a skill definition id
    name: str                      # the domain literal, or the definition's name
    base_domain: str
    system_id: Optional[str]
    system_name: Optional[str]
    description: Optional[str]     # the definition's; None for a base domain
    requires_master: bool
    start_rank: int                # 0 for requires_master, else DEFAULT_RANK
    max_rank: int                  # skill_max_rank
    visible: bool                  # skill_visible


def world_creation_rules(db: Session, world_id: str) -> CreationRuleSet:
    """The world's `creation_rules` row, else every default. Never writes."""
    row = db.exec(select(CreationRules).where(CreationRules.world_id == world_id)).first()
    if row is None:
        return CreationRuleSet(
            pool=DEFAULT_POOL, costs=DEFAULT_COSTS,
            caps=tuple((rank, DEFAULT_CAPS[rank]) for rank in CREATION_CAP_RANKS),
            max_rank=DEFAULT_MAX_RANK, max_master_skills=DEFAULT_MAX_MASTER_SKILLS,
            skills_visible=DEFAULT_SKILLS_VISIBLE,
        )
    return CreationRuleSet(
        pool=row.pool,
        costs=(0, row.cost_to_rank_1, row.cost_to_rank_2, row.cost_to_rank_3,
               row.cost_to_rank_4, row.cost_to_rank_5),
        caps=tuple((rank, getattr(row, f"cap_at_rank_{rank}")) for rank in CREATION_CAP_RANKS),
        max_rank=row.max_rank, max_master_skills=row.max_master_skills,
        skills_visible=bool(row.skills_visible),
    )


def _cascade(column: str, *, system: Any, definition: Any) -> Any:
    """`definition`'s column, else `system`'s; None when neither sets it."""
    for owner in (definition, system):
        value = getattr(owner, column, None) if owner is not None else None
        if value is not None:
            return value
    return None


def skill_visible(rules: CreationRuleSet, *, system: Any, definition: Any) -> bool:
    """Whether a skill may be chosen at creation. A base domain always may."""
    if definition is None:
        return True
    value = _cascade("visible_at_creation", system=system, definition=definition)
    return rules.skills_visible if value is None else bool(value)


def skill_max_rank(rules: CreationRuleSet, *, system: Any, definition: Any) -> int:
    """The highest rank a new character may hold in a skill."""
    if definition is None:
        return rules.max_rank
    value = _cascade("max_rank_at_creation", system=system, definition=definition)
    return rules.max_rank if value is None else value


def _world_skills(db: Session, world_id: str) -> tuple[list[SkillDefinition], dict[str, SkillSystem]]:
    definitions = list(db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all())
    systems = {s.id: s for s in db.exec(select(SkillSystem).where(SkillSystem.world_id == world_id)).all()}
    return definitions, systems


def visible_skill_ids(db: Session, world_id: str) -> frozenset[str]:
    """The ids of the world's skill definitions a player may choose at creation."""
    rules = world_creation_rules(db, world_id)
    definitions, systems = _world_skills(db, world_id)
    return frozenset(
        d.id for d in definitions
        if skill_visible(rules, system=systems.get(d.system_id), definition=d)
    )


def start_sheet(db: Session, world_id: str, rules: Optional[CreationRuleSet] = None) -> tuple[StartSkill, ...]:
    """The four base domains, then every definition of the world by (system
    name, no system last; name; id), each at the rank a new character holds."""
    rules = rules if rules is not None else world_creation_rules(db, world_id)
    lines = [
        StartSkill(skill_key=domain, name=domain, base_domain=domain, system_id=None,
                   system_name=None, description=None, requires_master=False,
                   start_rank=DEFAULT_RANK, max_rank=rules.max_rank, visible=True)
        for domain in BASE_SKILL_DOMAINS
    ]
    definitions, systems = _world_skills(db, world_id)

    def order(d: SkillDefinition) -> tuple:
        system = systems.get(d.system_id)
        return (system is None, system.name if system is not None else "", d.name, d.id)

    for d in sorted(definitions, key=order):
        system = systems.get(d.system_id)
        lines.append(StartSkill(
            skill_key=d.id, name=d.name, base_domain=d.base_domain,
            system_id=system.id if system is not None else None,
            system_name=system.name if system is not None else None,
            description=d.description, requires_master=bool(d.requires_master),
            start_rank=0 if d.requires_master else DEFAULT_RANK,
            max_rank=skill_max_rank(rules, system=system, definition=d),
            visible=skill_visible(rules, system=system, definition=d),
        ))
    return tuple(lines)


def rules_dict(rules: CreationRuleSet) -> dict:
    """The rules as the creator's routes return them (C-06)."""
    return {
        "pool": rules.pool,
        "costs": [{"rank": rank, "cost": rules.costs[rank]} for rank in range(1, 6)],
        "caps": [{"rank": rank, "cap": cap} for rank, cap in rules.caps],
        "max_rank": rules.max_rank,
        "max_master_skills": rules.max_master_skills,
        "skills_visible": rules.skills_visible,
    }
