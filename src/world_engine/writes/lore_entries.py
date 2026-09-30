"""The lore source record's writer (TICKET-0098, BRIEF-0098-B/-C, C-04).

`lore_entry` and `lore_entry_row` are non-canon (they record where canon rows
came from) and append-only: this module inserts, never updates or deletes;
the world cascade is their only delete. Nothing here commits; the caller owns
the transaction.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from ..models import LoreEntry, LoreEntryRow
from ..models.pipeline import LORE_ENTRY_ROW_ACTIONS, LORE_ENTRY_ROW_TABLES


def write_lore_entry(
    db: Session, *, world_id: str, statement: str,
    questions: Optional[str] = None, answers: Optional[str] = None,
) -> LoreEntry:
    """Insert one `lore_entry`. `ValueError` on an empty statement. Blank
    `questions` / `answers` are stored as NULL."""
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError("lore_entry: the statement is empty")
    entry = LoreEntry(
        world_id=world_id, statement=statement.strip(),
        questions=(questions or "").strip() or None,
        answers=(answers or "").strip() or None,
    )
    db.add(entry)
    return entry


def record_entry_row(
    db: Session, *, entry_id: str, row_table: str, row_id: str, action: str = "created",
) -> LoreEntryRow:
    """Insert one `lore_entry_row`. `ValueError` on a table or action outside
    the schema's CHECK lists."""
    if row_table not in LORE_ENTRY_ROW_TABLES:
        raise ValueError(f"lore_entry_row: unknown row_table {row_table!r}")
    if action not in LORE_ENTRY_ROW_ACTIONS:
        raise ValueError(f"lore_entry_row: unknown action {action!r}")
    row = LoreEntryRow(entry_id=entry_id, row_table=row_table, row_id=row_id, action=action)
    db.add(row)
    return row
