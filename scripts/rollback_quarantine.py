"""Rollback quarantine / restore for runtime entity types (B1) —
TICKET-0044, BRIEF-0044-e. Manual, deliberate, like `backup.py`.
danger_class: destructive_data.

Rollback contract (verbatim, also in CLAUDE.md and ARCHITECTURE_DECISIONS.md):

    Once a runtime type exists, rolling code back past the constructor
    version requires running scripts/rollback_quarantine.py first (after a
    backup). Roll-forward restoration (--restore) is potentially lossy,
    bounded to rows whose entity row was deleted during the rollback
    window; every lost row is preserved in _orphan_lost_* and reported —
    never silently dropped. This contract is SQLite-scoped (the
    rebuild-without-FK recipe is SQLite-specific), matching the engine's
    current single-backend reality.

Quarantine (default): for each `active`/`retired` entity_type, rebuild its
`ext_*` table under `_orphan_ext_*` WITHOUT the entity FK (and without any
other `REFERENCES entity(id)` FK — kept as plain TEXT), copy every row
across, drop the original, flip `entity_type.status` to `quarantined`, and
append a `type_quarantined` history row. Idempotent: a type whose
`_orphan_` table already exists is skipped.

Restore (--restore): for each `quarantined` entity_type, rebuild `ext_*`
WITH the FK restored. A row whose `entity` still exists is re-attached; a
row whose `entity` was deleted during the quarantine window is parked in
`_orphan_lost_ext_*` instead (created on demand) and counted — never
dropped. The `_orphan_` table is only dropped once every row is either
re-attached or parked. Flips `entity_type.status` back to `active` and
appends a `type_restored` history row recording `lost_count`.

Usage:
    python scripts/rollback_quarantine.py            # quarantine
    python scripts/rollback_quarantine.py --restore   # roll-forward restore
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import EntityType, EntityTypeHistory  # noqa: E402
from world_engine.writes.schema import (  # noqa: E402
    _COLUMN_TYPES,
    _build_create_table_ddl,
    EXT_PREFIX,
)

ORPHAN_PREFIX = "_orphan_" + EXT_PREFIX
LOST_PREFIX = "_orphan_lost_" + EXT_PREFIX
_FK_TYPES = ("FK_ENTITY", "FK_ENTITY_NULLABLE")


def _table_columns_from_creation(session: Session, entity_type_id: str) -> list[tuple[str, str]]:
    """The manifest is `entity_type`; the exact original DDL shape lives in
    its `type_created` history row — never re-derived or guessed."""
    row = session.exec(
        select(EntityTypeHistory)
        .where(EntityTypeHistory.entity_type_id == entity_type_id)
        .where(EntityTypeHistory.event == "type_created")
        .order_by(EntityTypeHistory.created_at)
    ).first()
    if row is None:
        raise RuntimeError(f"no type_created history for entity_type_id={entity_type_id!r}")
    return [tuple(c) for c in row.definition_snapshot["columns"]]


def _orphan_column_fragment(col_name: str, col_type: str) -> str:
    """Same Dcol1 enum as the writer, except an entity FK is downgraded to
    plain TEXT — the whole point of quarantine (`PRAGMA foreign_keys=ON`
    otherwise blocks an old-code `entity` delete)."""
    if col_type in _FK_TYPES:
        return f"{col_name} TEXT"
    return f"{col_name} {_COLUMN_TYPES[col_type].format(col=col_name)}"


def _build_orphan_ddl(table_name: str, columns: list[tuple[str, str]]) -> str:
    lines = ["id TEXT PRIMARY KEY"]
    lines.extend(_orphan_column_fragment(c, t) for c, t in columns)
    body = ",\n    ".join(lines)
    return f"CREATE TABLE {table_name} (\n    {body}\n)"


def quarantine_one(session: Session, et: EntityType) -> bool:
    """Quarantine one entity_type's physical table. Returns False (skip)
    if it is already quarantined."""
    orphan_table = ORPHAN_PREFIX + et.slug
    if inspect(session.get_bind()).has_table(orphan_table):
        print(f"skip {et.slug}: already quarantined ({orphan_table} present)")
        return False

    columns = _table_columns_from_creation(session, et.id)
    ddl = _build_orphan_ddl(orphan_table, columns)
    session.execute(text(ddl))

    col_names = ["id"] + [c for c, _ in columns]
    cols_csv = ", ".join(col_names)
    session.execute(text(f"INSERT INTO {orphan_table} ({cols_csv}) SELECT {cols_csv} FROM {et.physical_table}"))
    session.execute(text(f"DROP TABLE {et.physical_table}"))

    et.status = "quarantined"
    session.add(et)
    session.add(EntityTypeHistory(
        world_id=et.world_id,
        entity_type_id=et.id,
        event="type_quarantined",
        definition_snapshot={"columns": columns, "orphan_table": orphan_table},
        physical_table=et.physical_table,
        ddl_text=ddl,
        changed_by="rollback_quarantine.py",
    ))
    session.commit()
    print(f"quarantined {et.slug}: {et.physical_table} -> {orphan_table}")
    return True


def restore_one(session: Session, et: EntityType) -> tuple[bool, int, int]:
    """Restore one quarantined entity_type. Returns
    (restored, reattached_count, lost_count)."""
    orphan_table = ORPHAN_PREFIX + et.slug
    bind = session.get_bind()
    if not inspect(bind).has_table(orphan_table):
        print(f"skip {et.slug}: not quarantined (no {orphan_table})")
        return False, 0, 0

    columns = _table_columns_from_creation(session, et.id)
    ddl = _build_create_table_ddl(et.physical_table, columns)
    session.execute(text(ddl))

    col_names = ["id"] + [c for c, _ in columns]
    cols_csv = ", ".join(col_names)
    rows = session.execute(text(f"SELECT {cols_csv} FROM {orphan_table}")).fetchall()

    reattached = 0
    lost_rows = []
    for row in rows:
        exists = session.execute(
            text("SELECT 1 FROM entity WHERE id = :id"), {"id": row[0]}
        ).fetchone() is not None
        if exists:
            placeholders = ", ".join(f":{c}" for c in col_names)
            session.execute(
                text(f"INSERT INTO {et.physical_table} ({cols_csv}) VALUES ({placeholders})"),
                dict(zip(col_names, row)),
            )
            reattached += 1
        else:
            lost_rows.append(row)

    lost_count = len(lost_rows)
    lost_table = LOST_PREFIX + et.slug
    if lost_rows:
        if not inspect(bind).has_table(lost_table):
            session.execute(text(_build_orphan_ddl(lost_table, columns)))
        placeholders = ", ".join(f":{c}" for c in col_names)
        for row in lost_rows:
            session.execute(
                text(f"INSERT INTO {lost_table} ({cols_csv}) VALUES ({placeholders})"),
                dict(zip(col_names, row)),
            )

    session.execute(text(f"DROP TABLE {orphan_table}"))
    et.status = "active"
    session.add(et)
    session.add(EntityTypeHistory(
        world_id=et.world_id,
        entity_type_id=et.id,
        event="type_restored",
        definition_snapshot={
            "columns": columns,
            "reattached": reattached,
            "lost_count": lost_count,
            "lost_table": lost_table if lost_rows else None,
        },
        physical_table=et.physical_table,
        ddl_text=ddl,
        changed_by="rollback_quarantine.py",
    ))
    session.commit()
    summary = f", {lost_count} parked in {lost_table}" if lost_rows else ", 0 lost"
    print(f"restored {et.slug}: {reattached} re-attached{summary}")
    return True, reattached, lost_count


def quarantine_all(session: Session) -> None:
    types = session.exec(select(EntityType).where(EntityType.status.in_(("active", "retired")))).all()
    for et in types:
        try:
            quarantine_one(session, et)
        except Exception as exc:  # noqa: BLE001 — report and move on, never abort the batch
            session.rollback()
            print(f"FAILED quarantining {et.slug}: {exc}")


def restore_all(session: Session) -> None:
    types = session.exec(select(EntityType).where(EntityType.status == "quarantined")).all()
    for et in types:
        try:
            restore_one(session, et)
        except Exception as exc:  # noqa: BLE001 — report and move on, never abort the batch
            session.rollback()
            print(f"FAILED restoring {et.slug}: {exc}")


def _has_backup() -> bool:
    backup_dir = Path(os.environ.get("WORLD_ENGINE_BACKUP_DIR", str(Path.home() / ".world_engine" / "backups")))
    return any(backup_dir.glob("world_engine_*.db"))


def main() -> None:
    restore_mode = "--restore" in sys.argv[1:]
    if not _has_backup():
        raise SystemExit(
            "No backup found — this script rewrites/drops runtime `ext_*` tables "
            "(danger_class: destructive_data). Run `python scripts/backup.py` first."
        )
    with Session(engine) as session:
        if restore_mode:
            restore_all(session)
        else:
            quarantine_all(session)


if __name__ == "__main__":
    main()
