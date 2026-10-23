"""What a character designer may read: what everybody knows of a backstory's names and words, the places a character can start in, the public factions (TICKET-0126, BRIEF-0126-F; F-c, D1, INV-66). Built only on the public view. Reads only.

Every name of the backstory resolves under the public name scope
(`perspective_query.public_scope`), so a non-public entity is no surface
at all; a matched entity's lines come from `public_dossier`, a keyword's
from `public_facts_mentioning`. A starting place is a public active
location that is not a zone (`zone_rules.zone_ids`). No write, no flush,
no commit, no model call.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from .lore_resolve import CATEGORIES, normalize_surface, resolve_named
from .models import Entity
from .perspective_query import public_scope
from .perspective_selectors import PublicView, public_dossier, public_factions, public_facts_mentioning, public_view
from .zone_rules import zone_ids

MAX_NAMES = 10
MAX_KEYWORDS = 6
MAX_LORE_LINES = 80
MAX_LISTED = 60


@dataclass(frozen=True)
class CreationLore:
    lines: tuple[str, ...]
    people: tuple[dict, ...]     # {"entity_id", "name"}
    places: tuple[dict, ...]     # {"entity_id", "name"}
    factions: tuple[dict, ...]   # {"entity_id", "name", "description"}


def public_places(db: Session, world_id: str, view: PublicView) -> list[dict]:
    """The public active locations of the world that are not zones, by name then id."""
    zones = zone_ids(db, world_id)
    locations = db.exec(
        select(Entity).where(Entity.world_id == world_id, Entity.type == "location", Entity.status == "active")
    ).all()
    kept = [e for e in locations if e.id in view.entity_ids and e.id not in zones]
    return [{"entity_id": e.id, "name": e.name} for e in sorted(kept, key=lambda e: (e.name, e.id))]


def _distinct(texts: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for text in texts:
        stripped = (text or "").strip()
        key = normalize_surface(stripped)
        if not stripped or key in seen:
            continue
        seen.add(key)
        kept.append(stripped)
    return kept[:limit]


def _role(row: dict) -> str:
    return f" ({row['role']})" if row.get("role") else ""


def _dossier_line(row: dict) -> str:
    section = row["section"]
    if section == "identity":
        return f"— {row['name']} ({row['type']})"
    if section == "facets":
        return f"  • {row['label']} : {row['content']}"
    if section == "memberships":
        return f"  • membre de {row['faction_name']}{_role(row)}"
    return f"  • membre : {row['member_name']}{_role(row)}"


def gather_creation_lore(db: Session, world_id: str, *, names: list[str], keywords: list[str]) -> CreationLore:
    """The public lines of the backstory's names and keywords, the named
    public characters, the starting places and the public factions."""
    view = public_view(db, world_id)
    scope = public_scope(view)
    entity_ids: list[str] = []
    for name in _distinct(names, MAX_NAMES):
        for category in CATEGORIES:
            resolution = resolve_named(name, category, world_id, db, scope=scope)
            if resolution.verdict == "matched" and resolution.entity_id not in entity_ids:
                entity_ids.append(resolution.entity_id)

    lines: list[str] = []
    people: list[dict] = []
    for entity_id in entity_ids:
        lines += [_dossier_line(row) for row in public_dossier(entity_id, world_id, view, db)]
        entity = db.get(Entity, entity_id)
        if entity is not None and entity.type == "character" and entity_id in view.entity_ids:
            people.append({"entity_id": entity.id, "name": entity.name})
    for keyword in _distinct(keywords, MAX_KEYWORDS):
        lines += [f"• {row['content']}" for row in public_facts_mentioning(keyword, world_id, view, db)]

    factions = [
        {"entity_id": row["entity_id"], "name": row["name"], "description": row["description"]}
        for row in public_factions(world_id, view, db)
    ]
    return CreationLore(
        lines=tuple(dict.fromkeys(lines))[:MAX_LORE_LINES],
        people=tuple(people),
        places=tuple(public_places(db, world_id, view)[:MAX_LISTED]),
        factions=tuple(factions[:MAX_LISTED]),
    )
