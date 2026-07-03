"""Migration v1.67 — `prompt_template.model` override column (BRIEF-0008-a).

Adds `prompt_template.model TEXT NULL`. NULL means code decides (the
existing default_model); non-NULL is a creator override consumed by
`prompt_registry.effective_model`. No default value, no backfill — every
existing row is born NULL, so runtime model selection stays bit-identical
to pre-migration behavior.

Idempotent: safe to run if the column already exists.

Run from the project root:

    python scripts/migrate_v1_67_prompt_model.py
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
    cols = {c["name"] for c in inspector.get_columns("prompt_template")}

    if "model" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE prompt_template ADD COLUMN model TEXT"))
        print("Added column 'prompt_template.model' (TEXT NULL).")
    else:
        print("Column 'prompt_template.model' already exists — nothing to do.")

    print("Migration v1.67 applied.")


if __name__ == "__main__":
    main()
