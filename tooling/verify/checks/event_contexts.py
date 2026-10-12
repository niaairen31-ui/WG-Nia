"""G1 check for TICKET-0114 -- the models read the journal by what is known, and the MJ reads the states a player may see.

BRIEF-0114-D's rules.

ED1 -- who reads what (fixture). In a world where the PC Mira stands in the
   Forêt, six chronicle events: one Mira took part in, one with a `world`
   scope, one with a `location` scope on the Forêt, one with a `location`
   scope on the Ville, one an NPC keeps secret with no scope, and one Mira
   took part in whose type is not in the chronicle.
   `event_reads.known_chronicle_events` for Mira lists exactly the first
   three, newest first; `assemble_mj_context`'s `public_events` lists the
   same three titles, the Forêt's first; `public_chronicle_events` lists
   only the `world` one, and with the faction as participant only the
   faction's; the tick's location briefing for the Forêt names the `world`
   one held there and not the `location` one; the faction briefing names
   the faction's; the return-visit delta at the Forêt, after a visit
   recorded before the events, names the two known there.
ED2 -- WL1 (fixture). `attributes.perceived_states` of the Forêt reads
   « Ouvert : oui » from a visible attribute and never names a hidden one;
   `assemble_mj_context`'s location carries it and `format_mj_context`
   writes « États : Ouvert : oui »; blindfolded, the location carries no
   states. `context_describe._mj_context_co_presents` gives each co-present
   its `states` through `perceived_states`, none when blindfolded (static).
ED3 -- migration `scripts/migrate_v2_25_event_columns.py`, on a v2.24
   database (`event` and `event_entity` in their v2.24 DDL, frozen below):
   at v2.23 it refuses and changes nothing; with an `event_entity` row of a
   typed event that no participant twins, it refuses and changes nothing;
   at v2.24 it first types an event left untyped (its link becomes a
   participant, its fact is written), rebuilds `event` without the five
   columns, `type_id` required, every row kept, drops `event_entity` and
   sets `schema_meta` to the code's version; a second run writes nothing.
ED4 -- nothing reads what was dropped (static, AST). No module under `src/`
   names the attribute `knowledge_status`, `occurred_at`,
   `has_magic_impact` or `consequences` on anything, nor `EventEntity`;
   `event` declares none of the five columns; `context.py`,
   `cockpit/play_physical.py` and `tick_context.py` each call
   `event_reads`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION_V2_25 = ROOT / "scripts" / "migrate_v2_25_event_columns.py"

FAILURES: list[str] = []

V2_24_EVENT = (
    "CREATE TABLE event (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, session_id VARCHAR, batch_id VARCHAR, "
    "title VARCHAR NOT NULL, description VARCHAR, type VARCHAR, knowledge_status VARCHAR DEFAULT 'secret' NOT NULL, "
    "location_id VARCHAR, has_magic_impact BOOLEAN DEFAULT 0 NOT NULL, consequences JSON, occurred_at DATETIME, "
    "recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, type_id VARCHAR, quantity INTEGER, PRIMARY KEY (id), "
    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(session_id) REFERENCES session (id), "
    "FOREIGN KEY(batch_id) REFERENCES batch (id), FOREIGN KEY(location_id) REFERENCES entity (id), "
    "FOREIGN KEY(type_id) REFERENCES event_type (id))",
    "CREATE INDEX idx_event_world ON event (world_id)",
    "CREATE TABLE event_entity (id VARCHAR NOT NULL, event_id VARCHAR NOT NULL, entity_id VARCHAR NOT NULL, "
    "PRIMARY KEY (id), FOREIGN KEY(event_id) REFERENCES event (id), FOREIGN KEY(entity_id) REFERENCES entity (id))",
    "CREATE UNIQUE INDEX idx_event_entity_unique ON event_entity (event_id, entity_id)",
)
DROPPED = ("knowledge_status", "occurred_at", "has_magic_impact", "consequences")


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Faction, Location, Visit, World
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type

    with Session(engine) as db:
        world = World(name="Contextes", is_active=True)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("foret", "location", "Forêt"), ("ville", "location", "Ville"),
                                ("mira", "character", "Mira"), ("brakk", "character", "Brakk"),
                                ("guilde", "faction", "Guilde")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "location":
                db.add(Location(id=entity.id))
            elif kind == "faction":
                db.add(Faction(id=entity.id))
        db.flush()
        for key in ("mira", "brakk"):
            db.add(Character(id=ids[key], world_id=world.id, character_type="player" if key == "mira" else "npc",
                             current_location_id=ids["foret"]))
        db.add(Visit(world_id=world.id, player_id=ids["mira"], location_id=ids["foret"],
                     entered_at=datetime.now(UTC) - timedelta(days=1), present_npc_ids=[]))
        roles = (RoleSpec("qui", ("character", "faction")),)
        ids["fait"] = write_event_type(db, world_id=world.id, spec=EventTypeSpec(name="Fait", roles=roles)).id
        ids["compte"] = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Compte", roles=roles, in_chronicle=False)).id
        db.commit()
    return ids


def _events(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.models import Event
    from world_engine.writes.events import EventScopeSpec, EventSpec, ParticipantSpec, write_event

    with Session(engine) as db:
        qui = type_view(db, ids["fait"]).roles[0].id
        quic = type_view(db, ids["compte"]).roles[0].id
        rows = (
            ("Mira y était", ids["fait"], (ParticipantSpec(qui, entity_id=ids["mira"]),), (), ids["ville"]),
            ("Tout le monde le sait", ids["fait"], (ParticipantSpec(qui, entity_id=ids["guilde"]),),
             (EventScopeSpec("world", None, "knows"),), ids["foret"]),
            ("On le sait à la Forêt", ids["fait"], (), (EventScopeSpec("location", ids["foret"], "knows"),),
             ids["foret"]),
            ("On le sait à la Ville", ids["fait"], (), (EventScopeSpec("location", ids["ville"], "knows"),),
             ids["ville"]),
            ("Le secret de Brakk", ids["fait"], (ParticipantSpec(qui, entity_id=ids["brakk"], secret=True),), (),
             ids["foret"]),
            ("Mira compte un loup", ids["compte"], (ParticipantSpec(quic, entity_id=ids["mira"]),), (), ids["foret"]),
        )
        for k, (title, type_id, participants, scopes, place) in enumerate(rows):
            event = write_event(db, world_id=ids["world"], created_by="check", spec=EventSpec(
                type_id=type_id, title=title, participants=participants, scopes=scopes, location_id=place))
            event.recorded_at = datetime.now(UTC) - timedelta(hours=10 - k)
            db.add(event)
        db.commit()
        assert db.get(Event, event.id) is not None


def check_ed1(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.play_physical import _compute_return_delta
    from world_engine.context import assemble_mj_context
    from world_engine.event_reads import known_chronicle_events, public_chronicle_events
    from world_engine.tick_context import _tick_faction_recent_events_block
    from world_engine.models import Entity

    known_want = ["On le sait à la Forêt", "Tout le monde le sait", "Mira y était"]
    with Session(engine) as db:
        known = [e.title for e in known_chronicle_events(db, ids["mira"], ids["world"])]
        if known != known_want:
            fail(f"ED1: Mira knows {known}")
        mj = assemble_mj_context(db, ids["mira"], ids["foret"])
        titles = [e["title"] for e in mj["public_events"]]
        if titles != ["On le sait à la Forêt", "Tout le monde le sait", "Mira y était"]:
            fail(f"ED1: the MJ's public_events are {titles}")
        public = [e.title for e in public_chronicle_events(db, ids["world"])]
        guild = [e.title for e in public_chronicle_events(db, ids["world"], participant_id=ids["guilde"])]
        if public != ["Tout le monde le sait"] or guild != ["Tout le monde le sait"]:
            fail(f"ED1: public_chronicle_events gives {public}, with the guild {guild}")
        block = _tick_faction_recent_events_block(ids["guilde"], db.get(Entity, ids["guilde"]), db)
        if "Tout le monde le sait" not in block:
            fail(f"ED1: the faction briefing reads {block!r}")
        lines, _ = _compute_return_delta(db, ids["world"], ids["mira"], ids["foret"])
        named = [line for line in (lines or []) if line.startswith("- Événement")]
        if len(named) != 2 or "Tout le monde le sait" not in named[0] or "On le sait à la Forêt" not in named[1]:
            fail(f"ED1: the return delta names {named}")
    src = (SRC / "tick_context.py").read_text(encoding="utf-8")
    if "public_chronicle_events(session, place.world_id, location_id=location_id" not in src:
        fail("ED1: the tick's location briefing does not read public_chronicle_events at its place")


def check_ed2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.attributes import perceived_states
    from world_engine.context import assemble_mj_context, format_mj_context
    from sqlmodel import select

    from world_engine.models import AttributeChoice, Entity
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition, \
        write_attribute_value

    with Session(engine) as db:
        for name, hidden in (("Ouvert", False), ("Maudit", True)):
            definition = write_attribute_definition(db, world_id=ids["world"], spec=DefinitionSpec(
                name=name, kind="choice", holder_types=("location",), choices=(ChoiceSpec("non"), ChoiceSpec("oui")),
                default="non", is_hidden=hidden))
            oui = next(c for c in db.exec(select(AttributeChoice).where(
                AttributeChoice.definition_id == definition.id)).all() if c.label == "oui")
            write_attribute_value(db, world_id=ids["world"], definition_id=definition.id, entity_id=ids["foret"],
                                  value=oui.id, kind="changement", changed_by="check")
        db.commit()
        states = perceived_states(db, ids["world"], db.get(Entity, ids["foret"]))
        if states != "Ouvert : oui":
            fail(f"ED2: the Forêt's perceived states are {states!r}")
        mj = assemble_mj_context(db, ids["mira"], ids["foret"])
        if mj["location"].get("states") != "Ouvert : oui" or "États : Ouvert : oui" not in format_mj_context(mj) \
                or "Maudit" in format_mj_context(mj):
            fail(f"ED2: the MJ's location reads {mj['location']}")
        if assemble_mj_context(db, ids["mira"], ids["foret"], blindfolded=True)["location"].get("states"):
            fail("ED2: blindfolded, the location still carries states")
    describe = (SRC / "context_describe.py").read_text(encoding="utf-8")
    if '"states": None if blindfolded else (perceived_states(db, co_entity.world_id, co_entity) or None)' \
            not in describe:
        fail("ED2: context_describe does not give each co-present its perceived states")


# --- ED3 -------------------------------------------------------------------------

def _run_migration(db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION_V2_25)], env=env, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


def _v2_24_db(orphan: bool) -> str:
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng, tables=[t for n, t in SQLModel.metadata.tables.items() if n != "event"])
    eng.dispose()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE event_participant")
        for statement in V2_24_EVENT:
            conn.execute(statement)
        conn.executescript("""
            INSERT INTO schema_meta (id, static_version, updated_at) VALUES (1, 'v2.23', '2026-10-01');
            INSERT INTO world (id, name, is_active, created_at, updated_at) VALUES ('w', 'W', 0, '2026-10-01', '2026-10-01');
            INSERT INTO entity (id, world_id, type, name, status, created_at, updated_at)
              VALUES ('a', 'w', 'character', 'A', 'active', '2026-10-01', '2026-10-01');
            INSERT INTO event_type (id, world_id, name, domain, counts_quantity, in_chronicle, participants_secret,
              status, created_at, updated_at) VALUES ('t', 'w', 'Social', 'social', 0, 1, 0, 'active', '2026-10-01', '2026-10-01');
            INSERT INTO event_type_role (id, world_id, type_id, name, position, accepts_sorte, status)
              VALUES ('r', 'w', 't', 'Impliqué', 0, 0, 'active');
            INSERT INTO event_type_role_type (id, world_id, role_id, entity_type) VALUES ('rt', 'w', 'r', 'character');
            INSERT INTO event (id, world_id, title, type, knowledge_status, recorded_at, type_id)
              VALUES ('e1', 'w', 'Typé', 'social', 'secret', '2026-10-01', 't'),
                     ('e2', 'w', 'Après', 'social', 'public', '2026-10-02', NULL);
            INSERT INTO event_entity (id, event_id, entity_id) VALUES ('l1', 'e1', 'a'), ('l2', 'e2', 'a');
            INSERT INTO fact (id, world_id, event_id, content, facet, default_level, created_at, created_by, change_history)
              VALUES ('f1', 'w', 'e1', 'Typé', 'evenement', 'unaware', '2026-10-01', 'x', '[]');
        """)
        conn.execute(str(_participant_ddl()))
        if not orphan:
            conn.execute("INSERT INTO event_participant (id, world_id, event_id, role_id, entity_id, position) "
                         "VALUES ('p1', 'w', 'e1', 'r', 'a', 0)")
    return db_path


def _participant_ddl() -> str:
    from sqlalchemy.dialects import sqlite
    from sqlalchemy.schema import CreateTable
    from sqlmodel import SQLModel

    return str(CreateTable(SQLModel.metadata.tables["event_participant"]).compile(dialect=sqlite.dialect()))


def _state(db_path: str) -> dict:
    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "columns": [r[1] for r in conn.execute("PRAGMA table_info(event)")],
            "events": sorted(conn.execute("SELECT id, type_id FROM event").fetchall()),
            "participants": sorted(conn.execute("SELECT event_id, entity_id FROM event_participant").fetchall()),
            "facts": sorted(conn.execute("SELECT event_id FROM fact WHERE event_id IS NOT NULL").fetchall()),
            "event_entity": "event_entity" in tables,
        }


def check_ed3() -> None:
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    db_path = _v2_24_db(orphan=False)
    before = _state(db_path)
    if _run_migration(db_path).returncode == 0 or _state(db_path) != before:
        fail("ED3: v2.23 was not refused untouched")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.24' WHERE id = 1")
    orphan_path = _v2_24_db(orphan=True)
    with sqlite3.connect(orphan_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.24' WHERE id = 1")
    orphan_before = _state(orphan_path)
    refused = _run_migration(orphan_path)
    if refused.returncode == 0 or _state(orphan_path) != orphan_before:
        fail(f"ED3: an untwinned event_entity row was not refused untouched ({refused.returncode})")
    result = _run_migration(db_path)
    after = _state(db_path)
    want = {
        "version": EXPECTED_STATIC_SCHEMA_VERSION,
        "columns": ["id", "world_id", "session_id", "batch_id", "type_id", "title", "description", "location_id",
                    "quantity", "recorded_at"],
        "events": [("e1", "t"), ("e2", "t")],
        "participants": [("e1", "a"), ("e2", "a")],
        "facts": [("e1",), ("e2",)],
        "event_entity": False,
    }
    if result.returncode != 0 or after != want:
        fail(f"ED3: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "already fully applied" not in again.stdout or _state(db_path) != after:
        fail(f"ED3: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")


# --- ED4 -------------------------------------------------------------------------

def check_ed4() -> None:
    from sqlmodel import SQLModel

    scanned = 0
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        scanned += 1
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in DROPPED:
                fail(f"ED4: {rel}:{node.lineno} reads .{node.attr}")
            if isinstance(node, ast.Name) and node.id == "EventEntity":
                fail(f"ED4: {rel}:{node.lineno} names EventEntity")
    if scanned < 100:
        fail(f"ED4: only {scanned} modules scanned")
    columns = set(SQLModel.metadata.tables["event"].c.keys())
    if columns & set(DROPPED + ("type",)) or SQLModel.metadata.tables["event"].c["type_id"].nullable:
        fail(f"ED4: event declares {sorted(columns)}")
    for name in ("context.py", "cockpit/play_physical.py", "tick_context.py"):
        text = (SRC / name).read_text(encoding="utf-8")
        if "from .event_reads import" not in text and "from ..event_reads import" not in text:
            fail(f"ED4: {name} does not read event_reads")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    _events(engine, ids)
    rules = (("ED1", lambda: check_ed1(engine, ids)), ("ED2", lambda: check_ed2(engine, ids)), ("ED3", check_ed3),
             ("ED4", check_ed4))
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_contexts -- the MJ reads the chronicle the player knows, the tick what everyone knows; the "
          "MJ reads the states a player may see, never a hidden one; v2.25 drops the columns nobody reads")
    return 0


if __name__ == "__main__":
    sys.exit(main())
