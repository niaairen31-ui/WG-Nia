"""Migration v2.18 — objects held in quantity, quest terms, the quest economy
(TICKET-0109, BRIEF-0109-A, decisions A1, B1, D1, E1).

1. Holdings (A1). Every `item` row becomes a KIND: one `item_holding` of
   quantity 1 for its `owner_id` when set, else for its `location_id` when
   set (an object lying somewhere is held by that place). An item with both
   keeps its owner's holding; its place is listed, never kept. A holder that
   no longer exists is listed and skipped. A place that is now a zone keeps
   its holding and is listed (the v2.12 posture: existing data is reported,
   never moved).
2. Rebuild. `item` is rebuilt from the model: `owner_id`, `location_id`,
   `equipped` and the CHECK that tied them are dropped; `value` is added
   (default 1). Columns copied: `id`, `condition`.
3. Create. `item_holding`, `quest_offer_term`, `quest_term`, `quest_economy`
   from their models, when missing; `quest.settled_at` (nullable) added.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.17 (the migrations are sequential), before any change.

Idempotent: steps 1-2 run only while `item` still has `owner_id`; each table
and the column are created only when missing.

Post-checks, before `schema_meta` converges: `item` has the model's columns
and its row count is unchanged; one holding per item that had a living
owner or place; the four tables and `quest.settled_at` exist; `PRAGMA
foreign_key_check` is empty on the six tables this migration writes. A
dangling reference elsewhere in the database predates it: it is listed,
never a reason to stop (AMENDMENT-0107-01).

Run from the project root:

    python scripts/migrate_v2_18_quest_terms.py
"""

from __future__ import annotations

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
        "migrate_v2_18_quest_terms.py refuses to run without WORLD_ENGINE_ENV "
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
from world_engine.zone_rules import is_zone  # noqa: E402

_PREVIOUS_VERSION = "v2.17"
_NEW_MODELS = (models.ItemHolding, models.QuestOfferTerm, models.QuestTerm, models.QuestEconomy)
# The tables this migration writes: the only ones its foreign-key post-check judges.
_TOUCHED_TABLES = ("item", "quest") + tuple(m.__tablename__ for m in _NEW_MODELS)


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.18 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _create_from_model(cursor, model) -> None:
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _plan_holdings() -> tuple[list[tuple], list[str]]:
    """(world_id, item_id, holder_id) per item to hold, and the notes."""
    holdings: list[tuple] = []
    notes: list[str] = []
    with Session(engine) as session:
        rows = session.execute(text(
            "SELECT i.id, e.world_id, e.name, i.owner_id, i.location_id FROM item i "
            "JOIN entity e ON e.id = i.id ORDER BY e.name, i.id"
        )).fetchall()
        for item_id, world_id, name, owner_id, location_id in rows:
            holder_id = owner_id or location_id
            if owner_id and location_id:
                notes.append(f"{name} ({item_id}): owner kept, place {location_id} dropped")
            if holder_id is None:
                continue
            if session.get(models.Entity, holder_id) is None:
                notes.append(f"{name} ({item_id}): holder {holder_id} no longer exists, skipped")
                continue
            if holder_id == location_id and is_zone(session, holder_id):
                notes.append(f"{name} ({item_id}): lies in a zone ({holder_id}), kept as is")
            holdings.append((world_id, item_id, holder_id))
    return holdings, notes


def _rebuild_items(cursor) -> None:
    for (index_name,) in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='item' AND sql IS NOT NULL"
    ).fetchall():
        cursor.execute(f"DROP INDEX {index_name}")
    cursor.execute("ALTER TABLE item RENAME TO item_old")
    _create_from_model(cursor, models.Item)
    cursor.execute("INSERT INTO item (id, condition) SELECT id, condition FROM item_old")
    cursor.execute("DROP TABLE item_old")


def _apply_ddl(holdings: list[tuple]) -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    convert = "owner_id" in _columns("item")
    existing = set(inspect(engine).get_table_names())
    missing = [m for m in _NEW_MODELS if m.__tablename__ not in existing]
    add_settled = "settled_at" not in _columns("quest")
    if not (convert or missing or add_settled):
        return []
    applied: list[str] = []
    now = datetime.now(UTC).isoformat(sep=" ")
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for model in missing:
            _create_from_model(cursor, model)
            applied.append(f"{model.__tablename__} created")
        if add_settled:
            cursor.execute("ALTER TABLE quest ADD COLUMN settled_at DATETIME")
            applied.append("quest.settled_at added")
        if convert:
            for world_id, item_id, holder_id in holdings:
                cursor.execute(
                    "INSERT INTO item_holding (id, world_id, item_id, holder_entity_id, quantity, updated_at, "
                    "change_history) VALUES (?, ?, ?, ?, 1, ?, ?)",
                    (str(uuid.uuid4()), world_id, item_id, holder_id, now, json.dumps([])))
            _rebuild_items(cursor)
            applied.append(f"item rebuilt, {len(holdings)} holding(s) written")
        cursor.execute("COMMIT")
        cursor.execute("PRAGMA legacy_alter_table=OFF")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()
    return applied


def _post_checks(items_before: int, holdings_expected: int) -> None:
    item_columns = _columns("item")
    if item_columns != set(models.Item.__table__.columns.keys()):
        raise SystemExit(f"Migration v2.18 aborted, post-check failed: item columns are {sorted(item_columns)}.")
    with engine.connect() as conn:
        items_after = conn.execute(text("SELECT COUNT(*) FROM item")).scalar_one()
        holdings = conn.execute(text("SELECT COUNT(*) FROM item_holding")).scalar_one()
    if items_after != items_before:
        raise SystemExit(f"Migration v2.18 aborted, post-check failed: item rows {items_before} -> {items_after}.")
    if holdings < holdings_expected:
        raise SystemExit(f"Migration v2.18 aborted, post-check failed: {holdings} holding(s), expected {holdings_expected}.")
    tables = set(inspect(engine).get_table_names())
    missing = [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
    if missing or "settled_at" not in _columns("quest"):
        raise SystemExit(f"Migration v2.18 aborted, post-check failed: missing {missing or 'quest.settled_at'}.")
    with engine.connect() as conn:
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    if dangling:
        raise SystemExit(f"Migration v2.18 aborted, post-check failed: foreign_key_check {dangling}.")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: item has {sorted(item_columns)}; {items_after} item(s); {holdings} holding(s); "
          "four tables and quest.settled_at in place.")


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
    print("Migration v2.18 — item holdings, quest terms, quest economy, quest.settled_at")
    _refuse()
    with engine.connect() as conn:
        items_before = conn.execute(text("SELECT COUNT(*) FROM item")).scalar_one()
    holdings, notes = _plan_holdings() if "owner_id" in _columns("item") else ([], [])
    for note in notes:
        print(f"  Note: {note}")
    applied = _apply_ddl(holdings)
    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
    _post_checks(items_before, len(holdings))
    _converge_schema_meta()
    print("\nMigration v2.18 applied.")


if __name__ == "__main__":
    main()
