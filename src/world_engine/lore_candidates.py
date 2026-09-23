"""Candidate enrichment for the lore consultation surface's disambiguation
round-trip (TICKET-0085, BRIEF-0085-c).

A resolver's `candidate_ids` (lore_resolve.py) are bare ids -- nothing in
them lets a creator tell two same-named entities apart. This is a
presentation lookup, not a resolver concern (RECON-0085-a F5): it reads
`entity`, `character` and the entity's `description` facts (`facts_of`,
which drops creator-only facts by query construction) -- no `knowledge`
content, no `relation`, no `faction_membership`.
"""

from __future__ import annotations

from sqlmodel import Session, select

from .facet_reads import facts_of, joined
from .models import Character, Entity


def describe_candidates(candidate_ids: list[str], db: Session) -> list[dict]:
    """One dict per candidate id: `id`, `name`, `type`, `description`,
    `location_name`. `location_name` follows `character.current_location_id`
    to the location's `entity.name`, and is `None` for a candidate that is
    not a character or has no current location. Sorted by name -- no
    ordering that implies a default; the creator chooses."""
    entities = db.exec(select(Entity).where(Entity.id.in_(candidate_ids))).all()
    entity_by_id = {e.id: e for e in entities}

    characters: dict[str, Character] = {}
    location_ids: set[str] = set()
    for candidate_id in candidate_ids:
        entity = entity_by_id.get(candidate_id)
        if entity is None or entity.type != "character":
            continue
        character = db.get(Character, candidate_id)
        if character is None:
            continue
        characters[candidate_id] = character
        if character.current_location_id:
            location_ids.add(character.current_location_id)

    location_names = {
        e.id: e.name
        for e in db.exec(select(Entity).where(Entity.id.in_(location_ids))).all()
    } if location_ids else {}

    rows: list[dict] = []
    for candidate_id in candidate_ids:
        entity = entity_by_id.get(candidate_id)
        if entity is None:
            continue
        character = characters.get(candidate_id)
        location_id = character.current_location_id if character is not None else None
        rows.append(
            {
                "id": entity.id,
                "name": entity.name,
                "type": entity.type,
                "description": joined(facts_of(db, entity_id=entity.id, facets=("description",))),
                "location_name": location_names.get(location_id) if location_id else None,
            }
        )
    rows.sort(key=lambda r: r["name"])
    return rows
