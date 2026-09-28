"""G1 check for TICKET-0095 (BRIEF-0095-A) — the K1 review record (C-01,
C-02, C-03): a choice's candidates and evidence become rows, and every
review is kept.

V1 -- `write_day_mention_choices` writes one candidate row per candidate id
   and one evidence row per evidence fact id, ordinals from 1 in the lists'
   order; the JSON audit copy is still written.
V2 -- an invalid record raises `ValueError` and adds nothing (`db.new`
   empty).
V3 -- `records=[]` returns `[]` and adds nothing.
V4 -- `write_day_mention_review` writes three valid reviews on one choice
   (`choice_id` is not unique); each invalid shape raises `ValueError`
   whose message starts `write_day_mention_review: ` and adds nothing.
V5 -- the raw SQL of C-01 refuses an `agreed` review with a NULL
   `entity_id`, and a candidate row with `ordinal = 0` (the DB CHECKs agree
   with the writers).
V6 -- an evidence row and a review's `appellation_fact_id` citing a fact do
   not block that fact's hard delete (no FK, R-04); both rows survive it.
V7 -- `writes.pipeline._REVIEW_SCOPES` equals
   `writes.facets._APPELLATION_SCOPES`.

Fixtures run on a fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import — never
Nia's DB). Vacuity guard: V1 must have read back three candidate rows.
FAILURES list, print FAIL lines, exit 1.
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

    world, entity = _world(db, "day_mention_review_store")
    game_session = models.Session(world_id=world.id, number=1)
    db.add(game_session)
    db.flush()
    batch = writes.write_batch(db, session_id=game_session.id, changed_by="creator")
    db.add(batch)
    db.flush()
    pc = entity("character", "Aldric")
    maelis = entity("character", "Maelis")
    orn = entity("character", "Orn")
    pass_play = writes.write_pass_play(
        db, batch_id=batch.id, session_id=game_session.id, character_id=pc.id,
        declared_action="Je vais voir Maelis.",
    )
    db.add(pass_play)
    db.flush()
    return world, pass_play, maelis, orn


def _record(**overrides) -> dict:
    record = {
        "category": "person", "surface_form": "Maelys", "trigger": "near",
        "candidate_ids": [], "evidence_fact_ids": [], "verdict": "failed",
        "chosen_entity_id": None, "excerpt": None, "reason": None,
        "verdict_detail": "ollama error", "attempts": 2,
    }
    record.update(overrides)
    return record


def _ordered(db, model, choice_id: str, column: str) -> list[tuple]:
    from sqlmodel import select

    rows = db.exec(select(model).where(model.choice_id == choice_id).order_by(model.ordinal)).all()
    return [(row.ordinal, getattr(row, column)) for row in rows]


def check_store(engine) -> int:
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlmodel import Session, select

    from world_engine.models import (
        DayMentionChoice,
        DayMentionChoiceCandidate,
        DayMentionChoiceEvidence,
        DayMentionReview,
    )
    from world_engine.writes import (
        add_entity_fact,
        remove_entity_fact,
        write_day_mention_choices,
        write_day_mention_review,
    )

    with Session(engine) as db:
        world, pass_play, maelis, orn = _parents(db)
        fact = add_entity_fact(
            db, entity_id=maelis.id, facet="histoire", content="Elle tient la forge.", created_by="creator",
        )
        db.commit()
        world_id, pass_play_id = world.id, pass_play.id
        maelis_id, orn_id, fact_id = maelis.id, orn.id, fact.id

    def write(db, records):
        return write_day_mention_choices(db, world_id=world_id, pass_play_id=pass_play_id, records=records)

    def review(db, choice_id, verdict, entity_id, appellation_fact_id, appellation_scope):
        return write_day_mention_review(
            db, world_id=world_id, choice_id=choice_id, verdict=verdict, entity_id=entity_id,
            appellation_fact_id=appellation_fact_id, appellation_scope=appellation_scope,
        )

    # V1
    r1 = _record(
        verdict="accepted", chosen_entity_id=maelis_id, candidate_ids=[maelis_id, orn_id],
        evidence_fact_ids=["fact-gone"], excerpt="Maelis", reason="typo", verdict_detail=None, attempts=1,
    )
    r2 = _record(candidate_ids=[orn_id])
    with Session(engine) as db:
        rows = write(db, [r1, r2])
        db.commit()
        r1_id, r2_id = rows[0].id, rows[1].id
    candidate_read_back = 0
    with Session(engine) as db:
        cand1 = _ordered(db, DayMentionChoiceCandidate, r1_id, "entity_id")
        cand2 = _ordered(db, DayMentionChoiceCandidate, r2_id, "entity_id")
        candidate_read_back = len(cand1) + len(cand2)
        if cand1 != [(1, maelis_id), (2, orn_id)]:
            fail(f"V1: r1 candidate rows {cand1!r}")
        if cand2 != [(1, orn_id)]:
            fail(f"V1: r2 candidate rows {cand2!r}")
        ev1 = _ordered(db, DayMentionChoiceEvidence, r1_id, "fact_id")
        ev2 = _ordered(db, DayMentionChoiceEvidence, r2_id, "fact_id")
        if ev1 != [(1, "fact-gone")]:
            fail(f"V1: r1 evidence rows {ev1!r}")
        if ev2 != []:
            fail(f"V1: r2 evidence rows {ev2!r}")
        parent = db.get(DayMentionChoice, r1_id)
        if parent is None or json.loads(parent.candidate_ids) != [maelis_id, orn_id]:
            fail(f"V1: the JSON audit copy was not written: {parent and parent.candidate_ids!r}")

    # V2
    with Session(engine) as db:
        try:
            write(db, [_record(verdict="ambiguous")])
        except ValueError:
            pass
        else:
            fail("V2: verdict='ambiguous' did not raise ValueError")
        if db.new:
            fail(f"V2: an invalid record added {len(db.new)} object(s)")

    # V3
    with Session(engine) as db:
        result = write(db, [])
        if result != [] or db.new:
            fail(f"V3: empty records returned {result!r} / added {len(db.new)}")

    # V4
    with Session(engine) as db:
        review(db, r1_id, "agreed", maelis_id, None, None)
        review(db, r1_id, "disagreed", None, None, None)
        review(db, r1_id, "agreed", maelis_id, "f-1", "world")
        db.commit()
    with Session(engine) as db:
        stored = db.exec(select(DayMentionReview).where(DayMentionReview.choice_id == r1_id)).all()
        if len(stored) != 3:
            fail(f"V4: expected 3 review rows on one choice, got {len(stored)}")
    invalid = {
        "verdict 'maybe'": ("maybe", maelis_id, None, None),
        "agreed without entity": ("agreed", None, None, None),
        "appellation without entity": ("disagreed", None, "f", "rencontre"),
        "fact without scope": ("agreed", maelis_id, "f", None),
        "scope without fact": ("agreed", maelis_id, None, "world"),
        "unknown scope": ("agreed", maelis_id, "f", "public"),
    }
    for label, args in invalid.items():
        with Session(engine) as db:
            try:
                review(db, r1_id, *args)
            except ValueError as exc:
                if not str(exc).startswith("write_day_mention_review: "):
                    fail(f"V4: {label} raised with message {str(exc)!r}")
            else:
                fail(f"V4: {label} did not raise ValueError")
            if db.new:
                fail(f"V4: {label} added {len(db.new)} object(s)")

    # V5
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "INSERT INTO day_mention_review (id, world_id, choice_id, verdict, entity_id) "
                "VALUES ('v5', :w, :c, 'agreed', NULL)"
            ), {"w": world_id, "c": r1_id})
        except IntegrityError:
            pass
        else:
            fail("V5: the DB accepted an 'agreed' review with a NULL entity_id")
        conn.rollback()
        try:
            conn.execute(text(
                "INSERT INTO day_mention_choice_candidate (id, choice_id, ordinal, entity_id) "
                "VALUES ('v5c', :c, 0, :e)"
            ), {"c": r1_id, "e": maelis_id})
        except IntegrityError:
            pass
        else:
            fail("V5: the DB accepted a candidate row with ordinal 0")
        conn.rollback()

    # V6
    with Session(engine) as db:
        rows = write(db, [_record(
            verdict="accepted", chosen_entity_id=maelis_id, candidate_ids=[maelis_id],
            evidence_fact_ids=[fact_id], excerpt="Maelis", reason="forge", verdict_detail=None, attempts=1,
        )])
        v6_choice_id = rows[0].id
        v6_review = review(db, v6_choice_id, "agreed", maelis_id, fact_id, "none")
        db.commit()
        v6_review_id = v6_review.id
    with Session(engine) as db:
        try:
            remove_entity_fact(db, fact_id=fact_id)
            db.commit()
        except Exception as exc:  # noqa: BLE001 — any failure here is the finding
            fail(f"V6: deleting a cited fact failed: {type(exc).__name__}: {exc}")
    with Session(engine) as db:
        if _ordered(db, DayMentionChoiceEvidence, v6_choice_id, "fact_id") != [(1, fact_id)]:
            fail("V6: the evidence row did not survive the fact's delete")
        if db.get(DayMentionReview, v6_review_id) is None:
            fail("V6: the review row did not survive the fact's delete")

    # V7
    from world_engine.writes import facets as writes_facets
    from world_engine.writes import pipeline as writes_pipeline

    if writes_pipeline._REVIEW_SCOPES != writes_facets._APPELLATION_SCOPES:
        fail(
            f"V7: _REVIEW_SCOPES {writes_pipeline._REVIEW_SCOPES!r} != "
            f"_APPELLATION_SCOPES {writes_facets._APPELLATION_SCOPES!r}"
        )

    return candidate_read_back


def main() -> int:
    engine = _fresh_engine()
    read_back = check_store(engine)
    if read_back != 3:
        fail(f"vacuity: V1 read back {read_back} candidate row(s), expected 3")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: day_mention_review_store — candidates and evidence are written as ordered rows beside "
        "the JSON audit copy, invalid or empty batches add nothing, every valid review is kept and "
        "every invalid one refused, the DB CHECKs agree, a cited fact stays deletable, and the review "
        "scopes equal the appellation scopes (V1-V7)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
