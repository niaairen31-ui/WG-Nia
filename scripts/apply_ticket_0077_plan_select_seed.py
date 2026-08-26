"""One-shot, idempotent delivery of the TICKET-0077 `day_plan_select` prompt
head onto the live DB (BRIEF-0077-c).

Same CREATE-HEAD pattern as apply_ticket_0076_day_prompt_seed.py: it embeds
NO prompt text and NO head fields -- both come from
seed_pilot.DAY_PROMPT_HEADS (single source), and it loops the FULL tuple
(now nine heads), relying on upsert_prompt_template's idempotence (S2) so
the eight pre-existing heads report `existing` and only the ninth
(`pt-day-plan-select`) reports `created` on a first run.

Touches nothing else: no knowledge row, no relation, no other template.

Safe to re-run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0077_plan_select_seed.py refuses to run unless "
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
