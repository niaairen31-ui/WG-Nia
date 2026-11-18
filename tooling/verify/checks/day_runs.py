"""G1 check for TICKET-0128 (BRIEF-0128-E) -- a declared day runs in the background; every failure is written, listed, relaunched or abandoned.

DR1 -- `day_runner.failure_of` walks the lot's (b) table row by row: 502
   -> `model_failed`, 409 -> `blocked`, 422 with a dict `message` and 422
   with a string -> `rejected`, 400 / 404 -> `refused`, 500 / 503 ->
   `crashed`, each with its detail; any other exception -> `crashed`, its
   text or its class name.
DR2 -- `run_day`, `routes.day.plan_day` / `resolve_day` swapped for stubs,
   on a day of Bea in a world B that is not the active one: (a) both stubs
   succeed -> None, each called with the batch id, no failure row; (b) the
   plan stub raises 409 « ambigu » -> `blocked`, one row (plan, blocked,
   « ambigu ») in world B, the day `flagged`, the resolve stub not called;
   (c) a `resolving` day whose resolve stub raises 422 {message, reason} ->
   (resolve, rejected, « m »); (d) the plan stub raises
   RuntimeError(« boom ») -> (plan, crashed, « boom »); (e) a `resolved`
   day -> None, no stub called; (f) a batch with no day -> None.
DR3 -- `interrupt_stale_days`: a `submitted`, a `resolving` and a
   `resolved` day -> 2; rows (plan, interrupted, INTERRUPTED_REASON) and
   (resolve, interrupted, ...); both `flagged`; the `resolved` day
   untouched; a second call -> 0.
DR4 -- routes, `TestClient(app, base_url="http://127.0.0.1")`, active world
   A: `GET /api/day-runs/echecs` -> exactly C-12's keys per item, newest
   failure first, French labels; `relancer` on a plan-stage failure -> 200
   `{"ok": true, "stage": "plan"}`, the day `submitted`, `queued_count()`
   one more; again -> 409 `DAY_NOT_FLAGGED`; on a resolve-stage failure ->
   `resolving`; `abandonner` -> 200, `abandoned`; a batch of world B -> 404
   « Journée introuvable. »; `GET /api/day-runs/etat` -> `{"running": None,
   "queued": <n>}`.
DR5 -- the declaration, `day_declare.missing_usages` and
   `day_declare.enqueue_day` (a recorder) swapped: `POST /api/day/declare`
   on A's only PC -> 200, the day `submitted`, its batch id recorded once;
   an empty declaration -> 422 and the recorder not called.
DR6 -- `compute_metrics` with two `plan` failures (`blocked`, `crashed`)
   and one `resolve` failure in A: the `day_run_failures` rows are exactly
   (Plan, blocked label, 1, 2), (Plan, crashed label, 1, 2), (Résolution,
   its label, 1, 1).
DR7 -- static, code tokens: `plan_day` and `resolve_day` carry no
   decorator; `app.py`'s `_start_day_runner_on_startup` calls
   `interrupt_stale_days()` before `start_day_runner()`; `day_runner.py`
   holds exactly one `threading.Thread(` with `daemon=True` and
   `name="day-runner"`, no `print(`, and no module-level import naming
   `routes`; `abandon_refusal` names "flagged"; `Journee.svelte` holds
   neither `planDay(` nor `resolveDay(` and holds `<DayFailures />`;
   `Header.svelte` holds `<DayRunBanner />`; a built asset carries
   « Journées en échec » and « Journée en calcul ».

The worker thread is never started; every swapped name is restored in
`finally`. A rule not reached is a FAILURE. Fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
Nia's DB.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PACKAGE = SRC / "world_engine"
FRONTEND = ROOT / "frontend" / "src"
ASSETS = PACKAGE / "cockpit" / "static" / "assets"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


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


# --- fixture -------------------------------------------------------------------

def _pc(db, world_id: str, name: str) -> str:
    from world_engine.models import Character, Entity

    entity = Entity(world_id=world_id, type="character", name=name)
    db.add(entity)
    db.flush()
    db.add(Character(id=entity.id, world_id=world_id, character_type="player"))
    db.commit()
    return entity.id


def _day(db, world_id: str, character_id: str, status: str = "submitted") -> str:
    from world_engine.cockpit.routes.day import _get_or_open_session
    from world_engine.writes import write_batch, write_pass_play

    sess = _get_or_open_session(world_id, db)
    batch = write_batch(db, session_id=sess.id, changed_by="creator")
    db.add(batch)
    db.flush()
    pass_play = write_pass_play(db, batch_id=batch.id, session_id=sess.id, character_id=character_id,
                                declared_action="Je flâne.")
    pass_play.status = status
    db.add(pass_play)
    db.commit()
    return batch.id


def _pass_play(db, batch_id: str):
    from sqlmodel import select

    from world_engine.models import PassPlay

    db.rollback()
    return db.exec(select(PassPlay).where(PassPlay.batch_id == batch_id)).first()


def _failures(db, batch_id: str) -> list[tuple]:
    from sqlmodel import select

    from world_engine.models import DayRunFailure

    pass_play = _pass_play(db, batch_id)
    rows = db.exec(select(DayRunFailure).where(DayRunFailure.pass_play_id == pass_play.id)).all()
    return [(r.stage, r.code, r.reason, r.world_id) for r in rows]


def _fixture(db) -> dict:
    from world_engine.models import World

    a = World(name="Alpha", is_active=True)
    b = World(name="Beta", is_active=False)
    db.add(a)
    db.add(b)
    db.commit()
    ids = {"a": a.id, "b": b.id}
    ids["ana"] = _pc(db, a.id, "Ana")
    ids["bea"] = _pc(db, b.id, "Bea")
    return ids


def _clear_days(db) -> None:
    """Every day of the fixture moves out of the worker's statuses."""
    from sqlmodel import select

    from world_engine.models import PassPlay

    db.rollback()
    for row in db.exec(select(PassPlay).where(PassPlay.status.in_(("submitted", "resolving")))).all():
        row.status = "resolved"
        db.add(row)
    db.commit()


