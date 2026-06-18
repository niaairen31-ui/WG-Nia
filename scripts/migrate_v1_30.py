"""Migration v1.30 — add signpost_group to discoverable_detail.

File jumps v1_26 -> v1_30: the intervening schema versions (v1.27 UI shell,
v1.28 connects_to, v1.29 travel) required no DDL. The version marker lives
only in docs and commits -- there is no schema_version table in the DB.

Adds the `signpost_group TEXT` column (nullable; NULL = the row belongs to
no signpost cluster) to `discoverable_detail`, plus an index. Both the
`ambient` panel row and its grouped `hidden` content rows carry the SAME
`signpost_group` value to express the cluster (BRIEF-17).

Safe to run on any database created before this step -- it checks for the
column first and is a no-op if it already exists.

Run from the project root:

    python scripts/migrate_v1_30.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402


def main() -> None:
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("discoverable_detail")}

    if "signpost_group" in cols:
        print("Column 'signpost_group' already exists in 'discoverable_detail' — nothing to do.")
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE discoverable_detail ADD COLUMN signpost_group TEXT"))
        conn.execute(text(
            "CREATE INDEX idx_discoverable_signpost_group "
            "ON discoverable_detail(signpost_group)"
        ))

    print("Added column 'discoverable_detail.signpost_group' (TEXT, nullable) and its index.")


if __name__ == "__main__":
    main()
