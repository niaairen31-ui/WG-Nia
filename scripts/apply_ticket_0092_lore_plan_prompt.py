"""One-shot, idempotent delivery of the TICKET-0092 `lore_question_to_plan`
prompt update onto the live DB (BRIEF-0092-c, Scope IN item 4).

`pt-lore-question-to-plan` already exists — only the append-a-version branch
is needed (`apply_ticket_0087_subject_prompt.py` shape). Embeds NO prompt
text of its own; it imports `LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT`/
`LORE_QUESTION_TO_PLAN_USER_TEMPLATE` from `scripts/seed_pilot.py` (single
source of text): the planner now names five mention categories (`object`
and `other` join `place`, `person`, `faction`). History is sacred: this
NEVER edits the existing version row in place — a changed system prompt
lands as a new `prompt_version` row, the old one untouched.

Touches nothing else: no canon row, no other template.

Safe to re-run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0092_lore_plan_prompt.py refuses to run unless "
        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlmodel import Session  # noqa: E402

import seed_pilot  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.models import PromptTemplate  # noqa: E402
from world_engine.prompt_store import current_prompt  # noqa: E402
from world_engine.writes import write_prompt_version  # noqa: E402

_HEAD_ID = "pt-lore-question-to-plan"


def main() -> None:
    with Session(engine) as session:
        head = session.get(PromptTemplate, _HEAD_ID)
        if head is None:
            print(f"{_HEAD_ID}: head not found — run scripts/seed_pilot.py first")
            sys.exit(1)

        system_prompt = seed_pilot.LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT
        user_template = seed_pilot.LORE_QUESTION_TO_PLAN_USER_TEMPLATE

        current = current_prompt(session, head)
        if current.system_prompt == system_prompt and current.user_template == user_template:
            print(f"{_HEAD_ID}: unchanged (v{current.version_number})")
            return

        version = write_prompt_version(
            session,
            template_id=head.id,
            system_prompt=system_prompt,
            user_template=user_template,
            note="TICKET-0092 BRIEF-0092-c -- five mention categories",
        )
        session.commit()
        print(f"{_HEAD_ID}: v{current.version_number} -> v{version.version_number}")


if __name__ == "__main__":
    main()
