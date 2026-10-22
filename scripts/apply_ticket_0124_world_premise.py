"""One-shot, idempotent delivery of the TICKET-0124 world premise onto the
live DB (BRIEF-0124-D, P1): one new version per creator or player template,
`{world_premise}` at the head of its current system text, the creator's own
edits kept.

For each `PROMPT_REGISTRY` usage whose regime is not `none` (by registry
order), every active head of that usage (by `id`): its variables first gain
`world_premise` when absent (C1 refuses an undeclared placeholder); then its
CURRENT version, when neither text holds `{world_premise}`, is copied with
the placeholder prefixed to `system_prompt`. A head whose current text
already holds the placeholder is left as it is.

History is sacred: a changed text lands as a new `prompt_version` row
through `write_prompt_version`, the old one untouched. Touches nothing else.
Safe to re-run: an already-updated head prints "unchanged".

    python scripts/apply_ticket_0124_world_premise.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0124_world_premise.py refuses to run unless "
        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session, select  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import PromptTemplate, PromptVariable  # noqa: E402
from world_engine.prompt_registry import PROMPT_REGISTRY  # noqa: E402
from world_engine.prompt_store import current_prompt  # noqa: E402
from world_engine.world_premise import PLACEHOLDER, VARIABLE, regime_of  # noqa: E402
from world_engine.writes import write_prompt_variables, write_prompt_version  # noqa: E402

NOTE = "TICKET-0124 BRIEF-0124-D -- the world premise (P1)"


def main() -> None:
    # A head's id or text may hold characters a Windows console cannot
    # encode; a report line must never crash the delivery.
    sys.stdout.reconfigure(errors="replace")
    lines: list[str] = []
    with Session(engine) as session:
        for usage in PROMPT_REGISTRY:
            if regime_of(usage) == "none":
                continue
            heads = session.exec(
                select(PromptTemplate)
                .where(PromptTemplate.usage == usage, PromptTemplate.is_active == True)  # noqa: E712
                .order_by(PromptTemplate.id)
            ).all()
            for head in heads:
                variables = list(session.exec(
                    select(PromptVariable.name).where(PromptVariable.prompt_template_id == head.id)
                ).all())
                if VARIABLE not in variables:
                    write_prompt_variables(session, template_id=head.id,
                                           variables=variables + [VARIABLE])
                current = current_prompt(session, head)
                if PLACEHOLDER in current.system_prompt or PLACEHOLDER in current.user_template:
                    lines.append(f"{head.id}: unchanged (v{current.version_number})")
                    continue
                version = write_prompt_version(session, template_id=head.id,
                                               system_prompt=PLACEHOLDER + current.system_prompt,
                                               user_template=current.user_template, note=NOTE)
                session.flush()
                lines.append(f"{head.id}: v{current.version_number} -> v{version.version_number}")
        session.commit()
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
