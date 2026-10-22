"""What a draft adds from its world -- the names it may cite, the fields it fills, and code's judgment of its answer (TICKET-0124, BRIEF-0124-G; A2, G2).

The entity draft (`entity_author._entity_draft_call`) appends
`WORLD_FIELDS[entity_type]` to the fields it asks, and the citable names of
`known_names_block` after them. The model answers by exact name and label;
`resolve_world_block` decides what each answer means (Gate (b) table 3 of
LOT-0124): a state's label matched to a choice id, a name resolved to an
entity of the world, an unknown name turned into an entity to create. Every
id it returns comes from a `select` on the world's rows, never from the
model. Every drop appends one French note.

This module only reads: it writes, flushes and commits nothing.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session, select

from .attributes import BUILTIN_TYPE_LABELS_FR, AttributeView, applies_to, world_attributes
from .lore_resolve import normalize_surface
from .models import Character, Entity, World
from .relation_orientation import is_social

MAX_KNOWN_NAMES = 60
MAX_DRAFT_GERMS = 3
TO_CREATE_TYPES: tuple[str, ...] = ("character", "location", "faction")

_STATES = ('public.states (tableau d\'objets {"state","value"} — un par état listé dans le cadre '
           'du monde pour ce type ; state = nom exact de l\'état ; value = un des libellés '
           'proposés, un entier, ou le nom exact d\'une entité)')
_LINKS = ('public.links (tableau d\'objets {"name","type","note"} — liens avec une entité '
          'EXISTANTE de la liste ci-dessous ; name = nom exact ; type = la nature du lien vue '
          'depuis cette entité, ex. élève, rival, protecteur)')
_SAME_AS = ('public.same_as (string ou null — nom exact d\'un personnage de la liste qui '
            'pourrait être cette même personne, sinon null)')
_TO_CREATE = ('public.to_create (tableau d\'objets {"name","entity_type","concept","link"} — au '
              'plus 3 entités qui n\'existent pas encore et que cette fiche appelle ; '
              'entity_type parmi character|location|faction ; link = la nature du lien)')
WORLD_FIELDS: dict[str, str] = {
    "character": " ;\n".join((_STATES, _LINKS, _SAME_AS, _TO_CREATE)) + ".",
    "location": " ;\n".join((_STATES, _LINKS, _TO_CREATE)) + ".",
    "faction": " ;\n".join((_STATES, _LINKS, _TO_CREATE)) + ".",
}

_KNOWN_NAMES_HEADER = "Entités existantes que tu peux nommer (nom exact) :"


def active_world_id(db: Session) -> Optional[str]:
    """The id of the active world, or None."""
    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    return world.id if world is not None else None


def _type_label(entity_type: str) -> str:
    return BUILTIN_TYPE_LABELS_FR.get(entity_type, entity_type).lower()


def _key(text: Any) -> str:
    return text.strip().casefold() if isinstance(text, str) else ""


def _text(raw: Any) -> str:
    return raw.strip() if isinstance(raw, str) else ""


def _world_entities(db: Session, world_id: str) -> list[tuple[Entity, Optional[str]]]:
    """The world's active entities, each with its `character_type` (None
    for a non-character), sorted by casefolded name."""
    rows = db.exec(
        select(Entity, Character.character_type)
        .join(Character, Character.id == Entity.id, isouter=True)
        .where(Entity.world_id == world_id, Entity.status == "active")
    ).all()
    return sorted(rows, key=lambda row: row[0].name.casefold())


def known_names_block(db: Session, world_id: Optional[str], entity_type: str,
                      candidate_ids: tuple[str, ...] = ()) -> str:
    """The names a draft may cite (C-13): the candidates first, in order,
    then the active non-player characters, the factions and the locations,
    each by name, no repeat, at most `MAX_KNOWN_NAMES` lines; `""` when
    none. Every type is listed, whatever `entity_type` the draft is."""
    if world_id is None:
        return ""
    entities = _world_entities(db, world_id)
    by_id = {entity.id: (entity, kind) for entity, kind in entities}
    ordered = [by_id[c] for c in candidate_ids if c in by_id]
    ordered += [(e, k) for e, k in entities if e.type == "character" and k != "player"]
    ordered += [(e, k) for e, k in entities if e.type == "faction"]
    ordered += [(e, k) for e, k in entities if e.type == "location"]
    lines: list[str] = []
    seen: set[str] = set()
    for entity, kind in ordered:
        if entity.id in seen or kind == "player":
            continue
        seen.add(entity.id)
        lines.append(f"- {entity.name} ({_type_label(entity.type)})")
        if len(lines) == MAX_KNOWN_NAMES:
            break
    return "\n".join([_KNOWN_NAMES_HEADER, *lines]) if lines else ""


def _items(raw: Any) -> list[dict]:
    """A list answer's dict items; anything else is ignored without a note."""
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _state_value(view: AttributeView, raw: Any, by_name: dict, draft_name: str,
                 derived: list[dict], notes: list[str]) -> Optional[dict]:
    """One answered state's value, judged by its kind; None when dropped
    (a note) or turned into an entity to create (`derived`)."""
    state = {"key": view.key, "name": view.name, "kind": view.kind}
    if view.kind == "choice":
        wanted = normalize_surface(raw) if isinstance(raw, str) else None
        match = next((c for c in view.choices if wanted and normalize_surface(c[1]) == wanted), None)
        if match is not None:
            return {**state, "value": match[0], "label": match[1]}
    elif view.kind == "integer":
        number = raw if isinstance(raw, int) and not isinstance(raw, bool) else None
        if isinstance(raw, str) and raw.strip().lstrip("-").isdigit():
            number = int(raw.strip())
        if number is not None:
            return {**state, "value": number, "label": str(number)}
    elif view.kind == "entity" and _text(raw):
        match = next((e for e, _k in by_name.get(_key(raw), []) if e.type in view.value_types), None)
        if match is not None:
            return {**state, "value": match.id, "label": match.name}
        creatable = next((t for t in view.value_types if t in TO_CREATE_TYPES), None)
        if creatable is not None:
            derived.append({"name": _text(raw), "entity_type": creatable,
                            "concept": f"{view.name} de {draft_name}", "link_type": view.name})
            return None
    notes.append(f"Valeur invalide pour l'état « {view.name} » ignorée : {raw!r}")
    return None


