"""The `say`/`_stream` play path (BRIEF-0027-b/-d): mode interpretation, NPC
selection/run, mutation-proposal assembly, narration streaming. `say` is a
thin orchestrator in `cockpit/routes/play.py`, calling into this module's
two entry points.

Helpers formerly concentrated in `cockpit/app.py` were redistributed at
BRIEF-0027-d by which module already depended on them: some stayed here,
some moved to `play_physical.py`/`play_stream.py`. Cross-file references
use lazy (function-body) imports — `play_physical`/`play_stream` import
`from .play import ...` at THEIR module top, so this module must never
import them at its own module top (circular-import discipline).
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterator, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from .. import ollama_client
from ..context import (
    assemble_mj_context,
    assemble_npc_context,
    format_inventory_line,
    format_item_list_for_interpretation,
)
from ..db import engine
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
from ..prompt_store import current_prompt


@dataclass
class _TurnCtx:
    """Everything resolved once, before the stream starts."""
    conv: Conversation
    conv_id: str
    body: Any
    content: str
    db: Session
    model: str
    world_id: str
    npc_id: Optional[str]
    npc_entity: Optional[Entity]
    npc_name: str
    location_name: str
    npc_history: list[dict]
    recent_transcript: str
    player_turn: int
    npc_turn: int
    mj_turn: int
    system_prompt: str
    mj_user_template: str
    mj_system_prompt: str
    interpret_system: str
    interpret_user_tpl: str



class _SayAbort(Exception):
    """Raised by a phase helper to end the turn immediately (error or
    frozen-scene short-circuit) — carries the SSE lines still owed to the
    client before [DONE]."""

    def __init__(self, sse_lines: list[str]) -> None:
        super().__init__("say turn aborted")
        self.sse_lines = sse_lines


_PHYSICAL_BAND_OUTCOME = {
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
}

_NPC_REACTION_INSTRUCTION = (
    "\n\n[MODE RÉACTION NON-VERBALE] Le joueur n'a pas adressé "
    "la parole au personnage. Réponds UNIQUEMENT par un bref geste "
    "ou expression physique à la première personne. "
    "AUCUN MOT PRONONCÉ — pas de dialogue, pas de phrase dite."
)


# ─────────────────────────── turn setup (called once, from say()) ─────────

def _say_persist_and_build_history(
    conv_id: str, conv: Conversation, content: str, db: Session,
) -> tuple[int, int, int, list[dict], str, list[ConversationMessage]]:
    """Determine turn order, persist the player line, build NPC history.

    Returns (player_turn, npc_turn, mj_turn, npc_history, system_prompt, all_msgs).
    """
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

    # Turn order slots (npc_turn may remain unused for scene turns).
    npc_turn = player_turn + 1
    mj_turn = player_turn + 2
    return player_turn, npc_turn, mj_turn, npc_history, system_prompt, all_msgs


def _say_resolve_names_and_transcript(
    conv: Conversation, npc_id: Optional[str], all_msgs: list[ConversationMessage], db: Session,
) -> tuple[Optional[Entity], str, str, str]:
    """Resolve display names and build the recent player/npc transcript.

    Returns (npc_entity, npc_name, location_name, recent_transcript).
    """
    # Resolve display names for the MJ prompt.
    # npc_id may be None for pure gathering conversations (conv started from
    # the scene-level join without a seed NPC — see POST /api/scene/join).
    npc_entity = db.get(Entity, npc_id) if npc_id else None
    npc_name: str = (
        npc_entity.name if npc_entity
        else (npc_id or "le groupe")  # gathering conv: use "le groupe" as display name
    )
    loc_entity = db.get(Entity, conv.location_id) if conv.location_id else None
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
    return npc_entity, npc_name, location_name, recent_transcript


def _say_load_prompts(world_id: str, db: Session) -> tuple[str, str, str, str]:
    """Load MJ narration + interpret templates (both raise HTTP 503 if
    missing — before the stream opens). Returns (mj_user_template,
    mj_system_prompt, interpret_system, interpret_user_tpl)."""
    from . import play_physical as _play_physical
    from . import play_stream as _play_stream

    mj_template = _play_stream._load_mj_narration_template(world_id, db)
    interpret_template = _play_physical._load_mj_interpret_template(world_id, db)
    mj_version = current_prompt(db, mj_template)
    interpret_version = current_prompt(db, interpret_template)
    return (
        mj_version.user_template, mj_version.system_prompt,
        interpret_version.system_prompt, interpret_version.user_template,
    )


def _say_prepare_turn(conv: Conversation, conv_id: str, body: Any, content: str, db: Session) -> _TurnCtx:
    """Everything `say()` used to do before defining `_stream` — persist the
    player line, resolve names/history/templates. One SAVEPOINT-free read
    +write pass; `say()` calls this, then builds the stream from the result.
    """
    # Exemption, by construction (BRIEF-0008-a): NOT wired through
    # effective_model. This value was already resolved once, at conversation
    # start (see the `model = effective_model(behaviour, ...)` sites in
    # routes/play.py). Re-wiring it here would silently encode a `template.model` vs
    # `injected_context["model"]` precedence for every downstream call in
    # this module and the pass-through helpers it calls
    # (`_interpret_mode`, `_arbitrate`, `_npc_initiative_vote`,
    # `_select_group_speaker`) — a decision deferred to the write-path
    # chantier (verify/checks/prompt_registry.py allowlists this module).
    model = (conv.injected_context or {}).get("model", ollama_client.DEFAULT_MODEL)
    npc_id = conv.npc_id
    world_id = conv.world_id

    player_turn, npc_turn, mj_turn, npc_history, system_prompt, all_msgs = (
        _say_persist_and_build_history(conv_id, conv, content, db)
    )
    npc_entity, npc_name, location_name, recent_transcript = (
        _say_resolve_names_and_transcript(conv, npc_id, all_msgs, db)
    )
    mj_user_template, mj_system_prompt, interpret_system, interpret_user_tpl = (
        _say_load_prompts(world_id, db)
    )

    return _TurnCtx(
        conv=conv, conv_id=conv_id, body=body, content=content, db=db,
        model=model, world_id=world_id, npc_id=npc_id, npc_entity=npc_entity,
        npc_name=npc_name, location_name=location_name, npc_history=npc_history,
        recent_transcript=recent_transcript, player_turn=player_turn,
        npc_turn=npc_turn, mj_turn=mj_turn, system_prompt=system_prompt,
        mj_user_template=mj_user_template, mj_system_prompt=mj_system_prompt,
        interpret_system=interpret_system, interpret_user_tpl=interpret_user_tpl,
    )


# ─────────────────────────── stream phases ─────────────────────────────────

def _say_frozen_check(ctx: _TurnCtx, scene_state: dict) -> None:
    """Frozen scene: no model calls, fixed message. Raises _SayAbort if
    frozen (after persisting the fixed MJ line)."""
    if not scene_state.get("frozen"):
        return
    lines = [
        f"data: {json.dumps(_FROZEN_MJ_MESSAGE)}\n\n",
        f"data: {json.dumps({'mode': 'frozen'})}\n\n",
        f"data: {json.dumps({'npc_raw': ''})}\n\n",
        "data: [DONE]\n\n",
    ]
    with Session(engine) as persist_db:
        persist_db.add(ConversationMessage(
            conversation_id=ctx.conv_id,
            turn_order=ctx.mj_turn,
            speaker="mj",
            speaker_id=None,
            content=_FROZEN_MJ_MESSAGE,
        ))
        persist_db.commit()
    raise _SayAbort(lines)


def _say_gathering_phase(conv: Conversation, db: Session) -> tuple[Optional[Gathering], list[Gathering], str]:
    """Phase 0a: gathering membership (multi-NPC scenes, schema v1.8).

    Drives both join-priority and speaker selection below. A conversation
    with no location (shouldn't happen in the pilot) simply has no gatherings.
    """
    from . import play_physical as _play_physical

    player_gathering: Optional[Gathering] = None
    open_gatherings: list[Gathering] = []
    if conv.location_id:
        player_gathering = _player_gathering(conv.player_id, conv.location_id, conv.session_id, db)
        open_gatherings = _open_gatherings(conv.location_id, conv.session_id, db)
    gathering_status = _play_physical._render_gathering_status(conv.player_id, player_gathering, open_gatherings, db)
    return player_gathering, open_gatherings, gathering_status


def _say_interpret_phase(
    ctx: _TurnCtx, gathering_status: str, player_gathering: Optional[Gathering],
) -> tuple[Any, str, Optional[str]]:
    """Phase 0b: Interpret the player's input (mode routing).

    Classify as dialogue / npc_reaction / scene / join before calling any
    NPC. Falls back to 'dialogue' on any failure — a misclassification
    must never break a turn.
    """
    from . import play_physical as _play_physical

    item_list = format_item_list_for_interpretation(ctx.db, ctx.conv.player_id)
    mode, reference, used_object = _play_physical._interpret_mode(
        player_line=ctx.content,
        npc_name=ctx.npc_name,
        location_name=ctx.location_name,
        gathering_status=gathering_status,
        recent_transcript=ctx.recent_transcript,
        item_list=item_list,
        interpret_system=ctx.interpret_system,
        interpret_user_tpl=ctx.interpret_user_tpl,
        model=ctx.model,
    )
    # 'join' is only meaningful while ungrouped — a misclassification while
    # already in a gathering degrades to dialogue (never breaks a turn).
    if mode == ResponseMode.join and player_gathering is not None:
        mode = ResponseMode.dialogue
    return mode, reference, used_object


def _say_constraint_gating(mode: Any, ss_constraints: set) -> tuple[Any, bool, bool]:
    """BRIEF-12: constraint gating (before possession check).

    Gagged → any dialogue attempt re-routes to a composure roll (trying to
    speak through the gag). Restrained → any movement/physical/environment
    intent re-routes to an escape physical roll. These overrides happen
    AFTER interpretation so the player's text is still fed to the model
    for classification; the constraint then overrides the routing outcome.
    """
    is_gagged_attempt = False   # True: re-routed dialogue via gagged
    is_escape_attempt = False   # True: re-routed movement via restrained
    if "gagged" in ss_constraints and mode == ResponseMode.dialogue:
        mode = ResponseMode.physical
        is_gagged_attempt = True
    elif "restrained" in ss_constraints and mode in (
        ResponseMode.physical, ResponseMode.scene, ResponseMode.npc_reaction,
        ResponseMode.travel,
    ):
        mode = ResponseMode.physical
        is_escape_attempt = True
    return mode, is_gagged_attempt, is_escape_attempt


def _say_possession_check(
    ctx: _TurnCtx, mode: Any, is_gagged_attempt: bool, is_escape_attempt: bool, used_object: Optional[str],
) -> tuple[Any, Optional[str]]:
    """Phase 0c: possession check (binary, BRIEF-08 / D2a.1).

    Code judges possession against canon `item` rows — the structural
    fix for the D1 finding that the 8b model does not reliably honor
    prohibition rules in free-text narration. `used_object` owned by the
    player → pass; not owned or `unknown_object` → refused. The
    equipped/stowed distinction is dormant — `item.equipped` is not read.
    A refusal no longer skips the NPC phase: the gesture is socially
    visible, so the turn proceeds as a normal dialogue turn with a
    one-shot [GESTE RATÉ] instruction telling the NPC what it just saw.
    """
    from . import play_stream as _play_stream

    refusal_instruction: Optional[str] = None
    if mode != ResponseMode.join and not (is_gagged_attempt or is_escape_attempt) and used_object is not None:
        if used_object == "unknown_object":
            refusal_instruction = _play_stream._build_refusal_instruction(None)
        elif _play_stream._find_player_item(ctx.db, ctx.conv.player_id, used_object) is None:
            refusal_instruction = _play_stream._build_refusal_instruction(used_object)

    if refusal_instruction is not None:
        mode = ResponseMode.dialogue
    return mode, refusal_instruction


def _say_join_branch(
    ctx: _TurnCtx, reference: str, open_gatherings: list[Gathering],
) -> tuple[str, Optional[dict]]:
    """Phase 0c: join handling — takes priority while ungrouped.

    "Parler n'a pas de cible tant qu'on n'a pas rejoint": joining is an
    action, not dialogue — narrated in third person, no NPC call, and
    forms/anchors no canon mutation (see ARCHITECTURE_DECISIONS.md).
    """
    from . import play_physical as _play_physical
    from . import play_stream as _play_stream

    resolved_id = _play_physical._resolve_join_target(reference, open_gatherings, ctx.db)
    if resolved_id is not None:
        gathering = _join_gathering(ctx.conv, resolved_id, ctx.db)
        extra_event = {"joined": {"gathering_id": gathering.id, "label": gathering.label}}
        mj_user = _play_stream._build_join_narration_user(
            location_name=ctx.location_name, player_line=ctx.content,
            joined=True, gathering_label=gathering.label,
        )
    else:
        extra_event = {
            "join_candidates": [_gathering_brief(g.id, ctx.db) for g in open_gatherings]
        }
        mj_user = _play_stream._build_join_narration_user(
            location_name=ctx.location_name, player_line=ctx.content,
            joined=False, gathering_label=None,
        )
    return mj_user, extra_event


def _say_travel_mj_user(
    ctx: _TurnCtx, mj_context_travel: Optional[str], inventory_line_travel: str, travel_instruction: str,
) -> str:
    """Shared `_build_mj_user` call for the three travel outcomes (no exit /
    resolved / ambiguous) — only `travel_instruction` differs between them."""
    from . import play_stream as _play_stream

    return _play_stream._build_mj_user(
        mode=ResponseMode.travel,
        mj_user_template=ctx.mj_user_template,
        npc_name=ctx.npc_name,
        location_name=ctx.location_name,
        player_line=ctx.content,
        npc_reply="",
        mj_context=mj_context_travel,
        inventory_line=inventory_line_travel,
        travel_instruction=travel_instruction,
    )


def _say_travel_branch(
    ctx: _TurnCtx, reference: str, player_gathering: Optional[Gathering],
    ss_constraints: set, ss_condition: str,
) -> tuple[Any, str, Optional[dict], Optional[str]]:
    """Travel: intent -> direct-neighbour resolution -> picker fallback.
    (BRIEF-16) No NPC phase; restrained turns are intercepted before
    reaching here. Returns (mode, mj_user, extra_event, travel_dest_id)."""
    mode = ResponseMode.travel
    neighbours = _location_neighbours(ctx.conv.location_id, ctx.db)
    mj_context_travel = (
        assemble_mj_context(
            ctx.db, ctx.conv.player_id, ctx.conv.location_id,
            gathering_id=player_gathering.id if player_gathering else None,
            blindfolded="blindfolded" in ss_constraints,
            player_condition=ss_condition,
        )
        if ctx.conv.location_id else None
    )
    inventory_line_travel = format_inventory_line(ctx.db, ctx.conv.player_id)
    extra_event: Optional[dict] = None
    travel_dest_id: Optional[str] = None

    if not neighbours:
        # No exits — downgrade to scene so the SSE mode reflects it;
        # the [SORTIE INTROUVABLE] instruction prevents the MJ from
        # inventing exits or moving the player.
        mode = ResponseMode.scene
        mj_user = _say_travel_mj_user(ctx, mj_context_travel, inventory_line_travel, (
            "[SORTIE INTROUVABLE] Le joueur cherche à quitter le lieu "
            "mais aucune sortie évidente ne se présente. Narre sa "
            "recherche d'une issue sans en inventer une ; il reste sur place."
        ))
        return mode, mj_user, extra_event, travel_dest_id

    dest_id = _resolve_travel_target(reference, neighbours)
    if dest_id is not None:
        dest_name = next(name for eid, name in neighbours if eid == dest_id)
        extra_event = {"traveled": {"location_id": dest_id, "name": dest_name}}
        travel_dest_id = dest_id
        mj_user = _say_travel_mj_user(ctx, mj_context_travel, inventory_line_travel, (
            f"[DÉPART] Le joueur quitte {ctx.location_name} en direction de "
            f"{dest_name}. Narre uniquement son départ (il se lève, sort, "
            f"s'éloigne) — ne décris PAS le lieu d'arrivée ni ce qu'il y trouve."
        ))
    else:
        extra_event = {
            "travel_candidates": [
                {"id": eid, "name": name} for eid, name in neighbours
            ]
        }
        mj_user = _say_travel_mj_user(ctx, mj_context_travel, inventory_line_travel, (
            "[DÉPART INCERTAIN] Le joueur cherche à partir mais hésite sur "
            "la direction. Narre brièvement ce moment de pause au seuil, "
            "sans le faire bouger ni nommer de destination."
        ))
    return mode, mj_user, extra_event, travel_dest_id


def _say_resolve_speaker(
    ctx: _TurnCtx, mode: Any, player_gathering: Optional[Gathering],
) -> tuple[Any, Optional[str]]:
    """Speaker / target resolution (contract A3 hybrid). Returns (mode,
    responder_id) — mode may downgrade to 'scene' if nobody can answer."""
    from . import play_physical as _play_physical
    from . import play_stream as _play_stream

    db = ctx.db
    responder_id: Optional[str] = None
    if mode not in (ResponseMode.dialogue, ResponseMode.npc_reaction):
        return mode, responder_id

    target = ctx.body.target
    if target and target != "group":
        responder_id = target
    elif target == "group" and player_gathering is not None:
        co_members = [
            (gm, e) for gm, e in _active_members(player_gathering.id, db)
            if e.id != ctx.conv.player_id
        ]
        if co_members:
            responder_id = _play_stream._select_group_speaker(
                template=_play_physical._load_mj_speaker_template(ctx.world_id, db),
                location_name=ctx.location_name,
                gathering=player_gathering,
                members=co_members,
                player_line=ctx.content,
                model=ctx.model,
                db=db,
            )
    elif not target:
        if ctx.npc_id is None and ctx.conv.gathering_id:
            # Pure gathering conversation (started from scene-level
            # join, no seed NPC). Treat omitted target as "group"
            # so the MJ always picks a responder — the player joined
            # a gathering, not a 1:1.
            responder_id = _play_stream._select_group_speaker(
                template=_play_physical._load_mj_speaker_template(ctx.world_id, db),
                location_name=ctx.location_name,
                gathering=player_gathering,
                members=[
                    (gm, e) for gm, e in _active_members(player_gathering.id, db)
                    if e.id != ctx.conv.player_id
                ] if player_gathering else [],
                player_line=ctx.content,
                model=ctx.model,
                db=db,
            ) if player_gathering and _active_members(player_gathering.id, db) else None
        else:
            responder_id = ctx.npc_id  # backward-compatible default (1:1)

    if responder_id is None:
        # Addressed the group with nobody able to answer — narrate
        # the silence rather than inventing a respondent. Cadence
        # B1 still holds: zero is a valid responder count here.
        mode = ResponseMode.scene

    return mode, responder_id


def _say_npc_generation(
    ctx: _TurnCtx, mode: Any, responder_id: Optional[str], ss_condition: str,
    refusal_instruction: Optional[str],
) -> tuple[str, Optional[str], str]:
    """Phase 1: NPC generation (conditional, buffered). dialogue /
    npc_reaction: call the responder; persist raw reply as 'npc'. scene:
    skip entirely; npc_reply stays "". Returns (npc_reply, responder_id,
    responder_name). Raises _SayAbort on an Ollama error."""
    db = ctx.db
    if not (mode in (ResponseMode.dialogue, ResponseMode.npc_reaction) and responder_id):
        return "", responder_id, ctx.npc_name

    responder_entity = db.get(Entity, responder_id)
    responder_name = responder_entity.name if responder_entity else responder_id

    # The frozen baseline system_prompt only matches the seed NPC
    # in a plain (non-gathering) conversation — contract D1 needs
    # a freshly assembled, NPC-specific context for anyone else.
    if responder_id == ctx.npc_id and ctx.conv.gathering_id is None:
        responder_system_prompt = ctx.system_prompt
    else:
        responder_behaviour = _load_npc_dialogue_template(ctx.world_id, db)
        responder_behaviour_version = current_prompt(db, responder_behaviour)
        responder_context = assemble_npc_context(
            responder_id, ctx.conv.player_id, ctx.conv.location_id, db,
            gathering_id=ctx.conv.gathering_id,
            player_condition=ss_condition,
        )
        responder_system_prompt = _npc_dialogue_system_prompt(
            responder_behaviour_version.system_prompt, responder_context
        )

    npc_msg_list = [{"role": "system", "content": responder_system_prompt}, *ctx.npc_history]
    if mode == ResponseMode.npc_reaction:
        # Append a one-shot instruction so the NPC produces a brief
        # wordless gesture rather than spoken dialogue.
        npc_msg_list[0] = {
            "role": "system",
            "content": npc_msg_list[0]["content"] + _NPC_REACTION_INSTRUCTION,
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
            npc_msg_list, model=ctx.model,
            options=ollama_client.NPC_DIALOGUE_OPTIONS,
        ):
            npc_chunks.append(chunk)
    except ollama_client.OllamaError as exc:
        npc_error = str(exc)

    if npc_error:
        raise _SayAbort([
            f"data: {json.dumps({'error': npc_error})}\n\n",
            "data: [DONE]\n\n",
        ])

    npc_reply = "".join(npc_chunks)

    # Persist the NPC line (canonical truth) under its own speaker_id.
    with Session(engine) as persist_db:
        persist_db.add(ConversationMessage(
            conversation_id=ctx.conv_id,
            turn_order=ctx.npc_turn,
            speaker="npc",
            speaker_id=responder_id,
            content=npc_reply,
        ))
        persist_db.commit()

    return npc_reply, responder_id, responder_name


def _say_dialogue_mj_user(
    ctx: _TurnCtx, mode: Any, player_gathering: Optional[Gathering], ss_constraints: set,
    ss_condition: str, responder_name: str, npc_reply: str,
) -> str:
    """Phase 2: MJ narration user message (non-physical branch).

    MJ context (schema v1.12, scope D-b3): the player's perception
    boundary — read fresh every turn (co-presents change with C2
    migrations); see assemble_mj_context for the static/dynamic split.
    BRIEF-12: pass blindfolded flag (excludes visual info) and
    player_condition (MJ is aware of mechanical reality).
    """
    mj_context = (
        assemble_mj_context(
            ctx.db, ctx.conv.player_id, ctx.conv.location_id,
            gathering_id=player_gathering.id if player_gathering else None,
            blindfolded="blindfolded" in ss_constraints,
            player_condition=ss_condition,
        )
        if ctx.conv.location_id else None
    )
    # Inventory line (schema v1.18, BRIEF-06): read fresh every turn,
    # never cached or snapshotted alongside mj_context.
    inventory_line = format_inventory_line(ctx.db, ctx.conv.player_id)
    from . import play_stream as _play_stream

    return _play_stream._build_mj_user(
        mode=mode,
        mj_user_template=ctx.mj_user_template,
        npc_name=responder_name,
        location_name=ctx.location_name,
        player_line=ctx.content,
        npc_reply=npc_reply,
        mj_context=mj_context,
        inventory_line=inventory_line,
    )


def _say_run_turn(ctx: _TurnCtx) -> Iterator[str]:
    """The turn's SSE generator body — every phase in the original order.
    Wrapped by `_say_build_stream`, which catches `_SayAbort` (frozen scene
    / an Ollama error) and yields its owed lines before returning early.

    `play_physical` / `play_stream` are imported lazily (R5 split — see
    their module docstrings) so their `from .play import ...` at module top
    can only run once this module has finished loading.
    """
    from . import play_physical as _play_physical
    from . import play_stream as _play_stream

    scene_state = _play_physical._get_scene_state(ctx.conv)
    ss_constraints = set(scene_state.get("constraints", []))
    ss_condition = scene_state.get("condition", "unharmed")
    _say_frozen_check(ctx, scene_state)

    player_gathering, open_gatherings, gathering_status = _say_gathering_phase(ctx.conv, ctx.db)
    mode, reference, used_object = _say_interpret_phase(ctx, gathering_status, player_gathering)
    mode, is_gagged, is_escape = _say_constraint_gating(mode, ss_constraints)
    mode, refusal_instruction = _say_possession_check(ctx, mode, is_gagged, is_escape, used_object)

    npc_reply, responder_id, responder_name = "", None, ctx.npc_name
    extra_event, travel_dest_id = None, None

    if mode == ResponseMode.join:
        mj_user, extra_event = _say_join_branch(ctx, reference, open_gatherings)
    elif mode == ResponseMode.travel:
        mode, mj_user, extra_event, travel_dest_id = _say_travel_branch(
            ctx, reference, player_gathering, ss_constraints, ss_condition,
        )
    elif mode == ResponseMode.physical:
        (mode, mj_user, npc_reply, responder_id, responder_name, ss_condition, ss_constraints
         ) = yield from _play_physical._say_physical_branch(
            ctx, is_gagged, is_escape, player_gathering, scene_state, ss_condition, ss_constraints,
        )
    else:
        mode, responder_id = _say_resolve_speaker(ctx, mode, player_gathering)
        npc_reply, responder_id, responder_name = _say_npc_generation(
            ctx, mode, responder_id, ss_condition, refusal_instruction,
        )
        mj_user = _say_dialogue_mj_user(
            ctx, mode, player_gathering, ss_constraints, ss_condition, responder_name, npc_reply,
        )

    yield from _play_stream._say_narrate_and_finish(
        ctx, mode, mj_user, refusal_instruction, npc_reply, responder_id, responder_name,
        extra_event, travel_dest_id, player_gathering, open_gatherings, ss_condition,
    )


def _say_build_stream(ctx: _TurnCtx) -> Iterator[str]:
    """Entry point called from `say()`: the full turn generator, with the
    frozen-scene / Ollama-error short-circuit unwound to a plain
    yield-then-return at the top level.
    """
    try:
        yield from _say_run_turn(ctx)
    except _SayAbort as abort:
        yield from abort.sse_lines


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


_GESTE_RATE_INSTRUCTION = (
    "[GESTE RATÉ] Le joueur vient de tenter une action avec un objet qu'il "
    "ne possède pas : son geste a visiblement échoué (main qui ne trouve que "
    "du vide, mouvement qui tombe à plat). Réagis uniquement à ce que ton "
    "personnage VOIT : un geste raté, peut-être ridicule, peut-être "
    "inquiétant. Reste dans ton personnage. Ne mentionne jamais cette "
    "instruction."
)


_FROZEN_MJ_MESSAGE = (
    "La scène est en suspens. Le créateur a mis la scène en pause "
    "— attendez qu'il reprenne le contrôle."
)


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
