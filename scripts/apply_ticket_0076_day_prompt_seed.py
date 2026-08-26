"""One-shot, idempotent delivery of the TICKET-0075 day chain prompt
templates onto the live DB (TICKET-0076, BRIEF-0076-a).

Unlike apply_ticket_0024_prompt_updates.py this is a CREATE-HEAD script:
the eight heads do not exist yet on a DB seeded before BRIEF-0075-b. It
embeds NO prompt text and NO head fields -- both come from
seed_pilot.DAY_PROMPT_HEADS (single source).

Touches nothing else: no knowledge row, no relation, no other template.
S2 applies -- a head already present with >= 1 version never has its text
retouched.

Safe to re-run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0076_day_prompt_seed.py refuses to run unless "
        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlmodel import Session  # noqa: E402

import seed_pilot  # noqa: E402
from world_engine.db import engine  # noqa: E402


def main() -> None:
    with Session(engine) as session:
        before_created = len(seed_pilot._created)
        before_updated = len(seed_pilot._updated)
        before_existing = len(seed_pilot._existing)

        for entry in seed_pilot.DAY_PROMPT_HEADS:
            seed_pilot.upsert_prompt_template(session, **entry)
        session.commit()

        for table, id_ in seed_pilot._created[before_created:]:
            print(f"created  {table}/{id_}")
        for table, id_ in seed_pilot._updated[before_updated:]:
            print(f"updated  {table}/{id_}")
        for table, id_ in seed_pilot._existing[before_existing:]:
            print(f"existing {table}/{id_}")


if __name__ == "__main__":
    main()
