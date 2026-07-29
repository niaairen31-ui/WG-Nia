"""Sliding context window — shared seam for the played and observed lanes
(TICKET-0050, BRIEF-0050-a/-b/-d; TICKET-0052, B1/I2).

New module (G1, RECON-0050): `cockpit/play.py` has no line budget left, so
the window/summary logic lands here instead of growing `play.py`.
BRIEF-0050-a shipped the config reader; BRIEF-0050-b adds the K-verbatim
cap + scene-tail message-list builder (`build_npc_message_list`) and its
single call site, `resolve_npc_message_list` (used by
`cockpit/play.py::_say_npc_generation`). BRIEF-0050-c seeded the
`conversation_summary` prompt usage; BRIEF-0050-d fills the summary slot:
`resolve_npc_message_list` computes and inserts the sliding-summary note
when the world is over budget AND `summary_enabled`. BRIEF-0052-a
generalizes the module onto a lane-neutral line form (`TurnLine`) so the
observed lane (TICKET-0051) can share the same seam instead of running its
own uncapped transcript — the played lane's public entry points keep their
exact `list[dict]` signatures and convert internally.

`DEFAULT_WORD_BUDGET` / `DEFAULT_VERBATIM_TURNS` / `DEFAULT_SUMMARY_ENABLED`
are the single source of truth shared, by comment cross-reference, with the
`conversation_window_config` column `server_default`s
(`models/config.py`) and the migration that creates them
(`scripts/migrate_v1_89_conversation_window_config.py`) — all three must
agree.

This module is read + compute only (C1 — the summary is an ephemeral
prompt artifact, never persisted): no function here may INSERT/UPDATE a
`ConversationMessage` or any canon row (enforced, vacuous-proof, by
`tooling/verify/checks/summary_not_persisted.py`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from . import ollama_client
from .context import assemble_scene_tail
from .models import ConversationWindowConfig, PromptTemplate
from .prompt_registry import _author_model, effective_model
from .prompt_store import current_prompt

_log = logging.getLogger(__name__)

DEFAULT_WORD_BUDGET = 1200
DEFAULT_VERBATIM_TURNS = 6
DEFAULT_SUMMARY_ENABLED = True


@dataclass(frozen=True)
class TurnLine:
    """One line of prior scene, lane-neutral (TICKET-0052, I2).

    `role`   -- the ollama role the played lane needs when rebuilding a
                message list ("user" | "assistant").
    `label`  -- the LITERAL prefix used when rendering this line into a
                summarization transcript, separator included: "[Joueur]",
                "[PNJ]", or an NPC name followed by " :". Carrying the
                separator inside the label is what lets both lanes render
                byte-identically through one function.
    `content`-- the line text.
    """

    role: str
    label: str
    content: str


@dataclass(frozen=True)
class ConversationWindowDefaults:
    """In-memory stand-in for a missing `conversation_window_config` row.
    Carries the same three fields a real row would, read-only."""

    word_budget: int = DEFAULT_WORD_BUDGET
    verbatim_turns: int = DEFAULT_VERBATIM_TURNS
    summary_enabled: bool = DEFAULT_SUMMARY_ENABLED


def load_conversation_window_config(
    world_id: str, db: Session
) -> "ConversationWindowConfig | ConversationWindowDefaults":
    """Read-only: the world's `conversation_window_config` row if one
    exists, else an in-memory defaults object. Never inserts a row — reads
    never write."""
    row = db.exec(
        select(ConversationWindowConfig).where(ConversationWindowConfig.world_id == world_id)
    ).first()
    if row is not None:
        return row
    return ConversationWindowDefaults()


def line_word_count(lines: list[TurnLine]) -> int:
    """Total whitespace-split word count over `content` across every line.
    Pure, no DB. Replaces `history_word_count`."""
    return sum(len(ln.content.split()) for ln in lines)


def split_verbatim_tail(lines: list[TurnLine], k: int) -> tuple[list[TurnLine], list[TurnLine]]:
    """(older, recent_k): `recent_k` is the last `k` lines (or the whole
    list if shorter); `older` is the prefix. Pure."""
    if len(lines) <= k:
        return [], list(lines)
    return lines[:-k], lines[-k:]


def render_transcript(lines: list[TurnLine]) -> str:
    """Plain `{label} {content}` transcript, one line per entry — the
    labeling style at `cockpit/play.py:189-193`, generalized to carry any
    per-line label (TICKET-0052, I2). Replaces `_render_older_transcript`;
    public so the observed lane can render its own lines through it. Pure."""
    return "\n".join(f"{ln.label} {ln.content}" for ln in lines)


_PLAYED_LABELS = {"user": "[Joueur]", "assistant": "[PNJ]"}


def _played_to_lines(npc_history: list[dict]) -> list[TurnLine]:
    """Played-lane `list[dict]` -> `list[TurnLine]` (TICKET-0052, B1)."""
    return [
        TurnLine(
            role=m.get("role", "assistant"),
            label=_PLAYED_LABELS.get(m.get("role"), "[PNJ]"),
            content=m.get("content", ""),
        )
        for m in npc_history
    ]


def _lines_to_played(lines: list[TurnLine]) -> list[dict]:
    """`list[TurnLine]` -> played-lane `list[dict]`. Round-trips `role` and
    `content` exactly; `label` is derived, never read back."""
    return [{"role": ln.role, "content": ln.content} for ln in lines]


def build_npc_message_list(
    *,
    system_prompt: str,
    npc_history: list[dict],
    scene_tail: str,
    word_budget: int,
    verbatim_turns: int,
    summary_note: "str | None" = None,
) -> list[dict]:
    """The NPC dialogue message list (TICKET-0050, BRIEF-0050-b, H1):
    `[behaviour+context system, summary note, *verbatim_K, scene tail]`.
    Below `word_budget`, `npc_history` is handed over whole (unchanged
    pre-0050 behavior); above it, only the last `verbatim_turns` rows go
    through — the K-cap + scene tail apply on the over-budget condition
    alone, independent of `summary_enabled`. `summary_note` stays unused
    (None) until brief (d) fills the sliding-summary recovery in.

    Signature unchanged by TICKET-0052 (B1): converts to `TurnLine`
    internally; this stays the played lane's own entry point, no new
    public surface added here."""
    msgs: list[dict] = [{"role": "system", "content": system_prompt}]
    if summary_note is not None:
        msgs.append({"role": "system", "content": summary_note})
    lines = _played_to_lines(npc_history)
    if line_word_count(lines) > word_budget:
        _, recent = split_verbatim_tail(lines, verbatim_turns)
        msgs.extend(_lines_to_played(recent))
    else:
        msgs.extend(npc_history)
    msgs.append({"role": "system", "content": scene_tail})
    return msgs


def _load_summary_template(world_id: str, db: Session) -> PromptTemplate:
    """Return the active `conversation_summary` prompt template
    (world-specific preferred, else the world_id=NULL row) — mirrors
    `_load_npc_dialogue_template` (`cockpit/play.py:748`). Raises HTTP 503
    if none is seeded (the registry's named call site, BRIEF-0050-c)."""
    templates = db.exec(
        select(PromptTemplate).where(
            PromptTemplate.usage == "conversation_summary",
            PromptTemplate.is_active == True,  # noqa: E712
        )
    ).all()
    if not templates:
        raise HTTPException(
            status_code=503,
            detail="No active 'conversation_summary' prompt template found. Run seed_pilot.py.",
        )
    for prefer in (lambda t: t.world_id == world_id, lambda t: t.world_id is None):
        match = next((t for t in templates if prefer(t)), None)
        if match is not None:
            return match
    return templates[0]


def summarize_older_lines(older: list[TurnLine], world_id: str, db: Session) -> str:
    """Compress `older` into a short factual summary via the
    `conversation_summary` prompt (BRIEF-0050-d). Empty `older` -> "" (no
    call). Fail-soft: any `OllamaError` is logged and swallowed to "" — a
    summary failure must never abort the turn (the NPC still answers with
    the cap-only input); this is a prompt enrichment, not a canon gate.
    Replaces `summarize_older_turns`; operates on `TurnLine` (TICKET-0052)."""
    if not older:
        return ""
    template = _load_summary_template(world_id, db)
    version = current_prompt(db, template)
    user_message = version.user_template.replace("{transcript}", render_transcript(older))
    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]
    try:
        return ollama_client.chat(messages, model=effective_model(template, _author_model())).strip()
    except ollama_client.OllamaError as exc:
        _log.warning("conversation_summary call failed, falling back to cap-only input: %s", exc)
        return ""


