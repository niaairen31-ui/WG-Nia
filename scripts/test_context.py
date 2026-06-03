"""Test harness for assemble_npc_context (relation-gated, secret-excluding).

Assembles and prints Maelis's context toward the player Joran at the tavern —
where the NPC→interlocutor relation defaults to 50 (neutral), since Maelis has
no read on Joran — then asserts the disclosure policy:

- the three share_threshold=50 rows ARE present (50 >= 50),
- the phenomena row (share_threshold=65) is ABSENT (50 < 65),
- the the_unnamed secret is ABSENT (is_secret = TRUE, never injected),
- no other entity's secret and not the player's own secret appear.

No live model call.

    python scripts/test_context.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# UTF-8 console for the accented French context.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlmodel import Session, select  # noqa: E402

from world_engine import models as m  # noqa: E402
from world_engine.context import assemble_npc_context  # noqa: E402
from world_engine.db import engine  # noqa: E402

NPC_ID = "npc-maelis"
PLAYER_ID = "char-player"
LOCATION_ID = "loc-dernier-verre"


def main() -> None:
    with Session(engine) as session:
        context = assemble_npc_context(NPC_ID, PLAYER_ID, LOCATION_ID, session)

        print(context)
        print("=" * 72)
        print("ASSERTION REPORT — Maelis → Joran @ Le Dernier Verre (relation = 50)")
        print("=" * 72)

        # Maelis's knowledge rows, keyed by subject (content + flags from DB).
        maelis = {
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

        # 1-3. The three share_threshold=50 rows ARE present.
        for subject in ("tavern_daily", "tavern_clientele", "verkhaal_city"):
            row = maelis[subject]
            results.append(
                (
                    row.content in context,
                    f"threshold-50 row present: {subject}",
                )
            )

        # 4. The phenomena row (threshold 65) is ABSENT at relation 50.
        phen = maelis["local_magic_incidents"]
        results.append(
            (
                phen.content not in context,
                f"threshold-65 row withheld: local_magic_incidents "
                f"(threshold={phen.share_threshold} > 50)",
            )
        )

        # 5. The the_unnamed secret is ABSENT (is_secret = TRUE).
        secret = maelis["the_unnamed"]
        results.append(
            (
                secret.content not in context,
                "secret excluded entirely: the_unnamed (is_secret=TRUE)",
            )
        )

        # 6. No other entity's secret knowledge appears anywhere.
        leaked = [f"{k.entity_id}:{k.subject}" for k in other_secrets if k.content in context]
        results.append(
            (not leaked, f"no other entity's secret appears (leaks={leaked or 'none'})")
        )

        # 7. The player's own secret is absent (NPC can't read his mind).
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
