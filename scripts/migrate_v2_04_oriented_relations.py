"""Migration v2.04 — perceiver-oriented relations (TICKET-0090, BRIEF-0090-b).

Normalizes every social `relation` row (any `type` outside
`relation_orientation.RELATION_GRAPH_EXCLUDED_TYPES`) to one perceiver:
`direction = 'a_to_b'`, `entity_a` feels, `entity_b` receives. Then gives
every social relation its typed `lien` fact, backfills the `connects_to`
edges born after v2.00 without a fact, converts the reviewed directed
`visible_to_b = TRUE` values into knowledge rows (decision U3), and closes
the schema with the partial unique index `idx_relation_oriented_social`.

Steps, one transaction:

- S0 snapshot: social counts by (`direction`, `visible_to_b`); the id sets of
  `a_to_b` + TRUE and `b_to_a` + TRUE rows, captured BEFORE any change.
- S1 pre-check: an unknown `direction`, a duplicated oriented pair, or a
  social relation holding more than one fact aborts (ROLLBACK + SystemExit).
- S2 `b_to_a`: endpoints swapped, `direction = 'a_to_b'`.
- S3 `mutual`: `direction = 'a_to_b'`, plus a mirror row (endpoints swapped).
- S4 lien facts (C-01, `default_level = 'unaware'`).
- S5 `connects_to` facts (C-02, `default_level = 'knows'`, as v2.00).
- S6 U3: one `knowledge` row for `entity_b` on the lien fact of every S0
  `a_to_b` + TRUE row. `b_to_a` + TRUE rows are reported, never converted
  (the flag has no defined meaning on that shape); `mutual` values are
  dropped (they carry no information).
- S7 index (C-12). S8 report. S9 post-checks before COMMIT.
- S10 `_converge_schema_meta()`, as v2.00.

History is sacred: every row changed by S2/S3 gets its previous endpoints
and direction appended to `change_history` (`_append_history_snapshot`'s
shape does not carry them, so the entry is written here). `controls` and
`connects_to` rows are never modified — checksummed before and after.

Idempotent: every insert is guarded by `NOT EXISTS`, S2/S3 act only on
non-normalized directions, and S0 never re-captures a row that already
carries a v2.04 history entry (the swapped `b_to_a` and split `mutual` rows
keep their legacy `visible_to_b`, which U3 must not convert). A second run
prints zeros and changes no row.

Run from the project root:

    python scripts/migrate_v2_04_oriented_relations.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_04_oriented_relations.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.relation_orientation import (  # noqa: E402
    RELATION_GRAPH_EXCLUDED_TYPES,
    connects_to_fact_content,
    lien_fact_content,
    orient_legacy,
)
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

CREATED_BY = "migrate_v2_04"
KNOWLEDGE_SOURCE = "migrate_v2_04 (visible_to_b)"
INDEX_NAME = "idx_relation_oriented_social"
LEGACY_DIRECTIONS = ("a_to_b", "b_to_a", "mutual")

_EXCLUDED_SQL = ",".join(f"'{t}'" for t in RELATION_GRAPH_EXCLUDED_TYPES)
SOCIAL = f"type NOT IN ({_EXCLUDED_SQL})"
INDEX_DDL = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} "
    f"ON relation(entity_a_id, entity_b_id) WHERE {SOCIAL}"
)


class Abort(Exception):
    """A pre- or post-check failed; the transaction is rolled back."""


def _now() -> str:
    return datetime.now(UTC).isoformat(sep=" ")


def _history(raw) -> list:
    if raw is None:
        return []
    return json.loads(raw) if isinstance(raw, str) else list(raw)


def _carries_v2_04(raw) -> bool:
    return any(isinstance(e, dict) and e.get("migration") == "v2.04" for e in _history(raw))


def _names(cursor) -> dict[str, str]:
    return dict(cursor.execute("SELECT id, name FROM entity").fetchall())


def _structural_checksum(cursor) -> str:
    rows = cursor.execute(
        "SELECT id, world_id, entity_a_id, entity_b_id, type, direction, intensity, "
        "visible_to_b, notes, created_at, last_evolved_at, change_history "
        f"FROM relation WHERE NOT ({SOCIAL}) ORDER BY id"
    ).fetchall()
    return hashlib.sha256(json.dumps(rows, default=str).encode("utf-8")).hexdigest()


# --- S0 / S1 ----------------------------------------------------------------

def _snapshot(cursor) -> dict:
    rows = cursor.execute(
        "SELECT id, entity_a_id, entity_b_id, direction, visible_to_b, change_history "
        f"FROM relation WHERE {SOCIAL}"
    ).fetchall()
    counts = Counter((r[3], int(bool(r[4]))) for r in rows)
    a_true = [r[0] for r in rows if r[3] == "a_to_b" and r[4] and not _carries_v2_04(r[5])]
    b_true = [(r[0], r[2], r[1]) for r in rows if r[3] == "b_to_a" and r[4]]
    return {
        "rows": rows,
        "counts": counts,
        "social": len(rows),
        "mutual": sum(1 for r in rows if r[3] == "mutual"),
        "a_true": a_true,
        "b_true": b_true,  # (id, perceiver_id, target_id)
    }


def _precheck(cursor, snap: dict) -> None:
    unknown = [(r[0], r[3]) for r in snap["rows"] if r[3] not in LEGACY_DIRECTIONS]
    if unknown:
        raise Abort(f"S1: unknown direction value(s) on social rows: {unknown}")
    pairs = Counter()
    for rid, a, b, direction, visible, _ in snap["rows"]:
        for spec in orient_legacy(direction, a, b, bool(visible)):
            pairs[(spec.perceiver_id, spec.target_id)] += 1
    dupes = [pair for pair, n in pairs.items() if n > 1]
    if dupes:
        names = _names(cursor)
        listed = [f"{names.get(a, a)} -> {names.get(b, b)}" for a, b in dupes]
        raise Abort(f"S1: duplicated oriented pair(s): {listed}")
    multi = cursor.execute(
        f"SELECT r.id, COUNT(f.id) FROM relation r JOIN fact f ON f.relation_id = r.id "
        f"WHERE r.{SOCIAL} GROUP BY r.id HAVING COUNT(f.id) > 1"
    ).fetchall()
    if multi:
        raise Abort(f"S1: social relation(s) with more than one typed fact: {multi}")


# --- S2 / S3 ----------------------------------------------------------------

def _was(a: str, b: str, direction: str) -> dict:
    return {"migration": "v2.04", "was": {"entity_a_id": a, "entity_b_id": b, "direction": direction}}


def _swap_b_to_a(cursor) -> int:
    rows = cursor.execute(
        "SELECT id, entity_a_id, entity_b_id, change_history FROM relation "
        f"WHERE {SOCIAL} AND direction = 'b_to_a'"
    ).fetchall()
    for rid, a, b, hist in rows:
        entries = _history(hist) + [_was(a, b, "b_to_a")]
        cursor.execute(
            "UPDATE relation SET entity_a_id = ?, entity_b_id = ?, direction = 'a_to_b', "
            "change_history = ? WHERE id = ?",
            (b, a, json.dumps(entries), rid),
        )
    return len(rows)


def _split_mutual(cursor) -> int:
    rows = cursor.execute(
        "SELECT id, world_id, entity_a_id, entity_b_id, type, intensity, visible_to_b, "
        "notes, created_at, last_evolved_at, change_history FROM relation "
        f"WHERE {SOCIAL} AND direction = 'mutual'"
    ).fetchall()
    for rid, world, a, b, rtype, intensity, visible, notes, created, evolved, hist in rows:
        entries = _history(hist) + [_was(a, b, "mutual")]
        cursor.execute(
            "UPDATE relation SET direction = 'a_to_b', change_history = ? WHERE id = ?",
            (json.dumps(entries), rid),
        )
        cursor.execute(
            "INSERT INTO relation (id, world_id, entity_a_id, entity_b_id, type, direction, "
            "intensity, visible_to_b, notes, created_at, last_evolved_at, change_history) "
            "VALUES (?, ?, ?, ?, ?, 'a_to_b', ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), world, b, a, rtype, intensity, visible, notes, created,
             evolved, json.dumps([{"migration": "v2.04", "split_from": rid}])),
        )
    return len(rows)


# --- S4 / S5 ----------------------------------------------------------------

def _factless(cursor, where: str) -> list[tuple]:
    return cursor.execute(
        "SELECT r.id, r.world_id, r.entity_a_id, r.entity_b_id, r.type FROM relation r "
        f"WHERE r.{where} AND NOT EXISTS (SELECT 1 FROM fact f WHERE f.relation_id = r.id)"
    ).fetchall()


def _insert_fact(cursor, world: str, relation_id: str, content: str, level: str) -> None:
    cursor.execute(
        "INSERT INTO fact (id, world_id, relation_id, event_id, world_law_id, content, "
        "default_level, created_at, created_by, change_history) "
        "VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, '[]')",
        (str(uuid.uuid4()), world, relation_id, content, level, _now(), CREATED_BY),
    )


def _backfill_facts(cursor, names: dict, nameless: list) -> tuple[int, int]:
    def name(eid: str, rid: str) -> str:
        if names.get(eid):
            return names[eid]
        nameless.append((rid, eid))
        return eid

    lien = _factless(cursor, SOCIAL)
    for rid, world, a, b, rtype in lien:
        _insert_fact(cursor, world, rid, lien_fact_content(name(a, rid), rtype, name(b, rid)), "unaware")
    edges = _factless(cursor, "type = 'connects_to'")
    for rid, world, a, b, _ in edges:
        _insert_fact(cursor, world, rid, connects_to_fact_content(name(a, rid), name(b, rid)), "knows")
    return len(lien), len(edges)


# --- S6 ---------------------------------------------------------------------

def _convert_visibility(cursor, a_true: list[str]) -> list[str]:
    """Returns the relation ids converted THIS run."""
    converted = []
    for rid in a_true:
        target, fact_id, content = cursor.execute(
            "SELECT r.entity_b_id, f.id, f.content FROM relation r "
            "JOIN fact f ON f.relation_id = r.id WHERE r.id = ?",
            (rid,),
        ).fetchone()
        exists = cursor.execute(
            "SELECT 1 FROM knowledge WHERE entity_id = ? AND fact_id = ?", (target, fact_id)
        ).fetchone()
        if exists:
            continue
        now = _now()
        cursor.execute(
            "INSERT INTO knowledge (id, entity_id, fact_id, subject, level, content, source, "
            "is_incorrect, is_secret, share_threshold, acquired_at, updated_at, session_id, "
            "change_history) VALUES (?, ?, ?, ?, 'knows', ?, ?, 0, 0, 50, ?, ?, NULL, '[]')",
            (str(uuid.uuid4()), target, fact_id, content, content, KNOWLEDGE_SOURCE, now, now),
        )
        converted.append(rid)
    return converted


# --- S8 / S9 ----------------------------------------------------------------

def _report(cursor, snap: dict, stats: dict, converted: list[str], nameless: list) -> None:
    names = _names(cursor)
    print("S0 social rows by (direction, visible_to_b):")
    for (direction, visible), n in sorted(snap["counts"].items()):
        print(f"  {direction:<7} {visible}  {n}")
    print("  (R-25 fingerprint, prod 2026-09-22: a_to_b 0/52 1/40, b_to_a 0/8 1/6, mutual 1/67)")
    print(f"S8 rows swapped (b_to_a)        : {stats['swapped']}")
    print(f"S8 rows split (mutual)          : {stats['split']}")
    print(f"S8 lien facts inserted          : {stats['lien']}")
    print(f"S8 connects_to facts inserted   : {stats['edges']}")
    print(f"S8 knowledge rows inserted (U3) : {len(converted)}")
    print(f"S8 mutual visible_to_b dropped  : {stats['split']} (no information on a mutual row)")
    print(
        f"\nb_to_a rows with visible_to_b=TRUE ({len(snap['b_true'])}): visibility NOT converted — "
        "the flag has no defined meaning on that shape; the sheet's \"X le sait\" control sets it."
    )
    for rid, perceiver, target in snap["b_true"]:
        print(f"  {rid}  {names.get(perceiver, perceiver)} -> {names.get(target, target)}")
    pcs = {r[0] for r in cursor.execute("SELECT id FROM character WHERE character_type = 'player'")}
    pc_rows = [
        cursor.execute("SELECT entity_a_id, entity_b_id FROM relation WHERE id = ?", (rid,)).fetchone()
        for rid in converted
    ]
    pc_rows = [(a, b) for a, b in pc_rows if b in pcs]
    print(f"\nConverted rows targeting a player character ({len(pc_rows)}): the player now knows that feeling.")
    for a, b in pc_rows:
        print(f"  {names.get(a, a)} -> {names.get(b, b)}")
    if nameless:
        print(f"\nRelations whose endpoint has no name — entity id used in the fact ({len(nameless)}):")
        for rid, eid in nameless:
            print(f"  relation {rid}: entity {eid}")
    null_notes = cursor.execute(f"SELECT COUNT(*) FROM relation WHERE {SOCIAL} AND notes IS NULL").fetchone()[0]
    controls_bare = cursor.execute(
        "SELECT COUNT(*) FROM relation r WHERE r.type = 'controls' "
        "AND NOT EXISTS (SELECT 1 FROM fact f WHERE f.relation_id = r.id)"
    ).fetchone()[0]
    print(f"\nReport-only: social rows with NULL notes = {null_notes}; "
          f"controls relations without a fact (by design) = {controls_bare}")


def _postcheck(cursor, snap: dict, checksum_before: str) -> None:
    def one(sql: str) -> int:
        return cursor.execute(sql).fetchone()[0]

    problems = {
        "social rows with direction != a_to_b": one(
            f"SELECT COUNT(*) FROM relation WHERE {SOCIAL} AND direction != 'a_to_b'"),
        "social rows without exactly one fact": one(
            f"SELECT COUNT(*) FROM relation r WHERE r.{SOCIAL} AND "
            "(SELECT COUNT(*) FROM fact f WHERE f.relation_id = r.id) != 1"),
        "connects_to rows without exactly one fact": one(
            "SELECT COUNT(*) FROM relation r WHERE r.type = 'connects_to' AND "
            "(SELECT COUNT(*) FROM fact f WHERE f.relation_id = r.id) != 1"),
        "controls rows with a fact": one(
            "SELECT COUNT(*) FROM relation r WHERE r.type = 'controls' AND "
            "EXISTS (SELECT 1 FROM fact f WHERE f.relation_id = r.id)"),
        "index missing": 0 if one(
            f"SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name = '{INDEX_NAME}'") else 1,
        "structural rows changed": 0 if _structural_checksum(cursor) == checksum_before else 1,
    }
    social_after = one(f"SELECT COUNT(*) FROM relation WHERE {SOCIAL}")
    knowledge_after = one(f"SELECT COUNT(*) FROM knowledge WHERE source = '{KNOWLEDGE_SOURCE}'")
    expected_social = snap["social"] + snap["mutual"]
    failed = {k: v for k, v in problems.items() if v}
    if social_after != expected_social:
        failed["social count"] = f"{social_after} != S0 {snap['social']} + mutual {snap['mutual']}"
    if knowledge_after != len(snap["a_true"]):
        failed["U3 knowledge count"] = f"{knowledge_after} != S0 a_to_b+TRUE {len(snap['a_true'])}"
    if failed:
        raise Abort(f"S9 post-check failed: {failed}")
    print(f"\nS9 post-checks passed: social rows={social_after}, U3 knowledge rows={knowledge_after}, "
          f"{INDEX_NAME} present, structural rows unchanged.")


# --- driver -----------------------------------------------------------------

def _apply() -> None:
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("BEGIN")
        try:
            checksum_before = _structural_checksum(cursor)
            snap = _snapshot(cursor)
            _precheck(cursor, snap)
            nameless: list = []
            stats = {"swapped": _swap_b_to_a(cursor), "split": _split_mutual(cursor)}
            stats["lien"], stats["edges"] = _backfill_facts(cursor, _names(cursor), nameless)
            converted = _convert_visibility(cursor, snap["a_true"])
            cursor.execute(INDEX_DDL)
            _report(cursor, snap, stats, converted, nameless)
            _postcheck(cursor, snap, checksum_before)
        except Abort as exc:
            cursor.execute("ROLLBACK")
            raise SystemExit(f"Migration v2.04 aborted, rolled back. {exc}") from None
        cursor.execute("COMMIT")
        cursor.close()
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
    print("Migration v2.04 — perceiver-oriented relations")
    _apply()
    _converge_schema_meta()
    print("\nMigration v2.04 applied.")


if __name__ == "__main__":
    main()
