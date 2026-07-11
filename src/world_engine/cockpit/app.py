"""Cockpit — local review web UI for World Engine.

Endpoints
---------
GET  /                                serve index.html
GET  /api/conversations               list conversations (id, session, location,
                                       status, started_at, message_count)
GET  /api/conversations/{id}          transcript with resolved speaker names
POST /api/conversations/{id}/analyze  (re)generate proposed mutations via Ollama
GET  /api/mutations?status=proposed   list proposed_mutation rows
POST /api/mutations/{id}/reject       mark rejected; no canon write
POST /api/mutations/{id}/approve      apply to canon; on failure set 'approved'
POST /api/mutations/batch-review      approve/reject several proposed rows,
                                       sequentially, through the same paths
POST /api/world-tick                  scoped off-screen NPC advancement;
                                       writes proposed_mutation rows only
GET  /api/creations/pending           approved, unrealized entity_creation
                                       germs (TICK or CONVERSATION source)
POST /api/creations/{id}/generate     pure draft generation from a germ;
                                       writes nothing (BRIEF-0019-a)

Security
--------
- uvicorn is bound to 127.0.0.1 only (enforced in scripts/cockpit.py).
- No authentication needed for this solo local tool.
- No CORS opened to any origin.
- No external calls except the local Ollama endpoint via the existing client.
"""

from __future__ import annotations

import enum
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .. import ollama_client
from ..entity_author import build_world_roster as _build_world_roster
from ..entity_author import generate_agenda_draft as _generate_agenda_draft
from ..entity_author import generate_entity_draft as _generate_entity_draft
from ..entity_author import generate_event_draft as _generate_event_draft
from ..entity_author import generate_npc_goals as _generate_npc_goals
from ..entity_author import generate_player_draft as _generate_player_draft
from ..entity_author import generate_skill_catalogue_draft as _generate_skill_catalogue_draft
from ..entity_author import generate_world_draft as _generate_world_draft
from ..region_author import generate_region_draft as _generate_region_draft
from ..region_author import generate_region_manifest as _generate_region_manifest
from ..gathering import close_open_memberships
from ..gathering import enter_location as _enter_location
from ..gathering import migrate_npc as _migrate_npc
from ..analyzer import analyze_overhearing as _analyze_overhearing
from ..analyzer import analyze_window as _analyze_window
from ..tick import run_world_tick as _run_world_tick
from ..prompt_registry import PROMPT_REGISTRY, effective_model
from ..prompt_store import current_prompt
from ..context import (
    _SAFE_SUBCULTURE_KEYS,
    active_signposts,
    assemble_mj_context,
    assemble_npc_context,
    format_inventory_line,
    format_item_list_for_interpretation,
    format_mj_context,
)
from ..db import engine, get_session
from ..ledger import get_balance as _get_balance
from ..models import (
    Agenda,
    AgendaStep,
    BASE_SKILL_DOMAINS,
    Character,
    Conversation,
    ConversationMessage,
    DiscoverableDetail,
    Entity,
    Event,
    Faction,
    FactionMembership,
    Gathering,
    GatheringMember,
    Item,
    Knowledge,
    Location,
    NpcGoal,
    PromptTemplate,
    ProposedMutation,
    Relation,
    Session as GameSession,
    Skill,
    SkillDefinition,
    User,
    Visit,
    World,
)
from ..resolution import resolve_physical
from ..writes import (
    KNOWLEDGE_LEVELS,
    _find_relation_pair,
    delete_world_cascade as _delete_world_cascade,
    knowledge_level_rank,
    write_agenda,
    write_agenda_status,
    write_agenda_step,
    write_agenda_step_status,
    write_character_location,
    write_event,
    write_faction_role_capacities,
    write_goal_agenda_link,
    write_knowledge,
    write_ledger_entry,
    write_membership,
    write_npc_goal,
    write_npc_goal_status,
    write_relation,
)
from . import crud as _crud

_INDEX_HTML = Path(__file__).parent / "index.html"
_log = logging.getLogger(__name__)

# Vendored JS dependencies (BRIEF-0023-a, H1): one whitelisted file per
# entry, no StaticFiles mount — that generalization waits for a second
# vendored asset.
_VENDOR_DIR = Path(__file__).parent / "vendor"
_VENDOR_WHITELIST = {"cytoscape-3.34.0.min.js"}

app = FastAPI(title="World Engine Cockpit", docs_url=None, redoc_url=None)
app.include_router(_crud.router)


class EntityGenerateBody(BaseModel):
    entity_type: str
    brief: str


def _generate_draft_with_l1(entity_type: str, brief: str, db: Session) -> dict:
    """Shared write-free generation core (BRIEF-0019-a item 4, RECON F2) —
    both `/api/entities/generate` and `/api/creations/{mutation_id}/generate`
    call this instead of `generate_entity_draft` directly, so there is ONE
    generation path and L1 goals come for free on either route. Writes
    nothing; never raises (see `entity_author.generate_entity_draft`).

    L1 (BRIEF-0013-b): on a successful character draft, also calls
    generate_npc_goals with the draft's public fields and the resolved
    faction's `goals` (read-only query, None when unaffiliated) and merges
    the result as `draft["public"]["goals"]`. A goal-generation failure never
    fails the draft — it's appended to `notes` and the character draft ships
    without goals.
    """
    result = _generate_entity_draft(entity_type, brief, db)
    if entity_type == "character" and result.get("ok"):
        pub = result["draft"]["public"]
        faction_goals = None
        faction_id = pub.get("faction_id")
        if faction_id:
            faction = db.get(Faction, faction_id)
            faction_goals = faction.goals if faction else None
        goals_result = _generate_npc_goals(
            pub.get("name", ""), pub.get("description", ""), pub.get("backstory", ""), faction_goals, db
        )
        if goals_result.get("ok"):
            pub["goals"] = {"long": goals_result.get("long", ""), "shorts": goals_result.get("shorts", [])}
        else:
            result.setdefault("notes", []).append(
                f"Génération des objectifs échouée : {goals_result.get('error')}"
            )
    return result


@app.post("/api/entities/generate")
def generate_entity(
    body: EntityGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI draft generator (BRIEF-24; L1 goals, BRIEF-0013-b).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — keeping it in a separate router makes
    that property legible. Performs no write itself. Returns
    {"ok": false, "error": ...} (never a 500) on any failure — see
    entity_author.generate_entity_draft.
    """
    return _generate_draft_with_l1(body.entity_type, body.brief, db)


# ── Two-stage entity creation realization (TICKET-0019, BRIEF-0019-a) ───────
# The tick (or, dormantly, a conversation — RECON F6) proposes a THIN germ;
# creator approval parks it (`approve_mutation`'s short-circuit above); these
# two routes serve the Création tab's "Créations en attente" strip — one pure
# read, one pure write-free generation. Realization itself (the actual canon
# write) happens only in crud.py's create_entity, via its optional
# `mutation_id` linkage.

_ENTITY_CREATION_TYPES = frozenset({"character", "location", "faction"})

_ENTITY_CREATION_INTROS: dict[str, str] = {
    "character": "Nouveau personnage",
    "location": "Nouveau lieu",
    "faction": "Nouvelle faction",
}


def _compose_entity_creation_brief(payload: dict) -> str:
    """French prose brief for the pure generation chain (item 4) — weaves
    name + concept + anchor into 2-4 sentences. `anchor` already carries any
    scope-situating prose the model proposed (near/within/serves — RECON F7),
    so no extra lookup against the mutation's tick/scope is needed. Tolerant
    of the dormant conversation channel's shapeless payload (RECON F6):
    name/concept fall back across `name|title` and `concept|description|
    content`.
    """
    entity_type = str(payload.get("entity_type") or "").strip().casefold()
    intro = _ENTITY_CREATION_INTROS.get(entity_type, "Nouvelle entité")
    name = str(payload.get("name") or payload.get("title") or "").strip()
    concept = str(
        payload.get("concept") or payload.get("description") or payload.get("content") or ""
    ).strip()
    anchor = str(payload.get("anchor") or "").strip()

    sentences = [f"{intro} : {name}." if name else f"{intro}."]
    if concept:
        sentences.append(concept if concept.endswith((".", "!", "?")) else f"{concept}.")
    if anchor:
        sentences.append(anchor if anchor.endswith((".", "!", "?")) else f"{anchor}.")
    return " ".join(sentences)


@app.get("/api/creations/pending")
def list_pending_creations(db: Session = Depends(get_session)) -> list[dict]:
    """Approved-but-unrealized entity_creation germs, ALL sources — tick AND
    the dormant conversation channel join the same list (0017-style
    awakening, RECON F6). Query: mutation_type == entity_creation,
    status == approved, payload lacks created_entity_id.
    """
    rows = db.exec(
        select(ProposedMutation)
        .where(
            ProposedMutation.mutation_type == "entity_creation",
            ProposedMutation.status == "approved",
        )
        .order_by(ProposedMutation.proposed_at.desc())
    ).all()

    items: list[dict] = []
    for mut in rows:
        payload = mut.payload if isinstance(mut.payload, dict) else {}
        if "created_entity_id" in payload:
            continue
        entity_type = str(payload.get("entity_type") or "").strip().casefold()
        items.append({
            "mutation_id": mut.id,
            "source": "tick" if mut.tick_id else "conversation",
            "proposed_at": mut.proposed_at.isoformat() if mut.proposed_at else None,
            "name": str(payload.get("name") or payload.get("title") or "").strip(),
            "concept": str(
                payload.get("concept") or payload.get("description") or payload.get("content") or ""
            ).strip(),
            "anchor": payload.get("anchor"),
            "entity_type": entity_type if entity_type in _ENTITY_CREATION_TYPES else None,
        })
    return items


@app.post("/api/creations/{mutation_id}/generate")
def generate_creation_draft(mutation_id: str, db: Session = Depends(get_session)) -> dict:
    """Realization generation (item 4) — pure, writes nothing; reuses the
    same write-free chain as `/api/entities/generate` (+ L1 goals) via
    `_generate_draft_with_l1`. Regenerating later is free: an abandoned
    draft costs nothing because the mutation stays 'approved' until
    create_entity's guarded linkage flips it.
    """
    mut = db.get(ProposedMutation, mutation_id)
    if mut is None or mut.mutation_type != "entity_creation" or mut.status != "approved":
        raise HTTPException(409, "Mutation is not an approved, unrealized entity_creation germ")

    payload = mut.payload if isinstance(mut.payload, dict) else {}
    if "created_entity_id" in payload:
        raise HTTPException(409, "This germ has already been realized")

    entity_type = str(payload.get("entity_type") or "").strip().casefold()
    if entity_type not in _ENTITY_CREATION_TYPES:
        raise HTTPException(409, "Germ has no valid entity_type — cannot generate")

    brief = _compose_entity_creation_brief(payload)
    result = _generate_draft_with_l1(entity_type, brief, db)
    return {
        "ok": result.get("ok", False),
        "draft": result.get("draft"),
        "notes": result.get("notes", []),
        "error": result.get("error"),
        "mutation_id": mutation_id,
        "entity_type": entity_type,
    }


@app.get("/api/prompts/preview/npc_dialogue")
def preview_prompt_npc_dialogue(
    npc_id: str = Query(...),
    pc_id: str = Query(...),
    db: Session = Depends(get_session),
) -> dict:
    """Assembled dry-run preview (BRIEF-0008-b, C3) — the exact system prompt
    the real conversation-start path would build. Zero model calls, zero
    writes: no `conversation` row, no `injected_context` snapshot, no
    `change_history`. Reuses the real `assemble_npc_context` (never a
    reimplementation) and the extracted `_npc_dialogue_system_prompt`
    construction, so structural secret exclusion traverses the preview
    intact. Deliberately NOT in crud.py — same no-canon-write reasoning as
    `POST /api/entities/generate`.
    """
    npc_entity = db.get(Entity, npc_id)
    if npc_entity is None:
        raise HTTPException(status_code=404, detail=f"NPC {npc_id!r} not found")
    pc_entity = db.get(Entity, pc_id)
    if pc_entity is None:
        raise HTTPException(status_code=404, detail=f"Interlocutor {pc_id!r} not found")
    npc_char = db.get(Character, npc_id)
    location_id = npc_char.current_location_id if npc_char else None
    if not location_id:
        raise HTTPException(status_code=400, detail=f"NPC {npc_id!r} has no current location")

    world_id = _crud._world_id(db)
    spec = PROMPT_REGISTRY["npc_dialogue"]
    rows = db.exec(select(PromptTemplate).where(PromptTemplate.usage == "npc_dialogue")).all()
    behaviour = _crud._effective_prompt_row(rows, spec.world_scoped, world_id)
    if behaviour is None:
        raise HTTPException(status_code=503, detail="No active 'npc_dialogue' prompt template found.")

    assembled_context = assemble_npc_context(npc_id, pc_id, location_id, db)
    behaviour_version = current_prompt(db, behaviour)
    system_prompt = _npc_dialogue_system_prompt(behaviour_version.system_prompt, assembled_context)
    return {
        "prompt_template_id": behaviour.id,
        "npc_id": npc_id,
        "pc_id": pc_id,
        "location_id": location_id,
        "system_prompt": system_prompt,
    }


@app.get("/api/prompts/preview/player_narration")
def preview_prompt_player_narration(
    pc_id: str = Query(...),
    db: Session = Depends(get_session),
) -> dict:
    """Assembled dry-run preview (BRIEF-0008-b, C3) — the MJ context a
    `player_narration` turn actually renders. Zero model calls, zero writes.
    Reuses the real `assemble_mj_context` + `format_mj_context` (never a
    reimplementation) — the player's own knowledge (including `is_secret`
    rows) is present (MJ perception boundary, not the NPC secret boundary);
    other entities' secrets are excluded by the same query construction as
    live play.
    """
    pc_char = db.get(Character, pc_id)
    if pc_char is None or pc_char.character_type != "player":
        raise HTTPException(status_code=400, detail=f"{pc_id!r} is not a player character")
    location_id = pc_char.current_location_id
    if not location_id:
        raise HTTPException(status_code=400, detail="Player has no current location")

    world_id = _crud._world_id(db)
    spec = PROMPT_REGISTRY["player_narration"]
    rows = db.exec(select(PromptTemplate).where(PromptTemplate.usage == "player_narration")).all()
    mj_template = _crud._effective_prompt_row(rows, spec.world_scoped, world_id)
    if mj_template is None:
        raise HTTPException(status_code=503, detail="No active 'player_narration' prompt template found.")

    mj_context = assemble_mj_context(db, pc_id, location_id)
    mj_version = current_prompt(db, mj_template)
    return {
        "prompt_template_id": mj_template.id,
        "pc_id": pc_id,
        "location_id": location_id,
        "system_prompt": mj_version.system_prompt,
        "mj_context_rendered": format_mj_context(mj_context),
    }


class WorldGenerateBody(BaseModel):
    brief: str


@app.post("/api/worlds/generate")
def generate_world(
    body: WorldGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI world-premise draft generator (BRIEF-47).

    Deliberately NOT in crud.py and NOT routed through generate_entity:
    World has no entity_id FK, so it is not an entity type. Writes
    nothing — delegates only to entity_author.generate_world_draft.
    Returns {"ok": false, "error": ...} (never a 500) on any failure.
    """
    return _generate_world_draft(body.brief, db)


class PlayerGenerateBody(BaseModel):
    brief: str


@app.post("/api/characters/player/generate")
def generate_player(
    body: PlayerGenerateBody, db: Session = Depends(get_session)
) -> dict:
    """Creator-side AI PC-draft generator (BRIEF-52).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_player_draft. Returns {"ok": false, "error": ...}
    (never a 500) on any failure.
    """
    return _generate_player_draft(body.brief, db)


class SkillCatalogueGenerateBody(BaseModel):
    brief: str


@app.post("/api/skill-definitions/generate")
def generate_skill_catalogue(
    body: SkillCatalogueGenerateBody, db: Session = Depends(get_session)
) -> dict:
    """Creator-side AI skill-catalogue draft generator (BRIEF-56,
    D2-attach-b/D2-template-b).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_skill_catalogue_draft. Returns
    {"ok": false, "error": ...} (never a 500) on any failure. The creator
    edits/accepts the proposed skills through the existing creator-CRUD
    `POST /api/skill-definitions` (crud.py) — never written here.
    """
    return _generate_skill_catalogue_draft(body.brief, db)


class AgendaGenerateBody(BaseModel):
    owner_entity_id: str
    brief: str


