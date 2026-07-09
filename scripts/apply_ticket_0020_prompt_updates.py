"""One-shot, idempotent delivery of the TICKET-0020 prompt updates onto the
live DB (BRIEF-0020-b, item 7, S2).

Both `pt-world-tick` and `pt-world-tick-events` heads already exist — only
the append-a-version branch is needed for each (0015/0016/0018/0019 shape).
Embeds NO prompt text of its own; it imports the constants from
`scripts/seed_pilot.py` (single source of text).

Run order on the live DB:
    python scripts/seed_pilot.py                          # converges head fields (no-op on text, a version already exists, S2)
    python scripts/apply_ticket_0020_prompt_updates.py    # appends v(n+1) to each head, or reports unchanged

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

_HEADS = (
    ("pt-world-tick", "WORLD_TICK_SYSTEM_PROMPT", "WORLD_TICK_USER_TEMPLATE"),
    ("pt-world-tick-events", "WORLD_TICK_EVENTS_SYSTEM_PROMPT", "WORLD_TICK_EVENTS_USER_TEMPLATE"),
)


def main() -> None:
    with Session(engine) as session:
        for head_id, system_attr, user_attr in _HEADS:
            head = session.get(PromptTemplate, head_id)
            if head is None:
                print(f"{head_id}: head not found — run scripts/seed_pilot.py first")
                sys.exit(1)

            system_prompt = getattr(seed_pilot, system_attr)
            user_template = getattr(seed_pilot, user_attr)

            current = current_prompt(session, head)
            if current.system_prompt == system_prompt and current.user_template == user_template:
                print(f"{head_id}: unchanged (v{current.version_number})")
                continue

            version = write_prompt_version(
                session,
                template_id=head.id,
                system_prompt=system_prompt,
                user_template=user_template,
                note="TICKET-0020 BRIEF-0020-b",
            )
            session.commit()
            print(f"{head_id}: v{current.version_number} -> v{version.version_number}")


if __name__ == "__main__":
    main()
