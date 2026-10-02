"""Zone promotion seam of the creator CRUD (TICKET-0101, D + K, S1).

A location that gains its first active child becomes a zone. The creator
CRUD reaches that moment in two places -- a location created with a parent
(`_create_static_entity_core`) and a location whose parent or status changes
(`update_entity`) -- and both call `promote_for_child`:

- nothing to move (`needs_confirmation` False): the promotion is applied
  silently -- a fresh parent, a room nested in a room just created;
- something to move and the child is itself a zone (it has an active child
  already -- a re-parent or a reactivation): 409 with a creator-facing
  message, nothing written, confirmed or not (AMENDMENT-0101-01: the
  contents would land in a zone, which B1 forbids);
- something to move and the request did not carry `confirm_promotion`:
  409 with `{"code": "promotion_required", "preview": <promotion_preview>}`,
  nothing written (S1);
- confirmed: `writes.zone_promotion.apply_promotion`, then each moved being
  leaves its gatherings and joins the first child's live one, as a fiche
  location change does (`close_open_memberships`, `attach_on_arrival`).

The gatherings those moves may have emptied, and the open gatherings of the
promoted location, are parked on `db.info` and dissolved by
`take_promotion_gatherings(db)` in the caller's post-commit
`dissolve_emptied`, never before the commit.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session as DbSession

from ...gathering import attach_on_arrival, close_open_memberships
from ...models import Entity
from ...spatial_author import link_locations
from ...writes.zone_promotion import apply_promotion, promotion_preview

_PENDING_KEY = "zone_promotion_gatherings"


def promote_parent(db: DbSession, *, parent_id: str, child_id: str, confirmed: bool) -> Optional[dict]:
    """Promote `parent_id` around `child_id` when it is the first active
    child; returns the applied preview, or None when nothing promotes."""
    db.flush()
    preview = promotion_preview(db, parent_id, child_id=child_id)
    if not preview["promotes"]:
        return None
    if preview["needs_confirmation"] and preview["target_is_zone"]:
        raise HTTPException(409, _target_is_zone_message(db, parent_id, child_id))
    if preview["needs_confirmation"] and not confirmed:
        raise HTTPException(409, detail={"code": "promotion_required", "preview": preview})
    apply_promotion(db, parent_id=parent_id, child_id=child_id, changed_by="creator")
    closed = []
    for being in preview["beings"]:
        closed.extend(close_open_memberships(being["id"], db))
        attach_on_arrival(being["id"], child_id, db)
    pending = db.info.setdefault(_PENDING_KEY, set())
    pending.update(row.gathering_id for row in closed)
    pending.update(g["id"] for g in preview["gatherings"])
    return preview


def _target_is_zone_message(db: DbSession, parent_id: str, child_id: str) -> str:
    parent, child = db.get(Entity, parent_id), db.get(Entity, child_id)
    p_name = parent.name if parent is not None else parent_id
    c_name = child.name if child is not None else child_id
    return (
        f"« {c_name} » est déjà une zone : le contenu de « {p_name} » ne peut pas y être "
        f"déplacé. Rattachez d'abord un lieu visitable à « {p_name} », ou videz « {p_name} »."
    )


def promote_for_child(
    db: DbSession, entity: Entity, ext: Any, *, confirmed: bool,
    prior_parent_id: Optional[str] = None, prior_status: Optional[str] = None,
) -> Optional[dict]:
    """The CRUD trigger: `entity` is a location that is, after this write, an
    active child of `ext.parent_location_id`, and was not one before (new,
    re-parented, or reactivated)."""
    if entity.type != "location" or ext is None or entity.status != "active":
        return None
    parent_id = getattr(ext, "parent_location_id", None)
    if not parent_id or (parent_id == prior_parent_id and prior_status == "active"):
        return None
    return promote_parent(db, parent_id=parent_id, child_id=entity.id, confirmed=confirmed)


def link_new_location(db: DbSession, entity: Entity, neighbour_ids: list[str]) -> None:
    """K, "creating any child of a zone": the neighbours the creator ticked
    are linked to the new location through `link_locations`, which derives
    each type (`connects_to` to a visitable neighbour, `borde` to a zone).
    Runs after any promotion, so the parent is already a zone. A neighbour
    that is not a location is a 422."""
    for neighbour_id in dict.fromkeys(neighbour_ids or []):
        if neighbour_id == entity.id:
            continue
        try:
            link_locations(
                db, world_id=entity.world_id, entity_a_id=entity.id, entity_b_id=neighbour_id,
                changed_by="creator",
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc))


def take_promotion_gatherings(db: DbSession) -> set[str]:
    """The gathering ids parked by `promote_parent`, removed from `db.info`."""
    return db.info.pop(_PENDING_KEY, set())
