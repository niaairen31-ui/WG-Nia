"""G1 check for TICKET-0126 (BRIEF-0126-C) -- one function judges a character-creation sheet, over rules the creator reads and writes.

CB1 -- the cases of LOT-0126 (b)-1. One active world (`create_world`):
   systems `Martial` (`cap_raised_at_creation = 1`) and `Magie`
   (`visible_at_creation = False`, `cap_held_at_creation = 1`) through
   `create_skill_system`; definitions `Escrime`, `Lutte` (Martial),
   `Pistage` (no system, `max_rank_at_creation = 2`), `Sorts` (Magie),
   `Nécromancie` (Magie, requires a master, visible), `Alchimie` (no system,
   requires a master) through `create_skill_definition`; the rules of rows
   16-17 through `write_creation_rules`. For each of the 17 rows,
   `check_creation`'s `spent`, `remaining` and violation codes, in order,
   equal the table; rows 4, 5, 9 and 12 also compare the full French
   message. A supplementary row (rules `cost_to_rank_1 = 2`, `physical` 0)
   pins the refund to the Initié cost, which the table's default costs
   (Initié = Apprenti = 1) cannot tell apart.
CB2 -- the cascades of (b)-2. `skill_visible` and `skill_max_rank` on
   `SimpleNamespace` owners: a definition's value wins over its system's,
   a system's over the world's, the world's when neither sets it; a base
   domain is always visible and reads the world's maximum. `start_sheet`
   on CB1's world: the four base domains, then `Nécromancie, Sorts`
   (Magie), `Escrime, Lutte` (Martial), `Alchimie, Pistage` (no system);
   `Nécromancie` and `Alchimie` start at 0, every other line at 1.
CB3 -- the writer. Each refusal of C-05 (a bool never an int) raises its
   French message and writes no row; a world without a row reads every
   default; a valid call, then a second, leave one row, which
   `world_creation_rules` reads back, a None cap as no cap.
CB4 -- the routes, called directly on a fresh active world. `GET
   /api/creation-rules` equals the defaults' `rules_dict`; a PUT listing
   rank 3 twice is a 422 `Chaque rang est donné une fois.`; a PUT with
   `pool: -1` is a 422 with C-05's message and writes nothing; a valid PUT
   changes the rules and the GET returns them; a system created with
   `cap_held_at_creation: 1, visible_at_creation: false` reads them back; a
   definition updated with `max_rank_at_creation: 2`, then with it omitted,
   reads 2 then null.
CB5 -- static (INV-67). Under `src/`, the token `cost_to_rank_` occurs only
   in `models/canon_skill.py`, `creation_rules.py` and
   `writes/creation_rules.py`; `creation_rules.py` and `creation_check.py`
   contain none of `db.add(`, `.commit(`, `.flush(`, `chat(`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB; rows through the sanctioned writers
and the CRUD route functions. A rule that collected nothing is a FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PACKAGE = SRC / "world_engine"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


DEFAULT_COSTS = [1, 1, 2, 3, 4]
NO_CAPS = {0: 2, 2: None, 3: None, 4: None, 5: None}
DEFAULT_RULES_DICT = {
    "pool": 6,
    "costs": [{"rank": 1, "cost": 1}, {"rank": 2, "cost": 1}, {"rank": 3, "cost": 2},
              {"rank": 4, "cost": 3}, {"rank": 5, "cost": 4}],
    "caps": [{"rank": 0, "cap": 2}, {"rank": 2, "cap": None}, {"rank": 3, "cap": None},
             {"rank": 4, "cap": None}, {"rank": 5, "cap": None}],
    "max_rank": 5, "max_master_skills": 1, "skills_visible": True,
}
MESSAGES = {
    4: ["Réserve dépassée : 10 point(s) pour 6."],
    5: ["« Pistage » : au plus Apprenti à la création."],
    9: ["Au plus 1 compétence(s) qui exigent un maître.",
        "Système « Magie » : au plus 1 compétence(s) détenue(s)."],
    12: ["Système « Martial » : au plus 1 compétence(s) au-dessus de Initié."],
}


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
    return engine


def _new_world(engine, name: str) -> str:
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import WorldCreateBody, create_world

    with Session(engine) as db:
        created = create_world(WorldCreateBody(name=name, description="d", fundamental_laws="l"), db)
    return created["world_id"]


def _write_rules(engine, world_id: str, **overrides) -> None:
    from sqlmodel import Session

    from world_engine.writes.creation_rules import write_creation_rules

    fields = dict(pool=6, costs=list(DEFAULT_COSTS), caps=dict(NO_CAPS), max_rank=5,
                  max_master_skills=1, skills_visible=True)
    fields.update(overrides)
    with Session(engine) as db:
        write_creation_rules(db, world_id=world_id, **fields)
        db.commit()


def _cb1_world(engine) -> tuple[str, dict[str, str]]:
    from sqlmodel import Session

    from world_engine.cockpit.crud.skills import (
        SkillDefinitionWriteBody, SkillSystemWriteBody, create_skill_definition, create_skill_system,
    )

    world_id = _new_world(engine, "Budget")
    ids: dict[str, str] = {}
    with Session(engine) as db:
        martial = create_skill_system(SkillSystemWriteBody(name="Martial", cap_raised_at_creation=1), db)
        magie = create_skill_system(SkillSystemWriteBody(
            name="Magie", visible_at_creation=False, cap_held_at_creation=1), db)
        for name, system, extra in (
            ("Escrime", martial, {}), ("Lutte", martial, {}),
            ("Pistage", None, {"max_rank_at_creation": 2}), ("Sorts", magie, {}),
            ("Nécromancie", magie, {"requires_master": True, "visible_at_creation": True}),
            ("Alchimie", None, {"requires_master": True}),
        ):
            created = create_skill_definition(SkillDefinitionWriteBody(
                name=name, base_domain="physical", system_id=system["id"] if system else None, **extra), db)
            ids[name] = created["id"]
    return world_id, ids


def rule_cb1(engine, world_id: str, ids: dict[str, str]) -> int:
    from sqlmodel import Session

    from world_engine.creation_check import check_creation

    def key(name: str) -> str:
        return ids.get(name, name)

    # (row, choices, enforce, spent, codes); rules of rows 16-17 set before them.
    rows = [
        (1, {}, True, 0, []),
        (2, {"Escrime": 2}, True, 1, []),
        (3, {"Escrime": 4}, True, 6, []),
        (4, {"Escrime": 5}, True, 10, ["over_pool"]),
        (5, {"Pistage": 3}, True, 3, ["above_max_rank"]),
        (6, {"physical": 0}, True, -1, []),
        (7, {"physical": 0, "agility": 0, "perception": 0}, True, -3, ["over_rank_cap"]),
        (8, {"Nécromancie": 1}, True, 1, ["over_system_held"]),
        (9, {"Nécromancie": 1, "Alchimie": 1}, True, 2, ["over_master_count", "over_system_held"]),
        (10, {"Sorts": 2}, True, 1, ["not_visible"]),
        (11, {"Sorts": 2}, False, 1, []),
        (12, {"Escrime": 2, "Lutte": 2}, True, 2, ["over_system_raised"]),
        (13, {"nope": 2}, True, 0, ["unknown_skill"]),
        (14, {"Escrime": 7}, True, 0, ["rank_out_of_range"]),
        (15, {"Escrime": True}, True, 0, ["rank_out_of_range"]),
        (16, {"Escrime": 2, "Pistage": 2}, True, 2, ["over_rank_cap"]),
        (17, {"physical": 0, "Escrime": 2}, True, 0, []),
        ("17b", {"physical": 0}, True, -2, []),
    ]
    rules_before = {16: {"caps": {**NO_CAPS, 2: 1}}, 17: {"pool": 0},
                    "17b": {"costs": [2, 1, 2, 3, 4]}}
    counted = 0
    for number, choices, enforce, spent, codes in rows:
        if number in rules_before:
            _write_rules(engine, world_id, **rules_before[number])
        with Session(engine) as db:
            verdict = check_creation(db, world_id, {key(k): v for k, v in choices.items()},
                                     enforce_visibility=enforce)
        got_codes = [v.code for v in verdict.violations]
        if verdict.spent != spent or got_codes != codes:
            fail(f"CB1 row {number}: spent {verdict.spent}, codes {got_codes}; expected {spent}, {codes}")
        if verdict.remaining != verdict.pool - verdict.spent:
            fail(f"CB1 row {number}: remaining {verdict.remaining} is not pool - spent")
        if number == 6 and verdict.remaining != 7:
            fail(f"CB1 row 6: remaining {verdict.remaining}, expected 7")
        if number in MESSAGES and [v.message for v in verdict.violations] != MESSAGES[number]:
            fail(f"CB1 row {number}: messages {[v.message for v in verdict.violations]!r}, "
                 f"expected {MESSAGES[number]!r}")
        counted += 1
    return counted


def rule_cb2(engine, world_id: str) -> int:
    from sqlmodel import Session

    from world_engine.creation_rules import (
        CreationRuleSet, skill_max_rank, skill_visible, start_sheet, world_creation_rules,
    )

    def owner(visible=None, max_rank=None):
        return SimpleNamespace(visible_at_creation=visible, max_rank_at_creation=max_rank)

    caps = tuple((r, NO_CAPS[r]) for r in (0, 2, 3, 4, 5))
    rules = CreationRuleSet(pool=6, costs=(0, 1, 1, 2, 3, 4), caps=caps, max_rank=4,
                            max_master_skills=1, skills_visible=False)
    cases = [
        ("definition wins", skill_visible(rules, system=owner(True), definition=owner(False)), False),
        ("definition wins", skill_max_rank(rules, system=owner(max_rank=3), definition=owner(max_rank=2)), 2),
        ("system next", skill_visible(rules, system=owner(True), definition=owner()), True),
        ("system next", skill_max_rank(rules, system=owner(max_rank=3), definition=owner()), 3),
        ("world last", skill_visible(rules, system=owner(), definition=owner()), False),
        ("world last", skill_max_rank(rules, system=None, definition=owner()), 4),
        ("base domain", skill_visible(rules, system=None, definition=None), True),
        ("base domain", skill_max_rank(rules, system=owner(max_rank=2), definition=None), 4),
    ]
    for label, got, expected in cases:
        if got != expected:
            fail(f"CB2 cascade {label}: {got!r}, expected {expected!r}")
    with Session(engine) as db:
        sheet = start_sheet(db, world_id, world_creation_rules(db, world_id))
    names = [line.name for line in sheet]
    expected_names = ["physical", "agility", "perception", "composure", "Nécromancie", "Sorts",
                      "Escrime", "Lutte", "Alchimie", "Pistage"]
    if names != expected_names:
        fail(f"CB2 start_sheet order {names}, expected {expected_names}")
    starts = {line.name: line.start_rank for line in sheet}
    expected_starts = {name: 0 if name in ("Nécromancie", "Alchimie") else 1 for name in expected_names}
    if starts != expected_starts:
        fail(f"CB2 start ranks {starts}, expected {expected_starts}")
    return len(cases) + len(sheet)


def _rows_for(engine, world_id: str) -> int:
    from sqlalchemy import text

    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM creation_rules WHERE world_id = :w"),
                            {"w": world_id}).scalar_one()


def rule_cb3(engine) -> int:
    from sqlmodel import Session

    from world_engine.creation_rules import rules_dict, world_creation_rules
    from world_engine.writes.creation_rules import write_creation_rules

    world_id = _new_world(engine, "Writer")
    with Session(engine) as db:
        if rules_dict(world_creation_rules(db, world_id)) != DEFAULT_RULES_DICT:
            fail("CB3 a world without a row does not read every default")
    pool_msg = "La réserve est un nombre entier, au moins 0."
    cost_msg = "Chaque coût est un nombre entier, au moins 0."
    cap_msg = "Chaque plafond est vide ou un nombre entier, au moins 0."
    rank_msg = "Le rang maximal va d'Initié à Maître."
    master_msg = "Le nombre de compétences à maître est un nombre entier, au moins 0."
    visible_msg = "La visibilité est oui ou non."
    refusals = [
        ({"pool": -1}, pool_msg), ({"pool": True}, pool_msg),
        ({"costs": [1, 1, 2, 3]}, cost_msg), ({"costs": [1, 1, -2, 3, 4]}, cost_msg),
        ({"costs": [1, True, 2, 3, 4]}, cost_msg),
        ({"caps": {0: 2, 2: None, 3: None, 4: None}}, cap_msg), ({"caps": {**NO_CAPS, 3: -1}}, cap_msg),
        ({"max_rank": 0}, rank_msg), ({"max_rank": 6}, rank_msg), ({"max_rank": True}, rank_msg),
        ({"max_master_skills": -1}, master_msg), ({"skills_visible": 1}, visible_msg),
    ]
    counted = 0
    for overrides, message in refusals:
        fields = dict(pool=6, costs=list(DEFAULT_COSTS), caps=dict(NO_CAPS), max_rank=5,
                      max_master_skills=1, skills_visible=True)
        fields.update(overrides)
        with Session(engine) as db:
            try:
                write_creation_rules(db, world_id=world_id, **fields)
                fail(f"CB3 {overrides} was accepted")
            except ValueError as exc:
                if str(exc) != message:
                    fail(f"CB3 {overrides}: message {str(exc)!r}, expected {message!r}")
            db.rollback()
        if _rows_for(engine, world_id) != 0:
            fail(f"CB3 {overrides} wrote a row")
        counted += 1
    _write_rules(engine, world_id, pool=9)
    _write_rules(engine, world_id, pool=4, costs=[2, 2, 3, 4, 5], caps={0: None, 2: 1, 3: None, 4: None, 5: 0},
                 max_rank=3, max_master_skills=0, skills_visible=False)
    if _rows_for(engine, world_id) != 1:
        fail(f"CB3 two writes left {_rows_for(engine, world_id)} rows, expected 1")
    with Session(engine) as db:
        rules = world_creation_rules(db, world_id)
    got = (rules.pool, rules.costs, rules.caps, rules.max_rank, rules.max_master_skills, rules.skills_visible)
    expected = (4, (0, 2, 2, 3, 4, 5), ((0, None), (2, 1), (3, None), (4, None), (5, 0)), 3, 0, False)
    if got != expected:
        fail(f"CB3 the second write reads back {got}, expected {expected}")
    return counted + 1


def _status(call) -> tuple[int, str]:
    from fastapi import HTTPException

    try:
        call()
    except HTTPException as exc:
        return exc.status_code, str(exc.detail)
    return 200, ""


def rule_cb4(engine) -> int:
    from sqlmodel import Session

    from world_engine.cockpit.crud.skills import (
        CreationRulesBody, SkillDefinitionWriteBody, SkillSystemWriteBody, create_skill_definition,
        create_skill_system, get_creation_rules, update_creation_rules, update_skill_definition,
    )

    world_id = _new_world(engine, "Routes")
    counted = 0
    with Session(engine) as db:
        if get_creation_rules(db) != DEFAULT_RULES_DICT:
            fail(f"CB4 GET on a fresh world is {get_creation_rules(db)!r}, expected the defaults")
    counted += 1

    def body(**overrides) -> CreationRulesBody:
        fields = dict(pool=7, costs=[{"rank": r, "cost": r} for r in range(1, 6)],
                      caps=[{"rank": r, "cap": None} for r in (0, 2, 3, 4, 5)],
                      max_rank=4, max_master_skills=2, skills_visible=False)
        fields.update(overrides)
        return CreationRulesBody(**fields)

    twice = [{"rank": r, "cost": 1} for r in (1, 2, 3, 3, 5)]
    with Session(engine) as db:
        got = _status(lambda: update_creation_rules(body(costs=twice), db))
    if got != (422, "Chaque rang est donné une fois."):
        fail(f"CB4 a PUT listing rank 3 twice answered {got}")
    with Session(engine) as db:
        got = _status(lambda: update_creation_rules(body(pool=-1), db))
    if got != (422, "La réserve est un nombre entier, au moins 0."):
        fail(f"CB4 a PUT with pool -1 answered {got}")
    if _rows_for(engine, world_id) != 0:
        fail("CB4 a refused PUT wrote a row")
    counted += 2
    with Session(engine) as db:
        put = update_creation_rules(body(), db)
    with Session(engine) as db:
        back = get_creation_rules(db)
    expected = {"pool": 7, "costs": [{"rank": r, "cost": r} for r in range(1, 6)],
                "caps": [{"rank": r, "cap": None} for r in (0, 2, 3, 4, 5)],
                "max_rank": 4, "max_master_skills": 2, "skills_visible": False}
    if put != expected or back != expected:
        fail(f"CB4 the PUT answered {put!r} and the GET {back!r}, expected {expected!r}")
    counted += 1
    with Session(engine) as db:
        system = create_skill_system(SkillSystemWriteBody(
            name="Rituel", cap_held_at_creation=1, visible_at_creation=False), db)
    if (system.get("cap_held_at_creation"), system.get("visible_at_creation")) != (1, False):
        fail(f"CB4 the created system reads {system!r}")
    counted += 1
    with Session(engine) as db:
        created = create_skill_definition(SkillDefinitionWriteBody(name="Chant", base_domain="composure"), db)
        first = update_skill_definition(created["id"], SkillDefinitionWriteBody(
            name="Chant", base_domain="composure", max_rank_at_creation=2), db)
        second = update_skill_definition(created["id"], SkillDefinitionWriteBody(
            name="Chant", base_domain="composure"), db)
    if (first.get("max_rank_at_creation"), second.get("max_rank_at_creation")) != (2, None):
        fail(f"CB4 the definition's max_rank_at_creation reads {first.get('max_rank_at_creation')!r} "
             f"then {second.get('max_rank_at_creation')!r}, expected 2 then None")
    counted += 1
    return counted


def rule_cb5() -> int:
    allowed = {"models/canon_skill.py", "creation_rules.py", "writes/creation_rules.py"}
    files = sorted(PACKAGE.rglob("*.py"))
    if not files:
        fail("CB5 no source file collected")
        return 0
    holders = {p.relative_to(PACKAGE).as_posix() for p in files
               if "cost_to_rank_" in p.read_text(encoding="utf-8")}
    for extra in sorted(holders - allowed):
        fail(f"CB5 {extra} names cost_to_rank_ (only {sorted(allowed)} may)")
    if not holders:
        fail("CB5 no module names cost_to_rank_")
    counted = len(holders)
    for name in ("creation_rules.py", "creation_check.py"):
        path = PACKAGE / name
        if not path.is_file():
            fail(f"CB5 {name} is missing")
            continue
        source = path.read_text(encoding="utf-8")
        for token in ("db.add(", ".commit(", ".flush(", "chat("):
            if token in source:
                fail(f"CB5 {name} holds {token!r}: it reads only")
        counted += 1
    return counted


def main() -> int:
    engine = _fresh_engine()
    totals: dict[str, int] = {}
    world_id, ids = None, {}
    try:
        world_id, ids = _cb1_world(engine)
        totals["CB1"] = rule_cb1(engine, world_id, ids)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"CB1 raised {type(exc).__name__}: {exc}")
    for name, run in (
        ("CB2", lambda: rule_cb2(engine, world_id)),
        ("CB3", lambda: rule_cb3(engine)),
        ("CB4", lambda: rule_cb4(engine)),
        ("CB5", rule_cb5),
    ):
        try:
            totals[name] = run()
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{name} raised {type(exc).__name__}: {exc}")
    for name in ("CB1", "CB2", "CB3", "CB4", "CB5"):
        if not totals.get(name):
            fail(f"{name} collected nothing")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(f"PASS: creation_budget -- {totals['CB1']} sheet cases judged by check_creation, the cascades "
          f"and the start sheet, the writer's {totals['CB3'] - 1} refusals, the creator's routes and "
          f"overrides, the cost columns confined (INV-67)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