@app.post("/api/agendas/generate")
def generate_agenda(
    body: AgendaGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI agenda-draft assistant (TICKET-0021, BRIEF-0021-b,
    B1/C1/D1).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_agenda_draft. Server-side D1 resolution mirrors
    write_agenda's owner rule so the assistant can never draft for an owner
    the create would reject: 404/422 if the entity is missing, inactive, or
    not `faction`/`character`. owner_context is built from PUBLIC fields
    only (faction: description + Faction.philosophy; character: description
    + Character.backstory) — secrets stay structurally excluded: no
    `knowledge` row, no `character.secrets`, no `internal_tensions` is ever
    read here. Returns {"ok": false, "error": ...} (never a 500) on any
    failure.
    """
    owner = db.get(Entity, body.owner_entity_id)
    if owner is None:
        raise HTTPException(404, f"Entity {body.owner_entity_id!r} not found")
    if owner.status != "active" or owner.type not in ("faction", "character"):
        raise HTTPException(422, "owner_entity_id must be an active faction or character")

    if owner.type == "faction":
        owner_kind = "faction"
        faction = db.get(Faction, owner.id)
        philosophy = f"Philosophie : {faction.philosophy}" if faction and faction.philosophy else None
        parts = [p for p in (owner.description, philosophy) if p]
    else:
        owner_kind = "personnage"
        character = db.get(Character, owner.id)
        backstory = f"Passé : {character.backstory}" if character and character.backstory else None
        parts = [p for p in (owner.description, backstory) if p]
    owner_context = "\n".join(parts) if parts else "(aucune description)"

    return _generate_agenda_draft(owner_kind, owner.name, owner_context, body.brief, db)


class EventGenerateBody(BaseModel):
    brief: str
    location_id: Optional[str] = None


@app.post("/api/events/generate")
def generate_event(
    body: EventGenerateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI event-draft assistant (TICKET-0022, BRIEF-0022-b,
    I2/J3).

    Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
    and this route writes nothing — delegates only to
    entity_author.generate_event_draft. `location_id`, when supplied, must
    resolve to an active `location` entity in the active world (the same
    predicate as `_apply_mutation`'s `event_creation` branch); it then wins
    outright over the model's own location proposal. `location_context` is
    the location's `name` + `description` only — public fields, never
    `internal_name`, never `metadata`. The J3 roster
    (`entity_author.build_world_roster`) is public-only, filtered in SQL.
    Returns {"ok": false, "error": ...} (never a 500) on any failure.
    """
    brief = (body.brief or "").strip()
    if not brief:
        raise HTTPException(422, "Intention requise.")

    world_id = _crud._world_id(db)

    location_hint = ""
    location_context = ""
    if body.location_id:
        location = db.get(Entity, body.location_id)
        if (
            location is None
            or location.type != "location"
            or location.status != "active"
            or location.world_id != world_id
        ):
            raise HTTPException(422, f"location_id {body.location_id!r} is not an active location in this world")
        location_hint = location.name
        parts = [p for p in (location.name, location.description) if p]
        location_context = "\n".join(parts)

    roster = _build_world_roster(db, world_id)

    return _generate_event_draft(brief, location_hint, location_context, roster, db)


class RegionGenerateBody(BaseModel):
    brief: str


class RegionBuildBody(BaseModel):
    manifest: dict[str, Any]


@app.post("/api/regions/manifest")
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


@app.post("/api/regions/generate")
def generate_region(
    body: RegionBuildBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-side AI region draft generator — Phase B (BRIEF-34, chantier 1;
    repurposed to accept a manifest by BRIEF-38).

    Deliberately NOT in crud.py, same neighbourhood as /api/entities/generate:
    crud.py is a sanctioned canon-write path and this route writes nothing.
    Calls only generate_region_draft, which composes generate_entity_draft
    across factions/locations/NPCs and writes no canon itself. The manifest
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


@app.post("/api/regions/commit")
def commit_region(
    body: RegionCommitBody,
    db: Session = Depends(get_session),
) -> dict:
    """Atomic region commit (BRIEF-36, chantier 2, E1).

    Creator-direct, NOT a proposed_mutation path; same no-canon-write-by-
    default neighbourhood as /api/regions/generate but this route DOES write
    canon. The region draft + accept/reject map are untrusted client-held
    state (re-sent, not server-persisted) — every reference and the whole
    cascade (faction rejection -> NPC unaffiliated, host-location rejection
    -> NPC dropped, parent rejection -> re-parent to root) is re-derived here
    from the raw `accepted` map, never trusted from the client's rendering.

    Calls the commit-free cores directly (`_crud._create_entity_core`,
    `_crud._create_knowledge_core`) in dependency order — factions, then
    locations (root first), then placeable NPCs + their knowledge — against
    one shared session, with exactly one `db.commit()` at the end. Any
    exception rolls back the whole batch and returns {"ok": false, ...}; no
    half-committed region is ever observable.

    The structural skeleton is wired in stages 1-3: `parent_location_id`,
    the primary PUBLIC faction_membership (via `extension.faction_id`), and
    `current_location_id`. No `is_secret=True` membership is ever written.

    Stage 4 (BRIEF-37, chantier 3) extends this same transaction with the
    CONFIRMED `sensed_links` judgment suggestions — only the two wirable
    kinds (`connection` -> `connects_to`, `faction` -> `controls`
    faction->location `direction="a_to_b"`); `parent` / `other` /
    `shared_with` stay display-only, exactly as chantier 2 left them.
    Confirm flags are advisory (`body.confirmed_links`); resolution
    (`_region_resolve_link_target`, S1) is server-authoritative — a
    rejected/uncommitted source or target, or a miss against both the
    just-committed entities and the DB, writes no relation and is recorded
    in the response's `links.unresolved` list instead. `write_relation` is
    commit-free, so phase 4 joins the SAME transaction with no extra commit.
    """
    region = body.region
    accepted = body.accepted
    confirmed_links = body.confirmed_links

    factions_in = region.get("factions") or []
    locations_in = region.get("locations") or []
    npcs_in = region.get("npcs") or []

    accepted_factions = {f["local_id"]: f for f in factions_in if accepted.get(f["local_id"], True)}
    accepted_locations = {l["local_id"]: l for l in locations_in if accepted.get(l["local_id"], True)}
    root_local = next((l["local_id"] for l in locations_in if l.get("parent_local_id") is None), None)

    fac_id_map: dict[str, str] = {}
    loc_id_map: dict[str, str] = {}
    npc_id_map: dict[str, str] = {}
    committed = {"factions": [], "locations": [], "npcs": []}
    world_id = _crud._world_id(db)

    try:
        # ── Stage 1 — factions ───────────────────────────────────────────
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
            roles = [
                {"name": r["name"].strip(), "description": r.get("description") or ""}
                for r in (pub.get("roles") or [])
                if isinstance(r, dict) and (r.get("name") or "").strip()
            ]
            if roles:
                entity_data["metadata"] = {"roles": roles}
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
            committed["factions"].append({"local_id": local_id, "id": fac_entity.id, "name": fac_entity.name})

        # ── Stage 2 — locations, dependency order (parent before child) ──
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
                committed["locations"].append({"local_id": local_id, "id": loc_entity.id, "name": loc_entity.name})
                remaining.remove(entry)

        # ── Stage 3 — NPCs (accepted + placeable only) + their knowledge ─
        for entry in npcs_in:
            local_id = entry["local_id"]
            if not accepted.get(local_id, True):
                continue
            host_local = entry.get("location_local_id")
            if host_local not in loc_id_map:
                continue  # host location rejected/missing — NPC is unplaceable, dropped

            draft = entry["result"]["draft"]
            pub, sec = draft["public"], draft["secret"]
            entity_data = {
                "type": "character",
                "name": pub.get("name"),
                "description": pub.get("description"),
            }
            if pub.get("physical_tier") is not None:
                entity_data["metadata"] = {"physical_tier": pub["physical_tier"]}
            ext_data: dict[str, Any] = {
                "character_type": "npc",
                "appearance": pub.get("appearance"),
                "backstory": pub.get("backstory"),
                "aversion": pub.get("aversion"),
                "current_location_id": loc_id_map[host_local],
                "secrets": json.dumps(sec["creator_meta"]) if sec.get("creator_meta") is not None else None,
            }
            faction_local = entry.get("faction_local_id")
            if faction_local and faction_local in fac_id_map:
                ext_data["faction_id"] = fac_id_map[faction_local]

            npc_body = _crud.EntityWriteBody(entity=entity_data, extension=ext_data)
            npc_entity = _crud._create_entity_core(npc_body, db)
            npc_id_map[local_id] = npc_entity.id
            committed["npcs"].append({"local_id": local_id, "id": npc_entity.id, "name": npc_entity.name})

            for k in (sec.get("knowledge") or []):
                k_body = _crud.KnowledgeWriteBody(
                    subject=k.get("subject"),
                    level=k.get("level"),
                    content=k.get("content"),
                    source=None,
                    is_incorrect=False,
                    is_secret=True,
                    share_threshold=50,
                )
                _crud._create_knowledge_core(npc_entity.id, k_body, db)

            # BRIEF-0013-b (G1): the goal block attached at draft time
            # (region_author.generate_region_draft) writes here, in the SAME
            # transaction as the NPC — malformed or absent writes nothing for
            # that NPC, never blocks the rest of the commit.
            goals = pub.get("goals")
            if isinstance(goals, dict):
                long_desc = (goals.get("long") or "").strip()
                if long_desc:
                    write_npc_goal(
                        db, world_id=world_id, npc_id=npc_entity.id,
                        description=long_desc, horizon="long", changed_by="creator",
                    )
                for short_desc in (goals.get("shorts") or []):
                    short_desc = (short_desc or "").strip()
                    if short_desc:
                        write_npc_goal(
                            db, world_id=world_id, npc_id=npc_entity.id,
                            description=short_desc, horizon="short", changed_by="creator",
                        )

        # ── Stage 4 — confirmed judgment links (BRIEF-37, chantier 3) ────
        # world_id computed once, above, before Stage 3 (BRIEF-0013-b needs
        # it there too — same source, no re-derivation).
        committed_locations_by_name = {
            c["name"].strip().lower(): c["id"] for c in committed["locations"] if c.get("name")
        }
        committed_factions_by_name = {
            c["name"].strip().lower(): c["id"] for c in committed["factions"] if c.get("name")
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


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _mutation_dict(m: ProposedMutation) -> dict:
    return {
        "id": m.id,
        "mutation_type": m.mutation_type,
        "target_table": m.target_table,
        "target_id": m.target_id,
        "payload": m.payload,
        "rationale": m.rationale,
        "status": m.status,
        "creator_notes": m.creator_notes,
        "proposed_by": m.proposed_by,
        "source_type": m.source_type,
        "conversation_id": m.conversation_id,
        "pass_play_id": m.pass_play_id,
        "tick_id": m.tick_id,
        "proposed_at": _iso(m.proposed_at),
        "reviewed_at": _iso(m.reviewed_at),
        "applied_at": _iso(m.applied_at),
    }


# ── Duplicate-application guard ───────────────────────────────────────────────

def _find_event_duplicate(payload: dict, world_id: str, db: Session) -> Optional[str]:
    """Canon-existence duplicate check for `event_creation` (TICKET-0017,
    BRIEF-0017-a): duplicate iff an `Event` row already exists in this world
    with the same normalized (casefold/strip) title AND the same
    `location_id` (NULL matches NULL) — never tick_id/conversation equality
    (0014 guard doctrine). Applies regardless of source (tick-sourced or
    conversation-sourced): a re-run tick or a --force re-analysis must not
    double an event either way.
    """
    title = _normalize_goal_text(payload.get("title"))
    location_id = payload.get("location_id")
    candidates = db.exec(
        select(Event).where(Event.world_id == world_id, Event.location_id == location_id)
    ).all()
    for e in candidates:
        if _normalize_goal_text(e.title) == title:
            return (
                f"event_creation for title {payload.get('title')!r} already exists "
                "at this location."
            )
    return None


def _find_applied_duplicate(
    mut: ProposedMutation,
    db: Session,
) -> Optional[str]:
    """Return a warning string if an equivalent mutation was already applied for
    this conversation; return None if it is safe to apply.

    This guard prevents double-application when --force re-generates proposals
    after a previous round already applied one.  Only mutations from the SAME
    conversation are compared — the same knowledge acquired in two different
    conversations is not a duplicate.

    Match keys (design choice):
    - new_knowledge : same conversation_id + entity_id + subject.
        Rationale: (entity, subject) is the identity of a fact; applying twice
        creates duplicate knowledge rows and inflates NPC context.
    - status_change : same conversation_id + entity_id.
        Rationale: two status changes on the same entity in one conversation
        are unlikely to both be correct; surface for creator review.

    relation_change is intentionally EXCLUDED from this guard.
    Relation deltas ACCUMULATE — two independent +5 events sum to +10 and must
    both apply. These come only from per-turn immediate flags (one per turn),
    so they are never re-proposed by the final pass and can never be
    double-applied by --force.

    item_update is also intentionally EXCLUDED (neither branch above matches
    it, so it falls through unguarded): it is a state transition (equipped
    true/false), and a legitimate draw→stow→draw sequence within one
    conversation must apply each time. Dormant since BRIEF-08/D2a.1 — no
    live code path produces `item_update` anymore (see "Auto-applied
    mutations" in ARCHITECTURE_DECISIONS.md).

    knowledge_change is also intentionally EXCLUDED. Successive legitimate
    upgrades in one conversation (e.g. rumor → partial, then later
    partial → knows) must both apply — the monotone re-check inside
    _apply_mutation ("level already >= proposed") is the correct guard, not
    an identity-based duplicate check.

    resource_change is also intentionally EXCLUDED (BRIEF-19). Its money leg
    accumulates exactly like relation_change — two genuine purchases in one
    conversation must both apply. Its knowledge leg IS idempotent, but that
    guard lives inside the resource_change branch itself
    (_knowledge_leg_already_applied, guard 4c), not here — this generic
    guard must never be extended to pattern-match the whole mutation.

    goal_change IS included (TICKET-0013, BRIEF-0013-c) — the opposite
    asymmetry from knowledge_change, deliberately: a repeated identical
    knowledge upgrade across successive windows is legitimate (rumor ->
    partial -> knows), but a repeated identical goal event (the same goal,
    same action) within ONE conversation is not — a goal is completed,
    abandoned, or created once, not twice in the same scene. Match key:
    same conversation_id + action + normalized goal text.

    TICK SCOPE (TICKET-0014, BRIEF-0014-b, Y2/F2): a tick-sourced mutation
    (`conversation_id IS NULL`, `tick_id` set) never reaches the branches
    above — a re-run tick gets a NEW tick_id every time, so comparing WITHIN
    one tick_id would miss exactly the cross-run duplicates this guard
    exists for. Instead it asks the CANON directly, re-run-proof AND
    revival-safe (a closed goal reopened via creator CRUD is a NEW row, per
    0013 doctrine, and must be allowed to re-apply):
    - goal_change with action == "create_short": duplicate iff an ACTIVE
      NpcGoal already exists for this NPC whose normalized description
      equals the proposal's. complete/abandon get NO guard here — the apply
      branch's exactly-one-active-match requirement is already the correct
      gate for those.
    - new_knowledge: duplicate iff a Knowledge row already exists for
      (entity_id, subject).
    - relation_change: NO guard, same accumulating-deltas doctrine as the
      conversation-sourced branch above — a double delta from a re-run tick
      is visible in the queue and the creator's to judge, never blocked.

    EVENT_CREATION (TICKET-0017, BRIEF-0017-a): both the tick-sourced branch
    below AND the conversation-sourced branch further down route through
    `_find_event_duplicate` — the SAME canon-existence check (title +
    location_id, this world) regardless of source, so neither a re-run tick
    nor a --force re-analysis can double an event.

    AGENDA_CREATION (TICKET-0018, BRIEF-0018-a) is tick-sourced only (the
    creator's own CRUD create route needs no such guard — a human choosing
    to author two similarly-titled agendas is not a bug). Duplicate iff an
    ACTIVE agenda already exists for the proposal's owner with the same
    normalized title — EXCEPT for a `character` owner (TICKET-0020,
    BRIEF-0020-b), where ANY active agenda is a duplicate (the
    one-active-personal-agenda invariant makes title irrelevant). AGENDA_
    STEP_CHANGE gets NO clause here by design — the apply branch's
    active-status stale guard (canon-existence, 0014 doctrine) is strictly
    stronger (0015 F6 argument).

    AGENDA_DELEGATION (TICKET-0020, BRIEF-0020-b) is tick-sourced only
    (faction scope). Duplicate iff an ACTIVE goal with the same normalized
    text already exists for the target NPC — the same rule as goal_change's
    create_short guard below, applied here because delegation writes a goal
    too.
    """
    if not mut.conversation_id:
        if not mut.tick_id:
            return None

        payload = mut.payload if isinstance(mut.payload, dict) else {}

        if mut.mutation_type == "goal_change" and payload.get("action") == "create_short":
            normalized = _normalize_goal_text(payload.get("goal"))
            candidates = db.exec(
                select(NpcGoal).where(NpcGoal.npc_id == payload.get("npc_id"), NpcGoal.status == "active")
            ).all()
            if any(_normalize_goal_text(g.description) == normalized for g in candidates):
                return (
                    f"goal_change (create_short) for goal {payload.get('goal')!r} already exists "
                    f"as an active goal for this NPC."
                )
            return None

        if mut.mutation_type == "new_knowledge":
            existing = db.exec(
                select(Knowledge).where(
                    Knowledge.entity_id == payload.get("entity_id"),
                    Knowledge.subject == payload.get("subject"),
                )
            ).first()
            if existing is not None:
                return (
                    f"new_knowledge for entity {str(payload.get('entity_id',''))[:8]}… "
                    f"subject={payload.get('subject')!r} already exists as a knowledge row."
                )
            return None

        if mut.mutation_type == "npc_move":
            # Mirrors the apply branch's stale-from gate (RECON-0015 F6): one
            # canon check covers duplicate re-approval, cross-run tick
            # duplicates, AND the world having moved since the proposal — and
            # correctly ALLOWS a later legitimate A->B->A move.
            character = db.get(Character, payload.get("npc_id"))
            if character is not None and character.current_location_id != payload.get("from_location_id"):
                return (
                    f"npc_move for NPC {str(payload.get('npc_id',''))[:8]}… — NPC no longer at "
                    f"the proposal's origin (world moved since the tick)."
                )
            return None

        if mut.mutation_type == "event_creation":
            return _find_event_duplicate(payload, mut.world_id, db)

        if mut.mutation_type == "agenda_creation":
            # Canon-existence (TICKET-0018, BRIEF-0018-a): duplicate iff an
            # ACTIVE agenda already exists for this owner with the same
            # normalized title. agenda_step_change gets NO guard here — the
            # apply branch's active-status stale guard is strictly stronger
            # (0015 F6 argument: it also catches duplicate approval and
            # creator-moved-since, which a title/owner key alone would not).
            #
            # Character owner (TICKET-0020, BRIEF-0020-b): the guard widens
            # to ANY active agenda, not just a same-title one — the
            # one-active-personal-agenda invariant means a second creation
            # for the same NPC is always a duplicate, regardless of title.
            # Faction owners keep the same-title-only guard, unchanged.
            owner_id = payload.get("owner_entity_id")
            owner = db.get(Entity, owner_id)
            if owner is not None and owner.type == "character":
                existing_personal = db.exec(
                    select(Agenda).where(
                        Agenda.owner_entity_id == owner_id,
                        Agenda.status == "active",
                    )
                ).first()
                if existing_personal is not None:
                    return (
                        f"agenda_creation for NPC {str(owner_id)[:8]}… already holds an active "
                        f"agenda ({existing_personal.title!r})."
                    )
                return None

            normalized = _normalize_goal_text(payload.get("title"))
            candidates = db.exec(
                select(Agenda).where(
                    Agenda.owner_entity_id == owner_id,
                    Agenda.status == "active",
                )
            ).all()
            if any(_normalize_goal_text(a.title) == normalized for a in candidates):
                return (
                    f"agenda_creation for title {payload.get('title')!r} already exists "
                    "as an active agenda for this owner."
                )
            return None

        if mut.mutation_type == "agenda_delegation":
            # Reuse the create_short duplicate rule (item 4 of the brief):
            # an ACTIVE goal with the same normalized text on that NPC is a
            # duplicate — mirrors goal_change's own create_short guard
            # further down, applied here since agenda_delegation is
            # tick-sourced only (no conversation_id branch exists for it).
            normalized = _normalize_goal_text(payload.get("goal"))
            candidates = db.exec(
                select(NpcGoal).where(NpcGoal.npc_id == payload.get("npc_id"), NpcGoal.status == "active")
            ).all()
            if any(_normalize_goal_text(g.description) == normalized for g in candidates):
                return (
                    f"agenda_delegation for goal {payload.get('goal')!r} already exists "
                    "as an active goal for this NPC."
                )
            return None

        return None

    payload = mut.payload if isinstance(mut.payload, dict) else {}

    if mut.mutation_type == "event_creation":
        # Canon-existence, not conversation-scoped (the dormant analyzer
        # channel awakens alongside the tick producer, TICKET-0017): a
        # --force re-analysis must not double an event either.
        return _find_event_duplicate(payload, mut.world_id, db)

    applied_same_type = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == mut.conversation_id,
            ProposedMutation.status == "applied",
            ProposedMutation.mutation_type == mut.mutation_type,
        )
    ).all()

    if not applied_same_type:
        return None

    for prev in applied_same_type:
        prev_p = prev.payload if isinstance(prev.payload, dict) else {}

        if mut.mutation_type == "new_knowledge":
            if (prev_p.get("entity_id") == payload.get("entity_id")
                    and prev_p.get("subject") == payload.get("subject")):
                return (
                    f"new_knowledge for entity {str(payload.get('entity_id',''))[:8]}… "
                    f"subject={payload.get('subject')!r} was already applied by "
                    f"mutation {prev.id[:8]}…  Applying again would create a "
                    f"duplicate knowledge row."
                )

        elif mut.mutation_type == "status_change":
            prev_eid = prev_p.get("entity_id") or prev.target_id
            cur_eid  = payload.get("entity_id") or mut.target_id
            if prev_eid == cur_eid:
                return (
                    f"status_change for entity {str(cur_eid)[:8]}… was already "
                    f"applied by mutation {prev.id[:8]}…"
                )

        elif mut.mutation_type == "goal_change":
            if (prev_p.get("action") == payload.get("action")
                    and _normalize_goal_text(prev_p.get("goal")) == _normalize_goal_text(payload.get("goal"))):
                return (
                    f"goal_change ({payload.get('action')}) for goal "
                    f"{payload.get('goal')!r} was already applied by mutation "
                    f"{prev.id[:8]}…"
                )

    return None


def _normalize_goal_text(text: Optional[str]) -> str:
    """Casefold + whitespace-collapse a goal description for equality matching
    (TICKET-0013, BRIEF-0013-c) — goals are matched by exact description text,
    never by id (the model never receives structural ids)."""
    return " ".join(str(text or "").split()).casefold()


def _knowledge_leg_already_applied(
    db: Session,
    conversation_id: str,
    entity_id: str,
    subject: str,
) -> bool:
    """True if an equivalent knowledge acquisition was already applied for this
    conversation — scanning BOTH applied `new_knowledge` rows (payload
    `entity_id`+`subject`) AND applied `resource_change` knowledge legs
    (payload `knowledge.entity_id`+`knowledge.subject`). Part of the
    resource_change knowledge-leg block-whole guard (4c, BRIEF-19).

    KNOWN ACCEPTED GAP, one-directional by design: this guard protects a
    resource_change knowledge leg from colliding with a prior new_knowledge
    or resource_change row, but the new_knowledge branch's own
    _find_applied_duplicate is deliberately NOT extended to scan
    resource_change knowledge legs. Do not touch that guard to close this —
    see ARCHITECTURE_DECISIONS.md "Deferred decisions".
    """
    rows = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == conversation_id,
            ProposedMutation.status == "applied",
            ProposedMutation.mutation_type.in_(("new_knowledge", "resource_change")),
        )
    ).all()
    for row in rows:
        p = row.payload if isinstance(row.payload, dict) else {}
        if row.mutation_type == "new_knowledge":
            if p.get("entity_id") == entity_id and p.get("subject") == subject:
                return True
        else:
            k = p.get("knowledge")
            if isinstance(k, dict) and k.get("entity_id") == entity_id and k.get("subject") == subject:
                return True
    return False


# ── Completion effects (TICKET-0024, BRIEF-0024-c) ─────────────────────────
# Closed vocabulary shared by `goal_change complete` and
# `agenda_step_change complete` — B1: one effect type per concrete named
# case, expand only at a second concrete case.

_EFFECT_TYPES = frozenset({"relation_delta", "ledger_transfer", "role_change"})
_MAX_EFFECTS = 3


def _h1_strip_satisfied_prerequisite_deltas(
    goal: NpcGoal, effects: list, db: Session
) -> tuple[list, list[str]]:
    # H1 (TICKET-0024): the ONLY sanctioned partial application of a
    # mutation. Scope: relation_delta on a satisfied relation_gte pair,
    # nothing else. Any other invalid element remains a whole reject.
    """`goal_change complete` only, called AFTER the BRIEF-0024-b
    prerequisite judge has passed — every `relation_gte` prerequisite on
    this goal is therefore satisfied at this point. Strips any
    `relation_delta` effect whose {subject, target_entity_id} pair (either
    direction) equals a prerequisite pair (anti-double-count, H1). Returns
    the kept effects and one note per stripped effect."""
    if not effects or not goal.prerequisites:
        return effects, []
    satisfied_pairs = {
        frozenset((goal.npc_id, item.get("target_entity_id")))
        for item in goal.prerequisites
        if item.get("type") == "relation_gte"
    }
    kept: list = []
    notes: list[str] = []
    for eff in effects:
        pair = (
            frozenset((goal.npc_id, eff.get("target_entity_id")))
            if isinstance(eff, dict) else None
        )
        if isinstance(eff, dict) and eff.get("type") == "relation_delta" and pair in satisfied_pairs:
            target = db.get(Entity, eff.get("target_entity_id"))
            notes.append(f"stripped: relation_delta on prerequisite pair {target.name if target else eff.get('target_entity_id')}")
        else:
            kept.append(eff)
    return kept, notes


def _apply_completion_effects(
    db: Session,
    *,
    world_id: str,
    subject_id: str,
    subject_is_character: bool,
    effects: Optional[list],
    mutation_id: str,
) -> Optional[str]:
    """Validate and apply up to `_MAX_EFFECTS` completion effects — shared
    by `goal_change complete` and `agenda_step_change complete`. Returns an
    error string on any invalid effect (whole-mutation reject; the
    caller's SAVEPOINT rolls back everything this call already wrote) or
    `None` on success. `effects` is expected already H1-stripped by the
    caller when applicable (goal_change only). The subject is FORCED by
    the caller (O1/H1 forcing precedent) — never read from the payload
    here.
    """
    if not effects:
        return None
    if len(effects) > _MAX_EFFECTS:
        return f"too many effects ({len(effects)} > {_MAX_EFFECTS})"

    for item in effects:
        eff_type = item.get("type") if isinstance(item, dict) else None
        if eff_type not in _EFFECT_TYPES:
            return f"unknown effect type {eff_type!r}"

        if eff_type == "relation_delta":
            target_id = item.get("target_entity_id")
            relation_type = item.get("relation_type")
            try:
                value = int(item.get("value"))
            except (TypeError, ValueError):
                return "relation_delta: value must be a nonzero int in [-10, 10]"
            if value == 0 or not (-10 <= value <= 10):
                return "relation_delta: value must be a nonzero int in [-10, 10]"
            if not target_id or db.get(Entity, target_id) is None:
                return f"relation_delta: target entity {target_id!r} not found"
            if not isinstance(relation_type, str) or not relation_type.strip():
                return "relation_delta: relation_type is required"
            write_relation(
                db, mode="delta", world_id=world_id, entity_a_id=subject_id,
                entity_b_id=target_id, type=relation_type, value=value,
                mutation_id=mutation_id,
            )

        elif eff_type == "ledger_transfer":
            from_id = item.get("from_entity_id")
            to_id = item.get("to_entity_id")
            reason = item.get("reason")
            try:
                amount = int(item.get("amount"))
            except (TypeError, ValueError):
                return "ledger_transfer: amount must be a positive int"
            if amount <= 0:
                return "ledger_transfer: amount must be a positive int"
            if not from_id or db.get(Entity, from_id) is None:
                return f"ledger_transfer: from entity {from_id!r} not found"
            if not to_id or db.get(Entity, to_id) is None:
                return f"ledger_transfer: to entity {to_id!r} not found"
            if _get_balance(db, from_id) - amount < 0:
                return "insufficient balance"
            # BRIEF-19 idiom: two INSERT-only legs, mutual counterparty,
            # both source_type="tick" (M1 — new documented enum value).
            write_ledger_entry(
                db, world_id=world_id, entity_id=from_id, amount=-amount,
                counterparty_id=to_id, reason=reason, source_type="tick",
            )
            write_ledger_entry(
                db, world_id=world_id, entity_id=to_id, amount=amount,
                counterparty_id=from_id, reason=reason, source_type="tick",
            )

        elif eff_type == "role_change":
            if not subject_is_character:
                return "role_change: subject of a faction-owned agenda is not a character"
            faction_id = item.get("faction_id")
            role = item.get("role")
            declare = bool(item.get("declare", False))
            if not faction_id or not isinstance(role, str) or not role.strip():
                return "role_change: faction_id and role are required"
            faction_entity = db.get(Entity, faction_id)
            faction = db.get(Faction, faction_id)
            if faction_entity is None or faction_entity.world_id != world_id or faction is None:
                return f"role_change: faction {faction_id!r} not found"
            role_key = role.strip()

            # (i) subject must hold an ACTIVE membership in this faction.
            membership = db.exec(
                select(FactionMembership).where(
                    FactionMembership.entity_id == subject_id,
                    FactionMembership.faction_id == faction_id,
                    FactionMembership.left_at.is_(None),
                )
            ).first()
            if membership is None:
                return f"role_change: NPC is not an active member of {faction_entity.name}"

            # (ii) resolve role against role_capacities, exact case-insensitive.
            capacities = faction.role_capacities or {}
            resolved_key = next(
                (k for k in capacities if k.casefold() == role_key.casefold()), None
            )
            if resolved_key is not None:
                limit = capacities[resolved_key]
                if limit is not None:
                    holders = db.exec(
                        select(FactionMembership).where(
                            FactionMembership.faction_id == faction_id,
                            FactionMembership.left_at.is_(None),
                        )
                    ).all()
                    count = sum(
                        1 for m in holders if (m.role or "").casefold() == resolved_key.casefold()
                    )
                    if count >= limit:
                        return f"role_change: role {resolved_key} is full ({count}/{limit})"
                final_role = resolved_key
            elif declare:
                # L2 declare-and-occupy: a role is never created without a
                # holder — declaration (dict reassignment) and occupation
                # (close+reopen below) commit in the same SAVEPOINT as the
                # rest of this mutation. Newly declared capacity is always
                # unlimited; only the creator sets limits thereafter.
                new_capacities = dict(capacities)
                new_capacities[role_key] = None
                write_faction_role_capacities(
                    db, faction=faction, capacities=new_capacities,
                    changed_by=f"mutation:{mutation_id}",
                )
                final_role = role_key
            else:
                return f"role_change: role {role_key} is not declared for {faction_entity.name}"

            write_membership(db, mode="close", membership_id=membership.id)
            write_membership(
                db, mode="open", world_id=world_id, entity_id=subject_id,
                faction_id=faction_id, role=final_role,
                cover_role=membership.cover_role, is_primary=membership.is_primary,
                is_secret=membership.is_secret,
            )

    return None


# ── Canon writer ──────────────────────────────────────────────────────────────

