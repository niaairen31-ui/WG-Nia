"""Physical-mode branch of the `say` play path (BRIEF-0027-b): arbiter
classification, dice verdict, opposed NPC reaction, scene_state writes,
discovery gating. Split out of `play.py` to keep both modules under the
R5 module budget (<=1000 lines) — see play.py's module docstring for the
extraction's provenance and the `_app` reuse convention.

Imported lazily from `play._say_run_turn` (only once play.py has finished
loading) so `_TurnCtx`/`_SayAbort` can be imported here at module top
without a circular import.
"""

from __future__ import annotations

import json
from typing import Any, Iterator, Optional

from sqlmodel import Session, select

from .. import ollama_client
from ..context import assemble_mj_context, assemble_npc_context, format_inventory_line
from ..db import engine
from ..models import Conversation, DiscoverableDetail, Entity, Gathering, Skill, SkillDefinition
from ..prompt_store import current_prompt
from ..resolution import resolve_physical
from . import app as _app
from .play import _PHYSICAL_BAND_OUTCOME, _SayAbort, _TurnCtx


def _say_physical_roster_and_arbiter(
    ctx: _TurnCtx, is_gagged_attempt: bool, is_escape_attempt: bool, player_gathering: Optional[Gathering],
) -> tuple[str, Optional[str], Optional[str], bool, Optional[int], dict, tuple]:
    """Arbiter classification + Python dice, part 1 (BRIEF-11, schema v1.23).

    Candidate NPC roster for opposition: the player's gathering (excluding
    the player) if grouped, else the conversation's seed NPC for plain 1:1
    scenes. Returns (domain, opposed_npc_id, applies_constraint, violent,
    npc_tier, world_skill_defs_by_name, world_custom_skill_names) — npc_tier
    is 1 for a constraint-gated turn, else None (resolved by the caller).
    """
    db = ctx.db
    if player_gathering is not None:
        physical_npc_entities = [
            e for _gm, e in _app._active_members(player_gathering.id, db)
            if e.id != ctx.conv.player_id
        ]
    elif ctx.npc_entity is not None:
        physical_npc_entities = [ctx.npc_entity]
    else:
        physical_npc_entities = []
    physical_name_to_id = {e.name.lower(): e.id for e in physical_npc_entities}
    physical_npc_list = ", ".join(e.name for e in physical_npc_entities)

    # BRIEF-55 (5a, schema v1.63): dynamic candidate list — the active
    # world's custom skill definitions, injected into the arbiter
    # prompt as fillable text and used to widen the domain clamp.
    world_skill_defs = db.exec(
        select(SkillDefinition).where(SkillDefinition.world_id == ctx.world_id)
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
    npc_tier: Optional[int] = None
    if is_gagged_attempt:
        # Gagged speech attempt: composure roll, fixed difficulty.
        domain, opposed_npc_id = "composure", None
        npc_tier = 1     # pilot default: fixed restraint difficulty, see note
    elif is_escape_attempt:
        # Escape from restraint: physical roll, fixed difficulty.
        domain, opposed_npc_id = "physical", None
        npc_tier = 1     # pilot default: fixed restraint difficulty, see note
    else:
        arbiter_template = _app._load_mj_arbiter_template(ctx.world_id, db)
        if arbiter_template is not None:
            arbiter_version = current_prompt(db, arbiter_template)
            domain, opposed_npc_id, applies_constraint, violent = _app._arbitrate(
                player_line=ctx.content,
                npc_list=physical_npc_list,
                name_to_id=physical_name_to_id,
                arbiter_system=arbiter_version.system_prompt,
                arbiter_user_tpl=arbiter_version.user_template,
                model=ctx.model,
                custom_skill_names=world_custom_skill_names,
            )
        else:
            domain, opposed_npc_id = "physical", None

    return domain, opposed_npc_id, applies_constraint, violent, npc_tier, world_skill_defs_by_name, world_custom_skill_names


def _say_physical_resolve_verdict(
    ctx: _TurnCtx, domain: str, opposed_npc_id: Optional[str], npc_tier: Optional[int],
    world_skill_defs_by_name: dict,
) -> tuple[str, Any, Optional[Entity], str]:
    """Arbiter classification + Python dice, part 2: resolution mapping and
    the dice verdict. Returns (resolved_base_domain, verdict, opposed_entity,
    verdict_sse_line)."""
    db = ctx.db
    # BRIEF-55 (5d, schema v1.63): resolution mapping. `domain` may now
    # be a base domain OR a custom skill name (constraint-gated turns
    # above only ever set a base domain, so they fall in the first
    # branch). `resolved_base_domain` is what bands/discovery key off.
    custom_def = world_skill_defs_by_name.get(domain)
    if custom_def is None:
        resolved_base_domain = domain
        skill_row = db.exec(
            select(Skill).where(
                Skill.character_id == ctx.conv.player_id,
                Skill.domain == domain,
                Skill.skill_definition_id.is_(None),
            )
        ).first()
    else:
        resolved_base_domain = custom_def.base_domain
        skill_row = db.exec(
            select(Skill).where(
                Skill.character_id == ctx.conv.player_id,
                Skill.skill_definition_id == custom_def.id,
            )
        ).first()
        if skill_row is None:
            # Defensive fallback: the PC somehow lacks the custom row.
            skill_row = db.exec(
                select(Skill).where(
                    Skill.character_id == ctx.conv.player_id,
                    Skill.domain == resolved_base_domain,
                    Skill.skill_definition_id.is_(None),
                )
            ).first()

    # Player-roll rule (resolution.py): the roll always belongs to the
    # player — player_tier from the skill sheet, npc_tier (if opposed)
    # from character.physical_tier, default 0 either way.
    player_tier = skill_row.tier if skill_row else 0

    opposed_entity: Optional[Entity] = None
    # npc_tier already set for gated turns above; normal turns start at 0.
    if npc_tier is None:
        npc_tier = 0
    if opposed_npc_id:
        opposed_entity = db.get(Entity, opposed_npc_id)
        if opposed_entity is not None:
            opposed_character = db.get(_app.Character, opposed_npc_id)
            npc_tier = opposed_character.physical_tier if opposed_character is not None else 0

    verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)
    _app._log.info(
        "Physical verdict: domain=%s dice=%s modifier=%d total=%d band=%s "
        "(player_tier=%d, npc_tier=%d, opposed=%s)",
        verdict.domain, verdict.dice, verdict.modifier, verdict.total,
        verdict.band, player_tier, npc_tier, opposed_npc_id or "none",
    )
    verdict_sse_line = f"data: {json.dumps({'verdict': {'domain': verdict.domain, 'dice': list(verdict.dice), 'modifier': verdict.modifier, 'total': verdict.total, 'band': verdict.band}})}\n\n"
    return resolved_base_domain, verdict, opposed_entity, verdict_sse_line


