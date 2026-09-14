"""One-shot backfill of `fact_participant` rows for previously-unresolved
`knowledge.subject` values, plus the coverage report (TICKET-0087,
BRIEF-0087-c).

Walks `subject_resolve.unresolved_subjects` for each world and attaches the
resolved entity to every fact behind a `matched` subject, through
`attach_participants` (the sanctioned writer) with a read-before-write
idempotency guard on `(fact_id, entity_id)` -- mandatory, not defensive:
`idx_fact_participant_unique` would otherwise raise `IntegrityError` mid-run
and abort the pass. `ambiguous`/`unmatched` entries are left untouched and
counted. `write_knowledge` is never called here: no `knowledge` row is
created or edited, and no `change_history` entry is written -- a subject
attachment is an index annotation on a fact, not an edit to a knowledge row
(decision C2, ARCHITECTURE_DECISIONS.md).

Default mode is report-only: it prints the per-world table and writes
nothing. Running it by accident does nothing. `--apply` performs the
writes and requires `--yes`. `--world <id>` restricts to one world; absent,
every world in the database is walked.

Refuses to run against a database whose `schema_meta.static_version` is not
the version this script was written against -- a schema that has moved is a
reason to stop, not to guess.

Idempotent end to end: a second `--apply --yes` run finds every
previously-matched fact already carrying its participant, so it attaches
nothing new; the per-world "rows covered" / "rows still uncovered" totals
(the state actually reached) stay the same both times.

Usage:
    python scripts/apply_ticket_0087_subject_participants.py [--world ID]
    python scripts/apply_ticket_0087_subject_participants.py --apply --yes [--world ID]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_env = os.environ.get("WORLD_ENGINE_ENV")
if _env not in ("prod", "test"):
    print(
        "apply_ticket_0087_subject_participants.py refuses to run unless "
        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
    )
    sys.exit(1)

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

# UTF-8 console for French subject text on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlmodel import Session, select  # noqa: E402

from world_engine.db import engine  # noqa: E402
from world_engine.models import Entity, Fact, FactParticipant, Knowledge, SchemaMeta, World  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
from world_engine.subject_resolve import unresolved_subjects  # noqa: E402
from world_engine.writes import attach_participants  # noqa: E402

_TOP_N_UNMATCHED = 10


def _total_knowledge_rows(db: Session, world_id: str) -> int:
    """Total `knowledge` rows in `world_id`, independent of coverage state --
    the fixed denominator "covered" / "still uncovered" are measured against."""
    return len(
        db.exec(
            select(Knowledge.id)
            .join(Entity, Entity.id == Knowledge.entity_id)
            .where(Entity.world_id == world_id)
        ).all()
    )


def _check_schema_version(db: Session) -> None:
    row = db.get(SchemaMeta, 1)
    got = row.static_version if row is not None else "uninitialized"
    if got != EXPECTED_STATIC_SCHEMA_VERSION:
        print(
            "apply_ticket_0087_subject_participants.py refuses to run: "
            f"schema_meta.static_version is {got!r}, this script was written "
            f"against {EXPECTED_STATIC_SCHEMA_VERSION!r}."
        )
        sys.exit(1)


def _attach_matched(db: Session, entry: dict) -> tuple[int, int]:
    """Attach `entry`'s resolved entity to every one of its `fact_ids`.

    Returns `(facts_attached, orphans)`. An orphan is a `fact_id` with no
    matching `fact` row -- R-03 measured zero of these in production;
    defended anyway (ADAPT), skipped and counted rather than raising.
    """
    entity_id = entry["resolution"].entity_id
    facts_attached = 0
    orphans = 0
    for fact_id in entry["fact_ids"]:
        fact = db.get(Fact, fact_id)
        if fact is None:
            orphans += 1
            continue
        existing = db.exec(
            select(FactParticipant).where(
                FactParticipant.fact_id == fact_id,
                FactParticipant.entity_id == entity_id,
            )
        ).first()
        if existing is not None:
            continue
        attach_participants(db, fact=fact, entity_ids=[entity_id])
        facts_attached += 1
    return facts_attached, orphans


def _process_world(db: Session, world: World, *, apply: bool) -> dict:
    """`subjects_matched`/`ambiguous`/`unmatched` and `facts_attached`
    describe THIS run's walk (zero matched/attached on a re-run once
    everything resolvable is already covered -- that IS "attaches zero new
    rows"). `rows_now_covered`/`rows_still_uncovered` describe the state the
    world is IN afterward, measured fresh against the fixed row total, so
    they read the same on every re-run once coverage stops changing (a
    second `--apply --yes` reports the same 98-of-615-shaped totals as the
    first, even though it attached nothing new)."""
    entries = unresolved_subjects(world.id, db)
    matched = [e for e in entries if e["resolution"].verdict == "matched"]
    ambiguous = [e for e in entries if e["resolution"].verdict == "ambiguous"]
    unmatched = [e for e in entries if e["resolution"].verdict == "unmatched"]

    facts_attached = 0
    orphans = 0
    if apply:
        for entry in matched:
            attached, orph = _attach_matched(db, entry)
            facts_attached += attached
            orphans += orph
        db.commit()
        residual = unresolved_subjects(world.id, db)
    else:
        residual = entries

    rows_still_uncovered = sum(e["row_count"] for e in residual)
    rows_now_covered = _total_knowledge_rows(db, world.id) - rows_still_uncovered

    return {
        "world": world.name,
        "subjects_matched": len(matched),
        "subjects_ambiguous": len(ambiguous),
        "subjects_unmatched": len(unmatched),
        "facts_attached": facts_attached,
        "orphans": orphans,
        "rows_now_covered": rows_now_covered,
        "rows_still_uncovered": rows_still_uncovered,
        "top_unmatched": sorted(
            unmatched, key=lambda e: (-e["row_count"], e["subject"])
        )[:_TOP_N_UNMATCHED],
    }


def _print_report(reports: list[dict], *, apply: bool) -> None:
    header = (
        "world | subjects matched | ambiguous | unmatched | "
        "facts attached | rows covered | rows uncovered"
    )
    print(header)
    print("-" * len(header))
    totals = dict.fromkeys(
        (
            "subjects_matched", "subjects_ambiguous", "subjects_unmatched",
            "facts_attached", "orphans", "rows_now_covered", "rows_still_uncovered",
        ),
        0,
    )
    for r in reports:
        print(
            f"{r['world']} | {r['subjects_matched']} | {r['subjects_ambiguous']} | "
            f"{r['subjects_unmatched']} | {r['facts_attached']} | "
            f"{r['rows_now_covered']} | {r['rows_still_uncovered']}"
        )
        for key in totals:
            totals[key] += r[key]
        if r["orphans"]:
            print(f"    orphan fact_id(s) with no matching fact row: {r['orphans']}")
        if r["top_unmatched"]:
            print("    top unmatched subjects (report-only worklist):")
            for e in r["top_unmatched"]:
                print(f"      {e['row_count']:>4}  {e['subject']}")

    print("-" * len(header))
    print(
        f"TOTAL | {totals['subjects_matched']} | {totals['subjects_ambiguous']} | "
        f"{totals['subjects_unmatched']} | {totals['facts_attached']} | "
        f"{totals['rows_now_covered']} | {totals['rows_still_uncovered']}"
    )
    if totals["orphans"]:
        print(f"orphan fact_id(s), total: {totals['orphans']}")

    if not apply:
        print()
        print("Report-only run: nothing was written. Re-run with --apply --yes to write.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill fact_participant rows for resolved knowledge.subject values."
    )
    parser.add_argument("--world", help="Restrict to one world id; absent runs every world.")
    parser.add_argument("--apply", action="store_true", help="Perform the writes (default: report only).")
    parser.add_argument("--yes", action="store_true", help="Required alongside --apply to confirm.")
    args = parser.parse_args()

    if args.apply and not args.yes:
        print("--apply requires --yes -- refusing to write without explicit confirmation.")
        sys.exit(1)

    if args.apply:
        print("Before --apply against a real database: python scripts/backup.py")

    with Session(engine) as db:
        _check_schema_version(db)

        if args.world:
            world = db.get(World, args.world)
            if world is None:
                print(f"World {args.world!r} not found.")
                sys.exit(1)
            worlds = [world]
        else:
            worlds = db.exec(select(World)).all()

        reports = [_process_world(db, w, apply=args.apply) for w in worlds]

    _print_report(reports, apply=args.apply)


if __name__ == "__main__":
    main()
