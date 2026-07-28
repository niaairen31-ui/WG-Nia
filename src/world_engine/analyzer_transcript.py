"""Conversation-agnostic analysis core (TICKET-0051, BRIEF-0051-c).

Extracted from analyzer.py so that a played scene and an OBSERVED scene are
judged by the same code. The caller supplies the transcript and the receiver
set; this module never resolves a Conversation, never reads
ConversationMessage, never advances last_analyzed_turn, and never commits.
It returns un-persisted ProposedMutation objects.

Rationale for the seam: an observed run writes no conversation rows at all
(TICKET-0051 decision A3), so it cannot pass a conversation_id. Duplicating
the judge instead would let the observed path and the played path drift, and
observation exists precisely to draw conclusions about the played path.

# Transcript format contract (AMENDMENT 03, Correction 2)
`analyze_transcript` takes an ALREADY-BUILT `transcript: str` — building it
is the caller's job, kept caller-side so ConversationMessage never has to
enter this module. Two callers now produce this string independently
(`analyzer.py`'s `_window_build_transcript`, and BRIEF-0051-e's future
observed-run caller), so the exact format is a contract, not a convention:
one line per turn, in order, `"\\n"`-joined, each line
`f"[{'JOUEUR' if <player line> else 'PNJ'}] {content}"` — the French labels
so the model's French analysis aligns with the transcript. Both callers MUST
produce this format identically; a caller that deviates changes what the
model sees, not just where the string came from.

# Identity attribution contract (AMENDMENT 01/03)
Both public functions take an `AttributionContext`: participant identities a
payload builder may fall back on when the model's own output doesn't name
them. A None field means NO default is available — it does NOT mean "pick
something reasonable". An item that needs a missing default is DROPPED and
counted (`TranscriptAnalysis.dropped_unattributed` /
`.dropped_by_type`), never attributed by guess. A played scene supplies both
identities (the conversation's NPC and player); an observed scene supplies
neither, because a multi-NPC run has no run-level counterparty — beat 12 may
be Maelis addressing Reike, beat 19 Senna addressing Maelis.

# proposed_mutation provenance columns are the caller's job
`conversation_id` (a `ProposedMutation` column) is never set here — it is
always None on a returned mutation. The wrapper (`analyzer.analyze_window` /
`analyzer.analyze_overhearing`) sets it on every returned mutation before
persisting. This is not an oversight: `conversation_id` was a duplicate of
information this module has no business holding an opinion about (a
conversation is a caller concept), and AMENDMENT 02 removed the same
duplicate from `payload["source"]` for the identical reason — that field now
reads `f"overheard:{speaker_id}"` (no conversation id segment) for rows
written from schema v1.90 onward; older rows keep the pre-BRIEF-0051-c
`f"overheard:{conversation_id}:{speaker_id}"` format (history is append-only,
never migrated).
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .models import Character, Entity, Knowledge, ProposedMutation, PromptTemplate
from .prompt_registry import effective_model
from .prompt_store import current_prompt
from .writes import knowledge_level_rank

_log = logging.getLogger(__name__)

# Canonical mutation_type values (schema).
VALID_MUTATION_TYPES = frozenset(
    {
        "relation_change",
        "new_knowledge",
        "knowledge_change",
        "event_creation",
        "status_change",
        "entity_creation",
        "resource_change",
        "goal_change",
        "other",
    }
)

# Plausible target_table values (sanity filter, not exhaustive).
VALID_TARGET_TABLES = frozenset(
    {
        "relation",
        "knowledge",
        "event",
        "entity",
        "character",
        "location",
        "faction",
        "artifact",
        "ledger",
        "npc_goal",
        "other",
    }
)

# Maps model's natural type values → our mutation_type enum.
_MUTATION_TYPE_MAP: dict[str, str] = {
    "knowledge": "new_knowledge",
    "gain_knowledge": "new_knowledge",
    "acquire_knowledge": "new_knowledge",
    "new_knowledge": "new_knowledge",
    "knowledge_change": "knowledge_change",
    "update_knowledge": "knowledge_change",
    "relation": "relation_change",
    "relation_change": "relation_change",
    "trust": "relation_change",
    "relation_update": "relation_change",
    "event": "event_creation",
    "event_creation": "event_creation",
    "status": "status_change",
    "status_change": "status_change",
    "resource_change": "resource_change",
    "payment": "resource_change",
    "purchase": "resource_change",
    "transaction": "resource_change",
    "achat": "resource_change",
    "vente": "resource_change",
    "observation": "new_knowledge",   # reclassify model's "observations" as knowledge
    "rumeur": "new_knowledge",
    "rumor": "new_knowledge",
    "location": "status_change",
    "goal": "goal_change",
    "goal_change": "goal_change",
    "goal_update": "goal_change",
    "objective": "goal_change",
    "objective_change": "goal_change",
    "goal_completed": "goal_change",
    "new_goal": "goal_change",
}

# Maps mutation_type → likely target_table.
_TARGET_TABLE_MAP: dict[str, str] = {
    "relation_change": "relation",
    "new_knowledge": "knowledge",
    "knowledge_change": "knowledge",
    "event_creation": "event",
    "status_change": "entity",
    "entity_creation": "entity",
    "resource_change": "ledger",
    "goal_change": "npc_goal",
}

# Maps the model's natural goal-action wording (TICKET-0013, BRIEF-0013-c) ->
# our canonical action enum. Anything else is unrecognised — the item is
# dropped (better un-applied than wrongly applied).
_GOAL_ACTION_MAP: dict[str, str] = {
    "complete": "complete",
    "completed": "complete",
    "done": "complete",
    "accompli": "complete",
    "abandon": "abandon",
    "abandoned": "abandon",
    "given_up": "abandon",
    "abandonné": "abandon",
    "new": "create_short",
    "create": "create_short",
    "new_short": "create_short",
    "create_short": "create_short",
}

# knowledge.level ladder (schema): unaware < rumor < suspicious < partial <
# knows < fully_understands. The overhearing pass computes the acquired
# level one step below the speaker's, floored at 'rumor'.
_KNOWLEDGE_LEVEL_DOWNGRADE: dict[str, str] = {
    "fully_understands": "knows",
    "knows": "partial",
    "partial": "suspicious",
    "suspicious": "rumor",
    "rumor": "rumor",
    "unaware": "rumor",
}

# Strips non-word chars for subject slugs.
_SLUG_NON_WORD = re.compile(r"[^\w]")

# Sentinel distinguishing "key absent from the model's item" from "key
# present with a falsy value" — needed to know whether a field fell through
# to an AttributionContext default (see _build_payload_relation_change /
# _build_payload_resource_change).
_UNSET = object()


@dataclass(frozen=True)
class AttributionContext:
    """Participant identities a payload builder may fall back on.

    A None field means NO default is available for this transcript. It does
    NOT mean "pick something reasonable": an item that needs a missing
    default is DROPPED and counted, never attributed by guess. Played scenes
    supply both fields (the conversation's NPC and player); observed scenes
    supply neither, because a multi-NPC run has no run-level counterparty --
    beat 12 and beat 19 may involve different pairs entirely.
    """

    default_subject_id: str | None
    default_counterparty_id: str | None


@dataclass(frozen=True)
class TranscriptAnalysis:
    mutations: list[ProposedMutation]      # un-persisted
    dropped_unattributed: int
    dropped_by_type: dict[str, int] = field(default_factory=dict)


def load_analysis_prompt(
    db: Session,
    world_id: str | None = None,
    usage: str = "conversation_analysis",
) -> PromptTemplate:
    """Return the active template for `usage`, preferring world-specific.

    Exits with a clear message if none is found (mirrors load_npc_dialogue_prompt
    in talk.py for consistent error UX).
    """
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == usage,
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        _log.error(
            "No active %r prompt template found. Seed it first: python scripts/seed_pilot.py",
            usage,
        )
        sys.exit(1)
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _content_to_subject_slug(content: str) -> str:
    """Derive a short DB-friendly subject slug from free-text content."""
    if not content:
        return "unknown"
    words = content.lower().split()[:5]
    parts = [_SLUG_NON_WORD.sub("", w) for w in words if w]
    return ("_".join(p for p in parts if p))[:50] or "unknown"


def _first_of(item: dict, *keys: str, default: Any = None) -> Any:
    """Return the value of the first key found in item."""
    for k in keys:
        if k in item:
            return item[k]
    return default


def _resolve_player_id(db: Session, world_id: str) -> str | None:
    """Resolve the active world's player character id (character_type='player')."""
    char = db.exec(
        select(Character)
        .join(Entity, Entity.id == Character.id)
        .where(Entity.world_id == world_id, Character.character_type == "player")
    ).first()
    return char.id if char else None


def _normalize_mutation_type(item: dict) -> None:
    """mutation_type / target_table / target_id, in place."""
    if "mutation_type" not in item:
        for alias in ("type", "action", "kind", "change_type", "mutation"):
            if alias in item:
                item["mutation_type"] = item.pop(alias)
                break
    raw_mt = str(item.get("mutation_type") or "").lower()
    item["mutation_type"] = _MUTATION_TYPE_MAP.get(raw_mt, "other")
    if "target_table" not in item:
        item["target_table"] = _TARGET_TABLE_MAP.get(item["mutation_type"], "other")
    if "target_id" not in item:
        item["target_id"] = item.get("id") or None


def _build_payload_new_knowledge(
    item: dict, content: str, world_id: str, attribution: AttributionContext, db: Session,
) -> tuple[dict, bool]:
    # Infer who learned this from "subject"/"entity" field.
    subj = str(_first_of(item, "subject", "entity", default="")).lower()
    resolved_player_id = _resolve_player_id(db, world_id)
    player_hints = {"player", "joueur", attribution.default_counterparty_id, resolved_player_id} - {None}
    if not subj or any(h in subj for h in player_hints):
        entity_id = attribution.default_counterparty_id
    else:
        entity_id = attribution.default_subject_id
    payload = {
        "entity_id": entity_id,
        "subject": _content_to_subject_slug(content),
        "level": item.get("level") or "rumor",
        "content": content,
        "source": "conversation",
    }
    return payload, entity_id is None


def _build_payload_relation_change(item: dict, attribution: AttributionContext) -> tuple[dict, bool]:
    raw_b = _first_of(item, "entity_b_id", "entity_b", "to", default=_UNSET)
    unattributed = raw_b is _UNSET and attribution.default_counterparty_id is None
    entity_b_id = attribution.default_counterparty_id if raw_b is _UNSET else raw_b
    payload = {
        "entity_a_id": _first_of(item, "entity_a_id", "entity_a", "from", default=None),
        "entity_b_id": entity_b_id,
        "relation_type": _first_of(item, "relation_type", "relation", default="passive_attention"),
        "intensity_delta": int(_first_of(item, "intensity_delta", "delta", default=5)),
    }
    return payload, unattributed


def _build_payload_event_creation(
    item: dict, content: str, attribution: AttributionContext,
) -> tuple[dict, bool]:
    unattributed = attribution.default_counterparty_id is None or attribution.default_subject_id is None
    payload = {
        "title": item.get("title") or content[:60] or "Event",
        "description": content,
        "type": item.get("event_type") or "social",
        "involved_entities": [attribution.default_counterparty_id, attribution.default_subject_id],
    }
    return payload, unattributed


def _build_payload_resource_change(
    item: dict, content: str, attribution: AttributionContext,
) -> tuple[dict, bool]:
    # A1: the money leg always targets the player this step.
    raw_entity = _first_of(item, "entity_id", "entity", default=None)
    entity_id = raw_entity or attribution.default_counterparty_id
    raw_amount = _first_of(item, "amount", "montant", "price", "delta", "value", default=None)
    try:
        amount = int(raw_amount) if raw_amount is not None else None
    except (TypeError, ValueError):
        amount = None
    raw_counterparty = _first_of(
        item, "counterparty_id", "counterparty", "npc_id", "with", default=_UNSET,
    )
    counterparty_id = attribution.default_subject_id if raw_counterparty is _UNSET else raw_counterparty
    unattributed = (
        (not raw_entity and attribution.default_counterparty_id is None)
        or (raw_counterparty is _UNSET and attribution.default_subject_id is None)
    )
    reason = str(_first_of(item, "reason", "raison", "description", default=content) or "")
    resource_payload: dict = {
        "entity_id": entity_id,
        "amount": amount,
        "counterparty_id": counterparty_id,
        "reason": reason,
    }
    raw_knowledge = item.get("knowledge")
    if isinstance(raw_knowledge, dict):
        k_content = str(raw_knowledge.get("content") or "")
        resource_payload["knowledge"] = {
            "entity_id": raw_knowledge.get("entity_id") or entity_id,
            "subject": raw_knowledge.get("subject") or _content_to_subject_slug(k_content),
            "level": raw_knowledge.get("level") or "rumor",
            "content": k_content,
            "source": raw_knowledge.get("source") or "conversation",
            "is_secret": bool(raw_knowledge.get("is_secret", False)),
        }
    return resource_payload, unattributed


def _build_payload_generic(raw_item: dict) -> dict:
    # Generic fallback: collect any leftover fields as payload.
    skip = {
        "mutation_type", "target_table", "target_id", "rationale",
        "type", "action", "kind", "subject", "entity",
    }
    return {k: v for k, v in raw_item.items() if k not in skip}


def _build_payload(
    item: dict, raw_item: dict, world_id: str, attribution: AttributionContext, db: Session,
) -> tuple[dict, bool]:
    mt = item["mutation_type"]
    content = str(_first_of(item, "content", "details", "value", "description", default=""))
    if mt == "new_knowledge":
        return _build_payload_new_knowledge(item, content, world_id, attribution, db)
    if mt == "relation_change":
        return _build_payload_relation_change(item, attribution)
    if mt == "event_creation":
        return _build_payload_event_creation(item, content, attribution)
    if mt == "resource_change":
        return _build_payload_resource_change(item, content, attribution)
    return _build_payload_generic(raw_item), False


def _guard_relation_change(item: dict) -> dict | None:
    # relation_change with an unresolved entity_a_id/entity_b_id is dropped
    # rather than attributed to a window-level default: in a multi-NPC
    # gathering window, "the last NPC who spoke" is not necessarily the
    # entity the model meant. A silent wrong attribution is worse than a
    # dropped proposal — history is sacred. (Also the path a None
    # AttributionContext.default_counterparty_id falls through to.)
    payload = item["payload"]
    if not payload.get("entity_a_id") or not payload.get("entity_b_id"):
        return None
    return item


def _guard_resource_change(item: dict) -> dict | None:
    # resource_change with an unresolved entity_id (the player) or a
    # non-numeric amount is dropped rather than guessed at — same discipline
    # as the relation_change attribution rule above (BRIEF-19).
    payload = item["payload"]
    if not payload.get("entity_id") or not isinstance(payload.get("amount"), int):
        return None
    return item


def _guard_goal_change(item: dict, attribution: AttributionContext) -> tuple[dict | None, bool]:
    # goal_change (TICKET-0013, BRIEF-0013-c, H1/O1): npc_id is FORCED here,
    # in code — structural, not instructional. The model's input only ever
    # contains ONE NPC's TES OBJECTIFS, so it never chooses the target NPC,
    # and no horizon field is ever read (O1: the model cannot create or
    # re-horizon a long-term goal by any input). Runs unconditionally so a
    # fake npc_id/horizon in the model's own payload is always overwritten,
    # never trusted. action is coerced through _GOAL_ACTION_MAP; an
    # unrecognised action or empty goal text drops the item (better
    # un-applied than wrongly applied) — that drop is NOT an attribution
    # failure. Only a missing default_subject_id, with an otherwise-valid
    # action/goal, counts as unattributed.
    payload_in = item["payload"] if isinstance(item["payload"], dict) else {}
    raw_action = str(
        _first_of(payload_in, "action", "kind", default="")
        or _first_of(item, "action", "kind", default="")
    ).strip().lower()
    action = _GOAL_ACTION_MAP.get(raw_action)
    goal_text = str(
        _first_of(payload_in, "goal", "description", "content", default="")
        or _first_of(item, "goal", "description", "content", default="")
    ).strip()
    if action is None or not goal_text:
        return None, False
    if attribution.default_subject_id is None:
        return None, True
    payload: dict = {}
    payload["npc_id"] = attribution.default_subject_id
    payload["action"] = action
    payload["goal"] = goal_text
    item["payload"] = payload
    return item, False


def _apply_type_guards(item: dict, attribution: AttributionContext) -> tuple[dict | None, bool]:
    """Type-specific fail-closed guards, run after payload construction.
    Returns (item-or-None, unattributed). Order and rejection semantics
    frozen: every rejection path rejects identically to the
    pre-decomposition code."""
    mt = item["mutation_type"]
    if mt == "relation_change":
        return _guard_relation_change(item), False
    if mt == "resource_change":
        return _guard_resource_change(item), False
    if mt == "goal_change":
        return _guard_goal_change(item, attribution)
    return item, False


def _normalize_to_schema(
    raw_item: Any,
    world_id: str,
    attribution: AttributionContext,
    db: Session,
) -> tuple[dict | None, bool, str]:
    """Map a model's natural output object to our ProposedMutation schema fields.

    Returns (item-or-None, unattributed, mutation_type). unattributed is
    True only when the drop is specifically because an AttributionContext
    field needed by this item's mutation_type was None — never for a
    generic model-data problem (bad JSON shape, unresolvable mutation_type,
    missing entity_a_id, malformed goal action). mutation_type is always
    populated (even when the item is dropped) so the caller can bucket
    dropped_by_type without re-deriving it.
    """
    if not isinstance(raw_item, dict):
        return None, False, "other"
    item = dict(raw_item)

    _normalize_mutation_type(item)
    mt = item["mutation_type"]

    unattributed = False
    if not isinstance(item.get("payload"), dict):
        item["payload"], unattributed = _build_payload(item, raw_item, world_id, attribution, db)
    if not item.get("payload"):
        return None, unattributed, mt

    item, guard_unattributed = _apply_type_guards(item, attribution)
    unattributed = unattributed or guard_unattributed
    if item is None:
        return None, unattributed, mt

    if not item.get("rationale"):
        item["rationale"] = str(
            _first_of(
                item, "rationale", "reason", "details", "content", "value",
                default="",
            )
        )

    return item, unattributed, mt


def _validate_item(item: Any) -> str | None:
    """Return an error description if the item still fails validation, else None."""
    if not isinstance(item, dict):
        return "not a dict"
    mt = item.get("mutation_type")
    if mt not in VALID_MUTATION_TYPES:
        return f"unresolvable mutation_type {mt!r}"
    tt = item.get("target_table")
    if tt is not None and tt not in VALID_TARGET_TABLES:
        return f"unknown target_table {tt!r}"
    if not isinstance(item.get("payload"), dict):
        return "payload missing or not a dict"
    return None


def _mutation_match_key(mutation_type: str, payload: dict):
    """Return a hashable match key for write-time deduplication, or None.

    Used by the window path to avoid re-proposing an idempotent fact the
    overhearing pass already flagged (as a 'proposed' row) for the same
    window. Only idempotent mutation types are keyed here — applying the same
    idempotent fact twice is wrong; accumulating deltas (relation_change,
    and resource_change's money leg — BRIEF-19) are never deduplicated here.
    resource_change's knowledge leg is idempotent too, but that guard lives
    in `_apply_mutation` at apply time (4c), not here at propose time.
    """
    if mutation_type == "new_knowledge":
        return ("new_knowledge", payload.get("entity_id"), payload.get("subject"))
    if mutation_type == "status_change":
        eid = payload.get("entity_id")
        return ("status_change", eid) if eid else None
    return None


def _window_call_model(
    db: Session, world_id: str, transcript: str, injected_ctx_str: str,
    model: str, host: str,
) -> list:
    """Model call + JSON parse. Raises llm_parse.LlmParseError (logged here
    with the raw snippet) on a parse failure — analyze_transcript does not
    catch it; analyze_window's wrapper does, to skip marker advancement so
    the next trigger retries the same turns."""
    template = load_analysis_prompt(db, world_id=world_id)
    version = current_prompt(db, template)

    # str.replace instead of .format() so transcript/context JSON (which
    # contain { and }) are inserted verbatim without escaping issues.
    user_message = (
        version.user_template
        .replace("{transcript}", transcript)
        .replace("{injected_context}", injected_ctx_str)
    )
    llm_messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]

    _log.info("Analysis in progress...")
    # format="json" constrains Ollama to valid JSON syntax (≥ 0.1.x).
    # The normalizer below then maps the model's field names to our schema.
    raw = ollama_client.chat(
        llm_messages, model=effective_model(template, model), host=host, format="json"
    )
    try:
        return llm_parse.extract_array(raw)
    except llm_parse.LlmParseError as exc:
        _log.warning(
            "Model output is not valid JSON (%s). Raw snippet: %r", exc, raw[:400]
        )
        raise


