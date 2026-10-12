"""One-shot, idempotent delivery of the TICKET-0114 condition interpreter's
prompt update onto the live DB (BRIEF-0114-F): the model reads the world's
event types -- the `t` list, a new variable `event_types` -- and its sortes
(`sortes`), and writes an `event` leaf.

The same delivery as `apply_ticket_0113_condition_prompt.py`, whose
`apply_fragments` it imports (never a second copy): the CURRENT version of
`pt-condition-interpret` is edited fragment by fragment from
`seed_pilot.CONDITION_INTERPRET_FRAGMENTS`, so an edit the creator made in
the Prompts tab is kept; a fragment found in neither form is reported, to
be edited by hand. The head's variables are first set to the seed's.

History is sacred: a changed text lands as a new `prompt_version` row
through `write_prompt_version`, the old one untouched. Touches nothing else.
Safe to re-run: an already-updated head prints "unchanged".

Run after `migrate_v2_25_event_columns.py`:

    python scripts/apply_ticket_0114_condition_prompt.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0114_condition_prompt.py refuses to run unless "
        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlmodel import Session  # noqa: E402

from apply_ticket_0113_condition_prompt import HEAD, apply_fragments  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.models import PromptTemplate  # noqa: E402
from world_engine.prompt_store import current_prompt  # noqa: E402
from world_engine.writes import write_prompt_version  # noqa: E402
from world_engine.writes.prompts import write_prompt_variables  # noqa: E402

NOTE = "TICKET-0114 BRIEF-0114-F -- the interpreter reads the world's event types and sortes"


def main() -> None:
    with Session(engine) as session:
        head = session.get(PromptTemplate, HEAD["id"])
        if head is None:
            print(f"{HEAD['id']}: head not found -- nothing to do (the seed creates it)")
            return
        write_prompt_variables(session, template_id=head.id, variables=HEAD["variables"])
        current = current_prompt(session, head)
        texts, missing = apply_fragments({"system_prompt": current.system_prompt,
                                          "user_template": current.user_template})
        for line in missing:
            print(f"{HEAD['id']}: fragment not found, edit by hand -- {line}")
        if texts == {"system_prompt": current.system_prompt, "user_template": current.user_template}:
            session.commit()
            print(f"{HEAD['id']}: unchanged (v{current.version_number})")
            return
        version = write_prompt_version(session, template_id=head.id, system_prompt=texts["system_prompt"],
                                       user_template=texts["user_template"], note=NOTE)
        session.commit()
        print(f"{HEAD['id']}: v{current.version_number} -> v{version.version_number}")


if __name__ == "__main__":
    main()
