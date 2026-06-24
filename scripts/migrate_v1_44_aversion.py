"""Migration to schema v1.44 — add `character.aversion` and `faction.aversion`
(BRIEF-33).

Prose dual of `philosophy`: what an entity rejects or fears, as a concept or
category — never a named entity (that's the relation graph). Character-side
is read into the NPC dialogue prompt (`H_IDENTITY` block); faction-side is
stored + proposed but dormant — read by no assembler.

Idempotent: safe to re-run — skips a table's ALTER if the column already
exists on it.

Run from the project root:
    python scripts/migrate_v1_44_aversion.py
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

    for table in ("character", "faction"):
        columns = {c["name"] for c in inspector.get_columns(table)}
        if "aversion" in columns:
            print(f"Column '{table}.aversion' already present — skipping.")
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN aversion TEXT"))
        print(f"Migration v1.44 applied: {table}.aversion column added.")


if __name__ == "__main__":
    main()
