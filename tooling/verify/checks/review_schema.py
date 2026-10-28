"""G1 check for TICKET-0129 (BRIEF-0129-B) -- schema v2.33: the creator's review columns, the approved character, the review batches and the encounter source.

RS1 -- static, by import. Every C-03 column sits on its model with its
   nullability, server default and FK target (`V233_SPEC`);
   `pc_draft_sketch` carries the three review CHECK names;
   `idx_npc_batch_review_open` is unique on `(pc_draft_id, pc_group_label)`
   with `WHERE status = 'open' AND pc_draft_id IS NOT NULL`;
   `npc_batch_row.pc_draft_sketch_id` has no FK; C-04's constants
   (`PC_REVIEW_ACTIONS`, `PC_REVIEW_DEFAULT_RELATION`,
   `PC_REVIEW_DEFAULT_INTENSITY`, exported by `models`);
   `ENCOUNTER_SOURCES[-1] == "pc_creation"`;
   `EXPECTED_STATIC_SCHEMA_VERSION == "v2.33"`; the migration exists with
   `_PREVIOUS_VERSION = "v2.32"`; the JSON columns of the five tables are
   exactly `npc_batch.scope` and `npc_batch_row.payload` (INV-20).
RS2 -- CHECKs, raw INSERTs after a fresh `create_all`, each refusal paired
   with an admitted row of the same table. A sketch with `review_action =
   'x'`, `'attach'` with no entity, a NULL action with an entity, intensity
   0 and 101 are refused; `'create'` with no entity and `'attach'` with one
   are admitted; a sketch inserted without the review columns reads `ally`
   and 60; a membership without `review_dropped` reads 0; two `open`
   batches with the same `(pc_draft_id, pc_group_label)` are refused, an
   `abandoned` and an `open` one admitted, two `open` batches with
   `pc_draft_id` NULL admitted.
RS3 -- migration. The fixture creates every table, then recreates
   `pc_draft`, `pc_draft_sketch`, `pc_draft_membership`, `npc_batch` and
   `npc_batch_row` from the literal `V232_DDL` (compiled from the models at
   `11cafc0`), with one row each inserted raw, then
   `scripts/migrate_v2_33_creator_review.py` runs as a subprocess:
   (a) at `schema_meta` v2.31 it exits non-zero and nothing changes;
   (b) at v2.32 it exits zero: every v2.33 column and
       `idx_npc_batch_review_open` exist, the stored `pc_draft_sketch` SQL
       holds the three review CHECK names, the five rows keep their ids and
       values, the sketch reads `ally` and 60, the membership 0,
       `schema_meta` reads v2.33;
   (c) a second run exits zero and changes nothing.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A sub-rule not reached is a FAILURE.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
MIGRATION = ROOT / "scripts" / "migrate_v2_33_creator_review.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


# C-03: table -> the v2.33 columns.
V233_COLUMNS = {
    "pc_draft": ("review_location_id", "character_id"),
    "pc_draft_sketch": ("review_action", "review_entity_id", "review_relation_type", "review_intensity"),
    "pc_draft_membership": ("review_dropped",),
    "npc_batch": ("pc_draft_id", "pc_group_label"),
    "npc_batch_row": ("pc_draft_sketch_id",),
}
SKETCH_CHECKS = ("ck_pc_draft_sketch_review_action", "ck_pc_draft_sketch_review_entity",
                 "ck_pc_draft_sketch_review_intensity")
REVIEW_INDEX = "idx_npc_batch_review_open"
# C-03: (table, column) -> (nullable, server default, FK target)
V233_SPEC: dict[tuple[str, str], tuple[bool, str | None, str | None]] = {
    ("pc_draft", "review_location_id"): (True, None, "entity.id"),
    ("pc_draft", "character_id"): (True, None, "entity.id"),
    ("pc_draft_sketch", "review_action"): (True, None, None),
    ("pc_draft_sketch", "review_entity_id"): (True, None, "entity.id"),
    ("pc_draft_sketch", "review_relation_type"): (False, "'ally'", None),
    ("pc_draft_sketch", "review_intensity"): (False, "60", None),
    ("pc_draft_membership", "review_dropped"): (False, "0", None),
    ("npc_batch", "pc_draft_id"): (True, None, "pc_draft.id"),
    ("npc_batch", "pc_group_label"): (True, None, None),
    ("npc_batch_row", "pc_draft_sketch_id"): (True, None, None),
}
JSON_COLUMNS = {("npc_batch", "scope"), ("npc_batch_row", "payload")}
RESHAPED = ("npc_batch_row", "npc_batch", "pc_draft_membership", "pc_draft_sketch", "pc_draft")

# The five tables at 11cafc0 (v2.32), compiled from the models before BRIEF-0129-B.
V232_DDL = """
CREATE TABLE pc_draft (
    id VARCHAR NOT NULL,
    world_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'draft' NOT NULL,
    name VARCHAR DEFAULT '' NOT NULL,
    story VARCHAR DEFAULT '' NOT NULL,
    start_location_id VARCHAR,
    start_location_set_by VARCHAR,
    creator_note VARCHAR,
    submitted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_pc_draft_status CHECK (status IN ('draft','submitted','returned','approved')),
    CONSTRAINT ck_pc_draft_set_by CHECK (start_location_set_by IS NULL OR start_location_set_by IN ('player','designer')),
    FOREIGN KEY(world_id) REFERENCES world (id),
    FOREIGN KEY(user_id) REFERENCES user (id),
    FOREIGN KEY(start_location_id) REFERENCES entity (id)
);
CREATE UNIQUE INDEX idx_pc_draft_open ON pc_draft (world_id, user_id) WHERE status <> 'approved';
CREATE INDEX idx_pc_draft_world ON pc_draft (world_id);
CREATE TABLE pc_draft_sketch (
    id VARCHAR NOT NULL,
    draft_id VARCHAR NOT NULL,
    world_id VARCHAR NOT NULL,
    position INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    role VARCHAR DEFAULT '' NOT NULL,
    sentence VARCHAR DEFAULT '' NOT NULL,
    group_label VARCHAR DEFAULT '' NOT NULL,
    kind VARCHAR NOT NULL,
    skill_key VARCHAR,
    existing_entity_id VARCHAR,
    origin VARCHAR NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_pc_draft_sketch_kind CHECK (kind IN ('family','master','faction','other')),
    CONSTRAINT ck_pc_draft_sketch_master CHECK ((kind = 'master') = (skill_key IS NOT NULL)),
    CONSTRAINT ck_pc_draft_sketch_origin CHECK (origin IN ('player','designer')),
    FOREIGN KEY(draft_id) REFERENCES pc_draft (id),
    FOREIGN KEY(world_id) REFERENCES world (id),
    FOREIGN KEY(existing_entity_id) REFERENCES entity (id)
);
CREATE INDEX idx_pc_draft_sketch_draft ON pc_draft_sketch (draft_id);
CREATE TABLE pc_draft_membership (
    id VARCHAR NOT NULL,
    draft_id VARCHAR NOT NULL,
    world_id VARCHAR NOT NULL,
    faction_id VARCHAR NOT NULL,
    role VARCHAR,
    origin VARCHAR NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_pc_draft_membership_origin CHECK (origin IN ('player','designer')),
    FOREIGN KEY(draft_id) REFERENCES pc_draft (id),
    FOREIGN KEY(world_id) REFERENCES world (id),
    FOREIGN KEY(faction_id) REFERENCES entity (id)
);
CREATE UNIQUE INDEX idx_pc_draft_membership_faction ON pc_draft_membership (draft_id, faction_id);
CREATE TABLE npc_batch (
    id VARCHAR NOT NULL,
    world_id VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'open' NOT NULL,
    scope JSON NOT NULL,
    npcs_total INTEGER DEFAULT 0 NOT NULL,
    npcs_done INTEGER DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    closed_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(world_id) REFERENCES world (id)
);
CREATE TABLE npc_batch_row (
    id VARCHAR NOT NULL,
    batch_id VARCHAR NOT NULL,
    line_index INTEGER NOT NULL,
    kind VARCHAR NOT NULL,
    payload JSON NOT NULL,
    row_status VARCHAR DEFAULT 'proposed' NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(batch_id) REFERENCES npc_batch (id)
);
CREATE INDEX idx_npc_batch_row_batch ON npc_batch_row (batch_id);
"""
TS = "2026-01-01 00:00:00"
V232_ROWS = {
    "pc_draft": ("id, world_id, user_id, status, name, story, start_location_id, start_location_set_by, "
                 "creator_note, submitted_at, created_at, updated_at",
                 ("draft-1", "world-1", "user-1", "submitted", "Ilse", "Une histoire.", "place-1", "player",
                  None, TS, TS, TS)),
    "pc_draft_sketch": ("id, draft_id, world_id, position, name, role, sentence, group_label, kind, "
                        "skill_key, existing_entity_id, origin",
                        ("sketch-1", "draft-1", "world-1", 0, "Maître Oren", "maître", "Il m'apprit.",
                         "atelier", "master", "agility", None, "player")),
    "pc_draft_membership": ("id, draft_id, world_id, faction_id, role, origin",
                            ("member-1", "draft-1", "world-1", "faction-1", "apprentie", "designer")),
    "npc_batch": ("id, world_id, status, scope, npcs_total, npcs_done, created_at, closed_at",
                  ("batch-1", "world-1", "committed", '{"lines": []}', 2, 2, TS, TS)),
    "npc_batch_row": ("id, batch_id, line_index, kind, payload, row_status, created_at, updated_at",
                      ("row-1", "batch-1", 0, "draft", '{"draft": {}}', "committed", TS, TS)),
}


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    return engine, pathlib.Path(tmp_dir) / "check.db"


def _default(column) -> str | None:
    default = column.server_default
    if default is None:
        return None
    return str(getattr(default, "arg", default))


def _rs1_columns() -> int:
    from sqlalchemy import JSON
    from sqlmodel import SQLModel

    collected = 0
    for (table_name, name), expected in V233_SPEC.items():
        column = SQLModel.metadata.tables[table_name].columns.get(name)
        if column is None:
            fail(f"RS1 {table_name}.{name} is missing")
            continue
        targets = sorted(fk.target_fullname for fk in column.foreign_keys)
        got = (column.nullable, _default(column), targets[0] if len(targets) == 1 else (targets or None))
        if got != expected:
            fail(f"RS1 {table_name}.{name} is {got!r}, expected {expected!r}")
        collected += 1
    json_columns = {(t, c.name) for t in RESHAPED for c in SQLModel.metadata.tables[t].columns
                    if isinstance(c.type, JSON)}
    if json_columns != JSON_COLUMNS:
        fail(f"RS1 the JSON columns of the five tables are {sorted(json_columns)}, expected "
             f"{sorted(JSON_COLUMNS)} (INV-20)")
    return collected


def _rs1_constraints() -> int:
    from sqlmodel import SQLModel

    sketch = SQLModel.metadata.tables["pc_draft_sketch"]
    checks = {c.name for c in sketch.constraints if c.name and c.name.startswith("ck_")}
    for name in SKETCH_CHECKS:
        if name not in checks:
            fail(f"RS1 pc_draft_sketch lacks the CHECK {name}")
    index = next((i for i in SQLModel.metadata.tables["npc_batch"].indexes if i.name == REVIEW_INDEX), None)
    if index is None:
        fail(f"RS1 {REVIEW_INDEX} is missing")
        return 0
    where = index.dialect_options["sqlite"]["where"]
    if (not index.unique or [c.name for c in index.columns] != ["pc_draft_id", "pc_group_label"]
            or str(where) != "status = 'open' AND pc_draft_id IS NOT NULL"):
        fail(f"RS1 {REVIEW_INDEX} is unique={index.unique} on {[c.name for c in index.columns]} "
             f"WHERE {where!s}")
    return len(checks) + 1


def _rs1_constants() -> int:
    from world_engine import models
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    expected = {"PC_REVIEW_ACTIONS": ("create", "attach", "drop"), "PC_REVIEW_DEFAULT_RELATION": "ally",
                "PC_REVIEW_DEFAULT_INTENSITY": 60}
    for name, value in expected.items():
        if getattr(models, name, None) != value or name not in models.__all__:
            fail(f"RS1 models.{name} is {getattr(models, name, None)!r} or not exported, expected {value!r}")
    if models.ENCOUNTER_SOURCES[-1] != "pc_creation":
        fail(f"RS1 ENCOUNTER_SOURCES is {models.ENCOUNTER_SOURCES!r}")
    if EXPECTED_STATIC_SCHEMA_VERSION != "v2.33":
        fail(f"RS1 EXPECTED_STATIC_SCHEMA_VERSION is {EXPECTED_STATIC_SCHEMA_VERSION!r}")
    if not MIGRATION.exists():
        fail(f"RS1 {MIGRATION.name} is missing")
        return 0
    previous = None
    for node in ast.parse(MIGRATION.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_PREVIOUS_VERSION" for t in node.targets):
            previous = getattr(node.value, "value", None)
    if previous != "v2.32":
        fail(f"RS1 the migration's _PREVIOUS_VERSION is {previous!r}, expected 'v2.32'")
    return len(expected) + 1


def rule_rs1() -> None:
    if _rs1_columns() + _rs1_constraints() + _rs1_constants() == 0:
        fail("RS1 collected nothing")


def _raises(engine, sql: str, params: dict | None = None) -> bool:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    try:
        with engine.begin() as conn:
            conn.execute(text(sql), params or {})
    except IntegrityError:
        return True
    return False


def _refused(engine, label: str, sql: str, params: dict | None = None) -> int:
    if not _raises(engine, sql, params):
        fail(f"RS2 {label} was admitted")
    return 1


def _admitted(engine, label: str, sql: str, params: dict | None = None) -> int:
    if _raises(engine, sql, params):
        fail(f"RS2 {label} was refused")
    return 1


def _read(engine, sql: str) -> tuple | None:
    from sqlalchemy import text

    with engine.connect() as conn:
        row = conn.execute(text(sql)).first()
    return tuple(row) if row is not None else None


def _rs2_sketches(engine) -> int:
    counted = 0
    sketch = ("INSERT INTO pc_draft_sketch (id, draft_id, world_id, position, name, kind, origin, "
              "review_action, review_entity_id, review_intensity) "
              "VALUES (:id, 'd1', 'w1', 0, 'N', 'family', 'player', :a, :e, :i)")
    for label, action, entity, intensity in (
            ("a sketch with review_action 'x'", "x", None, 60),
            ("an attach with no entity", "attach", None, 60),
            ("a NULL action with an entity", None, "e1", 60),
            ("a sketch at intensity 0", "create", None, 0),
            ("a sketch at intensity 101", "create", None, 101)):
        counted += _refused(engine, label, sketch, {"id": f"k-{label}", "a": action, "e": entity, "i": intensity})
    counted += _admitted(engine, "a create with no entity", sketch, {"id": "k1", "a": "create", "e": None, "i": 1})
    counted += _admitted(engine, "an attach with an entity", sketch, {"id": "k2", "a": "attach", "e": "e1", "i": 100})
    counted += _admitted(engine, "a sketch without the review columns",
                         "INSERT INTO pc_draft_sketch (id, draft_id, world_id, position, name, kind, origin) "
                         "VALUES ('k3', 'd1', 'w1', 1, 'N', 'family', 'player')")
    defaults = _read(engine, "SELECT review_action, review_relation_type, review_intensity "
                             "FROM pc_draft_sketch WHERE id = 'k3'")
    if defaults != (None, "ally", 60):
        fail(f"RS2 a sketch without the review columns reads {defaults!r}, expected (None, 'ally', 60)")
    return counted


def _rs2_memberships_and_batches(engine) -> int:
    counted = _admitted(engine, "a membership without review_dropped",
                        "INSERT INTO pc_draft_membership (id, draft_id, world_id, faction_id, origin) "
                        "VALUES ('m1', 'd1', 'w1', 'e1', 'player')")
    dropped = _read(engine, "SELECT review_dropped FROM pc_draft_membership WHERE id = 'm1'")
    if dropped != (0,):
        fail(f"RS2 a membership without review_dropped reads {dropped!r}, expected (0,)")
    batch = ("INSERT INTO npc_batch (id, world_id, status, scope, pc_draft_id, pc_group_label) "
             "VALUES (:id, 'w1', :s, '{}', :d, :g)")
    counted += _admitted(engine, "an open review batch", batch, {"id": "b1", "s": "open", "d": "d1", "g": "atelier"})
    counted += _refused(engine, "a second open review batch for one draft and group", batch,
                        {"id": "b2", "s": "open", "d": "d1", "g": "atelier"})
    counted += _admitted(engine, "an abandoned review batch beside the open one", batch,
                         {"id": "b3", "s": "abandoned", "d": "d1", "g": "atelier"})
    counted += _admitted(engine, "an open agent batch", batch, {"id": "b4", "s": "open", "d": None, "g": None})
    counted += _admitted(engine, "a second open agent batch", batch, {"id": "b5", "s": "open", "d": None, "g": None})
    return counted


def rule_rs2(engine) -> int:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO world (id, name, is_active) VALUES ('w1', 'W', 0)"))
        conn.execute(text("INSERT INTO user (id, name, role) VALUES ('u1', 'u', 'player')"))
        conn.execute(text("INSERT INTO entity (id, world_id, type, name) VALUES ('e1', 'w1', 'character', 'E')"))
        conn.execute(text("INSERT INTO pc_draft (id, world_id, user_id) VALUES ('d1', 'w1', 'u1')"))
    return _rs2_sketches(engine) + _rs2_memberships_and_batches(engine)


def _reshape_to_v2_32(db_path: pathlib.Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in RESHAPED:
            conn.execute(f"DROP TABLE {table}")
        conn.executescript(V232_DDL)
        conn.execute("INSERT INTO world (id, name, is_active) VALUES ('world-1', 'W', 0)")
        conn.execute("INSERT INTO user (id, name, role) VALUES ('user-1', 'u', 'player')")
        for table in reversed(RESHAPED):
            columns, row = V232_ROWS[table]
            conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({', '.join('?' * len(row))})", row)
        conn.execute("INSERT INTO schema_meta (id, static_version) VALUES (1, 'v2.32')")
        conn.commit()
    finally:
        conn.close()


def _snapshot(db_path: pathlib.Path) -> tuple:
    conn = sqlite3.connect(db_path)
    try:
        master = tuple(conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name"))
        rows = tuple(tuple(conn.execute(f"SELECT * FROM {t} ORDER BY id")) for t in RESHAPED)
        meta = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()
    finally:
        conn.close()
    return master, rows, meta


def _set_version(db_path: pathlib.Path, version: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))
        conn.commit()
    finally:
        conn.close()


def _run_migration() -> int:
    proc = subprocess.run([sys.executable, str(MIGRATION)], env=dict(os.environ),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode


def _rs3b_state(conn) -> None:
    missing = False
    for table, columns in V233_COLUMNS.items():
        present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for column in columns:
            if column not in present:
                fail(f"RS3b {table}.{column} is missing after the migration")
                missing = True
    indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    if REVIEW_INDEX not in indexes:
        fail(f"RS3b {REVIEW_INDEX} is missing after the migration")
    sketch_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='pc_draft_sketch'").fetchone()[0]
    for name in SKETCH_CHECKS:
        if name not in sketch_sql:
            fail(f"RS3b the stored pc_draft_sketch SQL lacks {name}")
    for table, (columns, row) in V232_ROWS.items():
        got = [tuple(r) for r in conn.execute(f"SELECT {columns} FROM {table}")]
        if got != [row]:
            fail(f"RS3b {table} rows are {got!r}, expected {[row]!r}")
    if missing:
        return
    review = conn.execute("SELECT review_action, review_entity_id, review_relation_type, review_intensity "
                          "FROM pc_draft_sketch").fetchall()
    if review != [(None, None, "ally", 60)]:
        fail(f"RS3b the sketch's review columns read {review!r}, expected [(None, None, 'ally', 60)]")
    dropped = conn.execute("SELECT review_dropped FROM pc_draft_membership").fetchall()
    if dropped != [(0,)]:
        fail(f"RS3b the membership's review_dropped reads {dropped!r}, expected [(0,)]")
    meta = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()
    if meta is None or meta[0] != "v2.33":
        fail(f"RS3b schema_meta reads {meta!r}, expected 'v2.33'")


def rule_rs3(engine, db_path: pathlib.Path) -> int:
    reached = 0
    if not MIGRATION.exists():
        fail(f"RS3 {MIGRATION.name} missing")
        return reached
    engine.dispose()
    _reshape_to_v2_32(db_path)

    # (a) below v2.32: refused, nothing changes.
    _set_version(db_path, "v2.31")
    before = _snapshot(db_path)
    if _run_migration() == 0:
        fail("RS3a the migration exited zero at v2.31")
    if _snapshot(db_path) != before:
        fail("RS3a the refused migration changed the database")
    reached += 1

    # (b) at v2.32: applied, rows kept.
    _set_version(db_path, "v2.32")
    if _run_migration() != 0:
        fail("RS3b the migration exited non-zero at v2.32")
    conn = sqlite3.connect(db_path)
    try:
        _rs3b_state(conn)
    finally:
        conn.close()
    reached += 1

    # (c) a second run changes nothing.
    before = _snapshot(db_path)
    if _run_migration() != 0:
        fail("RS3c the second run exited non-zero")
    if _snapshot(db_path) != before:
        fail("RS3c the second run changed the database")
    reached += 1
    return reached


def main() -> int:
    engine, db_path = _fresh_engine()
    rule_rs1()
    if rule_rs2(engine) == 0:
        fail("RS2 probed nothing")
    if rule_rs3(engine, db_path) != 3:
        fail("RS3 a sub-rule was not reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: review_schema -- v2.33: the review columns, the approved character, the review batch "
          "index and the pc_creation source as C-03/C-04; the review CHECKs hold; the migration moves "
          "five tables from v2.32, keeps every row, refuses below v2.32 and changes nothing twice")
    return 0


if __name__ == "__main__":
    sys.exit(main())