def _drain() -> None:
    from world_engine.cockpit import day_runner

    while not day_runner._QUEUE.empty():
        day_runner._QUEUE.get_nowait()


# --- DR1 -----------------------------------------------------------------------

def rule_dr1() -> int:
    from fastapi import HTTPException

    from world_engine.cockpit.day_runner import failure_of

    class Quiet(Exception):
        def __str__(self) -> str:
            return ""

    table = (
        (HTTPException(502, "m502"), ("model_failed", "m502")),
        (HTTPException(409, "m409"), ("blocked", "m409")),
        (HTTPException(422, detail={"message": "msg", "reason": "r"}), ("rejected", "msg")),
        (HTTPException(422, "m422"), ("rejected", "m422")),
        (HTTPException(400, "m400"), ("refused", "m400")),
        (HTTPException(404, "m404"), ("refused", "m404")),
        (HTTPException(500, "m500"), ("crashed", "m500")),
        (HTTPException(503, "m503"), ("crashed", "m503")),
        (RuntimeError("boom"), ("crashed", "boom")),
        (Quiet(), ("crashed", "Quiet")),
    )
    for exc, expected in table:
        got = failure_of(exc)
        if got != expected:
            fail(f"DR1: failure_of({exc!r}) -> {got!r}, expected {expected!r}")
    return len(table)


# --- DR2 -----------------------------------------------------------------------

