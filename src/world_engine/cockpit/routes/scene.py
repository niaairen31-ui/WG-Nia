"""Scene lifecycle routes: view, enter, join, leave.

Extracted from `cockpit/routes/play.py` (TICKET-0032, C2: refactor over
module-budget exemption) — `routes/play.py` sat at exactly 1000/1000 lines
(the G1 module-budget cap, no baseline exemption available; see
`tooling/verify/checks/module_budget.py`'s "no permanent exemptions"
doctrine) and BRIEF-0032-a's G2-b addition had no room to land there. Pure
move, no logic change, no route path/method change — every handler below
keeps its original body verbatim, mirroring the BRIEF-0027-d precedent that
first split `cockpit/app.py` this way.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from ... import ollama_client
from ...gathering import enter_location as _enter_location
from ...analyzer import analyze_window as _analyze_window
from ...prompt_registry import effective_model
from ...prompt_store import current_prompt
from ...context import assemble_mj_context, format_item_list_for_interpretation
from ...db import get_session
from ...models import Character, Conversation, Entity, Gathering, GatheringMember, Visit
from .. import crud as _crud
from ..play import (
    ResponseMode,
    _active_members,
    _gathering_brief,
    _get_or_open_session,
    _join_gathering,
    _load_npc_dialogue_template,
    _open_gatherings,
    _player_gathering,
)
from ..play_physical import (
    _build_establishment_narration,
    _compute_return_delta,
    _default_scene_state,
    _interpret_mode,
    _load_mj_interpret_template,
    _render_gathering_status,
    _resolve_join_target,
    _write_scene_state,
)
from ..play_stream import _scene_response

router = APIRouter()
_log = logging.getLogger(__name__)


@router.get("/api/scene")
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


@router.post("/api/scene/enter")
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
    player_text: Optional[str] = None      # player's free-text join expression
    player_id: Optional[str] = None        # defaults to the resolved player character
    # G2-b (TICKET-0032): deterministic targeted join — when present, the
    # interpretation step is skipped entirely; code resolves what code knows.
    target_gathering_id: Optional[str] = None


def _scene_join_resolve_player(body: "SceneJoinBody", db: Session) -> tuple[str, str, str, str]:
    """(player_id, location_id, world_id, location_name)."""
    player_id = body.player_id or _crud._player_character_id(db, _crud._world_id(db))
    char = db.get(Character, player_id)
    if char is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id!r} not found")
    if not char.current_location_id:
        raise HTTPException(status_code=400, detail="Player has no current location")
    player_entity = db.get(Entity, player_id)
    if player_entity is None:
        raise HTTPException(status_code=404, detail=f"Player entity {player_id!r} not found")

    location_id = char.current_location_id
    world_id = player_entity.world_id
    loc_entity = db.get(Entity, location_id)
    location_name = loc_entity.name if loc_entity else location_id
    return player_id, location_id, world_id, location_name

def _scene_join_already_member(player_g: Gathering, player_id: str, location_id: str, world_id: str, sess, db: Session) -> dict:
    existing_conv = db.exec(
        select(Conversation).where(
            Conversation.gathering_id == player_g.id,
            Conversation.player_id    == player_id,
            Conversation.status       == "open",
        )
    ).first()
    if existing_conv:
        return {
            "already_joined":  True,
            "gathering":       _gathering_brief(player_g.id, db),
            "conversation_id": existing_conv.id,
        }

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

def _scene_join_resolve_and_create(
    body: "SceneJoinBody", player_id: str, location_id: str, location_name: str,
    world_id: str, open_g: list[Gathering], sess, db: Session,
) -> dict:
    # A2 reused: interpret the text to resolve a gathering target, then create the conversation.
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
    # Not classified as join: treat the full text as the reference anyway — join-field intent is clear.
    if mode != ResponseMode.join:
        reference = body.player_text

    resolved_id = _resolve_join_target(reference, open_g, db)
    if resolved_id is None:
        return {"join_candidates": [_gathering_brief(g.id, db) for g in open_g]}

    return _scene_join_create_for_gathering(resolved_id, player_id, location_id, world_id, sess, db)


def _scene_join_create_for_gathering(
    resolved_id: str, player_id: str, location_id: str, world_id: str, sess, db: Session,
) -> dict:
    behaviour   = _load_npc_dialogue_template(world_id, db)
    behaviour_version = current_prompt(db, behaviour)
    model       = effective_model(behaviour, ollama_client.DEFAULT_MODEL)
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


@router.post("/api/scene/join")
def scene_join(body: SceneJoinBody, db: Session = Depends(get_session)) -> dict:
    """Join a gathering from the scene view — creates the conversation.
    Autonomous join: no pre-existing conversation required. Exactly one of
    `player_text` / `target_gathering_id` must be set (422 otherwise).

    - `player_text`: interprets the free text (full pt-mj-interpretation
      pipeline, contract A2) to resolve a gathering target.
    - `target_gathering_id` (G2-b, TICKET-0032): the caller already knows
      the exact gathering (e.g. the spatial canvas's "Parler" affordance,
      resolved client-side from the scene roster) — the interpretation
      step is skipped entirely, zero model calls, after validating the
      gathering is open at the player's current location/session.

    Either way:
    - Resolved (exactly one match): inserts gathering_member, creates a
      conversation anchored to the gathering (npc_id=None — pure gathering
      conversation, A3-group responder). Returns {"conversation_id": ..., "gathering": {...}}.
    - Unresolved / ambiguous (free text only): returns {"join_candidates": [...]} so the
      cockpit picker (C2 selector) can surface the open gatherings.
    - Already joined: returns {"already_joined": True, "gathering": {...},
      "conversation_id": ...} with the active conversation if one exists.
    Joining is not a canon mutation — no proposed_mutation row is produced.
    """
    if (body.player_text is None) == (body.target_gathering_id is None):
        raise HTTPException(status_code=422, detail="Provide exactly one of player_text or target_gathering_id")

    player_id, location_id, world_id, location_name = _scene_join_resolve_player(body, db)

    sess    = _get_or_open_session(world_id, db)
    open_g  = _open_gatherings(location_id, sess.id, db)
    player_g = _player_gathering(player_id, location_id, sess.id, db)

    if player_g is not None:
        return _scene_join_already_member(player_g, player_id, location_id, world_id, sess, db)

    if not open_g:
        raise HTTPException(status_code=400, detail="No open gatherings at this location")

    if body.target_gathering_id is not None:
        gathering = db.get(Gathering, body.target_gathering_id)
        if gathering is None or gathering.status != "open":
            raise HTTPException(status_code=404, detail="Gathering not found or not open")
        if gathering.location_id != location_id or gathering.session_id != sess.id:
            raise HTTPException(status_code=400, detail="Gathering does not match this location/session")
        return _scene_join_create_for_gathering(gathering.id, player_id, location_id, world_id, sess, db)

    return _scene_join_resolve_and_create(
        body, player_id, location_id, location_name, world_id, open_g, sess, db,
    )


@router.post("/api/scene/leave")
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
