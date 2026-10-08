"""Migration v2.19 — debts, two debt requirement forms, an offer's contact
(TICKET-0110, BRIEF-0110-A, decisions J2, C2, G1, X1, I2).

1. Rebuild. `agenda_step_requirement` and `quest_offer_requirement` are
   rebuilt from their models so their two CHECKs carry `has_debt_to` and
   `no_debt_to` (an entity target, no threshold); `quest_economy` is rebuilt
   so its CHECK covers `debt_fact_relation` and `debt_skill_relation`, both
   added NULL (the code's defaults, 10 and 20). SQLite cannot alter a CHECK:
   each table is renamed, recreated from its model, its rows copied column
   for column, the old table dropped -- `migrate_v2_17_quests.py`'s
   raw-connection rebuild, verbatim in shape. The new CHECKs accept every
   row the old ones accepted.
2. Add. `quest_offer.contact_entity_id` (nullable, a reference to `entity`).
3. Create. `debt` and `debt_term`, from their models, when missing.

The relation type `debt` is retired in code (I2); this migration writes no
`relation` row and reads none: production held none (Nia's query,
2026-10-07). A row still carrying it is listed, never changed.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.18 (the migrations are sequential), before any change.

Idempotent: each rebuild runs only while its table lacks what it adds
(`'has_debt_to'` in the stored CHECK, `debt_fact_relation` among the
columns); the column is added and each table created only when missing.

Post-checks, before `schema_meta` converges: both stored requirement CHECKs
name the two forms; the four rebuilt or widened tables keep their row
counts; the column and the two tables exist; `PRAGMA foreign_key_check` is
empty on the six tables this migration writes. A dangling reference
elsewhere in the database predates it: it is listed, never a reason to stop
(AMENDMENT-0107-01).

Run from the project root:

    python scripts/migrate_v2_19_debts.py
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
        "migrate_v2_19_debts.py refuses to run without WORLD_ENGINE_ENV "
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

_PREVIOUS_VERSION = "v2.18"
_NEW_FORMS = ("has_debt_to", "no_debt_to")
_REQUIREMENT_COLUMNS = {
    "agenda_step_requirement": "id, world_id, step_id, type, target_entity_id, target_key, threshold",
    "quest_offer_requirement": "id, world_id, offer_id, step_id, type, target_entity_id, target_key, threshold",
}
class _Retired:
    """A table the code no longer declares -- TICKET-0111 (BRIEF-0111-C)
    dropped it at v2.20, its rows converted into `condition` trees. Its DDL
    is frozen here as this migration created it, so the migration still
    runs on the database it was written for."""

    def __init__(self, name: str, ddl: tuple[str, ...]) -> None:
        self.__tablename__ = name
        self.ddl = ddl


_REQUIREMENT_MODELS = {
    "agenda_step_requirement": _Retired("agenda_step_requirement", (
    """CREATE TABLE agenda_step_requirement (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL,
	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(step_id) REFERENCES agenda_step (id),
	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement (step_id, type, target_entity_id, target_key)",
    )),
    "quest_offer_requirement": _Retired("quest_offer_requirement", (
    """CREATE TABLE quest_offer_requirement (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL, step_id VARCHAR,
	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
	PRIMARY KEY (id),
	CONSTRAINT ck_quest_offer_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
	CONSTRAINT ck_quest_offer_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id),
	FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
	FOREIGN KEY(step_id) REFERENCES quest_offer_step (id),
	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
    "CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement (offer_id)",
    )),
}
_ECONOMY_COLUMNS = ("id, world_id, rate_money, rate_relation, rate_fact, rate_skill, band_low_pct, "
                    "band_high_pct, updated_at")
# Parents first: a debt before its terms.
_NEW_MODELS = (models.Debt, models.DebtTerm)
# The tables this migration writes: the only ones its foreign-key post-check judges.
_TOUCHED_TABLES = ("agenda_step_requirement", "quest_offer_requirement", "quest_economy", "quest_offer",
                   "debt", "debt_term")
_COUNTED_TABLES = ("agenda_step_requirement", "quest_offer_requirement", "quest_economy", "quest_offer")


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.19 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _table_sql(table: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).first()
    return row[0] if row is not None else ""


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _row_counts() -> dict[str, int]:
    with engine.connect() as conn:
        return {t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one() for t in _COUNTED_TABLES}


def _create_from_model(cursor, model) -> None:
    if isinstance(model, _Retired):
        for statement in model.ddl:
            cursor.execute(statement)
        return
    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
    for index in model.__table__.indexes:
        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _rebuild(cursor, table: str, model, columns: str) -> None:
    for (index_name,) in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)
    ).fetchall():
        cursor.execute(f"DROP INDEX {index_name}")
    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    _create_from_model(cursor, model)
    cursor.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
    cursor.execute(f"DROP TABLE {table}_old")


def _plan() -> tuple[list[str], bool, bool, list]:
    rebuild = [t for t in _REQUIREMENT_MODELS if "'has_debt_to'" not in _table_sql(t)]
    economy = "debt_fact_relation" not in _columns("quest_economy")
    contact = "contact_entity_id" not in _columns("quest_offer")
    existing = set(inspect(engine).get_table_names())
    missing = [model for model in _NEW_MODELS if model.__tablename__ not in existing]
    return rebuild, economy, contact, missing


def _apply_ddl() -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    rebuild, economy, contact, missing = _plan()
    if not (rebuild or economy or contact or missing):
        return []
    applied: list[str] = []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        for table in rebuild:
            _rebuild(cursor, table, _REQUIREMENT_MODELS[table], _REQUIREMENT_COLUMNS[table])
            applied.append(f"{table} rebuilt")
        if economy:
            _rebuild(cursor, "quest_economy", models.QuestEconomy, _ECONOMY_COLUMNS)
            applied.append("quest_economy rebuilt")
        if contact:
            cursor.execute("ALTER TABLE quest_offer ADD COLUMN contact_entity_id VARCHAR REFERENCES entity (id)")
            applied.append("quest_offer.contact_entity_id added")
        for model in missing:
            _create_from_model(cursor, model)
            applied.append(f"{model.__tablename__} created")
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


def _post_checks(before: dict[str, int]) -> None:
    for table in _REQUIREMENT_MODELS:
        absent = [form for form in _NEW_FORMS if f"'{form}'" not in _table_sql(table)]
        if absent:
            raise SystemExit(f"Migration v2.19 aborted, post-check failed: {table}'s CHECK lacks {absent}.")
    after = _row_counts()
    changed = {t: (before[t], after[t]) for t in _COUNTED_TABLES if before[t] != after[t]}
    if changed:
        raise SystemExit(f"Migration v2.19 aborted, post-check failed: row counts changed {changed}.")
    missing = [c for c in ("debt_fact_relation", "debt_skill_relation") if c not in _columns("quest_economy")]
    if "contact_entity_id" not in _columns("quest_offer"):
        missing.append("quest_offer.contact_entity_id")
    tables = set(inspect(engine).get_table_names())
    missing += [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
    if missing:
        raise SystemExit(f"Migration v2.19 aborted, post-check failed: missing {missing}.")
    with engine.connect() as conn:
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
        retired = conn.execute(text("SELECT COUNT(*) FROM relation WHERE type = 'debt'")).scalar_one()
    if dangling:
        raise SystemExit(f"Migration v2.19 aborted, post-check failed: foreign_key_check {dangling}.")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    if retired:
        print(f"  Note: {retired} relation row(s) still carry the retired type 'debt' (not changed).")
    print(f"Post-check: two CHECKs widened; row counts kept {after}; debt tables in place.")


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
    print("Migration v2.19 — debts, two debt requirement forms, an offer's contact")
    _refuse()
    before = _row_counts()
    applied = _apply_ddl()
    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
    _post_checks(before)
    _converge_schema_meta()
    print("\nMigration v2.19 applied.")


if __name__ == "__main__":
    main()