def _apply_mutation(mut: ProposedMutation, db: Session) -> Optional[str]:
    """Write one mutation to the canon tables.

    Returns an error string when the apply cannot proceed, None on success.
    Never raises — errors are returned so the caller can set status='approved'
    and store the message rather than crashing the request.

    Implemented types
    -----------------
    - relation_change  : find / create the relation, apply intensity delta,
                         clamp to 1–100, append previous state to change_history.
    - new_knowledge    : insert a knowledge row for the target entity.
    - status_change    : update entity.status and entity.updated_at.
    - item_update      : set item.equipped (BRIEF-07, schema v1.19 — the
                         equip toggle). Dormant since BRIEF-08/D2a.1: no
                         live code path produces this mutation type anymore;
                         the apply branch and cockpit toggle remain
                         functional for reactivation (see "Auto-applied
                         mutations" in ARCHITECTURE_DECISIONS.md).
    - knowledge_change : find the knowledge row by entity_id + subject, append
                         its previous state to change_history, update level
                         and source. Monotone — never applies a level that is
                         not strictly higher than the row's current level.
    - resource_change  : (BRIEF-19) two-leg write, both inside this one
                         SAVEPOINT — the single sanctioned exception to
                         one-branch-one-table. Money leg via
                         write_ledger_entry (always); optional knowledge leg
                         via write_knowledge (fresh acquisition only).
                         Guards: non-negative player balance; knowledge-leg
                         block-whole (existing row, or an equivalent
                         knowledge already applied this conversation) →
                         Needs attention, nothing written.
    - goal_change      : (TICKET-0013, BRIEF-0013-c) npc_id is FORCED to
                         conv.npc_id at emit time (analyzer.py) — never
                         trusted from the model beyond that. complete/abandon
                         match an ACTIVE goal (either horizon) by exact
                         normalized description text via write_npc_goal_status;
                         no match → Needs attention, nothing written.
                         create_short always inserts a SHORT goal via
                         write_npc_goal — horizon is hard-coded, O1 structural.
                         Own-agenda reference (TICKET-0020, BRIEF-0020-b,
                         per-NPC tick path only): an optional agenda_id
                         (already owner-index-resolved at normalize time)
                         links the new goal via write_goal_agenda_link; a
                         ValueError there → Needs attention, and the goal
                         insert is undone by the caller's SAVEPOINT rollback
                         (no separate pre-validation).
    - npc_move         : (TICKET-0015, BRIEF-0015-a) tick-only. Stale-from
                         gate: character.current_location_id must still equal
                         payload's from_location_id, else "Needs attention"
                         (covers duplicate re-approval, cross-run duplicates,
                         and a manual move since the proposal — RECON-0015
                         F6). Location write routes through
                         write_character_location; close_open_memberships is
                         called on apply regardless of player co-presence
                         (Nia's locked decision).
    - event_creation   : (TICKET-0017, BRIEF-0017-a) tolerant of BOTH payload
                         generations — the scope-level tick's closed shape
                         (title, description, type, knowledge_status,
                         involved_entities, location_id) and the analyzer's
                         minimal conversation-sourced shape (title,
                         description, type, involved_entities; no
                         status/location — write_event's defaults apply).
                         knowledge_status clamped to secret|public|confirmed
                         (defense in depth; 'confirmed' accepted here — a
                         creator may have edited the payload at review). A
                         present location_id must resolve to an ACTIVE
                         location entity of this world, else "Needs
                         attention", nothing written. Write via write_event.
    - agenda_step_change : (TICKET-0018, BRIEF-0018-a) tick-only, faction
                         scope. Stale guard: step.status must still be
                         'active', else "Needs attention", nothing written
                         (covers duplicate approval, cross-run re-proposal,
                         creator-moved-since — strictly stronger than any
                         tick_id key, so no _find_applied_duplicate clause
                         exists for this type). Advancement is CODE:
                         complete -> next pending step (by step_order)
                         becomes active, none left -> agenda completed;
                         fail -> the WHOLE agenda fails (no branching;
                         creator can reactivate via PATCH).
    - agenda_creation  : (TICKET-0018, BRIEF-0018-a) tick-only, faction
                         scope. write_agenda validates the owner resolves
                         to an ACTIVE faction entity (A1) — ValueError ->
                         "Needs attention". Writes one Agenda + N
                         AgendaStep rows (step 1 born active) in this one
                         SAVEPOINT — a parent-child aggregate, not a
                         one-branch-one-table exception of the
                         resource_change kind (an agenda_step has no
                         existence outside its agenda).
    - agenda_delegation : (TICKET-0020, BRIEF-0020-b) tick-only, faction
                         scope. Re-validates at apply (canon-existence): the
                         agenda is still ACTIVE; the NPC holds an ACTIVE
                         FactionMembership (secret OR public) in the agenda's
                         owner faction — either failing → Needs attention,
                         nothing written. Writes one NpcGoal + one
                         GoalAgendaLink in this one SAVEPOINT (same
                         parent-child-aggregate shape as agenda_creation,
                         not a resource_change-style exception).

    Unimplemented types (other) are left as 'approved' with a note — better
    un-applied than wrongly applied. `entity_creation` is realized through
    the Création tab (BRIEF-0019-a), never applied here: the unit approve
    endpoint short-circuits before this function ever sees that type.
    """
    # ── Duplicate guard ───────────────────────────────────────────────────────
    # Must run before any write.  If an equivalent mutation was already applied
    # for the same conversation, we block and surface it in the "Needs attention"
    # tab rather than silently doubling the effect.
    dup = _find_applied_duplicate(mut, db)
    if dup:
        return f"[duplicate blocked] {dup}"

    payload: dict = mut.payload if isinstance(mut.payload, dict) else {}

    # ── relation_change ───────────────────────────────────────────────────────
    if mut.mutation_type == "relation_change":
        a_id = payload.get("entity_a_id")
        b_id = payload.get("entity_b_id")
        if not a_id or not b_id:
            return "relation_change: payload must contain entity_a_id and entity_b_id"

        try:
            delta = int(payload.get("intensity_delta", 0))
        except (TypeError, ValueError):
            return "relation_change: intensity_delta must be an integer"

        rel_type = str(payload.get("relation_type") or "other")

        write_relation(
            db,
            mode="delta",
            world_id=mut.world_id,
            entity_a_id=a_id,
            entity_b_id=b_id,
            type=rel_type,
            value=delta,
            mutation_id=mut.id,
        )
        return None

    # ── new_knowledge ─────────────────────────────────────────────────────────
    elif mut.mutation_type == "new_knowledge":
        entity_id = payload.get("entity_id") or mut.target_id
        if not entity_id:
            return "new_knowledge: payload must contain entity_id (or set target_id)"

        # Pass session_id from the source conversation when available.
        session_id: Optional[str] = None
        if mut.conversation_id:
            conv = db.get(Conversation, mut.conversation_id)
            if conv:
                session_id = conv.session_id

        write_knowledge(
            db,
            entity_id=entity_id,
            subject=str(payload.get("subject") or "unknown"),
            level=str(payload.get("level") or "rumor"),
            content=str(payload.get("content") or ""),
            source=str(payload.get("source") or "conversation"),
            is_incorrect=bool(payload.get("is_incorrect", False)),
            is_secret=bool(payload.get("is_secret", False)),
            session_id=session_id,
        )
        # Flip discovered=TRUE on the source detail when this knowledge came
        # from an engine-proposed discovery. The flip is on APPLY (creator-
        # approved), not on propose — the creator can reject the proposal and
        # the detail stays available for re-selection in a later conversation.
        # Both the in-conversation _find_applied_duplicate guard and the
        # discovered=FALSE query in _stream() prevent double-proposing the
        # same detail (in-conversation guard) and re-proposing in future
        # conversations (discovered flag guard), respectively.
        detail_id = payload.get("discoverable_detail_id")
        if detail_id:
            detail = db.get(DiscoverableDetail, str(detail_id))
            if detail is not None:
                detail.discovered = True
                detail.updated_at = datetime.now(UTC)
                db.add(detail)
        return None

    # ── status_change ─────────────────────────────────────────────────────────
    elif mut.mutation_type == "status_change":
        entity_id = payload.get("entity_id") or mut.target_id
        new_status = (
            payload.get("status")
            or payload.get("new_status")
            or payload.get("value")
        )

        if not entity_id:
            return "status_change: need entity_id in payload or target_id on mutation"
        if not new_status:
            return "status_change: need 'status' (or 'new_status') in payload"

        entity = db.get(Entity, str(entity_id))
        if entity is None:
            return f"status_change: entity {entity_id!r} not found"

        entity.status = str(new_status)
        entity.updated_at = datetime.now(UTC)
        db.add(entity)
        return None

    # ── item_update (BRIEF-07, schema v1.19 — equip toggle) ──────────────────
    elif mut.mutation_type == "item_update":
        item_id = payload.get("item_id") or mut.target_id
        if not item_id:
            return "item_update: payload must contain item_id (or set target_id)"
        if "equipped" not in payload:
            return "item_update: payload must contain 'equipped'"

        item = db.get(Item, str(item_id))
        if item is None:
            return f"item_update: item {item_id!r} not found"
        if item.owner_id is None:
            return f"item_update: item {item_id!r} has no owner — cannot equip (schema CHECK)"

        item.equipped = bool(payload.get("equipped"))
        db.add(item)
        return None

    # ── knowledge_change ──────────────────────────────────────────────────────
    elif mut.mutation_type == "knowledge_change":
        entity_id = payload.get("entity_id") or mut.target_id
        subject = payload.get("subject")
        if not entity_id or not subject:
            return "knowledge_change: payload must contain entity_id and subject"

        row = db.exec(
            select(Knowledge).where(
                Knowledge.entity_id == entity_id,
                Knowledge.subject == subject,
            )
        ).first()
        if row is None:
            return "knowledge row not found"

        to_level = payload.get("to_level")
        if knowledge_level_rank(row.level) >= knowledge_level_rank(to_level):
            return "level already >= proposed"

        write_knowledge(
            db,
            mode="level_change",
            knowledge_id=row.id,
            level=to_level,
            source=payload.get("source"),
            changed_by="apply_mutation",
        )
        return None

    # ── goal_change (TICKET-0013, BRIEF-0013-c, H1/O1) ────────────────────────
    elif mut.mutation_type == "goal_change":
        npc_id = payload.get("npc_id")
        action = payload.get("action")
        goal_text = payload.get("goal")
        if not npc_id or not action or not goal_text:
            return "goal_change: payload must contain npc_id, action and goal"

        if action in ("complete", "abandon"):
            # O1: the model may close any active goal, either horizon —
            # matched by exact (normalized) description text, never by id.
            normalized = _normalize_goal_text(goal_text)
            candidates = db.exec(
                select(NpcGoal).where(NpcGoal.npc_id == npc_id, NpcGoal.status == "active")
            ).all()
            matches = [g for g in candidates if _normalize_goal_text(g.description) == normalized]
            if len(matches) != 1:
                return f"goal_change: no active goal matching {goal_text!r}"
            goal = matches[0]

            # Prerequisite judge (TICKET-0024, BRIEF-0024-b, G1): "model
            # proposes, code judges" — gates `complete` only, never
            # `abandon`. Fail-closed on an unrecognised type (the column is
            # creator-authored, but a hand-written row could still be
            # malformed).
            if action == "complete" and goal.prerequisites:
                for item in goal.prerequisites:
                    item_type = item.get("type")
                    if item_type != "relation_gte":
                        return f"goal_change: unknown prerequisite type {item_type!r}"
                    target_id = item.get("target_entity_id")
                    threshold = item.get("threshold")
                    rel = _find_relation_pair(db, npc_id, target_id)
                    current = rel.intensity if rel else 0
                    if current < threshold:
                        target = db.get(Entity, target_id)
                        target_name = target.name if target else target_id
                        return (
                            f"goal_change: prerequisite not met — relation "
                            f"with {target_name} is {current}, requires >= {threshold}"
                        )

            # Completion effects (TICKET-0024, BRIEF-0024-c) — `complete`
            # only, never `abandon`. Runs AFTER the prerequisite judge
            # above, so goal.prerequisites (if any) are all satisfied here.
            extra_history: dict[str, Any] = {}
            if action == "complete":
                effects = payload.get("effects")
                stripped_notes: list[str] = []
                if isinstance(effects, list):
                    effects, stripped_notes = _h1_strip_satisfied_prerequisite_deltas(
                        goal, effects, db
                    )

                effect_error = _apply_completion_effects(
                    db,
                    world_id=mut.world_id,
                    subject_id=npc_id,
                    subject_is_character=True,
                    effects=effects,
                    mutation_id=mut.id,
                )
                if effect_error:
                    return effect_error

                if stripped_notes:
                    mut.creator_notes = _append_note(mut.creator_notes, "; ".join(stripped_notes))
                    extra_history["stripped"] = stripped_notes

                # A1: zero prerequisites and zero effects applied (absent,
                # empty, or fully H1-stripped) is legitimate (Nia's type 3).
                if not goal.prerequisites and not effects:
                    extra_history["no_footprint"] = True

            write_npc_goal_status(
                db,
                goal=goal,
                new_status="completed" if action == "complete" else "abandoned",
                changed_by=f"mutation:{mut.id}",
                extra=extra_history or None,
            )
            return None

        if action == "create_short":
            # O1 structural: horizon is hard-coded "short" — the payload
            # carries no horizon field and none is read, so the model cannot
            # create a long-term goal by any input. S1: no active-count
            # check — the injection's read-side LIMIT is the bound.
            goal = write_npc_goal(
                db,
                world_id=mut.world_id,
                npc_id=npc_id,
                description=goal_text,
                horizon="short",
                changed_by=f"mutation:{mut.id}",
            )
            # Own-agenda reference (TICKET-0020, BRIEF-0020-b): normalize-time
            # resolved an optional agenda title into agenda_id (owner-only
            # index) — link preconditions (agenda still active, etc.) are
            # re-validated here (the agenda may have closed since the tick).
            # A ValueError is caught and returned as a string (this
            # function's "never raises" contract, kept consistent with every
            # other write_* call above) — the caller's outer SAVEPOINT then
            # rolls back the goal insert too, so a failed link means NO goal
            # either, exactly as if the whole mutation had been rejected.
            agenda_id = payload.get("agenda_id")
            if agenda_id:
                try:
                    write_goal_agenda_link(
                        db,
                        world_id=mut.world_id,
                        goal_id=goal.id,
                        agenda_id=agenda_id,
                        created_by=f"mutation:{mut.id}",
                        mutation_id=mut.id,
                    )
                except ValueError as exc:
                    return f"goal_change: {exc}"
            return None

        return f"goal_change: unrecognised action {action!r}"

    # ── npc_move (TICKET-0015, BRIEF-0015-a) ──────────────────────────────────
    elif mut.mutation_type == "npc_move":
        npc_id = payload.get("npc_id")
        from_location_id = payload.get("from_location_id")
        to_location_id = payload.get("to_location_id")
        if not npc_id or not from_location_id or not to_location_id:
            return "npc_move: payload must contain npc_id, from_location_id and to_location_id"

        character = db.get(Character, npc_id)
        if character is None:
            return f"npc_move: character {npc_id!r} not found"

        # Stale-from gate (RECON-0015 F6): the canon question "is the NPC
        # still at from_location_id?" covers duplicate re-approval, cross-run
        # tick duplicates, and a manual move since the proposal — while still
        # allowing a later legitimate A->B->A move.
        if character.current_location_id != from_location_id:
            return "npc_move: NPC no longer at the proposal's origin — world moved since the tick"

        destination = db.get(Entity, to_location_id)
        if (
            destination is None
            or destination.type != "location"
            or destination.status != "active"
            or destination.world_id != mut.world_id
        ):
            return f"npc_move: destination {to_location_id!r} is not an active location in this world"

        write_character_location(db, entity_id=npc_id, to_location_id=to_location_id, mutation_id=mut.id)
        # BRIEF-53 seam: closes the NPC's open gathering_member rows,
        # PLAYER PRESENT OR NOT — Nia's locked decision.
        close_open_memberships(npc_id, db)
        return None

    # ── event_creation (TICKET-0017, BRIEF-0017-a) ────────────────────────────
    elif mut.mutation_type == "event_creation":
        title = payload.get("title")
        if not title:
            return "event_creation: payload must contain title"

        knowledge_status = payload.get("knowledge_status")
        if knowledge_status not in ("secret", "public", "confirmed"):
            knowledge_status = "secret"

        location_id = payload.get("location_id")
        if location_id:
            location_entity = db.get(Entity, location_id)
            if (
                location_entity is None
                or location_entity.type != "location"
                or location_entity.status != "active"
                or location_entity.world_id != mut.world_id
            ):
                return f"event_creation: location {location_id!r} is not an active location in this world"

        write_event(
            db,
            world_id=mut.world_id,
            title=str(title),
            description=payload.get("description"),
            type=payload.get("type"),
            knowledge_status=knowledge_status,
            involved_entities=payload.get("involved_entities"),
            location_id=location_id,
            mutation_id=mut.id,
        )
        return None

    # ── resource_change (BRIEF-19) ────────────────────────────────────────────
    elif mut.mutation_type == "resource_change":
        entity_id = payload.get("entity_id")
        counterparty_id = payload.get("counterparty_id")
        reason = payload.get("reason")
        if not entity_id:
            return "resource_change: payload must contain entity_id"
        try:
            amount = int(payload.get("amount"))
        except (TypeError, ValueError):
            return "resource_change: payload must contain an integer 'amount'"

        knowledge_leg = payload.get("knowledge")
        if not isinstance(knowledge_leg, dict):
            knowledge_leg = None

        # Non-negative guard — AI path only; the creator CRUD path stays
        # god-mode (no balance check on POST /api/ledger).
        if amount < 0 and _get_balance(db, entity_id) + amount < 0:
            return "insufficient balance"

        # Knowledge-leg guard (block-whole) — if a clean fresh row cannot be
        # created, the WHOLE mutation is routed to Needs attention and
        # nothing is written (not even the money leg).
        if knowledge_leg is not None:
            k_entity_id = knowledge_leg.get("entity_id")
            k_subject = knowledge_leg.get("subject")
            if not k_entity_id or not k_subject:
                return "resource_change: knowledge leg must contain entity_id and subject"

            existing_row = db.exec(
                select(Knowledge).where(
                    Knowledge.entity_id == k_entity_id,
                    Knowledge.subject == k_subject,
                )
            ).first()
            if existing_row is not None:
                return "knowledge already held (upgrade-by-purchase deferred)"

            if mut.conversation_id and _knowledge_leg_already_applied(
                db, mut.conversation_id, k_entity_id, k_subject
            ):
                return "duplicate knowledge leg"

        # session_id from the source conversation, same as new_knowledge.
        session_id: Optional[str] = None
        if mut.conversation_id:
            conv = db.get(Conversation, mut.conversation_id)
            if conv:
                session_id = conv.session_id

        write_ledger_entry(
            db,
            world_id=mut.world_id,
            entity_id=entity_id,
            amount=amount,
            counterparty_id=counterparty_id,
            reason=reason,
            source_type="conversation",
            conversation_id=mut.conversation_id,
            session_id=session_id,
        )

        if knowledge_leg is not None:
            write_knowledge(
                db,
                entity_id=knowledge_leg.get("entity_id"),
                subject=str(knowledge_leg.get("subject") or "unknown"),
                level=str(knowledge_leg.get("level") or "rumor"),
                content=str(knowledge_leg.get("content") or ""),
                source=str(knowledge_leg.get("source") or "conversation"),
                is_incorrect=bool(knowledge_leg.get("is_incorrect", False)),
                is_secret=bool(knowledge_leg.get("is_secret", False)),
                session_id=session_id,
            )
        return None

    # ── agenda_step_change (TICKET-0018, BRIEF-0018-a) ────────────────────────
    elif mut.mutation_type == "agenda_step_change":
        step_id = payload.get("step_id")
        action = payload.get("action")
        if not step_id or action not in ("complete", "fail"):
            return "agenda_step_change: payload must contain step_id and action in {complete, fail}"

        step = db.get(AgendaStep, step_id)
        if step is None:
            return f"agenda_step_change: step {step_id!r} not found"

        # Stale guard (0014 doctrine, canon-existence): the step must still
        # be the ACTIVE one — covers duplicate approval, cross-run
        # re-proposal, and a creator-moved-since (RECON-0018 F5). Strictly
        # stronger than any tick_id key (0015 F6 argument) — no
        # _find_applied_duplicate clause is needed for this type.
        if step.status != "active":
            return "agenda_step_change: step no longer active — world moved since the tick"

        agenda = db.get(Agenda, step.agenda_id)
        if agenda is None:
            return f"agenda_step_change: agenda {step.agenda_id!r} not found"

        # Completion effects (TICKET-0024, BRIEF-0024-c) — `complete` only,
        # never `fail`. Subject is FORCED to the agenda's owner (character
        # or faction); a role_change effect on a faction-owned agenda is a
        # whole reject (role_change is character-only).
        extra_history: dict[str, Any] = {}
        if action == "complete":
            owner = db.get(Entity, agenda.owner_entity_id)
            subject_is_character = owner is not None and owner.type == "character"
            effects = payload.get("effects")

            effect_error = _apply_completion_effects(
                db,
                world_id=mut.world_id,
                subject_id=agenda.owner_entity_id,
                subject_is_character=subject_is_character,
                effects=effects,
                mutation_id=mut.id,
            )
            if effect_error:
                return effect_error

            # agenda_step has no prerequisites column (G3 deferred) — A1's
            # "zero prerequisites" side is always true here.
            if not effects:
                extra_history["no_footprint"] = True

        new_status = "completed" if action == "complete" else "failed"
        write_agenda_step_status(
            db, step=step, status=new_status, outcome=payload.get("outcome"), mutation_id=mut.id,
            extra=extra_history or None,
        )

        if action == "complete":
            next_step = db.exec(
                select(AgendaStep)
                .where(AgendaStep.agenda_id == agenda.id, AgendaStep.status == "pending")
                .order_by(AgendaStep.step_order)
            ).first()
            if next_step is not None:
                write_agenda_step_status(db, step=next_step, status="active", mutation_id=mut.id)
            else:
                write_agenda_status(db, agenda=agenda, status="completed", mutation_id=mut.id)
        else:  # fail — the WHOLE agenda fails, no branching (creator can reactivate via PATCH)
            write_agenda_status(db, agenda=agenda, status="failed", mutation_id=mut.id)
        return None

    # ── agenda_creation (TICKET-0018, BRIEF-0018-a) ───────────────────────────
    elif mut.mutation_type == "agenda_creation":
        owner_entity_id = payload.get("owner_entity_id")
        title = payload.get("title")
        steps = payload.get("steps")
        if (
            not owner_entity_id
            or not title
            or not isinstance(steps, list)
            or not (2 <= len(steps) <= 5)
            or not all(isinstance(s, str) and s.strip() for s in steps)
        ):
            return "agenda_creation: payload must contain owner_entity_id, title, and 2-5 non-empty steps"

        try:
            agenda = write_agenda(
                db, world_id=mut.world_id, owner_entity_id=owner_entity_id, title=str(title),
                mutation_id=mut.id,
            )
        except ValueError as exc:
            return f"agenda_creation: {exc}"

        # Parent-child aggregate, one SAVEPOINT (RECON-0018 F5) — NOT a
        # one-branch-one-table exception of the resource_change kind: an
        # agenda_step has no existence outside its agenda, so this is two
        # tables of the SAME canon domain, not two domains.
        for order, objective in enumerate(steps, start=1):
            write_agenda_step(
                db,
                agenda_id=agenda.id,
                step_order=order,
                objective=str(objective),
                # Step 1 is born active — the creator's approval IS the
                # activation (symmetric with the creator-CRUD create route).
                status="active" if order == 1 else "pending",
            )
        return None

    # ── agenda_delegation (TICKET-0020, BRIEF-0020-b) ─────────────────────────
    elif mut.mutation_type == "agenda_delegation":
        npc_id = payload.get("npc_id")
        goal_text = payload.get("goal")
        horizon = payload.get("horizon")
        agenda_id = payload.get("agenda_id")
        if not npc_id or not goal_text or horizon not in ("short", "long") or not agenda_id:
            return "agenda_delegation: payload must contain npc_id, goal, horizon in {short, long}, and agenda_id"

        agenda = db.get(Agenda, agenda_id)
        if agenda is None or agenda.status != "active":
            return f"agenda_delegation: agenda {agenda_id!r} is not active — world moved since the tick"

        # Re-validate at apply (stale-proof, canon-existence): the NPC must
        # hold an ACTIVE FactionMembership in the agenda's owner faction —
        # secret OR public, a faction may task a secret member.
        membership = db.exec(
            select(FactionMembership).where(
                FactionMembership.entity_id == npc_id,
                FactionMembership.faction_id == agenda.owner_entity_id,
                FactionMembership.left_at.is_(None),
            )
        ).first()
        if membership is None:
            return f"agenda_delegation: NPC {npc_id!r} is not an active member of the agenda's owner faction"

        # Same-domain parent-child aggregate, one SAVEPOINT — the 0018
        # agenda_creation precedent, not a one-branch-one-table exception of
        # the resource_change kind.
        goal = write_npc_goal(
            db,
            world_id=mut.world_id,
            npc_id=npc_id,
            description=str(goal_text),
            horizon=horizon,
            changed_by=f"mutation:{mut.id}",
        )
        try:
            write_goal_agenda_link(
                db,
                world_id=mut.world_id,
                goal_id=goal.id,
                agenda_id=agenda_id,
                created_by=f"mutation:{mut.id}",
                mutation_id=mut.id,
            )
        except ValueError as exc:
            return f"agenda_delegation: {exc}"
        return None

    # ── unimplemented ─────────────────────────────────────────────────────────
    else:
        return (
            f"mutation_type '{mut.mutation_type}' is not implemented in "
            f"_apply_mutation — left as 'approved' for manual handling."
        )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_ui() -> str:
    return _INDEX_HTML.read_text(encoding="utf-8")


@app.get("/vendor/{filename}")
def serve_vendor_file(filename: str) -> FileResponse:
    if filename not in _VENDOR_WHITELIST:
        raise HTTPException(status_code=404, detail=f"{filename!r} is not a vendored asset")
    return FileResponse(_VENDOR_DIR / filename, media_type="application/javascript")


# ── World selection ────────────────────────────────────────────────────────────

@app.get("/api/worlds")
def list_worlds(db: Session = Depends(get_session)) -> list:
    worlds = db.exec(select(World)).all()
    return [
        {"id": w.id, "name": w.name, "is_active": w.is_active}
        for w in worlds
    ]


@app.post("/api/worlds/{world_id}/activate")
def activate_world(world_id: str, db: Session = Depends(get_session)) -> dict:
    target = db.get(World, world_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"World {world_id!r} not found")
    try:
        for w in db.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
            w.is_active = False
            db.add(w)
        db.flush()
        target.is_active = True
        db.add(target)
        db.commit()
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "world_id": target.id}


class WorldCreateBody(BaseModel):
    name: str
    description: str = ""
    fundamental_laws: str = ""


@app.post("/api/worlds")
def create_world(body: WorldCreateBody, db: Session = Depends(get_session)) -> dict:
    """Generic empty-world bootstrap (BRIEF-44, B2). Creates one fresh-UUID
    `world` row and auto-activates it in the same transaction (reuses
    activate_world's deactivate-then-activate logic). The created world is
    empty: no PC, no session, no locations, no templates, no entities."""
    try:
        new_world = World(
            name=body.name,
            description=body.description,
            fundamental_laws=body.fundamental_laws,
        )
        db.add(new_world)
        db.flush()
        for w in db.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
            w.is_active = False
            db.add(w)
        db.flush()
        new_world.is_active = True
        db.add(new_world)
        db.commit()
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "world_id": new_world.id}


def _activate_world_core(world_id: str, db: Session) -> None:
    """Commit-free deactivate-then-activate core (BRIEF-54, E1 deferral).

    Replicates `activate_world`'s inline logic: deactivate every currently-
    active world, `db.flush()`, then activate the target. The flush-between
    is required — `idx_world_one_active` is a partial UNIQUE index, not a
    FK, so `PRAGMA defer_foreign_keys` does not cover it; two active rows
    must never coexist, even mid-transaction. Used by the delete route only
    in this brief — `activate_world` and `create_world` keep their own
    inline duplication (named deferral, not rewired here)."""
    for w in db.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
        w.is_active = False
        db.add(w)
    db.flush()
    target = db.get(World, world_id)
    target.is_active = True
    db.add(target)


@app.delete("/api/worlds/{world_id}")
def delete_world(world_id: str, db: Session = Depends(get_session)) -> dict:
    """Hard-delete a world block, full cascade, irreversible (BRIEF-54, A1).

    The sole sanctioned exception to "History is sacred" — see
    `delete_world_cascade` (`writes.py`). One atomic transaction: cascade +
    survivor re-activation either both happen or neither does."""
    target = db.get(World, world_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"World {world_id!r} not found")
    was_active = target.is_active
    try:
        _delete_world_cascade(world_id, db)
        remaining_worlds = db.exec(select(World)).all()
        remaining = len(remaining_worlds)
        if remaining == 0:
            active_world_id = None
        elif was_active:
            survivor = max(remaining_worlds, key=lambda w: w.created_at)
            _activate_world_core(survivor.id, db)
            active_world_id = survivor.id
        else:
            active = next((w for w in remaining_worlds if w.is_active), None)
            active_world_id = active.id if active else None
        db.commit()
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "remaining": remaining, "active_world_id": active_world_id}


# ── Bootstrap — resolved play context for the static cockpit JS (BRIEF-45) ────

@app.get("/api/bootstrap")
def get_bootstrap(db: Session = Depends(get_session)) -> dict:
    """Resolved play context for index.html, which is served as a static file
    with no server-side templating. Read-only; opens no session.

    Returns the active world's id, the structurally-resolved player character
    id (character_type='player'), and that character's current_location_id.
    `player_id`/`current_location_id` are null when the active world has no
    PC yet (BRIEF-46: a freshly created world has none until the creator uses
    the create-PC form) — `world_id` must still resolve so that form can
    scope its starting-location dropdown.
    """
    world_id = _crud._world_id(db)
    try:
        player_id = _crud._player_character_id(db, world_id)
    except HTTPException:
        player_id = None
    player_char = db.get(Character, player_id) if player_id else None
    return {
        "world_id": world_id,
        "player_id": player_id,
        "current_location_id": player_char.current_location_id if player_char else None,
    }


# ── Create-PC path (BRIEF-46) ──────────────────────────────────────────────────

class PlayerKnowledgeItem(BaseModel):
    subject: str
    level: str
    content: str


class PlayerCharacterCreateBody(BaseModel):
    name: str
    current_location_id: str
    description: Optional[str] = None
    appearance: Optional[str] = None
    backstory: Optional[str] = None
    knowledge: Optional[list[PlayerKnowledgeItem]] = None