def rule_dr2(db, ids: dict) -> int:
    from fastapi import HTTPException

    from world_engine.cockpit import day_runner
    from world_engine.cockpit.routes import day as day_route

    calls: list[tuple[str, str]] = []
    behaviour: dict = {}

    def _set(batch_id: str, session, status: str) -> None:
        from sqlmodel import select

        from world_engine.models import PassPlay

        row = session.exec(select(PassPlay).where(PassPlay.batch_id == batch_id)).first()
        row.status = status
        session.add(row)
        session.commit()

    def plan_stub(batch_id, session):
        calls.append(("plan", batch_id))
        if behaviour.get("plan") is not None:
            raise behaviour["plan"]
        _set(batch_id, session, "resolving")
        return {}

    def resolve_stub(batch_id, session):
        calls.append(("resolve", batch_id))
        if behaviour.get("resolve") is not None:
            raise behaviour["resolve"]
        _set(batch_id, session, "resolved")
        return {}

    originals = (day_route.plan_day, day_route.resolve_day)
    day_route.plan_day, day_route.resolve_day = plan_stub, resolve_stub
    reached = 0
    try:
        # (a)
        reached += 1
        batch = _day(db, ids["b"], ids["bea"])
        got = day_runner.run_day(batch)
        if got is not None or calls != [("plan", batch), ("resolve", batch)] or _failures(db, batch):
            fail(f"DR2 (a): got {got!r}, calls {calls!r}, failures {_failures(db, batch)!r}")
        if _pass_play(db, batch).status != "resolved":
            fail("DR2 (a): the day is not resolved")
        # (b)
        reached += 1
        calls.clear()
        behaviour.update(plan=HTTPException(409, "ambigu"), resolve=None)
        batch = _day(db, ids["b"], ids["bea"])
        got = day_runner.run_day(batch)
        rows = _failures(db, batch)
        if got != "blocked" or rows != [("plan", "blocked", "ambigu", ids["b"])]:
            fail(f"DR2 (b): got {got!r}, rows {rows!r}")
        if _pass_play(db, batch).status != "flagged" or ("resolve", batch) in calls:
            fail("DR2 (b): the day is not flagged, or the resolve stub ran")
        # (c)
        reached += 1
        behaviour.update(plan=None, resolve=HTTPException(422, detail={"message": "m", "reason": "r"}))
        batch = _day(db, ids["b"], ids["bea"], status="resolving")
        got = day_runner.run_day(batch)
        rows = _failures(db, batch)
        if got != "rejected" or [r[:3] for r in rows] != [("resolve", "rejected", "m")]:
            fail(f"DR2 (c): got {got!r}, rows {rows!r}")
        # (d)
        reached += 1
        behaviour.update(plan=RuntimeError("boom"), resolve=None)
        batch = _day(db, ids["b"], ids["bea"])
        got = day_runner.run_day(batch)
        rows = _failures(db, batch)
        if got != "crashed" or [r[:3] for r in rows] != [("plan", "crashed", "boom")]:
            fail(f"DR2 (d): got {got!r}, rows {rows!r}")
        # (e)
        reached += 1
        calls.clear()
        batch = _day(db, ids["b"], ids["bea"], status="resolved")
        if day_runner.run_day(batch) is not None or calls:
            fail(f"DR2 (e): a resolved day ran {calls!r}")
        # (f)
        reached += 1
        if day_runner.run_day("no-such-batch") is not None or calls:
            fail("DR2 (f): a missing day ran")
    finally:
        day_route.plan_day, day_route.resolve_day = originals
    return reached


# --- DR3 -----------------------------------------------------------------------

def rule_dr3(db, ids: dict) -> int:
    from world_engine.cockpit.day_runner import INTERRUPTED_REASON, interrupt_stale_days

    _clear_days(db)
    submitted = _day(db, ids["a"], ids["ana"])
    resolving = _day(db, ids["b"], ids["bea"], status="resolving")
    resolved = _day(db, ids["a"], ids["ana"], status="resolved")
    reached = 1
    count = interrupt_stale_days()
    if count != 2:
        fail(f"DR3: interrupt_stale_days -> {count}, expected 2")
    if _failures(db, submitted) != [("plan", "interrupted", INTERRUPTED_REASON, ids["a"])]:
        fail(f"DR3: the submitted day's rows are {_failures(db, submitted)!r}")
    if _failures(db, resolving) != [("resolve", "interrupted", INTERRUPTED_REASON, ids["b"])]:
        fail(f"DR3: the resolving day's rows are {_failures(db, resolving)!r}")
    for batch in (submitted, resolving):
        if _pass_play(db, batch).status != "flagged":
            fail("DR3: an interrupted day is not flagged")
    if _pass_play(db, resolved).status != "resolved" or _failures(db, resolved):
        fail("DR3: the resolved day was touched")
    reached += 1
    if interrupt_stale_days() != 0:
        fail("DR3: a second call interrupted again")
    return reached


