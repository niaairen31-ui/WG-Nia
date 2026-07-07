"""One-shot, idempotent delivery of the TICKET-0014 prompt onto the live DB
(BRIEF-0014-a, item 5, S2).

`pt-world-tick` is a BRAND NEW head (unlike TICKET-0013's script, which only
had to append versions onto already-seeded heads): on a live DB that has
never run this ticket's seed, the head row itself is absent. This script
creates the head + writes v1 through `writes.write_prompt_version` when
absent, and no-ops when the head already exists with identical text (S2:
never touches text on an existing head with a different diff either — a
real wording change would need its own delivery step, not a silent
overwrite here). Embeds NO prompt text of its own; it imports the constants
from `scripts/seed_pilot.py` (single source of text).

Run order on the live DB:
    python scripts/seed_pilot.py                          # converges head fields (no-ops here: pt-world-tick isn't in the seed's non-text fields path until this script creates the head)
    python scripts/apply_ticket_0014_prompt_updates.py    # creates the head + v1, or reports unchanged

Safe to re-run.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlmodel import Session  # noqa: E402

import seed_pilot  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.models import PromptTemplate  # noqa: E402
from world_engine.prompt_store import current_prompt  # noqa: E402
from world_engine.writes import write_prompt_version  # noqa: E402

HEAD_ID = "pt-world-tick"


def main() -> None:
    with Session(engine) as session:
        head = session.get(PromptTemplate, HEAD_ID)

        if head is None:
            head = PromptTemplate(
                id=HEAD_ID,
                world_id=None,
                name="World tick — avancement PNJ hors-champ (JSON)",
                usage="world_tick",
                variables=["tick_context", "interval_label"],
                destination="local",
            )
            session.add(head)
            session.flush()
            version = write_prompt_version(
                session,
                template_id=head.id,
                system_prompt=seed_pilot.WORLD_TICK_SYSTEM_PROMPT,
                user_template=seed_pilot.WORLD_TICK_USER_TEMPLATE,
                note="TICKET-0014 BRIEF-0014-a",
            )
            session.commit()
            print(f"{HEAD_ID}: created (v{version.version_number})")
            return

        current = current_prompt(session, head)
        if (
            current.system_prompt == seed_pilot.WORLD_TICK_SYSTEM_PROMPT
            and current.user_template == seed_pilot.WORLD_TICK_USER_TEMPLATE
        ):
            print(f"{HEAD_ID}: unchanged (v{current.version_number})")
            return

        version = write_prompt_version(
            session,
            template_id=head.id,
            system_prompt=seed_pilot.WORLD_TICK_SYSTEM_PROMPT,
            user_template=seed_pilot.WORLD_TICK_USER_TEMPLATE,
            note="TICKET-0014 BRIEF-0014-a",
        )
        session.commit()
        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")


if __name__ == "__main__":
    main()
