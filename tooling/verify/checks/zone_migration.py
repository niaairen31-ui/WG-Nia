"""G1 check for TICKET-0101 (BRIEF-0101-D) — migration v2.12.

Self-contained: a fresh temp-file SQLite database is built from the models,
then turned back into a v2.11-shaped one (the old
`idx_relation_oriented_social` predicate, `schema_meta` at v2.11) holding
the state the migration exists for: a location Z that has an active child C
and still a `connects_to` to V (written before C existed, as on a real v2.11
database), a `connects_to` V-W between two visitable locations, and an NPC
standing in Z with its `matin` schedule at Z. The migration runs as a
subprocess against that file (WORLD_ENGINE_DATABASE_URL), exactly as Nia runs
it. Zero outcomes in any assertion is a FAIL.

Four assertions:
  a. On a database at v2.10 the script exits non-zero and changes nothing.
  b. After a run at v2.11: the stored index SQL names `'borde'`;
     `schema_meta.static_version` is the code constant; Z-V is the same
     relation row, now `borde`, its `change_history` one longer, its fact
     content `borde_fact_content(...)` with the old content in the fact's
     `change_history`; V-W is untouched (`connects_to`, same history).
  c. T1: the output names the NPC standing in Z and its schedule; the NPC
     and its schedule row are still at Z (reported, never moved).
  d. A second run prints the zero-writes line and changes no relation row.

Named mutations: drop `_convert`'s `write_relation` call -> (b);
skip `_rebuild_index` -> (b); make `_report` move the NPC -> (c).
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
MIGRATION = ROOT / "scripts" / "migrate_v2_12_zone_borde.py"
OLD_INDEX = (
    "CREATE UNIQUE INDEX idx_relation_oriented_social ON relation(entity_a_id, entity_b_id) "
    "WHERE type NOT IN ('connects_to','controls')"
)

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    url = f"sqlite:///{db_path}"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = url
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine, url


def _set_version(engine, version: str) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM schema_meta"))
        conn.execute(text("INSERT INTO schema_meta (id, static_version, updated_at) "
                          "VALUES (1, :v, CURRENT_TIMESTAMP)"), {"v": version})


def _seed(engine) -> dict[str, str]:
    from sqlalchemy import text
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Location, NpcSchedule, World
    from world_engine.writes.relations import write_relation

    with engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_relation_oriented_social"))
        conn.execute(text(OLD_INDEX))
    ids: dict[str, str] = {}
    with Session(engine) as db:
        world = World(name="Migration check", is_active=True)
        db.add(world)
        db.commit()
        ids["world"] = world.id
        for label in ("Z", "V", "W"):
            entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
            db.add(entity)
            db.flush()
            db.add(Location(id=entity.id))
            db.commit()
            ids[label] = entity.id
        for a, b in (("Z", "V"), ("V", "W")):
            rel = write_relation(db, mode="set", world_id=world.id, entity_a_id=ids[a], entity_b_id=ids[b],
                                 type="connects_to", value=50, direction="mutual")
            db.commit()
            ids[a + b] = rel.id
        child = Entity(world_id=world.id, type="location", name="Lieu C")
        db.add(child)
        db.flush()
        db.add(Location(id=child.id, parent_location_id=ids["Z"]))
        npc = Entity(world_id=world.id, type="character", name="Sentinelle")
        db.add(npc)
        db.flush()
        db.add(Character(id=npc.id, world_id=world.id, character_type="npc", current_location_id=ids["Z"]))
        db.add(NpcSchedule(world_id=world.id, npc_id=npc.id, phase="matin", location_id=ids["Z"]))
        db.commit()
        ids["C"], ids["N"] = child.id, npc.id
    return ids


def _run(url: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=url)
    env.pop("WORLD_ENGINE_ENV", None)
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True, text=True, cwd=ROOT)


def _snapshot(engine, ids):
    from sqlmodel import Session

    from world_engine.models import Relation

    with Session(engine) as db:
        return {k: (db.get(Relation, ids[k]).type, len(db.get(Relation, ids[k]).change_history or []))
                for k in ("ZV", "VW")}


def _index_sql(engine) -> str:
    from sqlalchemy import text

    with engine.connect() as conn:
        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE name = 'idx_relation_oriented_social'")).first()
    return row[0] if row else ""


def check_a_refusal(engine, url, ids) -> None:
    _set_version(engine, "v2.10")
    before = _snapshot(engine, ids)
    proc = _run(url)
    COUNTS["a"] = 1 if proc.returncode != 0 else 0
    if proc.returncode == 0:
        fail("(a) the migration ran on a v2.10 database")
    if _snapshot(engine, ids) != before or "'borde'" in _index_sql(engine):
        fail("(a) the refused run changed the database")


def check_b_c_run(engine, url, ids) -> str:
    from sqlalchemy import text
    from sqlmodel import Session, select

    from world_engine.models import Character, NpcSchedule, Relation
    from world_engine.prose_render import entity_token
    from world_engine.relation_orientation import borde_fact_content
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.relations import lien_fact_of

    _set_version(engine, "v2.11")
    before = _snapshot(engine, ids)
    proc = _run(url)
    if proc.returncode != 0:
        fail(f"(b) the migration failed: {proc.stderr[-400:]}")
        return ""
    n = 0
    n += _ok("'borde'" in _index_sql(engine), "(b) the index predicate does not exclude 'borde'")
    with engine.connect() as conn:
        version = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).scalar()
    n += _ok(version == EXPECTED_STATIC_SCHEMA_VERSION, f"(b) schema_meta at {version!r}")
    after = _snapshot(engine, ids)
    n += _ok(after["ZV"] == ("borde", before["ZV"][1] + 1), f"(b) Z-V after the run: {after['ZV']}")
    n += _ok(after["VW"] == before["VW"], f"(b) V-W changed: {before['VW']} -> {after['VW']}")
    with Session(engine) as db:
        fact = lien_fact_of(db, db.get(Relation, ids["ZV"]))
        expected = borde_fact_content(entity_token(ids["Z"], "Lieu Z"), entity_token(ids["V"], "Lieu V"))
        n += _ok(fact is not None and fact.content_raw == expected and len(fact.change_history or []) == 1,
                 "(b) Z-V fact not rewritten with its history")
        COUNTS["b"] = n
        m = _ok("Sentinelle" in proc.stdout and "horaire matin" in proc.stdout,
                "(c) the report does not name the NPC and its schedule in the zone")
        m += _ok(db.get(Character, ids["N"]).current_location_id == ids["Z"], "(c) the NPC was moved")
        row = db.exec(select(NpcSchedule).where(NpcSchedule.npc_id == ids["N"])).one()
        m += _ok(row.location_id == ids["Z"],
                 "(c) the schedule was moved")
        COUNTS["c"] = m
    return proc.stdout


def _ok(cond: bool, msg: str) -> int:
    if not cond:
        fail(msg)
        return 0
    return 1


def check_d_rerun(engine, url, ids) -> None:
    before = _snapshot(engine, ids)
    proc = _run(url)
    n = _ok(proc.returncode == 0 and "zero writes" in proc.stdout, f"(d) second run: {proc.stdout[-200:]}")
    n += _ok(_snapshot(engine, ids) == before, "(d) the second run changed a relation")
    COUNTS["d"] = n


def main() -> int:
    engine, url = _fresh_engine()
    ids = _seed(engine)
    check_a_refusal(engine, url, ids)
    check_b_c_run(engine, url, ids)
    check_d_rerun(engine, url, ids)

    for key in ("a", "b", "c", "d"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero outcomes examined")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: zone_migration — "
        f"(a) refuses a v2.10 database [{COUNTS['a']}], (b) index + in-place borde [{COUNTS['b']}], "
        f"(c) T1 reports, never moves [{COUNTS['c']}], (d) idempotent [{COUNTS['d']}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
