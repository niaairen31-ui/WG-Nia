"""Migration v2.24 — the event journal's vocabulary (TICKET-0114,
BRIEF-0114-A; decisions F1, B1, C1, D1, H1, K-a, N1, O1 and V1 of the
conditions series).

Schema, additive except two rebuilds:

- creates `event_type`, `event_type_role`, `event_type_role_type`,
  `event_type_scope`, `event_sorte`, `event_participant` and
  `condition_node_filter`, exactly as the models declare them;
- adds `event.type_id`, `event.quantity` and `agenda_step.started_at`;
- rebuilds `condition` and `condition_draft` (their role CHECK gains
  `failure`, H1) and `condition_node` (a `since` column and its CHECK, F1),
  every row copied.

Data, for every event written before it (N1, V1, O1):

- each event is typed by its former category: the world's type named after
  that domain (« Social », « Autre »...), created when missing with one role
  « Impliqué » accepting every entity type of the world;
- each `event_entity` row becomes an `event_participant` in that role
  (`event_entity` itself stays until v2.25 drops it);
- each event gets its fact (`fact.event_id`, facet `evenement`, its title
  then its description), and an event that was `public` or `confirmed`
  gets a `world` default at `knows` -- known by everyone, as before; a
  `secret` one gets none -- known by no one (O1). No `knowledge` row is
  written.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.23. Idempotent: each step checks what is already there. One raw
transaction (`foreign_keys` and `legacy_alter_table` set before it).

Post-check, before `schema_meta` moves: every event has a type and exactly
one fact; `event_participant` holds as many rows as `event_entity`;
`condition`, `condition_node` and `condition_draft` kept their row counts;
`PRAGMA foreign_key_check` on the tables this migration writes is empty (a
dangling row elsewhere is a note, never a failure -- AMENDMENT-0107-01).
`schema_meta` then moves to v2.24 -- its own version, not the code's:
v2.25 (BRIEF-0114-C) drops what this one keeps.

Run from the project root:

    python scripts/migrate_v2_24_event_journal.py
"""

from __future__ import annotations

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
        "migrate_v2_24_event_journal.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

import unicodedata  # noqa: E402

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

_PREVIOUS_VERSION = "v2.23"
_THIS_VERSION = "v2.24"
# Parents first.
_NEW_MODELS = (
    models.EventType, models.EventTypeRole, models.EventTypeRoleType, models.EventTypeScope,
    models.EventSorte, models.EventParticipant, models.ConditionNodeFilter,
)
_CONDITION_COLUMNS = "id, world_id, role, quest_offer_id, quest_offer_step_id, agenda_step_id, created_at"
_DRAFT_COLUMNS = ("id, attempt_id, world_ref, world_name, role, instruction, outcome, retried, offer_ref, "
                  "saved_as_proposed, payload, model_calls, created_at, decided_at")
_NODE_COLUMNS = ("id, world_id, condition_id, parent_id, position, op, n, form, subject_role, "
                 "subject_entity_id, target_entity_id, target_key, threshold, value")
