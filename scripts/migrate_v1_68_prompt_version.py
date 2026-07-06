"""Migration to schema v1.68 — `prompt_version` table + text migration off
`prompt_template` (TICKET-0011 / BRIEF-0011-a).

Locked decisions: A2 (head pointer, text in version rows — "current" =
MAX(version_number), no pointer column), F1 (drop the head's text columns
after backfill).

Idempotent, in this order:
1. Create `prompt_version` (+ its indexes) via `create_db_and_tables()` —
   a no-op if the table already exists.
2. For every `prompt_template` row with ZERO `prompt_version` rows, insert
   version 1 copying its current `system_prompt`/`user_template` (raw SQL —
   the ORM model no longer maps those columns once this migration has run
   once, so a second run must read them the same way regardless).
3. Post-check: every head must now have >= 1 version; abort loudly before
   the column drop if not (never silently proceed on a partial backfill).
4. Drop `system_prompt`, `user_template`, `version` from `prompt_template`
   (F1) — SQLite >= 3.35 `ALTER TABLE ... DROP COLUMN` (precedent:
   scripts/migrate_v1_40_drop_character_faction_id.py).

Safe to re-run: if the head text columns are already gone, the script exits
immediately (step 4 already happened, so steps 2-3 are moot).

Run from the project root:
    python scripts/migrate_v1_68_prompt_version.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import create_db_and_tables, engine  # noqa: E402


def _backfill_v1(conn) -> int:
    """Insert a v1 `prompt_version` row for every head that has none yet.

    Reads `system_prompt`/`user_template` via raw SQL: this migration is the
    ONLY place still allowed to read those head columns once they exist,
    and the same raw read works whether this is the first run (columns
    present) or a harmless re-run before the drop has happened.
    """
    heads = conn.execute(text(
        "SELECT pt.id, pt.system_prompt, pt.user_template "
        "FROM prompt_template pt "
        "LEFT JOIN prompt_version pv ON pv.prompt_template_id = pt.id "
        "WHERE pv.id IS NULL"
    )).all()
    for head_id, system_prompt, user_template in heads:
        conn.execute(
            text(
                "INSERT INTO prompt_version "
                "(id, prompt_template_id, version_number, system_prompt, user_template, note) "
                "VALUES (:id, :head_id, 1, :system_prompt, :user_template, :note)"
            ),
            {
                "id": str(uuid4()),
                "head_id": head_id,
                "system_prompt": system_prompt,
                "user_template": user_template,
                "note": "migrated from prompt_template (v1.68)",
            },
        )
    return len(heads)


def _postcheck(conn) -> None:
    missing = conn.execute(text(
        "SELECT COUNT(*) FROM prompt_template pt "
        "LEFT JOIN prompt_version pv ON pv.prompt_template_id = pt.id "
        "WHERE pv.id IS NULL"
    )).scalar_one()
    if missing:
        raise SystemExit(
            f"Post-check failed: {missing} prompt_template head(s) still have "
            "zero prompt_version rows — aborting before the column drop."
        )


def _drop_head_text_columns(conn) -> None:
    conn.execute(text("ALTER TABLE prompt_template DROP COLUMN system_prompt"))
    conn.execute(text("ALTER TABLE prompt_template DROP COLUMN user_template"))
    conn.execute(text("ALTER TABLE prompt_template DROP COLUMN version"))


def main() -> None:
    create_db_and_tables()  # creates prompt_version (+ indexes) if absent

    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("prompt_template")}
    if "system_prompt" not in columns:
        print("prompt_template text columns already dropped — migration already applied.")
        return

    with engine.begin() as conn:
        backfilled = _backfill_v1(conn)
        _postcheck(conn)
    print(f"Backfilled {backfilled} prompt_template head(s) into prompt_version v1.")

    with engine.begin() as conn:
        _drop_head_text_columns(conn)

    print(
        "Migration v1.68 applied: prompt_version created + backfilled; "
        "prompt_template.system_prompt/user_template/version dropped."
    )


if __name__ == "__main__":
    main()
