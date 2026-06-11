"""Migrate the live database to schema v1.16 — `knowledge.change_history`.

Adds `change_history JSON DEFAULT '[]'` to `knowledge`, mirroring
`relation.change_history`. Existing rows start with `[]` — past edits are
unrecoverable, history starts now. Idempotent — safe to run more than once.

Run from the project root:

    python scripts/migrate_v1_16_knowledge_history.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def main() -> None:
    columns = {col["name"] for col in inspect(engine).get_columns("knowledge")}

    if "change_history" in columns:
        print("`knowledge.change_history` already present.")
        return

    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE knowledge ADD COLUMN change_history JSON NOT NULL DEFAULT '[]'"
        ))
    print("Added `knowledge.change_history` (JSON NOT NULL DEFAULT '[]').")


if __name__ == "__main__":
    main()
