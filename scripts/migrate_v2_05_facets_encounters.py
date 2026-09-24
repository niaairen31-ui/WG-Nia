"""Migration v2.05 — facets, encounters table, fact chokepoint (TICKET-0091,
BRIEF-0091-A, contract C-17).

Lays the structure the rest of LOT-0091 writes into: `fact.facet` and
`fact.aspect`, the `rencontre` scope on `fact_default`, and two new non-canon
tables, `rencontre` (encounter registry) and `unresolved_mention` (name-
resolution worklist). No prose moves; nothing reads a facet yet.

Steps, one transaction:

- S1 `ALTER TABLE fact ADD COLUMN facet TEXT`; `ADD COLUMN aspect TEXT` (no
  CHECK — the vocabulary is `facets.py`, Q2a).
- S2 facet of typed facts: `lien` where `relation_id` is set, `evenement`
  where `event_id`, `loi` where `world_law_id`. Free facts stay NULL — NULL
  means "predates TICKET-0091" and is never written again.
- S3 rebuild `fact_default` with the widened `ck_fact_default_scope_type`
  (`'rencontre'` added). SQLite cannot alter a CHECK, so this is the
  documented rebuild: create `fact_default_new` from the model's DDL, copy
  every column listed by `PRAGMA table_info(fact_default)`, drop the old
  table, rename, re-create `idx_fact_default_unique` and
  `idx_fact_default_fact` from the model. Aborts if the live table carries a
  column the model does not declare. FKs stay on: no table references
  `fact_default`, and the rebuilt table keeps every FK of the model.
- S4 `CREATE TABLE rencontre` + `idx_rencontre_pair`, `idx_rencontre_hi`.
- S5 `CREATE TABLE unresolved_mention` + `idx_unresolved_mention_world_open`.
- S6 report (counts per facet, rows copied).
- S7 post-checks before COMMIT: `fact_default` row count equal before and
  after; no typed fact with a NULL facet.
- S8 `_converge_schema_meta()` to v2.05.

Idempotent: every step is guarded by the live structure (column present,
CHECK already widened, table present) and S2 only touches NULL facets. A
second run prints zeros and changes no row.

Run from the project root:

    python scripts/migrate_v2_05_facets_encounters.py
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
        "migrate_v2_05_facets_encounters.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy.dialects import sqlite  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

TYPED_FACETS = (("relation_id", "lien"), ("event_id", "evenement"), ("world_law_id", "loi"))
NEW_TABLES = (models.Rencontre, models.UnresolvedMention)
_DIALECT = sqlite.dialect()


class Abort(Exception):
    """A pre- or post-check failed; the transaction is rolled back."""


def _one(cursor, sql: str) -> int:
    return cursor.execute(sql).fetchone()[0]


def _columns(cursor, table: str) -> list[str]:
    return [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]


def _table_exists(cursor, table: str) -> bool:
    return bool(_one(
        cursor, f"SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = '{table}'"))


def _create_table_ddl(model, name: str | None = None) -> str:
    ddl = str(CreateTable(model.__table__).compile(dialect=_DIALECT)).strip()
    if name is not None:
        ddl = ddl.replace(f"CREATE TABLE {model.__tablename__} ", f"CREATE TABLE {name} ", 1)
    return ddl


def _create_indexes(cursor, model) -> None:
    for index in sorted(model.__table__.indexes, key=lambda i: i.name):
        cursor.execute(str(CreateIndex(index).compile(dialect=_DIALECT)))


# --- steps ------------------------------------------------------------------

def _add_fact_columns(cursor) -> int:
    """S1."""
    present = set(_columns(cursor, "fact"))
    added = 0
    for column in ("facet", "aspect"):
        if column not in present:
            cursor.execute(f"ALTER TABLE fact ADD COLUMN {column} TEXT")
            added += 1
    return added


def _facet_typed_facts(cursor) -> dict[str, int]:
    """S2."""
    counts = {}
    for fk, facet in TYPED_FACETS:
        cursor.execute(
            f"UPDATE fact SET facet = '{facet}' WHERE {fk} IS NOT NULL AND facet IS NULL")
        counts[facet] = cursor.rowcount
    return counts


def _rebuild_fact_default(cursor) -> int:
    """S3. Returns the number of rows copied (0 when already widened)."""
    sql = _one(cursor, "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'fact_default'")
    if "'rencontre'" in sql:
        return 0
    live = _columns(cursor, "fact_default")
    declared = [c.name for c in models.FactDefault.__table__.columns]
    undeclared = [c for c in live if c not in declared]
    if undeclared:
        raise Abort(f"fact_default carries columns the model does not declare: {undeclared}")
    cols = ", ".join(live)
    cursor.execute(_create_table_ddl(models.FactDefault, "fact_default_new"))
    cursor.execute(f"INSERT INTO fact_default_new ({cols}) SELECT {cols} FROM fact_default")
    copied = _one(cursor, "SELECT COUNT(*) FROM fact_default_new")
    cursor.execute("DROP TABLE fact_default")
    cursor.execute("ALTER TABLE fact_default_new RENAME TO fact_default")
    _create_indexes(cursor, models.FactDefault)
    return copied


def _create_new_tables(cursor) -> list[str]:
    """S4, S5."""
    created = []
    for model in NEW_TABLES:
        if _table_exists(cursor, model.__tablename__):
            continue
        cursor.execute(_create_table_ddl(model))
        _create_indexes(cursor, model)
        created.append(model.__tablename__)
    return created


def _report(cursor, stats: dict) -> None:
    """S6."""
    print(f"\nS1 fact columns added: {stats['columns']}")
    for facet, count in stats["facets"].items():
        print(f"S2 typed facts given facet {facet!r}: {count}")
    print(f"S3 fact_default rows copied by the rebuild: {stats['copied']}")
    print(f"S4/S5 tables created: {len(stats['tables'])} {stats['tables']}")
    print("\nFacts per facet (state after this run):")
    for facet, count in cursor.execute(
            "SELECT COALESCE(facet, '<NULL>'), COUNT(*) FROM fact GROUP BY facet ORDER BY 1"):
        print(f"  {facet}: {count}")
    free_null = _one(
        cursor, "SELECT COUNT(*) FROM fact WHERE facet IS NULL AND relation_id IS NULL "
                "AND event_id IS NULL AND world_law_id IS NULL")
    print(f"\nReport-only: free facts with NULL facet = {free_null}")


def _postcheck(cursor, defaults_before: int) -> None:
    """S7."""
    failed = {}
    defaults_after = _one(cursor, "SELECT COUNT(*) FROM fact_default")
    if defaults_after != defaults_before:
        failed["fact_default rows"] = f"{defaults_after} != {defaults_before} before"
    typed_null = _one(
        cursor, "SELECT COUNT(*) FROM fact WHERE facet IS NULL AND (relation_id IS NOT NULL "
                "OR event_id IS NOT NULL OR world_law_id IS NOT NULL)")
    if typed_null:
        failed["typed facts with NULL facet"] = typed_null
    for model in NEW_TABLES:
        if not _table_exists(cursor, model.__tablename__):
            failed[f"{model.__tablename__} missing"] = 1
    if failed:
        raise Abort(f"S7 post-check failed: {failed}")
    print(f"\nS7 post-checks passed: fact_default rows={defaults_after}, "
          "no typed fact with NULL facet, rencontre and unresolved_mention present.")


# --- driver -----------------------------------------------------------------

def _apply() -> None:
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("BEGIN")
        try:
            defaults_before = _one(cursor, "SELECT COUNT(*) FROM fact_default")
            stats = {"columns": _add_fact_columns(cursor)}
            stats["facets"] = _facet_typed_facts(cursor)
            stats["copied"] = _rebuild_fact_default(cursor)
            stats["tables"] = _create_new_tables(cursor)
            _report(cursor, stats)
            _postcheck(cursor, defaults_before)
        except Abort as exc:
            cursor.execute("ROLLBACK")
            raise SystemExit(f"Migration v2.05 aborted, rolled back. {exc}") from None
        cursor.execute("COMMIT")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _converge_schema_meta() -> None:
    """S8."""
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
    print("Migration v2.05 — facets, encounters table, fact chokepoint")
    _apply()
    _converge_schema_meta()
    print("\nMigration v2.05 applied.")


if __name__ == "__main__":
    main()
