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
    Entity,
    GatheringMember,
    Knowledge,
    ProposedMutation,
    PromptTemplate,
)
from .writes import cap_knowledge_level, knowledge_level_rank

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

# Strips markdown fences the model might emit despite instructions.
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

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
        print(
            f"\n[error] No active {usage!r} prompt template found.\n"
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


def _normalize_to_schema(
    raw_item: Any,
    conv: Conversation,
    npc_entity_id: str | None = None,
) -> dict | None:
    """Map a model's natural output object to our ProposedMutation schema fields.

    Returns None when normalization cannot produce a usable item.
    The model reliably tells us what changed but uses its own field names.
    This function bridges the gap so we don't lose correct detections.

    `npc_entity_id`: when provided, takes priority over `conv.npc_id` as the
    default for `entity_a_id` in relation_change payloads.  Required for
    gathering conversations where `conv.npc_id` is None (no single NPC owns
    the conversation).
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
                    item, "entity_a_id", "entity_a", "from",
                    default=npc_entity_id or conv.npc_id,
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


def _entity_name(entity_id: str | None, db: Session) -> str:
    if not entity_id:
        return "?"
    ent = db.get(Entity, entity_id)
    return ent.name if ent else entity_id


def _maybe_convert_new_knowledge_to_change(
    item: dict,
    conv: Conversation,
    npc_entity_id: str | None,
    conversation_id: str,
    db: Session,
) -> dict | None:
    """Site 2 (per-turn) normalization for `new_knowledge` items.

    If the target entity already holds a `knowledge` row on the same
    subject, this is a level UPGRADE (direct affirmation), not a fresh
    acquisition — convert `item` into a `knowledge_change` proposal, or drop
    it entirely per the guards below.

    Returns:
    - `item` unchanged when the receiver holds NO row on the subject (plain
      acquisition — existing `new_knowledge` flow, untouched).
    - a converted `item` (mutation_type='knowledge_change') on a successful
      upgrade.
    - `None` to drop the item silently (K2 guard, secret guard, or monotone
      — model noise must not upgrade canon, and levels never go down).
    """
    payload = item.get("payload") or {}
    receiver_id = payload.get("entity_id")
    subject = payload.get("subject")
    if not receiver_id or not subject:
        return item

    existing_row = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == receiver_id,
            Knowledge.subject == subject,
        )
    ).first()
    if existing_row is None:
        return item  # plain acquisition — unchanged

    # Two-party speaker resolution: receiver = player → speaker = the turn's
    # responding NPC; receiver = NPC → speaker = the player.
    speaker_id = npc_entity_id if receiver_id == conv.player_id else conv.player_id
    if not speaker_id:
        return None

    # K2 guard — speaker holds no row on the subject: model noise.
    speaker_row = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == speaker_id,
            Knowledge.subject == subject,
        )
    ).first()
    if speaker_row is None:
        return None

    # Secret guard — secrets are structurally excluded from propagation.
    if speaker_row.is_secret:
        return None

    # Direct-affirmation level: speaker's row level, capped at 'knows'.
    to_level = cap_knowledge_level(speaker_row.level)

    # Monotone — target must exceed the receiver's existing level.
    if knowledge_level_rank(to_level) <= knowledge_level_rank(existing_row.level):
        return None

    location = db.get(Entity, conv.location_id) if conv.location_id else None
    location_name = location.name if location else "?"

    item["mutation_type"] = "knowledge_change"
    item["target_table"] = "knowledge"
    item["payload"] = {
        "entity_id": receiver_id,
        "subject": subject,
        "from_level": existing_row.level,
        "to_level": to_level,
        "source": f"affirmed:{conversation_id}:{speaker_id}",
    }
    item["rationale"] = (
        f"Affirmed by {_entity_name(speaker_id, db)} at {location_name} "
        f"({existing_row.level} → {to_level})"
    )
    return item


def analyze_single_turn(
    player_line: str,
    npc_reply: str,
    conversation_id: str,
    db: Session,
    model: str = ollama_client.DEFAULT_MODEL,
    host: str = ollama_client.OLLAMA_HOST,
    npc_entity_id: str | None = None,
) -> list[ProposedMutation]:
    """Per-turn immediate analysis: propose mutations for ONE player/NPC exchange.

    Reuses the same prompt, JSON extraction, normalizer, and validator as
    analyze_conversation. Returns un-persisted ProposedMutation objects tagged
    proposed_by='local_ai_immediate'. Returns [] on any failure.

    `npc_entity_id`: entity id of the NPC who spoke this turn.  Passed to
    _normalize_to_schema so that relation_change entity_a_id is correctly
    attributed in gathering conversations (where conv.npc_id is None).

    Knowledge-level upgrades (direct affirmation): a normalized
    `new_knowledge` item whose target entity already holds a row on that
    subject is converted to `knowledge_change` by
    _maybe_convert_new_knowledge_to_change (K2 guard, secret guard, level
    capped at 'knows', monotone) — or dropped. Plain acquisitions (receiver
    has no row) are unaffected.

    Note: load_analysis_prompt calls sys.exit(1) when no template is found;
    the caller must wrap this in try/except (Exception, SystemExit).
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return []

    # Mini-transcript: just this turn's exchange.
    transcript = f"[JOUEUR] {player_line}\n[PNJ] {npc_reply}"

    ctx = conv.injected_context or {}
    if isinstance(ctx, dict) and ctx.get("assembled_context"):
        injected_ctx_str = str(ctx["assembled_context"])
    elif ctx:
        injected_ctx_str = json.dumps(ctx, ensure_ascii=False, indent=2)
    else:
        injected_ctx_str = "(aucun contexte enregistré)"

    template = load_analysis_prompt(db, world_id=conv.world_id)
    user_message = (
        template.user_template
        .replace("{transcript}", transcript)
        .replace("{injected_context}", injected_ctx_str)
    )
    llm_messages = [
        {"role": "system", "content": template.system_prompt},
        {"role": "user",   "content": user_message},
    ]

    raw = ollama_client.chat(llm_messages, model=model, host=host, format="json")
    json_str = _extract_json_array(raw)
    try:
        items = json.loads(json_str)
    except json.JSONDecodeError:
        return []

    if not isinstance(items, list):
        return []

    now = datetime.now(UTC)
    mutations: list[ProposedMutation] = []
    for raw_item in items:
        normalized = _normalize_to_schema(raw_item, conv, npc_entity_id)
        if normalized is None:
            continue
        if normalized["mutation_type"] == "new_knowledge":
            normalized = _maybe_convert_new_knowledge_to_change(
                normalized, conv, npc_entity_id, conversation_id, db
            )
            if normalized is None:
                continue
        if _validate_item(normalized):
            continue
        mutations.append(ProposedMutation(
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
            # Tag as per-turn so the final-pass dedupe can see what was already flagged.
            proposed_by="local_ai_immediate",
            proposed_at=now,
        ))

    # Within-turn collapse: if the model emits duplicate relation_change entries
    # for the same entity pair + type in a SINGLE call, keep only the first.
    # This is model stutter inside one turn — not two distinct events.
    # Never collapse across turns (across separate calls to analyze_single_turn).
    seen_rel_keys: set = set()
    deduped: list[ProposedMutation] = []
    for mut in mutations:
        if mut.mutation_type == "relation_change":
            p = mut.payload if isinstance(mut.payload, dict) else {}
            rel_key = (
                frozenset([p.get("entity_a_id"), p.get("entity_b_id")]),
                p.get("relation_type"),
            )
            if rel_key in seen_rel_keys:
                continue
            seen_rel_keys.add(rel_key)
        deduped.append(mut)

    return deduped


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

    # b. Receiver computation (code, not model) — active members of the
    # conversation's gathering, minus the responding NPC and the player.
    # gathering_member.left_at IS NULL is the single roster source.
    if not conv.gathering_id:
        return []
    member_ids = db.exec(
        select(GatheringMember.entity_id).where(
            GatheringMember.gathering_id == conv.gathering_id,
            GatheringMember.left_at.is_(None),
        )
    ).all()
    eligible = set(member_ids) - {npc_entity_id, conv.player_id}
    if not eligible:
        return []

    # c. Subject list — closed list, scoped to the world.
    subjects = db.exec(
        select(Knowledge.subject)
        .join(Entity, Entity.id == Knowledge.entity_id)
        .where(Entity.world_id == conv.world_id)
        .distinct()
    ).all()
    if not subjects:
        return []
    subject_set = set(subjects)

    # d. Model call.
    template = load_analysis_prompt(
        db, world_id=conv.world_id, usage="overhearing_classification"
    )
    user_message = (
        template.user_template
        .replace("{subject_list}", "\n".join(sorted(subject_set)))
        .replace("{player_line}", player_line)
        .replace("{npc_line}", npc_line)
    )
    llm_messages = [
        {"role": "system", "content": template.system_prompt},
        {"role": "user", "content": user_message},
    ]
    raw = ollama_client.chat(llm_messages, model=model, host=host, format="json")
    json_str = _extract_json_array(raw)
    try:
        items = json.loads(json_str)
    except json.JSONDecodeError:
        return []
    if not isinstance(items, list):
        return []

    # e. Normalization — exact closed-list match only, no fuzzy matching.
    classified: list[tuple[str, str]] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            print(f"[overhearing] dropped non-dict element: {raw_item!r}")
            continue
        subject = raw_item.get("subject")
        speaker = raw_item.get("speaker")
        if subject not in subject_set:
            print(f"[overhearing] dropped unknown subject: {subject!r}")
            continue
        if speaker not in ("player", "npc"):
            print(f"[overhearing] dropped invalid speaker: {speaker!r}")
            continue
        classified.append((subject, speaker))

    if not classified:
        return []

    # Existing 'proposed' new_knowledge rows for this conversation, for the
    # proposal-dedup guard (k) — keyed by (entity_id, subject).
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

    # Existing 'proposed' knowledge_change rows for this conversation — same
    # dedup guard (k), extended to upgrade proposals.
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

    location = db.get(Entity, conv.location_id) if conv.location_id else None
    location_name = location.name if location else "?"
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
            # j. Existing-row check — a receiver with NO row gets a plain
            # acquisition (new_knowledge); a receiver who already holds a
            # row is only proposed an UPGRADE (knowledge_change) if the
            # computed level is strictly higher (monotone) — else skipped
            # silently, no noise in the queue.
            existing_row = db.exec(
                select(Knowledge).where(
                    Knowledge.entity_id == receiver_id,
                    Knowledge.subject == subject,
                )
            ).first()

            if existing_row is not None:
                if knowledge_level_rank(acquired_level) <= knowledge_level_rank(existing_row.level):
                    continue

                # k. Proposal-dedup, extended to knowledge_change.
                change_key = (receiver_id, subject)
                if change_key in proposed_change_keys:
                    continue
                proposed_change_keys.add(change_key)

                mutations.append(ProposedMutation(
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
                        f"Overheard from {_name(speaker_id)} at {location_name} "
                        f"({existing_row.level} → {acquired_level})"
                    ),
                    proposed_by="local_ai_overhearing",
                    proposed_at=now,
                ))
                continue

            # k. Proposal-dedup — re-stating the same fact later in the
            # conversation must not stack proposals.
            key = (receiver_id, subject)
            if key in proposed_keys:
                continue
            proposed_keys.add(key)

            # l. Write — one proposed_mutation per (receiver, subject).
            mutations.append(ProposedMutation(
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
                    f"Overheard from {_name(speaker_id)} at {location_name} "
                    f"(level {speaker_row.level} → {acquired_level})"
                ),
                proposed_by="local_ai_overhearing",
                proposed_at=now,
            ))

    return mutations


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

    # relation_change is excluded from the final pass: deltas accumulate across
    # turns and the per-turn immediate flags already sum the full arc. Proposing
    # them here too would double-count any trust shift the per-turn flags caught.
    # Trade-off: a gradual shift that no single turn trips won't be auto-proposed;
    # the creator can still add a relation_change manually if needed.
    before = len(mutations)
    mutations = [m for m in mutations if m.mutation_type != "relation_change"]
    dropped = before - len(mutations)
    if dropped:
        print(f"[info] Final pass: dropped {dropped} relation_change item(s) "
              f"(owned by per-turn flags).")

    return mutations