def _say_physical_npc_reaction(
    ctx: _TurnCtx, opposed_npc_id: Optional[str], opposed_entity: Optional[Entity], verdict: Any,
    ss_condition: str,
) -> tuple[str, Optional[str], str]:
    """NPC phase: opposed turns only (unopposed behaves like scene). Returns
    (npc_reply, responder_id, responder_name). Raises _SayAbort on an Ollama
    error (error event + [DONE], turn ends immediately)."""
    db = ctx.db
    if not (opposed_npc_id and opposed_entity is not None):
        return "", None, ctx.npc_name

    responder_id = opposed_npc_id
    responder_name = opposed_entity.name

    responder_behaviour = _app._load_npc_dialogue_template(ctx.world_id, db)
    responder_behaviour_version = current_prompt(db, responder_behaviour)
    responder_context = assemble_npc_context(
        responder_id, ctx.conv.player_id, ctx.conv.location_id, db,
        gathering_id=ctx.conv.gathering_id,
        player_condition=ss_condition,
    )
    responder_system_prompt = _app._npc_dialogue_system_prompt(
        responder_behaviour_version.system_prompt, responder_context
    )

    band_outcome = _PHYSICAL_BAND_OUTCOME[verdict.band]

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
        *ctx.npc_history,
    ]

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


