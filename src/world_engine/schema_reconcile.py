"""Physical-table reconciliation — C2 plane 2 (TICKET-0044, BRIEF-0044-d).

Runtime accounting, not migration-declared: every physical table in the
live database must be either a static model-declared table (plane 1) or a
registered runtime table (`entity_type.physical_table`, any status — an
active, retired, or quarantined type's table still physically exists).
Anything else is corruption we must never serve on. `_orphan_ext_*`
quarantine tables (BRIEF-0044-e) are pattern-accounted: this module only
ACCOUNTS for that prefix, it does not create it.

Runs at boot (`cockpit/app.py`, extending the BRIEF-0044-a version guard)
and as a standalone CLI (`python -m world_engine.schema_reconcile`) —
report-only: no auto-drop, no auto-register.
"""

from __future__ import annotations

import logging
import sys

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, select

from .writes.schema import EXT_PREFIX

_log = logging.getLogger(__name__)
_ORPHAN_PREFIX = "_orphan_" + EXT_PREFIX


def static_table_names() -> set[str]:
    """Every table declared on `SQLModel.metadata` — importing `models`
    registers them; never a hardcoded literal set."""
    from world_engine import models  # noqa: F401 — registers every table

    return set(SQLModel.metadata.tables.keys())


def registered_runtime_tables(session: Session) -> set[str]:
    """Every `entity_type.physical_table`, for ALL statuses — an active,
    retired, or quarantined type's table still physically exists."""
    from .models import EntityType

    return set(session.exec(select(EntityType.physical_table)).all())


def unaccounted_tables(engine, session: Session) -> list[str]:
    """Physical tables that are neither static, nor registered, nor a
    pattern-accounted `_orphan_ext_*` quarantine table. Sorted."""
    physical = set(inspect(engine).get_table_names())
    accounted = static_table_names() | registered_runtime_tables(session)
    accounted |= {t for t in physical if t.startswith(_ORPHAN_PREFIX)}
    return sorted(physical - accounted)


def main() -> int:
    from .db import engine as app_engine

    with Session(app_engine) as session:
        unaccounted = unaccounted_tables(app_engine, session)
    for table in unaccounted:
        _log.warning(table)
    return 1 if unaccounted else 0


if __name__ == "__main__":
    sys.exit(main())
