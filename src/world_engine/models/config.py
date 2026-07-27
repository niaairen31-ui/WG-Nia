"""Conversation-window curated config (TICKET-0050, BRIEF-0050-a).

Split out of `canon.py` (974/1000 lines, no headroom for a new table —
`tooling/verify/checks/module_budget.py`), not because this table belongs to
a different stratum: it is canon curated-config, same family as
`location_type_catalog` / `world_law` (metadata-config category, no
`change_history`).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, Index, Integer, text
from sqlmodel import Field, SQLModel

from .canon import _created_ts, _uuid

# -----------------------------------------------------------------------------
# conversation_window_config  (creator-tunable NPC dialogue context window,
# schema v1.89, TICKET-0050, BRIEF-0050-a)
#
# One row per world. Curated config (location_type_catalog family): no
# change_history, written ONLY via writes.upsert_conversation_window_config.
# Absence of a row is legal — the reader (conversation_window.py) applies
# in-memory defaults and never writes on read.
# -----------------------------------------------------------------------------
class ConversationWindowConfig(SQLModel, table=True):
    __tablename__ = "conversation_window_config"
    __table_args__ = (
        Index("idx_conversation_window_config_world", "world_id", unique=True),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    world_id: str = Field(foreign_key="world.id", nullable=False)
    word_budget: int = Field(
        default=1200,
        sa_column=Column(Integer, nullable=False, server_default=text("1200")),
    )
    # Counted in player/npc MESSAGE rows, NOT exchanges (6 rows = 3 exchanges).
    verbatim_turns: int = Field(
        default=6,
        sa_column=Column(Integer, nullable=False, server_default=text("6")),
    )
    summary_enabled: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default=text("1")),
    )
    updated_at: datetime = _created_ts()
