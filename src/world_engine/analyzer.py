"""Conversation analysis — extract proposed mutations from unanalyzed turns.

analyze_window() reads the conversation's transcript window (turns since
conv.last_analyzed_turn), calls the local model with that window and the NPC's
injected_context snapshot (what the NPC was authorised to know), persists the
resulting ProposedMutation rows, and advances conv.last_analyzed_turn — all in
one transaction.

analyze_overhearing() (Tier 4, separate pass) is unaffected by the above: it
classifies a single turn against a closed subject list and proposes
acquisition/upgrade knowledge mutations for bystanders.

Both are now thin, conversation-bound wrappers (TICKET-0051, BRIEF-0051-c):
they resolve the Conversation, gather conversation-scoped inputs (transcript,
receiver set, existing-proposal dedup keys, identity defaults), delegate the
actual judging to `analyzer_transcript.py` (which never touches a
Conversation), then own persistence — setting `conversation_id` on every
returned mutation (a duplicate the transcript module deliberately never
carries — see analyzer_transcript.py's module docstring), advancing
`last_analyzed_turn`, and committing. This split exists so a played scene and
an OBSERVED scene (BRIEF-0051-e) are judged by the identical code.

# Format note
Local 8b models reliably identify WHAT changed but consistently ignore exact
field-name requirements in prompts. The analyser therefore uses a two-step
approach (now split across this module and analyzer_transcript.py):
  1. Ask the model to output any JSON array describing the changes.
  2. _normalize_to_schema() (analyzer_transcript.py) maps the model's natural
     field names to ours and fills in required payload fields from an
     AttributionContext.
  3. _validate_item() (analyzer_transcript.py) skips anything that still
     can't be salvaged.
This makes the system robust to the model's formatting habits while keeping
the change-detection logic in the prompt.
"""

from __future__ import annotations

import json
import logging

from sqlmodel import Session, select

from . import llm_parse, ollama_client
from .analyzer_transcript import (
    AttributionContext,
    _GOAL_ACTION_MAP,
    _MUTATION_TYPE_MAP,
    _content_to_subject_slug,
    _mutation_match_key,
    analyze_overheard_lines,
    analyze_transcript,
    load_analysis_prompt,
)
from .models import Conversation, ConversationMessage, GatheringMember, ProposedMutation

_log = logging.getLogger(__name__)


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
    proposed_keys: set[tuple] = set()
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
    proposed_change_keys: set[tuple] = set()
    for pm in existing_changes:
        p = pm.payload if isinstance(pm.payload, dict) else {}
        proposed_change_keys.add((p.get("entity_id"), p.get("subject")))

    return proposed_keys, proposed_change_keys


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

    existing_keys = _overhearing_existing_keys(conversation_id, db)

    attribution = AttributionContext(
        default_subject_id=npc_entity_id,
        default_counterparty_id=conv.player_id,
    )

    result = analyze_overheard_lines(
        speaker_line=player_line,
        listener_line=npc_line,
        receiver_ids=eligible,
        world_id=conv.world_id,
        location_id=conv.location_id,
        existing_keys=existing_keys,
        attribution=attribution,
        db=db,
        model=model,
        host=host,
    )

    for mutation in result.mutations:
        mutation.conversation_id = conversation_id

    if result.dropped_unattributed:
        _log.debug(
            "[overhearing] dropped_unattributed=%d dropped_by_type=%r",
            result.dropped_unattributed, result.dropped_by_type,
        )

    return result.mutations


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
    """French labels so the model's French analysis aligns with the
    transcript. This exact format — one line per turn, "\\n"-joined,
    f"[{'JOUEUR' if player else 'PNJ'}] {content}" — is a contract shared
    with `analyze_transcript` (analyzer_transcript.py's module docstring);
    kept here rather than moved so `ConversationMessage` never has to enter
    that module (AMENDMENT 03, Correction 2)."""
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


def _window_covered_keys(conversation_id: str, db: Session) -> set:
    """Existing 'proposed' rows for this conversation — write-time dedup so a
    new_knowledge/status_change the overhearing pass already flagged for this
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
    covered = _window_covered_keys(conversation_id, db)

    attribution = AttributionContext(
        default_subject_id=conv.npc_id,
        default_counterparty_id=conv.player_id,
    )

    try:
        result = analyze_transcript(
            transcript=transcript,
            world_id=conv.world_id,
            injected_context=injected_ctx_str,
            covered_keys=covered,
            attribution=attribution,
            db=db,
            model=model,
            host=host,
        )
    except llm_parse.LlmParseError:
        return []

    mutations: list[ProposedMutation] = result.mutations
    for mutation in mutations:
        mutation.conversation_id = conversation_id
        db.add(mutation)
    conv.last_analyzed_turn = max(r.turn_order for r in rows)
    db.add(conv)
    db.commit()

    if result.dropped_unattributed:
        _log.debug(
            "[window] dropped_unattributed=%d dropped_by_type=%r",
            result.dropped_unattributed, result.dropped_by_type,
        )

    return result.mutations
