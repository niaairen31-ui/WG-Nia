"""Post-conversation analysis — extract proposed mutations from a closed transcript.

Calls the local model with the full transcript and the NPC's injected_context
snapshot (what the NPC was authorised to know).  Returns a list of
ProposedMutation instances that are NOT yet persisted; the caller decides
whether to write them (or just print them for --dry-run).

Nothing here touches world state or any real table.

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
import re
import sys
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from . import ollama_client
from .models import (
    Conversation,
    ConversationMessage,
    ProposedMutation,
    PromptTemplate,
)

# Canonical mutation_type values (schema).
VALID_MUTATION_TYPES = frozenset(
    {
        "relation_change",
        "new_knowledge",
        "knowledge_change",
        "event_creation",
        "status_change",
        "entity_creation",
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
    "observation": "new_knowledge",   # reclassify model's "observations" as knowledge
    "rumeur": "new_knowledge",
    "rumor": "new_knowledge",
    "location": "status_change",
}

# Maps mutation_type → likely target_table.
_TARGET_TABLE_MAP: dict[str, str] = {
    "relation_change": "relation",
    "new_knowledge": "knowledge",
    "knowledge_change": "knowledge",
    "event_creation": "event",
    "status_change": "entity",
    "entity_creation": "entity",
}

# Strips markdown fences the model might emit despite instructions.
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# Strips non-word chars for subject slugs.
_SLUG_NON_WORD = re.compile(r"[^\w]")


def load_analysis_prompt(db: Session, world_id: str | None = None) -> PromptTemplate:
    """Return the active conversation_analysis template, preferring world-specific.

    Exits with a clear message if none is found (mirrors load_npc_dialogue_prompt
    in talk.py for consistent error UX).
    """
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "conversation_analysis",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        print(
            "\n[error] No active 'conversation_analysis' prompt template found.\n"
            "        Seed it first: python scripts/seed_pilot.py"
        )
        sys.exit(1)
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def _extract_json_array(text: str) -> str:
    """Pull a JSON value out of raw model output; always return a JSON array string.

    Handles three shapes:
    - An array [...] (returned as-is after stripping fences/prose).
    - A single object {...} (wrapped into [...]).
    - Anything else (returns "[]").
    """
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1)

    bracket_start = text.find("[")
    brace_start = text.find("{")

    # Prefer array when both are present.
    if bracket_start != -1 and (brace_start == -1 or bracket_start <= brace_start):
        end = text.rfind("]")
        if end != -1 and end >= bracket_start:
            return text[bracket_start : end + 1]

    # Fall back to single object, wrap it.
    if brace_start != -1:
        end = text.rfind("}")
        if end != -1 and end >= brace_start:
            return "[" + text[brace_start : end + 1] + "]"

    return "[]"


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


def _normalize_to_schema(raw_item: Any, conv: Conversation) -> dict | None:
    """Map a model's natural output object to our ProposedMutation schema fields.

    Returns None when normalization cannot produce a usable item.
    The model reliably tells us what changed but uses its own field names.
    This function bridges the gap so we don't lose correct detections.
    """
    if not isinstance(raw_item, dict):
        return None
    item = dict(raw_item)

    # ── mutation_type ────────────────────────────────────────────────────────
    if "mutation_type" not in item:
        for alias in ("type", "action", "kind", "change_type", "mutation"):
            if alias in item:
                item["mutation_type"] = item.pop(alias)
                break
    raw_mt = str(item.get("mutation_type") or "").lower()
    item["mutation_type"] = _MUTATION_TYPE_MAP.get(raw_mt, "other")

    # ── target_table ─────────────────────────────────────────────────────────
    if "target_table" not in item:
        item["target_table"] = _TARGET_TABLE_MAP.get(item["mutation_type"], "other")

    # ── target_id ────────────────────────────────────────────────────────────
    if "target_id" not in item:
        item["target_id"] = item.get("id") or None

    # ── payload ──────────────────────────────────────────────────────────────
    if not isinstance(item.get("payload"), dict):
        mt = item["mutation_type"]
        content = str(
            _first_of(item, "content", "details", "value", "description", default="")
        )

        if mt == "new_knowledge":
            # Infer who learned this from "subject"/"entity" field.
            subj = str(_first_of(item, "subject", "entity", default="")).lower()
            player_hints = {"player", "joueur", "char-player", conv.player_id}
            entity_id = (
                conv.player_id if not subj or any(h in subj for h in player_hints)
                else conv.npc_id
            )
            item["payload"] = {
                "entity_id": entity_id,
                "subject": _content_to_subject_slug(content),
                "level": item.get("level") or "rumor",
                "content": content,
                "source": "conversation",
            }

        elif mt == "relation_change":
            item["payload"] = {
                "entity_a_id": _first_of(
                    item, "entity_a_id", "entity_a", "from", default=conv.npc_id
                ),
                "entity_b_id": _first_of(
                    item, "entity_b_id", "entity_b", "to", default=conv.player_id
                ),
                "relation_type": _first_of(
                    item, "relation_type", "relation", default="passive_attention"
                ),
                "intensity_delta": int(
                    _first_of(item, "intensity_delta", "delta", default=5)
                ),
            }

        elif mt == "event_creation":
            item["payload"] = {
                "title": item.get("title") or content[:60] or "Event",
                "description": content,
                "type": item.get("event_type") or "social",
                "involved_entities": [conv.player_id, conv.npc_id],
            }

        else:
            # Generic fallback: collect any leftover fields as payload.
            skip = {
                "mutation_type", "target_table", "target_id", "rationale",
                "type", "action", "kind", "subject", "entity",
            }
            item["payload"] = {k: v for k, v in raw_item.items() if k not in skip}

    if not item.get("payload"):
        return None

    # ── rationale ────────────────────────────────────────────────────────────
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


def analyze_conversation(
    conversation_id: str,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
) -> list[ProposedMutation]:
    """Run post-conversation analysis; return validated ProposedMutation objects.

    Does NOT persist anything.  Raises ValueError if the conversation is missing.
    ollama_client.chat already strips <think> blocks before returning.
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise ValueError(f"Conversation {conversation_id!r} not found.")

    rows = db.exec(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.turn_order)
    ).all()
    # 'mj' rows are presentation-only narration — never analyse them.
    # Only canonical player/npc lines carry world-state information.
    rows = [r for r in rows if r.speaker in ("player", "npc")]
    if not rows:
        print("[info] Conversation has no messages — nothing to analyse.")
        return []

    # French labels so the model's French analysis aligns with the transcript.
    transcript = "\n".join(
        f"[{'JOUEUR' if r.speaker == 'player' else 'PNJ'}] {r.content}"
        for r in rows
    )

    # Prefer the human-readable assembled_context over the full JSON blob.
    # The full blob contains raw system prompts and metadata — thousands of
    # tokens that appear to swamp the format instructions for local models.
    ctx = conv.injected_context or {}
    if isinstance(ctx, dict) and ctx.get("assembled_context"):
        injected_ctx_str = str(ctx["assembled_context"])
    elif ctx:
        injected_ctx_str = json.dumps(ctx, ensure_ascii=False, indent=2)
    else:
        injected_ctx_str = "(aucun contexte enregistré)"

    template = load_analysis_prompt(db, world_id=conv.world_id)

    # str.replace instead of .format() so transcript/context JSON (which
    # contain { and }) are inserted verbatim without escaping issues.
    user_message = (
        template.user_template
        .replace("{transcript}", transcript)
        .replace("{injected_context}", injected_ctx_str)
    )

    llm_messages = [
        {"role": "system", "content": template.system_prompt},
        {"role": "user", "content": user_message},
    ]

    print("Analyse en cours…", end="\r", flush=True)
    # format="json" constrains Ollama to valid JSON syntax (≥ 0.1.x).
    # The normalizer below then maps the model's field names to our schema.
    raw = ollama_client.chat(llm_messages, model=model, host=host, format="json")
    print(" " * 40, end="\r")

    json_str = _extract_json_array(raw)
    try:
        items = json.loads(json_str)
    except json.JSONDecodeError as exc:
        print(f"[warn] Model output is not valid JSON ({exc}).")
        print(f"       Raw snippet: {raw[:400]!r}")
        return []

    if not isinstance(items, list):
        print("[warn] Model returned a non-list JSON value — treating as empty.")
        return []

    now = datetime.now(UTC)
    mutations: list[ProposedMutation] = []
    for i, raw_item in enumerate(items):
        normalized = _normalize_to_schema(raw_item, conv)
        if normalized is None:
            print(f"[skip] Item {i}: normalization failed — {raw_item!r}")
            continue
        err = _validate_item(normalized)
        if err:
            print(f"[skip] Item {i}: {err} — {normalized!r}")
            continue
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
                proposed_by="local_ai",
                proposed_at=now,
            )
        )

    return mutations
