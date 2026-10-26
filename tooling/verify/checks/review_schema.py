"""G1 check for TICKET-0129 (BRIEF-0129-B) -- schema v2.33: the creator's review columns, the approved character, the review batches and the encounter source.

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
    if rule_rs3(engine, db_path) != 3:
        fail("RS3 a sub-rule was not reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: review_schema -- the v2.32 migration moves five tables to v2.33, keeps every row, "
          "refuses below v2.32 and changes nothing twice")
    return 0


if __name__ == "__main__":
    sys.exit(main())
