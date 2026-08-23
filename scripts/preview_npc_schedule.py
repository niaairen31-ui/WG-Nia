"""Preview `where_is` / `who_is_at` / `unresolved_npcs` — the concrete
reader for `world.current_phase` (T-A1) and the live-gate instrument for
TICKET-0074, BRIEF-0074-a.

Two modes:
    python scripts/preview_npc_schedule.py --npc <entity id> [--phase <p>]
    python scripts/preview_npc_schedule.py --location <entity id> --phase <p>

Omitting --phase in --npc mode reads `world.current_phase` from the active
world and reports which phase it used.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# UTF-8 console for French output on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "preview_npc_schedule.py refuses to run without WORLD_ENGINE_ENV or "
        "WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session, select  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import Entity, World  # noqa: E402
from world_engine.models.schedule import SCHEDULE_PHASES  # noqa: E402
from world_engine.schedule_reads import unresolved_npcs, where_is, who_is_at  # noqa: E402


def _name(entity_id: str, db: Session) -> str:
    entity = db.get(Entity, entity_id)
    return f"{entity.name} ({entity_id})" if entity is not None else entity_id


def _active_world(db: Session) -> World | None:
    return db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712


def _print_npc_mode(npc_id: str, phase: str | None, db: Session) -> None:
    if phase is not None:
        phases = [phase]
        is_present_for = {phase: True}
    else:
        world = _active_world(db)
        current = world.current_phase if world is not None else SCHEDULE_PHASES[0]
        print(f"(no --phase given; using world.current_phase = {current!r})")
        phases = list(SCHEDULE_PHASES)
        is_present_for = {p: (p == current) for p in phases}

    print(f"Day for {_name(npc_id, db)}:")
    for p in phases:
        res = where_is(npc_id, p, db, is_present=is_present_for[p])
        location = _name(res.location_id, db) if res.location_id else "None"
        goal_suffix = f", standing_goal_id={res.standing_goal_id}" if res.standing_goal_id else ""
        print(f"  {p:12s} source={res.source:16s} location={location}{goal_suffix}")


def _print_location_mode(location_id: str, phase: str, db: Session) -> None:
    is_present = True
    roster = who_is_at(location_id, phase, db, is_present=is_present)
    print(f"who_is_at({_name(location_id, db)}, phase={phase!r}):")
    if roster:
        for npc_id in roster:
            print(f"  - {_name(npc_id, db)}")
    else:
        print("  (nobody)")

    unresolved = unresolved_npcs(phase, db, is_present=is_present)
    print(f"\nunresolved_npcs(phase={phase!r}):")
    if unresolved:
        for npc_id in unresolved:
            print(f"  - {_name(npc_id, db)}")
    else:
        print("  (none)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview npc_schedule resolution.")
    parser.add_argument("--npc", help="Entity id of the NPC.")
    parser.add_argument("--location", help="Entity id of the location.")
    parser.add_argument("--phase", choices=SCHEDULE_PHASES, help="Day-cycle phase.")
    args = parser.parse_args()

    if args.location and not args.phase:
        parser.error("--location requires --phase")
    if not args.npc and not args.location:
        parser.error("one of --npc or --location is required")

    with Session(engine) as db:
        if args.location:
            _print_location_mode(args.location, args.phase, db)
        else:
            _print_npc_mode(args.npc, args.phase, db)


if __name__ == "__main__":
    main()
