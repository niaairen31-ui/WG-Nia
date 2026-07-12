"""Migration to schema v1.76 — `faction_role` relational table replaces
`faction.role_capacities` (JSON) + `entity.metadata['roles']`
(TICKET-0024, BRIEF-0024-d, corrective).

RECON-after-the-fact found BRIEF-0024-a built `faction.role_capacities`
UNAWARE of the pre-existing declared-role structure,
`entity.metadata['roles']` (BRIEF-31, schema v1.42) — two disconnected role
vocabularies on the same faction sheet. This migration merges both into one
relational table, `faction_role`, and removes the two JSON sources.

In ONE transaction:
  a. Create `faction_role` + unique index
     `idx_faction_role_name (faction_id, name COLLATE NOCASE)`.
  b. For every faction entity, copy `metadata['roles']` entries in array
     order -> rows (`position` = array index, `description` preserved,
     `max_holders` NULL, `created_by='migration:0024-d'`).
  c. Merge `faction.role_capacities` limits INTO those rows by casefold
     name match; a capacity key with NO matching metadata role becomes a
     NEW row (appended after the metadata ones, `description` NULL).
  d. A casefold collision inside a single faction's sources aborts the
     WHOLE migration, nothing written — validated in a read-only pass
     BEFORE any write.
  e. Strip the `roles` key from `entity.metadata` (whole-value
     reassignment, never an in-place mutation).
  f. Drop `faction.role_capacities` (SQLite `ALTER TABLE ... DROP COLUMN`,
     supported >= 3.35; guarded, aborts with instructions otherwise).

Idempotent: safe to re-run — skips entirely once `faction_role` exists (the
whole migration is one transaction, so a completed run is all-or-nothing).

Run from the project root:
    python scripts/migrate_v1_76_faction_role_table.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402

MIN_SQLITE_VERSION = (3, 35)


def _load_factions(conn) -> list[dict]:
    """Every faction entity's raw sources: metadata['roles'] list and
    faction.role_capacities dict, plus whether metadata had a 'roles' key
    at all (so stripping doesn't touch factions that never had one)."""
    rows = conn.execute(text(
        "SELECT e.id AS id, e.name AS name, e.metadata AS metadata, "
        "f.role_capacities AS role_capacities "
        "FROM entity e JOIN faction f ON f.id = e.id "
        "WHERE e.type = 'faction'"
    )).mappings().all()

    factions = []
    for row in rows:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        if not isinstance(metadata, dict):
            metadata = {}
        metadata_roles = metadata.get("roles")
        if not isinstance(metadata_roles, list):
            metadata_roles = []
        capacities = json.loads(row["role_capacities"]) if row["role_capacities"] else {}
        if not isinstance(capacities, dict):
            capacities = {}
        factions.append({
            "id": row["id"],
            "name": row["name"],
            "metadata_roles": metadata_roles,
            "capacities": capacities,
            "had_metadata_roles_key": "roles" in metadata,
        })
    return factions


def _plan_faction_roles(faction: dict) -> list[dict]:
    """Merge one faction's metadata roles + role_capacities into an ordered
    list of row dicts {name, description, max_holders}.

    Raises ValueError (readable, faction name included) on a casefold
    collision inside this faction's own sources — either two metadata role
    names, or two role_capacities keys, differing only by case. A
    capacities key that casefold-matches an existing metadata row is a
    legitimate MERGE, not a collision.
    """
    rows: list[dict] = []
    metadata_casefold: dict[str, int] = {}  # casefold name -> index in rows

    for entry in faction["metadata_roles"]:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        folded = name.casefold()
        if folded in metadata_casefold:
            other = rows[metadata_casefold[folded]]["name"]
            raise ValueError(
                f"{faction['name']!r}: {other!r} and {name!r} differ only by "
                "case (metadata.roles)"
            )
        metadata_casefold[folded] = len(rows)
        rows.append({
            "name": name,
            "description": entry.get("description") or None,
            "max_holders": None,
        })

    capacity_casefold: dict[str, str] = {}  # casefold name -> original key, new rows only
    for key, value in faction["capacities"].items():
        name = str(key).strip()
        if not name:
            continue
        folded = name.casefold()
        if folded in metadata_casefold:
            rows[metadata_casefold[folded]]["max_holders"] = value
            continue
        if folded in capacity_casefold:
            raise ValueError(
                f"{faction['name']!r}: {capacity_casefold[folded]!r} and {name!r} "
                "differ only by case (role_capacities)"
            )
        capacity_casefold[folded] = name
        rows.append({"name": name, "description": None, "max_holders": value})

    return rows


def _create_table(conn) -> None:
    conn.execute(text("""
        CREATE TABLE faction_role (
          id           TEXT PRIMARY KEY,
          world_id     TEXT NOT NULL REFERENCES world(id),
          faction_id   TEXT NOT NULL REFERENCES faction(id),
          name         TEXT NOT NULL,
          description  TEXT,
          max_holders  INTEGER,
          position     INTEGER NOT NULL DEFAULT 0,
          created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
          created_by   TEXT NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_faction_role_name "
        "ON faction_role(faction_id, name COLLATE NOCASE)"
    ))


def _insert_roles(conn, factions: list[dict], plans: dict[str, list[dict]]) -> int:
    inserted = 0
    for faction in factions:
        rows = plans[faction["id"]]
        if not rows:
            continue
        world_id = conn.execute(text(
            "SELECT world_id FROM entity WHERE id = :id"
        ), {"id": faction["id"]}).scalar_one()
        for position, row in enumerate(rows):
            conn.execute(text(
                "INSERT INTO faction_role "
                "(id, world_id, faction_id, name, description, max_holders, position, created_by) "
                "VALUES (:id, :world_id, :faction_id, :name, :description, :max_holders, :position, :created_by)"
            ), {
                "id": str(uuid.uuid4()),
                "world_id": world_id,
                "faction_id": faction["id"],
                "name": row["name"],
                "description": row["description"],
                "max_holders": row["max_holders"],
                "position": position,
                "created_by": "migration:0024-d",
            })
            inserted += 1
    return inserted


def _strip_metadata_roles(conn, factions: list[dict]) -> int:
    stripped = 0
    for faction in factions:
        if not faction["had_metadata_roles_key"]:
            continue
        raw = conn.execute(text(
            "SELECT metadata FROM entity WHERE id = :id"
        ), {"id": faction["id"]}).scalar_one()
        metadata = json.loads(raw) if raw else {}
        if not isinstance(metadata, dict) or "roles" not in metadata:
            continue
        new_metadata = {k: v for k, v in metadata.items() if k != "roles"}
        conn.execute(text(
            "UPDATE entity SET metadata = :metadata WHERE id = :id"
        ), {
            "metadata": json.dumps(new_metadata) if new_metadata else None,
            "id": faction["id"],
        })
        stripped += 1
    return stripped


def _drop_role_capacities(conn) -> None:
    conn.execute(text("ALTER TABLE faction DROP COLUMN role_capacities"))


def main() -> None:
    inspector = inspect(engine)
    if "faction_role" in inspector.get_table_names():
        print("Table 'faction_role' already exists — migration already applied, skipping.")
        return

    if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
        raise SystemExit(
            f"SQLite {'.'.join(map(str, MIN_SQLITE_VERSION))}+ is required for "
            f"ALTER TABLE ... DROP COLUMN (found {sqlite3.sqlite_version}). "
            "Upgrade SQLite, then re-run this migration — aborting, nothing written."
        )

    with engine.connect() as conn:
        factions = _load_factions(conn)

    plans: dict[str, list[dict]] = {}
    collisions: list[str] = []
    for faction in factions:
        try:
            plans[faction["id"]] = _plan_faction_roles(faction)
        except ValueError as exc:
            collisions.append(str(exc))

    if collisions:
        raise SystemExit(
            "Migration aborted — case collision(s) found, nothing written:\n"
            + "\n".join(f"  - {c}" for c in collisions)
            + "\nFix in the live UI (rename one of the colliding roles) and re-run."
        )

    with engine.begin() as conn:
        _create_table(conn)
        inserted = _insert_roles(conn, factions, plans)
        stripped = _strip_metadata_roles(conn, factions)
        _drop_role_capacities(conn)

    print(
        f"Migration v1.76 applied: faction_role table + index created, "
        f"{inserted} role row(s) inserted across {len(factions)} faction(s), "
        f"{stripped} metadata.roles key(s) stripped, "
        "faction.role_capacities column dropped."
    )


if __name__ == "__main__":
    main()