# --- DR4 -----------------------------------------------------------------------

FAILED_KEYS = {"batch_id", "day_number", "character_name", "declared_action", "stage", "stage_label",
               "code", "code_label", "reason", "failed_at"}


def _flag(db, batch_id: str, world_id: str, stage: str, code: str, when: datetime) -> None:
    from world_engine.writes.day_runs import write_day_run_failure

    pass_play = _pass_play(db, batch_id)
    row = write_day_run_failure(db, pass_play=pass_play, world_id=world_id, stage=stage, code=code, reason="r")
    row.created_at = when
    db.add(row)
    db.commit()


def rule_dr4(client, db, ids: dict) -> int:
    from world_engine.cockpit import day_runner
    from world_engine.day_run_reads import CODE_LABELS_FR, STAGE_LABELS_FR
    from world_engine.writes.day_runs import DAY_NOT_FLAGGED

    _clear_days(db)
    _drain()
    now = datetime.now(UTC)
    plan_day = _day(db, ids["a"], ids["ana"])
    _flag(db, plan_day, ids["a"], "plan", "blocked", now - timedelta(hours=1))
    resolve_day = _day(db, ids["a"], ids["ana"], status="resolving")
    _flag(db, resolve_day, ids["a"], "resolve", "rejected", now)
    reached = 0

    reached += 1
    resp = client.get("/api/day-runs/echecs")
    items = resp.json() if resp.status_code == 200 else []
    if resp.status_code != 200 or not items:
        fail(f"DR4: echecs -> {resp.status_code} {resp.text[:200]}")
    else:
        if any(set(item) != FAILED_KEYS for item in items):
            fail(f"DR4: echecs keys are {sorted(items[0])}")
        if items[0]["batch_id"] != resolve_day:
            fail("DR4: echecs is not newest failure first")
        if items[0]["stage_label"] != STAGE_LABELS_FR["resolve"] or items[0]["code_label"] != CODE_LABELS_FR["rejected"]:
            fail(f"DR4: echecs labels are {items[0]['stage_label']!r} / {items[0]['code_label']!r}")

    reached += 1
    before = day_runner.queued_count()
    resp = client.post(f"/api/day-runs/{plan_day}/relancer")
    if resp.status_code != 200 or resp.json() != {"ok": True, "stage": "plan"}:
        fail(f"DR4: relancer (plan) -> {resp.status_code} {resp.text}")
    if _pass_play(db, plan_day).status != "submitted":
        fail("DR4: a relaunched plan-stage day is not submitted")
    if day_runner.queued_count() != before + 1:
        fail("DR4: relancer did not enqueue the day")
    _drain()

    reached += 1
    resp = client.post(f"/api/day-runs/{plan_day}/relancer")
    if resp.status_code != 409 or resp.json().get("detail") != DAY_NOT_FLAGGED:
        fail(f"DR4: relancer on an unflagged day -> {resp.status_code} {resp.text}")

    reached += 1
    resp = client.post(f"/api/day-runs/{resolve_day}/relancer")
    if resp.status_code != 200 or _pass_play(db, resolve_day).status != "resolving":
        fail(f"DR4: relancer (resolve) -> {resp.status_code}, status {_pass_play(db, resolve_day).status!r}")
    _drain()

    reached += 1
    _flag(db, resolve_day, ids["a"], "resolve", "crashed", now + timedelta(minutes=1))
    resp = client.post(f"/api/day-runs/{resolve_day}/abandonner")
    if resp.status_code != 200 or resp.json() != {"ok": True} or _pass_play(db, resolve_day).status != "abandoned":
        fail(f"DR4: abandonner -> {resp.status_code} {resp.text}")

    reached += 1
    foreign = _day(db, ids["b"], ids["bea"], status="resolved")
    for verb in ("relancer", "abandonner"):
        resp = client.post(f"/api/day-runs/{foreign}/{verb}")
        if resp.status_code != 404 or resp.json().get("detail") != "Journée introuvable.":
            fail(f"DR4: {verb} on world B's day -> {resp.status_code} {resp.text}")

    reached += 1
    resp = client.get("/api/day-runs/etat")
    if resp.status_code != 200 or resp.json() != {"running": None, "queued": day_runner.queued_count()}:
        fail(f"DR4: etat -> {resp.status_code} {resp.text}")
    return reached


