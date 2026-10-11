"""One-shot, idempotent delivery of the TICKET-0113 condition interpreter's
prompt update onto the live DB (BRIEF-0113-D): the model reads the world's
attributes -- the `a` list, a new variable `attributes` -- and writes an
`attribute` leaf.

Like `apply_ticket_0110_link_prompt.py`, it edits the CURRENT version of
`pt-condition-interpret` fragment by fragment, so an edit the creator made
in the Prompts tab is kept. The fragments are
`seed_pilot.CONDITION_INTERPRET_FRAGMENTS` (single source: the seed's text
is the 0112 text with the same fragments applied). Per fragment: its new
text present -> already done (looked for first: an old fragment may stand
inside its own new text); else its old text present -> replaced; neither
-> reported, to be edited by hand. The head's variables are first set to the
seed's (`write_prompt_variables`), since a new version may only use
declared placeholders.

History is sacred: a changed text lands as a new `prompt_version` row
through `write_prompt_version`, the old one untouched. Touches nothing else.
Safe to re-run: an already-updated head prints "unchanged".

Run after `migrate_v2_23_attribute_leaves.py`:

    python scripts/apply_ticket_0113_condition_prompt.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0113_condition_prompt.py refuses to run unless "
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

HEAD = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
NOTE = "TICKET-0113 BRIEF-0113-D -- the interpreter reads the world's attributes"


def apply_fragments(texts: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """`texts` (`system_prompt`, `user_template`) with every fragment applied
    where its old text stands; the fragments found in neither form."""
    out = dict(texts)
    missing = []
    for field, old, new in seed_pilot.CONDITION_INTERPRET_FRAGMENTS:
        if new in out[field]:
            continue
        if old in out[field]:
            out[field] = out[field].replace(old, new)
        else:
            missing.append(f"{field}: {old[:60]}…")
    return out, missing


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