def format_summary_note(summary_text: str) -> "str | None":
    """Wrap non-empty summary text with the verbatim lead line; empty text
    -> None (no note, H1 message-list shape unaffected)."""
    if not summary_text:
        return None
    return f"[RESUME DE CE QUI PRECEDE — contexte, non rejouable tel quel]\n{summary_text}"


def resolve_npc_message_list(
    *,
    world_id: str,
    npc_id: str,
    location_id: "str | None",
    gathering_id: "str | None",
    player_condition: str,
    system_prompt: str,
    npc_history: list[dict],
    db: Session,
) -> list[dict]:
    """The single call site `cockpit/play.py::_say_npc_generation` uses:
    composes the world's window config, a fresh scene tail, the (optional)
    sliding-summary note, and `build_npc_message_list` into the final
    message list. Kept out of `play.py` (no line budget left there —
    RECON-0050, G1).

    The K-cap + scene tail apply whenever `npc_history` is over budget,
    independent of `summary_enabled` (BRIEF-0050-b). The summary note is an
    ADDITIONAL recovery layer on top, gated on `summary_enabled` alone
    (BRIEF-0050-d) — recomputed on every over-budget turn (F1, C1 ephemeral,
    no persisted cache)."""
    cfg = load_conversation_window_config(world_id, db)
    scene_tail = assemble_scene_tail(npc_id, location_id, gathering_id, player_condition, db)
    summary_note = None
    lines = _played_to_lines(npc_history)
    if cfg.summary_enabled and line_word_count(lines) > cfg.word_budget:
        older, _recent = split_verbatim_tail(lines, cfg.verbatim_turns)
        summary_note = format_summary_note(summarize_older_lines(older, world_id, db))
    return build_npc_message_list(
        system_prompt=system_prompt, npc_history=npc_history, scene_tail=scene_tail,
        word_budget=cfg.word_budget, verbatim_turns=cfg.verbatim_turns,
        summary_note=summary_note,
    )
