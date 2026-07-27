"""NPC dialogue context window — config + message-list assembly
(TICKET-0050, BRIEF-0050-a/-b).

New module (G1, RECON-0050): `cockpit/play.py` has no line budget left, so
the window/summary logic lands here instead of growing `play.py`.
BRIEF-0050-a shipped the config reader; BRIEF-0050-b adds the K-verbatim
cap + scene-tail message-list builder (`build_npc_message_list`) and its
single call site, `resolve_npc_message_list` (used by
`cockpit/play.py::_say_npc_generation`). The `conversation_summary` prompt
usage (brief c) and the summary-insertion wiring into `summary_note`
(brief d) land in later briefs — `summary_note` stays unused (None) until
then.

`DEFAULT_WORD_BUDGET` / `DEFAULT_VERBATIM_TURNS` / `DEFAULT_SUMMARY_ENABLED`
are the single source of truth shared, by comment cross-reference, with the
`conversation_window_config` column `server_default`s
(`models/config.py`) and the migration that creates them
(`scripts/migrate_v1_89_conversation_window_config.py`) — all three must
agree.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session, select

from .context import assemble_scene_tail
from .models import ConversationWindowConfig

DEFAULT_WORD_BUDGET = 1200
DEFAULT_VERBATIM_TURNS = 6
DEFAULT_SUMMARY_ENABLED = True


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


def history_word_count(npc_history: list[dict]) -> int:
    """Total whitespace-split word count over `content` across every
    message dict — the same list built at `cockpit/play.py`'s
    `_say_persist_and_build_history`. Pure, no DB."""
    return sum(len(m.get("content", "").split()) for m in npc_history)


def split_verbatim_tail(npc_history: list[dict], k: int) -> tuple[list[dict], list[dict]]:
    """(older, recent_k): `recent_k` is the last `k` messages (or the whole
    list if shorter); `older` is the prefix. Pure."""
    if len(npc_history) <= k:
        return [], list(npc_history)
    return npc_history[:-k], npc_history[-k:]


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
    (None) until brief (d) fills the sliding-summary recovery in."""
    msgs: list[dict] = [{"role": "system", "content": system_prompt}]
    if summary_note is not None:
        msgs.append({"role": "system", "content": summary_note})
    if history_word_count(npc_history) > word_budget:
        _, recent = split_verbatim_tail(npc_history, verbatim_turns)
        msgs.extend(recent)
    else:
        msgs.extend(npc_history)
    msgs.append({"role": "system", "content": scene_tail})
    return msgs


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
    composes the world's window config, a fresh scene tail, and
    `build_npc_message_list` into the final message list. Kept out of
    `play.py` (no line budget left there — RECON-0050, G1)."""
    cfg = load_conversation_window_config(world_id, db)
    scene_tail = assemble_scene_tail(npc_id, location_id, gathering_id, player_condition, db)
    return build_npc_message_list(
        system_prompt=system_prompt, npc_history=npc_history, scene_tail=scene_tail,
        word_budget=cfg.word_budget, verbatim_turns=cfg.verbatim_turns,
    )
