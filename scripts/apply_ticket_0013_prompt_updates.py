"""One-shot, idempotent delivery of the TICKET-0013 prompt updates onto the
live DB (BRIEF-0013-c, item 6, S2).

TICKET-0011's S2 guarantee means `seed_pilot.py` never touches text on an
existing head, so the goal-behaviour-loop wording (the OBJECTIFS directive on
`pt-npc-dialogue`, the GOAL_CHANGE rubric + EXEMPLE 5 on
`pt-conversation-analysis`) must reach the live DB as new `prompt_version`
rows through `writes.write_prompt_version` — the single sanctioned write
shape. This script embeds NO prompt text of its own; it imports the updated
constants from `scripts/seed_pilot.py` (single source of text) and writes
only what differs from each head's current version.

Run order on the live DB:
    python scripts/seed_pilot.py                          # converges head fields
    python scripts/apply_ticket_0013_prompt_updates.py    # text as new versions

Safe to re-run: a head whose current (system_prompt, user_template) already
equals the seed constants is left untouched and reported "unchanged".
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

# (head_id, system_prompt constant, user_template constant) — the two heads
# touched by the goal behaviour loop (BRIEF-0013-c).
TOUCHED_HEADS = [
    ("pt-npc-dialogue", seed_pilot.NPC_DIALOGUE_SYSTEM_PROMPT, "{player_line}"),
    ("pt-conversation-analysis", seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT, seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE),
]


def main() -> None:
    with Session(engine) as session:
        for head_id, system_prompt, user_template in TOUCHED_HEADS:
            head = session.get(PromptTemplate, head_id)
            if head is None:
                print(f"{head_id}: HEAD NOT FOUND — skipped")
                continue

            current = current_prompt(session, head)
            if current.system_prompt == system_prompt and current.user_template == user_template:
                print(f"{head_id}: unchanged (v{current.version_number})")
                continue

            new_version = write_prompt_version(
                session,
                template_id=head_id,
                system_prompt=system_prompt,
                user_template=user_template,
                note="TICKET-0013 BRIEF-0013-c",
            )
            session.commit()
            print(f"{head_id}: v{current.version_number} -> v{new_version.version_number}")


if __name__ == "__main__":
    main()
