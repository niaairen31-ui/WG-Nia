"""Migration v2.08 — the K1 review record (TICKET-0095, BRIEF-0095-A).

Creates three tables (C-01):

- `day_mention_choice_candidate` (`id, choice_id, ordinal, entity_id`) and
  its unique index `idx_day_mention_choice_candidate_choice(choice_id,
  ordinal)`;
- `day_mention_choice_evidence` (`id, choice_id, ordinal, fact_id` — no FK on
  `fact_id`) and its unique index `idx_day_mention_choice_evidence_choice
  (choice_id, ordinal)`;
- `day_mention_review` (`id, world_id, choice_id, verdict, entity_id,
  appellation_fact_id, appellation_scope, created_at`) with its verdict,
  scope and shape CHECKs, and the index `idx_day_mention_review_choice`.

The two child tables are created AND backfilled in ONE transaction from
every existing `day_mention_choice` row: one candidate row per id of its
`candidate_ids` JSON list, one evidence row per id of its
`evidence_fact_ids` JSON list, `ordinal` = position in the list, from 1.
`day_mention_choice` itself is only read — never altered, never rewritten;
its JSON columns stay as an audit copy.

Aborts, writing nothing, when a JSON value is not a list of str, or when a
candidate id is not an `entity.id` — both checked before the first INSERT.

Idempotent, per (b5):
- both child tables absent -> create both + backfill, one transaction;
- both present -> skip them;
- exactly one present -> abort, no write (impossible after an atomic run);
- review table absent -> create it; present -> skip it.

Post-checks: on every run, candidate row count == sum of
len(candidate_ids) and evidence row count == sum of len(evidence_fact_ids)
over every choice; on the run that creates it, `day_mention_review` holds
0 rows.

Run from the project root:

    python scripts/migrate_v2_08_choice_review.py
"""

from __future__ import annotations

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
        "migrate_v2_08_choice_review.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlalchemy import inspect, text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

_CANDIDATE_TABLE = "day_mention_choice_candidate"
_EVIDENCE_TABLE = "day_mention_choice_evidence"
_REVIEW_TABLE = "day_mention_review"

_CHILD_DDL: tuple[str, ...] = (
    """
CREATE TABLE day_mention_choice_candidate (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  entity_id  TEXT NOT NULL REFERENCES entity(id)
)
""",
    """
CREATE UNIQUE INDEX idx_day_mention_choice_candidate_choice
  ON day_mention_choice_candidate(choice_id, ordinal)
""",
    """
CREATE TABLE day_mention_choice_evidence (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  fact_id    TEXT NOT NULL    -- no FK: a descriptive fact can be hard-deleted (R-04)
)
""",
    """
CREATE UNIQUE INDEX idx_day_mention_choice_evidence_choice
  ON day_mention_choice_evidence(choice_id, ordinal)
""",
)

_REVIEW_DDL: tuple[str, ...] = (
    """
CREATE TABLE day_mention_review (
  id                   TEXT PRIMARY KEY,
  world_id             TEXT NOT NULL REFERENCES world(id),
  choice_id            TEXT NOT NULL REFERENCES day_mention_choice(id),
  verdict              TEXT NOT NULL CHECK (verdict IN ('agreed','disagreed')),
  entity_id            TEXT REFERENCES entity(id),
  appellation_fact_id  TEXT,  -- no FK: the appellation can be hard-deleted later (R-04)
  appellation_scope    TEXT CHECK (appellation_scope IS NULL
                                   OR appellation_scope IN ('rencontre','world','none')),
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (verdict <> 'agreed' OR entity_id IS NOT NULL)
    AND (appellation_fact_id IS NULL OR entity_id IS NOT NULL)
    AND ((appellation_fact_id IS NULL) = (appellation_scope IS NULL))
  )
)
""",
    "CREATE INDEX idx_day_mention_review_choice ON day_mention_review(choice_id)",
)


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def _backfill(conn) -> tuple[int, int]:
    choices = conn.execute(text(
        "SELECT id, candidate_ids, evidence_fact_ids FROM day_mention_choice ORDER BY created_at, id"
    )).all()

    parsed: list[tuple[str, list[str], list[str]]] = []
    for choice_id, candidate_raw, evidence_raw in choices:
        lists: list[list[str]] = []
        for column, raw in (("candidate_ids", candidate_raw), ("evidence_fact_ids", evidence_raw)):
            try:
                value = json.loads(raw)
            except (TypeError, ValueError):
                value = None
            if not _is_str_list(value):
                raise SystemExit(
                    f"Migration v2.08 aborted: day_mention_choice {choice_id} {column} "
                    f"is not a JSON list of str"
                )
            lists.append(value)
        parsed.append((choice_id, lists[0], lists[1]))

    entity_ids = {row[0] for row in conn.execute(text("SELECT id FROM entity"))}
    missing = {e for _, candidates, _ in parsed for e in candidates if e not in entity_ids}
    if missing:
        raise SystemExit(f"Migration v2.08 aborted: candidate ids not in entity: {sorted(missing)}")

    candidate_rows = 0
    evidence_rows = 0
    for choice_id, candidates, evidence in parsed:
        for ordinal, entity_id in enumerate(candidates, start=1):
            conn.execute(
                text(
                    "INSERT INTO day_mention_choice_candidate (id, choice_id, ordinal, entity_id) "
                    "VALUES (:id, :choice_id, :ordinal, :entity_id)"
                ),
                {"id": str(uuid.uuid4()), "choice_id": choice_id, "ordinal": ordinal, "entity_id": entity_id},
            )
            candidate_rows += 1
        for ordinal, fact_id in enumerate(evidence, start=1):
            conn.execute(
                text(
                    "INSERT INTO day_mention_choice_evidence (id, choice_id, ordinal, fact_id) "
                    "VALUES (:id, :choice_id, :ordinal, :fact_id)"
                ),
                {"id": str(uuid.uuid4()), "choice_id": choice_id, "ordinal": ordinal, "fact_id": fact_id},
            )
            evidence_rows += 1
    return candidate_rows, evidence_rows


