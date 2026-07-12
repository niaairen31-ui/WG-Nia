"""Migration to schema v1.77 — `character.physical_tier` column +
`npc_price` relational table replace `entity.metadata['physical_tier']` and
`entity.metadata['price_list']` (TICKET-0025, BRIEF-0025-a).

TICKET-0024's duplication bug was caused by a UI field (`roles`) living
inside `entity.metadata`, invisible to RECON's column-grepping. TICKET-0025
extracts every remaining UI-visible `entity.metadata` key to relational
storage and drops the column outright — the two keys still in live use are
`physical_tier` (NPC sheet "Carrure", opposed-roll reader) and `price_list`
(Tarifs editor, seller-tariff prompt injection).

In ONE transaction:
  a. Add `character.physical_tier` (server default 0); create `npc_price` +
     unique index `idx_npc_price_tag (entity_id, tag COLLATE NOCASE)`.
  b. For every entity: copy `metadata['physical_tier']` (int) into the
     `character` row; copy `metadata['price_list']` entries into `npc_price`
     rows (provenance `migration:0025-a` is logged, not stored — no such
     column exists on `npc_price`).
  c. Drop `entity.metadata` (SQLite `ALTER TABLE ... DROP COLUMN`, supported
     >= 3.35; guarded, aborts with instructions otherwise).

Read-only validation pass BEFORE any write, fail-closed:
  - any entity whose `metadata` contains a key OTHER than `physical_tier` /
    `price_list` aborts the WHOLE migration, listing entity id + offending
    keys — unknown data is never silently dropped.
  - a `physical_tier` or `price_list` key on an entity with NO `character`
    row (the columns/table these keys migrate to are character-only) aborts
    the WHOLE migration, listing the entity id.
  - a malformed `physical_tier` (not an int) or `price_list` (not a flat
    dict of string -> int/float) aborts likewise.

Idempotent: safe to re-run — skips entirely once `npc_price` exists (the
whole migration is one transaction, so a completed run is all-or-nothing).

Run from the project root:
    python scripts/migrate_v1_77_metadata_extraction.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from numbers import Real
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402

MIN_SQLITE_VERSION = (3, 35)
_ALLOWED_METADATA_KEYS = {"physical_tier", "price_list"}


def _load_entities(conn) -> list[dict]:
    rows = conn.execute(text(
        "SELECT e.id AS id, e.name AS name, e.metadata AS metadata, "
        "c.id AS character_id "
        "FROM entity e LEFT JOIN character c ON c.id = e.id "
        "WHERE e.metadata IS NOT NULL"
    )).mappings().all()

    entities = []
    for row in rows:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        if not isinstance(metadata, dict):
            metadata = {}
        entities.append({
            "id": row["id"],
            "name": row["name"],
            "metadata": metadata,
            "is_character": row["character_id"] is not None,
        })
    return entities


def _validate(entities: list[dict]) -> tuple[dict[str, int], list[tuple[str, str, int]], list[str]]:
    """Fail-closed validation pass. Returns (physical_tier updates keyed by
    entity id, price rows as (entity_id, tag, amount) tuples, problems)."""
    physical_tier_updates: dict[str, int] = {}
    price_rows: list[tuple[str, str, int]] = []
    problems: list[str] = []

    for entity in entities:
        unknown_keys = set(entity["metadata"]) - _ALLOWED_METADATA_KEYS
        if unknown_keys:
            problems.append(
                f"{entity['id']} ({entity['name']!r}): unexpected metadata key(s) "
                f"{sorted(unknown_keys)}"
            )
            continue

        if not entity["metadata"]:
            continue

        if not entity["is_character"]:
            problems.append(
                f"{entity['id']} ({entity['name']!r}): carries "
                f"{sorted(entity['metadata'])} but is not a character"
            )
            continue

        if "physical_tier" in entity["metadata"]:
            value = entity["metadata"]["physical_tier"]
            if not isinstance(value, int) or isinstance(value, bool):
                problems.append(
                    f"{entity['id']} ({entity['name']!r}): physical_tier "
                    f"{value!r} is not an int"
                )
            else:
                physical_tier_updates[entity["id"]] = value

        if "price_list" in entity["metadata"]:
            price_list = entity["metadata"]["price_list"]
            if not isinstance(price_list, dict):
                problems.append(
                    f"{entity['id']} ({entity['name']!r}): price_list is not a dict"
                )
                continue
            for tag, amount in price_list.items():
                if not isinstance(tag, str) or not tag.strip():
                    problems.append(
                        f"{entity['id']} ({entity['name']!r}): price_list has a "
                        f"non-string or empty tag {tag!r}"
                    )
                    continue
                if not isinstance(amount, Real) or isinstance(amount, bool):
                    problems.append(
                        f"{entity['id']} ({entity['name']!r}): price_list[{tag!r}] "
                        f"= {amount!r} is not a number"
                    )
                    continue
                price_rows.append((entity["id"], tag.strip(), int(amount)))

    return physical_tier_updates, price_rows, problems


def _create_npc_price_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE npc_price (
          id         TEXT PRIMARY KEY,
          world_id   TEXT NOT NULL REFERENCES world(id),
          entity_id  TEXT NOT NULL REFERENCES entity(id),
          tag        TEXT NOT NULL,
          amount     INTEGER NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_npc_price_tag "
        "ON npc_price(entity_id, tag COLLATE NOCASE)"
    ))


def _add_physical_tier_column(conn) -> None:
    conn.execute(text(
        "ALTER TABLE character ADD COLUMN physical_tier INTEGER NOT NULL DEFAULT 0"
    ))


def _apply_physical_tier(conn, updates: dict[str, int]) -> None:
    for entity_id, value in updates.items():
        conn.execute(text(
            "UPDATE character SET physical_tier = :value WHERE id = :id"
        ), {"value": value, "id": entity_id})


def _insert_prices(conn, price_rows: list[tuple[str, str, int]]) -> None:
    for entity_id, tag, amount in price_rows:
        world_id = conn.execute(text(
            "SELECT world_id FROM entity WHERE id = :id"
        ), {"id": entity_id}).scalar_one()
        conn.execute(text(
            "INSERT INTO npc_price (id, world_id, entity_id, tag, amount) "
            "VALUES (:id, :world_id, :entity_id, :tag, :amount)"
        ), {
            "id": str(uuid.uuid4()),
            "world_id": world_id,
            "entity_id": entity_id,
            "tag": tag,
            "amount": amount,
        })


def _drop_metadata_column(conn) -> None:
    conn.execute(text("ALTER TABLE entity DROP COLUMN metadata"))


def main() -> None:
    inspector = inspect(engine)
    if "npc_price" in inspector.get_table_names():
        print("Table 'npc_price' already exists — migration already applied, skipping.")
        return

    if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
        raise SystemExit(
            f"SQLite {'.'.join(map(str, MIN_SQLITE_VERSION))}+ is required for "
            f"ALTER TABLE ... DROP COLUMN (found {sqlite3.sqlite_version}). "
            "Upgrade SQLite, then re-run this migration — aborting, nothing written."
        )

    with engine.connect() as conn:
        entities = _load_entities(conn)

    physical_tier_updates, price_rows, problems = _validate(entities)

    if problems:
        raise SystemExit(
            "Migration aborted — unexpected metadata content found, nothing written:\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\nResolve in the live UI, then re-run."
        )

    with engine.begin() as conn:
        _add_physical_tier_column(conn)
        _create_npc_price_table(conn)
        _apply_physical_tier(conn, physical_tier_updates)
        _insert_prices(conn, price_rows)
        _drop_metadata_column(conn)

    print(
        f"Migration v1.77 applied: character.physical_tier column + npc_price table "
        f"+ index created, {len(physical_tier_updates)} physical_tier value(s) migrated "
        f"(provenance migration:0025-a), {len(price_rows)} price row(s) inserted across "
        f"{len({r[0] for r in price_rows})} character(s), entity.metadata column dropped."
    )


if __name__ == "__main__":
    main()
