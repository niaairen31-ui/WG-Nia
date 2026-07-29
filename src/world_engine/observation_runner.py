"""Observation runner (TICKET-0051, BRIEF-0051-e): assembles the socle
(-a), the disclosure floor (-b), the analysis seam (-c) and the engine (-d)
into a bounded run that executes N beats and stops.

Beat sequencing and persistence live here — `observation_engine.py` (-d)
supplies the mechanism (one intent call per present NPC, pure arbitration)
and writes nothing; `observation_writes.py` (-a) is the only module allowed
to write an `observation_*` row.

Roster model: a run carries no participant/roster column. "Present NPCs"
is re-derived fresh at every beat from `Character.current_location_id ==
run.location_id` (mirrors `gathering.py`'s `_present_npcs`) rather than
snapshotted at run start — this ticket adds no NPC-movement mechanism, so
the set is expected to be stable across a run; G1 accepts the live-DB
consequence of that choice.

Template pinning (L, reduced): `observation_run_template` rows captured at
`start_run` are an ATTRIBUTION record (what was active when the run began),
not a replay lock — every beat re-resolves the head template by usage and
calls `current_prompt` for the latest text, exactly like -d's
`request_intent`. Bit-exact replay is out of scope by decision.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .analyzer_transcript import AttributionContext, analyze_overheard_lines, analyze_transcript
from .context import assemble_npc_context
from .models import (
    Character,
    Entity,
    NpcGoal,
    ObservationBeat,
    ObservationRun,
    ProposedMutation,
    PromptTemplate,
    Relation,
)
from .observation_engine import arbitrate, request_intent
from .observation_window import resolve_observation_transcript
from .observation_writes import (
    OBSERVED_PROPOSED_BY,
    close_observation_run,
    link_observation_mutation,
    write_observation_beat,
    write_observation_intent,
    write_observation_run,
)
from .prompt_store import current_prompt

_log = logging.getLogger(__name__)

OBSERVATION_NARRATION_USAGE = "observation_narration"

_NPC_INITIATIVE_ACT_FALLBACK = (
    "[MODE INITIATIVE] Tu prends l'initiative SPONTANÉMENT, sans qu'on te l'ait demandé.\n\n"
    "Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne, rien d'autre :\n"
    '{"act_text":"<ton acte spontané, 1 à 2 phrases, première personne>","move":false}\n\n'
    '"act_text" : ta parole ou ton geste spontané. 1 à 2 phrases, première personne.\n'
    "             Aucun mot inventé, aucun fait inventé — reste dans ta fiche de contexte."
)

_OBSERVATION_NARRATION_FALLBACK_SYSTEM = (
    "Tu es le narrateur d'une scène observée : des personnages non-joueurs agissent "
    "entre eux, sans joueur présent. Reformule en prose narrative légère, à la "
    "troisième personne, ce que le personnage vient de faire ou dire. Cite sa "
    "réplique VERBATIM entre guillemets français si elle parle. Cadrage minimal, "
    "n'invente rien au-delà de ce qui est fourni. Deux à trois phrases, rien d'autre."
)

_OBSERVATION_NARRATION_FALLBACK_USER = (
    "Lieu : {location_name}\n\nContexte récent :\n{transcript}\n\n"
    "{actor_name} vient de faire ceci :\n{line}\n\nNarration :"
)

# ── Readiness gate (fail-closed) ─────────────────────────────────────────


def check_run_readiness(
    location_id: str,
    npc_ids: list[str],
    db: Session,
    *,
    world_id: str,
    player_presence: str,
) -> list[str]:
    """The gate exists because a flat scene has two very different causes: a
    passive initiative system (what this ticket measures) and an
    under-populated world (what it does not). Without the gate the first
    finding of every run risks being misattributed to the engine. Refusing
    loudly costs one message; a misattributed conclusion costs a redesign.

    Returns the list of failed conditions (empty = ready). `world_id` and
    `player_presence` extend the brief's minimal documented signature
    (`location_id, npc_ids, db`) with the two identities no condition here
    can be checked without — mirrors -d's `arbitrate` carrying
    `beats_since_last_act`/`relation_intensities` beyond its own minimal
    doc signature for the same reason."""
    failures: list[str] = []

    if player_presence != "absent":
        failures.append(
            f"player_presence {player_presence!r} is not implemented — "
            "only 'absent' is supported (TICKET-0051, H2)"
        )

    location = db.get(Entity, location_id)
    if location is None or location.type != "location" or location.world_id != world_id:
        failures.append(f"location {location_id!r} does not exist or does not belong to world {world_id!r}")

    if len(npc_ids) < 2:
        failures.append(f"fewer than 2 NPCs present (found {len(npc_ids)})")

    if npc_ids:
        entities = {e.id: e for e in db.exec(select(Entity).where(Entity.id.in_(npc_ids))).all()}
        for npc_id in npc_ids:
            entity = entities.get(npc_id)
            if entity is None or not (entity.name or "").strip() or not (entity.description or "").strip():
                failures.append(f"NPC {npc_id!r} lacks a describable identity (name and description)")

        goal_npc_ids = {
            g.npc_id
            for g in db.exec(
                select(NpcGoal).where(NpcGoal.npc_id.in_(npc_ids), NpcGoal.status == "active")
            ).all()
        }
        for npc_id in npc_ids:
            if npc_id not in goal_npc_ids:
                entity = entities.get(npc_id)
                label = entity.name if entity is not None else npc_id
                failures.append(f"NPC {label} has no active goal")

    return failures


def _present_npc_ids(location_id: str, db: Session) -> list[str]:
    """NPCs actually present at a location — physical co-location, never
    gathering membership (a run neither creates nor attaches to a
    gathering; mini-RECON item 4)."""
    rows = db.exec(
        select(Character.id)
        .join(Entity, Entity.id == Character.id)
        .where(
            Character.current_location_id == location_id,
            Character.character_type == "npc",
            Character.vital_status == "alive",
            Entity.status == "active",
        )
    ).all()
    return list(rows)


# ── Template pinning (L) ─────────────────────────────────────────────────


def _load_template_by_usage(usage: str, world_id: Optional[str], db: Session) -> Optional[PromptTemplate]:
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == usage,
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


def _pin_templates(world_id: str, mj_narration: bool, db: Session) -> list[dict]:
    pins: list[dict] = []
    for usage in ("observation_intent", "npc_initiative_act"):
        template = _load_template_by_usage(usage, world_id, db)
        if template is None:
            raise RuntimeError(f"start_run: no active {usage!r} prompt template — seed it first")
        version = current_prompt(db, template)
        pins.append({"usage": usage, "template_id": template.id, "version": version.version_number})
    if mj_narration:
        template = _load_template_by_usage(OBSERVATION_NARRATION_USAGE, world_id, db)
        if template is not None:
            version = current_prompt(db, template)
            pins.append(
                {"usage": OBSERVATION_NARRATION_USAGE, "template_id": template.id, "version": version.version_number}
            )
    return pins


# ── Run start ─────────────────────────────────────────────────────────────


def start_run(
    world_id: str,
    location_id: str,
    db: Session,
    *,
    max_beats: int = 30,
    quiescence_limit: int = 5,
    mj_narration: bool = False,
    cooldown_beats: int = 2,
    debt_weight: float = 1.0,
    propensity_mode: str = "flat",
    model: str = ollama_client.DEFAULT_MODEL,
    player_presence: str = "absent",
    gathering_id: Optional[str] = None,
) -> tuple[Optional[ObservationRun], list[str]]:
    """Readiness gate, then (only on success) the single write. Returns
    `(None, failures)` on refusal — no `observation_run` row — or
    `(run, [])` on success."""
    npc_ids = _present_npc_ids(location_id, db)
    failures = check_run_readiness(location_id, npc_ids, db, world_id=world_id, player_presence=player_presence)
    if failures:
        return None, failures

    templates = _pin_templates(world_id, mj_narration, db)
    run = write_observation_run(
        db,
        world_id=world_id,
        location_id=location_id,
        gathering_id=gathering_id,
        player_presence=player_presence,
        max_beats=max_beats,
        quiescence_limit=quiescence_limit,
        mj_narration=mj_narration,
        cooldown_beats=cooldown_beats,
        debt_weight=debt_weight,
        propensity_mode=propensity_mode,
        model=model,
        templates=templates,
    )
    return run, []


# ── Beat bookkeeping ──────────────────────────────────────────────────────


def _prior_beats(run_id: str, db: Session) -> list[ObservationBeat]:
    return list(
        db.exec(
            select(ObservationBeat)
            .where(ObservationBeat.run_id == run_id)
            .order_by(ObservationBeat.beat_index)
        ).all()
    )


def _regular_beat_count(beats: list[ObservationBeat]) -> int:
    """max_beats counts NPC-decision beats only — an injected event
    consumes no allowance (K2)."""
    return sum(1 for b in beats if b.outcome != "event")


def _consecutive_non_acted(beats: list[ObservationBeat]) -> int:
    """Scans backward, skipping 'event' beats entirely (neither a datum nor
    a reset — they are creator narration, not an NPC declining)."""
    count = 0
    for beat in reversed(beats):
        if beat.outcome == "event":
            continue
        if beat.outcome == "acted":
            break
        count += 1
    return count


def _acted_history(beats: list[ObservationBeat]) -> tuple[dict[str, int], Optional[str], Optional[int]]:
    acted_counts: dict[str, int] = {}
    last_actor_id: Optional[str] = None
    last_acted_beat_index: Optional[int] = None
    for b in beats:
        if b.outcome == "acted":
            acted_counts[b.actor_id] = acted_counts.get(b.actor_id, 0) + 1
            last_actor_id = b.actor_id
            last_acted_beat_index = b.beat_index
    return acted_counts, last_actor_id, last_acted_beat_index


def _intent_transcript(beats: list[ObservationBeat], db: Session) -> str:
    """'Name : line' per acted beat, raw text for an injected event.
    TICKET-0052 (H1): its only remaining reader is the MJ narration call
    (`_generate_mj_narration`) — the intent call and the act-line call now
    resolve their transcript per NPC through `observation_window.
    resolve_observation_transcript` instead. Distinct from the
    analysis-pass transcript's frozen [PNJ]/[JOUEUR] contract, built
    separately in `_analysis_transcript`."""
    names: dict[str, str] = {}
    lines: list[str] = []
    for b in beats:
        if b.line is None:
            continue
        if b.outcome == "event":
            lines.append(b.line)
            continue
        if b.actor_id not in names:
            entity = db.get(Entity, b.actor_id)
            names[b.actor_id] = entity.name if entity else b.actor_id
        lines.append(f"{names[b.actor_id]} : {b.line}")
    return "\n".join(lines)


def _relation_intensities(npc_ids: list[str], last_actor_id: str, db: Session) -> dict[str, int]:
    rows = db.exec(
        select(Relation).where(
            ((Relation.entity_a_id.in_(npc_ids)) & (Relation.entity_b_id == last_actor_id))
            | ((Relation.entity_b_id.in_(npc_ids)) & (Relation.entity_a_id == last_actor_id))
        )
    ).all()
    result: dict[str, int] = {}
    for r in rows:
        source = r.entity_a_id if r.entity_a_id in npc_ids else r.entity_b_id
        result[source] = r.intensity
    return result


def _beat_outcome(selected_npc_id: Optional[str], intents: list) -> str:
    if selected_npc_id is not None:
        return "acted"
    if any(i.call_status == "ok" for i in intents):
        return "silence"
    return "degraded"


# ── Line / narration generation ──────────────────────────────────────────


def _generate_act_line(
    actor_id: str, target_id: Optional[str], present_ids: list[str], location_id: str,
    transcript: str, world_id: str, db: Session, model: str,
) -> str:
    """Second call of an 'acted' beat: turn the winning candidate's intent
    into an actual line, reusing the played path's npc_initiative_act
    contract verbatim (brief step 5). Mirrors play_initiative.py's
    _say_initiative_context/_say_initiative_generate composition (npc
    dialogue system prompt + context + act instruction) — duplicated
    rather than imported: core modules never import cockpit modules."""
    dialogue_template = _load_template_by_usage("npc_dialogue", world_id, db)
    dialogue_prompt = current_prompt(db, dialogue_template).system_prompt if dialogue_template is not None else ""

    act_template = _load_template_by_usage("npc_initiative_act", world_id, db)
    act_instruction = (
        current_prompt(db, act_template).system_prompt
        if act_template is not None else _NPC_INITIATIVE_ACT_FALLBACK
    )

    audience_ids = [i for i in present_ids if i != actor_id]
    if target_id in audience_ids:
        interlocutor_id, rest_audience = target_id, [i for i in audience_ids if i != target_id]
    elif audience_ids:
        interlocutor_id, rest_audience = audience_ids[0], audience_ids[1:]
    else:
        interlocutor_id, rest_audience = None, []

    npc_context = (
        assemble_npc_context(actor_id, interlocutor_id, location_id, db, audience_ids=rest_audience or None)
        if interlocutor_id is not None else ""
    )
    system_prompt = f"{dialogue_prompt}\n\n{npc_context}\n\n{act_instruction}"
    user_msg = f"Ce qui vient de se passer dans la scène :\n{transcript}\n\nTu prends l'initiative maintenant."

    try:
        raw = ollama_client.chat(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
            model=model, format="json", options=ollama_client.NPC_DIALOGUE_OPTIONS,
        )
    except ollama_client.OllamaError:
        return ""
    obj = llm_parse.extract_object_or_none(raw)
    if obj is not None:
        return str(obj.get("act_text") or "").strip()
    return raw.strip()


def _generate_mj_narration(
    actor_id: str, line: str, location_id: str, transcript: str, world_id: str, db: Session, model: str,
) -> Optional[str]:
    """One non-streaming call after the line (brief step 7) — no perception
    scoping (no player to scope for; an omniscient creator reads this)."""
    template = _load_template_by_usage(OBSERVATION_NARRATION_USAGE, world_id, db)
    if template is not None:
        version = current_prompt(db, template)
        system_prompt, user_template = version.system_prompt, version.user_template
    else:
        system_prompt, user_template = _OBSERVATION_NARRATION_FALLBACK_SYSTEM, _OBSERVATION_NARRATION_FALLBACK_USER

    actor = db.get(Entity, actor_id)
    location = db.get(Entity, location_id)
    user_msg = (
        user_template
        .replace("{location_name}", location.name if location else location_id)
        .replace("{actor_name}", actor.name if actor else actor_id)
        .replace("{line}", line)
        .replace("{transcript}", transcript)
        + "\n/no_think"
    )
    try:
        raw = ollama_client.chat(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
            model=model, options=ollama_client.MJ_NARRATION_OPTIONS,
        )
    except ollama_client.OllamaError:
        return None
    return raw.strip() or None


# ── The beat ──────────────────────────────────────────────────────────────


def run_one_beat(run_id: str, db: Session) -> ObservationBeat:
    """Executes exactly one beat against an open run (B1). Universal
    opportunity (C3): every present NPC gets an intent call, always; one
    observation_beat and one observation_intent per candidate are written,
    including on total failure (M2 — outcome is never inferred)."""
    run = db.get(ObservationRun, run_id)
    if run is None:
        raise ValueError(f"run_one_beat: no observation_run {run_id!r}")
    if run.status != "running":
        raise ValueError(f"run_one_beat: run {run_id!r} is not running (status={run.status!r})")

    npc_ids = _present_npc_ids(run.location_id, db)
    if len(npc_ids) < 2:
        raise ValueError(f"run_one_beat: fewer than 2 NPCs present at {run.location_id!r}")

    prior_beats = _prior_beats(run_id, db)
    beat_index = len(prior_beats)
    transcript = _intent_transcript(prior_beats, db)

    intent_template = _load_template_by_usage("observation_intent", run.world_id, db)
    if intent_template is None:
        raise RuntimeError("run_one_beat: no active observation_intent prompt template")

    # Windowed, PER NPC (G2): the intent call and the act-line call share this
    # resolution — one per NPC per beat, never recomputed for the act line.
    windowed_transcripts = {
        npc_id: resolve_observation_transcript(
            world_id=run.world_id, npc_id=npc_id, location_id=run.location_id,
            beats=prior_beats, db=db,
        )
        for npc_id in npc_ids
    }
    intents = [
        request_intent(
            npc_id, [i for i in npc_ids if i != npc_id], windowed_transcripts[npc_id], run.location_id,
            intent_template, db, run.model, ollama_client.OLLAMA_HOST,
        )
        for npc_id in npc_ids
    ]

    acted_counts, last_actor_id, last_acted_beat_index = _acted_history(prior_beats)
    beats_since_last_act = (
        beat_index - last_acted_beat_index if last_acted_beat_index is not None else beat_index + 1
    )
    relation_intensities = (
        _relation_intensities(npc_ids, last_actor_id, db)
        if run.propensity_mode == "relation_weighted" and last_actor_id is not None
        else None
    )
    arb = arbitrate(
        intents=intents, npc_ids=npc_ids, last_actor_id=last_actor_id,
        acted_counts=acted_counts, beats_elapsed=beat_index,
        cooldown_beats=run.cooldown_beats, debt_weight=run.debt_weight,
        propensity_mode=run.propensity_mode,
        beats_since_last_act=beats_since_last_act,
        relation_intensities=relation_intensities,
    )

    line: Optional[str] = None
    mj_text: Optional[str] = None
    if arb.selected_npc_id is not None:
        selected_intent = intents[npc_ids.index(arb.selected_npc_id)]
        line = _generate_act_line(
            arb.selected_npc_id, selected_intent.target_id, npc_ids, run.location_id,
            windowed_transcripts[arb.selected_npc_id], run.world_id, db, run.model,
        )
        if run.mj_narration:
            # H1 (TICKET-0052): the MJ narration deliberately keeps the RAW transcript.
            # The played MJ narrator has no history at all (play_stream.py:51-54 sends
            # [system, one user message]), so there is no MJ window to mirror. Named
            # deferral D-0052-mj. Do not "fix" this by routing it through the seam.
            mj_text = _generate_mj_narration(
                arb.selected_npc_id, line, run.location_id, transcript, run.world_id, db, run.model,
            )

    outcome = _beat_outcome(arb.selected_npc_id, intents)

    beat = write_observation_beat(
        db, run_id=run_id, beat_index=beat_index, outcome=outcome,
        actor_id=arb.selected_npc_id, line=line, mj_narration=mj_text,
    )
    for npc_id, intent, score in zip(npc_ids, intents, arb.scores):
        write_observation_intent(
            db, run_id=run_id, beat_id=beat.id, npc_id=npc_id,
            act=intent.act, urgency=intent.urgency, target_id=intent.target_id, why=intent.why,
            propensity=score.propensity, cooldown_active=score.cooldown_active,
            debt_score=score.debt_score, final_score=score.final_score, selected=score.selected,
            call_status=intent.call_status, latency_ms=intent.latency_ms, raw_response=intent.raw_response,
        )
    return beat


def _run_beat_safely(run_id: str, db: Session) -> ObservationBeat:
    """A run must never stay 'running' after the process returns, including
    on an unhandled exception — closes failed/error before propagating."""
    try:
        return run_one_beat(run_id, db)
    except Exception:
        try:
            close_observation_run(run_id, "failed", "error", db)
        except ValueError:
            pass  # already terminal — don't mask the original exception
        _produce_proposals_quietly(run_id, db)
        raise


# ── Stop conditions / stepping ───────────────────────────────────────────


def _apply_stop_conditions(run: ObservationRun, db: Session) -> ObservationRun:
    beats = _prior_beats(run.id, db)
    if _regular_beat_count(beats) >= run.max_beats:
        run = close_observation_run(run.id, "completed", "max_beats", db)
        _produce_proposals_quietly(run.id, db)
        return run
    if _consecutive_non_acted(beats) >= run.quiescence_limit:
        run = close_observation_run(run.id, "completed", "quiescence", db)
        _produce_proposals_quietly(run.id, db)
        return run
    return run


def step_run(run_id: str, db: Session) -> tuple[ObservationBeat, ObservationRun]:
    """One beat, then the same stop-condition check `run_bounded` applies —
    a manual step and a bounded loop converge on the same terminal state."""
    run = db.get(ObservationRun, run_id)
    if run is None:
        raise ValueError(f"step_run: no observation_run {run_id!r}")
    if run.status != "running":
        raise ValueError(f"step_run: run {run_id!r} is not running (status={run.status!r})")
    beat = _run_beat_safely(run_id, db)
    run = _apply_stop_conditions(run, db)
    return beat, run


def run_bounded(run_id: str, db: Session) -> ObservationRun:
    """Loops single-beat stepping until a stop condition (B2). Built ON
    run_one_beat/step_run — one implementation, two entry points."""
    while True:
        run = db.get(ObservationRun, run_id)
        if run is None:
            raise ValueError(f"run_bounded: no observation_run {run_id!r}")
        if run.status != "running":
            return run
        _, run = step_run(run_id, db)


def stop_run(run_id: str, db: Session) -> ObservationRun:
    """Creator-forced stop."""
    run = close_observation_run(run_id, "stopped", "creator_stop", db)
    _produce_proposals_quietly(run_id, db)
    return run


def inject_event(run_id: str, text: str, db: Session) -> ObservationBeat:
    """K2: a creator-authored beat with no actor and no intent rows,
    consuming no beat allowance. Becomes part of the transcript every
    subsequent NPC reads via _intent_transcript — that is the mechanism."""
    run = db.get(ObservationRun, run_id)
    if run is None:
        raise ValueError(f"inject_event: no observation_run {run_id!r}")
    if run.status != "running":
        raise ValueError(f"inject_event: run {run_id!r} is not running (status={run.status!r})")
    beat_index = len(_prior_beats(run_id, db))
    return write_observation_beat(db, run_id=run_id, beat_index=beat_index, outcome="event", actor_id=None, line=text)


# ── F3: proposal production (once per run, after close) ─────────────────


def _analysis_transcript(beats: list[ObservationBeat]) -> str:
    """The frozen [PNJ] contract (analyzer_transcript.py's module
    docstring) for every acted line — never [JOUEUR], no player exists.
    Injected events get their own label: they are creator narration, not
    something a PNJ said, and the frozen contract has no third option."""
    lines = []
    for b in beats:
        if b.line is None:
            continue
        if b.outcome == "event":
            lines.append(f"[ÉVÉNEMENT] {b.line}")
        elif b.outcome == "acted":
            lines.append(f"[PNJ] {b.line}")
    return "\n".join(lines)


def _persist_and_link(run_id: str, mutations: list[ProposedMutation], db: Session) -> list[ProposedMutation]:
    for mutation in mutations:
        mutation.proposed_by = OBSERVED_PROPOSED_BY
        db.add(mutation)
    db.commit()
    for mutation in mutations:
        db.refresh(mutation)
        link_observation_mutation(db, run_id=run_id, beat_id=None, mutation_id=mutation.id)
    return mutations


def produce_run_proposals(run_id: str, db: Session) -> list[ProposedMutation]:
    """Called once, after the run closes (any terminal status) — a run is
    the unit of analysis; per-beat analysis would multiply model calls by
    30 for no gain at this stage. Every returned proposal is retagged
    OBSERVED_PROPOSED_BY and linked via observation_mutation_link — the
    canon proposed_mutation row itself is never altered beyond that tag."""
    run = db.get(ObservationRun, run_id)
    if run is None:
        return []
    beats = _prior_beats(run_id, db)
    transcript = _analysis_transcript(beats)
    if not transcript.strip():
        return []

    mutations: list[ProposedMutation] = []
    try:
        window_result = analyze_transcript(
            transcript=transcript,
            world_id=run.world_id,
            injected_context="(scène observée — aucun contexte de conversation)",
            covered_keys=set(),
            attribution=AttributionContext(default_subject_id=None, default_counterparty_id=None),
            db=db,
            model=run.model,
            host=ollama_client.OLLAMA_HOST,
        )
        mutations.extend(window_result.mutations)
    except llm_parse.LlmParseError:
        _log.warning("produce_run_proposals: window pass parse failure for run %r", run_id)

    present_ids = _present_npc_ids(run.location_id, db)
    proposed_keys: set = set()
    proposed_change_keys: set = set()
    for beat in beats:
        if beat.outcome != "acted" or not beat.line:
            continue
        receivers = set(present_ids) - {beat.actor_id}
        if not receivers:
            continue
        over_result = analyze_overheard_lines(
            speaker_line=beat.line,
            listener_line=beat.line,
            receiver_ids=receivers,
            world_id=run.world_id,
            location_id=run.location_id,
            existing_keys=(proposed_keys, proposed_change_keys),
            attribution=AttributionContext(default_subject_id=beat.actor_id, default_counterparty_id=None),
            db=db,
            model=run.model,
            host=ollama_client.OLLAMA_HOST,
        )
        mutations.extend(over_result.mutations)

    if not mutations:
        return []
    return _persist_and_link(run_id, mutations, db)


def _produce_proposals_quietly(run_id: str, db: Session) -> None:
    """F3 must never undo a run's terminal closure — any analysis failure
    is logged, never raised past this point."""
    try:
        produce_run_proposals(run_id, db)
    except Exception:
        _log.exception("produce_run_proposals failed for run %r — run stays closed", run_id)
