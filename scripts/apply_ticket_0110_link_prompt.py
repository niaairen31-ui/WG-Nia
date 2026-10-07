"""One-shot, idempotent delivery of the TICKET-0110 prompt update onto the
live DB (BRIEF-0110-A, I2): the NPC link agent's pair pass no longer offers
the relation type `debt` -- « X owes Y » is a `debt` row, never a link.

Unlike `apply_ticket_0097_fact_code_prompts.py`, this script does not take
the text from `scripts/seed_pilot.py`: it edits the CURRENT head of
`pt-npc-link-pair` in place of one fragment, so an edit the creator made in
the Prompts tab is kept. The fragment is the type list's opening, exactly as
the seed wrote it (`ally, enemy, debt, fear`); it becomes `ally, enemy,
fear`. A head whose text no longer carries the fragment is left alone and
reported -- the creator then removes `debt` by hand, if it is still there.

History is sacred: a changed text lands as a new `prompt_version` row
through `write_prompt_version`, the old one untouched. Touches nothing else.
Safe to re-run: an already-updated head prints "unchanged".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0110_link_prompt.py refuses to run unless "
        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import PromptTemplate  # noqa: E402
from world_engine.prompt_store import current_prompt  # noqa: E402
from world_engine.writes import write_prompt_version  # noqa: E402

HEAD_ID = "pt-npc-link-pair"
OLD_FRAGMENT = "ally, enemy, debt, fear"
NEW_FRAGMENT = "ally, enemy, fear"
NOTE = "TICKET-0110 BRIEF-0110-A -- the relation type `debt` is retired (I2)"


def main() -> None:
    with Session(engine) as session:
        head = session.get(PromptTemplate, HEAD_ID)
        if head is None:
            print(f"{HEAD_ID}: head not found -- nothing to do")
            return
        current = current_prompt(session, head)
        if OLD_FRAGMENT not in current.user_template:
            state = "unchanged" if NEW_FRAGMENT in current.user_template else "fragment not found, edit by hand"
            print(f"{HEAD_ID}: {state} (v{current.version_number})")
            return
        version = write_prompt_version(
            session, template_id=head.id, system_prompt=current.system_prompt,
            user_template=current.user_template.replace(OLD_FRAGMENT, NEW_FRAGMENT), note=NOTE,
        )
        session.commit()
        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")


if __name__ == "__main__":
    main()
