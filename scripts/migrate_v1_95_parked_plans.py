"""Migration v1.95 — parked plans (TICKET-0077, BRIEF-0077-a).

Two independent, idempotent pieces:

- `agenda.status` CHECK widened to include `'paused'` — SQLite has no
  `ALTER CONSTRAINT`, so the table is rebuilt (`migrate_v1_8_gatherings.py`
  precedent: rename, recreate from the model, copy, drop). Skipped when the
  live CHECK already contains `'paused'`.
- `pass_play.agenda_id` — a new nullable FK column plus its index
  (`migrate_v1_94_agenda_step_plan.py` precedent). NULL for every existing
  row; no backfill (BRIEF-0077-a Scope OUT) — `/resolve` falls back to the
  player's active agenda when it is NULL.

Run from the project root:

    python scripts/migrate_v1_95_parked_plans.py
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
        "migrate_v1_95_parked_plans.py refuses to run without "
        "WORLD_ENGINE_ENV or WORLD_ENGINE_DATABASE_URL set (fail-closed, "
        f"TICKET-0049) — got: {_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

AGENDA_COLUMNS = (
    "id, world_id, owner_entity_id, title, status, created_at, updated_at, change_history"
)


def _agenda_check_has_paused() -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='agenda'")
        ).fetchone()
    if row is None or row[0] is None:
        raise RuntimeError("agenda table not found")
    return "'paused'" in row[0]


def _rebuild_agenda_table() -> None:
    """Rebuild `agenda` on a RAW DBAPI connection, not `engine.begin()`.

    `db.py`'s `Engine.begin` listener issues an explicit `BEGIN` the instant
    a SQLAlchemy Core `Connection` autobegins (BRIEF-0044-f, transactional
    DDL) — and `PRAGMA foreign_keys` is a documented SQLite no-op once a
    transaction is already pending, silently leaving FK enforcement ON
    through the whole rebuild (confirmed empirically: `engine.begin()` here
    raises `FOREIGN KEY constraint failed` on the final `DROP TABLE
    agenda_old`, because SQLite's rename-tracks-references default rewrites
    `agenda_step`/`goal_agenda_link`'s FK text to `agenda_old` and
    `legacy_alter_table` cannot prevent that once a transaction is already
    open either). `engine.raw_connection()` bypasses Core's autobegin
    entirely, so both PRAGMAs land before any transaction exists; BEGIN/
    COMMIT/ROLLBACK are then issued by hand on that same connection. The
    CREATE TABLE/INDEX DDL is compiled from the model (same source of truth
    as `Table.create()`) rather than executed through it, since `.create()`
    needs a SQLAlchemy `Connection`, not a raw cursor.
    """
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        cursor.execute("DROP INDEX IF EXISTS idx_agenda_owner_status")
        cursor.execute("ALTER TABLE agenda RENAME TO agenda_old")

        cursor.execute(str(CreateTable(models.Agenda.__table__).compile(dialect=engine.dialect)))
        for ix in models.Agenda.__table__.indexes:
            cursor.execute(str(CreateIndex(ix).compile(dialect=engine.dialect)))

        cursor.execute(
            f"INSERT INTO agenda ({AGENDA_COLUMNS}) "
            f"SELECT {AGENDA_COLUMNS} FROM agenda_old"
        )
        cursor.execute("DROP TABLE agenda_old")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _apply_agenda_rebuild() -> None:
    if _agenda_check_has_paused():
        print("`agenda.status` CHECK already includes 'paused' — nothing to do.")
        return
    with engine.connect() as conn:
        before = conn.execute(text("SELECT COUNT(*) FROM agenda")).scalar_one()
    _rebuild_agenda_table()
    with engine.connect() as conn:
        after = conn.execute(text("SELECT COUNT(*) FROM agenda")).scalar_one()
    if before != after:
        raise SystemExit(
            f"Post-check failed: agenda row count changed during rebuild ({before} -> {after})."
        )
    checks = {ck["name"] for ck in inspect(engine).get_check_constraints("agenda")}
    if "ck_agenda_status" not in checks:
        raise SystemExit("Post-check failed: ck_agenda_status missing after rebuild.")
    if not _agenda_check_has_paused():
        raise SystemExit("Post-check failed: ck_agenda_status still lacks 'paused' after rebuild.")
    print(f"Rebuilt `agenda`: CHECK now includes 'paused' — {after} row(s) preserved.")


def _pass_play_columns() -> set[str]:
    inspector = inspect(engine)
    return {c["name"] for c in inspector.get_columns("pass_play")}


def _apply_pass_play_agenda_id() -> None:
    columns = _pass_play_columns()
    if "agenda_id" in columns:
        print("`pass_play.agenda_id` already present — nothing to do.")
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE pass_play ADD COLUMN agenda_id TEXT REFERENCES agenda(id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_passplay_agenda ON pass_play(agenda_id)"))
    print("Schema: added column `pass_play.agenda_id` and index `idx_passplay_agenda`.")


def main() -> None:
    print("Migration v1.95 — parked plans")
    _apply_agenda_rebuild()
    _apply_pass_play_agenda_id()
    print("\nMigration v1.95 applied.")


if __name__ == "__main__":
    main()
