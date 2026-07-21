"""Region generation + commit routes (BRIEF-34/36/37/38).

Split out of `cockpit/routes/creator.py` at TICKET-0027, BRIEF-0027-d (R5):
`creator.py`'s regions sub-domain (region manifest/generate/commit,
including the 264-line `commit_region`) pushed creator.py past the
unbaselined 1000-line module cap on its own — the brief listed regions as
one of creator's sub-domains but the line budget doesn't fit in one file.
Kept as a same-tier sibling router rather than a further creator split;
route paths, methods and bodies are unchanged (pure move).
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ...region_author import generate_region_draft as _generate_region_draft
from ...region_author import generate_region_manifest as _generate_region_manifest
from ...db import get_session
from ...models import Entity
from ...writes import write_faction_role, write_relation
from .. import crud as _crud

router = APIRouter()


class RegionGenerateBody(BaseModel):
    brief: str


class RegionBuildBody(BaseModel):
    manifest: dict[str, Any]


@router.post("/api/regions/manifest")
def generate_region_manifest_route(
    body: RegionGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI region manifest generator — Phase A (BRIEF-38).

    Deliberately NOT in crud.py, same neighbourhood as /api/entities/generate:
    crud.py is a sanctioned canon-write path and this route writes nothing.
    Calls only generate_region_manifest, which produces the Stage-0 manifest
    for the creator checkpoint. Returns {"ok": false, "error": ...} (never a
    500) on any failure.
    """
    return _generate_region_manifest(body.brief, db)


