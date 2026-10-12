"""G1 check for TICKET-0119 -- what an event type does to the state of the world: its effects, written and read.

BRIEF-0119-A's rules (M-c, C1, D3 and E1 of the conditions series). An effect
only pre-fills an event's proposal; what an approved event writes is
`event_changes.py`'s.

EF1 -- storage (import). `event_type_effect` carries exactly its contract's
   columns, CHECK names and index names, none of them JSON;
   `EVENT_EFFECT_MODES` is its mode CHECK's values; `attribute_change` has
   `event_id` and `idx_attribute_change_event`; `EFFECT_SYSTEM_KEYS` are
   system attributes (`attributes.SYSTEM_ATTRIBUTES`) and are exactly
   `sys:vital_status` and `sys:status`; the code's schema version is v2.26
   or later.
EF2 -- the writer (fixture). `write_event_type` writes « Ouvrir » (Cible ->
   Ouvert = oui, a choice), « Usurper » (Trône -> Occupé par = the
   Usurpateur's entity, a role), « Alerter » (Garnison -> Alerte = 3 set and
   « Être repéré » Garnison -> Alerte + 1 added) and « Tuer » (Victime ->
   État vital = mort, a system state); `type_view` reads each effect back
   with its role, state, mode, kind and value, in order. Refused, each with
   no row written: an unknown state, `Magie` (a system state no event
   changes), a role that holds only sortes, a state that applies to no
   entity type the role accepts, a value that is not one of the state's
   choices, `add` on a choice, a text for an integer, an entity state naming
   the same role, an unknown role or a role whose entities the state may
   not name, one role and state twice, nine effects.
EF3 -- replaced whole, and what an effect holds (fixture). « Ouvrir » saved
   with no effect keeps no `event_type_effect` row. While an effect names
   « Ouvert », retiring it, changing its kind, or dropping its choice
   « oui » is refused; once the effect is gone, retiring works.
EF4 -- a change names its event (fixture). `write_attribute_value` with an
   `event_id` and the kind `correction` is refused, nothing written; with
   `changement` it stores the event on its `attribute_change` row.
EF5 -- migration `scripts/migrate_v2_26_event_effects.py`, on a v2.25
   database (`attribute_change` and `lore_entry_row` in their v2.25 DDL,
   frozen below, one row each; no `event_type_effect`): at v2.24 it refuses
   and changes nothing; at v2.25 it creates the table, adds the column and
   index, rebuilds `lore_entry_row` (its CHECK naming `event`), keeps both
   rows, and sets `schema_meta` to v2.26; a second run writes nothing.
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
SRC = ROOT / "src" / "world_engine"
MIGRATION = ROOT / "scripts" / "migrate_v2_26_event_effects.py"

FAILURES: list[str] = []

COLUMNS = ("id", "world_id", "type_id", "role_id", "definition_id", "system_key", "mode", "choice_id",
           "system_value", "integer_value", "value_role_id", "position")
CHECKS = ("ck_event_type_effect_add", "ck_event_type_effect_mode", "ck_event_type_effect_state",
          "ck_event_type_effect_value")
INDEXES = ("idx_event_type_effect_definition", "idx_event_type_effect_type")

# The two tables v2.26 changes, as v2.25 declared them (frozen: EF5 builds
# the database the migration was written for).
V2_25_DDL: tuple[str, ...] = (
    "CREATE TABLE attribute_change (id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, value_id VARCHAR NOT NULL, "
    "kind VARCHAR NOT NULL, changed_by VARCHAR NOT NULL, before_choice_id VARCHAR, before_integer INTEGER, "
    "before_entity_id VARCHAR, after_choice_id VARCHAR, after_integer INTEGER, after_entity_id VARCHAR, "
    "changed_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id), "
    "CONSTRAINT ck_attribute_change_kind CHECK (kind IN ('correction','changement')), "
    "FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(value_id) REFERENCES attribute_value (id), "
    "FOREIGN KEY(before_choice_id) REFERENCES attribute_choice (id), "
    "FOREIGN KEY(before_entity_id) REFERENCES entity (id), "
    "FOREIGN KEY(after_choice_id) REFERENCES attribute_choice (id), "
    "FOREIGN KEY(after_entity_id) REFERENCES entity (id))",
    "CREATE INDEX idx_attribute_change_value ON attribute_change (value_id, changed_at)",
    "CREATE TABLE lore_entry_row (id VARCHAR NOT NULL, entry_id VARCHAR NOT NULL, row_table VARCHAR NOT NULL, "
    "row_id VARCHAR NOT NULL, action VARCHAR NOT NULL, PRIMARY KEY (id), "
    "CONSTRAINT ck_lore_entry_row_table CHECK (row_table IN ('entity','fact','fact_participant','fact_default',"
    "'knowledge','relation','faction_membership')), "
    "CONSTRAINT ck_lore_entry_row_action CHECK (action IN ('created','updated')), "
    "FOREIGN KEY(entry_id) REFERENCES lore_entry (id))",
    "CREATE UNIQUE INDEX idx_lore_entry_row_entry ON lore_entry_row (entry_id, row_table, row_id)",
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


# --- EF1 -------------------------------------------------------------------------

def check_ef1() -> None:
    import re

    from sqlalchemy import JSON, CheckConstraint
    from sqlmodel import SQLModel

    from world_engine import models
    from world_engine.attributes import SYSTEM_ATTRIBUTES
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.event_types import EFFECT_SYSTEM_KEYS

    table = SQLModel.metadata.tables.get("event_type_effect")
    if table is None:
        fail("EF1: event_type_effect is not declared")
        return
    if tuple(table.c.keys()) != COLUMNS:
        fail(f"EF1: event_type_effect columns are {tuple(table.c.keys())}")
    checks = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
    if tuple(sorted(checks)) != CHECKS:
        fail(f"EF1: event_type_effect CHECKs are {sorted(checks)}")
    if tuple(sorted(i.name for i in table.indexes)) != INDEXES:
        fail(f"EF1: event_type_effect indexes are {sorted(i.name for i in table.indexes)}")
    if any(isinstance(c.type, JSON) for c in table.c):
        fail("EF1: event_type_effect has a JSON column")
    modes = tuple(re.findall(r"'([^']+)'", checks.get("ck_event_type_effect_mode", "")))
    if modes != tuple(models.EVENT_EFFECT_MODES) or modes != ("set", "add"):
        fail(f"EF1: the mode CHECK names {modes}, EVENT_EFFECT_MODES {models.EVENT_EFFECT_MODES}")
    change = SQLModel.metadata.tables["attribute_change"]
    if "event_id" not in change.c or "idx_attribute_change_event" not in {i.name for i in change.indexes}:
        fail("EF1: attribute_change has no event_id or no idx_attribute_change_event")
    system = {s.key for s in SYSTEM_ATTRIBUTES}
    if tuple(EFFECT_SYSTEM_KEYS) != ("sys:vital_status", "sys:status") or not set(EFFECT_SYSTEM_KEYS) <= system:
        fail(f"EF1: EFFECT_SYSTEM_KEYS is {EFFECT_SYSTEM_KEYS}")
    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 26):
        fail(f"EF1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")


# --- fixture -----------------------------------------------------------------------

def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Faction, Location, World
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition

    with Session(engine) as db:
        world = World(name="Effets", is_active=False)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("brakk", "character", "Brakk"), ("ysa", "character", "Ysa"),
                                ("porte", "location", "Porte"), ("guilde", "faction", "Guilde")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "character":
                db.add(Character(id=entity.id, world_id=world.id, character_type="npc"))
            elif kind == "location":
                db.add(Location(id=entity.id))
            else:
                db.add(Faction(id=entity.id))
        ouvert = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Ouvert", kind="choice", holder_types=("location", "item"),
            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
        occupe = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Occupé par", kind="entity", holder_types=("item", "location"), value_types=("character",)))
        alerte = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Alerte", kind="integer", holder_types=("faction",), default=0))
        db.commit()
        from world_engine.attributes import attribute_view

        ids.update(ouvert=ouvert.id, occupe=occupe.id, alerte=alerte.id,
                   oui=dict((label, key) for key, label in attribute_view(db, world.id, ouvert.id).choices)["oui"],
                   non=dict((label, key) for key, label in attribute_view(db, world.id, ouvert.id).choices)["non"])
    return ids


def _counts(db) -> tuple[int, ...]:
    from sqlmodel import func, select

    from world_engine import models

    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (
        models.EventType, models.EventTypeRole, models.EventTypeEffect))


def _refused(db, label: str, rule: str, call) -> None:
    before = _counts(db)
    try:
        call()
    except ValueError:
        db.rollback()
        if _counts(db) != before:
            fail(f"{rule}: {label} was refused but wrote rows")
        return
    db.rollback()
    fail(f"{rule}: {label} was not refused")


def _role(name, types=("character",), sorte=False):
    from world_engine.writes.event_types import RoleSpec

    return RoleSpec(name=name, entity_types=types, accepts_sorte=sorte)


def _effect(role, attribute, value, mode="set"):
    from world_engine.writes.event_types import EffectSpec

    return EffectSpec(role=role, attribute=attribute, value=value, mode=mode)


def _type(name, roles, effects):
    from world_engine.writes.event_types import EventTypeSpec

    return EventTypeSpec(name=name, roles=tuple(roles), effects=tuple(effects))


def check_ef2(engine, ids: dict) -> dict:
    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.writes.event_types import write_event_type

    w = ids["world"]
    specs = {
        "ouvrir": _type("Ouvrir", [_role("Ouvreur"), _role("Cible", ("location", "item"))],
                        [_effect("Cible", ids["ouvert"], ids["oui"])]),
        "usurper": _type("Usurper", [_role("Usurpateur"), _role("Trône", ("item", "location"))],
                         [_effect("Trône", ids["occupe"], "Usurpateur")]),
        "alerter": _type("Alerter", [_role("Garnison", ("faction",))],
                         [_effect("Garnison", ids["alerte"], 3)]),
        "reperer": _type("Être repéré", [_role("Intrus"), _role("Garnison", ("faction",))],
                         [_effect("Garnison", ids["alerte"], 1, "add")]),
        "tuer": _type("Tuer", [_role("Tueur"), _role("Victime", ("character",), sorte=True)],
                      [_effect("Victime", "sys:vital_status", "dead")]),
    }
    made: dict[str, str] = {}
    with Session(engine) as db:
        for key, spec in specs.items():
            made[key] = write_event_type(db, world_id=w, spec=spec).id
        db.commit()
        got = {}
        for key, type_id in made.items():
            view = type_view(db, type_id)
            names = {r.id: r.name for r in view.roles}
            got[key] = [(names[e.role_id], e.attribute, e.mode, e.value_kind,
                         names.get(e.value, e.value) if e.value_kind == "role" else e.value) for e in view.effects]
    want = {
        "ouvrir": [("Cible", ids["ouvert"], "set", "choice", ids["oui"])],
        "usurper": [("Trône", ids["occupe"], "set", "role", "Usurpateur")],
        "alerter": [("Garnison", ids["alerte"], "set", "integer", 3)],
        "reperer": [("Garnison", ids["alerte"], "add", "integer", 1)],
        "tuer": [("Victime", "sys:vital_status", "set", "choice", "dead")],
    }
    if got != want:
        fail(f"EF2: the effects read back are {got}")
    cible = [_role("Ouvreur"), _role("Cible", ("location", "item"))]
    refused = (
        ("an unknown state", _type("X1", cible, [_effect("Cible", "nope", "oui")])),
        ("Magie", _type("X2", cible, [_effect("Cible", "sys:magic_status", "active")])),
        ("a sorte-only role", _type("X3", [_role("Proie", (), sorte=True)],
                                    [_effect("Proie", "sys:vital_status", "dead")])),
        ("a state for no type of the role", _type("X4", [_role("Qui")], [_effect("Qui", ids["ouvert"], ids["oui"])])),
        ("a value not a choice", _type("X5", cible, [_effect("Cible", ids["ouvert"], "peut-être")])),
        ("add on a choice", _type("X6", cible, [_effect("Cible", ids["ouvert"], ids["oui"], "add")])),
        ("a text for an integer", _type("X7", [_role("G", ("faction",))], [_effect("G", ids["alerte"], "3")])),
        ("the same role as value", _type("X8", [_role("U"), _role("T", ("item",))], [_effect("T", ids["occupe"], "T")])),
        ("an unknown value role", _type("X9", [_role("U"), _role("T", ("item",))],
                                        [_effect("T", ids["occupe"], "Personne")])),
        ("a value role the state may not name", _type("X10", [_role("U", ("faction",)), _role("T", ("item",))],
                                                      [_effect("T", ids["occupe"], "U")])),
        ("one role and state twice", _type("X11", cible, [_effect("Cible", ids["ouvert"], ids["oui"]),
                                                          _effect("Cible", ids["ouvert"], ids["non"])])),
        ("nine effects", _type("X12", [_role(f"R{i}", ("location",)) for i in range(8)] + [_role("R8", ("location",))],
                               [_effect(f"R{i}", ids["ouvert"], ids["oui"]) for i in range(9)])),
    )
    with Session(engine) as db:
        for label, spec in refused:
            _refused(db, label, "EF2", lambda spec=spec: write_event_type(db, world_id=w, spec=spec))
    return made


def check_ef3(engine, ids: dict, made: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.models import EventTypeEffect
    from world_engine.writes.attributes import (
        ChoiceSpec,
        DefinitionSpec,
        set_attribute_status,
        write_attribute_definition,
    )
    from world_engine.writes.event_types import write_event_type

    w = ids["world"]
    with Session(engine) as db:
        _refused(db, "retiring a state an effect names", "EF3",
                 lambda: set_attribute_status(db, world_id=w, definition_id=ids["ouvert"], status="retired"))
        _refused(db, "changing its kind", "EF3", lambda: write_attribute_definition(
            db, world_id=w, definition_id=ids["ouvert"], spec=DefinitionSpec(
                name="Ouvert", kind="integer", holder_types=("location", "item"), default=0)))
        _refused(db, "dropping the choice an effect names", "EF3", lambda: write_attribute_definition(
            db, world_id=w, definition_id=ids["ouvert"], spec=DefinitionSpec(
                name="Ouvert", kind="choice", holder_types=("location", "item"),
                choices=(ChoiceSpec("non", ids["non"]), ChoiceSpec("fermé")), default="non")))
        write_event_type(db, world_id=w, type_id=made["ouvrir"], spec=_type(
            "Ouvrir", [_role("Ouvreur"), _role("Cible", ("location", "item"))], []))
        db.commit()
        left = db.exec(select(EventTypeEffect).where(EventTypeEffect.type_id == made["ouvrir"])).all()
        if left:
            fail(f"EF3: « Ouvrir » saved with no effect keeps {len(left)} effect row(s)")
        try:
            set_attribute_status(db, world_id=w, definition_id=ids["ouvert"], status="retired")
            db.commit()
        except ValueError as exc:
            db.rollback()
            fail(f"EF3: once no effect names « Ouvert », retiring it is refused: {exc}")


def check_ef4(engine, ids: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.models import AttributeChange, Event
    from world_engine.writes.attributes import set_attribute_status, write_attribute_value
    from world_engine.writes.event_types import ensure_domain_type

    w = ids["world"]
    with Session(engine) as db:
        set_attribute_status(db, world_id=w, definition_id=ids["ouvert"], status="active")
        event = Event(world_id=w, type_id=ensure_domain_type(db, world_id=w, domain="other").id, title="t")
        db.add(event)
        db.commit()
        before = len(db.exec(select(AttributeChange)).all())
        try:
            write_attribute_value(db, world_id=w, definition_id=ids["ouvert"], entity_id=ids["porte"],
                                  value=ids["oui"], kind="correction", changed_by="check", event_id=event.id)
            fail("EF4: a correction naming an event was not refused")
        except ValueError:
            db.rollback()
        if len(db.exec(select(AttributeChange)).all()) != before:
            fail("EF4: the refused correction wrote a change")
        change = write_attribute_value(db, world_id=w, definition_id=ids["ouvert"], entity_id=ids["porte"],
                                       value=ids["oui"], kind="changement", changed_by="check", event_id=event.id)
        db.commit()
        if change is None or db.get(AttributeChange, change.id).event_id != event.id:
            fail("EF4: a changement does not keep its event")


# --- EF5 -------------------------------------------------------------------------

def _v2_25_db() -> str:
    """A database the migration was written for: every table of the code
    but `event_type_effect` and the two it changes, those in v2.25 DDL."""
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
    eng = create_engine(f"sqlite:///{db_path}")
    skipped = {"event_type_effect", "attribute_change", "lore_entry_row"}
    SQLModel.metadata.create_all(eng, tables=[t for n, t in SQLModel.metadata.tables.items() if n not in skipped])
    eng.dispose()
    with sqlite3.connect(db_path) as conn:
        for statement in V2_25_DDL:
            conn.execute(statement)
        conn.executescript("""
            INSERT INTO schema_meta (id, static_version, updated_at) VALUES (1, 'v2.24', '2026-10-01');
            INSERT INTO world (id, name, is_active, created_at, updated_at) VALUES ('w', 'W', 0, '2026-10-01', '2026-10-01');
            INSERT INTO entity (id, world_id, type, name, status, created_at, updated_at)
              VALUES ('a', 'w', 'location', 'A', 'active', '2026-10-01', '2026-10-01');
            INSERT INTO attribute_definition (id, world_id, name, kind, is_hidden, status, created_at, updated_at)
              VALUES ('d', 'w', 'Ouvert', 'integer', 0, 'active', '2026-10-01', '2026-10-01');
            INSERT INTO attribute_value (id, world_id, definition_id, entity_id, integer_value, updated_at)
              VALUES ('v', 'w', 'd', 'a', 1, '2026-10-01');
            INSERT INTO attribute_change (id, world_id, value_id, kind, changed_by, after_integer, changed_at)
              VALUES ('c', 'w', 'v', 'correction', 'creator', 1, '2026-10-01');
            INSERT INTO lore_entry (id, world_id, statement, created_at) VALUES ('le', 'w', 's', '2026-10-01');
            INSERT INTO lore_entry_row (id, entry_id, row_table, row_id, action)
              VALUES ('r', 'le', 'entity', 'a', 'created');
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
            "effect": bool(sql("event_type_effect")),
            "event_id": "event_id" in [r[1] for r in conn.execute("PRAGMA table_info(attribute_change)")],
            "index": bool(sql("idx_attribute_change_event")),
            "lore_check": "'event'" in sql("lore_entry_row"),
            "rows": (conn.execute("SELECT id, after_integer FROM attribute_change").fetchall(),
                     conn.execute("SELECT id, row_table FROM lore_entry_row").fetchall()),
        }


