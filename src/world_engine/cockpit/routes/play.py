"""Play-path routes: conversations, scene, travel, world-tick.

Split out of `cockpit/app.py` (TICKET-0027, BRIEF-0027-d) — pure move, no
logic change, no route path/method change. `say` stays the thin
orchestrator it already was (BRIEF-0027-b), calling into `cockpit/play.py`.
Every other route handler here keeps its original body verbatim; the
private helpers it calls were redistributed into `cockpit/play.py`,
`cockpit/play_physical.py` and `cockpit/play_stream.py` by which of those
existing modules already depended on them (module-budget-driven where a
helper had no prior consumer — see BRIEF-0027-d execution notes).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ... import ollama_client
from ...gathering import enter_location as _enter_location
from ...analyzer import analyze_window as _analyze_window
from ...tick import run_world_tick as _run_world_tick
from ...prompt_registry import effective_model
from ...prompt_store import current_prompt
from ...context import assemble_mj_context, assemble_npc_context, format_item_list_for_interpretation
from ...db import get_session
from ...models import (
    Character,
    Conversation,
    ConversationMessage,
    Entity,
    FactionMembership,
    Gathering,
    GatheringMember,
    ProposedMutation,
    Visit,
)
from .. import crud as _crud
from ..play import (
    ResponseMode,
    _active_members,
    _gathering_brief,
    _get_or_open_session,
    _join_gathering,
    _load_npc_dialogue_template,
    _location_neighbours,
    _npc_dialogue_system_prompt,
    _open_gatherings,
    _player_gathering,
)
from ..play_physical import (
    _CONDITION_LADDER,
    _PHYSICAL_DOMAINS,
    _VALID_CONSTRAINTS,
    _build_establishment_narration,
    _compute_return_delta,
    _default_scene_state,
    _get_scene_state,
    _render_gathering_status,
    _resolve_join_target,
    _write_scene_state,
)
from ..play_stream import _perform_travel, _scene_response
from .mutations import _find_applied_duplicate, _iso, _mutation_dict

router = APIRouter()


_VALID_TICK_INTERVALS = frozenset({"quelques heures", "quelques jours", "quelques semaines"})


class StartConversationBody(BaseModel):
    npc_id: str
    # Defaults: pilot player and tavern location (set by /start handler).
    location_id: Optional[str] = None
    player_id: Optional[str] = None


@router.post("/api/conversations/start")
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


@router.post("/api/conversations/{conv_id}/say")
def say(
    conv_id: str,
    body: SayBody,
    db: Session = Depends(get_session),
) -> StreamingResponse:
    """Persist the player's line, interpret its mode, conditionally run an
    NPC, then stream the MJ narration. See the protocol reference comment
    above for mode routing, speaker selection, the SSE event contract, and
    turn_order layout."""
    from .. import play as _play

    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.status != "open":
        raise HTTPException(status_code=400, detail="Conversation is already closed")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Player line must not be empty")

    ctx = _play._say_prepare_turn(conv, conv_id, body, content, db)
    return StreamingResponse(_play._say_build_stream(ctx), media_type="text/event-stream")


@router.post("/api/conversations/{conv_id}/end")
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


@router.post("/api/conversations/{conv_id}/join")
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


@router.post("/api/conversations/{conv_id}/travel")
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
    player_text: str                       # player's free-text join expression
    player_id: Optional[str] = None        # defaults to the resolved player character


@router.post("/api/scene/join")
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


@router.get("/api/conversations/{conv_id}/scene-state")
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


@router.patch("/api/conversations/{conv_id}/scene-state")
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


class TravelBody(BaseModel):
    location_id: str


@router.post("/api/travel")
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


@router.get("/api/conversations")
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


@router.get("/api/conversations/{conv_id}")
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


@router.post("/api/conversations/{conv_id}/analyze")
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


class WorldTickBody(BaseModel):
    scope_type: str  # npcs | location | faction
    npc_ids: Optional[list[str]] = None  # scope_type == "npcs"
    scope_id: Optional[str] = None       # scope_type == "location" | "faction"
    interval: str


@router.post("/api/world-tick")
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
