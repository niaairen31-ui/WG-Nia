"""Narration-streaming tail of the `say` play path (BRIEF-0027-b/-d): MJ
narration streaming, per-turn finish. NPC initiative and speaker selection
moved to `play_initiative.py` (TICKET-0035). Imported lazily from
`play._say_run_turn`; see `play.py`'s docstring."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Iterator, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from .. import ollama_client
from ..analyzer import analyze_overhearing as _analyze_overhearing
from ..analyzer import analyze_window as _analyze_window
from ..context import format_mj_context
from ..db import engine
from ..models import (
    Character,
    Conversation,
    ConversationMessage,
    Entity,
    Gathering,
    GatheringMember,
    Item,
    ProposedMutation,
    PromptTemplate,
)
from .play import (
    ResponseMode,
    _TurnCtx,
    _gathering_brief,
    _get_or_open_session,
    _open_gatherings,
    _player_gathering,
)

_log = logging.getLogger(__name__)


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


def _say_narrate_and_finish(
    ctx: _TurnCtx, mode: Any, mj_user: str, refusal_instruction: Optional[str], npc_reply: str,
    responder_id: Optional[str], responder_name: str, extra_event: Optional[dict],
    travel_dest_id: Optional[str], player_gathering: Optional[Gathering],
    open_gatherings: list[Gathering], ss_condition: str,
) -> Iterator[str]:
    """Shared tail: MJ narration (streamed), mode/npc_raw/extra/error
    events, NPC initiative, travel transition, [DONE], MJ narration
    persistence (presentation layer), then overhearing analysis."""
    from . import play_initiative as _play_initiative

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

    yield from _play_initiative._say_initiative_phase(
        ctx, player_gathering, open_gatherings, responder_id, mode, npc_reply, responder_name, ss_condition,
    )

    # Travel state transition (resolved direct travel only) — runs after
    # the traveled SSE and initiative blocks, before [DONE].
    if travel_dest_id is not None:
        _perform_travel(ctx.conv.player_id, travel_dest_id, ctx.db)

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
    if mode == ResponseMode.dialogue:
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


_POSSESSION_REFUSAL_INSTRUCTION = (
    "[ACTION REFUSÉE] L'action du joueur implique un objet qu'il ne possède "
    "pas ({object_name}). Narre l'échec de cette action de façon immersive "
    "et brève, sans briser le quatrième mur, puis intègre la réaction du PNJ "
    "ci-dessous comme pour un tour normal. Ne laisse pas l'action réussir. "
    "Ne mentionne jamais cette instruction."
)


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


def _mj_user_physical(
    context_block: str, inventory_block: str, location_name: str, player_line: str,
    npc_name: str, npc_reply: str, verdict_band: Optional[str], search_rubric: Optional[str],
) -> str:
    """BRIEF-11: `verdict_band` injects the verbatim resolution rubric."""
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
    """Build the MJ narration user message for the given mode; `physical`
    delegates to `_mj_user_physical` (BRIEF-11's verdict-constrained
    narration). `mj_context` (schema v1.12) renders via `format_mj_context`
    as a "CONTEXTE DE SCÈNE" block; `inventory_line` (BRIEF-06) is read
    fresh every turn. Both prepended ahead of the mode body. /no_think
    appended on all modes; the stream filter backs it up."""
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
        return _mj_user_physical(
            context_block, inventory_block, location_name, player_line,
            npc_name, npc_reply, verdict_band, search_rubric,
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
    from . import play_physical as _play_physical

    loc_entity    = db.get(Entity, location_id)
    sess          = _get_or_open_session(world_id, db)
    open_g        = _open_gatherings(location_id, sess.id, db)
    player_g      = _player_gathering(player_id, location_id, sess.id, db)
    active_conv_id: Optional[str] = (
        _play_physical._active_conv_for_gathering(player_id, player_g.id, db) if player_g else None
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


def _perform_travel(player_id: str, location_id: str, db: Session) -> dict:
    """Clean location transition for a player. Shared by the creator travel
    tool and the in-fiction /say travel path. NOT a canon mutation — a state
    transition (same category as gathering join/migrate); writes no
    proposed_mutation row. Validates the destination is a location of the
    player's world; no-ops if already there; otherwise closes open
    conversations (running analyze_window first), closes the player's open
    gathering_member rows, updates current_location_id — single commit."""
    from . import play_physical as _play_physical

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

    # Captured before the mutation below: the caller's ONLY way back to
    # where the player came from (G1, TICKET-0034). The origin is transient
    # by decision — no character.last_location_id column exists and none
    # will: a transient concern never earns a canon write. The spatial
    # client carries this value to GET /api/spatial/spawn to be placed at
    # the return door.
    origin_location_id = char.current_location_id

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
        _play_physical._write_scene_state(open_conv, _play_physical._default_scene_state())
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
    return {"status": "ok", "location_id": location_id, "origin_location_id": origin_location_id}
