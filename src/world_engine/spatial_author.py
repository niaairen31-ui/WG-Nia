"""Creation-side spatial materialization (TICKET-0039).

materialize_doors turns a location's live connects_to neighbours into door
rows via writes.config.write_location_doors - the SOLE door-write path. It
NEVER creates, judges or removes connects_to edges (a door is the spatial
manifestation of an edge, never its source - B1). It preserves hand-placed
door coordinates and only invents a placeholder point (placement.
door_placeholder_point, N1) for an edge that has no door yet - except a
point still sitting at the exact H1 bounds center, which is re-derived onto
the perimeter (G1, TICKET-0040). Idempotent: re-running on the same
locations reproduces the same door set. This module is NOT reachable from
_apply_mutation - world creation is creator direct authority, never an AI
proposal.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional

from sqlmodel import Session, select

from . import placement
from .models import Door, Entity, Location, LocationTypeCatalog, Relation
from .writes import write_location_doors, write_relation


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
    existing (x, y) for a surviving edge - except a point still sitting at
    the exact H1 bounds center, which is re-derived onto the perimeter (G1,
    TICKET-0040); invents placement.door_placeholder_point(location,
    neighbour_id) only for an edge that has no door yet. Full-replace
    naturally drops doors whose edge died. Caller owns the commit (match the
    region commit's single-db.commit() contract, regions.py) — this
    function never commits.

    Returns `{"locations": n, "doors_written": m, "placeholders": k, "rederived": r}`.
    """
    summary = {"locations": 0, "doors_written": 0, "placeholders": 0, "rederived": 0}
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
            if neighbour_id not in existing_points:
                x, y = placement.door_placeholder_point(location, neighbour_id)
                summary["placeholders"] += 1
            elif placement.is_legacy_center(location, existing_points[neighbour_id]):
                x, y = placement.door_placeholder_point(location, neighbour_id)
                summary["rederived"] += 1
            else:
                x, y = existing_points[neighbour_id]
            payload.append({"target_location_id": neighbour_id, "x": x, "y": y})

        new_doors = write_location_doors(
            db, world_id=world_id, location_id=location_id, doors=payload, changed_by=changed_by
        )
        summary["locations"] += 1
        summary["doors_written"] += len(new_doors)

    return summary


def connect_locations(
    db: Session,
    *,
    world_id: str,
    entity_a_id: str,
    entity_b_id: str,
    changed_by: str,
) -> dict:
    """Writes a `connects_to` edge and materializes doors for both endpoints
    in one call (J1, TICKET-0039) — the single point where a connects_to
    edge is born wraps "write the edge + materialize both endpoints", so
    every edge creator (region commit, the manual relation-CRUD path) yields
    doors. Does NOT commit — caller owns the commit.
    """
    write_relation(
        db, mode="set", world_id=world_id,
        entity_a_id=entity_a_id, entity_b_id=entity_b_id,
        type="connects_to", value=50, direction="mutual",
    )
    return materialize_doors(
        db, world_id=world_id, location_ids=[entity_a_id, entity_b_id], changed_by=changed_by,
    )


def _catalog_row(db: Session, *, world_id: str, type_name: str) -> Optional[LocationTypeCatalog]:
    """The single catalog read path (J1, TICKET-0040). Both the
    interior/exterior classification and the size template resolve a
    location_type through here; writes.upsert_location_type keeps its own
    lookup - the write layer never climbs into the read layer.
    """
    folded = type_name.casefold()
    for row in db.exec(
        select(LocationTypeCatalog).where(LocationTypeCatalog.world_id == world_id)
    ).all():
        if row.name.casefold() == folded:
            return row
    return None


def location_classification(db: Session, *, world_id: str, location_id: str) -> Optional[str]:
    """The `interior` | `exterior` | None classification of a location's
    `location_type`, read through `location_type_catalog` (case-insensitive
    lookup, world-scoped — same lookup `writes.upsert_location_type` uses).
    NULL `location_type`, or a type with no catalog row, or a catalogued but
    still-unclassified type, all resolve to None (D1: inert for door-kind
    derivation and the E1 street-access note until the creator classifies
    it). This is the ONLY interior/exterior reader — never infer from the
    type string itself.
    """
    location = db.get(Location, location_id)
    if location is None or not location.location_type:
        return None
    row = _catalog_row(db, world_id=world_id, type_name=location.location_type)
    return row.classification if row is not None else None


def location_type_template(
    db: Session, *, world_id: str, type_name: Optional[str]
) -> Optional[tuple[float, float]]:
    """Fail-closed (B1): no template -> None -> the location is born with
    NULL bounds and has no spatial mode. Nothing is ever invented.
    """
    if not type_name:
        return None
    row = _catalog_row(db, world_id=world_id, type_name=type_name)
    if row is None:
        return None
    width, height = row.default_width, row.default_height
    if width is None or height is None:
        return None
    if not math.isfinite(width) or not math.isfinite(height):
        return None
    if width <= 0 or height <= 0:
        return None
    return (width, height)
