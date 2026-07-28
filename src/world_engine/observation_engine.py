"""Per-NPC intent request and pure code-side arbitration for observed
scenes (TICKET-0051, BRIEF-0051-d).

Two responsibilities, kept deliberately separate:

- `request_intent` — one short JSON call PER present NPC, per beat. The
  model answers ONLY for itself: it never ranks, never sees a rival's
  intent, and never emits an entity id (only a name, resolved here against
  the audience roster it was shown).
- `arbitrate` — pure, no I/O, no model. Every selection input is a number
  computed in Python: propensity (D1/O1), cooldown (D2), speaking debt
  (D3). No RNG (D4 not taken).

This is the mechanism only. Beat sequencing, persistence into
`observation_*` tables, and the readiness gate belong to BRIEF-0051-e —
this module writes nothing and imports no observation model.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .context import assemble_npc_context
from .models import Entity, PromptTemplate
from .prompt_store import current_prompt

NEUTRAL_INTENSITY = 50
# O1: relation_weighted's multiplier is capped at 1.5 — k=0.5 is that cap,
# since abs(intensity - 50) / 50 already ranges [0, 1].
_RELATION_WEIGHTED_K = 0.5


@dataclass
class IntentResult:
    act: bool
    urgency: int | None
    target_id: str | None
    why: str | None
    call_status: str  # 'ok' | 'parse_error' | 'timeout' | 'error'
    latency_ms: int
    raw_response: str


@dataclass
class CandidateScore:
    npc_id: str
    propensity: float
    cooldown_active: bool
    debt_score: float
    final_score: float
    selected: bool


@dataclass
class ArbitrationResult:
    scores: list[CandidateScore]
    selected_npc_id: str | None


def _observation_intent_names(entity_ids: list[str], db: Session) -> dict[str, str]:
    """id -> name for every entity in `entity_ids` (a missing row is simply absent)."""
    if not entity_ids:
        return {}
    rows = db.exec(select(Entity).where(Entity.id.in_(entity_ids))).all()
    return {e.id: e.name for e in rows}


def _observation_resolve_target(name: str, names_by_id: dict[str, str]) -> str | None:
    """Exact, case-insensitive match against the roster the model was shown.
    Empty or unresolved -> None. The model never emits an id directly."""
    name = name.strip()
    if not name:
        return None
    lowered = name.lower()
    for entity_id, entity_name in names_by_id.items():
        if entity_name.strip().lower() == lowered:
            return entity_id
    return None


def _observation_intent_messages(
    npc_id: str, interlocutor_id: str, rest_audience: list[str] | None,
    location_id: str, transcript: str, names_by_id: dict[str, str],
    template: PromptTemplate, db: Session,
) -> list[dict[str, str]]:
    """Assemble the system/user pair for one intent call. The disclosure
    floor sees the FULL audience (worst-case listener, BRIEF-0051-b) —
    which member plays `interlocutor_id` vs `rest_audience` doesn't affect
    it (context.py unions them back before computing the floor); it only
    picks who the cosmetic "how you see X" section describes."""
    npc_context = assemble_npc_context(
        npc_id, interlocutor_id, location_id, db, audience_ids=rest_audience,
    )
    location = db.get(Entity, location_id)
    location_name = location.name if location else location_id
    present_names = "\n".join(f"- {name}" for name in names_by_id.values())

    version = current_prompt(db, template)
    system_prompt = f"{version.system_prompt}\n\n{npc_context}"
    user_msg = (
        version.user_template
        .replace("{location_name}", location_name)
        .replace("{transcript}", transcript)
        .replace("{present_names}", present_names)
        + "\n/no_think"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]


def _observation_intent_call_status(exc: ollama_client.OllamaError) -> str:
    """`timeout` when the underlying failure was a socket timeout, `error`
    otherwise. `ollama_client.chat` collapses every network failure into
    `OllamaError`; the distinction is recovered from the wrapped cause
    (`raise ... from exc` in ollama_client.py)."""
    return "timeout" if isinstance(exc.__cause__, TimeoutError) else "error"


def _observation_parse_intent(raw: str, names_by_id: dict[str, str], latency_ms: int) -> IntentResult:
    """Turn a successful call's raw text into an IntentResult. A parse
    failure is a recorded `parse_error`, never an implicit decline (this is
    the defect play_initiative.py:508-510 collapses today)."""
    try:
        obj = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError:
        return IntentResult(
            act=False, urgency=None, target_id=None, why=None,
            call_status="parse_error", latency_ms=latency_ms, raw_response=raw,
        )

    if not obj.get("act"):
        return IntentResult(
            act=False, urgency=None, target_id=None, why=None,
            call_status="ok", latency_ms=latency_ms, raw_response=raw,
        )

    try:
        urgency = max(0, min(100, int(obj.get("urgency", 0))))
    except (TypeError, ValueError):
        urgency = 0
    target_id = _observation_resolve_target(str(obj.get("target", "")), names_by_id)
    why = str(obj.get("why") or "").strip() or None
    return IntentResult(
        act=True, urgency=urgency, target_id=target_id, why=why,
        call_status="ok", latency_ms=latency_ms, raw_response=raw,
    )


def request_intent(
    npc_id: str,
    audience_ids: list[str],
    transcript: str,
    location_id: str,
    template: PromptTemplate,
    db: Session,
    model: str,
    host: str,
) -> IntentResult:
    """One JSON intent call for `npc_id`: does it want to act on this beat,
    and how urgently. `audience_ids` is every OTHER present entity (NPCs
    and, if not absent, the player) — the correctly floored disclosure set
    reaches the prompt via `assemble_npc_context`, never the addressee alone.
    """
    if not audience_ids:
        raise ValueError("audience_ids must not be empty — an intent call needs at least one other present entity")

    interlocutor_id, *rest = audience_ids
    names_by_id = _observation_intent_names(audience_ids, db)
    messages = _observation_intent_messages(
        npc_id, interlocutor_id, rest or None, location_id, transcript,
        names_by_id, template, db,
    )

    start = time.monotonic()
    try:
        raw = ollama_client.chat(messages, model=model, host=host, format="json")
    except ollama_client.OllamaError as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return IntentResult(
            act=False, urgency=None, target_id=None, why=None,
            call_status=_observation_intent_call_status(exc),
            latency_ms=latency_ms, raw_response=str(exc),
        )
    latency_ms = int((time.monotonic() - start) * 1000)

    return _observation_parse_intent(raw, names_by_id, latency_ms)


def _observation_propensity(
    npc_id: str, last_actor_id: str | None, propensity_mode: str,
    relation_intensities: dict[str, int] | None,
) -> float:
    """D1/O1: `flat` (default) never looks at relation intensity at all.
    `relation_weighted` reads `npc_id`'s intensity toward `last_actor_id`
    from the caller-supplied map (missing entries default to neutral)."""
    if propensity_mode != "relation_weighted" or last_actor_id is None:
        return 1.0
    intensity = (relation_intensities or {}).get(npc_id, NEUTRAL_INTENSITY)
    return 1.0 + _RELATION_WEIGHTED_K * (abs(intensity - NEUTRAL_INTENSITY) / NEUTRAL_INTENSITY)


def _observation_debt_score(
    npc_id: str, acted_counts: dict[str, int], beats_elapsed: int,
    npc_count: int, debt_weight: float,
) -> float:
    """D3: positive means under-served relative to an even split so far."""
    expected_share = beats_elapsed / npc_count
    actual_share = acted_counts.get(npc_id, 0)
    return debt_weight * (expected_share - actual_share)


def _observation_select(
    candidates: list[tuple[str, IntentResult, CandidateScore]],
    npc_ids: list[str],
    acted_counts: dict[str, int],
) -> str | None:
    """Highest `final_score` among acting candidates wins. A cooling
    candidate is excluded UNLESS every other candidate declined (D2, soft
    floor — never a hard drop that would produce a false `silence`). Ties
    break on lowest `acted_counts`, then stable `npc_ids` order. No RNG."""
    order = {npc_id: i for i, npc_id in enumerate(npc_ids)}

    def _rank_key(item: tuple[str, IntentResult, CandidateScore]) -> tuple:
        npc_id, _intent, score = item
        return (-score.final_score, acted_counts.get(npc_id, 0), order[npc_id])

    acting = [c for c in candidates if c[1].act]
    if not acting:
        return None
    fresh = [c for c in acting if not c[2].cooldown_active]
    pool = fresh if fresh else acting
    return min(pool, key=_rank_key)[0]


def arbitrate(
    intents: list[IntentResult],
    npc_ids: list[str],
    last_actor_id: str | None,
    acted_counts: dict[str, int],
    beats_elapsed: int,
    cooldown_beats: int,
    debt_weight: float,
    propensity_mode: str,
    *,
    beats_since_last_act: int = 1,
    relation_intensities: dict[str, int] | None = None,
) -> ArbitrationResult:
    """Pure, no I/O, no model. `intents[i]` is `npc_ids[i]`'s reported
    intent — parallel arrays, positionally matched.

    `beats_since_last_act` and `relation_intensities` complete two rules
    the ticket specifies (D2's cooldown window; O1's relation-weighted
    propensity) with data the call has nowhere else to carry. Both default
    to the single-beat / no-history case the Done-means criteria exercise,
    so a caller passing only the documented positional arguments reproduces
    the tested behavior exactly.

    Every candidate gets a full component row, including a declined one
    (`final_score=0.0`) and every candidate when nobody acted — arbitration
    is a first-class, reconstructible result, never an empty return.
    """
    if len(intents) != len(npc_ids):
        raise ValueError("intents and npc_ids must be parallel lists of equal length")

    scores: list[CandidateScore] = []
    for npc_id, intent in zip(npc_ids, intents):
        if not intent.act:
            scores.append(CandidateScore(npc_id, 0.0, False, 0.0, 0.0, False))
            continue
        cooldown_active = npc_id == last_actor_id and beats_since_last_act < cooldown_beats
        propensity = _observation_propensity(npc_id, last_actor_id, propensity_mode, relation_intensities)
        debt_score = _observation_debt_score(npc_id, acted_counts, beats_elapsed, len(npc_ids), debt_weight)
        final_score = (intent.urgency or 0) * propensity + debt_score
        scores.append(CandidateScore(npc_id, propensity, cooldown_active, debt_score, final_score, False))

    candidates = list(zip(npc_ids, intents, scores))
    selected_id = _observation_select(candidates, npc_ids, acted_counts)
    if selected_id is not None:
        for score in scores:
            if score.npc_id == selected_id:
                score.selected = True

    return ArbitrationResult(scores=scores, selected_npc_id=selected_id)
