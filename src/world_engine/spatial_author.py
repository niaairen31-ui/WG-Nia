"""Creation-side spatial materialization (TICKET-0039).

materialize_doors turns a location's live connects_to neighbours into door
rows via writes.config.write_location_doors - the SOLE door-write path. It
NEVER creates, judges or removes connects_to edges (a door is the spatial
manifestation of an edge, never its source - B1). It preserves hand-placed
door coordinates and only invents a placeholder point (placement.
door_placeholder_point, H1) for an edge that has no door yet. Idempotent:
re-running on the same locations reproduces the same door set. This module
is NOT reachable from _apply_mutation - world creation is creator direct
authority, never an AI proposal.
"""
from __future__ import annotations

from typing import Iterable

from sqlmodel import Session, select

from . import placement
from .models import Door, Entity, Location, Relation
from .writes import write_location_doors


def _live_neighbour_ids(location_id: str, db: Session) -> list[str]:
    """Active-location connects_to neighbours of location_id, reading both
    column orders exactly as play.py:848 _location_neighbours does (the
    fifth reader — decision D1 of BRIEF-19 stands; not refactored into a
    shared helper). A neighbour that is not an active location entity is
    dropped, defensively — it must never abort the commit."""
    rels_a = db.exec(
        select(Relation).where(
            Relation.type == "connects_to",
            Relation.entity_a_id == location_id,
        )
    ).all()
    rels_b = db.exec(
        select(Relation).where(
            Relation.type == "connects_to",
            Relation.entity_b_id == location_id,
        )
    ).all()
    seen: set[str] = set()
    neighbour_ids: list[str] = []
    for rel in [*rels_a, *rels_b]:
        neighbour_id = rel.entity_b_id if rel.entity_a_id == location_id else rel.entity_a_id
        if neighbour_id in seen:
            continue
        seen.add(neighbour_id)
        neighbour = db.get(Entity, neighbour_id)
        if neighbour is not None and neighbour.type == "location" and neighbour.status == "active":
            neighbour_ids.append(neighbour_id)
    return neighbour_ids


def materialize_doors(
    db: Session,
    *,
    world_id: str,
    location_ids: Iterable[str],
    changed_by: str,
) -> dict:
    """Rebuilds the `door` rows of every location in `location_ids` from its
    live `connects_to` neighbours, via write_location_doors. Preserves any
    existing (x, y) for a surviving edge; invents
    placement.door_placeholder_point(location) only for an edge that has no
    door yet. Full-replace naturally drops doors whose edge died. Caller
    owns the commit (match the region commit's single-db.commit() contract,
    regions.py) — this function never commits.

    Returns `{"locations": n, "doors_written": m, "placeholders": k}`.
    """
    summary = {"locations": 0, "doors_written": 0, "placeholders": 0}
    for location_id in dict.fromkeys(location_ids):
        location = db.get(Location, location_id)
        if location is None:
            continue

        neighbour_ids = _live_neighbour_ids(location_id, db)
        existing_doors = db.exec(
            select(Door).where(Door.location_id == location_id)
        ).all()
        existing_points = {door.target_location_id: (door.x, door.y) for door in existing_doors}

        payload = []
        for neighbour_id in neighbour_ids:
            if neighbour_id in existing_points:
                x, y = existing_points[neighbour_id]
            else:
                x, y = placement.door_placeholder_point(location)
                summary["placeholders"] += 1
            payload.append({"target_location_id": neighbour_id, "x": x, "y": y})

        new_doors = write_location_doors(
            db, world_id=world_id, location_id=location_id, doors=payload, changed_by=changed_by
        )
        summary["locations"] += 1
        summary["doors_written"] += len(new_doors)

    return summary
