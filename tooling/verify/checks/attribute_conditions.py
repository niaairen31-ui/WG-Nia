"""G1 check for TICKET-0113 -- the attribute condition form: a leaf reads any attribute of any entity it applies to, and a player never reads a hidden one.

The lot adds its pieces brief by brief; this check grows with it (the
`conditions.py` precedent). Each brief adds its rules here in the same
commit. The attributes themselves are `attributes.py`'s (BRIEF-0113-A).

AB1 -- the form (BRIEF-0113-B, import). `attributes.ATTRIBUTE_FORM` is in
   `REQUIREMENT_TYPES`, `KEY_TARGET_TYPES` and `ANY_SUBJECT_TYPES`, has an
   evaluator, a French phrase, a blocked-step detail and an interpreter
   hint; `vital_status` is in none of them, nor in `FORM_VALUES`; the code's
   schema version is v2.23 or later.
AB2 -- the leaf writer (fixture). `write_condition` stores, and
   `read_condition` returns equal, `attribute` leaves on a world's choice
   (on the doer), integer (« 3 or more », on a fixed location) and entity
   definitions (an entity, and anyone, on a fixed item) and on
   `sys:vital_status` (a fixed character). Refused, each with no row
   written: an unknown attribute, a retired one, a label of another
   attribute, an integer leaf with no threshold, an entity value of a type
   the attribute does not name, a fixed subject of a type it does not apply
   to. Once a leaf names a definition: retiring it, changing its kind,
   dropping its label or the type of the leaf's fixed subject are refused
   (WJ2). `editor_choices` lists every attribute (`key`, `kind`,
   `choices`) and every active entity with its type.
AB3 -- evaluation (fixture). On the doer: a choice leaf reads the default
   before any value, then the value; an integer leaf is met at or above its
   threshold; an entity leaf is met by the entity named, an empty-target
   leaf by anyone, and unmet while the value is empty. A leaf whose fixed
   subject the attribute does not apply to, or `sys:vital_status` on a
   faction giver, is `unknown` with its French reason, no verdict.
AB4 -- what a player may read (WH1, fixture). A leaf on a hidden attribute
   about the PC himself reads `HIDDEN_STATE_FR` and `?` in the PC's
   `verdict_lines`, its name and label in none of his lines;
   `blocked_details_fr` and `player_detail_fr` read
   `HIDDEN_STATE_DETAIL_FR`; the creator's `verdict_lines` writes its name
   and value; a leaf on a visible attribute about the PC shows its value
   and its mark to him. A hidden attribute his character cannot hold (it
   applies to locations only), judged on him through `doer`, is `unknown`
   with `HIDDEN_STATE_REASON_FR`: its name and its label are in none of his
   `verdict_lines` nor `blocked_details_fr` (AMENDMENT-0113-01).
AB5 -- migration `scripts/migrate_v2_23_attribute_leaves.py`, on a v2.22
   database holding a `vital_status` leaf (the form as v2.22 stored it):
   at v2.21 it refuses and changes nothing; with a leaf whose value is not
   a vital status it refuses and changes nothing; at v2.22 the leaf is an
   `attribute` leaf on `sys:vital_status`, its subject and value kept,
   `schema_meta` v2.23; a second run converts nothing.

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
MIGRATION_V2_23 = ROOT / "scripts" / "migrate_v2_23_attribute_leaves.py"

FAILURES: list[str] = []


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


def _count(db, model) -> int:
    from sqlmodel import func, select

    return db.exec(select(func.count()).select_from(model)).one()


def _refused(db, label: str, rule: str, call) -> None:
    from world_engine import models

    tables = (models.AttributeDefinition, models.AttributeDefinitionType, models.AttributeChoice,
              models.Condition, models.ConditionNode)
    before = tuple(_count(db, m) for m in tables)
    try:
        call()
    except ValueError:
        db.rollback()
        if tuple(_count(db, m) for m in tables) != before:
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


def _run_migration(path: pathlib.Path, db_path: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(path)], env=env, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


# --- AB1 -------------------------------------------------------------------------

def check_ab1() -> None:
    from world_engine import condition_forms, condition_interpreter, condition_text, day_resolve
    from world_engine.attributes import ATTRIBUTE_FORM
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    homes = {
        "REQUIREMENT_TYPES": condition_forms.REQUIREMENT_TYPES,
        "KEY_TARGET_TYPES": condition_forms.KEY_TARGET_TYPES,
        "ANY_SUBJECT_TYPES": condition_forms.ANY_SUBJECT_TYPES,
        "_EVALUATORS": tuple(condition_forms._EVALUATORS),
        "FORM_PHRASES_FR": tuple(condition_text.FORM_PHRASES_FR),
        "_BLOCKED_DETAIL_FR": tuple(day_resolve._BLOCKED_DETAIL_FR),
        "TARGET_HINTS_FR": tuple(condition_interpreter.TARGET_HINTS_FR),
    }
    for name, forms in homes.items():
        if ATTRIBUTE_FORM not in forms:
            fail(f"AB1: {name} lacks {ATTRIBUTE_FORM!r}")
        if "vital_status" in forms:
            fail(f"AB1: {name} still names the vital_status form")
    if "vital_status" in condition_forms.FORM_VALUES or "vital_status" in condition_text.VALUE_LABELS_FR:
        fail("AB1: FORM_VALUES or VALUE_LABELS_FR still names vital_status")
    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 23):
        fail(f"AB1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")


# --- AB fixture ----------------------------------------------------------------

def _ab_world(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Agenda, AgendaStep, Character, Entity, Faction, Item, Location, World
    from world_engine.writes.attributes import write_attribute_definition

    with Session(engine) as db:
        world = World(name="Attributs AB", is_active=False)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("pc", "character", "Millys"), ("npc", "character", "Ysa"),
                                ("guilde", "faction", "Guilde"), ("trone", "item", "Trône"),
                                ("crypte", "location", "Crypte")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "character":
                db.add(Character(id=entity.id, world_id=world.id,
                                 character_type="player" if key == "pc" else "npc"))
            else:
                db.add({"faction": Faction, "item": Item, "location": Location}[kind](id=entity.id))
        agenda = Agenda(world_id=world.id, owner_entity_id=ids["pc"], title="A", change_history=[])
        db.add(agenda)
        db.flush()
        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="active", change_history=[])
        db.add(step)
        db.flush()
        ids["step"] = step.id
        for key, spec in (
            ("maudit", _spec(name="Maudit", holder_types=("character", "faction"))),
            ("secret", _spec(name="Marqué", holder_types=("character",), choices=("non", "oui"), default="non",
                             is_hidden=True)),
            ("alerte", _spec(name="Alerte", kind="integer", holder_types=("location",), choices=(), default=0)),
            ("occupe", _spec(name="Occupé par", kind="entity", holder_types=("item",),
                             value_types=("character",), choices=(), default=None)),
            ("vieux", _spec(name="Vieux", holder_types=("character",))),
        ):
            ids[key] = write_attribute_definition(db, world_id=world.id, spec=spec).id
        db.commit()
    return ids


def _leaf(**kw):
    from world_engine.condition_forms import RequirementSpec

    base = {"type": "attribute", "subject_role": "doer"}
    base.update(kw)
    if base.get("subject_entity_id"):
        base["subject_role"] = None
    return RequirementSpec(**base)


def _choice(db, world, key, label):
    from world_engine.attributes import attribute_view

    return next(k for k, l in attribute_view(db, world, key).choices if l == label)


def _ab_tree(db, ids):
    from world_engine.conditions import all_of

    return all_of([
        _leaf(target_key=ids["maudit"], value=_choice(db, ids["world"], ids["maudit"], "oui")),
        _leaf(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3),
        _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["npc"]),
        _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"]),
        _leaf(subject_entity_id=ids["npc"], target_key="sys:vital_status", value="alive"),
    ])


def _condition_rows(db) -> tuple[int, int]:
    from world_engine.models import Condition, ConditionNode

    return _count(db, Condition), _count(db, ConditionNode)


def check_ab2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.conditions import all_of, read_condition
    from world_engine.quest_reads import editor_choices
    from world_engine.writes.attributes import ChoiceSpec, set_attribute_status, write_attribute_definition
    from world_engine.writes.conditions import write_condition

    with Session(engine) as db:
        world = ids["world"]
        tree = _ab_tree(db, ids)
        write_condition(db, world_id=world, role="completion", tree=tree, agenda_step_id=ids["step"])
        db.commit()
        if read_condition(db, role="completion", agenda_step_id=ids["step"]) != tree:
            fail("AB2: the attribute leaves do not read back equal")
        set_attribute_status(db, world_id=world, definition_id=ids["vieux"], status="retired")
        db.commit()

        def write(spec):
            return lambda: write_condition(db, world_id=world, role="prerequisite", tree=all_of([spec]),
                                           agenda_step_id=ids["step"])

        cases = {
            "an unknown attribute": _leaf(target_key="sys:humeur", value="x"),
            "a retired attribute": _leaf(target_key=ids["vieux"], value=_choice(db, world, ids["vieux"], "oui")),
            "a label of another attribute": _leaf(target_key=ids["secret"],
                                                  value=_choice(db, world, ids["maudit"], "oui")),
            "an integer leaf with no threshold": _leaf(subject_entity_id=ids["crypte"], target_key=ids["alerte"]),
            "an entity value of a type it does not name": _leaf(subject_entity_id=ids["trone"],
                                                                target_key=ids["occupe"],
                                                                target_entity_id=ids["guilde"]),
            "a fixed subject it does not apply to": _leaf(subject_entity_id=ids["crypte"], target_key=ids["maudit"],
                                                          value=_choice(db, world, ids["maudit"], "oui")),
        }
        for label, spec in cases.items():
            before = _condition_rows(db)
            try:
                write(spec)()
            except ValueError:
                db.rollback()
                if _condition_rows(db) != before:
                    fail(f"AB2: refusing {label} wrote rows")
                continue
            db.rollback()
            fail(f"AB2: write_condition accepts {label}")
        oui = _choice(db, world, ids["maudit"], "oui")
        non = _choice(db, world, ids["maudit"], "non")
        in_use = {
            "retiring a definition a leaf names": lambda: set_attribute_status(
                db, world_id=world, definition_id=ids["maudit"], status="retired"),
            "changing a named definition's kind": lambda: write_attribute_definition(
                db, world_id=world, definition_id=ids["maudit"], spec=_spec(
                    name="Maudit", kind="integer", holder_types=("character", "faction"), choices=(), default=0)),
            "dropping a label a leaf holds": lambda: write_attribute_definition(
                db, world_id=world, definition_id=ids["maudit"], spec=_spec(
                    name="Maudit", holder_types=("character", "faction"),
                    choices=(ChoiceSpec("non", id=non), ChoiceSpec("peut-être")), default="non")),
            "dropping the type of a leaf's fixed subject": lambda: write_attribute_definition(
                db, world_id=world, definition_id=ids["alerte"], spec=_spec(
                    name="Alerte", kind="integer", holder_types=("faction",), choices=(), default=0)),
        }
        del oui
        for label, call in in_use.items():
            _refused(db, label, "AB2", call)
        choices = editor_choices(world, db)
        keys = {a["key"]: a for a in choices.get("attributes", [])}
        if not {ids["maudit"], ids["alerte"], "sys:vital_status"} <= set(keys) \
                or keys[ids["alerte"]]["kind"] != "integer" or not keys[ids["maudit"]]["choices"]:
            fail(f"AB2: editor_choices lists attributes {sorted(keys)}")
        types = {e["id"]: e["type"] for e in choices.get("entities", [])}
        if types.get(ids["trone"]) != "item" or types.get(ids["crypte"]) != "location":
            fail(f"AB2: editor_choices lists entities {types}")


def check_ab3(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.conditions import Bindings, evaluate, leaf
    from world_engine.models import Character
    from world_engine.writes.attributes import write_attribute_value

    with Session(engine) as db:
        world = ids["world"]
        pc = db.get(Character, ids["pc"])
        oui, non = (_choice(db, world, ids["maudit"], label) for label in ("oui", "non"))

        def state(spec, **bind):
            return evaluate(leaf(spec), Bindings(doer=pc, **bind), db)

        if state(_leaf(target_key=ids["maudit"], value=non)).state != "met" \
                or state(_leaf(target_key=ids["maudit"], value=oui)).state != "unmet":
            fail("AB3: a choice leaf does not read the default before any value")
        write_attribute_value(db, world_id=world, definition_id=ids["maudit"], entity_id=ids["pc"], value=oui,
                              kind="changement", changed_by="creator_crud")
        db.commit()
        if state(_leaf(target_key=ids["maudit"], value=oui)).state != "met":
            fail("AB3: a choice leaf does not read the value")
        alert = _leaf(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3)
        if state(alert).state != "unmet":
            fail("AB3: an integer leaf is met below its threshold")
        write_attribute_value(db, world_id=world, definition_id=ids["alerte"], entity_id=ids["crypte"], value=3,
                              kind="changement", changed_by="creator_crud")
        db.commit()
        if state(alert).state != "met":
            fail("AB3: an integer leaf is not met at its threshold")
        named = _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["npc"])
        anyone = _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"])
        if state(named).state != "unmet" or state(anyone).state != "unmet":
            fail("AB3: an empty entity value meets a leaf")
        write_attribute_value(db, world_id=world, definition_id=ids["occupe"], entity_id=ids["trone"],
                              value=ids["npc"], kind="changement", changed_by="creator_crud")
        db.commit()
        if state(named).state != "met" or state(anyone).state != "met":
            fail("AB3: the entity named does not meet its leaves")
        for label, node in {
            "a subject the attribute does not apply to": state(_leaf(
                subject_entity_id=ids["crypte"], target_key=ids["maudit"], value=oui)),
            "sys:vital_status on a faction giver": state(_leaf(
                subject_role="giver", target_key="sys:vital_status", value="alive"), giver_id=ids["guilde"]),
        }.items():
            if node.state != "unknown" or node.verdict is not None or "n'a pas l'état" not in (node.reason or ""):
                fail(f"AB3: {label} is {node.state} ({node.reason!r})")


def check_ab4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.condition_text import HIDDEN_STATE_FR, verdict_lines
    from world_engine.conditions import Bindings, all_of, evaluate
    from world_engine.day_resolve import HIDDEN_STATE_DETAIL_FR, blocked_details_fr, player_detail_fr
    from world_engine.models import Character

    with Session(engine) as db:
        world = ids["world"]
        pc = db.get(Character, ids["pc"])
        oui = _choice(db, world, ids["secret"], "oui")
        hidden = evaluate(all_of([_leaf(target_key=ids["secret"], value=oui)]), Bindings(doer=pc), db)
        lines = verdict_lines(db, hidden, viewer_id=pc.id)
        texts = " ".join(line["text"] for line in lines)
        want = HIDDEN_STATE_FR.format(who="le personnage")
        if not lines or lines[-1]["mark"] != "?" or want[1:] not in texts or "Marqué" in texts:
            fail(f"AB4: the player reads the hidden leaf as {lines}")
        creator = " ".join(line["text"] for line in verdict_lines(db, hidden))
        if "Marqué" not in creator or "oui" not in creator:
            fail(f"AB4: the creator reads the hidden leaf as {creator!r}")
        if blocked_details_fr(hidden, db, pc.id) == [] or "Marqué" in " ".join(blocked_details_fr(hidden, db, pc.id)):
            fail(f"AB4: blocked_details_fr reads {blocked_details_fr(hidden, db, pc.id)}")
        verdict = hidden.leaf_verdicts()[0]
        if player_detail_fr(verdict, pc.id, db) != HIDDEN_STATE_DETAIL_FR:
            fail(f"AB4: player_detail_fr reads {player_detail_fr(verdict, pc.id, db)!r}")
        maudit_oui = _choice(db, world, ids["maudit"], "oui")
        visible = evaluate(all_of([_leaf(target_key=ids["maudit"], value=maudit_oui)]), Bindings(doer=pc), db)
        shown = verdict_lines(db, visible, viewer_id=pc.id)
        if shown[-1]["mark"] != "✓" or "Maudit" not in shown[-1]["text"]:
            fail(f"AB4: the player reads a visible leaf about himself as {shown}")
        _ab4_unholdable(db, world, pc)


def _ab4_unholdable(db, world: str, pc) -> None:
    """AMENDMENT-0113-01: a hidden attribute the subject cannot hold."""
    from world_engine.condition_text import verdict_lines
    from world_engine.conditions import HIDDEN_STATE_REASON_FR, Bindings, all_of, evaluate
    from world_engine.day_resolve import blocked_details_fr
    from world_engine.writes.attributes import write_attribute_definition

    haunted = write_attribute_definition(db, world_id=world, spec=_spec(
        name="Hanté", holder_types=("location",), choices=("non", "oui"), default="non", is_hidden=True)).id
    oui = _choice(db, world, haunted, "oui")
    tree = evaluate(all_of([_leaf(target_key=haunted, value=oui)]), Bindings(doer=pc), db)
    leaf = tree.children[0]
    if leaf.state != "unknown" or leaf.reason != HIDDEN_STATE_REASON_FR:
        fail(f"AB4: an unholdable hidden leaf is {leaf.state} because {leaf.reason!r}")
    said = " ".join(line["text"] for line in verdict_lines(db, tree, viewer_id=pc.id))
    said += " " + " ".join(blocked_details_fr(tree, db, pc.id))
    if "Hanté" in said or "oui" in said:
        fail(f"AB4: the player reads an unholdable hidden leaf as {said!r}")
    db.rollback()


# --- AB5 -------------------------------------------------------------------------

def _v222_db_with_leaf(value: str) -> str:
    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel

    from world_engine.models import Agenda, AgendaStep, Character, Condition, Entity, SchemaMeta, World

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "leaves.db")
    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as db:
        db.add(SchemaMeta(id=1, static_version="v2.22"))
        world = World(name="v2.22", is_active=False)
        db.add(world)
        db.flush()
        npc = Entity(world_id=world.id, type="character", name="Garde")
        db.add(npc)
        db.flush()
        db.add(Character(id=npc.id, world_id=world.id, character_type="npc"))
        agenda = Agenda(world_id=world.id, owner_entity_id=npc.id, title="A", change_history=[])
        db.add(agenda)
        db.flush()
        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", change_history=[])
        db.add(step)
        db.flush()
        condition = Condition(world_id=world.id, role="prerequisite", agenda_step_id=step.id)
        db.add(condition)
        db.commit()
        world_id, condition_id, npc_id = world.id, condition.id, npc.id
    eng.dispose()
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO condition_node (id, world_id, condition_id, position, op, form, subject_entity_id, "
                     "value) VALUES ('leaf-v222', ?, ?, 0, 'leaf', 'vital_status', ?, ?)",
                     (world_id, condition_id, npc_id, value))
    return db_path


def _leaf_row(db_path: str) -> tuple:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT form, target_key, subject_entity_id IS NOT NULL, value FROM condition_node "
                           "WHERE id = 'leaf-v222'").fetchone()
        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
    return row, version


def check_ab5() -> None:
    db_path = _v222_db_with_leaf("dead")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.21' WHERE id = 1")
    result = _run_migration(MIGRATION_V2_23, db_path)
    if result.returncode == 0 or _leaf_row(db_path)[0][0] != "vital_status":
        fail(f"AB5: v2.21 was not refused (exit {result.returncode})")
    bad = _v222_db_with_leaf("asleep")
    result = _run_migration(MIGRATION_V2_23, bad)
    if result.returncode == 0 or _leaf_row(bad) != (("vital_status", None, 1, "asleep"), "v2.22"):
        fail(f"AB5: a leaf that is no vital status was not refused: {_leaf_row(bad)}")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.22' WHERE id = 1")
    result = _run_migration(MIGRATION_V2_23, db_path)
    if result.returncode != 0 or _leaf_row(db_path) != (("attribute", "sys:vital_status", 1, "dead"), "v2.23"):
        fail(f"AB5: exit {result.returncode}, the leaf is {_leaf_row(db_path)}: {result.stderr.strip()[-200:]}")
    again = _run_migration(MIGRATION_V2_23, db_path)
    if again.returncode != 0 or "nothing to convert" not in again.stdout:
        fail(f"AB5: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")



def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ab = _ab_world(engine)
    for name, rule in (("AB1", check_ab1), ("AB2", lambda: check_ab2(engine, ab)),
                       ("AB3", lambda: check_ab3(engine, ab)), ("AB4", lambda: check_ab4(engine, ab)),
                       ("AB5", check_ab5)):
        try:
            rule()
        except Exception as exc:  # a crash is that rule's failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: attribute_conditions -- the attribute form reads a world's attribute or a system one on any "
          "entity it applies to, replaces vital_status (v2.23), keeps every attribute it names in use, and "
          "never shows a hidden one to a player")
    return 0


if __name__ == "__main__":
    sys.exit(main())
