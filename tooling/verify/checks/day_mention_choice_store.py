"""G1 check for TICKET-0094 (BRIEF-0094-A) — the H2 choice record (C-01,
C-02): `write_day_mention_choices` validates every record before it builds
one row, and the database agrees with the writer.

S1 -- a valid `accepted` record and a valid `failed` record write two rows;
   after commit, `candidate_ids` round-trips through `json.loads`.
S2 -- each invalid record raises `ValueError` and adds nothing (`db.new`
   empty): unknown category, unknown trigger, unknown verdict, `attempts=3`,
   `accepted` without a chosen id, `declined` with one, `candidate_ids` not
   a list.
S3 -- a batch mixing one valid and one invalid record adds nothing.
S4 -- `records=[]` returns `[]`.
S5 -- the raw SQL of C-01 refuses an `accepted` row with a NULL
   `chosen_entity_id` (the DB CHECK agrees with the writer).

Fixtures run on a fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import — never
Nia's DB). Vacuity guard: S1 must have read back two rows. FAILURES list,
print FAIL lines, exit 1.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _world(session, label: str):
    from world_engine.models import Entity, World

    world = World(name=label, is_active=False)
    session.add(world)
    session.flush()

    def entity(kind: str, name: str):
        row = Entity(world_id=world.id, type=kind, name=name)
        session.add(row)
        session.flush()
        return row

    return world, entity


def _parents(db):
    """World -> session -> batch -> character entity -> pass_play, each
    flushed before its children (FK enforcement is on)."""
    from world_engine import models, writes

    world, entity = _world(db, "day_mention_choice_store")
    game_session = models.Session(world_id=world.id, number=1)
    db.add(game_session)
    db.flush()
    batch = writes.write_batch(db, session_id=game_session.id, changed_by="creator")
    db.add(batch)
    db.flush()
    pc = entity("character", "Aldric")
    maelis = entity("character", "Maelis")
    pass_play = writes.write_pass_play(
        db, batch_id=batch.id, session_id=game_session.id, character_id=pc.id,
        declared_action="Je vais voir Maelis.",
    )
    db.add(pass_play)
    db.flush()
    return world, pass_play, maelis


def _record(**overrides) -> dict:
    record = {
        "category": "person", "surface_form": "Maelys", "trigger": "near",
        "candidate_ids": [], "evidence_fact_ids": [], "verdict": "failed",
        "chosen_entity_id": None, "excerpt": None, "reason": None,
        "verdict_detail": "ollama error", "attempts": 2,
    }
    record.update(overrides)
    return record


def check_store(engine) -> int:
    from sqlmodel import Session, select

    from world_engine.models import DayMentionChoice
    from world_engine.writes import write_day_mention_choices

    read_back = 0
    with Session(engine) as db:
        world, pass_play, maelis = _parents(db)
        db.commit()
        world_id, pass_play_id, maelis_id = world.id, pass_play.id, maelis.id

    def write(db, records):
        return write_day_mention_choices(db, world_id=world_id, pass_play_id=pass_play_id, records=records)

    # S1
    accepted = _record(
        verdict="accepted", chosen_entity_id=maelis_id, candidate_ids=[maelis_id, "autre"],
        excerpt="Maelis", reason="typo", verdict_detail=None, attempts=1,
    )
    with Session(engine) as db:
        rows = write(db, [accepted, _record()])
        if len(rows) != 2:
            fail(f"S1: expected 2 rows returned, got {len(rows)}")
        db.commit()
    with Session(engine) as db:
        stored = db.exec(select(DayMentionChoice).where(DayMentionChoice.pass_play_id == pass_play_id)).all()
        read_back = len(stored)
        if read_back != 2:
            fail(f"S1: expected 2 stored rows, got {read_back}")
        by_verdict = {row.verdict: row for row in stored}
        row = by_verdict.get("accepted")
        if row is None or json.loads(row.candidate_ids) != [maelis_id, "autre"]:
            fail(f"S1: accepted row candidate_ids did not round-trip: {row and row.candidate_ids!r}")
        if "failed" not in by_verdict or by_verdict["failed"].chosen_entity_id is not None:
            fail("S1: failed row missing or carrying a chosen id")

    # S2
    invalid = {
        "unknown category": _record(category="item"),
        "unknown trigger": _record(trigger="cast"),
        "unknown verdict": _record(verdict="ambiguous"),
        "attempts=3": _record(attempts=3),
        "accepted without chosen id": _record(verdict="accepted", chosen_entity_id=None),
        "declined with chosen id": _record(verdict="declined", chosen_entity_id=maelis_id),
        "candidate_ids not a list": _record(candidate_ids=maelis_id),
    }
    for label, record in invalid.items():
        with Session(engine) as db:
            try:
                write(db, [record])
            except ValueError:
                pass
            else:
                fail(f"S2: {label} did not raise ValueError")
            if db.new:
                fail(f"S2: {label} added {len(db.new)} object(s)")

    # S3
    with Session(engine) as db:
        try:
            write(db, [_record(), _record(attempts=3)])
        except ValueError:
            pass
        else:
            fail("S3: a mixed batch did not raise ValueError")
        if db.new:
            fail(f"S3: a mixed batch added {len(db.new)} object(s)")

    # S4
    with Session(engine) as db:
        result = write(db, [])
        if result != [] or db.new:
            fail(f"S4: empty records returned {result!r} / added {len(db.new)}")

    # S5
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    with engine.connect() as conn:
        try:
            conn.execute(text(
                "INSERT INTO day_mention_choice (id, world_id, pass_play_id, category, surface_form, "
                "trigger, candidate_ids, evidence_fact_ids, verdict, chosen_entity_id, attempts) "
                "VALUES ('s5', :w, :p, 'person', 'Maelys', 'near', '[]', '[]', 'accepted', NULL, 1)"
            ), {"w": world_id, "p": pass_play_id})
        except IntegrityError:
            pass
        else:
            fail("S5: the DB accepted an 'accepted' row with a NULL chosen_entity_id")
        conn.rollback()

    return read_back


def main() -> int:
    engine = _fresh_engine()
    read_back = check_store(engine)
    if read_back == 0:
        fail("vacuity: S1 read back zero rows")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: day_mention_choice_store — valid records round-trip, every invalid record "
        "or mixed batch adds nothing, an empty batch is a no-op, and the DB CHECK agrees "
        "with the writer (S1-S5)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
