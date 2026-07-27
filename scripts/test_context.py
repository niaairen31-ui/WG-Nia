"""Test harness for assemble_npc_context (relation-gated, secret-excluding).

Assembles and prints the test Keeper's context toward the test player at the
test tavern — where the NPC→interlocutor relation defaults to 50 (neutral),
since the Keeper has no read on the player — then asserts the disclosure
policy against the deterministic fixture seeded by `seed_test.py`
(BRIEF-0049-b, H1 contract):

- the share_threshold=50 row IS present (50 >= 50),
- the share_threshold=65 row is ABSENT (50 < 65),
- the the_unnamed secret is ABSENT (is_secret = TRUE, never injected),
- no other entity's secret and not the player's own secret appear.

Requires `WORLD_ENGINE_ENV=test` and a seeded test DB. No live model call.

    WORLD_ENGINE_ENV=test python scripts/seed_test.py
    WORLD_ENGINE_ENV=test python scripts/test_context.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env != "test":
    print(
        f"test_context.py refuses to run unless WORLD_ENGINE_ENV=test (got: {_env or 'unset'})."
    )
    sys.exit(1)

# UTF-8 console for the accented French context.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session, select  # noqa: E402

from world_engine import models as m  # noqa: E402
from world_engine.context import assemble_npc_context  # noqa: E402
from world_engine.db import engine  # noqa: E402

NPC_ID = "npc-test-keeper"
PLAYER_ID = "char-test-player"
LOCATION_ID = "loc-test-tavern"


def main() -> None:
    with Session(engine) as session:
        context = assemble_npc_context(NPC_ID, PLAYER_ID, LOCATION_ID, session)

        print(context)
        print("=" * 72)
        print("ASSERTION REPORT — Test Keeper → Test Player @ Test Tavern (relation = 50)")
        print("=" * 72)

        # The Keeper's knowledge rows, keyed by subject (content + flags from DB).
        keeper = {
            k.subject: k
            for k in session.exec(
                select(m.Knowledge).where(m.Knowledge.entity_id == NPC_ID)
            ).all()
        }
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

        results: list[tuple[bool, str]] = []

        # 1. The share_threshold=50 row IS present.
        for subject in ("tavern_daily",):
            row = keeper[subject]
            results.append(
                (
                    row.content in context,
                    f"threshold-50 row present: {subject}",
                )
            )

        # 2. The guarded row (threshold 65) is ABSENT at relation 50.
        guarded = keeper["local_rumor"]
        results.append(
            (
                guarded.content not in context,
                f"threshold-65 row withheld: local_rumor "
                f"(threshold={guarded.share_threshold} > 50)",
            )
        )

        # 3. The the_unnamed secret is ABSENT (is_secret = TRUE).
        secret = keeper["the_unnamed"]
        results.append(
            (
                secret.content not in context,
                "secret excluded entirely: the_unnamed (is_secret=TRUE)",
            )
        )

        # 4. No other entity's secret knowledge appears anywhere.
        leaked = [f"{k.entity_id}:{k.subject}" for k in other_secrets if k.content in context]
        results.append(
            (not leaked, f"no other entity's secret appears (leaks={leaked or 'none'})")
        )

        # 5. The player's own secret is absent (the NPC can't read their mind).
        results.append(
            (
                player_secret.content not in context,
                "player's own secret absent: personal_magic_incident",
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
