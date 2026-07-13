"""Narration-streaming tail of the `say` play path (BRIEF-0027-b): MJ
narration token streaming, NPC initiative (vote / act / migrate /
narrate), and the shared per-turn finish (events, [DONE], persistence,
overhearing analysis). Split out of `play.py` to keep both modules under
the R5 module budget (<=1000 lines) — see play.py's module docstring for
the extraction's provenance and the `_app` reuse convention.

Imported lazily from `play._say_run_turn` (only once play.py has finished
loading) so `_TurnCtx` can be imported here at module top without a
circular import.
"""

from __future__ import annotations

import json
from typing import Any, Iterator, Optional

from sqlmodel import Session

from .. import ollama_client
from ..analyzer import analyze_overhearing as _analyze_overhearing
from ..context import assemble_npc_context
from ..db import engine
from ..models import ConversationMessage, Entity, Gathering
from ..prompt_store import current_prompt
from . import app as _app
from .play import _TurnCtx


def _say_stream_mj_narration(
    mj_system_prompt_for_turn: str, mj_user: str, model: str, result: dict,
) -> Iterator[str]:
    """MJ narration (streamed to the player). Mutates `result` in place
    with `chunks` (list[str]) and `error` (str | None) for the caller to
    read once this generator is exhausted (a `yield from` fully drains it
    before the next statement runs)."""
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
    result["chunks"] = mj_chunks
    result["error"] = mj_error


def _say_initiative_vote(
    ctx: _TurnCtx, player_gathering: Optional[Gathering], open_gatherings: list[Gathering],
    responder_id: Optional[str], mode: Any,
) -> tuple[list[tuple], set, Optional[str], Optional[str]]:
    """Phase 3: NPC initiative vote (cheap, non-streaming).

    In-group: player's gathering members, excluding player and this-turn
    responder. Non-members: active members of all OTHER open gatherings at
    this location — open_gatherings is a live snapshot from phase 0a; no
    migration has occurred yet this turn (E1: at most one initiative,
    which fires after the vote). Only fires when the player is in a
    gathering. Returns (all_candidates, non_member_ids_initiative, act,
    initiator_id) — act/initiator_id are None if nobody fires.
    """
    db = ctx.db
    if player_gathering is None:
        return [], set(), None, None

    in_group_initiative = [
        (gm, e) for gm, e in _app._active_members(player_gathering.id, db)
        if e.id != ctx.conv.player_id and e.id != responder_id
    ]
    non_member_initiative: list[tuple] = []
    for _g in open_gatherings:
        if _g.id == player_gathering.id:
            continue
        non_member_initiative.extend(_app._active_members(_g.id, db))
    non_member_ids_initiative: set = {e.id for _gm, e in non_member_initiative}
    all_candidates = in_group_initiative + non_member_initiative
    if not all_candidates:
        return all_candidates, non_member_ids_initiative, None, None

    initiative_template = _app._load_mj_initiative_template(ctx.world_id, db)
    if initiative_template is None:
        return all_candidates, non_member_ids_initiative, None, None

    act, initiator_id = _app._npc_initiative_vote(
        template=initiative_template,
        location_name=ctx.location_name,
        members=all_candidates,
        non_member_ids=non_member_ids_initiative,
        player_line=ctx.content,
        interpreted_mode=mode,
        player_id=ctx.conv.player_id,
        model=ctx.model,
        db=db,
    )
    return all_candidates, non_member_ids_initiative, act, initiator_id


def _say_initiative_context(ctx: _TurnCtx, initiator_id: str, ss_condition: str) -> tuple[str, str]:
    """Fresh context (D1 — same pipeline as normal responders) for the NPC
    taking initiative. For non-members, gathering_id = player's gathering:
    the NPC sees who it is approaching, not where it currently stands. v1
    conscious choice: distant NPCs are at-a-glance distance (same room).
    Revisit if out-of-sight gatherings are added. Returns (init_system,
    initiator_name).
    """
    db = ctx.db
    initiator_entity = db.get(Entity, initiator_id)
    initiator_name = initiator_entity.name if initiator_entity else initiator_id

    init_behaviour = _app._load_npc_dialogue_template(ctx.world_id, db)
    init_behaviour_version = current_prompt(db, init_behaviour)
    init_ctx = assemble_npc_context(
        initiator_id, ctx.conv.player_id, ctx.conv.location_id, db,
        gathering_id=ctx.conv.gathering_id,
        player_condition=ss_condition,
    )
    # C2: load JSON-output contract from dedicated template
    # (usage="npc_initiative_act") — never bleeds into normal
    # /say turns which use the shared npc_dialogue template.
    init_act_tmpl = _app._load_npc_initiative_act_template(ctx.world_id, db)
    init_act_instruction = (
        current_prompt(db, init_act_tmpl).system_prompt
        if init_act_tmpl is not None
        else _app._NPC_INITIATIVE_ACT_FALLBACK
    )
    init_system = (
        f"{_app._npc_dialogue_system_prompt(init_behaviour_version.system_prompt, init_ctx)}"
        f"\n\n{init_act_instruction}"
    )
    return init_system, initiator_name


