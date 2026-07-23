"""B1 reader/proof for rollback_quarantine.py (TICKET-0044, BRIEF-0044-e).

Against a scratch DB (never the real world-engine database, mirroring
test_ddl_atomicity.py's pattern):

- build a throwaway runtime type `qtest` (`ext_qtest`, one BOOLEAN column)
  via `create_entity_type`;
- insert 2 matching `entity` rows + 2 `ext_qtest` rows;
- quarantine -> assert `_orphan_ext_qtest` exists WITHOUT the entity FK,
  `ext_qtest` is gone, both rows survive, `entity_type.status` is
  `quarantined`, a `type_quarantined` history row exists, and
  `schema_reconcile.unaccounted_tables` reports nothing (orphan
  pattern-accounted);
- delete ONE of the two `entity` rows (simulating an old-code delete
  during the quarantine window);
- restore -> assert the surviving row is re-attached into a rebuilt
  `ext_qtest` WITH the FK, the orphaned-of-entity row is parked in
  `_orphan_lost_ext_qtest` (not dropped), the reported `lost_count` is 1,
  a `type_restored` history row records it, and status is back to
  `active`.

No model call.

    python scripts/test_rollback_quarantine.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_SCRATCH_DB = Path(tempfile.gettempdir()) / "world_engine_rollback_quarantine_scratch.db"
if _SCRATCH_DB.exists():
    _SCRATCH_DB.unlink()
os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{_SCRATCH_DB}"

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from world_engine import schema_reconcile  # noqa: E402
from world_engine.db import create_db_and_tables, engine  # noqa: E402
from world_engine.models import Entity, EntityType, EntityTypeHistory, World  # noqa: E402
from world_engine.writes.schema import create_entity_type  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rollback_quarantine as rq  # noqa: E402


def main() -> None:
    results: list[tuple[bool, str]] = []
    create_db_and_tables()

    with Session(engine) as session:
        world = World(name="B1 scratch world")
        session.add(world)
        session.commit()
        session.refresh(world)

        e1 = Entity(world_id=world.id, type="test", name="qtest-1")
        e2 = Entity(world_id=world.id, type="test", name="qtest-2")
        session.add(e1)
        session.add(e2)
        session.commit()

        entity_type_id = create_entity_type(
            session,
            world_id=world.id,
            name="QTest",
            slug="qtest",
            columns=[("flag", "BOOLEAN")],
            changed_by="test_rollback_quarantine.py",
        )
        session.commit()

        session.execute(
            text("INSERT INTO ext_qtest (id, flag) VALUES (:id, 1)"),
            {"id": e1.id},
        )
        session.execute(
            text("INSERT INTO ext_qtest (id, flag) VALUES (:id, 0)"),
            {"id": e2.id},
        )
        session.commit()

        # ── Quarantine ───────────────────────────────────────────────────
        et = session.get(EntityType, entity_type_id)
        rq.quarantine_one(session, et)

        bind = session.get_bind()
        results.append((inspect(bind).has_table("_orphan_ext_qtest"), "_orphan_ext_qtest created"))
        results.append((not inspect(bind).has_table("ext_qtest"), "ext_qtest dropped"))
        results.append((
            not inspect(bind).get_foreign_keys("_orphan_ext_qtest"),
            "_orphan_ext_qtest carries no FK",
        ))
        orphan_rows = session.execute(
            text("SELECT count(*) FROM _orphan_ext_qtest")
        ).scalar()
        results.append((orphan_rows == 2, f"both rows preserved in orphan table (found {orphan_rows})"))

        session.refresh(et)
        results.append((et.status == "quarantined", f"entity_type.status == 'quarantined' (got {et.status!r})"))

        quarantined_hist = session.exec(
            select(EntityTypeHistory)
            .where(EntityTypeHistory.entity_type_id == entity_type_id)
            .where(EntityTypeHistory.event == "type_quarantined")
        ).first()
        results.append((quarantined_hist is not None, "type_quarantined history row present"))

        unaccounted = schema_reconcile.unaccounted_tables(engine, session)
        results.append((unaccounted == [], f"reconciliation clean during quarantine (found {unaccounted})"))

        # ── Simulate an old-code delete of one entity during the window ───
        session.delete(session.get(Entity, e2.id))
        session.commit()

        # ── Restore ─────────────────────────────────────────────────────
        session.refresh(et)
        restored, reattached, lost_count = rq.restore_one(session, et)

        results.append((inspect(bind).has_table("ext_qtest"), "ext_qtest rebuilt"))
        results.append((
            any(fk["referred_table"] == "entity" for fk in inspect(bind).get_foreign_keys("ext_qtest")),
            "rebuilt ext_qtest carries the entity FK",
        ))
        results.append((not inspect(bind).has_table("_orphan_ext_qtest"), "_orphan_ext_qtest dropped after restore"))
        results.append((inspect(bind).has_table("_orphan_lost_ext_qtest"), "_orphan_lost_ext_qtest created"))
        results.append((reattached == 1, f"exactly 1 row re-attached (got {reattached})"))
        results.append((lost_count == 1, f"lost_count == 1 (got {lost_count})"))

        surviving = session.execute(
            text("SELECT count(*) FROM ext_qtest WHERE id = :id"), {"id": e1.id}
        ).scalar()
        results.append((surviving == 1, "surviving row present in rebuilt ext_qtest"))

        lost = session.execute(
            text("SELECT count(*) FROM _orphan_lost_ext_qtest WHERE id = :id"), {"id": e2.id}
        ).scalar()
        results.append((lost == 1, "deleted-entity row parked in _orphan_lost_ext_qtest, not dropped"))

        session.refresh(et)
        results.append((et.status == "active", f"entity_type.status back to 'active' (got {et.status!r})"))

        restored_hist = session.exec(
            select(EntityTypeHistory)
            .where(EntityTypeHistory.entity_type_id == entity_type_id)
            .where(EntityTypeHistory.event == "type_restored")
        ).first()
        results.append((restored_hist is not None, "type_restored history row present"))
        results.append((
            restored_hist is not None and restored_hist.definition_snapshot.get("lost_count") == 1,
            "type_restored history records lost_count == 1",
        ))

    for ok, label in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

    passed = sum(1 for ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed.")

    engine.dispose()
    if _SCRATCH_DB.exists():
        _SCRATCH_DB.unlink()

    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
