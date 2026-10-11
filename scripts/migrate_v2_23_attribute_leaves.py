"""Migration v2.23 — the `vital_status` form becomes an `attribute` leaf
(TICKET-0113, BRIEF-0113-B; decisions WE1 and WG1 of the conditions series).

No table changes. Every `condition_node` leaf of the retired form
`vital_status` becomes a leaf of the form `attribute` reading the system
attribute `sys:vital_status`: `form = 'attribute'`, `target_key =
'sys:vital_status'`; its subject and its `value` (`alive`, `dead`,
`missing`, `unknown` -- the system attribute's choices) are kept. The
column `character.vital_status` is untouched: the system attribute reads it
in place (G3 of the series).

Measured before this lot was written: the production database held no such
leaf (2026-10-10). The conversion still runs, on any database.

Refuses to run on a database whose `schema_meta.static_version` is older
than v2.22, and refuses -- changing nothing -- when a `vital_status` leaf
carries a value outside the system attribute's choices or a target.

Idempotent: a second run finds no `vital_status` leaf.

Post-check, before `schema_meta` moves to v2.23: no leaf of the form
`vital_status` remains.

Run from the project root, after `migrate_v2_22_attributes.py`:

    python scripts/migrate_v2_23_attribute_leaves.py
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_23_attribute_leaves.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.attributes import ATTRIBUTE_FORM, system_attribute  # noqa: E402
from world_engine.db import engine  # noqa: E402

_PREVIOUS_VERSION = "v2.22"
_THIS_VERSION = "v2.23"
_RETIRED_FORM = "vital_status"
_SYSTEM_KEY = "sys:vital_status"


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.lstrip("v").split(".")
    return int(major), int(minor)


def _refuse_if_behind() -> None:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
        found = row[0] if row is not None else "no schema_meta row"
        raise SystemExit(
            f"Migration v2.23 refused: the database is at {found!r}; run the migrations "
            f"up to {_PREVIOUS_VERSION} first."
        )


def _convert() -> int:
    allowed = {value for value, _label in system_attribute(_SYSTEM_KEY).values}
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT id, value, target_key, target_entity_id, threshold FROM condition_node WHERE form = :form"
        ), {"form": _RETIRED_FORM}).all()
        for node_id, value, target_key, target_entity_id, threshold in rows:
            if value not in allowed or target_key or target_entity_id or threshold is not None:
                raise SystemExit(
                    f"Migration v2.23 refused: leaf {node_id!r} ({value!r}, {target_key!r}, "
                    f"{target_entity_id!r}, {threshold!r}) is not a vital_status leaf this migration "
                    "can convert. Nothing was changed."
                )
        conn.execute(text(
            "UPDATE condition_node SET form = :form, target_key = :key WHERE form = :retired"
        ), {"form": ATTRIBUTE_FORM, "key": _SYSTEM_KEY, "retired": _RETIRED_FORM})
    return len(rows)


def _post_checks() -> None:
    with engine.connect() as conn:
        left = conn.execute(text("SELECT COUNT(*) FROM condition_node WHERE form = :form"),
                            {"form": _RETIRED_FORM}).scalar()
    if left:
        raise SystemExit(f"Migration v2.23 aborted, post-check failed: {left} vital_status leaf(s) remain.")
    print("Post-check: no vital_status leaf remains.")


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if _version_key(row.static_version) < _version_key(_THIS_VERSION):
            previous = row.static_version
            row.static_version = _THIS_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {_THIS_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.23 — vital_status leaves become attribute leaves")
    _refuse_if_behind()
    converted = _convert()
    if converted:
        print(f"Converted: {converted} vital_status leaf(s) -> attribute {_SYSTEM_KEY}.")
    else:
        print("No vital_status leaf — nothing to convert.")
    _post_checks()
    _converge_schema_meta()
    print("\nMigration v2.23 applied.")


if __name__ == "__main__":
    main()
