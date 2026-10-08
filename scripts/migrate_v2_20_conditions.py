"""Migration v2.20 — the condition language (TICKET-0111, BRIEF-0111-C,
decisions A1, I1, O-a, S1).

1. Create. `condition` and `condition_node`, from their models, when
   missing.
2. Convert. Every requirement row becomes a leaf of a tree, one tree per
   owner: an offer's eligibility (a `quest_offer_requirement` row with no
   step), an offer step's prerequisite (one with a step), an agenda step's
   prerequisite (an `agenda_step_requirement` row). Each tree is `all` of its
   leaves -- the meaning a list of requirements always had -- in the rows'
   insertion order (`rowid`). Every leaf judges the one who acts
   (`subject_role = 'doer'`, what every evaluator did). A `quest_completed`
   row becomes `quest_state` with the value `completed` (S1: one form for a
   quest's state); every other form keeps its name and arguments.
3. Drop. `agenda_step_requirement` and `quest_offer_requirement`, once their
   rows are converted, in the same transaction.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.19 (the migrations are sequential), before any change.

Idempotent: the tables are created only when missing; the conversion and
the drop run only while an old table still exists. A second run finds
nothing to do.

Post-checks, before `schema_meta` converges: neither old table remains;
the leaves written equal the rows read, form by form (`quest_completed`
counted as `quest_state`); every condition has exactly one root;
`PRAGMA foreign_key_check` is empty on the two tables this migration writes.
A dangling reference elsewhere predates it: it is listed, never a reason to
stop (AMENDMENT-0107-01).

Run from the project root:

    python scripts/migrate_v2_20_conditions.py
"""

from __future__ import annotations

import os
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_20_conditions.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.19"
_OLD_TABLES = ("agenda_step_requirement", "quest_offer_requirement")
# Parents first: a condition before its nodes.
_NEW_MODELS = (models.Condition, models.ConditionNode)
_TOUCHED_TABLES = ("condition", "condition_node")
_RENAMED_FORMS = {"quest_completed": ("quest_state", "completed")}


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.20 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _read_groups(cursor, present: set[str]) -> list[tuple[str, str, str, str, list[tuple]]]:
    """(world_id, owner column, owner id, role, rows) per tree to write; a
    row is (type, target_entity_id, target_key, threshold)."""
    groups: dict[tuple[str, str, str], list[tuple]] = {}
    worlds: dict[tuple[str, str, str], str] = {}
    selects = []
    if "quest_offer_requirement" in present:
        selects.append(
            "SELECT world_id, CASE WHEN step_id IS NULL THEN 'quest_offer_id' ELSE 'quest_offer_step_id' END, "
            "COALESCE(step_id, offer_id), CASE WHEN step_id IS NULL THEN 'eligibility' ELSE 'prerequisite' END, "
            "type, target_entity_id, target_key, threshold FROM quest_offer_requirement ORDER BY rowid"
        )
    if "agenda_step_requirement" in present:
        selects.append(
            "SELECT world_id, 'agenda_step_id', step_id, 'prerequisite', type, target_entity_id, target_key, "
            "threshold FROM agenda_step_requirement ORDER BY rowid"
        )
    for select in selects:
        for world_id, column, owner_id, role, *leaf in cursor.execute(select).fetchall():
            key = (column, owner_id, role)
            groups.setdefault(key, []).append(tuple(leaf))
            worlds[key] = world_id
    return [(worlds[key], *key, rows) for key, rows in groups.items()]


def _write_tree(cursor, world_id: str, column: str, owner_id: str, role: str, rows: list[tuple]) -> None:
    condition_id, root_id = str(uuid.uuid4()), str(uuid.uuid4())
    cursor.execute(
        f"INSERT INTO condition (id, world_id, role, {column}, created_at) VALUES (?, ?, ?, ?, ?)",
        (condition_id, world_id, role, owner_id, datetime.now(UTC).isoformat(" ")),
    )
    cursor.execute(
        "INSERT INTO condition_node (id, world_id, condition_id, parent_id, position, op) "
        "VALUES (?, ?, ?, NULL, 0, 'all')", (root_id, world_id, condition_id),
    )
    for position, (form, target_entity_id, target_key, threshold) in enumerate(rows):
        form, value = _RENAMED_FORMS.get(form, (form, None))
        cursor.execute(
            "INSERT INTO condition_node (id, world_id, condition_id, parent_id, position, op, form, subject_role, "
            "target_entity_id, target_key, threshold, value) VALUES (?, ?, ?, ?, ?, 'leaf', ?, 'doer', ?, ?, ?, ?)",
            (str(uuid.uuid4()), world_id, condition_id, root_id, position, form, target_entity_id, target_key,
             threshold, value),
        )


def _old_forms(cursor, present: set[str]) -> Counter:
    counts: Counter = Counter()
    for table in present & set(_OLD_TABLES):
        for (form,) in cursor.execute(f"SELECT type FROM {table}").fetchall():
            counts[_RENAMED_FORMS.get(form, (form, None))[0]] += 1
    return counts


def _apply() -> tuple[list[str], Counter]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    existing = set(inspect(engine).get_table_names())
    present = existing & set(_OLD_TABLES)
    missing = [model for model in _NEW_MODELS if model.__tablename__ not in existing]
    if not (present or missing):
        return [], Counter()
    applied: list[str] = []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for model in missing:
            _create_from_model(cursor, model)
            applied.append(f"{model.__tablename__} created")
        read = _old_forms(cursor, present)
        groups = _read_groups(cursor, present)
        for world_id, column, owner_id, role, rows in groups:
            _write_tree(cursor, world_id, column, owner_id, role, rows)
        if present:
            applied.append(f"{len(groups)} condition(s) written from {sum(read.values())} requirement row(s)")
        for table in sorted(present):
            cursor.execute(f"DROP TABLE {table}")
            applied.append(f"{table} dropped")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return applied, read


def _post_checks(read: Counter) -> None:
    tables = set(inspect(engine).get_table_names())
    left = sorted(tables & set(_OLD_TABLES))
    missing = [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
    if left or missing:
        raise SystemExit(f"Migration v2.20 aborted, post-check failed: still present {left}, missing {missing}.")
    with engine.connect() as conn:
        written = Counter(dict(conn.execute(text(
            "SELECT form, COUNT(*) FROM condition_node WHERE op = 'leaf' GROUP BY form")).fetchall()))
        roots = conn.execute(text(
            "SELECT c.id FROM condition c LEFT JOIN condition_node n ON n.condition_id = c.id AND n.parent_id IS NULL "
            "GROUP BY c.id HAVING COUNT(n.id) <> 1")).fetchall()
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    if read and written != read:
        raise SystemExit(f"Migration v2.20 aborted, post-check failed: leaves {dict(written)} for rows {dict(read)}.")
    if roots:
        raise SystemExit(f"Migration v2.20 aborted, post-check failed: {len(roots)} condition(s) without one root.")
    if dangling:
        raise SystemExit(f"Migration v2.20 aborted, post-check failed: foreign_key_check {dangling}.")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: old tables gone; leaves by form {dict(sorted(written.items()))}; one root per condition.")


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
    print("Migration v2.20 — the condition language: requirement rows become condition trees")
    _refuse()
    applied, read = _apply()
    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
    _post_checks(read)
    _converge_schema_meta()
    print("\nMigration v2.20 applied.")


if __name__ == "__main__":
    main()
