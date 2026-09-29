"""One-shot, idempotent delivery of the TICKET-0097 prompt updates onto the
live DB: models name facts by code, never by a free-text subject.

- `pt-overhearing-classification` (BRIEF-0097-C, L1): classifies against a
  coded fact list; its variables become `fact_list`, `player_line`,
  `npc_line`.
- `pt-world-tick` (BRIEF-0097-C, Z2): a `new_knowledge` names what the NPC
  passes on by its briefing code (`source_fact`).
- `pt-day-plan` (BRIEF-0097-D, D1'a): a `knowledge` requirement's
  `target_key` is the code of a fact from the appended learnable list.
- `pt-conversation-analysis` (BRIEF-0097-F, M1/N1): no `subject` in any
  knowledge shape or example, and no `knowledge_change` type.
- `pt-player-generation` (BRIEF-0097-F, K1): a knowledge item is a level and
  a content, no subject.

Embeds NO prompt text of its own; it imports each text from
`scripts/seed_pilot.py` (single source of text). History is sacred: a changed
text lands as a new `prompt_version` row, the old one untouched. Variables
are full-replaced through `write_prompt_variables`, as `seed_pilot.py` does.

Touches nothing else. Safe to re-run: an unchanged head prints "unchanged".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0097_fact_code_prompts.py refuses to run unless "
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
from world_engine.writes import write_prompt_variables, write_prompt_version  # noqa: E402

# (head id, system prompt, user template, variables, version note)
_UPDATES: tuple[tuple[str, str, str, list[str], str], ...] = (
    (
        "pt-overhearing-classification",
        seed_pilot.OVERHEARING_CLASSIFICATION_SYSTEM_PROMPT,
        seed_pilot.OVERHEARING_CLASSIFICATION_USER_TEMPLATE,
        ["fact_list", "player_line", "npc_line"],
        "TICKET-0097 BRIEF-0097-C -- classify against a coded fact list (L1)",
    ),
    (
        "pt-world-tick",
        seed_pilot.WORLD_TICK_SYSTEM_PROMPT,
        seed_pilot.WORLD_TICK_USER_TEMPLATE,
        ["tick_context", "interval_label"],
        "TICKET-0097 BRIEF-0097-C -- new_knowledge names its source fact by code (Z2)",
    ),
    (
        "pt-day-plan",
        seed_pilot.DAY_PLAN_SYSTEM_PROMPT,
        seed_pilot.DAY_PLAN_USER_TEMPLATE,
        ["character_name", "declaration"],
        "TICKET-0097 BRIEF-0097-D -- a knowledge gate names its fact by code (D1'a)",
    ),
    (
        "pt-conversation-analysis",
        seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
        seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE,
        ["transcript", "injected_context"],
        "TICKET-0097 BRIEF-0097-F -- no subject, no knowledge_change (M1, N1)",
    ),
    (
        "pt-player-generation",
        seed_pilot.PLAYER_GENERATION_SYSTEM_PROMPT,
        seed_pilot.PLAYER_GENERATION_USER_TEMPLATE,
        ["brief"],
        "TICKET-0097 BRIEF-0097-F -- a knowledge item has no subject (K1)",
    ),
)


def _apply(session: Session, head_id: str, system_prompt: str, user_template: str,
           variables: list[str], note: str) -> None:
    head = session.get(PromptTemplate, head_id)
    if head is None:
        print(f"{head_id}: head not found — run scripts/seed_pilot.py first")
        sys.exit(1)
    write_prompt_variables(session, template_id=head.id, variables=variables)
    current = current_prompt(session, head)
    if current.system_prompt == system_prompt and current.user_template == user_template:
        print(f"{head_id}: unchanged (v{current.version_number})")
        return
    version = write_prompt_version(
        session, template_id=head.id, system_prompt=system_prompt,
        user_template=user_template, note=note,
    )
    print(f"{head_id}: v{current.version_number} -> v{version.version_number}")


def main() -> None:
    with Session(engine) as session:
        for update in _UPDATES:
            _apply(session, *update)
        session.commit()


if __name__ == "__main__":
    main()
