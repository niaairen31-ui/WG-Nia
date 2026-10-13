"""G1 check for TICKET-0115 -- the dashboard is a registry in code: its metrics read relational columns only, its deferrals point at the passage that declares them, and its export carries what the tab does not show.

BRIEF-0115-D's rules (H1, E2, F2, I1, J1, K2, L and M1 of the conditions
series' dashboard).

DB1 -- the deferral registry (static). `DEFERRALS` is not empty; each
   entry's `source` exists and holds its `anchor` exactly once (whitespace
   folded); its `status` is one of `DEFERRAL_STATUSES`, `follow_up` only
   when `reached`; its `metric` is None, `EXPORT` or a `METRICS` key; no
   `(code, ticket)` twice; every text is non-empty.
DB2 -- the metrics (static). `METRICS` keys are unique, each with a title, a
   question and a compute function. M1: `dashboard_metrics.py` reads no
   JSON column -- no attribute `payload`, `original_payload` or
   `model_calls`, no `text(` -- and neither does the route module.
DB3 -- the numbers (fixture, two worlds). In world A: three window events
   reviewed -- one accepted as proposed, one edited, one rejected; two tick
   events accepted, both edited, one with a changed `type_id` (retyped)
   and one with a changed title only (not retyped); three step changes -- one
   approved while its completion was `met`, one approved while `unmet`, one
   with no condition; one interpreter draft `saved` as proposed and one
   `discarded`; one `event` leaf under a `not` of two. World B holds one
   more window event. `dashboard(world=A)` gives exactly the rows of
   `EXPECTED`; `world=all` counts B's event too; `until` today includes
   today; `since` the day after today leaves every dated metric empty and
   the undated ones unchanged.
DB4 -- the scope. A date that does not parse, `since` after `until` and an
   unknown world each answer 422.
DB5 -- the export. `dashboard_export(world=A)` answers an attachment whose
   JSON has `format`, A's proposals only -- the edited one with its
   `original_payload`, its round and its change `title` --, both
   interpreter drafts with their payload, the metrics and the deferrals.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import sys
import tempfile
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
METRICS_PY = ROOT / "src" / "world_engine" / "dashboard_metrics.py"
ROUTES_PY = ROOT / "src" / "world_engine" / "cockpit" / "routes" / "dashboard.py"

FAILURES: list[str] = []
FORBIDDEN_ATTRS = ("payload", "original_payload", "model_calls")

# (metric, group, label) -> (value, of), for world A.
EXPECTED: dict[tuple[str, str, str], tuple[int, int | None]] = {
    ("event_reviews", "Play — analyse de fenêtre", "accepté tel quel"): (1, 3),
    ("event_reviews", "Play — analyse de fenêtre", "accepté corrigé"): (1, 3),
    ("event_reviews", "Play — analyse de fenêtre", "rejeté"): (1, 3),
    ("event_reviews", "Tick du monde", "accepté corrigé"): (2, 2),
    ("tick_retyped", "Tick du monde", "retypés par Nia"): (1, 2),
    ("step_verdicts", "Étapes", "Nia confirme la condition"): (1, 3),
    ("step_verdicts", "Étapes", "Nia contredit la condition"): (1, 3),
    ("step_verdicts", "Étapes", "pas de condition à juger"): (1, 3),
    ("interpreter", "Propositions", "enregistrée"): (1, 2),
    ("interpreter", "Propositions", "écartée par Nia"): (1, 2),
    ("interpreter", "Enregistrées", "telles que proposées"): (1, 1),
    ("absence_leaves", "Feuilles « événement »", "sous un « non »"): (1, 2),
    ("edited_fields", "event_creation", "title"): (2, None),
    ("edited_fields", "event_creation", "type_id"): (1, None),
}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", text)


# --- DB1, DB2 --------------------------------------------------------------------

def check_db1() -> None:
    from world_engine.dashboard_deferrals import DEFERRAL_STATUSES, DEFERRALS, EXPORT
    from world_engine.dashboard_metrics import METRICS

    keys = {m.key for m in METRICS}
    if not DEFERRALS:
        fail("DB1: the deferral registry is empty")
    seen = set()
    for d in DEFERRALS:
        where = f"DB1: {d.code} ({d.ticket})"
        if (d.code, d.ticket) in seen:
            fail(f"{where} is listed twice")
        seen.add((d.code, d.ticket))
        if not all(s.strip() for s in (d.code, d.ticket, d.deferred_fr, d.condition_fr, d.anchor)):
            fail(f"{where} has an empty text")
        source = ROOT / d.source
        if not source.exists():
            fail(f"{where}: {d.source} not found")
        elif _fold(source.read_text(encoding="utf-8")).count(_fold(d.anchor)) != 1:
            fail(f"{where}: its anchor is not found exactly once in {d.source}")
        if d.status not in DEFERRAL_STATUSES or (d.follow_up is not None and d.status != "reached"):
            fail(f"{where}: status {d.status!r}, follow-up {d.follow_up!r}")
        if d.metric not in (None, EXPORT) and d.metric not in keys:
            fail(f"{where}: unknown metric {d.metric!r}")


def _attrs_and_text(path: pathlib.Path) -> tuple[set[str], bool]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    raw = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "text"
              for n in ast.walk(tree))
    return attrs, raw


def check_db2() -> None:
    from world_engine.dashboard_metrics import METRICS

    if not METRICS:
        fail("DB2: no metric")
    if len({m.key for m in METRICS}) != len(METRICS):
        fail("DB2: a metric key is listed twice")
    for m in METRICS:
        if not (m.title.strip() and m.question.strip() and callable(m.compute)):
            fail(f"DB2: {m.key} lacks a title, a question or a computation")
    for path in (METRICS_PY, ROUTES_PY):
        if not path.exists():
            fail(f"DB2: {path} not found")
            continue
        attrs, raw = _attrs_and_text(path)
        if raw or set(FORBIDDEN_ATTRS) & attrs:
            fail(f"DB2: {path.name} reads {sorted(set(FORBIDDEN_ATTRS) & attrs)} or raw SQL (M1)")


# --- fixture ---------------------------------------------------------------------

def _review(db, mut, action: str, before: dict, status: str, verdict=None) -> None:
    from world_engine.writes.mutation_reviews import ReviewCall, record_review

    mut.status = status
    db.add(mut)
    record_review(db, mut, ReviewCall(action, "unit", before, verdict))


def _fixture(engine) -> dict:
    from sqlmodel import Session

    from world_engine.conditions import node_from_dict
    from world_engine.models import (
        Agenda, AgendaStep, Character, ConditionDraft, Entity, ProposedMutation, World,
    )
    from world_engine.writes.conditions import write_condition
    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type

    with Session(engine) as db:
        ids = {}
        for key in ("a", "b"):
            world = World(name=f"Monde {key.upper()}", is_active=key == "a")
            db.add(world)
            db.flush()
            ids[key] = world.id
        brakk = Entity(world_id=ids["a"], type="character", name="Brakk")
        db.add(brakk)
        db.flush()
        db.add(Character(id=brakk.id, world_id=ids["a"], character_type="player"))
        chasse = write_event_type(db, world_id=ids["a"], spec=EventTypeSpec(
            name="Chasse", roles=(RoleSpec("Chasseur", ("character",)),)))

        def proposal(world: str, producer: str, kind: str = "event_creation", payload=None):
            row = ProposedMutation(world_id=ids[world], source_type="conversation", mutation_type=kind,
                                   payload=payload or {"title": "t", "type_id": "x"}, proposed_by=producer)
            db.add(row)
            db.flush()
            return row

        plain = proposal("a", "local_ai_window")
        _review(db, plain, "approve", dict(plain.payload), "applied")
        edited = proposal("a", "local_ai_window")
        ids["edited"] = edited.id
        before = dict(edited.payload)
        edited.payload = {"title": "Chasse au loup", "type_id": "x"}
        _review(db, edited, "approve", before, "applied")
        rejected = proposal("a", "local_ai_window")
        _review(db, rejected, "reject", dict(rejected.payload), "rejected")
        tick_titled = proposal("a", "local_ai_tick")
        before = dict(tick_titled.payload)
        tick_titled.payload = {"title": "Loups", "type_id": "x"}
        _review(db, tick_titled, "approve", before, "applied")
        tick_typed = proposal("a", "local_ai_tick")
        before = dict(tick_typed.payload)
        tick_typed.payload = {"title": "t", "type_id": "y"}
        _review(db, tick_typed, "approve", before, "applied")
        other = proposal("b", "local_ai_window")
        _review(db, other, "approve", dict(other.payload), "applied")

        for verdict in ("met", "unmet", "none"):
            step = proposal("a", "local_ai", "agenda_step_change", {"step_id": "s", "action": "complete"})
            _review(db, step, "approve", dict(step.payload), "applied", verdict)

        for outcome, saved in (("saved", True), ("discarded", None)):
            db.add(ConditionDraft(attempt_id="at", world_ref=ids["a"], world_name="Monde A", role="completion",
                                  instruction="trois loups", outcome=outcome,
                                  offer_ref="offer" if saved else None, saved_as_proposed=saved,
                                  payload={"notes": ["« apporte 3 peaux » : c'est un coût"]}))

        agenda = Agenda(world_id=ids["a"], owner_entity_id=brakk.id, title="t", status="active")
        db.add(agenda)
        db.flush()
        leaf = {"op": "leaf", "type": "event", "subject_role": "doer", "target_key": chasse.id, "threshold": 1}
        for order, tree in ((1, {"op": "not", "children": [leaf]}), (2, leaf)):
            step = AgendaStep(agenda_id=agenda.id, step_order=order, objective="o",
                              status="active" if order == 1 else "pending")
            db.add(step)
            db.flush()
            write_condition(db, world_id=ids["a"], role="completion", tree=node_from_dict(tree),
                            agenda_step_id=step.id)
        db.commit()
    return ids


def _rows(answer: dict) -> dict[tuple[str, str, str], tuple[int, int | None]]:
    return {(m["key"], r["group"], r["label"]): (r["value"], r["of"])
            for m in answer["metrics"] for r in m["rows"]}


# --- DB3, DB4, DB5 ---------------------------------------------------------------

def check_db3(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.routes import dashboard as routes

    with Session(engine) as db:
        a = _rows(routes.dashboard(world=ids["a"], since=None, until=None, db=db))
        every = _rows(routes.dashboard(world="all", since=None, until=None, db=db))
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        later = routes.dashboard(world=ids["a"], since=tomorrow, until=None, db=db)
        today = _rows(routes.dashboard(world=ids["a"], since=None, until=date.today().isoformat(), db=db))
    keys = {k[0] for k in EXPECTED}
    got = {k: v for k, v in a.items() if k[0] in keys}
    if got != EXPECTED:
        fail(f"DB3: world A's rows are {sorted(got.items())}")
    window = ("event_reviews", "Play — analyse de fenêtre", "accepté tel quel")
    if today.get(window) != (1, 3):
        fail(f"DB3: `until` today counts {today.get(window)}: the last day is not included")
    if every.get(window) != (2, 4):
        fail(f"DB3: every world counts {every.get(window)} window events accepted as proposed")
    for metric in later["metrics"]:
        undated = [r for r in _rows({"metrics": [metric]}).items()]
        if metric["dated"] and metric["rows"] and any(r["value"] for r in metric["rows"]):
            fail(f"DB3: {metric['key']} counts {metric['rows']} after tomorrow")
        if not metric["dated"] and dict(undated) != {k: v for k, v in a.items() if k[0] == metric["key"]}:
            fail(f"DB3: the undated {metric['key']} moved with the dates")


def check_db4(engine, ids: dict) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.routes import dashboard as routes

    cases = ((ids["a"], "2026-13-01", None), (ids["a"], "2026-10-12", "2026-10-01"), ("no-such-world", None, None))
    with Session(engine) as db:
        for world, since, until in cases:
            try:
                routes.dashboard(world=world, since=since, until=until, db=db)
                fail(f"DB4: {world}/{since}/{until} was accepted")
            except HTTPException as exc:
                if exc.status_code != 422:
                    fail(f"DB4: {world}/{since}/{until} answered {exc.status_code}")


def check_db5(engine, ids: dict) -> None:
    from sqlmodel import Session

    from world_engine.cockpit.routes import dashboard as routes

    with Session(engine) as db:
        answer = routes.dashboard_export(world=ids["a"], since=None, until=None, db=db)
    if "attachment" not in answer.headers.get("content-disposition", ""):
        fail(f"DB5: the export is not an attachment: {answer.headers}")
    data = json.loads(answer.body)
    proposals = data.get("proposals", [])
    if data.get("format") != "wg-nia-dashboard-export/1" or len(proposals) != 8 \
            or any(p["world_id"] != ids["a"] for p in proposals):
        fail(f"DB5: {len(proposals)} proposals, format {data.get('format')}")
    edited = next((p for p in proposals if p["id"] == ids["edited"]), None)
    if edited is None or edited["original_payload"] != {"title": "t", "type_id": "x"} \
            or [c["path"] for r in edited["reviews"] for c in r["changes"]] != ["title"]:
        fail(f"DB5: the edited proposal exports as {edited}")
    drafts = data.get("interpreter", [])
    if len(drafts) != 2 or not all(d["payload"].get("notes") for d in drafts):
        fail(f"DB5: the interpreter exports {drafts}")
    if not data.get("metrics") or not data.get("deferrals"):
        fail("DB5: the export lacks its metrics or its deferrals")


def main() -> None:
    _fresh_db()
    from sqlmodel import SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    check_db1()
    check_db2()
    ids = _fixture(engine)
    check_db3(engine, ids)
    check_db4(engine, ids)
    check_db5(engine, ids)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: dashboard_registry -- the metrics read relational columns, each deferral points at its "
          "declaration, the numbers and the export hold on a fixture")


if __name__ == "__main__":
    main()