@app.post("/api/characters/player")
def create_player_character(
    body: PlayerCharacterCreateBody, db: Session = Depends(get_session)
) -> dict:
    """Create a PC and place it at a starting location in the active world.

    Binds to the lone creator user (`role='creator'`) — there is no real
    multiplayer user identity yet. Mirrors `seed_pilot.py`'s `char-player`
    creation: entity + `character` row + the four `skill` rows (physical,
    agility, perception, composure) at `tier=0`, since the skill sheet and
    physical-resolution arbiter both read those rows off a PC. One PC per
    user per world is defended by `idx_character_one_pc_per_user_world`
    (partial unique index) — a collision surfaces as a clean `{"ok": false}`,
    not a 500.

    BRIEF-52 (E1): also accepts the optional PC creation assistant draft —
    `description`/`appearance`/`backstory` set on the rows that own them,
    and `knowledge` written through `write_knowledge` with `is_secret=False`
    (never through `POST /api/entities/{id}/knowledge`, which 422s on a bad
    level instead of defaulting to "rumor"). The base-domain skill seed stays
    untouched (B1, no proposed tiers).

    BRIEF-55 (B1, schema v1.63): after the four base-domain rows, also seeds
    one `skill` row per `skill_definition` of the PC's world, at `tier=0`,
    `domain=<definition.base_domain>`, `skill_definition_id=<definition.id>`
    — never proposed by a model.
    """
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    world_id = _crud._world_id(db)

    location_entity = db.get(Entity, body.current_location_id)
    if (
        location_entity is None
        or location_entity.world_id != world_id
        or location_entity.type != "location"
    ):
        raise HTTPException(
            status_code=400,
            detail="current_location_id must be a location entity in the active world",
        )

    creator_user = db.exec(select(User).where(User.role == "creator")).first()
    if creator_user is None:
        raise HTTPException(status_code=400, detail="No creator user found.")

    try:
        entity = Entity(
            world_id=world_id,
            type="character",
            name=name,
            description=(body.description or None),
        )
        db.add(entity)
        db.flush()
        character = Character(
            id=entity.id,
            world_id=world_id,
            character_type="player",
            user_id=creator_user.id,
            current_location_id=body.current_location_id,
            appearance=(body.appearance or None),
            backstory=(body.backstory or None),
        )
        db.add(character)
        for domain in BASE_SKILL_DOMAINS:
            db.add(Skill(character_id=entity.id, domain=domain, tier=0))
        # B1 (schema v1.63): flat tier-0 seed for every custom skill of the
        # PC's world — never proposed by a model, set here after the draft
        # is accepted.
        custom_defs = db.exec(
            select(SkillDefinition).where(SkillDefinition.world_id == world_id)
        ).all()
        for definition in custom_defs:
            db.add(Skill(
                character_id=entity.id,
                domain=definition.base_domain,
                tier=0,
                skill_definition_id=definition.id,
            ))
        for item in (body.knowledge or []):
            level = item.level if item.level in KNOWLEDGE_LEVELS else "rumor"
            write_knowledge(
                db,
                entity_id=entity.id,
                subject=item.subject,
                level=level,
                content=item.content,
                source="pc_creation",
                is_incorrect=False,
                is_secret=False,
                share_threshold=50,
                session_id=None,
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        return {
            "ok": False,
            "error": "A player character already exists for this user in this world.",
        }
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": str(exc)}

    db.refresh(entity)
    return {"ok": True, "id": entity.id, "name": entity.name}


# ── Play loop — provisional creator entry point ───────────────────────────────
# These three endpoints (npcs, conversations/start, say, end) form the play
# loop introduced for browser-based conversations.  The NPC selector and
# /start endpoint are PROVISIONAL creator-side scaffolding; they will be
# replaced by a full player view.  The persistence and streaming logic (say,
# end) is the durable piece.

@app.get("/api/npcs")
def list_npcs(db: Session = Depends(get_session)) -> list:
    """Return every NPC character in the world (id, display name, faction)."""
    chars = db.exec(
        select(Character).where(Character.character_type == "npc")
    ).all()
    result = []
    for char in chars:
        entity = db.get(Entity, char.id)
        if entity is None:
            continue
        faction_name: Optional[str] = None
        membership = db.exec(
            select(FactionMembership).where(
                FactionMembership.entity_id == char.id,
                FactionMembership.left_at.is_(None),
                FactionMembership.is_primary == True,  # noqa: E712
            )
        ).first()
        if membership:
            fac = db.get(Entity, membership.faction_id)
            if fac:
                faction_name = fac.name
        result.append({"id": char.id, "name": entity.name, "faction": faction_name})
    return result


def _get_or_open_session(world_id: str, db: Session) -> GameSession:
    """Return the world's open session, creating one if none exists."""
    existing = db.exec(
        select(GameSession)
        .where(GameSession.world_id == world_id, GameSession.status == "open")
        .order_by(GameSession.number.desc())
    ).first()
    if existing is not None:
        return existing
    numbers = db.exec(
        select(GameSession.number).where(GameSession.world_id == world_id)
    ).all()
    number = (max(numbers) if numbers else 0) + 1
    sess = GameSession(
        world_id=world_id,
        number=number,
        title="Live play session",
        status="open",
        started_at=datetime.now(UTC),
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _load_npc_dialogue_template(world_id: str, db: Session) -> PromptTemplate:
    """Return the active npc_dialogue prompt template (world-specific preferred)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "npc_dialogue",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        raise HTTPException(
            status_code=503,
            detail="No active 'npc_dialogue' prompt template found. Run seed_pilot.py.",
        )
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _npc_dialogue_system_prompt(system_prompt: str, context: str) -> str:
    """The exact system-prompt concatenation every live npc_dialogue path
    uses (BRIEF-0008-b, fidelity rule) — extracted so the read-only preview
    endpoint reuses this construction verbatim instead of duplicating it.

    Takes the already-resolved version text (TICKET-0011, G1) — every call
    site fetches its version via `current_prompt` next to the head load,
    never inside this helper."""
    return f"{system_prompt}\n\n{context}"


# ── Multi-NPC scenes — gatherings (schema v1.8, Tier 1, step 3) ───────────────
# Helpers consumed by the /say flow's join handling (contract A2) and speaker
# selection (contract A3 hybrid). Generation itself lives in gathering.py;
# these only read the partition that `enter_location` already produced.

def _open_gatherings(location_id: str, session_id: str, db: Session) -> list[Gathering]:
    return list(db.exec(
        select(Gathering).where(
            Gathering.location_id == location_id,
            Gathering.session_id == session_id,
            Gathering.status == "open",
        )
    ).all())


def _active_members(gathering_id: str, db: Session) -> list[tuple[GatheringMember, Entity]]:
    """Return the active (left_at IS NULL) members of a gathering.

    Single source of truth for gathering rosters (C2 preparation rule a).
    All roster reads — initiative vote, speaker selection, context assembly —
    must go through this function so that when C2 updates membership, every
    consumer automatically sees the correct composition.

    Unicité invariant (C2 preparation rule b): an entity must be an active
    member of at most one open gathering at a time. Not yet enforced
    mechanically (nothing migrates members before C2), but the invariant is
    designated here for when C2 lifts the restriction.
    """
    return list(db.exec(
        select(GatheringMember, Entity)
        .join(Entity, Entity.id == GatheringMember.entity_id)
        .join(Character, Character.id == Entity.id)
        .where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.left_at.is_(None),
            Entity.status == "active",
            Character.vital_status == "alive",
        )
    ).all())


def _gathering_brief(gathering_id: str, db: Session) -> Optional[dict]:
    """{id, label, members:[{id, name}]} for an open gathering, or None."""
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        return None
    return {
        "id": gathering.id,
        "label": gathering.label,
        "members": [{"id": e.id, "name": e.name} for _gm, e in _active_members(gathering_id, db)],
    }


def _player_gathering(player_id: str, location_id: str, session_id: str, db: Session) -> Optional[Gathering]:
    """The open gathering at this location+session the player currently belongs to, if any."""
    row = db.exec(
        select(Gathering)
        .join(GatheringMember, GatheringMember.gathering_id == Gathering.id)
        .where(
            Gathering.location_id == location_id,
            Gathering.session_id == session_id,
            Gathering.status == "open",
            GatheringMember.entity_id == player_id,
            GatheringMember.left_at.is_(None),
        )
    ).first()
    return row


def _render_gathering_status(
    player_id: str,
    player_gathering: Optional[Gathering],
    open_gatherings: list[Gathering],
    db: Session,
) -> str:
    """Free-text block fed to the interpretation prompt.

    Describes the player's current group membership and — when ungrouped —
    the open gatherings actually present, by label and member names, so the
    model can recognize a join attempt and quote a `reference` against names
    it was actually shown (contract A2: never invent).
    """
    if player_gathering is not None:
        names = ", ".join(e.name for _gm, e in _active_members(player_gathering.id, db) if e.id != player_id)
        if names:
            return f"Vous faites partie du groupe « {player_gathering.label} », avec {names}."
        return f"Vous faites partie du groupe « {player_gathering.label} »."
    if not open_gatherings:
        return "Vous n'avez rejoint aucun groupe ; aucun groupe ne s'est encore formé ici."
    lines = []
    for gathering in open_gatherings:
        names = ", ".join(e.name for _gm, e in _active_members(gathering.id, db))
        lines.append(f"- « {gathering.label} »" + (f" : {names}" if names else ""))
    return (
        "Vous n'avez rejoint aucun groupe. Groupes présents dans la salle :\n"
        + "\n".join(lines)
    )


def _resolve_join_target(reference: str, open_gatherings: list[Gathering], db: Session) -> Optional[str]:
    """Resolve the player's join `reference` to exactly one open gathering id.

    A2 — structural, not generative: matches the model's free-text reference
    against the labels and member names of the gatherings actually present,
    case-insensitively. Returns a gathering id only on an unambiguous match;
    None (no match, or more than one) routes to the cockpit fallback picker.
    Never guesses, never invents.
    """
    ref = (reference or "").strip().lower()
    if not ref:
        return None
    candidates: set[str] = set()
    for gathering in open_gatherings:
        if gathering.label and gathering.label.strip().lower() in ref:
            candidates.add(gathering.id)
            continue
        if any(e.name.strip().lower() in ref for _gm, e in _active_members(gathering.id, db)):
            candidates.add(gathering.id)
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _location_neighbours(location_id: str, db: Session) -> list[tuple[str, str]]:
    """Direct connects_to neighbours of a location: (entity_id, name) for each
    ACTIVE location linked by a connects_to relation touching location_id.
    A distinct job from GET /api/locations/graph (whole-world graph) — they
    both read connects_to but are not refactored to share code (decision D1)."""
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
    result: list[tuple[str, str]] = []
    for rel in [*rels_a, *rels_b]:
        neighbour_id = rel.entity_b_id if rel.entity_a_id == location_id else rel.entity_a_id
        if neighbour_id in seen:
            continue
        seen.add(neighbour_id)
        neighbour = db.get(Entity, neighbour_id)
        if neighbour is not None and neighbour.status == "active":
            result.append((neighbour.id, neighbour.name))
    return result


def _resolve_travel_target(reference: str, neighbours: list[tuple[str, str]]) -> Optional[str]:
    """Case-insensitive exact-ish match of the player's destination words
    against neighbour names. Returns one entity_id or None. NEVER guesses,
    NEVER nearest-match (contract A2) — an ambiguous or absent reference
    returns None and the caller shows the picker."""
    ref = (reference or "").strip().lower()
    if not ref:
        return None
    candidates: set[str] = set()
    for entity_id, name in neighbours:
        if name.strip().lower() in ref or ref in name.strip().lower():
            candidates.add(entity_id)
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _join_gathering(conv: Conversation, gathering_id: str, db: Session) -> Gathering:
    """Insert the player as an active member of `gathering_id` and anchor the
    conversation to it. Idempotent — rejoining the same gathering is a no-op
    on membership (the row already exists and stays open)."""
    gathering = db.get(Gathering, gathering_id)
    if gathering is None:
        raise HTTPException(status_code=404, detail=f"Gathering {gathering_id!r} not found")
    existing = db.exec(
        select(GatheringMember).where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.entity_id == conv.player_id,
            GatheringMember.left_at.is_(None),
        )
    ).first()
    if existing is None:
        db.add(GatheringMember(
            gathering_id=gathering_id,
            entity_id=conv.player_id,
            joined_at=datetime.now(UTC),
            left_at=None,
        ))
    conv.gathering_id = gathering_id
    db.add(conv)
    db.commit()
    db.refresh(gathering)
    return gathering


def _load_mj_speaker_template(world_id: str, db: Session) -> Optional[PromptTemplate]:
    """Return the active mj_speaker_selection prompt template, or None."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "mj_speaker_selection",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _select_group_speaker(
    *,
    template: Optional[PromptTemplate],
    location_name: str,
    gathering: Gathering,
    members: list[tuple[GatheringMember, Entity]],
    player_line: str,
    model: str,
    db: Session,
) -> str:
    """Pick exactly one active gathering member to respond (contract A3 hybrid).

    Asks the MJ to choose; resolves the returned name against the active
    roster (A2-style exact, case-insensitive match). Falls back to the first
    active member on a missing template, a call failure, or an unresolved
    name — cadence B1 (exactly one responder per turn) holds regardless; the
    scene must stay playable.
    """
    if template is not None:
        version = current_prompt(db, template)
        member_lines = "\n".join(f"- {e.name}" for _gm, e in members)
        user_msg = (
            version.user_template
            .replace("{location_name}", location_name)
            .replace("{group_label}", gathering.label or "Groupe")
            .replace("{member_list}", member_lines)
            .replace("{player_line}", player_line)
            + "\n/no_think"
        )
        try:
            raw = ollama_client.chat(
                [
                    {"role": "system", "content": version.system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
                model=model,
                format="json",
            )
            obj = json.loads(raw)
            name = str(obj.get("speaker", "")).strip().lower()
            for _gm, e in members:
                if e.name.strip().lower() == name:
                    return e.id
            _log.info("MJ speaker selection: unresolved name %r — fallback to first member", name)
        except Exception as exc:
            _log.warning("MJ speaker selection call failed (%s) — fallback to first member", exc)
    return members[0][1].id


def _build_join_narration_user(
    *,
    location_name: str,
    player_line: str,
    joined: bool,
    gathering_label: Optional[str],
) -> str:
    """MJ narration for a join action — third-person, no dialogue, no NPC call.

    `joined=True`  : the player successfully settles in with the named group.
    `joined=False` : resolution was ambiguous; the player hesitates while the
                     cockpit shows the fallback picker (see /join endpoint).
    """
    if joined:
        return (
            f"Lieu : « {location_name} ».\n"
            f"Mode : le joueur rejoint un groupe — « {gathering_label} ».\n\n"
            f"Action du joueur :\n{player_line}\n\n"
            f"Narration MJ — décris en 2-3 phrases courtes, à la troisième personne, "
            f"comment le joueur s'approche et s'installe avec ce groupe. Aucun "
            f"dialogue, aucun guillemet, aucun nom inventé.\n"
            f"Narration MJ :\n/no_think"
        )
    return (
        f"Lieu : « {location_name} ».\n"
        f"Mode : le joueur cherche à rejoindre un groupe, mais sa cible reste floue.\n\n"
        f"Action du joueur :\n{player_line}\n\n"
        f"Narration MJ — décris en 2-3 phrases courtes, à la troisième personne, "
        f"le joueur hésitant, regardant autour de lui sans encore se décider. Aucun "
        f"dialogue, aucun guillemet, aucun nom inventé.\n"
        f"Narration MJ :\n/no_think"
    )


def _load_mj_initiative_template(world_id: str, db: Session) -> Optional[PromptTemplate]:
    """Return the active mj_initiative prompt template, or None (initiative silently skipped)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "mj_initiative",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _load_npc_initiative_act_template(world_id: str, db: Session) -> Optional[PromptTemplate]:
    """Return the active npc_initiative_act template, or None (caller uses fallback constant)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "npc_initiative_act",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _load_mj_arbiter_template(world_id: str, db: Session) -> Optional[PromptTemplate]:
    """Return the active mj_arbitration prompt template, or None (caller falls back)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "mj_arbitration",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _load_mj_establishment_template(world_id: str, db: Session) -> Optional[PromptTemplate]:
    """Return the active mj_establishment prompt template, or None (caller skips narration)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "mj_establishment",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        return None
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _build_establishment_user(
    template: str,
    location_name: str,
    description: Optional[str],
    subculture: dict,
    signposts: list[str],
    changes: Optional[list[str]] = None,
) -> str:
    """Build the establishment user message (schema v1.30, BRIEF-17; `changes`
    added schema v1.71, BRIEF-0016-a).

    Reads `entity.description` (passed in by the caller), NOT
    `location.description` (no such column). Subculture is the SAME
    `_SAFE_SUBCULTURE_KEYS` allow-listed slice `assemble_mj_context` uses —
    not widened, "hidden" never read. `signposts` are the ONLY
    perceptible-detail material (from `active_signposts`, never a raw
    `subject`/`signpost_group`). `changes` is the code-computed return-visit
    delta (`_compute_return_delta`) — None/empty renders the placeholder,
    never an invented block.
    """
    ambiance = " ".join(str(v) for v in subculture.values() if v)
    sign_block = (
        "\n".join(f"- {s}" for s in signposts)
        if signposts
        else "(rien de particulier ne saute aux yeux)"
    )
    changes_block = (
        "\n".join(changes)
        if changes
        else "(rien de notable depuis votre dernière venue — ou première visite)"
    )
    return (
        template
        .replace("{location_name}", location_name)
        .replace("{description}", description or "")
        .replace("{subculture}", ambiance)
        .replace("{signposts}", sign_block)
        .replace("{changes}", changes_block)
    )


def _compute_return_delta(
    db: Session, world_id: str, player_id: str, location_id: str
) -> tuple[Optional[list[str]], list[str]]:
    """Code-computed return-visit delta (schema v1.71, BRIEF-0016-a, G2).

    Returns `(changes_lines_or_None, current_present_npc_ids)`. None means
    "no changes block" — either a first visit, or a visit with nothing to
    report; the model never sees an empty header to embroider on. Presence
    uses the tick's location-scope predicate VERBATIM (public, alive, active
    NPCs). Departed names resolve from `Entity` WITHOUT the alive/active
    filter (RECON-0016 F5) — the player saw them, their absence is public.
    The event leg applies the SAME structural exclusion as the only other
    Event reader (context.py) — secret events can never surface here.
    """
    previous = db.exec(
        select(Visit)
        .where(Visit.player_id == player_id, Visit.location_id == location_id)
        .order_by(Visit.entered_at.desc())
    ).first()

    current_rows = db.exec(
        select(Character)
        .join(Entity, Entity.id == Character.id)
        .where(
            Entity.world_id == world_id,
            Character.current_location_id == location_id,
            Character.character_type == "npc",
            Character.vital_status == "alive",
            Entity.status == "active",
        )
    ).all()
    current_ids = [c.id for c in current_rows]

    if previous is None:
        return None, current_ids

    def _names(ids: set) -> list[str]:
        names = []
        for eid in ids:
            entity = db.get(Entity, eid)
            if entity is not None:
                names.append(entity.name)
        return sorted(names)

    previous_ids = set(previous.present_npc_ids or [])
    current_set = set(current_ids)
    departed_names = _names(previous_ids - current_set)
    arrived_names = _names(current_set - previous_ids)

    lines: list[str] = []
    if departed_names:
        lines.append(f"- Parti·e·s depuis votre dernière visite : {', '.join(departed_names)}")
    if arrived_names:
        lines.append(f"- Arrivé·e·s : {', '.join(arrived_names)}")

    events = db.exec(
        select(Event)
        .where(
            Event.world_id == world_id,
            Event.location_id == location_id,
            Event.knowledge_status.in_(("public", "confirmed")),
            Event.recorded_at > previous.entered_at,
        )
        .order_by(Event.recorded_at)
    ).all()
    for e in events:
        line = f"- Événement : {e.title}"
        if e.description:
            first_sentence = e.description.split(".")[0].strip()
            if first_sentence:
                line += f" — {first_sentence}."
        lines.append(line)

    if not lines:
        return None, current_ids
    return lines, current_ids


def _build_establishment_narration(
    location_id: str,
    player_character_id: str,
    world_id: str,
    db: Session,
    *,
    changes: Optional[list[str]] = None,
) -> Optional[str]:
    """Entry narration (schema v1.30, BRIEF-17, F3/G1): a single non-streamed
    MJ call describing the scene the player perceives on entering. Fired on
    every entry; a failure must never block scene entry (resilience doctrine,
    same as the analysis passes). `changes` (schema v1.71, BRIEF-0016-a) is
    the code-computed return-visit delta, None on a re-render.
    """
    try:
        template = _load_mj_establishment_template(world_id, db)
        if template is None:
            return None
        loc_entity = db.get(Entity, location_id)
        location = db.get(Location, location_id)
        description = loc_entity.description if loc_entity else None
        subculture: dict = {}
        if location and isinstance(location.subculture, dict):
            subculture = {
                key: value
                for key, value in location.subculture.items()
                if key in _SAFE_SUBCULTURE_KEYS and value
            }
        signposts = active_signposts(db, location_id, player_character_id)
        version = current_prompt(db, template)
        user_msg = _build_establishment_user(
            version.user_template,
            loc_entity.name if loc_entity else location_id,
            description,
            subculture,
            signposts,
            changes,
        )
        raw = ollama_client.chat(
            [
                {"role": "system", "content": version.system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            model=effective_model(template, ollama_client.DEFAULT_MODEL),
        )
        narration = raw.strip()
        return narration or None
    except (Exception, SystemExit):
        _log.exception("Establishment narration failed for location %s", location_id)
        return None


# Hardcoded fallback used when the npc_initiative_act template is not yet seeded.
# Keeps initiative working on pre-C2 databases without requiring a seed re-run.
_NPC_INITIATIVE_ACT_FALLBACK = (
    "[MODE INITIATIVE] Tu prends l'initiative SPONTANÉMENT, sans qu'on te l'ait demandé.\n\n"
    "Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :\n"
    '{"act_text":"<ton acte spontané, 1 à 2 phrases, première personne>","move":false}\n\n'
    '"act_text" : ta parole ou ton geste spontané. 1 à 2 phrases, première personne.\n'
    "             Aucun mot inventé, aucun fait inventé — reste dans ta fiche de contexte.\n"
    '"move"     : true UNIQUEMENT si tu te lèves physiquement pour rejoindre le groupe du\n'
    "             joueur. false par défaut. En cas de doute, false."
)


def _npc_initiative_vote(
    *,
    template: PromptTemplate,
    location_name: str,
    members: list[tuple[GatheringMember, Entity]],
    non_member_ids: set[str],
    player_line: str,
    interpreted_mode: ResponseMode,
    player_id: str,
    model: str,
    db: Session,
) -> tuple[bool, Optional[str]]:
    """Ask the MJ if a bystander NPC takes spontaneous initiative this turn.

    Returns (act, entity_id). Resolves the model's answer against the active
    roster (A2-style: case-insensitive exact match on the list of names
    actually shown). Unresolved name → (False, None); never invents.

    Cadence E1: at most one NPC per turn. The caller is responsible for not
    calling this function more than once per turn.

    members = all_candidates (in-group + non-members from other open gatherings
    at the same location). non_member_ids identifies the non-member subset so
    the prompt labels the two classes distinctly and the caller can apply the
    structural move override.
    """
    if not members:
        return False, None

    npc_ids = [e.id for _gm, e in members]
    # Batch-query NPC→player relations for all candidates in one round-trip.
    all_rels = db.exec(
        select(Relation).where(
            ((Relation.entity_a_id.in_(npc_ids)) & (Relation.entity_b_id == player_id))
            | ((Relation.entity_b_id.in_(npc_ids)) & (Relation.entity_a_id == player_id))
        )
    ).all()

    def _npc_rel(npc_id: str) -> Optional[Relation]:
        for rel in all_rels:
            if rel.entity_a_id == npc_id and rel.direction in ("a_to_b", "mutual"):
                return rel
            if rel.entity_b_id == npc_id and rel.direction in ("b_to_a", "mutual"):
                return rel
        return None

    # BRIEF-0013-c (R1): one batched query for every candidate's most recent
    # ACTIVE short-term goal — long-term goals never enter the vote.
    all_short_goals = db.exec(
        select(NpcGoal)
        .where(NpcGoal.npc_id.in_(npc_ids), NpcGoal.horizon == "short", NpcGoal.status == "active")
        .order_by(NpcGoal.created_at.desc())
    ).all()
    goal_by_npc: dict[str, str] = {}
    for g in all_short_goals:
        goal_by_npc.setdefault(g.npc_id, g.description)

    def _signal_line(e: Entity) -> str:
        rel = _npc_rel(e.id)
        signal = f"relation={rel.type} ({rel.intensity}/100)" if rel else "relation=neutre (50/100)"
        goal_text = goal_by_npc.get(e.id)
        goal_frag = ""
        if goal_text:
            text = goal_text if len(goal_text) <= 80 else goal_text[:80] + "…"
            goal_frag = f", objectif=« {text} »"
        return f"- {e.name} : {signal}, statut={e.status}{goal_frag}"

    # Two-section signal list: in-group members react in place; non-members can
    # only intervene by approaching the player's gathering (structural move=True).
    group_lines   = [_signal_line(e) for _gm, e in members if e.id not in non_member_ids]
    distant_lines = [_signal_line(e) for _gm, e in members if e.id in non_member_ids]
    parts: list[str] = []
    if group_lines:
        parts.append(
            "DANS LE GROUPE DU JOUEUR (réagissent en restant sur place) :\n"
            + "\n".join(group_lines)
        )
    if distant_lines:
        parts.append(
            "DANS UN AUTRE GROUPE (ne peuvent intervenir QU'EN se levant pour rejoindre le groupe du joueur) :\n"
            + "\n".join(distant_lines)
        )

    version = current_prompt(db, template)
    user_msg = (
        version.user_template
        .replace("{location_name}", location_name)
        .replace("{interpreted_mode}", interpreted_mode.value)
        .replace("{player_line}", player_line)
        .replace("{member_signal_list}", "\n\n".join(parts))
        + "\n/no_think"
    )
    try:
        raw = ollama_client.chat(
            [
                {"role": "system", "content": version.system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            model=model,
            format="json",
        )
        obj = json.loads(raw)
        if not obj.get("act"):
            return False, None
        npc_name = str(obj.get("npc", "")).strip().lower()
        for _gm, e in members:
            if e.name.strip().lower() == npc_name:
                _log.info(
                    "MJ initiative: %s takes initiative (reason: %s)",
                    e.name, obj.get("reason", ""),
                )
                return True, e.id
        _log.info("MJ initiative: unresolved name %r → no initiative", npc_name)
        return False, None
    except Exception as exc:
        _log.warning("MJ initiative vote failed (%s) → no initiative", exc)
        return False, None


def _build_initiative_trigger(
    player_line: str,
    npc_reply: str,
    responder_name: Optional[str],
) -> str:
    """Scene-context message that triggers a spontaneous NPC initiative.

    The NPC acts without being addressed. This gives it scene context (what
    just happened in the room) so it can react authentically. This message is
    appended after npc_history; it is not stored as a permanent conversation
    message.

    C2: "depuis ta place" removed — the NPC may now choose to move (move=true
    in the JSON act object). Physical migration is handled by the caller.
    """
    if npc_reply and responder_name:
        return (
            f"[Contexte de scène : le joueur vient de dire/faire — {player_line}\n"
            f"{responder_name} vient de répondre — {npc_reply}\n"
            f"Tu prends maintenant l'initiative spontanément.]"
        )
    return (
        f"[Contexte de scène : le joueur vient de dire/faire — {player_line}\n"
        f"Tu prends maintenant l'initiative spontanément.]"
    )


def _build_initiative_mj_user(
    *,
    npc_name: str,
    location_name: str,
    initiative_line: str,
    player_line: str,
) -> str:
    """MJ narration user message for a spontaneous NPC initiative.

    Follows the same verbatim-quote contract as the main MJ narration template:
    the NPC's line is cited in full. /no_think is appended; the stream filter
    backs it up.
    """
    return (
        f"Scène : {npc_name} dans « {location_name} ».\n\n"
        f"Contexte : le joueur vient de faire/dire — {player_line}\n\n"
        f"{npc_name} intervient spontanément — cite cette réplique INTÉGRALEMENT "
        f"et VERBATIM, sans modifier ni supprimer un seul mot :\n{initiative_line}\n\n"
        f"Narration MJ :\n/no_think"
    )


def _load_mj_narration_template(world_id: str, db: Session) -> PromptTemplate:
    """Return the active player_narration (MJ) prompt template (world-specific preferred)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "player_narration",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        raise HTTPException(
            status_code=503,
            detail="No active 'player_narration' prompt template found. Run seed_pilot.py.",
        )
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


# ── Mode routing (MJ interpretation layer) ────────────────────────────────────

class ResponseMode(str, enum.Enum):
    """Classification of the player's input for routing a /say turn.

    Extensible: add new values here when more routing modes are needed (e.g.
    'address_different_npc'). Unknown values returned by the model fall back
    to 'dialogue' in _interpret_mode — new modes are backward-compatible
    without any change to the fallback logic.
    """
    dialogue     = "dialogue"      # player speaks / questions / solicits NPC reply
    npc_reaction = "npc_reaction"  # action toward NPC, no words → wordless NPC gesture
    scene        = "scene"         # environment action, NPC not engaged → skip NPC call
    join         = "join"          # player approaches and settles with a gathering;
                                    # only meaningful while ungrouped (see _stream)
    physical     = "physical"      # physical attempt with an uncertain outcome — climbing,
                                    # grabbing, dodging, forcing, sneaking, resisting; routed
                                    # to _arbitrate() + resolve_physical() (BRIEF-11)
    travel       = "travel"        # player intends to leave the current location for a
                                    # direct connects_to neighbour (BRIEF-16)


def _load_mj_interpret_template(world_id: str, db: Session) -> PromptTemplate:
    """Return the active mj_interpretation prompt template (world-specific preferred)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "mj_interpretation",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        raise HTTPException(
            status_code=503,
            detail="No active 'mj_interpretation' prompt template found. Run seed_pilot.py.",
        )
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _interpret_mode(
    *,
    player_line: str,
    npc_name: str,
    location_name: str,
    gathering_status: str,
    recent_transcript: str,
    item_list: str,
    interpret_system: str,
    interpret_user_tpl: str,
    model: str,
) -> tuple[ResponseMode, str, Optional[str]]:
    """Classify the player's input into a ResponseMode via the local model.

    Returns `(mode, reference, used_object)`.
    - `reference` is the model's free-text quote of what the player named
      when joining a group (contract A2 — resolved against the actual roster
      downstream by `_resolve_join_target`, never invented); empty for every
      other mode.
    - `used_object` (schema v1.19, simplified BRIEF-08/D2a.1): canonical name
      of the item the player physically uses this turn, `"unknown_object"` if
      the player's wording matches no item in `item_list`, or `None` if no
      object is in play. Fed to the code-side possession check in `_stream`.

    Falls back to `(ResponseMode.dialogue, "", None)` on any failure (parse
    error, unknown value, Ollama error). A misclassification must never break
    a turn.
    """
    user_msg = (
        interpret_user_tpl
        .replace("{npc_name}", npc_name)
        .replace("{location_name}", location_name)
        .replace("{gathering_status}", gathering_status)
        .replace("{item_list}", item_list)
        .replace("{recent_transcript}", recent_transcript or "(aucun historique)")
        .replace("{player_line}", player_line)
        + "\n/no_think"
    )
    try:
        raw = ollama_client.chat(
            [
                {"role": "system", "content": interpret_system},
                {"role": "user",   "content": user_msg},
            ],
            model=model,
            format="json",
        )
        obj = json.loads(raw)
        mode_str = str(obj.get("mode", "")).strip()
        mode = ResponseMode(mode_str)
        reference = str(obj.get("reference", "") or "").strip()

        used_object_raw = obj.get("used_object")
        used_object = str(used_object_raw).strip() if used_object_raw else None
        if used_object in ("null", ""):
            used_object = None

        _log.info(
            "MJ interpret: %r → %s (reason: %s)%s%s",
            player_line[:60], mode.value, obj.get("reason", ""),
            f" [reference: {reference!r}]" if mode == ResponseMode.join else "",
            f" [used_object: {used_object!r}]" if used_object else "",
        )
        return mode, reference, used_object
    except Exception as exc:
        _log.warning("MJ interpret failed (%s), fallback to dialogue", exc)
        return ResponseMode.dialogue, "", None


# ── Arbiter classification (physical resolution, BRIEF-11, schema v1.23) ──

_PHYSICAL_DOMAINS = BASE_SKILL_DOMAINS  # single source of truth (schema v1.63)


def _arbitrate(
    *,
    player_line: str,
    npc_list: str,
    name_to_id: dict[str, str],
    arbiter_system: str,
    arbiter_user_tpl: str,
    model: str,
    custom_skill_names: tuple[str, ...] = (),
) -> tuple[str, Optional[str], Optional[str], bool]:
    """Classify a `physical` turn into a domain and optional NPC opposition.

    The model sees only NPC names (never raw entity rows) and returns the
    name of the NPC it targets (or null) in `opposed_npc_id` — resolved here
    to an actual entity id via case-insensitive lookup in `name_to_id`, the
    same "exact match against the roster, never invented" pattern as
    `_resolve_join_target`'s `reference`.

    The model classifies ONLY; it never rolls and never decides outcomes. On
    any failure (bad JSON, unknown domain, Ollama error, timeout): falls back
    to `("physical", None, None, False)` — a misclassification must never
    break a turn.

    `custom_skill_names` (BRIEF-55, schema v1.63): the active world's
    `skill_definition.name` values, filled into the `pt-mj-arbiter` prompt's
    `{custom_skill_names}` placeholder and widening the domain clamp below —
    a returned `domain` may be a base domain OR one of these custom names.
    `(aucune)` when the world has none, and the arbiter behaves byte-for-byte
    as before (1-C).

    Returns (domain, opposed_npc_id, applies_constraint, violent):
    - domain: a base domain (BASE_SKILL_DOMAINS) or a custom skill name.
    - applies_constraint (BRIEF-12): the constraint that would be applied on
      failure (e.g. "restrained" if an NPC is trying to pin the player), or
      None if no constraint stake. Only valid values from _VALID_CONSTRAINTS.
    - violent (BRIEF-12): True if the action involves a risk of physical harm
      to the player (blow, weapon, fall, combat). Drives condition degradation
      on failure.
    """
    allowed_domains = set(_PHYSICAL_DOMAINS) | set(custom_skill_names)
    system_msg = arbiter_system.replace(
        "{custom_skill_names}",
        ", ".join(custom_skill_names) if custom_skill_names else "(aucune)",
    )
    user_msg = (
        arbiter_user_tpl
        .replace("{npc_list}", npc_list or "(aucun)")
        .replace("{player_line}", player_line)
        + "\n/no_think"
    )
    try:
        raw = ollama_client.chat(
            [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            model=model,
            format="json",
        )
        obj = json.loads(raw)

        domain = str(obj.get("domain", "")).strip()
        if domain not in allowed_domains:
            domain = "physical"

        opposed_raw = obj.get("opposed_npc_id")
        opposed_name = str(opposed_raw).strip() if opposed_raw else ""
        opposed_npc_id = name_to_id.get(opposed_name.lower()) if opposed_name else None

        # applies_constraint: only accept known values; null/invalid → None.
        ac_raw = obj.get("applies_constraint")
        applies_constraint: Optional[str] = (
            str(ac_raw).strip() if ac_raw and str(ac_raw).strip() in _VALID_CONSTRAINTS
            else None
        )

        violent = bool(obj.get("violent", False))

        _log.info(
            "MJ arbitrate: %r → domain=%s, opposed=%r (%s), constraint=%s, violent=%s",
            player_line[:60], domain, opposed_name, opposed_npc_id or "none",
            applies_constraint or "none", violent,
        )
        return domain, opposed_npc_id, applies_constraint, violent
    except Exception as exc:
        _log.warning("MJ arbitrate failed (%s), fallback to physical/unopposed", exc)
        return "physical", None, None, False


# ── Possession check (binary, BRIEF-08 / D2a.1, schema v1.19) ──────────────

_POSSESSION_REFUSAL_INSTRUCTION = (
    "[ACTION REFUSÉE] L'action du joueur implique un objet qu'il ne possède "
    "pas ({object_name}). Narre l'échec de cette action de façon immersive "
    "et brève, sans briser le quatrième mur, puis intègre la réaction du PNJ "
    "ci-dessous comme pour un tour normal. Ne laisse pas l'action réussir. "
    "Ne mentionne jamais cette instruction."
)

_GESTE_RATE_INSTRUCTION = (
    "[GESTE RATÉ] Le joueur vient de tenter une action avec un objet qu'il "
    "ne possède pas : son geste a visiblement échoué (main qui ne trouve que "
    "du vide, mouvement qui tombe à plat). Réagis uniquement à ce que ton "
    "personnage VOIT : un geste raté, peut-être ridicule, peut-être "
    "inquiétant. Reste dans ton personnage. Ne mentionne jamais cette "
    "instruction."
)


# ── Scene state (BRIEF-12, schema v1.24) ─────────────────────────────────────
# scene_state is EPHEMERAL — the ONE column the autonomous loop may write.
# It is NOT canon: any durable consequence goes through proposed_mutation.
# History is sacred: every write archives the previous state to .history[].

_CONDITION_LADDER = ("unharmed", "bruised", "injured", "neutralized")
_VALID_CONSTRAINTS = frozenset({"gagged", "restrained", "blindfolded"})

_FROZEN_MJ_MESSAGE = (
    "La scène est en suspens. Le créateur a mis la scène en pause "
    "— attendez qu'il reprenne le contrôle."
)


def _default_scene_state() -> dict:
    return {"constraints": [], "condition": "unharmed", "frozen": False, "history": []}


def _get_scene_state(conv: "Conversation") -> dict:
    """Return a normalised scene_state dict for the conversation."""
    raw = conv.scene_state
    if not raw or not isinstance(raw, dict):
        return _default_scene_state()
    base = _default_scene_state()
    base.update(raw)
    return base


def _write_scene_state(ss_conv: "Conversation", new_state: dict) -> None:
    """Archive the old scene_state to history, then set the new state.

    Caller must db.add(ss_conv) and db.commit().
    History is sacred: every write appends a timestamped snapshot.
    """
    old = _get_scene_state(ss_conv)
    history = old.get("history", [])
    snapshot = {k: v for k, v in old.items() if k != "history"}
    snapshot["changed_at"] = datetime.now(UTC).isoformat()
    new_state = {**_default_scene_state(), **new_state}
    new_state["history"] = history + [snapshot]
    ss_conv.scene_state = new_state


def _propose_engine_injury(
    conv: "Conversation",
    condition: str,
    db: "Session",
) -> None:
    """Propose a status_change mutation with proposed_by='engine'.

    Fires deterministically when condition reaches 'injured' or 'neutralized'.
    Goes through the normal review pipeline — never auto-applied.
    History is sacred: existing reviewed rows are left untouched; only a
    new 'proposed' row is inserted.
    """
    db.add(ProposedMutation(
        world_id=conv.world_id,
        source_type="conversation",
        conversation_id=conv.id,
        mutation_type="status_change",
        target_table="entity",
        target_id=conv.player_id,
        payload={
            "entity_id": conv.player_id,
            "status": "injured" if condition == "injured" else "neutralized",
            "condition_reached": condition,
            "scene_origin": "physical_verdict",
        },
        rationale=(
            f"Condition reached '{condition}' during physical resolution. "
            "A lasting consequence may be appropriate — review and decide."
        ),
        proposed_by="engine",
    ))


def _propose_engine_discovery(
    conv: "Conversation",
    detail: "DiscoverableDetail",
    db: "Session",
) -> None:
    """Propose a new_knowledge mutation with proposed_by='engine'.

    Fires deterministically when a perception search finds an undiscovered
    hidden detail. Goes through the normal review pipeline — never auto-applied.
    The discoverable_detail_id back-reference in the payload lets _apply_mutation
    flip detail.discovered to TRUE when the creator approves (see that branch).
    """
    db.add(ProposedMutation(
        world_id=conv.world_id,
        source_type="conversation",
        conversation_id=conv.id,
        mutation_type="new_knowledge",
        target_table="entity",
        target_id=conv.player_id,
        payload={
            "entity_id": conv.player_id,
            "subject": detail.subject,
            "level": "knows",
            "content": detail.content,
            "source": "discovery",
            "is_secret": False,
            "discoverable_detail_id": detail.id,
        },
        rationale=(
            f"Perception search in location {conv.location_id!r}: "
            f"detail '{detail.subject}' found."
        ),
        proposed_by="engine",
    ))


def _find_player_item(db: Session, player_id: str, item_name: str) -> Optional[tuple[Item, Entity]]:
    """Resolve a canonical item name (`_interpret_mode`'s `used_object`) to
    the player's owned `item` + `entity` rows, or `None` if not owned.

    Possession is binary since BRIEF-08/D2a.1 — `item.equipped` is no longer
    read by the check (dormant, cockpit-only).
    """
    return db.exec(
        select(Item, Entity)
        .join(Entity, Entity.id == Item.id)
        .where(Item.owner_id == player_id, Entity.name == item_name)
    ).first()


def _build_refusal_instruction(object_name: Optional[str]) -> str:
    """One-shot MJ instruction for a possession-check refusal — not
    persisted, same pattern as [MODE RÉACTION NON-VERBALE].

    `object_name` is the canonical item name when known; `None` for
    `unknown_object` (the player's wording matched nothing in `item_list`).
    """
    return _POSSESSION_REFUSAL_INSTRUCTION.format(object_name=object_name or "cet objet")


def _build_mj_user(
    *,
    mode: ResponseMode,
    mj_user_template: str,
    npc_name: str,
    location_name: str,
    player_line: str,
    npc_reply: str,
    mj_context: dict | None = None,
    inventory_line: str = "",
    verdict_band: Optional[str] = None,
    search_rubric: Optional[str] = None,
    travel_instruction: Optional[str] = None,
) -> str:
    """Build the MJ narration user message for the given mode.

    dialogue     → existing template (verbatim NPC quote contract unchanged).
    npc_reaction → third-person wordless reaction; no dialogue to quote.
    scene        → environment description only; NPC not involved.
    physical     → verdict-constrained narration (BRIEF-11); `verdict_band`
                   ("failure" | "partial" | "success") is required for this
                   mode and injects the verbatim resolution rubric.
    travel       → departure-only narration (BRIEF-16); `travel_instruction`
                   carries the one-shot [DÉPART] / [DÉPART INCERTAIN] /
                   [SORTIE INTROUVABLE] directive (not persisted).

    `mj_context` (schema v1.12, scope D-b3): the dict returned by
    `assemble_mj_context`, rendered via `format_mj_context` and prepended as
    a "CONTEXTE DE SCÈNE" block — the player's perception boundary (location,
    co-presents, player knowledge, public events). Empty/None → no block.
    `scene` mode benefits most (environment prose finally has material).

    `inventory_line` (schema v1.18, BRIEF-06): the player's static inventory
    line (`format_inventory_line`), read fresh every turn — never cached.
    Prepended ahead of the scene description in every mode.

    /no_think appended on all modes; the stream filter backs it up.
    """
    context_block = format_mj_context(mj_context) if mj_context else ""
    if context_block:
        context_block = f"=== CONTEXTE DE SCÈNE ===\n{context_block}\n"

    inventory_block = f"{inventory_line}\n" if inventory_line else ""

    if mode == ResponseMode.dialogue:
        return (
            mj_user_template
            .replace("{mj_context}", context_block)
            .replace("{inventory_line}", inventory_block)
            .replace("{npc_name}", npc_name)
            .replace("{location_name}", location_name)
            .replace("{player_line}", player_line)
            .replace("{npc_reply}", npc_reply)
            + "\n/no_think"
        )
    if mode == ResponseMode.npc_reaction:
        return (
            f"{context_block}"
            f"{inventory_block}"
            f"Scène : {npc_name} dans « {location_name} ».\n"
            f"Mode : réaction non-verbale.\n\n"
            f"Le joueur fait :\n{player_line}\n\n"
            f"{npc_name} réagit sans prononcer un mot :\n{npc_reply}\n\n"
            f"Narration MJ — traduis cette réaction en prose narrative à la troisième "
            f"personne. Aucun guillemet français, aucune ligne de dialogue, aucun mot "
            f"inventé. 2–3 phrases courtes.\n"
            f"Narration MJ :\n/no_think"
        )
    if mode == ResponseMode.physical:
        band = verdict_band or "failure"
        npc_reaction_block = (
            f"{npc_name} réagit :\n{npc_reply}\n\n" if npc_reply else ""
        )
        search_rubric_block = f"\n{search_rubric}\n" if search_rubric else ""
        return (
            f"{context_block}"
            f"{inventory_block}"
            f"Lieu : « {location_name} ».\n"
            f"Mode : résolution physique.\n\n"
            f"Action du joueur :\n{player_line}\n\n"
            f"{npc_reaction_block}"
            f"[RÉSOLUTION PHYSIQUE — VERDICT IMPOSÉ]\n"
            f"Résultat mécanique : {band}.\n"
            f"- failure : l'action échoue. Ne l'adoucis pas en demi-réussite.\n"
            f"- partial : l'action réussit MAIS avec un coût, une complication ou\n"
            f"  une position dégradée, OU échoue avec un avantage inattendu.\n"
            f"- success : l'action réussit nettement.\n"
            f"Tu narres les conséquences ; tu ne rejuges JAMAIS le résultat.\n"
            f"Aucune mort, blessure permanente ou capture durable ne peut découler\n"
            f"de cette narration : au pire, neutralisé ou contraint.{search_rubric_block}\n\n"
            f"Narration MJ :\n/no_think"
        )
    if mode == ResponseMode.travel and travel_instruction:
        return (
            f"{context_block}"
            f"{inventory_block}"
            f"Lieu : « {location_name} ».\n\n"
            f"Action du joueur :\n{player_line}\n\n"
            f"{travel_instruction}\n\n"
            f"Narration MJ :\n/no_think"
        )
    # ResponseMode.scene (also used for zero-neighbour travel downgrade via scene template)
    return (
        f"{context_block}"
        f"{inventory_block}"
        f"Lieu : « {location_name} ».\n"
        f"Mode : description d'environnement — le PNJ n'est pas impliqué.\n\n"
        f"Action du joueur :\n{player_line}\n\n"
        f"Narration MJ — décris le résultat de cette action sur l'environnement en "
        f"troisième personne, en t'appuyant sur le CONTEXTE DE SCÈNE ci-dessus s'il "
        f"est fourni. N'implique pas le PNJ, n'invente aucun fait au-delà de ce "
        f"contexte, aucun nom propre. 2–3 phrases courtes.\n"
        f"Narration MJ :\n/no_think"
    )


class StartConversationBody(BaseModel):
    npc_id: str
    # Defaults: pilot player and tavern location (set by /start handler).
    location_id: Optional[str] = None
    player_id: Optional[str] = None


@app.post("/api/conversations/start")
def start_conversation(
    body: StartConversationBody,
    db: Session = Depends(get_session),
) -> dict:
    """Create and open a new conversation between the player and an NPC.

    Assembles the NPC context via assemble_npc_context (same as talk.py) and
    stores it in injected_context for audit and for the /say handler to reuse.

    Defaults: player = the active world's resolved player character, location
    = loc-dernier-verre. These defaults are the pilot setup; a future player
    view will pass explicit IDs from the player's active session instead.
    """
    # Resolve defaults (pilot player / pilot location).
    player_id   = body.player_id   or _crud._player_character_id(db, _crud._world_id(db))
    location_id = body.location_id or "loc-dernier-verre"

    npc_entity = db.get(Entity, body.npc_id)
    if npc_entity is None:
        raise HTTPException(status_code=404, detail=f"NPC {body.npc_id!r} not found")
    npc_char = db.get(Character, body.npc_id)
    if npc_char is None or npc_char.character_type != "npc":
        raise HTTPException(status_code=400, detail=f"{body.npc_id!r} is not an NPC character")

    world_id = npc_entity.world_id
    sess = _get_or_open_session(world_id, db)

    behaviour = _load_npc_dialogue_template(world_id, db)
    behaviour_version = current_prompt(db, behaviour)
    assembled_context = assemble_npc_context(body.npc_id, player_id, location_id, db)
    system_prompt = _npc_dialogue_system_prompt(behaviour_version.system_prompt, assembled_context)

    # MJ context snapshot (schema v1.12, scope D-b3): static parts only
    # (location, player_knowledge, public_events) — co_presents is dynamic
    # and read fresh at narration time, never snapshotted. This is what a
    # future bleed auditor compares MJ narration against.
    mj_context = assemble_mj_context(db, player_id, location_id)
    mj_snapshot = {k: v for k, v in mj_context.items() if k != "co_presents"}

    # npc_dialogue's resolved model (BRIEF-0008-a): captured once here, into
    # injected_context["model"], and read back unwired at the say-turn
    # boundary in `say()` (`model = injected.get("model", ...)`, exempted by
    # construction — see the comment there).
    model = effective_model(behaviour, ollama_client.DEFAULT_MODEL)
    conv = Conversation(
        world_id=world_id,
        session_id=sess.id,
        location_id=location_id,
        player_id=player_id,
        npc_id=body.npc_id,
        status="open",
        injected_context={
            "model": model,
            "npc_id": body.npc_id,
            "interlocutor_id": player_id,
            "location_id": location_id,
            "prompt_template_id": behaviour.id,
            "behaviour_prompt": behaviour_version.system_prompt,
            "assembled_context": assembled_context,
            "system_prompt": system_prompt,
            "mj": mj_snapshot,
        },
        started_at=datetime.now(UTC),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"conversation_id": conv.id}


class SayBody(BaseModel):
    content: str
    # Speaker target (contract A3 hybrid — cockpit selector, contract C2):
    #   None / absent → the conversation's seed NPC (conv.npc_id) — backward
    #     compatible with plain 1:1 conversations.
    #   "group"       → addresses the gathering; the MJ picks exactly one
    #     active member to answer (requires the player to have joined one).
    #   <entity id>   → addresses that NPC directly; it answers.
    target: Optional[str] = None


class JoinBody(BaseModel):
    gathering_id: str


@app.post("/api/conversations/{conv_id}/say")
def say(
    conv_id: str,
    body: SayBody,
    db: Session = Depends(get_session),
) -> StreamingResponse:
    """Persist the player's line, interpret its mode, conditionally run an NPC,
    then stream the MJ narration.

    Mode routing (MJ interpretation pass — runs before any NPC)
    ------------------------------------------------------------
    'dialogue'     : player speaks / questions an NPC. The NPC replies in full.
    'npc_reaction' : action toward an NPC without words. It reacts wordlessly.
    'scene'        : environment action, no NPC engaged. NPC call is skipped.
    'join'         : player approaches and settles with an open gathering —
                     only considered while the player belongs to none yet
                     ("parler n'a pas de cible tant qu'on n'a pas rejoint").
                     No NPC call; the MJ narrates the approach. The reference
                     the player used is resolved against the gatherings
                     actually present (contract A2 — exact, case-insensitive,
                     never invented); on failure the cockpit shows a picker
                     (`join_candidates` event, completed via POST .../join).
    'travel'       : player intends to leave the current location. No NPC call;
                     MJ narrates the departure only (arrival is step C,
                     deferred). Resolved against direct connects_to neighbours
                     (contract A2 — exact, never guessed); on ambiguity shows
                     picker (`travel_candidates` event, completed via POST
                     .../travel). Under `restrained`, rerouted to physical.
    Fallback: 'dialogue' on any interpretation error (never breaks a turn).

    Speaker selection for dialogue / npc_reaction (contract A3 hybrid)
    -------------------------------------------------------------------
    `body.target` drives who answers:
      - omitted/None : the conversation's seed NPC (`conv.npc_id`) — plain 1:1.
      - "group"      : addresses the player's gathering; the MJ picks exactly
                       one active member to answer this turn (cadence B1 — one
                       responder, no PNJ↔PNJ exchange, that's Tier 3).
      - <entity id>  : addresses that NPC directly; it answers.
    Each responding NPC gets a freshly assembled context (contract D1 —
    co-participants of its current gathering are injected) and produces its
    canonical `npc` line under its own `speaker_id`.

    SSE protocol (text/event-stream):
      - No events while interpreting + NPC (if called) is generating (indicator up).
      - Each MJ narration token: data: <JSON-encoded string>\\n\\n
      - Mode event (before DONE): data: {"mode": "<value>"}\\n\\n
        — tells the browser WHY a turn produced no NPC dialogue.
      - Raw NPC line event (before DONE): data: {"npc_raw": "<escaped>"}\\n\\n
        — empty string when no NPC was called.
      - Join outcome (join mode only, before DONE):
          data: {"joined": {"gathering_id":..., "label":...}}\\n\\n        — resolved
          data: {"join_candidates": [{"id":..., "label":..., "members":[...]}]}\\n\\n — ambiguous
      - Travel outcome (travel mode only, before DONE):
          data: {"traveled": {"location_id":..., "name":...}}\\n\\n           — resolved, player moved
          data: {"travel_candidates": [{"id":..., "name":...}]}\\n\\n          — ambiguous, picker
      - Initiative events (gathering scenes, before DONE — Tier 3 step 1 C1):
          data: {"initiative_start": {"npc_name": "<name>"}}\\n\\n  — bystander NPC acts
          data: <JSON token>\\n\\n  (initiative MJ narration, same format as main tokens)
          data: {"initiative_npc_raw": "<escaped>"}\\n\\n  — raw NPC line for creator audit
      - End of stream: data: [DONE]\\n\\n
      - Error event: data: {"error": "<msg>"}\\n\\n

    turn_order layout per player turn:
      player_turn   → player line (canonical)
      player_turn+1 → npc line (canonical, internal; absent when no NPC answers)
      player_turn+2 → mj line (presentation, streamed; persisted after [DONE])
      player_turn+3 → initiative npc line (canonical; absent when no initiative)
      player_turn+4 → initiative mj line (presentation; absent when no initiative)
    """
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.status != "open":
        raise HTTPException(status_code=400, detail="Conversation is already closed")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Player line must not be empty")

    # Determine next turn_order.
    last_msg = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conv_id)
        .order_by(ConversationMessage.turn_order.desc())
    ).first()
    player_turn = (last_msg.turn_order + 1) if last_msg else 1

    # Persist the player message immediately (before streaming starts).
    db.add(ConversationMessage(
        conversation_id=conv_id,
        turn_order=player_turn,
        speaker="player",
        speaker_id=conv.player_id,
        content=content,
    ))
    db.commit()

    # Build the NPC message list: system prompt + player/npc history only.
    # 'mj' rows are presentation-only and must not be fed back to the NPC model.
    injected = conv.injected_context or {}
    system_prompt = injected.get("system_prompt", "")
    # Exemption, by construction (BRIEF-0008-a): NOT wired through
    # effective_model. This value was already resolved once, at conversation
    # start (see the `model = effective_model(behaviour, ...)` sites above);
    # re-wiring it here would silently encode a `template.model` vs
    # `injected_context["model"]` precedence for every downstream call in
    # this function and `_stream()` — a decision deferred to the write-path
    # chantier (verify/checks/prompt_registry.py allowlists this function and
    # `_stream`, plus the pass-through helpers `_interpret_mode`, `_arbitrate`,
    # `_npc_initiative_vote`, `_select_group_speaker`, which all consume this
    # same already-resolved value via their own `model` parameter).
    model = injected.get("model", ollama_client.DEFAULT_MODEL)

    all_msgs = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conv_id)
        .order_by(ConversationMessage.turn_order)
    ).all()
    npc_history = [
        {"role": "user" if m.speaker == "player" else "assistant", "content": m.content}
        for m in all_msgs
        if m.speaker in ("player", "npc")
    ]
    npc_messages = [{"role": "system", "content": system_prompt}, *npc_history]

    # Turn order slots (npc_turn may remain unused for scene turns).
    npc_id    = conv.npc_id
    npc_turn  = player_turn + 1
    mj_turn   = player_turn + 2

    # Load templates (both raise HTTP 503 if missing — before stream opens).
    world_id = conv.world_id
    mj_template        = _load_mj_narration_template(world_id, db)
    interpret_template = _load_mj_interpret_template(world_id, db)

    # Resolve display names for the MJ prompt.
    # npc_id may be None for pure gathering conversations (conv started from
    # the scene-level join without a seed NPC — see POST /api/scene/join).
    npc_entity    = db.get(Entity, npc_id) if npc_id else None
    npc_name: str = (
        npc_entity.name if npc_entity
        else (npc_id or "le groupe")  # gathering conv: use "le groupe" as display name
    )
    loc_entity    = db.get(Entity, conv.location_id) if conv.location_id else None
    location_name = loc_entity.name if loc_entity else "inconnu"

    # Recent player/npc transcript for the interpret call (excludes 'mj' rows
    # and the current player line, which is passed separately as {player_line}).
    # Multi-NPC scenes mean different turns may have different speakers — each
    # 'npc' row is labelled with its own speaker_id's name, not conv.npc_id.
    history_only = [m for m in all_msgs if m.speaker in ("player", "npc")][:-1]
    history_speaker_ids = {m.speaker_id for m in history_only if m.speaker == "npc" and m.speaker_id}
    history_name_map: dict[str, str] = {}
    if history_speaker_ids:
        history_name_map = {
            e.id: e.name for e in db.exec(select(Entity).where(Entity.id.in_(history_speaker_ids))).all()
        }
    recent_transcript = "\n".join(
        (f"[Joueur] {m.content}" if m.speaker == "player"
         else f"[{history_name_map.get(m.speaker_id or '', npc_name)}] {m.content}")
        for m in history_only[-6:]  # last 3 exchanges
    )

    # Capture for closure.
    mj_version         = current_prompt(db, mj_template)
    interpret_version  = current_prompt(db, interpret_template)
    mj_user_template   = mj_version.user_template
    mj_system_prompt   = mj_version.system_prompt
    interpret_system   = interpret_version.system_prompt
    interpret_user_tpl = interpret_version.user_template

    def _stream() -> Iterator[str]:
        # ── BRIEF-12: read scene_state — drives frozen check + constraint gating ──
        scene_state = _get_scene_state(conv)
        ss_constraints = set(scene_state.get("constraints", []))
        ss_condition   = scene_state.get("condition", "unharmed")

        # ── Frozen scene: no model calls, fixed message ────────────────────────
        if scene_state.get("frozen"):
            yield f"data: {json.dumps(_FROZEN_MJ_MESSAGE)}\n\n"
            yield f"data: {json.dumps({'mode': 'frozen'})}\n\n"
            yield f"data: {json.dumps({'npc_raw': ''})}\n\n"
            yield "data: [DONE]\n\n"
            with Session(engine) as persist_db:
                persist_db.add(ConversationMessage(
                    conversation_id=conv_id,
                    turn_order=mj_turn,
                    speaker="mj",
                    speaker_id=None,
                    content=_FROZEN_MJ_MESSAGE,
                ))
                persist_db.commit()
            return

        # ── Phase 0a: gathering membership (multi-NPC scenes, schema v1.8) ────
        # Drives both join-priority and speaker selection below. A conversation
        # with no location (shouldn't happen in the pilot) simply has no gatherings.
        player_gathering: Optional[Gathering] = None
        open_gatherings: list[Gathering] = []
        if conv.location_id:
            player_gathering = _player_gathering(conv.player_id, conv.location_id, conv.session_id, db)
            open_gatherings = _open_gatherings(conv.location_id, conv.session_id, db)
        gathering_status = _render_gathering_status(conv.player_id, player_gathering, open_gatherings, db)

        # ── Phase 0b: Interpret the player's input (mode routing) ─────────────
        # Classify as dialogue / npc_reaction / scene / join before calling any
        # NPC. Falls back to 'dialogue' on any failure — a misclassification
        # must never break a turn.
        item_list = format_item_list_for_interpretation(db, conv.player_id)
        mode, reference, used_object = _interpret_mode(
            player_line=content,
            npc_name=npc_name,
            location_name=location_name,
            gathering_status=gathering_status,
            recent_transcript=recent_transcript,
            item_list=item_list,
            interpret_system=interpret_system,
            interpret_user_tpl=interpret_user_tpl,
            model=model,
        )
        # 'join' is only meaningful while ungrouped — a misclassification while
        # already in a gathering degrades to dialogue (never breaks a turn).
        if mode == ResponseMode.join and player_gathering is not None:
            mode = ResponseMode.dialogue

        # ── BRIEF-12: constraint gating (before possession check) ─────────────
        # Gagged → any dialogue attempt re-routes to a composure roll (trying to
        # speak through the gag). Restrained → any movement/physical/environment
        # intent re-routes to an escape physical roll. These overrides happen
        # AFTER interpretation so the player's text is still fed to the model
        # for classification; the constraint then overrides the routing outcome.
        is_gagged_attempt   = False   # True: re-routed dialogue via gagged
        is_escape_attempt   = False   # True: re-routed movement via restrained
        if "gagged" in ss_constraints and mode == ResponseMode.dialogue:
            mode = ResponseMode.physical
            is_gagged_attempt = True
        elif "restrained" in ss_constraints and mode in (
            ResponseMode.physical, ResponseMode.scene, ResponseMode.npc_reaction,
            ResponseMode.travel,
        ):
            mode = ResponseMode.physical
            is_escape_attempt = True

        # ── Phase 0c: possession check (binary, BRIEF-08 / D2a.1) ──────────────
        # Code judges possession against canon `item` rows — the structural
        # fix for the D1 finding that the 8b model does not reliably honor
        # prohibition rules in free-text narration. `used_object` owned by the
        # player → pass; not owned or `unknown_object` → refused. The
        # equipped/stowed distinction is dormant — `item.equipped` is not read.
        # A refusal no longer skips the NPC phase: the gesture is socially
        # visible, so the turn proceeds as a normal dialogue turn with a
        # one-shot [GESTE RATÉ] instruction telling the NPC what it just saw.
        refusal_instruction: Optional[str] = None
        if mode != ResponseMode.join and not (is_gagged_attempt or is_escape_attempt) and used_object is not None:
            if used_object == "unknown_object":
                refusal_instruction = _build_refusal_instruction(None)
            elif _find_player_item(db, conv.player_id, used_object) is None:
                refusal_instruction = _build_refusal_instruction(used_object)

        if refusal_instruction is not None:
            mode = ResponseMode.dialogue

        npc_reply = ""
        responder_id: Optional[str] = None
        responder_name = npc_name
        extra_event: Optional[dict] = None
        travel_dest_id: Optional[str] = None   # set for resolved direct travel

        # ── Phase 0c: join handling — takes priority while ungrouped ──────────
        # "Parler n'a pas de cible tant qu'on n'a pas rejoint": joining is an
        # action, not dialogue — narrated in third person, no NPC call, and
        # forms/anchors no canon mutation (see ARCHITECTURE_DECISIONS.md).
        if mode == ResponseMode.join:
            resolved_id = _resolve_join_target(reference, open_gatherings, db)
            if resolved_id is not None:
                gathering = _join_gathering(conv, resolved_id, db)
                extra_event = {"joined": {"gathering_id": gathering.id, "label": gathering.label}}
                mj_user = _build_join_narration_user(
                    location_name=location_name, player_line=content,
                    joined=True, gathering_label=gathering.label,
                )
            else:
                extra_event = {
                    "join_candidates": [_gathering_brief(g.id, db) for g in open_gatherings]
                }
                mj_user = _build_join_narration_user(
                    location_name=location_name, player_line=content,
                    joined=False, gathering_label=None,
                )
        elif mode == ResponseMode.travel:
            # ── Travel: intent → direct-neighbour resolution → picker fallback ──
            # (BRIEF-16) No NPC phase. MJ narrates departure only; arrival is
            # step C (deferred). Restrained turns are intercepted above and
            # rerouted to physical before reaching here.
            neighbours = _location_neighbours(conv.location_id, db)
            mj_context_travel = (
                assemble_mj_context(
                    db, conv.player_id, conv.location_id,
                    gathering_id=player_gathering.id if player_gathering else None,
                    blindfolded="blindfolded" in ss_constraints,
                    player_condition=ss_condition,
                )
                if conv.location_id else None
            )
            inventory_line_travel = format_inventory_line(db, conv.player_id)

            if not neighbours:
                # No exits — downgrade to scene so the SSE mode reflects it;
                # the [SORTIE INTROUVABLE] instruction prevents the MJ from
                # inventing exits or moving the player.
                mode = ResponseMode.scene
                mj_user = _build_mj_user(
                    mode=ResponseMode.travel,
                    mj_user_template=mj_user_template,
                    npc_name=responder_name,
                    location_name=location_name,
                    player_line=content,
                    npc_reply="",
                    mj_context=mj_context_travel,
                    inventory_line=inventory_line_travel,
                    travel_instruction=(
                        "[SORTIE INTROUVABLE] Le joueur cherche à quitter le lieu "
                        "mais aucune sortie évidente ne se présente. Narre sa "
                        "recherche d'une issue sans en inventer une ; il reste sur place."
                    ),
                )
            else:
                dest_id = _resolve_travel_target(reference, neighbours)
                if dest_id is not None:
                    dest_name = next(name for eid, name in neighbours if eid == dest_id)
                    extra_event = {"traveled": {"location_id": dest_id, "name": dest_name}}
                    travel_dest_id = dest_id
                    mj_user = _build_mj_user(
                        mode=ResponseMode.travel,
                        mj_user_template=mj_user_template,
                        npc_name=responder_name,
                        location_name=location_name,
                        player_line=content,
                        npc_reply="",
                        mj_context=mj_context_travel,
                        inventory_line=inventory_line_travel,
                        travel_instruction=(
                            f"[DÉPART] Le joueur quitte {location_name} en direction de "
                            f"{dest_name}. Narre uniquement son départ (il se lève, sort, "
                            f"s'éloigne) — ne décris PAS le lieu d'arrivée ni ce qu'il y trouve."
                        ),
                    )
                else:
                    extra_event = {
                        "travel_candidates": [
                            {"id": eid, "name": name} for eid, name in neighbours
                        ]
                    }
                    mj_user = _build_mj_user(
                        mode=ResponseMode.travel,
                        mj_user_template=mj_user_template,
                        npc_name=responder_name,
                        location_name=location_name,
                        player_line=content,
                        npc_reply="",
                        mj_context=mj_context_travel,
                        inventory_line=inventory_line_travel,
                        travel_instruction=(
                            "[DÉPART INCERTAIN] Le joueur cherche à partir mais hésite sur "
                            "la direction. Narre brièvement ce moment de pause au seuil, "
                            "sans le faire bouger ni nommer de destination."
                        ),
                    )

        elif mode == ResponseMode.physical:
            # ── Arbiter classification + Python dice (BRIEF-11, schema v1.23) ──
            # Candidate NPC roster for opposition: the player's gathering
            # (excluding the player) if grouped, else the conversation's seed
            # NPC for plain 1:1 scenes. Names only — never raw entity rows.
            if player_gathering is not None:
                physical_npc_entities = [
                    e for _gm, e in _active_members(player_gathering.id, db)
                    if e.id != conv.player_id
                ]
            elif npc_entity is not None:
                physical_npc_entities = [npc_entity]
            else:
                physical_npc_entities = []
            physical_name_to_id = {e.name.lower(): e.id for e in physical_npc_entities}
            physical_npc_list = ", ".join(e.name for e in physical_npc_entities)

            # BRIEF-55 (5a, schema v1.63): dynamic candidate list — the active
            # world's custom skill definitions, injected into the arbiter
            # prompt as fillable text and used to widen the domain clamp.
            world_skill_defs = db.exec(
                select(SkillDefinition).where(SkillDefinition.world_id == world_id)
            ).all()
            world_skill_defs_by_name = {d.name: d for d in world_skill_defs}
            world_custom_skill_names = tuple(world_skill_defs_by_name)

            # BRIEF-12: constraint-gated turns bypass the arbiter — domain and
            # opposition are already determined by the constraint effect.
            # Gated attempts (gagged speech, escape from restraint) resolve against a
            # fixed npc_tier = 1 — NOT 0. At player_tier 0 this shifts failure 41% -> 58%,
            # making a gated attempt harder than an unopposed roll, which is the intended
            # "contested resolution" for acting against a constraint. The 1/1 value is a
            # deliberate pilot simplification: a gag (object) and a grip (person) are
            # different resistances but share one tier for now. True provenance — escape
            # rolling against the captor's physical_tier — is deferred (see changelog);
            # the "highest-tier NPC in the gathering" heuristic is explicitly rejected as
            # false certainty (the strongest present NPC is not necessarily the captor).
            applies_constraint: Optional[str] = None
            violent = False
            if is_gagged_attempt:
                # Gagged speech attempt: composure roll, fixed difficulty.
                domain, opposed_npc_id = "composure", None
                npc_tier = 1     # pilot default: fixed restraint difficulty, see note
            elif is_escape_attempt:
                # Escape from restraint: physical roll, fixed difficulty.
                domain, opposed_npc_id = "physical", None
                npc_tier = 1     # pilot default: fixed restraint difficulty, see note
            else:
                arbiter_template = _load_mj_arbiter_template(world_id, db)
                if arbiter_template is not None:
                    arbiter_version = current_prompt(db, arbiter_template)
                    domain, opposed_npc_id, applies_constraint, violent = _arbitrate(
                        player_line=content,
                        npc_list=physical_npc_list,
                        name_to_id=physical_name_to_id,
                        arbiter_system=arbiter_version.system_prompt,
                        arbiter_user_tpl=arbiter_version.user_template,
                        model=model,
                        custom_skill_names=world_custom_skill_names,
                    )
                else:
                    domain, opposed_npc_id = "physical", None

            # BRIEF-55 (5d, schema v1.63): resolution mapping. `domain` may now
            # be a base domain OR a custom skill name (constraint-gated turns
            # above only ever set a base domain, so they fall in the first
            # branch). `resolved_base_domain` is what bands/discovery key off.
            custom_def = world_skill_defs_by_name.get(domain)
            if custom_def is None:
                resolved_base_domain = domain
                skill_row = db.exec(
                    select(Skill).where(
                        Skill.character_id == conv.player_id,
                        Skill.domain == domain,
                        Skill.skill_definition_id.is_(None),
                    )
                ).first()
            else:
                resolved_base_domain = custom_def.base_domain
                skill_row = db.exec(
                    select(Skill).where(
                        Skill.character_id == conv.player_id,
                        Skill.skill_definition_id == custom_def.id,
                    )
                ).first()
                if skill_row is None:
                    # Defensive fallback: the PC somehow lacks the custom row.
                    skill_row = db.exec(
                        select(Skill).where(
                            Skill.character_id == conv.player_id,
                            Skill.domain == resolved_base_domain,
                            Skill.skill_definition_id.is_(None),
                        )
                    ).first()

            # Player-roll rule (resolution.py): the roll always belongs to the
            # player — player_tier from the skill sheet, npc_tier (if opposed)
            # from entity.metadata.physical_tier, default 0 either way.
            player_tier = skill_row.tier if skill_row else 0

            opposed_entity: Optional[Entity] = None
            # npc_tier already set for gated turns above; normal turns start at 0.
            if not (is_gagged_attempt or is_escape_attempt):
                npc_tier = 0
            if opposed_npc_id:
                opposed_entity = db.get(Entity, opposed_npc_id)
                if opposed_entity is not None:
                    npc_tier = (opposed_entity.metadata_ or {}).get("physical_tier", 0)

            verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)
            _log.info(
                "Physical verdict: domain=%s dice=%s modifier=%d total=%d band=%s "
                "(player_tier=%d, npc_tier=%d, opposed=%s)",
                verdict.domain, verdict.dice, verdict.modifier, verdict.total,
                verdict.band, player_tier, npc_tier, opposed_npc_id or "none",
            )
            yield f"data: {json.dumps({'verdict': {'domain': verdict.domain, 'dice': list(verdict.dice), 'modifier': verdict.modifier, 'total': verdict.total, 'band': verdict.band}})}\n\n"

            # ── NPC phase: opposed turns only (unopposed behaves like scene) ──
            if opposed_npc_id and opposed_entity is not None:
                responder_id = opposed_npc_id
                responder_name = opposed_entity.name

                responder_behaviour = _load_npc_dialogue_template(world_id, db)
                responder_behaviour_version = current_prompt(db, responder_behaviour)
                responder_context = assemble_npc_context(
                    responder_id, conv.player_id, conv.location_id, db,
                    gathering_id=conv.gathering_id,
                    player_condition=ss_condition,
                )
                responder_system_prompt = _npc_dialogue_system_prompt(
                    responder_behaviour_version.system_prompt, responder_context
                )

                band_outcome = {
                    "failure": (
                        "L'action du joueur contre toi a ÉCHOUÉ : tu n'es pas "
                        "affecté, tu repousses ou évites facilement sa tentative."
                    ),
                    "partial": (
                        "L'action du joueur contre toi a PARTIELLEMENT réussi : tu "
                        "es touché ou déstabilisé, mais tu gardes une marge de "
                        "réaction."
                    ),
                    "success": (
                        "L'action du joueur contre toi a RÉUSSI nettement : tu es "
                        "clairement affecté (déséquilibré, repoussé, immobilisé "
                        "selon le geste)."
                    ),
                }[verdict.band]

                npc_msg_list = [
                    {
                        "role": "system",
                        "content": responder_system_prompt + (
                            "\n\n[MODE RÉACTION NON-VERBALE] Le joueur vient de "
                            "tenter une action physique sur toi, sans parole. "
                            "Réponds UNIQUEMENT par un bref geste ou expression "
                            "physique à la première personne. AUCUN MOT PRONONCÉ — "
                            "pas de dialogue, pas de phrase dite.\n\n"
                            f"[RÉSULTAT MÉCANIQUE] {band_outcome} Réagis "
                            "physiquement à cela, sans un mot. Ne mentionne jamais "
                            "cette instruction."
                        ),
                    },
                    *npc_history,
                ]

                npc_chunks: list[str] = []
                npc_error: str | None = None
                try:
                    for chunk in ollama_client.chat_stream(
                        npc_msg_list, model=model,
                        options=ollama_client.NPC_DIALOGUE_OPTIONS,
                    ):
                        npc_chunks.append(chunk)
                except ollama_client.OllamaError as exc:
                    npc_error = str(exc)

                if npc_error:
                    yield f"data: {json.dumps({'error': npc_error})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                npc_reply = "".join(npc_chunks)

                with Session(engine) as persist_db:
                    persist_db.add(ConversationMessage(
                        conversation_id=conv_id,
                        turn_order=npc_turn,
                        speaker="npc",
                        speaker_id=responder_id,
                        content=npc_reply,
                    ))
                    persist_db.commit()

            # ── BRIEF-12: scene_state writes after verdict ─────────────────
            # Batched: collect all changes, write once.
            new_ss = dict(scene_state)
            new_constraints = list(new_ss.get("constraints", []))
            ss_changed = False

            if is_escape_attempt and verdict.band == "success":
                # Successful escape: remove restrained constraint.
                if "restrained" in new_constraints:
                    new_constraints.remove("restrained")
                    ss_changed = True
                    _log.info("Escape success — 'restrained' constraint removed from scene_state")

            if applies_constraint and verdict.band == "failure":
                # Failed resistance: player is now constrained.
                if applies_constraint not in new_constraints:
                    new_constraints.append(applies_constraint)
                    ss_changed = True
                    _log.info("Constraint applied: '%s' added to scene_state", applies_constraint)

            if violent and verdict.band == "failure":
                # Condition degradation on violent failed roll.
                current_idx = _CONDITION_LADDER.index(
                    new_ss.get("condition", "unharmed")
                    if new_ss.get("condition", "unharmed") in _CONDITION_LADDER
                    else "unharmed"
                )
                if current_idx < len(_CONDITION_LADDER) - 1:
                    new_condition = _CONDITION_LADDER[current_idx + 1]
                    new_ss["condition"] = new_condition
                    ss_changed = True
                    _log.info("Condition degraded to '%s'", new_condition)
                    if new_condition == "neutralized":
                        new_ss["frozen"] = True
                        _log.info("Condition 'neutralized' — scene frozen")

            if ss_changed:
                new_ss["constraints"] = new_constraints
                with Session(engine) as ss_db:
                    ss_conv = ss_db.get(Conversation, conv_id)
                    if ss_conv:
                        _write_scene_state(ss_conv, new_ss)
                        ss_db.add(ss_conv)
                        ss_db.commit()
                # If condition reached injured/neutralized, propose engine injury.
                final_condition = new_ss.get("condition", "unharmed")
                if final_condition in ("injured", "neutralized"):
                    with Session(engine) as inj_db:
                        inj_conv = inj_db.get(Conversation, conv_id)
                        if inj_conv:
                            _propose_engine_injury(inj_conv, final_condition, inj_db)
                            inj_db.commit()
                # Update local copies for the MJ context below.
                ss_condition = new_ss.get("condition", "unharmed")
                ss_constraints = set(new_ss.get("constraints", []))

            # ── Discovery gating (BRIEF-13, schema v1.26) ────────────────────
            # Fires only for perception searches: domain="perception" AND no NPC
            # opposition. A perception roll WITH opposition (e.g. spotting a NPC's
            # hidden weapon under pressure) is NOT a search — must not trigger
            # discovery. Only the code judges what is found; the model receives
            # content ONLY after selection.
            search_rubric: Optional[str] = None
            if resolved_base_domain == "perception" and opposed_npc_id is None:
                if verdict.band in ("partial", "success"):
                    # Select the oldest undiscovered hidden detail REACHABLE at this
                    # roll: discovery_threshold <= verdict.total (N1). When every
                    # undiscovered detail is above threshold the query returns no row,
                    # found_detail is None, and we fall through to [FOUILLE INFRUCTUEUSE]
                    # below — structurally identical to an exhausted location, so gated
                    # content never leaks.
                    found_detail = db.exec(
                        select(DiscoverableDetail).where(
                            DiscoverableDetail.location_id == conv.location_id,
                            DiscoverableDetail.access_level == "hidden",
                            DiscoverableDetail.discovered == False,  # noqa: E712
                            DiscoverableDetail.discovery_threshold <= verdict.total,
                        ).order_by(
                            DiscoverableDetail.created_at,
                            DiscoverableDetail.id,
                        )
                    ).first() if conv.location_id else None

                    if found_detail is not None:
                        with Session(engine) as disc_db:
                            disc_conv = disc_db.get(Conversation, conv_id)
                            if disc_conv:
                                _propose_engine_discovery(disc_conv, found_detail, disc_db)
                                disc_db.commit()
                        search_rubric = (
                            f"[FOUILLE — VERDICT {verdict.band}]\n"
                            f"success : le personnage trouve ce qu'il cherchait, proprement.\n"
                            f"partial : le personnage trouve ce qu'il cherchait, MAIS au prix d'une\n"
                            f"  complication (bruit, objet renversé, un témoin remarque son manège).\n"
                            f"  L'information est bel et bien trouvée ; seule la position se dégrade.\n"
                            f"Contenu trouvé : {found_detail.content}\n"
                            f"Tu narres la découverte ; tu ne rejuges pas le résultat."
                        )
                    else:
                        # Exhausted location — no undiscovered hidden detail.
                        search_rubric = (
                            "[FOUILLE INFRUCTUEUSE]\n"
                            "Le personnage cherche mais ne trouve rien de notable.\n"
                            "N'invente AUCUN objet, lettre, passage ou indice. Décris la fouille\n"
                            "elle-même (gestes, recoins inspectés) et le fait que rien ne ressort."
                        )
                else:
                    # failure band: anti-invention rubric, no proposal.
                    search_rubric = (
                        "[FOUILLE INFRUCTUEUSE]\n"
                        "Le personnage cherche mais ne trouve rien de notable.\n"
                        "N'invente AUCUN objet, lettre, passage ou indice. Décris la fouille\n"
                        "elle-même (gestes, recoins inspectés) et le fait que rien ne ressort."
                    )

            # ── MJ narration user message ────────────────────────────────────
            mj_context = (
                assemble_mj_context(
                    db, conv.player_id, conv.location_id,
                    gathering_id=player_gathering.id if player_gathering else None,
                    blindfolded="blindfolded" in ss_constraints,
                    player_condition=ss_condition,
                )
                if conv.location_id else None
            )
            inventory_line = format_inventory_line(db, conv.player_id)
            mj_user = _build_mj_user(
                mode=mode,
                mj_user_template=mj_user_template,
                npc_name=responder_name,
                location_name=location_name,
                player_line=content,
                npc_reply=npc_reply,
                mj_context=mj_context,
                inventory_line=inventory_line,
                verdict_band=verdict.band,
                search_rubric=search_rubric,
            )
        else:
            # ── Speaker / target resolution (contract A3 hybrid) ──────────────
            if mode in (ResponseMode.dialogue, ResponseMode.npc_reaction):
                if body.target and body.target != "group":
                    responder_id = body.target
                elif body.target == "group" and player_gathering is not None:
                    co_members = [
                        (gm, e) for gm, e in _active_members(player_gathering.id, db)
                        if e.id != conv.player_id
                    ]
                    if co_members:
                        responder_id = _select_group_speaker(
                            template=_load_mj_speaker_template(world_id, db),
                            location_name=location_name,
                            gathering=player_gathering,
                            members=co_members,
                            player_line=content,
                            model=model,
                            db=db,
                        )
                elif not body.target:
                    if npc_id is None and conv.gathering_id:
                        # Pure gathering conversation (started from scene-level
                        # join, no seed NPC). Treat omitted target as "group"
                        # so the MJ always picks a responder — the player joined
                        # a gathering, not a 1:1.
                        responder_id = _select_group_speaker(
                            template=_load_mj_speaker_template(world_id, db),
                            location_name=location_name,
                            gathering=player_gathering,
                            members=[
                                (gm, e) for gm, e in _active_members(player_gathering.id, db)
                                if e.id != conv.player_id
                            ] if player_gathering else [],
                            player_line=content,
                            model=model,
                            db=db,
                        ) if player_gathering and _active_members(player_gathering.id, db) else None
                    else:
                        responder_id = npc_id  # backward-compatible default (1:1)

                if responder_id is None:
                    # Addressed the group with nobody able to answer — narrate
                    # the silence rather than inventing a respondent. Cadence
                    # B1 still holds: zero is a valid responder count here.
                    mode = ResponseMode.scene

            # ── Phase 1: NPC generation (conditional, buffered) ───────────────
            # dialogue / npc_reaction: call the responder; persist raw reply as 'npc'.
            # scene: skip entirely; npc_reply stays "".
            if mode in (ResponseMode.dialogue, ResponseMode.npc_reaction) and responder_id:
                responder_entity = db.get(Entity, responder_id)
                responder_name = responder_entity.name if responder_entity else responder_id

                # The frozen baseline system_prompt only matches the seed NPC
                # in a plain (non-gathering) conversation — contract D1 needs
                # a freshly assembled, NPC-specific context for anyone else.
                if responder_id == npc_id and conv.gathering_id is None:
                    responder_system_prompt = system_prompt
                else:
                    responder_behaviour = _load_npc_dialogue_template(world_id, db)
                    responder_behaviour_version = current_prompt(db, responder_behaviour)
                    responder_context = assemble_npc_context(
                        responder_id, conv.player_id, conv.location_id, db,
                        gathering_id=conv.gathering_id,
                        player_condition=ss_condition,
                    )
                    responder_system_prompt = _npc_dialogue_system_prompt(
                        responder_behaviour_version.system_prompt, responder_context
                    )

                npc_msg_list = [{"role": "system", "content": responder_system_prompt}, *npc_history]
                if mode == ResponseMode.npc_reaction:
                    # Append a one-shot instruction so the NPC produces a brief
                    # wordless gesture rather than spoken dialogue.
                    npc_msg_list[0] = {
                        "role": "system",
                        "content": npc_msg_list[0]["content"] + (
                            "\n\n[MODE RÉACTION NON-VERBALE] Le joueur n'a pas adressé "
                            "la parole au personnage. Réponds UNIQUEMENT par un bref geste "
                            "ou expression physique à la première personne. "
                            "AUCUN MOT PRONONCÉ — pas de dialogue, pas de phrase dite."
                        ),
                    }
                if refusal_instruction is not None:
                    # The player's gesture just failed (possession check) —
                    # the NPC reacts to what it witnessed (BRIEF-08 / D2a.1).
                    npc_msg_list[0] = {
                        "role": "system",
                        "content": npc_msg_list[0]["content"] + "\n\n" + _GESTE_RATE_INSTRUCTION,
                    }

                npc_chunks: list[str] = []
                npc_error: str | None = None
                try:
                    for chunk in ollama_client.chat_stream(
                        npc_msg_list, model=model,
                        options=ollama_client.NPC_DIALOGUE_OPTIONS,
                    ):
                        npc_chunks.append(chunk)
                except ollama_client.OllamaError as exc:
                    npc_error = str(exc)

                if npc_error:
                    yield f"data: {json.dumps({'error': npc_error})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                npc_reply = "".join(npc_chunks)

                # Persist the NPC line (canonical truth) under its own speaker_id.
                with Session(engine) as persist_db:
                    persist_db.add(ConversationMessage(
                        conversation_id=conv_id,
                        turn_order=npc_turn,
                        speaker="npc",
                        speaker_id=responder_id,
                        content=npc_reply,
                    ))
                    persist_db.commit()

            # ── Phase 2: MJ narration user message ─────────────────────────────
            # MJ context (schema v1.12, scope D-b3): the player's perception
            # boundary — read fresh every turn (co-presents change with C2
            # migrations); see assemble_mj_context for the static/dynamic split.
            # BRIEF-12: pass blindfolded flag (excludes visual info) and
            # player_condition (MJ is aware of mechanical reality).
            mj_context = (
                assemble_mj_context(
                    db, conv.player_id, conv.location_id,
                    gathering_id=player_gathering.id if player_gathering else None,
                    blindfolded="blindfolded" in ss_constraints,
                    player_condition=ss_condition,
                )
                if conv.location_id else None
            )
            # Inventory line (schema v1.18, BRIEF-06): read fresh every turn,
            # never cached or snapshotted alongside mj_context.
            inventory_line = format_inventory_line(db, conv.player_id)
            mj_user = _build_mj_user(
                mode=mode,
                mj_user_template=mj_user_template,
                npc_name=responder_name,
                location_name=location_name,
                player_line=content,
                npc_reply=npc_reply,
                mj_context=mj_context,
                inventory_line=inventory_line,
            )

        # ── MJ narration (streamed to the player) ─────────────────────────────
        # Refusal instruction (BRIEF-08 / D2a.1): appended to the system prompt
        # for this turn only — never persisted, same pattern as
        # [MODE RÉACTION NON-VERBALE].
        mj_system_prompt_for_turn = (
            f"{mj_system_prompt}\n\n{refusal_instruction}"
            if refusal_instruction is not None
            else mj_system_prompt
        )
        mj_messages = [
            {"role": "system", "content": mj_system_prompt_for_turn},
            {"role": "user",   "content": mj_user},
        ]

        mj_chunks: list[str] = []
        mj_error: str | None = None
        try:
            for chunk in ollama_client.chat_stream(
                mj_messages, model=model,
                options=ollama_client.MJ_NARRATION_OPTIONS,
            ):
                mj_chunks.append(chunk)
                yield f"data: {json.dumps(chunk)}\n\n"
        except ollama_client.OllamaError as exc:
            mj_error = str(exc)

        # Send mode and raw NPC line before [DONE] for client-side audit.
        # mode: tells the UI why a turn may have produced no NPC dialogue.
        # npc_raw: empty string for scene turns (no NPC call).
        yield f"data: {json.dumps({'mode': mode.value})}\n\n"
        yield f"data: {json.dumps({'npc_raw': npc_reply})}\n\n"
        if extra_event is not None:
            yield f"data: {json.dumps(extra_event)}\n\n"

        if mj_error:
            yield f"data: {json.dumps({'error': mj_error})}\n\n"

        # ── Phase 3 & 4: NPC initiative (Tier 3 — C1 vote, C2 migration) ───────
        # Vote (cheap, non-streaming): ask the MJ if a bystander NPC acts.
        # Generation (non-streaming JSON): only when the vote fires. Produces
        # {"act_text": "…", "move": <bool>}. move=true → NPC physically migrates
        # to the player's gathering before the act is narrated (C2).
        # Cadence E1: at most one NPC per turn.
        # Only fires when the player is in a gathering (initiative is a
        # gathering-level concept; 1:1 conversations have no bystanders).
        initiative_npc_reply = ""
        initiative_initiator_id: str | None = None  # entity_id of the NPC who took initiative
        if player_gathering is not None:
            # In-group: player's gathering members, excluding player and this-turn responder.
            in_group_initiative = [
                (gm, e) for gm, e in _active_members(player_gathering.id, db)
                if e.id != conv.player_id and e.id != responder_id
            ]
            # Non-members: active members of all OTHER open gatherings at this location.
            # open_gatherings is a live snapshot from phase 0a; no migration has occurred
            # yet this turn (E1: at most one initiative, which fires after the vote).
            non_member_initiative: list[tuple[GatheringMember, Entity]] = []
            for _g in open_gatherings:
                if _g.id == player_gathering.id:
                    continue
                non_member_initiative.extend(_active_members(_g.id, db))
            non_member_ids_initiative: set[str] = {e.id for _gm, e in non_member_initiative}
            all_candidates = in_group_initiative + non_member_initiative
            if all_candidates:
                initiative_template = _load_mj_initiative_template(world_id, db)
                if initiative_template is not None:
                    act, initiator_id = _npc_initiative_vote(
                        template=initiative_template,
                        location_name=location_name,
                        members=all_candidates,
                        non_member_ids=non_member_ids_initiative,
                        player_line=content,
                        interpreted_mode=mode,
                        player_id=conv.player_id,
                        model=model,
                        db=db,
                    )
                    if act and initiator_id:
                        initiator_entity = db.get(Entity, initiator_id)
                        initiator_name = (
                            initiator_entity.name if initiator_entity else initiator_id
                        )

                        # Fresh context (D1 — same pipeline as normal responders).
                        # For non-members, gathering_id = player's gathering: the NPC
                        # sees who it is approaching, not where it currently stands.
                        # v1 conscious choice: distant NPCs are at-a-glance distance
                        # (same room). Revisit if out-of-sight gatherings are added.
                        init_behaviour = _load_npc_dialogue_template(world_id, db)
                        init_behaviour_version = current_prompt(db, init_behaviour)
                        init_ctx = assemble_npc_context(
                            initiator_id, conv.player_id, conv.location_id, db,
                            gathering_id=conv.gathering_id,
                            player_condition=ss_condition,
                        )
                        # C2: load JSON-output contract from dedicated template
                        # (usage="npc_initiative_act") — never bleeds into normal
                        # /say turns which use the shared npc_dialogue template.
                        init_act_tmpl = _load_npc_initiative_act_template(world_id, db)
                        init_act_instruction = (
                            current_prompt(db, init_act_tmpl).system_prompt
                            if init_act_tmpl is not None
                            else _NPC_INITIATIVE_ACT_FALLBACK
                        )
                        init_system = (
                            f"{_npc_dialogue_system_prompt(init_behaviour_version.system_prompt, init_ctx)}"
                            f"\n\n{init_act_instruction}"
                        )

                        init_trigger = _build_initiative_trigger(
                            player_line=content,
                            npc_reply=npc_reply,
                            responder_name=responder_name if responder_id else None,
                        )
                        init_msg_list = [
                            {"role": "system", "content": init_system},
                            *npc_history,
                            {"role": "user", "content": init_trigger},
                        ]

                        # C2: non-streaming JSON call replaces streaming free text.
                        # Accepted debt: act appears all-at-once (short pause); restoring
                        # incremental streaming is a future improvement, not this session.
                        initiative_act_text = ""
                        initiative_move = False
                        try:
                            raw_act = ollama_client.chat(
                                init_msg_list, model=model,
                                format="json",
                                options=ollama_client.NPC_DIALOGUE_OPTIONS,
                            )
                            raw_act = ollama_client.strip_think(raw_act)
                            try:
                                act_obj = json.loads(raw_act)
                                initiative_act_text = str(
                                    act_obj.get("act_text") or ""
                                ).strip()
                                initiative_move = bool(act_obj.get("move", False))
                            except (json.JSONDecodeError, ValueError):
                                # Salvage: model emitted prose instead of JSON.
                                # Use raw text as act; migration must not fire on
                                # degraded output — move stays False.
                                initiative_act_text = raw_act.strip()
                                initiative_move = False
                        except ollama_client.OllamaError:
                            pass  # initiative failure is silent — never surfaces

                        # Structural override: a non-member winning the vote implies
                        # physical migration regardless of what the model returned.
                        # The idempotent guard in migrate_npc makes this a no-op for
                        # in-group NPCs if they somehow emit move=True.
                        if initiator_id in non_member_ids_initiative:
                            initiative_move = True

                        # Conscious choice: a valid JSON response with an empty
                        # act_text (e.g. {"move": true}) skips the act AND the
                        # migration. No migration without narration — avoids invisible
                        # NPC movement that the player would never see narrated.
                        if initiative_act_text:
                            initiative_npc_reply = initiative_act_text
                            initiative_initiator_id = initiator_id

                            # C2 migration: move the NPC into the player's gathering
                            # BEFORE persisting or narrating, so the DB roster is
                            # already at destination when post-[DONE] analysis runs.
                            # mig_db is a short-lived session; the SSE generator's db
                            # session has no open write transaction at this point
                            # (all earlier writes used their own Session(engine) blocks
                            # and committed), so there is no nested-transaction conflict.
                            # player_gathering is in scope — captured before the stream
                            # started and remains valid for the duration of the generator.
                            if initiative_move and player_gathering is not None:
                                with Session(engine) as mig_db:
                                    _migrate_npc(
                                        initiator_id,
                                        player_gathering.id,
                                        mig_db,
                                    )

                            # Persist initiative NPC line (canonical, speaker='npc').
                            with Session(engine) as persist_db:
                                persist_db.add(ConversationMessage(
                                    conversation_id=conv_id,
                                    turn_order=player_turn + 3,
                                    speaker="npc",
                                    speaker_id=initiator_id,
                                    content=initiative_npc_reply,
                                ))
                                persist_db.commit()

                            # Stream initiative MJ narration to the player.
                            init_mj_user = _build_initiative_mj_user(
                                npc_name=initiator_name,
                                location_name=location_name,
                                initiative_line=initiative_npc_reply,
                                player_line=content,
                            )
                            init_mj_messages = [
                                {"role": "system", "content": mj_system_prompt},
                                {"role": "user",   "content": init_mj_user},
                            ]

                            yield f"data: {json.dumps({'initiative_start': {'npc_name': initiator_name}})}\n\n"

                            init_mj_chunks: list[str] = []
                            try:
                                for chunk in ollama_client.chat_stream(
                                    init_mj_messages, model=model,
                                    options=ollama_client.MJ_NARRATION_OPTIONS,
                                ):
                                    init_mj_chunks.append(chunk)
                                    yield f"data: {json.dumps(chunk)}\n\n"
                            except ollama_client.OllamaError:
                                pass

                            yield f"data: {json.dumps({'initiative_npc_raw': initiative_npc_reply})}\n\n"

                            # Persist initiative MJ narration before [DONE] so that
                            # the next turn's player_turn computation (last+1) sees
                            # the correct last row and avoids turn_order collisions.
                            with Session(engine) as persist_db:
                                persist_db.add(ConversationMessage(
                                    conversation_id=conv_id,
                                    turn_order=player_turn + 4,
                                    speaker="mj",
                                    speaker_id=None,
                                    content="".join(init_mj_chunks),
                                ))
                                persist_db.commit()

        # ── Travel state transition (resolved direct travel only) ─────────────
        # Runs after the traveled SSE and initiative blocks, before [DONE].
        # Closes the current conversation (runs analyze_window) and updates
        # current_location_id — same as the creator POST /api/travel path.
        if travel_dest_id is not None:
            _perform_travel(conv.player_id, travel_dest_id, db)

        yield "data: [DONE]\n\n"

        # Persist the main MJ narration (presentation layer).
        # Runs after [DONE] — the player can read and type while this completes.
        mj_narration = "".join(mj_chunks)
        with Session(engine) as persist_db:
            persist_db.add(ConversationMessage(
                conversation_id=conv_id,
                turn_order=mj_turn,
                speaker="mj",
                speaker_id=None,
                content=mj_narration,
            ))
            persist_db.commit()

        # Overhearing analysis (sync-after-stream, Tier 4, acquire or upgrade).
        # 'dialogue' turns only — 'scene' has no NPC line, 'npc_reaction' is
        # wordless (analyze_overhearing's own guard would also catch both via
        # an empty npc_reply, but the mode check keeps the gating explicit).
        # Failures are silently swallowed — analysis must never surface to
        # the player.
        if mode == ResponseMode.dialogue:
            with Session(engine) as overhear_db:
                try:
                    overheard = _analyze_overhearing(
                        player_line=content,
                        npc_line=npc_reply,
                        conversation_id=conv_id,
                        db=overhear_db,
                        model=model,
                        npc_entity_id=responder_id,
                    )
                    for mut in overheard:
                        overhear_db.add(mut)
                    if overheard:
                        overhear_db.commit()
                except (Exception, SystemExit):
                    pass

    return StreamingResponse(_stream(), media_type="text/event-stream")


@app.post("/api/conversations/{conv_id}/end")
def end_conversation(conv_id: str, db: Session = Depends(get_session)) -> dict:
    """Close a conversation, running window analysis first (trigger a)."""
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.status == "closed":
        return {"status": "already_closed"}
    try:
        _analyze_window(conv_id, db)
    except (Exception, SystemExit):
        _log.exception("analyze_window failed for conversation %s", conv_id)
    # Archive scene_state to history[] before clearing (history is sacred even
    # on close: the final constraint/condition snapshot must survive for
    # post-scene audit — direct assignment would destroy the chain).
    _write_scene_state(conv, _default_scene_state())
    conv.status = "closed"
    conv.ended_at = datetime.now(UTC)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"status": "closed", "ended_at": _iso(conv.ended_at)}


@app.post("/api/conversations/{conv_id}/join")
def join_gathering(conv_id: str, body: JoinBody, db: Session = Depends(get_session)) -> dict:
    """Explicit join action — the C2 cockpit-selector fallback for an
    unresolved 'join' intent (contract A2: ambiguous/not-found → the player
    picks from the list of open gatherings rather than the model guessing).

    Joining is not a canon mutation (see ARCHITECTURE_DECISIONS.md, MULTI-NPC
    SCENES) — it only inserts a `gathering_member` row and anchors the
    conversation's `gathering_id`; no `proposed_mutation` is written here.
    """
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.status != "open":
        raise HTTPException(status_code=400, detail="Conversation is not open")

    gathering = db.get(Gathering, body.gathering_id)
    if gathering is None or gathering.status != "open":
        raise HTTPException(status_code=404, detail="Gathering not found or not open")
    if gathering.location_id != conv.location_id or gathering.session_id != conv.session_id:
        raise HTTPException(status_code=400, detail="Gathering does not match this conversation's location/session")

    gathering = _join_gathering(conv, gathering.id, db)
    return {"joined": True, "gathering": _gathering_brief(gathering.id, db)}


class ConvTravelBody(BaseModel):
    location_id: str


@app.post("/api/conversations/{conv_id}/travel")
def conv_travel(
    conv_id: str,
    body: ConvTravelBody,
    db: Session = Depends(get_session),
) -> dict:
    """In-fiction picker callback — the player chose a destination from the
    travel_candidates picker after an unresolved travel intent (BRIEF-16).

    Distinct from the creator POST /api/travel: this endpoint is
    neighbour-restricted (only direct connects_to neighbours of the
    conversation's current location are accepted). A stale or non-neighbour
    selection is rejected with 400.

    No MJ narration is produced here — the [DÉPART INCERTAIN] hesitation
    already covered the fictional moment; the move itself is silent, consistent
    with the creator travel tool. Travel is not a canon mutation.
    """
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.status != "open":
        raise HTTPException(status_code=400, detail="Conversation is not open")

    origin = conv.location_id
    neighbours = _location_neighbours(origin, db)
    neighbour_ids = {eid for eid, _name in neighbours}
    if body.location_id not in neighbour_ids:
        raise HTTPException(
            status_code=400,
            detail=f"{body.location_id!r} is not an active neighbour of the current location",
        )

    result = _perform_travel(conv.player_id, body.location_id, db)
    return result


# ── Scene-level endpoints (location entry surface, Tier 1 step 3) ──────────
# These sit above the conversation layer: the player enters a location and sees
# the gathering partition before any conversation is opened.

def _active_conv_for_gathering(player_id: str, gathering_id: str, db: Session) -> Optional[str]:
    """Return the id of any open conversation the player has in this gathering, or None."""
    conv = db.exec(
        select(Conversation).where(
            Conversation.gathering_id == gathering_id,
            Conversation.player_id    == player_id,
            Conversation.status       == "open",
        )
    ).first()
    return conv.id if conv else None


def _scene_response(
    location_id: str,
    player_id: str,
    world_id: str,
    db: Session,
    establishment: Optional[str] = None,
) -> dict:
    """Build the canonical scene dict (shared by GET /api/scene and POST /api/scene/enter).

    Includes `active_conversation_id`: the open conversation for the player's
    current gathering, if any. The UI uses this to offer "Reprendre" vs
    "Continuer à parler" (a new conversation in the same gathering).

    `establishment` (schema v1.30, BRIEF-17): the entry narration text, or
    None when not computed (GET /api/scene, a skipped/failed MJ call).
    """
    loc_entity    = db.get(Entity, location_id)
    sess          = _get_or_open_session(world_id, db)
    open_g        = _open_gatherings(location_id, sess.id, db)
    player_g      = _player_gathering(player_id, location_id, sess.id, db)
    active_conv_id: Optional[str] = (
        _active_conv_for_gathering(player_id, player_g.id, db) if player_g else None
    )
    return {
        "location_id":           location_id,
        "location_name":         loc_entity.name if loc_entity else location_id,
        "session_id":            sess.id,
        "gatherings":            [_gathering_brief(g.id, db) for g in open_g],
        "player_gathering":      _gathering_brief(player_g.id, db) if player_g else None,
        "active_conversation_id": active_conv_id,  # None when no open conv in gathering
        "establishment":         establishment,  # None when not computed/skipped/failed
    }


@app.get("/api/scene")
def get_scene(
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    """Current scene for the player's location: open gatherings + their rosters.

    Read-only — never calls enter_location. Use POST /api/scene/enter to
    generate the gathering partition on a genuine location transition.
    """
    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
    char = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player character {player_id!r} not found")
    if not char.current_location_id:
        raise HTTPException(status_code=404, detail="Player has no current location")
    player_entity = db.get(Entity, player_id)
    if player_entity is None:
        raise HTTPException(status_code=404, detail=f"Player entity {player_id!r} not found")
    return _scene_response(char.current_location_id, player_id, player_entity.world_id, db)


@app.post("/api/scene/enter")
def enter_scene(
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    """Enter the player's current location.

    Calls enter_location (dissolve open gatherings + generate a fresh partition)
    ONLY if no open gatherings already exist for this location+session — which
    distinguishes a genuine location transition from a re-render or F5 refresh
    (contract B1 / invariant C1: generating once at entry, no spontaneous
    reshuffling on re-load).

    Idempotent: calling enter again while open gatherings exist is a silent
    no-op that returns the existing partition.
    """
    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
    char = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player character {player_id!r} not found")
    if not char.current_location_id:
        raise HTTPException(status_code=404, detail="Player has no current location")
    player_entity = db.get(Entity, player_id)
    if player_entity is None:
        raise HTTPException(status_code=404, detail=f"Player entity {player_id!r} not found")

    location_id = char.current_location_id
    world_id    = player_entity.world_id
    sess        = _get_or_open_session(world_id, db)

    # ── Idempotent enter guard (protects C1 from F5 reshuffling) ──────────
    open_g = _open_gatherings(location_id, sess.id, db)
    changes_lines: Optional[list[str]] = None
    if not open_g:
        # No open gatherings → genuine location transition (or first load).
        # Run window analysis on any conversation left open at the previous
        # location (trigger b) before regenerating the partition here.
        left_convs = db.exec(
            select(Conversation).where(
                Conversation.player_id == player_id,
                Conversation.status == "open",
                Conversation.location_id != location_id,
            )
        ).all()
        for oc in left_convs:
            try:
                _analyze_window(oc.id, db)
            except (Exception, SystemExit):
                _log.exception("analyze_window failed for conversation %s", oc.id)

        # Return-visit delta (schema v1.71, BRIEF-0016-a, G2): compute from
        # the PREVIOUS visit row before the new one is appended (RECON-0016
        # F7 — compute-then-append; _enter_location touches only gatherings,
        # never current_location_id, so the presence read is safe either
        # side of it).
        changes_lines, current_npc_ids = _compute_return_delta(db, world_id, player_id, location_id)

        # Generate the partition; never raises (falls back to all-solo on error).
        _enter_location(location_id, sess.id, db)

        db.add(Visit(
            world_id=world_id,
            player_id=player_id,
            location_id=location_id,
            present_npc_ids=current_npc_ids,
        ))
        db.commit()

    # Entry narration (schema v1.30, BRIEF-17, F3/G1; changes v1.71,
    # BRIEF-0016-a): fired on EVERY entry. A refresh passes changes=None (G2
    # lifted — the delta rides in only on a genuine transition). Resilience
    # doctrine: a failed/skipped call must never block scene entry.
    establishment = _build_establishment_narration(
        location_id, player_id, world_id, db, changes=changes_lines
    )

    return _scene_response(location_id, player_id, world_id, db, establishment=establishment)


class SceneJoinBody(BaseModel):
    player_text: str                       # player's free-text join expression
    player_id: Optional[str] = None        # defaults to the resolved player character


@app.post("/api/scene/join")
def scene_join(body: SceneJoinBody, db: Session = Depends(get_session)) -> dict:
    """Join a gathering from the scene view — creates the conversation.

    Autonomous join: no pre-existing conversation required. Interprets the
    player's text (via the full pt-mj-interpretation pipeline) to resolve a
    gathering target (contract A2), then:

    - Resolved (exactly one match): inserts gathering_member, creates a
      conversation anchored to the gathering (npc_id=None — pure gathering
      conversation; responder selection is A3-group by default). Returns
      {"conversation_id": ..., "gathering": {...}}.
    - Unresolved / ambiguous: returns {"join_candidates": [...]} so the
      cockpit picker (C2 selector) can surface the open gatherings for an
      explicit click.
    - Already joined: returns {"already_joined": True, "gathering": {...},
      "conversation_id": ...} with the active conversation if one exists.

    Joining is not a canon mutation — no proposed_mutation row is produced.
    """
    player_id     = body.player_id or _crud._player_character_id(db, _crud._world_id(db))
    char          = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id!r} not found")
    if not char.current_location_id:
        raise HTTPException(status_code=400, detail="Player has no current location")
    player_entity = db.get(Entity, player_id)
    if player_entity is None:
        raise HTTPException(status_code=404, detail=f"Player entity {player_id!r} not found")

    location_id  = char.current_location_id
    world_id     = player_entity.world_id
    loc_entity   = db.get(Entity, location_id)
    location_name = loc_entity.name if loc_entity else location_id

    sess    = _get_or_open_session(world_id, db)
    open_g  = _open_gatherings(location_id, sess.id, db)
    player_g = _player_gathering(player_id, location_id, sess.id, db)

    if player_g is not None:
        # Already a gathering member — find any open conversation in it.
        existing_conv = db.exec(
            select(Conversation).where(
                Conversation.gathering_id == player_g.id,
                Conversation.player_id    == player_id,
                Conversation.status       == "open",
            )
        ).first()
        if existing_conv:
            # Resume the active conversation.
            return {
                "already_joined":  True,
                "gathering":       _gathering_brief(player_g.id, db),
                "conversation_id": existing_conv.id,
            }
        # In the gathering but no open conversation (e.g. previous one was
        # closed, or the player re-loaded after the test). Create a fresh one
        # anchored to the same gathering — identical to the resolve path below.
        behaviour = _load_npc_dialogue_template(world_id, db)
        behaviour_version = current_prompt(db, behaviour)
        model     = effective_model(behaviour, ollama_client.DEFAULT_MODEL)
        mj_context = assemble_mj_context(db, player_id, location_id, gathering_id=player_g.id)
        new_conv  = Conversation(
            world_id    = world_id,
            session_id  = sess.id,
            location_id = location_id,
            player_id   = player_id,
            npc_id      = None,
            status      = "open",
            injected_context = {
                "model":              model,
                "interlocutor_id":    player_id,
                "location_id":        location_id,
                "prompt_template_id": behaviour.id,
                "behaviour_prompt":   behaviour_version.system_prompt,
                "system_prompt":      "",
                "mj": {k: v for k, v in mj_context.items() if k != "co_presents"},
            },
            gathering_id = player_g.id,
            started_at   = datetime.now(UTC),
        )
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        return {
            "already_joined":  True,
            "gathering":       _gathering_brief(player_g.id, db),
            "conversation_id": new_conv.id,
        }

    if not open_g:
        raise HTTPException(status_code=400, detail="No open gatherings at this location")

    # ── Interpret the player's text via the full MJ pipeline (A2 reused) ──
    gathering_status  = _render_gathering_status(player_id, None, open_g, db)
    interpret_template = _load_mj_interpret_template(world_id, db)
    interpret_version = current_prompt(db, interpret_template)
    model             = effective_model(interpret_template, ollama_client.DEFAULT_MODEL)

    # Provide a plausible NPC name for the template context (any member present).
    any_npc_name = "?"
    for g in open_g:
        for _gm, e in _active_members(g.id, db):
            any_npc_name = e.name
            break
        if any_npc_name != "?":
            break

    mode, reference, _used_object = _interpret_mode(
        player_line       = body.player_text,
        npc_name          = any_npc_name,
        location_name     = location_name,
        gathering_status  = gathering_status,
        recent_transcript = "",
        item_list         = format_item_list_for_interpretation(db, player_id),
        interpret_system  = interpret_version.system_prompt,
        interpret_user_tpl = interpret_version.user_template,
        model             = model,
    )

    # If the model didn't classify as join, treat the full text as the reference
    # anyway — the player typed in a join-specific field, so intent is clear.
    if mode != ResponseMode.join:
        reference = body.player_text

    resolved_id = _resolve_join_target(reference, open_g, db)

    if resolved_id is None:
        return {"join_candidates": [_gathering_brief(g.id, db) for g in open_g]}

    # ── Create the conversation anchored to the resolved gathering ─────────
    behaviour   = _load_npc_dialogue_template(world_id, db)
    behaviour_version = current_prompt(db, behaviour)
    mj_context = assemble_mj_context(db, player_id, location_id, gathering_id=resolved_id)
    conv = Conversation(
        world_id    = world_id,
        session_id  = sess.id,
        location_id = location_id,
        player_id   = player_id,
        npc_id      = None,   # pure gathering conversation — responder chosen per turn (A3)
        status      = "open",
        injected_context = {
            "model":              model,
            "interlocutor_id":    player_id,
            "location_id":        location_id,
            "prompt_template_id": behaviour.id,
            "behaviour_prompt":   behaviour_version.system_prompt,
            # system_prompt left empty — assembled fresh per responder in _stream (D1)
            "system_prompt":      "",
            "mj": {k: v for k, v in mj_context.items() if k != "co_presents"},
        },
        started_at = datetime.now(UTC),
    )
    db.add(conv)
    db.flush()  # get conv.id before _join_gathering commits

    # _join_gathering inserts gathering_member + sets conv.gathering_id, then commits.
    gathering = _join_gathering(conv, resolved_id, db)
    db.refresh(conv)

    return {
        "conversation_id": conv.id,
        "gathering":       _gathering_brief(gathering.id, db),
    }


@app.post("/api/scene/leave")
def scene_leave(
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    """Remove the player from their current gathering.

    Sets GatheringMember.left_at to now — the gathering itself and its other
    members are unaffected.  Any open conversation the player had in that
    gathering is closed (the player has left; no more turns).

    Returns the updated scene so the UI can re-render directly.
    """
    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
    char = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id!r} not found")
    location_id = char.current_location_id
    if not location_id:
        raise HTTPException(status_code=400, detail="Player has no current location")

    player_entity = db.get(Entity, player_id)
    if player_entity is None:
        raise HTTPException(status_code=404, detail=f"Player entity {player_id!r} not found")
    world_id = player_entity.world_id

    sess     = _get_or_open_session(world_id, db)
    player_g = _player_gathering(player_id, location_id, sess.id, db)

    if player_g is None:
        # Already ungrouped — return fresh scene (idempotent).
        return _scene_response(location_id, player_id, world_id, db)

    # 1. Mark the player's GatheringMember row as left.
    gm = db.exec(
        select(GatheringMember).where(
            GatheringMember.gathering_id == player_g.id,
            GatheringMember.entity_id   == player_id,
            GatheringMember.left_at.is_(None),
        )
    ).first()
    if gm:
        gm.left_at = datetime.now(UTC)
        db.add(gm)

    # 2. Close any open conversation the player had in this gathering.
    open_conv = db.exec(
        select(Conversation).where(
            Conversation.gathering_id == player_g.id,
            Conversation.player_id   == player_id,
            Conversation.status      == "open",
        )
    ).first()
    if open_conv:
        # Archive scene_state to history[] before clearing (history is sacred
        # even on close — direct assignment would destroy the constraint chain).
        _write_scene_state(open_conv, _default_scene_state())
        open_conv.status = "closed"
        db.add(open_conv)

    db.commit()

    return _scene_response(location_id, player_id, world_id, db)


# ── Scene state endpoints (BRIEF-12, schema v1.24) ──────────────────────────


@app.get("/api/conversations/{conv_id}/scene-state")
def get_scene_state(conv_id: str, db: Session = Depends(get_session)) -> dict:
    """Return the current scene_state for a conversation."""
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _get_scene_state(conv)


class SceneStateBody(BaseModel):
    constraints: Optional[list[str]] = None
    condition: Optional[str] = None
    frozen: Optional[bool] = None


@app.patch("/api/conversations/{conv_id}/scene-state")
def update_scene_state(
    conv_id: str,
    body: SceneStateBody,
    db: Session = Depends(get_session),
) -> dict:
    """Creator-direct edit of scene_state.

    Accepts any subset of {constraints, condition, frozen}. Missing fields
    keep their current value. Merges the update, archives the previous state
    to history (history is sacred), and returns the new state.

    This is a creator CRUD operation — no proposed_mutation checkpoint.
    """
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Closed conversations have scene_state cleared to the default by the close
    # path. Guard here so a PATCH-after-close cannot re-populate it and
    # silently re-falsify the invariant ("fermée ⇒ scene_state vide").
    if conv.status == "closed":
        raise HTTPException(status_code=400, detail="Conversation is already closed")

    # Validate inputs.
    if body.constraints is not None:
        bad = [c for c in body.constraints if c not in _VALID_CONSTRAINTS]
        if bad:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown constraint(s): {bad}. Valid: {sorted(_VALID_CONSTRAINTS)}",
            )
    if body.condition is not None and body.condition not in _CONDITION_LADDER:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown condition {body.condition!r}. Valid: {_CONDITION_LADDER}",
        )

    current = _get_scene_state(conv)
    new_ss: dict = {
        "constraints": body.constraints if body.constraints is not None
                       else current["constraints"],
        "condition":   body.condition   if body.condition   is not None
                       else current["condition"],
        "frozen":      body.frozen      if body.frozen      is not None
                       else current["frozen"],
    }
    # Setting condition to neutralized auto-sets frozen.
    if new_ss["condition"] == "neutralized":
        new_ss["frozen"] = True

    _write_scene_state(conv, new_ss)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _get_scene_state(conv)


def _perform_travel(player_id: str, location_id: str, db: Session) -> dict:
    """Clean location transition for a player. Shared by the creator travel
    tool and the in-fiction /say travel path. NOT a canon mutation — a state
    transition (same category as gathering join/migrate); writes no
    proposed_mutation row. Validates the destination is a location of the
    player's world; no-ops if already there; otherwise closes open
    conversations (running analyze_window first), closes the player's open
    gathering_member rows, updates current_location_id — single commit."""
    player_entity = db.get(Entity, player_id)
    world_id = player_entity.world_id if player_entity else None

    dest = db.get(Entity, location_id)
    if (
        dest is None
        or dest.type != "location"
        or world_id is None
        or dest.world_id != world_id
        or dest.status != "active"
    ):
        return {"status": "invalid_destination", "location_id": location_id}

    char = db.get(Character, player_id)
    if char is None:
        return {"status": "invalid_destination", "location_id": location_id}

    if char.current_location_id == location_id:
        return {"status": "noop", "location_id": location_id}

    # 1. Close any open conversation(s) of the player. Normally at most one,
    # but close every match defensively — a stray open conversation left at
    # the old location must not stay open after the player leaves.
    now = datetime.now(UTC)
    open_convs = db.exec(
        select(Conversation).where(
            Conversation.player_id == player_id,
            Conversation.status == "open",
        )
    ).all()
    for open_conv in open_convs:
        try:
            _analyze_window(open_conv.id, db)
        except (Exception, SystemExit):
            _log.exception("analyze_window failed for conversation %s", open_conv.id)
        # Archive scene_state to history[] before clearing (history is sacred
        # even on close — direct assignment would destroy the constraint chain).
        _write_scene_state(open_conv, _default_scene_state())
        open_conv.status = "closed"
        open_conv.ended_at = now
        db.add(open_conv)

    # 2. Close the player's open gathering_member rows. NPC members are
    # untouched; the existing dissolve-before-create in enter_location
    # handles that location's gatherings when it is next entered.
    open_memberships = db.exec(
        select(GatheringMember).where(
            GatheringMember.entity_id == player_id,
            GatheringMember.left_at.is_(None),
        )
    ).all()
    for gm in open_memberships:
        gm.left_at = now
        db.add(gm)

    # 3. Update the player's location.
    char.current_location_id = location_id
    db.add(char)

    db.commit()
    return {"status": "ok", "location_id": location_id}


class TravelBody(BaseModel):
    location_id: str


@app.post("/api/travel")
def travel(
    body: TravelBody,
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_session),
) -> dict:
    """Creator travel control — clean location transition (E1).

    Delegates to _perform_travel (shared with the in-fiction travel path).
    Does NOT call `enter_location` / `generate_gatherings` — the existing
    scene-entry flow remains the single owner of gathering generation.
    No narration is produced; this is a silent creator tool.

    Travel to the current location is a no-op. Travel to an id that is not
    a location of the player's world is rejected with 400, no state change.
    """
    player_id = player_id or _crud._player_character_id(db, _crud._world_id(db))
    char = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id!r} not found")
    player_entity = db.get(Entity, player_id)
    if player_entity is None:
        raise HTTPException(status_code=404, detail=f"Player entity {player_id!r} not found")

    result = _perform_travel(player_id, body.location_id, db)
    if result["status"] == "invalid_destination":
        raise HTTPException(
            status_code=400,
            detail=f"{body.location_id!r} is not a location of this world",
        )
    return result