@router.post("/api/regions/generate")
def generate_region(
    body: RegionBuildBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI region draft generator — Phase B (BRIEF-34, chantier 1;
    repurposed to accept a manifest by BRIEF-38).

    Deliberately NOT in crud.py, same neighbourhood as /api/entities/generate:
    crud.py is a sanctioned canon-write path and this route writes nothing.
    Calls only generate_region_draft, which composes generate_entity_draft
    across factions/locations and writes no canon itself. The manifest
    is re-normalized server-side before use (client-edited input is
    advisory). Returns {"ok": false, "error": ...} (never a 500) on any
    failure.
    """
    return _generate_region_draft(body.manifest, db)


class RegionCommitBody(BaseModel):
    region: dict[str, Any]
    accepted: dict[str, bool] = {}
    confirmed_links: dict[str, bool] = {}


def _region_resolve_location_parent(
    entry: dict, accepted_locations: dict, root_local: Optional[str]
) -> Optional[str]:
    """Re-derive a location's effective parent local id from the raw
    accept/reject map (server-authoritative cascade, never the client's).

    Reject-a-parent re-parents to ROOT (not the nearest accepted ancestor) —
    same rule as generation's manifest parser. Returns None if there is no
    surviving parent to attach to (e.g. the root itself was rejected).
    """
    parent_local = entry.get("parent_local_id")
    if parent_local is None:
        return None
    if parent_local in accepted_locations:
        return parent_local
    if root_local is not None and root_local in accepted_locations and root_local != entry["local_id"]:
        return root_local
    return None


def _region_resolve_link_target(
    db: Session,
    world_id: Optional[str],
    name: Any,
    kind: str,
    committed_locations_by_name: dict[str, str],
    committed_factions_by_name: dict[str, str],
) -> tuple[Optional[str], Optional[str]]:
    """Resolve a confirmed `sensed_links` target (S1): intra-region first
    (by committed name), then DB exact-match (case-insensitive, whitespace-
    stripped), scoped to the committed world. Never auto-creates a target —
    a miss returns (None, <reason>).
    """
    if not name or not isinstance(name, str):
        return None, "Nom de cible manquant"
    target = name.strip().lower()
    if not target:
        return None, "Nom de cible manquant"

    entity_type = "location" if kind == "connection" else "faction"
    by_name = committed_locations_by_name if kind == "connection" else committed_factions_by_name
    intra = by_name.get(target)
    if intra:
        return intra, None

    stmt = select(Entity).where(Entity.type == entity_type)
    if world_id is not None:
        stmt = stmt.where(Entity.world_id == world_id)
    for candidate in db.exec(stmt).all():
        if (candidate.name or "").strip().lower() == target:
            return candidate.id, None
    return None, f"Cible « {name} » introuvable"


def _commit_region_factions(
    factions_in: list[dict], accepted_factions: dict, world_id: Optional[str], db: Session,
) -> tuple[dict[str, str], list[dict]]:
    """Stage 1 — factions.

    Also commits each faction's role vocabulary (`public.roles`, produced by
    `entity_author._normalize_roles`) through `write_faction_role` — the
    sole `faction_role` write chokepoint — mirroring the unitary faction
    creator's `POST /factions/{id}/roles` route exactly (BRIEF-0033-a
    corrective; previously silently dropped). Casefold-deduped, first
    occurrence wins, so a model-produced duplicate name never aborts the
    atomic region commit via the unique index.
    """
    fac_id_map: dict[str, str] = {}
    committed_factions: list[dict] = []
    for entry in factions_in:
        local_id = entry["local_id"]
        if local_id not in accepted_factions:
            continue
        draft = entry["result"]["draft"]
        pub, sec = draft["public"], draft["secret"]
        entity_data: dict[str, Any] = {
            "type": "faction",
            "name": pub.get("name"),
            "description": pub.get("description"),
        }
        ext_data = {
            "faction_type": pub.get("faction_type"),
            "philosophy": pub.get("philosophy"),
            "internal_structure": pub.get("internal_structure"),
            "aversion": pub.get("aversion"),
            "internal_tensions": sec.get("internal_tensions"),
            "goals": sec.get("goals"),
        }
        fac_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data)
        fac_entity = _crud._create_entity_core(fac_body, db)
        fac_id_map[local_id] = fac_entity.id
        committed_factions.append({"local_id": local_id, "id": fac_entity.id, "name": fac_entity.name})

        seen_casefold: set[str] = set()
        for r in (pub.get("roles") or []):
            name = (r.get("name") or "").strip()
            if not name or name.casefold() in seen_casefold:
                continue
            seen_casefold.add(name.casefold())
            write_faction_role(
                db, mode="create", world_id=world_id, faction_id=fac_entity.id,
                name=name, description=r.get("description"), max_holders=None,
                changed_by="creator",
            )
    return fac_id_map, committed_factions


def _commit_region_locations(
    locations_in: list[dict], accepted_locations: dict, root_local: Optional[str], db: Session,
) -> tuple[dict[str, str], list[dict]]:
    """Stage 2 — locations, dependency order (parent before child)."""
    loc_id_map: dict[str, str] = {}
    committed_locations: list[dict] = []
    remaining = [l for l in locations_in if l["local_id"] in accepted_locations]
    while remaining:
        ready = [
            l for l in remaining
            if (p := _region_resolve_location_parent(l, accepted_locations, root_local)) is None
            or p in loc_id_map
        ]
        if not ready:
            break  # cycle guard — should not happen on a well-formed draft
        for entry in ready:
            local_id = entry["local_id"]
            draft = entry["result"]["draft"]
            pub, sec = draft["public"], draft["secret"]
            subculture = dict(pub.get("subculture") or {})
            if sec.get("subculture_hidden"):
                subculture["hidden"] = sec["subculture_hidden"]
            parent_local = _region_resolve_location_parent(entry, accepted_locations, root_local)
            entity_data = {
                "type": "location",
                "name": pub.get("name"),
                "description": pub.get("description"),
            }
            ext_data = {
                "location_type": pub.get("location_type"),
                "access_level": pub.get("access_level") or None,
                "subculture": subculture or None,
                "parent_location_id": loc_id_map.get(parent_local) if parent_local else None,
            }
            loc_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data)
            loc_entity = _crud._create_entity_core(loc_body, db)
            loc_id_map[local_id] = loc_entity.id
            committed_locations.append({"local_id": local_id, "id": loc_entity.id, "name": loc_entity.name})
            remaining.remove(entry)
    return loc_id_map, committed_locations


def _commit_region_links(
    locations_in: list[dict], loc_id_map: dict, confirmed_links: dict,
    committed_locations: list[dict], committed_factions: list[dict],
    world_id: Optional[str], db: Session,
) -> tuple[list[dict], list[dict]]:
    """Stage 4 — confirmed judgment links (BRIEF-37, chantier 3)."""
    committed_locations_by_name = {
        c["name"].strip().lower(): c["id"] for c in committed_locations if c.get("name")
    }
    committed_factions_by_name = {
        c["name"].strip().lower(): c["id"] for c in committed_factions if c.get("name")
    }
    written_links: list[dict] = []
    unresolved_links: list[dict] = []
    for entry in locations_in:
        local_id = entry["local_id"]
        source_id = loc_id_map.get(local_id)
        sensed_links = entry["result"]["draft"]["secret"].get("sensed_links") or []
        for idx, link in enumerate(sensed_links):
            if not isinstance(link, dict):
                continue
            kind = link.get("kind")
            if kind not in ("connection", "faction"):
                continue  # parent/other stay display-only
            if not confirmed_links.get(f"{local_id}#{idx}"):
                continue  # default unconfirmed — creator opts in

            if source_id is None:
                unresolved_links.append({
                    "location_local_id": local_id, "kind": kind, "name": link.get("name"),
                    "reason": "Lieu source rejeté ou non commité",
                })
                continue

            target_id, reason = _region_resolve_link_target(
                db, world_id, link.get("name"), kind,
                committed_locations_by_name, committed_factions_by_name,
            )
            if target_id is None:
                unresolved_links.append({
                    "location_local_id": local_id, "kind": kind, "name": link.get("name"),
                    "reason": reason,
                })
                continue
            if target_id == source_id:
                unresolved_links.append({
                    "location_local_id": local_id, "kind": kind, "name": link.get("name"),
                    "reason": "Auto-lien ignoré",
                })
                continue

            if kind == "connection":
                write_relation(
                    db, mode="set", world_id=world_id,
                    entity_a_id=source_id, entity_b_id=target_id,
                    type="connects_to", value=50, direction="mutual",
                )
                written_links.append({
                    "location_local_id": local_id, "kind": kind, "type": "connects_to",
                    "entity_a_id": source_id, "entity_b_id": target_id,
                })
            else:  # kind == "faction" — controller is entity_a, asset is entity_b
                write_relation(
                    db, mode="set", world_id=world_id,
                    entity_a_id=target_id, entity_b_id=source_id,
                    type="controls", value=50, direction="a_to_b",
                )
                written_links.append({
                    "location_local_id": local_id, "kind": kind, "type": "controls",
                    "entity_a_id": target_id, "entity_b_id": source_id,
                })
    return written_links, unresolved_links


@router.post("/api/regions/commit")
def commit_region(
    body: RegionCommitBody,
    db: Session = Depends(get_session),
) -> dict:
    """Atomic region commit (BRIEF-36, chantier 2, E1).

    Creator-direct, NOT a proposed_mutation path; same no-canon-write-by-
    default neighbourhood as /api/regions/generate but this route DOES write
    canon. The region draft + accept/reject map are untrusted client-held
    state (re-sent, not server-persisted) — every reference and the whole
    cascade (parent rejection -> re-parent to root) is re-derived here from
    the raw `accepted` map, never trusted from the client's rendering.

    Calls the commit-free cores directly (`_crud._create_entity_core`) in
    dependency order — factions, then locations (root first) — against one
    shared session, with exactly one `db.commit()` at the end. Any
    exception rolls back the whole batch and returns {"ok": false, ...}; no
    half-committed region is ever observable.

    The structural skeleton is wired in stages 1-2: `parent_location_id` and
    each faction's role vocabulary (`write_faction_role`).

    Stage 3 (BRIEF-37, chantier 3) extends this same transaction with the
    CONFIRMED `sensed_links` judgment suggestions — only the two wirable
    kinds (`connection` -> `connects_to`, `faction` -> `controls`
    faction->location `direction="a_to_b"`); `parent` / `other` /
    `shared_with` stay display-only, exactly as chantier 2 left them.
    Confirm flags are advisory (`body.confirmed_links`); resolution
    (`_region_resolve_link_target`, S1) is server-authoritative — a
    rejected/uncommitted source or target, or a miss against both the
    just-committed entities and the DB, writes no relation and is recorded
    in the response's `links.unresolved` list instead. `write_relation` is
    commit-free, so phase 3 joins the SAME transaction with no extra commit.
    """
    region = body.region
    accepted = body.accepted
    confirmed_links = body.confirmed_links

    factions_in = region.get("factions") or []
    locations_in = region.get("locations") or []

    accepted_factions = {f["local_id"]: f for f in factions_in if accepted.get(f["local_id"], True)}
    accepted_locations = {l["local_id"]: l for l in locations_in if accepted.get(l["local_id"], True)}
    root_local = next((l["local_id"] for l in locations_in if l.get("parent_local_id") is None), None)

    world_id = _crud._world_id(db)
    committed = {"factions": [], "locations": []}

    try:
        _fac_id_map, committed["factions"] = _commit_region_factions(factions_in, accepted_factions, world_id, db)
        loc_id_map, committed["locations"] = _commit_region_locations(
            locations_in, accepted_locations, root_local, db,
        )
        written_links, unresolved_links = _commit_region_links(
            locations_in, loc_id_map, confirmed_links,
            committed["locations"], committed["factions"], world_id, db,
        )

        db.commit()
    except HTTPException as exc:
        db.rollback()
        return {"ok": False, "error": str(exc.detail)}
    except IntegrityError as exc:
        db.rollback()
        return {"ok": False, "error": f"Database integrity error: {exc}"}
    except Exception as exc:  # noqa: BLE001 — atomicity: any failure rolls back, never half-commits
        db.rollback()
        return {"ok": False, "error": str(exc)}

    return {"ok": True, "committed": committed, "links": {"written": written_links, "unresolved": unresolved_links}}
