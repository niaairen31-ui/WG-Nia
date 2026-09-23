"""Migration v2.06 — lore as facts: relocation and drop (TICKET-0091,
BRIEF-0091-I, contract C-18).

Moves every filled prose column and every `location_subculture` row into a
descriptive `fact` (text unchanged, L2 — outer whitespace trimmed only),
then drops the ten columns and the table. Readers and writers stopped
touching them in BRIEF-0091-E to -H; this script is the relocation.

| source                        | facet        | aspect           | default                                   |
|-------------------------------|--------------|------------------|-------------------------------------------|
| `entity.description`          | description  | —                | world/knows if `entity.is_public`         |
| `character.appearance`        | physique     | —                | rencontre/knows, scope_id = the character |
| `character.backstory`         | histoire     | —                | none                                      |
| `character.aversion`          | aversion     | —                | none                                      |
| `character.secrets`           | histoire     | —                | none + `creator_meta` knowledge (S3)      |
| `faction.philosophy`          | doctrine     | —                | world/knows                               |
| `faction.internal_structure`  | organisation | —                | none                                      |
| `faction.internal_tensions`   | tension      | —                | none                                      |
| `faction.goals`               | visee        | —                | none                                      |
| `faction.aversion`            | aversion     | —                | none                                      |
| `location_subculture` row     | coutume      | lower(trim(key)) | location/knows at itself if not hidden    |

Every fact has `created_by = 'migrate_v2_06'` and the source entity as its
one participant.

Steps, one transaction:

- S1 one fact + one participant per filled source cell.
- S2 the default of that fact, per the table.
- S3 for `character.secrets`: one `knowledge` row, entity = the character,
  `subject='creator_meta'`, `level='unaware'`, `is_secret=1` — the character
  never knows the creator's note (same shape as `writes/facets.py`).
- S7 post-checks BEFORE any drop: every filled source cell has exactly one
  matching fact (and, for `secrets`, its `creator_meta` row). A failure
  rolls everything back; nothing is dropped.
- S4 `ALTER TABLE ... DROP COLUMN` for the ten columns, `DROP TABLE
  location_subculture`.
- S5 D3b' control query: groups of facts created by this migration with an
  identical `(world_id, facet, content)` — printed, never merged.
- S6 report (per source column: created / already present).
- S8 `_converge_schema_meta()` to v2.06.

Idempotent: a source cell whose fact already exists (`created_by =
'migrate_v2_06'`, same participant, facet, aspect, content) is skipped;
`backstory` and `secrets` share the `histoire` facet, so the match is
discriminated by the presence of the `creator_meta` row. The drops are
guarded by `PRAGMA table_info` / `sqlite_master`; once they ran, there is no
source left and a second run prints zeros.

The script writes SQL; it does not import `writes/facets.py`.

Run from the project root (after `python scripts/backup.py`):

    python scripts/migrate_v2_06_lore_as_facts.py
"""

from __future__ import annotations

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
        "migrate_v2_06_lore_as_facts.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402

CREATED_BY = "migrate_v2_06"
CREATOR_META = "creator_meta"

# (table, column, facet, default) — default is None, "world", "public_world"
# (world when entity.is_public) or "rencontre" (scope_id = the entity).
COLUMN_SOURCES = (
    ("entity", "description", "description", "public_world"),
    ("character", "appearance", "physique", "rencontre"),
    ("character", "backstory", "histoire", None),
    ("character", "aversion", "aversion", None),
    ("character", "secrets", "histoire", None),
    ("faction", "philosophy", "doctrine", "world"),
    ("faction", "internal_structure", "organisation", None),
    ("faction", "internal_tensions", "tension", None),
    ("faction", "goals", "visee", None),
    ("faction", "aversion", "aversion", None),
)
SUBCULTURE = "location_subculture"


class Abort(Exception):
    """A pre- or post-check failed; the transaction is rolled back."""


def _uuid() -> str:
    return str(uuid.uuid4())


def _one(cursor, sql: str, params: tuple = ()) -> int:
    return cursor.execute(sql, params).fetchone()[0]


