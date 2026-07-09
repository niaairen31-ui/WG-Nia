"""One-shot, idempotent delivery of the TICKET-0019 prompt onto the live DB
(BRIEF-0019-a, item 7, S2).

`pt-world-tick-events`'s head already exists since TICKET-0017 — only the
append-a-version branch is needed here (0015/0016/0018 shape). Embeds NO
prompt text of its own; it imports the constants from `scripts/seed_pilot.py`
(single source of text).

Run order on the live DB:
    python scripts/seed_pilot.py                          # converges head fields (no-op on text, a version already exists, S2)
    python scripts/apply_ticket_0019_prompt_updates.py    # appends v(n+1), or reports unchanged

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

HEAD_ID = "pt-world-tick-events"


def main() -> None:
    with Session(engine) as session:
        head = session.get(PromptTemplate, HEAD_ID)
        if head is None:
            print(f"{HEAD_ID}: head not found — run scripts/seed_pilot.py first")
            sys.exit(1)

        current = current_prompt(session, head)
        if (
            current.system_prompt == seed_pilot.WORLD_TICK_EVENTS_SYSTEM_PROMPT
            and current.user_template == seed_pilot.WORLD_TICK_EVENTS_USER_TEMPLATE
        ):
            print(f"{HEAD_ID}: unchanged (v{current.version_number})")
            return

        version = write_prompt_version(
            session,
            template_id=head.id,
            system_prompt=seed_pilot.WORLD_TICK_EVENTS_SYSTEM_PROMPT,
            user_template=seed_pilot.WORLD_TICK_EVENTS_USER_TEMPLATE,
            note="TICKET-0019 BRIEF-0019-a",
        )
        session.commit()
        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")


if __name__ == "__main__":
    main()
