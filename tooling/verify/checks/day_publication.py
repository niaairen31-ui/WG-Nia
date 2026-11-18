"""G1 check for TICKET-0128 (BRIEF-0128-F) -- a resolved day is published by the creator once its proposals are reviewed; one unpublished day per character; a published day is never replayed.

DP1 -- `writes.day_runs.publish_day`: a `resolved` unpublished day with
   « Mon texte » -> `published_text` « Mon texte », `published_at` set,
   `batch.final_result` unchanged; with « » -> `EMPTY_NARRATIVE`; published
   again -> `DAY_NOT_PUBLISHABLE`; a `flagged` day -> `DAY_NOT_PUBLISHABLE`;
   it never commits (a rollback leaves the row unpublished).
DP2 -- routes, `TestClient(app, base_url="http://127.0.0.1")`, the active
   world: `GET /api/day-runs/a-publier` -> exactly C-12's keys, oldest
   first, `narrator_text` the batch's `final_result`; a day with a proposal
   at `proposed` -> `publier` 409 `PENDING_REVIEW`; at `approved` -> 409;
   once `applied` -> `publier` with `{"text": "  Réécrit  "}` -> 200,
   `published_text` « Réécrit »; another day with `{"text": null}` -> the
   narrator's text; `{"text": ""}` -> 422 `EMPTY_NARRATIVE`; a published
   day -> 409 `DAY_NOT_PUBLISHABLE`; another world's batch -> 404; `GET
   /api/day/{id}` of the published day holds `published_text` and
   `published_at`.
DP3 -- E1, `POST /api/day/declare` with `day_declare.missing_usages` and
   `day_declare.enqueue_day` swapped: a PC with a `resolved` unpublished
   day -> 409 `DAY_IN_PROGRESS`, no new day; with a `flagged` day -> 409;
   with only published and `abandoned` days -> 200.
DP4 -- T1: `routes.day._load_resolvable_day` on a published `resolved` day
   -> 409 « ... is published and cannot be replayed »; on an unpublished
   `resolved` day -> returns it.
DP5 -- static: `DayPublish.svelte` holds « À publier » and `publish(`;
   `Journee.svelte` holds `<DayPublish />` and `published_text`; a built
   asset carries « À publier ».

A rule not reached is a FAILURE. Fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import, through
`day_runs.py`'s fixture) -- never Nia's DB.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import UTC, datetime, timedelta

import day_runs as dr  # the sibling check: its fresh engine and day fixture

ROOT = pathlib.Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src"
ASSETS = ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets"
PUBLISHED_KEYS = {"batch_id", "day_number", "character_name", "declared_action", "narrator_text",
                  "pending_proposals"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _resolved(db, world_id: str, character_id: str, narrator: str, when: datetime) -> str:
    from world_engine.models import Batch

    batch_id = dr._day(db, world_id, character_id, status="resolved")
    batch = db.get(Batch, batch_id)
    batch.final_result = narrator
    db.add(batch)
    db.commit()
    pass_play = dr._pass_play(db, batch_id)
    pass_play.submitted_at = when
    db.add(pass_play)
    db.commit()
    return batch_id


def _proposal(db, world_id: str, batch_id: str, status: str) -> str:
    from world_engine.models import ProposedMutation

    row = ProposedMutation(world_id=world_id, source_type="pass_play", pass_play_id=dr._pass_play(db, batch_id).id,
                           mutation_type="knowledge_change", payload={}, status=status, proposed_by="local_ai")
    db.add(row)
    db.commit()
    return row.id


def _set_status(db, model, row_id: str, status: str) -> None:
    db.rollback()
    row = db.get(model, row_id)
    row.status = status
    db.add(row)
    db.commit()


# --- DP1 -----------------------------------------------------------------------

def rule_dp1(db, ids: dict) -> int:
    from world_engine.models import Batch
    from world_engine.writes.day_runs import DAY_NOT_PUBLISHABLE, EMPTY_NARRATIVE, publish_day

    reached = 0
    batch_id = _resolved(db, ids["b"], ids["bea"], "Le narrateur.", datetime.now(UTC))

    reached += 1
    pass_play = dr._pass_play(db, batch_id)
    publish_day(db, pass_play=pass_play, text="Mon texte")
    db.rollback()
    if dr._pass_play(db, batch_id).published_at is not None:
        fail("DP1: publish_day committed")

    reached += 1
    pass_play = dr._pass_play(db, batch_id)
    publish_day(db, pass_play=pass_play, text="  Mon texte ")
    db.commit()
    row = dr._pass_play(db, batch_id)
    if row.published_text != "Mon texte" or row.published_at is None:
        fail(f"DP1: published {row.published_text!r} at {row.published_at!r}")
    if db.get(Batch, batch_id).final_result != "Le narrateur.":
        fail("DP1: the narrator's text changed")

    for label, text_, target, expected in (
        ("empty", "  ", "fresh", EMPTY_NARRATIVE),
        ("published again", "x", batch_id, DAY_NOT_PUBLISHABLE),
        ("flagged", "x", "flagged", DAY_NOT_PUBLISHABLE),
    ):
        reached += 1
        if target == "fresh":
            target = _resolved(db, ids["b"], ids["bea"], "n", datetime.now(UTC))
        elif target == "flagged":
            target = dr._day(db, ids["b"], ids["bea"], status="flagged")
        try:
            publish_day(db, pass_play=dr._pass_play(db, target), text=text_)
            fail(f"DP1 {label}: publish_day accepted")
        except ValueError as exc:
            if str(exc) != expected:
                fail(f"DP1 {label}: {exc}")
        db.rollback()
    return reached


# --- DP2 -----------------------------------------------------------------------

def rule_dp2(client, db, ids: dict) -> int:
    from world_engine.day_run_reads import PENDING_REVIEW
    from world_engine.models import ProposedMutation
    from world_engine.writes.day_runs import DAY_NOT_PUBLISHABLE, EMPTY_NARRATIVE

    reached = 0
    now = datetime.now(UTC)
    first = _resolved(db, ids["a"], ids["ana"], "Récit un.", now - timedelta(hours=2))
    second = _resolved(db, ids["a"], ids["ana"], "Récit deux.", now - timedelta(hours=1))
    proposal = _proposal(db, ids["a"], first, "proposed")

    reached += 1
    resp = client.get("/api/day-runs/a-publier")
    items = resp.json() if resp.status_code == 200 else []
    mine = [i for i in items if i.get("batch_id") in (first, second)]
    if resp.status_code != 200 or [i["batch_id"] for i in mine] != [first, second]:
        fail(f"DP2: a-publier -> {resp.status_code}, order {[i.get('batch_id') for i in mine]!r}")
    elif any(set(i) != PUBLISHED_KEYS for i in items) or mine[0]["narrator_text"] != "Récit un." \
            or mine[0]["pending_proposals"] != 1:
        fail(f"DP2: a-publier items are {mine!r}")

    for status in ("proposed", "approved"):
        reached += 1
        _set_status(db, ProposedMutation, proposal, status)
        resp = client.post(f"/api/day-runs/{first}/publier", json={"text": "x"})
        if resp.status_code != 409 or resp.json().get("detail") != PENDING_REVIEW:
            fail(f"DP2: publier with a {status} proposal -> {resp.status_code} {resp.text}")

    reached += 1
    _set_status(db, ProposedMutation, proposal, "applied")
    resp = client.post(f"/api/day-runs/{first}/publier", json={"text": "  Réécrit  "})
    if resp.status_code != 200 or not resp.json().get("ok") or dr._pass_play(db, first).published_text != "Réécrit":
        fail(f"DP2: publier rewritten -> {resp.status_code} {resp.text}")

    reached += 1
    resp = client.post(f"/api/day-runs/{second}/publier", json={"text": ""})
    if resp.status_code != 422 or resp.json().get("detail") != EMPTY_NARRATIVE:
        fail(f"DP2: publier empty -> {resp.status_code} {resp.text}")

    reached += 1
    resp = client.post(f"/api/day-runs/{second}/publier", json={"text": None})
    if resp.status_code != 200 or dr._pass_play(db, second).published_text != "Récit deux.":
        fail(f"DP2: publier null -> {resp.status_code} {resp.text}")

    reached += 1
    resp = client.post(f"/api/day-runs/{first}/publier", json={"text": "encore"})
    if resp.status_code != 409 or resp.json().get("detail") != DAY_NOT_PUBLISHABLE:
        fail(f"DP2: publier twice -> {resp.status_code} {resp.text}")

    reached += 1
    foreign = _resolved(db, ids["b"], ids["bea"], "n", now)
    resp = client.post(f"/api/day-runs/{foreign}/publier", json={"text": "x"})
    if resp.status_code != 404:
        fail(f"DP2: publier on world B -> {resp.status_code}")

    reached += 1
    resp = client.get(f"/api/day/{first}")
    body = resp.json() if resp.status_code == 200 else {}
    if body.get("published_text") != "Réécrit" or not body.get("published_at"):
        fail(f"DP2: GET /api/day -> {resp.status_code}, {body.get('published_text')!r}")
    return reached


# --- DP3 -----------------------------------------------------------------------

def _day_count(db) -> int:
    from sqlmodel import func, select

    from world_engine.models import PassPlay

    db.rollback()
    return db.exec(select(func.count()).select_from(PassPlay)).one()


def rule_dp3(client, db, ids: dict) -> int:
    from world_engine.cockpit import day_declare
    from world_engine.day_run_reads import DAY_IN_PROGRESS
    from world_engine.models import PassPlay
    from world_engine.models import World

    reached = 0
    world = World(name="E1", is_active=False)
    db.add(world)
    db.commit()
    for other in db.exec(__import__("sqlmodel").select(World)).all():
        other.is_active = False  # all off first: one active world at every flush
        db.add(other)
    db.commit()
    world.is_active = True
    db.add(world)
    db.commit()
    pc = dr._pc(db, world.id, "Eli")
    originals = (day_declare.missing_usages, day_declare.enqueue_day)
    day_declare.missing_usages = lambda *a, **k: []
    day_declare.enqueue_day = lambda batch_id: None
    body = {"declared_action": "Je marche."}
    try:
        reached += 1
        resolved = _resolved(db, world.id, pc, "n", datetime.now(UTC))
        before = _day_count(db)
        resp = client.post("/api/day/declare", json=body)
        if resp.status_code != 409 or resp.json().get("detail") != DAY_IN_PROGRESS or _day_count(db) != before:
            fail(f"DP3: a resolved unpublished day -> {resp.status_code} {resp.text}")

        reached += 1
        row = dr._pass_play(db, resolved)
        row.published_at = datetime.now(UTC)
        db.add(row)
        db.commit()
        flagged = dr._day(db, world.id, pc, status="flagged")
        resp = client.post("/api/day/declare", json=body)
        if resp.status_code != 409 or resp.json().get("detail") != DAY_IN_PROGRESS:
            fail(f"DP3: a flagged day -> {resp.status_code} {resp.text}")

        reached += 1
        _set_status(db, PassPlay, dr._pass_play(db, flagged).id, "abandoned")
        resp = client.post("/api/day/declare", json=body)
        if resp.status_code != 200:
            fail(f"DP3: only published and abandoned days -> {resp.status_code} {resp.text}")
    finally:
        day_declare.missing_usages, day_declare.enqueue_day = originals
    return reached


# --- DP4 -----------------------------------------------------------------------

def rule_dp4(db, ids: dict) -> int:
    from fastapi import HTTPException

    from world_engine.cockpit.routes.day import _load_resolvable_day

    reached = 0
    published = _resolved(db, ids["b"], ids["bea"], "n", datetime.now(UTC))
    row = dr._pass_play(db, published)
    row.published_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    reached += 1
    try:
        _load_resolvable_day(published, ids["b"], db)
        fail("DP4: a published day was loaded for resolution")
    except HTTPException as exc:
        if exc.status_code != 409 or "is published and cannot be replayed" not in str(exc.detail):
            fail(f"DP4: a published day -> {exc.status_code} {exc.detail}")
    reached += 1
    fresh = _resolved(db, ids["b"], ids["bea"], "n", datetime.now(UTC))
    _batch, pass_play = _load_resolvable_day(fresh, ids["b"], db)
    if pass_play.batch_id != fresh:
        fail("DP4: an unpublished resolved day was not returned")
    return reached


# --- DP5 -----------------------------------------------------------------------

def rule_dp5() -> int:
    publish_src = (FRONTEND / "journee" / "DayPublish.svelte").read_text(encoding="utf-8")
    if "À publier" not in publish_src or "publish(" not in publish_src:
        fail("DP5: DayPublish.svelte lacks « À publier » or publish(")
    journee = (FRONTEND / "journee" / "Journee.svelte").read_text(encoding="utf-8")
    if "<DayPublish />" not in journee or "published_text" not in journee:
        fail("DP5: Journee.svelte lacks <DayPublish /> or published_text")
    built = "".join(p.read_text(encoding="utf-8", errors="replace") for p in ASSETS.glob("*.js"))
    if "À publier" not in built:
        fail("DP5: no built asset carries « À publier »")
    return 3


def main() -> int:
    expected = {"DP1": 5, "DP2": 9, "DP3": 3, "DP4": 2, "DP5": 3}
    reached: dict[str, int] = {}
    try:
        reached["DP5"] = rule_dp5()
    except Exception as exc:  # noqa: BLE001 -- fail-closed
        fail(f"DP5 raised {type(exc).__name__}: {exc}")
    engine = dr._fresh_engine()
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit.app import app

    try:
        with Session(engine) as db:
            ids = dr._fixture(db)
            reached["DP1"] = rule_dp1(db, ids)
            reached["DP4"] = rule_dp4(db, ids)
            client = TestClient(app, base_url="http://127.0.0.1")
            reached["DP2"] = rule_dp2(client, db, ids)
            reached["DP3"] = rule_dp3(client, db, ids)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"raised {type(exc).__name__}: {exc}")
    finally:
        dr._drain()
    for rule, count in expected.items():
        if reached.get(rule, 0) != count:
            fail(f"{rule} reached {reached.get(rule, 0)} of its {count} rows")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: day_publication -- DP1-DP5: the creator publishes a reviewed day once, the narrator's "
          "text kept; one unpublished day per character; a published day is never replayed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