# --- DR5 -----------------------------------------------------------------------

def rule_dr5(client, db, ids: dict) -> int:
    from world_engine.cockpit import day_declare

    recorded: list[str] = []
    originals = (day_declare.missing_usages, day_declare.enqueue_day)
    day_declare.missing_usages = lambda *a, **k: []
    day_declare.enqueue_day = recorded.append
    reached = 0
    try:
        reached += 1
        resp = client.post("/api/day/declare", json={"declared_action": "Je pêche."})
        if resp.status_code != 200:
            fail(f"DR5: declare -> {resp.status_code} {resp.text}")
        else:
            batch_id = resp.json()["id"]
            if resp.json()["status"] != "submitted" or _pass_play(db, batch_id).status != "submitted":
                fail("DR5: the declared day is not submitted")
            if recorded != [batch_id]:
                fail(f"DR5: enqueue_day recorded {recorded!r}")
        reached += 1
        recorded.clear()
        resp = client.post("/api/day/declare", json={"declared_action": "   "})
        if resp.status_code != 422 or recorded:
            fail(f"DR5: an empty declaration -> {resp.status_code}, recorded {recorded!r}")
    finally:
        day_declare.missing_usages, day_declare.enqueue_day = originals
    return reached


# --- DR6 -----------------------------------------------------------------------

def rule_dr6(engine) -> int:
    from sqlmodel import Session

    from world_engine.dashboard_metrics import Scope, compute_metrics
    from world_engine.day_run_reads import CODE_LABELS_FR

    with Session(engine) as db:
        world = __import__("world_engine.models", fromlist=["World"]).World(name="Metric", is_active=False)
        db.add(world)
        db.commit()
        pc = _pc(db, world.id, "Mia")
        now = datetime.now(UTC)
        for stage, code, status in (("plan", "blocked", "submitted"), ("plan", "crashed", "submitted"),
                                    ("resolve", "model_failed", "resolving")):
            _flag(db, _day(db, world.id, pc, status=status), world.id, stage, code, now)
        metrics = {m["key"]: m for m in compute_metrics(db, Scope(world_ids=(world.id,)))}
    metric = metrics.get("day_run_failures")
    if metric is None:
        fail("DR6: compute_metrics holds no day_run_failures")
        return 1
    rows = [(r["group"], r["label"], r["value"], r["of"]) for r in metric["rows"]]
    expected = [("Plan", CODE_LABELS_FR["blocked"], 1, 2), ("Plan", CODE_LABELS_FR["crashed"], 1, 2),
                ("Résolution", CODE_LABELS_FR["model_failed"], 1, 1)]
    if rows != expected:
        fail(f"DR6: rows are {rows!r}")
    return 1


# --- DR7 -----------------------------------------------------------------------

