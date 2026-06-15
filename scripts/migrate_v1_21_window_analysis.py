"""Migrate the live database to schema v1.21 — `conversation.last_analyzed_turn`.

Adds `last_analyzed_turn INTEGER NOT NULL DEFAULT 0` to `conversation` — the
high-water mark for window analysis (`analyze_window`). 0 = never analyzed.
Idempotent — safe to run more than once.

Run from the project root:

    python scripts/migrate_v1_21_window_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def main() -> None:
    columns = {col["name"] for col in inspect(engine).get_columns("conversation")}

    if "last_analyzed_turn" in columns:
        print("`conversation.last_analyzed_turn` already present.")
        return

    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE conversation ADD COLUMN last_analyzed_turn "
            "INTEGER NOT NULL DEFAULT 0"
        ))
    print("Added `conversation.last_analyzed_turn` (INTEGER NOT NULL DEFAULT 0).")


if __name__ == "__main__":
    main()
