"""Export the Lore shell's usage journal as JSON Lines (TICKET-0103,
BRIEF-0103-E, decision E1).

The journal's sole reader (`lore_usage_event`, schema v2.13). One line per
attempt -- one use of a Lore panel, keyed by `(attempt_id, world_ref, kind)`
-- in the order the attempts started:

    {"attempt_id", "kind", "world_ref", "world_name", "started_at",
     "ended_at", "committed", "lore_entry_refs", "events": [
        {"step", "outcome", "created_at", "payload", "model_calls",
         "lore_entry_ref"}, ...]}

`committed` is true when a write attempt holds an `ok` commit, false when it
holds none (an abandoned attempt), and null for a consultation. Nothing is
diffed or summarized here: the analysis reads the draft and the committed
proposal of an attempt from its events. Read-only: this script never writes
the database.

The export carries everything the journal holds -- secrets and creator notes
of every world included -- so it refuses an `--out` inside this repository:
it can never be staged by accident.

Run from the project root:

    python scripts/export_lore_usage.py --out lore_usage.jsonl [--since 2026-10-01] [--world-ref <id>]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "export_lore_usage.py refuses to run without WORLD_ENGINE_ENV or "
        "WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session, select  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import LoreUsageEvent  # noqa: E402


def _iso(value: datetime) -> str:
    return value.isoformat()


def _event(row: LoreUsageEvent) -> dict:
    return {
        "step": row.step, "outcome": row.outcome, "created_at": _iso(row.created_at),
        "payload": row.payload, "model_calls": row.model_calls,
        "lore_entry_ref": row.lore_entry_ref,
    }


def attempts(rows: list[LoreUsageEvent]) -> list[dict]:
    """Group `rows` (already in `(created_at, id)` order) by attempt, in the
    order each attempt's first event appears."""
    grouped: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        key = (row.attempt_id, row.world_ref, row.kind)
        attempt = grouped.get(key)
        if attempt is None:
            attempt = grouped[key] = {
                "attempt_id": row.attempt_id, "kind": row.kind, "world_ref": row.world_ref,
                "world_name": row.world_name, "started_at": _iso(row.created_at),
                "ended_at": None, "committed": None, "lore_entry_refs": [], "events": [],
            }
        attempt["events"].append(_event(row))
        attempt["ended_at"] = _iso(row.created_at)
        if row.lore_entry_ref is not None:
            attempt["lore_entry_refs"].append(row.lore_entry_ref)
    for attempt in grouped.values():
        if attempt["kind"] == "write":
            attempt["committed"] = bool(attempt["lore_entry_refs"])
    return list(grouped.values())


def _read(since: str | None, world_ref: str | None) -> list[LoreUsageEvent]:
    query = select(LoreUsageEvent).order_by(LoreUsageEvent.created_at, LoreUsageEvent.id)
    if world_ref:
        query = query.where(LoreUsageEvent.world_ref == world_ref)
    with Session(engine) as session:
        rows = list(session.exec(query).all())
    if since:
        start = datetime.fromisoformat(since)
        first: dict[tuple[str, str, str], datetime] = {}
        for row in rows:
            first.setdefault((row.attempt_id, row.world_ref, row.kind), row.created_at)
        rows = [r for r in rows if first[(r.attempt_id, r.world_ref, r.kind)].replace(tzinfo=None)
                >= start.replace(tzinfo=None)]
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the Lore usage journal as JSON Lines.")
    parser.add_argument("--out", required=True, help="the .jsonl file to write (overwritten)")
    parser.add_argument("--since", help="keep attempts started on or after this ISO date")
    parser.add_argument("--world-ref", help="keep one world's attempts (a world id, even deleted)")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    if out == REPO or REPO in out.parents:
        print(f"export_lore_usage.py refuses to write inside the repository ({out}): "
              "the export holds every world's secrets. Choose a path outside it.", file=sys.stderr)
        return 2
    rows = _read(args.since, args.world_ref)
    exported = attempts(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for attempt in exported:
            handle.write(json.dumps(attempt, ensure_ascii=False) + "\n")
    print(f"{len(exported)} attempt(s), {len(rows)} event(s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
