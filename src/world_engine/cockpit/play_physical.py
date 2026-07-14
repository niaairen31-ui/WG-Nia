"""Physical-mode branch of the `say` play path (BRIEF-0027-b/-d): arbiter
classification, dice verdict, opposed NPC reaction, scene_state writes,
establishment narration, discovery gating. Imported lazily from
`play._say_run_turn` to avoid a circular import; see `play.py`'s module
docstring for the split rationale.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Iterator, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from .. import ollama_client
from ..context import (
    _SAFE_SUBCULTURE_KEYS,
    active_signposts,
    assemble_mj_context,
    assemble_npc_context,
    format_inventory_line,
)
from ..db import engine
from ..models import (
    BASE_SKILL_DOMAINS,
    Character,
    Conversation,
    ConversationMessage,
    DiscoverableDetail,
    Entity,
    Event,
    Gathering,
    Location,
    LocationSubculture,
    PromptTemplate,
    Skill,
    SkillDefinition,
    Visit,
)
from ..prompt_registry import effective_model
from ..prompt_store import current_prompt
from ..resolution import resolve_physical
from .play import (
    ResponseMode,
    _PHYSICAL_BAND_OUTCOME,
    _SayAbort,
    _TurnCtx,
    _active_members,
    _load_npc_dialogue_template,
    _npc_dialogue_system_prompt,
    _propose_engine_discovery,
)

_log = logging.getLogger(__name__)

_PHYSICAL_DOMAINS = BASE_SKILL_DOMAINS  # single source of truth (schema v1.63)
_VALID_CONSTRAINTS = frozenset({"gagged", "restrained", "blindfolded"})


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
            e for _gm, e in _active_members(player_gathering.id, db)
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
        arbiter_template = _load_mj_arbiter_template(ctx.world_id, db)
        if arbiter_template is not None:
            arbiter_version = current_prompt(db, arbiter_template)
            domain, opposed_npc_id, applies_constraint, violent = _arbitrate(
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
            opposed_character = db.get(Character, opposed_npc_id)
            npc_tier = opposed_character.physical_tier if opposed_character is not None else 0

    verdict = resolve_physical(resolved_base_domain, player_tier, npc_tier)
    _log.info(
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
    from . import play_stream as _play_stream

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
            ss_conv = ss_db.get(Conversation, ctx.conv_id)
            if ss_conv:
                _write_scene_state(ss_conv, new_ss)
                ss_db.add(ss_conv)
                ss_db.commit()
        # If condition reached injured/neutralized, propose engine injury.
        final_condition = new_ss.get("condition", "unharmed")
        if final_condition in ("injured", "neutralized"):
            with Session(engine) as inj_db:
                inj_conv = inj_db.get(Conversation, ctx.conv_id)
                if inj_conv:
                    _play_stream._propose_engine_injury(inj_conv, final_condition, inj_db)
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
            _propose_engine_discovery(disc_conv, found_detail, disc_db)
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
    from . import play_stream as _play_stream

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
    return _play_stream._build_mj_user(
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
        ctx, ResponseMode.physical, player_gathering, ss_constraints, ss_condition,
        responder_name, npc_reply, verdict, search_rubric,
    )
    return (
        ResponseMode.physical, mj_user, npc_reply, responder_id, responder_name,
        ss_condition, ss_constraints,
    )


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
        if location:
            subculture_rows = db.exec(
                select(LocationSubculture).where(
                    LocationSubculture.location_id == location_id,
                    LocationSubculture.key.in_(_SAFE_SUBCULTURE_KEYS),
                    LocationSubculture.is_hidden == False,  # noqa: E712
                )
            ).all()
            subculture = {row.key: row.value for row in subculture_rows if row.value}
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


_CONDITION_LADDER = ("unharmed", "bruised", "injured", "neutralized")


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
