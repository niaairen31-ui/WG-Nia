"""Migration v2.27 — the creator's review of a proposal, round by round
(TICKET-0115, BRIEF-0115-A; decisions A3, C1 and H1a of the conditions
series' dashboard).

Schema, additive only; no data is written:

- adds `proposed_mutation.original_payload` (JSON, nullable): the payload
  as its producer wrote it, kept the first time the creator approves an
  edited one;
- creates `mutation_review` (one row per review call: round, approve or
  reject, unit or batch, the status it left, edited or not, a step's
  verdict) and `mutation_review_change` (one row per value changed in a
  round: path, field, kind, a scalar's before and after), with their
  indexes, exactly as the models declare them.

A proposal reviewed before v2.27 has no `mutation_review` row: the
dashboard counts only the reviews this schema records.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.26. Idempotent: each step checks what is already there. One raw
transaction (`foreign_keys` set before it).

Post-check, before `schema_meta` moves: `proposed_mutation` kept its row
count; the column and both tables are in place; `PRAGMA foreign_key_check`
on the tables this migration writes is empty (a dangling row elsewhere is a
note, never a failure -- AMENDMENT-0107-01). `schema_meta` then moves to
v2.27.

Run from the project root:

    python scripts/migrate_v2_27_mutation_reviews.py
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
        "migrate_v2_27_mutation_reviews.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.26"
_THIS_VERSION = "v2.27"
# The tables this migration writes: the only ones its foreign-key post-check judges.
_TOUCHED_TABLES = ("proposed_mutation", "mutation_review", "mutation_review_change")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.27 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _count(conn, table: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _plan() -> dict:
    existing = set(inspect(engine).get_table_names())
    return {
        "original_payload": "original_payload" not in _columns("proposed_mutation"),
        "review": "mutation_review" not in existing,
        "change": "mutation_review_change" not in existing,
    }


def _apply(plan: dict) -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    applied: list[str] = []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("BEGIN")
        if plan["original_payload"]:
            cursor.execute("ALTER TABLE proposed_mutation ADD COLUMN original_payload JSON")
            applied.append("proposed_mutation.original_payload added")
        if plan["review"]:
            _create_from_model(cursor, models.MutationReview)
            applied.append("mutation_review created")
        if plan["change"]:
            _create_from_model(cursor, models.MutationReviewChange)
            applied.append("mutation_review_change created")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return applied


def _post_checks(before: dict[str, int]) -> None:
    with engine.connect() as conn:
        after = {t: _count(conn, t) for t in before}
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    existing = set(inspect(engine).get_table_names())
    problems = []
    if after != before:
        problems.append(f"row counts changed {before} -> {after}")
    if "original_payload" not in _columns("proposed_mutation"):
        problems.append("proposed_mutation.original_payload is missing")
    for table in ("mutation_review", "mutation_review_change"):
        if table not in existing:
            problems.append(f"{table} was not created")
    if dangling:
        problems.append(f"foreign_key_check {dangling}")
    if problems:
        raise SystemExit("Migration v2.27 aborted, post-check failed: " + "; ".join(problems) + ".")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: proposed_mutation.original_payload, mutation_review and mutation_review_change "
          f"in place; counts kept {after}.")


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=_THIS_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {_THIS_VERSION!r}")
        elif _version_key(row.static_version) < _version_key(_THIS_VERSION):
            previous = row.static_version
            row.static_version = _THIS_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {_THIS_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.27 — the creator's review of a proposal, round by round")
    _refuse()
    with engine.connect() as conn:
        before = {"proposed_mutation": _count(conn, "proposed_mutation")}
    applied = _apply(_plan())
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.27 already fully applied.")
    _post_checks(before)
    _converge_schema_meta()
    print("\nMigration v2.27 applied.")


if __name__ == "__main__":
    main()
