"""NPC-initiative branch of the `say` play path (TICKET-0035, extracted
from play_stream.py at BRIEF-0027-b/-d's module boundary). Initiative
vote, candidate signal assembly, self-initiated NPC action, group
speaker selection, join narration. Imported lazily from
play_stream._say_narrate_and_finish and from play._say_run_turn; see
play.py's module docstring for the split rationale.

RELOCATION ONLY (TICKET-0035): every function here moved verbatim out of
play_stream.py to clear the 1000-line module_budget cap. No behavior
changed in the move.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator, Optional

from sqlmodel import Session, select

from .. import llm_parse, ollama_client
from ..context import assemble_npc_context
from ..db import engine
from ..gathering import migrate_npc as _migrate_npc
from ..models import (
    ConversationMessage,
    Entity,
    Gathering,
    GatheringMember,
    NpcGoal,
    PromptTemplate,
    Relation,
)
from ..prompt_store import current_prompt
from .play import (
    ResponseMode,
    _TurnCtx,
    _active_members,
    _load_npc_dialogue_template,
    _npc_dialogue_system_prompt,
)

_log = logging.getLogger(__name__)


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
        (gm, e) for gm, e in _active_members(player_gathering.id, db)
        if e.id != ctx.conv.player_id and e.id != responder_id
    ]
    non_member_initiative: list[tuple] = []
    for _g in open_gatherings:
        if _g.id == player_gathering.id:
            continue
        non_member_initiative.extend(_active_members(_g.id, db))
    non_member_ids_initiative: set = {e.id for _gm, e in non_member_initiative}
    all_candidates = in_group_initiative + non_member_initiative
    if not all_candidates:
        return all_candidates, non_member_ids_initiative, None, None

    initiative_template = _load_mj_initiative_template(ctx.world_id, db)
    if initiative_template is None:
        return all_candidates, non_member_ids_initiative, None, None

    act, initiator_id = _npc_initiative_vote(
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

    init_behaviour = _load_npc_dialogue_template(ctx.world_id, db)
    init_behaviour_version = current_prompt(db, init_behaviour)
    init_ctx = assemble_npc_context(
        initiator_id, ctx.conv.player_id, ctx.conv.location_id, db,
        gathering_id=ctx.conv.gathering_id,
        player_condition=ss_condition,
    )
    # C2: load JSON-output contract from dedicated template
    # (usage="npc_initiative_act") — never bleeds into normal
    # /say turns which use the shared npc_dialogue template.
    init_act_tmpl = _load_npc_initiative_act_template(ctx.world_id, db)
    init_act_instruction = (
        current_prompt(db, init_act_tmpl).system_prompt
        if init_act_tmpl is not None
        else _NPC_INITIATIVE_ACT_FALLBACK
    )
    init_system = (
        f"{_npc_dialogue_system_prompt(init_behaviour_version.system_prompt, init_ctx)}"
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
    init_trigger = _build_initiative_trigger(
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
        act_obj = llm_parse.extract_object_or_none(raw_act)
        if act_obj is not None:
            initiative_act_text = str(act_obj.get("act_text") or "").strip()
            initiative_move = bool(act_obj.get("move", False))
        else:
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
            _migrate_npc(initiator_id, player_gathering.id, mig_db)

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
    init_mj_user = _build_initiative_mj_user(
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
            obj = llm_parse.extract_object(raw)
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


_NPC_INITIATIVE_ACT_FALLBACK = (
    "[MODE INITIATIVE] Tu prends l'initiative SPONTANÉMENT, sans qu'on te l'ait demandé.\n\n"
    "Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :\n"
    '{"act_text":"<ton acte spontané, 1 à 2 phrases, première personne>","move":false}\n\n'
    '"act_text" : ta parole ou ton geste spontané. 1 à 2 phrases, première personne.\n'
    "             Aucun mot inventé, aucun fait inventé — reste dans ta fiche de contexte.\n"
    '"move"     : true UNIQUEMENT si tu te lèves physiquement pour rejoindre le groupe du\n'
    "             joueur. false par défaut. En cas de doute, false."
)


def _initiative_candidate_data(npc_ids: list[str], player_id: str, db: Session) -> tuple[list[Relation], dict[str, str]]:
    all_rels = db.exec(
        select(Relation).where(
            ((Relation.entity_a_id.in_(npc_ids)) & (Relation.entity_b_id == player_id))
            | ((Relation.entity_b_id.in_(npc_ids)) & (Relation.entity_a_id == player_id))
        )
    ).all()
    all_short_goals = db.exec(
        select(NpcGoal)
        .where(NpcGoal.npc_id.in_(npc_ids), NpcGoal.horizon == "short", NpcGoal.status == "active")
        .order_by(NpcGoal.created_at.desc())
    ).all()
    goal_by_npc: dict[str, str] = {}
    for g in all_short_goals:
        goal_by_npc.setdefault(g.npc_id, g.description)
    return all_rels, goal_by_npc


def _initiative_signal_lines(
    members: list[tuple[GatheringMember, Entity]], non_member_ids: set[str],
    all_rels: list[Relation], goal_by_npc: dict[str, str],
) -> tuple[list[str], list[str]]:
    """(group_lines, distant_lines) — non-members can only intervene by approaching (move=True)."""
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
        goal_text = goal_by_npc.get(e.id)
        goal_frag = ""
        if goal_text:
            text = goal_text if len(goal_text) <= 80 else goal_text[:80] + "…"
            goal_frag = f", objectif=« {text} »"
        return f"- {e.name} : {signal}, statut={e.status}{goal_frag}"

    group_lines   = [_signal_line(e) for _gm, e in members if e.id not in non_member_ids]
    distant_lines = [_signal_line(e) for _gm, e in members if e.id in non_member_ids]
    return group_lines, distant_lines


def _initiative_vote_call(
    template: PromptTemplate, location_name: str, interpreted_mode: ResponseMode,
    player_line: str, group_lines: list[str], distant_lines: list[str],
    members: list[tuple[GatheringMember, Entity]], model: str, db: Session,
) -> tuple[bool, Optional[str]]:
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
        obj = llm_parse.extract_object(raw)
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
    """Returns (act, entity_id) — see `_initiative_vote_call`. Cadence E1: at
    most one NPC per turn, enforced by the caller. members = all_candidates;
    non_member_ids lets the caller apply the structural move override."""
    if not members:
        return False, None

    npc_ids = [e.id for _gm, e in members]
    all_rels, goal_by_npc = _initiative_candidate_data(npc_ids, player_id, db)
    group_lines, distant_lines = _initiative_signal_lines(members, non_member_ids, all_rels, goal_by_npc)

    return _initiative_vote_call(
        template, location_name, interpreted_mode, player_line,
        group_lines, distant_lines, members, model, db,
    )


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
