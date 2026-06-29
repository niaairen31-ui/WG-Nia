"""Migration v1.63 — world-scoped custom skill catalogue (BRIEF-55).

Creates the `skill_definition` table (one row = one custom skill definition
for one world; `base_domain` CHECK against the four base domains, `UNIQUE
(world_id, name)`) and adds `skill.skill_definition_id`, a nullable FK to
`skill_definition(id)` with `ON DELETE RESTRICT` — NULL for the four
base-domain rows, set for custom-skill rows.

Idempotent: safe to run if the table/column already exist.

Run from the project root:

    python scripts/migrate_v1_63.py
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
    tables = set(inspector.get_table_names())

    if "skill_definition" not in tables:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE skill_definition ("
                "  id           TEXT PRIMARY KEY,"
                "  world_id     TEXT NOT NULL REFERENCES world(id),"
                "  name         TEXT NOT NULL,"
                "  base_domain  TEXT NOT NULL"
                "               CHECK (base_domain IN ('physical','agility','perception','composure')),"
                "  description  TEXT,"
                "  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,"
                "  updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            conn.execute(text(
                "CREATE UNIQUE INDEX idx_skill_definition_world_name "
                "ON skill_definition(world_id, name)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_skill_definition_world ON skill_definition(world_id)"
            ))
        print("Created table 'skill_definition' with its two indexes.")
    else:
        print("Table 'skill_definition' already exists — nothing to do.")

    cols = {c["name"] for c in inspector.get_columns("skill")}
    if "skill_definition_id" not in cols:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE skill ADD COLUMN skill_definition_id TEXT "
                "REFERENCES skill_definition(id) ON DELETE RESTRICT"
            ))
        print("Added column 'skill.skill_definition_id'.")
    else:
        print("Column 'skill.skill_definition_id' already exists — nothing to do.")

    print("Migration v1.63 applied.")


if __name__ == "__main__":
    main()