def _window_build_mutations(
    items: list, world_id: str, attribution: AttributionContext, db: Session, covered: set,
) -> tuple[list[ProposedMutation], int, dict[str, int]]:
    now = datetime.now(UTC)
    mutations: list[ProposedMutation] = []
    dropped_unattributed = 0
    dropped_by_type: dict[str, int] = {}
    for i, raw_item in enumerate(items):
        normalized, unattributed, mt = _normalize_to_schema(raw_item, world_id, attribution, db)
        if normalized is None:
            if unattributed:
                dropped_unattributed += 1
                dropped_by_type[mt] = dropped_by_type.get(mt, 0) + 1
            _log.warning("[skip] Item %d: normalization failed — %r", i, raw_item)
            continue
        err = _validate_item(normalized)
        if err:
            _log.warning("[skip] Item %d: %s — %r", i, err, normalized)
            continue

        key = _mutation_match_key(normalized["mutation_type"], normalized["payload"])
        if key is not None:
            if key in covered:
                _log.warning("[skip] Item %d: already proposed this window — %r", i, key)
                continue
            covered.add(key)

        mutations.append(
            ProposedMutation(
                world_id=world_id,
                source_type="conversation",
                pass_play_id=None,
                mutation_type=normalized["mutation_type"],
                target_table=normalized.get("target_table"),
                target_id=normalized.get("target_id"),
                payload=normalized["payload"],
                status="proposed",
                rationale=normalized.get("rationale"),
                proposed_by="local_ai_window",
                proposed_at=now,
            )
        )
    return mutations, dropped_unattributed, dropped_by_type