@app.get("/api/conversations")
def list_conversations(db: Session = Depends(get_session)) -> list:
    convs = db.exec(
        select(Conversation).order_by(Conversation.started_at.desc())
    ).all()

    result = []
    for conv in convs:
        # Count messages in Python — local tool, not perf-critical.
        msg_count = len(
            db.exec(
                select(ConversationMessage).where(
                    ConversationMessage.conversation_id == conv.id
                )
            ).all()
        )
        loc_name: Optional[str] = None
        if conv.location_id:
            loc = db.get(Entity, conv.location_id)
            if loc:
                loc_name = loc.name

        result.append({
            "id": conv.id,
            "session_id": conv.session_id,
            "location": loc_name,
            "status": conv.status,
            "started_at": _iso(conv.started_at),
            "message_count": msg_count,
        })

    return result


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str, db: Session = Depends(get_session)) -> dict:
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conv_id)
        .order_by(ConversationMessage.turn_order)
    ).all()

    # Batch-resolve entity names for all speaker_ids in one query.
    speaker_ids = [m.speaker_id for m in msgs if m.speaker_id]
    name_map: dict[str, str] = {}
    if speaker_ids:
        entities = db.exec(
            select(Entity).where(Entity.id.in_(speaker_ids))
        ).all()
        name_map = {e.id: e.name for e in entities}

    # The conversation record also names the two parties directly.
    player_entity = db.get(Entity, conv.player_id) if conv.player_id else None
    npc_entity = db.get(Entity, conv.npc_id) if conv.npc_id else None
    loc_entity = db.get(Entity, conv.location_id) if conv.location_id else None

    messages = []
    for msg in msgs:
        # Priority: explicit speaker_id entity name → role-matched party name
        # → 'mj' sentinel → raw speaker label.
        display_name: str = (
            name_map.get(msg.speaker_id or "")
            or (player_entity.name if msg.speaker == "player" and player_entity else "")
            or (npc_entity.name if msg.speaker == "npc" and npc_entity else "")
            or ("MJ" if msg.speaker == "mj" else "")
            or msg.speaker
        )
        messages.append({
            "id": msg.id,
            "turn_order": msg.turn_order,
            "speaker": msg.speaker,
            "speaker_id": msg.speaker_id,
            "display_name": display_name,
            "content": msg.content,
        })

    return {
        "id": conv.id,
        "session_id": conv.session_id,
        "location": loc_entity.name if loc_entity else None,
        "status": conv.status,
        "started_at": _iso(conv.started_at),
        "ended_at": _iso(conv.ended_at),
        "player_id": conv.player_id,
        "player_name": player_entity.name if player_entity else conv.player_id,
        "npc_name": (npc_entity.name if npc_entity else conv.npc_id) or "le groupe",
        "gathering": _gathering_brief(conv.gathering_id, db) if conv.gathering_id else None,
        "messages": messages,
    }