_ADDED_COLUMNS = (
    ("event", "type_id", "VARCHAR REFERENCES event_type (id)"),
    ("event", "quantity", "INTEGER"),
    ("agenda_step", "started_at", "DATETIME"),
)
# The domains and their French type names -- frozen here as v2.24 wrote
# them (`event_vocab.DOMAIN_LABELS_FR`, `DOMAIN_ROLE_FR` at v2.24).
_DOMAIN_NAMES = {
    "political": "Politique", "magical": "Magique", "criminal": "Criminel", "military": "Militaire",
    "social": "Social", "mystery": "Mystère", "other": "Autre",
}
_ROLE_NAME = "Impliqué"
_BUILTIN_TYPES = ("character", "location", "faction", "item")
_CREATED_BY = "migration_v2_24"
# The tables this migration writes: the only ones its foreign-key post-check judges.
_TOUCHED_TABLES = (
    "event", "agenda_step", "condition", "condition_node", "condition_draft", "event_type", "event_type_role",
    "event_type_role_type", "event_type_scope", "event_sorte", "event_participant",
    "condition_node_filter", "fact", "fact_default",
)


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.24 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _table_sql(table: str) -> str:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).first()
    return row[0] if row is not None else ""


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _count(conn, table: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def _create_from_model(cursor, model) -> None:
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


def _plan() -> dict:
    existing = set(inspect(engine).get_table_names())
    return {
        "condition": "'failure'" not in _table_sql("condition"),
        "condition_draft": "'failure'" not in _table_sql("condition_draft"),
        "condition_node": "since" not in _columns("condition_node"),
        "columns": [(t, c, ddl) for t, c, ddl in _ADDED_COLUMNS if c not in _columns(t)],
        "models": [m for m in _NEW_MODELS if m.__tablename__ not in existing],
    }


# --- the data (N1, V1, O1) -------------------------------------------------------

def _key(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    return " ".join("".join(ch for ch in decomposed if not unicodedata.combining(ch)).split())


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")


def _world_types(cursor, world_id: str) -> list[str]:
    slugs = [row[0] for row in cursor.execute(
        "SELECT slug FROM entity_type WHERE world_id = ? AND status = 'active'", (world_id,)).fetchall()]
    return list(_BUILTIN_TYPES) + sorted(s for s in slugs if s not in _BUILTIN_TYPES)


def _domain_type(cursor, world_id: str, domain: str, made: dict) -> tuple[str, str]:
    """(type id, role id) of the world's type for `domain`, made if missing."""
    name = _DOMAIN_NAMES[domain]
    if (world_id, domain) in made:
        return made[(world_id, domain)]
    for type_id, type_name in cursor.execute(
            "SELECT id, name FROM event_type WHERE world_id = ?", (world_id,)).fetchall():
        if _key(type_name) == _key(name):
            role = cursor.execute("SELECT id FROM event_type_role WHERE type_id = ? ORDER BY position, id",
                                  (type_id,)).fetchone()
            made[(world_id, domain)] = (type_id, role[0])
            return made[(world_id, domain)]
    now = _now()
    type_id, role_id = str(uuid.uuid4()), str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO event_type (id, world_id, name, domain, counts_quantity, in_chronicle, participants_secret, "
        "status, created_at, updated_at) VALUES (?, ?, ?, ?, 0, 1, 0, 'active', ?, ?)",
        (type_id, world_id, name, domain, now, now))
    cursor.execute(
        "INSERT INTO event_type_role (id, world_id, type_id, name, position, accepts_sorte, status) "
        "VALUES (?, ?, ?, ?, 0, 0, 'active')", (role_id, world_id, type_id, _ROLE_NAME))
    for entity_type in _world_types(cursor, world_id):
        cursor.execute("INSERT INTO event_type_role_type (id, world_id, role_id, entity_type) VALUES (?, ?, ?, ?)",
                       (str(uuid.uuid4()), world_id, role_id, entity_type))
    made[(world_id, domain)] = (type_id, role_id)
    return type_id, role_id


def _fact_text(title: str, description) -> str:
    description = (description or "").strip()
    return f"{title} — {description}" if description else title


def _backfill(cursor) -> list[str]:
    done: list[str] = []
    made: dict = {}
    events = cursor.execute(
        "SELECT id, world_id, type, title, description, knowledge_status FROM event WHERE type_id IS NULL "
        "ORDER BY recorded_at, id").fetchall()
    for event_id, world_id, category, title, description, status in events:
        domain = category if category in _DOMAIN_NAMES else "other"
        type_id, role_id = _domain_type(cursor, world_id, domain, made)
        cursor.execute("UPDATE event SET type_id = ? WHERE id = ?", (type_id, event_id))
        links = cursor.execute("SELECT entity_id FROM event_entity WHERE event_id = ? ORDER BY rowid",
                               (event_id,)).fetchall()
        for position, (entity_id,) in enumerate(links):
            cursor.execute(
                "INSERT INTO event_participant (id, world_id, event_id, role_id, entity_id, position) "
                "VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), world_id, event_id, role_id, entity_id, position))
        if cursor.execute("SELECT 1 FROM fact WHERE event_id = ?", (event_id,)).fetchone() is None:
            fact_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO fact (id, world_id, event_id, content, facet, default_level, created_at, created_by, "
                "change_history) VALUES (?, ?, ?, ?, 'evenement', 'unaware', ?, ?, '[]')",
                (fact_id, world_id, event_id, _fact_text(title, description), _now(), _CREATED_BY))
            if status in ("public", "confirmed"):
                cursor.execute(
                    "INSERT INTO fact_default (id, world_id, fact_id, scope_type, scope_id, level, created_at, "
                    "created_by) VALUES (?, ?, ?, 'world', NULL, 'knows', ?, ?)",
                    (str(uuid.uuid4()), world_id, fact_id, _now(), _CREATED_BY))
        done.append(event_id)
    return done


def _apply(plan: dict) -> list[str]:
    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
    PRAGMAs must land before any transaction exists)."""
    applied: list[str] = []
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA legacy_alter_table=ON")
        cursor.execute("BEGIN")
        if plan["condition"]:
            _rebuild(cursor, "condition", models.Condition, _CONDITION_COLUMNS)
            applied.append("condition rebuilt")
        if plan["condition_draft"]:
            _rebuild(cursor, "condition_draft", models.ConditionDraft, _DRAFT_COLUMNS)
            applied.append("condition_draft rebuilt")
        if plan["condition_node"]:
            _rebuild(cursor, "condition_node", models.ConditionNode, _NODE_COLUMNS)
            applied.append("condition_node rebuilt")
        for table, column, ddl in plan["columns"]:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            applied.append(f"{table}.{column} added")
        for model in plan["models"]:
            _create_from_model(cursor, model)
            applied.append(f"{model.__tablename__} created")
        typed = _backfill(cursor)
        if typed:
            applied.append(f"{len(typed)} event(s) typed, with their participants and facts")
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
    with engine.connect() as conn:
        untyped = conn.execute(text("SELECT COUNT(*) FROM event WHERE type_id IS NULL")).scalar_one()
        unfacted = conn.execute(text(
            "SELECT COUNT(*) FROM event e WHERE (SELECT COUNT(*) FROM fact f WHERE f.event_id = e.id) != 1"
        )).scalar_one()
        participants, links = _count(conn, "event_participant"), _count(conn, "event_entity")
        after = {t: _count(conn, t) for t in before}
        dangling = [row for table in _TOUCHED_TABLES
                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
                     if row[0] not in _TOUCHED_TABLES]
    problems = []
    if untyped:
        problems.append(f"{untyped} event(s) without a type")
    if unfacted:
        problems.append(f"{unfacted} event(s) without exactly one fact")
    if participants != links:
        problems.append(f"event_participant holds {participants} row(s), event_entity {links}")
    if after != before:
        problems.append(f"row counts changed {before} -> {after}")
    if "'failure'" not in _table_sql("condition") or "'failure'" not in _table_sql("condition_draft") \
            or "since" not in _columns("condition_node"):
        problems.append("condition, condition_draft or condition_node was not rebuilt")
    if dangling:
        problems.append(f"foreign_key_check {dangling}")
    if problems:
        raise SystemExit("Migration v2.24 aborted, post-check failed: " + "; ".join(problems) + ".")
    for table, rowid, parent, _fk in elsewhere:
        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
    print(f"Post-check: every event typed with one fact; {participants} participant(s); counts kept {after}.")


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
    print("Migration v2.24 — the event journal's vocabulary")
    _refuse()
    with engine.connect() as conn:
        before = {t: _count(conn, t) for t in ("condition", "condition_node", "condition_draft", "event",
                                               "agenda_step")}
    applied = _apply(_plan())
    print("Applied: " + ", ".join(applied) + "." if applied else "Migration v2.24 already fully applied.")
    _post_checks(before)
    _converge_schema_meta()
    print("\nMigration v2.24 applied.")


if __name__ == "__main__":
    main()