def _say_initiative_generate(
    ctx: _TurnCtx, init_system: str, initiator_id: str, npc_reply: str,
    responder_id: Optional[str], responder_name: str, non_member_ids_initiative: set,
) -> tuple[str, bool]:
    """Phase 4: NPC initiative generation (non-streaming JSON).

    Produces {"act_text": "…", "move": <bool>}. C2: non-streaming JSON call
    replaces streaming free text. Accepted debt: act appears all-at-once
    (short pause); restoring incremental streaming is a future improvement,
    not this session. Returns (initiative_act_text, initiative_move).
    """
    init_trigger = _app._build_initiative_trigger(
        player_line=ctx.content,
        npc_reply=npc_reply,
        responder_name=responder_name if responder_id else None,
    )
    init_msg_list = [
        {"role": "system", "content": init_system},
        *ctx.npc_history,
        {"role": "user", "content": init_trigger},
    ]

    initiative_act_text = ""
    initiative_move = False
    try:
        raw_act = ollama_client.chat(
            init_msg_list, model=ctx.model,
            format="json",
            options=ollama_client.NPC_DIALOGUE_OPTIONS,
        )
        raw_act = ollama_client.strip_think(raw_act)
        try:
            act_obj = json.loads(raw_act)
            initiative_act_text = str(act_obj.get("act_text") or "").strip()
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

    return initiative_act_text, initiative_move


def _say_initiative_apply(
    ctx: _TurnCtx, initiative_act_text: str, initiative_move: bool, initiator_id: str,
    player_gathering: Optional[Gathering],
) -> None:
    """Migrates the NPC (if it won the vote as a non-member) and persists
    its canonical line. Conscious choice: a valid JSON response with an
    empty act_text (e.g. {"move": true}) skips the act AND the migration —
    no migration without narration, avoids invisible NPC movement the
    player would never see narrated. Caller only invokes this when
    `initiative_act_text` is truthy.
    """
    # C2 migration: move the NPC into the player's gathering BEFORE
    # persisting or narrating, so the DB roster is already at destination
    # when post-[DONE] analysis runs. mig_db is a short-lived session; the
    # SSE generator's db session has no open write transaction at this
    # point (all earlier writes used their own Session(engine) blocks and
    # committed), so there is no nested-transaction conflict.
    if initiative_move and player_gathering is not None:
        with Session(engine) as mig_db:
            _app._migrate_npc(initiator_id, player_gathering.id, mig_db)

    # Persist initiative NPC line (canonical, speaker='npc').
    with Session(engine) as persist_db:
        persist_db.add(ConversationMessage(
            conversation_id=ctx.conv_id,
            turn_order=ctx.player_turn + 3,
            speaker="npc",
            speaker_id=initiator_id,
            content=initiative_act_text,
        ))
        persist_db.commit()


def _say_initiative_narrate(
    ctx: _TurnCtx, initiator_name: str, initiative_npc_reply: str,
) -> Iterator[str]:
    """Streams the initiative MJ narration to the player and persists it
    before [DONE] so that the next turn's player_turn computation (last+1)
    sees the correct last row and avoids turn_order collisions."""
    init_mj_user = _app._build_initiative_mj_user(
        npc_name=initiator_name,
        location_name=ctx.location_name,
        initiative_line=initiative_npc_reply,
        player_line=ctx.content,
    )
    init_mj_messages = [
        {"role": "system", "content": ctx.mj_system_prompt},
        {"role": "user",   "content": init_mj_user},
    ]

    yield f"data: {json.dumps({'initiative_start': {'npc_name': initiator_name}})}\n\n"

    init_mj_chunks: list[str] = []
    try:
        for chunk in ollama_client.chat_stream(
            init_mj_messages, model=ctx.model,
            options=ollama_client.MJ_NARRATION_OPTIONS,
        ):
            init_mj_chunks.append(chunk)
            yield f"data: {json.dumps(chunk)}\n\n"
    except ollama_client.OllamaError:
        pass

    yield f"data: {json.dumps({'initiative_npc_raw': initiative_npc_reply})}\n\n"

    with Session(engine) as persist_db:
        persist_db.add(ConversationMessage(
            conversation_id=ctx.conv_id,
            turn_order=ctx.player_turn + 4,
            speaker="mj",
            speaker_id=None,
            content="".join(init_mj_chunks),
        ))
        persist_db.commit()


