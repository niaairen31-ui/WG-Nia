"""Test harness for assemble_npc_context.

Assembles and prints the full context for Maelis speaking to the player Joran at
the tavern, then runs a short assertion report verifying the structural
secret-protection guarantees. No live model call.

Run from the project root, after seeding:

    python scripts/test_context.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# The assembled context is UTF-8 (accented French + markers); make sure stdout
# can render it even on a legacy Windows code page.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session, select  # noqa: E402

from world_engine import models as m  # noqa: E402
from world_engine.context import (  # noqa: E402
    H_CONCEAL,
    assemble_npc_context,
)
from world_engine.db import engine  # noqa: E402

NPC_ID = "npc-maelis"
PLAYER_ID = "char-player"
LOCATION_ID = "loc-dernier-verre"


def parse_sections(text: str) -> dict[str, str]:
    """Split the context into {header: body} on the '=== HEADER ===' lines."""
    parts = re.split(r"(?m)^=== (.+?) ===$", text)
    sections: dict[str, str] = {}
    fields = iter(parts[1:])
    for title, body in zip(fields, fields):
        sections[title.strip()] = body.strip()
    return sections


def main() -> None:
    with Session(engine) as session:
        context = assemble_npc_context(NPC_ID, PLAYER_ID, LOCATION_ID, session)

        print(context)
        print("=" * 72)
        print("ASSERTION REPORT — Maelis → Joran @ Le Dernier Verre")
        print("=" * 72)

        sections = parse_sections(context)
        conceal_body = next(
            (b for h, b in sections.items() if h.startswith(H_CONCEAL[:20])), ""
        )

        # Reference data pulled from the DB (not hardcoded strings).
        maelis_secret = session.exec(
            select(m.Knowledge).where(
                m.Knowledge.entity_id == NPC_ID,
                m.Knowledge.subject == "the_unnamed",
            )
        ).first()
        player_secret = session.exec(
            select(m.Knowledge).where(
                m.Knowledge.entity_id == PLAYER_ID,
                m.Knowledge.subject == "personal_magic_incident",
            )
        ).first()
        other_secrets = session.exec(
            select(m.Knowledge).where(
                m.Knowledge.entity_id != NPC_ID,
                m.Knowledge.is_secret == True,  # noqa: E712
            )
        ).all()
        other_chars = session.exec(
            select(m.Character).where(m.Character.id != NPC_ID)
        ).all()

        results: list[tuple[bool, str]] = []

        # 1. Maelis's the_unnamed secret appears ONLY in the concealed section.
        secret_text = maelis_secret.content
        in_conceal = secret_text in conceal_body
        elsewhere = [
            h for h, b in sections.items()
            if not h.startswith(H_CONCEAL[:20]) and secret_text in b
        ]
        results.append(
            (
                in_conceal and not elsewhere,
                f"Maelis's 'the_unnamed' secret is in the concealed section "
                f"(found={in_conceal}) and nowhere else (leaked_in={elsewhere or 'none'})",
            )
        )

        # 2. No other entity's secret knowledge appears anywhere in the context.
        leaked_secrets = [
            f"{k.entity_id}:{k.subject}" for k in other_secrets if k.content in context
        ]
        results.append(
            (
                not leaked_secrets,
                f"No other entity's secret knowledge appears (leaks={leaked_secrets or 'none'})",
            )
        )

        # 2b. No other character's creator-only `secrets` blob appears either.
        leaked_blobs = []
        for c in other_chars:
            if c.secrets:
                for key, val in c.secrets.items():
                    if isinstance(val, str) and val in context:
                        leaked_blobs.append(f"{c.id}:{key}")
        results.append(
            (
                not leaked_blobs,
                f"No other character's secret blob appears (leaks={leaked_blobs or 'none'})",
            )
        )

        # 3. The player's own secret (personal_magic_incident) is absent.
        player_present = player_secret.content in context
        results.append(
            (
                not player_present,
                f"Player's own secret 'personal_magic_incident' is absent "
                f"(present={player_present})",
            )
        )

        for ok, label in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

        passed = sum(1 for ok, _ in results if ok)
        print(f"\n{passed}/{len(results)} checks passed.")
        if passed != len(results):
            sys.exit(1)


if __name__ == "__main__":
    main()