def check_ef5() -> None:
    db_path = _v2_25_db()
    before = _snapshot(db_path)
    refused = _run_migration(db_path)
    if refused.returncode == 0 or _snapshot(db_path) != before:
        fail(f"EF5: v2.24 was not refused untouched (exit {refused.returncode})")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.25' WHERE id = 1")
    result = _run_migration(db_path)
    after = _snapshot(db_path)
    want = {"version": "v2.26", "effect": True, "event_id": True, "index": True, "lore_check": True,
            "rows": ([("c", 1)], [("r", "entity")])}
    if result.returncode != 0 or after != want:
        fail(f"EF5: exit {result.returncode}, state {after}: {result.stderr.strip()[-300:]}")
    again = _run_migration(db_path)
    if again.returncode != 0 or "already fully applied" not in again.stdout or _snapshot(db_path) != after:
        fail(f"EF5: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    state: dict = {}

    def ef2() -> None:
        state["made"] = check_ef2(engine, ids)

    rules = (
        ("EF1", check_ef1), ("EF2", ef2), ("EF3", lambda: check_ef3(engine, ids, state["made"])),
        ("EF4", lambda: check_ef4(engine, ids)), ("EF5", check_ef5),
    )
    for name, rule in rules:
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_effects -- v2.26 keeps what an event type does to the state of the world: the role whose "
          "entity changes, the state, and a value of its kind; a state an effect names is never taken away, and "
          "a change keeps the event that made it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