def _say_initiative_phase(
    ctx: _TurnCtx, player_gathering: Optional[Gathering], open_gatherings: list[Gathering],
    responder_id: Optional[str], mode: Any, npc_reply: str, responder_name: str, ss_condition: str,
) -> Iterator[str]:
    """Phase 3 & 4: NPC initiative (Tier 3 — C1 vote, C2 migration).
    Cadence E1: at most one NPC per turn. Only fires when the player is in
    a gathering (initiative is a gathering-level concept; 1:1 conversations
    have no bystanders)."""
    _candidates, non_member_ids, act, initiator_id = _say_initiative_vote(
        ctx, player_gathering, open_gatherings, responder_id, mode,
    )
    if not (act and initiator_id):
        return

    init_system, initiator_name = _say_initiative_context(ctx, initiator_id, ss_condition)
    initiative_act_text, initiative_move = _say_initiative_generate(
        ctx, init_system, initiator_id, npc_reply, responder_id, responder_name, non_member_ids,
    )
    if not initiative_act_text:
        return

    _say_initiative_apply(ctx, initiative_act_text, initiative_move, initiator_id, player_gathering)
    yield from _say_initiative_narrate(ctx, initiator_name, initiative_act_text)


def _say_narrate_and_finish(
    ctx: _TurnCtx, mode: Any, mj_user: str, refusal_instruction: Optional[str], npc_reply: str,
    responder_id: Optional[str], responder_name: str, extra_event: Optional[dict],
    travel_dest_id: Optional[str], player_gathering: Optional[Gathering],
    open_gatherings: list[Gathering], ss_condition: str,
) -> Iterator[str]:
    """Shared tail: MJ narration (streamed), mode/npc_raw/extra/error
    events, NPC initiative, travel transition, [DONE], MJ narration
    persistence (presentation layer), then overhearing analysis."""
    # Refusal instruction (BRIEF-08 / D2a.1): appended to the system prompt
    # for this turn only — never persisted, same pattern as
    # [MODE RÉACTION NON-VERBALE].
    mj_system_prompt_for_turn = (
        f"{ctx.mj_system_prompt}\n\n{refusal_instruction}"
        if refusal_instruction is not None
        else ctx.mj_system_prompt
    )
    result: dict = {}
    yield from _say_stream_mj_narration(mj_system_prompt_for_turn, mj_user, ctx.model, result)
    mj_chunks, mj_error = result["chunks"], result["error"]

    # Send mode and raw NPC line before [DONE] for client-side audit.
    # mode: tells the UI why a turn may have produced no NPC dialogue.
    # npc_raw: empty string for scene turns (no NPC call).
    yield f"data: {json.dumps({'mode': mode.value})}\n\n"
    yield f"data: {json.dumps({'npc_raw': npc_reply})}\n\n"
    if extra_event is not None:
        yield f"data: {json.dumps(extra_event)}\n\n"
    if mj_error:
        yield f"data: {json.dumps({'error': mj_error})}\n\n"

    yield from _say_initiative_phase(
        ctx, player_gathering, open_gatherings, responder_id, mode, npc_reply, responder_name, ss_condition,
    )

    # Travel state transition (resolved direct travel only) — runs after
    # the traveled SSE and initiative blocks, before [DONE].
    if travel_dest_id is not None:
        _app._perform_travel(ctx.conv.player_id, travel_dest_id, ctx.db)

    yield "data: [DONE]\n\n"

    # Persist the main MJ narration (presentation layer).
    # Runs after [DONE] — the player can read and type while this completes.
    with Session(engine) as persist_db:
        persist_db.add(ConversationMessage(
            conversation_id=ctx.conv_id,
            turn_order=ctx.mj_turn,
            speaker="mj",
            speaker_id=None,
            content="".join(mj_chunks),
        ))
        persist_db.commit()

    # Overhearing analysis (sync-after-stream, Tier 4, acquire or upgrade).
    # 'dialogue' turns only — 'scene' has no NPC line, 'npc_reaction' is
    # wordless (analyze_overhearing's own guard would also catch both via
    # an empty npc_reply, but the mode check keeps the gating explicit).
    # Failures are silently swallowed — analysis must never surface to
    # the player.
    if mode == _app.ResponseMode.dialogue:
        with Session(engine) as overhear_db:
            try:
                overheard = _analyze_overhearing(
                    player_line=ctx.content,
                    npc_line=npc_reply,
                    conversation_id=ctx.conv_id,
                    db=overhear_db,
                    model=ctx.model,
                    npc_entity_id=responder_id,
                )
                for mut in overheard:
                    overhear_db.add(mut)
                if overheard:
                    overhear_db.commit()
            except (Exception, SystemExit):
                pass


