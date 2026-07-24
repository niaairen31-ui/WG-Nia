"""Verify-and-report script for the `entity_trait` projection table, schema
v1.88 (TICKET-0045, BRIEF-0045-a).

This does NOT seed rows into `entity_trait` — no entity_type has checked a
trait yet (that is the constructor UI's job, TICKET-0046). It only confirms
the table exists and is empty, then prints the five canonical trait keys
that `traits.py` (BRIEF-0045-b) will declare, so the live operator can
eyeball that the migration landed before the registry module is wired.

If `traits.py` does not yet exist, the keys are printed from the literal
below and the script notes the fallback. Once `traits.py` exists, the keys
are imported from it and asserted to match this literal — the literal is a
pre-registry bootstrap, never a second source of truth (S-norme).

Run from the project root, after `scripts/migrate_v1_88_entity_trait.py`:

    python scripts/seed_trait_keys.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402

# Bootstrap literal ONLY — superseded the moment traits.py exists (asserted
# equal below). traits.py, not this list, is the source of truth.
TRAIT_KEYS = ["describable", "spatial", "knowable", "secretable", "mutable_by_ai"]


def main() -> None:
    inspector = inspect(engine)
    if models.EntityTrait.__tablename__ not in inspector.get_table_names():
        print(
            f"FAIL: table `{models.EntityTrait.__tablename__}` does not exist — "
            "run scripts/migrate_v1_88_entity_trait.py first."
        )
        raise SystemExit(1)
    print(f"Table `{models.EntityTrait.__tablename__}` exists.")

    with Session(engine) as db:
        row_count = len(db.exec(select(models.EntityTrait)).all())
    if row_count != 0:
        print(f"FAIL: expected `entity_trait` to be empty, found {row_count} row(s).")
        raise SystemExit(1)
    print("Table `entity_trait` is empty, as expected.")

    try:
        from world_engine.traits import trait_keys as registry_trait_keys  # noqa: E402

        registry_keys = list(registry_trait_keys())
        if registry_keys != TRAIT_KEYS:
            print(
                "FAIL: traits.py trait_keys() drifted from the brief literal.\n"
                f"  traits.py:      {registry_keys}\n"
                f"  brief literal:  {TRAIT_KEYS}"
            )
            raise SystemExit(1)
        print("Canonical trait keys (from traits.py):")
    except ModuleNotFoundError:
        print(
            "traits.py not yet present — keys shown from brief literal:"
        )

    for key in TRAIT_KEYS:
        print(f"  - {key}")


if __name__ == "__main__":
    main()