def analyze_transcript(
    transcript: str,
    world_id: str,
    injected_context: str,
    covered_keys: set,
    attribution: AttributionContext,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
) -> TranscriptAnalysis:
    """Judge an ordered transcript and return UN-PERSISTED proposals.

    Raises llm_parse.LlmParseError on a model-output parse failure — the
    caller decides what "failure" means for its own marker/commit semantics.
    """
    items = _window_call_model(db, world_id, transcript, injected_context, model, host)
    mutations, dropped_unattributed, dropped_by_type = _window_build_mutations(
        items, world_id, attribution, db, covered_keys,
    )
    return TranscriptAnalysis(
        mutations=mutations,
        dropped_unattributed=dropped_unattributed,
        dropped_by_type=dropped_by_type,
    )


def _overhearing_subject_set(world_id: str, db: Session) -> set[str]:
    """c. Subject list — closed list, scoped to the world."""
    subjects = db.exec(
        select(Knowledge.subject)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .where(Entity.world_id == world_id)
        .distinct()
    ).all()
    return set(subjects)


def _overhearing_classify(
    db: Session, world_id: str, speaker_line: str, listener_line: str,
    subject_set: set[str], model: str, host: str,
) -> list | None:
    """d. Model call."""
    template = load_analysis_prompt(
        db, world_id=world_id, usage="overhearing_classification"
    )
    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{subject_list}", "\n".join(sorted(subject_set)))
        .replace("{player_line}", speaker_line)
        .replace("{npc_line}", listener_line)
    )
    llm_messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]
    raw = ollama_client.chat(
        llm_messages, model=effective_model(template, model), host=host, format="json"
    )
    return llm_parse.extract_array_or_none(raw)