def _say_physical_scene_state_writes(
    ctx: _TurnCtx, is_escape_attempt: bool, applies_constraint: Optional[str], violent: bool,
    verdict: Any, scene_state: dict, ss_condition: str, ss_constraints: set,
) -> tuple[str, set]:
    """BRIEF-12: scene_state writes after verdict. Batched: collect all
    changes, write once. Returns (ss_condition, ss_constraints) — unchanged
    if nothing about the scene changed."""
    new_ss = dict(scene_state)
    new_constraints = list(new_ss.get("constraints", []))
    ss_changed = False

    if is_escape_attempt and verdict.band == "success":
        # Successful escape: remove restrained constraint.
        if "restrained" in new_constraints:
            new_constraints.remove("restrained")
            ss_changed = True
            _app._log.info("Escape success — 'restrained' constraint removed from scene_state")

    if applies_constraint and verdict.band == "failure":
        # Failed resistance: player is now constrained.
        if applies_constraint not in new_constraints:
            new_constraints.append(applies_constraint)
            ss_changed = True
            _app._log.info("Constraint applied: '%s' added to scene_state", applies_constraint)

    if violent and verdict.band == "failure":
        # Condition degradation on violent failed roll.
        current_idx = _app._CONDITION_LADDER.index(
            new_ss.get("condition", "unharmed")
            if new_ss.get("condition", "unharmed") in _app._CONDITION_LADDER
            else "unharmed"
        )
        if current_idx < len(_app._CONDITION_LADDER) - 1:
            new_condition = _app._CONDITION_LADDER[current_idx + 1]
            new_ss["condition"] = new_condition
            ss_changed = True
            _app._log.info("Condition degraded to '%s'", new_condition)
            if new_condition == "neutralized":
                new_ss["frozen"] = True
                _app._log.info("Condition 'neutralized' — scene frozen")

    if ss_changed:
        new_ss["constraints"] = new_constraints
        with Session(engine) as ss_db:
            ss_conv = ss_db.get(Conversation, ctx.conv_id)
            if ss_conv:
                _app._write_scene_state(ss_conv, new_ss)
                ss_db.add(ss_conv)
                ss_db.commit()
        # If condition reached injured/neutralized, propose engine injury.
        final_condition = new_ss.get("condition", "unharmed")
        if final_condition in ("injured", "neutralized"):
            with Session(engine) as inj_db:
                inj_conv = inj_db.get(Conversation, ctx.conv_id)
                if inj_conv:
                    _app._propose_engine_injury(inj_conv, final_condition, inj_db)
                    inj_db.commit()
        # Update local copies for the MJ context below.
        ss_condition = new_ss.get("condition", "unharmed")
        ss_constraints = set(new_ss.get("constraints", []))

    return ss_condition, ss_constraints


def _say_physical_discovery(
    ctx: _TurnCtx, resolved_base_domain: str, opposed_npc_id: Optional[str], verdict: Any,
) -> Optional[str]:
    """Discovery gating (BRIEF-13, schema v1.26).

    Fires only for perception searches: domain="perception" AND no NPC
    opposition. A perception roll WITH opposition (e.g. spotting a NPC's
    hidden weapon under pressure) is NOT a search — must not trigger
    discovery. Only the code judges what is found; the model receives
    content ONLY after selection.
    """
    db = ctx.db
    if resolved_base_domain != "perception" or opposed_npc_id is not None:
        return None

    if verdict.band not in ("partial", "success"):
        # failure band: anti-invention rubric, no proposal.
        return (
            "[FOUILLE INFRUCTUEUSE]\n"
            "Le personnage cherche mais ne trouve rien de notable.\n"
            "N'invente AUCUN objet, lettre, passage ou indice. Décris la fouille\n"
            "elle-même (gestes, recoins inspectés) et le fait que rien ne ressort."
        )

    # Select the oldest undiscovered hidden detail REACHABLE at this
    # roll: discovery_threshold <= verdict.total (N1). When every
    # undiscovered detail is above threshold the query returns no row,
    # found_detail is None, and we fall through to [FOUILLE INFRUCTUEUSE]
    # below — structurally identical to an exhausted location, so gated
    # content never leaks.
    found_detail = db.exec(
        select(DiscoverableDetail).where(
            DiscoverableDetail.location_id == ctx.conv.location_id,
            DiscoverableDetail.access_level == "hidden",
            DiscoverableDetail.discovered == False,  # noqa: E712
            DiscoverableDetail.discovery_threshold <= verdict.total,
        ).order_by(
            DiscoverableDetail.created_at,
            DiscoverableDetail.id,
        )
    ).first() if ctx.conv.location_id else None

    if found_detail is None:
        return (
            "[FOUILLE INFRUCTUEUSE]\n"
            "Le personnage cherche mais ne trouve rien de notable.\n"
            "N'invente AUCUN objet, lettre, passage ou indice. Décris la fouille\n"
            "elle-même (gestes, recoins inspectés) et le fait que rien ne ressort."
        )

    with Session(engine) as disc_db:
        disc_conv = disc_db.get(Conversation, ctx.conv_id)
        if disc_conv:
            _app._propose_engine_discovery(disc_conv, found_detail, disc_db)
            disc_db.commit()
    return (
        f"[FOUILLE — VERDICT {verdict.band}]\n"
        f"success : le personnage trouve ce qu'il cherchait, proprement.\n"
        f"partial : le personnage trouve ce qu'il cherchait, MAIS au prix d'une\n"
        f"  complication (bruit, objet renversé, un témoin remarque son manège).\n"
        f"  L'information est bel et bien trouvée ; seule la position se dégrade.\n"
        f"Contenu trouvé : {found_detail.content}\n"
        f"Tu narres la découverte ; tu ne rejuges pas le résultat."
    )


