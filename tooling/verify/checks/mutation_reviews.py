"""G1 check for TICKET-0115 -- the creator's review of a proposal is recorded, round by round.

BRIEF-0115-A's rules (A3 and C1 of the conditions series' dashboard): the
storage of v2.27.

MR1 -- storage (import). `mutation_review` and `mutation_review_change`
   carry exactly their contract's columns, CHECK names and index names, none
   of them JSON; `proposed_mutation` has `original_payload`, JSON and
   nullable; `REVIEW_ACTIONS`, `REVIEW_VIAS`, `REVIEW_STATUSES`,
   `STEP_VERDICTS` and `REVIEW_CHANGE_KINDS` are the values their CHECKs
   name; the code's schema version is v2.27 or later.
MR2 -- constraints (fixture). A review round 0, an action, via, status or
   verdict outside its tuple, a reject left `applied`, an approve left
   `rejected`, an edited reject or an edited batch review, a second review
   of one proposal with the same round, a change kind outside its tuple, an
   `added` change with a before value, a `removed` change with an after
   value, and one path twice in one review are each refused by the
   database; a well-formed review and change are accepted.
MR3 -- migration `scripts/migrate_v2_27_mutation_reviews.py`, on a v2.26
   database (`proposed_mutation` in its v2.26 DDL, frozen below, one row;
   no review table): at v2.25 it refuses and changes nothing; at v2.26 it
   adds the column, creates both tables, keeps the row, and sets
   `schema_meta` to v2.27; a second run writes nothing.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "scripts" / "migrate_v2_27_mutation_reviews.py"

FAILURES: list[str] = []

REVIEW_COLUMNS = ("id", "world_id", "mutation_id", "round", "action", "via", "status_after", "edited",
                  "step_verdict", "reviewed_at")
REVIEW_CHECKS = ("ck_mutation_review_action", "ck_mutation_review_edited", "ck_mutation_review_outcome",
                 "ck_mutation_review_round", "ck_mutation_review_status", "ck_mutation_review_verdict",
                 "ck_mutation_review_via")
REVIEW_INDEXES = ("idx_mutation_review_round", "idx_mutation_review_world")
CHANGE_COLUMNS = ("id", "world_id", "review_id", "path", "field", "kind", "before_value", "after_value")
CHANGE_CHECKS = ("ck_mutation_review_change_added", "ck_mutation_review_change_kind",
                 "ck_mutation_review_change_removed")
CHANGE_INDEXES = ("idx_mutation_review_change_field", "idx_mutation_review_change_path")

# `proposed_mutation` as v2.26 declared it (frozen: MR3 builds the database
# the migration was written for).
V2_26_DDL: tuple[str, ...] = (
    "CREATE TABLE schema_meta (id INTEGER NOT NULL, static_version VARCHAR NOT NULL, "
    "updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
    "CONSTRAINT ck_schema_meta_singleton CHECK (id = 1))",
    "CREATE TABLE world (id VARCHAR NOT NULL, name VARCHAR NOT NULL, PRIMARY KEY (id))",
    "CREATE TABLE proposed_mutation (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, "
    "source_type VARCHAR NOT NULL, pass_play_id VARCHAR, conversation_id VARCHAR, tick_id VARCHAR, "
    "mutation_type VARCHAR NOT NULL, target_table VARCHAR, target_id VARCHAR, payload JSON NOT NULL, "
    "status VARCHAR DEFAULT 'proposed' NOT NULL, rationale VARCHAR, creator_notes VARCHAR, "
    "proposed_by VARCHAR DEFAULT 'local_ai' NOT NULL, "
    "proposed_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, reviewed_at DATETIME, applied_at DATETIME, "
    "PRIMARY KEY (id), FOREIGN KEY(world_id) REFERENCES world (id), "
    "FOREIGN KEY(pass_play_id) REFERENCES pass_play (id), "
    "FOREIGN KEY(conversation_id) REFERENCES conversation (id))",
    "CREATE INDEX idx_mutation_status ON proposed_mutation (status)",
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


# --- MR1 -------------------------------------------------------------------------

def _shape(table, columns, checks, indexes, label: str) -> None:
    from sqlalchemy import JSON, CheckConstraint

    if table is None:
        fail(f"MR1: {label} is not declared")
        return
    if tuple(table.c.keys()) != columns:
        fail(f"MR1: {label} columns are {tuple(table.c.keys())}")
    found = tuple(sorted(c.name for c in table.constraints if isinstance(c, CheckConstraint)))
    if found != checks:
        fail(f"MR1: {label} CHECKs are {found}")
    if tuple(sorted(i.name for i in table.indexes)) != indexes:
        fail(f"MR1: {label} indexes are {sorted(i.name for i in table.indexes)}")
    if any(isinstance(c.type, JSON) for c in table.c):
        fail(f"MR1: {label} holds a JSON column")


def _check_values(table, name: str) -> str:
    from sqlalchemy import CheckConstraint

    return next((str(c.sqltext) for c in table.constraints
                 if isinstance(c, CheckConstraint) and c.name == name), "")


def check_mr1() -> None:
    from sqlalchemy import JSON
    from sqlmodel import SQLModel

    from world_engine import models
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    tables = SQLModel.metadata.tables
    review, change = tables.get("mutation_review"), tables.get("mutation_review_change")
    _shape(review, REVIEW_COLUMNS, REVIEW_CHECKS, REVIEW_INDEXES, "mutation_review")
    _shape(change, CHANGE_COLUMNS, CHANGE_CHECKS, CHANGE_INDEXES, "mutation_review_change")
    column = tables["proposed_mutation"].c.get("original_payload")
    if column is None or not isinstance(column.type, JSON) or not column.nullable:
        fail("MR1: proposed_mutation.original_payload is not a nullable JSON column")
    if review is None or change is None:
        return
    pairs = (
        (models.REVIEW_ACTIONS, _check_values(review, "ck_mutation_review_action")),
        (models.REVIEW_VIAS, _check_values(review, "ck_mutation_review_via")),
        (models.REVIEW_STATUSES, _check_values(review, "ck_mutation_review_status")),
        (models.STEP_VERDICTS, _check_values(review, "ck_mutation_review_verdict")),
        (models.REVIEW_CHANGE_KINDS, _check_values(change, "ck_mutation_review_change_kind")),
    )
    for values, sql in pairs:
        if not values or any(f"'{v}'" not in sql for v in values) or sql.count("'") != 2 * len(values):
            fail(f"MR1: the tuple {values} is not its CHECK's values ({sql})")
    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 27):
        fail(f"MR1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")


# --- MR2 -------------------------------------------------------------------------

def _refused(engine, sql: str) -> bool:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    with engine.connect() as conn:
        try:
            conn.execute(text(sql))
            conn.rollback()
            return False
        except IntegrityError:
            conn.rollback()
            return True


def check_mr2(engine) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO world (id, name, created_at) VALUES ('w', 'Monde', '2026-10-12')"))
        conn.execute(text("INSERT INTO proposed_mutation (id, world_id, source_type, mutation_type, payload) "
                          "VALUES ('pm', 'w', 'conversation', 'event_creation', '{}')"))
        conn.execute(text("INSERT INTO mutation_review (id, world_id, mutation_id, round, action, via, "
                          "status_after, edited) VALUES ('r1', 'w', 'pm', 1, 'approve', 'unit', 'applied', 1)"))
        conn.execute(text("INSERT INTO mutation_review_change (id, world_id, review_id, path, field, kind, "
                          "before_value, after_value) VALUES ('c1', 'w', 'r1', 'title', 'title', 'changed', "
                          "'\"a\"', '\"b\"')"))

    def review(rid: str, round_: str = "2", action: str = "approve", via: str = "unit", status: str = "applied",
               edited: str = "0", verdict: str = "NULL") -> str:
        return ("INSERT INTO mutation_review (id, world_id, mutation_id, round, action, via, status_after, edited, "
                f"step_verdict) VALUES ('{rid}', 'w', 'pm', {round_}, '{action}', '{via}', '{status}', {edited}, "
                f"{verdict})")

    def change(cid: str, path: str = "x", kind: str = "changed", before: str = "NULL", after: str = "NULL") -> str:
        return ("INSERT INTO mutation_review_change (id, world_id, review_id, path, field, kind, before_value, "
                f"after_value) VALUES ('{cid}', 'w', 'r1', '{path}', '{path}', '{kind}', {before}, {after})")

    refused = {
        "round 0": review("a", round_="0"),
        "an unknown action": review("b", action="defer"),
        "an unknown via": review("c", via="script"),
        "an unknown status": review("d", status="proposed", action="approve"),
        "an unknown verdict": review("e", verdict="'true'"),
        "a reject left applied": review("f", action="reject", status="applied"),
        "an approve left rejected": review("g", status="rejected"),
        "an edited reject": review("h", action="reject", status="rejected", edited="1"),
        "an edited batch review": review("i", via="batch", edited="1"),
        "a second round 1": review("j", round_="1"),
        "an unknown change kind": change("k", kind="moved"),
        "an added change with a before value": change("l", kind="added", before="'1'"),
        "a removed change with an after value": change("m", kind="removed", after="'1'"),
        "one path twice in one review": change("n", path="title"),
    }
    for label, sql in refused.items():
        if not _refused(engine, sql):
            fail(f"MR2: {label} was accepted")
    accepted = (review("ok", verdict="'not_judged'"), change("ok2", path="participants[Cible].entity_id",
                                                            kind="added", after="'\"e\"'"))
    for sql in accepted:
        if _refused(engine, sql):
            fail(f"MR2: a well-formed row was refused: {sql}")


# --- MR3 -------------------------------------------------------------------------

def _v2_26_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "v2_26.db")
    with sqlite3.connect(db_path) as conn:
        for statement in V2_26_DDL:
            conn.execute(statement)
        conn.executescript("""
            INSERT INTO schema_meta (id, static_version) VALUES (1, 'v2.25');
            INSERT INTO world (id, name) VALUES ('w', 'Monde');
            INSERT INTO proposed_mutation (id, world_id, source_type, mutation_type, payload)
              VALUES ('pm', 'w', 'conversation', 'event_creation', '{"title": "t"}');
        """)
    return db_path


def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


def _snapshot(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        def sql(name: str) -> str:
            row = conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (name,)).fetchone()
            return row[0] if row else ""
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "column": "original_payload" in [r[1] for r in conn.execute("PRAGMA table_info(proposed_mutation)")],
            "review": bool(sql("mutation_review")) and bool(sql("idx_mutation_review_round")),
            "change": bool(sql("mutation_review_change")) and bool(sql("idx_mutation_review_change_path")),
            "rows": conn.execute("SELECT id, payload FROM proposed_mutation").fetchall(),
        }


def check_mr3() -> None:
    if not MIGRATION.exists():
        fail(f"MR3: {MIGRATION.name} not found")
        return
    db_path = _v2_26_db()
    before = _snapshot(db_path)
    refused = _run_migration(db_path)
    if refused.returncode == 0 or _snapshot(db_path) != before:
        fail(f"MR3: v2.25 was not refused untouched (exit {refused.returncode})")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.26' WHERE id = 1")
    result = _run_migration(db_path)
    after = _snapshot(db_path)
    want = {"version": "v2.27", "column": True, "review": True, "change": True,
            "rows": [("pm", '{"title": "t"}')]}
    if result.returncode != 0 or after != want:
        fail(f"MR3: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "already fully applied" not in again.stdout or _snapshot(db_path) != after:
        fail(f"MR3: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")


def main() -> None:
    _fresh_db()
    from sqlmodel import SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    check_mr1()
    check_mr2(engine)
    check_mr3()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: mutation_reviews -- v2.27 stores a review round by round and its changes; the migration "
          "refuses below v2.26 and runs once")


if __name__ == "__main__":
    main()
