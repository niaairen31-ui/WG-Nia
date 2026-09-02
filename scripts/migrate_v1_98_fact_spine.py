"""Migration v1.98 — `fact`/`fact_participant`, the knowledge anchor spine
(TICKET-0082, BRIEF-0082-b).

Three pieces, one transaction, raw DBAPI connection (`migrate_v1_95_
parked_plans.py` precedent — `engine.begin()`'s autobegin listener issues a
`BEGIN` before a PRAGMA can land, and `PRAGMA foreign_keys` is a documented
no-op once a transaction is already open):

1. Create `fact` and `fact_participant` from the model (from-scratch tables,
   `migrate_v1_97_day_rewrite.py` precedent).
2. Backfill: for each DISTINCT `(entity.world_id, knowledge.subject)` pair
   reachable through `knowledge.entity_id -> entity.world_id`, insert one
   free-standing `fact` (`content = subject`, `default_level = 'unaware'`,
   `created_by = 'migrate_v1_98'`, zero participants). The literal subject
   `"unknown"` gets a fact like any other — never special-cased, never
   repaired here (BRIEF-0082-b Scope OUT).
3. Rebuild `knowledge` with `fact_id` NOT NULL (SQLite has no
   `ALTER TABLE ... ADD COLUMN ... NOT NULL` without a default and no way to
   add a CHECK spanning tables anyway — full rebuild, `migrate_v1_8_
   gatherings.py` / `migrate_v1_95_parked_plans.py` precedent): rename old,
   create new from the model (carries `idx_knowledge_subject` and every
   other existing index/constraint plus the new `idx_knowledge_fact`),
   copy every row with its resolved `fact_id` (joined on `(world_id,
   content=subject)` against the facts just inserted), drop old.

Orphan guard: a `knowledge` row whose `entity_id` cannot resolve a world
aborts before any DDL runs (never invents a world for it). Post-checks
(row count unchanged, zero NULL `fact_id`, a checksum over `(id, entity_id,
subject, level, content, acquired_at)` unchanged) roll back the WHOLE
transaction and exit non-zero on failure — checked BEFORE commit, unlike
the `migrate_v1_95_parked_plans.py` precedent, which checks after.

Idempotent: a `fact`/`fact_participant` pair already present, and a
`knowledge.fact_id` column already present, both skip straight to the
`schema_meta` convergence.

Run from the project root:

    python scripts/migrate_v1_98_fact_spine.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v1_98_fact_spine.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

KNOWLEDGE_NEW_COLUMNS = (
    "id, entity_id, fact_id, subject, level, content, source, is_incorrect, "
    "is_secret, share_threshold, acquired_at, updated_at, session_id, change_history"
)


def _tables_present() -> bool:
    tables = inspect(engine).get_table_names()
    return "fact" in tables and "fact_participant" in tables


def _knowledge_has_fact_id() -> bool:
    columns = {c["name"] for c in inspect(engine).get_columns("knowledge")}
    return "fact_id" in columns


def _checksum(cursor, table_name: str) -> str:
    cursor.execute(
        f"SELECT id, entity_id, subject, level, content, acquired_at "
        f"FROM {table_name} ORDER BY id"
    )
    payload = json.dumps(cursor.fetchall(), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _create_tables(cursor) -> None:
    for model in (models.Fact, models.FactParticipant):
        cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
        for ix in model.__table__.indexes:
            cursor.execute(str(CreateIndex(ix).compile(dialect=engine.dialect)))


def _backfill_facts(cursor) -> int:
    cursor.execute(
        "SELECT DISTINCT e.world_id, k.subject FROM knowledge k "
        "JOIN entity e ON e.id = k.entity_id"
    )
    pairs = cursor.fetchall()
    now = datetime.now(UTC).isoformat(sep=" ")
    for world_id, subject in pairs:
        cursor.execute(
            "INSERT INTO fact (id, world_id, relation_id, event_id, world_law_id, "
            "content, default_level, created_at, created_by, change_history) "
            "VALUES (?, ?, NULL, NULL, NULL, ?, 'unaware', ?, 'migrate_v1_98', '[]')",
            (str(uuid.uuid4()), world_id, subject, now),
        )
    return len(pairs)


def _rebuild_knowledge(cursor) -> None:
    cursor.execute("DROP INDEX IF EXISTS idx_knowledge_subject")
    cursor.execute("DROP INDEX IF EXISTS idx_knowledge_entity")
    cursor.execute("ALTER TABLE knowledge RENAME TO knowledge_old")

    cursor.execute(str(CreateTable(models.Knowledge.__table__).compile(dialect=engine.dialect)))
    for ix in models.Knowledge.__table__.indexes:
        cursor.execute(str(CreateIndex(ix).compile(dialect=engine.dialect)))

    cursor.execute(
        f"INSERT INTO knowledge ({KNOWLEDGE_NEW_COLUMNS}) "
        f"SELECT k.id, k.entity_id, f.id, k.subject, k.level, k.content, k.source, "
        f"k.is_incorrect, k.is_secret, k.share_threshold, k.acquired_at, k.updated_at, "
        f"k.session_id, k.change_history "
        f"FROM knowledge_old k "
        f"JOIN entity e ON e.id = k.entity_id "
        f"JOIN fact f ON f.world_id = e.world_id AND f.content = k.subject"
    )


def _apply_fact_spine() -> tuple[int, int]:
    """Returns (before_count, after_count). Raises SystemExit (after an
    explicit ROLLBACK) on any post-check failure — never commits a partial
    or altered `knowledge` table."""
    if _tables_present() and _knowledge_has_fact_id():
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM knowledge")).scalar_one()
        print("`fact`/`fact_participant`/`knowledge.fact_id` already present — nothing to do.")
        return count, count

    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")

        cursor.execute(
            "SELECT k.id FROM knowledge k LEFT JOIN entity e ON e.id = k.entity_id "
            "WHERE e.id IS NULL"
        )
        orphans = [row[0] for row in cursor.fetchall()]
        if orphans:
            cursor.execute("ROLLBACK")
            raise SystemExit(
                "Migration v1.98 aborted: knowledge row(s) with no resolvable "
                f"world via entity_id (never inventing one): {orphans}"
            )

        before_count = cursor.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        before_checksum = _checksum(cursor, "knowledge")

        _create_tables(cursor)
        fact_count = _backfill_facts(cursor)
        _rebuild_knowledge(cursor)

        after_count = cursor.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        null_fact_count = cursor.execute(
            "SELECT COUNT(*) FROM knowledge WHERE fact_id IS NULL"
        ).fetchone()[0]
        after_checksum = _checksum(cursor, "knowledge")

        if after_count != before_count or null_fact_count != 0 or after_checksum != before_checksum:
            cursor.execute("ROLLBACK")
            raise SystemExit(
                "Migration v1.98 aborted, post-check failed: "
                f"before={before_count} after={after_count} "
                f"null_fact_id={null_fact_count} "
                f"checksum_before={before_checksum} checksum_after={after_checksum}"
            )

        cursor.execute("DROP TABLE knowledge_old")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        print(f"Schema: created `fact` ({fact_count} row(s)) and `fact_participant` (0 rows).")
        print(f"Rebuilt `knowledge` with `fact_id` NOT NULL — {after_count} row(s) preserved.")
        print(f"Checksum (id, entity_id, subject, level, content, acquired_at): {after_checksum}")
        return before_count, after_count
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
            previous = row.static_version
            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v1.98 — fact, fact_participant, knowledge.fact_id")
    before, after = _apply_fact_spine()
    print(f"knowledge row count: before={before} after={after}")
    _converge_schema_meta()
    print("\nMigration v1.98 applied.")


if __name__ == "__main__":
    main()
