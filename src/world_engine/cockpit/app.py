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
from typing import Iterator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import ollama_client
from ..gathering import enter_location as _enter_location
from ..gathering import migrate_npc as _migrate_npc
from ..analyzer import analyze_conversation as _analyze_conversation
from ..analyzer import analyze_single_turn as _analyze_single_turn
from ..context import assemble_mj_context, assemble_npc_context, format_mj_context
from ..db import engine, get_session
from ..models import (
    Character,
    Conversation,
    ConversationMessage,
    Entity,
    Gathering,
    GatheringMember,
    PromptTemplate,
    ProposedMutation,
    Relation,
    Session as GameSession,
)
from ..writes import write_knowledge, write_relation
from . import crud as _crud

_INDEX_HTML = Path(__file__).parent / "index.html"
_log = logging.getLogger(__name__)

app = FastAPI(title="World Engine Cockpit", docs_url=None, redoc_url=None)
app.include_router(_crud.router)


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
        "proposed_at": _iso(m.proposed_at),
        "reviewed_at": _iso(m.reviewed_at),
        "applied_at": _iso(m.applied_at),
    }


# ── Duplicate-application guard ───────────────────────────────────────────────

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
    """
    if not mut.conversation_id:
        return None

    payload = mut.payload if isinstance(mut.payload, dict) else {}

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

    return None


# ── Deduplication key ────────────────────────────────────────────────────────

def _mutation_match_key(mutation_type: str, payload: dict):
    """Return a hashable match key for per-conversation deduplication, or None.

    Used by the final-pass analyze endpoint to avoid re-proposing what per-turn
    immediate flags already captured.  Only idempotent mutation types are keyed
    here — applying the same idempotent fact twice is wrong; accumulating deltas
    (relation_change) must never be suppressed.

    relation_change is intentionally EXCLUDED: deltas accumulate across turns
    and the final pass never proposes them (per-turn flags own all relation arcs).
    """
    if mutation_type == "new_knowledge":
        return ("new_knowledge", payload.get("entity_id"), payload.get("subject"))
    if mutation_type == "status_change":
        eid = payload.get("entity_id")
        return ("status_change", eid) if eid else None
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

    Unimplemented types (event_creation, entity_creation, knowledge_change, other)
    are left as 'approved' with a note — better un-applied than wrongly applied.
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
        if char.faction_id:
            fac = db.get(Entity, char.faction_id)
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
        .where(
            GatheringMember.gathering_id == gathering_id,
            GatheringMember.left_at.is_(None),
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
) -> str:
    """Pick exactly one active gathering member to respond (contract A3 hybrid).

    Asks the MJ to choose; resolves the returned name against the active
    roster (A2-style exact, case-insensitive match). Falls back to the first
    active member on a missing template, a call failure, or an unresolved
    name — cadence B1 (exactly one responder per turn) holds regardless; the
    scene must stay playable.
    """
    if template is not None:
        member_lines = "\n".join(f"- {e.name}" for _gm, e in members)
        user_msg = (
            template.user_template
            .replace("{location_name}", location_name)
            .replace("{group_label}", gathering.label or "Groupe")
            .replace("{member_list}", member_lines)
            .replace("{player_line}", player_line)
            + "\n/no_think"
        )
        try:
            raw = ollama_client.chat(
                [
                    {"role": "system", "content": template.system_prompt},
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

    def _signal_line(e: Entity) -> str:
        rel = _npc_rel(e.id)
        signal = f"relation={rel.type} ({rel.intensity}/100)" if rel else "relation=neutre (50/100)"
        return f"- {e.name} : {signal}, statut={e.status}"

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

    user_msg = (
        template.user_template
        .replace("{location_name}", location_name)
        .replace("{interpreted_mode}", interpreted_mode.value)
        .replace("{player_line}", player_line)
        .replace("{member_signal_list}", "\n\n".join(parts))
        + "\n/no_think"
    )
    try:
        raw = ollama_client.chat(
            [
                {"role": "system", "content": template.system_prompt},
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
    interpret_system: str,
    interpret_user_tpl: str,
    model: str,
) -> tuple[ResponseMode, str]:
    """Classify the player's input into a ResponseMode via the local model.

    Returns `(mode, reference)`. `reference` is the model's free-text quote of
    what the player named when joining a group (contract A2 — resolved against
    the actual roster downstream by `_resolve_join_target`, never invented);
    empty for every other mode.

    Falls back to `(ResponseMode.dialogue, "")` on any failure (parse error,
    unknown value, Ollama error). A misclassification must never break a turn.
    """
    user_msg = (
        interpret_user_tpl
        .replace("{npc_name}", npc_name)
        .replace("{location_name}", location_name)
        .replace("{gathering_status}", gathering_status)
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
        _log.info(
            "MJ interpret: %r → %s (reason: %s)%s",
            player_line[:60], mode.value, obj.get("reason", ""),
            f" [reference: {reference!r}]" if mode == ResponseMode.join else "",
        )
        return mode, reference
    except Exception as exc:
        _log.warning("MJ interpret failed (%s), fallback to dialogue", exc)
        return ResponseMode.dialogue, ""


def _build_mj_user(
    *,
    mode: ResponseMode,
    mj_user_template: str,
    npc_name: str,
    location_name: str,
    player_line: str,
    npc_reply: str,
    mj_context: dict | None = None,
) -> str:
    """Build the MJ narration user message for the given mode.

    dialogue     → existing template (verbatim NPC quote contract unchanged).
    npc_reaction → third-person wordless reaction; no dialogue to quote.
    scene        → environment description only; NPC not involved.

    `mj_context` (schema v1.12, scope D-b3): the dict returned by
    `assemble_mj_context`, rendered via `format_mj_context` and prepended as
    a "CONTEXTE DE SCÈNE" block — the player's perception boundary (location,
    co-presents, player knowledge, public events). Empty/None → no block.
    `scene` mode benefits most (environment prose finally has material).

    /no_think appended on all modes; the stream filter backs it up.
    """
    context_block = format_mj_context(mj_context) if mj_context else ""
    if context_block:
        context_block = f"=== CONTEXTE DE SCÈNE ===\n{context_block}\n"

    if mode == ResponseMode.dialogue:
        return (
            mj_user_template
            .replace("{mj_context}", context_block)
            .replace("{npc_name}", npc_name)
            .replace("{location_name}", location_name)
            .replace("{player_line}", player_line)
            .replace("{npc_reply}", npc_reply)
            + "\n/no_think"
        )
    if mode == ResponseMode.npc_reaction:
        return (
            f"{context_block}"
            f"Scène : {npc_name} dans « {location_name} ».\n"
            f"Mode : réaction non-verbale.\n\n"
            f"Le joueur fait :\n{player_line}\n\n"
            f"{npc_name} réagit sans prononcer un mot :\n{npc_reply}\n\n"
            f"Narration MJ — traduis cette réaction en prose narrative à la troisième "
            f"personne. Aucun guillemet français, aucune ligne de dialogue, aucun mot "
            f"inventé. 2–3 phrases courtes.\n"
            f"Narration MJ :\n/no_think"
        )
    # ResponseMode.scene
    return (
        f"{context_block}"
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

    Defaults: player = char-player (Joran), location = loc-dernier-verre.
    These defaults are the pilot setup; a future player view will pass explicit
    IDs from the player's active session instead.
    """
    # Resolve defaults (pilot player / pilot location).
    player_id   = body.player_id   or "char-player"
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
    assembled_context = assemble_npc_context(body.npc_id, player_id, location_id, db)
    system_prompt = f"{behaviour.system_prompt}\n\n{assembled_context}"

    # MJ context snapshot (schema v1.12, scope D-b3): static parts only
    # (location, player_knowledge, public_events) — co_presents is dynamic
    # and read fresh at narration time, never snapshotted. This is what a
    # future bleed auditor compares MJ narration against.
    mj_context = assemble_mj_context(db, player_id, location_id)
    mj_snapshot = {k: v for k, v in mj_context.items() if k != "co_presents"}

    model = ollama_client.DEFAULT_MODEL
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
            "behaviour_prompt": behaviour.system_prompt,
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
    mj_user_template   = mj_template.user_template
    mj_system_prompt   = mj_template.system_prompt
    interpret_system   = interpret_template.system_prompt
    interpret_user_tpl = interpret_template.user_template

    def _stream() -> Iterator[str]:
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
        mode, reference = _interpret_mode(
            player_line=content,
            npc_name=npc_name,
            location_name=location_name,
            gathering_status=gathering_status,
            recent_transcript=recent_transcript,
            interpret_system=interpret_system,
            interpret_user_tpl=interpret_user_tpl,
            model=model,
        )
        # 'join' is only meaningful while ungrouped — a misclassification while
        # already in a gathering degrades to dialogue (never breaks a turn).
        if mode == ResponseMode.join and player_gathering is not None:
            mode = ResponseMode.dialogue

        npc_reply = ""
        responder_id: Optional[str] = None
        responder_name = npc_name
        extra_event: Optional[dict] = None

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
                    responder_context = assemble_npc_context(
                        responder_id, conv.player_id, conv.location_id, db,
                        gathering_id=conv.gathering_id,
                    )
                    responder_system_prompt = f"{responder_behaviour.system_prompt}\n\n{responder_context}"

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
            mj_context = (
                assemble_mj_context(
                    db, conv.player_id, conv.location_id,
                    gathering_id=player_gathering.id if player_gathering else None,
                )
                if conv.location_id else None
            )
            mj_user = _build_mj_user(
                mode=mode,
                mj_user_template=mj_user_template,
                npc_name=responder_name,
                location_name=location_name,
                player_line=content,
                npc_reply=npc_reply,
                mj_context=mj_context,
            )

        # ── MJ narration (streamed to the player) ─────────────────────────────
        mj_messages = [
            {"role": "system", "content": mj_system_prompt},
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
                        init_ctx = assemble_npc_context(
                            initiator_id, conv.player_id, conv.location_id, db,
                            gathering_id=conv.gathering_id,
                        )
                        # C2: load JSON-output contract from dedicated template
                        # (usage="npc_initiative_act") — never bleeds into normal
                        # /say turns which use the shared npc_dialogue template.
                        init_act_tmpl = _load_npc_initiative_act_template(world_id, db)
                        init_act_instruction = (
                            init_act_tmpl.system_prompt
                            if init_act_tmpl is not None
                            else _NPC_INITIATIVE_ACT_FALLBACK
                        )
                        init_system = (
                            f"{init_behaviour.system_prompt}\n\n{init_ctx}"
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

        # Per-turn immediate analysis (sync-after-stream). For scene turns
        # npc_reply is "" — the analyzer handles empty replies correctly (no rows).
        # Failures are silently swallowed — analysis must never surface to the player.
        with Session(engine) as flag_db:
            try:
                immediate = _analyze_single_turn(
                    player_line=content,
                    npc_reply=npc_reply,
                    conversation_id=conv_id,
                    db=flag_db,
                    model=model,
                    npc_entity_id=responder_id,
                )
                for mut in immediate:
                    flag_db.add(mut)
                if immediate:
                    flag_db.commit()
            except (Exception, SystemExit):
                pass

        # Per-turn analysis for the initiative NPC line (same pipeline — the
        # act itself creates no mutation, only its consequences do, per D1).
        if initiative_npc_reply:
            with Session(engine) as flag_db:
                try:
                    initiative_immediate = _analyze_single_turn(
                        player_line="",  # spontaneous — no player line to re-analyze
                        npc_reply=initiative_npc_reply,
                        conversation_id=conv_id,
                        db=flag_db,
                        model=model,
                        npc_entity_id=initiative_initiator_id,
                    )
                    for mut in initiative_immediate:
                        flag_db.add(mut)
                    if initiative_immediate:
                        flag_db.commit()
                except (Exception, SystemExit):
                    pass

    return StreamingResponse(_stream(), media_type="text/event-stream")


@app.post("/api/conversations/{conv_id}/end")
def end_conversation(conv_id: str, db: Session = Depends(get_session)) -> dict:
    """Close a conversation; analysis stays manual (use the Analyze button)."""
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.status == "closed":
        return {"status": "already_closed"}
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


def _scene_response(location_id: str, player_id: str, world_id: str, db: Session) -> dict:
    """Build the canonical scene dict (shared by GET /api/scene and POST /api/scene/enter).

    Includes `active_conversation_id`: the open conversation for the player's
    current gathering, if any. The UI uses this to offer "Reprendre" vs
    "Continuer à parler" (a new conversation in the same gathering).
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
    }


@app.get("/api/scene")
def get_scene(
    player_id: str = Query("char-player"),
    db: Session = Depends(get_session),
) -> dict:
    """Current scene for the player's location: open gatherings + their rosters.

    Read-only — never calls enter_location. Use POST /api/scene/enter to
    generate the gathering partition on a genuine location transition.
    """
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
    player_id: str = Query("char-player"),
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
    if not open_g:
        # No open gatherings → genuine location transition (or first load).
        # Generate the partition; never raises (falls back to all-solo on error).
        _enter_location(location_id, sess.id, db)

    return _scene_response(location_id, player_id, world_id, db)


class SceneJoinBody(BaseModel):
    player_text: str                # player's free-text join expression
    player_id: str = "char-player"  # defaults to the pilot player


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
    player_id     = body.player_id
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
        model     = ollama_client.DEFAULT_MODEL
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
                "behaviour_prompt":   behaviour.system_prompt,
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
    model             = ollama_client.DEFAULT_MODEL

    # Provide a plausible NPC name for the template context (any member present).
    any_npc_name = "?"
    for g in open_g:
        for _gm, e in _active_members(g.id, db):
            any_npc_name = e.name
            break
        if any_npc_name != "?":
            break

    mode, reference = _interpret_mode(
        player_line       = body.player_text,
        npc_name          = any_npc_name,
        location_name     = location_name,
        gathering_status  = gathering_status,
        recent_transcript = "",
        interpret_system  = interpret_template.system_prompt,
        interpret_user_tpl = interpret_template.user_template,
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
            "behaviour_prompt":   behaviour.system_prompt,
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
    player_id: str = Query("char-player"),
    db: Session = Depends(get_session),
) -> dict:
    """Remove the player from their current gathering.

    Sets GatheringMember.left_at to now — the gathering itself and its other
    members are unaffected.  Any open conversation the player had in that
    gathering is closed (the player has left; no more turns).

    Returns the updated scene so the UI can re-render directly.
    """
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
        open_conv.status = "closed"
        db.add(open_conv)

    db.commit()

    return _scene_response(location_id, player_id, world_id, db)


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
    """Run post-conversation analysis; return the resulting proposals.

    Without force: if unreviewed (proposed) rows already exist, return them.
    With force=True: delete ONLY unreviewed rows and re-run.
    Reviewed rows (applied/approved/rejected) are NEVER deleted — history is sacred.
    """
    all_for_conv = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == conv_id
        )
    ).all()

    # Separate unreviewed (deletable) from reviewed (immutable history).
    proposed_rows = [r for r in all_for_conv if r.status == "proposed"]
    reviewed_rows = [r for r in all_for_conv if r.status != "proposed"]

    # Idempotency guard: only block on unreviewed proposals (reviewed rows are
    # fine to have — they don't block a re-analysis).
    if proposed_rows and not force:
        return {
            "status": "existing",
            "count": len(proposed_rows),
            "proposals": [_mutation_dict(m) for m in proposed_rows],
        }

    # Force: delete only proposed rows; reviewed rows survive regardless.
    for row in proposed_rows:
        db.delete(row)
    if proposed_rows:
        db.commit()

    # Fail fast if Ollama is unreachable.
    try:
        ollama_client.ping()
    except ollama_client.OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        mutations = _analyze_conversation(conv_id, db)
    except (ValueError, SystemExit) as exc:
        # analyzer.py calls sys.exit(1) when no prompt template found;
        # catch SystemExit so we return HTTP 400 instead of killing the process.
        raise HTTPException(status_code=400, detail=str(exc))

    # Dedupe against existing proposed rows for this conversation (per-turn
    # immediate flags). Uses the same logical match key as _find_applied_duplicate.
    # Only write what the per-turn flags missed; never re-propose an equivalent.
    # After force=True the per-turn rows were already deleted above, so this
    # set is empty and all final-pass results are written as-is.
    still_proposed = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == conv_id,
            ProposedMutation.status == "proposed",
        )
    ).all()
    if still_proposed:
        covered: set = set()
        for ep in still_proposed:
            ep_payload = ep.payload if isinstance(ep.payload, dict) else {}
            key = _mutation_match_key(ep.mutation_type, ep_payload)
            if key is not None:
                covered.add(key)
        mutations = [
            m for m in mutations
            if _mutation_match_key(
                m.mutation_type,
                m.payload if isinstance(m.payload, dict) else {},
            ) not in covered
        ]

    for mut in mutations:
        db.add(mut)
    db.commit()

    # Include duplicate warnings so the queue shows the banner immediately
    # after a forced re-analysis on a conversation that already has applied rows.
    proposals = []
    for m in mutations:
        d = _mutation_dict(m)
        d["applied_duplicate"] = _find_applied_duplicate(m, db)
        proposals.append(d)

    return {
        "status": "ok",
        "count": len(mutations),
        "proposals": proposals,
    }


@app.get("/api/mutations")
def list_mutations(
    status: str = Query(default="proposed"),
    db: Session = Depends(get_session),
) -> list:
    mutations = db.exec(
        select(ProposedMutation)
        .where(ProposedMutation.status == status)
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
