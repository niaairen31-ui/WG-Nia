"""G1 check for TICKET-0105 -- what a character keeps of a fact.

The lot adds its pieces brief by brief; this check grows with it (the
`lore_write.py` precedent, TICKET-0098). Each brief adds its rules here in
the same commit.

A1 -- schema (BRIEF-0105-A, v2.14). `passage` declares exactly the columns
   `id, world_id, entity_id, location_id, last_at`, `last_at` NOT NULL, the
   UNIQUE index `idx_passage_entity_location (entity_id, location_id)` and
   the index `idx_passage_location (location_id)`; `rencontre` declares a
   nullable `last_at`. The `tenue` facet presets `rencontre`.
A2 -- migration `scripts/migrate_v2_14_passage.py`, on a v2.13-shaped
   database (the current schema without `passage` and without
   `rencontre.last_at`, `schema_meta` at v2.13), filled with: a character at
   a place, an NPC with a schedule row at another place, a player with two
   visits of a third place, an encounter dated 2020, a `tenue` fact with one
   participant and no default, a `tenue` fact with two participants:
   a. at v2.12 it refuses (non-zero exit) and creates nothing;
   b. at v2.13 it creates `passage` and `rencontre.last_at` with the
      model's shape, gives the one-participant `tenue` a `rencontre` default
      on its participant at `knows` and leaves the other without one, dates
      the encounter no earlier than that default, fills exactly the three
      passages (the visit at its latest `entered_at`), and moves
      `schema_meta` to the code's version;
   c. a second run exits zero and changes no row.

B1 -- one writer (BRIEF-0105-B, AST). No `Passage(` call under `src/` or
   `scripts/` outside `src/world_engine/passages.py` and
   `scripts/migrate_v2_14_passage.py`; the text `UPDATE passage` /
   `DELETE FROM passage` (case-insensitive) appears nowhere in `src/`.
B2 -- the listener. `src/world_engine/db.py` imports `passages`, and
   `passages.listener_registered()` is true once `world_engine.db` is
   imported.
B3 -- every placement is a passage (fixture): a character created at L1;
   moved to L2 by `write_character_location`; moved to L3 by assigning
   `current_location_id` (the travel path); each flush leaves exactly the
   passages of the places entered and left, `last_at` never moving back;
   recording one pair twice in one flush leaves one row; an NPC schedule
   at L4, then replaced by one at L5, leaves passages at L4 and L5.
B4 -- encounters move their last contact (fixture): a new pair has
   `last_at == first_at`; a later `visit` encounter moves `last_at` and
   keeps `first_at` and the row count; a later `relation` encounter and an
   earlier `gathering` one move nothing.

C1 -- the kind of a rewrite (BRIEF-0105-C, fixture). `update_fact_content`
   without `kind` raises `TypeError`; with a kind outside
   `FACT_CHANGE_KINDS` it raises `ValueError` and appends nothing; with
   `correction` and `changement` each history entry carries its kind.
C2 -- every rewrite names its kind (AST). Every call to
   `update_fact_content`, `update_typed_fact_content` and
   `edit_entity_fact` under `src/` and `scripts/` passes `kind=`; the
   literal is `correction` in `writes/mentions.py::bind_mention` and
   `writes/relations.py::_refresh_map_content`, `changement` in
   `writes/relations.py::_refresh_lien_content`.
C3 -- the version known (`fact_versions.version_text`, pure). History:
   correction at t1, changement at t2 (text before it "v1"), correction at
   t3, changement at t4 (text before it "v2b"), current "v3", and one entry
   without kind at t5 (text "old"). As of t0 < t1 and as of t1.5 -> "v1";
   as of t2.5 and t3.5 -> "v2b"; as of t4.5 and t6 -> "v3"; as of None ->
   "v3".

D1 -- resolution dated by contact (BRIEF-0105-D, fixture, times t0 < t1 <
   t2 < t3 before now), each row on `resolve_knowledge` AND
   `resolve_known_for_entity` (absent from the batch = `unaware`):
   a. a place passed at t1, its default written at t2 -> unaware;
   b. a place passed at t1, its default written at t0 -> its level, kept
      after leaving;
   c. a zone's default at t0, a place inside it passed at t1 -> known;
   d. two passed places, `rumor` and `knows` -> `knows` (C1);
   e. an entity met at t1, its rencontre default at t2 -> unaware; at t0 ->
      known;
   f. a faction left at t1: its default at t0 -> known (J2), at t2 ->
      unaware; an active membership -> known whatever the date;
   g. an entity never met but at the same current place (O1), or sharing a
      schedule slot (L1), its rencontre default at t3 -> known.
D2 -- `as_of` (N1). A `tenue` of A with a rencontre default on A at t0, A
   met at t1, then rewritten as a `changement`: `as_of == t1` and the
   version known is the old text; after a new encounter, the current one.
   A fact with a `world` default and one's own description -> `as_of` None.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that examines zero rows is a
FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_14_passage.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


# --- A1 ------------------------------------------------------------------------

def check_a1() -> None:
    from world_engine.facets import FACETS
    from world_engine.models import Passage, Rencontre

    table = Passage.__table__
    columns = {c.name: c for c in table.columns}
    if set(columns) != {"id", "world_id", "entity_id", "location_id", "last_at"}:
        fail(f"A1: passage columns are {sorted(columns)}")
    elif columns["last_at"].nullable:
        fail("A1: passage.last_at is nullable")
    indexes = {i.name: ([c.name for c in i.columns], bool(i.unique)) for i in table.indexes}
    if indexes != {"idx_passage_entity_location": (["entity_id", "location_id"], True),
                   "idx_passage_location": (["location_id"], False)}:
        fail(f"A1: passage indexes are {indexes}")
    last = Rencontre.__table__.columns.get("last_at")
    if last is None or not last.nullable:
        fail("A1: rencontre.last_at is missing or NOT NULL")
    if FACETS["tenue"].preset != "rencontre":
        fail(f"A1: the tenue facet presets {FACETS['tenue'].preset!r}")


# --- A2 ------------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
                          text=True, cwd=str(ROOT), timeout=120)


def _shape(conn, table: str) -> list[tuple[str, int]]:
    return [(r[1], r[3]) for r in conn.execute(f"PRAGMA table_info({table})")]


def _seed(session) -> dict:
    from datetime import UTC, datetime

    from world_engine.models import (
        Character, Entity, Location, NpcSchedule, Rencontre, SchemaMeta, Visit, World,
    )
    from world_engine.writes import attach_participants, create_fact

    world = World(name="Learning A2", is_active=True)
    session.add(world)
    session.flush()
    ids: dict = {"world": world.id}

    def entity(etype: str, name: str) -> str:
        row = Entity(world_id=world.id, type=etype, name=name)
        session.add(row)
        session.flush()
        return row.id

    for key in ("L1", "L2", "L3"):
        ids[key] = entity("location", key)
        session.add(Location(id=ids[key], parent_location_id=None))
    for key, kind, place in (("C", "npc", "L1"), ("N", "npc", None), ("P", "player", None)):
        ids[key] = entity("character", key)
        session.add(Character(id=ids[key], world_id=world.id, character_type=kind,
                              current_location_id=ids[place] if place else None))
    session.flush()
    session.add(NpcSchedule(world_id=world.id, npc_id=ids["N"], phase="soir",
                            location_id=ids["L2"]))
    ids["visit_last"] = datetime(2021, 3, 4, 5, 6, 7, tzinfo=UTC)
    for at in (datetime(2020, 1, 1, tzinfo=UTC), ids["visit_last"]):
        session.add(Visit(world_id=world.id, player_id=ids["P"], location_id=ids["L3"], entered_at=at))
    lo, hi = sorted((ids["C"], ids["N"]))
    session.add(Rencontre(world_id=world.id, entity_lo_id=lo, entity_hi_id=hi,
                          first_at=datetime(2020, 1, 1, tzinfo=UTC), source="visit"))
    for key, owners in (("T1", ["N"]), ("T2", ["N", "C"])):
        fact = create_fact(session, world_id=world.id, content=key, created_by="check", facet="tenue")
        session.flush()
        attach_participants(session, fact=fact, entity_ids=[ids[o] for o in owners])
        ids[key] = fact.id
    if session.get(SchemaMeta, 1) is None:
        session.add(SchemaMeta(id=1, static_version="v2.13"))
    session.commit()
    return ids


def _to_v213(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS passage")
        if "last_at" in {r[1] for r in conn.execute("PRAGMA table_info(rencontre)")}:
            conn.execute("ALTER TABLE rencontre DROP COLUMN last_at")
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))


def _state(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        state = {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "passage_shape": _shape(conn, "passage") if "passage" in tables else None,
            "rencontre_shape": _shape(conn, "rencontre"),
            "defaults": sorted(conn.execute(
                "SELECT fact_id, scope_type, scope_id, level, created_at FROM fact_default").fetchall()),
        }
        state["passages"] = sorted(conn.execute(
            "SELECT entity_id, location_id, last_at FROM passage").fetchall()) if "passage" in tables else None
        has_last = "last_at" in {c for c, _ in state["rencontre_shape"]}
        state["encounters"] = conn.execute(
            "SELECT last_at FROM rencontre" if has_last else "SELECT NULL FROM rencontre").fetchall()
    return state


def check_a2(db_path: str) -> None:
    from sqlmodel import Session

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    with Session(engine) as session:
        ids = _seed(session)
    engine.dispose()
    with sqlite3.connect(db_path) as conn:
        model_passage = _shape(conn, "passage")
        model_rencontre = _shape(conn, "rencontre")
    _to_v213(db_path, "v2.12")
    result = _run_migration(db_path)
    if result.returncode == 0 or _state(db_path)["passage_shape"] is not None:
        fail(f"A2a: v2.12 was not refused (exit {result.returncode})")
    _to_v213(db_path, "v2.13")
    result = _run_migration(db_path)
    after = _state(db_path)
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    if result.returncode != 0 or after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
        fail(f"A2b: exit {result.returncode}, version {after['version']!r}: "
             f"{result.stderr.strip()[-300:]}")
        return
    if after["passage_shape"] != model_passage or after["rencontre_shape"] != model_rencontre:
        fail(f"A2b: shapes {after['passage_shape']} / {after['rencontre_shape']} differ from the models")
    tenue = [d for d in after["defaults"] if d[0] in (ids["T1"], ids["T2"])]
    if [d[:4] for d in tenue] != [(ids["T1"], "rencontre", ids["N"], "knows")]:
        fail(f"A2b: tenue defaults are {tenue}")
    encounters = after["encounters"]
    if len(encounters) != 1 or encounters[0][0] is None or (tenue and encounters[0][0] < tenue[0][4]):
        fail(f"A2b: encounter dates {encounters} vs tenue default {tenue}")
    passages = {(e, loc): at for e, loc, at in after["passages"] or []}
    want = {(ids["C"], ids["L1"]), (ids["N"], ids["L2"]), (ids["P"], ids["L3"])}
    if set(passages) != want:
        fail(f"A2b: passages are {sorted(passages)}")
    elif not str(passages[(ids["P"], ids["L3"])]).startswith("2021-03-04 05:06:07"):
        fail(f"A2b: the visit passage is dated {passages[(ids['P'], ids['L3'])]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or _state(db_path) != after:
        fail(f"A2c: second run exit {again.returncode} or changed rows: {again.stdout.strip()[-200:]}")


# --- B1-B4 ---------------------------------------------------------------------

def check_b1() -> None:
    import ast
    import re

    allowed = {"src/world_engine/passages.py", "scripts/migrate_v2_14_passage.py"}
    seen = 0
    for base in (ROOT / "src", ROOT / "scripts"):
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            seen += 1
            for node in ast.walk(ast.parse(text)):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "Passage" and rel not in allowed):
                    fail(f"B1: Passage( constructed in {rel}")
            if rel.startswith("src/") and re.search(r"(UPDATE\s+passage|DELETE\s+FROM\s+passage)\b",
                                                    text, re.IGNORECASE):
                fail(f"B1: raw passage mutation in {rel}")
    if seen == 0:
        fail("B1: no file scanned")


def check_b2() -> None:
    db_text = (SRC / "db.py").read_text(encoding="utf-8")
    if "from world_engine import passages" not in db_text:
        fail("B2: db.py does not import passages")
    import world_engine.db  # noqa: F401
    from world_engine import passages
    if not passages.listener_registered():
        fail("B2: the placement listener is not registered")


def _world(session, name: str) -> dict:
    from world_engine.models import Entity, Location, World

    world = World(name=name, is_active=False)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key in ("L1", "L2", "L3", "L4", "L5"):
        row = Entity(world_id=world.id, type="location", name=f"{name} {key}")
        session.add(row)
        session.flush()
        session.add(Location(id=row.id, parent_location_id=None))
        ids[key] = row.id
    for key in ("A", "B"):
        row = Entity(world_id=world.id, type="character", name=f"{name} {key}")
        session.add(row)
        session.flush()
        ids[key] = row.id
    session.commit()
    return ids


def _passages_of(session, entity_id: str) -> dict:
    from sqlmodel import select

    from world_engine.models import Passage
    rows = session.exec(select(Passage).where(Passage.entity_id == entity_id)).all()
    return {r.location_id: r.last_at for r in rows}


def check_b3(engine) -> None:
    from sqlmodel import Session

    from world_engine.models import Character
    from world_engine.passages import record_passage
    from world_engine.writes import write_character_location, write_npc_schedule

    with Session(engine) as session:
        ids = _world(session, "B3")
        session.add(Character(id=ids["A"], world_id=ids["world"], character_type="npc",
                              current_location_id=ids["L1"]))
        session.commit()
        first = _passages_of(session, ids["A"])
        if set(first) != {ids["L1"]}:
            fail(f"B3: creation left passages {sorted(first)}")
            return
        write_character_location(session, entity_id=ids["A"], to_location_id=ids["L2"])
        session.commit()
        moved = _passages_of(session, ids["A"])
        if set(moved) != {ids["L1"], ids["L2"]} or moved[ids["L1"]] < first[ids["L1"]]:
            fail(f"B3: a move left passages {moved}")
        char = session.get(Character, ids["A"])
        char.current_location_id = ids["L3"]
        session.add(char)
        session.commit()
        travelled = _passages_of(session, ids["A"])
        if set(travelled) != {ids["L1"], ids["L2"], ids["L3"]} or travelled[ids["L2"]] < moved[ids["L2"]]:
            fail(f"B3: an assignment left passages {travelled}")
        record_passage(session, world_id=ids["world"], entity_id=ids["A"], location_id=ids["L4"])
        record_passage(session, world_id=ids["world"], entity_id=ids["A"], location_id=ids["L4"])
        session.commit()
        if len(_passages_of(session, ids["A"])) != 4:
            fail("B3: one pair recorded twice in one flush is not one row")
        session.add(Character(id=ids["B"], world_id=ids["world"], character_type="npc"))
        session.commit()
        for place in ("L4", "L5"):
            session.add_all(write_npc_schedule(
                session, world_id=ids["world"], npc_id=ids["B"],
                rows=[{"phase": "soir", "location_id": ids[place]}], changed_by="check"))
            session.commit()
        if set(_passages_of(session, ids["B"])) != {ids["L4"], ids["L5"]}:
            fail(f"B3: schedules left passages {sorted(_passages_of(session, ids['B']))}")


def check_b4(engine) -> None:
    from datetime import UTC, datetime, timedelta

    from sqlmodel import Session, select

    from world_engine.encounters import record_encounter
    from world_engine.models import Rencontre

    with Session(engine) as session:
        ids = _world(session, "B4")
        t0 = datetime(2026, 1, 1, tzinfo=UTC)

        def row():
            rows = session.exec(select(Rencontre).where(Rencontre.world_id == ids["world"])).all()
            return rows[0] if len(rows) == 1 else None

        def stamp(value):
            return value.replace(tzinfo=UTC) if value.utcoffset() is None else value

        record_encounter(session, world_id=ids["world"], a_id=ids["A"], b_id=ids["B"],
                         source="gathering", at=t0)
        session.commit()
        created = row()
        if created is None or stamp(created.last_at) != stamp(created.first_at):
            fail("B4: a new pair's last_at is not its first_at")
            return
        later = t0 + timedelta(days=3)
        record_encounter(session, world_id=ids["world"], a_id=ids["B"], b_id=ids["A"],
                         source="visit", at=later)
        session.commit()
        moved = row()
        if moved is None or stamp(moved.last_at) != later or stamp(moved.first_at) != t0:
            fail("B4: a later visit did not move last_at alone")
            return
        record_encounter(session, world_id=ids["world"], a_id=ids["A"], b_id=ids["B"],
                         source="relation", at=later + timedelta(days=1))
        record_encounter(session, world_id=ids["world"], a_id=ids["A"], b_id=ids["B"],
                         source="gathering", at=t0)
        session.commit()
        kept = row()
        if kept is None or stamp(kept.last_at) != later:
            fail("B4: a relation or an earlier encounter moved last_at")


# --- C1-C3 ---------------------------------------------------------------------

def check_c1(engine) -> None:
    from sqlmodel import Session

    from world_engine.writes import create_fact
    from world_engine.writes.facts import update_fact_content

    with Session(engine) as session:
        ids = _world(session, "C1")
        fact = create_fact(session, world_id=ids["world"], content="a", created_by="check",
                           facet="information")
        session.flush()
        try:
            update_fact_content(session, fact=fact, content="b", changed_by="check")  # type: ignore[call-arg]
            fail("C1: a rewrite without kind was accepted")
        except TypeError:
            pass
        try:
            update_fact_content(session, fact=fact, content="b", changed_by="check", kind="x")
            fail("C1: an unknown kind was accepted")
        except ValueError:
            pass
        if fact.change_history:
            fail("C1: a refused rewrite appended history")
        update_fact_content(session, fact=fact, content="b", changed_by="check", kind="correction")
        update_fact_content(session, fact=fact, content="c", changed_by="check", kind="changement")
        kinds = [e.get("kind") for e in fact.change_history]
        if kinds != ["correction", "changement"] or fact.content_raw != "c":
            fail(f"C1: history kinds {kinds}, content {fact.content_raw!r}")
        session.rollback()


_KIND_CALLS = {"update_fact_content", "update_typed_fact_content", "edit_entity_fact"}
_KIND_LITERALS = {
    ("src/world_engine/writes/mentions.py", "bind_mention"): "correction",
    ("src/world_engine/writes/relations.py", "_refresh_map_content"): "correction",
    ("src/world_engine/writes/relations.py", "_refresh_lien_content"): "changement",
}


def check_c2() -> None:
    import ast

    calls = 0
    literals: dict = {}
    for base in (ROOT / "src", ROOT / "scripts"):
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
                for node in ast.walk(func):
                    if not isinstance(node, ast.Call):
                        continue
                    name = node.func.id if isinstance(node.func, ast.Name) else (
                        node.func.attr if isinstance(node.func, ast.Attribute) else None)
                    if name not in _KIND_CALLS:
                        continue
                    calls += 1
                    kind = next((k.value for k in node.keywords if k.arg == "kind"), None)
                    if kind is None:
                        fail(f"C2: {rel}::{func.name} calls {name} without kind=")
                    elif (rel, func.name) in _KIND_LITERALS:
                        literals[(rel, func.name)] = getattr(kind, "value", None)
    if calls == 0:
        fail("C2: no rewrite call found")
    if literals != _KIND_LITERALS:
        fail(f"C2: the code-made rewrites name {literals}")


def check_c3() -> None:
    from datetime import UTC, datetime, timedelta

    from world_engine.fact_versions import version_text

    base = datetime(2026, 1, 1, tzinfo=UTC)

    def t(n: float) -> datetime:
        return base + timedelta(days=n)

    history = [
        {"content": "v0", "at": t(1).isoformat(), "kind": "correction"},
        {"content": "v1", "at": t(2).isoformat(), "kind": "changement"},
        {"content": "v2a", "at": t(3).isoformat(), "kind": "correction"},
        {"content": "v2b", "at": t(4).isoformat(), "kind": "changement"},
        {"content": "old", "at": t(5).isoformat()},
    ]
    cases = ((t(0), "v1"), (t(1.5), "v1"), (t(2.5), "v2b"), (t(3.5), "v2b"),
             (t(4.5), "v3"), (t(6), "v3"), (None, "v3"),
             (t(2.5).replace(tzinfo=None), "v2b"))
    for as_of, want in cases:
        got = version_text(history, "v3", as_of)
        if got != want:
            fail(f"C3: as of {as_of} -> {got!r}, expected {want!r}")


# --- D1-D2 ---------------------------------------------------------------------

def _d_world(session):
    from datetime import UTC, datetime, timedelta

    from world_engine.models import Character, Entity, Faction, Location, World

    world = World(name="D1", is_active=False)
    session.add(world)
    session.flush()
    ids: dict = {"world": world.id}
    now = datetime.now(UTC)
    ids.update({f"t{i}": now - timedelta(days=4 - i) for i in range(4)})

    def entity(etype: str, name: str) -> str:
        row = Entity(world_id=world.id, type=etype, name=f"D1 {name}")
        session.add(row)
        session.flush()
        return row.id

    for key, parent in (("Z", None), ("C", "Z"), ("L", None), ("M", None), ("Q", None)):
        ids[key] = entity("location", key)
        session.add(Location(id=ids[key], parent_location_id=ids[parent] if parent else None))
    for key in ("F1", "F2", "F3"):
        ids[key] = entity("faction", key)
        session.add(Faction(id=ids[key]))
    for key in ("P", "A", "B", "S"):
        ids[key] = entity("character", key)
        session.add(Character(id=ids[key], world_id=world.id, character_type="npc"))
    session.commit()
    return ids


def _d_fact(session, ids, label, facet="information", about=None, scopes=()):
    from world_engine.writes import attach_participants, create_fact, create_fact_default

    fact = create_fact(session, world_id=ids["world"], content=f"D1 {label}", created_by="check",
                       facet=facet)
    session.flush()
    if about:
        attach_participants(session, fact=fact, entity_ids=[ids[about]])
    for scope_type, key, level, at in scopes:
        row = create_fact_default(session, world_id=ids["world"], fact_id=fact.id,
                                  scope_type=scope_type, scope_id=ids[key] if key else None,
                                  level=level, created_by="check")
        session.flush()
        row.created_at = ids[at] if at else row.created_at
        session.add(row)
    session.commit()
    return fact.id


def _d_cases(session, ids) -> dict:
    from world_engine.encounters import record_encounter
    from world_engine.models import Character, FactionMembership
    from world_engine.passages import record_passage
    from world_engine.writes import write_npc_schedule

    w = ids["world"]
    for key, at in (("L", "t1"), ("M", "t1"), ("C", "t1")):
        record_passage(session, world_id=w, entity_id=ids["P"], location_id=ids[key], at=ids[at])
    record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="visit", at=ids["t1"])
    session.add(FactionMembership(world_id=w, entity_id=ids["P"], faction_id=ids["F1"], left_at=ids["t1"]))
    session.add(FactionMembership(world_id=w, entity_id=ids["P"], faction_id=ids["F2"], left_at=ids["t1"]))
    session.add(FactionMembership(world_id=w, entity_id=ids["P"], faction_id=ids["F3"]))
    session.commit()
    cases = {
        "a": (_d_fact(session, ids, "a", scopes=[("location", "L", "knows", "t2")]), "unaware"),
        "b": (_d_fact(session, ids, "b", scopes=[("location", "M", "partial", "t0")]), "partial"),
        "c": (_d_fact(session, ids, "c", scopes=[("location", "Z", "knows", "t0")]), "knows"),
        "d": (_d_fact(session, ids, "d", scopes=[("location", "L", "rumor", "t0"),
                                                 ("location", "M", "knows", "t0")]), "knows"),
        "e-late": (_d_fact(session, ids, "e1", scopes=[("rencontre", "A", "knows", "t2")]), "unaware"),
        "e-early": (_d_fact(session, ids, "e2", scopes=[("rencontre", "A", "rumor", "t0")]), "rumor"),
        "f-early": (_d_fact(session, ids, "f1", scopes=[("faction", "F1", "knows", "t0")]), "knows"),
        "f-late": (_d_fact(session, ids, "f2", scopes=[("faction", "F2", "knows", "t2")]), "unaware"),
        "f-active": (_d_fact(session, ids, "f3", scopes=[("faction", "F3", "rumor", "t3")]), "rumor"),
        "g-place": (_d_fact(session, ids, "g1", scopes=[("rencontre", "B", "knows", "t3")]), "knows"),
        "g-slot": (_d_fact(session, ids, "g2", scopes=[("rencontre", "S", "partial", "t3")]), "partial"),
    }
    for key in ("P", "B"):
        char = session.get(Character, ids[key])
        char.current_location_id = ids["Q"]
        session.add(char)
    for key in ("P", "S"):
        session.add_all(write_npc_schedule(session, world_id=w, npc_id=ids[key],
                                           rows=[{"phase": "soir", "location_id": ids["M"]}],
                                           changed_by="check"))
    session.commit()
    return cases


def check_d1(engine) -> None:
    from sqlmodel import Session

    from world_engine.knowledge_resolve import resolve_known_for_entity, resolve_knowledge

    with Session(engine) as session:
        ids = _d_world(session)
        cases = _d_cases(session, ids)
        batch = resolve_known_for_entity(session, ids["P"])
        for case, (fact_id, want) in sorted(cases.items()):
            single = resolve_knowledge(session, ids["P"], fact_id).level
            batched = batch[fact_id].level if fact_id in batch else "unaware"
            if single != want or batched != want:
                fail(f"D1 {case}: expected {want!r}, got {single!r} / {batched!r}")


def check_d2(engine) -> None:
    from sqlmodel import Session

    from world_engine.encounters import record_encounter
    from world_engine.fact_versions import version_text
    from world_engine.knowledge_resolve import resolve_known_for_entity, resolve_knowledge
    from world_engine.models import Fact
    from world_engine.writes.facts import update_fact_content

    with Session(engine) as session:
        ids = _d_world(session)
        w = ids["world"]
        record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="visit", at=ids["t1"])
        session.commit()
        tenue = _d_fact(session, ids, "noir", facet="tenue", about="A",
                        scopes=[("rencontre", "A", "knows", "t0")])
        fact = session.get(Fact, tenue)
        update_fact_content(session, fact=fact, content="D1 rouge", changed_by="check", kind="changement")
        session.commit()
        known = resolve_knowledge(session, ids["P"], tenue)
        batched = resolve_known_for_entity(session, ids["P"]).get(tenue)
        if known.as_of != ids["t1"] or batched is None or batched.as_of != ids["t1"]:
            fail(f"D2: as_of is {known.as_of} / {batched}, expected {ids['t1']}")
        elif version_text(fact.change_history, fact.content_raw, known.as_of) != "D1 noir":
            fail("D2: the version known before the new encounter is not the old text")
        record_encounter(session, world_id=w, a_id=ids["P"], b_id=ids["A"], source="gathering")
        session.commit()
        again = resolve_knowledge(session, ids["P"], tenue)
        if version_text(fact.change_history, fact.content_raw, again.as_of) != "D1 rouge":
            fail("D2: a new encounter did not bring the current text")
        public = _d_fact(session, ids, "public", scopes=[("world", None, "rumor", None)])
        own = _d_fact(session, ids, "own", facet="physique", about="P")
        for label, fact_id in (("world", public), ("own", own)):
            if resolve_knowledge(session, ids["P"], fact_id).as_of is not None:
                fail(f"D2: a {label} fact is not always current")


def main() -> int:
    db_path = _fresh_db()
    check_a1()
    check_a2(db_path)
    check_b1()
    check_b2()
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_b3(engine)
    check_b4(engine)
    check_c1(engine)
    check_c2()
    check_c3()
    check_d1(engine)
    check_d2(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: fact_learning -- v2.14 declares passage and the encounter's last "
          "contact, presets tenue to rencontre, and migrates from v2.13 only; every "
          "placement and every encounter moves its last contact, through one writer each; "
          "every rewrite says whether it corrects or changes the world, and the version "
          "known follows the changes alone; a default is learned by a contact after it, kept "
          "after leaving, and dated by the last contact with its anchors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