def _say_physical_mj_user(
    ctx: _TurnCtx, mode: Any, player_gathering: Optional[Gathering], ss_constraints: set,
    ss_condition: str, responder_name: str, npc_reply: str, verdict: Any, search_rubric: Optional[str],
) -> str:
    """MJ narration user message for the physical branch."""
    mj_context = (
        assemble_mj_context(
            ctx.db, ctx.conv.player_id, ctx.conv.location_id,
            gathering_id=player_gathering.id if player_gathering else None,
            blindfolded="blindfolded" in ss_constraints,
            player_condition=ss_condition,
        )
        if ctx.conv.location_id else None
    )
    inventory_line = format_inventory_line(ctx.db, ctx.conv.player_id)
    return _app._build_mj_user(
        mode=mode,
        mj_user_template=ctx.mj_user_template,
        npc_name=responder_name,
        location_name=ctx.location_name,
        player_line=ctx.content,
        npc_reply=npc_reply,
        mj_context=mj_context,
        inventory_line=inventory_line,
        verdict_band=verdict.band,
        search_rubric=search_rubric,
    )


def _say_physical_branch(
    ctx: _TurnCtx, is_gagged_attempt: bool, is_escape_attempt: bool,
    player_gathering: Optional[Gathering], scene_state: dict, ss_condition: str, ss_constraints: set,
) -> Iterator[str]:
    """Orchestrates the physical mode branch, yielding the verdict SSE event
    at the exact point the original code did — before the (silent,
    buffered — no per-chunk yield) opposed NPC reaction call. Returns
    (mode, mj_user, npc_reply, responder_id, responder_name, ss_condition,
    ss_constraints) via PEP 380 `return`, retrieved by the caller as the
    `yield from` expression's value.
    """
    (domain, opposed_npc_id, applies_constraint, violent, npc_tier,
     world_skill_defs_by_name, _custom_names) = _say_physical_roster_and_arbiter(
        ctx, is_gagged_attempt, is_escape_attempt, player_gathering,
    )
    resolved_base_domain, verdict, opposed_entity, verdict_line = _say_physical_resolve_verdict(
        ctx, domain, opposed_npc_id, npc_tier, world_skill_defs_by_name,
    )
    yield verdict_line

    npc_reply, responder_id, responder_name = _say_physical_npc_reaction(
        ctx, opposed_npc_id, opposed_entity, verdict, ss_condition,
    )

    ss_condition, ss_constraints = _say_physical_scene_state_writes(
        ctx, is_escape_attempt, applies_constraint, violent, verdict,
        scene_state, ss_condition, ss_constraints,
    )

    search_rubric = _say_physical_discovery(ctx, resolved_base_domain, opposed_npc_id, verdict)
    mj_user = _say_physical_mj_user(
        ctx, _app.ResponseMode.physical, player_gathering, ss_constraints, ss_condition,
        responder_name, npc_reply, verdict, search_rubric,
    )
    return (
        _app.ResponseMode.physical, mj_user, npc_reply, responder_id, responder_name,
        ss_condition, ss_constraints,
    )


