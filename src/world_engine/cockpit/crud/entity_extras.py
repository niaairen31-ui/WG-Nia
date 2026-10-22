"""A create's world extras -- the states, links and germs a draft proposed and the creator kept, written in the create's own transaction (TICKET-0124, BRIEF-0124-E).

C-09 of LOT-0124: `write_create_extras` runs after `_create_entity_core`
and before `create_entity`'s single commit (INV-18): it never commits and
never rolls back. Every refusal is a `ValueError` the route answers 422
after rolling the whole create back -- everything or nothing (S1).

States go through `write_attribute_value`, links through
`write_oriented_relations` (social types only), and each ticked germ is an
`entity_creation` proposal born `approved` -- the creator's tick is the
approval (I1) -- with `source_type="creation"` and no source FK, the tick
precedent.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlmodel import Session

from ...attributes import system_attribute
from ...day_concordance import _germ_blocked
from ...models import Entity, ProposedMutation
from ...relation_orientation import is_social
from ...writes.attributes import write_attribute_value
from ...writes.relations import write_oriented_relations

GERM_TYPES = ("character", "location", "faction")
CHANGED_BY = "creator_crud"


def write_create_extras(db: Session, entity: Entity, body: Any) -> dict:
    """Write `body.states`, `body.relations` and `body.germs` for the new
    `entity`; returns the counts, the germs' mutation ids and the germs
    skipped as already named in the world."""
    germs, skipped = _write_germs(db, entity, body.germs)
    return {
        "states": _write_states(db, entity, body.states),
        "relations": _write_relations(db, entity, body.relations),
        "germs": germs,
        "germs_skipped": skipped,
    }


def _write_states(db: Session, entity: Entity, states: list[dict]) -> int:
    for state in states:
        key = state.get("key")
        if not key:
            raise ValueError("Un état sans clé ne s'écrit pas.")
        if system_attribute(key) is not None:
            raise ValueError(f"Un état système ne s'écrit pas ici : {key}")
        write_attribute_value(
            db, world_id=entity.world_id, definition_id=key, entity_id=entity.id,
            value=state.get("value"), kind="correction", changed_by=CHANGED_BY,
        )
    return len(states)


def _write_relations(db: Session, entity: Entity, relations: list[dict]) -> int:
    written = 0
    for link in relations:
        other_id = link.get("other_entity_id")
        other = db.get(Entity, other_id) if isinstance(other_id, str) else None
        if other is None or other.world_id != entity.world_id:
            raise ValueError(f"Un lien vise une entité hors de ce monde : {other_id!r}")
        if other.id == entity.id:
            raise ValueError("Une entité ne se lie pas à elle-même.")
        relation_type = str(link.get("type") or "").strip()
        if not relation_type or not is_social(relation_type):
            raise ValueError(f"Un lien de création est social : {relation_type!r} ne l'est pas.")
        rows = write_oriented_relations(
            db, world_id=entity.world_id, entity_a_id=entity.id, entity_b_id=other.id,
            type=relation_type, value=50, direction="a_to_b", visible_to_b=False,
            notes=link.get("notes"), changed_by=CHANGED_BY,
        )
        written += len(rows)
    return written


def _write_germs(db: Session, entity: Entity, germs: list[dict]) -> tuple[list[str], list[dict]]:
    made: list[str] = []
    skipped: list[dict] = []
    for germ in germs:
        entity_type = germ.get("entity_type")
        if entity_type not in GERM_TYPES:
            raise ValueError(f"Un germe est un personnage, un lieu ou une faction, pas {entity_type!r}.")
        name = str(germ.get("name") or "").strip()
        if not name:
            raise ValueError("Un germe sans nom ne s'écrit pas.")
        reason = _germ_blocked(name, entity.world_id, db)
        if reason is not None:
            skipped.append({"name": name, "reason": reason})
            continue
        mutation = ProposedMutation(
            world_id=entity.world_id, source_type="creation", mutation_type="entity_creation",
            status="approved", proposed_by="creator_draft",
            payload=_germ_payload(entity, entity_type, name, germ),
            rationale="coché dans le brouillon de " + entity.name,
            creator_notes="en attente de réalisation — onglet Création",
        )
        db.add(mutation)
        db.flush()
        made.append(mutation.id)
    return made, skipped


def _germ_payload(entity: Entity, entity_type: str, name: str, germ: dict) -> dict:
    """C-10's draft germ: exactly these five keys."""
    link_type: Optional[str] = str(germ.get("link_type") or "").strip() or None
    return {
        "entity_type": entity_type,
        "name": name,
        "concept": str(germ.get("concept") or "").strip(),
        "origin_entity_id": entity.id,
        "link_type": link_type,
    }