@app.post("/api/conversations/{conv_id}/analyze")
def analyze_conversation_endpoint(
    conv_id: str,
    force: bool = Query(default=False),
    db: Session = Depends(get_session),
) -> dict:
    """Run window analysis on unanalyzed turns; return the resulting proposals.

    Without force: analyzes only `ConversationMessage` rows past
    `conversation.last_analyzed_turn`. If there is nothing new, returns
    {"status": "nothing_new"} without calling the model.
    With force=True: delete ONLY unreviewed ('proposed') rows for this
    conversation, reset `last_analyzed_turn` to 0, and re-run over the full
    transcript. Reviewed rows (applied/approved/rejected) are NEVER deleted —
    history is sacred.
    """
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if force:
        # Force is a debug path: re-analyzing the full transcript may
        # re-propose relation deltas that were already applied. Review
        # re-proposals manually.
        proposed_rows = db.exec(
            select(ProposedMutation).where(
                ProposedMutation.conversation_id == conv_id,
                ProposedMutation.status == "proposed",
            )
        ).all()
        for row in proposed_rows:
            db.delete(row)
        if proposed_rows:
            db.commit()
        conv.last_analyzed_turn = 0
        db.add(conv)
        db.commit()

    has_new = db.exec(
        select(ConversationMessage).where(
            ConversationMessage.conversation_id == conv_id,
            ConversationMessage.turn_order > conv.last_analyzed_turn,
            ConversationMessage.speaker.in_(("player", "npc")),
        )
    ).first()
    if has_new is None:
        return {"status": "nothing_new", "count": 0, "proposals": []}

    # Fail fast if Ollama is unreachable.
    try:
        ollama_client.ping()
    except ollama_client.OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        mutations = _analyze_window(conv_id, db)
    except (ValueError, SystemExit) as exc:
        # analyzer.py calls sys.exit(1) when no prompt template found;
        # catch SystemExit so we return HTTP 400 instead of killing the process.
        raise HTTPException(status_code=400, detail=str(exc))

    # Include duplicate warnings so the queue shows the banner immediately
    # after a forced re-analysis on a conversation that already has applied rows.
    proposals = [
        {**_mutation_dict(m), "applied_duplicate": _find_applied_duplicate(m, db)}
        for m in mutations
    ]

    return {
        "status": "ok",
        "count": len(mutations),
        "proposals": proposals,
    }


