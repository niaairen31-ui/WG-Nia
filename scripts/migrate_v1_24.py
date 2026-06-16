"""Migration v1.24 — add scene_state to conversation.

Adds the `scene_state JSON NOT NULL DEFAULT '{}'` column to the `conversation`
table (BRIEF-12, schema v1.24).

Safe to run on any database created before this step — it checks for the column
first and is a no-op if it already exists.

Run from the project root:

    python scripts/migrate_v1_24.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def main() -> None:
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("conversation")}

    if "scene_state" in cols:
        print("Column 'scene_state' already exists in 'conversation' — nothing to do.")
        return

    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE conversation ADD COLUMN scene_state JSON NOT NULL DEFAULT '{}'")
        )

    print("Added column 'conversation.scene_state' (JSON NOT NULL DEFAULT '{}').")


if __name__ == "__main__":
    main()
