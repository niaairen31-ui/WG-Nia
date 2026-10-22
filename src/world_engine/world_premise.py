"""The world premise -- what every generator is told about the world it writes
for, in the regime its usage declares (TICKET-0124, BRIEF-0124-B; decisions
A2, B2, C1, D2).

A prompt text carries the premise through one placeholder, `{world_premise}`;
`fill` replaces it with the block `world_premise` builds for the active world,
in the regime `PromptSpec.premise` declares for the usage:

- `creator` -- the world's name, description, tone and laws, its skill
  systems, and, when an entity type is given, the states that type carries.
- `player` -- the name, description, tone and laws only (D2: the laws are
  public). It never carries a skill system or a state.
- `none` -- nothing: the usage writes no fiction, or is framed elsewhere.

`missing_premise` tells whether a text holds the placeholder its regime asks.
This module only reads: it writes, flushes and commits nothing.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .attributes import BUILTIN_TYPE_LABELS_FR, applies_to, world_attributes
from .models import SkillSystem, World, WorldLaw
from .prompt_registry import PROMPT_REGISTRY

PLACEHOLDER = "{world_premise}"
VARIABLE = "world_premise"
PREMISE_REGIMES: tuple[str, ...] = ("creator", "player", "none")

_HEADER = "=== CADRE DU MONDE ==="
_FOOTER = "=== FIN DU CADRE ==="


def regime_of(usage: str) -> str:
    """The usage's declared regime; `none` for a usage the registry does not hold."""
    spec = PROMPT_REGISTRY.get(usage)
    return spec.premise if spec is not None else "none"


def _type_label(entity_type: str) -> str:
    return BUILTIN_TYPE_LABELS_FR.get(entity_type, entity_type).lower()


def _state_line(view) -> str:
    if view.kind == "choice":
        detail = "un parmi : " + ", ".join(label for _, label in view.choices)
        default = dict(view.choices).get(view.default)
        if default is not None:
            detail += f" ; par défaut {default}"
    elif view.kind == "integer":
        detail = "un entier"
        if view.default is not None:
            detail += f" ; par défaut {view.default}"
    else:
        detail = "une entité : " + ", ".join(_type_label(t) for t in view.value_types)
    line = f"- {view.name} ({detail})"
    return line + " — caché du joueur" if view.hidden else line


def _state_lines(db: Session, world: World, entity_type: str) -> list[str]:
    views = [
        v for v in world_attributes(db, world.id)
        if not v.system and v.status == "active" and applies_to(v, entity_type)
    ]
    if not views:
        return []
    header = (f"États que porte chaque {_type_label(entity_type)} de ce monde"
              " — propose une valeur pour chacun :")
    return [header] + [_state_line(v) for v in views]


def world_premise(db: Session, regime: str, *, entity_type: Optional[str] = None) -> str:
    """The premise block of the active world in `regime`; `""` for `none`, no
    active world, or a world with nothing but its name to say."""
    if regime == "none":
        return ""
    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    if world is None:
        return ""
    body: list[str] = []
    if world.description:
        body.append(world.description)
    if world.tone:
        body.append(f"Ton et style : {world.tone}")
    laws = db.exec(
        select(WorldLaw).where(WorldLaw.world_id == world.id).order_by(WorldLaw.position)
    ).all()
    law_texts = [law.text_ for law in laws if law.text_]
    if law_texts:
        body.append("Lois fondamentales — vraies partout, connues de tous et observables :")
        body.extend(f"- {text}" for text in law_texts)
    if regime == "creator":
        systems = db.exec(
            select(SkillSystem).where(SkillSystem.world_id == world.id).order_by(SkillSystem.name)
        ).all()
        if systems:
            body.append("Systèmes de compétences : " + " ; ".join(s.name for s in systems))
        if entity_type is not None:
            body.extend(_state_lines(db, world, entity_type))
    if not body:
        return ""
    return "\n".join([_HEADER, f"Monde : {world.name}", *body, _FOOTER]) + "\n\n"


def fill(text: str, db: Session, usage: str, *, entity_type: Optional[str] = None) -> str:
    """`text` with every `{world_premise}` replaced by the usage's premise;
    unchanged, and no query run, when it holds none."""
    if PLACEHOLDER not in text:
        return text
    return text.replace(PLACEHOLDER, world_premise(db, regime_of(usage), entity_type=entity_type))


def missing_premise(usage: str, system_prompt: str, user_template: str) -> Optional[str]:
    """The French refusal when the texts disagree with the usage's regime, else None."""
    held = PLACEHOLDER in system_prompt or PLACEHOLDER in user_template
    if regime_of(usage) == "none":
        if held:
            return "Ce prompt ne reçoit pas le cadre du monde : retirez {world_premise}."
        return None
    if not held:
        return "Le cadre du monde {world_premise} est obligatoire pour ce prompt."
    return None


__all__ = [
    "PLACEHOLDER", "PREMISE_REGIMES", "VARIABLE",
    "fill", "missing_premise", "regime_of", "world_premise",
]