# Verbatim interval labels (BRIEF-0014-a M3 / BRIEF-0014-b item 8) — the
# creator picks the elapsed interval at invocation; nothing is stored.
_VALID_TICK_INTERVALS = frozenset({"quelques heures", "quelques jours", "quelques semaines"})


class WorldTickBody(BaseModel):
    scope_type: str  # npcs | location | faction
    npc_ids: Optional[list[str]] = None  # scope_type == "npcs"
    scope_id: Optional[str] = None       # scope_type == "location" | "faction"
    interval: str


@app.post("/api/world-tick")
def world_tick_endpoint(
    body: WorldTickBody,
    db: Session = Depends(get_session),
) -> dict:
    """Resolve a scope to NPC ids, then run one world tick over them
    (TICKET-0014, BRIEF-0014-b). Writes `proposed_mutation` rows only (C2) —
    every result still needs creator approval through the normal queue.

    Unknown interval, unknown scope_type, or an empty resolved NPC list ->
    422, no model call, nothing written.
    """
    if body.interval not in _VALID_TICK_INTERVALS:
        raise HTTPException(422, f"interval must be one of {sorted(_VALID_TICK_INTERVALS)}")

    world_id = _crud._world_id(db)
    npc_ids: list[str]

    if body.scope_type == "npcs":
        npc_ids = []
        for entity_id in (body.npc_ids or []):
            char = db.get(Character, entity_id)
            entity = db.get(Entity, entity_id)
            if (
                char is None or entity is None
                or entity.world_id != world_id
                or char.character_type != "npc"
            ):
                raise HTTPException(
                    422, f"{entity_id!r} does not resolve to an NPC character of the active world"
                )
            npc_ids.append(entity_id)

    elif body.scope_type == "location":
        if not body.scope_id:
            raise HTTPException(422, "scope_id is required for scope_type='location'")
        rows = db.exec(
            select(Character)
            .join(Entity, Entity.id == Character.id)
            .where(
                Entity.world_id == world_id,
                Character.current_location_id == body.scope_id,
                Character.character_type == "npc",
                Character.vital_status == "alive",
                Entity.status == "active",
            )
        ).all()
        npc_ids = [c.id for c in rows]

    elif body.scope_type == "faction":
        if not body.scope_id:
            raise HTTPException(422, "scope_id is required for scope_type='faction'")
        rows = db.exec(
            select(Character)
            .join(Entity, Entity.id == Character.id)
            .join(FactionMembership, FactionMembership.entity_id == Character.id)
            .where(
                Entity.world_id == world_id,
                FactionMembership.faction_id == body.scope_id,
                FactionMembership.left_at.is_(None),
                Character.character_type == "npc",
                Character.vital_status == "alive",
                Entity.status == "active",
            )
        ).all()
        npc_ids = [c.id for c in rows]

    else:
        raise HTTPException(422, f"unknown scope_type {body.scope_type!r}")

    if not npc_ids:
        raise HTTPException(422, "resolved scope is empty — nothing to tick")

    # Fail fast if Ollama is unreachable (same guard as /analyze).
    try:
        ollama_client.ping()
    except ollama_client.OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return _run_world_tick(
        db, npc_ids, body.interval, scope_type=body.scope_type, scope_id=body.scope_id
    )


