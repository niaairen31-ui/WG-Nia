"""Runtime G1 check for TICKET-0037 (BRIEF-0037-e) — the shared retention
purge helper `_purge_closed_batches` must delete row-children BEFORE their
parent batch, under real SQLite FK enforcement (`PRAGMA foreign_keys=ON`,
`db.py`'s connect listener).

Root cause this guards against: the batch/row models carry only a
column-level `foreign_key=` (no ORM `relationship()`), so the SQLAlchemy
unit-of-work gives no child-before-parent delete ordering on per-object
`db.delete(...)` — an autoflush can emit the parent DELETE first, which
SQLite rejects. `tooling/verify/checks/npc_batch_purge.py` is AST-only and
cannot see this: it never executes the purge. This check does, against a
real FK-enforcing DB with >2 closed batches of BOTH agents (link + npc)
present — the exact condition that crashed the live app.

Fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL set before any
world_engine import) — the real DB is never touched.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    """Point WORLD_ENGINE_DATABASE_URL at a fresh temp SQLite file BEFORE
    importing world_engine.db (module-level engine) — isolates this check
    from the real DB and from any other check already imported in-process."""
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _seed_world_and_entity(session, world_name: str):
    from world_engine.models import Entity, World

    world = World(name=world_name, is_active=False)
    session.add(world)
    session.commit()
    session.refresh(world)

    entity = Entity(world_id=world.id, type="character", name="Anchor")
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return world, entity


def _check_pair(engine, batch_model, row_model, row_fk_attr, make_row_kwargs) -> None:
    """One (batch_model, row_model) pair: 3 closed batches (ascending
    closed_at) each with >=1 row-child, plus 1 open batch with a
    row-child. Asserts `_purge_closed_batches` does not raise, exactly the
    2 latest-closed batches survive, the purged batch's row-children are
    gone, the retained batches' and the open batch's row-children remain."""
    from sqlmodel import Session as DbSession, select

    from world_engine.cockpit.app import _purge_closed_batches

    with DbSession(engine) as session:
        world, entity = _seed_world_and_entity(session, f"Check-{batch_model.__tablename__}")

        base_time = datetime.now(UTC) - timedelta(days=10)
        batch_ids = []
        for i in range(3):
            batch = batch_model(
                world_id=world.id, status="committed",
                closed_at=base_time + timedelta(days=i), scope={},
            )
            session.add(batch)
            session.commit()
            session.refresh(batch)
            batch_ids.append(batch.id)  # snapshot the id string — objects expire post-commit
            session.add(row_model(batch_id=batch.id, **make_row_kwargs(entity)))
            session.commit()

        oldest_id, middle_id, newest_id = batch_ids  # ascending closed_at

        open_batch = batch_model(world_id=world.id, status="open", scope={})
        session.add(open_batch)
        session.commit()
        session.refresh(open_batch)
        open_batch_id = open_batch.id
        session.add(row_model(batch_id=open_batch_id, **make_row_kwargs(entity)))
        session.commit()

        try:
            _purge_closed_batches(session, batch_model, row_model, row_fk_attr)
        except Exception as exc:  # noqa: BLE001 — the exact regression is an exception
            fail(f"{batch_model.__tablename__}: _purge_closed_batches raised {exc!r}")
            return

    with DbSession(engine) as session:
        surviving_ids = {b.id for b in session.exec(select(batch_model)).all()}
        expected_kept = {middle_id, newest_id, open_batch_id}
        if surviving_ids != expected_kept:
            fail(
                f"{batch_model.__tablename__}: expected surviving batches "
                f"{expected_kept}, got {surviving_ids}"
            )

        for label, batch_id in (("middle", middle_id), ("newest", newest_id)):
            rows = session.exec(
                select(row_model).where(getattr(row_model, row_fk_attr) == batch_id)
            ).all()
            if not rows:
                fail(f"{batch_model.__tablename__}: {label} retained batch lost its row-children")

        purged_rows = session.exec(
            select(row_model).where(getattr(row_model, row_fk_attr) == oldest_id)
        ).all()
        if purged_rows:
            fail(f"{batch_model.__tablename__}: purged batch's row-children were NOT deleted")

        open_rows = session.exec(
            select(row_model).where(getattr(row_model, row_fk_attr) == open_batch_id)
        ).all()
        if not open_rows:
            fail(f"{batch_model.__tablename__}: open batch's row-child was deleted")


def main() -> int:
    engine = _fresh_engine()
    from world_engine.models import LinkBatch, LinkBatchRow, NpcBatch, NpcBatchRow

    _check_pair(
        engine, LinkBatch, LinkBatchRow, "batch_id",
        lambda entity: dict(pair_a_id=entity.id, pair_b_id=entity.id, kind="no_links", payload={}),
    )
    _check_pair(
        engine, NpcBatch, NpcBatchRow, "batch_id",
        lambda entity: dict(line_index=0, kind="draft", payload={}),
    )

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: purge_fk_ordering — _purge_closed_batches deletes row-children "
        "before their batch under real FK enforcement, for both link and npc batches"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
