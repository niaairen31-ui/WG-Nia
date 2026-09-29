"""Migration v2.10 — drop `knowledge.subject` (TICKET-0097, BRIEF-0097-G, B3).

Since v2.09 a `knowledge` row is identified by the fact it knows, and no
code reads `subject` any more (`knowledge_identity.py` K3). One transaction:

- S1 guard: v2.09 ran — `idx_knowledge_entity_fact` exists. Otherwise abort,
  writing nothing: the identity must stand before its old key goes.
- S2 guard: every legacy label is still readable elsewhere — for every
  `knowledge` row whose `subject` is neither `creator_meta` nor its fact's
  content (the only other shape v2.09 leaves is an `npc:<id>` subject whose
  fact was tokenized), the fact has a participant. Otherwise abort and list
  the rows.
- S3 `DROP INDEX idx_knowledge_subject` (SQLite refuses to drop an indexed
  column).
- S4 `ALTER TABLE knowledge DROP COLUMN subject`.
- S5 post-check: the column and its index are gone; the row count is
  unchanged.
- then `schema_meta` converges to v2.10.

Idempotent: a second run finds no `subject` column, skips S2-S4 and only
converges `schema_meta`.

Run from the project root, right after `migrate_v2_09_knowledge_identity.py`
(after `python scripts/backup.py`), before starting the cockpit:

    python scripts/migrate_v2_10_drop_knowledge_subject.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_10_drop_knowledge_subject.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

TARGET_VERSION = "v2.10"
CREATOR_META = "creator_meta"


class Abort(Exception):
    """A pre- or post-check failed; the transaction is rolled back."""


def _has_column(cursor) -> bool:
    return "subject" in [row[1] for row in cursor.execute("PRAGMA table_info(knowledge)")]


def _has_index(cursor, name: str) -> bool:
    return cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)
    ).fetchone() is not None


def orphan_labels(cursor) -> list[tuple]:
    """S2: (knowledge id, subject) of rows whose label would be lost."""
    return cursor.execute(
        "SELECT k.id, k.subject FROM knowledge k JOIN fact f ON f.id = k.fact_id "
        "WHERE k.subject <> ? AND k.subject IS NOT f.content "
        "AND NOT EXISTS (SELECT 1 FROM fact_participant p WHERE p.fact_id = k.fact_id) "
        "ORDER BY k.id",
        (CREATOR_META,),
    ).fetchall()


def migrate(cursor) -> bool:
    """S1-S5 on an open transaction. True when the column was dropped, False
    when it was already gone. Raises `Abort` on any failed check."""
    if not _has_index(cursor, "idx_knowledge_entity_fact"):
        raise Abort("idx_knowledge_entity_fact is missing — run migrate_v2_09_knowledge_identity.py first")
    if not _has_column(cursor):
        return False
    orphans = orphan_labels(cursor)
    if orphans:
        raise Abort(f"{len(orphans)} knowledge row(s) would lose their only label: {orphans[:10]!r}")
    rows_before = cursor.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    if _has_index(cursor, "idx_knowledge_subject"):
        cursor.execute("DROP INDEX idx_knowledge_subject")
    cursor.execute("ALTER TABLE knowledge DROP COLUMN subject")
    if _has_column(cursor) or _has_index(cursor, "idx_knowledge_subject"):
        raise Abort("post-check: knowledge.subject or its index is still present")
    rows_after = cursor.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    if rows_after != rows_before:
        raise Abort(f"post-check: knowledge holds {rows_after} row(s), expected {rows_before}")
    return True


def _apply() -> None:
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("BEGIN")
        try:
            dropped = migrate(cursor)
        except Abort as exc:
            cursor.execute("ROLLBACK")
            raise SystemExit(f"Migration {TARGET_VERSION} aborted, rolled back. {exc}") from None
        cursor.execute("COMMIT")
        cursor.close()
        print("knowledge.subject dropped." if dropped else "knowledge.subject already gone — nothing to do.")
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=TARGET_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {TARGET_VERSION!r}")
        elif row.static_version != TARGET_VERSION:
            previous = row.static_version
            row.static_version = TARGET_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {TARGET_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {TARGET_VERSION!r} — nothing to do")
        session.commit()


def main() -> None:
    print(f"Migration {TARGET_VERSION} — drop knowledge.subject")
    _apply()
    _converge_schema_meta()
    print(f"\nMigration {TARGET_VERSION} applied.")


if __name__ == "__main__":
    main()
