"""G1 check for TICKET-0125 (BRIEF-0125-B) -- schema v2.31: a world opens to players and the Lore journal admits the perspective kind.

PS1 -- static. `World.open_to_players` exists, NOT NULL, server default `0`;
   `LORE_USAGE_STEPS["perspective"] == ("perspective_ask",
   "perspective_resolve")`; `writes/lore_usage.PAYLOAD_KEYS` holds both steps
   with exactly C-09's keys.
PS2 -- migration. A fresh fixture is reshaped to v2.30 (`world` loses
   `open_to_players`; `lore_usage_event` is recreated with the literal DDL of
   `migrate_v2_13_lore_usage.py`'s `_create_table`, imported; one journal row
   inserted raw; `schema_meta` at v2.30), then
   `scripts/migrate_v2_31_player_entry.py` runs as a subprocess on it:
   (a) at v2.29 it exits non-zero and changes nothing;
   (b) at v2.30 it exits zero, `world.open_to_players` exists with default 0,
       the stored journal SQL holds `'perspective_ask'`, the raw row is still
       there unchanged, `schema_meta` reads v2.31;
   (c) a second run exits zero and changes nothing;
   (d) a row written by `write_usage_event` with kind `perspective` reads
       back, and a raw INSERT with kind `perspective`, step `ask` is refused
       by the database.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A sub-rule not reached is a FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
MIGRATION = SCRIPTS / "migrate_v2_31_player_entry.py"

C09_KEYS = {
    "perspective_ask": {"question", "perspective", "asked_by", "response", "withheld", "error"},
    "perspective_resolve": {"question", "perspective", "asked_by", "plan", "bindings", "response",
                            "withheld", "error"},
}
RAW_ROW = ("raw-1", "attempt-1", "world-1", "Monde", "consult", "ask", "ok",
           '{"question": "q", "response": "r", "error": null}', "[]", None, "2026-01-01 00:00:00")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    sys.path.insert(0, str(SCRIPTS))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    return engine


def rule_ps1() -> None:
    from world_engine.models import World
    from world_engine.models.pipeline import LORE_USAGE_STEPS
    from world_engine.writes.lore_usage import PAYLOAD_KEYS

    column = World.__table__.columns.get("open_to_players")
    if column is None:
        fail("PS1 World has no open_to_players column")
    else:
        if column.nullable:
            fail("PS1 World.open_to_players is nullable")
        default = column.server_default
        if default is None or str(getattr(default, "arg", default)) != "0":
            fail(f"PS1 World.open_to_players server default is {default!r}, expected 0")
    steps = LORE_USAGE_STEPS.get("perspective")
    if steps != ("perspective_ask", "perspective_resolve"):
        fail(f"PS1 LORE_USAGE_STEPS['perspective'] is {steps!r}")
    for step, keys in C09_KEYS.items():
        got = PAYLOAD_KEYS.get(step)
        if got is None or set(got) != keys:
            fail(f"PS1 PAYLOAD_KEYS[{step!r}] is {sorted(got) if got else got!r}, expected {sorted(keys)}")


def _columns(conn, table: str) -> dict[str, tuple]:
    from sqlalchemy import text

    return {row[1]: tuple(row) for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def _snapshot(engine) -> tuple:
    from sqlalchemy import text

    with engine.connect() as conn:
        tables = tuple(conn.execute(text(
            "SELECT name, sql FROM sqlite_master WHERE name IN ('world', 'lore_usage_event') "
            "OR tbl_name = 'lore_usage_event' ORDER BY name")).fetchall())
        rows = tuple(conn.execute(text("SELECT * FROM lore_usage_event ORDER BY id")).fetchall())
        meta = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).scalar_one()
    return tables, rows, meta


def _set_version(engine, version: str) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("UPDATE schema_meta SET static_version = :v WHERE id = 1"), {"v": version})


def _reshape_to_v2_30(engine) -> None:
    from sqlalchemy import text

    import migrate_v2_13_lore_usage

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE world DROP COLUMN open_to_players"))
        conn.execute(text("DROP TABLE lore_usage_event"))
    migrate_v2_13_lore_usage._create_table()
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO lore_usage_event (id, attempt_id, world_ref, world_name, kind, step, outcome, "
            "payload, model_calls, lore_entry_ref, created_at) VALUES "
            "(:a, :b, :c, :d, :e, :f, :g, :h, :i, :j, :k)"),
            dict(zip("abcdefghijk", RAW_ROW)))
        conn.execute(text("INSERT INTO schema_meta (id, static_version) VALUES (1, 'v2.30')"))


def _run_migration(engine) -> int:
    engine.dispose()
    proc = subprocess.run([sys.executable, str(MIGRATION)], env=dict(os.environ),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode


def rule_ps2(engine) -> int:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlmodel import Session

    from world_engine.models import LoreUsageEvent
    from world_engine.writes.lore_usage import write_usage_event

    reached = 0
    if not MIGRATION.exists():
        fail(f"PS2 {MIGRATION.name} missing")
        return reached
    _reshape_to_v2_30(engine)
    with engine.connect() as conn:
        if "open_to_players" in _columns(conn, "world"):
            fail("PS2 fixture: world still holds open_to_players after the reshape")
            return reached

    # (a) below v2.30: refused, nothing changes.
    _set_version(engine, "v2.29")
    before = _snapshot(engine)
    if _run_migration(engine) == 0:
        fail("PS2a the migration exited zero at v2.29")
    if _snapshot(engine) != before:
        fail("PS2a the refused migration changed the database")
    reached += 1

    # (b) at v2.30: applied.
    _set_version(engine, "v2.30")
    if _run_migration(engine) != 0:
        fail("PS2b the migration exited non-zero at v2.30")
    with engine.connect() as conn:
        column = _columns(conn, "world").get("open_to_players")
        if column is None:
            fail("PS2b world lacks open_to_players")
        elif column[3] != 1 or str(column[4]) != "0":
            fail(f"PS2b world.open_to_players is {column!r}, expected NOT NULL DEFAULT 0")
    tables, rows, meta = _snapshot(engine)
    journal_sql = dict((name, sql) for name, sql in tables).get("lore_usage_event") or ""
    if "'perspective_ask'" not in journal_sql:
        fail("PS2b the stored lore_usage_event SQL lacks 'perspective_ask'")
    if [tuple(r) for r in rows] != [RAW_ROW]:
        fail(f"PS2b the journal rows are {rows!r}, expected the raw row unchanged")
    if meta != "v2.31":
        fail(f"PS2b schema_meta reads {meta!r}, expected 'v2.31'")
    reached += 1

    # (c) a second run changes nothing.
    before = _snapshot(engine)
    if _run_migration(engine) != 0:
        fail("PS2c the second run exited non-zero")
    if _snapshot(engine) != before:
        fail("PS2c the second run changed the database")
    reached += 1

    # (d) the perspective kind is admitted; a cross-kind step is refused.
    with Session(engine) as db:
        payload = {key: None for key in C09_KEYS["perspective_ask"]}
        payload.update(question="q", perspective="public", asked_by="creator", withheld=[])
        event = write_usage_event(db, attempt_id="attempt-2", world_ref="world-1", world_name="Monde",
                                  kind="perspective", step="perspective_ask", outcome="ok",
                                  payload=payload, model_calls=[])
        db.commit()
        event_id = event.id
    with Session(engine) as db:
        back = db.get(LoreUsageEvent, event_id)
        if back is None or back.kind != "perspective" or back.step != "perspective_ask":
            fail(f"PS2d the perspective row does not read back: {back!r}")
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO lore_usage_event (id, attempt_id, world_ref, world_name, kind, step, "
                "outcome, payload) VALUES ('raw-2', 'a', 'w', 'W', 'perspective', 'ask', 'ok', '{}')"))
        fail("PS2d a raw perspective/ask row was accepted by the database")
    except IntegrityError:
        pass
    reached += 1
    return reached


def main() -> int:
    engine = _fresh_engine()
    try:
        rule_ps1()
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"PS1 raised {type(exc).__name__}: {exc}")
    reached = 0
    try:
        reached = rule_ps2(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"PS2 raised {type(exc).__name__}: {exc}")
    if reached != 4:
        fail(f"PS2 reached {reached} of its 4 sub-rules")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: player_entry_schema -- v2.31: world.open_to_players and the perspective journal kind, "
          "migration idempotent and refusing below v2.30")
    return 0


if __name__ == "__main__":
    sys.exit(main())
