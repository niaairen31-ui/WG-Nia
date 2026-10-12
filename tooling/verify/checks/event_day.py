"""G1 check for TICKET-0119 -- Journée proposes the event a completed step's objective names.

BRIEF-0119-F's rules (Bt1, M-c and V1 of the conditions series).

EJ1 -- the proposal (fixture). A step whose completion is « Chasse, Brakk
   as Chasseur, 3, a Proie filter on the sorte Loup, in the Forêt, since the
   step », resolved `success` with one wolf already counted since the step
   began, proposes one `event_creation` at `status='proposed'`,
   `source_type='pass_play'`: its type, Brakk in the role Chasseur, the
   sorte in Proie, the quantity still lacking (2), the Forêt, the step's
   objective and the day's number as its title, and the type's effect pre-filled in
   `state_changes`.
EJ2 -- nothing invented (fixture). Nothing is proposed for: a `failure` or
   `blocked` band; a leaf already met; a leaf under `any`; a leaf on the
   giver rather than the one who acts; a step with no completion. (A
   condition never names a retired type: retiring one is refused while a
   condition names it, `event_journal.py` EA3.) A leaf saying « any role » takes the type's first role
   accepting a character.
EJ3 -- wiring (static). `day_mutations._EMITTERS["event_creation"]` is
   `emit_objective_events`; `day_events.py` constructs `ProposedMutation`
   with `status="proposed"` only and calls no writer (`writes` is not
   imported).

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


def _fixture(engine) -> dict:
    from datetime import UTC, datetime, timedelta

    from sqlmodel import Session

    from world_engine.event_vocab import type_view
    from world_engine.models import Batch, Character, Entity, Location, PassPlay, Session as PlaySession, World
    from world_engine.writes.attributes import DefinitionSpec, write_attribute_definition
    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, write_event_type, write_sorte

    with Session(engine) as db:
        world = World(name="Journée", is_active=True)
        db.add(world)
        db.flush()
        ids = {"world": world.id}
        for key, kind, name in (("brakk", "character", "Brakk"), ("odo", "character", "Odo"),
                                ("foret", "location", "Forêt")):
            row = Entity(world_id=world.id, type=kind, name=name)
            db.add(row)
            db.flush()
            ids[key] = row.id
            db.add(Character(id=row.id, world_id=world.id, character_type="player" if key == "brakk" else "npc")
                   if kind == "character" else Location(id=row.id))
        fatigue = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
            name="Fatigue", kind="integer", holder_types=("character",), default=0))
        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
            name="Chasse", counts_quantity=True,
            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True)),
            effects=(EffectSpec("Chasseur", fatigue.id, 1, "add"),)))
        ids.update(chasse=chasse.id, fatigue=fatigue.id,
                   loup=write_sorte(db, world_id=world.id, name="Loup").id)
        for role in type_view(db, chasse.id).roles:
            ids[role.name] = role.id
        play = PlaySession(world_id=world.id, number=1)
        db.add(play)
        db.flush()
        batch = Batch(session_id=play.id, day_number=4)
        db.add(batch)
        db.flush()
        pass_play = PassPlay(batch_id=batch.id, session_id=play.id, character_id=ids["brakk"], declared_action="a")
        db.add(pass_play)
        db.flush()
        ids["pass_play"], ids["session"] = pass_play.id, play.id
        ids["started"] = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
    return ids


def _step(db, ids: dict, tree_dict) -> str:
    from world_engine.conditions import node_from_dict
    from world_engine.models import Agenda, AgendaStep
    from world_engine.writes.conditions import write_condition

    agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["brakk"], title="t", status="active")
    db.add(agenda)
    db.flush()
    step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="Chasser trois loups", status="active",
                      started_at=ids["started"])
    db.add(step)
    db.flush()
    if tree_dict is not None:
        write_condition(db, world_id=ids["world"], role="completion", tree=node_from_dict(tree_dict),
                        agenda_step_id=step.id)
    db.commit()
    return step.id


def _leaf(ids: dict, **fields) -> dict:
    leaf = {"op": "leaf", "type": "event", "subject_role": "doer", "target_key": ids["chasse"],
            "value": ids["Chasseur"], "threshold": 3, "target_entity_id": ids["foret"], "since": "step",
            "filters": [{"role_id": ids["Proie"], "sorte_id": ids["loup"]}]}
    leaf.update(fields)
    return leaf


def _emit(db, ids: dict, step_id: str, band: str = "success") -> list:
    from world_engine.day_events import emit_objective_events
    from world_engine.day_resolve import StepOutcome
    from world_engine.models import Character, PassPlay

    outcome = StepOutcome(agenda_step_id=step_id, step_order=1, objective="Chasser trois loups", domain=None,
                          verdict=None, band=band, requirement_verdicts=(), canon_ids=())
    return emit_objective_events(outcome, db.get(PassPlay, ids["pass_play"]), db.get(Character, ids["brakk"]),
                                 ids["world"], db)


def check_ej1(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.writes.events import EventSpec, ParticipantSpec, write_event

    with Session(engine) as db:
        step_id = _step(db, ids, _leaf(ids))
        write_event(db, world_id=ids["world"], created_by="check", spec=EventSpec(
            type_id=ids["chasse"], title="Un loup", quantity=1, location_id=ids["foret"], participants=(
                ParticipantSpec(ids["Chasseur"], entity_id=ids["brakk"]),
                ParticipantSpec(ids["Proie"], sorte_id=ids["loup"]))))
        db.commit()
        rows = _emit(db, ids, step_id)
        payload = rows[0].payload if len(rows) == 1 else {}
        got = (len(rows), rows[0].status if rows else None, rows[0].source_type if rows else None,
               payload.get("type_id"), [(p["role_id"], p["entity_id"], p["sorte_id"]) for p in
                                        payload.get("participants", [])],
               payload.get("quantity"), payload.get("location_id"), payload.get("title"),
               payload.get("state_changes"))
        want = (1, "proposed", "pass_play", ids["chasse"],
                [(ids["Chasseur"], ids["brakk"], None), (ids["Proie"], None, ids["loup"])], 2, ids["foret"],
                "Chasser trois loups — jour 4",
                [{"entity_id": ids["brakk"], "attribute": ids["fatigue"], "mode": "add", "value": 1}])
        if got != want:
            fail(f"EJ1: the proposal is {got}")


def check_ej2(engine, ids: dict) -> None:
    from sqlmodel import Session

    with Session(engine) as db:
        cases = {
            "a failure": (_leaf(ids), "failure"),
            "a blocked step": (_leaf(ids), "blocked"),
            "a leaf already met": (_leaf(ids, threshold=1, since="always"), "success"),
            "a leaf under any": ({"op": "any", "children": [_leaf(ids), _leaf(ids, threshold=9)]}, "success"),
            "a leaf on the giver": (_leaf(ids, subject_role="giver"), "success"),
            "no completion": (None, "success"),
        }
        for label, (tree, band) in cases.items():
            step_id = _step(db, ids, tree)
            rows = _emit(db, ids, step_id, band)
            if rows:
                fail(f"EJ2: {label} proposed {[r.payload for r in rows]}")
        step_id = _step(db, ids, _leaf(ids, value=None, filters=[], target_entity_id=None, since="always",
                                       threshold=9))
        rows = _emit(db, ids, step_id)
        roles = [p["role_id"] for p in rows[0].payload["participants"]] if len(rows) == 1 else None
        if roles != [ids["Chasseur"]]:
            fail(f"EJ2: an « any role » leaf gave roles {roles}")


def check_ej3() -> None:
    tree = ast.parse((SRC / "day_mutations.py").read_text(encoding="utf-8"))
    emitters = next((n.value for n in ast.walk(tree) if isinstance(n, ast.AnnAssign)
                     and isinstance(n.target, ast.Name) and n.target.id == "_EMITTERS"), None)
    found = None
    if isinstance(emitters, ast.Dict):
        for key, value in zip(emitters.keys, emitters.values):
            if isinstance(key, ast.Constant) and key.value == "event_creation" and isinstance(value, ast.Name):
                found = value.id
    if found != "emit_objective_events":
        fail(f"EJ3: _EMITTERS['event_creation'] is {found}")
    events = ast.parse((SRC / "day_events.py").read_text(encoding="utf-8"))
    built = 0
    for node in ast.walk(events):
        if isinstance(node, ast.ImportFrom) and node.module and "writes" in node.module:
            fail(f"EJ3: day_events.py imports {node.module}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ProposedMutation":
            built += 1
            status = next((k.value for k in node.keywords if k.arg == "status"), None)
            if not (isinstance(status, ast.Constant) and status.value == "proposed"):
                fail("EJ3: day_events.py builds a ProposedMutation not at status 'proposed'")
    if built == 0:
        fail("EJ3: day_events.py builds no ProposedMutation")


def main() -> int:
    _fresh_db()
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    ids = _fixture(engine)
    for name, rule in (("EJ1", lambda: check_ej1(engine, ids)), ("EJ2", lambda: check_ej2(engine, ids)),
                       ("EJ3", check_ej3)):
        try:
            rule()
        except Exception as exc:  # a crash is a failure, never a pass
            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: event_day -- a completed step whose objective is an event proposes that event, as its leaf says "
          "it: its type, the one who acts in his role, its filters, its place, what is still lacking, its changes "
          "pre-filled; nothing else is invented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