def _function(tree: ast.AST, name: str):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def rule_dr7() -> int:
    reached = 0
    day_tree = ast.parse((PACKAGE / "cockpit" / "routes" / "day.py").read_text(encoding="utf-8"))
    for name in ("plan_day", "resolve_day"):
        reached += 1
        fn = _function(day_tree, name)
        if fn is None or fn.decorator_list:
            fail(f"DR7: routes/day.py::{name} is missing or decorated")

    reached += 1
    app_tree = ast.parse((PACKAGE / "cockpit" / "app.py").read_text(encoding="utf-8"))
    hook = _function(app_tree, "_start_day_runner_on_startup")
    order = [n.func.id for n in ast.walk(hook) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)] \
        if hook is not None else []
    if order != ["interrupt_stale_days", "start_day_runner"]:
        fail(f"DR7: _start_day_runner_on_startup calls {order!r}")

    reached += 1
    runner_src = (PACKAGE / "cockpit" / "day_runner.py").read_text(encoding="utf-8")
    runner_tree = ast.parse(runner_src)
    threads = [n for n in ast.walk(runner_tree) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute) and n.func.attr == "Thread"]
    kws = {kw.arg: getattr(kw.value, "value", None) for kw in threads[0].keywords} if len(threads) == 1 else {}
    if len(threads) != 1 or kws.get("daemon") is not True or kws.get("name") != "day-runner":
        fail(f"DR7: day_runner.py holds {len(threads)} Thread( call(s), keywords {kws!r}")
    if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
           for n in ast.walk(runner_tree)):
        fail("DR7: day_runner.py calls print(")
    for node in runner_tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [getattr(node, "module", None) or ""] + [a.name for a in node.names]
            if any("routes" in n for n in names):
                fail(f"DR7: day_runner.py imports {names!r} at module level")

    reached += 1
    quests_tree = ast.parse((PACKAGE / "writes" / "quests.py").read_text(encoding="utf-8"))
    refusal = _function(quests_tree, "abandon_refusal")
    if refusal is None or not any(isinstance(n, ast.Constant) and n.value == "flagged" for n in ast.walk(refusal)):
        fail("DR7: abandon_refusal does not name 'flagged'")

    reached += 1
    journee = (FRONTEND / "journee" / "Journee.svelte").read_text(encoding="utf-8")
    if "planDay(" in journee or "resolveDay(" in journee or "<DayFailures />" not in journee:
        fail("DR7: Journee.svelte still plans or resolves, or lacks <DayFailures />")
    if "<DayRunBanner />" not in (FRONTEND / "Header.svelte").read_text(encoding="utf-8"):
        fail("DR7: Header.svelte lacks <DayRunBanner />")

    reached += 1
    built = "".join(p.read_text(encoding="utf-8", errors="replace") for p in ASSETS.glob("*.js"))
    for text_ in ("Journées en échec", "Journée en calcul"):
        if text_ not in built:
            fail(f"DR7: no built asset carries « {text_} »")
    return reached


def main() -> int:
    expected = {"DR1": 10, "DR2": 6, "DR3": 2, "DR4": 7, "DR5": 2, "DR6": 1, "DR7": 7}
    reached: dict[str, int] = {}
    try:
        reached["DR7"] = rule_dr7()
    except Exception as exc:  # noqa: BLE001 -- fail-closed
        fail(f"DR7 raised {type(exc).__name__}: {exc}")
    engine = _fresh_engine()
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit.app import app

    try:
        reached["DR1"] = rule_dr1()
        with Session(engine) as db:
            ids = _fixture(db)
            reached["DR2"] = rule_dr2(db, ids)
            reached["DR3"] = rule_dr3(db, ids)
            client = TestClient(app, base_url="http://127.0.0.1")
            reached["DR4"] = rule_dr4(client, db, ids)
            reached["DR5"] = rule_dr5(client, db, ids)
        reached["DR6"] = rule_dr6(engine)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"raised {type(exc).__name__}: {exc}")
    finally:
        _drain()
    for rule, count in expected.items():
        if reached.get(rule, 0) != count:
            fail(f"{rule} reached {reached.get(rule, 0)} of its {count} rows")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: day_runs -- DR1-DR7: failure codes, the worker's run and its failures, "
          "the startup sweep, relaunch and abandon, the declaration enqueues, the metric, the wiring")
    return 0


if __name__ == "__main__":
    sys.exit(main())
