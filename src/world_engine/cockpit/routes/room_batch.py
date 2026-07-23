"""Room batch generation + commit routes (TICKET-0042).

Read routes (BRIEF-0042-d) are thin wrappers over room_batch_author's three
phases -- same no-canon-write neighbourhood as /api/regions/manifest and
/api/regions/generate (regions.py). The commit route (BRIEF-0042-e) is the
SOLE canon-write path for a batch, posture identical to commit_region: the
client is untrusted, the parent cascade is re-derived server-side, doors
materialize through spatial_author.connect_locations, and the whole batch
commits in one transaction with full rollback on any exception.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from ...db import get_session
from ...models import Entity, Location
from ...room_batch_author import _name_key  # commit-time name resolution must
# stay bit-identical to generation-time resolution (BRIEF-0042-a's K1 spanning
# tree, BRIEF-0042-c's coherence index both key on this) -- reused directly
# rather than a second, potentially-diverging copy (mirrors region_author's
# OWN separate _name_key precedent only where no such identity constraint
# exists; here it does).
from ...room_batch_author import generate_room_batch_draft as _generate_room_batch_draft
from ...room_batch_author import generate_room_batch_manifest as _generate_room_batch_manifest
from ...room_batch_author import propose_batch_coherence as _propose_batch_coherence
from ...spatial_author import connect_locations, location_classification
from .. import crud as _crud

router = APIRouter()


class RoomBatchManifestBody(BaseModel):
    anchor_id: str
    count: int


@router.post("/api/room-batch/manifest")
def generate_room_batch_manifest_route(
    body: RoomBatchManifestBody,
    db: Session = Depends(get_session),
) -> dict:
    """Phase A (BRIEF-0042-a) -- writes no canon."""
    return _generate_room_batch_manifest(body.anchor_id, body.count, db)


class RoomBatchDraftBody(BaseModel):
    manifest: dict[str, Any]
    anchor: dict[str, Any]


@router.post("/api/room-batch/draft")
def generate_room_batch_draft_route(
    body: RoomBatchDraftBody,
    db: Session = Depends(get_session),
) -> dict:
    """Phase B (BRIEF-0042-b) -- writes no canon."""
    return _generate_room_batch_draft(body.manifest, body.anchor, db)


class RoomBatchCoherenceBody(BaseModel):
    manifest: dict[str, Any]
    drafts: dict[str, Any]
    anchor: dict[str, Any]


@router.post("/api/room-batch/coherence")
def propose_batch_coherence_route(
    body: RoomBatchCoherenceBody,
    db: Session = Depends(get_session),
) -> dict:
    """Phase C (BRIEF-0042-c) -- writes no canon."""
    return _propose_batch_coherence(body.manifest, body.drafts, body.anchor, db)


# ── Atomic commit (BRIEF-0042-e) -- the SOLE canon-write path for a batch ──


class RoomBatchCommitRoom(BaseModel):
    local_id: str
    name: str
    parent_room: Optional[str] = None
    result: dict[str, Any]


class RoomBatchCommitEdge(BaseModel):
    id: str
    a_id: str
    b_id: str
    a_local: bool
    b_local: bool
    reason: Optional[str] = None


class RoomBatchCommitBody(BaseModel):
    anchor_id: str
    rooms: list[RoomBatchCommitRoom]
    accepted: dict[str, bool] = {}
    edges: list[RoomBatchCommitEdge] = []
    confirmed_edges: dict[str, bool] = {}


def _commit_batch_rooms(
    rooms_in: list[dict], accepted: dict[str, bool], anchor_id: str, world_id: str, db: Session,
) -> tuple[dict[str, str], dict[str, str], list[dict]]:
    """Rooms only, dependency order (parent before child). Server-authoritative
    cascade (mirrors _region_resolve_location_parent's SHAPE, regions.py):
    a room's parent_room NAME is re-resolved against the ACCEPTED set only --
    an unaccepted/renamed-away parent falls back to the anchor. The client's
    rendering of its own cascade is never trusted, only `accepted` is.
    Returns (local_id -> entity_id, entity_id -> parent entity_id -- doubling
    as the K1 spanning-tree edge list -- , committed room summaries)."""
    accepted_rooms = [r for r in rooms_in if accepted.get(r["local_id"], True)]
    name_to_local: dict[str, str] = {}
    for r in accepted_rooms:
        name_to_local.setdefault(_name_key(r["name"]), r["local_id"])

    def parent_local_id(room: dict) -> Optional[str]:
        parent_name = room.get("parent_room")
        return name_to_local.get(_name_key(parent_name)) if parent_name else None

    room_id_map: dict[str, str] = {}
    parent_entity_of: dict[str, str] = {}
    committed_rooms: list[dict] = []
    remaining = list(accepted_rooms)
    while remaining:
        ready = [r for r in remaining if (p := parent_local_id(r)) is None or p in room_id_map]
        if not ready:
            break  # cycle guard -- K1 already guaranteed a tree at generation time
        for entry in ready:
            local_id = entry["local_id"]
            pub = entry["result"]["draft"]["public"]
            parent_local = parent_local_id(entry)
            parent_entity_id = room_id_map[parent_local] if parent_local else anchor_id
            entity_data = {"type": "location", "name": entry["name"], "description": pub.get("description")}
            ext_data = {
                "location_type": pub.get("location_type"),
                "access_level": pub.get("access_level") or None,
                "parent_location_id": parent_entity_id,
            }
            room_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data)
            room_entity = _crud._create_entity_core(room_body, db)
            room_id_map[local_id] = room_entity.id
            parent_entity_of[room_entity.id] = parent_entity_id
            committed_rooms.append({"local_id": local_id, "id": room_entity.id, "name": room_entity.name})
            remaining.remove(entry)
    return room_id_map, parent_entity_of, committed_rooms


def _commit_batch_tree_edges(parent_entity_of: dict[str, str], world_id: str, db: Session) -> int:
    """K1 spanning-tree edges -- every committed room's parent-child
    adjacency IS a passage (N1: doors materialize on the perimeter via
    connect_locations, never model-proposed). Unconditional -- not gated by
    confirmed_edges, which governs the SUPPLEMENTARY edges only."""
    written = 0
    for entity_id, parent_entity_id in parent_entity_of.items():
        connect_locations(db, world_id=world_id, entity_a_id=parent_entity_id, entity_b_id=entity_id, changed_by="creator")
        written += 1
    return written


def _commit_batch_edges(
    edges_in: list[dict], confirmed_edges: dict[str, bool], room_id_map: dict[str, str], world_id: str, db: Session,
) -> tuple[int, list[dict]]:
    """Confirmed supplementary edges only (L1 posture). `a_local`/`b_local`
    (BRIEF-0042-c) tell whether a side is a batch `local_id` (resolved
    through `room_id_map`, populated THIS transaction) or already a real
    canon entity id (the anchor or a sibling, used directly). An endpoint
    that was rejected or never committed resolves to None here and writes
    nothing -- recorded as unresolved instead."""
    written = 0
    unresolved: list[dict] = []
    for edge in edges_in:
        if not confirmed_edges.get(edge["id"]):
            continue
        a_id = room_id_map.get(edge["a_id"]) if edge.get("a_local") else edge["a_id"]
        b_id = room_id_map.get(edge["b_id"]) if edge.get("b_local") else edge["b_id"]
        if a_id is None or b_id is None:
            unresolved.append({"a_id": edge["a_id"], "b_id": edge["b_id"], "reason": "Extrémité rejetée ou non commitée"})
            continue
        connect_locations(db, world_id=world_id, entity_a_id=a_id, entity_b_id=b_id, changed_by="creator")
        written += 1
    return written, unresolved


def _anchor_t1_note(anchor_location: Optional[Location], world_id: str, db: Session) -> Optional[str]:
    """T1: an anchor with NULL bounds or NULL classification never blocks
    the batch -- doors on that side degrade to the origin (placement.py).
    Advisory only."""
    if anchor_location is None:
        return None
    bounds_missing = anchor_location.bounds_width is None or anchor_location.bounds_height is None
    classification_missing = location_classification(
        db, world_id=world_id, location_id=anchor_location.id
    ) is None
    if bounds_missing or classification_missing:
        return "Ancre sans bounds -- portes cote ancre a l'origine jusqu'a classification"
    return None


@router.post("/api/room-batch/commit")
def commit_room_batch(
    body: RoomBatchCommitBody,
    db: Session = Depends(get_session),
) -> dict:
    """Atomic batch commit (BRIEF-0042-e) -- the SOLE canon-write path for a
    room batch, posture identical to commit_region (regions.py): the client
    is untrusted, the parent cascade is re-derived server-side from the
    `accepted` map (never from a client-sent effective parent), every
    `connects_to` edge (K1 spanning tree AND confirmed supplementary edges)
    is written through spatial_author.connect_locations so doors materialize
    on the perimeter, and the whole batch commits in ONE transaction with
    full rollback on any exception -- no half-batch is ever observable.
    """
    world_id = _crud._world_id(db)
    anchor = db.get(Entity, body.anchor_id)
    if anchor is None or anchor.type != "location" or anchor.world_id != world_id:
        return {"ok": False, "error": "Anchor location not found"}
    anchor_location = db.get(Location, body.anchor_id)

    rooms_in = [r.model_dump() for r in body.rooms]
    edges_in = [e.model_dump() for e in body.edges]

    try:
        room_id_map, parent_entity_of, committed_rooms = _commit_batch_rooms(
            rooms_in, body.accepted, body.anchor_id, world_id, db,
        )
        tree_written = _commit_batch_tree_edges(parent_entity_of, world_id, db)
        supplementary_written, unresolved = _commit_batch_edges(
            edges_in, body.confirmed_edges, room_id_map, world_id, db,
        )
        notes = []
        t1_note = _anchor_t1_note(anchor_location, world_id, db)
        if t1_note:
            notes.append(t1_note)
        db.commit()
    except HTTPException as exc:
        db.rollback()
        return {"ok": False, "error": str(exc.detail)}
    except IntegrityError as exc:
        db.rollback()
        return {"ok": False, "error": f"Database integrity error: {exc}"}
    except Exception as exc:  # noqa: BLE001 -- atomicity: any failure rolls back, never half-commits
        db.rollback()
        return {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "committed": {"rooms": committed_rooms},
        "edges_written": tree_written + supplementary_written,
        "unresolved": unresolved,
        "notes": notes,
    }
