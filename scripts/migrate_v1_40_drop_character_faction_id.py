"""Migration to schema v1.40 — drop `character.faction_id` (BRIEF-28).

`character.faction_id` was deliberately retained at v1.39 (BRIEF-27) behind a
grep-gate, as a live anchor for five consumer sites. BRIEF-28 recabled all
five onto `faction_membership` (the active `is_primary=TRUE` row) and a
fresh RECON re-confirmed no sixth consumer. The data is already fully
backfilled into `faction_membership` by migrate_v1_38/v1_39 — every historical
`character.faction_id` value has a matching `is_primary=TRUE` membership row.
This migration drops the column. Data loss is nil.

Pre-check (asserted, not re-backfilled): the count of historical non-NULL
`character.faction_id` values must equal the count of `is_primary=TRUE`
`faction_membership` rows whose `(entity_id, faction_id)` pair matches one of
those historical values. If they don't match, the migration aborts — that
would mean an unbackfilled row exists, which this script does not attempt to
fix (re-run migrate_v1_39 first).

SQLite mechanics: `ALTER TABLE ... DROP COLUMN` (supported since SQLite
3.35, confirmed present here) refuses to drop a column that is still
indexed — `idx_character_faction` must be dropped first. The column's own
outbound FK (`faction_id REFERENCES entity(id)`) does not block the drop;
SQLite silently omits it from the rebuilt table definition.

Idempotent: safe to re-run — skips straight to "already dropped" if the
column is gone.

Run from the project root:
    python scripts/migrate_v1_40_drop_character_faction_id.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def _precheck(conn) -> tuple[int, int]:
    """Return (historical_non_null_faction_id_count, matching_membership_count)."""
    historical = conn.execute(text(
        "SELECT COUNT(*) FROM character WHERE faction_id IS NOT NULL"
    )).scalar_one()
    matching = conn.execute(text(
        "SELECT COUNT(*) FROM character c "
        "JOIN faction_membership fm "
        "  ON fm.entity_id = c.id AND fm.faction_id = c.faction_id AND fm.is_primary = 1 "
        "WHERE c.faction_id IS NOT NULL"
    )).scalar_one()
    return historical, matching


def _drop_column(conn) -> None:
    conn.execute(text("DROP INDEX IF EXISTS idx_character_faction"))
    conn.execute(text("ALTER TABLE character DROP COLUMN faction_id"))


def main() -> None:
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("character")}

    if "faction_id" not in columns:
        print("Column 'character.faction_id' already absent — skipping.")
        return

    with engine.begin() as conn:
        historical, matching = _precheck(conn)
        if historical != matching:
            raise SystemExit(
                f"Pre-check failed: {historical} character row(s) with non-NULL "
                f"faction_id, but only {matching} have a matching is_primary "
                "faction_membership row. Run migrate_v1_39_faction_membership.py "
                "first — aborting, no column dropped."
            )
        print(f"Pre-check OK: {historical} historical faction_id value(s), all backfilled.")

    with engine.begin() as conn:
        _drop_column(conn)

    print("Migration v1.40 applied: character.faction_id column and idx_character_faction index dropped.")


if __name__ == "__main__":
    main()
