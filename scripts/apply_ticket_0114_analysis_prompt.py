"""One-shot, idempotent delivery of the TICKET-0114 conversation analysis
prompt update onto the live DB (BRIEF-0114-H): the analyzer reads the
world's event types -- the `t` list, a new variable `event_types` -- and
its sortes (`sortes`), names an event's type by code and its participants
by role, and may propose a type (I2).

Like `apply_ticket_0113_condition_prompt.py`, it edits the CURRENT version
of `pt-conversation-analysis` fragment by fragment, so an edit the creator
made in the Prompts tab is kept. The fragments are
`seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114` (single source: the
seed's texts hold each new fragment). Per fragment: its new text present ->
already done (looked for first: an old fragment may stand inside its own
new text); else its old text present -> replaced; neither -> reported, to
be edited by hand. The head's variables are first set to the seed's
(`write_prompt_variables`), since a new version may only use declared
placeholders.

History is sacred: a changed text lands as a new `prompt_version` row
through `write_prompt_version`, the old one untouched. Touches nothing else.
Safe to re-run: an already-updated head prints "unchanged".

Run after `migrate_v2_25_event_columns.py`:

    python scripts/apply_ticket_0114_analysis_prompt.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0114_analysis_prompt.py refuses to run unless "
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
from world_engine.writes.prompts import write_prompt_variables  # noqa: E402

HEAD_ID = "pt-conversation-analysis"
NOTE = "TICKET-0114 BRIEF-0114-H -- typed events by code and role, a proposed type (I2)"


def apply_fragments(texts: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """`texts` with every fragment applied where its old text stands; the
    fragments found in neither form."""
    out = dict(texts)
    missing = []
    for field, old, new in seed_pilot.CONVERSATION_ANALYSIS_FRAGMENTS_0114:
        if new in out[field]:
            continue
        if old in out[field]:
            out[field] = out[field].replace(old, new)
        else:
            missing.append(f"{field}: {old[:60]}…")
    return out, missing


def main() -> None:
    # A fragment's text holds characters a Windows console cannot encode; a
    # report line must never crash the delivery.
    sys.stdout.reconfigure(errors="replace")
    with Session(engine) as session:
        head = session.get(PromptTemplate, HEAD_ID)
        if head is None:
            print(f"{HEAD_ID}: head not found -- nothing to do (the seed creates it)")
            return
        write_prompt_variables(session, template_id=head.id,
                               variables=list(seed_pilot.CONVERSATION_ANALYSIS_VARIABLES))
        current = current_prompt(session, head)
        texts, missing = apply_fragments({"system_prompt": current.system_prompt,
                                          "user_template": current.user_template})
        for line in missing:
            print(f"{HEAD_ID}: fragment not found, edit by hand -- {line}")
        if texts == {"system_prompt": current.system_prompt, "user_template": current.user_template}:
            session.commit()
            print(f"{HEAD_ID}: unchanged (v{current.version_number})")
            return
        version = write_prompt_version(session, template_id=head.id, system_prompt=texts["system_prompt"],
                                       user_template=texts["user_template"], note=NOTE)
        session.commit()
        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")


if __name__ == "__main__":
    main()
