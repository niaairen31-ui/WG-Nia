"""G1 check for TICKET-0121 -- a quest request is a row the creator works through.

BRIEF-0121-B's rules (L1 of the Journée quest designer): the storage and
writer of v2.28, and the dashboard's way to watch D2, S3 and P1.

QR1 -- storage (import). `quest_request` carries exactly its contract's
   columns, CHECK names and index names; the code's schema version is v2.28
   or later; the migration `scripts/migrate_v2_28_quest_requests.py` exists
   and refuses below v2.27 (`_PREVIOUS_VERSION == "v2.27"`).
QR2 -- `open_request` refuses an unknown trigger, an empty declaration and a
   missing step; a second call for one step returns the same row, one row in
   the table.
QR3 -- `move_request` appends one `change_history` entry per call holding
   the former status and every field it changed; it refuses an unknown
   status, an unknown field and an answer outside `EXISTENCE_ANSWERS`.
QR4 -- the CHECKs hold: a raw INSERT with `status='done'`, one with
   `trigger='other'` and one with `existence_answer='maybe'` each raise
   `IntegrityError`.
QR5 -- `inquiry_step_ids` returns the steps of `route` and `dropped`
   requests of that agenda only: a `blocked` one and another agenda's are
   absent.
QR6 -- `compute_metrics` over a fixture (one request of each trigger, one
   answered `already`, one proposal `applied` whose offer's giver was
   created after it): the `quest_requests` rows equal a literal expected
   list; a world with none gives the same labels at 0.
QR7 -- the deferrals `D2`, `S3` and `P1` of `TICKET-0121` exist with
   `metric == "quest_requests"`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
import tempfile
from datetime import UTC, datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "scripts" / "migrate_v2_28_quest_requests.py"

FAILURES: list[str] = []

COLUMNS = ("id", "world_id", "character_id", "pass_play_id", "agenda_step_id", "trigger", "declaration",
           "subject", "status", "existence_answer", "creator_text", "existing_entity_id", "lore_entry_id",
           "mutation_id", "offer_id", "note", "created_at", "updated_at", "change_history")
CHECKS = ("ck_quest_request_answer", "ck_quest_request_status", "ck_quest_request_trigger")
INDEXES = ("idx_quest_request_step", "idx_quest_request_world")

EXPECTED_ROWS = [
    ("Origine", "Déclaration aiguillée", 1, 3),
    ("Origine", "Étape bloquée", 1, 3),
    ("Origine", "Savoir introuvable", 1, 3),
    ("Origine", "Journées aiguillées vers une quête", 1, 2),
    ("Existence", "Elle existe", 0, 3),
    ("Existence", "Elle n'existe pas", 1, 3),
    ("Existence", "Le lore le disait déjà", 1, 3),
    ("Donneur", "Offres approuvées", 1, 3),
    ("Donneur", "Donneur créé après la proposition", 1, 1),
]


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_db() -> None:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


# --- QR1 -------------------------------------------------------------------------

def check_qr1() -> None:
    from sqlalchemy import CheckConstraint
    from sqlmodel import SQLModel

    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    table = SQLModel.metadata.tables.get("quest_request")
    if table is None:
        fail("QR1: quest_request is not declared")
        return
    if tuple(table.c.keys()) != COLUMNS:
        fail(f"QR1: columns are {tuple(table.c.keys())}")
    found = tuple(sorted(c.name for c in table.constraints if isinstance(c, CheckConstraint)))
    if found != CHECKS:
        fail(f"QR1: CHECKs are {found}")
    if tuple(sorted(i.name for i in table.indexes)) != INDEXES:
        fail(f"QR1: indexes are {sorted(i.name for i in table.indexes)}")
    unique = [i.name for i in table.indexes if i.unique]
    if unique != ["idx_quest_request_step"]:
        fail(f"QR1: unique indexes are {unique}")
    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < _version_key("v2.28"):
        fail(f"QR1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
    if not MIGRATION.is_file():
        fail("QR1: scripts/migrate_v2_28_quest_requests.py is missing")
    elif not re.search(r'^_PREVIOUS_VERSION = "v2\.27"$', MIGRATION.read_text(encoding="utf-8"), re.M):
        fail('QR1: the migration\'s _PREVIOUS_VERSION is not "v2.27"')


# --- fixture ---------------------------------------------------------------------

def _build(db):
    """A world with a session, two agendas, steps, pass_plays and a giver."""
    from world_engine.models import (
        Agenda, AgendaStep, Batch, Entity, PassPlay, QuestOffer, World,
    )
    from world_engine.models import Session as GameSession

    ids: dict[str, str] = {}
    world = World(name="Monde")
    db.add(world)
    db.flush()
    ids["world"] = world.id
    session = GameSession(world_id=world.id, number=1)
    db.add(session)
    char = Entity(world_id=world.id, type="character", name="Doer")
    db.add(char)
    db.flush()
    batch = Batch(session_id=session.id, day_number=1)
    db.add(batch)
    agenda = Agenda(world_id=world.id, owner_entity_id=char.id, title="Plan")
    other = Agenda(world_id=world.id, owner_entity_id=char.id, title="Autre", status="paused")
    db.add_all([agenda, other])
    db.flush()
    ids.update(char=char.id, session=session.id, agenda=agenda.id, other=other.id)
    for n in (1, 2, 3):
        step = AgendaStep(agenda_id=agenda.id, step_order=n, objective=f"o{n}")
        db.add(step)
        db.flush()
        ids[f"s{n}"] = step.id
    foreign = AgendaStep(agenda_id=other.id, step_order=1, objective="x")
    db.add(foreign)
    db.flush()
    ids["s_other"] = foreign.id
    for name, agenda_id in (("pp1", agenda.id), ("pp2", agenda.id), ("pp3", None)):
        play = PassPlay(batch_id=batch.id, session_id=session.id, character_id=char.id,
                        declared_action="agir", agenda_id=agenda_id)
        db.add(play)
        db.flush()
        ids[name] = play.id
    giver = Entity(world_id=world.id, type="character", name="Donneur",
                   created_at=datetime.now(UTC) + timedelta(hours=1))
    db.add(giver)
    db.flush()
    offer = QuestOffer(world_id=world.id, giver_entity_id=giver.id, title="Offre")
    db.add(offer)
    db.flush()
    ids["offer"] = offer.id
    db.commit()
    return ids


def _open(db, ids, trigger: str, step: str):
    from world_engine.writes.quest_requests import open_request

    return open_request(db, world_id=ids["world"], character_id=ids["char"], pass_play_id=ids["pp1"],
                        trigger=trigger, declaration="je cherche", agenda_step_id=ids[step])


def _raises(fn, kind=ValueError) -> bool:
    try:
        fn()
    except kind:
        return True
    return False


# --- QR2, QR3 ---------------------------------------------------------------------

def check_qr2_qr3(db, ids) -> None:
    from sqlmodel import select

    from world_engine.models import QuestRequest
    from world_engine.writes.quest_requests import move_request, open_request

    def call(**over):
        args = dict(world_id=ids["world"], character_id=ids["char"], pass_play_id=ids["pp1"],
                    trigger="route", declaration="je cherche", agenda_step_id=ids["s1"])
        args.update(over)
        return lambda: open_request(db, **args)

    if not _raises(call(trigger="other")):
        fail("QR2: an unknown trigger was accepted")
    if not _raises(call(declaration="   ")):
        fail("QR2: an empty declaration was accepted")
    if not _raises(call(agenda_step_id="missing")):
        fail("QR2: a missing step was accepted")
    first = open_request(db, **{"world_id": ids["world"], "character_id": ids["char"],
                                "pass_play_id": ids["pp1"], "trigger": "route", "declaration": "je cherche",
                                "agenda_step_id": ids["s1"]})
    again = open_request(db, **{"world_id": ids["world"], "character_id": ids["char"],
                                "pass_play_id": ids["pp1"], "trigger": "blocked", "declaration": "autre",
                                "agenda_step_id": ids["s1"]})
    db.commit()
    rows = db.exec(select(QuestRequest).where(QuestRequest.agenda_step_id == ids["s1"])).all()
    if again.id != first.id or len(rows) != 1 or rows[0].trigger != "route" or first.status != "new":
        fail(f"QR2: a second call for one step gave {len(rows)} row(s), same={again.id == first.id}")

    request = first
    move_request(db, request, "asking", subject="le puits")
    move_request(db, request, "writing_lore", existence_answer="absent", note="n")
    history = list(request.change_history)
    if len(history) != 2 or request.status != "writing_lore":
        fail(f"QR3: change_history has {len(history)} entries, status {request.status!r}")
    elif (history[0].get("status") != "new" or history[0].get("subject") is not None
          or history[1].get("status") != "asking" or "subject" in history[1]
          or history[1].get("existence_answer") is not None or "note" not in history[1]):
        fail(f"QR3: change_history entries are {history}")
    if not _raises(lambda: move_request(db, request, "done")):
        fail("QR3: an unknown status was accepted")
    if not _raises(lambda: move_request(db, request, "asking", colour="red")):
        fail("QR3: an unknown field was accepted")
    if not _raises(lambda: move_request(db, request, "asking", existence_answer="maybe")):
        fail("QR3: an answer outside EXISTENCE_ANSWERS was accepted")
    if len(request.change_history) != 2:
        fail("QR3: a refused move still wrote change_history")
    db.commit()


# --- QR4 -------------------------------------------------------------------------

def check_qr4(engine, ids) -> None:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    def insert(rid: str, **over) -> str:
        values = {"status": "new", "trigger": "route", "existence_answer": None, **over}
        answer = "NULL" if values["existence_answer"] is None else f"'{values['existence_answer']}'"
        return ("INSERT INTO quest_request (id, world_id, character_id, pass_play_id, agenda_step_id, "
                "\"trigger\", declaration, status, existence_answer) "
                f"VALUES ('{rid}', '{ids['world']}', '{ids['char']}', '{ids['pp1']}', '{ids['s2']}', "
                f"'{values['trigger']}', 'd', '{values['status']}', {answer})")

    def refused(sql: str) -> bool:
        with engine.connect() as conn:
            try:
                conn.execute(text(sql))
                conn.rollback()
                return False
            except IntegrityError:
                conn.rollback()
                return True

    for label, sql in (("status 'done'", insert("a", status="done")),
                       ("trigger 'other'", insert("b", trigger="other")),
                       ("answer 'maybe'", insert("c", existence_answer="maybe"))):
        if not refused(sql):
            fail(f"QR4: {label} was accepted")
    if refused(insert("ok")):
        fail("QR4: a well-formed row was refused")


# --- QR5, QR6 ----------------------------------------------------------------------

def check_qr5(db, ids) -> None:
    from world_engine.quest_requests import inquiry_step_ids

    _open(db, ids, "blocked", "s2")
    _open(db, ids, "dropped", "s3")
    _open(db, ids, "route", "s_other")
    db.commit()
    got = inquiry_step_ids(db, ids["agenda"])
    if got != frozenset({ids["s1"], ids["s3"]}):
        fail(f"QR5: inquiry steps of the agenda are {sorted(got)}")
    if inquiry_step_ids(db, ids["other"]) != frozenset({ids["s_other"]}):
        fail("QR5: the other agenda's inquiry steps are wrong")


def check_qr6(db, ids) -> None:
    from sqlmodel import select

    from world_engine.dashboard_metrics import Scope, compute_metrics
    from world_engine.models import ProposedMutation, QuestRequest
    from world_engine.writes.quest_requests import move_request

    by_step = {r.agenda_step_id: r for r in db.exec(select(QuestRequest)).all()}
    # s1 route, s2 blocked, s3 dropped; the other agenda's request leaves the fixture.
    db.delete(by_step[ids["s_other"]])
    blocked = by_step[ids["s2"]]
    move_request(db, blocked, "covered", existence_answer="already", offer_id=ids["offer"])
    proposal = ProposedMutation(
        world_id=ids["world"], source_type="pass_play", pass_play_id=ids["pp1"],
        mutation_type="quest_offer_creation", payload={}, status="applied",
        proposed_at=datetime.now(UTC),
    )
    db.add(proposal)
    db.flush()
    dropped = by_step[ids["s3"]]
    move_request(db, dropped, "proposed", mutation_id=proposal.id, offer_id=ids["offer"])
    db.commit()

    def rows(world_id: str):
        out = compute_metrics(db, Scope(world_ids=(world_id,)))
        metric = next((m for m in out if m["key"] == "quest_requests"), None)
        if metric is None:
            fail("QR6: no quest_requests metric")
            return []
        return [(r["group"], r["label"], r["value"], r["of"]) for r in metric["rows"]]

    got = rows(ids["world"])
    if got != EXPECTED_ROWS:
        fail(f"QR6: rows are {got}")
    empty = rows("no-such-world")
    if empty != [(g, label, 0, 0) for g, label, _v, _o in EXPECTED_ROWS]:
        fail(f"QR6: a world with no request gave {empty}")


# --- QR7 -------------------------------------------------------------------------

def check_qr7() -> None:
    from world_engine.dashboard_deferrals import DEFERRALS

    found = {d.code: d for d in DEFERRALS if d.ticket == "TICKET-0121"}
    for code in ("D2", "S3", "P1"):
        deferral = found.get(code)
        if deferral is None:
            fail(f"QR7: deferral {code} of TICKET-0121 is missing")
        elif deferral.metric != "quest_requests":
            fail(f"QR7: deferral {code} watches {deferral.metric!r}")


def main() -> None:
    _fresh_db()
    from sqlmodel import Session, SQLModel

    from world_engine import models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    check_qr1()
    with Session(engine) as db:
        ids = _build(db)
        check_qr2_qr3(db, ids)
        check_qr4(engine, ids)
        check_qr5(db, ids)
        check_qr6(db, ids)
    check_qr7()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: quest_requests -- v2.28 stores a request per step, its writer keeps the history, "
          "and the dashboard watches D2, S3 and P1")


if __name__ == "__main__":
    main()
