"""G1 check for TICKET-0113 -- the state of the world: a world's attributes, one value per entity, its history kept.

BRIEF-0113-A's rules, then BRIEF-0113-C's (the Création surfaces); the
attribute condition form has its own check,
`attribute_conditions.py` (BRIEF-0113-B), so each stays inside the
corpus's per-check time budget.

AA1 -- storage (BRIEF-0113-A, import). The five attribute tables carry
   exactly their contract's columns, CHECK names and index names; no column
   of theirs is JSON; `ATTRIBUTE_KINDS`, `ATTRIBUTE_TYPE_SIDES`,
   `ATTRIBUTE_STATUSES` and `ATTRIBUTE_CHANGE_KINDS` are the values their
   CHECKs quote, in order, and `ATTRIBUTE_CHANGE_KINDS` is
   `writes.facts.FACT_CHANGE_KINDS`; the code's schema version is v2.22 or
   later.
AA2 -- the definition writer (fixture). `write_attribute_definition` writes
   a `choice`, an `integer` and an `entity` definition; `attribute_view`
   reads each back with its types, its choices in order and its default;
   `world_attributes` lists the three system attributes first, then the
   definitions by name. Refused, each with no row written: an unknown kind,
   an empty name, a system attribute's name (any case or accent), another
   definition's name (« maudit » against « Maudit »), an unknown entity
   type, no holder type, a choice kind with one label or a default that is
   none of its labels, an integer kind with a non-integer default, an
   entity kind with no value type, value types on a choice kind, an id on a
   new definition's choice.
AA3 -- values and history (fixture). `write_attribute_value` sets a choice,
   an integer and an entity value, each appending one `attribute_change`
   whose `before_*` is the default and `after_*` the value, with its kind;
   a second write's `before_*` is the first value; an unchanged write
   returns None and adds no row; `current_value` reads the default with
   `is_default` before any write and the value after. Refused, each with no
   row written: an unknown change kind, no `changed_by`, an entity of a
   type the definition does not name, a label of another definition, an
   entity value of a type the definition does not name, a non-integer for
   an integer, a retired definition.
AA4 -- vocabularies (fixture, import). `BUILTIN_ENTITY_TYPES` is
   `ENTITY_TYPE_REGISTRY`'s keys; `sys:status` reads `ENTITY_STATUSES`,
   `sys:vital_status` the character's `vital_status` options and
   `sys:magic_status` the location's `magic_status` options, each in order;
   `world_entity_types` adds an active runtime type's slug and never a
   retired one; `current_value` reads each system attribute from its column.
AA5 -- in use (WJ2, fixture). Once a value exists, the kind cannot change
   and a holder type an entity holding a value has cannot be dropped; a
   label a value holds cannot be dropped; an unused label dropped is
   retired, its row kept; the same label named again comes back active;
   renaming a definition writes no `attribute_change`; a definition with no
   condition is retired and restored.
AA6 -- migration `scripts/migrate_v2_22_attributes.py`, on a database
   without the five tables: at v2.20 it refuses and creates nothing; at
   v2.21 it creates the five tables with the models' columns, zero rows,
   and sets `schema_meta` to v2.22 -- its own version; a second run says
   nothing to do.
AA7 -- the reader writes nothing (static, AST). `attributes.py` calls no
   `add`, `commit`, `delete`, `execute` or `flush`.
AC1 -- the routes (BRIEF-0113-C, route functions on the AA world made
   active). `list_attributes` lists the system attributes first, the
   retired ones too, each with `in_condition`, and the world's types with
   their French names (a runtime type by its name). A new name near
   another's (« Maudit » beside « Maudite ») answers `saved: false` with the
   near one and writes nothing; `confirm_near` writes it; saving a
   definition under its own name asks nothing. `get_states` lists the
   system attributes then the world's that apply to the entity, with value,
   `is_default` and history; `set_state` writes a change of the kind given
   and answers the states with its history line (before, after, kind); a
   system key, an unknown kind or a refused value answer 422 and write
   nothing.
AC2 -- nearness (fixture). `near_attributes` finds « Maudite » for
   « maudit » (score 92 or more) and the system « État vital » for « etat
   vitale », never an attribute it excludes, nothing for « Porte rouge »;
   `lore_resolve.near_in_surfaces` and `near_attributes` both score through
   `near_ratio` (static).
AC3 -- the Création surfaces (static). `tabs.js`'s `etats` entry mounts
   the `states` island in `creation-etats` and routes « + Nouvel état »
   through `triggerPrimaryAction('states')`; `registry.js` declares
   `states` as origin 'new', created by TICKET-0113; `States.svelte` exports
   `primaryAction` and renders `<AttributeDefinitionForm`;
   `attributes.svelte.js` exports `definitionDraft` and `definitionBody`
   and sends `confirm_near`; `Sheet.svelte` renders `<StatesPanel` for a
   saved entity; `StatesPanel.svelte` sends the change's `kind`, offers
   `correction` and `changement`, and preselects neither.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
MIGRATION_V2_22 = ROOT / "scripts" / "migrate_v2_22_attributes.py"

FAILURES: list[str] = []

TABLES: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "attribute_definition": (
        ("id", "world_id", "name", "kind", "default_integer", "is_hidden", "status", "created_at", "updated_at"),
        ("ck_attribute_definition_kind", "ck_attribute_definition_status", "ck_attribute_definition_default"),
        ("idx_attribute_definition_name",),
    ),
    "attribute_definition_type": (
        ("id", "world_id", "definition_id", "side", "entity_type"),
        ("ck_attribute_definition_type_side",),
        ("idx_attribute_definition_type_unique",),
    ),
    "attribute_choice": (
        ("id", "world_id", "definition_id", "label", "position", "is_default", "status"),
        ("ck_attribute_choice_status", "ck_attribute_choice_default"),
        ("idx_attribute_choice_label", "idx_attribute_choice_one_default"),
    ),
    "attribute_value": (
        ("id", "world_id", "definition_id", "entity_id", "choice_id", "integer_value", "entity_value_id",
         "updated_at"),
        ("ck_attribute_value_one",),
        ("idx_attribute_value_pair", "idx_attribute_value_entity"),
    ),
    "attribute_change": (
        ("id", "world_id", "value_id", "kind", "changed_by", "before_choice_id", "before_integer",
         "before_entity_id", "after_choice_id", "after_integer", "after_entity_id", "changed_at"),
        ("ck_attribute_change_kind",),
        ("idx_attribute_change_value",),
    ),
}


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


# --- AA1 -------------------------------------------------------------------------

def _quoted(sql: str) -> tuple[str, ...]:
    return tuple(re.findall(r"'([^']+)'", sql))


def check_aa1() -> None:
    from sqlalchemy import JSON, CheckConstraint
    from sqlmodel import SQLModel

    from world_engine import models
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
    from world_engine.writes.facts import FACT_CHANGE_KINDS

    seen = 0
    for name, (columns, checks, indexes) in TABLES.items():
        table = SQLModel.metadata.tables.get(name)
        if table is None:
            fail(f"AA1: table {name} is not declared")
            continue
        seen += 1
        if tuple(table.c.keys()) != columns:
            fail(f"AA1: {name} columns are {tuple(table.c.keys())}")
        found = tuple(sorted(c.name for c in table.constraints if isinstance(c, CheckConstraint)))
        if found != tuple(sorted(checks)):
            fail(f"AA1: {name} CHECKs are {found}")
        if tuple(sorted(i.name for i in table.indexes)) != tuple(sorted(indexes)):
            fail(f"AA1: {name} indexes are {sorted(i.name for i in table.indexes)}")
        for column in table.c:
            if isinstance(column.type, JSON):
                fail(f"AA1: {name}.{column.name} is JSON")
    if seen != len(TABLES):
        fail(f"AA1: {seen} of {len(TABLES)} tables declared")
    meta = SQLModel.metadata.tables

    def check_text(table: str, ck: str) -> str:
        return next(str(c.sqltext) for c in meta[table].constraints
                    if isinstance(c, CheckConstraint) and c.name == ck)

    pairs = (
        (models.ATTRIBUTE_KINDS, check_text("attribute_definition", "ck_attribute_definition_kind")),
        (models.ATTRIBUTE_STATUSES, check_text("attribute_definition", "ck_attribute_definition_status")),
        (models.ATTRIBUTE_STATUSES, check_text("attribute_choice", "ck_attribute_choice_status")),
        (models.ATTRIBUTE_TYPE_SIDES, check_text("attribute_definition_type", "ck_attribute_definition_type_side")),
        (models.ATTRIBUTE_CHANGE_KINDS, check_text("attribute_change", "ck_attribute_change_kind")),
    )
    for values, sql in pairs:
        if tuple(values) != _quoted(sql):
            fail(f"AA1: {values} is not the CHECK's {_quoted(sql)}")
    if tuple(models.ATTRIBUTE_CHANGE_KINDS) != tuple(FACT_CHANGE_KINDS):
        fail(f"AA1: ATTRIBUTE_CHANGE_KINDS {models.ATTRIBUTE_CHANGE_KINDS} != FACT_CHANGE_KINDS")
    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 22):
        fail(f"AA1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")


# --- fixture -----------------------------------------------------------------------

def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, EntityType, Item, Location, World

    with Session(engine) as db:
        world = World(name="Attributs", is_active=False)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("ysa", "character", "Ysa"), ("garde", "character", "Garde"),
                                ("trone", "item", "Trône"), ("crypte", "location", "Crypte"),
                                ("guilde", "faction", "Guilde")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "character":
                db.add(Character(id=entity.id, world_id=world.id, character_type="npc"))
            elif kind == "item":
                db.add(Item(id=entity.id))
            elif kind == "location":
                db.add(Location(id=entity.id))
        for slug, status in (("navire", "active"), ("epave", "retired")):
            db.add(EntityType(world_id=world.id, name=slug, slug=slug, physical_table=f"ext_{slug}",
                              status=status))
        db.commit()
    return ids


def _count(db, model) -> int:
    from sqlmodel import func, select

    return db.exec(select(func.count()).select_from(model)).one()


def _counts(db) -> tuple[int, ...]:
    from world_engine import models

    return tuple(_count(db, m) for m in (models.AttributeDefinition, models.AttributeDefinitionType,
                                         models.AttributeChoice, models.AttributeValue,
                                         models.AttributeChange))


def _refused(db, label: str, rule: str, call) -> None:
    before = _counts(db)
    try:
        call()
    except ValueError:
        db.rollback()
        if _counts(db) != before:
            fail(f"{rule}: {label} was refused after writing a row")
        return
    db.rollback()
    fail(f"{rule}: {label} was accepted")


def _spec(**fields):
    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec

    base = dict(name="Maudit", kind="choice", holder_types=("character", "item"),
                choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non")
    base.update(fields)
    if "choices" in fields and fields["choices"] and isinstance(fields["choices"][0], str):
        base["choices"] = tuple(ChoiceSpec(c) for c in fields["choices"])
    return DefinitionSpec(**base)


def _definitions(engine, ids) -> dict:
    from sqlmodel import Session

    from world_engine.writes.attributes import write_attribute_definition

    with Session(engine) as db:
        made = {}
        for key, spec in (
            ("maudit", _spec()),
            ("alerte", _spec(name="Niveau d'alerte", kind="integer", holder_types=("location",),
                             choices=(), default=2)),
            ("occupe", _spec(name="Occupé par", kind="entity", holder_types=("item",),
                             value_types=("character",), choices=(), default=None)),
        ):
            made[key] = write_attribute_definition(db, world_id=ids["world"], spec=spec).id
        db.commit()
    return made


def check_aa2(engine, ids: dict, defs: dict) -> None:
    from sqlmodel import Session

    from world_engine.attributes import SYSTEM_ATTRIBUTES, attribute_view, world_attributes
    from world_engine.writes.attributes import write_attribute_definition

    with Session(engine) as db:
        maudit = attribute_view(db, ids["world"], defs["maudit"])
        if maudit is None or maudit.kind != "choice" or maudit.holder_types != ("character", "item") \
                or [label for _key, label in maudit.choices] != ["non", "oui"] \
                or maudit.default != maudit.choices[0][0] or maudit.hidden or maudit.system:
            fail(f"AA2: the choice definition reads back as {maudit}")
        alerte = attribute_view(db, ids["world"], defs["alerte"])
        if alerte is None or alerte.kind != "integer" or alerte.default != 2 or alerte.choices:
            fail(f"AA2: the integer definition reads back as {alerte}")
        occupe = attribute_view(db, ids["world"], defs["occupe"])
        if occupe is None or occupe.value_types != ("character",) or occupe.default is not None:
            fail(f"AA2: the entity definition reads back as {occupe}")
        listed = [v.key for v in world_attributes(db, ids["world"])]
        want = [s.key for s in SYSTEM_ATTRIBUTES] + [defs["maudit"], defs["alerte"], defs["occupe"]]
        if listed != want:
            fail(f"AA2: world_attributes lists {listed}")
        cases = {
            "an unknown kind": _spec(name="A", kind="texte"),
            "an empty name": _spec(name="  "),
            "a system attribute's name": _spec(name="etat VITAL"),
            "another definition's name": _spec(name="maudit"),
            "an unknown entity type": _spec(name="B", holder_types=("dragon",)),
            "no holder type": _spec(name="C", holder_types=()),
            "a choice kind with one label": _spec(name="D", choices=("oui",), default="oui"),
            "a default that is none of its labels": _spec(name="E", default="peut-être"),
            "an integer default that is not one": _spec(name="F", kind="integer", choices=(), default="3"),
            "an entity kind with no value type": _spec(name="G", kind="entity", choices=(), default=None),
            "value types on a choice kind": _spec(name="H", value_types=("character",)),
        }
        for label, spec in cases.items():
            _refused(db, label, "AA2", lambda spec=spec: write_attribute_definition(
                db, world_id=ids["world"], spec=spec))
        from world_engine.writes.attributes import ChoiceSpec
        with_id = _spec(name="I", choices=(ChoiceSpec("a", id="x"), ChoiceSpec("b")), default="a")
        _refused(db, "an id on a new definition's choice", "AA2", lambda: write_attribute_definition(
            db, world_id=ids["world"], spec=with_id))


def check_aa3(engine, ids: dict, defs: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.attributes import attribute_view, current_value
    from world_engine.models import AttributeChange, Entity
    from world_engine.writes.attributes import set_attribute_status, write_attribute_definition, \
        write_attribute_value

    with Session(engine) as db:
        world = ids["world"]
        maudit = attribute_view(db, world, defs["maudit"])
        non, oui = (key for key, _label in maudit.choices)
        ysa = db.get(Entity, ids["ysa"])
        before = current_value(db, maudit, ysa)
        if before.raw != non or not before.is_default or before.label != "non":
            fail(f"AA3: before any write, Ysa reads {before}")
        first = write_attribute_value(db, world_id=world, definition_id=defs["maudit"], entity_id=ids["ysa"],
                                      value=oui, kind="changement", changed_by="creator_crud")
        second = write_attribute_value(db, world_id=world, definition_id=defs["maudit"], entity_id=ids["ysa"],
                                       value=non, kind="correction", changed_by="creator_crud")
        same = write_attribute_value(db, world_id=world, definition_id=defs["maudit"], entity_id=ids["ysa"],
                                     value=non, kind="correction", changed_by="creator_crud")
        db.commit()
        if first is None or (first.before_choice_id, first.after_choice_id, first.kind) != (non, oui, "changement"):
            fail(f"AA3: the first change is {first}")
        if second is None or (second.before_choice_id, second.after_choice_id, second.kind) != (oui, non, "correction"):
            fail(f"AA3: the second change is {second}")
        if same is not None:
            fail("AA3: an unchanged value appended a change")
        after = current_value(db, maudit, ysa)
        if after.raw != non or after.is_default:
            fail(f"AA3: after the writes, Ysa reads {after}")
        alerte = write_attribute_value(db, world_id=world, definition_id=defs["alerte"], entity_id=ids["crypte"],
                                       value=-1, kind="changement", changed_by="creator_crud")
        occupe = write_attribute_value(db, world_id=world, definition_id=defs["occupe"], entity_id=ids["trone"],
                                       value=ids["ysa"], kind="changement", changed_by="creator_crud")
        db.commit()
        if alerte is None or (alerte.before_integer, alerte.after_integer) != (2, -1):
            fail(f"AA3: the integer change is {alerte}")
        if occupe is None or (occupe.before_entity_id, occupe.after_entity_id) != (None, ids["ysa"]):
            fail(f"AA3: the entity change is {occupe}")
        rows = db.exec(select(AttributeChange)).all()
        if len(rows) != 4:
            fail(f"AA3: {len(rows)} changes written, expected 4")
        other = write_attribute_definition(db, world_id=world, spec=_spec(name="Ouvert", holder_types=("location",)))
        db.commit()
        foreign = attribute_view(db, world, other.id).choices[0][0]

        def value(definition, entity, raw, kind="changement", by="creator_crud"):
            return lambda: write_attribute_value(db, world_id=world, definition_id=defs[definition] if definition
                                                 in defs else definition, entity_id=ids[entity], value=raw,
                                                 kind=kind, changed_by=by)

        cases = {
            "an unknown change kind": value("maudit", "garde", oui, kind="oubli"),
            "no changed_by": value("maudit", "garde", oui, by=""),
            "an entity of a type it does not name": value("maudit", "crypte", oui),
            "a label of another definition": value("maudit", "garde", foreign),
            "an entity value of a type it does not name": value("occupe", "trone", ids["guilde"]),
            "a non-integer for an integer": value("alerte", "crypte", "3"),
        }
        for label, call in cases.items():
            _refused(db, label, "AA3", call)
        set_attribute_status(db, world_id=world, definition_id=other.id, status="retired")
        db.commit()
        _refused(db, "a retired definition", "AA3", value(other.id, "crypte", foreign))


def check_aa4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.attributes import BUILTIN_ENTITY_TYPES, SYSTEM_ATTRIBUTES, attribute_view, \
        current_value, world_entity_types
    from world_engine.cockpit.crud.entities import ENTITY_STATUSES, ENTITY_TYPE_REGISTRY
    from world_engine.models import Character, Entity, Location

    if tuple(ENTITY_TYPE_REGISTRY) != BUILTIN_ENTITY_TYPES:
        fail(f"AA4: BUILTIN_ENTITY_TYPES {BUILTIN_ENTITY_TYPES} != {tuple(ENTITY_TYPE_REGISTRY)}")

    def options(entity_type: str, field: str) -> tuple:
        spec = next(f for f in ENTITY_TYPE_REGISTRY[entity_type]["fields"] if f["name"] == field)
        return tuple(spec["options"])

    want = {"sys:status": tuple(ENTITY_STATUSES), "sys:vital_status": options("character", "vital_status"),
            "sys:magic_status": options("location", "magic_status")}
    got = {s.key: tuple(v for v, _label in s.values) for s in SYSTEM_ATTRIBUTES}
    if got != want:
        fail(f"AA4: the system vocabularies are {got}, expected {want}")
    with Session(engine) as db:
        types = world_entity_types(db, ids["world"])
        if types != BUILTIN_ENTITY_TYPES + ("navire",):
            fail(f"AA4: world_entity_types is {types}")
        db.get(Character, ids["garde"]).vital_status = "dead"
        db.get(Location, ids["crypte"]).magic_status = "nexus"
        db.get(Entity, ids["trone"]).status = "destroyed"
        db.commit()
        reads = {
            ("sys:vital_status", "garde"): "dead", ("sys:magic_status", "crypte"): "nexus",
            ("sys:status", "trone"): "destroyed",
        }
        for (key, entity), raw in reads.items():
            value = current_value(db, attribute_view(db, ids["world"], key), db.get(Entity, ids[entity]))
            if value.raw != raw or value.is_default:
                fail(f"AA4: {key} of {entity} reads {value}")


def check_aa5(engine, ids: dict, defs: dict) -> None:
    from sqlmodel import Session, select

    from world_engine.attributes import attribute_view
    from world_engine.models import AttributeChange, AttributeChoice, AttributeDefinition
    from world_engine.writes.attributes import ChoiceSpec, set_attribute_status, write_attribute_definition

    with Session(engine) as db:
        world = ids["world"]
        view = attribute_view(db, world, defs["maudit"])
        (non_id, _), (oui_id, _) = view.choices
        save = lambda spec: (lambda: write_attribute_definition(  # noqa: E731
            db, world_id=world, spec=spec, definition_id=defs["maudit"]))
        _refused(db, "a kind change once a value exists", "AA5", lambda: write_attribute_definition(
            db, world_id=world, definition_id=defs["alerte"],
            spec=_spec(name="Niveau d'alerte", holder_types=("location",))))
        _refused(db, "dropping a holder type a value holds", "AA5", save(_spec(holder_types=("item",))))
        _refused(db, "dropping a label a value holds", "AA5",
                 save(_spec(choices=(ChoiceSpec("oui", id=oui_id), ChoiceSpec("peut-être")), default="oui")))
        changes = len(db.exec(select(AttributeChange)).all())
        write_attribute_definition(db, world_id=world, definition_id=defs["maudit"], spec=_spec(
            name="Maudite", choices=(ChoiceSpec("non", id=non_id), ChoiceSpec("peut-être")), default="non"))
        db.commit()
        oui = db.get(AttributeChoice, oui_id)
        if oui is None or oui.status != "retired":
            fail(f"AA5: an unused label dropped is {oui and oui.status}")
        if db.get(AttributeDefinition, defs["maudit"]).name != "Maudite":
            fail("AA5: the definition was not renamed")
        if len(db.exec(select(AttributeChange)).all()) != changes:
            fail("AA5: saving a definition wrote an attribute_change")
        write_attribute_definition(db, world_id=world, definition_id=defs["maudit"], spec=_spec(
            name="Maudite", choices=(ChoiceSpec("non", id=non_id), ChoiceSpec("oui")), default="non"))
        db.commit()
        back = db.get(AttributeChoice, oui_id)
        if back.status != "active" or [k for k, _l in attribute_view(db, world, defs["maudit"]).choices] \
                != [non_id, oui_id]:
            fail("AA5: a retired label named again did not come back")
        retired = set_attribute_status(db, world_id=world, definition_id=defs["alerte"], status="retired")
        restored = set_attribute_status(db, world_id=world, definition_id=defs["alerte"], status="active")
        db.commit()
        if retired.status != "active" or restored.status != "active":
            fail("AA5: a definition with no condition was not retired then restored")


# --- AA6 -------------------------------------------------------------------------

def _run_migration(path: pathlib.Path, db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(path)], env=env, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


def _drop_attributes(db_path: str, version: str) -> None:
    with sqlite3.connect(db_path) as conn:
        for name in reversed(tuple(TABLES)):
            conn.execute(f"DROP TABLE IF EXISTS {name}")
        conn.execute("UPDATE schema_meta SET static_version = ? WHERE id = 1", (version,))


def _state(db_path: str) -> tuple[dict, str]:
    with sqlite3.connect(db_path) as conn:
        shapes = {}
        for name in TABLES:
            cols = tuple(r[1] for r in conn.execute(f"PRAGMA table_info({name})"))
            count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] if cols else None
            shapes[name] = (cols, count)
        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
    return shapes, version


def _migrated_db() -> str:
    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel

    from world_engine.models import SchemaMeta

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "migrate.db")
    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        session.add(SchemaMeta(id=1, static_version="v2.21"))
        session.commit()
    eng.dispose()
    return db_path


def check_aa6() -> None:
    db_path = _migrated_db()
    _drop_attributes(db_path, "v2.20")
    result = _run_migration(MIGRATION_V2_22, db_path)
    shapes, _version = _state(db_path)
    if result.returncode == 0 or any(cols for cols, _count in shapes.values()):
        fail(f"AA6: v2.20 was not refused (exit {result.returncode})")
    _drop_attributes(db_path, "v2.21")
    result = _run_migration(MIGRATION_V2_22, db_path)
    shapes, version = _state(db_path)
    want = {name: (cols, 0) for name, (cols, _checks, _indexes) in TABLES.items()}
    if result.returncode != 0 or shapes != want or version != "v2.22":
        fail(f"AA6: exit {result.returncode}, version {version}, shapes {shapes}: {result.stderr.strip()[-200:]}")
    again = _run_migration(MIGRATION_V2_22, db_path)
    if again.returncode != 0 or "nothing to do" not in again.stdout:
        fail(f"AA6: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")


# --- AA7 -------------------------------------------------------------------------

def check_aa7() -> None:
    path = SRC / "attributes.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    if not calls:
        fail("AA7: attributes.py makes no attribute call at all")
    for call in calls:
        if call.func.attr in ("add", "commit", "delete", "execute", "flush"):
            fail(f"AA7: attributes.py calls .{call.func.attr} on line {call.lineno}")


# --- AC1 -------------------------------------------------------------------------

def check_ac1(engine, ids: dict, defs: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.routes import attributes as routes
    from world_engine.models import AttributeChange, AttributeDefinition, World

    with Session(engine) as db:
        db.get(World, ids["world"]).is_active = True
        db.commit()
        listed = routes.list_attributes(db)
        keys = [a["key"] for a in listed["attributes"]]
        if keys[:3] != ["sys:vital_status", "sys:status", "sys:magic_status"] or not all(
                "in_condition" in a for a in listed["attributes"]):
            fail(f"AC1: list_attributes lists {keys}")
        labels = {t["type"]: t["label"] for t in listed["entity_types"]}
        if labels.get("character") != "Personnage" or labels.get("navire") != "navire" or "epave" in labels:
            fail(f"AC1: the entity types read {labels}")
        before = _count(db, AttributeDefinition)
        body = routes.DefinitionBody(name="Maudit", kind="choice", holder_types=["character"],
                                     choices=[routes.ChoiceBody(label="non"), routes.ChoiceBody(label="oui")],
                                     default="non")
        asked = routes.create_attribute(body, db)
        if asked.get("saved") is not False or "Maudite" not in [n["name"] for n in asked.get("near", [])] \
                or _count(db, AttributeDefinition) != before:
            fail(f"AC1: a near name answered {asked}")
        body.confirm_near = True
        made = routes.create_attribute(body, db)
        if made.get("saved") is not True or _count(db, AttributeDefinition) != before + 1:
            fail(f"AC1: confirm_near answered {made}")
        same = routes.save_attribute(made["attribute"]["key"], routes.DefinitionBody(
            name="Maudit", kind="choice", holder_types=["character"], default="oui",
            choices=[routes.ChoiceBody(label=c["label"], id=c["value"]) for c in made["attribute"]["choices"]]), db)
        if same.get("saved") is not True:
            fail(f"AC1: saving a definition under its own name answered {same}")
        states = routes.get_states(ids["garde"], db)
        names = [st["name"] for st in states]
        if names[:2] != ["État vital", "Statut"] or "Maudit" not in names or "Niveau d'alerte" in names:
            fail(f"AC1: get_states lists {names}")
        key = made["attribute"]["key"]
        non = next(c["value"] for c in made["attribute"]["choices"] if c["label"] == "non")
        after = routes.set_state(ids["garde"], key, routes.ValueBody(value=non, kind="changement"), db)
        row = next(st for st in after if st["key"] == key)
        line = row["history"][0] if len(row["history"]) == 1 else {}
        if row["label"] != "non" or row["is_default"] \
                or (line.get("kind"), line.get("before"), line.get("after")) != ("changement", "oui", "non"):
            fail(f"AC1: set_state answered {row}")
        changes = _count(db, AttributeChange)
        for label, call in {
            "a system key": lambda: routes.set_state(ids["garde"], "sys:vital_status",
                                                     routes.ValueBody(value="dead", kind="correction"), db),
            "an unknown kind": lambda: routes.set_state(ids["garde"], key, routes.ValueBody(value=non, kind="x"), db),
            "a refused value": lambda: routes.set_state(ids["garde"], key, routes.ValueBody(value="z",
                                                                                           kind="correction"), db),
        }.items():
            try:
                call()
                fail(f"AC1: set_state accepts {label}")
            except HTTPException as exc:
                if exc.status_code != 422 or _count(db, AttributeChange) != changes:
                    fail(f"AC1: {label} answered {exc.status_code} or wrote a change")
        db.get(World, ids["world"]).is_active = False
        db.commit()


# --- AC2 -------------------------------------------------------------------------

def check_ac2(engine, ids: dict, defs: dict) -> None:
    from sqlmodel import Session

    from world_engine.attributes import near_attributes

    with Session(engine) as db:
        world = ids["world"]
        found = {n.name: n.score for n in near_attributes(db, world, "maudit")}
        if found.get("Maudite", 0) < 92:
            fail(f"AC2: « maudit » finds {found}")
        if "État vital" not in {n.name for n in near_attributes(db, world, "etat vitale")}:
            fail("AC2: « etat vitale » does not find the system « État vital »")
        if any(n.key == defs["maudit"] for n in near_attributes(db, world, "maudit", exclude_key=defs["maudit"])):
            fail("AC2: an excluded attribute is listed")
        if near_attributes(db, world, "Porte rouge"):
            fail("AC2: « Porte rouge » finds a near attribute")
    for rel in ("lore_resolve.py", "attributes.py"):
        text = (SRC / rel).read_text(encoding="utf-8")
        if "near_ratio(" not in text:
            fail(f"AC2: {rel} does not score through near_ratio")
    if (SRC / "attributes.py").read_text(encoding="utf-8").count("SequenceMatcher"):
        fail("AC2: attributes.py scores nearness on its own")


# --- AC3 -------------------------------------------------------------------------

def check_ac3() -> None:
    front = ROOT / "frontend" / "src" / "creation"

    def read(name: str) -> str:
        path = front / name
        if not path.exists():
            fail(f"AC3: {name} is missing")
            return ""
        return path.read_text(encoding="utf-8")

    tabs = read("tabs.js")
    entry = re.search(r"\n  etats: \{(.*?)\n  \},", tabs, re.S)
    body = entry.group(1) if entry else ""
    for needle in ("{ key: 'states', containerId: 'creation-etats' }", "triggerPrimaryAction('states')"):
        if needle not in body:
            fail(f"AC3: tabs.js's etats entry lacks {needle}")
    registry = read("registry.js")
    island = re.search(r"\n  states: Object\.freeze\(\{(.*?)\}\),", registry, re.S)
    if not island or "origin: 'new'" not in island.group(1) or "createdBy: 'TICKET-0113'" not in island.group(1):
        fail("AC3: registry.js does not declare the states island as new, TICKET-0113")
    states = read("States.svelte")
    for needle in ("export function primaryAction", "<AttributeDefinitionForm"):
        if needle not in states:
            fail(f"AC3: States.svelte lacks {needle}")
    module = read("attributes.svelte.js")
    for needle in ("export function definitionDraft", "export function definitionBody", "confirm_near"):
        if needle not in module:
            fail(f"AC3: attributes.svelte.js lacks {needle}")
    if "<StatesPanel entityId={detail.id}" not in read("Sheet.svelte"):
        fail("AC3: Sheet.svelte does not render the states panel")
    panel = read("StatesPanel.svelte")
    for needle in ("kind: editing.kind", 'value="correction"', 'value="changement"', "kind: '' }"):
        if needle not in panel:
            fail(f"AC3: StatesPanel.svelte lacks {needle}")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    defs = _definitions(engine, ids)
    rules = (
        ("AA1", check_aa1), ("AA2", lambda: check_aa2(engine, ids, defs)),
        ("AA3", lambda: check_aa3(engine, ids, defs)), ("AA4", lambda: check_aa4(engine, ids)),
        ("AA5", lambda: check_aa5(engine, ids, defs)), ("AA6", check_aa6), ("AA7", check_aa7),
        ("AC1", lambda: check_ac1(engine, ids, defs)), ("AC2", lambda: check_ac2(engine, ids, defs)),
        ("AC3", check_ac3),
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
    print("PASS: attributes -- v2.22 keeps a world's attributes, one value per entity of the types each "
          "names, its history row by row; the system attributes read the canon's own columns; nothing in "
          "use is taken away; Création defines them, asks before a near name, and sets an entity's "
          "value as a correction or a change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