def _overhearing_parse_classifications(items: list, subject_set: set[str]) -> list[tuple[str, str]]:
    """e. Normalization — exact closed-list match only, no fuzzy matching."""
    classified: list[tuple[str, str]] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            _log.warning("[overhearing] dropped non-dict element: %r", raw_item)
            continue
        subject = raw_item.get("subject")
        speaker = raw_item.get("speaker")
        if subject not in subject_set:
            _log.warning("[overhearing] dropped unknown subject: %r", subject)
            continue
        if speaker not in ("player", "npc"):
            _log.warning("[overhearing] dropped invalid speaker: %r", speaker)
            continue
        classified.append((subject, speaker))
    return classified


def _resolve_location_name(db: Session, location_id: str | None) -> str:
    location = db.get(Entity, location_id) if location_id else None
    return location.name if location else "?"


def _overhearing_mutation_for_receiver(
    receiver_id: str, subject: str, speaker_id: str, speaker_row: Knowledge,
    acquired_level: str, world_id: str, db: Session,
    proposed_keys: set, proposed_change_keys: set, location_name: str,
    name_fn, now: datetime,
) -> Optional[ProposedMutation]:
    """j/k/l for one (subject, receiver) pair — acquisition or monotone
    upgrade, proposal-deduped, or None (skipped silently, no queue noise)."""
    existing_row = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == receiver_id,
            Knowledge.subject == subject,
        )
    ).first()

    if existing_row is not None:
        if knowledge_level_rank(acquired_level) <= knowledge_level_rank(existing_row.level):
            return None
        change_key = (receiver_id, subject)
        if change_key in proposed_change_keys:
            return None
        proposed_change_keys.add(change_key)
        return ProposedMutation(
            world_id=world_id,
            source_type="conversation",
            pass_play_id=None,
            mutation_type="knowledge_change",
            target_table="knowledge",
            target_id=None,
            payload={
                "entity_id": receiver_id,
                "subject": subject,
                "from_level": existing_row.level,
                "to_level": acquired_level,
                "source": f"overheard:{speaker_id}",
            },
            status="proposed",
            rationale=(
                f"Overheard from {name_fn(speaker_id)} at {location_name} "
                f"({existing_row.level} → {acquired_level})"
            ),
            proposed_by="local_ai_overhearing",
            proposed_at=now,
        )

    key = (receiver_id, subject)
    if key in proposed_keys:
        return None
    proposed_keys.add(key)

    return ProposedMutation(
        world_id=world_id,
        source_type="conversation",
        pass_play_id=None,
        mutation_type="new_knowledge",
        target_table="knowledge",
        target_id=None,
        payload={
            "entity_id": receiver_id,
            "subject": subject,
            "level": acquired_level,
            "content": speaker_row.content,
            "is_incorrect": speaker_row.is_incorrect,
            "source": f"overheard:{speaker_id}",
        },
        status="proposed",
        rationale=(
            f"Overheard from {name_fn(speaker_id)} at {location_name} "
            f"(level {speaker_row.level} → {acquired_level})"
        ),
        proposed_by="local_ai_overhearing",
        proposed_at=now,
    )