def _apply_ddl() -> bool:
    tables = set(inspect(engine).get_table_names())
    has_candidate = _CANDIDATE_TABLE in tables
    has_evidence = _EVIDENCE_TABLE in tables

    if not has_candidate and not has_evidence:
        with engine.begin() as conn:
            for statement in _CHILD_DDL:
                conn.execute(text(statement))
            candidate_rows, evidence_rows = _backfill(conn)
        print(f"Backfilled {candidate_rows} candidate row(s) and {evidence_rows} evidence row(s).")
    elif has_candidate and has_evidence:
        print(f"Tables '{_CANDIDATE_TABLE}' and '{_EVIDENCE_TABLE}' already exist — nothing to do.")
    else:
        raise SystemExit(
            "Migration v2.08 aborted: exactly one of the two child tables exists — "
            "investigate before re-running"
        )

    if _REVIEW_TABLE not in tables:
        with engine.begin() as conn:
            for statement in _REVIEW_DDL:
                conn.execute(text(statement))
        print(f"Created table '{_REVIEW_TABLE}' + its index.")
        return True
    print(f"Table '{_REVIEW_TABLE}' already exists — nothing to do.")
    return False


def _post_checks(review_created: bool) -> None:
    with engine.connect() as conn:
        choices = conn.execute(text("SELECT candidate_ids, evidence_fact_ids FROM day_mention_choice")).all()
        expected_candidates = sum(len(json.loads(c)) for c, _ in choices)
        expected_evidence = sum(len(json.loads(e)) for _, e in choices)
        candidate_rows = conn.execute(text("SELECT COUNT(*) FROM day_mention_choice_candidate")).scalar()
        evidence_rows = conn.execute(text("SELECT COUNT(*) FROM day_mention_choice_evidence")).scalar()
        review_rows = conn.execute(text("SELECT COUNT(*) FROM day_mention_review")).scalar()

    if candidate_rows != expected_candidates:
        raise SystemExit(
            f"Migration v2.08 aborted, post-check failed: day_mention_choice_candidate holds "
            f"{candidate_rows} row(s), expected {expected_candidates}."
        )
    print(f"Post-check: day_mention_choice_candidate row count = {candidate_rows} (expected {expected_candidates}).")

    if evidence_rows != expected_evidence:
        raise SystemExit(
            f"Migration v2.08 aborted, post-check failed: day_mention_choice_evidence holds "
            f"{evidence_rows} row(s), expected {expected_evidence}."
        )
    print(f"Post-check: day_mention_choice_evidence row count = {evidence_rows} (expected {expected_evidence}).")

    if review_created:
        if review_rows != 0:
            raise SystemExit(
                f"Migration v2.08 aborted, post-check failed: day_mention_review row count "
                f"is {review_rows}, expected 0 — this migration must create zero review rows."
            )
        print(f"Post-check: day_mention_review row count = {review_rows} (expected 0).")


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
    print("Migration v2.08 — choice review")

    review_created = _apply_ddl()
    _post_checks(review_created)
    _converge_schema_meta()
    print("\nMigration v2.08 applied.")


if __name__ == "__main__":
    main()