def _columns(cursor, table: str) -> list[str]:
    return [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]


def _table_exists(cursor, table: str) -> bool:
    return bool(_one(
        cursor, "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)))


def _aspect(key: str) -> str | None:
    """lower(trim(key)); an empty key yields no aspect."""
    return key.strip().lower() or None


# --- sources ----------------------------------------------------------------

def _cells(cursor) -> list[dict]:
    """Every filled source cell still present, as the fact it becomes."""
    cells = []
    for table, column, facet, default in COLUMN_SOURCES:
        if not _table_exists(cursor, table) or column not in _columns(cursor, table):
            continue
        rows = cursor.execute(
            f"SELECT e.id, e.world_id, e.is_public, t.{column} FROM {table} t "
            f"JOIN entity e ON e.id = t.id "
            f"WHERE t.{column} IS NOT NULL AND trim(t.{column}) != '' ORDER BY e.id"
        ).fetchall()
        for entity_id, world_id, is_public, value in rows:
            scope = None
            if default == "world" or (default == "public_world" and is_public):
                scope = ("world", None)
            elif default == "rencontre":
                scope = ("rencontre", entity_id)
            cells.append({
                "source": f"{table}.{column}", "entity_id": entity_id, "world_id": world_id,
                "facet": facet, "aspect": None, "content": value.strip(), "scope": scope,
                "creator_meta": (table, column) == ("character", "secrets"),
            })
    if _table_exists(cursor, SUBCULTURE):
        rows = cursor.execute(
            f"SELECT location_id, world_id, key, value, is_hidden FROM {SUBCULTURE} "
            "WHERE value IS NOT NULL AND trim(value) != '' ORDER BY location_id, key"
        ).fetchall()
        for location_id, world_id, key, value, is_hidden in rows:
            cells.append({
                "source": SUBCULTURE, "entity_id": location_id, "world_id": world_id,
                "facet": "coutume", "aspect": _aspect(key), "content": value.strip(),
                "scope": None if is_hidden else ("location", location_id),
                "creator_meta": False,
            })
    return cells


def _matching_facts(cursor, cell: dict) -> list[str]:
    """Facts of this migration matching the cell (idempotency key)."""
    rows = cursor.execute(
        "SELECT f.id FROM fact f JOIN fact_participant p ON p.fact_id = f.id "
        "WHERE f.created_by = ? AND p.entity_id = ? AND f.facet = ? "
        "AND f.aspect IS ? AND f.content = ?",
        (CREATED_BY, cell["entity_id"], cell["facet"], cell["aspect"], cell["content"]),
    ).fetchall()
    matches = []
    for (fact_id,) in rows:
        has_meta = bool(_one(
            cursor, "SELECT COUNT(*) FROM knowledge WHERE fact_id = ? AND entity_id = ? "
                    "AND subject = ? AND is_secret = 1",
            (fact_id, cell["entity_id"], CREATOR_META)))
        if has_meta == cell["creator_meta"]:
            matches.append(fact_id)
    return matches


# --- steps ------------------------------------------------------------------

def _relocate(cursor, cell: dict) -> None:
    """S1 fact + participant, S2 default, S3 creator_meta knowledge."""
    fact_id = _uuid()
    cursor.execute(
        "INSERT INTO fact (id, world_id, content, facet, aspect, default_level, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'unaware', ?)",
        (fact_id, cell["world_id"], cell["content"], cell["facet"], cell["aspect"], CREATED_BY))
    cursor.execute(
        "INSERT INTO fact_participant (id, world_id, fact_id, entity_id, position) "
        "VALUES (?, ?, ?, ?, 0)",
        (_uuid(), cell["world_id"], fact_id, cell["entity_id"]))
    if cell["scope"] is not None:
        scope_type, scope_id = cell["scope"]
        cursor.execute(
            "INSERT INTO fact_default (id, world_id, fact_id, scope_type, scope_id, level, created_by) "
            "VALUES (?, ?, ?, ?, ?, 'knows', ?)",
            (_uuid(), cell["world_id"], fact_id, scope_type, scope_id, CREATED_BY))
    if cell["creator_meta"]:
        cursor.execute(
            "INSERT INTO knowledge (id, entity_id, fact_id, subject, level, is_secret) "
            "VALUES (?, ?, ?, ?, 'unaware', 1)",
            (_uuid(), cell["entity_id"], fact_id, CREATOR_META))


def _relocate_all(cursor, cells: list[dict]) -> dict[str, list[int]]:
    """S1-S3. Returns {source: [created, already present]}."""
    stats: dict[str, list[int]] = {}
    for cell in cells:
        counts = stats.setdefault(cell["source"], [0, 0])
        if _matching_facts(cursor, cell):
            counts[1] += 1
            continue
        _relocate(cursor, cell)
        counts[0] += 1
    return stats


def _postcheck(cursor, cells: list[dict]) -> None:
    """S7 — runs before any drop, inside the same transaction."""
    failed = []
    for cell in cells:
        found = len(_matching_facts(cursor, cell))
        if found != 1:
            failed.append(f"{cell['source']} {cell['entity_id']} aspect={cell['aspect']!r}: {found} fact(s)")
    if failed:
        raise Abort("S7 post-check failed, nothing dropped:\n  " + "\n  ".join(failed))
    print(f"\nS7 post-checks passed: {len(cells)} filled source cell(s), one fact each.")


def _drop_sources(cursor) -> list[str]:
    """S4. Returns what was dropped."""
    dropped = []
    for table, column, _facet, _default in COLUMN_SOURCES:
        if _table_exists(cursor, table) and column in _columns(cursor, table):
            cursor.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
            dropped.append(f"{table}.{column}")
    if _table_exists(cursor, SUBCULTURE):
        cursor.execute(f"DROP TABLE {SUBCULTURE}")
        dropped.append(SUBCULTURE)
    return dropped


def _control_query(cursor) -> list[tuple]:
    """S5 — D3b': identical free facts created by this migration. Printed only."""
    return cursor.execute(
        "SELECT world_id, facet, content, COUNT(*) FROM fact "
        "WHERE created_by = ? AND relation_id IS NULL AND event_id IS NULL "
        "AND world_law_id IS NULL GROUP BY world_id, facet, content HAVING COUNT(*) > 1 "
        "ORDER BY world_id, facet, content",
        (CREATED_BY,),
    ).fetchall()


def _report(stats: dict[str, list[int]], dropped: list[str], groups: list[tuple]) -> None:
    """S6."""
    print("\nS1-S3 facts per source (created / already present):")
    total = 0
    for table, column, _facet, _default in COLUMN_SOURCES:
        created, present = stats.get(f"{table}.{column}", [0, 0])
        total += created
        print(f"  {table}.{column}: {created} / {present}")
    created, present = stats.get(SUBCULTURE, [0, 0])
    total += created
    print(f"  {SUBCULTURE}: {created} / {present}")
    print(f"S1-S3 facts created this run: {total}")
    print(f"S4 dropped: {len(dropped)} {dropped}")
    print(f"S5 D3b' groups of identical free facts (world, facet, content): {len(groups)}")
    for world_id, facet, content, count in groups:
        print(f"  [{world_id}] {facet} x{count}: {content[:80]!r}")


# --- driver -----------------------------------------------------------------

def _apply() -> None:
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("BEGIN")
        try:
            cells = _cells(cursor)
            stats = _relocate_all(cursor, cells)
            _postcheck(cursor, cells)
            dropped = _drop_sources(cursor)
            groups = _control_query(cursor)
            _report(stats, dropped, groups)
        except Abort as exc:
            cursor.execute("ROLLBACK")
            raise SystemExit(f"Migration v2.06 aborted, rolled back. {exc}") from None
        cursor.execute("COMMIT")
        cursor.close()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _converge_schema_meta() -> None:
    """S8."""
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
    print("Migration v2.06 — lore as facts: relocation and drop")
    _apply()
    _converge_schema_meta()
    print("\nMigration v2.06 applied.")


if __name__ == "__main__":
    main()
