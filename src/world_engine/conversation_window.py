"""NPC dialogue context window — config reader (TICKET-0050, BRIEF-0050-a).

New module (G1, RECON-0050): `cockpit/play.py` sits at 990/1000 lines with
no headroom, so the window/summary logic lands here instead of growing
`play.py`. This brief ships the reader only; message-list construction
(brief b), the `conversation_summary` prompt usage (brief c), and the
budget-trigger/summary-insertion wiring (brief d) land in later briefs.

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
