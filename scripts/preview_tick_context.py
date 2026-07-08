"""Preview the full-interiority briefing a world tick would send to one NPC
(TICKET-0014, BRIEF-0014-a; TICKET-0015, BRIEF-0015-a adds --interval) — the
concrete reader for `assemble_tick_context` in this brief, and the live-gate
instrument for the T1 review.

Usage:
    python scripts/preview_tick_context.py --npc <entity id> --interval "quelques jours"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# UTF-8 console for French output on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlmodel import Session  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import Character  # noqa: E402
from world_engine.tick import (  # noqa: E402
    INTERVAL_HOP_RADIUS,
    _reachable_locations,
    assemble_tick_context,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print the world-tick briefing assembled for one NPC."
    )
    parser.add_argument("--npc", required=True, help="Entity id of the NPC.")
    parser.add_argument(
        "--interval",
        choices=sorted(INTERVAL_HOP_RADIUS),
        default="quelques jours",
        help="Interval label — scales the OÙ TU PEUX ALLER radius.",
    )
    args = parser.parse_args()

    with Session(engine) as db:
        npc_char = db.get(Character, args.npc)
        reachable = (
            _reachable_locations(db, npc_char.current_location_id, args.interval)
            if npc_char and npc_char.current_location_id
            else []
        )
        try:
            briefing = assemble_tick_context(args.npc, db, destinations=reachable)
        except ValueError as exc:
            print(f"[error] {exc}", file=sys.stderr)
            sys.exit(1)

    print(briefing)


if __name__ == "__main__":
    main()
