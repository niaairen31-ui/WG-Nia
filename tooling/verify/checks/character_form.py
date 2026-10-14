"""G1 check for TICKET-0121 -- `is_character`, the form of a quest kept for one character.

BRIEF-0121-A's rules (E3a): the eligibility of an offer reaches one
character through the same language as every other condition, so a quest
for one character is a leaf, not a column.

CF1 -- vocabulary (import). `is_character` is the last member of
   `REQUIREMENT_TYPES` and of `ENTITY_TARGET_TYPES`; it is not a model form,
   not an any-subject form, and not a key, threshold or value form; it is a
   key of `_EVALUATORS`, `FORM_PHRASES_FR`, `_BLOCKED_DETAIL_FR`,
   `TARGET_HINTS_FR`, and `_TARGET_ENTITY_TYPE` (a `character`).
CF2 -- judging (fixture). A tree `all(is_character doer -> P)` is met for P
   and not met for Q; `describe` names the target.
CF3 -- cleaning (fixture). `clean_leaf` refuses the leaf with the role
   `giver`, with a fixed subject, and with a location as target; it accepts
   doer -> P.
CF4 -- storage (fixture). An eligibility `all(is_character doer -> P)`
   written on an offer reads back as the same tree.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


def check_cf1() -> None:
    from world_engine import condition_forms, condition_interpreter, condition_text, day_resolve
    from world_engine.writes import conditions as write_conditions

    form = "is_character"
    forms = condition_forms
    if forms.REQUIREMENT_TYPES[-1] != form or forms.REQUIREMENT_TYPES.count(form) != 1:
        fail(f"CF1: REQUIREMENT_TYPES ends {forms.REQUIREMENT_TYPES[-1]!r}")
    if forms.ENTITY_TARGET_TYPES[-1] != form or forms.ENTITY_TARGET_TYPES.count(form) != 1:
        fail(f"CF1: ENTITY_TARGET_TYPES ends {forms.ENTITY_TARGET_TYPES[-1]!r}")
    for name in ("MODEL_REQUIREMENT_TYPES", "ANY_SUBJECT_TYPES", "KEY_TARGET_TYPES", "THRESHOLD_TYPES"):
        if form in getattr(forms, name):
            fail(f"CF1: {form} is in {name}")
    if form in forms.FORM_VALUES:
        fail("CF1: is_character is in FORM_VALUES")
    for label, table in (("_EVALUATORS", forms._EVALUATORS),
                         ("FORM_PHRASES_FR", condition_text.FORM_PHRASES_FR),
                         ("_BLOCKED_DETAIL_FR", day_resolve._BLOCKED_DETAIL_FR),
                         ("TARGET_HINTS_FR", condition_interpreter.TARGET_HINTS_FR)):
        if form not in table:
            fail(f"CF1: {form} is not a key of {label}")
    if write_conditions._TARGET_ENTITY_TYPE.get(form) != ("character",):
        fail(f"CF1: _TARGET_ENTITY_TYPE[{form!r}] is {write_conditions._TARGET_ENTITY_TYPE.get(form)!r}")


def _world(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import Character, Entity, Location, World

    with Session(engine) as db:
        world = World(name="Quête unique CF", is_active=False)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("p", "character", "Millys"), ("q", "character", "Ysa"),
                                ("place", "location", "Crypte")):
            entity = Entity(world_id=world.id, type=kind, name=name)
            db.add(entity)
            db.flush()
            ids[key] = entity.id
            if kind == "character":
                db.add(Character(id=entity.id, world_id=world.id,
                                 character_type="player" if key == "p" else "npc"))
            else:
                db.add(Location(id=entity.id))
        db.commit()
    return ids


def _leaf(target: str, role: str | None = "doer", subject_entity_id: str | None = None):
    from world_engine.condition_forms import RequirementSpec

    return RequirementSpec(type="is_character", subject_role=None if subject_entity_id else role,
                           subject_entity_id=subject_entity_id, target_entity_id=target)


def check_cf2(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.condition_text import describe
    from world_engine.conditions import Bindings, all_of, evaluate
    from world_engine.models import Character

    with Session(engine) as db:
        tree = all_of([_leaf(ids["p"])])
        p, q = db.get(Character, ids["p"]), db.get(Character, ids["q"])
        for who, character, want in (("P", p, True), ("Q", q, False)):
            verdict = evaluate(tree, Bindings(doer=character), db)
            if verdict is None or bool(verdict.met) is not want:
                fail(f"CF2: {who} judged {getattr(verdict, 'met', None)!r}, wanted {want}")
        lines = describe(db, tree)
        if not any(" est " in line["text"] and "Millys" in line["text"] for line in lines):
            fail(f"CF2: describe gives {lines!r}")


def check_cf3(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.writes.conditions import clean_leaf

    with Session(engine) as db:
        world = ids["world"]
        cases = {
            "the role giver": _leaf(ids["p"], role="giver"),
            "a fixed subject": _leaf(ids["p"], subject_entity_id=ids["q"]),
            "a location target": _leaf(ids["place"]),
        }
        for label, spec in cases.items():
            try:
                clean_leaf(db, world, spec)
            except ValueError:
                continue
            fail(f"CF3: {label} was accepted")
        try:
            clean_leaf(db, world, _leaf(ids["p"]))
        except ValueError as exc:
            fail(f"CF3: doer -> P was refused: {exc}")


def check_cf4(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.conditions import all_of, read_condition
    from world_engine.models import QuestOffer
    from world_engine.writes.conditions import write_condition

    with Session(engine) as db:
        offer = QuestOffer(world_id=ids["world"], giver_entity_id=ids["q"], title="Pour Millys", change_history=[])
        db.add(offer)
        db.flush()
        tree = all_of([_leaf(ids["p"])])
        write_condition(db, world_id=ids["world"], role="eligibility", quest_offer_id=offer.id, tree=tree)
        db.commit()
        back = read_condition(db, role="eligibility", quest_offer_id=offer.id)
        if back != tree:
            fail(f"CF4: the leaf reads back as {back!r}")


def main() -> None:
    _fresh_db()
    from sqlmodel import SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    check_cf1()
    ids = _world(engine)
    check_cf2(engine, ids)
    check_cf3(engine, ids)
    check_cf4(engine, ids)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: character_form -- is_character is one leaf of the one language, judged on the doer, "
          "stored and read back like any other")


if __name__ == "__main__":
    main()
