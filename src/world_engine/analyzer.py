"""Conversation analysis — extract proposed mutations from unanalyzed turns.

analyze_window() reads the conversation's transcript window (turns since
conv.last_analyzed_turn), calls the local model with that window and the NPC's
injected_context snapshot (what the NPC was authorised to know), persists the
resulting ProposedMutation rows, and advances conv.last_analyzed_turn — all in
one transaction.

analyze_overhearing() (Tier 4, separate pass) is unaffected by the above: it
classifies a single turn against a closed subject list and proposes
acquisition/upgrade knowledge mutations for bystanders.

# Format note
Local 8b models reliably identify WHAT changed but consistently ignore exact
field-name requirements in prompts.  The analyser therefore uses a two-step
approach:
  1. Ask the model to output any JSON array describing the changes.
  2. _normalize_to_schema() maps the model's natural field names to ours and
     fills in required payload fields from conversation context.
  3. _validate_item() skips anything that still can't be salvaged.
This makes the system robust to the model's formatting habits while keeping
the change-detection logic in the prompt.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any, Optional

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .models import (
    Character,
    Conversation,
    ConversationMessage,
    Entity,
    GatheringMember,
    Knowledge,
    ProposedMutation,
    PromptTemplate,
)
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
# knows < fully_understands. analyze_overhearing computes the acquired level
# one step below the speaker's row level, floored at 'rumor'.
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


def _build_payload_new_knowledge(item: dict, content: str, conv: Conversation, db: Session) -> dict:
    # Infer who learned this from "subject"/"entity" field.
    subj = str(_first_of(item, "subject", "entity", default="")).lower()
    resolved_player_id = _resolve_player_id(db, conv.world_id)
    player_hints = {"player", "joueur", conv.player_id, resolved_player_id} - {None}
    entity_id = (
        conv.player_id if not subj or any(h in subj for h in player_hints)
        else conv.npc_id
    )
    return {
        "entity_id": entity_id,
        "subject": _content_to_subject_slug(content),
        "level": item.get("level") or "rumor",
        "content": content,
        "source": "conversation",
    }


def _build_payload_relation_change(item: dict, conv: Conversation) -> dict:
    return {
        "entity_a_id": _first_of(item, "entity_a_id", "entity_a", "from", default=None),
        "entity_b_id": _first_of(item, "entity_b_id", "entity_b", "to", default=conv.player_id),
        "relation_type": _first_of(item, "relation_type", "relation", default="passive_attention"),
        "intensity_delta": int(_first_of(item, "intensity_delta", "delta", default=5)),
    }


def _build_payload_event_creation(item: dict, content: str, conv: Conversation) -> dict:
    return {
        "title": item.get("title") or content[:60] or "Event",
        "description": content,
        "type": item.get("event_type") or "social",
        "involved_entities": [conv.player_id, conv.npc_id],
    }


def _build_payload_resource_change(item: dict, content: str, conv: Conversation) -> dict:
    # A1: the money leg always targets the player this step.
    entity_id = _first_of(item, "entity_id", "entity", default=None) or conv.player_id
    raw_amount = _first_of(item, "amount", "montant", "price", "delta", "value", default=None)
    try:
        amount = int(raw_amount) if raw_amount is not None else None
    except (TypeError, ValueError):
        amount = None
    counterparty_id = _first_of(
        item, "counterparty_id", "counterparty", "npc_id", "with", default=conv.npc_id,
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
    return resource_payload


def _build_payload_generic(raw_item: dict) -> dict:
    # Generic fallback: collect any leftover fields as payload.
    skip = {
        "mutation_type", "target_table", "target_id", "rationale",
        "type", "action", "kind", "subject", "entity",
    }
    return {k: v for k, v in raw_item.items() if k not in skip}


def _build_payload(item: dict, raw_item: dict, conv: Conversation, db: Session) -> dict:
    mt = item["mutation_type"]
    content = str(_first_of(item, "content", "details", "value", "description", default=""))
    if mt == "new_knowledge":
        return _build_payload_new_knowledge(item, content, conv, db)
    if mt == "relation_change":
        return _build_payload_relation_change(item, conv)
    if mt == "event_creation":
        return _build_payload_event_creation(item, content, conv)
    if mt == "resource_change":
        return _build_payload_resource_change(item, content, conv)
    return _build_payload_generic(raw_item)


def _guard_relation_change(item: dict) -> dict | None:
    # relation_change with an unresolved entity_a_id/entity_b_id is dropped
    # rather than attributed to a window-level default: in a multi-NPC
    # gathering window, "the last NPC who spoke" is not necessarily the
    # entity the model meant. A silent wrong attribution is worse than a
    # dropped proposal — history is sacred.
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


def _guard_goal_change(item: dict, conv: Conversation) -> dict | None:
    # goal_change (TICKET-0013, BRIEF-0013-c, H1/O1): npc_id is FORCED to
    # conv.npc_id here, in code — structural, not instructional. The model's
    # input only ever contains ONE NPC's TES OBJECTIFS, so it never chooses
    # the target NPC, and no horizon field is ever read (O1: the model
    # cannot create or re-horizon a long-term goal by any input). Runs
    # unconditionally so a fake npc_id/horizon in the model's own payload is
    # always overwritten, never trusted. action is coerced through
    # _GOAL_ACTION_MAP; an unrecognised action or empty goal text drops the
    # item (better un-applied than wrongly applied).
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
        return None
    item["payload"] = {"npc_id": conv.npc_id, "action": action, "goal": goal_text}
    return item


def _apply_type_guards(item: dict, conv: Conversation) -> dict | None:
    """Type-specific fail-closed guards, run after payload construction.
    Returns None to drop the item or the item (possibly mutated — goal_change
    forces its payload). Order and rejection semantics frozen: every
    rejection path rejects identically to the pre-decomposition code."""
    mt = item["mutation_type"]
    if mt == "relation_change":
        return _guard_relation_change(item)
    if mt == "resource_change":
        return _guard_resource_change(item)
    if mt == "goal_change":
        return _guard_goal_change(item, conv)
    return item


def _normalize_to_schema(
    raw_item: Any,
    conv: Conversation,
    db: Session,
) -> dict | None:
    """Map a model's natural output object to our ProposedMutation schema fields.

    Returns None when normalization cannot produce a usable item.
    The model reliably tells us what changed but uses its own field names.
    This function bridges the gap so we don't lose correct detections.
    """
    if not isinstance(raw_item, dict):
        return None
    item = dict(raw_item)

    _normalize_mutation_type(item)

    if not isinstance(item.get("payload"), dict):
        item["payload"] = _build_payload(item, raw_item, conv, db)
    if not item.get("payload"):
        return None

    item = _apply_type_guards(item, conv)
    if item is None:
        return None

    if not item.get("rationale"):
        item["rationale"] = str(
            _first_of(
                item, "rationale", "reason", "details", "content", "value",
                default="",
            )
        )

    return item


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


def _overhearing_eligible_receivers(conv: Conversation, npc_entity_id: str | None, db: Session) -> set[str]:
    """b. Receiver computation (code, not model) — active members of the
    conversation's gathering, minus the responding NPC and the player.
    gathering_member.left_at IS NULL is the single roster source. Empty
    (including no gathering_id at all) signals no bystanders to the caller."""
    if not conv.gathering_id:
        return set()
    member_ids = db.exec(
        select(GatheringMember.entity_id).where(
            GatheringMember.gathering_id == conv.gathering_id,
            GatheringMember.left_at.is_(None),
        )
    ).all()
    return set(member_ids) - {npc_entity_id, conv.player_id}


def _overhearing_subject_set(conv: Conversation, db: Session) -> set[str]:
    """c. Subject list — closed list, scoped to the world."""
    subjects = db.exec(
        select(Knowledge.subject)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .where(Entity.world_id == conv.world_id)
        .distinct()
    ).all()
    return set(subjects)


def _overhearing_classify(
    db: Session, conv: Conversation, player_line: str, npc_line: str,
    subject_set: set[str], model: str, host: str,
) -> list | None:
    """d. Model call."""
    template = load_analysis_prompt(
        db, world_id=conv.world_id, usage="overhearing_classification"
    )
    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{subject_list}", "\n".join(sorted(subject_set)))
        .replace("{player_line}", player_line)
        .replace("{npc_line}", npc_line)
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


def _overhearing_existing_keys(conversation_id: str, db: Session) -> tuple[set, set]:
    """Existing 'proposed' new_knowledge/knowledge_change rows for this
    conversation, for the proposal-dedup guard (k) — keyed by
    (entity_id, subject)."""
    existing = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == conversation_id,
            ProposedMutation.status == "proposed",
            ProposedMutation.mutation_type == "new_knowledge",
        )
    ).all()
    proposed_keys: set[tuple[Any, Any]] = set()
    for pm in existing:
        p = pm.payload if isinstance(pm.payload, dict) else {}
        proposed_keys.add((p.get("entity_id"), p.get("subject")))

    existing_changes = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == conversation_id,
            ProposedMutation.status == "proposed",
            ProposedMutation.mutation_type == "knowledge_change",
        )
    ).all()
    proposed_change_keys: set[tuple[Any, Any]] = set()
    for pm in existing_changes:
        p = pm.payload if isinstance(pm.payload, dict) else {}
        proposed_change_keys.add((p.get("entity_id"), p.get("subject")))

    return proposed_keys, proposed_change_keys


def _overhearing_mutation_for_receiver(
    receiver_id: str, subject: str, speaker_id: str, speaker_row: Knowledge,
    acquired_level: str, conv: Conversation, conversation_id: str, db: Session,
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
            world_id=conv.world_id,
            source_type="conversation",
            conversation_id=conversation_id,
            pass_play_id=None,
            mutation_type="knowledge_change",
            target_table="knowledge",
            target_id=None,
            payload={
                "entity_id": receiver_id,
                "subject": subject,
                "from_level": existing_row.level,
                "to_level": acquired_level,
                "source": f"overheard:{conversation_id}:{speaker_id}",
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
        world_id=conv.world_id,
        source_type="conversation",
        conversation_id=conversation_id,
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
            "source": f"overheard:{conversation_id}:{speaker_id}",
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
    classified: list[tuple[str, str]], eligible: set[str], npc_entity_id: Optional[str],
    conv: Conversation, conversation_id: str, db: Session,
    proposed_keys: set, proposed_change_keys: set, location_name: str,
) -> list[ProposedMutation]:
    entity_names: dict[str, str] = {}

    def _name(entity_id: str) -> str:
        if entity_id not in entity_names:
            ent = db.get(Entity, entity_id)
            entity_names[entity_id] = ent.name if ent else entity_id
        return entity_names[entity_id]

    now = datetime.now(UTC)
    mutations: list[ProposedMutation] = []
    for subject, speaker in classified:
        # f. Speaker resolution. Per line speaker, the eligible receiver set
        # additionally excludes the resolved speaker (an NPC never overhears
        # itself).
        speaker_id = npc_entity_id if speaker == "npc" else conv.player_id
        if not speaker_id:
            continue
        receivers = eligible - {speaker_id}
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
                conv, conversation_id, db, proposed_keys, proposed_change_keys,
                location_name, _name, now,
            )
            if mutation is not None:
                mutations.append(mutation)

    return mutations


def analyze_overhearing(
    player_line: str,
    npc_line: str,
    conversation_id: str,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
    npc_entity_id: str | None = None,
) -> list[ProposedMutation]:
    """Tier 4 overhearing pass: bystanders may ACQUIRE or UPGRADE knowledge.

    A receiver with NO row on the subject gets a `new_knowledge` proposal
    (acquisition, level one step below the speaker's, floored at 'rumor').
    A receiver who already holds a row gets a `knowledge_change` proposal
    (upgrade) ONLY if the computed level is strictly higher than their
    existing level — monotone, never a downgrade; otherwise it is skipped
    silently. Both proposal types are tagged
    `proposed_by='local_ai_overhearing'`; no knowledge row is ever written
    here. Returns un-persisted ProposedMutation objects — the caller adds and
    commits them. Returns [] on any failure or when nothing qualifies;
    failures must never surface to the player.

    `npc_entity_id`: the responding NPC of this turn (the addressed NPC) —
    excluded from the receiver set and used to resolve `speaker = "npc"`.

    Note: load_analysis_prompt calls sys.exit(1) when no template is found;
    the caller must wrap this in try/except (Exception, SystemExit).
    """
    # a. Turn-mode guard — re-checked even though the caller only invokes for
    # 'dialogue' turns.
    if not npc_line:
        return []

    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return []

    eligible = _overhearing_eligible_receivers(conv, npc_entity_id, db)
    if not eligible:
        return []

    subject_set = _overhearing_subject_set(conv, db)
    if not subject_set:
        return []

    items = _overhearing_classify(db, conv, player_line, npc_line, subject_set, model, host)
    if items is None:
        return []

    classified = _overhearing_parse_classifications(items, subject_set)
    if not classified:
        return []

    proposed_keys, proposed_change_keys = _overhearing_existing_keys(conversation_id, db)

    location = db.get(Entity, conv.location_id) if conv.location_id else None
    location_name = location.name if location else "?"

    return _overhearing_build_mutations(
        classified, eligible, npc_entity_id, conv, conversation_id, db,
        proposed_keys, proposed_change_keys, location_name,
    )


def _mutation_match_key(mutation_type: str, payload: dict):
    """Return a hashable match key for write-time deduplication, or None.

    Used by analyze_window to avoid re-proposing an idempotent fact that
    analyze_overhearing already flagged (as a 'proposed' row) for the same
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


def _window_unanalyzed_rows(conversation_id: str, conv: Conversation, db: Session) -> list[ConversationMessage]:
    """Turns since last_analyzed_turn. 'mj' rows are presentation-only
    narration — never analysed; only canonical player/npc lines carry
    world-state information."""
    rows = db.exec(
        select(ConversationMessage)
        .where(
            ConversationMessage.conversation_id == conversation_id,
            ConversationMessage.turn_order > conv.last_analyzed_turn,
        )
        .order_by(ConversationMessage.turn_order)
    ).all()
    return [r for r in rows if r.speaker in ("player", "npc")]


def _window_build_transcript(rows: list[ConversationMessage]) -> str:
    """French labels so the model's French analysis aligns with the transcript."""
    return "\n".join(
        f"[{'JOUEUR' if r.speaker == 'player' else 'PNJ'}] {r.content}"
        for r in rows
    )


def _window_injected_context_str(conv: Conversation) -> str:
    """Prefer the human-readable assembled_context over the full JSON blob.
    The full blob contains raw system prompts and metadata — thousands of
    tokens that appear to swamp the format instructions for local models."""
    ctx = conv.injected_context or {}
    if isinstance(ctx, dict) and ctx.get("assembled_context"):
        return str(ctx["assembled_context"])
    if ctx:
        return json.dumps(ctx, ensure_ascii=False, indent=2)
    return "(aucun contexte enregistré)"


def _window_call_model(
    db: Session, conv: Conversation, transcript: str, injected_ctx_str: str,
    model: str, host: str,
) -> Optional[list]:
    """Model call + JSON parse. Returns None WITHOUT advancing the caller's
    marker on a parse failure, so the next trigger retries the same turns."""
    template = load_analysis_prompt(db, world_id=conv.world_id)
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
        return None


def _window_covered_keys(conversation_id: str, db: Session) -> set:
    """Existing 'proposed' rows for this conversation — write-time dedup so a
    new_knowledge/status_change analyze_overhearing already flagged for this
    window isn't proposed twice."""
    existing = db.exec(
        select(ProposedMutation).where(
            ProposedMutation.conversation_id == conversation_id,
            ProposedMutation.status == "proposed",
        )
    ).all()
    covered: set = set()
    for pm in existing:
        key = _mutation_match_key(
            pm.mutation_type, pm.payload if isinstance(pm.payload, dict) else {}
        )
        if key is not None:
            covered.add(key)
    return covered


def _window_build_mutations(
    items: list, conv: Conversation, conversation_id: str, db: Session, covered: set,
) -> list[ProposedMutation]:
    now = datetime.now(UTC)
    mutations: list[ProposedMutation] = []
    for i, raw_item in enumerate(items):
        normalized = _normalize_to_schema(raw_item, conv, db)
        if normalized is None:
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
                world_id=conv.world_id,
                source_type="conversation",
                conversation_id=conversation_id,
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
    return mutations


def analyze_window(
    conversation_id: str,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
) -> list[ProposedMutation]:
    """Window analysis: propose mutations for turns since last_analyzed_turn.

    Reads ConversationMessage rows with turn_order > conv.last_analyzed_turn
    (player/npc only, ordered). Proposes ALL mutation types — including
    relation_change, per the anti-inflation rubric in pt-conversation-analysis
    — persists the surviving proposals, and advances
    conv.last_analyzed_turn to the highest turn_order read, all in one
    transaction. Returns the written ProposedMutation rows.

    No-op when there is nothing new: returns [] without a model call, a
    marker change, or a commit. Raises ValueError if the conversation is
    missing. On a JSON parse failure (or a non-list response), logs a warning
    and returns [] WITHOUT advancing the marker, so the next trigger retries
    the same turns.

    ollama_client.chat already strips <think> blocks before returning.
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise ValueError(f"Conversation {conversation_id!r} not found.")

    rows = _window_unanalyzed_rows(conversation_id, conv, db)
    if not rows:
        return []

    transcript = _window_build_transcript(rows)
    injected_ctx_str = _window_injected_context_str(conv)

    items = _window_call_model(db, conv, transcript, injected_ctx_str, model, host)
    if items is None:
        return []

    covered = _window_covered_keys(conversation_id, db)
    mutations = _window_build_mutations(items, conv, conversation_id, db, covered)

    for mutation in mutations:
        db.add(mutation)
    conv.last_analyzed_turn = max(r.turn_order for r in rows)
    db.add(conv)
    db.commit()

    return mutations
