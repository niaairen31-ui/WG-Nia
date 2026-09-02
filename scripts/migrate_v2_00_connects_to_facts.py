"""Migration v2.00 — `connects_to` facts, the known-reachability floor
(TICKET-0082, BRIEF-0082-d).

For every `relation` row with `type = 'connects_to'`, inserts one typed
`fact` (`relation_id` set, so `ck_fact_spine_exclusive` forbids any
`fact_participant` on it), `content` a generated French statement of the
edge in the exact form `"{name_a} communique avec {name_b}."`,
`default_level = 'knows'`, `created_by = 'migrate_v2_00'`. Every edge
arrives already known: on arrival, `tick_context._reachable_locations`'
knowledge-filtered graph is IDENTICAL to the unfiltered truth graph for
every entity — behaviour is preserved by construction, matching BRIEF-
0082-d's safety property. This migration never lowers a default.

Data-only: no DDL, no column added, no table created. Per CLAUDE.md's
schema-version rule this still counts as a version bump — v1.6 precedent
("No new tables or columns. Comment-level changes only") already
established that a non-DDL step bumps the version. v1.99 was the last
version before this ticket's own rollover decision (QUESTION-TICKET-0082,
block 1: `MINOR=99 -> MAJOR+1, MINOR=00`), so this is the first `v2.00`.

Idempotent: a `connects_to` relation that already has a backing fact
(`fact.relation_id` set to it) is skipped, never double-inserted — safe to
re-run after a partial failure.

Post-checks, before commit: exactly one `fact` per `connects_to` relation
(no more, no fewer — the `known_reachability.py` verify check applies the
vacuous-proof "zero relations collected = FAIL" rule; this migration script
itself does not, since a world legitimately without any `connects_to`
relation is not a migration failure), zero `fact_participant` rows created
by this run, and a checksum over the ENTIRE `relation` table identical
before and after (history is sacred — this migration inserts facts, it
must not touch a single `relation` row).

Run from the project root:

    python scripts/migrate_v2_00_connects_to_facts.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_00_connects_to_facts.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402


def _relation_checksum(cursor) -> str:
    cursor.execute(
        "SELECT id, world_id, entity_a_id, entity_b_id, type, direction, intensity, "
        "visible_to_b, notes, created_at, last_evolved_at, change_history "
        "FROM relation ORDER BY id"
    )
    payload = json.dumps(cursor.fetchall(), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _connects_to_relation_count(cursor) -> int:
    cursor.execute("SELECT COUNT(*) FROM relation WHERE type = 'connects_to'")
    return cursor.fetchone()[0]


def _relations_missing_facts(cursor) -> list[tuple]:
    cursor.execute(
        "SELECT r.id, r.world_id, ea.name, eb.name FROM relation r "
        "JOIN entity ea ON ea.id = r.entity_a_id "
        "JOIN entity eb ON eb.id = r.entity_b_id "
        "LEFT JOIN fact f ON f.relation_id = r.id "
        "WHERE r.type = 'connects_to' AND f.id IS NULL"
    )
    return cursor.fetchall()


def _backfill(cursor) -> int:
    rows = _relations_missing_facts(cursor)
    now = datetime.now(UTC).isoformat(sep=" ")
    for relation_id, world_id, name_a, name_b in rows:
        content = f"{name_a} communique avec {name_b}."
        cursor.execute(
            "INSERT INTO fact (id, world_id, relation_id, event_id, world_law_id, "
            "content, default_level, created_at, created_by, change_history) "
            "VALUES (?, ?, ?, NULL, NULL, ?, 'knows', ?, 'migrate_v2_00', '[]')",
            (str(uuid.uuid4()), world_id, relation_id, content, now),
        )
    return len(rows)


def _apply_connects_to_facts() -> tuple[int, int]:
    """Returns (connects_to_relation_count, facts_inserted_this_run). Raises
    SystemExit (after an explicit ROLLBACK) on any post-check failure —
    never commits a partial or altered `relation` table."""
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("BEGIN")

        relation_checksum_before = _relation_checksum(cursor)
        fact_participant_before = cursor.execute("SELECT COUNT(*) FROM fact_participant").fetchone()[0]

        inserted = _backfill(cursor)

        cursor.execute(
            "SELECT COUNT(*) FROM relation r WHERE r.type = 'connects_to' AND "
            "(SELECT COUNT(*) FROM fact f WHERE f.relation_id = r.id) != 1"
        )
        mismatched = cursor.fetchone()[0]
        relation_checksum_after = _relation_checksum(cursor)
        fact_participant_after = cursor.execute("SELECT COUNT(*) FROM fact_participant").fetchone()[0]

        if (
            mismatched != 0
            or relation_checksum_after != relation_checksum_before
            or fact_participant_after != fact_participant_before
        ):
            cursor.execute("ROLLBACK")
            raise SystemExit(
                "Migration v2.00 aborted, post-check failed: "
                f"connects_to relations without exactly one fact={mismatched} "
                f"relation_checksum_before={relation_checksum_before} "
                f"relation_checksum_after={relation_checksum_after} "
                f"fact_participant_before={fact_participant_before} "
                f"fact_participant_after={fact_participant_after}"
            )

        connects_to_count = _connects_to_relation_count(cursor)
        cursor.execute("COMMIT")
        cursor.close()
        print(f"Inserted {inserted} `fact` row(s) this run; {connects_to_count} `connects_to` relation(s) total.")
        print(f"relation checksum unchanged: {relation_checksum_after}")
        print(f"fact_participant count unchanged: {fact_participant_after}")
        return connects_to_count, inserted
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
            previous = row.static_version
            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
        session.commit()


def main() -> None:
    print("Migration v2.00 — connects_to facts (known-reachability floor)")
    relation_count, inserted = _apply_connects_to_facts()
    print(f"connects_to relation count={relation_count}, facts inserted this run={inserted}")
    _converge_schema_meta()
    print("\nMigration v2.00 applied.")


if __name__ == "__main__":
    main()
