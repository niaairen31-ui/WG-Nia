"""The one check of a character-creation skill sheet (TICKET-0126, BRIEF-0126-C; INV-67): the player's, the designer's and the one submitted are judged here and nowhere else. Reads only.

`check_creation` reads the world's rules (`creation_rules`) and its rank
labels (`skill_ranks.world_ladder`), prices every line of the start sheet
against the wanted ranks and lists the violations in a fixed order (C-04):
the per-line codes, the master count, the rank caps, the system caps, the
pool. A cost is per step reached; lowering a held skill to Inexpérimenté
gives back the Initié cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from sqlmodel import Session

from .creation_rules import start_sheet, world_creation_rules
from .models import CREATION_CAP_RANKS, SkillSystem
from .skill_ranks import DEFAULT_RANK, world_ladder

VIOLATION_CODES: tuple[str, ...] = (
    "unknown_skill", "rank_out_of_range", "not_visible", "above_max_rank",
    "over_master_count", "over_rank_cap", "over_system_raised", "over_system_held", "over_pool",
)
DRAFT_VIOLATION_CODES: tuple[str, ...] = (
    "name_missing", "backstory_missing", "start_place_missing", "start_place_invalid",
    "too_many_sketches", "master_without_sketch", "sketch_existing_invalid",
    "membership_invalid", "pc_exists",
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
    for key in choices:
        if key not in by_key:
            violations.append(Violation("unknown_skill", key, f"Compétence inconnue : {key}."))
    for key, value in choices.items():
        if not _valid_rank(value):
            name = by_key[key].name if key in by_key else key
            violations.append(Violation("rank_out_of_range", key,
                                        f"« {name} » : le rang doit être entre 0 et 5."))

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
    system_ids = {line.system_id for line in sheet if line.system_id is not None}
    systems = sorted((s for s in (db.get(SkillSystem, i) for i in system_ids) if s is not None),
                     key=lambda s: (s.name, s.id))
    for system in systems:
        members = [line for line in sheet if line.system_id == system.id]
        raised = sum(1 for line in members if ranks[line.skill_key] > DEFAULT_RANK)
        held = sum(1 for line in members if ranks[line.skill_key] >= 1)
        if system.cap_raised_at_creation is not None and raised > system.cap_raised_at_creation:
            violations.append(Violation(
                "over_system_raised", None,
                f"Système « {system.name} » : au plus {system.cap_raised_at_creation} compétence(s) "
                f"au-dessus de {labels[DEFAULT_RANK]}."))
        if system.cap_held_at_creation is not None and held > system.cap_held_at_creation:
            violations.append(Violation(
                "over_system_held", None,
                f"Système « {system.name} » : au plus {system.cap_held_at_creation} compétence(s) détenue(s)."))

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


# check_draft: BRIEF-0126-G (C-04).