def _resolve_states(raw: Any, views: list[AttributeView], by_name: dict, draft_name: str,
                    derived: list[dict], notes: list[str]) -> list[dict]:
    by_state = {view.name.casefold(): view for view in views}
    states: list[dict] = []
    seen: set[str] = set()
    for item in _items(raw):
        view = by_state.get(_key(item.get("state")))
        if view is None or view.key in seen:
            notes.append(f"État inconnu ou répété ignoré : {item.get('state')!r}")
            continue
        seen.add(view.key)
        value = _state_value(view, item.get("value"), by_name, draft_name, derived, notes)
        if value is not None:
            states.append(value)
    return states


def _resolve_links(raw: Any, by_name: dict, draft_name: str,
                   derived: list[dict], notes: list[str]) -> list[dict]:
    links: list[dict] = []
    linked: set[str] = set()
    for item in _items(raw):
        name, kind, note = _text(item.get("name")), _text(item.get("type")), _text(item.get("note"))
        if not name or _key(name) == _key(draft_name):
            notes.append(f"Lien sans entité ignoré : {name!r}")
            continue
        found = by_name.get(_key(name))
        if not found:
            derived.append({"name": name, "entity_type": "character", "concept": note, "link_type": kind})
            continue
        entity = found[0][0]
        if not kind or not is_social(kind):
            notes.append(f"Lien vers {entity.name} ignoré : nature absente ou non sociale ({kind!r})")
        elif entity.id in linked:
            notes.append(f"Lien répété vers {entity.name} ignoré")
        else:
            linked.add(entity.id)
            links.append({"entity_id": entity.id, "name": entity.name, "type": kind, "note": note})
    return links


def _resolve_same_as(raw: Any, entity_type: str, by_name: dict, notes: list[str]) -> Optional[dict]:
    name = _text(raw)
    if not name:
        return None
    if entity_type == "character":
        for entity, kind in by_name.get(_key(name), []):
            if entity.type == "character" and kind != "player":
                return {"entity_id": entity.id, "name": entity.name}
    notes.append(f"Même personne possible non reconnue : {name!r}")
    return None


def _resolve_to_create(raw: Any, by_name: dict, derived: list[dict], notes: list[str]) -> list[dict]:
    """The derived entities to create first, then the model's, by casefolded
    name, free names only, cut to `MAX_DRAFT_GERMS`."""
    asked = [{"name": _text(i.get("name")), "entity_type": _text(i.get("entity_type")).casefold(),
              "concept": _text(i.get("concept")), "link_type": _text(i.get("link"))}
             for i in _items(raw)]
    kept: list[dict] = []
    seen: set[str] = set()
    for germ in derived + asked:
        name = germ["name"]
        if not name or germ["entity_type"] not in TO_CREATE_TYPES:
            notes.append(f"Entité à créer ignorée (nom ou type invalide) : {name!r}")
        elif _key(name) in by_name:
            notes.append(f"Entité à créer ignorée, existe déjà : {name}")
        elif _key(name) in seen:
            notes.append(f"Entité à créer répétée ignorée : {name}")
        else:
            seen.add(_key(name))
            kept.append(germ)
    if len(kept) > MAX_DRAFT_GERMS:
        notes.append(f"Au plus {MAX_DRAFT_GERMS} entités à créer : "
                     + ", ".join(g["name"] for g in kept[MAX_DRAFT_GERMS:]) + " ignorées")
    return kept[:MAX_DRAFT_GERMS]


def resolve_world_block(db: Session, world_id: str, entity_type: str, public_in: dict,
                        draft_name: str, notes: list[str]) -> dict:
    """Code's judgment of a draft's world answer (C-13, Gate (b) table 3):
    `{"states", "links", "same_as", "to_create"}`, in that order of
    resolution; every drop appends one French note to `notes`."""
    public_in = public_in if isinstance(public_in, dict) else {}
    by_name: dict[str, list[tuple[Entity, Optional[str]]]] = {}
    for entity, kind in _world_entities(db, world_id):
        by_name.setdefault(entity.name.strip().casefold(), []).append((entity, kind))
    views = [v for v in world_attributes(db, world_id)
             if not v.system and v.status == "active" and applies_to(v, entity_type)]
    derived: list[dict] = []
    states = _resolve_states(public_in.get("states"), views, by_name, draft_name, derived, notes)
    links = _resolve_links(public_in.get("links"), by_name, draft_name, derived, notes)
    same_as = _resolve_same_as(public_in.get("same_as"), entity_type, by_name, notes)
    to_create = _resolve_to_create(public_in.get("to_create"), by_name, derived, notes)
    return {"states": states, "links": links, "same_as": same_as, "to_create": to_create}


__all__ = [
    "MAX_DRAFT_GERMS", "MAX_KNOWN_NAMES", "TO_CREATE_TYPES", "WORLD_FIELDS",
    "active_world_id", "known_names_block", "resolve_world_block",
]
