"""Full-replace curated-config canon-write chokepoints (TICKET-0028,
BRIEF-0028-b — decomposed from `writes.py`). Pure moves, no logic change —
none of these three functions were baselined.

- `write_npc_prices(...)`               : full-replace `npc_price` rows
  (TICKET-0025, BRIEF-0025-a — replaces `entity.metadata['price_list']`,
  BRIEF-20). Curated config (faction_role family): no `change_history`,
  hard delete of the prior rows is the sanctioned edit.
- `write_location_subculture(...)`      : full-replace `location_subculture`
  rows (TICKET-0025, BRIEF-0025-b — replaces `location.subculture` JSON).
  Same curated-config discipline; casefold-duplicate keys are rejected
  before write.
- `write_world_laws(...)`               : full-replace `world_law` rows
  (TICKET-0025, BRIEF-0025-b — replaces `world.fundamental_laws` JSON).
  `position` is list order; same curated-config discipline.
- `write_location_obstacles(...)`       : full-replace `obstacle` +
  `obstacle_vertex` rows (TICKET-0029, BRIEF-0029-a — intra-location wall
  geometry). Same curated-config discipline: no `change_history`,
  delete-then-insert inside the caller's transaction.
"""

from __future__ import annotations

import math

from sqlalchemy import text
from sqlmodel import Session

from ..models import Character, LocationSubculture, NpcPrice, Obstacle, ObstacleVertex, World, WorldLaw


def write_npc_prices(
    db: Session,
    *,
    entity: Character,
    prices: dict[str, int],
    changed_by: str,
) -> list[NpcPrice]:
    """Full-replace `npc_price` rows for one NPC. Caller adds the returned
    rows to the session and commits.

    Deletes every existing `npc_price` row for `entity`, then inserts one
    row per `(tag, amount)` pair — the same read-merge-write CONTRACT the
    Tarifs editor already had, now backed by a relational full-replace
    instead of a JSON blob reassignment.
    """
    clean: list[tuple[str, int]] = []
    for tag, amount in prices.items():
        tag = str(tag).strip()
        if not tag:
            raise ValueError("write_npc_prices: tag must be a non-empty string")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError(f"write_npc_prices: amount for {tag!r} must be an int >= 0")
        clean.append((tag, amount))

    db.execute(text("DELETE FROM npc_price WHERE entity_id = :entity_id"), {"entity_id": entity.id})
    rows: list[NpcPrice] = []
    for tag, amount in clean:
        row = NpcPrice(world_id=entity.world_id, entity_id=entity.id, tag=tag, amount=amount)
        db.add(row)
        rows.append(row)
    return rows


def write_location_subculture(
    db: Session,
    *,
    world_id: str,
    location_id: str,
    rows: list[dict],
    changed_by: str,
) -> list[LocationSubculture]:
    """Full-replace `location_subculture` rows for one location. Caller adds
    the returned rows to the session and commits.

    Each item is `{"key": str, "value": str, "is_hidden": bool}` — key and
    value must be non-empty after strip; casefold-duplicate keys are
    rejected before write (defense in depth — the unique index is the
    structural guard). `is_hidden` rows are creator-only — every
    non-creator reader excludes them at query construction (context.py),
    never here.
    """
    clean: list[tuple[str, str, bool]] = []
    seen_casefold: set[str] = set()
    for item in rows:
        key = str(item.get("key") or "").strip()
        value = str(item.get("value") or "").strip()
        is_hidden = bool(item.get("is_hidden", False))
        if not key:
            raise ValueError("write_location_subculture: key must be a non-empty string")
        if not value:
            raise ValueError(f"write_location_subculture: value for {key!r} must be non-empty")
        folded = key.casefold()
        if folded in seen_casefold:
            raise ValueError(f"write_location_subculture: duplicate key {key!r} (casefold)")
        seen_casefold.add(folded)
        clean.append((key, value, is_hidden))

    db.execute(
        text("DELETE FROM location_subculture WHERE location_id = :location_id"),
        {"location_id": location_id},
    )
    new_rows: list[LocationSubculture] = []
    for key, value, is_hidden in clean:
        row = LocationSubculture(world_id=world_id, location_id=location_id, key=key, value=value, is_hidden=is_hidden)
        db.add(row)
        new_rows.append(row)
    return new_rows


def write_world_laws(
    db: Session,
    *,
    world: World,
    laws: list[str],
    changed_by: str,
) -> list[WorldLaw]:
    """Full-replace `world_law` rows for one world. Caller adds the
    returned rows to the session and commits.

    Strips empties; `position` is list order (no reordering UI exists
    today).
    """
    clean = [law.strip() for law in laws if law and law.strip()]

    db.execute(text("DELETE FROM world_law WHERE world_id = :world_id"), {"world_id": world.id})
    new_rows: list[WorldLaw] = []
    for position, law in enumerate(clean):
        row = WorldLaw(world_id=world.id, position=position, text_=law)
        db.add(row)
        new_rows.append(row)
    return new_rows


def write_location_obstacles(
    db: Session,
    *,
    world_id: str,
    location_id: str,
    obstacles: list[list[tuple[float, float]]],
    changed_by: str,
) -> list[Obstacle]:
    """Full-replace `obstacle` + `obstacle_vertex` rows for one location.
    Caller adds the returned rows to the session and commits.

    Each item in `obstacles` is an ordered list of `(x, y)` vertex tuples
    forming one closed polygon — validated all-or-nothing before any write:
    each obstacle needs >= 3 vertices, and every coordinate must be a finite
    float (NaN/inf rejected). `vertex_order` is emitted by enumeration
    (0..n-1), so contiguity is by construction. NO bounds-containment
    validation here — the collision endpoint (ticket 0030) is the sole judge
    of space.
    """
    clean: list[list[tuple[float, float]]] = []
    for polygon in obstacles:
        if len(polygon) < 3:
            raise ValueError(
                f"write_location_obstacles: obstacle has {len(polygon)} vertex/vertices, needs >= 3"
            )
        vertices: list[tuple[float, float]] = []
        for x, y in polygon:
            fx, fy = float(x), float(y)
            if not (math.isfinite(fx) and math.isfinite(fy)):
                raise ValueError(f"write_location_obstacles: non-finite vertex ({x!r}, {y!r})")
            vertices.append((fx, fy))
        clean.append(vertices)

    db.execute(
        text(
            "DELETE FROM obstacle_vertex WHERE obstacle_id IN "
            "(SELECT id FROM obstacle WHERE location_id = :location_id)"
        ),
        {"location_id": location_id},
    )
    db.execute(
        text("DELETE FROM obstacle WHERE location_id = :location_id"),
        {"location_id": location_id},
    )

    new_obstacles: list[Obstacle] = []
    for vertices in clean:
        obstacle = Obstacle(world_id=world_id, location_id=location_id)
        db.add(obstacle)
        new_obstacles.append(obstacle)
        for vertex_order, (x, y) in enumerate(vertices):
            db.add(ObstacleVertex(obstacle_id=obstacle.id, vertex_order=vertex_order, x=x, y=y))
    return new_obstacles