@app.get("/api/mutations")
def list_mutations(
    status: str = Query(default="proposed"),
    db: Session = Depends(get_session),
) -> list:
    mutations = db.exec(
        select(ProposedMutation)
        .where(ProposedMutation.status == status)
        .where(ProposedMutation.world_id == _crud._world_id(db))
        .order_by(ProposedMutation.proposed_at)
    ).all()
    result = []
    for m in mutations:
        d = _mutation_dict(m)
        # For proposed rows only: surface any already-applied equivalent so the
        # UI can show the duplicate-risk banner before the creator clicks Approve.
        d["applied_duplicate"] = (
            _find_applied_duplicate(m, db) if m.status == "proposed" else None
        )
        result.append(d)
    return result


class RejectBody(BaseModel):
    creator_notes: Optional[str] = None


@app.post("/api/mutations/{mut_id}/reject")
def reject_mutation(
    mut_id: str,
    body: RejectBody = RejectBody(),
    db: Session = Depends(get_session),
) -> dict:
    mut = db.get(ProposedMutation, mut_id)
    if mut is None:
        raise HTTPException(status_code=404, detail="Mutation not found")
    if mut.status == "applied":
        raise HTTPException(
            status_code=409,
            detail="Cannot reject a mutation that has already been applied to canon.",
        )

    mut.status = "rejected"
    mut.reviewed_at = datetime.now(UTC)
    if body.creator_notes:
        mut.creator_notes = body.creator_notes
    db.add(mut)
    db.commit()
    db.refresh(mut)
    return _mutation_dict(mut)


class ApproveBody(BaseModel):
    # The creator may edit the payload in the UI before approving.
    # Sent as a JSON string so the textarea value is passed verbatim.
    payload: Optional[str] = None
    creator_notes: Optional[str] = None


@app.post("/api/mutations/{mut_id}/approve")
def approve_mutation(
    mut_id: str,
    body: ApproveBody = ApproveBody(),
    db: Session = Depends(get_session),
) -> dict:
    """Approve and apply a mutation to canon.

    Success path  → status='applied',  applied_at set.
    Failure path  → status='approved', error stored in creator_notes, returned
                    to the caller.  Canon is never partially written.

    The canon writes happen inside a SAVEPOINT so a failure rolls back only
    those writes — the mutation row update (reviewed_at, notes, status) lives
    in the outer transaction and is always committed.
    """
    mut = db.get(ProposedMutation, mut_id)
    if mut is None:
        raise HTTPException(status_code=404, detail="Mutation not found")

    if mut.status == "applied":
        return {"status": "already_applied", "mutation": _mutation_dict(mut)}

    # Apply an edited payload from the form before writing anything.
    if body.payload is not None:
        try:
            mut.payload = json.loads(body.payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422, detail=f"Payload is not valid JSON: {exc}"
            )

    if body.creator_notes is not None:
        mut.creator_notes = body.creator_notes

    now = datetime.now(UTC)
    mut.reviewed_at = now

    # ── entity_creation short-circuit (TICKET-0019, BRIEF-0019-a) ───────────
    # Approval PARKS the germ — it never reaches _apply_mutation, never a
    # savepoint, never the "[apply error]" framing (RECON F3): I2 forbids any
    # synchronous authoring call here. A fresh canon-existence recheck (F5)
    # routes a genuine collision to "Needs attention" instead of parking it.
    if mut.mutation_type == "entity_creation":
        payload = mut.payload if isinstance(mut.payload, dict) else {}
        name = str(payload.get("name") or "").strip()
        collision = any(
            e.name.casefold() == name.casefold()
            for e in db.exec(
                select(Entity).where(Entity.world_id == mut.world_id, Entity.status == "active")
            ).all()
        )
        if collision:
            mut.status = "approved"
            mut.creator_notes = _append_note(
                mut.creator_notes, f"une entité active porte déjà ce nom : {name!r}"
            )
            db.add(mut)
            db.commit()
            db.refresh(mut)
            return {
                "status": "approved",
                "error": mut.creator_notes,
                "mutation": _mutation_dict(mut),
            }

        mut.status = "approved"
        mut.creator_notes = _append_note(mut.creator_notes, "en attente de réalisation — onglet Création")
        db.add(mut)
        db.commit()
        db.refresh(mut)
        return {
            "status": "pending_realization",
            "error": "en attente de réalisation — onglet Création",
            "mutation": _mutation_dict(mut),
        }

    try:
        # SAVEPOINT: canon writes are rolled back on failure; the outer
        # transaction (mutation row update) stays live either way.
        with db.begin_nested():
            error = _apply_mutation(mut, db)
            if error:
                raise RuntimeError(error)

        # Savepoint committed → canon updated.
        mut.status = "applied"
        mut.applied_at = now
        db.add(mut)
        db.commit()
        db.refresh(mut)
        return {"status": "applied", "mutation": _mutation_dict(mut)}

    except Exception as exc:
        # Savepoint rolled back — canon is clean.
        error_msg = str(exc)
        mut.status = "approved"
        prior = mut.creator_notes or ""
        mut.creator_notes = f"{prior}\n[apply error] {error_msg}".strip()
        db.add(mut)
        db.commit()
        db.refresh(mut)
        return {
            "status": "approved",
            "error": error_msg,
            "mutation": _mutation_dict(mut),
        }


_BATCH_REVIEW_MARKER = "batch-review"


def _append_note(existing: Optional[str], note: str) -> str:
    prior = existing or ""
    return f"{prior}\n{note}".strip()


class BatchReviewBody(BaseModel):
    action: str  # "approve" | "reject"
    mutation_ids: list[str]


@app.post("/api/mutations/batch-review")
def batch_review_mutations(
    body: BatchReviewBody,
    db: Session = Depends(get_session),
) -> dict:
    """Approve or reject several proposed mutations in one gesture.

    Sequential, per-row, through the SAME paths as unit review
    (`_apply_mutation` for approve, the unit reject fields for reject).
    Payloads are applied exactly as proposed — no batch payload editing.

    Each row is re-loaded and re-checked: only `status == 'proposed'` rows
    are processed. Anything else (already reviewed, e.g. a stale client
    selection) is SKIPPED, never touched — reviewed rows are immutable
    history. One row failing to apply never stops the loop; it lands in
    "Needs attention" exactly as in unit review.

    Every processed row gets the `batch-review` marker appended to
    `creator_notes`, so a batch decision is distinguishable from a unit
    decision later.
    """
    if body.action not in ("approve", "reject"):
        raise HTTPException(
            status_code=422, detail="action must be 'approve' or 'reject'"
        )

    now = datetime.now(UTC)
    skipped = 0

    if body.action == "approve":
        applied = 0
        needs_attention = 0

        for mut_id in body.mutation_ids:
            mut = db.get(ProposedMutation, mut_id)
            if mut is None or mut.status != "proposed":
                skipped += 1
                continue

            mut.reviewed_at = now

            try:
                # SAVEPOINT: same per-row isolation as unit approve — a failed
                # apply rolls back only the canon writes for this row.
                with db.begin_nested():
                    error = _apply_mutation(mut, db)
                    if error:
                        raise RuntimeError(error)

                mut.status = "applied"
                mut.applied_at = now
                mut.creator_notes = _append_note(
                    mut.creator_notes, _BATCH_REVIEW_MARKER
                )
                db.add(mut)
                db.commit()
                applied += 1

            except Exception as exc:
                error_msg = str(exc)
                mut.status = "approved"
                mut.creator_notes = _append_note(
                    _append_note(mut.creator_notes, f"[apply error] {error_msg}"),
                    _BATCH_REVIEW_MARKER,
                )
                db.add(mut)
                db.commit()
                needs_attention += 1

        return {
            "status": "ok",
            "action": "approve",
            "applied": applied,
            "needs_attention": needs_attention,
            "skipped": skipped,
        }

    # action == "reject"
    rejected = 0
    for mut_id in body.mutation_ids:
        mut = db.get(ProposedMutation, mut_id)
        if mut is None or mut.status != "proposed":
            skipped += 1
            continue

        mut.status = "rejected"
        mut.reviewed_at = now
        mut.creator_notes = _append_note(mut.creator_notes, _BATCH_REVIEW_MARKER)
        db.add(mut)
        db.commit()
        rejected += 1

    return {
        "status": "ok",
        "action": "reject",
        "rejected": rejected,
        "skipped": skipped,
    }