def _overhearing_build_mutations(
    classified: list[tuple[str, str]],
    receiver_ids: set[str],
    attribution: AttributionContext,
    world_id: str,
    location_name: str,
    db: Session,
    proposed_keys: set,
    proposed_change_keys: set,
) -> tuple[list[ProposedMutation], int, dict[str, int]]:
    entity_names: dict[str, str] = {}

    def _name(entity_id: str) -> str:
        if entity_id not in entity_names:
            ent = db.get(Entity, entity_id)
            entity_names[entity_id] = ent.name if ent else entity_id
        return entity_names[entity_id]

    now = datetime.now(UTC)
    mutations: list[ProposedMutation] = []
    dropped_unattributed = 0
    dropped_by_type: dict[str, int] = {}
    for subject, speaker in classified:
        # f. Speaker resolution via the refusable identity contract — an
        # NPC never overhears itself, and a "player spoke" classification
        # with no player in this transcript (an observed run) is a model
        # error, never guessed onto some NPC.
        speaker_id = attribution.default_subject_id if speaker == "npc" else attribution.default_counterparty_id
        if not speaker_id:
            dropped_unattributed += 1
            # The would-be type (new_knowledge vs knowledge_change) is only
            # determinable per-receiver, after resolving speaker_id — which
            # is exactly what's missing. Bucketed generically; this key is
            # not a real ProposedMutation.mutation_type value.
            dropped_by_type["overhearing"] = dropped_by_type.get("overhearing", 0) + 1
            continue

        receivers = receiver_ids - {speaker_id}
        if not receivers:
            continue

        # g. K2 guard (source authority) — the speaker's row is the only
        # authority; a speaker "knowing" without a row is model noise.
        speaker_row = db.exec(
            select(Knowledge).where(
                Knowledge.entity_id == speaker_id,
                Knowledge.subject == subject,
            )
        ).first()
        if speaker_row is None:
            continue

        # h. Secret guard — secrets are structurally excluded from NPC
        # context, so a match on one is spurious by definition.
        if speaker_row.is_secret:
            continue

        # i. Level computation (deterministic, floored at 'rumor').
        acquired_level = _KNOWLEDGE_LEVEL_DOWNGRADE.get(speaker_row.level, "rumor")

        for receiver_id in receivers:
            mutation = _overhearing_mutation_for_receiver(
                receiver_id, subject, speaker_id, speaker_row, acquired_level,
                world_id, db, proposed_keys, proposed_change_keys,
                location_name, _name, now,
            )
            if mutation is not None:
                mutations.append(mutation)

    return mutations, dropped_unattributed, dropped_by_type


