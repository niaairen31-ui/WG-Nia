"""Promotion of a visitable location into a zone (TICKET-0101, D + K, N1).

A location becomes a zone the moment it gains its first active child (A1).
Everything that only makes sense in a place one can stand in moves, in the
same transaction, to that first child; everything that describes the place
stays and now describes the zone.

- `promotion_preview(db, parent_id, child_id=None)` : read-only. Whether
  gaining `child_id` (or any first child) promotes `parent_id`, the exact
  rows that would move, and whether `child_id` is itself a zone
  (`target_is_zone`, AMENDMENT-0101-01: such a child cannot receive them). The confirmation dialog and the 409 of S1
  both show this dict; `apply_promotion` moves exactly these rows.
- `apply_promotion(db, parent_id, child_id, changed_by)` : moves them.
  Never commits; the caller owns the transaction and, after its commit,
  dissolves the gatherings the moves emptied (`gathering.dissolve_emptied`
  -- gatherings are not canon, so they are the caller's, never this
  module's).

Resolution table (K), one line per row family:
- `connects_to` rows touching the parent -> retyped in place to `borde`
  through `write_relation(mode="set")`: row history and fact history kept
  (N1). Existing `borde` rows are untouched.
- characters whose `current_location_id` is the parent -> the first child,
  through `write_character_location`.
- `npc_schedule` rows at the parent -> the first child, through a
  full-replace `write_npc_schedule` of each affected NPC's whole schedule.
- items the parent holds (lying there; `item_holding`, TICKET-0109) and discoverable details
  (`discoverable_detail.location_id`) -> the first child.
- open gatherings at the parent -> listed; the caller closes them.
- bounds, obstacles, doors, events, facts, knowledge, `controls`,
  artefacts -> untouched.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Session, select

from ..holdings import items_held
from ..models import Character, DiscoverableDetail, Entity, Gathering, NpcSchedule, Relation
from ..zone_rules import active_child_ids, is_zone
from .characters import write_character_location
from .config import write_npc_schedule
from .items import write_holding
from .relations import write_relation


def _names(db: Session, ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {e.id: e.name for e in db.exec(select(Entity).where(Entity.id.in_(ids))).all()}


def _links(db: Session, parent_id: str) -> list[dict]:
    rows = db.exec(
        select(Relation)
        .where(
            Relation.type == "connects_to",
            (Relation.entity_a_id == parent_id) | (Relation.entity_b_id == parent_id),
        )
        .order_by(Relation.created_at, Relation.id)
    ).all()
    other_ids = [r.entity_b_id if r.entity_a_id == parent_id else r.entity_a_id for r in rows]
    names = _names(db, other_ids)
    return [{"id": r.id, "other_id": o, "other_name": names.get(o, o)} for r, o in zip(rows, other_ids)]


def _beings(db: Session, parent_id: str) -> list[dict]:
    rows = db.exec(
        select(Character, Entity)
        .join(Entity, Entity.id == Character.id)
        .where(Character.current_location_id == parent_id)
        .order_by(Entity.name)
    ).all()
    return [{"id": c.id, "name": e.name, "character_type": c.character_type} for c, e in rows]


def _schedules(db: Session, parent_id: str) -> list[dict]:
    rows = db.exec(
        select(NpcSchedule).where(NpcSchedule.location_id == parent_id).order_by(NpcSchedule.npc_id)
    ).all()
    names = _names(db, [r.npc_id for r in rows])
    return [{"npc_id": r.npc_id, "npc_name": names.get(r.npc_id, r.npc_id), "phase": r.phase} for r in rows]


def _items(db: Session, parent_id: str) -> list[dict]:
    """The items the parent holds (lying there, TICKET-0109 A1)."""
    return [{"id": item.id, "name": e.name, "quantity": h.quantity} for h, item, e in items_held(db, parent_id)]


def _details(db: Session, parent_id: str) -> list[dict]:
    rows = db.exec(
        select(DiscoverableDetail).where(DiscoverableDetail.location_id == parent_id)
        .order_by(DiscoverableDetail.subject)
    ).all()
    return [{"id": d.id, "subject": d.subject} for d in rows]


def _gatherings(db: Session, parent_id: str) -> list[dict]:
    rows = db.exec(
        select(Gathering).where(Gathering.location_id == parent_id, Gathering.status == "open")
    ).all()
    return [{"id": g.id, "label": g.label or ""} for g in rows]


MOVING_KEYS = ("links", "beings", "schedules", "items", "details", "gatherings")


def promotion_preview(db: Session, parent_id: Optional[str], *, child_id: Optional[str] = None) -> dict:
    """What `parent_id` gaining `child_id` moves. `promotes` is False -- and
    every list empty -- when `parent_id` is None, not a location, or already
    has an active child other than `child_id`. `needs_confirmation` is True
    when it promotes and at least one list is non-empty (S1).
    `target_is_zone` is True when `child_id` itself has an active child."""
    parent = db.get(Entity, parent_id) if parent_id else None
    preview: dict = {
        "location_id": parent_id,
        "location_name": parent.name if parent is not None else None,
        "promotes": False,
        "needs_confirmation": False,
        "target_is_zone": is_zone(db, child_id),
        **{key: [] for key in MOVING_KEYS},
    }
    if parent is None or parent.type != "location" or active_child_ids(db, parent.id, exclude_id=child_id):
        return preview
    preview.update(
        promotes=True,
        links=_links(db, parent.id), beings=_beings(db, parent.id), schedules=_schedules(db, parent.id),
        items=_items(db, parent.id), details=_details(db, parent.id), gatherings=_gatherings(db, parent.id),
    )
    preview["needs_confirmation"] = any(preview[key] for key in MOVING_KEYS)
    return preview


def _retarget_schedules(db: Session, world_id: str, preview: dict, parent_id: str, child_id: str, changed_by: str) -> None:
    for npc_id in sorted({row["npc_id"] for row in preview["schedules"]}):
        rows = db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == npc_id)).all()
        write_npc_schedule(
            db, world_id=world_id, npc_id=npc_id, changed_by=changed_by,
            rows=[{
                "phase": r.phase,
                "location_id": child_id if r.location_id == parent_id else r.location_id,
                "standing_goal_id": r.standing_goal_id,
            } for r in rows],
        )


def apply_promotion(db: Session, *, parent_id: str, child_id: str, changed_by: str) -> dict:
    """Promote `parent_id` into a zone around its first child `child_id`,
    which must already be in the session. Returns the preview it applied
    (`promotes=False`: nothing was done). Never commits."""
    preview = promotion_preview(db, parent_id, child_id=child_id)
    if not preview["promotes"]:
        return preview
    world_id = db.get(Entity, parent_id).world_id
    for link in preview["links"]:
        rel = db.get(Relation, link["id"])
        write_relation(
            db, mode="set", relation_id=rel.id, type="borde", value=rel.intensity,
            direction=rel.direction, visible_to_b=rel.visible_to_b, notes=rel.notes,
            changed_by=changed_by,
        )
    for being in preview["beings"]:
        write_character_location(db, entity_id=being["id"], to_location_id=child_id)
    _retarget_schedules(db, world_id, preview, parent_id, child_id, changed_by)
    now = datetime.now(UTC)
    for item in preview["items"]:
        write_holding(db, world_id=world_id, item_id=item["id"], holder_entity_id=parent_id,
                      delta=-item["quantity"], changed_by=changed_by)
        write_holding(db, world_id=world_id, item_id=item["id"], holder_entity_id=child_id,
                      delta=item["quantity"], changed_by=changed_by)
    for detail in preview["details"]:
        row = db.get(DiscoverableDetail, detail["id"])
        row.location_id = child_id
        row.updated_at = now
        db.add(row)
    return preview
