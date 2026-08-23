"""Migration v1.91 — `npc_goal.kind` (TICKET-0073, BRIEF-0073-b).

Adds `npc_goal.kind` (TEXT NOT NULL DEFAULT 'volition'), with both CHECK
expressions riding on the same `ALTER TABLE ... ADD COLUMN` statement:
SQLite has no `ADD CONSTRAINT`, so a column-level CHECK is the only way to
attach one to an existing table. The model declares the two constraints as
separate named `CheckConstraint`s (`ck_npc_goal_kind`,
`ck_npc_goal_standing_horizon`) so a fresh `create_all` produces the same
semantics under readable names — this asymmetry (one combined expression
here, two named constraints in the model) is intentional.

Purely additive: no data movement, no backfill. Every existing row takes
the column default `'volition'`, which trivially satisfies both CHECKs.

Idempotent: safe to run if the column already exists.

Run from the project root:

    python scripts/migrate_v1_91_npc_goal_kind.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v1_91_npc_goal_kind.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _has_kind_column() -> bool:
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("npc_goal")}
    return "kind" in columns


def main() -> None:
    print("Migration v1.91 — npc_goal.kind")

    if _has_kind_column():
        print("`npc_goal.kind` already present — nothing to do.")
    else:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE npc_goal ADD COLUMN kind TEXT NOT NULL DEFAULT 'volition' "
                "CHECK (kind IN ('volition','standing') "
                "AND (kind <> 'standing' OR horizon = 'long'))"
            ))
        print("Schema: added column `npc_goal.kind`.")

    if not _has_kind_column():
        raise SystemExit("Post-check failed: npc_goal.kind still missing after ALTER TABLE.")

    with engine.connect() as conn:
        bad_kind = conn.execute(text(
            "SELECT COUNT(*) FROM npc_goal WHERE kind NOT IN ('volition','standing')"
        )).scalar_one()
        if bad_kind != 0:
            raise SystemExit(
                f"Post-check failed: {bad_kind} npc_goal row(s) hold a kind outside ('volition','standing')."
            )

        bad_horizon = conn.execute(text(
            "SELECT COUNT(*) FROM npc_goal WHERE kind = 'standing' AND horizon <> 'long'"
        )).scalar_one()
        if bad_horizon != 0:
            raise SystemExit(
                f"Post-check failed: {bad_horizon} npc_goal row(s) hold kind='standing' with horizon <> 'long'."
            )

    print("\nMigration v1.91 applied.")


if __name__ == "__main__":
    main()