def analyze_overheard_lines(
    speaker_line: str,
    listener_line: str,
    receiver_ids: set[str],
    world_id: str,
    location_id: str | None,
    existing_keys: tuple[set, set],
    attribution: AttributionContext,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
) -> TranscriptAnalysis:
    """Bystander knowledge pass over an EXPLICIT receiver set.

    Returns [] (empty TranscriptAnalysis) on any failure or when nothing
    qualifies — failures must never surface to the player, and there is no
    marker here to protect, so unlike analyze_transcript this never raises.
    """
    if not receiver_ids:
        return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})

    subject_set = _overhearing_subject_set(world_id, db)
    if not subject_set:
        return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})

    items = _overhearing_classify(db, world_id, speaker_line, listener_line, subject_set, model, host)
    if items is None:
        return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})

    classified = _overhearing_parse_classifications(items, subject_set)
    if not classified:
        return TranscriptAnalysis(mutations=[], dropped_unattributed=0, dropped_by_type={})

    proposed_keys, proposed_change_keys = existing_keys
    location_name = _resolve_location_name(db, location_id)

    mutations, dropped_unattributed, dropped_by_type = _overhearing_build_mutations(
        classified, receiver_ids, attribution, world_id, location_name, db,
        proposed_keys, proposed_change_keys,
    )
    return TranscriptAnalysis(
        mutations=mutations,
        dropped_unattributed=dropped_unattributed,
        dropped_by_type=dropped_by_type,
    )
