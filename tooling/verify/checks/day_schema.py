"""G1 check for TICKET-0128 (BRIEF-0128-A) -- schema v2.34: the active player character, the day's pin, its publication and its failures.

DS1 -- static, by import. `World.active_pc_id` is nullable with one FK to
   `character.id` whose `ondelete` is `SET NULL`; `PassPlay.quest_id` is
   nullable with an FK to `quest.id`; `published_text` and `published_at`
   are nullable with no FK; `day_run_failure` has exactly C-01's columns
   (`world_id`, `pass_play_id` not null with their FKs), the CHECKs
   `ck_day_run_failure_stage` and `ck_day_run_failure_code`, and the indexes
   `idx_day_run_failure_pass_play` (`pass_play_id`, `created_at`) and
   `idx_day_run_failure_world` (`world_id`, `created_at`); none of these
   columns is JSON (INV-20); `models.DAY_RUN_STAGES` and
   `models.DAY_RUN_FAILURE_CODES` equal C-01's tuples and, with
   `DayRunFailure`, are in `models.__all__`;
   `PASS_PLAY_STATUSES[-1] == "abandoned"`; `"day_run_failure"` is in
   `_DIRECT_WORLD_SCOPED_DELETES`; `EXPECTED_STATIC_SCHEMA_VERSION ==
   "v2.34"`; `scripts/migrate_v2_34_player_day.py` exists with
   `_PREVIOUS_VERSION = "v2.33"` (read by `ast`).
DS2 -- fixture after `create_all`, raw INSERTs. A failure with stage `x` is
   refused, one with code `x` refused, one with `("plan", "crashed")`
   admitted. A world whose `active_pc_id` names a player character: a raw
   `DELETE FROM character` of it, then of its `entity`, leaves
   `world.active_pc_id` NULL.
DS3 -- migration, subprocess. The fixture creates every table, drops
   `day_run_failure`, rebuilds `world` and `pass_play` from the literal
   `V233_DDL` (as stored at `055b890`), inserts one world, one session,
   three batches (`processed_at`, `final_result = "Récit"`) and three days
   on them (`resolved`, `resolving`, `submitted`):
   (a) at `schema_meta` v2.32 the script exits non-zero and nothing changes;
   (b) at v2.33 it exits zero: the four columns, the table and both indexes
       exist; the `resolved` day reads `published_text = "Récit"` and
       `published_at` = its batch's `processed_at`; the other two read NULL;
       `schema_meta` reads v2.34;
   (c) the `resolving` day is set `resolved` raw and the script run again:
       it exits zero, prints « Nothing to do. », and that day stays
       unpublished (W1 ran once).

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
MIGRATION = ROOT / "scripts" / "migrate_v2_34_player_day.py"

FAILURES: list[str] = []

STAGES = ("plan", "resolve")
CODES = ("model_failed", "blocked", "rejected", "refused", "crashed", "interrupted")
FAILURE_COLUMNS = {"id", "world_id", "pass_play_id", "stage", "code", "reason", "created_at"}
FAILURE_CHECKS = {"ck_day_run_failure_stage", "ck_day_run_failure_code"}
FAILURE_INDEXES = {
    "idx_day_run_failure_pass_play": ["pass_play_id", "created_at"],
    "idx_day_run_failure_world": ["world_id", "created_at"],
}
NEW_COLUMNS = (("world", "active_pc_id"), ("pass_play", "quest_id"),
               ("pass_play", "published_text"), ("pass_play", "published_at"))
PROCESSED_AT = "2026-01-02 03:04:05.000000"

# The v2.33 shape of `world` and `pass_play`, as stored at `055b890`
# (BRIEF-0128-A, R-36).
V233_DDL = (
    "CREATE TABLE world (\n\tid VARCHAR NOT NULL, \n\tname VARCHAR NOT NULL, \n\tdescription VARCHAR, "
    "\n\ttone VARCHAR, \n\topen_to_players BOOLEAN DEFAULT 0 NOT NULL, \n\tis_active BOOLEAN DEFAULT 0 "
    "NOT NULL, \n\tcurrent_phase VARCHAR DEFAULT 'matin' NOT NULL, \n\tcreated_at DATETIME DEFAULT "
    "CURRENT_TIMESTAMP NOT NULL, \n\tupdated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tPRIMARY "
    "KEY (id), \n\tCONSTRAINT ck_world_current_phase CHECK (current_phase IN "
    "('matin','apres-midi','soir','nuit'))\n);\n"
    "CREATE UNIQUE INDEX idx_world_one_active ON world (is_active) WHERE is_active = 1;\n"
    "CREATE TABLE pass_play (\n\tid VARCHAR NOT NULL, \n\tbatch_id VARCHAR NOT NULL, \n\tsession_id "
    "VARCHAR NOT NULL, \n\tcharacter_id VARCHAR NOT NULL, \n\tagenda_id VARCHAR, \n\tdeclared_action "
    "VARCHAR NOT NULL, \n\tinjected_context JSON, \n\tcreator_notes VARCHAR, \n\tstatus VARCHAR DEFAULT "
    "'submitted' NOT NULL, \n\tbatch_order INTEGER, \n\thistory JSON DEFAULT '[]' NOT NULL, "
    "\n\tsubmitted_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, \n\tapplied_at DATETIME, \n\tPRIMARY "
    "KEY (id), \n\tFOREIGN KEY(batch_id) REFERENCES batch (id), \n\tFOREIGN KEY(session_id) REFERENCES "
    "session (id), \n\tFOREIGN KEY(character_id) REFERENCES entity (id), \n\tFOREIGN KEY(agenda_id) "
    "REFERENCES agenda (id)\n);\n"
    "CREATE INDEX idx_passplay_batch ON pass_play (batch_id);\n"
    "CREATE INDEX idx_passplay_agenda ON pass_play (agenda_id);\n"
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


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


# --- DS1 ---------------------------------------------------------------------
def _fk_targets(column) -> list[tuple[str, str | None]]:
    return sorted((fk.target_fullname, fk.ondelete) for fk in column.foreign_keys)


def _ds1_columns() -> int:
    from sqlalchemy import JSON
    from sqlmodel import SQLModel

    tables = SQLModel.metadata.tables
    expected = {
        ("world", "active_pc_id"): [("character.id", "SET NULL")],
        ("pass_play", "quest_id"): [("quest.id", None)],
        ("pass_play", "published_text"): [],
        ("pass_play", "published_at"): [],
    }
    reached = 0
    for (table, name), targets in expected.items():
        column = tables[table].columns.get(name)
        if column is None:
            fail(f"DS1 {table}.{name} is missing")
            continue
        if not column.nullable:
            fail(f"DS1 {table}.{name} is NOT NULL")
        if _fk_targets(column) != targets:
            fail(f"DS1 {table}.{name} FKs are {_fk_targets(column)!r}, expected {targets!r}")
        if isinstance(column.type, JSON):
            fail(f"DS1 {table}.{name} is JSON (INV-20)")
        reached += 1

    failure = tables.get("day_run_failure")
    if failure is None:
        fail("DS1 day_run_failure is not a table of the metadata")
        return reached
    names = {c.name for c in failure.columns}
    if names != FAILURE_COLUMNS:
        fail(f"DS1 day_run_failure columns are {sorted(names)}, expected {sorted(FAILURE_COLUMNS)}")
    for name, target in (("world_id", "world.id"), ("pass_play_id", "pass_play.id")):
        column = failure.columns.get(name)
        if column is None or column.nullable or [t for t, _ in _fk_targets(column)] != [target]:
            fail(f"DS1 day_run_failure.{name} is not a NOT NULL FK to {target}")
    json_columns = [c.name for c in failure.columns if isinstance(c.type, JSON)]
    if json_columns:
        fail(f"DS1 day_run_failure has JSON columns {json_columns} (INV-20)")
    checks = {c.name for c in failure.constraints if c.__class__.__name__ == "CheckConstraint"}
    if checks != FAILURE_CHECKS:
        fail(f"DS1 day_run_failure CHECKs are {sorted(checks)}, expected {sorted(FAILURE_CHECKS)}")
    indexes = {i.name: [c.name for c in i.columns] for i in failure.indexes}
    if indexes != FAILURE_INDEXES:
        fail(f"DS1 day_run_failure indexes are {indexes!r}, expected {FAILURE_INDEXES!r}")
    return reached + 1


def _ds1_constants() -> int:
    from world_engine import models
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes import pipeline, worlds

    if getattr(models, "DAY_RUN_STAGES", None) != STAGES:
        fail(f"DS1 models.DAY_RUN_STAGES is {getattr(models, 'DAY_RUN_STAGES', None)!r}")
    if getattr(models, "DAY_RUN_FAILURE_CODES", None) != CODES:
        fail(f"DS1 models.DAY_RUN_FAILURE_CODES is {getattr(models, 'DAY_RUN_FAILURE_CODES', None)!r}")
    for name in ("DayRunFailure", "DAY_RUN_STAGES", "DAY_RUN_FAILURE_CODES"):
        if name not in models.__all__:
            fail(f"DS1 {name} is not in models.__all__")
    if pipeline.PASS_PLAY_STATUSES[-1] != "abandoned":
        fail(f"DS1 PASS_PLAY_STATUSES is {pipeline.PASS_PLAY_STATUSES!r}")
    if "day_run_failure" not in worlds._DIRECT_WORLD_SCOPED_DELETES:
        fail("DS1 day_run_failure is not in _DIRECT_WORLD_SCOPED_DELETES")
    if EXPECTED_STATIC_SCHEMA_VERSION != "v2.34":
        fail(f"DS1 EXPECTED_STATIC_SCHEMA_VERSION is {EXPECTED_STATIC_SCHEMA_VERSION!r}")
    if not MIGRATION.exists():
        fail(f"DS1 {MIGRATION.name} is missing")
        return 1
    previous = None
    for node in ast.parse(MIGRATION.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_PREVIOUS_VERSION" for t in node.targets):
            previous = getattr(node.value, "value", None)
    if previous != "v2.33":
        fail(f"DS1 the migration's _PREVIOUS_VERSION is {previous!r}, expected 'v2.33'")
    return 1


def rule_ds1() -> int:
    return _ds1_columns() + _ds1_constants()


# --- DS2 ---------------------------------------------------------------------
def _raises(engine, sql: str, params: dict | None = None) -> bool:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    try:
        with engine.begin() as conn:
            conn.execute(text(sql), params or {})
    except IntegrityError:
        return True
    return False


_FAILURE_INSERT = ("INSERT INTO day_run_failure (id, world_id, pass_play_id, stage, code, reason) "
                   "VALUES (:id, 'w1', 'pp1', :stage, :code, 'r')")


def rule_ds2(engine) -> int:
    from sqlalchemy import text

    reached = 0
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO world (id, name, is_active) VALUES ('w1', 'W', 0)"))
        conn.execute(text("INSERT INTO entity (id, world_id, type, name) VALUES ('pc1', 'w1', 'character', 'P')"))
        conn.execute(text("INSERT INTO character (id, world_id, character_type) VALUES ('pc1', 'w1', 'player')"))
        conn.execute(text("INSERT INTO session (id, world_id, number) VALUES ('s1', 'w1', 1)"))
        conn.execute(text("INSERT INTO batch (id, session_id, day_number) VALUES ('b1', 's1', 1)"))
        conn.execute(text("INSERT INTO pass_play (id, batch_id, session_id, character_id, declared_action) "
                          "VALUES ('pp1', 'b1', 's1', 'pc1', 'a')"))
    for label, stage, code, refused in (("stage 'x'", "x", "crashed", True),
                                        ("code 'x'", "plan", "x", True),
                                        ("('plan', 'crashed')", "plan", "crashed", False)):
        got = _raises(engine, _FAILURE_INSERT, {"id": f"f-{reached}", "stage": stage, "code": code})
        if got != refused:
            fail(f"DS2 a failure with {label} was {'admitted' if refused else 'refused'}")
        reached += 1

    with engine.begin() as conn:
        conn.execute(text("UPDATE world SET active_pc_id = 'pc1' WHERE id = 'w1'"))
        conn.execute(text("DELETE FROM day_run_failure"))
        conn.execute(text("DELETE FROM pass_play"))
    if _raises(engine, "DELETE FROM character WHERE id = 'pc1'") or _raises(
            engine, "DELETE FROM entity WHERE id = 'pc1'"):
        fail("DS2 deleting the world's active PC was refused under FK enforcement")
        return reached
    with engine.connect() as conn:
        active = conn.execute(text("SELECT active_pc_id FROM world WHERE id = 'w1'")).scalar_one()
    if active is not None:
        fail(f"DS2 world.active_pc_id reads {active!r} after its character was deleted, expected NULL")
    return reached + 1


# --- DS3 ---------------------------------------------------------------------
def _reshape_to_v2_33(db_path: pathlib.Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in ("day_run_failure", "pass_play", "world"):
            conn.execute(f"DROP TABLE {table}")
        conn.executescript(V233_DDL)
        for table in ("schema_meta", "batch", "session", "character", "entity"):
            conn.execute(f"DELETE FROM {table}")  # DS2's rows
        conn.execute("INSERT INTO world (id, name, is_active) VALUES ('w1', 'W', 0)")
        conn.execute("INSERT INTO entity (id, world_id, type, name) VALUES ('pc1', 'w1', 'character', 'P')")
        conn.execute("INSERT INTO character (id, world_id, character_type) VALUES ('pc1', 'w1', 'player')")
        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('s1', 'w1', 1)")
        for day, status in enumerate(("resolved", "resolving", "submitted"), start=1):
            conn.execute("INSERT INTO batch (id, session_id, day_number, processed_at, final_result) "
                         "VALUES (?, 's1', ?, ?, 'Récit')", (f"b{day}", day, PROCESSED_AT))
            conn.execute("INSERT INTO pass_play (id, batch_id, session_id, character_id, declared_action, "
                         "status) VALUES (?, ?, 's1', 'pc1', 'a', ?)", (f"pp-{status}", f"b{day}", status))
        conn.execute("INSERT INTO schema_meta (id, static_version) VALUES (1, 'v2.32')")
        conn.commit()
    finally:
        conn.close()


def _snapshot(db_path: pathlib.Path) -> tuple:
    conn = sqlite3.connect(db_path)
    try:
        master = tuple(conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name"))
        rows = tuple(tuple(conn.execute(f"SELECT * FROM {t} ORDER BY id")) for t in ("world", "pass_play"))
        meta = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()
    finally:
        conn.close()
    return master, rows, meta


def _execute(db_path: pathlib.Path, sql: str, params: tuple = ()) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _run_migration() -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(MIGRATION)], env=dict(os.environ),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _published(conn) -> dict[str, tuple]:
    return {pid: (text_, at) for pid, text_, at in
            conn.execute("SELECT id, published_text, published_at FROM pass_play")}


def _ds3b_state(db_path: pathlib.Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for table, column in NEW_COLUMNS:
            if column not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
                fail(f"DS3b {table}.{column} is missing after the migration")
                return
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "day_run_failure" not in tables:
            fail("DS3b day_run_failure is missing after the migration")
        indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
        for name in FAILURE_INDEXES:
            if name not in indexes:
                fail(f"DS3b {name} is missing after the migration")
        expected = {"pp-resolved": ("Récit", PROCESSED_AT), "pp-resolving": (None, None),
                    "pp-submitted": (None, None)}
        got = _published(conn)
        if got != expected:
            fail(f"DS3b the days read {got!r}, expected {expected!r}")
        meta = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()
        if meta is None or meta[0] != "v2.34":
            fail(f"DS3b schema_meta reads {meta!r}, expected 'v2.34'")
    finally:
        conn.close()


def rule_ds3(engine, db_path: pathlib.Path) -> int:
    reached = 0
    if not MIGRATION.exists():
        fail(f"DS3 {MIGRATION.name} missing")
        return reached
    engine.dispose()
    _reshape_to_v2_33(db_path)

    # (a) at v2.32: refused, nothing changes.
    before = _snapshot(db_path)
    if _run_migration().returncode == 0:
        fail("DS3a the migration exited zero at v2.32")
    if _snapshot(db_path) != before:
        fail("DS3a the refused migration changed the database")
    reached += 1

    # (b) at v2.33: applied, W1 publishes the resolved day only.
    _execute(db_path, "UPDATE schema_meta SET static_version = 'v2.33' WHERE id = 1")
    proc = _run_migration()
    if proc.returncode != 0:
        fail(f"DS3b the migration exited {proc.returncode} at v2.33: {proc.stderr.strip()[-300:]}")
    _ds3b_state(db_path)
    reached += 1

    # (c) W1 ran once: a day resolved after it stays unpublished.
    _execute(db_path, "UPDATE pass_play SET status = 'resolved' WHERE id = 'pp-resolving'")
    proc = _run_migration()
    if proc.returncode != 0:
        fail(f"DS3c the second run exited {proc.returncode}")
    if "Nothing to do." not in proc.stdout:
        fail("DS3c the second run did not print « Nothing to do. »")
    conn = sqlite3.connect(db_path)
    try:
        if _published(conn).get("pp-resolving") != (None, None):
            fail("DS3c the day resolved after the migration was published by a second run")
    finally:
        conn.close()
    reached += 1
    return reached


def main() -> int:
    engine, db_path = _fresh_engine()
    if rule_ds1() == 0:
        fail("DS1 collected nothing")
    if rule_ds2(engine) != 4:
        fail("DS2 a sub-rule was not reached")
    if rule_ds3(engine, db_path) != 3:
        fail("DS3 a sub-rule was not reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: day_schema -- v2.34 (DS1-DS3): world.active_pc_id (SET NULL), pass_play's pin and "
          "publication, day_run_failure with its CHECKs and indexes; the migration refuses below v2.33, "
          "publishes the resolved days once (W1) and changes nothing twice")
    return 0


if __name__ == "__main__":
    sys.exit(main())
